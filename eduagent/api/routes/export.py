"""Export routes — PDF, DOCX, Markdown downloads and share links."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse

from eduagent.api.server import get_db
from eduagent.models import DailyLesson

router = APIRouter(tags=["export"])


@router.get("/export/{lesson_id}")
async def export_lesson_endpoint(lesson_id: str, fmt: str = "markdown"):
    """Export a lesson as Markdown, PDF, or DOCX."""
    from eduagent.exporter import export_lesson

    db = get_db()
    lesson_row = db.get_lesson(lesson_id)
    if not lesson_row:
        return JSONResponse({"error": "Lesson not found."}, status_code=404)

    lesson = DailyLesson.model_validate_json(lesson_row["lesson_json"])
    tmp_dir = Path(tempfile.mkdtemp())

    if fmt == "markdown":
        path = export_lesson(lesson, tmp_dir, fmt="markdown")
        return FileResponse(str(path), filename=path.name, media_type="text/markdown")
    elif fmt == "pdf":
        path = export_lesson(lesson, tmp_dir, fmt="pdf")
        return FileResponse(str(path), filename=path.name, media_type="application/pdf")
    elif fmt == "docx":
        path = export_lesson(lesson, tmp_dir, fmt="docx")
        return FileResponse(
            str(path),
            filename=path.name,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    else:
        return JSONResponse({"error": f"Unsupported format: {fmt}"}, status_code=400)


@router.get("/share/{token}")
async def share_lesson_api(token: str):
    """Get a lesson by its share token (JSON API)."""
    db = get_db()
    lesson_row = db.get_lesson_by_token(token)
    if not lesson_row:
        return JSONResponse({"error": "Lesson not found."}, status_code=404)

    lesson_data = json.loads(lesson_row["lesson_json"]) if lesson_row["lesson_json"] else {}
    return {
        "lesson_id": lesson_row["id"],
        "title": lesson_row["title"],
        "share_token": token,
        "lesson": lesson_data,
    }
