"""Parent communication tools — progress updates in the teacher's voice.

Generates parent-facing notes and emails that match the teacher's
authentic communication style.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from clawed.llm import LLMClient
from clawed.models import AppConfig, ProgressUpdate, TeacherPersona

PROMPT_PATH = Path(__file__).parent / "prompts" / "parent_note.txt"


async def generate_progress_update(
    student_name: str,
    strengths: list[str],
    areas_to_grow: list[str],
    teacher_persona: Optional[TeacherPersona] = None,
    topic: str = "general progress",
    config: Optional[AppConfig] = None,
) -> ProgressUpdate:
    """Generate a parent progress update in the teacher's voice.

    Args:
        student_name: The student's name.
        strengths: List of observed strengths to highlight.
        areas_to_grow: List of growth areas to address constructively.
        teacher_persona: The teacher's persona for voice matching.
        topic: Context for the update (e.g., "midterm", "quarterly", "behavior").
        config: Optional app config override.

    Returns:
        A ProgressUpdate with greeting, strengths, growth areas, examples,
        action items, and closing — all in the teacher's voice.
    """
    config = config or AppConfig.load()
    persona = teacher_persona or TeacherPersona()
    persona_context = persona.to_prompt_context()

    prompt_template = PROMPT_PATH.read_text(encoding="utf-8")
    prompt = (
        prompt_template
        .replace("{persona}", persona_context)
        .replace("{student_name}", student_name)
        .replace("{topic}", topic)
        .replace("{strengths}", ", ".join(strengths) if strengths else "general positive observations")
        .replace("{areas_to_grow}", ", ".join(areas_to_grow) if areas_to_grow else "general growth areas")
    )

    client = LLMClient(config)
    data = await client.generate_json(
        prompt=prompt,
        system=(
            "You are helping a teacher write a progress update to a student's parent/guardian. "
            "Write in the teacher's authentic voice. Be warm, specific, and actionable. "
            "Return valid JSON only."
        ),
        temperature=0.6,
        max_tokens=4096,
    )

    return ProgressUpdate.model_validate(data)


def save_progress_update(update: ProgressUpdate, output_dir: Path) -> Path:
    """Save a progress update as JSON and return the path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    from clawed import _safe_filename

    safe_name = _safe_filename(update.student_name)
    filename = f"progress_update_{safe_name}.json"
    path = output_dir / filename
    path.write_text(update.model_dump_json(indent=2), encoding="utf-8")
    return path


def format_progress_update_text(update: ProgressUpdate) -> str:
    """Format a ProgressUpdate as a ready-to-send email/note."""
    lines = []

    lines.append(update.greeting)
    lines.append("")

    if update.strengths:
        for s in update.strengths:
            lines.append(s)
        lines.append("")

    if update.specific_examples:
        for ex in update.specific_examples:
            lines.append(ex)
        lines.append("")

    if update.areas_to_grow:
        for a in update.areas_to_grow:
            lines.append(a)
        lines.append("")

    if update.action_items:
        lines.append("Here's how we can work together:")
        for item in update.action_items:
            lines.append(f"  - {item}")
        lines.append("")

    if update.closing:
        lines.append(update.closing)

    return "\n".join(lines)
