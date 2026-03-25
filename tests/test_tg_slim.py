"""Tests for the slimmed Telegram transport."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from clawed.gateway_response import Button, GatewayResponse


class TestTelegramTransport:
    def test_import(self):
        from clawed.tg import EduAgentTelegramBot, TelegramAPI, run_bot
        assert EduAgentTelegramBot is not None
        assert TelegramAPI is not None

    def test_telegram_api_init(self):
        from clawed.tg import TelegramAPI
        api = TelegramAPI("fake_token")
        assert api.token == "fake_token"
        api.close()

    def test_bot_creates_gateway(self):
        from clawed.tg import EduAgentTelegramBot
        bot = EduAgentTelegramBot("fake_token")
        assert bot.gateway is not None

    def test_render_text_only(self):
        from clawed.tg import EduAgentTelegramBot
        bot = EduAgentTelegramBot("fake_token")
        api = MagicMock()
        r = GatewayResponse(text="Hello")
        bot._send_response(api, 12345, r)
        api.send_message.assert_called_once()

    def test_render_with_files(self):
        from clawed.tg import EduAgentTelegramBot
        bot = EduAgentTelegramBot("fake_token")
        api = MagicMock()
        r = GatewayResponse(text="Here's your file", files=[Path("/tmp/test.pptx")])
        bot._send_response(api, 12345, r)
        api.send_message.assert_called_once()
        api.send_document.assert_called_once()

    def test_render_with_buttons(self):
        from clawed.tg import EduAgentTelegramBot
        bot = EduAgentTelegramBot("fake_token")
        api = MagicMock()
        r = GatewayResponse(
            text="Rate?",
            button_rows=[[Button(label="5★", callback_data="rate:x:5")]],
        )
        bot._send_response(api, 12345, r)
        call_kwargs = api.send_message.call_args
        assert call_kwargs is not None
        assert "reply_markup" in str(call_kwargs)

    def test_render_empty_response(self):
        from clawed.tg import EduAgentTelegramBot
        bot = EduAgentTelegramBot("fake_token")
        api = MagicMock()
        r = GatewayResponse.empty()
        bot._send_response(api, 12345, r)
        api.send_message.assert_not_called()
