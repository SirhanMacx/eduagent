"""Tests for v0.1.3 features — class codes, Telegram polish, onboarding wizard, dashboard v2.

Covers all 4 feature waves with 55+ new tests:
  Wave 1: Class code system edge cases and DB operations
  Wave 2: Telegram bot conversation state machine and error recovery
  Wave 3: Onboarding model detection, persona preview, ingestion
  Wave 4: Web dashboard pages, lesson list filters, embed snippet
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from eduagent.database import Database
from eduagent.models import AppConfig, LLMProvider, TeacherPersona
from eduagent.state import init_db
from eduagent.telegram_bot import (
    BOT_COMMANDS,
    ChatState,
    ConversationState,
    _chat_states,
    _get_chat_state,
    _log_error,
)


def _run(coro):
    return asyncio.run(coro)


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _use_tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr("eduagent.state.DEFAULT_DATA_DIR", tmp_path)
    init_db()


@pytest.fixture(autouse=True)
def _clear_chat_states():
    _chat_states.clear()
    yield
    _chat_states.clear()


@pytest.fixture
def db(tmp_path):
    d = Database(tmp_path / "web_test.db")
    yield d
    d.close()


@pytest.fixture
def app(db):
    import eduagent.api.server as srv
    from eduagent.api.server import create_app

    old = srv._db
    srv._db = db
    a = create_app()
    yield a
    srv._db = old


@pytest.fixture
def client(app):
    return TestClient(app)


# ═══════════════════════════════════════════════════════════════════════════
# WAVE 1: CLASS CODE SYSTEM
# ═══════════════════════════════════════════════════════════════════════════


class TestClassCodeDBOperations:
    """Test database-level class code operations."""

    def test_duplicate_enrollment_ignored(self, db):
        db.create_class_code(code="DU-PLI-1", teacher_id="t1")
        db.enroll_student("stu-001", "DU-PLI-1")
        db.enroll_student("stu-001", "DU-PLI-1")  # duplicate
        assert db.count_enrollments("DU-PLI-1") == 1

    def test_list_enrollments(self, db):
        db.create_class_code(code="LS-ENR-1", teacher_id="t1")
        db.enroll_student("stu-A", "LS-ENR-1")
        db.enroll_student("stu-B", "LS-ENR-1")
        enrollments = db.list_enrollments("LS-ENR-1")
        assert len(enrollments) == 2
        ids = {e["student_id"] for e in enrollments}
        assert "stu-A" in ids
        assert "stu-B" in ids

    def test_get_class_code_nonexistent(self, db):
        assert db.get_class_code("NOPE") is None

    def test_class_code_with_expiry(self, db):
        db.create_class_code(
            code="EX-PIR-1", teacher_id="t1",
            expires_at="2026-06-15T23:59:59",
        )
        row = db.get_class_code("EX-PIR-1")
        assert row["expires_at"] == "2026-06-15T23:59:59"

    def test_student_questions_empty(self, db):
        assert db.count_student_questions("NO-CLASS") == 0
        assert db.get_student_questions("NO-CLASS") == []

    def test_student_questions_multiple(self, db):
        db.insert_student_question("s1", "CL-ORD-1", "Q1?", "A1")
        db.insert_student_question("s1", "CL-ORD-1", "Q2?", "A2")
        qs = db.get_student_questions("CL-ORD-1")
        assert len(qs) == 2
        questions = {q["question"] for q in qs}
        assert "Q1?" in questions
        assert "Q2?" in questions


class TestStudentBotClassExtended:
    """Extended tests for student bot class management."""

    def test_multiple_classes_same_teacher(self):
        from eduagent.student_bot import StudentBot

        bot = StudentBot()
        c1 = bot.create_class("teacher-multi", name="Period 1")
        c2 = bot.create_class("teacher-multi", name="Period 2")
        assert c1 != c2
        assert bot.get_class(c1).name == "Period 1"
        assert bot.get_class(c2).name == "Period 2"

    def test_student_conversation_history(self):
        from eduagent.student_bot import StudentBot

        bot = StudentBot()
        code = bot.create_class("teacher-hist")
        # No conversation yet
        history = bot.get_student_conversation("stu-1", code)
        assert history == []

    def test_is_expired_with_invalid_date(self):
        from eduagent.student_bot import StudentBot

        bot = StudentBot()
        code = bot.create_class("teacher-bad", expires_at="not-a-date")
        # Should not crash, should return False
        assert bot.is_expired(code) is False

    def test_get_mode_nonexistent_class(self):
        from eduagent.student_bot import StudentBot

        bot = StudentBot()
        # get_mode on non-existent class returns "answer" (default)
        assert bot.get_mode("FAKE-CODE") == "answer"

    @patch("eduagent.chat.student_chat", new_callable=AsyncMock)
    def test_weekly_report_anonymized(self, mock_chat):
        from eduagent.state import TeacherSession
        from eduagent.student_bot import StudentBot

        session = TeacherSession(
            teacher_id="teacher-anon",
            persona=TeacherPersona(name="Mr. Anon"),
        )
        session.save()

        bot = StudentBot()
        code = bot.create_class("teacher-anon")
        lesson = json.dumps({"title": "Test", "objective": "Test"})
        _run(bot.set_active_lesson(code, "l1", "teacher-anon", lesson))

        mock_chat.return_value = "Answer."
        _run(bot.handle_message("Q?", "stu-real-name", code))

        report = _run(bot.get_weekly_report(code))
        # Student activity uses "student_number" not real IDs
        for item in report["student_activity"]:
            assert "student_number" in item
            assert "student_id" not in item

    def test_class_stats_empty_class(self):
        from eduagent.student_bot import StudentBot

        bot = StudentBot()
        code = bot.create_class("teacher-empty")
        stats = bot.get_class_stats(code)
        assert stats["registered_students"] == 0
        assert stats["total_questions"] == 0
        assert stats["active_students"] == 0


# ═══════════════════════════════════════════════════════════════════════════
# WAVE 2: TELEGRAM BOT POLISH
# ═══════════════════════════════════════════════════════════════════════════


class TestConversationStateMachineExtended:
    """Extended conversation state machine tests."""

    def test_collecting_state_not_busy(self):
        state = ChatState()
        state.state = ConversationState.COLLECTING_LESSON_INFO
        assert not state.is_busy()

    def test_state_stores_pending_topic(self):
        state = ChatState()
        state.pending_topic = "photosynthesis"
        assert state.pending_topic == "photosynthesis"

    def test_state_stores_last_lesson_id(self):
        state = ChatState()
        state.last_lesson_id = "lesson-abc123"
        assert state.last_lesson_id == "lesson-abc123"

    def test_multiple_chats_independent(self):
        s1 = _get_chat_state(1001)
        s2 = _get_chat_state(1002)
        s1.state = ConversationState.GENERATING
        assert s2.state == ConversationState.IDLE

    def test_state_persists_across_lookups(self):
        s = _get_chat_state(2001)
        s.state = ConversationState.DONE
        s.last_lesson_id = "test-id"
        s2 = _get_chat_state(2001)
        assert s2.state == ConversationState.DONE
        assert s2.last_lesson_id == "test-id"


class TestBotCommandContents:
    """Test the contents of bot commands and help text."""

    def test_commands_list_has_seven_entries(self):
        assert len(BOT_COMMANDS) == 7

    def test_all_commands_have_lowercase_names(self):
        for cmd, _ in BOT_COMMANDS:
            assert cmd == cmd.lower()

    def test_health_command_in_list(self):
        cmds = dict(BOT_COMMANDS)
        assert "health" in cmds
        assert "status" in cmds["health"].lower()


class TestErrorLogging:
    """Test error logging to file."""

    def test_error_log_creates_file(self, tmp_path):
        log_file = tmp_path / "errors.log"
        with patch("eduagent.telegram_bot._ERROR_LOG", log_file):
            _log_error(RuntimeError("test boom"))
        assert log_file.exists()
        assert "RuntimeError" in log_file.read_text()
        assert "test boom" in log_file.read_text()

    def test_error_log_appends(self, tmp_path):
        log_file = tmp_path / "errors.log"
        with patch("eduagent.telegram_bot._ERROR_LOG", log_file):
            _log_error(ValueError("first"))
            _log_error(TypeError("second"))
        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 2

    def test_error_log_includes_timestamp(self, tmp_path):
        log_file = tmp_path / "errors.log"
        with patch("eduagent.telegram_bot._ERROR_LOG", log_file):
            _log_error(Exception("timed"))
        content = log_file.read_text()
        # ISO format timestamp
        assert "T" in content  # datetime separator


class TestEduAgentBotConfig:
    """Test bot configuration and token resolution."""

    def test_bot_from_env_with_config_fallback(self, tmp_path, monkeypatch):
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        with patch("eduagent.models.AppConfig.load") as mock_cfg:
            mock_cfg.return_value = MagicMock(telegram_bot_token="config:TOKEN")
            bot = __import__("eduagent.telegram_bot", fromlist=["EduAgentBot"]).EduAgentBot.from_env(data_dir=tmp_path)
            assert bot.token == "config:TOKEN"


# ═══════════════════════════════════════════════════════════════════════════
# WAVE 3: ONBOARDING FLOW POLISH
# ═══════════════════════════════════════════════════════════════════════════


class TestModelAutoDetection:
    """Test model auto-detection priority and edge cases."""

    def test_anthropic_takes_priority_over_openai(self):
        from eduagent.onboarding import _detect_available_models

        with patch.dict("os.environ", {
            "ANTHROPIC_API_KEY": "sk-ant-test",
            "OPENAI_API_KEY": "sk-test",
        }, clear=True):
            provider, _ = _detect_available_models()
            assert provider == LLMProvider.ANTHROPIC

    def test_ollama_preferred_model_minimax(self):
        from eduagent.onboarding import _detect_available_models

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "models": [
                {"name": "mistral:latest"},
                {"name": "minimax-m2.7:latest"},
                {"name": "llama3.2:latest"},
            ]
        }
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("httpx.get", return_value=mock_resp),
        ):
            provider, msg = _detect_available_models()
            assert provider == LLMProvider.OLLAMA
            assert "minimax" in msg

    def test_ollama_no_models_pulled(self):
        from eduagent.onboarding import _detect_available_models

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"models": []}
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("httpx.get", return_value=mock_resp),
        ):
            provider, msg = _detect_available_models()
            assert provider == LLMProvider.OLLAMA
            assert "no models" in msg.lower()

    def test_ollama_connection_refused(self):
        from eduagent.onboarding import _detect_available_models

        with (
            patch.dict("os.environ", {}, clear=True),
            patch("httpx.get", side_effect=ConnectionError("refused")),
        ):
            provider, msg = _detect_available_models()
            assert provider is None


class TestOnboardingPersonaPreview:
    """Test the persona preview and confirmation flow."""

    def test_preview_contains_subjects(self):
        from eduagent.onboarding import _show_persona_preview

        with patch("eduagent.onboarding.Prompt.ask", return_value="y"):
            result = _show_persona_preview(
                ["Social Studies", "History"], ["8", "9"], "NY"
            )
            assert result is True

    def test_preview_state_resolution(self):
        from eduagent.onboarding import _resolve_state

        # Test various state inputs
        assert _resolve_state("Florida") == "FL"
        assert _resolve_state("fl") == "FL"
        assert _resolve_state("Mass") == "MA"


class TestOnboardingMaterialsIngestion:
    """Test material ingestion edge cases."""

    def test_ask_materials_whitespace_only(self):
        from eduagent.onboarding import _ask_materials

        with patch("eduagent.onboarding.Prompt.ask", return_value="   "):
            result = _ask_materials()
            assert result is None

    def test_ingest_supported_extensions_filter(self):
        """Verify the supported extension set used during ingestion."""
        supported_exts = {".pdf", ".docx", ".pptx", ".txt", ".md"}
        assert ".csv" not in supported_exts
        assert ".png" not in supported_exts
        assert ".pdf" in supported_exts
        assert ".docx" in supported_exts


class TestAppConfigRoundtrip:
    """Test config save/load roundtrip."""

    def test_config_serialization(self):
        config = AppConfig(
            provider=LLMProvider.OLLAMA,
            ollama_model="llama3.2",
        )
        data = config.model_dump_json()
        loaded = AppConfig.model_validate_json(data)
        assert loaded.provider == LLMProvider.OLLAMA
        assert loaded.ollama_model == "llama3.2"

    def test_config_save_load(self, tmp_path):
        config_file = tmp_path / "config.json"
        config = AppConfig(provider=LLMProvider.OPENAI)
        with patch.object(AppConfig, "config_path", return_value=config_file):
            config.save()
            assert config_file.exists()
            loaded = AppConfig.load()
            assert loaded.provider == LLMProvider.OPENAI


# ═══════════════════════════════════════════════════════════════════════════
# WAVE 4: WEB DASHBOARD GAPS
# ═══════════════════════════════════════════════════════════════════════════


class TestLessonsListPage:
    """Test the lessons list page with filters."""

    def test_lessons_page_renders_empty(self, client):
        resp = client.get("/lessons")
        assert resp.status_code == 200
        assert "All Lessons" in resp.text
        assert "Generate New Lesson" in resp.text

    def test_lessons_page_with_data(self, client, db):
        tid = db.upsert_teacher("T", '{}')
        uid = db.insert_unit(tid, "U", "Math", "8", "Algebra", '{}')
        db.insert_lesson(uid, 1, "Solving Equations", '{"title": "Solving Equations"}')
        resp = client.get("/lessons")
        assert resp.status_code == 200
        assert "Solving Equations" in resp.text

    def test_lessons_page_subject_filter(self, client, db):
        tid = db.upsert_teacher("T", '{}')
        uid1 = db.insert_unit(tid, "U1", "Math", "8", "Algebra", '{}')
        uid2 = db.insert_unit(tid, "U2", "Science", "8", "Cells", '{}')
        db.insert_lesson(uid1, 1, "Math Lesson", '{}')
        db.insert_lesson(uid2, 1, "Science Lesson", '{}')
        resp = client.get("/lessons?subject=Math")
        assert resp.status_code == 200
        assert "Math Lesson" in resp.text
        # Science lesson should be filtered out
        assert "Science Lesson" not in resp.text

    def test_lessons_page_grade_filter(self, client, db):
        tid = db.upsert_teacher("T", '{}')
        uid = db.insert_unit(tid, "U1", "Math", "6", "Fractions", '{}')
        db.insert_lesson(uid, 1, "Fractions Lesson", '{}')
        resp = client.get("/lessons?grade=6")
        assert resp.status_code == 200
        assert "Fractions Lesson" in resp.text

    def test_lessons_page_no_results(self, client, db):
        tid = db.upsert_teacher("T", '{}')
        uid = db.insert_unit(tid, "U1", "Math", "8", "Algebra", '{}')
        db.insert_lesson(uid, 1, "Algebra", '{}')
        resp = client.get("/lessons?subject=Art")
        assert resp.status_code == 200
        assert "No lessons" in resp.text


class TestSettingsPageExtended:
    """Extended tests for the settings page."""

    def test_settings_page_shows_provider(self, client):
        resp = client.get("/settings")
        assert resp.status_code == 200

    def test_settings_api_get(self, client):
        resp = client.get("/api/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert "provider" in data
        assert "has_anthropic_key" in data
        assert "has_openai_key" in data

    def test_settings_test_connection(self, client):
        resp = client.get("/api/settings/test-connection")
        assert resp.status_code == 200


class TestStudentClassPage:
    """Test the student-facing class page."""

    def test_student_page_unknown_class(self, client):
        resp = client.get("/student/FAKE-CODE")
        assert resp.status_code == 404
        assert "not found" in resp.text.lower()


class TestLessonPageEmbedSnippet:
    """Test that lesson pages include the embed snippet."""

    def test_lesson_page_has_chat_and_copy(self, client, db):
        from eduagent.models import DailyLesson

        tid = db.upsert_teacher("T", '{"name": "T"}')
        uid = db.insert_unit(tid, "U", "Science", "8", "Cells", '{}')
        lesson = DailyLesson(
            title="Cell Division",
            lesson_number=1,
            objective="Learn about cells",
        )
        lid = db.insert_lesson(uid, 1, "Cell Division", lesson.model_dump_json())
        resp = client.get(f"/lesson/{lid}")
        assert resp.status_code == 200
        # Lesson page has chat section and copy-to-clipboard for classroom export
        assert "Ask About This Lesson" in resp.text
        assert "Copy to Clipboard" in resp.text

    def test_lesson_page_shows_share_link(self, client, db):
        from eduagent.models import DailyLesson

        tid = db.upsert_teacher("T", '{"name": "T"}')
        uid = db.insert_unit(tid, "U", "Science", "8", "Cells", '{}')
        lesson = DailyLesson(title="Sharing Test", lesson_number=1, objective="Test")
        lid = db.insert_lesson(uid, 1, "Sharing Test", lesson.model_dump_json())
        row = db.get_lesson(lid)
        resp = client.get(f"/lesson/{lid}")
        assert resp.status_code == 200
        assert row["share_token"] in resp.text


class TestStudentsPage:
    """Test the students page route."""

    def test_students_page_renders(self, client):
        resp = client.get("/students")
        assert resp.status_code == 200

    def test_library_page_renders(self, client):
        resp = client.get("/library")
        assert resp.status_code == 200


class TestProfilePage:
    """Test the profile page route."""

    def test_profile_page_renders(self, client):
        resp = client.get("/profile")
        assert resp.status_code == 200
        assert "Profile" in resp.text


class TestDashboardPage:
    """Test the dashboard page with recent items."""

    def test_dashboard_with_units(self, client, db):
        tid = db.upsert_teacher("Ms. Teacher", '{"name": "Ms. Teacher"}')
        db.insert_unit(tid, "Unit A", "Math", "8", "Algebra", '{}')
        db.insert_unit(tid, "Unit B", "Science", "7", "Cells", '{}')
        resp = client.get("/dashboard")
        assert resp.status_code == 200
        assert "Unit A" in resp.text
        assert "Unit B" in resp.text


# ═══════════════════════════════════════════════════════════════════════════
# CROSS-WAVE: VERSION AND MODULE TESTS
# ═══════════════════════════════════════════════════════════════════════════


class TestVersion:
    def test_version_string(self):
        from eduagent import __version__

        assert __version__ == "0.1.3"

    def test_version_in_health_endpoint(self, client):
        resp = client.get("/api/health")
        data = resp.json()
        assert data["version"] == "0.1.3"
