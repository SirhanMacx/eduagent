"""CLI commands for the teacher workspace."""

from __future__ import annotations

import typer
from rich.panel import Panel
from rich.table import Table

from eduagent.commands._helpers import console

workspace_app = typer.Typer(help="Teacher workspace — identity, memory, notes, and student profiles.")


@workspace_app.command("init")
def workspace_init() -> None:
    """Initialize the workspace from the current persona and config."""
    from eduagent.workspace import init_workspace

    ws_path = init_workspace()
    console.print(
        Panel(
            f"[bold green]Workspace initialized![/bold green]\n\n"
            f"  Location: [cyan]{ws_path}[/cyan]\n\n"
            f"Files created:\n"
            f"  - identity.md  (who you are)\n"
            f"  - soul.md      (teaching philosophy)\n"
            f"  - memory.md    (long-term memories)\n"
            f"  - heartbeat.md (scheduled task checks)\n"
            f"  - notes/       (daily teaching notes)\n"
            f"  - students/    (per-student profiles)",
            title="[bold]Teacher Workspace[/bold]",
            border_style="green",
        )
    )


@workspace_app.command("show")
def workspace_show() -> None:
    """Display identity, soul, and today's notes."""
    from eduagent.workspace import (
        IDENTITY_PATH,
        SOUL_PATH,
        _ensure_workspace,
        get_daily_notes,
    )

    _ensure_workspace()

    if IDENTITY_PATH.exists():
        console.print(
            Panel(
                IDENTITY_PATH.read_text(),
                title="[bold]Identity[/bold]",
                border_style="blue",
            )
        )
    else:
        console.print("[dim]No identity.md found. Run 'eduagent workspace init'.[/dim]")

    if SOUL_PATH.exists():
        console.print(
            Panel(
                SOUL_PATH.read_text(),
                title="[bold]Teaching Soul[/bold]",
                border_style="cyan",
            )
        )

    notes = get_daily_notes()
    if notes:
        console.print(
            Panel(
                notes,
                title="[bold]Today's Notes[/bold]",
                border_style="green",
            )
        )
    else:
        console.print("[dim]No notes for today yet.[/dim]")


@workspace_app.command("note")
def workspace_note(
    text: str = typer.Argument(..., help="Note text to append"),
    category: str = typer.Option("general", "--category", "-c", help="Note category"),
) -> None:
    """Add a note to today's daily notes file."""
    from eduagent.workspace import _ensure_workspace, append_daily_note

    _ensure_workspace()
    append_daily_note(text, category=category)
    console.print(f"[green]Note added to today's file.[/green] [{category}]")


@workspace_app.command("memory")
def workspace_memory() -> None:
    """Show the long-term memory file."""
    from eduagent.workspace import MEMORY_PATH, _ensure_workspace

    _ensure_workspace()

    if MEMORY_PATH.exists():
        console.print(
            Panel(
                MEMORY_PATH.read_text(),
                title="[bold]Teaching Memory[/bold]",
                border_style="yellow",
            )
        )
    else:
        console.print("[dim]No memory.md found. Run 'eduagent workspace init'.[/dim]")


@workspace_app.command("students")
def workspace_students() -> None:
    """List all student profiles in the workspace."""
    from eduagent.workspace import STUDENTS_DIR, _ensure_workspace, list_student_profiles

    _ensure_workspace()

    profiles = list_student_profiles()
    if not profiles:
        console.print(
            "[dim]No student profiles yet. They are created automatically"
            " from student bot interactions.[/dim]"
        )
        return

    table = Table(title="Student Profiles")
    table.add_column("#", style="dim", justify="right")
    table.add_column("Student Name", style="bold")
    table.add_column("File", style="cyan")

    for i, name in enumerate(profiles, 1):
        filename = name.lower().replace(" ", "_") + ".md"
        table.add_row(str(i), name, str(STUDENTS_DIR / filename))

    console.print(table)


@workspace_app.command("context")
def workspace_context() -> None:
    """Show what gets injected into LLM context."""
    from eduagent.workspace import _ensure_workspace, load_context

    _ensure_workspace()

    ctx = load_context()
    if ctx:
        console.print(
            Panel(
                ctx,
                title="[bold]LLM Context Injection[/bold]",
                border_style="magenta",
            )
        )
    else:
        console.print("[dim]No workspace context available. Run 'eduagent workspace init'.[/dim]")
