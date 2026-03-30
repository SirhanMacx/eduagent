"""Tests for shared async utility."""

import pytest

from clawed.async_utils import run_async_safe


async def _async_add(a, b):
    return a + b


class TestRunAsyncSafe:
    def test_from_sync_context(self):
        """run_async_safe works from plain sync code."""
        result = run_async_safe(_async_add(2, 3))
        assert result == 5

    @pytest.mark.asyncio
    async def test_from_async_context(self):
        """run_async_safe works from inside a running event loop."""
        result = run_async_safe(_async_add(10, 20))
        assert result == 30
