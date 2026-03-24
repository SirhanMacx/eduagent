"""Terminal chat interface — test EDUagent from the command line."""

from __future__ import annotations

import asyncio

from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.spinner import Spinner

from clawed.commands._helpers import console
from clawed.gateway import Gateway
from clawed.state import TeacherSession

_WELCOME = """\
👋 Welcome to **EDUagent** — your AI teaching partner.

**Get started:**
• Tell me what you teach: *"I teach 8th grade science"*
• Share your materials: *"use my files at ~/Documents/Lessons/"*
• Plan something: *"plan a unit on photosynthesis for 8th grade, 2 weeks"*

**Commands:**
• `/quit` — exit the chat
• `/status` — show your current session
• `/clear` — reset your session

Type anything to begin!
"""


async def run_chat(teacher_id: str = "local-teacher") -> None:
    """Run an interactive terminal chat session with EDUagent."""
    console.print(
        Panel(
            Markdown(_WELCOME),
            title="[bold green]EDUagent Chat[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
    )

    gateway = Gateway()

    session = TeacherSession.load(teacher_id)
    if not session.is_new:
        name = session.persona.name if session.persona else teacher_id
        console.print(f"[dim]Resuming session for {name}[/dim]\n")

    while True:
        try:
            message = Prompt.ask("[bold blue]You[/bold blue]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/dim]")
            break

        text = message.strip()
        if not text:
            continue

        # Built-in commands
        if text.lower() in ("/quit", "/exit", "quit", "exit"):
            console.print("[dim]Goodbye![/dim]")
            break

        if text.lower() == "/clear":
            session = TeacherSession(teacher_id=teacher_id)
            session.save()
            console.print("[yellow]Session cleared.[/yellow]\n")
            continue

        if text.lower() == "/status":
            text = "show status"

        # Show spinner while generating
        with Live(
            Spinner("dots", text="[dim]Thinking...[/dim]", style="green"),
            console=console,
            transient=True,
        ):
            try:
                result = await gateway.handle(text, teacher_id)
            except Exception as e:
                result = None
                response_text = f"Error: {e}"
            else:
                response_text = result.text

        console.print()
        console.print(
            Panel(
                response_text,
                title="[bold green]EDUagent[/bold green]",
                border_style="green",
                padding=(0, 1),
            )
        )
        console.print()

        # Send any files the gateway produced
        if result and result.files:
            for f in result.files:
                console.print(f"[green]File: {f}[/green]")
            console.print()

        # Show buttons as text options in CLI
        if result and (result.button_rows or result.buttons):
            rows = result.button_rows or [result.buttons]
            options = [b.label for row in rows for b in row]
            console.print(f"[dim]Options: {' | '.join(options)}[/dim]\n")


def main(teacher_id: str = "local-teacher") -> None:
    """Synchronous entry point for the chat REPL."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(run_chat(teacher_id))
    except RuntimeError:
        asyncio.run(run_chat(teacher_id))
