"""Student chatbot engine — students ask questions, get answers in their teacher's voice.

The student bot is the other half of EDUagent. Teachers set up their persona and
activate a lesson; students join with a class code and ask questions about today's
lesson. The bot answers in the teacher's voice, gives hints (not answers) for
homework, and tracks what students are asking so the teacher can see patterns.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from eduagent.models import AppConfig, TeacherPersona
from eduagent.state import _get_conn, init_db


@dataclass
class StudentSession:
    """A student's active chat session."""

    student_id: str
    teacher_id: str = ""
    current_lesson_id: str = ""
    class_code: str = ""
    message_count: int = 0


@dataclass
class ClassInfo:
    """A teacher's class with an active lesson."""

    class_code: str
    teacher_id: str
    active_lesson_id: Optional[str] = None
    active_lesson_json: Optional[str] = None
    hint_mode: bool = False
    created_at: str = ""


class StudentBot:
    """Student-facing chatbot that answers questions in the teacher's voice."""

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or AppConfig.load()
        init_db()

    # ── Class management ─────────────────────────────────────────────────

    def create_class(self, teacher_id: str) -> str:
        """Create a new class and return its class code."""
        # Generate a short, readable class code
        code = f"CLASS-{uuid.uuid4().hex[:6].upper()}"
        with _get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO classes (class_code, teacher_id) VALUES (?, ?)",
                (code, teacher_id),
            )
        return code

    def get_class(self, class_code: str) -> Optional[ClassInfo]:
        """Load class info by code."""
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM classes WHERE class_code = ?", (class_code,)
            ).fetchone()
        if not row:
            return None
        return ClassInfo(
            class_code=row["class_code"],
            teacher_id=row["teacher_id"],
            active_lesson_id=row["active_lesson_id"],
            active_lesson_json=row["active_lesson_json"],
            hint_mode=bool(row["hint_mode"]),
            created_at=row["created_at"],
        )

    async def set_active_lesson(
        self, class_code: str, lesson_id: str, teacher_id: str, lesson_json: str = ""
    ) -> None:
        """Teacher sets which lesson is active for their class."""
        with _get_conn() as conn:
            # Ensure class exists
            row = conn.execute(
                "SELECT class_code FROM classes WHERE class_code = ?", (class_code,)
            ).fetchone()
            if not row:
                conn.execute(
                    """INSERT INTO classes
                    (class_code, teacher_id, active_lesson_id, active_lesson_json)
                    VALUES (?, ?, ?, ?)""",
                    (class_code, teacher_id, lesson_id, lesson_json),
                )
            else:
                conn.execute(
                    """UPDATE classes SET active_lesson_id = ?,
                    active_lesson_json = ?, teacher_id = ?
                    WHERE class_code = ?""",
                    (lesson_id, lesson_json, teacher_id, class_code),
                )

    def set_hint_mode(self, class_code: str, enabled: bool) -> None:
        """Toggle hint-only mode for a class (no direct answers to homework)."""
        with _get_conn() as conn:
            conn.execute(
                "UPDATE classes SET hint_mode = ? WHERE class_code = ?",
                (1 if enabled else 0, class_code),
            )

    # ── Student message handling ─────────────────────────────────────────

    async def handle_message(
        self, message: str, student_id: str, class_code: str
    ) -> str:
        """Handle a student message. Answers in teacher's voice using lesson context.

        Rules:
        - Give hints, not direct answers to homework questions (when hint mode on)
        - Use the teacher's vocabulary and tone
        - Reference specific parts of today's lesson
        - Track what the student asked (feeds back to teacher)
        - Encouraging, patient, uses teacher's actual phrases
        """
        # Load class info
        class_info = self.get_class(class_code)
        if not class_info:
            return "Hmm, I don't recognize that class code. Double-check with your teacher!"

        # Load teacher persona
        from eduagent.state import TeacherSession

        teacher_session = TeacherSession.load(class_info.teacher_id)
        persona = teacher_session.persona or TeacherPersona()

        # Load lesson context
        lesson_json: dict[str, Any] = {}
        if class_info.active_lesson_json:
            try:
                lesson_json = json.loads(class_info.active_lesson_json)
            except (json.JSONDecodeError, TypeError):
                pass

        if not lesson_json:
            return (
                "Your teacher hasn't activated a lesson yet. "
                "Check back soon — they'll set one up for you!"
            )

        # Update student session
        self._touch_student_session(student_id, class_code)

        # Build the response using the existing chat engine
        from eduagent.chat import student_chat

        # Build hint mode instruction
        hint_instruction = ""
        if class_info.hint_mode:
            hint_instruction = (
                "\n\nIMPORTANT — HINT MODE IS ON:\n"
                "- Do NOT give direct answers to homework or assessment questions.\n"
                "- Instead, guide the student with hints, leading questions, and scaffolding.\n"
                "- Encourage them to think through the problem step by step.\n"
                "- It's okay to confirm correct thinking or redirect wrong paths.\n"
            )

        # Get recent chat history for this student/class
        history = self._get_student_history(student_id, class_code, limit=6)

        answer = await student_chat(
            question=message + hint_instruction,
            lesson_json=lesson_json,
            persona=persona,
            chat_history=history,
            config=self.config,
        )

        # Log the question and answer
        self._log_question(
            student_id=student_id,
            class_code=class_code,
            question=message,
            answer=answer,
            lesson_topic=lesson_json.get("title", ""),
        )

        return answer

    # ── Reporting ────────────────────────────────────────────────────────

    async def get_student_report(self, class_code: str) -> dict:
        """Return what questions students asked (for teacher insight)."""
        with _get_conn() as conn:
            questions = conn.execute(
                """SELECT student_id, question, lesson_topic, created_at
                FROM student_questions WHERE class_code = ?
                ORDER BY created_at DESC LIMIT 50""",
                (class_code,),
            ).fetchall()

            student_count = conn.execute(
                "SELECT COUNT(DISTINCT student_id) as cnt FROM student_sessions WHERE class_code = ?",
                (class_code,),
            ).fetchone()

            total_messages = conn.execute(
                "SELECT SUM(message_count) as total FROM student_sessions WHERE class_code = ?",
                (class_code,),
            ).fetchone()

        return {
            "class_code": class_code,
            "student_count": student_count["cnt"] if student_count else 0,
            "total_messages": total_messages["total"] if total_messages and total_messages["total"] else 0,
            "recent_questions": [
                {
                    "student_id": q["student_id"],
                    "question": q["question"],
                    "topic": q["lesson_topic"],
                    "asked_at": q["created_at"],
                }
                for q in questions
            ],
        }

    # ── Internal helpers ─────────────────────────────────────────────────

    def _touch_student_session(self, student_id: str, class_code: str) -> None:
        """Create or update a student session, incrementing message count."""
        session_id = f"{student_id}:{class_code}"
        with _get_conn() as conn:
            existing = conn.execute(
                "SELECT id FROM student_sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE student_sessions SET message_count = message_count + 1, last_activity = ? WHERE id = ?",
                    (datetime.utcnow().isoformat(), session_id),
                )
            else:
                conn.execute(
                    """INSERT INTO student_sessions
                    (id, student_id, class_code, message_count, last_activity)
                    VALUES (?, ?, ?, 1, ?)""",
                    (session_id, student_id, class_code, datetime.utcnow().isoformat()),
                )

    def _log_question(
        self,
        student_id: str,
        class_code: str,
        question: str,
        answer: str,
        lesson_topic: str,
    ) -> None:
        """Log a student question for teacher reporting."""
        with _get_conn() as conn:
            conn.execute(
                """INSERT INTO student_questions
                (id, student_id, class_code, question, answer, lesson_topic)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), student_id, class_code, question, answer, lesson_topic),
            )

    def _get_student_history(
        self, student_id: str, class_code: str, limit: int = 6
    ) -> list[dict[str, str]]:
        """Get recent Q&A history for a student in a class."""
        with _get_conn() as conn:
            rows = conn.execute(
                """SELECT question, answer FROM student_questions
                WHERE student_id = ? AND class_code = ?
                ORDER BY created_at DESC LIMIT ?""",
                (student_id, class_code, limit),
            ).fetchall()
        # Reverse to chronological order and format as chat history
        history: list[dict[str, str]] = []
        for row in reversed(rows):
            history.append({"role": "user", "content": row["question"]})
            history.append({"role": "assistant", "content": row["answer"]})
        return history
