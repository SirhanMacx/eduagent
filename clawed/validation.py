"""Post-generation output validation for all Claw-ED generation types."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from clawed.master_content import MasterContent

DELEGATION_PHRASES = [
    "teacher will distribute", "teacher will provide", "your teacher will give",
    "refer to the textbook", "see page", "open your textbook",
    "[insert primary source here]", "[insert", "teacher will hand out",
    "ask your teacher", "check with your teacher for",
]


def check_self_contained(text: str) -> list[str]:
    """Return a list of delegation-phrase violations found in *text*."""
    violations = []
    text_lower = text.lower()
    for phrase in DELEGATION_PHRASES:
        if phrase in text_lower:
            violations.append(f"Delegation phrase found: '{phrase}'")
    return violations


def validate_master_content(mc: "MasterContent", topic: str) -> list[str]:
    """Validate a MasterContent object for required collections and topic alignment."""
    errors = []
    if len(mc.guided_notes) < 1:
        errors.append("No guided notes generated")
    if len(mc.exit_ticket) < 1:
        errors.append("No exit ticket questions generated")
    if len(mc.primary_sources) < 1:
        errors.append("No primary sources generated")
    if len(mc.direct_instruction) < 1:
        errors.append("No instruction sections generated")
    if topic.lower() not in mc.title.lower() and topic.lower() not in mc.topic.lower():
        errors.append(f"Topic drift: requested '{topic}', got '{mc.title}'")
    for q in mc.exit_ticket:
        if not q.stimulus.strip():
            errors.append(f"Exit ticket question missing stimulus: '{q.question[:50]}'")
    return errors


def validate_alignment(mc: "MasterContent") -> tuple[float, list[str]]:
    """Check cross-document alignment within a MasterContent.

    Returns a (score, issues) tuple where *score* is the percentage of guided
    note answers found verbatim in the direct instruction text (0–100).
    """
    issues = []
    total_notes = len(mc.guided_notes)
    matched = 0
    all_instruction_text = " ".join(
        s.content + " " + " ".join(s.key_points) for s in mc.direct_instruction
    ).lower()
    for note in mc.guided_notes:
        if note.answer.lower() in all_instruction_text:
            matched += 1
        else:
            issues.append(f"Guided note answer '{note.answer}' not found in instruction")
    source_ids = {s.id for s in mc.primary_sources}
    for station in mc.stations:
        if station.source_ref not in source_ids:
            issues.append(
                f"Station '{station.title}' references unknown source '{station.source_ref}'"
            )
    for i, q in enumerate(mc.exit_ticket):
        if not q.stimulus.strip():
            issues.append(f"Exit ticket question {i + 1} has empty stimulus")
    score = (matched / total_notes * 100) if total_notes > 0 else 0.0
    return score, issues


# ── Per-type validators ────────────────────────────────────────────────────


def validate_quiz(quiz, topic: str, requested_count: int) -> list[str]:
    """Validate a Quiz for non-empty questions, correct count, and topic alignment."""
    errors = []
    if not quiz.questions:
        errors.append("No questions generated in quiz")
    elif len(quiz.questions) != requested_count:
        errors.append(
            f"Wrong question count: expected {requested_count}, got {len(quiz.questions)}"
        )
    if topic.lower() not in quiz.topic.lower():
        errors.append(f"Topic drift: requested '{topic}', got '{quiz.topic}'")
    return errors


def validate_rubric(rubric, requested_criteria: int) -> list[str]:
    """Validate a Rubric for non-empty criteria and correct count."""
    errors = []
    if not rubric.criteria:
        errors.append("No criteria generated in rubric")
    elif len(rubric.criteria) != requested_criteria:
        errors.append(
            f"Wrong criteria count: expected {requested_criteria}, got {len(rubric.criteria)}"
        )
    return errors


def validate_year_map(ym, subject: str) -> list[str]:
    """Validate a YearMap for non-empty units and subject alignment."""
    errors = []
    if not ym.units:
        errors.append("No units generated in year map")
    if subject.lower() not in ym.subject.lower():
        errors.append(f"Subject drift: requested '{subject}', got '{ym.subject}'")
    return errors


def validate_unit_plan(up, topic: str) -> list[str]:
    """Validate a UnitPlan for non-empty lessons and topic alignment."""
    errors = []
    if not up.daily_lessons:
        errors.append("No daily lessons generated in unit plan")
    if topic.lower() not in up.title.lower() and topic.lower() not in up.topic.lower():
        errors.append(f"Topic drift: requested '{topic}', got '{up.title}'")
    return errors


def validate_formative(fa) -> list[str]:
    """Validate a FormativeAssessment for non-empty questions and objective."""
    errors = []
    if not fa.questions:
        errors.append("No questions generated in formative assessment")
    if not fa.objective.strip():
        errors.append("Formative assessment has no objective")
    return errors


def validate_summative(sa) -> list[str]:
    """Validate a SummativeAssessment for non-empty questions and objectives."""
    errors = []
    if not sa.questions:
        errors.append("No questions generated in summative assessment")
    if not sa.objectives:
        errors.append("No objectives listed in summative assessment")
    return errors


def validate_dbq(dbq) -> list[str]:
    """Validate a DBQAssessment for non-empty documents and essay prompt."""
    errors = []
    if not dbq.documents:
        errors.append("No documents generated in DBQ assessment")
    if not dbq.essay_prompt.strip():
        errors.append("DBQ assessment has no essay prompt")
    return errors


def validate_lesson_materials(mats) -> list[str]:
    """Validate LessonMaterials for non-empty worksheet items and assessment questions."""
    errors = []
    if not mats.worksheet_items:
        errors.append("No worksheet items generated in lesson materials")
    if not mats.assessment_questions:
        errors.append("No assessment questions generated in lesson materials")
    return errors


def validate_pacing_guide(pg) -> list[str]:
    """Validate a PacingGuide for non-empty weeks and a start date."""
    errors = []
    if not pg.weeks:
        errors.append("No weeks generated in pacing guide")
    if not pg.start_date.strip():
        errors.append("Pacing guide has no start date")
    return errors
