"""Tests for gateway handlers."""
import pytest
from unittest.mock import AsyncMock, patch
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


from eduagent.handlers.generate import GenerateHandler


class TestGenerateHandler:
    def setup_method(self):
        self.handler = GenerateHandler()

    @pytest.mark.asyncio
    async def test_generate_lesson_returns_response(self):
        with patch("eduagent.handlers.generate.handle_message", new_callable=AsyncMock) as mock_hm:
            mock_hm.return_value = "Here is your lesson on photosynthesis..."
            r = await self.handler.lesson("photosynthesis", "teacher_1")
            assert isinstance(r, GatewayResponse)
            assert "photosynthesis" in r.text.lower()
            mock_hm.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_generate_unit_returns_response(self):
        with patch("eduagent.handlers.generate.handle_message", new_callable=AsyncMock) as mock_hm:
            mock_hm.return_value = "Unit plan for WWI..."
            r = await self.handler.unit("World War I", "teacher_1")
            assert isinstance(r, GatewayResponse)
            assert r.has_content

    @pytest.mark.asyncio
    async def test_generate_with_post_gen_buttons(self):
        with patch("eduagent.handlers.generate.handle_message", new_callable=AsyncMock) as mock_hm:
            mock_hm.return_value = "Lesson content..."
            with patch("eduagent.handlers.generate.get_last_lesson_id", return_value="lesson_abc"):
                r = await self.handler.lesson("fractions", "teacher_1")
                assert len(r.button_rows) > 0 or len(r.buttons) > 0

    @pytest.mark.asyncio
    async def test_generate_error_returns_friendly_message(self):
        with patch("eduagent.handlers.generate.handle_message", new_callable=AsyncMock) as mock_hm:
            mock_hm.side_effect = RuntimeError("LLM timeout")
            r = await self.handler.lesson("topic", "teacher_1")
            assert "issue" in r.text.lower() or "error" in r.text.lower() or "try again" in r.text.lower()


from pathlib import Path
from eduagent.handlers.export import ExportHandler


class TestExportHandler:
    def setup_method(self):
        self.handler = ExportHandler()

    @pytest.mark.asyncio
    async def test_export_unknown_format(self):
        r = await self.handler.export("lesson_123", "teacher_1", "unknown_format")
        assert "not supported" in r.text.lower() or "format" in r.text.lower()

    @pytest.mark.asyncio
    async def test_export_no_lesson_found(self):
        r = await self.handler.export("nonexistent_id", "teacher_1", "slides")
        assert "couldn't find" in r.text.lower() or "no lesson" in r.text.lower()

    @pytest.mark.asyncio
    async def test_export_slides_calls_pptx(self):
        from eduagent.models import DailyLesson
        lesson = DailyLesson(
            title="Test Lesson", lesson_number=1, objective="Test",
            do_now="Test", direct_instruction="Test",
            guided_practice="Test", independent_work="Test",
        )
        with patch("eduagent.handlers.export._load_lesson", return_value=lesson):
            with patch("eduagent.handlers.export._load_persona", return_value=None):
                with patch.object(self.handler, "_do_export", new_callable=AsyncMock) as mock_export:
                    mock_export.return_value = Path("/tmp/test.pptx")
                    r = await self.handler.export("lesson_123", "teacher_1", "slides")
                    assert len(r.files) == 1
                    mock_export.assert_called_once()

    def test_supported_formats(self):
        assert "slides" in ExportHandler.SUPPORTED_FORMATS
        assert "handout" in ExportHandler.SUPPORTED_FORMATS
        assert "doc" in ExportHandler.SUPPORTED_FORMATS
