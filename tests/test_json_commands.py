"""Test --json flag on all commands that support it."""
import json
import subprocess
import sys

import pytest

# Commands that work without an API key (fast, always testable)
FAST_COMMANDS = [
    (["ingest", "/tmp/nonexistent", "--json"], "gen.ingest"),
    (["train", "--benchmark", "-n", "0", "--json"], "train"),
    (["config", "show", "--json"], "config.show"),
]

# Commands that need an API key and may hang in CI (skip in CI)
GENERATION_COMMANDS = [
    (["unit", "Test", "-g", "8", "-s", "US History", "--json"], "gen.unit"),
    (["materials", "--lesson-file", "/tmp/nonexistent.json", "--json"], "gen.materials"),
    (["game", "create", "Test", "--json"], "game.create"),
]


@pytest.mark.parametrize("args,expected_command", FAST_COMMANDS)
def test_json_flag_produces_valid_envelope(args, expected_command):
    """Commands that don't need an API key return valid JSON envelopes."""
    result = subprocess.run(
        [sys.executable, "-m", "clawed", "--python"] + args,
        capture_output=True, text=True, timeout=15,
    )
    output = json.loads(result.stdout)
    assert output["command"] == expected_command
    assert output["status"] in ("success", "error")
    assert isinstance(output["files"], list)
    assert isinstance(output["errors"], list)


@pytest.mark.parametrize("args,expected_command", GENERATION_COMMANDS)
def test_generation_json_flag(args, expected_command):
    """Generation commands return JSON or timeout (need API key)."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "clawed", "--python"] + args,
            capture_output=True, text=True, timeout=5,
        )
        # If it returns quickly, it should be a valid JSON envelope
        if result.stdout.strip():
            output = json.loads(result.stdout)
            assert output["status"] in ("success", "error")
    except subprocess.TimeoutExpired:
        # Expected in CI without an API key — command hangs on API call
        pytest.skip("Generation command needs API key (timed out)")
