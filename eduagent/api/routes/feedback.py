"""Feedback routes — rating, analysis, and prompt improvement."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from eduagent.api.server import get_db
from eduagent.feedback import analyze_feedback, collect_feedback
from eduagent.improver import improve_prompts

router = APIRouter(tags=["feedback"])


class FeedbackRequest(BaseModel):
    lesson_id: str
    rating: int
    notes: str = ""
    sections_edited: list[str] = Field(default_factory=list)


class ImproveRequest(BaseModel):
    feedback_window_days: int = 7


@router.post("/feedback")
async def submit_feedback(req: FeedbackRequest):
    """Teacher rates generated content."""
    if not 1 <= req.rating <= 5:
        return JSONResponse({"error": "Rating must be 1-5."}, status_code=400)

    db = get_db()

    lesson = db.get_lesson(req.lesson_id)
    if not lesson:
        return JSONResponse({"error": "Lesson not found."}, status_code=404)

    feedback_id = collect_feedback(
        db=db,
        lesson_id=req.lesson_id,
        rating=req.rating,
        notes=req.notes,
        sections_edited=req.sections_edited,
    )

    db.rate_lesson(req.lesson_id, req.rating)

    return {"feedback_id": feedback_id, "message": "Feedback recorded. Thank you!"}


@router.get("/feedback/{lesson_id}")
async def get_feedback(lesson_id: str):
    """Get all feedback for a lesson."""
    db = get_db()
    feedback_list = db.get_feedback_for_lesson(lesson_id)
    return {"feedback": feedback_list}


@router.get("/feedback-analysis")
async def feedback_analysis(days: int = 7):
    """Get feedback analysis summary."""
    db = get_db()
    analysis = analyze_feedback(db, days)
    return {"analysis": analysis}


@router.post("/improve")
async def trigger_improvement(req: ImproveRequest | None = None):
    """Trigger a prompt improvement cycle."""
    db = get_db()
    days = req.feedback_window_days if req else 7

    try:
        result = await improve_prompts(db, feedback_window_days=days)
    except Exception as e:
        return JSONResponse({"error": f"Improvement failed: {e}"}, status_code=500)

    return result
