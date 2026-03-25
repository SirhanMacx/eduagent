"""Tests for clawed.onboarding — first-run guided wizard."""

from __future__ import annotations

from unittest.mock import patch

from clawed.models import AppConfig, LLMProvider


class TestOnboardingImport:
    def test_module_imports(self):
        from clawed.onboarding import (
            US_STATES,
            check_first_run,
            run_onboarding,
        )

        assert callable(run_onboarding)
        assert callable(check_first_run)
        assert isinstance(US_STATES, list)

    def test_us_states_complete(self):
        from clawed.onboarding import US_STATES

        # 50 states + DC = 51
        assert len(US_STATES) == 51

    def test_us_states_sorted(self):
        from clawed.onboarding import US_STATES

        assert US_STATES == sorted(US_STATES)


class TestResolveState:
    def test_full_name(self):
        from clawed.onboarding import _resolve_state

        assert _resolve_state("New York") == "NY"
        assert _resolve_state("California") == "CA"
        assert _resolve_state("Texas") == "TX"

    def test_abbreviation(self):
        from clawed.onboarding import _resolve_state

        assert _resolve_state("NY") == "NY"
        assert _resolve_state("CA") == "CA"
        assert _resolve_state("tx") == "TX"

    def test_case_insensitive(self):
        from clawed.onboarding import _resolve_state

        assert _resolve_state("new york") == "NY"
        assert _resolve_state("NEW YORK") == "NY"
        assert _resolve_state("california") == "CA"

    def test_prefix_match(self):
        from clawed.onboarding import _resolve_state

        assert _resolve_state("New Y") == "NY"
        assert _resolve_state("Cal") == "CA"

    def test_invalid_state(self):
        from clawed.onboarding import _resolve_state

        assert _resolve_state("Narnia") is None
        assert _resolve_state("") is None
        assert _resolve_state("XX") is None

    def test_dc(self):
        from clawed.onboarding import _resolve_state

        assert _resolve_state("DC") == "DC"
        assert _resolve_state("District of Columbia") == "DC"


class TestCheckFirstRun:
    def test_returns_false_when_config_exists(self, tmp_path):
        """If config already exists, check_first_run returns False."""
        config_file = tmp_path / "config.json"
        config_file.write_text("{}")

        with patch.object(AppConfig, "config_path", return_value=config_file):
            from clawed.onboarding import check_first_run

            result = check_first_run()
            assert result is False

    def test_returns_true_when_no_config(self, tmp_path):
        """If no config, check_first_run launches onboarding and returns True."""
        config_file = tmp_path / "nonexistent" / "config.json"

        with (
            patch.object(AppConfig, "config_path", return_value=config_file),
            patch("clawed.onboarding.run_onboarding") as mock_onboard,
            patch("sys.stdin") as mock_stdin,
        ):
            mock_stdin.isatty.return_value = True
            mock_onboard.return_value = AppConfig()

            from clawed.onboarding import check_first_run

            result = check_first_run()
            assert result is True
            mock_onboard.assert_called_once()

    def test_handles_keyboard_interrupt(self, tmp_path):
        """If user Ctrl-C during onboarding, it should not crash."""
        config_file = tmp_path / "nonexistent" / "config.json"

        with (
            patch.object(AppConfig, "config_path", return_value=config_file),
            patch("clawed.onboarding.run_onboarding", side_effect=KeyboardInterrupt),
            patch("sys.stdin") as mock_stdin,
        ):
            mock_stdin.isatty.return_value = True
            from clawed.onboarding import check_first_run

            result = check_first_run()
            assert result is True

    def test_skips_onboarding_when_non_interactive(self, tmp_path):
        """When stdin is not a TTY, skip interactive onboarding."""
        config_file = tmp_path / "nonexistent" / "config.json"

        with (
            patch.object(AppConfig, "config_path", return_value=config_file),
            patch("clawed.onboarding.run_onboarding") as mock_onboard,
            patch("sys.stdin") as mock_stdin,
        ):
            mock_stdin.isatty.return_value = False
            from clawed.onboarding import check_first_run

            result = check_first_run()
            assert result is True
            mock_onboard.assert_not_called()


class TestAskProvider:
    def test_anthropic_selection(self):
        from clawed.onboarding import _ask_provider

        with patch("clawed.onboarding.Prompt.ask", side_effect=["1", "sk-ant-test-key"]):
            provider, key = _ask_provider()
            assert provider == LLMProvider.ANTHROPIC
            assert key == "sk-ant-test-key"

    def test_openai_selection(self):
        from clawed.onboarding import _ask_provider

        with patch("clawed.onboarding.Prompt.ask", side_effect=["2", "sk-test-key"]):
            provider, key = _ask_provider()
            assert provider == LLMProvider.OPENAI
            assert key == "sk-test-key"

    def test_ollama_selection_no_key(self):
        from clawed.onboarding import _ask_provider

        with patch("clawed.onboarding.Prompt.ask", return_value="3"):
            provider, key = _ask_provider()
            assert provider == LLMProvider.OLLAMA
            assert key is None


class TestAskMaterials:
    def test_skip_on_enter(self):
        from clawed.onboarding import _ask_materials

        with patch("clawed.onboarding.Prompt.ask", return_value=""):
            result = _ask_materials()
            assert result is None

    def test_returns_resolved_path(self, tmp_path):
        from clawed.onboarding import _ask_materials

        lesson_dir = tmp_path / "lessons"
        lesson_dir.mkdir()

        with patch("clawed.onboarding.Prompt.ask", return_value=str(lesson_dir)):
            result = _ask_materials()
            assert result == str(lesson_dir)

    def test_invalid_path_returns_none(self):
        from clawed.onboarding import _ask_materials

        with patch("clawed.onboarding.Prompt.ask", return_value="/nonexistent/path/xyz"):
            result = _ask_materials()
            assert result is None


class TestStateNameToAbbr:
    def test_all_50_states_plus_dc_mapped(self):
        from clawed.onboarding import _STATE_NAME_TO_ABBR

        # Every state in the config should have both name and abbreviation entries
        from clawed.state_standards import STATE_STANDARDS_CONFIG

        for abbr, info in STATE_STANDARDS_CONFIG.items():
            assert info["name"].lower() in _STATE_NAME_TO_ABBR
            assert abbr.lower() in _STATE_NAME_TO_ABBR


class TestRunOnboarding:
    def test_full_flow_saves_config(self, tmp_path):
        """Simulate a complete onboarding flow and verify config is saved."""
        config_file = tmp_path / "config.json"

        side_effects = [
            "Global History",        # subjects
            "10",                    # grade levels
            "New York",              # state
            "y",                     # persona preview confirmation
            "3",                     # provider (Ollama) — only asked if not auto-detected
            "",                      # materials (skip)
        ]

        with (
            patch.object(AppConfig, "config_path", return_value=config_file),
            patch("clawed.onboarding.Prompt.ask", side_effect=side_effects),
            patch("clawed.onboarding._test_connection", return_value=True),
            patch("clawed.onboarding._detect_available_models", return_value=(None, "No LLM found")),
        ):
            from clawed.onboarding import run_onboarding

            config = run_onboarding()

            assert config.provider == LLMProvider.OLLAMA
            assert config.teacher_profile.state == "NY"
            assert "Global History" in config.teacher_profile.subjects
            assert "10" in config.teacher_profile.grade_levels
            assert config_file.exists()
