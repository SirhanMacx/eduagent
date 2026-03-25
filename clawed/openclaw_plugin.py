"""Claw-ED OpenClaw Plugin — thin shim delegating to the gateway.

External callers (Telegram bot, tests, CLI) import these names:
    handle_message   — routes through gateway.handle()
    get_last_lesson_id
    _show_status
    _transcribe_attachments
    _fmt_unit_summary, _fmt_lesson_summary, _fmt_persona

All generation logic lives in clawed.generation (the service layer).
All routing lives in clawed.gateway (the brain).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from clawed.models import AppConfig, TeacherPersona
from clawed.state import TeacherSession

# ── Rating helpers ────────────────────────────────────────────────────────────


def get_last_lesson_id(teacher_id: str) -> Optional[str]:
    """Return the ID of the most recently generated lesson, then clear it.

    Used by Telegram bot and CLI chat to offer a rating prompt.
    """
    session = TeacherSession.load(teacher_id)
    lesson_id = session.config.pop("last_lesson_id", None)
    if lesson_id:
        session.save()
    return lesson_id


# ── Response formatters ──────────────────────────────────────────────────────


def _fmt_unit_summary(unit) -> str:
    """Format a unit plan for Telegram (no markdown tables)."""
    lines = [
        f"\U0001f4da *{unit.title}*",
        f"Grade {unit.grade_level} {unit.subject} | {unit.duration_weeks} weeks | {len(unit.daily_lessons)} lessons",
        "",
        "\U0001f4cc *Essential Questions*",
    ]
    for q in unit.essential_questions[:3]:
        lines.append(f"\u2022 {q}")
    lines.append("")
    lines.append("\U0001f4c5 *Lesson Sequence*")
    for lesson in unit.daily_lessons[:5]:
        lines.append(f"  L{lesson.lesson_number}: {lesson.topic}")
    if len(unit.daily_lessons) > 5:
        lines.append(f"  ... +{len(unit.daily_lessons) - 5} more lessons")
    lines.append("")
    lines.append("_Reply with 'generate lesson 1' to get the full first lesson plan, or 'export PDF' to download._")
    return "\n".join(lines)


def _fmt_lesson_summary(lesson) -> str:
    """Format a lesson plan for Telegram."""
    lines = [
        f"\U0001f4dd *Lesson {lesson.lesson_number}: {lesson.title}*",
        "",
        f"\U0001f3af *Objective:* {lesson.objective}",
        "",
        f"\U0001f514 *Do-Now (5 min):* {lesson.do_now[:200]}...",
        "",
        "\U0001f4cb *Structure:*",
        f"\u2022 Direct Instruction ({lesson.time_estimates.get('direct_instruction', 20)} min)",
        f"\u2022 Guided Practice ({lesson.time_estimates.get('guided_practice', 15)} min)",
        f"\u2022 Independent Work ({lesson.time_estimates.get('independent_work', 10)} min)",
        f"\u2022 Exit Ticket ({len(lesson.exit_ticket)} questions)",
        "",
    ]
    if lesson.differentiation.struggling:
        lines.append("\u267f *Differentiation included* (struggling/advanced/ELL)")
    if lesson.homework:
        lines.append("\U0001f4da *Homework:* Yes")
    lines.append("")
    lines.append("_Reply 'generate materials' for the worksheet + assessment, or 'export PDF' to download._")
    return "\n".join(lines)


def _fmt_persona(persona: TeacherPersona) -> str:
    """Format a teacher persona for Telegram."""
    lines = [
        "\U0001f469\u200d\U0001f3eb *Your Teaching Profile*",
        "",
        f"\u2022 Style: {persona.teaching_style.value.replace('_', ' ').title()}",
        f"\u2022 Tone: {persona.tone}",
        f"\u2022 Format: {persona.preferred_lesson_format}",
    ]
    if persona.structural_preferences:
        lines.append(f"\u2022 Preferences: {', '.join(persona.structural_preferences[:4])}")
    if persona.subject_area:
        lines.append(f"\u2022 Subject: {persona.subject_area}")
    if persona.grade_levels:
        lines.append(f"\u2022 Grades: {', '.join(persona.grade_levels)}")
    lines.append("")
    lines.append("_Everything I generate will match this profile. Reply 'update my profile' to change anything._")
    return "\n".join(lines)


# ── Audio transcription ───────────────────────────────────────────────────────


async def _transcribe_attachments(attachments: list[str]) -> str:
    """Transcribe any audio files found in the attachment list."""
    from clawed.voice import is_audio_file, transcribe_audio

    parts: list[str] = []
    for att in attachments:
        if is_audio_file(att):
            try:
                text = await transcribe_audio(Path(att))
                if text:
                    parts.append(text)
            except Exception:
                pass  # Skip files that fail to transcribe
    return " ".join(parts)


# ── Status ────────────────────────────────────────────────────────────────────


def _show_status(session: TeacherSession) -> str:
    """Return a formatted status string for the given session."""
    lines = ["\u2699\ufe0f *Claw-ED Status*", ""]
    if session.persona:
        lines.append(f"\U0001f469\u200d\U0001f3eb Persona: {session.persona.teaching_style.value.replace('_', ' ').title()} teacher")
        if session.persona.subject_area:
            lines.append(f"\U0001f4da Subject: {session.persona.subject_area}")
        if session.persona.grade_levels:
            lines.append(f"\U0001f393 Grades: {', '.join(session.persona.grade_levels)}")
    else:
        lines.append("\U0001f469\u200d\U0001f3eb Persona: Not set up yet")

    if session.config.get("drive_url"):
        lines.append("\u2601\ufe0f Drive: Connected")
    elif session.config.get("materials_path"):
        lines.append(f"\U0001f4c1 Materials: {Path(session.config['materials_path']).name}")
    else:
        lines.append("\U0001f4c2 Materials: Not connected")

    config = AppConfig.load()
    lines.append(f"\U0001f916 LLM: {config.provider.value}")

    if session.current_unit:
        lines.append(f"\U0001f4d6 Current unit: {session.current_unit.title}")
    if session.current_lesson:
        lines.append(f"\U0001f4dd Current lesson: {session.current_lesson.title}")

    recent = session.get_recent_units(limit=3)
    if recent:
        lines.append("")
        lines.append("\U0001f4da Recent units:")
        for u in recent:
            lines.append(f"  \u2022 {u['title']} ({u['subject']}, Gr. {u['grade_level']})")

    return "\n".join(lines)


# ── Main handler (thin shim) ────────────────────────────────────────────────


async def handle_message(
    message: str,
    teacher_id: str,
    *,
    subject: Optional[str] = None,
    grade: Optional[str] = None,
    attachments: Optional[list[str]] = None,
) -> str:
    """Handle a teacher message and return a response string.

    This is the backward-compatible entry point.  It delegates to the gateway
    for routing and intent dispatch.  The gateway calls into
    clawed.generation for the actual LLM work.
    """
    # Auto-transcribe audio attachments
    if attachments:
        transcribed = await _transcribe_attachments(attachments)
        if transcribed:
            if not message.strip():
                message = transcribed
            else:
                message = message + "\n\n" + transcribed

    # Delegate to the gateway (the single brain)
    from clawed.gateway import Gateway
    gw = Gateway()
    response = await gw.handle(message, teacher_id)
    return response.text
