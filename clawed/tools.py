"""Claw-ED tools -- functions the conversational agent can call.

These are the tools available during freeform chat. When a teacher
asks something that needs action (generate a lesson, look up standards,
read a file), the LLM can call these tools.

Reuses implementations from the MCP server and handlers where possible.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# -- Tool definitions (OpenAI function-calling format) ---------------------

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "generate_lesson",
            "description": "Generate a complete daily lesson plan on a topic",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "The lesson topic"},
                    "grade": {"type": "string", "description": "Grade level (e.g. '8', 'K')"},
                    "subject": {"type": "string", "description": "Subject area (e.g. 'Math', 'Science')"},
                },
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_unit",
            "description": "Generate a multi-week unit plan with daily lesson sequence",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "The unit topic"},
                    "grade": {"type": "string", "description": "Grade level"},
                    "subject": {"type": "string", "description": "Subject area"},
                    "weeks": {"type": "integer", "description": "Duration in weeks (1-6)", "default": 2},
                },
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_quiz",
            "description": "Generate a quiz or assessment on a topic",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Quiz topic"},
                    "grade": {"type": "string", "description": "Grade level"},
                    "num_questions": {"type": "integer", "description": "Number of questions", "default": 10},
                },
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_standards",
            "description": "Look up curriculum standards for a subject and grade level",
            "parameters": {
                "type": "object",
                "properties": {
                    "subject": {"type": "string", "description": "Subject (e.g. 'math', 'science')"},
                    "grade": {"type": "string", "description": "Grade level"},
                },
                "required": ["subject"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_persona",
            "description": "Read the current teacher's persona/teaching style profile",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List generated files (lessons, units, exports) in the teacher's output directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Which directory to list: 'output', 'workspace', or 'all'",
                        "default": "all",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read and return the contents of a generated file (lesson, unit, etc.)",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search generated files by keyword in filenames and content",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search term"},
                },
                "required": ["query"],
            },
        },
    },
]


# -- Tool implementations -------------------------------------------------


async def execute_tool(name: str, arguments: dict[str, Any], teacher_id: str = "") -> str:
    """Execute a tool by name and return the result as a string."""
    try:
        if name == "generate_lesson":
            return await _tool_generate_lesson(**arguments)
        elif name == "generate_unit":
            return await _tool_generate_unit(**arguments)
        elif name == "generate_quiz":
            return await _tool_generate_quiz(**arguments)
        elif name == "search_standards":
            return await _tool_search_standards(**arguments)
        elif name == "read_persona":
            return await _tool_read_persona(teacher_id)
        elif name == "list_files":
            return _tool_list_files(**arguments)
        elif name == "read_file":
            return _tool_read_file(**arguments)
        elif name == "search_files":
            return _tool_search_files(**arguments)
        else:
            return json.dumps({"error": f"Unknown tool: {name}"})
    except Exception as e:
        logger.error("Tool %s failed: %s", name, e)
        return json.dumps({"error": str(e)})


async def _tool_generate_lesson(topic: str, grade: str = "8", subject: str = "General") -> str:
    """Generate a lesson -- reuses existing lesson generation."""
    from clawed.lesson import generate_lesson
    from clawed.models import AppConfig, LessonBrief, TeacherPersona, UnitPlan

    config = AppConfig.load()
    persona = TeacherPersona()
    try:
        from clawed.persona import load_persona
        persona = load_persona(Path.home() / ".eduagent" / "persona.json")
    except Exception:
        pass

    unit = UnitPlan(
        title=f"{topic} Unit", subject=subject, grade_level=grade, topic=topic,
        duration_weeks=1, overview=f"A lesson on {topic}.",
        daily_lessons=[LessonBrief(lesson_number=1, topic=topic, description=f"Introduction to {topic}")],
    )
    lesson = await generate_lesson(lesson_number=1, unit=unit, persona=persona, config=config)
    # Return a readable summary, not raw JSON
    lines = [f"**{lesson.title}**", f"Objective: {lesson.objective}", ""]
    if lesson.do_now:
        lines.append(f"**Do Now:** {lesson.do_now[:300]}")
    if lesson.direct_instruction:
        lines.append(f"\n**Direct Instruction:** {lesson.direct_instruction[:500]}")
    if lesson.guided_practice:
        lines.append(f"\n**Guided Practice:** {lesson.guided_practice[:300]}")
    if lesson.exit_ticket:
        lines.append(f"\n**Exit Ticket:** {len(lesson.exit_ticket)} question(s)")
    return "\n".join(lines)


async def _tool_generate_unit(topic: str, grade: str = "8", subject: str = "General", weeks: int = 2) -> str:
    """Generate a unit plan."""
    from clawed.models import AppConfig, TeacherPersona
    from clawed.planner import plan_unit

    config = AppConfig.load()
    persona = TeacherPersona()
    try:
        from clawed.persona import load_persona
        persona = load_persona(Path.home() / ".eduagent" / "persona.json")
    except Exception:
        pass

    unit = await plan_unit(
        subject=subject, grade_level=grade, topic=topic,
        duration_weeks=weeks, persona=persona, config=config,
    )
    lines = [f"**{unit.title}** ({unit.duration_weeks} weeks, {len(unit.daily_lessons)} lessons)"]
    for q in unit.essential_questions[:3]:
        lines.append(f"  - {q}")
    for brief in unit.daily_lessons:
        lines.append(f"  Lesson {brief.lesson_number}: {brief.topic}")
    return "\n".join(lines)


async def _tool_generate_quiz(topic: str, grade: str = "8", num_questions: int = 10) -> str:
    """Generate a quiz."""
    from clawed.assessment import AssessmentGenerator
    from clawed.models import AppConfig

    config = AppConfig.load()
    gen = AssessmentGenerator(config)
    quiz = await gen.generate_quiz(topic=topic, question_count=num_questions, grade=grade)
    lines = [f"**Quiz: {quiz.topic}** ({quiz.total_points} points, {len(quiz.questions)} questions)"]
    for q in quiz.questions[:5]:
        lines.append(f"  {q.question_number}. {q.question[:100]}")
    if len(quiz.questions) > 5:
        lines.append(f"  ... and {len(quiz.questions) - 5} more")
    return "\n".join(lines)


async def _tool_search_standards(subject: str, grade: str = "") -> str:
    """Look up curriculum standards."""
    from clawed.standards import get_standards
    results = get_standards(subject, grade or None)
    if not results:
        return f"No standards found for {subject} grade {grade}."
    lines = [f"Standards for {subject.title()} Grade {grade}:"]
    for code, desc, _band in results[:10]:
        lines.append(f"  {code}: {desc}")
    if len(results) > 10:
        lines.append(f"  ... and {len(results) - 10} more")
    return "\n".join(lines)


async def _tool_read_persona(teacher_id: str = "") -> str:
    """Read the teacher's persona."""
    try:
        from clawed.state import TeacherSession
        session = TeacherSession.load(teacher_id or "local-teacher")
        if session.persona:
            return session.persona.to_prompt_context()
        return "No persona configured yet. Run 'clawed ingest <folder>' to learn your teaching style."
    except Exception:
        return "No persona available."


def _tool_list_files(directory: str = "all") -> str:
    """List files in teacher's output/workspace directories."""
    dirs_to_check: list[tuple[str, Path]] = []
    base = Path.home() / ".eduagent"

    if directory in ("output", "all"):
        dirs_to_check.append(("Generated Output", Path("clawed_output").resolve()))
        dirs_to_check.append(("Generated Output (legacy)", Path("eduagent_output").resolve()))
    if directory in ("workspace", "all"):
        dirs_to_check.append(("Workspace", base / "workspace"))

    lines: list[str] = []
    for label, d in dirs_to_check:
        if not d.exists():
            continue
        files = sorted(d.rglob("*"))
        files = [f for f in files if f.is_file() and not f.name.startswith(".")]
        if files:
            lines.append(f"**{label}** ({d}):")
            for f in files[:20]:
                size = f.stat().st_size
                lines.append(f"  {f.relative_to(d)} ({size:,} bytes)")
            if len(files) > 20:
                lines.append(f"  ... and {len(files) - 20} more files")
    if not lines:
        return "No generated files found yet. Generate a lesson with 'lesson on [topic]'."
    return "\n".join(lines)


def _tool_read_file(path: str) -> str:
    """Read a file and return its contents (truncated if large)."""
    p = Path(path).expanduser().resolve()
    # Security: only allow reading from known directories
    allowed = [Path.home() / ".eduagent", Path("clawed_output").resolve(), Path("eduagent_output").resolve()]
    if not any(str(p).startswith(str(a)) for a in allowed):
        return "Cannot read files outside of Claw-ED directories."
    if not p.exists():
        return f"File not found: {path}"
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
        if len(content) > 3000:
            return content[:3000] + f"\n\n... (truncated, {len(content):,} chars total)"
        return content
    except Exception as e:
        return f"Could not read file: {e}"


def _tool_search_files(query: str) -> str:
    """Search filenames and content for a keyword."""
    query_lower = query.lower()
    matches: list[str] = []
    dirs = [Path.home() / ".eduagent", Path("clawed_output").resolve(), Path("eduagent_output").resolve()]
    for d in dirs:
        if not d.exists():
            continue
        for f in d.rglob("*"):
            if not f.is_file() or f.name.startswith("."):
                continue
            if query_lower in f.name.lower():
                matches.append(f"  {f} (filename match)")
                continue
            try:
                if f.suffix in (".json", ".txt", ".md") and f.stat().st_size < 100_000:
                    content = f.read_text(encoding="utf-8", errors="replace")
                    if query_lower in content.lower():
                        matches.append(f"  {f} (content match)")
            except Exception:
                pass
            if len(matches) >= 15:
                break
    if not matches:
        return f"No files matching '{query}' found."
    return f"Files matching '{query}':\n" + "\n".join(matches)
