"""Generation commands: ingest, unit, lesson, materials, full, course, year-map, pacing,
assess, rubric, differentiate, sub-packet, parent-note, score, improve, transcribe."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.panel import Panel
from rich.table import Table

from eduagent import _safe_filename
from eduagent.commands._helpers import _safe_progress, console, load_persona_or_exit
from eduagent.commands._helpers import output_dir as _output_dir
from eduagent.commands._helpers import run_async as _run_async
from eduagent.models import AppConfig

generate_app = typer.Typer()


# ── Ingest command ───────────────────────────────────────────────────────


@generate_app.command()
def ingest(
    path: str = typer.Argument(
        ..., help="Path to directory, ZIP file, or single file to ingest"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be processed without actually processing"
    ),
):
    """Ingest teaching materials and extract a teacher persona."""
    from eduagent.ingestor import ingest_path, scan_directory

    source = Path(path).expanduser().resolve()

    if dry_run:
        console.print(
            Panel(
                f"[yellow]DRY RUN[/yellow] — scanning [bold]{source}[/bold]",
                title="EDUagent",
            )
        )

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
            table.add_row(
                str(i), doc.title, doc.doc_type.value.upper(), doc.source_path or ""
            )
        console.print(table)
        console.print(f"\n[green]{len(documents)} files would be processed.[/green]")
        return

    console.print(
        Panel(f"Ingesting materials from [bold]{source}[/bold]", title="EDUagent")
    )

    # Show format summary for directories
    if source.is_dir():
        files, summary = scan_directory(source)
        console.print(f"\n[cyan]{summary}[/cyan]\n")
        file_count = len(files)
    else:
        file_count = 1

    # Use progress bar for large directories (>20 files), spinner otherwise
    if file_count > 20:
        with _safe_progress(console=console) as progress:
            task = progress.add_task("Ingesting files...", total=file_count)

            def _update_progress(current: int, total: int) -> None:
                progress.update(task, completed=current)

            documents = ingest_path(source, progress_callback=_update_progress)
            progress.update(
                task,
                description=f"Done — {len(documents)} documents extracted",
            )
    else:
        with _safe_progress(console=console) as progress:
            task = progress.add_task("Scanning files...", total=None)
            documents = ingest_path(source)
            progress.update(
                task, description=f"Found {len(documents)} documents"
            )

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

    with _safe_progress(console=console) as progress:
        task = progress.add_task("Analyzing teaching style...", total=None)
        persona = _run_async(extract_persona(documents))
        progress.update(task, description="Persona extracted!")

    out = save_persona(persona, _output_dir())
    console.print(
        Panel(
            f"[green]Persona saved to {out}[/green]\n\n"
            f"[bold]Style:[/bold] {persona.teaching_style.value.replace('_', ' ').title()}\n"
            f"[bold]Tone:[/bold] {persona.tone}\n"
            f"[bold]Subject:[/bold] {persona.subject_area}\n"
            f"[bold]Format:[/bold] {persona.preferred_lesson_format}",
            title="Teacher Persona",
        )
    )


# ── Transcribe command ───────────────────────────────────────────────────


@generate_app.command()
def transcribe(
    audio_file: str = typer.Argument(
        ..., help="Path to audio file (ogg/wav/mp3/m4a)"
    ),
) -> None:
    """Transcribe a voice note to text using Whisper."""
    from eduagent.voice import is_audio_file, transcribe_audio

    source = Path(audio_file).expanduser().resolve()
    if not source.exists():
        console.print(f"[red]File not found:[/red] {source}")
        raise typer.Exit(1)

    if not is_audio_file(source):
        console.print(f"[red]Unsupported format:[/red] {source.suffix}")
        console.print(
            "[dim]Supported: ogg, wav, mp3, m4a, flac, webm, opus[/dim]"
        )
        raise typer.Exit(1)

    with _safe_progress(console=console) as progress:
        progress.add_task("Transcribing audio...", total=None)
        try:
            text = _run_async(transcribe_audio(source))
        except RuntimeError as e:
            console.print(f"[red]{e}[/red]")
            raise typer.Exit(1) from e

    console.print(
        Panel(
            text,
            title="[bold green]Transcription[/bold green]",
            border_style="green",
        )
    )


# ── Unit planning ────────────────────────────────────────────────────────


@generate_app.command()
def unit(
    topic: str = typer.Argument(..., help="Unit topic (e.g., 'Photosynthesis')"),
    grade: str = typer.Option("8", "--grade", "-g", help="Grade level"),
    subject: str = typer.Option("Science", "--subject", "-s", help="Subject area"),
    weeks: int = typer.Option(3, "--weeks", "-w", help="Duration in weeks"),
    standards: Optional[str] = typer.Option(
        None, "--standards", help="Comma-separated standards"
    ),
    fmt: str = typer.Option(
        "markdown", "--format", "-f", help="Export format: markdown, pdf, docx"
    ),
):
    """Plan a complete curriculum unit."""
    from eduagent.exporter import export_unit
    from eduagent.planner import plan_unit, save_unit

    persona = load_persona_or_exit()
    std_list = [s.strip() for s in standards.split(",")] if standards else None

    console.print(
        Panel(
            f"[bold]{topic}[/bold] | Grade {grade} {subject} | {weeks} weeks",
            title="Planning Unit",
        )
    )

    with _safe_progress(console=console) as progress:
        task = progress.add_task("Generating unit plan...", total=None)
        unit_plan = _run_async(
            plan_unit(
                subject=subject,
                grade_level=grade,
                topic=topic,
                duration_weeks=weeks,
                persona=persona,
                standards=std_list,
            )
        )
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


@generate_app.command(name="year-map")
def year_map(
    subject: str = typer.Argument(..., help="Subject area (e.g., 'Math')"),
    grade: str = typer.Option("8", "--grade", "-g", help="Grade level"),
    standards: Optional[str] = typer.Option(
        None, "--standards", help="Comma-separated standards"
    ),
    weeks: int = typer.Option(
        36, "--weeks", "-w", help="Total instructional weeks"
    ),
    school_year: str = typer.Option(
        "", "--school-year", help="School year label (e.g., '2025-26')"
    ),
    fmt: str = typer.Option(
        "markdown", "--format", "-f", help="Export format: markdown, pdf, docx"
    ),
):
    """Generate a full-year curriculum map with unit sequence, big ideas, and assessment calendar."""
    from eduagent.curriculum_map import CurriculumMapper, save_year_map
    from eduagent.exporter import export_year_map

    persona = load_persona_or_exit()
    std_list = [s.strip() for s in standards.split(",")] if standards else None

    console.print(
        Panel(
            f"[bold]{subject}[/bold] | Grade {grade} | {weeks} instructional weeks",
            title="Planning Year Map",
        )
    )

    with _safe_progress(console=console) as progress:
        task = progress.add_task(
            "Generating full-year curriculum map...", total=None
        )
        mapper = CurriculumMapper()
        result = _run_async(
            mapper.generate_year_map(
                subject=subject,
                grade_level=grade,
                standards=std_list,
                persona=persona,
                school_year=school_year,
                total_weeks=weeks,
            )
        )
        progress.update(task, description="Year map complete!")

    out_dir = _output_dir()
    json_path = save_year_map(result, out_dir)
    export_path = export_year_map(result, out_dir, fmt=fmt)

    console.print(f"\n[green]Year map saved:[/green] {json_path}")
    console.print(f"[green]Exported:[/green] {export_path}")

    # Summary table
    table = Table(
        title=f"Year Map — {result.subject}, Grade {result.grade_level}"
    )
    table.add_column("#", style="dim")
    table.add_column("Unit", style="bold")
    table.add_column("Weeks", justify="right")
    table.add_column("Essential Questions")
    for u in result.units:
        eq_preview = (
            u.essential_questions[0][:60] + "..."
            if u.essential_questions
            else "—"
        )
        table.add_row(
            str(u.unit_number), u.title, str(u.duration_weeks), eq_preview
        )
    console.print(table)

    if result.big_ideas:
        console.print("\n[bold]Big Ideas:[/bold]")
        for bi in result.big_ideas:
            units_str = ", ".join(str(n) for n in bi.connected_units)
            console.print(f"  * {bi.idea} [dim](Units {units_str})[/dim]")


@generate_app.command()
def pacing(
    year_map_file: str = typer.Option(
        ..., "--year-map", "-y", help="Path to year map JSON"
    ),
    start_date: str = typer.Option(
        ..., "--start-date", "-d", help="First instructional day (YYYY-MM-DD)"
    ),
    calendar_file: Optional[str] = typer.Option(
        None, "--calendar", "-c", help="School calendar JSON file"
    ),
    fmt: str = typer.Option(
        "markdown", "--format", "-f", help="Export format: markdown, pdf, docx"
    ),
):
    """Generate a week-by-week pacing guide from a year map."""
    from eduagent.curriculum_map import (
        CurriculumMapper,
        load_year_map,
        save_pacing_guide,
    )
    from eduagent.exporter import export_pacing_guide
    from eduagent.models import SchoolCalendarEvent

    persona = load_persona_or_exit()
    ym = load_year_map(Path(year_map_file))

    # Load school calendar if provided
    school_cal: list[SchoolCalendarEvent] | None = None
    if calendar_file:
        cal_path = Path(calendar_file)
        if cal_path.exists():
            import json as _json

            cal_data = _json.loads(cal_path.read_text(encoding="utf-8"))
            school_cal = [
                SchoolCalendarEvent.model_validate(e) for e in cal_data
            ]

    console.print(
        Panel(
            f"[bold]{ym.subject}[/bold] Grade {ym.grade_level}"
            f" | Starting {start_date}",
            title="Generating Pacing Guide",
        )
    )

    with _safe_progress(console=console) as progress:
        task = progress.add_task(
            "Creating week-by-week pacing guide...", total=None
        )
        mapper = CurriculumMapper()
        guide = _run_async(
            mapper.generate_pacing_guide(
                year_map=ym,
                start_date=start_date,
                school_calendar=school_cal,
                persona=persona,
            )
        )
        progress.update(task, description="Pacing guide complete!")

    out_dir = _output_dir()
    json_path = save_pacing_guide(guide, out_dir)
    export_path = export_pacing_guide(guide, out_dir, fmt=fmt)

    console.print(f"\n[green]Pacing guide saved:[/green] {json_path}")
    console.print(f"[green]Exported:[/green] {export_path}")

    # Summary table
    table = Table(
        title=f"Pacing Guide — {guide.subject}, Grade {guide.grade_level}"
    )
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
        console.print(
            f"[dim]  ... and {len(guide.weeks) - 10} more weeks"
            " (see exported file)[/dim]"
        )


# ── Lesson generation ────────────────────────────────────────────────────


@generate_app.command()
def lesson(
    topic: str = typer.Argument(..., help="Lesson topic (e.g. 'The American Revolution')"),
    unit_file: Optional[str] = typer.Option(
        None, "--unit-file", "-u", help="Path to unit plan JSON (omit for standalone lesson)"
    ),
    lesson_num: int = typer.Option(
        1, "--lesson-num", "-n", help="Lesson number in unit"
    ),
    grade: str = typer.Option(
        "8", "--grade", "-g", help="Grade level (for standalone lesson)"
    ),
    subject: str = typer.Option(
        "Social Studies", "--subject", "-s", help="Subject area (for standalone lesson)"
    ),
    homework: bool = typer.Option(
        True, "--homework/--no-homework", help="Include homework"
    ),
    fmt: str = typer.Option("markdown", "--format", "-f", help="Export format: markdown, pptx, docx, pdf"),
):
    """Generate a detailed daily lesson plan.

    \b
    Standalone mode (no unit plan needed):
        eduagent lesson "The American Revolution" --grade 8 --subject "social studies"

    From a unit plan:
        eduagent lesson "Photosynthesis" --unit-file output/unit_photosynthesis.json -n 1
    """
    from eduagent.exporter import export_lesson
    from eduagent.lesson import generate_lesson, save_lesson

    persona = load_persona_or_exit()

    if unit_file:
        from eduagent.planner import load_unit
        unit_plan = load_unit(Path(unit_file))
    else:
        # Standalone mode: create a minimal unit plan from the topic
        from eduagent.models import LessonBrief, UnitPlan
        unit_plan = UnitPlan(
            title=f"{topic} Lesson",
            subject=subject,
            grade_level=grade,
            topic=topic,
            duration_weeks=1,
            overview=f"A standalone lesson on {topic} for grade {grade} {subject}.",
            essential_questions=[f"What are the key concepts of {topic}?"],
            daily_lessons=[
                LessonBrief(
                    lesson_number=1,
                    topic=topic,
                    description=f"Explore the key concepts, events, and significance of {topic}.",
                    lesson_type="direct_instruction",
                )
            ],
        )
        lesson_num = 1

    with _safe_progress(console=console) as progress:
        task = progress.add_task(
            f"Generating lesson {lesson_num}...", total=None
        )
        daily = _run_async(
            generate_lesson(
                lesson_number=lesson_num,
                unit=unit_plan,
                persona=persona,
                include_homework=homework,
            )
        )
        progress.update(task, description="Lesson plan complete!")

    out_dir = _output_dir()
    json_path = save_lesson(daily, out_dir)

    # For doc formats (pptx/docx/pdf), use doc_export directly;
    # export_lesson only handles markdown/pdf/docx natively.
    export_path = None
    if fmt in ("pptx", "docx", "pdf"):
        try:
            from eduagent.doc_export import export_lesson_docx, export_lesson_pdf, export_lesson_pptx
            if fmt == "pptx":
                doc_path = export_lesson_pptx(daily, persona, out_dir)
            elif fmt == "docx":
                doc_path = export_lesson_docx(daily, persona, out_dir)
            else:
                doc_path = export_lesson_pdf(daily, persona, out_dir)
            export_path = doc_path
            console.print(f"[green]Document exported:[/green] {doc_path}")
        except Exception as e:
            console.print(f"[yellow]Document export failed: {e}[/yellow]")
            # Fall back to markdown
            export_path = export_lesson(daily, out_dir, fmt="markdown")
    else:
        export_path = export_lesson(daily, out_dir, fmt=fmt)

    console.print(f"\n[green]Lesson saved:[/green] {json_path}")
    if export_path:
        console.print(f"[green]Exported:[/green] {export_path}")
    console.print(
        Panel(
            f"[bold]Objective:[/bold] {daily.objective}\n"
            f"[bold]Standards:[/bold] {', '.join(daily.standards)}",
            title=f"Lesson {daily.lesson_number}: {daily.title}",
        )
    )


# ── Materials generation ─────────────────────────────────────────────────


@generate_app.command()
def materials(
    lesson_file: str = typer.Option(
        ..., "--lesson-file", "-l", help="Path to lesson plan JSON"
    ),
    fmt: str = typer.Option("markdown", "--format", "-f", help="Export format"),
):
    """Generate all supporting materials for a lesson."""
    from eduagent.exporter import export_materials
    from eduagent.lesson import load_lesson
    from eduagent.materials import generate_all_materials, save_materials

    persona = load_persona_or_exit()
    daily = load_lesson(Path(lesson_file))

    with _safe_progress(console=console) as progress:
        task = progress.add_task("Generating worksheet...", total=4)
        mats = _run_async(generate_all_materials(daily, persona))
        progress.update(
            task, completed=4, description="All materials generated!"
        )

    out_dir = _output_dir()
    json_path = save_materials(mats, out_dir)
    export_path = export_materials(mats, out_dir, fmt=fmt)

    console.print(f"\n[green]Materials saved:[/green] {json_path}")
    console.print(f"[green]Exported:[/green] {export_path}")
    console.print(
        Panel(
            f"[bold]Worksheet:[/bold] {len(mats.worksheet_items)} items\n"
            f"[bold]Assessment:[/bold] {len(mats.assessment_questions)} questions\n"
            f"[bold]Rubric:[/bold] {len(mats.rubric)} criteria\n"
            f"[bold]Slides:[/bold] {len(mats.slide_outline)} slides\n"
            f"[bold]IEP Notes:[/bold] {len(mats.iep_notes)} accommodations",
            title="Materials Summary",
        )
    )


# ── Assessment intelligence ──────────────────────────────────────────────


@generate_app.command()
def assess(
    type: str = typer.Option(
        "quiz",
        "--type",
        "-t",
        help="Assessment type: formative, summative, dbq, quiz",
    ),
    topic: str = typer.Option("", "--topic", help="Topic for quiz or DBQ"),
    grade: str = typer.Option("8", "--grade", "-g", help="Grade level"),
    questions: int = typer.Option(
        10, "--questions", "-q", help="Number of questions (quiz only)"
    ),
    question_types: str = typer.Option(
        "mixed",
        "--question-types",
        help="Question types: mixed, multiple_choice, short_answer",
    ),
    lesson_file: Optional[str] = typer.Option(
        None,
        "--lesson-file",
        "-l",
        help="Lesson JSON for formative assessment",
    ),
    unit_file: Optional[str] = typer.Option(
        None,
        "--unit-file",
        "-u",
        help="Unit JSON for summative assessment",
    ),
    context: str = typer.Option(
        "", "--context", "-c", help="Additional context (DBQ)"
    ),
):
    """Generate intelligent assessments — DBQ, summative, formative, or quiz."""
    from eduagent.assessment import AssessmentGenerator, save_assessment

    persona = load_persona_or_exit()
    gen = AssessmentGenerator(AppConfig.load())

    out_dir = _output_dir()

    if type == "formative":
        if not lesson_file:
            console.print(
                "[red]--lesson-file required for formative assessment.[/red]"
            )
            raise typer.Exit(1)
        from eduagent.lesson import load_lesson

        daily = load_lesson(Path(lesson_file))
        console.print(
            Panel(
                f"[bold]{daily.title}[/bold]"
                " — exit ticket for today's objective",
                title="Formative Assessment",
            )
        )
        with _safe_progress(console=console) as progress:
            task = progress.add_task(
                "Generating exit ticket...", total=None
            )
            result = _run_async(gen.generate_formative(daily, persona))
            progress.update(task, description="Exit ticket ready!")

        path = save_assessment(result, out_dir, "formative")
        console.print(f"\n[green]Saved:[/green] {path}")
        console.print(
            Panel(
                f"[bold]Objective:[/bold] {result.objective}\n"
                f"[bold]Questions:[/bold] {len(result.questions)}\n"
                f"[bold]Time:[/bold] {result.time_minutes} minutes",
                title="Exit Ticket Summary",
            )
        )

    elif type == "summative":
        if not unit_file:
            console.print(
                "[red]--unit-file required for summative assessment.[/red]"
            )
            raise typer.Exit(1)
        from eduagent.planner import load_unit

        unit_plan = load_unit(Path(unit_file))
        console.print(
            Panel(
                f"[bold]{unit_plan.title}[/bold] — unit test",
                title="Summative Assessment",
            )
        )
        with _safe_progress(console=console) as progress:
            task = progress.add_task(
                "Generating unit test...", total=None
            )
            result = _run_async(gen.generate_summative(unit_plan, persona))
            progress.update(task, description="Unit test ready!")

        path = save_assessment(result, out_dir, "summative")
        console.print(f"\n[green]Saved:[/green] {path}")
        console.print(
            Panel(
                f"[bold]Questions:[/bold] {len(result.questions)}\n"
                f"[bold]Total Points:[/bold] {result.total_points}\n"
                f"[bold]Rubric Criteria:[/bold] {len(result.rubric)}\n"
                f"[bold]Time:[/bold] {result.time_minutes} minutes",
                title="Unit Test Summary",
            )
        )

    elif type == "dbq":
        if not topic:
            console.print(
                "[red]--topic required for DBQ assessment.[/red]"
            )
            raise typer.Exit(1)
        console.print(
            Panel(
                f"[bold]{topic}[/bold]"
                f" — NYS Regents-style DBQ | Grade {grade}",
                title="Document-Based Question",
            )
        )
        with _safe_progress(console=console) as progress:
            task = progress.add_task(
                "Generating DBQ with documents...", total=None
            )
            result = _run_async(
                gen.generate_dbq(
                    topic, persona, grade_level=grade, context=context
                )
            )
            progress.update(task, description="DBQ ready!")

        path = save_assessment(result, out_dir, "dbq")
        console.print(f"\n[green]Saved:[/green] {path}")
        console.print(
            Panel(
                f"[bold]Documents:[/bold] {len(result.documents)}\n"
                f"[bold]Rubric Criteria:[/bold] {len(result.rubric)}\n"
                f"[bold]Model Answer:[/bold]"
                f" {'Yes' if result.model_answer else 'No'}\n"
                f"[bold]Time:[/bold] {result.time_minutes} minutes",
                title="DBQ Summary",
            )
        )

    elif type == "quiz":
        if not topic:
            console.print("[red]--topic required for quiz.[/red]")
            raise typer.Exit(1)
        console.print(
            Panel(
                f"[bold]{topic}[/bold] | Grade {grade}"
                f" | {questions} questions ({question_types})",
                title="Quiz",
            )
        )
        with _safe_progress(console=console) as progress:
            task = progress.add_task("Generating quiz...", total=None)
            result = _run_async(
                gen.generate_quiz(
                    topic=topic,
                    question_count=questions,
                    question_types=question_types,
                    grade=grade,
                    persona=persona,
                )
            )
            progress.update(task, description="Quiz ready!")

        path = save_assessment(result, out_dir, "quiz")
        console.print(f"\n[green]Saved:[/green] {path}")
        console.print(
            Panel(
                f"[bold]Questions:[/bold] {len(result.questions)}\n"
                f"[bold]Total Points:[/bold] {result.total_points}\n"
                f"[bold]Time:[/bold] {result.time_minutes} minutes",
                title="Quiz Summary",
            )
        )

    else:
        console.print(
            f"[red]Unknown assessment type '{type}'."
            " Use: formative, summative, dbq, quiz[/red]"
        )
        raise typer.Exit(1)


@generate_app.command()
def rubric(
    task: str = typer.Option(
        ..., "--task", help="Description of the task to build a rubric for"
    ),
    criteria: int = typer.Option(
        4, "--criteria", "-c", help="Number of rubric criteria"
    ),
    grade: str = typer.Option("", "--grade", "-g", help="Grade level"),
):
    """Generate a detailed scoring rubric for any written task."""
    from eduagent.assessment import AssessmentGenerator, save_assessment

    persona = load_persona_or_exit()
    gen = AssessmentGenerator(AppConfig.load())

    console.print(
        Panel(
            f"[bold]{task}[/bold] | {criteria} criteria",
            title="Rubric Generator",
        )
    )

    with _safe_progress(console=console) as progress:
        prog_task = progress.add_task("Generating rubric...", total=None)
        result = _run_async(
            gen.generate_rubric(
                task, persona, criteria_count=criteria, grade_level=grade
            )
        )
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
        table.add_row(
            c.criterion, c.excellent, c.proficient, c.developing, c.beginning
        )
    console.print(table)
    console.print(f"\n[bold]Total Points:[/bold] {result.total_points}")


# ── Differentiation / IEP ────────────────────────────────────────────────


@generate_app.command()
def differentiate(
    lesson_file: str = typer.Option(
        ..., "--lesson-file", "-l", help="Path to lesson plan JSON"
    ),
    iep: Optional[str] = typer.Option(
        None, "--iep", help="Path to IEP student profiles JSON"
    ),
    accommodations_504: Optional[str] = typer.Option(
        None, "--504", help="Comma-separated 504 accommodations"
    ),
    tiered_topic: Optional[str] = typer.Option(
        None, "--tiered-topic", help="Topic for tiered assignments"
    ),
    tiered_grade: str = typer.Option(
        "8", "--tiered-grade", help="Grade level for tiered assignments"
    ),
    tiers: int = typer.Option(
        3, "--tiers", help="Number of difficulty tiers"
    ),
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
        console.print(
            Panel(
                f"Generating modified lessons for"
                f" [bold]{len(profiles)}[/bold] IEP students",
                title="IEP Modifications",
            )
        )

        with _safe_progress(console=console) as progress:
            task = progress.add_task(
                "Modifying lessons for IEP students...", total=None
            )
            modifications = _run_async(
                generate_iep_lesson_modifications(daily, profiles)
            )
            progress.update(
                task,
                description=(
                    f"Generated {len(modifications)} modified lessons!"
                ),
            )

        paths = save_modified_lessons(modifications, out_dir)
        table = Table(title="IEP Modified Lessons")
        table.add_column("Student", style="bold")
        table.add_column("Modified Title")
        table.add_column("File", style="dim")
        for name, mod_lesson in modifications.items():
            path = next(
                (
                    p
                    for p in paths
                    if _safe_filename(name) in str(p)
                ),
                paths[0],
            )
            table.add_row(name, mod_lesson.title, str(path))
        console.print(table)

    # 504 accommodations
    if accommodations_504:
        ran_any = True
        acc_list = [a.strip() for a in accommodations_504.split(",")]
        console.print(
            Panel(
                f"Generating 504 accommodations: {', '.join(acc_list)}",
                title="504 Accommodations",
            )
        )

        with _safe_progress(console=console) as progress:
            task = progress.add_task(
                "Generating 504 accommodations...", total=None
            )
            notes = _run_async(
                generate_504_accommodations(daily, acc_list)
            )
            progress.update(
                task, description="504 accommodations complete!"
            )

        console.print(
            Panel(
                "\n".join(f"  - {s}" for s in notes.struggling) or "  (none)",
                title="504 Accommodation Notes",
            )
        )

    # Tiered assignments
    if tiered_topic:
        ran_any = True
        console.print(
            Panel(
                f"Generating [bold]{tiers}-tier[/bold]"
                f" assignments for: {tiered_topic}",
                title="Tiered Assignments",
            )
        )

        with _safe_progress(console=console) as progress:
            task = progress.add_task(
                "Generating tiered assignments...", total=None
            )
            items = _run_async(
                generate_tiered_assignments(
                    tiered_topic, tiered_grade, tiers
                )
            )
            progress.update(
                task,
                description=f"Generated {len(items)} tiered items!",
            )

        path = save_tiered_assignments(items, out_dir, tiered_topic)
        table = Table(title="Tiered Assignment Summary")
        table.add_column("Tier", style="bold")
        table.add_column("Items", justify="right")
        for t in range(tiers):
            low = t * 100 + (1 if t == 0 else 0)
            high = (t + 1) * 100
            count = sum(1 for i in items if low <= i.item_number < high)
            labels = ["Approaching", "On-Level", "Advanced"] + [
                f"Tier {t + 1}"
            ]
            table.add_row(labels[min(t, len(labels) - 1)], str(count))
        console.print(table)
        console.print(f"[green]Saved:[/green] {path}")

    if not ran_any:
        console.print(
            "[yellow]Specify at least one option:[/yellow]"
            " --iep, --504, or --tiered-topic\n"
            "Example: eduagent differentiate"
            " --lesson-file lesson.json --iep students.json"
        )
        raise typer.Exit(1)


# ── Full pipeline ────────────────────────────────────────────────────────


@generate_app.command()
def full(
    topic: str = typer.Argument(..., help="Unit topic"),
    grade: str = typer.Option("8", "--grade", "-g", help="Grade level"),
    subject: str = typer.Option(
        "Science", "--subject", "-s", help="Subject area"
    ),
    weeks: int = typer.Option(3, "--weeks", "-w", help="Duration in weeks"),
    standards: Optional[str] = typer.Option(
        None, "--standards", help="Comma-separated standards"
    ),
    homework: bool = typer.Option(
        True, "--homework/--no-homework", help="Include homework"
    ),
    fmt: str = typer.Option("markdown", "--format", "-f", help="Export format"),
    max_lessons: Optional[int] = typer.Option(
        None, "--max-lessons", help="Limit lessons generated"
    ),
):
    """End-to-end generation: unit plan + all lesson plans + all materials."""
    from eduagent.exporter import export_lesson, export_materials, export_unit
    from eduagent.lesson import generate_lesson, save_lesson
    from eduagent.materials import generate_all_materials, save_materials
    from eduagent.planner import plan_unit, save_unit

    persona = load_persona_or_exit()
    std_list = [s.strip() for s in standards.split(",")] if standards else None
    out_dir = _output_dir()

    console.print(
        Panel(
            f"[bold]{topic}[/bold] | Grade {grade} {subject} | {weeks} weeks\n"
            f"Full pipeline: unit plan + lessons + materials",
            title="EDUagent Full Generation",
        )
    )

    # Step 1: Unit plan
    with _safe_progress(console=console) as progress:
        task = progress.add_task("Step 1/3: Planning unit...", total=None)
        unit_plan = _run_async(
            plan_unit(
                subject=subject,
                grade_level=grade,
                topic=topic,
                duration_weeks=weeks,
                persona=persona,
                standards=std_list,
            )
        )
        progress.update(task, description="Unit plan complete!")

    save_unit(unit_plan, out_dir)
    export_unit(unit_plan, out_dir, fmt=fmt)
    console.print(
        f"[green]Unit plan:[/green] {unit_plan.title}"
        f" ({len(unit_plan.daily_lessons)} lessons)"
    )

    # Step 2: Lesson plans
    lesson_briefs = unit_plan.daily_lessons
    if max_lessons:
        lesson_briefs = lesson_briefs[:max_lessons]

    lessons = []
    with _safe_progress(console=console) as progress:
        task = progress.add_task(
            "Step 2/3: Generating lessons...", total=len(lesson_briefs)
        )
        for brief in lesson_briefs:
            progress.update(
                task,
                description=f"Lesson {brief.lesson_number}: {brief.topic}",
            )
            daily = _run_async(
                generate_lesson(
                    lesson_number=brief.lesson_number,
                    unit=unit_plan,
                    persona=persona,
                    include_homework=homework,
                )
            )
            save_lesson(daily, out_dir)
            export_lesson(daily, out_dir, fmt=fmt)
            lessons.append(daily)
            progress.advance(task)

    # Step 3: Materials for each lesson
    with _safe_progress(console=console) as progress:
        task = progress.add_task(
            "Step 3/3: Generating materials...", total=len(lessons)
        )
        for daily in lessons:
            progress.update(
                task,
                description=(
                    f"Materials for lesson {daily.lesson_number}"
                ),
            )
            mats = _run_async(generate_all_materials(daily, persona))
            save_materials(mats, out_dir)
            export_materials(mats, out_dir, fmt=fmt)
            progress.advance(task)

    # Final summary
    console.print(
        Panel(
            f"[green bold]Generation complete![/green bold]\n\n"
            f"[bold]Unit:[/bold] {unit_plan.title}\n"
            f"[bold]Lessons:[/bold] {len(lessons)}\n"
            f"[bold]Materials sets:[/bold] {len(lessons)}\n"
            f"[bold]Output:[/bold] {out_dir}",
            title="Done!",
        )
    )


# ── Sub-Packet command ──────────────────────────────────────────────────


@generate_app.command(name="sub-packet")
def sub_packet(
    date: str = typer.Option(
        ...,
        "--date",
        "-d",
        help="Date for the sub packet (e.g. '2026-03-24' or 'tomorrow')",
    ),
    class_name: str = typer.Option(
        "My Class", "--class", "-c", help="Class name"
    ),
    grade: str = typer.Option("8", "--grade", "-g", help="Grade level"),
    subject: str = typer.Option("General", "--subject", "-s", help="Subject"),
    topic: Optional[str] = typer.Option(
        None, "--topic", "-t", help="Lesson topic"
    ),
    fmt: str = typer.Option(
        "text", "--format", "-f", help="Output format: text, json"
    ),
) -> None:
    """Generate a complete substitute teacher packet."""
    from datetime import datetime, timedelta

    from eduagent.llm import LLMClient
    from eduagent.sub_packet import (
        SubPacketRequest,
        generate_sub_packet,
        save_sub_packet,
        sub_packet_to_markdown,
    )

    resolved_date = date.strip().lower()
    if resolved_date == "tomorrow":
        resolved_date = (datetime.now() + timedelta(days=1)).strftime(
            "%Y-%m-%d"
        )
    elif resolved_date == "today":
        resolved_date = datetime.now().strftime("%Y-%m-%d")

    cfg = AppConfig.load()
    teacher_name = cfg.teacher_profile.name or "Teacher"
    school_name = cfg.teacher_profile.school or ""

    request = SubPacketRequest(
        teacher_name=teacher_name,
        school=school_name,
        class_name=class_name,
        grade=grade,
        subject=subject,
        date=resolved_date,
        period_or_time=class_name,
        lesson_topic=topic or "",
    )

    console.print(
        Panel(
            f"Generating sub packet for [bold]{resolved_date}[/bold]",
            title="[bold blue]Substitute Teacher Packet[/bold blue]",
            border_style="blue",
        )
    )

    with _safe_progress(console=console) as progress:
        task = progress.add_task("Generating sub packet...", total=None)
        llm = LLMClient(cfg)
        packet = _run_async(generate_sub_packet(request, llm))
        progress.update(task, description="Sub packet complete!")

    md_path = save_sub_packet(packet, _output_dir())
    console.print(f"[green]Saved:[/green] {md_path}")

    if fmt == "text":
        text = sub_packet_to_markdown(packet)
        console.print()
        console.print(
            Panel(text, title="Sub Packet Preview", border_style="blue")
        )
    else:
        console.print(
            Panel(
                f"[bold]Teacher:[/bold] {packet.teacher_name}\n"
                f"[bold]Date:[/bold] {packet.date}\n"
                f"[bold]Class:[/bold] {packet.class_name}\n"
                f"[bold]Instructions:[/bold] {len(packet.lesson_instructions)}\n"
                f"[bold]Materials:[/bold]"
                f" {len(packet.materials_needed)} items",
                title="Sub Packet Summary",
            )
        )


# ── Parent Note command ─────────────────────────────────────────────────


@generate_app.command(name="parent-note")
def parent_note(
    student: str = typer.Option(
        ..., "--student", "-s", help="Student's name"
    ),
    topic: str = typer.Option(
        "general progress",
        "--topic",
        "-t",
        help="Note context (e.g. 'midterm', 'behavior')",
    ),
    strengths: Optional[str] = typer.Option(
        None, "--strengths", help="Comma-separated strengths"
    ),
    growth: Optional[str] = typer.Option(
        None, "--growth", help="Comma-separated growth areas"
    ),
    teacher_id: str = typer.Option(
        "local-teacher", "--id", help="Teacher session ID"
    ),
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

    strength_list = (
        [s.strip() for s in strengths.split(",")] if strengths else []
    )
    growth_list = (
        [g.strip() for g in growth.split(",")] if growth else []
    )

    console.print(
        Panel(
            f"Generating progress update for"
            f" [bold]{student}[/bold]\nTopic: {topic}",
            title="[bold green]Parent Communication[/bold green]",
            border_style="green",
        )
    )

    with _safe_progress(console=console) as progress:
        task = progress.add_task(
            "Writing progress update...", total=None
        )
        update = _run_async(
            generate_progress_update(
                student_name=student,
                strengths=strength_list,
                areas_to_grow=growth_list,
                teacher_persona=persona,
                topic=topic,
            )
        )
        progress.update(task, description="Progress update complete!")

    out_dir = _output_dir()
    json_path = save_progress_update(update, out_dir)
    console.print(f"[green]Saved:[/green] {json_path}")

    text = format_progress_update_text(update)
    console.print()
    console.print(
        Panel(
            text,
            title=f"Progress Update — {student}",
            border_style="green",
        )
    )


# ── Score command ────────────────────────────────────────────────────


@generate_app.command()
def score(
    lesson_file: str = typer.Option(
        ..., "--lesson-file", "-l", help="Path to a saved lesson JSON file"
    ),
):
    """Score a lesson plan on quality dimensions (1-5 per dimension)."""
    import json

    from eduagent.models import DailyLesson
    from eduagent.quality import LessonQualityScore

    path = Path(lesson_file).expanduser().resolve()
    if not path.exists():
        console.print(f"[red]File not found:[/red] {path}")
        raise typer.Exit(1)

    data = json.loads(path.read_text(encoding="utf-8"))
    lesson_obj = DailyLesson.model_validate(data)

    with _safe_progress(console=console) as progress:
        task = progress.add_task("Scoring lesson quality...", total=None)
        scorer = LessonQualityScore()
        scores = _run_async(scorer.score(lesson_obj))
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
    console.print(
        f"\n[bold]Overall Score:[/bold] [{color}]{overall}/5[/{color}]"
    )


# ── Improve command ───────────────────────────────────────────────────


@generate_app.command()
def improve(
    days: int = typer.Option(
        7, "--days", "-d", help="Feedback window in days"
    ),
):
    """Run one cycle of prompt improvement based on teacher feedback."""
    from eduagent.database import Database
    from eduagent.improver import improve_prompts

    db = Database()

    with _safe_progress(console=console) as progress:
        task = progress.add_task(
            "Analyzing feedback and improving prompts...", total=None
        )
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
        console.print(
            Panel(
                f"[green]{message}[/green]\n"
                f"[bold]Prompt type:[/bold]"
                f" {result.get('prompt_type', '')}\n"
                f"[bold]New version:[/bold]"
                f" {result.get('new_version', '')}\n"
                f"[bold]Avg rating:[/bold]"
                f" {result.get('feedback_summary', {}).get('avg_rating', '')}/5",
                title="Prompt Improvement",
            )
        )
    else:
        console.print(f"[dim]{message}[/dim]")


# ── Course command ───────────────────────────────────────────────────


@generate_app.command()
def course(
    subject: str = typer.Option(
        ..., "--subject", "-s", help="Subject area"
    ),
    grade: str = typer.Option(
        ..., "--grade", "-g", help="Grade level"
    ),
    topics_file: str = typer.Option(
        ...,
        "--topics-file",
        "-t",
        help="Path to a text file with one topic per line",
    ),
    weeks_per_topic: int = typer.Option(
        2, "--weeks", "-w", help="Weeks per topic"
    ),
    fmt: str = typer.Option("markdown", "--format", "-f", help="Export format"),
):
    """Generate a full course — one unit per topic from a pacing guide."""
    from eduagent.exporter import export_unit
    from eduagent.planner import plan_unit, save_unit

    persona = load_persona_or_exit()

    path = Path(topics_file).expanduser().resolve()
    if not path.exists():
        console.print(f"[red]File not found:[/red] {path}")
        raise typer.Exit(1)

    topics = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not topics:
        console.print("[red]No topics found in file.[/red]")
        raise typer.Exit(1)

    console.print(
        Panel(
            f"[bold]{subject} — Grade {grade}[/bold]\n"
            f"{len(topics)} topics, {weeks_per_topic} weeks each",
            title="Course Generation",
        )
    )

    out_dir = _output_dir() / "course"
    units = []

    with _safe_progress(console=console) as progress:
        task = progress.add_task(
            "Generating course...", total=len(topics)
        )
        for i, topic in enumerate(topics, 1):
            progress.update(
                task, description=f"Unit {i}/{len(topics)}: {topic}"
            )
            try:
                unit_plan = _run_async(
                    plan_unit(
                        subject=subject,
                        grade_level=grade,
                        topic=topic,
                        duration_weeks=weeks_per_topic,
                        persona=persona,
                    )
                )
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


# ── Evaluate command ──────────────────────────────────────────────────────


@generate_app.command()
def evaluate(
    lessons: int = typer.Option(
        5, "--lessons", "-n", help="Number of lessons to generate and evaluate"
    ),
    topic: str = typer.Option(
        "", "--topic", "-t", help="Topic for generated lessons (default: from persona)"
    ),
    grade: str = typer.Option(
        "", "--grade", "-g", help="Grade level (default: from persona)"
    ),
) -> None:
    """Generate lessons and evaluate voice consistency against your persona.

    This is the voice quality test harness. It generates N lessons using your
    persona, then uses the LLM to score each one on voice consistency,
    vocabulary match, and structure match.
    """
    from eduagent.evaluation import evaluate_voice_consistency
    from eduagent.lesson import generate_lesson
    from eduagent.models import DailyLesson, LessonBrief, UnitPlan

    persona = load_persona_or_exit()
    config = AppConfig.load()

    eval_topic = topic or persona.subject_area or "General Topics"
    eval_grade = grade or (persona.grade_levels[0] if persona.grade_levels else "8")

    console.print(
        Panel(
            f"Evaluating voice consistency\n"
            f"Persona: {persona.name}\n"
            f"Topic: {eval_topic} | Grade: {eval_grade}\n"
            f"Generating {lessons} lessons...",
            title="Voice Evaluation",
            border_style="blue",
        )
    )

    # Generate lessons
    generated: list[DailyLesson] = []
    with _safe_progress(console=console) as progress:
        task = progress.add_task("Generating lessons...", total=lessons)

        for i in range(1, lessons + 1):
            unit = UnitPlan(
                title=f"{eval_topic} Unit",
                subject=persona.subject_area or "General",
                grade_level=eval_grade,
                topic=eval_topic,
                duration_weeks=1,
                overview=f"A unit on {eval_topic}.",
                daily_lessons=[
                    LessonBrief(
                        lesson_number=1,
                        topic=f"{eval_topic} - Part {i}",
                        description=f"Lesson {i} on {eval_topic}",
                    )
                ],
            )
            try:
                lesson = _run_async(
                    generate_lesson(
                        lesson_number=1,
                        unit=unit,
                        persona=persona,
                        config=config,
                    )
                )
                lesson.lesson_number = i
                generated.append(lesson)
            except Exception as e:
                console.print(f"[yellow]Lesson {i} failed: {e}[/yellow]")
            progress.advance(task)

    if not generated:
        console.print("[red]No lessons generated. Check your LLM configuration.[/red]")
        raise typer.Exit(1)

    # Evaluate
    console.print("\nEvaluating voice consistency...")
    report = _run_async(evaluate_voice_consistency(persona, generated, config))

    # Display results
    eval_table = Table(title="Voice Evaluation Results")
    eval_table.add_column("Lesson", style="dim")
    eval_table.add_column("Voice", justify="center")
    eval_table.add_column("Vocab", justify="center")
    eval_table.add_column("Structure", justify="center")
    eval_table.add_column("Notes")

    for score in report.lesson_scores:
        eval_table.add_row(
            f"L{score.lesson_number}: {score.lesson_title[:30]}",
            f"{score.voice_consistency}/5",
            f"{score.vocabulary_match}/5",
            f"{score.structure_match}/5",
            score.notes[:50] if score.notes else "",
        )

    console.print(eval_table)

    console.print(
        Panel(
            f"Voice Consistency:  {report.avg_voice_consistency:.1f}/5\n"
            f"Vocabulary Match:   {report.avg_vocabulary_match:.1f}/5\n"
            f"Structure Match:    {report.avg_structure_match:.1f}/5\n"
            f"Overall Score:      {report.overall_score:.1f}/5\n\n"
            + (
                "Recommendations:\n" + "\n".join(f"  - {r}" for r in report.recommendations)
                if report.recommendations
                else "No recommendations."
            ),
            title="Summary",
            border_style="green" if report.overall_score >= 3.5 else "yellow",
        )
    )


# ── Curriculum gap analyzer ──────────────────────────────────────────────


@generate_app.command(name="gap-analyze")
def gap_analyze(
    subject: str = typer.Option(..., "--subject", "-s", help="Subject area (e.g. 'Social Studies')"),
    grade: str = typer.Option(..., "--grade", "-g", help="Grade level (e.g. '8')"),
    standards: Optional[str] = typer.Option(
        None,
        "--standards",
        help="Comma-separated standards codes/descriptions, or path to a .txt file (one per line)",
    ),
    materials_dir: Optional[str] = typer.Option(
        None,
        "--materials-dir",
        "-m",
        help="Directory of teacher materials to scan (defaults to persona corpus dir)",
    ),
    fmt: str = typer.Option("html", "--format", "-f", help="Output format: html or markdown"),
):
    """Analyze existing materials against standards and identify curriculum gaps.

    Scans teacher materials, compares them to the provided standards, and
    outputs a prioritized gap report with severity ratings and suggestions.

    Example:\n
        eduagent gap-analyze --subject "Social Studies" --grade 8 \\
            --standards "8.1.a,8.2.b,8.3.c"
    """
    from datetime import datetime

    from eduagent.curriculum_map import CurriculumMapper
    from eduagent.models import CurriculumGap, TeacherPersona

    persona = load_persona_or_exit()

    # ── Resolve standards ──────────────────────────────────────────────
    standards_list: list[str] = []
    if standards:
        p = Path(standards).expanduser()
        if p.exists():
            standards_list = [
                line.strip()
                for line in p.read_text().splitlines()
                if line.strip()
            ]
        else:
            standards_list = [s.strip() for s in standards.split(",") if s.strip()]

    if not standards_list:
        standards_list = [f"Grade {grade} {subject} — Core Standards (auto-inferred from materials)"]

    # ── Collect existing materials ─────────────────────────────────────
    mat_path: Path | None = None
    if materials_dir:
        mat_path = Path(materials_dir).expanduser().resolve()
        if not mat_path.is_dir():
            console.print(f"[red]Materials directory not found:[/red] {mat_path}")
            raise typer.Exit(1)
    else:
        cfg = AppConfig.load()
        corpus_base = Path.home() / ".eduagent"
        if getattr(cfg, "active_teacher_id", None):
            corpus_base = corpus_base / "teachers" / cfg.active_teacher_id / "corpus"
        else:
            corpus_base = corpus_base / "corpus"
        if corpus_base.is_dir():
            mat_path = corpus_base

    materials_list: list[str] = []
    if mat_path and mat_path.is_dir():
        exts = {".txt", ".md", ".pdf", ".docx", ".json"}
        files = [f for f in mat_path.rglob("*") if f.suffix.lower() in exts and f.is_file()]
        materials_list = [f.name for f in files[:200]]

    if not materials_list:
        materials_list = ["(no materials found — analysis is standards-only)"]

    # ── Run gap analysis ───────────────────────────────────────────────
    console.print(
        Panel(
            f"[bold]{subject} — Grade {grade}[/bold]\n"
            f"Standards: {len(standards_list)}  |  Materials: {len(materials_list)} files",
            title="Curriculum Gap Analyzer",
        )
    )

    mapper = CurriculumMapper()
    teacher_persona = TeacherPersona(
        name=getattr(persona, "name", ""),
        grade_levels=[grade],
        subject_area=subject,
    )

    with _safe_progress(console=console) as progress:
        task = progress.add_task("Analyzing curriculum gaps...", total=None)
        gaps: list[CurriculumGap] = _run_async(
            mapper.identify_curriculum_gaps(
                existing_materials=materials_list,
                standards=standards_list,
                persona=teacher_persona,
            )
        )
        progress.update(task, description="Analysis complete!")

    if not gaps:
        console.print("[green]No curriculum gaps identified! Coverage looks complete.[/green]")
        return

    # ── Severity counts ────────────────────────────────────────────────
    high = [g for g in gaps if g.severity.lower() == "high"]
    med  = [g for g in gaps if g.severity.lower() == "medium"]
    low  = [g for g in gaps if g.severity.lower() == "low"]

    # ── Display summary table ──────────────────────────────────────────
    table = Table(title=f"Curriculum Gaps — {subject} Grade {grade}")
    table.add_column("Severity", style="bold", justify="center")
    table.add_column("Standard", style="dim")
    table.add_column("Description")
    table.add_column("Suggestion")

    sev_order = {"high": 0, "medium": 1, "low": 2}
    for g in sorted(gaps, key=lambda x: sev_order.get(x.severity.lower(), 3)):
        sev_colors = {"high": "red", "medium": "yellow", "low": "green"}
        color = sev_colors.get(g.severity.lower(), "white")
        table.add_row(
            f"[{color}]{g.severity.upper()}[/{color}]",
            g.standard,
            g.description[:80] + ("…" if len(g.description) > 80 else ""),
            g.suggestion[:60] + ("…" if len(g.suggestion) > 60 else ""),
        )
    console.print(table)
    console.print(
        f"\n[bold]Summary:[/bold] {len(high)} HIGH  |  {len(med)} MEDIUM  |  {len(low)} LOW"
    )

    # ── Export ─────────────────────────────────────────────────────────
    out_dir = _output_dir() / "gap-reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = _safe_filename(f"{subject}_grade{grade}")

    if fmt == "html":
        html_path = out_dir / f"{slug}_gap_report.html"
        rows_html = ""
        badge_colors = {"high": "#ef4444", "medium": "#f59e0b", "low": "#22c55e"}
        for g in sorted(gaps, key=lambda x: sev_order.get(x.severity.lower(), 3)):
            color = badge_colors.get(g.severity.lower(), "#6b7280")
            rows_html += f"""
            <tr>
              <td><span class="badge" style="background:{color}">{g.severity.upper()}</span></td>
              <td class="standard">{g.standard}</td>
              <td>{g.description}</td>
              <td class="suggestion">{g.suggestion}</td>
            </tr>"""

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Curriculum Gap Report — {subject} Grade {grade}</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 1100px;
    margin: 2rem auto; padding: 0 1.5rem; color: #1f2937; }}
  h1 {{ font-size: 1.75rem; margin-bottom: .25rem; }}
  .meta {{ color: #6b7280; font-size: .9rem; margin-bottom: 2rem; }}
  .summary-bar {{ display: flex; gap: 1rem; margin-bottom: 2rem; }}
  .pill {{ padding: .4rem 1rem; border-radius: 9999px; font-weight: 600; font-size: .85rem; color: #fff; }}
  .pill.high {{ background: #ef4444; }} .pill.med {{ background: #f59e0b; }} .pill.low {{ background: #22c55e; }}
  table {{ width: 100%; border-collapse: collapse; font-size: .9rem; }}
  th {{ text-align: left; padding: .6rem .8rem; background: #f3f4f6; border-bottom: 2px solid #e5e7eb; }}
  td {{ padding: .6rem .8rem; border-bottom: 1px solid #e5e7eb; vertical-align: top; }}
  tr:hover td {{ background: #f9fafb; }}
  .badge {{ display: inline-block; padding: .2rem .6rem; border-radius: .3rem;
    color: #fff; font-size: .75rem; font-weight: 700; }}
  .standard {{ font-family: monospace; white-space: nowrap; color: #4b5563; }}
  .suggestion {{ font-style: italic; color: #374151; }}
  @media print {{ body {{ max-width: 100%; }} .summary-bar {{ break-inside: avoid; }} }}
</style>
</head>
<body>
<h1>Curriculum Gap Report</h1>
<div class="meta">{subject} · Grade {grade} · Generated {datetime.now().strftime("%B %d, %Y")}</div>
<div class="summary-bar">
  <span class="pill high">{len(high)} HIGH</span>
  <span class="pill med">{len(med)} MEDIUM</span>
  <span class="pill low">{len(low)} LOW</span>
</div>
<table>
  <thead><tr><th>Severity</th><th>Standard</th><th>Gap Description</th><th>Suggestion</th></tr></thead>
  <tbody>{rows_html}
  </tbody>
</table>
<p class="meta" style="margin-top:2rem">
  Generated by EDUagent · {len(materials_list)} materials analyzed · {len(standards_list)} standards checked
</p>
</body>
</html>"""
        html_path.write_text(html)
        console.print(f"\n[green]Gap report saved:[/green] {html_path}")

    else:
        md_path = out_dir / f"{slug}_gap_report.md"
        lines = [
            f"# Curriculum Gap Report — {subject} Grade {grade}\n",
            f"**Generated:** {datetime.now().strftime('%B %d, %Y')}  \n",
            f"**Summary:** {len(high)} HIGH | {len(med)} MEDIUM | {len(low)} LOW\n",
            "",
            "| Severity | Standard | Description | Suggestion |",
            "|----------|----------|-------------|------------|",
        ]
        for g in sorted(gaps, key=lambda x: sev_order.get(x.severity.lower(), 3)):
            lines.append(f"| **{g.severity.upper()}** | `{g.standard}` | {g.description} | {g.suggestion} |")
        md_path.write_text("\n".join(lines))
        console.print(f"\n[green]Gap report saved:[/green] {md_path}")
