"""Tool: configure_profile — wraps teacher profile configuration."""
from __future__ import annotations

from typing import Any

from clawed.agent_core.context import AgentContext, ToolResult


class ConfigureProfileTool:
    """Configure the teacher's profile (name, subject, grade levels)."""

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "configure_profile",
                "description": (
                    "Save or update the teacher's profile during onboarding. "
                    "Sets name, subject, grade levels, and state."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "teacher_name": {
                            "type": "string",
                            "description": "The teacher's name",
                        },
                        "subject": {
                            "type": "string",
                            "description": "Primary subject area",
                        },
                        "grade_levels": {
                            "type": "string",
                            "description": "Comma-separated grade levels (e.g. '6,7,8')",
                            "default": "",
                        },
                        "state": {
                            "type": "string",
                            "description": "US state for state standards (e.g. 'NY')",
                            "default": "",
                        },
                    },
                    "required": ["teacher_name", "subject"],
                },
            },
        }

    async def execute(
        self, params: dict[str, Any], context: AgentContext
    ) -> ToolResult:
        from clawed.models import TeacherPersona, TeacherProfile
        from clawed.state import TeacherSession

        teacher_name = params["teacher_name"]
        subject = params["subject"]
        grade_levels_str = params.get("grade_levels", "")
        state = params.get("state", "")

        grades = [g.strip() for g in grade_levels_str.split(",") if g.strip()]

        try:
            config = context.config
            config.teacher_profile = TeacherProfile(
                name=teacher_name,
                subjects=[subject],
                grade_levels=grades,
                state=state,
            )
            config.save()

            persona = TeacherPersona(name=teacher_name, subject_area=subject)
            session = TeacherSession.load(context.teacher_id or "local-teacher")
            session.persona = persona
            session.save()

            try:
                from clawed.workspace import init_workspace
                init_workspace(persona, config)
            except Exception:
                pass

            return ToolResult(
                text=f"Profile saved: {teacher_name}, {subject}"
                f"{', grades ' + grade_levels_str if grades else ''}.",
                data={
                    "teacher_name": teacher_name,
                    "subject": subject,
                    "grade_levels": grades,
                    "state": state,
                },
                side_effects=["Updated teacher profile and persona"],
            )
        except Exception as e:
            return ToolResult(text=f"Failed to configure profile: {e}")
