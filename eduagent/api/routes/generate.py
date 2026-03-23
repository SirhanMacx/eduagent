"""Generation routes — unit plans, lessons, materials, full pipeline."""

from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from eduagent.api.server import get_db
from eduagent.models import DailyLesson, TeacherPersona, UnitPlan

router = APIRouter(tags=["generate"])


class UnitRequest(BaseModel):
    topic: str
    grade_level: str = "8"
    subject: str = "Science"
    duration_weeks: int = 3
    standards: list[str] = Field(default_factory=list)


class LessonRequest(BaseModel):
    unit_id: str
    lesson_number: int = 1


class MaterialsRequest(BaseModel):
    lesson_id: str


class FullRequest(BaseModel):
    topic: str
    grade_level: str = "8"
    subject: str = "Science"
    duration_weeks: int = 3
    standards: list[str] = Field(default_factory=list)
    include_homework: bool = True
    max_lessons: int | None = None


def _get_persona(db) -> tuple[TeacherPersona | None, str | None]:
    """Load persona from the default teacher in the DB."""
    teacher = db.get_default_teacher()
    if not teacher or not teacher.get("persona_json"):
        return None, None
    persona = TeacherPersona.model_validate_json(teacher["persona_json"])
    return persona, teacher["id"]


@router.post("/unit")
async def create_unit(req: UnitRequest):
    """Generate a unit plan."""
    from eduagent.planner import plan_unit

    db = get_db()
    persona, teacher_id = _get_persona(db)
    if not persona:
        return JSONResponse({"error": "No persona found. Upload teaching materials first."}, status_code=400)

    try:
        unit = await plan_unit(
            subject=req.subject,
            grade_level=req.grade_level,
            topic=req.topic,
            duration_weeks=req.duration_weeks,
            persona=persona,
            standards=req.standards or None,
        )
    except Exception as e:
        return JSONResponse({"error": f"Unit generation failed: {e}"}, status_code=500)

    unit_id = db.insert_unit(
        teacher_id=teacher_id,
        title=unit.title,
        subject=unit.subject,
        grade_level=unit.grade_level,
        topic=unit.topic,
        unit_json=unit.model_dump_json(),
    )

    return {"unit_id": unit_id, "unit": unit.model_dump()}


@router.post("/lesson")
async def create_lesson(req: LessonRequest):
    """Generate a single lesson plan for a unit."""
    from eduagent.lesson import generate_lesson

    db = get_db()
    persona, _ = _get_persona(db)
    if not persona:
        return JSONResponse({"error": "No persona found."}, status_code=400)

    unit_row = db.get_unit(req.unit_id)
    if not unit_row:
        return JSONResponse({"error": "Unit not found."}, status_code=404)

    unit = UnitPlan.model_validate_json(unit_row["unit_json"])

    try:
        lesson = await generate_lesson(
            lesson_number=req.lesson_number,
            unit=unit,
            persona=persona,
        )
    except Exception as e:
        return JSONResponse({"error": f"Lesson generation failed: {e}"}, status_code=500)

    lesson_id = db.insert_lesson(
        unit_id=req.unit_id,
        lesson_number=lesson.lesson_number,
        title=lesson.title,
        lesson_json=lesson.model_dump_json(),
    )

    return {"lesson_id": lesson_id, "lesson": lesson.model_dump()}


@router.post("/materials")
async def create_materials(req: MaterialsRequest):
    """Generate materials for a lesson."""
    from eduagent.materials import generate_all_materials

    db = get_db()
    persona, _ = _get_persona(db)
    if not persona:
        return JSONResponse({"error": "No persona found."}, status_code=400)

    lesson_row = db.get_lesson(req.lesson_id)
    if not lesson_row:
        return JSONResponse({"error": "Lesson not found."}, status_code=404)

    lesson = DailyLesson.model_validate_json(lesson_row["lesson_json"])

    try:
        materials = await generate_all_materials(lesson, persona)
    except Exception as e:
        return JSONResponse({"error": f"Materials generation failed: {e}"}, status_code=500)

    db.update_lesson_materials(req.lesson_id, materials.model_dump_json())

    return {"lesson_id": req.lesson_id, "materials": materials.model_dump()}


@router.post("/full")
async def full_pipeline(req: FullRequest):
    """End-to-end: generate unit + all lessons + materials. Returns SSE progress events."""
    from eduagent.lesson import generate_lesson
    from eduagent.materials import generate_all_materials
    from eduagent.planner import plan_unit

    db = get_db()
    persona, teacher_id = _get_persona(db)
    if not persona:
        return JSONResponse({"error": "No persona found."}, status_code=400)

    async def event_stream():
        yield {"event": "progress", "data": json.dumps({"step": "unit", "status": "generating", "message": "Generating unit plan..."})}

        try:
            unit = await plan_unit(
                subject=req.subject,
                grade_level=req.grade_level,
                topic=req.topic,
                duration_weeks=req.duration_weeks,
                persona=persona,
                standards=req.standards or None,
            )
        except Exception as e:
            yield {"event": "error", "data": json.dumps({"error": f"Unit generation failed: {e}"})}
            return

        unit_id = db.insert_unit(
            teacher_id=teacher_id,
            title=unit.title,
            subject=unit.subject,
            grade_level=unit.grade_level,
            topic=unit.topic,
            unit_json=unit.model_dump_json(),
        )

        yield {"event": "progress", "data": json.dumps({"step": "unit", "status": "done", "unit_id": unit_id, "title": unit.title, "lesson_count": len(unit.daily_lessons)})}

        briefs = unit.daily_lessons
        if req.max_lessons:
            briefs = briefs[: req.max_lessons]

        lesson_ids = []
        for brief in briefs:
            yield {"event": "progress", "data": json.dumps({"step": "lesson", "status": "generating", "lesson_number": brief.lesson_number, "topic": brief.topic})}

            try:
                lesson = await generate_lesson(
                    lesson_number=brief.lesson_number,
                    unit=unit,
                    persona=persona,
                    include_homework=req.include_homework,
                )
            except Exception as e:
                yield {"event": "progress", "data": json.dumps({"step": "lesson", "status": "error", "lesson_number": brief.lesson_number, "error": str(e)})}
                continue

            lid = db.insert_lesson(
                unit_id=unit_id,
                lesson_number=lesson.lesson_number,
                title=lesson.title,
                lesson_json=lesson.model_dump_json(),
            )
            lesson_ids.append(lid)

            yield {"event": "progress", "data": json.dumps({"step": "lesson", "status": "done", "lesson_id": lid, "lesson_number": lesson.lesson_number, "title": lesson.title})}

        for lid in lesson_ids:
            lesson_row = db.get_lesson(lid)
            if not lesson_row:
                continue

            yield {"event": "progress", "data": json.dumps({"step": "materials", "status": "generating", "lesson_id": lid})}

            lesson_obj = DailyLesson.model_validate_json(lesson_row["lesson_json"])

            try:
                materials = await generate_all_materials(lesson_obj, persona)
                db.update_lesson_materials(lid, materials.model_dump_json())
            except Exception:
                pass

            yield {"event": "progress", "data": json.dumps({"step": "materials", "status": "done", "lesson_id": lid})}

        yield {"event": "done", "data": json.dumps({"unit_id": unit_id, "lesson_count": len(lesson_ids)})}

    return EventSourceResponse(event_stream())


@router.get("/units")
async def list_units():
    """List all generated units."""
    db = get_db()
    units = db.list_units()
    for u in units:
        u["lesson_count"] = len(db.list_lessons(u["id"]))
    return {"units": units}


@router.get("/lessons/{unit_id}")
async def list_lessons(unit_id: str):
    """List all lessons for a unit."""
    db = get_db()
    lessons = db.list_lessons(unit_id)
    return {"lessons": lessons}
