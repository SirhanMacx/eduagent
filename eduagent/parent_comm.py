"""Parent communication generator — professional parent emails and notes."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from eduagent.llm import LLMClient


class CommType(str, Enum):
    """Types of parent communications."""

    PROGRESS_UPDATE = "progress_update"
    BEHAVIOR_CONCERN = "behavior_concern"
    POSITIVE_NOTE = "positive_note"
    UPCOMING_UNIT = "upcoming_unit"
    PERMISSION_REQUEST = "permission_request"
    GENERAL_UPDATE = "general_update"


_COMM_TYPE_LABELS: dict[CommType, str] = {
    CommType.PROGRESS_UPDATE: "Progress Update",
    CommType.BEHAVIOR_CONCERN: "Behavior Concern",
    CommType.POSITIVE_NOTE: "Positive Note",
    CommType.UPCOMING_UNIT: "Upcoming Unit Announcement",
    CommType.PERMISSION_REQUEST: "Permission Request",
    CommType.GENERAL_UPDATE: "General Update",
}


class ParentCommRequest(BaseModel):
    """Everything the generator needs to create a parent communication."""

    comm_type: CommType
    student_description: str
    class_context: str
    tone: str = "professional and warm"
    additional_notes: str = ""


class ParentComm(BaseModel):
    """A complete parent communication ready to send."""

    comm_type: CommType
    subject_line: str
    email_body: str
    follow_up_suggestions: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.now)


_SYSTEM_PROMPT = (
    "You are an experienced teacher writing a professional email to a parent or "
    "guardian. Write in a tone that is {tone}. Be clear, specific, and actionable. "
    "Never use the student's real name — use 'your child' or 'your student' instead."
)

_USER_PROMPT_TEMPLATE = """\
Generate a parent communication email as JSON.

Communication type: {comm_type_label}
Student description: {student_description}
Class context: {class_context}
Tone: {tone}
{additional_line}

Return a JSON object with these exact keys:
- "subject_line": A concise, professional email subject line.
- "email_body": The full email text. Include a greeting, body paragraphs, and \
a professional closing with the teacher's name placeholder "[Teacher Name]". \
Do NOT use any real student names — say "your child" or "your student".
- "follow_up_suggestions": A list of 2-4 suggested follow-up actions the \
teacher could take (e.g. "Schedule a parent-teacher conference", \
"Send a follow-up in two weeks").

Return ONLY the JSON object, no markdown fences."""


async def generate_parent_comm(
    request: ParentCommRequest,
    llm: LLMClient,
) -> ParentComm:
    """Generate a complete parent communication email via LLM."""
    comm_type_label = _COMM_TYPE_LABELS.get(
        request.comm_type, request.comm_type.value.replace("_", " ").title()
    )
    additional_line = (
        f"Additional notes: {request.additional_notes}\n"
        if request.additional_notes
        else ""
    )

    prompt = _USER_PROMPT_TEMPLATE.format(
        comm_type_label=comm_type_label,
        student_description=request.student_description,
        class_context=request.class_context,
        tone=request.tone,
        additional_line=additional_line,
    )

    system = _SYSTEM_PROMPT.format(tone=request.tone)

    data = await llm.generate_json(
        prompt=prompt,
        system=system,
        temperature=0.6,
        max_tokens=4096,
    )

    return ParentComm(
        comm_type=request.comm_type,
        subject_line=data.get("subject_line", ""),
        email_body=data.get("email_body", ""),
        follow_up_suggestions=data.get("follow_up_suggestions", []),
    )


def parent_comm_to_text(comm: ParentComm) -> str:
    """Format a ParentComm for output (email-ready text)."""
    lines: list[str] = []
    lines.append(f"Subject: {comm.subject_line}")
    lines.append("")
    lines.append(comm.email_body)
    lines.append("")

    if comm.follow_up_suggestions:
        lines.append("---")
        lines.append("Suggested follow-ups:")
        for suggestion in comm.follow_up_suggestions:
            lines.append(f"  - {suggestion}")

    return "\n".join(lines)
