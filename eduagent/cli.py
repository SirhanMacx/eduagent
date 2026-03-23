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
from rich.progress import Progress, SpinnerColumn, TextColumn
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
):
    """Ingest teaching materials and extract a teacher persona."""
    from eduagent.ingestor import ingest_path
    from eduagent.persona import extract_persona, save_persona

    source = Path(path).expanduser().resolve()
    console.print(Panel(f"Ingesting materials from [bold]{source}[/bold]", title="EDUagent"))

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


@config_app.command("show")
def config_show():
    """Show current configuration."""
    cfg = AppConfig.load()
    console.print(Panel(
        f"[bold]Provider:[/bold] {cfg.provider.value}\n"
        f"[bold]Anthropic Model:[/bold] {cfg.anthropic_model}\n"
        f"[bold]OpenAI Model:[/bold] {cfg.openai_model}\n"
        f"[bold]Ollama Model:[/bold] {cfg.ollama_model}\n"
        f"[bold]Ollama URL:[/bold] {cfg.ollama_base_url}\n"
        f"[bold]Output Dir:[/bold] {cfg.output_dir}\n"
        f"[bold]Export Format:[/bold] {cfg.export_format}\n"
        f"[bold]Include Homework:[/bold] {cfg.include_homework}",
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
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload for development"),
    skip_setup: bool = typer.Option(False, "--skip-setup", help="Skip first-run setup wizard"),
):
    """Start the EDUagent web server."""
    import uvicorn

    if not skip_setup:
        _first_run_setup()

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


if __name__ == "__main__":
    app()
