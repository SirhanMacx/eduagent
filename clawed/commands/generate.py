"""Generation commands — main module and entry point.

Core commands kept here: ingest, transcribe, lesson, differentiate,
sub-packet, parent-note, gap-analyze.

Split modules (imported at bottom):
  - generate_unit.py      — unit, year-map, pacing, full, course
  - generate_assessment.py — materials, assess, rubric, score, improve, evaluate
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.panel import Panel
from rich.table import Table

from clawed.commands._helpers import _safe_progress, console, load_persona_or_exit
from clawed.commands._helpers import output_dir as _output_dir
from clawed.commands._helpers import run_async as _run_async
from clawed.io import safe_filename as _safe_filename
from clawed.models import AppConfig

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
    from clawed.ingestor import ingest_path, scan_directory

    source = Path(path).expanduser().resolve()

    if dry_run:
        console.print(
            Panel(
                f"[yellow]DRY RUN[/yellow] — scanning [bold]{source}[/bold]",
                title="Claw-ED",
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
        Panel(f"Ingesting materials from [bold]{source}[/bold]", title="Claw-ED")
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
    from clawed.persona import extract_persona, save_persona

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
    from clawed.voice import is_audio_file, transcribe_audio

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
    fmt: str = typer.Option("markdown", "--format", "-f", help="Export format: markdown, pptx, docx, pdf, handout"),
):
    """Generate a detailed daily lesson plan.

    \b
    Standalone mode (no unit plan needed):
        clawed lesson "The American Revolution" --grade 8 --subject "social studies"

    From a unit plan:
        clawed lesson "Photosynthesis" --unit-file output/unit_photosynthesis.json -n 1
    """
    from clawed.export_markdown import export_lesson
    from clawed.lesson import generate_lesson, save_lesson

    persona = load_persona_or_exit()

    if unit_file:
        from clawed.planner import load_unit
        unit_plan = load_unit(Path(unit_file))
    else:
        # Standalone mode: create a minimal unit plan from the topic
        from clawed.models import LessonBrief, UnitPlan
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

    # For doc formats (pptx/docx/pdf/handout), use doc_export directly;
    # export_lesson only handles markdown/pdf/docx natively.
    export_path = None
    if fmt in ("pptx", "docx", "pdf", "handout"):
        try:
            from clawed.doc_export import (
                export_lesson_docx,
                export_lesson_pdf,
                export_lesson_pptx,
                export_student_handout,
            )
            if fmt == "pptx":
                doc_path = export_lesson_pptx(daily, persona, out_dir)
            elif fmt == "docx":
                doc_path = export_lesson_docx(daily, persona, out_dir)
            elif fmt == "handout":
                doc_path = export_student_handout(daily, persona, out_dir)
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
    from clawed.differentiation import (
        generate_504_accommodations,
        generate_iep_lesson_modifications,
        generate_tiered_assignments,
        load_iep_profiles,
        save_modified_lessons,
        save_tiered_assignments,
    )
    from clawed.lesson import load_lesson

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
            "Example: clawed differentiate"
            " --lesson-file lesson.json --iep students.json"
        )
        raise typer.Exit(1)


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

    from clawed.llm import LLMClient
    from clawed.sub_packet import (
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
    from clawed.parent_comm import (
        format_progress_update_text,
        generate_progress_update,
        save_progress_update,
    )
    from clawed.state import TeacherSession as _TeacherSession

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
        clawed gap-analyze --subject "Social Studies" --grade 8 \\
            --standards "8.1.a,8.2.b,8.3.c"
    """
    from datetime import datetime

    from clawed.curriculum_map import CurriculumMapper
    from clawed.models import CurriculumGap, TeacherPersona

    persona = load_persona_or_exit()

    # ── Resolve standards ──────────────────────────────────────────────
    standards_list: list[str] = []
    if standards:
        p = Path(standards).expanduser()
        if p.exists():
            standards_list = [
                line.strip()
                for line in p.read_text(encoding="utf-8").splitlines()
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
  Generated by Claw-ED · {len(materials_list)} materials analyzed · {len(standards_list)} standards checked
</p>
</body>
</html>"""
        html_path.write_text(html, encoding="utf-8")
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
        md_path.write_text("\n".join(lines), encoding="utf-8")
        console.print(f"\n[green]Gap report saved:[/green] {md_path}")


# ── Import split modules so their commands register on generate_app ──────
import clawed.commands.generate_assessment  # noqa: E402, F401
import clawed.commands.generate_unit  # noqa: E402, F401
