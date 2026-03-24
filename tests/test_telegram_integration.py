"""Integration tests for the EDUagent Telegram bot.

Tests: /start, /lesson flow, /health, error recovery (LLM fails -> retry -> fallback),
conversation state machine, command menu registration, and action callbacks.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from eduagent.telegram_bot import (
    ACTION_CALLBACK_PREFIX,
    BOT_COMMANDS,
    RATING_CALLBACK_PREFIX,
    ChatState,
    ConversationState,
    EduAgentBot,
    _chat_states,
    _get_chat_state,
    _log_error,
)

# ── Helpers ────────────────────────────────────────────────────────────────


def _make_update(text: str, user_id: int = 12345, chat_id: int = 99):
    """Create a mock Telegram Update with a text message."""
    update = MagicMock()
    update.message = MagicMock()
    update.message.text = text
    update.message.from_user = MagicMock()
    update.message.from_user.id = user_id
    update.message.chat = MagicMock()
    update.message.chat_id = chat_id
    update.message.chat.send_action = AsyncMock()
    update.message.reply_text = AsyncMock()
    return update


def _extract_handlers(bot: EduAgentBot) -> dict:
    """Run bot.start() with mocked telegram to capture registered handlers.

    Returns dict mapping command names (and 'handle_message') to their callbacks.
    """
    handlers: dict = {}

    mock_app = MagicMock()
    mock_app.run_polling = AsyncMock()
    mock_builder = MagicMock()
    mock_builder.token.return_value = mock_builder
    mock_builder.build.return_value = mock_app

    mock_ext = MagicMock()
    mock_ext.Application.builder.return_value = mock_builder
    mock_ext.filters.TEXT = MagicMock()
    mock_ext.filters.COMMAND = MagicMock()
    mock_ext.filters.TEXT.__and__ = MagicMock(return_value="text_filter")

    # Intercept CommandHandler to capture (command_name, callback)
    def fake_command_handler(name, callback, **kw):
        handlers[name] = callback
        return MagicMock(commands={name}, callback=callback)

    mock_ext.CommandHandler = fake_command_handler

    # Intercept MessageHandler to capture the text handler
    def fake_message_handler(filters, callback, **kw):
        handlers["handle_message"] = callback
        return MagicMock(callback=callback)

    mock_ext.MessageHandler = fake_message_handler

    # Intercept CallbackQueryHandler
    def fake_callback_handler(callback, pattern=None, **kw):
        handlers[f"callback:{pattern}"] = callback
        return MagicMock(callback=callback, pattern=pattern)

    mock_ext.CallbackQueryHandler = fake_callback_handler

    mock_app.add_handler = MagicMock()

    with patch.dict("sys.modules", {
        "telegram": MagicMock(),
        "telegram.ext": mock_ext,
    }):
        asyncio.run(bot.start())

    return handlers


@pytest.fixture(autouse=True)
def _clear_state():
    """Reset in-memory chat states between tests."""
    _chat_states.clear()
    yield
    _chat_states.clear()


# ── Conversation state machine ─────────────────────────────────────────────


class TestConversationStateMachine:
    def test_initial_state_is_idle(self):
        state = ChatState()
        assert state.state == ConversationState.IDLE
        assert not state.is_busy()

    def test_generating_state_is_busy(self):
        state = ChatState()
        state.state = ConversationState.GENERATING
        assert state.is_busy()

    def test_get_chat_state_creates_new(self):
        state = _get_chat_state(999)
        assert state.state == ConversationState.IDLE
        assert 999 in _chat_states

    def test_get_chat_state_returns_existing(self):
        state1 = _get_chat_state(42)
        state1.state = ConversationState.DONE
        state2 = _get_chat_state(42)
        assert state2.state == ConversationState.DONE

    def test_done_state_not_busy(self):
        state = ChatState()
        state.state = ConversationState.DONE
        assert not state.is_busy()

    def test_state_transitions_during_generation(self):
        state = ChatState()
        assert state.state == ConversationState.IDLE
        state.state = ConversationState.GENERATING
        assert state.is_busy()
        state.state = ConversationState.IDLE
        assert not state.is_busy()


# ── Bot initialization ─────────────────────────────────────────────────────


class TestBotInit:
    def test_creates_data_dir(self, tmp_path):
        data_dir = tmp_path / "test_eduagent"
        bot = EduAgentBot(token="fake:token", data_dir=data_dir)
        assert bot.token == "fake:token"
        assert data_dir.exists()

    def test_stores_token(self):
        bot = EduAgentBot(token="123:ABC")
        assert bot.token == "123:ABC"

    def test_default_data_dir(self):
        bot = EduAgentBot(token="fake:token")
        assert bot.data_dir == Path.home() / ".eduagent"


# ── Command menu registration ─────────────────────────────────────────────


class TestCommandMenu:
    def test_bot_commands_defined(self):
        cmd_names = [cmd for cmd, _ in BOT_COMMANDS]
        assert "lesson" in cmd_names
        assert "unit" in cmd_names
        assert "assess" in cmd_names
        assert "worksheet" in cmd_names
        assert "help" in cmd_names
        assert "health" in cmd_names

    def test_bot_commands_have_descriptions(self):
        for cmd, desc in BOT_COMMANDS:
            assert len(desc) > 5, f"Command /{cmd} needs a description"


# ── Handler registration ──────────────────────────────────────────────────


class TestHandlerRegistration:
    def test_extracts_all_command_handlers(self):
        bot = EduAgentBot(token="fake:token")
        handlers = _extract_handlers(bot)

        assert "start" in handlers
        assert "help" in handlers
        assert "status" in handlers
        assert "health" in handlers
        assert "lesson" in handlers
        assert "unit" in handlers
        assert "assess" in handlers
        assert "worksheet" in handlers
        assert "handle_message" in handlers

    def test_callback_handlers_registered(self):
        bot = EduAgentBot(token="fake:token")
        handlers = _extract_handlers(bot)

        # Rating and action callback handlers
        rating_key = f"callback:^{RATING_CALLBACK_PREFIX}"
        action_key = f"callback:^{ACTION_CALLBACK_PREFIX}"
        assert rating_key in handlers
        assert action_key in handlers


# ── /start → welcome message ─────────────────────────────────────────────


class TestStartCommand:
    def test_start_sends_welcome(self):
        bot = EduAgentBot(token="fake:token")
        handlers = _extract_handlers(bot)

        update = _make_update("/start")
        asyncio.run(handlers["start"](update, None))

        update.message.reply_text.assert_awaited_once()
        text = update.message.reply_text.call_args.args[0]
        assert "Welcome to EDUagent" in text
        assert "/help" in text

    def test_start_mentions_lesson_plans(self):
        bot = EduAgentBot(token="fake:token")
        handlers = _extract_handlers(bot)

        update = _make_update("/start")
        asyncio.run(handlers["start"](update, None))

        text = update.message.reply_text.call_args.args[0]
        assert "lesson plans" in text.lower()

    def test_start_mentions_teaching_voice(self):
        bot = EduAgentBot(token="fake:token")
        handlers = _extract_handlers(bot)

        update = _make_update("/start")
        asyncio.run(handlers["start"](update, None))

        text = update.message.reply_text.call_args.args[0]
        assert "teaching voice" in text.lower()


# ── /lesson → ask topic → respond → generate lesson ─────────────────────


class TestLessonFlow:
    def test_lesson_command_asks_for_topic(self):
        """Test /lesson prompts the user for a topic."""
        bot = EduAgentBot(token="fake:token")
        handlers = _extract_handlers(bot)

        update = _make_update("/lesson", chat_id=200)
        asyncio.run(handlers["lesson"](update, None))

        update.message.reply_text.assert_awaited_once()
        text = update.message.reply_text.call_args.args[0]
        assert "topic" in text.lower()

    def test_lesson_sets_collecting_state(self):
        """/lesson should transition state to COLLECTING_LESSON_INFO."""
        bot = EduAgentBot(token="fake:token")
        handlers = _extract_handlers(bot)

        update = _make_update("/lesson", chat_id=300)
        asyncio.run(handlers["lesson"](update, None))

        state = _get_chat_state(300)
        assert state.state == ConversationState.COLLECTING_LESSON_INFO

    @patch("eduagent.telegram_bot._get_store")
    @patch("eduagent.openclaw_plugin.handle_message", new_callable=AsyncMock)
    def test_user_message_triggers_generation(self, mock_process, mock_store):
        """User's message triggers LLM generation and returns the response."""
        mock_store.return_value = MagicMock(
            get=MagicMock(return_value=None),
            save=MagicMock(),
        )
        mock_process.return_value = "Here is your lesson on photosynthesis..."

        bot = EduAgentBot(token="fake:token")
        handlers = _extract_handlers(bot)

        update = _make_update("photosynthesis for 6th grade", chat_id=400)

        with patch("eduagent.openclaw_plugin.get_last_lesson_id", return_value=None):
            asyncio.run(handlers["handle_message"](update, None))

        update.message.reply_text.assert_awaited()
        text = update.message.reply_text.call_args.args[0]
        assert "photosynthesis" in text.lower()
        mock_process.assert_called_once()


# ── /health → returns status string ──────────────────────────────────────


class TestHealthCommand:
    @patch("eduagent.telegram_bot._get_store")
    def test_health_returns_all_fields(self, mock_store):
        """Test /health shows model, persona, lesson count, corpus size."""
        mock_store.return_value = MagicMock(
            get=MagicMock(return_value=None),
            save=MagicMock(),
        )

        bot = EduAgentBot(token="fake:token")
        handlers = _extract_handlers(bot)

        update = _make_update("/health", chat_id=500)

        with (
            patch("eduagent.models.AppConfig.load") as mock_cfg,
            patch("eduagent.state.TeacherSession.load") as mock_session,
            patch("eduagent.state.init_db"),
            patch("eduagent.state._get_conn") as mock_conn,
        ):
            mock_cfg.return_value = MagicMock(
                provider=MagicMock(value="ollama"),
                anthropic_model="claude-3-5-sonnet-20241022",
                openai_model="gpt-4o",
                ollama_model="llama3.2",
            )
            mock_session.return_value = MagicMock(persona=MagicMock())
            mock_ctx = MagicMock()
            mock_ctx.execute.return_value.fetchone.return_value = {"c": 5}
            mock_conn.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_conn.return_value.__exit__ = MagicMock(return_value=False)

            asyncio.run(handlers["health"](update, None))

        update.message.reply_text.assert_awaited_once()
        text = update.message.reply_text.call_args.args[0]
        assert "Model:" in text
        assert "Persona loaded:" in text
        assert "Lessons generated:" in text
        assert "Corpus examples:" in text

    @patch("eduagent.telegram_bot._get_store")
    def test_health_shows_persona_yes(self, mock_store):
        """When persona is loaded, health should say 'yes'."""
        mock_store.return_value = MagicMock(
            get=MagicMock(return_value=None),
            save=MagicMock(),
        )

        bot = EduAgentBot(token="fake:token")
        handlers = _extract_handlers(bot)
        update = _make_update("/health", chat_id=501)

        with (
            patch("eduagent.models.AppConfig.load") as mock_cfg,
            patch("eduagent.state.TeacherSession.load") as mock_session,
            patch("eduagent.state.init_db"),
            patch("eduagent.state._get_conn") as mock_conn,
        ):
            mock_cfg.return_value = MagicMock(
                provider=MagicMock(value="anthropic"),
                anthropic_model="claude-sonnet-4-20250514",
                openai_model="gpt-4o",
                ollama_model="llama3.2",
            )
            mock_session.return_value = MagicMock(persona=MagicMock())
            mock_ctx = MagicMock()
            mock_ctx.execute.return_value.fetchone.return_value = {"c": 0}
            mock_conn.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_conn.return_value.__exit__ = MagicMock(return_value=False)

            asyncio.run(handlers["health"](update, None))

        text = update.message.reply_text.call_args.args[0]
        assert "yes" in text

    @patch("eduagent.telegram_bot._get_store")
    def test_health_shows_persona_no(self, mock_store):
        """When no persona, health should say 'no'."""
        mock_store.return_value = MagicMock(
            get=MagicMock(return_value=None),
            save=MagicMock(),
        )

        bot = EduAgentBot(token="fake:token")
        handlers = _extract_handlers(bot)
        update = _make_update("/health", chat_id=502)

        with (
            patch("eduagent.models.AppConfig.load") as mock_cfg,
            patch("eduagent.state.TeacherSession.load") as mock_session,
            patch("eduagent.state.init_db"),
            patch("eduagent.state._get_conn") as mock_conn,
        ):
            mock_cfg.return_value = MagicMock(
                provider=MagicMock(value="ollama"),
                anthropic_model="claude-3-5-sonnet-20241022",
                openai_model="gpt-4o",
                ollama_model="llama3.2",
            )
            mock_session.return_value = MagicMock(persona=None)
            mock_ctx = MagicMock()
            mock_ctx.execute.return_value.fetchone.return_value = {"c": 0}
            mock_conn.return_value.__enter__ = MagicMock(return_value=mock_ctx)
            mock_conn.return_value.__exit__ = MagicMock(return_value=False)

            asyncio.run(handlers["health"](update, None))

        text = update.message.reply_text.call_args.args[0]
        assert "no" in text


# ── Error recovery: LLM fails → retry → fallback ────────────────────────


class TestErrorRecovery:
    @patch("eduagent.telegram_bot._get_store")
    @patch("eduagent.openclaw_plugin.handle_message", new_callable=AsyncMock)
    def test_retry_succeeds_on_second_attempt(self, mock_process, mock_store):
        """LLM fails once, retry succeeds — user gets the generated content."""
        mock_store.return_value = MagicMock(
            get=MagicMock(return_value=None),
            save=MagicMock(),
        )
        mock_process.side_effect = [
            RuntimeError("API timeout"),
            "Here is your lesson on science...",
        ]

        bot = EduAgentBot(token="fake:token")
        handlers = _extract_handlers(bot)

        update = _make_update("generate a lesson on science", chat_id=600)

        with patch("eduagent.openclaw_plugin.get_last_lesson_id", return_value=None):
            asyncio.run(handlers["handle_message"](update, None))

        assert mock_process.call_count == 2
        text = update.message.reply_text.call_args.args[0]
        assert "science" in text.lower()

    @patch("eduagent.telegram_bot._get_store")
    @patch("eduagent.openclaw_plugin.handle_message", new_callable=AsyncMock)
    def test_fallback_after_both_fail(self, mock_process, mock_store):
        """Both attempts fail — user gets a friendly fallback, no traceback."""
        mock_store.return_value = MagicMock(
            get=MagicMock(return_value=None),
            save=MagicMock(),
        )
        mock_process.side_effect = RuntimeError("API down")

        bot = EduAgentBot(token="fake:token")
        handlers = _extract_handlers(bot)

        update = _make_update("generate a lesson", chat_id=601)
        asyncio.run(handlers["handle_message"](update, None))

        text = update.message.reply_text.call_args.args[0]
        assert "couldn't generate" in text.lower()
        assert "Traceback" not in text
        assert "RuntimeError" not in text

    @patch("eduagent.telegram_bot._get_store")
    @patch("eduagent.openclaw_plugin.handle_message", new_callable=AsyncMock)
    def test_state_resets_after_error(self, mock_process, mock_store):
        """State resets to IDLE even when generation fails."""
        mock_store.return_value = MagicMock(
            get=MagicMock(return_value=None),
            save=MagicMock(),
        )
        mock_process.side_effect = RuntimeError("boom")

        bot = EduAgentBot(token="fake:token")
        handlers = _extract_handlers(bot)

        update = _make_update("generate lesson", chat_id=602)
        asyncio.run(handlers["handle_message"](update, None))

        state = _get_chat_state(602)
        assert state.state == ConversationState.IDLE

    def test_error_logging(self, tmp_path):
        """Errors should be written to errors.log."""
        log_file = tmp_path / "errors.log"
        with patch("eduagent.telegram_bot._ERROR_LOG", log_file):
            _log_error(ValueError("test error"))
        assert log_file.exists()
        content = log_file.read_text()
        assert "ValueError" in content
        assert "test error" in content


# ── Busy state handling ──────────────────────────────────────────────────


class TestBusyState:
    @patch("eduagent.telegram_bot._get_store")
    @patch("eduagent.openclaw_plugin.handle_message", new_callable=AsyncMock)
    def test_busy_message_when_generating(self, mock_process, mock_store):
        """Messages during generation get a 'still working' response."""
        mock_store.return_value = MagicMock(
            get=MagicMock(return_value=None),
            save=MagicMock(),
        )

        cs = ChatState()
        cs.state = ConversationState.GENERATING
        _chat_states[700] = cs

        bot = EduAgentBot(token="fake:token")
        handlers = _extract_handlers(bot)

        update = _make_update("another message", chat_id=700)
        asyncio.run(handlers["handle_message"](update, None))

        update.message.reply_text.assert_awaited_once()
        text = update.message.reply_text.call_args.args[0]
        assert "still working" in text.lower()
        mock_process.assert_not_called()

    @patch("eduagent.telegram_bot._get_store")
    @patch("eduagent.openclaw_plugin.handle_message", new_callable=AsyncMock)
    def test_state_resets_after_success(self, mock_process, mock_store):
        """State resets to IDLE after successful generation."""
        mock_store.return_value = MagicMock(
            get=MagicMock(return_value=None),
            save=MagicMock(),
        )
        mock_process.return_value = "Generated lesson"

        bot = EduAgentBot(token="fake:token")
        handlers = _extract_handlers(bot)

        update = _make_update("make a lesson", chat_id=800)

        with patch("eduagent.openclaw_plugin.get_last_lesson_id", return_value=None):
            asyncio.run(handlers["handle_message"](update, None))

        state = _get_chat_state(800)
        assert state.state == ConversationState.IDLE

    def test_skips_empty_messages(self):
        update = MagicMock()
        update.message = MagicMock()
        update.message.text = None
        assert not update.message.text

    def test_skips_no_message(self):
        update = MagicMock()
        update.message = None
        assert not update.message


# ── Response chunking ────────────────────────────────────────────────────


class TestResponseChunking:
    def test_short_response_single_message(self):
        update = _make_update("hello")

        async def _test():
            response = "Short response"
            if len(response) <= 4096:
                await update.message.reply_text(response, parse_mode="Markdown")
            else:
                for chunk in [response[i:i + 4000] for i in range(0, len(response), 4000)]:
                    await update.message.reply_text(chunk, parse_mode="Markdown")

        asyncio.run(_test())
        update.message.reply_text.assert_awaited_once()

    def test_long_response_chunked(self):
        update = _make_update("test")
        response = "x" * 8500

        async def _test():
            if len(response) <= 4096:
                await update.message.reply_text(response, parse_mode="Markdown")
            else:
                for chunk in [response[i:i + 4000] for i in range(0, len(response), 4000)]:
                    await update.message.reply_text(chunk, parse_mode="Markdown")

        asyncio.run(_test())
        assert update.message.reply_text.await_count == 3


# ── Token persistence ────────────────────────────────────────────────────


class TestTokenPersistence:
    def test_app_config_telegram_token(self):
        from eduagent.models import AppConfig
        config = AppConfig(telegram_bot_token="123:FAKE")
        assert config.telegram_bot_token == "123:FAKE"

    def test_app_config_default_no_token(self):
        from eduagent.models import AppConfig
        config = AppConfig()
        assert config.telegram_bot_token is None

    def test_token_roundtrip_json(self):
        from eduagent.models import AppConfig
        config = AppConfig(telegram_bot_token="999:TEST")
        json_str = config.model_dump_json()
        loaded = AppConfig.model_validate_json(json_str)
        assert loaded.telegram_bot_token == "999:TEST"


# ── Callback prefixes ───────────────────────────────────────────────────


class TestCallbackPrefixes:
    def test_action_prefix(self):
        assert ACTION_CALLBACK_PREFIX == "action:"

    def test_rating_prefix(self):
        assert RATING_CALLBACK_PREFIX == "rate:"
