"""Lesson sharing routes — create and retrieve shareable lesson URLs."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from clawed.api.server import get_db

router = APIRouter(tags=["lessons"])


@router.post("/lessons/{lesson_id}/share")
async def create_share_link(lesson_id: str):
    """Generate a shareable URL for a lesson."""
    db = get_db()
    lesson = db.get_lesson(lesson_id)
    if not lesson:
        return JSONResponse({"error": "Lesson not found"}, status_code=404)

    token = lesson.get("share_token")
    if not token:
        return JSONResponse({"error": "No share token available"}, status_code=500)

    share_url = f"/shared/{token}"
    return {"share_url": share_url, "token": token}
