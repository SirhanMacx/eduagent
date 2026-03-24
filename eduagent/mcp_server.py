"""EDUagent MCP Server — expose teaching tools via Model Context Protocol.

This lets OpenClaw, Claude Desktop, and other MCP clients call EDUagent
tools directly: generate lessons, plan units, ingest materials, answer
student questions, and look up standards.

Usage:
    eduagent mcp-server              # stdio transport (default for MCP)
    eduagent mcp-server --port 8100  # SSE transport for network access
"""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "EDUagent",
    instructions=(
        "EDUagent is an AI teaching assistant. Use these tools to generate "
        "lesson plans, unit plans, materials, answer student questions, and "
        "look up education standards — all in a specific teacher's voice."
    ),
)


@mcp.tool()
async def generate_lesson(
    topic: str,
    grade: str = "8",
    subject: str = "General",
    persona_path: str = "",
) -> str:
    """Generate a complete daily lesson plan in the teacher's voice.

    Args:
        topic: The lesson topic (e.g., "photosynthesis", "fractions")
        grade: Grade level (e.g., "8", "K", "11")
        subject: Subject area (e.g., "Science", "Math", "History")
        persona_path: Optional path to persona JSON file
    """
    from eduagent.lesson import generate_lesson as gen_lesson
    from eduagent.models import AppConfig, LessonBrief, TeacherPersona, UnitPlan

    config = AppConfig.load()
    persona = TeacherPersona()

    if persona_path:
        from pathlib import Path

        p = Path(persona_path).expanduser()
        if p.exists():
            persona = TeacherPersona.model_validate_json(p.read_text(encoding="utf-8"))

    # Create minimal unit context for standalone lesson
    unit = UnitPlan(
        title=f"{topic} Unit",
        subject=subject,
        grade_level=grade,
        topic=topic,
        duration_weeks=1,
        overview=f"A lesson on {topic}.",
        daily_lessons=[
            LessonBrief(lesson_number=1, topic=topic, description=f"Introduction to {topic}")
        ],
    )

    lesson = await gen_lesson(lesson_number=1, unit=unit, persona=persona, config=config)
    return lesson.model_dump_json(indent=2)


@mcp.tool()
async def generate_unit(
    topic: str,
    grade: str = "8",
    subject: str = "General",
    weeks: int = 2,
) -> str:
    """Generate a multi-week unit plan with daily lesson sequence.

    Args:
        topic: The unit topic (e.g., "American Revolution", "Ecosystems")
        grade: Grade level
        subject: Subject area
        weeks: Duration in weeks (1-6)
    """
    from eduagent.models import AppConfig, TeacherPersona
    from eduagent.planner import plan_unit

    config = AppConfig.load()
    persona = TeacherPersona()

    unit = await plan_unit(
        subject=subject,
        grade_level=grade,
        topic=topic,
        duration_weeks=weeks,
        persona=persona,
        config=config,
    )
    return unit.model_dump_json(indent=2)


@mcp.tool()
async def ingest_materials(path: str) -> str:
    """Ingest teaching materials and extract a teacher persona.

    Args:
        path: Path to a directory, ZIP file, or single file containing teaching materials
    """
    from pathlib import Path as _Path

    from eduagent.ingestor import ingest_path
    from eduagent.models import AppConfig
    from eduagent.persona import extract_persona

    source = _Path(path).expanduser().resolve()
    docs = ingest_path(source)

    if not docs:
        return json.dumps({"error": "No supported documents found", "path": str(source)})

    config = AppConfig.load()
    persona = await extract_persona(docs, config)

    return json.dumps({
        "documents_ingested": len(docs),
        "persona": json.loads(persona.model_dump_json()),
    }, indent=2)


@mcp.tool()
async def student_question(
    question: str,
    class_code: str,
    student_id: str = "mcp-student",
) -> str:
    """Answer a student question using the active lesson context and teacher's voice.

    Args:
        question: The student's question about the lesson
        class_code: The class code provided by the teacher
        student_id: Optional student identifier
    """
    from eduagent.student_bot import StudentBot

    bot = StudentBot()
    answer = await bot.handle_message(question, student_id, class_code)
    return answer


@mcp.tool()
async def get_teacher_standards(
    state: str = "",
    subjects: str = "",
    grades: str = "",
) -> str:
    """Look up education standards for a teacher's state, subjects, and grades.

    Args:
        state: US state abbreviation (e.g., "NY", "CA", "TX")
        subjects: Comma-separated subjects (e.g., "math,science")
        grades: Comma-separated grade levels (e.g., "7,8")
    """
    from eduagent.state_standards import get_standards_context_for_prompt

    subject_list = [s.strip() for s in subjects.split(",") if s.strip()] if subjects else []
    grade_list = [g.strip() for g in grades.split(",") if g.strip()] if grades else []

    if not state:
        return json.dumps({"error": "State abbreviation required (e.g., 'NY', 'CA')"})

    context = get_standards_context_for_prompt(state, subject_list, grade_list)
    return context if context else json.dumps({"message": f"No standards data for state={state}"})


def run_server(host: str = "localhost", port: int = 8100) -> None:
    """Run the MCP server. Uses stdio transport by default (standard MCP)."""
    mcp.run(transport="stdio")
