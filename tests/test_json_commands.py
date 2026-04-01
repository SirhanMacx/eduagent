"""Test --json flag on all commands that support it."""
import json
import subprocess
import sys

import pytest

COMMANDS_WITH_JSON = [
    (["ingest", "/tmp/nonexistent", "--json"], "gen.ingest"),
    (["unit", "Test", "-g", "8", "-s", "US History", "--json"], "gen.unit"),
    (["materials", "--lesson-file", "/tmp/nonexistent.json", "--json"], "gen.materials"),
    (["game", "create", "Test", "--json"], "game.create"),
    (["train", "--benchmark", "-n", "0", "--json"], "train"),
    (["config", "show", "--json"], "config.show"),
]


@pytest.mark.parametrize("args,expected_command", COMMANDS_WITH_JSON)
def test_json_flag_produces_valid_envelope(args, expected_command):
    """Every command with --json returns a valid JSON envelope."""
    result = subprocess.run(
        [sys.executable, "-m", "clawed"] + args,
        capture_output=True, text=True, timeout=30,
    )
    # Must produce valid JSON on stdout
    output = json.loads(result.stdout)
    assert output["command"] == expected_command
    assert output["status"] in ("success", "error")
    assert isinstance(output["files"], list)
    assert isinstance(output["errors"], list)
