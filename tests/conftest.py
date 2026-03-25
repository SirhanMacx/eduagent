"""Shared test fixtures — isolate state to prevent cascade failures."""

import pytest


@pytest.fixture(autouse=True)
def _isolate_state_db(tmp_path, monkeypatch):
    """Redirect ALL filesystem paths to a temp dir for every test.

    Prevents SQLite connection leaks and cross-test contamination
    that caused 1647 cascade errors when running the full suite.

    Covers every module-level path constant that could write to the
    real ~/.eduagent/ directory.  The EDUAGENT_DATA_DIR env var catches
    runtime callers (functions that read os.environ at call time), while
    monkeypatch.setattr catches module-level constants that were already
    evaluated at import time.
    """
    # ── Environment variable (catches runtime os.environ.get calls) ────
    monkeypatch.setenv("EDUAGENT_DATA_DIR", str(tmp_path))

    # ── clawed.state ───────────────────────────────────────────────────
    monkeypatch.setattr("clawed.state.DEFAULT_DATA_DIR", tmp_path, raising=False)

    # ── clawed.workspace ───────────────────────────────────────────────
    monkeypatch.setattr(
        "clawed.workspace._BASE_DIR", tmp_path, raising=False,
    )
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

    # ── clawed.config (secrets storage) ────────────────────────────────
    monkeypatch.setattr("clawed.config._BASE_DIR", tmp_path, raising=False)
    monkeypatch.setattr("clawed.config._SECRETS_DIR", tmp_path, raising=False)
    monkeypatch.setattr(
        "clawed.config._SECRETS_FILE", tmp_path / "secrets.json", raising=False,
    )

    # ── clawed.scheduler ───────────────────────────────────────────────
    monkeypatch.setattr(
        "clawed.scheduler.SCHEDULE_CONFIG_PATH",
        tmp_path / "schedule.json",
        raising=False,
    )

    # ── clawed.auth (API key storage for hosted mode) ──────────────────
    monkeypatch.setattr("clawed.auth._BASE_DIR", tmp_path, raising=False)
    monkeypatch.setattr(
        "clawed.auth._KEYS_PATH", tmp_path / "api_keys.json", raising=False,
    )

    # ── clawed.bot_state ───────────────────────────────────────────────
    monkeypatch.setattr("clawed.bot_state._BASE_DIR", tmp_path, raising=False)

    # ── clawed.corpus ──────────────────────────────────────────────────
    monkeypatch.setattr("clawed.corpus._BASE_DIR", tmp_path, raising=False)
    monkeypatch.setattr("clawed.corpus.CORPUS_DIR", tmp_path / "corpus", raising=False)
    monkeypatch.setattr(
        "clawed.corpus.CORPUS_DB", tmp_path / "corpus" / "corpus.db", raising=False,
    )

    # ── clawed.slide_images (image cache) ──────────────────────────────
    monkeypatch.setattr(
        "clawed.slide_images._CACHE_DIR",
        tmp_path / "cache" / "images",
        raising=False,
    )

    # ── clawed.skills.library (custom skill YAML files) ────────────────
    monkeypatch.setattr(
        "clawed.skills.library.CUSTOM_SKILLS_DIR",
        tmp_path / "skills",
        raising=False,
    )

    # ── clawed.telegram_bot (error log / lock file) ────────────────────
    monkeypatch.setattr(
        "clawed.telegram_bot._ERROR_LOG", tmp_path / "errors.log", raising=False,
    )
    monkeypatch.setattr(
        "clawed.telegram_bot._BOT_LOCK", tmp_path / "bot.lock", raising=False,
    )

    # ── clawed.student_telegram_bot ────────────────────────────────────
    monkeypatch.setattr(
        "clawed.student_telegram_bot._ERROR_LOG",
        tmp_path / "student_errors.log",
        raising=False,
    )

    # ── clawed.transports.telegram ─────────────────────────────────────
    monkeypatch.setattr(
        "clawed.transports.telegram._BOT_LOCK",
        tmp_path / "bot.lock",
        raising=False,
    )
    monkeypatch.setattr(
        "clawed.transports.telegram._ERROR_LOG",
        tmp_path / "errors.log",
        raising=False,
    )
