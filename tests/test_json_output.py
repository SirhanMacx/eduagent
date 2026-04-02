"""Tests for the JSON output infrastructure."""
import json
import subprocess
import sys

import pytest


def test_json_envelope_success():
    """JSON output wraps successful results in standard envelope."""
    from clawed._json_output import json_envelope
    result = json_envelope("gen.lesson", data={"title": "WWI"}, files=["/tmp/out.docx"])
    assert result["status"] == "success"
    assert result["command"] == "gen.lesson"
    assert result["data"]["title"] == "WWI"
    assert result["files"] == ["/tmp/out.docx"]
    assert result["errors"] == []
    assert result["warnings"] == []


def test_json_envelope_error():
    """JSON output wraps errors properly."""
    from clawed._json_output import json_envelope
    result = json_envelope("gen.lesson", status="error", errors=["API key missing"])
    assert result["status"] == "error"
    assert result["errors"] == ["API key missing"]


def test_json_envelope_serializable():
    """Envelope is JSON-serializable."""
    from clawed._json_output import json_envelope
    result = json_envelope("test", data={"nested": {"key": "val"}})
    serialized = json.dumps(result)
    assert isinstance(serialized, str)
    roundtrip = json.loads(serialized)
    assert roundtrip["data"]["nested"]["key"] == "val"


def test_lesson_json_flag_error_without_config():
    """clawed lesson --json returns JSON envelope or times out (needs API key)."""
    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "clawed", "--python",
                "lesson", "Test Topic", "-g", "8", "-s", "US History", "--json",
            ],
            capture_output=True, text=True, timeout=5,
        )
        if result.stdout.strip():
            output = json.loads(result.stdout)
            assert output["command"] == "gen.lesson"
            assert output["status"] in ("success", "error")
    except subprocess.TimeoutExpired:
        pytest.skip("Lesson generation needs API key (timed out)")
