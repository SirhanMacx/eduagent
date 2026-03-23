"""Rich CLI for EDUagent — beautiful terminal interface with typer."""

from __future__ import annotations

import asyncio
import json
import re
import webbrowser
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

from eduagent import __version__
from eduagent.models import AppConfig, LLMProvider, TeacherPersona

app = typer.Typer(
    name="eduagent",
    help="Your teaching files, your AI co-teacher.",
    rich_markup_mode="rich",
)
console = Console()

# Sub-apps
config_app = typer.Typer(help="Configure EDUagent settings.")
persona_app = typer.Typer(help="Manage teacher personas.")
standards_app = typer.Typer(help="Browse education standards (CCSS, NGSS, C3).")
templates_app = typer.Typer(help="Browse lesson structure templates.")
skills_app = typer.Typer(help="Browse subject-specific pedagogy skills.")
app.add_typer(config_app, name="config")
app.add_typer(persona_app, name="persona")
app.add_typer(standards_app, name="standards")
app.add_typer(templates_app, name="templates")
school_app = typer.Typer(help="Multi-teacher school deployment and shared curriculum.")
app.add_typer(skills_app, name="skills")
app.add_typer(school_app, name="school")


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


def _output_dir() -> Path:
    cfg = AppConfig.load()
    return Path(cfg.output_dir).expanduser().resolve()


def _run_async(coro):
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


def _persona_path() -> Path:
    return _output_dir() / "persona.json"


def _load_persona_or_exit() -> TeacherPersona:
    path = _persona_path()
    if not path.exists():
        console.print(
            "[red]No persona found.[/red] Run [bold]eduagent ingest <path>[/bold] first."
        )
        raise typer.Exit(1)
    from eduagent.persona import load_persona
    return load_persona(path)


# ── Chat command ─────────────────────────────────────────────────────────


@app.command()
def chat(
    teacher_id: str = typer.Option("local-teacher", "--id", help="Teacher session ID"),
) -> None:
    """Start an interactive chat session with EDUagent in the terminal."""
    from eduagent.cli_chat import main as chat_main

    chat_main(teacher_id)


# ── Student chat command ─────────────────────────────────────────────────


@app.command(name="student-chat")
def student_chat(
    class_code: str = typer.Option(..., "--class-code", help="Class code from your teacher"),
    student_id: str = typer.Option("student-001", "--student-id", help="Your student ID"),
) -> None:
    """Start a student chat session — ask questions about today's lesson."""
    from eduagent.student_bot import StudentBot

    bot = StudentBot()
    class_info = bot.get_class(class_code)
    if not class_info:
        console.print(f"[red]Class code '{class_code}' not found.[/red] Check with your teacher.")
        raise typer.Exit(1)

    if not class_info.active_lesson_json:
        console.print("[yellow]Your teacher hasn't activated a lesson yet. Check back soon![/yellow]")
        raise typer.Exit(1)

    import json as _json

    lesson_data = _json.loads(class_info.active_lesson_json)
    lesson_title = lesson_data.get("title", "Today's Lesson")

    console.print(
        Panel(
            f"📚 *{lesson_title}*\n\n"
            f"Ask me anything about today's lesson!\n"
            f"Type '/quit' to exit.\n",
            title=f"[bold green]Student Chat — {class_code}[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
    )

    from rich.live import Live
    from rich.prompt import Prompt
    from rich.spinner import Spinner

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
                response = _run_async(bot.handle_message(text, student_id, class_code))
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


# ── Sub-Packet command ──────────────────────────────────────────────────


@app.command(name="sub-packet")
def sub_packet(
    date: str = typer.Option(
        ..., "--date", "-d", help="Date for the sub packet (e.g. '2026-03-24' or 'tomorrow')"
    ),
    teacher_id: str = typer.Option("local-teacher", "--id", help="Teacher session ID"),
    lesson_id: Optional[str] = typer.Option(None, "--lesson-id", "-l", help="Specific lesson ID"),
    fmt: str = typer.Option("text", "--format", "-f", help="Output format: text, json"),
) -> None:
    """Generate a complete substitute teacher packet."""
    from datetime import datetime, timedelta

    from eduagent.sub_packet import format_sub_packet_text, generate_sub_packet, save_sub_packet

    resolved_date = date.strip().lower()
    if resolved_date == "tomorrow":
        resolved_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    elif resolved_date == "today":
        resolved_date = datetime.now().strftime("%Y-%m-%d")

    console.print(Panel(
        f"Generating sub packet for [bold]{resolved_date}[/bold]",
        title="[bold blue]Substitute Teacher Packet[/bold blue]",
        border_style="blue",
    ))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Generating sub packet...", total=None)
        packet = _run_async(generate_sub_packet(
            teacher_id=teacher_id,
            date=resolved_date,
            lesson_id=lesson_id,
        ))
        progress.update(task, description="Sub packet complete!")

    out_dir = _output_dir()
    json_path = save_sub_packet(packet, out_dir)
    console.print(f"[green]Saved:[/green] {json_path}")

    if fmt == "text":
        text = format_sub_packet_text(packet)
        text_path = out_dir / f"sub_packet_{resolved_date}.txt"
        text_path.write_text(text)
        console.print(f"[green]Text version:[/green] {text_path}")
        console.print()
        console.print(Panel(text, title="Sub Packet Preview", border_style="blue"))
    else:
        console.print(Panel(
            f"[bold]Teacher:[/bold] {packet.teacher_name}\n"
            f"[bold]Date:[/bold] {packet.date}\n"
            f"[bold]Periods:[/bold] {len(packet.schedule)}\n"
            f"[bold]Lessons:[/bold] {len(packet.lesson_instructions)}\n"
            f"[bold]Materials:[/bold] {len(packet.materials_checklist)} items",
            title="Sub Packet Summary",
        ))


# ── Parent Note command ─────────────────────────────────────────────────


@app.command(name="parent-note")
def parent_note(
    student: str = typer.Option(..., "--student", "-s", help="Student's name"),
    topic: str = typer.Option(
        "general progress", "--topic", "-t", help="Note context (e.g. 'midterm', 'behavior')"
    ),
    strengths: Optional[str] = typer.Option(None, "--strengths", help="Comma-separated strengths"),
    growth: Optional[str] = typer.Option(None, "--growth", help="Comma-separated growth areas"),
    teacher_id: str = typer.Option("local-teacher", "--id", help="Teacher session ID"),
) -> None:
    """Generate a parent progress update in the teacher's voice."""
    from eduagent.parent_communication import (
        format_progress_update_text,
        generate_progress_update,
        save_progress_update,
    )
    from eduagent.state import TeacherSession as _TeacherSession

    session = _TeacherSession.load(teacher_id)
    persona = session.persona

    strength_list = [s.strip() for s in strengths.split(",")] if strengths else []
    growth_list = [g.strip() for g in growth.split(",")] if growth else []

    console.print(Panel(
        f"Generating progress update for [bold]{student}[/bold]\nTopic: {topic}",
        title="[bold green]Parent Communication[/bold green]",
        border_style="green",
    ))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Writing progress update...", total=None)
        update = _run_async(generate_progress_update(
            student_name=student,
            strengths=strength_list,
            areas_to_grow=growth_list,
            teacher_persona=persona,
            topic=topic,
        ))
        progress.update(task, description="Progress update complete!")

    out_dir = _output_dir()
    json_path = save_progress_update(update, out_dir)
    console.print(f"[green]Saved:[/green] {json_path}")

    text = format_progress_update_text(update)
    console.print()
    console.print(Panel(text, title=f"Progress Update — {student}", border_style="green"))


# ── MCP Server command ──────────────────────────────────────────────────


@app.command(name="mcp-server")
def mcp_server(
    host: str = typer.Option("localhost", "--host", help="Host to bind to"),
    port: int = typer.Option(8100, "--port", help="Port to bind to"),
) -> None:
    """Start the EDUagent MCP server for tool integration."""
    from eduagent.mcp_server import run_server

    console.print(
        Panel(
            f"Starting MCP server on {host}:{port}\n"
            "Tools: generate_lesson, generate_unit, ingest_materials, student_question, get_teacher_standards",
            title="[bold blue]EDUagent MCP Server[/bold blue]",
            border_style="blue",
        )
    )
    run_server(host=host, port=port)


# ── Ingest command ───────────────────────────────────────────────────────


@app.command()
def ingest(
    path: str = typer.Argument(..., help="Path to directory, ZIP file, or single file to ingest"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be processed without actually processing"),
):
    """Ingest teaching materials and extract a teacher persona."""
    from eduagent.ingestor import ingest_path, scan_directory

    source = Path(path).expanduser().resolve()

    if dry_run:
        console.print(Panel(f"[yellow]DRY RUN[/yellow] — scanning [bold]{source}[/bold]", title="EDUagent"))

        # Show format summary
        if source.is_dir():
            files, summary = scan_directory(source)
            console.print(f"\n[cyan]{summary}[/cyan]\n")
        documents = ingest_path(source, dry_run=True)

        if not documents:
            console.print("[red]No supported documents found.[/red]")
            raise typer.Exit(1)

        table = Table(title="Would Process")
        table.add_column("#", style="dim")
        table.add_column("Title", style="bold")
        table.add_column("Type")
        table.add_column("Path", style="dim")
        for i, doc in enumerate(documents, 1):
            table.add_row(str(i), doc.title, doc.doc_type.value.upper(), doc.source_path or "")
        console.print(table)
        console.print(f"\n[green]{len(documents)} files would be processed.[/green]")
        return

    console.print(Panel(f"Ingesting materials from [bold]{source}[/bold]", title="EDUagent"))

    # Show format summary for directories
    if source.is_dir():
        files, summary = scan_directory(source)
        console.print(f"\n[cyan]{summary}[/cyan]\n")
        file_count = len(files)
    else:
        file_count = 1

    # Use progress bar for large directories (>20 files), spinner otherwise
    if file_count > 20:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Ingesting files...", total=file_count)

            def _update_progress(current: int, total: int) -> None:
                progress.update(task, completed=current)

            documents = ingest_path(source, progress_callback=_update_progress)
            progress.update(task, description=f"Done — {len(documents)} documents extracted")
    else:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Scanning files...", total=None)
            documents = ingest_path(source)
            progress.update(task, description=f"Found {len(documents)} documents")

    if not documents:
        console.print("[red]No supported documents found.[/red]")
        raise typer.Exit(1)

    # Display what was found
    table = Table(title="Ingested Documents")
    table.add_column("#", style="dim")
    table.add_column("Title", style="bold")
    table.add_column("Type")
    table.add_column("Size", justify="right")
    for i, doc in enumerate(documents, 1):
        size = f"{len(doc.content):,} chars"
        table.add_row(str(i), doc.title, doc.doc_type.value.upper(), size)
    console.print(table)

    # Extract persona
    from eduagent.persona import extract_persona, save_persona

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing teaching style...", total=None)
        persona = _run_async(extract_persona(documents))
        progress.update(task, description="Persona extracted!")

    out = save_persona(persona, _output_dir())
    console.print(Panel(
        f"[green]Persona saved to {out}[/green]\n\n"
        f"[bold]Style:[/bold] {persona.teaching_style.value.replace('_', ' ').title()}\n"
        f"[bold]Tone:[/bold] {persona.tone}\n"
        f"[bold]Subject:[/bold] {persona.subject_area}\n"
        f"[bold]Format:[/bold] {persona.preferred_lesson_format}",
        title="Teacher Persona",
    ))


# ── Transcribe command ───────────────────────────────────────────────────


@app.command()
def transcribe(
    audio_file: str = typer.Argument(..., help="Path to audio file (ogg/wav/mp3/m4a)"),
) -> None:
    """Transcribe a voice note to text using Whisper."""
    from eduagent.voice import is_audio_file, transcribe_audio

    source = Path(audio_file).expanduser().resolve()
    if not source.exists():
        console.print(f"[red]File not found:[/red] {source}")
        raise typer.Exit(1)

    if not is_audio_file(source):
        console.print(f"[red]Unsupported format:[/red] {source.suffix}")
        console.print("[dim]Supported: ogg, wav, mp3, m4a, flac, webm, opus[/dim]")
        raise typer.Exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Transcribing audio...", total=None)
        try:
            text = _run_async(transcribe_audio(source))
        except RuntimeError as e:
            console.print(f"[red]{e}[/red]")
            raise typer.Exit(1) from e

    console.print(Panel(text, title="[bold green]Transcription[/bold green]", border_style="green"))


# ── Persona commands ─────────────────────────────────────────────────────


@persona_app.command("show")
def persona_show():
    """Display the current teacher persona."""
    persona = _load_persona_or_exit()
    console.print(Panel(persona.to_prompt_context(), title="Teacher Persona"))


# ── Unit planning ────────────────────────────────────────────────────────


@app.command()
def unit(
    topic: str = typer.Argument(..., help="Unit topic (e.g., 'Photosynthesis')"),
    grade: str = typer.Option("8", "--grade", "-g", help="Grade level"),
    subject: str = typer.Option("Science", "--subject", "-s", help="Subject area"),
    weeks: int = typer.Option(3, "--weeks", "-w", help="Duration in weeks"),
    standards: Optional[str] = typer.Option(None, "--standards", help="Comma-separated standards"),
    fmt: str = typer.Option("markdown", "--format", "-f", help="Export format: markdown, pdf, docx"),
):
    """Plan a complete curriculum unit."""
    from eduagent.exporter import export_unit
    from eduagent.planner import plan_unit, save_unit

    persona = _load_persona_or_exit()
    std_list = [s.strip() for s in standards.split(",")] if standards else None

    console.print(Panel(
        f"[bold]{topic}[/bold] | Grade {grade} {subject} | {weeks} weeks",
        title="Planning Unit",
    ))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Generating unit plan...", total=None)
        unit_plan = _run_async(plan_unit(
            subject=subject,
            grade_level=grade,
            topic=topic,
            duration_weeks=weeks,
            persona=persona,
            standards=std_list,
        ))
        progress.update(task, description="Unit plan complete!")

    out_dir = _output_dir()
    json_path = save_unit(unit_plan, out_dir)
    export_path = export_unit(unit_plan, out_dir, fmt=fmt)

    console.print(f"\n[green]Unit plan saved:[/green] {json_path}")
    console.print(f"[green]Exported:[/green] {export_path}")

    # Summary table
    table = Table(title=unit_plan.title)
    table.add_column("#", style="dim")
    table.add_column("Lesson", style="bold")
    table.add_column("Type")
    for brief in unit_plan.daily_lessons:
        table.add_row(str(brief.lesson_number), brief.topic, brief.lesson_type)
    console.print(table)


# ── Year map & pacing guide ──────────────────────────────────────────────


@app.command(name="year-map")
def year_map(
    subject: str = typer.Argument(..., help="Subject area (e.g., 'Math')"),
    grade: str = typer.Option("8", "--grade", "-g", help="Grade level"),
    standards: Optional[str] = typer.Option(None, "--standards", help="Comma-separated standards"),
    weeks: int = typer.Option(36, "--weeks", "-w", help="Total instructional weeks"),
    school_year: str = typer.Option("", "--school-year", help="School year label (e.g., '2025-26')"),
    fmt: str = typer.Option("markdown", "--format", "-f", help="Export format: markdown, pdf, docx"),
):
    """Generate a full-year curriculum map with unit sequence, big ideas, and assessment calendar."""
    from eduagent.curriculum_map import CurriculumMapper, save_year_map
    from eduagent.exporter import export_year_map

    persona = _load_persona_or_exit()
    std_list = [s.strip() for s in standards.split(",")] if standards else None

    console.print(Panel(
        f"[bold]{subject}[/bold] | Grade {grade} | {weeks} instructional weeks",
        title="Planning Year Map",
    ))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Generating full-year curriculum map...", total=None)
        mapper = CurriculumMapper()
        result = _run_async(mapper.generate_year_map(
            subject=subject,
            grade_level=grade,
            standards=std_list,
            persona=persona,
            school_year=school_year,
            total_weeks=weeks,
        ))
        progress.update(task, description="Year map complete!")

    out_dir = _output_dir()
    json_path = save_year_map(result, out_dir)
    export_path = export_year_map(result, out_dir, fmt=fmt)

    console.print(f"\n[green]Year map saved:[/green] {json_path}")
    console.print(f"[green]Exported:[/green] {export_path}")

    # Summary table
    table = Table(title=f"Year Map — {result.subject}, Grade {result.grade_level}")
    table.add_column("#", style="dim")
    table.add_column("Unit", style="bold")
    table.add_column("Weeks", justify="right")
    table.add_column("Essential Questions")
    for u in result.units:
        eq_preview = u.essential_questions[0][:60] + "..." if u.essential_questions else "—"
        table.add_row(str(u.unit_number), u.title, str(u.duration_weeks), eq_preview)
    console.print(table)

    if result.big_ideas:
        console.print("\n[bold]Big Ideas:[/bold]")
        for bi in result.big_ideas:
            units_str = ", ".join(str(n) for n in bi.connected_units)
            console.print(f"  • {bi.idea} [dim](Units {units_str})[/dim]")


@app.command()
def pacing(
    year_map_file: str = typer.Option(..., "--year-map", "-y", help="Path to year map JSON"),
    start_date: str = typer.Option(..., "--start-date", "-d", help="First instructional day (YYYY-MM-DD)"),
    calendar_file: Optional[str] = typer.Option(None, "--calendar", "-c", help="School calendar JSON file"),
    fmt: str = typer.Option("markdown", "--format", "-f", help="Export format: markdown, pdf, docx"),
):
    """Generate a week-by-week pacing guide from a year map."""
    from eduagent.curriculum_map import CurriculumMapper, load_year_map, save_pacing_guide
    from eduagent.exporter import export_pacing_guide
    from eduagent.models import SchoolCalendarEvent

    persona = _load_persona_or_exit()
    ym = load_year_map(Path(year_map_file))

    # Load school calendar if provided
    school_cal: list[SchoolCalendarEvent] | None = None
    if calendar_file:
        cal_path = Path(calendar_file)
        if cal_path.exists():
            import json as _json
            cal_data = _json.loads(cal_path.read_text())
            school_cal = [SchoolCalendarEvent.model_validate(e) for e in cal_data]

    console.print(Panel(
        f"[bold]{ym.subject}[/bold] Grade {ym.grade_level} | Starting {start_date}",
        title="Generating Pacing Guide",
    ))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Creating week-by-week pacing guide...", total=None)
        mapper = CurriculumMapper()
        guide = _run_async(mapper.generate_pacing_guide(
            year_map=ym,
            start_date=start_date,
            school_calendar=school_cal,
            persona=persona,
        ))
        progress.update(task, description="Pacing guide complete!")

    out_dir = _output_dir()
    json_path = save_pacing_guide(guide, out_dir)
    export_path = export_pacing_guide(guide, out_dir, fmt=fmt)

    console.print(f"\n[green]Pacing guide saved:[/green] {json_path}")
    console.print(f"[green]Exported:[/green] {export_path}")

    # Summary table
    table = Table(title=f"Pacing Guide — {guide.subject}, Grade {guide.grade_level}")
    table.add_column("Week", style="dim", justify="right")
    table.add_column("Dates")
    table.add_column("Unit", style="bold")
    table.add_column("Topics")
    for w in guide.weeks[:10]:  # Show first 10 weeks
        topics = "; ".join(w.topics[:2]) if w.topics else "—"
        table.add_row(
            str(w.week_number),
            f"{w.start_date} – {w.end_date}",
            f"U{w.unit_number}: {w.unit_title}",
            topics,
        )
    console.print(table)
    if len(guide.weeks) > 10:
        console.print(f"[dim]  ... and {len(guide.weeks) - 10} more weeks (see exported file)[/dim]")


# ── Lesson generation ────────────────────────────────────────────────────


@app.command()
def lesson(
    topic: str = typer.Argument(..., help="Lesson topic"),
    unit_file: str = typer.Option(..., "--unit-file", "-u", help="Path to unit plan JSON"),
    lesson_num: int = typer.Option(1, "--lesson-num", "-n", help="Lesson number in unit"),
    homework: bool = typer.Option(True, "--homework/--no-homework", help="Include homework"),
    fmt: str = typer.Option("markdown", "--format", "-f", help="Export format"),
):
    """Generate a detailed daily lesson plan."""
    from eduagent.exporter import export_lesson
    from eduagent.lesson import generate_lesson, save_lesson
    from eduagent.planner import load_unit

    persona = _load_persona_or_exit()
    unit_plan = load_unit(Path(unit_file))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Generating lesson {lesson_num}...", total=None)
        daily = _run_async(generate_lesson(
            lesson_number=lesson_num,
            unit=unit_plan,
            persona=persona,
            include_homework=homework,
        ))
        progress.update(task, description="Lesson plan complete!")

    out_dir = _output_dir()
    json_path = save_lesson(daily, out_dir)
    export_path = export_lesson(daily, out_dir, fmt=fmt)

    console.print(f"\n[green]Lesson saved:[/green] {json_path}")
    console.print(f"[green]Exported:[/green] {export_path}")
    console.print(Panel(
        f"[bold]Objective:[/bold] {daily.objective}\n"
        f"[bold]Standards:[/bold] {', '.join(daily.standards)}",
        title=f"Lesson {daily.lesson_number}: {daily.title}",
    ))


# ── Materials generation ─────────────────────────────────────────────────


@app.command()
def materials(
    lesson_file: str = typer.Option(..., "--lesson-file", "-l", help="Path to lesson plan JSON"),
    fmt: str = typer.Option("markdown", "--format", "-f", help="Export format"),
):
    """Generate all supporting materials for a lesson."""
    from eduagent.exporter import export_materials
    from eduagent.lesson import load_lesson
    from eduagent.materials import generate_all_materials, save_materials

    persona = _load_persona_or_exit()
    daily = load_lesson(Path(lesson_file))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Generating worksheet...", total=4)
        mats = _run_async(generate_all_materials(daily, persona))
        progress.update(task, completed=4, description="All materials generated!")

    out_dir = _output_dir()
    json_path = save_materials(mats, out_dir)
    export_path = export_materials(mats, out_dir, fmt=fmt)

    console.print(f"\n[green]Materials saved:[/green] {json_path}")
    console.print(f"[green]Exported:[/green] {export_path}")
    console.print(Panel(
        f"[bold]Worksheet:[/bold] {len(mats.worksheet_items)} items\n"
        f"[bold]Assessment:[/bold] {len(mats.assessment_questions)} questions\n"
        f"[bold]Rubric:[/bold] {len(mats.rubric)} criteria\n"
        f"[bold]Slides:[/bold] {len(mats.slide_outline)} slides\n"
        f"[bold]IEP Notes:[/bold] {len(mats.iep_notes)} accommodations",
        title="Materials Summary",
    ))


# ── Assessment intelligence ──────────────────────────────────────────────


@app.command()
def assess(
    type: str = typer.Option("quiz", "--type", "-t", help="Assessment type: formative, summative, dbq, quiz"),
    topic: str = typer.Option("", "--topic", help="Topic for quiz or DBQ"),
    grade: str = typer.Option("8", "--grade", "-g", help="Grade level"),
    questions: int = typer.Option(10, "--questions", "-q", help="Number of questions (quiz only)"),
    question_types: str = typer.Option("mixed", "--question-types", help="Question types: mixed, multiple_choice, short_answer"),
    lesson_file: Optional[str] = typer.Option(None, "--lesson-file", "-l", help="Lesson JSON for formative assessment"),
    unit_file: Optional[str] = typer.Option(None, "--unit-file", "-u", help="Unit JSON for summative assessment"),
    context: str = typer.Option("", "--context", "-c", help="Additional context (DBQ)"),
):
    """Generate intelligent assessments — DBQ, summative, formative, or quiz."""
    from eduagent.assessment import (
        AssessmentGenerator,
        save_assessment,
    )

    persona = _load_persona_or_exit()
    gen = AssessmentGenerator(AppConfig.load())

    out_dir = _output_dir()

    if type == "formative":
        if not lesson_file:
            console.print("[red]--lesson-file required for formative assessment.[/red]")
            raise typer.Exit(1)
        from eduagent.lesson import load_lesson

        daily = load_lesson(Path(lesson_file))
        console.print(Panel(
            f"[bold]{daily.title}[/bold] — exit ticket for today's objective",
            title="Formative Assessment",
        ))
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("Generating exit ticket...", total=None)
            result = _run_async(gen.generate_formative(daily, persona))
            progress.update(task, description="Exit ticket ready!")

        path = save_assessment(result, out_dir, "formative")
        console.print(f"\n[green]Saved:[/green] {path}")
        console.print(Panel(
            f"[bold]Objective:[/bold] {result.objective}\n"
            f"[bold]Questions:[/bold] {len(result.questions)}\n"
            f"[bold]Time:[/bold] {result.time_minutes} minutes",
            title="Exit Ticket Summary",
        ))

    elif type == "summative":
        if not unit_file:
            console.print("[red]--unit-file required for summative assessment.[/red]")
            raise typer.Exit(1)
        from eduagent.planner import load_unit

        unit_plan = load_unit(Path(unit_file))
        console.print(Panel(
            f"[bold]{unit_plan.title}[/bold] — unit test",
            title="Summative Assessment",
        ))
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("Generating unit test...", total=None)
            result = _run_async(gen.generate_summative(unit_plan, persona))
            progress.update(task, description="Unit test ready!")

        path = save_assessment(result, out_dir, "summative")
        console.print(f"\n[green]Saved:[/green] {path}")
        console.print(Panel(
            f"[bold]Questions:[/bold] {len(result.questions)}\n"
            f"[bold]Total Points:[/bold] {result.total_points}\n"
            f"[bold]Rubric Criteria:[/bold] {len(result.rubric)}\n"
            f"[bold]Time:[/bold] {result.time_minutes} minutes",
            title="Unit Test Summary",
        ))

    elif type == "dbq":
        if not topic:
            console.print("[red]--topic required for DBQ assessment.[/red]")
            raise typer.Exit(1)
        console.print(Panel(
            f"[bold]{topic}[/bold] — NYS Regents-style DBQ | Grade {grade}",
            title="Document-Based Question",
        ))
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("Generating DBQ with documents...", total=None)
            result = _run_async(gen.generate_dbq(topic, persona, grade_level=grade, context=context))
            progress.update(task, description="DBQ ready!")

        path = save_assessment(result, out_dir, "dbq")
        console.print(f"\n[green]Saved:[/green] {path}")
        console.print(Panel(
            f"[bold]Documents:[/bold] {len(result.documents)}\n"
            f"[bold]Rubric Criteria:[/bold] {len(result.rubric)}\n"
            f"[bold]Model Answer:[/bold] {'Yes' if result.model_answer else 'No'}\n"
            f"[bold]Time:[/bold] {result.time_minutes} minutes",
            title="DBQ Summary",
        ))

    elif type == "quiz":
        if not topic:
            console.print("[red]--topic required for quiz.[/red]")
            raise typer.Exit(1)
        console.print(Panel(
            f"[bold]{topic}[/bold] | Grade {grade} | {questions} questions ({question_types})",
            title="Quiz",
        ))
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("Generating quiz...", total=None)
            result = _run_async(gen.generate_quiz(
                topic=topic,
                question_count=questions,
                question_types=question_types,
                grade=grade,
                persona=persona,
            ))
            progress.update(task, description="Quiz ready!")

        path = save_assessment(result, out_dir, "quiz")
        console.print(f"\n[green]Saved:[/green] {path}")
        console.print(Panel(
            f"[bold]Questions:[/bold] {len(result.questions)}\n"
            f"[bold]Total Points:[/bold] {result.total_points}\n"
            f"[bold]Time:[/bold] {result.time_minutes} minutes",
            title="Quiz Summary",
        ))

    else:
        console.print(f"[red]Unknown assessment type '{type}'. Use: formative, summative, dbq, quiz[/red]")
        raise typer.Exit(1)


@app.command()
def rubric(
    task: str = typer.Option(..., "--task", help="Description of the task to build a rubric for"),
    criteria: int = typer.Option(4, "--criteria", "-c", help="Number of rubric criteria"),
    grade: str = typer.Option("", "--grade", "-g", help="Grade level"),
):
    """Generate a detailed scoring rubric for any written task."""
    from eduagent.assessment import AssessmentGenerator, save_assessment

    persona = _load_persona_or_exit()
    gen = AssessmentGenerator(AppConfig.load())

    console.print(Panel(
        f"[bold]{task}[/bold] | {criteria} criteria",
        title="Rubric Generator",
    ))

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        prog_task = progress.add_task("Generating rubric...", total=None)
        result = _run_async(gen.generate_rubric(task, persona, criteria_count=criteria, grade_level=grade))
        progress.update(prog_task, description="Rubric ready!")

    out_dir = _output_dir()
    path = save_assessment(result, out_dir, "rubric")
    console.print(f"\n[green]Saved:[/green] {path}")

    # Display rubric as a table
    table = Table(title=f"Rubric: {task[:60]}")
    table.add_column("Criterion", style="bold")
    table.add_column("Excellent (4)", style="green")
    table.add_column("Proficient (3)", style="cyan")
    table.add_column("Developing (2)", style="yellow")
    table.add_column("Beginning (1)", style="red")
    for c in result.criteria:
        table.add_row(c.criterion, c.excellent, c.proficient, c.developing, c.beginning)
    console.print(table)
    console.print(f"\n[bold]Total Points:[/bold] {result.total_points}")


# ── Differentiation / IEP ────────────────────────────────────────────────


@app.command()
def differentiate(
    lesson_file: str = typer.Option(..., "--lesson-file", "-l", help="Path to lesson plan JSON"),
    iep: Optional[str] = typer.Option(None, "--iep", help="Path to IEP student profiles JSON"),
    accommodations_504: Optional[str] = typer.Option(None, "--504", help="Comma-separated 504 accommodations"),
    tiered_topic: Optional[str] = typer.Option(None, "--tiered-topic", help="Topic for tiered assignments"),
    tiered_grade: str = typer.Option("8", "--tiered-grade", help="Grade level for tiered assignments"),
    tiers: int = typer.Option(3, "--tiers", help="Number of difficulty tiers"),
):
    """Generate IEP modifications, 504 accommodations, and tiered assignments."""
    from eduagent.differentiation import (
        generate_504_accommodations,
        generate_iep_lesson_modifications,
        generate_tiered_assignments,
        load_iep_profiles,
        save_modified_lessons,
        save_tiered_assignments,
    )
    from eduagent.lesson import load_lesson

    daily = load_lesson(Path(lesson_file))
    out_dir = _output_dir()
    ran_any = False

    # IEP modifications
    if iep:
        ran_any = True
        profiles = load_iep_profiles(Path(iep))
        console.print(Panel(
            f"Generating modified lessons for [bold]{len(profiles)}[/bold] IEP students",
            title="IEP Modifications",
        ))

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Modifying lessons for IEP students...", total=None)
            modifications = _run_async(generate_iep_lesson_modifications(daily, profiles))
            progress.update(task, description=f"Generated {len(modifications)} modified lessons!")

        paths = save_modified_lessons(modifications, out_dir)
        table = Table(title="IEP Modified Lessons")
        table.add_column("Student", style="bold")
        table.add_column("Modified Title")
        table.add_column("File", style="dim")
        for name, mod_lesson in modifications.items():
            path = next((p for p in paths if name.lower().replace(" ", "_")[:50] in str(p)), paths[0])
            table.add_row(name, mod_lesson.title, str(path))
        console.print(table)

    # 504 accommodations
    if accommodations_504:
        ran_any = True
        acc_list = [a.strip() for a in accommodations_504.split(",")]
        console.print(Panel(
            f"Generating 504 accommodations: {', '.join(acc_list)}",
            title="504 Accommodations",
        ))

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Generating 504 accommodations...", total=None)
            notes = _run_async(generate_504_accommodations(daily, acc_list))
            progress.update(task, description="504 accommodations complete!")

        console.print(Panel(
            "\n".join(f"  - {s}" for s in notes.struggling) or "  (none)",
            title="504 Accommodation Notes",
        ))

    # Tiered assignments
    if tiered_topic:
        ran_any = True
        console.print(Panel(
            f"Generating [bold]{tiers}-tier[/bold] assignments for: {tiered_topic}",
            title="Tiered Assignments",
        ))

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Generating tiered assignments...", total=None)
            items = _run_async(generate_tiered_assignments(tiered_topic, tiered_grade, tiers))
            progress.update(task, description=f"Generated {len(items)} tiered items!")

        path = save_tiered_assignments(items, out_dir, tiered_topic)
        table = Table(title="Tiered Assignment Summary")
        table.add_column("Tier", style="bold")
        table.add_column("Items", justify="right")
        for t in range(tiers):
            low = t * 100 + (1 if t == 0 else 0)
            high = (t + 1) * 100
            count = sum(1 for i in items if low <= i.item_number < high)
            labels = ["Approaching", "On-Level", "Advanced"] + [f"Tier {t + 1}"]
            table.add_row(labels[min(t, len(labels) - 1)], str(count))
        console.print(table)
        console.print(f"[green]Saved:[/green] {path}")

    if not ran_any:
        console.print(
            "[yellow]Specify at least one option:[/yellow] --iep, --504, or --tiered-topic\n"
            "Example: eduagent differentiate --lesson-file lesson.json --iep students.json"
        )
        raise typer.Exit(1)


# ── Full pipeline ────────────────────────────────────────────────────────


@app.command()
def full(
    topic: str = typer.Argument(..., help="Unit topic"),
    grade: str = typer.Option("8", "--grade", "-g", help="Grade level"),
    subject: str = typer.Option("Science", "--subject", "-s", help="Subject area"),
    weeks: int = typer.Option(3, "--weeks", "-w", help="Duration in weeks"),
    standards: Optional[str] = typer.Option(None, "--standards", help="Comma-separated standards"),
    homework: bool = typer.Option(True, "--homework/--no-homework", help="Include homework"),
    fmt: str = typer.Option("markdown", "--format", "-f", help="Export format"),
    max_lessons: Optional[int] = typer.Option(None, "--max-lessons", help="Limit lessons generated"),
):
    """End-to-end generation: unit plan + all lesson plans + all materials."""
    from eduagent.exporter import export_lesson, export_materials, export_unit
    from eduagent.lesson import generate_lesson, save_lesson
    from eduagent.materials import generate_all_materials, save_materials
    from eduagent.planner import plan_unit, save_unit

    persona = _load_persona_or_exit()
    std_list = [s.strip() for s in standards.split(",")] if standards else None
    out_dir = _output_dir()

    console.print(Panel(
        f"[bold]{topic}[/bold] | Grade {grade} {subject} | {weeks} weeks\n"
        f"Full pipeline: unit plan + lessons + materials",
        title="EDUagent Full Generation",
    ))

    # Step 1: Unit plan
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Step 1/3: Planning unit...", total=None)
        unit_plan = _run_async(plan_unit(
            subject=subject,
            grade_level=grade,
            topic=topic,
            duration_weeks=weeks,
            persona=persona,
            standards=std_list,
        ))
        progress.update(task, description="Unit plan complete!")

    save_unit(unit_plan, out_dir)
    export_unit(unit_plan, out_dir, fmt=fmt)
    console.print(f"[green]Unit plan:[/green] {unit_plan.title} ({len(unit_plan.daily_lessons)} lessons)")

    # Step 2: Lesson plans
    lesson_briefs = unit_plan.daily_lessons
    if max_lessons:
        lesson_briefs = lesson_briefs[:max_lessons]

    lessons = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Step 2/3: Generating lessons...", total=len(lesson_briefs))
        for brief in lesson_briefs:
            progress.update(task, description=f"Lesson {brief.lesson_number}: {brief.topic}")
            daily = _run_async(generate_lesson(
                lesson_number=brief.lesson_number,
                unit=unit_plan,
                persona=persona,
                include_homework=homework,
            ))
            save_lesson(daily, out_dir)
            export_lesson(daily, out_dir, fmt=fmt)
            lessons.append(daily)
            progress.advance(task)

    # Step 3: Materials for each lesson
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Step 3/3: Generating materials...", total=len(lessons))
        for daily in lessons:
            progress.update(task, description=f"Materials for lesson {daily.lesson_number}")
            mats = _run_async(generate_all_materials(daily, persona))
            save_materials(mats, out_dir)
            export_materials(mats, out_dir, fmt=fmt)
            progress.advance(task)

    # Final summary
    console.print(Panel(
        f"[green bold]Generation complete![/green bold]\n\n"
        f"[bold]Unit:[/bold] {unit_plan.title}\n"
        f"[bold]Lessons:[/bold] {len(lessons)}\n"
        f"[bold]Materials sets:[/bold] {len(lessons)}\n"
        f"[bold]Output:[/bold] {out_dir}",
        title="Done!",
    ))


# ── Config commands ──────────────────────────────────────────────────────


@config_app.command("set-model")
def config_set_model(
    provider: str = typer.Argument(..., help="LLM provider: anthropic, openai, or ollama"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Model name override"),
):
    """Configure the LLM backend."""
    try:
        llm_provider = LLMProvider(provider.lower())
    except ValueError:
        console.print(f"[red]Unknown provider: {provider}[/red]. Use: anthropic, openai, ollama")
        raise typer.Exit(1)

    cfg = AppConfig.load()
    cfg.provider = llm_provider

    if model:
        if llm_provider == LLMProvider.ANTHROPIC:
            cfg.anthropic_model = model
        elif llm_provider == LLMProvider.OPENAI:
            cfg.openai_model = model
        elif llm_provider == LLMProvider.OLLAMA:
            cfg.ollama_model = model

    cfg.save()
    model_name = model or {
        LLMProvider.ANTHROPIC: cfg.anthropic_model,
        LLMProvider.OPENAI: cfg.openai_model,
        LLMProvider.OLLAMA: cfg.ollama_model,
    }[llm_provider]

    console.print(Panel(
        f"[bold]Provider:[/bold] {llm_provider.value}\n"
        f"[bold]Model:[/bold] {model_name}",
        title="Configuration Updated",
    ))


@config_app.command("set-token")
def config_set_token(
    token: str = typer.Argument(..., help="Telegram bot token from @BotFather"),
):
    """Save your Telegram bot token so you don't need to pass it every time.

    After saving, just run:

        eduagent bot

    No --token flag needed.
    """
    cfg = AppConfig.load()
    cfg.telegram_bot_token = token
    cfg.save()
    masked = token[:5] + "..." + token[-4:] if len(token) > 12 else "***"
    console.print(Panel(
        f"[bold green]Token saved![/bold green]\n\n"
        f"Token: {masked}\n\n"
        f"You can now start the bot with just:\n"
        f"  [cyan]eduagent bot[/cyan]",
        title="Telegram Bot Token",
    ))


@config_app.command("show")
def config_show():
    """Show current configuration."""
    cfg = AppConfig.load()
    token_display = "Not set"
    if cfg.telegram_bot_token:
        t = cfg.telegram_bot_token
        token_display = t[:5] + "..." + t[-4:] if len(t) > 12 else "***"
    console.print(Panel(
        f"[bold]Provider:[/bold] {cfg.provider.value}\n"
        f"[bold]Anthropic Model:[/bold] {cfg.anthropic_model}\n"
        f"[bold]OpenAI Model:[/bold] {cfg.openai_model}\n"
        f"[bold]Ollama Model:[/bold] {cfg.ollama_model}\n"
        f"[bold]Ollama URL:[/bold] {cfg.ollama_base_url}\n"
        f"[bold]Output Dir:[/bold] {cfg.output_dir}\n"
        f"[bold]Export Format:[/bold] {cfg.export_format}\n"
        f"[bold]Include Homework:[/bold] {cfg.include_homework}\n"
        f"[bold]Telegram Token:[/bold] {token_display}",
        title="EDUagent Configuration",
    ))


# ── Demo command ─────────────────────────────────────────────────────────


_DEMO_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EDUagent Demo</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    line-height: 1.6; color: #1a1a2e; background: #fff; max-width: 860px;
    margin: 0 auto; padding: 2rem 1.5rem;
  }
  h1 { font-size: 2rem; margin-bottom: .25rem; }
  .subtitle { color: #555; margin-bottom: 2rem; font-size: 1.1rem; }
  h2 { font-size: 1.35rem; margin: 2rem 0 .75rem; color: #16213e; border-bottom: 2px solid #0f3460; padding-bottom: .3rem; }
  table { width: 100%%; border-collapse: collapse; margin-bottom: 1.5rem; }
  th, td { text-align: left; padding: .65rem .85rem; border: 1px solid #ddd; }
  th { background: #0f3460; color: #fff; font-weight: 600; }
  tr:nth-child(even) { background: #f8f9fa; }
  td:first-child { font-weight: 600; white-space: nowrap; width: 200px; }
  .get-started {
    background: #f0f4ff; border: 1px solid #0f3460; border-radius: 8px;
    padding: 1.5rem; margin-top: 2.5rem;
  }
  .get-started h2 { border: none; margin-top: 0; padding-bottom: 0; }
  .get-started ol { padding-left: 1.3rem; }
  .get-started li { margin-bottom: .4rem; }
  code {
    background: #eef; padding: .15rem .4rem; border-radius: 3px;
    font-family: "SF Mono", "Fira Code", "Cascadia Code", monospace; font-size: .92em;
  }
  a { color: #0f3460; }
  .badge-row { display: flex; gap: .5rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
  .badge {
    display: inline-block; padding: .2rem .65rem; border-radius: 4px;
    font-size: .8rem; font-weight: 600; color: #fff;
  }
  .badge-blue { background: #0f3460; }
  .badge-green { background: #2e7d32; }
  .badge-orange { background: #e65100; }
</style>
</head>
<body>
<h1>EDUagent Demo</h1>
<p class="subtitle">No API key needed &mdash; example output for 8th Grade Science / Photosynthesis / 2 weeks</p>
<div class="badge-row">
  <span class="badge badge-blue">Python 3.10+</span>
  <span class="badge badge-green">MIT License</span>
  <span class="badge badge-orange">Works with Ollama</span>
</div>

<h2>Sample Unit Plan</h2>
<table>
  <tr><th>Field</th><th>Value</th></tr>
  <tr><td>Title</td><td>Life From Light: Understanding Photosynthesis</td></tr>
  <tr><td>Grade</td><td>8th Grade Science</td></tr>
  <tr><td>Duration</td><td>2 weeks / 10 lessons</td></tr>
  <tr><td>Essential Questions</td><td>How do plants convert light into food?<br>Why does photosynthesis matter for all life on Earth?<br>How do plants and animals depend on each other?</td></tr>
  <tr><td>Enduring Understandings</td><td>Energy flows through ecosystems starting with photosynthesis.<br>Matter and energy transformations obey conservation laws.</td></tr>
  <tr><td>Lesson Sequence</td><td>L1: What is Photosynthesis? The Big Picture<br>L2: Light Energy and Chlorophyll<br>L3: The Light-Dependent Reactions<br>L4: The Calvin Cycle<br>L5: Lab &mdash; Leaf Disk Assay<br>L6&ndash;10: Factors, Applications &amp; Assessment</td></tr>
</table>

<h2>Sample Lesson Plan &mdash; Lesson 1</h2>
<table>
  <tr><th>Component</th><th>Content</th></tr>
  <tr><td>Objective (SWBAT)</td><td>Students will be able to write the overall equation for photosynthesis and explain what enters and exits the leaf.</td></tr>
  <tr><td>Do-Now (5 min)</td><td>Look at the photo on the board. Where does a plant get its food? Write your hypothesis in 2 sentences.</td></tr>
  <tr><td>Direct Instruction (20 min)</td><td>Walk through the big-picture equation: sunlight = power, CO&#8322; + H&#8322;O = raw materials, glucose = product. Use the chloroplast diagram on p.&nbsp;34.</td></tr>
  <tr><td>Guided Practice (15 min)</td><td>Leaf observation: each pair gets a leaf, hand lens, and recording sheet. Students sketch the leaf structure and label where photosynthesis occurs.</td></tr>
  <tr><td>Exit Ticket (5 min)</td><td>1. Write the word equation for photosynthesis.<br>2. Name ONE thing a plant needs from the environment.<br>3. Name ONE thing a plant releases.</td></tr>
  <tr><td>Differentiation</td><td>Struggling: sentence frames for exit ticket.<br>Advanced: research C4 vs C3 photosynthesis.</td></tr>
</table>

<div class="get-started">
  <h2>Get Started</h2>
  <ol>
    <li><code>pip install eduagent</code></li>
    <li><code>eduagent config set-model ollama</code> &nbsp;(free, local)</li>
    <li><code>eduagent ingest ~/your-lesson-plans/</code></li>
    <li><code>eduagent full "Photosynthesis" --grade 8 --subject science --weeks 2</code></li>
  </ol>
  <p style="margin-top:1rem;">GitHub: <a href="https://github.com/SirhanMacx/eduagent">github.com/SirhanMacx/eduagent</a></p>
</div>
</body>
</html>
"""


@app.command()
def demo(
    web: bool = typer.Option(False, "--web", help="Generate an HTML demo page and open it in your browser"),
):
    """Show a sample output without needing an API key or any files.

    Prints a realistic example unit plan and lesson plan to demonstrate
    what EDUagent generates. No setup required.
    """
    if web:
        out_dir = Path("~/eduagent_output").expanduser().resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        html_path = out_dir / "demo.html"
        html_path.write_text(_DEMO_HTML)
        console.print(f"[green]Demo HTML saved:[/green] {html_path}")
        webbrowser.open(html_path.as_uri())
        return

    console.print(Panel(
        "[bold green]EDUagent Demo[/bold green] — no API key needed\n"
        "This is example output for: 8th Grade Science / Photosynthesis / 2 weeks",
        title="EDUagent",
        border_style="green",
    ))

    # ── Sample unit plan ──────────────────────────────────────────────────────
    unit_table = Table(title="Sample Unit Plan", show_header=True, header_style="bold cyan")
    unit_table.add_column("Field", style="bold")
    unit_table.add_column("Value")
    unit_table.add_row("Title", "Life From Light: Understanding Photosynthesis")
    unit_table.add_row("Grade", "8th Grade Science")
    unit_table.add_row("Duration", "2 weeks / 10 lessons")
    unit_table.add_row(
        "Essential Questions",
        "How do plants convert light into food?\n"
        "Why does photosynthesis matter for all life on Earth?\n"
        "How do plants and animals depend on each other?",
    )
    unit_table.add_row(
        "Enduring Understandings",
        "Energy flows through ecosystems starting with photosynthesis.\n"
        "Matter and energy transformations obey conservation laws.",
    )
    unit_table.add_row(
        "Lesson Sequence (sample)",
        "L1: What is Photosynthesis? The Big Picture\n"
        "L2: Light Energy and Chlorophyll\n"
        "L3: The Light-Dependent Reactions\n"
        "L4: The Calvin Cycle\n"
        "L5: Lab — Leaf Disk Assay\n"
        "L6-10: Factors, Applications & Assessment",
    )
    console.print(unit_table)

    console.print()

    # ── Sample lesson plan ────────────────────────────────────────────────────
    lesson_table = Table(title="Sample Lesson Plan — Lesson 1", show_header=True, header_style="bold magenta")
    lesson_table.add_column("Component", style="bold")
    lesson_table.add_column("Content", max_width=70)
    lesson_table.add_row(
        "Objective (SWBAT)",
        "Students will be able to write the overall equation for photosynthesis\n"
        "and explain what enters and exits the leaf.",
    )
    lesson_table.add_row(
        "Do-Now (5 min)",
        "Look at the photo on the board. Where does a plant get its food?\n"
        "Write your hypothesis in 2 sentences.",
    )
    lesson_table.add_row(
        "Direct Instruction (20 min)",
        "Walk through the big-picture equation: sunlight = power,\n"
        "CO₂ + H₂O = raw materials, glucose = product.\n"
        "Use the chloroplast diagram on p. 34.",
    )
    lesson_table.add_row(
        "Guided Practice (15 min)",
        "Leaf observation: each pair gets a leaf, hand lens, and recording sheet.\n"
        "Students sketch the leaf structure and label where photosynthesis occurs.",
    )
    lesson_table.add_row(
        "Exit Ticket (5 min)",
        "1. Write the word equation for photosynthesis.\n"
        "2. Name ONE thing a plant needs from the environment.\n"
        "3. Name ONE thing a plant releases.",
    )
    lesson_table.add_row(
        "Differentiation",
        "Struggling: sentence frames for exit ticket.\n"
        "Advanced: research C4 vs C3 photosynthesis.",
    )
    console.print(lesson_table)

    console.print()
    console.print(Panel(
        "[bold]To generate real content from your own materials:[/bold]\n\n"
        "  1. [cyan]pip install eduagent[/cyan]\n"
        "  2. [cyan]eduagent config set-model ollama[/cyan]  (free, local)\n"
        "  3. [cyan]eduagent ingest ~/your-lesson-plans/[/cyan]\n"
        "  4. [cyan]eduagent full \"Photosynthesis\" --grade 8 --subject science --weeks 2[/cyan]\n\n"
        "GitHub: [link]https://github.com/SirhanMacx/eduagent[/link]",
        title="Get Started",
        border_style="cyan",
    ))


# ── Standards commands ───────────────────────────────────────────────────


@standards_app.command("list")
def standards_list(
    grade: str = typer.Option(..., "--grade", "-g", help="Grade level (e.g., K, 5, 8, 9-12)"),
    subject: str = typer.Option(..., "--subject", "-s", help="Subject (math, ela, science, history)"),
):
    """List education standards for a grade and subject."""
    from eduagent.standards import get_standards, resolve_subject

    canonical = resolve_subject(subject)
    if canonical is None:
        console.print(
            f"[red]Unknown subject: {subject}[/red]. "
            "Supported: math, ela/english, science, history/social studies"
        )
        raise typer.Exit(1)

    results = get_standards(subject, grade)
    if not results:
        console.print(f"[yellow]No standards found for grade {grade} {subject}.[/yellow]")
        raise typer.Exit(0)

    framework = {
        "math": "CCSS Mathematics",
        "ela": "CCSS ELA/Literacy",
        "science": "NGSS",
        "history": "C3 Framework",
    }[canonical]

    table = Table(title=f"{framework} — Grade {grade}")
    table.add_column("Standard Code", style="bold cyan", no_wrap=True)
    table.add_column("Description")
    table.add_column("Grade Band", style="dim", justify="center")

    for code, desc, band in results:
        table.add_row(code, desc, band)

    console.print(table)
    console.print(f"\n[dim]{len(results)} standard(s) found.[/dim]")


# ── Share command ────────────────────────────────────────────────────────


def _lesson_to_html(data: dict) -> str:
    """Convert a lesson JSON dict to a self-contained HTML page."""
    title = data.get("title", "Lesson Plan")
    objective = data.get("objective", "")
    do_now = data.get("do_now", "")
    direct_instruction = data.get("direct_instruction", "")
    guided_practice = data.get("guided_practice", "")
    independent_work = data.get("independent_work", "")
    homework = data.get("homework", "")
    standards = data.get("standards", [])
    materials_needed = data.get("materials_needed", [])
    lesson_number = data.get("lesson_number", "")

    exit_tickets = data.get("exit_ticket", [])
    exit_html = ""
    if exit_tickets:
        for et in exit_tickets:
            q = et.get("question", "") if isinstance(et, dict) else str(et)
            exit_html += f"<li>{_esc(q)}</li>"
        exit_html = f"<ol>{exit_html}</ol>"

    diff = data.get("differentiation", {})
    diff_html = ""
    if isinstance(diff, dict):
        for key, val in diff.items():
            if val:
                label = key.replace("_", " ").title()
                diff_html += f"<p><strong>{_esc(label)}:</strong> {_esc(str(val))}</p>"

    standards_html = ""
    if standards:
        standards_html = ", ".join(_esc(s) for s in standards)

    materials_html = ""
    if materials_needed:
        materials_html = ", ".join(_esc(m) for m in materials_needed)

    def _section(heading: str, body: str) -> str:
        if not body:
            return ""
        return f'<div class="section"><h3>{heading}</h3><p>{_esc(body)}</p></div>'

    sections = [
        _section("Objective (SWBAT)", objective),
        _section("Do-Now", do_now),
        _section("Direct Instruction", direct_instruction),
        _section("Guided Practice", guided_practice),
        _section("Independent Work", independent_work),
    ]
    if exit_html:
        sections.append(f'<div class="section"><h3>Exit Ticket</h3>{exit_html}</div>')
    if homework:
        sections.append(_section("Homework", homework))
    if diff_html:
        sections.append(f'<div class="section"><h3>Differentiation</h3>{diff_html}</div>')

    num_label = f"Lesson {lesson_number}: " if lesson_number else ""

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_esc(title)}</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    line-height: 1.6; color: #1a1a2e; background: #fff; max-width: 800px;
    margin: 0 auto; padding: 2rem 1.5rem;
  }}
  h1 {{ font-size: 1.8rem; margin-bottom: .25rem; color: #0f3460; }}
  .meta {{ color: #555; margin-bottom: 1.5rem; font-size: .95rem; }}
  .section {{ margin-bottom: 1.25rem; }}
  h3 {{ font-size: 1.1rem; color: #16213e; margin-bottom: .3rem; border-left: 3px solid #0f3460; padding-left: .6rem; }}
  p {{ margin-bottom: .5rem; }}
  ol {{ padding-left: 1.3rem; margin-bottom: .5rem; }}
  li {{ margin-bottom: .25rem; }}
  .footer {{ margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #ddd; color: #888; font-size: .85rem; }}
</style>
</head>
<body>
<h1>{_esc(num_label + title)}</h1>
<p class="meta">
  {f"<strong>Standards:</strong> {standards_html}<br>" if standards_html else ""}
  {f"<strong>Materials:</strong> {materials_html}" if materials_html else ""}
</p>
{"".join(sections)}
<div class="footer">Generated by EDUagent &mdash; <a href="https://github.com/SirhanMacx/eduagent">github.com/SirhanMacx/eduagent</a></div>
</body>
</html>
"""


def _esc(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


@app.command()
def share(
    lesson_file: str = typer.Option(..., "--lesson-file", "-l", help="Path to a saved lesson JSON file"),
):
    """Generate a shareable HTML file from a saved lesson plan JSON."""
    path = Path(lesson_file).expanduser().resolve()
    if not path.exists():
        console.print(f"[red]File not found:[/red] {path}")
        raise typer.Exit(1)

    data = json.loads(path.read_text())
    title = data.get("title", "lesson")
    safe_title = re.sub(r"[^a-zA-Z0-9_-]", "_", title).strip("_")[:80]

    out_dir = Path("eduagent_output/shared").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / f"lesson_{safe_title}.html"

    html_path.write_text(_lesson_to_html(data))
    console.print(f"[green]Shareable lesson saved:[/green] {html_path}")


# ── Landing page command ─────────────────────────────────────────────


@app.command(name="generate-landing")
def generate_landing(
    output: str = typer.Option("./eduagent_output/landing", "--output", "-o", help="Output directory"),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="Open in browser after generating"),
):
    """Generate the EDUagent landing page (self-contained HTML)."""
    landing_src = Path(__file__).parent / "landing" / "index.html"
    if not landing_src.exists():
        console.print("[red]Landing page template not found.[/red]")
        raise typer.Exit(1)

    out_dir = Path(output).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / "index.html"
    dest.write_text(landing_src.read_text())

    console.print(f"[green]Landing page generated:[/green] {dest}")
    if open_browser:
        webbrowser.open(dest.as_uri())


# ── Serve command ──────────────────────────────────────────────────────


def _first_run_setup() -> None:
    """Interactive first-run setup wizard. Only runs when no config exists."""
    from rich.prompt import Prompt

    from eduagent.config import has_config, set_api_key, test_llm_connection

    if has_config():
        return

    console.print(Panel(
        "[bold]Welcome to EDUagent![/bold]\n\nLet's get you set up in 2 minutes.",
        title="Setup",
        border_style="blue",
    ))

    # Provider selection
    provider_choice = Prompt.ask(
        "Which AI provider do you want to use?",
        choices=["ollama", "anthropic", "openai"],
        default="ollama",
    )

    cfg = AppConfig()
    cfg.provider = LLMProvider(provider_choice)

    # API key for cloud providers
    if provider_choice in ("anthropic", "openai"):
        api_key = Prompt.ask(f"Enter your {provider_choice.title()} API key", password=True)
        if api_key.strip():
            set_api_key(provider_choice, api_key.strip())
            console.print("[green]API key saved securely.[/green]")

    # Test connection
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task("Testing connection...", total=None)
        result = _run_async(test_llm_connection(cfg))
        progress.update(task, description="Done!")

    model = result.get("model", "")
    if result.get("connected"):
        console.print(f"[green]Connected to {model}[/green]")
    else:
        console.print(f"[yellow]Could not connect: {result.get('error', 'unknown')}[/yellow]")
        console.print("[dim]You can update settings later at http://localhost:8000/settings[/dim]")

    # Subject and grades
    subject = Prompt.ask("What subject do you teach?", default="Science")
    grades = Prompt.ask("What grade(s)?", default="8")

    cfg.save()

    console.print("\n[green]Configuration saved![/green]")
    console.print(f"[dim]Subject: {subject}, Grades: {grades}[/dim]\n")


@app.command()
def serve(
    port: int = typer.Option(8000, "--port", "-p", help="Port to listen on"),
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind to"),
    token: Optional[str] = typer.Option(None, "--token", "-t", envvar="TELEGRAM_BOT_TOKEN", help="Telegram bot token"),
    tui: bool = typer.Option(False, "--tui", help="Launch the live TUI dashboard"),
    skip_setup: bool = typer.Option(False, "--skip-setup", help="Skip first-run setup wizard"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload for development"),
):
    """Start the EDUagent server.

    \b
    Modes:
      eduagent serve --token TOKEN --tui   # Full TUI + gateway + web
      eduagent serve --token TOKEN         # Gateway + web (no TUI, for VPS)
      eduagent serve --tui                 # TUI only (no Telegram, demos)
      eduagent serve                       # Web server only
    """
    if not skip_setup:
        _first_run_setup()

    cfg = AppConfig.load()

    # Resolve token from saved config if not provided
    if not token:
        token = cfg.telegram_bot_token

    if tui:
        _serve_with_tui(token=token or None, host=host, port=port, config=cfg)
    elif token:
        _serve_gateway_headless(token=token, host=host, port=port, config=cfg)
    else:
        import uvicorn
        console.print(Panel(
            f"[bold]Starting EDUagent web server[/bold]\n"
            f"[cyan]http://{host}:{port}[/cyan]\n"
            f"Dashboard: [cyan]http://{host}:{port}/dashboard[/cyan]\n"
            f"Generate: [cyan]http://{host}:{port}/generate[/cyan]\n"
            f"Settings: [cyan]http://{host}:{port}/settings[/cyan]",
            title="EDUagent Server",
            border_style="green",
        ))
        uvicorn.run("eduagent.api.server:app", host=host, port=port, reload=reload)


def _serve_with_tui(
    token: Optional[str], host: str, port: int, config: Optional[AppConfig] = None,
) -> None:
    """Launch the full TUI dashboard with gateway."""
    try:
        from eduagent.gateway import EduAgentGateway
        from eduagent.tui import EduAgentDashboard
    except ImportError as e:
        console.print(f"[red]Missing dependency:[/red] {e}")
        console.print("\nInstall TUI support with:")
        console.print("  [cyan]pip install 'eduagent[tui]'[/cyan]")
        raise typer.Exit(1)

    gateway = EduAgentGateway(token=token, config=config)

    async def _run() -> None:
        tasks = [asyncio.create_task(gateway.start())]

        # Also start web server in background
        import uvicorn
        uv_config = uvicorn.Config("eduagent.api.server:app", host=host, port=port, log_level="warning")
        server = uvicorn.Server(uv_config)
        tasks.append(asyncio.create_task(server.serve()))

        # TUI blocks until quit
        dashboard = EduAgentDashboard(gateway=gateway)
        tasks.append(asyncio.create_task(dashboard.run_async()))

        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for t in pending:
            t.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        await gateway.stop()

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped.[/yellow]")


def _serve_gateway_headless(
    token: str, host: str, port: int, config: Optional[AppConfig] = None,
) -> None:
    """Run gateway + web server without TUI (VPS mode)."""
    from eduagent.gateway import EduAgentGateway

    gateway = EduAgentGateway(token=token, config=config)

    console.print(Panel(
        f"[bold green]EDUagent Gateway[/bold green]\n\n"
        f"Telegram: connected\n"
        f"Web: [cyan]http://{host}:{port}[/cyan]\n\n"
        f"[dim]Press Ctrl+C to stop[/dim]",
        title="\U0001f393 EDUagent",
        border_style="green",
    ))

    async def _run() -> None:
        import uvicorn
        tasks = [asyncio.create_task(gateway.start())]
        uv_config = uvicorn.Config("eduagent.api.server:app", host=host, port=port, log_level="warning")
        server = uvicorn.Server(uv_config)
        tasks.append(asyncio.create_task(server.serve()))
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for t in pending:
            t.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        await gateway.stop()

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Gateway stopped.[/yellow]")


@app.command()
def status():
    """Quick one-line status check (no TUI, for scripts)."""
    cfg = AppConfig.load()
    profile = cfg.teacher_profile
    name = profile.name or "Teacher"
    provider = cfg.provider.value
    if provider == "ollama":
        model = cfg.ollama_model
    elif provider == "anthropic":
        model = cfg.anthropic_model
    else:
        model = cfg.openai_model

    has_token = bool(cfg.telegram_bot_token)
    tg_status = "[green]configured[/green]" if has_token else "[dim]not set[/dim]"

    console.print(
        f"[bold]{name}[/bold] | "
        f"Model: {model} ({provider}) | "
        f"Telegram: {tg_status} | "
        f"Output: {cfg.output_dir}"
    )


# ── Improve command ───────────────────────────────────────────────────


@app.command()
def improve(
    days: int = typer.Option(7, "--days", "-d", help="Feedback window in days"),
):
    """Run one cycle of prompt improvement based on teacher feedback."""
    from eduagent.database import Database
    from eduagent.improver import improve_prompts

    db = Database()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing feedback and improving prompts...", total=None)
        result = _run_async(improve_prompts(db, feedback_window_days=days))
        progress.update(task, description="Done!")

    db.close()

    status = result.get("status", "unknown")
    message = result.get("message", "")

    if status == "no_feedback":
        console.print(f"[yellow]{message}[/yellow]")
    elif status == "good":
        console.print(f"[green]{message}[/green]")
    elif status == "improved":
        console.print(Panel(
            f"[green]{message}[/green]\n"
            f"[bold]Prompt type:[/bold] {result.get('prompt_type', '')}\n"
            f"[bold]New version:[/bold] {result.get('new_version', '')}\n"
            f"[bold]Avg rating:[/bold] {result.get('feedback_summary', {}).get('avg_rating', '')}/5",
            title="Prompt Improvement",
        ))
    else:
        console.print(f"[dim]{message}[/dim]")


# ── Score command ────────────────────────────────────────────────────


@app.command()
def score(
    lesson_file: str = typer.Option(..., "--lesson-file", "-l", help="Path to a saved lesson JSON file"),
):
    """Score a lesson plan on quality dimensions (1-5 per dimension)."""
    from eduagent.models import DailyLesson
    from eduagent.quality import LessonQualityScore

    path = Path(lesson_file).expanduser().resolve()
    if not path.exists():
        console.print(f"[red]File not found:[/red] {path}")
        raise typer.Exit(1)

    data = json.loads(path.read_text())
    lesson = DailyLesson.model_validate(data)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Scoring lesson quality...", total=None)
        scorer = LessonQualityScore()
        scores = _run_async(scorer.score(lesson))
        progress.update(task, description="Scoring complete!")

    table = Table(title="Lesson Quality Score")
    table.add_column("Dimension", style="bold")
    table.add_column("Score", justify="center")
    table.add_column("Explanation")

    for dim in LessonQualityScore.dimensions:
        info = scores.get(dim, {})
        s = info.get("score", 0)
        color = "green" if s >= 4 else ("yellow" if s == 3 else "red")
        table.add_row(
            dim.replace("_", " ").title(),
            f"[{color}]{s}/5[/{color}]",
            info.get("explanation", ""),
        )

    console.print(table)
    overall = scores.get("overall", 0)
    color = "green" if overall >= 4 else ("yellow" if overall >= 3 else "red")
    console.print(f"\n[bold]Overall Score:[/bold] [{color}]{overall}/5[/{color}]")


# ── Export Classroom command ─────────────────────────────────────────


@app.command("export")
def export_cmd(
    lesson_file: str = typer.Option(..., "--lesson-file", "-l", help="Path to lesson JSON"),
    fmt: str = typer.Option("classroom", "--format", "-f", help="Export format: classroom"),
):
    """Export a lesson plan (e.g., to Google Classroom JSON)."""
    path = Path(lesson_file).expanduser().resolve()
    if not path.exists():
        console.print(f"[red]File not found:[/red] {path}")
        raise typer.Exit(1)

    data = json.loads(path.read_text())

    if fmt == "classroom":
        description_parts = [data.get("objective", "")]
        if data.get("standards"):
            description_parts.append(f"Standards: {', '.join(data['standards'])}")
        if data.get("homework"):
            description_parts.append(f"Homework: {data['homework']}")

        coursework = {
            "title": data.get("title", "Lesson"),
            "description": "\n\n".join(description_parts),
            "materials": [],
            "maxPoints": 100,
            "workType": "ASSIGNMENT",
            "state": "DRAFT",
            "submissionModificationMode": "MODIFIABLE_UNTIL_TURNED_IN",
        }

        output = json.dumps(coursework, indent=2)
        console.print(Panel(output, title="Google Classroom CourseWork JSON"))

        out_path = path.with_suffix(".classroom.json")
        out_path.write_text(output)
        console.print(f"[green]Saved:[/green] {out_path}")
    else:
        console.print(f"[red]Unsupported format: {fmt}[/red]")
        raise typer.Exit(1)


# ── Course command ───────────────────────────────────────────────────


@app.command()
def course(
    subject: str = typer.Option(..., "--subject", "-s", help="Subject area"),
    grade: str = typer.Option(..., "--grade", "-g", help="Grade level"),
    topics_file: str = typer.Option(..., "--topics-file", "-t", help="Path to a text file with one topic per line"),
    weeks_per_topic: int = typer.Option(2, "--weeks", "-w", help="Weeks per topic"),
    fmt: str = typer.Option("markdown", "--format", "-f", help="Export format"),
):
    """Generate a full course — one unit per topic from a pacing guide."""
    from eduagent.exporter import export_unit
    from eduagent.planner import plan_unit, save_unit

    persona = _load_persona_or_exit()

    path = Path(topics_file).expanduser().resolve()
    if not path.exists():
        console.print(f"[red]File not found:[/red] {path}")
        raise typer.Exit(1)

    topics = [line.strip() for line in path.read_text().splitlines() if line.strip()]
    if not topics:
        console.print("[red]No topics found in file.[/red]")
        raise typer.Exit(1)

    console.print(Panel(
        f"[bold]{subject} — Grade {grade}[/bold]\n"
        f"{len(topics)} topics, {weeks_per_topic} weeks each",
        title="Course Generation",
    ))

    out_dir = _output_dir() / "course"
    units = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Generating course...", total=len(topics))
        for i, topic in enumerate(topics, 1):
            progress.update(task, description=f"Unit {i}/{len(topics)}: {topic}")
            try:
                unit_plan = _run_async(plan_unit(
                    subject=subject,
                    grade_level=grade,
                    topic=topic,
                    duration_weeks=weeks_per_topic,
                    persona=persona,
                ))
                save_unit(unit_plan, out_dir)
                export_unit(unit_plan, out_dir, fmt=fmt)
                units.append(unit_plan)
            except Exception as e:
                console.print(f"[red]Failed: {topic} — {e}[/red]")
            progress.advance(task)

    # Summary table
    table = Table(title="Course Map")
    table.add_column("#", style="dim")
    table.add_column("Unit", style="bold")
    table.add_column("Lessons", justify="center")
    for i, u in enumerate(units, 1):
        table.add_row(str(i), u.title, str(len(u.daily_lessons)))
    console.print(table)
    console.print(f"\n[green]Course saved:[/green] {out_dir}")


# ── Templates commands ───────────────────────────────────────────────


@templates_app.command("list")
def templates_list():
    """List all available lesson structure templates."""
    from eduagent.templates_lib import list_templates

    all_templates = list_templates()

    table = Table(title="Lesson Structure Templates")
    table.add_column("Name", style="bold")
    table.add_column("Slug", style="cyan")
    table.add_column("Description")
    table.add_column("Best For", style="dim")
    for t in all_templates:
        table.add_row(t.name, t.slug, t.description[:80] + "..." if len(t.description) > 80 else t.description, t.best_for[:60] if t.best_for else "")
    console.print(table)


# ── Skills commands ─────────────────────────────────────────────────


@skills_app.command("list")
def skills_list():
    """List all available subject pedagogy skills."""
    from eduagent.skills import SkillLibrary

    lib = SkillLibrary()
    all_skills = lib.list_skills()

    table = Table(title="Subject Pedagogy Skills")
    table.add_column("Subject", style="bold")
    table.add_column("Display Name", style="cyan")
    table.add_column("Description")
    table.add_column("Aliases", style="dim")
    for s in all_skills:
        aliases = ", ".join(s.aliases[:4])
        if len(s.aliases) > 4:
            aliases += f" (+{len(s.aliases) - 4})"
        desc = s.description[:80] + "..." if len(s.description) > 80 else s.description
        table.add_row(s.subject, s.display_name, desc, aliases)
    console.print(table)


@skills_app.command("show")
def skills_show(
    subject: str = typer.Argument(help="Subject name or alias (e.g., 'math', 'biology', 'ela')."),
):
    """Show detailed pedagogy skill for a subject."""
    from eduagent.skills import SkillLibrary

    lib = SkillLibrary()
    skill = lib.get(subject)
    if skill is None:
        console.print(f"[red]No skill found for '{subject}'.[/red]")
        console.print(f"Available: {', '.join(lib.subjects())}")
        raise typer.Exit(1)

    console.print(Panel(skill.to_system_context(), title=f"[bold]{skill.display_name}[/bold] Pedagogy Skill", border_style="cyan"))

    if skill.example_strategies:
        table = Table(title="Example Strategies")
        table.add_column("Strategy", style="bold")
        table.add_column("Description")
        for name, desc in skill.example_strategies.items():
            table.add_row(name, desc)
        console.print(table)


# ── School commands ─────────────────────────────────────────────────


@school_app.command("setup")
def school_setup(
    name: str = typer.Option(..., "--name", help="School name"),
    state: str = typer.Option("", "--state", help="State abbreviation (e.g., NY, CA)"),
    district: str = typer.Option("", "--district", help="School district"),
    grade_levels: str = typer.Option("", "--grades", help="Comma-separated grade levels (e.g., '6,7,8')"),
) -> None:
    """Create a new school deployment for multi-teacher sharing."""
    from eduagent.database import Database
    from eduagent.school import setup_school

    db = Database()
    grades = [g.strip() for g in grade_levels.split(",") if g.strip()] if grade_levels else []
    school_id = setup_school(db, name=name, state=state, district=district, grade_levels=grades)
    db.close()

    console.print(Panel(
        f"[bold green]School created![/bold green]\n\n"
        f"  Name:      {name}\n"
        f"  State:     {state or '—'}\n"
        f"  District:  {district or '—'}\n"
        f"  Grades:    {', '.join(grades) or '—'}\n"
        f"  School ID: [cyan]{school_id}[/cyan]\n\n"
        f"Share this ID with teachers: [bold]eduagent school join --school-id {school_id}[/bold]",
        title="[bold]School Setup[/bold]",
        border_style="green",
    ))


@school_app.command("join")
def school_join(
    school_id: str = typer.Option(..., "--school-id", help="School ID to join"),
    teacher_id: str = typer.Option("local-teacher", "--teacher-id", help="Teacher ID"),
    department: str = typer.Option("", "--department", help="Department (e.g., 'Science', 'Math')"),
    role: str = typer.Option("teacher", "--role", help="Role: teacher or admin"),
) -> None:
    """Join a school as a teacher or admin."""
    from eduagent.database import Database
    from eduagent.school import add_teacher

    db = Database()
    school = db.get_school(school_id)
    if not school:
        console.print(f"[red]School '{school_id}' not found.[/red]")
        db.close()
        raise typer.Exit(1)

    add_teacher(db, school_id, teacher_id, role=role, department=department)
    db.close()

    console.print(f"[green]Joined [bold]{school['name']}[/bold] as {role}.[/green]")
    if department:
        console.print(f"  Department: {department}")


@school_app.command("roster")
def school_roster(
    school_id: str = typer.Option(..., "--school-id", help="School ID"),
) -> None:
    """Show all teachers in a school."""
    from eduagent.database import Database
    from eduagent.school import list_teachers

    db = Database()
    school = db.get_school(school_id)
    if not school:
        console.print(f"[red]School '{school_id}' not found.[/red]")
        db.close()
        raise typer.Exit(1)

    teachers = list_teachers(db, school_id)
    db.close()

    table = Table(title=f"Roster — {school['name']}")
    table.add_column("Teacher ID", style="cyan")
    table.add_column("Name", style="bold")
    table.add_column("Role")
    table.add_column("Department")
    for t in teachers:
        table.add_row(t["teacher_id"], t.get("teacher_name") or "—", t["role"], t.get("department") or "—")
    console.print(table)


@school_app.command("share")
def school_share(
    school_id: str = typer.Option(..., "--school-id", help="School ID"),
    teacher_id: str = typer.Option("local-teacher", "--teacher-id", help="Your teacher ID"),
    unit_id: str = typer.Option(None, "--unit-id", help="Unit ID to share"),
    lesson_id: str = typer.Option(None, "--lesson-id", help="Lesson ID to share"),
    department: str = typer.Option("", "--department", help="Share with a specific department"),
) -> None:
    """Share a unit or lesson with your school's curriculum library."""
    from eduagent.database import Database
    from eduagent.school import share_lesson, share_unit

    if not unit_id and not lesson_id:
        console.print("[red]Provide --unit-id or --lesson-id to share.[/red]")
        raise typer.Exit(1)

    db = Database()
    if unit_id:
        sid = share_unit(db, school_id, teacher_id, unit_id, department=department)
        label = "Unit"
    else:
        sid = share_lesson(db, school_id, teacher_id, lesson_id, department=department)  # type: ignore[arg-type]
        label = "Lesson"
    db.close()

    if sid:
        dept_msg = f" with department '{department}'" if department else " with the whole school"
        console.print(f"[green]{label} shared{dept_msg}.[/green]  Shared ID: [cyan]{sid}[/cyan]")
    else:
        console.print(f"[red]{label} not found.[/red]")
        raise typer.Exit(1)


@school_app.command("library")
def school_library(
    school_id: str = typer.Option(..., "--school-id", help="School ID"),
    department: str = typer.Option("", "--department", help="Filter by department"),
) -> None:
    """Browse your school's shared curriculum library."""
    from eduagent.database import Database
    from eduagent.school import get_shared_library

    db = Database()
    school = db.get_school(school_id)
    if not school:
        console.print(f"[red]School '{school_id}' not found.[/red]")
        db.close()
        raise typer.Exit(1)

    items = get_shared_library(db, school_id, department=department)
    db.close()

    title = f"Shared Library — {school['name']}"
    if department:
        title += f" ({department})"
    table = Table(title=title)
    table.add_column("Type", style="bold")
    table.add_column("Title")
    table.add_column("Subject")
    table.add_column("Grade")
    table.add_column("Shared By")
    table.add_column("Rating", justify="right")
    for item in items:
        rating_str = str(item["rating"]) if item.get("rating") else "—"
        table.add_row(
            item["content_type"],
            item["title"],
            item.get("subject") or "—",
            item.get("grade_level") or "—",
            item.get("teacher_name") or "—",
            rating_str,
        )
    console.print(table)
    if not items:
        console.print("[dim]No shared content yet. Use 'eduagent school share' to contribute![/dim]")


@app.command()
def stats(
    teacher_id: str = typer.Option("local-teacher", "--teacher", "-t", help="Teacher ID"),
):
    """Show a beautiful stats dashboard with rating trends and analytics.

    Displays lesson ratings, top topics, streaks, and areas for improvement.
    """
    from eduagent.analytics import get_teacher_stats

    data = get_teacher_stats(teacher_id)

    # Header
    console.print()
    console.print(Panel(
        "[bold]EDUagent Teaching Analytics[/bold]",
        border_style="blue",
    ))

    # Overview stats
    overview = Table(show_header=False, box=None, padding=(0, 2))
    overview.add_column("label", style="dim")
    overview.add_column("value", style="bold")
    overview.add_row("Total lessons", str(data["total_lessons"]))
    overview.add_row("Rated lessons", str(data["rated_lessons"]))
    overview.add_row("Total units", str(data["total_units"]))
    avg = data["overall_avg_rating"]
    stars = "★" * round(avg) + "☆" * (5 - round(avg)) if avg else "No ratings yet"
    overview.add_row("Average rating", f"{stars} ({avg}/5)" if avg else stars)
    overview.add_row("Usage streak", f"{data['streak']} day{'s' if data['streak'] != 1 else ''}")
    console.print(Panel(overview, title="[blue]Overview[/blue]", border_style="blue"))

    # Rating distribution
    dist = data["rating_distribution"]
    if any(dist.values()):
        dist_table = Table(show_header=True, title="Rating Distribution")
        dist_table.add_column("Stars", style="yellow")
        dist_table.add_column("Count", justify="right")
        dist_table.add_column("Bar")
        max_count = max(dist.values()) or 1
        for star in range(5, 0, -1):
            count = dist.get(star, 0)
            bar_len = int((count / max_count) * 20) if max_count else 0
            bar = "█" * bar_len
            dist_table.add_row(f"{'★' * star}", str(count), f"[green]{bar}[/green]")
        console.print(dist_table)

    # Ratings by subject
    by_subject = data["by_subject"]
    if by_subject:
        subj_table = Table(show_header=True, title="Ratings by Subject")
        subj_table.add_column("Subject")
        subj_table.add_column("Avg Rating", justify="right")
        for subj, avg_r in sorted(by_subject.items(), key=lambda x: x[1], reverse=True):
            color = "green" if avg_r >= 4 else "yellow" if avg_r >= 3 else "red"
            subj_table.add_row(subj, f"[{color}]{avg_r}/5[/{color}]")
        console.print(subj_table)

    # Top topics
    top = data["top_topics"]
    if top:
        top_table = Table(show_header=True, title="Most Effective Topics")
        top_table.add_column("Topic")
        top_table.add_column("Avg Rating", justify="right")
        top_table.add_column("Lessons", justify="right")
        for t in top:
            color = "green" if t["avg_rating"] >= 4 else "yellow" if t["avg_rating"] >= 3 else "red"
            top_table.add_row(t["topic"], f"[{color}]{t['avg_rating']}/5[/{color}]", str(t["count"]))
        console.print(top_table)

    # Needs improvement
    needs = data["needs_improvement"]
    if needs:
        needs_table = Table(show_header=True, title="[red]Needs Improvement[/red]")
        needs_table.add_column("Lesson")
        needs_table.add_column("Rating", justify="right")
        needs_table.add_column("Date")
        for n in needs[:10]:
            needs_table.add_row(
                n["title"] or "Untitled",
                f"[red]{n['rating']}/5[/red]",
                (n.get("created_at") or "")[:10],
            )
        console.print(needs_table)

    if not data["rated_lessons"]:
        console.print(
            "\n[dim]No ratings yet. Generate a lesson with 'eduagent chat' and rate it to see analytics here.[/dim]"
        )
    console.print()


@app.command()
def bot(
    token: Optional[str] = typer.Option(None, "--token", "-t", envvar="TELEGRAM_BOT_TOKEN", help="Telegram bot token from @BotFather"),
    data_dir: Optional[str] = typer.Option(None, "--data-dir", help="Data directory (default: ~/.eduagent)"),
    live: bool = typer.Option(False, "--live", help="Show a Rich live status display while running"),
):
    """Start the EDUagent Telegram bot.

    \b
    Get a bot token from @BotFather on Telegram, then run:
        eduagent bot --token YOUR_TOKEN
        eduagent bot --token YOUR_TOKEN --live   # with live status display

    Or save it once and forget about it:
        eduagent config set-token YOUR_TOKEN
        eduagent bot
    """
    import asyncio

    from eduagent.telegram_bot import run_bot

    # Resolve token: --token flag > TELEGRAM_BOT_TOKEN env > saved config
    if not token:
        cfg = AppConfig.load()
        token = cfg.telegram_bot_token
    if not token:
        console.print(
            "[red]No bot token found.[/red]\n\n"
            "Provide one of:\n"
            "  1. [cyan]eduagent bot --token YOUR_TOKEN[/cyan]\n"
            "  2. [cyan]export TELEGRAM_BOT_TOKEN=YOUR_TOKEN[/cyan]\n"
            "  3. [cyan]eduagent config set-token YOUR_TOKEN[/cyan]  (saves permanently)\n\n"
            "Get a token from @BotFather on Telegram."
        )
        raise typer.Exit(1)

    data_path = Path(data_dir).expanduser().resolve() if data_dir else None

    if live:
        _bot_with_live_display(token=token, data_path=data_path)
    else:
        console.print(Panel(
            f"[bold green]EDUagent Telegram Bot[/bold green]\n\n"
            f"Starting bot...\n"
            f"Data directory: {data_path or Path.home() / '.eduagent'}\n\n"
            f"[dim]Press Ctrl+C to stop[/dim]",
            title="\U0001f393 EDUagent",
            border_style="green",
        ))

        try:
            asyncio.run(run_bot(token=token, data_dir=data_path))
        except KeyboardInterrupt:
            console.print("\n[yellow]Bot stopped.[/yellow]")
        except ImportError as e:
            console.print(f"[red]Missing dependency:[/red] {e}")
            console.print("\nInstall Telegram support with:")
            console.print("  [cyan]pip install 'python-telegram-bot>=20.0'[/cyan]")
            raise typer.Exit(1)


def _bot_with_live_display(token: str, data_path: Optional[Path] = None) -> None:
    """Run the Telegram bot with a Rich Live status panel."""
    import asyncio
    import time

    from rich.live import Live

    from eduagent.gateway import EduAgentGateway

    gateway = EduAgentGateway(token=token)
    start_time = time.monotonic()

    def _make_display() -> Panel:
        elapsed = int(time.monotonic() - start_time)
        h, remainder = divmod(elapsed, 3600)
        m, s = divmod(remainder, 60)
        stats = gateway._gateway_stats
        sessions = len(gateway.active_sessions)
        return Panel(
            f"[bold green]EDUagent Bot[/bold green]  [dim]running[/dim]\n\n"
            f"  Messages:     {stats.messages_today}\n"
            f"  Generations:  {stats.generations_today}\n"
            f"  Errors:       {stats.errors_today}\n"
            f"  Sessions:     {sessions}\n"
            f"  Uptime:       {h}:{m:02d}:{s:02d}\n\n"
            f"[dim]Press Ctrl+C to stop[/dim]",
            title="\U0001f393 EDUagent",
            border_style="green",
        )

    async def _run() -> None:
        await gateway.start()
        # Keep alive — gateway.start() returns after setup, polling runs in background
        while True:
            await asyncio.sleep(60)

    try:
        with Live(_make_display(), console=console, refresh_per_second=1) as live_display:

            async def _run_with_refresh() -> None:
                await gateway.start()
                while True:
                    live_display.update(_make_display())
                    await asyncio.sleep(1)

            asyncio.run(_run_with_refresh())
    except KeyboardInterrupt:
        console.print("\n[yellow]Bot stopped.[/yellow]")


if __name__ == "__main__":
    app()
