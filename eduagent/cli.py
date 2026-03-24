"""Rich CLI for EDUagent — beautiful terminal interface with typer.

This module registers all CLI sub-apps from eduagent.commands.* modules.
The actual command implementations live in:
  - commands/generate.py  — ingest, unit, lesson, materials, full, etc.
  - commands/config.py    — config, persona, standards, templates, skills, school, waitlist
  - commands/export.py    — export, share, demo, landing
  - commands/bot.py       — chat, student-chat, bot, serve, mcp-server
"""

from __future__ import annotations

from typing import Optional

import typer

from eduagent import __version__
from eduagent.commands._helpers import console
from eduagent.commands.bot import bot_app
from eduagent.commands.config import (
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
from eduagent.commands.export import (
    _DEMO_HTML,
    _lesson_to_html,
    export_app,
)
from eduagent.commands.generate import generate_app
from eduagent.commands.queue import queue_app
from eduagent.commands.schedule_cmd import schedule_app
from eduagent.commands.workspace_cmd import workspace_app

# ── Build the main app ──────────────────────────────────────────────────

app = typer.Typer(
    name="eduagent",
    help="Your teaching files, your AI co-teacher.",
    rich_markup_mode="rich",
)


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"EDUagent v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
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
# top-level commands on the main app (e.g. `eduagent ingest`, not
# `eduagent generate ingest`).

for _cmd_info in generate_app.registered_commands:
    app.registered_commands.append(_cmd_info)

for _cmd_info in export_app.registered_commands:
    app.registered_commands.append(_cmd_info)

for _cmd_info in bot_app.registered_commands:
    app.registered_commands.append(_cmd_info)

# Register stats and status as top-level commands via helper functions
register_stats(app)
register_status(app)

# ── Backward compatibility ──────────────────────────────────────────────
# Tests and other modules import these directly from eduagent.cli
__all__ = ["app", "_DEMO_HTML", "_lesson_to_html"]

if __name__ == "__main__":
    app()
