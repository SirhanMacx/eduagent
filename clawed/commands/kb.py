"""Knowledge base commands -- browse, search, and manage your curriculum wiki."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from clawed.commands._helpers import console

kb_app = typer.Typer(help="Browse and manage your curriculum knowledge base.")

_BASE_DIR = Path(os.environ.get("EDUAGENT_DATA_DIR", str(Path.home() / ".eduagent")))
_CORPUS_DB = _BASE_DIR / "corpus" / "corpus.db"
_CURRICULUM_STATE = _BASE_DIR / "curriculum_state.json"
_CURRICULUM_CACHE = _BASE_DIR / "jon_curriculum_cache"
_CURRICULUM_KB_DB = _BASE_DIR / "memory" / "curriculum_kb.db"


def _corpus_exists() -> bool:
    return _CORPUS_DB.exists()


def _load_curriculum_state() -> dict:
    """Load curriculum_state.json if it exists."""
    if _CURRICULUM_STATE.exists():
        try:
            return json.loads(_CURRICULUM_STATE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


@kb_app.command("stats")
def kb_stats() -> None:
    """Show knowledge base statistics -- files ingested, topics, and coverage."""
    state = _load_curriculum_state()

    # Count files in curriculum cache
    cache_files = 0
    cache_dirs = 0
    if _CURRICULUM_CACHE.exists():
        for d in _CURRICULUM_CACHE.iterdir():
            if d.is_dir():
                cache_dirs += 1
                cache_files += sum(1 for f in d.iterdir() if f.is_file())

    # Count corpus entries
    corpus_count = 0
    corpus_subjects: set[str] = set()
    corpus_types: dict[str, int] = {}
    if _corpus_exists():
        try:
            conn = sqlite3.connect(str(_CORPUS_DB))
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT COUNT(*) as cnt FROM corpus_examples").fetchone()
            corpus_count = row["cnt"] if row else 0
            for r in conn.execute("SELECT DISTINCT subject FROM corpus_examples"):
                corpus_subjects.add(r["subject"])
            for r in conn.execute(
                "SELECT content_type, COUNT(*) as cnt FROM corpus_examples GROUP BY content_type"
            ):
                corpus_types[r["content_type"]] = r["cnt"]
            conn.close()
        except Exception:
            pass

    # Count curriculum KB chunks
    kb_chunks = 0
    if _CURRICULUM_KB_DB.exists():
        try:
            conn = sqlite3.connect(str(_CURRICULUM_KB_DB))
            row = conn.execute("SELECT COUNT(*) as cnt FROM chunks").fetchone()
            kb_chunks = row[0] if row else 0
            conn.close()
        except Exception:
            pass

    # Course info from curriculum state
    courses = state.get("courses", {})

    lines = []
    lines.append(f"[bold]Curriculum Cache:[/bold] {cache_files} files across {cache_dirs} subjects")
    if courses:
        lines.append(f"[bold]Active Courses:[/bold]  {len(courses)}")
    lines.append(f"[bold]Corpus Examples:[/bold] {corpus_count}")
    if corpus_subjects:
        lines.append(f"[bold]Subjects:[/bold]        {', '.join(sorted(corpus_subjects))}")
    if corpus_types:
        type_str = ", ".join(f"{k}: {v}" for k, v in sorted(corpus_types.items()))
        lines.append(f"[bold]By Type:[/bold]         {type_str}")
    lines.append(f"[bold]KB Chunks:[/bold]       {kb_chunks} searchable text chunks")

    if not _corpus_exists() and cache_files == 0:
        lines.append("")
        lines.append(
            "[yellow]No files ingested yet.[/yellow] "
            "Run [bold]clawed ingest <path>[/bold] to add your teaching materials."
        )

    console.print(
        Panel(
            "\n".join(lines),
            title="[bold]Knowledge Base Stats[/bold]",
            border_style="cyan",
        )
    )


@kb_app.command("topics")
def kb_topics() -> None:
    """List all topics from your curriculum -- courses, units, and what's coming up."""
    state = _load_curriculum_state()
    courses = state.get("courses", {})

    if not courses:
        console.print(
            "[dim]No curriculum data yet. "
            "Your topics will appear here after you ingest materials "
            "or set up your courses.[/dim]"
        )
        return

    table = Table(title="Your Courses and Topics")
    table.add_column("Course", style="bold")
    table.add_column("Grade", style="cyan", justify="center")
    table.add_column("Current Unit", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Next Up", style="dim")

    for _key, course in courses.items():
        table.add_row(
            course.get("name", _key),
            course.get("grade", ""),
            course.get("current_unit", ""),
            course.get("status", ""),
            course.get("next_unit", ""),
        )

    console.print(table)

    # Show completed units per course
    for _key, course in courses.items():
        completed = course.get("units_completed", [])
        remaining = course.get("units_remaining", [])
        if completed or remaining:
            course_name = course.get("name", _key)
            tree = Tree(f"[bold]{course_name}[/bold]")
            if completed:
                done_branch = tree.add("[green]Completed[/green]")
                for u in completed:
                    done_branch.add(f"[dim]{u}[/dim]")
            if remaining:
                todo_branch = tree.add("[yellow]Remaining[/yellow]")
                for u in remaining:
                    todo_branch.add(u)
            console.print(tree)
            console.print()


@kb_app.command("search")
def kb_search(
    query: str = typer.Argument(..., help="What to search for in your materials"),
    limit: int = typer.Option(10, "--limit", "-n", help="Max results to show"),
) -> None:
    """Search your curriculum knowledge base for topics, files, and examples."""
    query_lower = query.lower()
    results: list[dict] = []

    # 1. Search corpus.db
    if _corpus_exists():
        try:
            conn = sqlite3.connect(str(_CORPUS_DB))
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id, content_type, subject, grade_level, topic,
                       quality_score, source, created_at
                FROM corpus_examples
                WHERE topic LIKE ? OR subject LIKE ? OR content_type LIKE ?
                ORDER BY quality_score DESC
                LIMIT ?
                """,
                (f"%{query_lower}%", f"%{query_lower}%", f"%{query_lower}%", limit),
            ).fetchall()
            for r in rows:
                results.append({
                    "source": "corpus",
                    "type": r["content_type"],
                    "subject": r["subject"],
                    "grade": r["grade_level"],
                    "topic": r["topic"] or "",
                    "quality": r["quality_score"],
                    "created": r["created_at"] or "",
                })
            conn.close()
        except Exception:
            pass

    # 2. Search curriculum_state.json
    state = _load_curriculum_state()
    for _key, course in state.get("courses", {}).items():
        course_name = course.get("name", "")
        current = course.get("current_unit", "")
        notes = course.get("notes", "")
        searchable = f"{course_name} {current} {notes}".lower()
        all_units = course.get("units_completed", []) + course.get("units_remaining", [])
        for unit in all_units:
            if query_lower in unit.lower():
                results.append({
                    "source": "curriculum",
                    "type": "unit",
                    "subject": course_name,
                    "grade": course.get("grade", ""),
                    "topic": unit,
                    "quality": 0,
                    "created": "",
                })
        if query_lower in searchable and not any(
            r["subject"] == course_name for r in results
        ):
            results.append({
                "source": "curriculum",
                "type": "course",
                "subject": course_name,
                "grade": course.get("grade", ""),
                "topic": current,
                "quality": 0,
                "created": "",
            })

    # 3. Search file names in curriculum cache
    if _CURRICULUM_CACHE.exists():
        for subject_dir in _CURRICULUM_CACHE.iterdir():
            if not subject_dir.is_dir():
                continue
            for f in subject_dir.iterdir():
                if query_lower in f.name.lower():
                    results.append({
                        "source": "files",
                        "type": f.suffix.lstrip(".") or "file",
                        "subject": subject_dir.name.replace("_", " ").title(),
                        "grade": "",
                        "topic": f.name,
                        "quality": 0,
                        "created": "",
                    })

    if not results:
        console.print(f"[yellow]No results found for '{query}'.[/yellow]")
        if not _corpus_exists():
            console.print(
                "[dim]Your knowledge base is empty. "
                "Run [bold]clawed ingest <path>[/bold] to add your teaching materials.[/dim]"
            )
        return

    # De-duplicate and limit
    seen = set()
    unique_results = []
    for r in results:
        key = (r["source"], r["subject"], r["topic"])
        if key not in seen:
            seen.add(key)
            unique_results.append(r)
    results = unique_results[:limit]

    table = Table(title=f"Search Results for '{query}'")
    table.add_column("Source", style="dim")
    table.add_column("Type", style="cyan")
    table.add_column("Subject", style="bold")
    table.add_column("Grade", justify="center")
    table.add_column("Topic / File")

    for r in results:
        table.add_row(
            r["source"],
            r["type"],
            r["subject"],
            r["grade"],
            r["topic"],
        )

    console.print(table)
    console.print(f"\n[dim]{len(results)} result(s) found.[/dim]")


@kb_app.command("browse")
def kb_browse() -> None:
    """Browse your ingested curriculum files organized by subject."""
    if not _CURRICULUM_CACHE.exists():
        console.print(
            "[dim]No curriculum files found.[/dim]\n"
            "Run [bold]clawed ingest <path>[/bold] to add your teaching materials, "
            "or point to a folder of your lesson files."
        )
        return

    subjects = sorted(
        d for d in _CURRICULUM_CACHE.iterdir() if d.is_dir()
    )

    if not subjects:
        console.print("[dim]No subject folders found in curriculum cache.[/dim]")
        return

    tree = Tree("[bold]Your Teaching Materials[/bold]")

    for subject_dir in subjects:
        files = sorted(f for f in subject_dir.iterdir() if f.is_file())
        label = subject_dir.name.replace("_", " ").title()
        branch = tree.add(f"[bold cyan]{label}[/bold cyan] ({len(files)} files)")

        # Show up to 8 files per subject, then summarize
        for f in files[:8]:
            size_kb = f.stat().st_size / 1024
            suffix = f.suffix.upper().lstrip(".")
            branch.add(f"[dim]{suffix}[/dim] {f.name} [dim]({size_kb:.0f} KB)[/dim]")
        if len(files) > 8:
            branch.add(f"[dim]... and {len(files) - 8} more files[/dim]")

    console.print(tree)

    total_files = sum(
        sum(1 for f in d.iterdir() if f.is_file())
        for d in subjects
    )
    console.print(
        f"\n[dim]{len(subjects)} subjects, {total_files} files total.[/dim]"
    )
