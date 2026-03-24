"""Multi-step onboarding for new teachers.

State machine: ask_subject → ask_grade → ask_name → done.
Extracted from tg.py lines 1156-1263.
"""
from __future__ import annotations

import re
from enum import Enum

from eduagent.gateway_response import GatewayResponse
from eduagent.models import AppConfig, LLMProvider, TeacherProfile, TeacherPersona


class OnboardState(Enum):
    ASK_SUBJECT = "ask_subject"
    ASK_GRADE = "ask_grade"
    ASK_NAME = "ask_name"
    DONE = "done"


def _parse_grade_and_subject(text: str) -> tuple[str, str]:
    """Parse '8th grade math' into (grade, subject).

    Copied verbatim from tg.py lines 384-422 to preserve exact behavior.
    Returns (grade, subject) where either may be empty string if not found.
    """
    text = text.strip()
    grade = ""
    subject = text

    grade_match = re.search(
        r'(?:(\d{1,2})(?:st|nd|rd|th)?\s*grade)|(?:grade\s*(\d{1,2}))',
        text,
        re.IGNORECASE,
    )
    if grade_match:
        grade = grade_match.group(1) or grade_match.group(2)
        subject = text[:grade_match.start()] + text[grade_match.end():]
        subject = subject.strip().strip("-,. ")

    if subject:
        subject = subject.strip()
        words = subject.split()
        capitalized = []
        for w in words:
            if w.upper() in ("AP", "IB", "ELA"):
                capitalized.append(w.upper())
            else:
                capitalized.append(w.capitalize())
        subject = " ".join(capitalized)

    return grade, subject


class OnboardHandler:
    """Manages conversational onboarding state per teacher."""

    def __init__(self):
        self._state: dict[str, dict] = {}

    def is_onboarding(self, teacher_id: str) -> bool:
        return teacher_id in self._state

    async def step(self, teacher_id: str, text: str) -> GatewayResponse:
        """Advance onboarding by one step."""
        if teacher_id not in self._state:
            self._state[teacher_id] = {
                "step": OnboardState.ASK_SUBJECT,
                "subject": None,
                "grade": None,
                "name": None,
            }
            return GatewayResponse(
                text=(
                    "Welcome! Let's get you set up.\n\n"
                    "What subject do you teach? "
                    "(You can say something like '8th grade math')"
                ),
            )

        state = self._state[teacher_id]
        current = state["step"]

        if current == OnboardState.ASK_SUBJECT:
            grade, subject = _parse_grade_and_subject(text)
            state["subject"] = subject if subject else text.strip().title()
            if grade:
                state["grade"] = grade
                state["step"] = OnboardState.ASK_NAME
                return GatewayResponse(
                    text=f"Got it — {state['subject']}, grade {grade}.\n\nWhat's your name?"
                )
            state["step"] = OnboardState.ASK_GRADE
            return GatewayResponse(
                text=f"Great — {state['subject']}!\n\nWhat grade level do you teach?"
            )

        if current == OnboardState.ASK_GRADE:
            grade_match = re.search(r"(\d{1,2})", text)
            if grade_match:
                state["grade"] = grade_match.group(1)
            elif re.search(r"(?:kindergarten|kinder|pre-?k)", text, re.IGNORECASE):
                state["grade"] = "K"
            else:
                state["grade"] = text.strip()
            state["step"] = OnboardState.ASK_NAME
            return GatewayResponse(
                text=f"Grade {state['grade']} — got it.\n\nWhat's your name?"
            )

        if current == OnboardState.ASK_NAME:
            state["name"] = text.strip()
            return self._complete_onboarding(teacher_id)

        return GatewayResponse(text="Something went wrong with setup. Try /start again.")

    def _complete_onboarding(self, teacher_id: str) -> GatewayResponse:
        """Finalize onboarding: create TeacherProfile + AppConfig, save, clean up."""
        state = self._state[teacher_id]

        profile = TeacherProfile(
            name=state["name"],
            subjects=[state["subject"]],
            grade_levels=[state["grade"]],
        )
        config = AppConfig.load()
        config.teacher_profile = profile
        config.save()

        try:
            from eduagent.workspace import init_workspace
            persona = TeacherPersona(name=state["name"], subject_area=state["subject"])
            init_workspace(persona, config)
        except Exception:
            pass

        del self._state[teacher_id]

        return GatewayResponse(
            text=(
                f"You're all set, {state['name']}!\n\n"
                f"Subject: {state['subject']}\n"
                f"Grade: {state['grade']}\n\n"
                "Try: 'plan a unit on [topic]' or 'make a lesson on [topic]'"
            ),
        )
