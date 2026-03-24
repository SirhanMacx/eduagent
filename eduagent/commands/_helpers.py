"""Shared CLI helpers used by all command modules."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import typer
from rich.console import Console

from eduagent.models import AppConfig, TeacherPersona


def _is_utf8_terminal() -> bool:
    """Check if the terminal supports UTF-8."""
    import locale

    try:
        encoding = locale.getpreferredencoding(False)
        return encoding.lower().replace("-", "") in ("utf8",)
    except Exception:
        return False


def _make_console() -> Console:
    """Create a Rich console with safe encoding for all platforms."""
    # Windows cmd.exe and PowerShell may not handle UTF-8 box chars
    force_ascii = sys.platform == "win32" and not _is_utf8_terminal()
    return Console(
        highlight=False,
        safe_box=force_ascii,
        force_terminal=None,  # Let Rich auto-detect
    )


console = _make_console()


def output_dir() -> Path:
    cfg = AppConfig.load()
    return Path(cfg.output_dir).expanduser().resolve()


def run_async(coro):
    """Run an async coroutine from synchronous CLI code."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    except RuntimeError:
        # No running event loop — create a new one
        return asyncio.run(coro)


def persona_path() -> Path:
    return output_dir() / "persona.json"


def _safe_progress(**kwargs):
    """Create a Progress bar that works on all platforms.

    On Windows with cp1252, Rich's SpinnerColumn() uses Braille characters
    that crash.  We substitute a plain TextColumn on win32.
    """
    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TaskProgressColumn,
        TextColumn,
    )

    columns: list = []
    if sys.platform == "win32":
        columns.append(TextColumn("[progress.description]{task.description}"))
    else:
        columns.append(SpinnerColumn())
        columns.append(TextColumn("[progress.description]{task.description}"))
    columns.extend([BarColumn(), TaskProgressColumn()])
    return Progress(*columns, **kwargs)


def load_persona_or_exit() -> TeacherPersona:
    path = persona_path()
    if not path.exists():
        console.print(
            "[red]No persona found.[/red] Run [bold]eduagent ingest <path>[/bold] first."
        )
        raise typer.Exit(1)
    from eduagent.persona import load_persona

    return load_persona(path)
