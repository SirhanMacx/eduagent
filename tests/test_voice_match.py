"""Tests for voice match scoring."""

from unittest.mock import AsyncMock

import pytest

from clawed.quality import score_voice_match


class TestVoiceMatch:
    @pytest.mark.asyncio
    async def test_returns_float(self):
        """score_voice_match returns a float in range 1.0-5.0."""
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(
            return_value='{"score": 4.2, "reason": "good match"}',
        )
        score = await score_voice_match("lesson text", "persona text", mock_llm)
        assert isinstance(score, float)
        assert 1.0 <= score <= 5.0

    @pytest.mark.asyncio
    async def test_returns_neutral_on_no_llm(self):
        """Without an LLM client, returns neutral 3.0."""
        score = await score_voice_match("lesson", "persona", None)
        assert score == 3.0

    @pytest.mark.asyncio
    async def test_returns_neutral_on_empty_inputs(self):
        """Empty inputs return neutral 3.0."""
        score = await score_voice_match("", "", None)
        assert score == 3.0

    @pytest.mark.asyncio
    async def test_returns_neutral_on_error(self):
        """LLM errors return neutral 3.0 (fail-neutral, not fail-closed)."""
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(side_effect=Exception("fail"))
        score = await score_voice_match("lesson", "persona", mock_llm)
        assert score == 3.0

    @pytest.mark.asyncio
    async def test_clamps_score(self):
        """Scores above 5.0 are clamped to 5.0."""
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(
            return_value='{"score": 99.0, "reason": "oops"}',
        )
        score = await score_voice_match("lesson", "persona", mock_llm)
        assert score == 5.0
