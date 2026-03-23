"""Shared CLI helpers used by all command modules."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console

from eduagent.models import AppConfig, TeacherPersona

console = Console()


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


def load_persona_or_exit() -> TeacherPersona:
    path = persona_path()
    if not path.exists():
        console.print(
            "[red]No persona found.[/red] Run [bold]eduagent ingest <path>[/bold] first."
        )
        raise typer.Exit(1)
    from eduagent.persona import load_persona

    return load_persona(path)
