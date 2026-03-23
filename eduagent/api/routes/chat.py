"""Chat routes — student chatbot endpoint."""

from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from eduagent.api.server import get_db
from eduagent.chat import student_chat
from eduagent.models import TeacherPersona

router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    lesson_id: str
    question: str
    history: list[dict[str, str]] = Field(default_factory=list)


@router.post("/chat")
async def chat_endpoint(req: ChatRequest):
    """Student asks a question about a lesson; bot answers in teacher's voice."""
    db = get_db()

    lesson_row = db.get_lesson(req.lesson_id)
    if not lesson_row:
        return JSONResponse({"error": "Lesson not found."}, status_code=404)

    lesson_data = json.loads(lesson_row["lesson_json"]) if lesson_row["lesson_json"] else {}

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
    except Exception as e:
        return JSONResponse({"error": f"Chat failed: {e}"}, status_code=500)

    db.insert_chat_message(req.lesson_id, "user", req.question)
    db.insert_chat_message(req.lesson_id, "assistant", response)

    return {"response": response, "lesson_id": req.lesson_id}
