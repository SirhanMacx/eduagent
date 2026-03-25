"""Shared test fixtures — isolate state to prevent cascade failures."""

import pytest


@pytest.fixture(autouse=True)
def _isolate_state_db(tmp_path, monkeypatch):
    """Redirect the state database to a temp dir for every test.

    Prevents SQLite connection leaks and cross-test contamination
    that caused 1647 cascade errors when running the full suite.
    """
    monkeypatch.setattr("clawed.state.DEFAULT_DATA_DIR", tmp_path, raising=False)

    # Isolate the central I/O layer so tests don't write to real ~/.eduagent/
    monkeypatch.setenv("EDUAGENT_DATA_DIR", str(tmp_path))

    # Also isolate workspace to prevent tests writing to real ~/.eduagent/
    monkeypatch.setattr(
        "clawed.workspace.WORKSPACE_DIR", tmp_path / "workspace", raising=False,
    )
    monkeypatch.setattr(
        "clawed.workspace.IDENTITY_PATH", tmp_path / "workspace" / "identity.md", raising=False,
    )
    monkeypatch.setattr(
        "clawed.workspace.SOUL_PATH", tmp_path / "workspace" / "soul.md", raising=False,
    )
    monkeypatch.setattr(
        "clawed.workspace.MEMORY_PATH", tmp_path / "workspace" / "memory.md", raising=False,
    )
    monkeypatch.setattr(
        "clawed.workspace.HEARTBEAT_PATH", tmp_path / "workspace" / "heartbeat.md", raising=False,
    )
    monkeypatch.setattr(
        "clawed.workspace.NOTES_DIR", tmp_path / "workspace" / "notes", raising=False,
    )
    monkeypatch.setattr(
        "clawed.workspace.STUDENTS_DIR", tmp_path / "workspace" / "students", raising=False,
    )
