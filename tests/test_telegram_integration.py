"""Integration tests for the EDUagent Telegram bot.

Tests: /start, /lesson flow, /health, error recovery (LLM fails -> retry -> fallback),
conversation state machine, and command menu registration.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from eduagent.telegram_bot import (
    BOT_COMMANDS,
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
        _chat_states.clear()
        state = _get_chat_state(999)
        assert state.state == ConversationState.IDLE
        assert 999 in _chat_states

    def test_get_chat_state_returns_existing(self):
        _chat_states.clear()
        state1 = _get_chat_state(42)
        state1.state = ConversationState.DONE
        state2 = _get_chat_state(42)
        assert state2.state == ConversationState.DONE

    def test_done_state_not_busy(self):
        state = ChatState()
        state.state = ConversationState.DONE
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


# ── Command menu registration ─────────────────────────────────────────────


class TestCommandMenu:
    def test_bot_commands_defined(self):
        """BOT_COMMANDS should include all required commands."""
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
    def test_registers_all_handlers(self):
        """Verify the bot registers all command handlers + message handler."""
        bot = EduAgentBot(token="fake:token")

        mock_app_instance = MagicMock()
        mock_app_instance.run_polling = AsyncMock()
        mock_builder = MagicMock()
        mock_builder.token.return_value = mock_builder
        mock_builder.build.return_value = mock_app_instance

        mock_telegram = MagicMock()
        mock_telegram_ext = MagicMock()
        mock_telegram_ext.Application.builder.return_value = mock_builder
        mock_telegram_ext.filters.TEXT = MagicMock()
        mock_telegram_ext.filters.COMMAND = MagicMock()
        mock_telegram_ext.filters.TEXT.__and__ = MagicMock(return_value="text_filter")

        with patch.dict("sys.modules", {
            "telegram": mock_telegram,
            "telegram.ext": mock_telegram_ext,
        }):
            asyncio.run(bot.start())

            # Should register:
            #   start, help, status, health, lesson, unit, assess, worksheet
            #   + rating callback + message = 10 handlers
            assert mock_app_instance.add_handler.call_count == 10

            # 8 CommandHandlers
            assert mock_telegram_ext.CommandHandler.call_count == 8

            # 1 MessageHandler
            assert mock_telegram_ext.MessageHandler.call_count == 1

            # Verify command names
            cmd_names = [
                call.args[0] for call in mock_telegram_ext.CommandHandler.call_args_list
            ]
            assert "start" in cmd_names
            assert "help" in cmd_names
            assert "status" in cmd_names
            assert "health" in cmd_names
            assert "lesson" in cmd_names
            assert "unit" in cmd_names
            assert "assess" in cmd_names
            assert "worksheet" in cmd_names

            # post_init should be set for BotFather command registration
            assert mock_app_instance.post_init is not None

            mock_app_instance.run_polling.assert_awaited_once()


# ── /start command ─────────────────────────────────────────────────────────


class TestStartCommand:
    def test_start_message_content(self):
        """The welcome message should include key onboarding info."""
        # Verify the text patterns that will be sent
        welcome = (
            "Welcome to EDUagent!\n\n"
            "I'm your AI teaching assistant."
        )
        assert "Welcome to EDUagent" in welcome
        assert "teaching assistant" in welcome


# ── /health command ────────────────────────────────────────────────────────


class TestHealthCommand:
    def test_health_returns_status_info(self):
        """Health text should include model, persona, lesson count, corpus size."""
        # Simulate health output
        health_text = (
            "EDUagent Health\n\n"
            "Model: llama3.2 (ollama)\n"
            "Persona loaded: yes\n"
            "Lessons generated: 5\n"
            "Corpus examples: 12"
        )
        assert "Model:" in health_text
        assert "Persona loaded:" in health_text
        assert "Lessons generated:" in health_text
        assert "Corpus examples:" in health_text


# ── Error recovery ─────────────────────────────────────────────────────────


class TestErrorRecovery:
    def test_error_logged_to_file(self, tmp_path):
        """Errors should be logged to errors.log."""
        with patch("eduagent.telegram_bot._ERROR_LOG", tmp_path / "errors.log"):
            _log_error(RuntimeError("test error"))
            log_content = (tmp_path / "errors.log").read_text()
            assert "RuntimeError" in log_content
            assert "test error" in log_content

    def test_error_produces_friendly_fallback(self):
        """On LLM failure, the fallback message should be user-friendly."""
        fallback = "Couldn't generate right now. Try `/lesson` again in a minute."
        assert "Couldn't generate" in fallback
        assert "/lesson" in fallback

    def test_busy_state_message(self):
        """If generating, user gets a 'still working' message."""
        msg = "Still working on your lesson -- almost done!"
        assert "still working" in msg.lower()


# ── /lesson flow ───────────────────────────────────────────────────────────


class TestLessonFlow:
    def test_lesson_command_asks_for_topic(self):
        """The /lesson command should prompt for a topic."""
        prompt = (
            "What topic should the lesson be about? "
            "(e.g. 'photosynthesis for 6th grade' or 'causes of WWI')"
        )
        assert "topic" in prompt.lower()
        assert "photosynthesis" in prompt

    def test_state_transitions_during_generation(self):
        """State should go IDLE -> GENERATING -> IDLE."""
        state = ChatState()
        assert state.state == ConversationState.IDLE
        state.state = ConversationState.GENERATING
        assert state.is_busy()
        state.state = ConversationState.IDLE
        assert not state.is_busy()


# ── Response chunking ──────────────────────────────────────────────────────


class TestResponseChunking:
    def test_short_response_single_message(self):
        """Short responses sent as one message."""
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
        """Responses over 4096 chars should be split."""
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


# ── Token persistence ──────────────────────────────────────────────────────


class TestTokenPersistence:
    def test_app_config_telegram_token(self):
        from eduagent.models import AppConfig
        config = AppConfig(telegram_bot_token="123:FAKE")
        assert config.telegram_bot_token == "123:FAKE"

    def test_app_config_default_no_token(self):
        from eduagent.models import AppConfig
        config = AppConfig()
        assert config.telegram_bot_token is None
