"""Lesson sharing and management routes."""

from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from eduagent.api.server import get_db

router = APIRouter(tags=["lessons"])


@router.get("/units")
async def list_units():
    db = get_db()
    units = db.list_units()
    return {"units": units}


@router.get("/lessons/{unit_id}")
async def list_lessons(unit_id: str):
    db = get_db()
    lessons = db.list_lessons(unit_id)
    return {"lessons": lessons}


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


@router.get("/share/{token}")
async def get_shared_lesson(token: str):
    """Retrieve a lesson by its share token (public, no auth)."""
    db = get_db()
    lesson = db.get_lesson_by_token(token)
    if not lesson:
        return JSONResponse({"error": "Shared lesson not found"}, status_code=404)

    lesson_data = json.loads(lesson["lesson_json"]) if lesson.get("lesson_json") else {}
    return {
        "id": lesson["id"],
        "title": lesson.get("title", ""),
        "lesson_number": lesson.get("lesson_number"),
        "lesson_data": lesson_data,
        "share_token": token,
    }
