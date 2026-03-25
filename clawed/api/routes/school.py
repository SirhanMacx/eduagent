"""School deployment routes — shared curriculum library and roster."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from clawed.api.deps import get_db

router = APIRouter(tags=["school"])


# ── Request models ────────────────────────────────────────────────────


class SchoolSetupRequest(BaseModel):
    name: str
    state: str = ""
    district: str = ""
    grade_levels: list[str] = Field(default_factory=list)


class AddTeacherRequest(BaseModel):
    school_id: str
    teacher_id: str
    role: str = "teacher"
    department: str = ""


class ShareContentRequest(BaseModel):
    school_id: str
    teacher_id: str
    content_type: str = "unit"
    content_id: str
    department: str = ""


class RateSharedRequest(BaseModel):
    shared_id: str
    rating: int


# ── Endpoints ─────────────────────────────────────────────────────────


@router.post("/school/setup")
async def setup_school(req: SchoolSetupRequest):
    from clawed.school import setup_school as _setup

    db = get_db()
    school_id = _setup(db, name=req.name, state=req.state, district=req.district, grade_levels=req.grade_levels)
    return {"school_id": school_id, "name": req.name}


@router.get("/school/{school_id}")
async def get_school(school_id: str):
    db = get_db()
    school = db.get_school(school_id)
    if not school:
        return JSONResponse({"error": "School not found"}, status_code=404)
    return school


@router.post("/school/add-teacher")
async def add_teacher(req: AddTeacherRequest):
    from clawed.school import add_teacher as _add

    db = get_db()
    school = db.get_school(req.school_id)
    if not school:
        return JSONResponse({"error": "School not found"}, status_code=404)
    _add(db, req.school_id, req.teacher_id, role=req.role, department=req.department)
    return {"status": "added", "teacher_id": req.teacher_id, "school_id": req.school_id}


@router.get("/school/{school_id}/teachers")
async def list_teachers(school_id: str):
    db = get_db()
    school = db.get_school(school_id)
    if not school:
        return JSONResponse({"error": "School not found"}, status_code=404)
    teachers = db.list_school_teachers(school_id)
    return {"school_id": school_id, "teachers": teachers}


@router.post("/school/share")
async def share_content(req: ShareContentRequest):
    from clawed.school import share_lesson, share_unit

    db = get_db()
    if req.content_type == "unit":
        sid = share_unit(db, req.school_id, req.teacher_id, req.content_id, department=req.department)
    elif req.content_type == "lesson":
        sid = share_lesson(db, req.school_id, req.teacher_id, req.content_id, department=req.department)
    else:
        return JSONResponse({"error": "content_type must be 'unit' or 'lesson'"}, status_code=400)

    if sid is None:
        return JSONResponse({"error": f"{req.content_type} not found"}, status_code=404)
    return {"shared_id": sid, "content_type": req.content_type}


@router.get("/school/{school_id}/shared-library")
async def shared_library(school_id: str, department: str = "", limit: int = 50):
    """Return top-rated shared content from the school's curriculum library."""
    from clawed.school import get_shared_library

    db = get_db()
    school = db.get_school(school_id)
    if not school:
        return JSONResponse({"error": "School not found"}, status_code=404)
    items = get_shared_library(db, school_id, department=department, limit=limit)
    return {"school_id": school_id, "items": items}


@router.post("/school/rate-shared")
async def rate_shared(req: RateSharedRequest):
    if req.rating < 1 or req.rating > 5:
        return JSONResponse({"error": "Rating must be 1-5"}, status_code=400)
    db = get_db()
    db.rate_shared_content(req.shared_id, req.rating)
    return {"status": "rated", "shared_id": req.shared_id, "rating": req.rating}
