"""Lesson plan generator — creates detailed daily lesson plans via LLM."""

from __future__ import annotations

from pathlib import Path

from clawed.corpus import get_few_shot_context
from clawed.llm import LLMClient
from clawed.model_router import route as route_model
from clawed.models import AppConfig, DailyLesson, TeacherPersona, UnitPlan

PROMPT_PATH = Path(__file__).parent / "prompts" / "lesson_plan.txt"


async def generate_lesson(
    lesson_number: int,
    unit: UnitPlan,
    persona: TeacherPersona,
    include_homework: bool = True,
    config: AppConfig | None = None,
    task_type: str = "lesson_plan",
    state: str = "",
    teacher_materials: str = "",
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

    # Auto-populate unit standards from teacher profile if missing
    if not unit.standards:
        try:
            config = config or AppConfig.load()
            if config.teacher_profile and config.teacher_profile.state:
                from clawed.standards import get_standards
                results = get_standards(unit.subject, unit.grade_level)
                unit.standards = [
                    f"{code}: {desc}" for code, desc, _ in results[:5]
                ]
        except Exception:
            pass

    # Pull few-shot examples from the corpus for this subject/grade
    few_shot_context = get_few_shot_context(
        content_type="lesson_plan",
        subject=unit.subject.lower(),
        grade_level=unit.grade_level,
    )

    # Look up applicable standards for this lesson
    from clawed.standards import format_standards_for_prompt, get_standards_for_lesson

    effective_state = state
    if not effective_state and config:
        effective_state = getattr(config, "teacher_profile", None) and config.teacher_profile.state or ""
    standards_list = get_standards_for_lesson(
        subject=unit.subject,
        grade=unit.grade_level,
        state=effective_state,
        topic=lesson_brief.topic,
    )
    standards_text = format_standards_for_prompt(standards_list)

    prompt_template = PROMPT_PATH.read_text(encoding="utf-8")
    prompt = (
        prompt_template
        .replace("{persona}", persona.to_prompt_context())
        .replace("{unit_title}", unit.title)
        .replace("{unit_overview}", unit.overview[:1500])
        .replace("{essential_questions}", "\n".join(f"- {q}" for q in unit.essential_questions))
        .replace("{lesson_number}", str(lesson_number))
        .replace("{total_lessons}", str(len(unit.daily_lessons)))
        .replace("{lesson_topic}", lesson_brief.topic)
        .replace("{lesson_description}", lesson_brief.description)
        .replace("{grade_level}", unit.grade_level)
        .replace("{subject}", unit.subject)
        .replace("{include_homework}", "Yes" if include_homework else "No — do not include homework")
        .replace("{few_shot_context}", few_shot_context)
        .replace("{standards}", standards_text)
        .replace("{teacher_materials}", teacher_materials)
    )

    # Build rich system prompt with persona and voice context
    persona_context = persona.to_prompt_context() if persona else ""
    soul_context = ""
    try:
        soul_path = Path.home() / ".eduagent" / "workspace" / "SOUL.md"
        if soul_path.exists():
            soul_context = soul_path.read_text(encoding="utf-8")[:2000]
    except Exception:
        pass

    system_parts = [
        "You are an expert lesson plan writer who EXACTLY replicates "
        "this teacher's pedagogical fingerprint in EVERY lesson. "
        "This means: use their specific graphic organizers (INSPECT charts, T-charts, etc.), "
        "their activity structures (jigsaw, pair role division, desk islands), "
        "their Do Now format (multi-part visual analysis), their scaffolding moves "
        "(writing frames, sentence starters, pre-taught vocabulary with icons), "
        "and their signature teaching moves. If the persona says they use INSPECT charts, "
        "the lesson MUST include an INSPECT chart. If they cold-call students, script cold calls. "
        "If they say 'what is this source NOT telling us,' include that exact prompt.",
    ]
    if persona_context:
        system_parts.append(persona_context)
    if soul_context:
        system_parts.append(soul_context)
    system_parts.append(
        "Respond only with valid JSON matching the specified format. "
        "Do NOT use XML tags, angle brackets, or markdown formatting in the JSON values."
    )
    system = "\n\n".join(system_parts)

    if task_type and config:
        config = route_model(task_type, config)
    client = LLMClient(config)
    return await client.safe_generate_json(
        prompt=prompt,
        model_class=DailyLesson,
        system=system,
        temperature=0.6,
        max_tokens=12000,
    )


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
    from clawed.io import write_text

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"lesson_{lesson.lesson_number:02d}.json"
    write_text(path, lesson.model_dump_json(indent=2))
    return path


def load_lesson(path: Path) -> DailyLesson:
    """Load a lesson plan from a JSON file."""
    if not path.exists():
        raise FileNotFoundError(f"Lesson file not found: {path}")
    return DailyLesson.model_validate_json(path.read_text(encoding="utf-8"))
