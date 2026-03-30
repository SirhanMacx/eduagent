"""Tests for demo mode detection with env var override."""

import os
from unittest.mock import patch


class TestDemoModeEnvOverride:
    def test_demo_mode_forced_by_env(self):
        """CLAWED_DEMO=1 forces demo mode even with stored key."""
        with patch.dict(os.environ, {"CLAWED_DEMO": "1"}):
            from clawed.demo import is_demo_mode

            assert is_demo_mode() is True

    def test_demo_mode_forced_by_true(self):
        """CLAWED_DEMO=true also works."""
        with patch.dict(os.environ, {"CLAWED_DEMO": "true"}):
            from clawed.demo import is_demo_mode

            assert is_demo_mode() is True

    def test_demo_mode_not_forced_when_unset(self):
        """Without CLAWED_DEMO, stored key disables demo mode."""
        env = os.environ.copy()
        env.pop("CLAWED_DEMO", None)
        with patch.dict(os.environ, env, clear=True):
            with patch(
                "clawed.config.resolve_credentials",
                return_value=("anthropic", "sk-test"),
            ):
                from clawed.demo import is_demo_mode

                assert is_demo_mode() is False
