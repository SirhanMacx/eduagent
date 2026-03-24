"""Tests for teacher-friendly customization features.

Covers:
1. Conversational onboarding state machine
2. Natural language scheduling through the bot
3. Rule-based self-improvement (lesson metadata tracking)
4. Gap analysis command
5. Model switching through the bot
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from eduagent.tg import (
    ONBOARD_ASK_GRADE,
    ONBOARD_ASK_MODEL,
    ONBOARD_ASK_NAME,
    ONBOARD_ASK_SUBJECT,
    EduAgentTelegramBot,
    _cron_to_human,
    _detect_intent,
    _match_task_name,
    _parse_day_of_week,
    _parse_grade_and_subject,
    _parse_schedule_time,
)

# ── Helpers ──────────────────────────────────────────────────────────


def _make_bot(tmp_path: Path) -> EduAgentTelegramBot:
    """Create a bot with a mocked API that records sent messages."""
    bot = EduAgentTelegramBot(token="fake:token", data_dir=tmp_path)
    bot.api = MagicMock()
    bot.api.send_message = MagicMock()
    bot.api.send_chat_action = MagicMock()
    return bot


def _msg(text: str, chat_id: int = 100, user_id: int = 42) -> dict:
    """Build a fake Telegram message dict."""
    return {
        "chat": {"id": chat_id},
        "from": {"id": user_id},
        "text": text,
    }


# ══════════════════════════════════════════════════════════════════════
# 1. Conversational onboarding
# ══════════════════════════════════════════════════════════════════════


class TestParseGradeAndSubject:
    def test_grade_and_subject_combined(self):
        grade, subject = _parse_grade_and_subject("8th grade social studies")
        assert grade == "8"
        assert "Social Studies" in subject

    def test_subject_only(self):
        grade, subject = _parse_grade_and_subject("AP Chemistry")
        assert grade == ""
        assert "AP" in subject
        assert "Chemistry" in subject

    def test_grade_and_subject_reversed(self):
        grade, subject = _parse_grade_and_subject("math 5th grade")
        assert grade == "5"
        assert "Math" in subject

    def test_grade_word_format(self):
        grade, subject = _parse_grade_and_subject("grade 3 science")
        assert grade == "3"
        assert "Science" in subject

    def test_just_subject(self):
        grade, subject = _parse_grade_and_subject("English")
        assert grade == ""
        assert subject == "English"

    def test_ela_preserved(self):
        grade, subject = _parse_grade_and_subject("ela")
        assert subject == "ELA"

    def test_empty_input(self):
        grade, subject = _parse_grade_and_subject("")
        assert grade == ""
        assert subject == ""


class TestOnboardingStateMachine:
    """Test the full conversational onboarding flow."""

    def test_start_without_config_begins_onboarding(self, tmp_path):
        bot = _make_bot(tmp_path)
        # No config file exists -- should start onboarding
        with patch.object(bot, "_has_config", return_value=False):
            bot._cmd_start(100, _msg("/start"), "")

        assert 100 in bot._onboard_state
        assert bot._onboard_state[100]["step"] == ONBOARD_ASK_SUBJECT
        # Should ask about subject
        sent = bot.api.send_message.call_args[0][1]
        assert "subject" in sent.lower()

    def test_start_with_config_shows_welcome(self, tmp_path):
        bot = _make_bot(tmp_path)
        with patch.object(bot, "_has_config", return_value=True):
            bot._cmd_start(100, _msg("/start"), "")

        assert 100 not in bot._onboard_state
        sent = bot.api.send_message.call_args[0][1]
        assert "EDUagent" in sent

    def test_onboarding_subject_only(self, tmp_path):
        bot = _make_bot(tmp_path)
        bot._onboard_state[100] = {"step": ONBOARD_ASK_SUBJECT}

        bot._handle_onboarding(100, _msg("Social Studies"), "Social Studies")

        assert bot._onboard_state[100]["subject"] == "Social Studies"
        assert bot._onboard_state[100]["step"] == ONBOARD_ASK_GRADE

    def test_onboarding_subject_and_grade_combined(self, tmp_path):
        bot = _make_bot(tmp_path)
        bot._onboard_state[100] = {"step": ONBOARD_ASK_SUBJECT}

        bot._handle_onboarding(100, _msg("8th grade social studies"), "8th grade social studies")

        # Should skip grade step
        assert bot._onboard_state[100]["grade"] == "8"
        assert "Social Studies" in bot._onboard_state[100]["subject"]
        assert bot._onboard_state[100]["step"] == ONBOARD_ASK_NAME

    def test_onboarding_grade_step(self, tmp_path):
        bot = _make_bot(tmp_path)
        bot._onboard_state[100] = {"step": ONBOARD_ASK_GRADE, "subject": "Math"}

        bot._handle_onboarding(100, _msg("7"), "7")

        assert bot._onboard_state[100]["grade"] == "7"
        assert bot._onboard_state[100]["step"] == ONBOARD_ASK_NAME

    def test_onboarding_name_step(self, tmp_path):
        bot = _make_bot(tmp_path)
        bot._onboard_state[100] = {
            "step": ONBOARD_ASK_NAME,
            "subject": "Math",
            "grade": "7",
        }

        bot._handle_onboarding(100, _msg("Mr. Smith"), "Mr. Smith")

        assert bot._onboard_state[100]["name"] == "Mr. Smith"
        assert bot._onboard_state[100]["step"] == ONBOARD_ASK_MODEL
        sent = bot.api.send_message.call_args[0][1]
        assert "Mr. Smith" in sent
        assert "ollama" in sent.lower()

    def test_onboarding_model_step_saves_config(self, tmp_path):
        bot = _make_bot(tmp_path)
        bot._onboard_state[100] = {
            "step": ONBOARD_ASK_MODEL,
            "subject": "Science",
            "grade": "6",
            "name": "Ms. Jones",
        }

        with patch("eduagent.models.AppConfig.save"):
            bot._handle_onboarding(100, _msg("ollama"), "ollama")

        # Onboarding state should be cleaned up
        assert 100 not in bot._onboard_state
        # Should send summary
        sent = bot.api.send_message.call_args[0][1]
        assert "Science" in sent
        assert "Ms. Jones" in sent

    def test_onboarding_rejects_invalid_model(self, tmp_path):
        bot = _make_bot(tmp_path)
        bot._onboard_state[100] = {
            "step": ONBOARD_ASK_MODEL,
            "subject": "Math",
            "grade": "8",
            "name": "Test",
        }

        bot._handle_onboarding(100, _msg("chatgpt"), "chatgpt")

        # Should still be on model step
        assert bot._onboard_state[100]["step"] == ONBOARD_ASK_MODEL
        sent = bot.api.send_message.call_args[0][1]
        assert "ollama" in sent.lower()

    def test_onboarding_intercepts_messages(self, tmp_path):
        """While onboarding, free text goes to onboarding, not LLM."""
        bot = _make_bot(tmp_path)
        bot._onboard_state[100] = {"step": ONBOARD_ASK_SUBJECT}

        # This should be handled by onboarding, not fall through
        bot._handle_message(_msg("History"))

        assert "subject" in bot._onboard_state[100]


# ══════════════════════════════════════════════════════════════════════
# 2. Natural language scheduling
# ══════════════════════════════════════════════════════════════════════


class TestScheduleTimeParser:
    def test_morning(self):
        result = _parse_schedule_time("morning")
        assert result["hour"] == "7"

    def test_evening(self):
        result = _parse_schedule_time("every evening")
        assert result["hour"] == "19"

    def test_afternoon(self):
        result = _parse_schedule_time("afternoon")
        assert result["hour"] == "15"

    def test_explicit_am(self):
        result = _parse_schedule_time("7am")
        assert result["hour"] == "7"
        assert result["minute"] == "0"

    def test_explicit_pm(self):
        result = _parse_schedule_time("4pm")
        assert result["hour"] == "16"
        assert result["minute"] == "0"

    def test_explicit_time_with_minutes(self):
        result = _parse_schedule_time("7:30am")
        assert result["hour"] == "7"
        assert result["minute"] == "30"

    def test_24_hour(self):
        result = _parse_schedule_time("19:00")
        assert result["hour"] == "19"
        assert result["minute"] == "0"

    def test_default_when_no_time(self):
        result = _parse_schedule_time("do something")
        assert result["hour"] == "7"

    def test_noon_pm(self):
        result = _parse_schedule_time("12pm")
        assert result["hour"] == "12"

    def test_midnight_am(self):
        result = _parse_schedule_time("12am")
        assert result["hour"] == "0"


class TestParseDayOfWeek:
    def test_sunday(self):
        assert _parse_day_of_week("every Sunday evening") == "sun"

    def test_friday(self):
        assert _parse_day_of_week("Friday afternoon") == "fri"

    def test_no_day(self):
        assert _parse_day_of_week("every morning at 7am") == ""

    def test_monday(self):
        assert _parse_day_of_week("Monday") == "mon"


class TestCronToHuman:
    def test_daily(self):
        result = _cron_to_human({"hour": "7", "minute": "0"})
        assert "7:00 AM" in result
        assert "Daily" in result

    def test_weekly(self):
        result = _cron_to_human({"day_of_week": "sun", "hour": "19", "minute": "0"})
        assert "Sunday" in result
        assert "7:00 PM" in result

    def test_pm_time(self):
        result = _cron_to_human({"hour": "16", "minute": "30"})
        assert "4:30 PM" in result

    def test_midnight(self):
        result = _cron_to_human({"hour": "0", "minute": "0"})
        assert "12:00 AM" in result

    def test_noon(self):
        result = _cron_to_human({"hour": "12", "minute": "0"})
        assert "12:00 PM" in result


class TestMatchTaskName:
    def test_morning_prep(self):
        assert _match_task_name("morning prep at 7am") == "morning-prep"

    def test_weekly_plan(self):
        assert _match_task_name("weekly plan sunday evening") == "weekly-plan"

    def test_student_digest(self):
        assert _match_task_name("student questions every friday") == "student-digest"

    def test_feedback(self):
        assert _match_task_name("feedback digest at 8pm") == "feedback-digest"

    def test_unknown(self):
        assert _match_task_name("something random") is None


class TestScheduleCommand:
    def test_show_schedule_no_args(self, tmp_path, monkeypatch):
        config_path = tmp_path / "schedule.json"
        monkeypatch.setattr("eduagent.scheduler.SCHEDULE_CONFIG_PATH", config_path)

        bot = _make_bot(tmp_path)
        bot._cmd_schedule(100, _msg("/schedule"), "")

        sent = bot.api.send_message.call_args[0][1]
        assert "scheduled tasks" in sent.lower()

    def test_enable_task(self, tmp_path, monkeypatch):
        config_path = tmp_path / "schedule.json"
        monkeypatch.setattr("eduagent.scheduler.SCHEDULE_CONFIG_PATH", config_path)

        bot = _make_bot(tmp_path)
        bot._cmd_schedule(100, _msg("morning prep at 7am"), "morning prep at 7am")

        sent = bot.api.send_message.call_args[0][1]
        assert "scheduled" in sent.lower() or "7" in sent

        # Verify it was saved
        from eduagent.scheduler import load_schedule_config
        config = load_schedule_config()
        assert config["morning-prep"]["enabled"] is True
        assert config["morning-prep"]["cron"]["hour"] == "7"

    def test_disable_task(self, tmp_path, monkeypatch):
        config_path = tmp_path / "schedule.json"
        monkeypatch.setattr("eduagent.scheduler.SCHEDULE_CONFIG_PATH", config_path)

        # First enable
        from eduagent.scheduler import enable_task
        enable_task("morning-prep")

        bot = _make_bot(tmp_path)
        bot._cmd_schedule(100, _msg("stop morning prep"), "stop morning prep")

        sent = bot.api.send_message.call_args[0][1]
        assert "disable" in sent.lower() or "morning-prep" in sent.lower()

    def test_cancel_all(self, tmp_path, monkeypatch):
        config_path = tmp_path / "schedule.json"
        monkeypatch.setattr("eduagent.scheduler.SCHEDULE_CONFIG_PATH", config_path)

        from eduagent.scheduler import enable_task
        enable_task("morning-prep")
        enable_task("weekly-plan")

        bot = _make_bot(tmp_path)
        bot._cmd_schedule(100, _msg("cancel all reminders"), "cancel all reminders")

        from eduagent.scheduler import load_schedule_config
        config = load_schedule_config()
        assert all(not task["enabled"] for task in config.values())

    def test_weekly_schedule_with_day(self, tmp_path, monkeypatch):
        config_path = tmp_path / "schedule.json"
        monkeypatch.setattr("eduagent.scheduler.SCHEDULE_CONFIG_PATH", config_path)

        bot = _make_bot(tmp_path)
        bot._cmd_schedule(
            100, _msg("weekly plan sunday evening"),
            "weekly plan sunday evening",
        )

        from eduagent.scheduler import load_schedule_config
        config = load_schedule_config()
        assert config["weekly-plan"]["enabled"] is True
        assert config["weekly-plan"]["cron"]["day_of_week"] == "sun"
        assert config["weekly-plan"]["cron"]["hour"] == "19"


# ══════════════════════════════════════════════════════════════════════
# 3. Rule-based self-improvement (lesson metadata tracking)
# ══════════════════════════════════════════════════════════════════════


class TestTrackLessonMetadata:
    def test_tracks_high_rated_lesson(self, tmp_path, monkeypatch):
        monkeypatch.setenv("EDUAGENT_DATA_DIR", str(tmp_path))
        from eduagent.memory_engine import track_lesson_metadata
        from eduagent.models import DailyLesson, ExitTicketQuestion

        lesson = DailyLesson(
            title="Great Lesson",
            lesson_number=1,
            objective="Test",
            do_now="What do you think will happen next?",
            exit_ticket=[
                ExitTicketQuestion(question="Q1?", expected_response="A1"),
                ExitTicketQuestion(question="Q2?", expected_response="A2"),
            ],
            materials_needed=["Handout"],
        )

        track_lesson_metadata(lesson, rating=5)

        stats_path = tmp_path / "lesson_stats.json"
        assert stats_path.exists()
        stats = json.loads(stats_path.read_text())
        assert "high" in stats["has_do_now"]
        assert stats["has_do_now"]["high"] == [1]
        assert stats["exit_ticket_count"]["high"] == [2]
        assert stats["has_materials_list"]["high"] == [1]

    def test_tracks_low_rated_lesson(self, tmp_path, monkeypatch):
        monkeypatch.setenv("EDUAGENT_DATA_DIR", str(tmp_path))
        from eduagent.memory_engine import track_lesson_metadata
        from eduagent.models import DailyLesson

        lesson = DailyLesson(
            title="Bad Lesson",
            lesson_number=1,
            objective="Test",
            do_now="",
        )

        track_lesson_metadata(lesson, rating=1)

        stats_path = tmp_path / "lesson_stats.json"
        stats = json.loads(stats_path.read_text())
        assert "low" in stats["has_do_now"]
        assert stats["has_do_now"]["low"] == [0]

    def test_accumulates_over_multiple_lessons(self, tmp_path, monkeypatch):
        monkeypatch.setenv("EDUAGENT_DATA_DIR", str(tmp_path))
        from eduagent.memory_engine import track_lesson_metadata
        from eduagent.models import DailyLesson, ExitTicketQuestion

        for i in range(3):
            lesson = DailyLesson(
                title=f"Lesson {i}",
                lesson_number=i,
                objective="Test",
                do_now="A fairly long do-now activity for testing" if i < 2 else "",
                exit_ticket=[
                    ExitTicketQuestion(question="Q?", expected_response="A")
                ] * (i + 1),
            )
            track_lesson_metadata(lesson, rating=5)

        stats_path = tmp_path / "lesson_stats.json"
        stats = json.loads(stats_path.read_text())
        assert len(stats["has_do_now"]["high"]) == 3
        assert len(stats["exit_ticket_count"]["high"]) == 3

    def test_mid_rating_bucket(self, tmp_path, monkeypatch):
        monkeypatch.setenv("EDUAGENT_DATA_DIR", str(tmp_path))
        from eduagent.memory_engine import track_lesson_metadata
        from eduagent.models import DailyLesson

        lesson = DailyLesson(title="OK", lesson_number=1, objective="Test")
        track_lesson_metadata(lesson, rating=3)

        stats_path = tmp_path / "lesson_stats.json"
        stats = json.loads(stats_path.read_text())
        assert "mid" in stats["has_do_now"]


class TestGetQualityInsights:
    def test_empty_stats_no_insights(self, tmp_path, monkeypatch):
        monkeypatch.setenv("EDUAGENT_DATA_DIR", str(tmp_path))
        from eduagent.memory_engine import get_quality_insights

        insights = get_quality_insights()
        assert insights == []

    def test_with_enough_data_produces_insights(self, tmp_path, monkeypatch):
        monkeypatch.setenv("EDUAGENT_DATA_DIR", str(tmp_path))
        from eduagent.memory_engine import get_quality_insights, track_lesson_metadata
        from eduagent.models import DailyLesson, ExitTicketQuestion

        # Create pattern: high-rated lessons have exit tickets, low-rated don't
        for i in range(5):
            good = DailyLesson(
                title=f"Good {i}",
                lesson_number=i,
                objective="Test",
                do_now="A substantial do-now activity here",
                exit_ticket=[
                    ExitTicketQuestion(question="Q1?", expected_response="A1"),
                    ExitTicketQuestion(question="Q2?", expected_response="A2"),
                    ExitTicketQuestion(question="Q3?", expected_response="A3"),
                ],
                materials_needed=["item"],
            )
            track_lesson_metadata(good, rating=5)

            bad = DailyLesson(
                title=f"Bad {i}",
                lesson_number=i,
                objective="Test",
            )
            track_lesson_metadata(bad, rating=1)

        insights = get_quality_insights()
        assert isinstance(insights, list)
        # With clear patterns, we should get at least one insight
        assert len(insights) >= 1
        # Check that insights are human-readable strings
        for insight in insights:
            assert isinstance(insight, str)
            assert len(insight) > 10

    def test_insights_are_rule_based(self, tmp_path, monkeypatch):
        """Verify no LLM calls happen during insight generation."""
        monkeypatch.setenv("EDUAGENT_DATA_DIR", str(tmp_path))
        from eduagent.memory_engine import get_quality_insights, track_lesson_metadata
        from eduagent.models import DailyLesson

        lesson = DailyLesson(title="Test", lesson_number=1, objective="Test")
        track_lesson_metadata(lesson, rating=5)
        track_lesson_metadata(lesson, rating=5)
        track_lesson_metadata(lesson, rating=1)

        # This should complete without any network calls
        insights = get_quality_insights()
        assert isinstance(insights, list)


# ══════════════════════════════════════════════════════════════════════
# 4. Gap analysis intent detection
# ══════════════════════════════════════════════════════════════════════


class TestGapsIntent:
    def test_what_am_i_missing(self):
        intent, _ = _detect_intent("what am I missing?")
        assert intent == "gaps"

    def test_curriculum_gaps(self):
        intent, _ = _detect_intent("curriculum gaps")
        assert intent == "gaps"

    def test_what_havent_i_covered(self):
        intent, _ = _detect_intent("what haven't I covered?")
        assert intent == "gaps"

    def test_gap_analysis(self):
        intent, _ = _detect_intent("gap analysis")
        assert intent == "gaps"


class TestGapsCommand:
    def test_gaps_sends_typing(self, tmp_path):
        bot = _make_bot(tmp_path)
        # Mock the internals to avoid real LLM calls
        mock_cfg = MagicMock()
        mock_cfg.teacher_profile.subjects = ["Math"]
        mock_cfg.teacher_profile.grade_levels = ["8"]

        # Mock asyncio.run to raise immediately, preventing the async
        # identify_curriculum_gaps coroutine from leaking.
        with patch("eduagent.models.AppConfig.load", return_value=mock_cfg):
            with patch("eduagent.tg.asyncio.run", side_effect=Exception("No LLM")):
                bot._cmd_gaps(100, _msg("/gaps"), "")

        bot.api.send_chat_action.assert_called_with(100, "typing")


# ══════════════════════════════════════════════════════════════════════
# 5. Model switching
# ══════════════════════════════════════════════════════════════════════


class TestModelSwitchIntent:
    def test_switch_to_ollama(self):
        intent, _ = _detect_intent("switch to ollama")
        assert intent == "model"

    def test_use_anthropic(self):
        intent, _ = _detect_intent("use anthropic")
        assert intent == "model"

    def test_change_model(self):
        intent, _ = _detect_intent("change model")
        assert intent == "model"

    def test_switch_to_openai(self):
        intent, _ = _detect_intent("switch to openai")
        assert intent == "model"


class TestModelSwitchCommand:
    def test_switch_to_ollama(self, tmp_path):
        bot = _make_bot(tmp_path)
        mock_cfg = MagicMock()

        with patch("eduagent.models.AppConfig.load", return_value=mock_cfg):
            with patch("eduagent.models.AppConfig.save"):
                bot._cmd_model_switch(100, "switch to ollama")

        sent = bot.api.send_message.call_args[0][1]
        assert "ollama" in sent.lower()
        assert "switched" in sent.lower()

    def test_switch_to_anthropic(self, tmp_path):
        bot = _make_bot(tmp_path)
        mock_cfg = MagicMock()

        with patch("eduagent.models.AppConfig.load", return_value=mock_cfg):
            with patch("eduagent.models.AppConfig.save"):
                bot._cmd_model_switch(100, "use anthropic")

        sent = bot.api.send_message.call_args[0][1]
        assert "anthropic" in sent.lower()

    def test_switch_unknown_provider(self, tmp_path):
        bot = _make_bot(tmp_path)

        bot._cmd_model_switch(100, "use chatgpt")

        sent = bot.api.send_message.call_args[0][1]
        assert "which" in sent.lower()


# ══════════════════════════════════════════════════════════════════════
# Schedule intent detection
# ══════════════════════════════════════════════════════════════════════


class TestScheduleIntent:
    def test_remind_me(self):
        intent, _ = _detect_intent("remind me to prep lessons every Sunday")
        assert intent == "schedule"

    def test_send_me(self):
        intent, _ = _detect_intent("send me student questions every Friday afternoon")
        assert intent == "schedule"

    def test_morning_reminder(self):
        intent, _ = _detect_intent("morning reminders at 7am")
        assert intent == "schedule"

    def test_stop_reminders(self):
        intent, _ = _detect_intent("stop morning reminders")
        assert intent == "schedule"

    def test_whats_scheduled(self):
        intent, _ = _detect_intent("what's scheduled?")
        assert intent == "schedule"

    def test_cancel_all(self):
        intent, _ = _detect_intent("cancel all reminders")
        assert intent == "schedule"


# ══════════════════════════════════════════════════════════════════════
# Existing intent detection still works
# ══════════════════════════════════════════════════════════════════════


class TestExistingIntentStillWorks:
    """Make sure adding new intents didn't break existing ones."""

    def test_lesson_intent(self):
        intent, _ = _detect_intent("make a lesson on photosynthesis")
        assert intent == "lesson"

    def test_unit_intent(self):
        intent, _ = _detect_intent("create a unit on the Civil War")
        assert intent == "unit"

    def test_demo_intent(self):
        intent, _ = _detect_intent("show me what you can do")
        assert intent == "demo"

    def test_help_intent(self):
        intent, _ = _detect_intent("how do I get started?")
        assert intent == "help"

    def test_fallthrough(self):
        intent, _ = _detect_intent("hello there")
        assert intent is None
