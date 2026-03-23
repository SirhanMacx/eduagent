"""Tests for the student bot, class management, and MCP server."""

from __future__ import annotations

import asyncio
import json
import os
from unittest.mock import AsyncMock, patch

import pytest

from eduagent.models import AppConfig, DailyLesson, TeacherPersona
from eduagent.state import init_db


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _use_tmp_db(tmp_path, monkeypatch):
    """Route all state.py DB operations to a temp directory."""
    monkeypatch.setattr("eduagent.state.DEFAULT_DATA_DIR", tmp_path)
    init_db()


# ── Student session creation ────────────────────────────────────────


class TestStudentSessionCreation:
    def test_student_session_dataclass(self):
        from eduagent.student_bot import StudentSession

        session = StudentSession(
            student_id="stu-001",
            teacher_id="teacher-mac",
            class_code="MR-MAC-P3",
        )
        assert session.student_id == "stu-001"
        assert session.teacher_id == "teacher-mac"
        assert session.class_code == "MR-MAC-P3"
        assert session.message_count == 0

    def test_student_session_defaults(self):
        from eduagent.student_bot import StudentSession

        session = StudentSession(student_id="stu-002")
        assert session.teacher_id == ""
        assert session.current_lesson_id == ""
        assert session.class_code == ""


# ── Class creation and management ───────────────────────────────────


class TestClassCreation:
    def test_create_class_returns_code(self):
        from eduagent.student_bot import StudentBot

        bot = StudentBot()
        code = bot.create_class("teacher-001")
        assert code.startswith("CLASS-")
        assert len(code) == 12  # "CLASS-" + 6 hex chars

    def test_create_class_is_unique(self):
        from eduagent.student_bot import StudentBot

        bot = StudentBot()
        code1 = bot.create_class("teacher-001")
        code2 = bot.create_class("teacher-001")
        assert code1 != code2

    def test_get_class_returns_none_for_unknown(self):
        from eduagent.student_bot import StudentBot

        bot = StudentBot()
        assert bot.get_class("NONEXISTENT") is None

    def test_get_class_returns_info(self):
        from eduagent.student_bot import StudentBot

        bot = StudentBot()
        code = bot.create_class("teacher-mac")
        info = bot.get_class(code)
        assert info is not None
        assert info.class_code == code
        assert info.teacher_id == "teacher-mac"
        assert info.hint_mode is False


# ── Set active lesson ───────────────────────────────────────────────


class TestSetActiveLesson:
    def test_set_active_lesson(self):
        from eduagent.student_bot import StudentBot

        bot = StudentBot()
        code = bot.create_class("teacher-mac")

        lesson_data = json.dumps({"title": "Photosynthesis", "objective": "Learn about plants"})
        _run(bot.set_active_lesson(code, "lesson-1", "teacher-mac", lesson_data))

        info = bot.get_class(code)
        assert info.active_lesson_id == "lesson-1"
        assert info.active_lesson_json == lesson_data

    def test_set_active_lesson_creates_class_if_needed(self):
        from eduagent.student_bot import StudentBot

        bot = StudentBot()
        _run(bot.set_active_lesson("NEW-CLASS-01", "lesson-1", "teacher-new", '{"title": "Test"}'))

        info = bot.get_class("NEW-CLASS-01")
        assert info is not None
        assert info.teacher_id == "teacher-new"


# ── Handle question ─────────────────────────────────────────────────


class TestHandleQuestion:
    def test_unknown_class_code(self):
        from eduagent.student_bot import StudentBot

        bot = StudentBot()
        result = _run(bot.handle_message("What is photosynthesis?", "stu-001", "BAD-CODE"))
        assert "don't recognize" in result.lower()

    def test_no_active_lesson(self):
        from eduagent.student_bot import StudentBot

        bot = StudentBot()
        code = bot.create_class("teacher-001")
        result = _run(bot.handle_message("Help!", "stu-001", code))
        assert "hasn't activated" in result.lower()

    @patch("eduagent.chat.student_chat", new_callable=AsyncMock)
    def test_handle_question_returns_string(self, mock_chat):
        from eduagent.state import TeacherSession

        from eduagent.student_bot import StudentBot

        # Set up teacher session with persona
        session = TeacherSession(
            teacher_id="teacher-mac",
            persona=TeacherPersona(name="Mr. Mac", subject_area="Science"),
        )
        session.save()

        bot = StudentBot()
        code = bot.create_class("teacher-mac")
        lesson = json.dumps({
            "title": "Photosynthesis",
            "objective": "Explain photosynthesis",
            "do_now": "What do plants need?",
            "direct_instruction": "Plants use sunlight...",
            "guided_practice": "Label the diagram",
            "independent_work": "Answer questions 1-5",
        })
        _run(bot.set_active_lesson(code, "lesson-1", "teacher-mac", lesson))

        mock_chat.return_value = "Great question! Plants use sunlight to make food."

        result = _run(bot.handle_message("What is photosynthesis?", "stu-001", code))
        assert isinstance(result, str)
        assert len(result) > 0
        mock_chat.assert_called_once()


# ── Hint mode ───────────────────────────────────────────────────────


class TestHintMode:
    @patch("eduagent.chat.student_chat", new_callable=AsyncMock)
    def test_hint_mode_does_not_give_direct_answer(self, mock_chat):
        from eduagent.state import TeacherSession

        from eduagent.student_bot import StudentBot

        # Set up teacher with persona
        session = TeacherSession(
            teacher_id="teacher-hint",
            persona=TeacherPersona(name="Ms. Hint"),
        )
        session.save()

        bot = StudentBot()
        code = bot.create_class("teacher-hint")
        lesson = json.dumps({"title": "Test Lesson", "objective": "Test"})
        _run(bot.set_active_lesson(code, "lesson-1", "teacher-hint", lesson))

        # Enable hint mode
        bot.set_hint_mode(code, True)

        info = bot.get_class(code)
        assert info.hint_mode is True

        mock_chat.return_value = "Think about what plants need from the sun..."

        result = _run(bot.handle_message("What's the answer to #3?", "stu-002", code))
        assert isinstance(result, str)

        # Verify the hint mode instruction was passed to the chat function
        call_args = mock_chat.call_args
        question_arg = call_args.kwargs.get("question", "")
        assert "HINT MODE" in question_arg

    def test_set_hint_mode_toggle(self):
        from eduagent.student_bot import StudentBot

        bot = StudentBot()
        code = bot.create_class("teacher-toggle")

        bot.set_hint_mode(code, True)
        assert bot.get_class(code).hint_mode is True

        bot.set_hint_mode(code, False)
        assert bot.get_class(code).hint_mode is False


# ── Student report ──────────────────────────────────────────────────


class TestStudentReport:
    def test_empty_report(self):
        from eduagent.student_bot import StudentBot

        bot = StudentBot()
        code = bot.create_class("teacher-report")
        report = _run(bot.get_student_report(code))

        assert report["class_code"] == code
        assert report["student_count"] == 0
        assert report["total_messages"] == 0
        assert report["recent_questions"] == []

    @patch("eduagent.chat.student_chat", new_callable=AsyncMock)
    def test_report_after_questions(self, mock_chat):
        from eduagent.state import TeacherSession

        from eduagent.student_bot import StudentBot

        session = TeacherSession(
            teacher_id="teacher-rpt",
            persona=TeacherPersona(name="Mr. Report"),
        )
        session.save()

        bot = StudentBot()
        code = bot.create_class("teacher-rpt")
        lesson = json.dumps({"title": "History 101", "objective": "Learn history"})
        _run(bot.set_active_lesson(code, "lesson-1", "teacher-rpt", lesson))

        mock_chat.return_value = "The Civil War began in 1861."

        _run(bot.handle_message("When did the Civil War start?", "stu-A", code))
        _run(bot.handle_message("Who was president?", "stu-B", code))

        report = _run(bot.get_student_report(code))
        assert report["student_count"] == 2
        assert report["total_messages"] == 2
        assert len(report["recent_questions"]) == 2


# ── Router patterns ─────────────────────────────────────────────────


class TestRouterStudentBotPatterns:
    def test_start_student_bot_intent(self):
        from eduagent.router import Intent, parse_intent

        result = parse_intent("start student bot for lesson 1")
        assert result.intent == Intent.START_STUDENT_BOT

    def test_show_student_report_intent(self):
        from eduagent.router import Intent, parse_intent

        result = parse_intent("show me what students are asking")
        assert result.intent == Intent.SHOW_STUDENT_REPORT

    def test_set_hint_mode_intent(self):
        from eduagent.router import Intent, parse_intent

        result = parse_intent("set homework hint mode")
        assert result.intent == Intent.SET_HINT_MODE

    def test_activate_student_chat(self):
        from eduagent.router import Intent, parse_intent

        result = parse_intent("activate student chat")
        assert result.intent == Intent.START_STUDENT_BOT

    def test_student_activity_report(self):
        from eduagent.router import Intent, parse_intent

        result = parse_intent("student activity report")
        assert result.intent == Intent.SHOW_STUDENT_REPORT

    def test_disable_hint_mode(self):
        from eduagent.router import Intent, parse_intent

        result = parse_intent("disable hint mode")
        assert result.intent == Intent.SET_HINT_MODE


# ── MCP server ──────────────────────────────────────────────────────


class TestMCPServer:
    def test_mcp_server_import(self):
        from eduagent.mcp_server import mcp
        assert mcp is not None

    def test_mcp_tools_registered(self):
        from eduagent.mcp_server import mcp

        # FastMCP registers tools internally; verify our module loaded
        assert hasattr(mcp, "run")

    def test_mcp_tool_functions_exist(self):
        from eduagent.mcp_server import (
            generate_lesson,
            generate_unit,
            get_teacher_standards,
            ingest_materials,
            student_question,
        )

        assert callable(generate_lesson)
        assert callable(generate_unit)
        assert callable(ingest_materials)
        assert callable(student_question)
        assert callable(get_teacher_standards)
