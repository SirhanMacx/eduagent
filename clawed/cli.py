"""Rich CLI for Claw-ED — beautiful terminal interface with typer.

This module registers all CLI sub-apps from clawed.commands.* modules.
The actual command implementations live in:
  - commands/generate.py  — ingest, unit, lesson, materials, full, etc.
  - commands/config.py    — config, persona, standards, templates, skills, school, waitlist
  - commands/export.py    — export, share, demo, landing
  - commands/bot.py       — chat, student-chat, bot, serve, mcp-server
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.panel import Panel

from clawed import __version__
from clawed.commands._helpers import console

# UTF-8 encoding is enforced in clawed/__init__.py for all entry points
from clawed.commands.bot import bot_app
from clawed.commands.config import (
    class_app,
    config_app,
    persona_app,
    register_stats,
    register_status,
    school_app,
    skills_app,
    standards_app,
    templates_app,
    waitlist_app,
)
from clawed.commands.export import (
    _DEMO_HTML,
    _lesson_to_html,
    export_app,
)
from clawed.commands.generate import generate_app
from clawed.commands.queue import queue_app
from clawed.commands.schedule_cmd import schedule_app
from clawed.commands.sub import sub_app
from clawed.commands.workspace_cmd import workspace_app

# ── Build the main app ──────────────────────────────────────────────────

app = typer.Typer(
    name="clawed",
    help="Your teaching files, your AI co-teacher.",
    rich_markup_mode="rich",
)


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"Claw-ED v{__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-V",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """Your teaching files, your AI co-teacher."""
    if ctx.invoked_subcommand is None:
        config_path = Path.home() / ".eduagent" / "config.json"
        if not config_path.exists():
            # First run — open browser-based setup wizard
            import threading
            import webbrowser

            import uvicorn

            port = 8000
            console.print(Panel(
                "[bold]Welcome to Claw-ED![/bold]\n\n"
                "Opening the setup wizard in your browser...\n"
                f"If it doesn't open, go to: [cyan]http://localhost:{port}/setup[/cyan]\n\n"
                "[dim]Press Ctrl+C when you're done.[/dim]",
                title="\U0001f393 Claw-ED",
                border_style="green",
            ))

            def _open_browser():
                import time
                time.sleep(1.5)
                webbrowser.open(f"http://localhost:{port}/setup")

            threading.Thread(target=_open_browser, daemon=True).start()

            try:
                uvicorn.run("clawed.api.server:app", host="127.0.0.1", port=port, log_level="warning")
            except KeyboardInterrupt:
                pass

            if config_path.exists():
                console.print("\n[green]Setup complete![/green] Run [bold]clawed[/bold] again to start chatting.")
            raise typer.Exit()
        else:
            # Returning user — drop straight into chat
            import asyncio

            from clawed.transports.cli import run_chat
            try:
                asyncio.run(run_chat())
            except (KeyboardInterrupt, EOFError):
                pass
        raise typer.Exit()


# ── Top-level setup command ────────────────────────────────────────────


@app.command()
def setup(
    reset: bool = typer.Option(False, "--reset", help="Reset existing config and start fresh"),
) -> None:
    """Set up Claw-ED -- guided wizard for new teachers.

    \b
    Walks you through:
      1. What you teach (subject, grade, state)
      2. Choosing an AI model (we recommend one)
      3. Optionally importing your existing lesson plans

    Run this again anytime to change your settings.
    """
    from clawed.onboarding import run_setup_wizard

    run_setup_wizard(reset=reset)


# ── Register named sub-app groups ───────────────────────────────────────

app.add_typer(config_app, name="config")
app.add_typer(persona_app, name="persona")
app.add_typer(standards_app, name="standards")
app.add_typer(templates_app, name="templates")
app.add_typer(skills_app, name="skills")
app.add_typer(school_app, name="school")
app.add_typer(waitlist_app, name="waitlist")
app.add_typer(class_app, name="class")
app.add_typer(queue_app, name="queue")
app.add_typer(workspace_app, name="workspace")
app.add_typer(schedule_app, name="schedule")

# ── Register top-level commands from sub-modules ────────────────────────
# Commands from generate_app, export_app, and bot_app are registered as
# top-level commands on the main app (e.g. `clawed ingest`, not
# `clawed generate ingest`).

for _cmd_info in generate_app.registered_commands:
    app.registered_commands.append(_cmd_info)

for _cmd_info in export_app.registered_commands:
    app.registered_commands.append(_cmd_info)

for _cmd_info in bot_app.registered_commands:
    app.registered_commands.append(_cmd_info)

for _cmd_info in sub_app.registered_commands:
    app.registered_commands.append(_cmd_info)

# Register stats and status as top-level commands via helper functions
register_stats(app)
register_status(app)

# ── Backward compatibility ──────────────────────────────────────────────
# Tests and other modules import these directly from clawed.cli
__all__ = ["app", "_DEMO_HTML", "_lesson_to_html"]

if __name__ == "__main__":
    app()
