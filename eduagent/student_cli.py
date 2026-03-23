"""Student-facing CLI — simple terminal chat for testing the student bot.

Usage:
    python -m eduagent.student_cli --class-code MR-MAC-P3
    eduagent student-chat --class-code MR-MAC-P3
"""

from __future__ import annotations

import asyncio
import sys
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.spinner import Spinner
from rich.live import Live

console = Console()


def _run_async(coro):
    """Run an async coroutine from synchronous code."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def main(
    class_code: str,
    student_id: str = "student-001",
    student_name: Optional[str] = None,
) -> None:
    """Run the student chat terminal.

    Args:
        class_code: The class code from the teacher.
        student_id: A unique student identifier.
        student_name: Optional display name for registration.
    """
    from eduagent.student_bot import StudentBot

    bot = StudentBot()

    # Validate class code
    class_info = bot.get_class(class_code)
    if not class_info:
        console.print(
            f"[red]Class code '{class_code}' not found.[/red] "
            "Check with your teacher and try again."
        )
        sys.exit(1)

    # Auto-register if first time
    if not bot.is_registered(student_id, class_code):
        name = student_name or student_id
        result = bot.register_student(student_id, class_code, name)
        console.print(f"[green]{result}[/green]\n")

    # Check for active lesson
    if not class_info.active_lesson_json:
        console.print(
            "[yellow]Your teacher hasn't activated a lesson yet. "
            "Check back soon![/yellow]"
        )
        sys.exit(1)

    import json

    lesson_data = json.loads(class_info.active_lesson_json)
    lesson_title = lesson_data.get("title", "Today's Lesson")

    mode_label = "Hint Mode" if class_info.hint_mode else "Answer Mode"
    console.print(
        Panel(
            f"[bold]{lesson_title}[/bold]\n\n"
            f"Ask me anything about today's lesson!\n"
            f"Mode: {mode_label}\n"
            f"Type '/quit' to exit.\n",
            title=f"[bold green]Student Chat — {class_code}[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
    )

    while True:
        try:
            message = Prompt.ask("[bold cyan]You[/bold cyan]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/dim]")
            break

        text = message.strip()
        if not text:
            continue
        if text.lower() in ("/quit", "/exit", "quit", "exit"):
            console.print("[dim]Goodbye![/dim]")
            break

        with Live(
            Spinner("dots", text="[dim]Thinking...[/dim]", style="green"),
            console=console,
            transient=True,
        ):
            try:
                response = _run_async(
                    bot.handle_message(text, student_id, class_code)
                )
            except Exception as e:
                response = f"Oops, something went wrong: {e}"

        console.print()
        console.print(
            Panel(
                response,
                title="[bold green]Teacher[/bold green]",
                border_style="green",
                padding=(0, 1),
            )
        )
        console.print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="EDUagent Student Chat")
    parser.add_argument(
        "--class-code", required=True, help="Class code from your teacher"
    )
    parser.add_argument(
        "--student-id", default="student-001", help="Your student ID"
    )
    parser.add_argument(
        "--name", default=None, help="Your display name"
    )
    args = parser.parse_args()
    main(args.class_code, args.student_id, args.name)
