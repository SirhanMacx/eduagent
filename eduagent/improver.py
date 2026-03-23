"""Prompt improvement loop — analyzes feedback and generates improved prompt variants."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from eduagent.database import Database
from eduagent.feedback import analyze_feedback
from eduagent.llm import LLMClient
from eduagent.models import AppConfig

PROMPT_DIR = Path(__file__).parent / "prompts"

# Map prompt types to their template files
PROMPT_FILES: dict[str, str] = {
    "lesson_plan": "lesson_plan.txt",
    "unit_plan": "unit_plan.txt",
    "persona_extract": "persona_extract.txt",
    "worksheet": "worksheet.txt",
    "assessment": "assessment.txt",
    "differentiation": "differentiation.txt",
}


async def improve_prompts(
    db: Database,
    feedback_window_days: int = 7,
    config: AppConfig | None = None,
) -> dict[str, Any]:
    """Analyze recent feedback and generate improved prompt variants.

    Steps:
        1. Pull lessons with low ratings from last N days
        2. Pull teacher edit patterns (which sections get edited most)
        3. Ask LLM: "Given these examples of bad output and what teachers changed,
           how should the prompt be improved?"
        4. Generate 3 new prompt variants
        5. Store as prompt_versions with is_active=False
        6. Randomly assign new generations to test variants (A/B test)
        7. After 10 uses, promote winner to active

    Returns:
        Summary of what was improved.
    """
    analysis = analyze_feedback(db, feedback_window_days)

    if analysis["total_feedback"] == 0:
        return {"status": "no_feedback", "message": "No feedback collected yet. Generate and rate some lessons first."}

    if analysis["avg_rating"] >= 4.0 and analysis["low_rated_count"] == 0:
        msg = f"Prompts performing well (avg rating: {analysis['avg_rating']}). No improvement needed."
        return {"status": "good", "message": msg}

    # Collect examples of poorly-rated lessons
    low_rated_lessons = db.get_low_rated_lessons(max_rating=2, days=feedback_window_days)

    lesson_examples = ""
    for i, row in enumerate(low_rated_lessons[:3], 1):
        lesson_data = row.get("lesson_json", "{}")
        notes = row.get("feedback_notes", "")
        rating = row.get("feedback_rating", "?")
        lesson_examples += (
            f"\n--- Example {i} (rated {rating}/5) ---\n"
            f"Teacher notes: {notes}\n"
            f"Lesson excerpt: {lesson_data[:500]}\n"
        )

    # Determine which prompt type to improve based on edit patterns
    target_type = "lesson_plan"  # Default to lesson plan
    edited = analysis["most_edited_sections"]
    if edited:
        # If teachers mostly edit objectives/standards, improve unit planning
        plan_sections = {"overview", "essential_questions", "standards", "assessment_plan"}
        if any(s in plan_sections for s in edited):
            target_type = "unit_plan"

    # Load current prompt
    prompt_file = PROMPT_FILES.get(target_type, "lesson_plan.txt")
    current_prompt = (PROMPT_DIR / prompt_file).read_text()

    # Get current version number
    versions = db.get_prompt_versions(target_type)
    next_version = (versions[0]["version"] + 1) if versions else 2

    # Ask LLM to suggest improvements
    improvement_prompt = (
        f"You are an expert prompt engineer for educational AI systems.\n\n"
        f"## Current Prompt Template\n```\n{current_prompt[:2000]}\n```\n\n"
        f"## Feedback Analysis\n"
        f"- Average rating: {analysis['avg_rating']}/5\n"
        f"- Low-rated lessons: {analysis['low_rated_count']}\n"
        f"- Most edited sections: {', '.join(analysis['most_edited_sections']) or 'N/A'}\n"
        f"- Teacher complaints: {'; '.join(analysis['sample_notes'][:5]) or 'None recorded'}\n\n"
        f"## Examples of Poor Output\n{lesson_examples or 'No specific examples available.'}\n\n"
        f"## Task\n"
        f"Generate an improved version of this prompt that addresses the feedback.\n"
        f"Focus on: making output more practical, better aligned to teacher expectations, "
        f"and reducing the need for manual edits.\n\n"
        f"Return ONLY the improved prompt text, nothing else."
    )

    client = LLMClient(config)
    improved_text = await client.generate(
        prompt=improvement_prompt,
        system="You are a prompt engineering expert. Return only the improved prompt template.",
        temperature=0.5,
        max_tokens=4000,
    )

    # Store the new variant
    prompt_id = db.insert_prompt_version(target_type, next_version, improved_text)

    # Check if any prior versions have enough usage to promote
    _check_and_promote(db, target_type)

    return {
        "status": "improved",
        "prompt_type": target_type,
        "new_version": next_version,
        "prompt_id": prompt_id,
        "feedback_summary": analysis,
        "message": f"Generated improved {target_type} prompt (version {next_version}).",
    }


def _check_and_promote(db: Database, prompt_type: str) -> None:
    """Check if any test variants have enough usage data to promote."""
    versions = db.get_prompt_versions(prompt_type)
    candidates = [v for v in versions if v["usage_count"] >= 10 and not v["is_active"]]
    if not candidates:
        return

    # Find the best-performing variant
    best = max(candidates, key=lambda v: v["avg_rating"] or 0)
    active = db.get_active_prompt(prompt_type)

    if active and best.get("avg_rating", 0) and active.get("avg_rating", 0):
        if best["avg_rating"] > active["avg_rating"]:
            db.promote_prompt(best["id"], prompt_type)
