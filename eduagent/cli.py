"""Rich CLI for EDUagent — beautiful terminal interface with typer."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

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
app.add_typer(config_app, name="config")
app.add_typer(persona_app, name="persona")


def _output_dir() -> Path:
    cfg = AppConfig.load()
    return Path(cfg.output_dir).expanduser().resolve()


def _run_async(coro):
    """Run an async coroutine from synchronous CLI code."""
    return asyncio.get_event_loop().run_until_complete(coro)


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


if __name__ == "__main__":
    app()
