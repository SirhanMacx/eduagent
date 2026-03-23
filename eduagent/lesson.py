"""Lesson plan generator — creates detailed daily lesson plans via LLM."""

from __future__ import annotations

from pathlib import Path

from eduagent.corpus import get_few_shot_context
from eduagent.llm import LLMClient
from eduagent.models import AppConfig, DailyLesson, TeacherPersona, UnitPlan

PROMPT_PATH = Path(__file__).parent / "prompts" / "lesson_plan.txt"


async def generate_lesson(
    lesson_number: int,
    unit: UnitPlan,
    persona: TeacherPersona,
    include_homework: bool = True,
    config: AppConfig | None = None,
) -> DailyLesson:
    """Generate a complete daily lesson plan for a specific lesson in a unit.

    Args:
        lesson_number: Which lesson in the unit (1-indexed).
        unit: The parent unit plan for context.
        persona: Teacher persona to match.
        include_homework: Whether to generate a homework assignment.
        config: Optional app config override.

    Returns:
        A fully populated DailyLesson.
    """
    # Find the matching lesson brief from the unit plan
    lesson_brief = None
    for brief in unit.daily_lessons:
        if brief.lesson_number == lesson_number:
            lesson_brief = brief
            break

    if lesson_brief is None:
        raise ValueError(
            f"Lesson {lesson_number} not found in unit plan. "
            f"Unit has {len(unit.daily_lessons)} lessons."
        )

    # Pull few-shot examples from the corpus for this subject/grade
    few_shot_context = get_few_shot_context(
        content_type="lesson_plan",
        subject=unit.subject.lower(),
        grade_level=unit.grade_level,
    )

    prompt_template = PROMPT_PATH.read_text()
    prompt = (
        prompt_template
        .replace("{persona}", persona.to_prompt_context())
        .replace("{unit_title}", unit.title)
        .replace("{unit_overview}", unit.overview[:500])
        .replace("{essential_questions}", "\n".join(f"- {q}" for q in unit.essential_questions))
        .replace("{lesson_number}", str(lesson_number))
        .replace("{total_lessons}", str(len(unit.daily_lessons)))
        .replace("{lesson_topic}", lesson_brief.topic)
        .replace("{lesson_description}", lesson_brief.description)
        .replace("{grade_level}", unit.grade_level)
        .replace("{subject}", unit.subject)
        .replace("{include_homework}", "Yes" if include_homework else "No — do not include homework")
        .replace("{few_shot_context}", few_shot_context)
    )

    client = LLMClient(config)
    data = await client.generate_json(
        prompt=prompt,
        system=(
            "You are an expert lesson plan writer. "
            "Respond only with valid JSON matching the specified format."
        ),
        temperature=0.6,
        max_tokens=12000,
    )

    return DailyLesson.model_validate(data)


async def generate_all_lessons(
    unit: UnitPlan,
    persona: TeacherPersona,
    include_homework: bool = True,
    config: AppConfig | None = None,
) -> list[DailyLesson]:
    """Generate lesson plans for every lesson in a unit sequentially."""
    lessons: list[DailyLesson] = []
    for brief in unit.daily_lessons:
        lesson = await generate_lesson(
            lesson_number=brief.lesson_number,
            unit=unit,
            persona=persona,
            include_homework=include_homework,
            config=config,
        )
        lessons.append(lesson)
    return lessons


def save_lesson(lesson: DailyLesson, output_dir: Path) -> Path:
    """Save a lesson plan to disk as JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"lesson_{lesson.lesson_number:02d}.json"
    path.write_text(lesson.model_dump_json(indent=2))
    return path


def load_lesson(path: Path) -> DailyLesson:
    """Load a lesson plan from a JSON file."""
    if not path.exists():
        raise FileNotFoundError(f"Lesson file not found: {path}")
    return DailyLesson.model_validate_json(path.read_text())
