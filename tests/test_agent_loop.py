"""Tests for the agent loop with FakeLLM."""
import pytest

from clawed.agent_core.fake_llm import FakeLLM, FakeLLMExhaustedError


class TestFakeLLM:
    @pytest.mark.asyncio
    async def test_text_response(self):
        llm = FakeLLM([{"type": "text", "content": "Hello!"}])
        resp = await llm.generate(messages=[], tools=None, system="")
        assert resp["type"] == "text"
        assert resp["content"] == "Hello!"

    @pytest.mark.asyncio
    async def test_tool_call_response(self):
        llm = FakeLLM([{
            "type": "tool_calls",
            "tool_calls": [{"id": "1", "name": "generate_lesson", "arguments": {"topic": "fractions"}}],
        }])
        resp = await llm.generate(messages=[], tools=None, system="")
        assert resp["type"] == "tool_calls"
        assert resp["tool_calls"][0]["name"] == "generate_lesson"

    @pytest.mark.asyncio
    async def test_sequence(self):
        llm = FakeLLM([
            {"type": "tool_calls", "tool_calls": [{"id": "1", "name": "search_standards", "arguments": {}}]},
            {"type": "text", "content": "Found standards."},
        ])
        r1 = await llm.generate(messages=[], tools=None, system="")
        assert r1["type"] == "tool_calls"
        r2 = await llm.generate(messages=[], tools=None, system="")
        assert r2["type"] == "text"

    @pytest.mark.asyncio
    async def test_exhausted_raises(self):
        llm = FakeLLM([{"type": "text", "content": "only one"}])
        await llm.generate(messages=[], tools=None, system="")
        with pytest.raises(FakeLLMExhaustedError):
            await llm.generate(messages=[], tools=None, system="")
