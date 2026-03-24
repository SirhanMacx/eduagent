"""Tests for gateway handlers."""
import pytest
from eduagent.gateway_response import GatewayResponse
from eduagent.handlers.onboard import OnboardHandler, OnboardState


class TestOnboardHandler:
    def setup_method(self):
        self.handler = OnboardHandler()

    @pytest.mark.asyncio
    async def test_start_onboarding_asks_subject(self):
        r = await self.handler.step("teacher_1", "hi")
        assert isinstance(r, GatewayResponse)
        assert "subject" in r.text.lower() or "teach" in r.text.lower()

    @pytest.mark.asyncio
    async def test_subject_then_asks_grade(self):
        await self.handler.step("t1", "hi")  # → ask_subject
        r = await self.handler.step("t1", "math")  # → ask_grade
        assert "grade" in r.text.lower()

    @pytest.mark.asyncio
    async def test_grade_then_asks_name(self):
        await self.handler.step("t1", "hi")
        await self.handler.step("t1", "science")
        r = await self.handler.step("t1", "8th grade")
        assert "name" in r.text.lower()

    @pytest.mark.asyncio
    async def test_full_onboarding_flow(self):
        await self.handler.step("t1", "hi")
        await self.handler.step("t1", "history")
        await self.handler.step("t1", "10")
        r = await self.handler.step("t1", "Ms. Rivera")
        assert r.has_content

    @pytest.mark.asyncio
    async def test_is_onboarding(self):
        assert not self.handler.is_onboarding("t1")
        await self.handler.step("t1", "hi")
        assert self.handler.is_onboarding("t1")

    @pytest.mark.asyncio
    async def test_combined_subject_and_grade(self):
        """User says '8th grade math' in one message — should skip grade step."""
        await self.handler.step("t1", "hi")
        r = await self.handler.step("t1", "8th grade math")
        assert "name" in r.text.lower()

    @pytest.mark.asyncio
    async def test_onboarding_state_cleared_after_complete(self):
        await self.handler.step("t1", "hi")
        await self.handler.step("t1", "math")
        await self.handler.step("t1", "6")
        await self.handler.step("t1", "Mr. Smith")
        assert not self.handler.is_onboarding("t1")

    def test_onboard_state_enum(self):
        assert OnboardState.ASK_SUBJECT.value == "ask_subject"
        assert OnboardState.DONE.value == "done"
