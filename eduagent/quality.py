"""Lesson Quality Score Engine — score generated lesson plans on multiple dimensions."""

from __future__ import annotations

from typing import Any

from eduagent.llm import LLMClient
from eduagent.models import AppConfig, DailyLesson, LessonMaterials


class LessonQualityScore:
    """Score a generated lesson plan on multiple dimensions."""

    dimensions = [
        "objective_clarity",
        "do_now_relevance",
        "instruction_depth",
        "differentiation_quality",
        "exit_ticket_alignment",
        "materials_completeness",
    ]

    dimension_descriptions = {
        "objective_clarity": "Is the SWBAT measurable and specific?",
        "do_now_relevance": "Does the warm-up connect to the objective?",
        "instruction_depth": "Is the direct instruction substantive?",
        "differentiation_quality": "Are accommodations specific, not generic?",
        "exit_ticket_alignment": "Do exit ticket questions test the objective?",
        "materials_completeness": "Does the worksheet cover key concepts?",
    }

    def __init__(self, config: AppConfig | None = None):
        self.client = LLMClient(config)

    async def score(
        self, lesson: DailyLesson, materials: LessonMaterials | None = None
    ) -> dict[str, Any]:
        """Score each dimension 1-5 with brief explanation.

        Returns:
            {
                "objective_clarity": {"score": 4, "explanation": "..."},
                ...,
                "overall": 3.8
            }
        """
        lesson_text = self._lesson_to_text(lesson)
        materials_text = self._materials_to_text(materials) if materials else "No materials provided."

        dimensions_block = "\n".join(
            f"- {dim}: {desc}" for dim, desc in self.dimension_descriptions.items()
        )

        prompt = (
            "You are an expert instructional coach evaluating a lesson plan.\n\n"
            "## Lesson Plan\n"
            f"{lesson_text}\n\n"
            "## Materials\n"
            f"{materials_text}\n\n"
            "## Scoring Dimensions\n"
            f"{dimensions_block}\n\n"
            "## Task\n"
            "Score each dimension from 1-5 (1=poor, 5=excellent). "
            "For each, provide a 1-sentence explanation.\n\n"
            "Return valid JSON with this exact structure:\n"
            "{\n"
            '  "objective_clarity": {"score": <int>, "explanation": "<string>"},\n'
            '  "do_now_relevance": {"score": <int>, "explanation": "<string>"},\n'
            '  "instruction_depth": {"score": <int>, "explanation": "<string>"},\n'
            '  "differentiation_quality": {"score": <int>, "explanation": "<string>"},\n'
            '  "exit_ticket_alignment": {"score": <int>, "explanation": "<string>"},\n'
            '  "materials_completeness": {"score": <int>, "explanation": "<string>"}\n'
            "}\n"
            "Return ONLY the JSON object, nothing else."
        )

        raw = await self.client.generate_json(
            prompt=prompt,
            system="You are a lesson quality evaluator. Return only valid JSON.",
            temperature=0.3,
            max_tokens=2000,
        )

        # Validate and normalize scores
        result: dict[str, Any] = {}
        scores = []
        for dim in self.dimensions:
            entry = raw.get(dim, {"score": 3, "explanation": "Not evaluated."})
            score_val = max(1, min(5, int(entry.get("score", 3))))
            result[dim] = {
                "score": score_val,
                "explanation": str(entry.get("explanation", "")),
            }
            scores.append(score_val)

        result["overall"] = round(sum(scores) / len(scores), 2) if scores else 0.0
        return result

    @staticmethod
    def _lesson_to_text(lesson: DailyLesson) -> str:
        parts = [
            f"Title: {lesson.title}",
            f"Objective: {lesson.objective}",
            f"Standards: {', '.join(lesson.standards) if lesson.standards else 'None'}",
            f"Do-Now: {lesson.do_now}",
            f"Direct Instruction: {lesson.direct_instruction}",
            f"Guided Practice: {lesson.guided_practice}",
            f"Independent Work: {lesson.independent_work}",
        ]
        if lesson.exit_ticket:
            parts.append("Exit Ticket Questions:")
            for et in lesson.exit_ticket:
                parts.append(f"  - {et.question}")
        if lesson.differentiation:
            diff = lesson.differentiation
            if diff.struggling:
                parts.append(f"Struggling learners: {'; '.join(diff.struggling)}")
            if diff.advanced:
                parts.append(f"Advanced learners: {'; '.join(diff.advanced)}")
            if diff.ell:
                parts.append(f"ELL: {'; '.join(diff.ell)}")
        return "\n".join(parts)

    @staticmethod
    def _materials_to_text(materials: LessonMaterials) -> str:
        parts = [f"Lesson Title: {materials.lesson_title}"]
        if materials.worksheet_items:
            parts.append(f"Worksheet: {len(materials.worksheet_items)} items")
            for item in materials.worksheet_items[:5]:
                parts.append(f"  - {item.prompt}")
        if materials.assessment_questions:
            parts.append(f"Assessment: {len(materials.assessment_questions)} questions")
        return "\n".join(parts)
