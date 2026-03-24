"""Chat routes — student chatbot endpoint."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from eduagent.api.server import get_db, limiter
from eduagent.chat import student_chat
from eduagent.models import TeacherPersona

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    lesson_id: str
    question: str
    history: list[dict[str, str]] = Field(default_factory=list)


@router.post("/chat")
@limiter.limit("30/minute")
async def chat_endpoint(request: Request, req: ChatRequest):
    """Student asks a question about a lesson; bot answers in teacher's voice."""
    db = get_db()

    lesson_row = db.get_lesson(req.lesson_id)
    if not lesson_row:
        return JSONResponse({"error": "Lesson not found."}, status_code=404)

    try:
        lesson_data = json.loads(lesson_row["lesson_json"]) if lesson_row["lesson_json"] else {}
    except (json.JSONDecodeError, TypeError) as exc:
        logger.warning("Failed to parse lesson_json for lesson %s: %s", req.lesson_id, exc)
        lesson_data = {}

    teacher = db.get_default_teacher()
    if not teacher or not teacher.get("persona_json"):
        return JSONResponse({"error": "No teacher persona found."}, status_code=400)

    persona = TeacherPersona.model_validate_json(teacher["persona_json"])

    history = req.history
    if not history:
        db_history = db.get_chat_history(req.lesson_id, limit=10)
        history = [{"role": m["role"], "content": m["content"]} for m in reversed(db_history)]

    try:
        response = await student_chat(
            question=req.question,
            lesson_json=lesson_data,
            persona=persona,
            chat_history=history,
        )
    except Exception:
        logger.error("Chat failed", exc_info=True)
        return JSONResponse({"error": "Chat failed. Please try again."}, status_code=500)

    db.insert_chat_message(req.lesson_id, "user", req.question)
    db.insert_chat_message(req.lesson_id, "assistant", response)

    return {"response": response, "lesson_id": req.lesson_id}
