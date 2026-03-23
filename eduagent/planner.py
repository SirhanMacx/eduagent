"""Unit and curriculum planner — generates structured unit plans via LLM."""

from __future__ import annotations

from pathlib import Path

from eduagent.corpus import get_few_shot_context
from eduagent.llm import LLMClient
from eduagent.models import AppConfig, TeacherPersona, UnitPlan

PROMPT_PATH = Path(__file__).parent / "prompts" / "unit_plan.txt"


async def plan_unit(
    subject: str,
    grade_level: str,
    topic: str,
    duration_weeks: int,
    persona: TeacherPersona,
    standards: list[str] | None = None,
    config: AppConfig | None = None,
) -> UnitPlan:
    """Generate a complete unit plan aligned to the teacher's persona.

    Args:
        subject: The academic subject (e.g., "Science", "ELA").
        grade_level: Grade level string (e.g., "8", "K", "11-12").
        topic: The unit topic (e.g., "Photosynthesis").
        duration_weeks: Number of weeks for the unit.
        persona: The teacher persona to match in voice and style.
        standards: Optional list of standards to align to.
        config: Optional app config override.

    Returns:
        A fully populated UnitPlan.
    """
    # Estimate ~5 lessons per week
    total_lessons = duration_weeks * 5

    # Pull few-shot examples from the corpus for this subject/grade
    few_shot_context = get_few_shot_context(
        content_type="unit_plan",
        subject=subject.lower(),
        grade_level=grade_level,
    )

    prompt_template = PROMPT_PATH.read_text()
    prompt = (
        prompt_template
        .replace("{persona}", persona.to_prompt_context())
        .replace("{subject}", subject)
        .replace("{grade_level}", grade_level)
        .replace("{topic}", topic)
        .replace("{duration_weeks}", str(duration_weeks))
        .replace("{total_lessons}", str(total_lessons))
        .replace("{standards}", ", ".join(standards) if standards else "Use appropriate grade-level standards")
        .replace("{few_shot_context}", few_shot_context)
    )

    client = LLMClient(config)
    data = await client.generate_json(
        prompt=prompt,
        system=(
            "You are an expert curriculum designer. "
            "Respond only with valid JSON matching the specified format."
        ),
        temperature=0.5,
        max_tokens=6000,
    )

    return UnitPlan.model_validate(data)


def save_unit(unit: UnitPlan, output_dir: Path) -> Path:
    """Save a unit plan to disk as JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_title = unit.title.lower().replace(" ", "_")[:50]
    path = output_dir / f"unit_{safe_title}.json"
    path.write_text(unit.model_dump_json(indent=2))
    return path


def load_unit(path: Path) -> UnitPlan:
    """Load a unit plan from a JSON file."""
    if not path.exists():
        raise FileNotFoundError(f"Unit plan file not found: {path}")
    return UnitPlan.model_validate_json(path.read_text())
