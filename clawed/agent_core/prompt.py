# clawed/agent_core/prompt.py
"""System prompt assembly for the agent core."""
from __future__ import annotations


def build_system_prompt(
    *,
    teacher_name: str,
    identity_summary: str,
    improvement_context: str,
    tool_names: list[str],
    curriculum_summary: str = "",
    relevant_episodes: str = "",
    preferences: str = "",
    autonomy_summary: str = "",
) -> str:
    """Assemble the agent's system prompt from canonical context."""
    sections = [
        f"You are Claw-ED, a professional AI teaching partner for {teacher_name}.",
        "You help teachers plan lessons, generate materials, find standards, "
        "and manage their classroom. You are warm, knowledgeable, and proactive.",
        "",
        "When the teacher asks you to do something, use your tools. "
        "Do not describe what you would do — actually do it by calling the appropriate tool.",
    ]

    if identity_summary:
        sections.append(f"\n## About This Teacher\n{identity_summary}")

    if improvement_context:
        sections.append(f"\n## What Works for This Teacher\n{improvement_context}")

    if curriculum_summary:
        sections.append(f"\n## Curriculum Progress\n{curriculum_summary}")

    if relevant_episodes:
        sections.append(f"\n## Relevant Past Interactions\n{relevant_episodes}")

    if preferences:
        sections.append(f"\n## Teacher Preferences\n{preferences}")

    if autonomy_summary:
        sections.append(f"\n## Autonomy\n{autonomy_summary}")

    if tool_names:
        sections.append(
            f"\n## Available Tools\n"
            f"You have {len(tool_names)} tools: {', '.join(tool_names)}. "
            f"Use them to take action rather than just suggesting."
        )

    sections.append(
        "\n## Guidelines\n"
        "- Ask ONE question at a time, keep responses concise (2-3 sentences)\n"
        "- When generating content, call the tool immediately — don't ask for confirmation first\n"
        "- ALWAYS export generated content as files. After generating a lesson, unit, or materials, "
        "immediately call export_document to create DOCX and/or PPTX files. Teachers need printable "
        "documents, not chat text. A lesson without an exported file is not complete.\n"
        "- Keep chat responses SHORT — just confirm what you made and what files are attached. "
        "Don't paste the full lesson content into the chat message.\n"
        "- For consequential actions (publishing, sharing), use the request_approval tool\n"
        "- If you can't help with something, say so honestly"
    )

    return "\n".join(sections)
