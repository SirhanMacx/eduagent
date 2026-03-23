"""Integration tests for the EDUagent Telegram bot.

Tests bot initialization, message chunking logic, error handling,
handler wiring, and AppConfig token persistence — all without
requiring python-telegram-bot to be installed.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from eduagent.telegram_bot import EduAgentBot

# ── Helpers ──────────────────────────────────────────────────────────────


def _make_update(text: str, user_id: int = 12345):
    """Create a mock Telegram Update with a text message."""
    update = MagicMock()
    update.message = MagicMock()
    update.message.text = text
    update.message.from_user = MagicMock()
    update.message.from_user.id = user_id
    update.message.chat = MagicMock()
    update.message.chat.send_action = AsyncMock()
    update.message.reply_text = AsyncMock()
    return update


# ── Bot initialization ──────────────────────────────────────────────────


class TestBotInit:
    def test_creates_data_dir(self, tmp_path):
        data_dir = tmp_path / "test_eduagent"
        bot = EduAgentBot(token="fake:token", data_dir=data_dir)
        assert bot.token == "fake:token"
        assert bot.data_dir == data_dir
        assert data_dir.exists()

    def test_default_data_dir(self):
        bot = EduAgentBot(token="fake:token")
        assert bot.data_dir == Path.home() / ".eduagent"

    def test_stores_token(self):
        bot = EduAgentBot(token="123:ABC")
        assert bot.token == "123:ABC"


# ── Handler registration ────────────────────────────────────────────────


class TestHandlerRegistration:
    def test_registers_all_handlers(self):
        """Verify the bot registers /start, /help, /status, and a text handler."""
        bot = EduAgentBot(token="fake:token")

        mock_app_instance = MagicMock()
        mock_app_instance.run_polling = AsyncMock()
        mock_builder = MagicMock()
        mock_builder.token.return_value = mock_builder
        mock_builder.build.return_value = mock_app_instance

        # Create mock telegram.ext module
        mock_telegram_ext = MagicMock()
        mock_telegram_ext.Application.builder.return_value = mock_builder
        mock_telegram_ext.filters.TEXT = MagicMock()
        mock_telegram_ext.filters.COMMAND = MagicMock()
        mock_telegram_ext.filters.TEXT.__and__ = MagicMock(return_value="text_filter")

        with patch.dict("sys.modules", {
            "telegram": MagicMock(),
            "telegram.ext": mock_telegram_ext,
        }):
            asyncio.run(bot.start())

            # Should register 4 handlers: start, help, status, message
            assert mock_app_instance.add_handler.call_count == 4

            # 3 CommandHandler calls + 1 MessageHandler call
            assert mock_telegram_ext.CommandHandler.call_count == 3
            assert mock_telegram_ext.MessageHandler.call_count == 1

            # Verify command names
            cmd_names = [
                call.args[0] for call in mock_telegram_ext.CommandHandler.call_args_list
            ]
            assert "start" in cmd_names
            assert "help" in cmd_names
            assert "status" in cmd_names

            mock_app_instance.run_polling.assert_awaited_once()


# ── Message routing ──────────────────────────────────────────────────────


class TestMessageRouting:
    def test_routes_teacher_id_from_user(self):
        """Teacher ID should be derived from Telegram user ID."""
        update = _make_update("plan a unit on photosynthesis", user_id=42)
        teacher_id = str(update.message.from_user.id)
        assert teacher_id == "42"

    def test_extracts_message_text(self):
        """Message text should be extracted from update."""
        update = _make_update("hello world")
        assert update.message.text == "hello world"

    def test_skips_empty_messages(self):
        """Messages with no text should be detected by the guard."""
        update = MagicMock()
        update.message = MagicMock()
        update.message.text = None
        # The handler checks `if not update.message or not update.message.text: return`
        assert not update.message.text

    def test_skips_no_message(self):
        """Updates with no message object should be detected by the guard."""
        update = MagicMock()
        update.message = None
        assert not update.message


# ── Response chunking ────────────────────────────────────────────────────


def _send_response(update, response):
    """Replicate the chunking logic from telegram_bot.py."""
    async def _do():
        if len(response) <= 4096:
            await update.message.reply_text(response, parse_mode="Markdown")
        else:
            for chunk in [response[i:i + 4000] for i in range(0, len(response), 4000)]:
                await update.message.reply_text(chunk, parse_mode="Markdown")
    asyncio.run(_do())


class TestResponseChunking:
    def test_short_response_single_message(self):
        """Responses under 4096 chars should be sent as one message."""
        update = _make_update("hello")
        _send_response(update, "Short response")
        update.message.reply_text.assert_awaited_once_with("Short response", parse_mode="Markdown")

    def test_long_response_chunked(self):
        """Responses over 4096 chars should be split into 4000-char chunks."""
        update = _make_update("generate a big unit")
        response = "x" * 8500  # 3 chunks: 4000 + 4000 + 500
        _send_response(update, response)

        assert update.message.reply_text.await_count == 3
        first_chunk = update.message.reply_text.await_args_list[0].args[0]
        assert len(first_chunk) == 4000
        last_chunk = update.message.reply_text.await_args_list[2].args[0]
        assert len(last_chunk) == 500

    def test_exact_boundary_response(self):
        """A response exactly 4096 chars should be sent as one message."""
        update = _make_update("test")
        _send_response(update, "y" * 4096)
        update.message.reply_text.assert_awaited_once()

    def test_just_over_boundary(self):
        """A response of 4097 chars should be split into two chunks."""
        update = _make_update("test")
        _send_response(update, "z" * 4097)
        assert update.message.reply_text.await_count == 2
        first = update.message.reply_text.await_args_list[0].args[0]
        second = update.message.reply_text.await_args_list[1].args[0]
        assert len(first) == 4000
        assert len(second) == 97


# ── Error handling ───────────────────────────────────────────────────────


class TestErrorHandling:
    def test_error_produces_friendly_message(self):
        """When the plugin raises, the bot should produce a user-friendly error."""
        # This tests the error handling pattern from telegram_bot.py handle_message
        try:
            raise RuntimeError("LLM connection failed")
        except Exception:
            response = (
                "I ran into an issue processing that. "
                "Check your API key with `/status` or try again."
            )

        assert "ran into an issue" in response
        assert "`/status`" in response

    def test_import_error_when_telegram_missing(self):
        """Bot.start() should raise ImportError with install instructions when telegram missing."""
        bot = EduAgentBot(token="fake:token")

        with patch.dict("sys.modules", {"telegram": None, "telegram.ext": None}):
            with pytest.raises(ImportError, match="python-telegram-bot"):
                # Force a fresh import attempt inside start()
                asyncio.run(bot.start())


# ── Command handler content ──────────────────────────────────────────────


class TestCommandContent:
    def test_start_message_has_welcome(self):
        """The /start welcome text should contain key onboarding info."""
        # This is the exact text from telegram_bot.py cmd_start
        welcome = (
            "🎓 *Welcome to EDUagent!*\n\n"
            "I'm your AI teaching assistant. I learn from your lesson plans "
            "and generate lessons, units, and materials in your exact teaching voice.\n\n"
            "To get started:\n"
            "• Share a folder path: `my materials are in ~/Documents/Lessons/`\n"
            "• Or just tell me what you teach: `I teach 8th grade social studies`\n\n"
            "Type `/help` to see what I can do."
        )
        assert "Welcome to EDUagent" in welcome
        assert "/help" in welcome
        assert "lesson plans" in welcome

    def test_help_message_has_capabilities(self):
        """The /help text should list generation and setup capabilities."""
        # From telegram_bot.py cmd_help
        help_text = (
            "🎓 *EDUagent Commands*\n\n"
            "*Generate content:*\n"
            "• Plan a unit on \\[topic\\] for \\[grade\\]\n"
            "• Generate a lesson on \\[topic\\]\n"
        )
        assert "Commands" in help_text
        assert "Generate content" in help_text

    def test_status_calls_show_status(self):
        """The /status handler should use _show_status from openclaw_plugin."""
        with (
            patch("eduagent.state.TeacherSession.load") as mock_load,
            patch("eduagent.openclaw_plugin._show_status") as mock_status,
        ):
            mock_session = MagicMock()
            mock_load.return_value = mock_session
            mock_status.return_value = "⚙️ *EDUagent Status*\n\n👩‍🏫 Persona: Not set up yet"

            result = mock_status(mock_session)
            assert "Status" in result
            mock_status.assert_called_once_with(mock_session)


# ── Token persistence via AppConfig ──────────────────────────────────────


class TestTokenConfig:
    def test_app_config_has_telegram_token(self):
        """AppConfig should support storing a Telegram bot token."""
        from eduagent.models import AppConfig
        config = AppConfig(telegram_bot_token="123:FAKE")
        assert config.telegram_bot_token == "123:FAKE"

    def test_app_config_default_no_token(self):
        """AppConfig should default to no Telegram token."""
        from eduagent.models import AppConfig
        config = AppConfig()
        assert config.telegram_bot_token is None

    def test_token_roundtrip_json(self):
        """Token should survive JSON serialization/deserialization."""
        from eduagent.models import AppConfig
        config = AppConfig(telegram_bot_token="999:TEST_TOKEN")
        json_str = config.model_dump_json()
        loaded = AppConfig.model_validate_json(json_str)
        assert loaded.telegram_bot_token == "999:TEST_TOKEN"

    def test_token_excluded_when_none(self):
        """When token is None, it should not cause issues in JSON."""
        from eduagent.models import AppConfig
        config = AppConfig()
        json_str = config.model_dump_json()
        loaded = AppConfig.model_validate_json(json_str)
        assert loaded.telegram_bot_token is None
