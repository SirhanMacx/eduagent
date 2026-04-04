"""Tests for cross-transport session store (Phase 1: One Ed)."""

from __future__ import annotations

import os
import time

import pytest

from clawed.agent_core.memory import sessions


@pytest.fixture(autouse=True)
def _isolate_sessions(tmp_path, monkeypatch):
    """Redirect session DB to tmp_path."""
    monkeypatch.setenv("EDUAGENT_DATA_DIR", str(tmp_path))
    sessions.reset_db()
    yield
    sessions.reset_db()


class TestSaveTurn:
    def test_save_and_load_roundtrip(self):
        sessions.save_turn("t1", "user", "Hello Ed", transport="cli")
        sessions.save_turn("t1", "assistant", "Hi there!", transport="cli")
        turns = sessions.load_recent("t1", limit=10)
        assert len(turns) == 2
        assert turns[0]["role"] == "user"
        assert turns[0]["content"] == "Hello Ed"
        assert turns[0]["transport"] == "cli"
        assert turns[1]["role"] == "assistant"
        assert turns[1]["content"] == "Hi there!"

    def test_transport_metadata_preserved(self):
        sessions.save_turn("t1", "user", "From CLI", transport="cli")
        sessions.save_turn("t1", "user", "From Telegram", transport="telegram")
        sessions.save_turn("t1", "user", "From MCP", transport="mcp")
        turns = sessions.load_recent("t1", limit=10)
        assert turns[0]["transport"] == "cli"
        assert turns[1]["transport"] == "telegram"
        assert turns[2]["transport"] == "mcp"

    def test_content_truncated_at_4000(self):
        long_msg = "x" * 5000
        sessions.save_turn("t1", "user", long_msg)
        turns = sessions.load_recent("t1", limit=1)
        assert len(turns[0]["content"]) == 4000

    def test_limit_respected(self):
        for i in range(20):
            sessions.save_turn("t1", "user", f"Message {i}")
        turns = sessions.load_recent("t1", limit=5)
        assert len(turns) == 5
        # Should be the 5 most recent
        assert turns[-1]["content"] == "Message 19"
        assert turns[0]["content"] == "Message 15"


class TestCrossTransport:
    def test_cli_and_telegram_share_session(self):
        """The core One Ed test: both transports see each other's messages."""
        sessions.save_turn("teacher-abc", "user", "Make a lesson on WW2", transport="cli")
        sessions.save_turn("teacher-abc", "assistant", "Here's your WW2 lesson...", transport="cli")
        sessions.save_turn("teacher-abc", "user", "Send me the exit ticket", transport="telegram")

        turns = sessions.load_recent("teacher-abc", limit=10)
        assert len(turns) == 3
        assert turns[0]["transport"] == "cli"
        assert turns[2]["transport"] == "telegram"

    def test_different_teachers_isolated(self):
        sessions.save_turn("teacher-a", "user", "Teacher A message")
        sessions.save_turn("teacher-b", "user", "Teacher B message")
        a_turns = sessions.load_recent("teacher-a")
        b_turns = sessions.load_recent("teacher-b")
        assert len(a_turns) == 1
        assert len(b_turns) == 1
        assert a_turns[0]["content"] == "Teacher A message"
        assert b_turns[0]["content"] == "Teacher B message"


class TestLoadRecentForLLM:
    def test_returns_role_content_only(self):
        sessions.save_turn("t1", "user", "Hello")
        sessions.save_turn("t1", "assistant", "Hi!")
        llm_history = sessions.load_recent_for_llm("t1")
        assert llm_history == [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ]

    def test_empty_for_new_teacher(self):
        assert sessions.load_recent_for_llm("new-teacher") == []


class TestFormatForPrompt:
    def test_format_with_transport_tags(self):
        sessions.save_turn("t1", "user", "Hi from CLI", transport="cli")
        sessions.save_turn("t1", "assistant", "Hello!", transport="cli")
        sessions.save_turn("t1", "user", "Hi from Telegram", transport="telegram")
        prompt = sessions.format_for_prompt("t1")
        assert "Teacher:" in prompt
        assert "Ed:" in prompt
        assert "(via telegram)" in prompt
        # CLI messages should NOT have a tag (it's the default)
        lines = prompt.split("\n")
        assert not any("(via cli)" in line for line in lines)

    def test_empty_for_no_history(self):
        assert sessions.format_for_prompt("no-history") == ""

    def test_content_truncated_in_prompt(self):
        long_msg = "x" * 2000
        sessions.save_turn("t1", "user", long_msg)
        prompt = sessions.format_for_prompt("t1")
        # Should be truncated to 800 chars in the prompt display
        assert len(prompt.split(": ", 1)[1]) <= 800


class TestChronologicalOrder:
    def test_oldest_first(self):
        sessions.save_turn("t1", "user", "First")
        time.sleep(0.01)  # Ensure distinct timestamps
        sessions.save_turn("t1", "user", "Second")
        time.sleep(0.01)
        sessions.save_turn("t1", "user", "Third")
        turns = sessions.load_recent("t1")
        assert turns[0]["content"] == "First"
        assert turns[1]["content"] == "Second"
        assert turns[2]["content"] == "Third"
