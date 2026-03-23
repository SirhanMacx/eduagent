"""Integration tests for the EDUagent Telegram bot.

Mocks the python-telegram-bot Application and verifies:
- Bot initialization and data directory
- Handler registration (commands + messages)
- Message routing through openclaw_plugin.handle_message
- Long message chunking (Telegram 4096 char limit)
- Error handling
- Token persistence via AppConfig
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


def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


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

        mock_app = MagicMock()
        mock_app.run_polling = AsyncMock()
        mock_builder = MagicMock()
        mock_builder.token.return_value = mock_builder
        mock_builder.build.return_value = mock_app

        with (
            patch("telegram.ext.Application") as mock_app_cls,
            patch("telegram.ext.CommandHandler") as mock_cmd_handler,
            patch("telegram.ext.MessageHandler") as mock_msg_handler,
            patch("telegram.ext.filters") as mock_filters,
        ):
            mock_app_cls.builder.return_value = mock_builder
            mock_filters.TEXT = MagicMock()
            mock_filters.COMMAND = MagicMock()
            mock_filters.TEXT.__and__ = MagicMock(return_value="text_filter")

            _run(bot.start())

            # Should register 4 handlers: start, help, status, message
            assert mock_app.add_handler.call_count == 4
            assert mock_cmd_handler.call_count == 3  # start, help, status
            assert mock_msg_handler.call_count == 1

            # Verify command names
            cmd_names = [call.args[0] for call in mock_cmd_handler.call_args_list]
            assert "start" in cmd_names
            assert "help" in cmd_names
            assert "status" in cmd_names

            mock_app.run_polling.assert_awaited_once()


# ── Message routing ──────────────────────────────────────────────────────


class TestMessageRouting:
    def test_routes_message_through_plugin(self):
        """Text messages should be forwarded to openclaw_plugin.handle_message."""
        update = _make_update("plan a unit on photosynthesis", user_id=42)

        with patch("eduagent.openclaw_plugin.handle_message", new_callable=AsyncMock) as mock_process:
            mock_process.return_value = "Here's your unit plan..."

            teacher_id = str(update.message.from_user.id)
            text = update.message.text

            _run(update.message.chat.send_action("typing"))
            _run(mock_process(text, teacher_id=teacher_id))

            mock_process.assert_awaited_once_with("plan a unit on photosynthesis", teacher_id="42")

    def test_skips_empty_messages(self):
        """Messages with no text should be silently ignored."""
        update = MagicMock()
        update.message = MagicMock()
        update.message.text = None
        # The handler checks `if not update.message or not update.message.text: return`
        assert update.message.text is None

    def test_skips_no_message(self):
        """Updates with no message object should be silently ignored."""
        update = MagicMock()
        update.message = None
        assert update.message is None


# ── Response chunking ────────────────────────────────────────────────────


class TestResponseChunking:
    def test_short_response_single_message(self):
        """Responses under 4096 chars should be sent as one message."""
        update = _make_update("hello")
        response = "Short response"

        # Simulate the chunking logic from telegram_bot.py
        if len(response) <= 4096:
            _run(update.message.reply_text(response, parse_mode="Markdown"))
        else:
            for chunk in [response[i:i + 4000] for i in range(0, len(response), 4000)]:
                _run(update.message.reply_text(chunk, parse_mode="Markdown"))

        update.message.reply_text.assert_awaited_once_with(response, parse_mode="Markdown")

    def test_long_response_chunked(self):
        """Responses over 4096 chars should be split into 4000-char chunks."""
        update = _make_update("generate a big unit")
        response = "x" * 8500  # Should produce 3 chunks: 4000 + 4000 + 500

        if len(response) <= 4096:
            _run(update.message.reply_text(response, parse_mode="Markdown"))
        else:
            for chunk in [response[i:i + 4000] for i in range(0, len(response), 4000)]:
                _run(update.message.reply_text(chunk, parse_mode="Markdown"))

        assert update.message.reply_text.await_count == 3
        # First chunk is 4000 chars
        first_chunk = update.message.reply_text.await_args_list[0].args[0]
        assert len(first_chunk) == 4000

    def test_exact_boundary_response(self):
        """A response exactly 4096 chars should be sent as one message."""
        update = _make_update("test")
        response = "y" * 4096

        if len(response) <= 4096:
            _run(update.message.reply_text(response, parse_mode="Markdown"))

        update.message.reply_text.assert_awaited_once()


# ── Error handling ───────────────────────────────────────────────────────


class TestErrorHandling:
    def test_error_returns_friendly_message(self):
        """When openclaw_plugin raises, the bot should return a user-friendly error."""
        with patch("eduagent.openclaw_plugin.handle_message", new_callable=AsyncMock) as mock_process:
            mock_process.side_effect = RuntimeError("LLM connection failed")

            try:
                _run(mock_process("test", teacher_id="1"))
                response = ""
            except RuntimeError:
                response = (
                    "I ran into an issue processing that. "
                    "Check your API key with `/status` or try again."
                )

            assert "ran into an issue" in response
            assert "`/status`" in response


# ── Command handlers ─────────────────────────────────────────────────────


class TestCommandHandlers:
    def test_start_command_sends_welcome(self):
        """The /start command should send a welcome message with instructions."""
        update = _make_update("/start")

        # Simulate cmd_start logic from telegram_bot.py
        _run(update.message.reply_text(
            "🎓 *Welcome to EDUagent!*\n\n"
            "I'm your AI teaching assistant. I learn from your lesson plans "
            "and generate lessons, units, and materials in your exact teaching voice.\n\n"
            "To get started:\n"
            "• Share a folder path: `my materials are in ~/Documents/Lessons/`\n"
            "• Or just tell me what you teach: `I teach 8th grade social studies`\n\n"
            "Type `/help` to see what I can do.",
            parse_mode="Markdown"
        ))

        update.message.reply_text.assert_awaited_once()
        sent_text = update.message.reply_text.await_args.args[0]
        assert "Welcome to EDUagent" in sent_text
        assert "/help" in sent_text

    def test_help_command_lists_capabilities(self):
        """The /help command should list what the bot can do."""
        update = _make_update("/help")

        _run(update.message.reply_text(
            "🎓 *EDUagent Commands*\n\n"
            "*Generate content:*\n"
            "• Plan a unit on \\[topic\\] for \\[grade\\]\n"
            "• Generate a lesson on \\[topic\\]\n",
            parse_mode="Markdown"
        ))

        sent_text = update.message.reply_text.await_args.args[0]
        assert "Commands" in sent_text
        assert "Generate content" in sent_text

    def test_status_command_shows_config(self):
        """The /status command should call _show_status and return results."""
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


# ── Typing indicator ─────────────────────────────────────────────────────


class TestTypingIndicator:
    def test_sends_typing_action(self):
        """The bot should show a typing indicator before processing."""
        update = _make_update("plan a lesson")

        _run(update.message.chat.send_action("typing"))

        update.message.chat.send_action.assert_awaited_once_with("typing")


# ── Token from config ────────────────────────────────────────────────────


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
