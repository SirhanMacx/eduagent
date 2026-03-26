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


import pytest


class TestAgentGateway:
    @pytest.mark.asyncio
    async def test_handle_returns_gateway_response(self):
        from unittest.mock import patch
        from clawed.agent_core.core import Gateway as AgentGateway
        from clawed.agent_core.fake_llm import FakeLLM
        from clawed.models import AppConfig

        llm = FakeLLM([{"type": "text", "content": "Hello teacher!"}])
        gw = AgentGateway(config=AppConfig(agent_gateway=True), llm=llm)
        with patch("clawed.agent_core.core.has_config", return_value=True):
            result = await gw.handle("hi", "t1")
        assert result.text == "Hello teacher!"

    @pytest.mark.asyncio
    async def test_file_routes_to_ingest(self):
        from pathlib import Path
        from clawed.agent_core.core import Gateway as AgentGateway
        from clawed.models import AppConfig
        from unittest.mock import AsyncMock, patch
        from clawed.gateway_response import GatewayResponse

        gw = AgentGateway(config=AppConfig(agent_gateway=True))
        with patch.object(gw._ingest, "handle", new_callable=AsyncMock) as mock_ingest:
            mock_ingest.return_value = GatewayResponse(text="Ingested!")
            result = await gw.handle("hi", "t1", files=[Path("/tmp/test.pdf")])
        mock_ingest.assert_called_once()
        assert result.text == "Ingested!"

    @pytest.mark.asyncio
    async def test_callback_routes_approval(self):
        from clawed.agent_core.core import Gateway as AgentGateway
        from clawed.models import AppConfig

        gw = AgentGateway(config=AppConfig(agent_gateway=True))
        result = await gw.handle_callback("approve:nonexistent123", "t1")
        assert result.text  # some response even if approval not found

    def test_has_event_bus(self):
        from clawed.agent_core.core import Gateway as AgentGateway
        from clawed.models import AppConfig
        gw = AgentGateway(config=AppConfig(agent_gateway=True))
        assert gw.event_bus is not None

    @pytest.mark.asyncio
    async def test_has_stats(self):
        from clawed.agent_core.core import Gateway as AgentGateway
        from clawed.models import AppConfig
        gw = AgentGateway(config=AppConfig(agent_gateway=True))
        s = await gw.stats()
        assert "messages_today" in s

    def test_has_backward_compat_methods(self):
        from clawed.agent_core.core import Gateway as AgentGateway
        from clawed.models import AppConfig
        gw = AgentGateway(config=AppConfig(agent_gateway=True))
        assert hasattr(gw, "process_message")
        assert hasattr(gw, "start")
        assert hasattr(gw, "stop")
        assert hasattr(gw, "handle_system_event")

    def test_feature_flag_on_routes_here(self):
        from clawed.gateway import Gateway
        from clawed.models import AppConfig
        gw = Gateway(config=AppConfig(agent_gateway=True))
        assert gw.__class__.__module__ == "clawed.agent_core.core"
