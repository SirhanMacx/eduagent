"""Tool: generate_lesson — wraps clawed.lesson.generate_lesson."""
from __future__ import annotations

import json
from typing import Any

from clawed.agent_core.context import AgentContext, ToolResult


class GenerateLessonTool:
    """Generate a complete daily lesson plan on a topic."""

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "generate_lesson",
                "description": (
                    "Generate a complete daily lesson plan on a topic. "
                    "Returns a structured lesson with Do Now, instruction, activities, "
                    "exit ticket, and differentiation."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "The lesson topic",
                        },
                        "grade": {
                            "type": "string",
                            "description": "Grade level (e.g. '8', 'K')",
                            "default": "8",
                        },
                        "subject": {
                            "type": "string",
                            "description": "Subject area",
                            "default": "General",
                        },
                    },
                    "required": ["topic"],
                },
            },
        }

    async def execute(
        self, params: dict[str, Any], context: AgentContext
    ) -> ToolResult:
        from clawed.lesson import generate_lesson
        from clawed.models import LessonBrief, TeacherPersona, UnitPlan

        topic = params["topic"]
        grade = params.get("grade", "8")
        subject = params.get("subject", "General")

        config = context.config
        persona = TeacherPersona()
        if context.persona:
            try:
                persona = TeacherPersona(**context.persona)
            except Exception:
                pass

        unit = UnitPlan(
            title=f"{topic} Unit",
            subject=subject,
            grade_level=grade,
            topic=topic,
            duration_weeks=1,
            overview=f"A lesson on {topic}.",
            daily_lessons=[
                LessonBrief(
                    lesson_number=1,
                    topic=topic,
                    description=f"Introduction to {topic}",
                )
            ],
        )

        try:
            lesson = await generate_lesson(
                lesson_number=1,
                unit=unit,
                persona=persona,
                config=config,
            )
            lesson_data = lesson.model_dump()
            title = lesson_data.get("title", topic)
            return ToolResult(
                text=f"Generated lesson: {title}\n\n"
                f"{json.dumps(lesson_data, indent=2)[:2000]}",
                data=lesson_data,
                side_effects=[f"Generated lesson on {topic}"],
            )
        except Exception as e:
            return ToolResult(text=f"Failed to generate lesson: {e}")
