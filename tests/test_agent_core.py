"""Tests for agent_core data types."""
from pathlib import Path

from clawed.agent_core.context import AgentContext, ToolResult


class TestToolResult:
    def test_defaults(self):
        r = ToolResult()
        assert r.text == ""
        assert r.files == []
        assert r.data == {}
        assert r.side_effects == []

    def test_with_values(self):
        r = ToolResult(text="done", files=[Path("/tmp/a.pdf")], side_effects=["created file"])
        assert r.text == "done"
        assert len(r.files) == 1
        assert r.side_effects == ["created file"]


class TestAgentContext:
    def test_construction(self):
        from clawed.models import AppConfig
        ctx = AgentContext(
            teacher_id="t1",
            config=AppConfig(),
            teacher_profile={"name": "Ms. Smith"},
            persona=None,
            session_history=[],
            improvement_context="",
        )
        assert ctx.teacher_id == "t1"
        assert ctx.teacher_profile["name"] == "Ms. Smith"


class TestPromptAssembly:
    def test_builds_prompt_with_teacher_name(self):
        from clawed.agent_core.prompt import build_system_prompt
        prompt = build_system_prompt(
            teacher_name="Ms. Smith",
            identity_summary="8th grade Science, inquiry-based",
            improvement_context="Students struggle with graphs",
            tool_names=["generate_lesson", "search_standards"],
        )
        assert "Ms. Smith" in prompt
        assert "inquiry-based" in prompt
        assert "graphs" in prompt

    def test_builds_prompt_without_improvement_context(self):
        from clawed.agent_core.prompt import build_system_prompt
        prompt = build_system_prompt(
            teacher_name="Teacher",
            identity_summary="",
            improvement_context="",
            tool_names=[],
        )
        assert "Claw-ED" in prompt
        assert "Teacher" in prompt
