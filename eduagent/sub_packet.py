"""Substitute teacher packet generator.

Generates a complete packet that a substitute teacher can pick up and run
with zero prior knowledge of the class, subject, or school.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from eduagent.llm import LLMClient
from eduagent.models import AppConfig, SubPacket, TeacherPersona
from eduagent.state import TeacherSession

PROMPT_PATH = Path(__file__).parent / "prompts" / "sub_packet.txt"


async def generate_sub_packet(
    teacher_id: str,
    date: str,
    lesson_id: Optional[str] = None,
    config: Optional[AppConfig] = None,
) -> SubPacket:
    """Generate a complete substitute teacher packet.

    Args:
        teacher_id: The teacher's session ID (used to load persona and lessons).
        date: The date the sub will be covering (e.g. "2026-03-24").
        lesson_id: Optional specific lesson ID to base instructions on.
        config: Optional app config override.

    Returns:
        A fully populated SubPacket ready for printing.
    """
    config = config or AppConfig.load()
    session = TeacherSession.load(teacher_id)

    # Build persona context
    persona = session.persona or TeacherPersona()
    persona_context = persona.to_prompt_context()

    # Build school context from teacher profile
    school = config.teacher_profile.school or "School name not configured"

    # Build lesson context if we have a current lesson or specific lesson_id
    lesson_context = _build_lesson_context(session, lesson_id)

    prompt_template = PROMPT_PATH.read_text()
    prompt = (
        prompt_template
        .replace("{persona}", persona_context)
        .replace("{school}", school)
        .replace("{date}", date)
        .replace("{lesson_context}", lesson_context)
    )

    client = LLMClient(config)
    data = await client.generate_json(
        prompt=prompt,
        system=(
            "You are an experienced substitute teacher coordinator. "
            "Generate a detailed, practical substitute teacher packet as JSON. "
            "Be extremely specific — the sub knows nothing about this class."
        ),
        temperature=0.5,
        max_tokens=8192,
    )

    return SubPacket.model_validate(data)


def _build_lesson_context(session: TeacherSession, lesson_id: Optional[str] = None) -> str:
    """Build lesson context string from session state."""
    parts = []

    if lesson_id:
        # Try to load specific lesson from DB
        from eduagent.state import _get_conn, init_db

        init_db()
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT lesson_json, title FROM generated_lessons WHERE id = ? AND teacher_id = ?",
                (lesson_id, session.teacher_id),
            ).fetchone()
        if row and row["lesson_json"]:
            parts.append(f"Lesson to teach today:\n{row['lesson_json']}")
    elif session.current_lesson:
        parts.append(f"Lesson to teach today:\n{session.current_lesson.model_dump_json()}")

    if session.current_unit:
        parts.append(f"Current unit context:\nTitle: {session.current_unit.title}")
        parts.append(f"Subject: {session.current_unit.subject}")
        parts.append(f"Grade: {session.current_unit.grade_level}")

    if not parts:
        return "No specific lesson loaded — generate a reasonable review/practice day for the teacher's subject area."

    return "\n".join(parts)


def save_sub_packet(packet: SubPacket, output_dir: Path) -> Path:
    """Save the sub packet as JSON and return the path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"sub_packet_{packet.date}.json"
    path = output_dir / filename
    path.write_text(packet.model_dump_json(indent=2))
    return path


def format_sub_packet_text(packet: SubPacket) -> str:
    """Format a SubPacket as a human-readable text document."""
    lines = []
    lines.append("SUBSTITUTE TEACHER PACKET")
    lines.append(f"{'=' * 50}")
    lines.append(f"Teacher: {packet.teacher_name}")
    lines.append(f"Date: {packet.date}")
    if packet.school:
        lines.append(f"School: {packet.school}")
    lines.append("")

    # Schedule
    lines.append("DAILY SCHEDULE")
    lines.append("-" * 40)
    for block in packet.schedule:
        line = f"  {block.time}  |  {block.period}  |  {block.class_name}"
        if block.notes:
            line += f"  ({block.notes})"
        lines.append(line)
    lines.append("")

    # Behavioral notes
    lines.append("CLASSROOM NOTES")
    lines.append("-" * 40)
    for note in packet.behavioral_notes:
        lines.append(f"\n  {note.period}:")
        lines.append(f"    Dynamics: {note.class_dynamics}")
        lines.append(f"    Seating: {note.seating_chart}")
        if note.accommodations:
            lines.append("    Accommodations:")
            for acc in note.accommodations:
                lines.append(f"      - {acc}")
        if note.key_students:
            lines.append("    Key Students:")
            for ks in note.key_students:
                lines.append(f"      - {ks}")
    lines.append("")

    # Lesson instructions
    lines.append("LESSON INSTRUCTIONS")
    lines.append("-" * 40)
    for instr in packet.lesson_instructions:
        lines.append(f"\n  {instr.period}: {instr.lesson_title}")
        lines.append(f"  Objective: {instr.objective}")
        lines.append("  Steps:")
        for step in instr.step_by_step:
            lines.append(f"    {step}")
        if instr.materials_needed:
            lines.append(f"  Materials: {', '.join(instr.materials_needed)}")
        if instr.backup_activity:
            lines.append(f"  BACKUP PLAN: {instr.backup_activity}")
        if instr.answer_key_location:
            lines.append(f"  Answer Key: {instr.answer_key_location}")
    lines.append("")

    # Emergency info
    lines.append("EMERGENCY CONTACTS")
    lines.append("-" * 40)
    for contact in packet.emergency_contacts:
        lines.append(f"  {contact}")
    lines.append("")
    lines.append("EMERGENCY PROCEDURES")
    lines.append("-" * 40)
    lines.append(f"  {packet.emergency_procedures}")
    lines.append("")

    # Materials checklist
    if packet.materials_checklist:
        lines.append("MATERIALS CHECKLIST")
        lines.append("-" * 40)
        for item in packet.materials_checklist:
            lines.append(f"  [ ] {item}")
        lines.append("")

    # General notes
    if packet.general_notes:
        lines.append("GENERAL NOTES")
        lines.append("-" * 40)
        lines.append(f"  {packet.general_notes}")

    return "\n".join(lines)
