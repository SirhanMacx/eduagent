"""Tests for the tool protocol and registry."""
import pytest

from clawed.agent_core.context import AgentContext, ToolResult
from clawed.agent_core.tools.base import ToolRegistry


class _DummyTool:
    """A minimal tool for testing the registry."""
    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "dummy",
                "description": "A test tool",
                "parameters": {"type": "object", "properties": {}},
            },
        }

    async def execute(self, params: dict, context: AgentContext) -> ToolResult:
        return ToolResult(text="dummy result")


class TestToolRegistry:
    def test_register_and_list(self):
        reg = ToolRegistry()
        reg.register(_DummyTool())
        names = reg.tool_names()
        assert "dummy" in names

    def test_get_tool(self):
        reg = ToolRegistry()
        tool = _DummyTool()
        reg.register(tool)
        assert reg.get("dummy") is tool

    def test_get_unknown_returns_none(self):
        reg = ToolRegistry()
        assert reg.get("nonexistent") is None

    def test_schemas(self):
        reg = ToolRegistry()
        reg.register(_DummyTool())
        schemas = reg.schemas()
        assert len(schemas) == 1
        assert schemas[0]["function"]["name"] == "dummy"

    @pytest.mark.asyncio
    async def test_execute(self):
        from clawed.models import AppConfig
        reg = ToolRegistry()
        reg.register(_DummyTool())
        ctx = AgentContext(
            teacher_id="t1", config=AppConfig(),
            teacher_profile={}, persona=None,
            session_history=[], improvement_context="",
        )
        result = await reg.execute("dummy", {}, ctx)
        assert result.text == "dummy result"

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self):
        from clawed.models import AppConfig
        reg = ToolRegistry()
        ctx = AgentContext(
            teacher_id="t1", config=AppConfig(),
            teacher_profile={}, persona=None,
            session_history=[], improvement_context="",
        )
        result = await reg.execute("nonexistent", {}, ctx)
        assert "Unknown tool" in result.text


class TestGenerateLessonTool:
    def test_schema_valid(self):
        from clawed.agent_core.tools.generate_lesson import GenerateLessonTool
        tool = GenerateLessonTool()
        s = tool.schema()
        assert s["function"]["name"] == "generate_lesson"
        assert "topic" in s["function"]["parameters"]["properties"]

    @pytest.mark.asyncio
    async def test_execute_returns_tool_result(self):
        from unittest.mock import AsyncMock, patch

        from clawed.agent_core.tools.generate_lesson import GenerateLessonTool
        from clawed.models import AppConfig

        tool = GenerateLessonTool()
        ctx = AgentContext(
            teacher_id="t1", config=AppConfig(),
            teacher_profile={}, persona=None,
            session_history=[], improvement_context="",
        )
        mock_lesson = type(
            "Lesson", (),
            {"model_dump": lambda self: {"title": "Fractions", "sections": []}},
        )()
        with patch("clawed.lesson.generate_lesson", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_lesson
            result = await tool.execute({"topic": "fractions"}, ctx)
        assert isinstance(result, ToolResult)
        assert "Fractions" in result.text or "fractions" in result.text.lower()
