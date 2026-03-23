"""EDUagent OpenClaw Plugin — Main entrypoint.

This is what OpenClaw calls when a teacher sends a message.
It routes the message, manages state, and returns a response.

The teacher experience:
  Teacher: "plan a unit on photosynthesis for my 8th graders, 3 weeks"
  Bot: "Planning your photosynthesis unit... 🌿 [generates and returns unit plan]"

This module is intentionally simple — it orchestrates the other modules.
All the hard work happens in router.py, state.py, and the generation engines.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from eduagent.model_router import route as route_model
from eduagent.models import AppConfig, TeacherPersona
from eduagent.router import Intent, ParsedIntent, needs_clarification, parse_intent
from eduagent.state import TeacherSession
from eduagent.student_bot import StudentBot

# ── Response helpers ──────────────────────────────────────────────────────────

def _fmt_unit_summary(unit) -> str:
    """Format a unit plan for Telegram (no markdown tables)."""
    lines = [
        f"📚 *{unit.title}*",
        f"Grade {unit.grade_level} {unit.subject} | {unit.duration_weeks} weeks | {len(unit.daily_lessons)} lessons",
        "",
        "📌 *Essential Questions*",
    ]
    for q in unit.essential_questions[:3]:
        lines.append(f"• {q}")
    lines.append("")
    lines.append("📅 *Lesson Sequence*")
    for lesson in unit.daily_lessons[:5]:
        lines.append(f"  L{lesson.lesson_number}: {lesson.topic}")
    if len(unit.daily_lessons) > 5:
        lines.append(f"  ... +{len(unit.daily_lessons) - 5} more lessons")
    lines.append("")
    lines.append("_Reply with 'generate lesson 1' to get the full first lesson plan, or 'export PDF' to download._")
    return "\n".join(lines)


def _fmt_lesson_summary(lesson) -> str:
    """Format a lesson plan for Telegram."""
    lines = [
        f"📝 *Lesson {lesson.lesson_number}: {lesson.title}*",
        "",
        f"🎯 *Objective:* {lesson.objective}",
        "",
        f"🔔 *Do-Now (5 min):* {lesson.do_now[:200]}...",
        "",
        "📋 *Structure:*",
        f"• Direct Instruction ({lesson.time_estimates.get('direct_instruction', 20)} min)",
        f"• Guided Practice ({lesson.time_estimates.get('guided_practice', 15)} min)",
        f"• Independent Work ({lesson.time_estimates.get('independent_work', 10)} min)",
        f"• Exit Ticket ({len(lesson.exit_ticket)} questions)",
        "",
    ]
    if lesson.differentiation.struggling:
        lines.append("♿ *Differentiation included* (struggling/advanced/ELL)")
    if lesson.homework:
        lines.append("📚 *Homework:* Yes")
    lines.append("")
    lines.append("_Reply 'generate materials' for the worksheet + assessment, or 'export PDF' to download._")
    return "\n".join(lines)


def _fmt_persona(persona: TeacherPersona) -> str:
    """Format a teacher persona for Telegram."""
    lines = [
        "👩‍🏫 *Your Teaching Profile*",
        "",
        f"• Style: {persona.teaching_style.value.replace('_', ' ').title()}",
        f"• Tone: {persona.tone}",
        f"• Format: {persona.preferred_lesson_format}",
    ]
    if persona.structural_preferences:
        lines.append(f"• Preferences: {', '.join(persona.structural_preferences[:4])}")
    if persona.subject_area:
        lines.append(f"• Subject: {persona.subject_area}")
    if persona.grade_levels:
        lines.append(f"• Grades: {', '.join(persona.grade_levels)}")
    lines.append("")
    lines.append("_Everything I generate will match this profile. Reply 'update my profile' to change anything._")
    return "\n".join(lines)


# ── Main handler ──────────────────────────────────────────────────────────────

async def handle_message(
    message: str,
    teacher_id: str,
    *,
    subject: Optional[str] = None,
    grade: Optional[str] = None,
) -> str:
    """
    Handle a teacher message and return a response string.

    This is the main entrypoint called by OpenClaw (or the web UI / CLI chat).

    Args:
        message: The teacher's message text
        teacher_id: Unique identifier for this teacher (Telegram user ID, session UUID, etc.)
        subject: Optional default subject (from session context)
        grade: Optional default grade (from session context)

    Returns:
        Response string formatted for the channel (Telegram-friendly by default)
    """
    session = TeacherSession.load(teacher_id)
    session.add_context("user", message)

    parsed = parse_intent(message)

    # Use session defaults for missing params
    if not parsed.grade and grade:
        parsed.grade = grade
    if not parsed.grade and session.persona and session.persona.grade_levels:
        parsed.grade = session.persona.grade_levels[0]

    # Check if we need clarification
    clarification = needs_clarification(parsed)
    if clarification:
        session.add_context("assistant", clarification)
        session.save()
        return clarification

    # Route to handler
    response = await _dispatch(parsed, session)

    session.add_context("assistant", response[:1000])
    session.save()
    return response


async def _dispatch(parsed: ParsedIntent, session: TeacherSession) -> str:
    """Route to the appropriate handler based on intent."""

    # ── New teacher onboarding ────────────────────────────────────────────────
    if session.is_new and parsed.intent not in (
        Intent.SETUP, Intent.CONNECT_DRIVE, Intent.CONNECT_LOCAL, Intent.HELP
    ):
        return (
            "👋 Hi! I'm EDUagent — your AI teaching assistant.\n\n"
            "To get started, share some of your existing lesson plans with me:\n"
            "• Google Drive link: share your lesson plans folder\n"
            "• Local folder: tell me the path (e.g. ~/Documents/Lessons/)\n\n"
            "Or just tell me about yourself: 'I teach 8th grade science' and we'll start from scratch.\n\n"
            "What subject and grade do you teach?"
        )

    # ── Intent dispatch ───────────────────────────────────────────────────────

    if parsed.intent == Intent.HELP:
        return _help_text()

    if parsed.intent == Intent.SHOW_STATUS:
        return _show_status(session)

    if parsed.intent == Intent.CONNECT_DRIVE:
        return await _handle_connect_drive(parsed, session)

    if parsed.intent == Intent.CONNECT_LOCAL:
        return await _handle_connect_local(parsed, session)

    if parsed.intent == Intent.SETUP:
        return _setup_guide()

    if parsed.intent == Intent.GENERATE_UNIT:
        return await _handle_generate_unit(parsed, session)

    if parsed.intent == Intent.GENERATE_LESSON:
        return await _handle_generate_lesson(parsed, session)

    if parsed.intent == Intent.GENERATE_MATERIALS:
        return await _handle_generate_materials(parsed, session)

    if parsed.intent == Intent.GENERATE_ASSESSMENT:
        return await _handle_generate_assessment(parsed, session)

    if parsed.intent == Intent.GENERATE_BELLRINGER:
        return await _handle_generate_bellringer(parsed, session)

    if parsed.intent == Intent.GENERATE_DIFFERENTIATION:
        return await _handle_generate_differentiation(parsed, session)

    if parsed.intent == Intent.WEB_SEARCH:
        return await _handle_web_search(parsed, session)

    if parsed.intent == Intent.SEARCH_STANDARDS:
        return await _handle_search_standards(parsed, session)

    if parsed.intent == Intent.EXPORT_PDF:
        return await _handle_export(parsed, session, fmt="pdf")

    if parsed.intent == Intent.EXPORT_CLASSROOM:
        return await _handle_export(parsed, session, fmt="classroom")

    if parsed.intent == Intent.SHARE_STUDENTS:
        return await _handle_share_students(parsed, session)

    if parsed.intent == Intent.START_STUDENT_BOT:
        return await _handle_start_student_bot(parsed, session)

    if parsed.intent == Intent.SHOW_STUDENT_REPORT:
        return await _handle_show_student_report(parsed, session)

    if parsed.intent == Intent.SET_HINT_MODE:
        return await _handle_set_hint_mode(parsed, session)

    # Unknown intent — use LLM to figure it out
    return await _handle_freeform(parsed.raw, session)


# ── Intent handlers ───────────────────────────────────────────────────────────

async def _handle_connect_drive(parsed: ParsedIntent, session: TeacherSession) -> str:
    if not parsed.url:
        return "Could you share the Google Drive folder link? Right-click the folder → Share → Copy link"

    session.config["drive_url"] = parsed.url
    session.save()

    # Trigger ingestion
    try:
        from eduagent.drive import ingest_drive_folder
        docs = await ingest_drive_folder(parsed.url)
        if docs:
            from eduagent.persona import extract_persona
            config = AppConfig.load()
            persona = await extract_persona(docs, config)
            session.persona = persona
            session.save()
            return (
                f"✅ Connected! I analyzed {len(docs)} documents from your Drive.\n\n"
                + _fmt_persona(persona)
            )
        else:
            return "I connected to Drive but couldn't find any lesson plan files (PDF, DOCX, PPTX). Make sure the folder contains your lesson materials and try again."
    except Exception as e:
        return (
            f"Connected to Drive at {parsed.url}\n\n"
            "I'll analyze your materials in the background. "
            "Reply 'what do you know about me' once I've had a chance to learn your style.\n\n"
            f"_(Technical note: {str(e)[:100]})_"
        )


async def _handle_connect_local(parsed: ParsedIntent, session: TeacherSession) -> str:
    path = parsed.url
    if not path:
        return "What's the path to your lesson plan folder? (e.g., ~/Documents/Teaching/)"

    resolved = Path(path).expanduser().resolve()
    if not resolved.exists():
        return f"I can't find the folder at `{path}`. Could you double-check the path?"

    session.config["materials_path"] = str(resolved)
    session.save()

    try:
        from eduagent.ingestor import ingest_path
        from eduagent.persona import extract_persona
        docs = ingest_path(resolved)
        if docs:
            config = AppConfig.load()
            persona = await extract_persona(docs, config)
            session.persona = persona
            session.save()
            return (
                f"✅ Analyzed {len(docs)} files from {resolved.name}/\n\n"
                + _fmt_persona(persona)
            )
        else:
            return f"Found the folder but no lesson plan files (PDF, DOCX, PPTX, TXT) inside `{resolved.name}/`. Try a different folder?"
    except Exception as e:
        return f"Had trouble reading files from {path}: {str(e)[:150]}"


async def _handle_generate_unit(parsed: ParsedIntent, session: TeacherSession) -> str:
    from eduagent.models import AppConfig
    from eduagent.planner import plan_unit

    topic = parsed.topic or "the current topic"
    grade = parsed.grade or (session.persona.grade_levels[0] if session.persona and session.persona.grade_levels else "8")
    subject = (session.persona.subject_area if session.persona and session.persona.subject_area else "General")
    weeks = parsed.weeks or 2
    persona = session.persona or TeacherPersona()

    try:
        config = route_model("unit_plan", AppConfig.load())
        unit = await plan_unit(
            subject=subject,
            grade_level=grade,
            topic=topic,
            duration_weeks=weeks,
            persona=persona,
            config=config,
        )
        session.save_unit(unit)
        return _fmt_unit_summary(unit)
    except Exception as e:
        return f"Ran into an issue generating the unit plan: {str(e)[:200]}\n\nMake sure your API key is configured (`/setup` to check)."


async def _handle_generate_lesson(parsed: ParsedIntent, session: TeacherSession) -> str:
    from eduagent.lesson import generate_lesson
    from eduagent.models import AppConfig, LessonBrief, UnitPlan

    # If we have a current unit, generate the next lesson in sequence
    if session.current_unit:
        unit = session.current_unit
        # Figure out which lesson number was requested
        lesson_num = 1
        if parsed.raw:
            import re
            m = re.search(r"lesson\s+(\d+)", parsed.raw, re.IGNORECASE)
            if m:
                lesson_num = int(m.group(1))
    else:
        # Create a minimal unit context for a standalone lesson
        topic = parsed.topic or "today's lesson"
        grade = parsed.grade or "8"
        subject = (session.persona.subject_area if session.persona else "General")
        unit = UnitPlan(
            title=f"{topic} Unit",
            subject=subject,
            grade_level=grade,
            topic=topic,
            duration_weeks=1,
            overview=f"A lesson on {topic}.",
            daily_lessons=[LessonBrief(lesson_number=1, topic=topic, description=f"Introduction to {topic}")],
        )
        lesson_num = 1

    persona = session.persona or TeacherPersona()

    try:
        config = route_model("lesson_plan", AppConfig.load())
        lesson = await generate_lesson(
            lesson_number=lesson_num,
            unit=unit,
            persona=persona,
            config=config,
        )
        session.save_lesson(lesson)
        return _fmt_lesson_summary(lesson)
    except Exception as e:
        return f"Had trouble generating the lesson: {str(e)[:200]}"


async def _handle_generate_materials(parsed: ParsedIntent, session: TeacherSession) -> str:
    from eduagent.materials import generate_materials
    from eduagent.models import AppConfig

    if not session.current_lesson:
        return "Which lesson should I make materials for? Generate a lesson plan first, or tell me the topic."

    lesson = session.current_lesson
    persona = session.persona or TeacherPersona()

    try:
        config = route_model("materials", AppConfig.load())
        materials = await generate_materials(lesson=lesson, persona=persona, config=config)
        lines = [
            f"📋 *Materials for: {lesson.title}*",
            "",
            f"✅ Worksheet: {len(materials.worksheet_items)} questions",
            f"✅ Assessment: {len(materials.assessment_questions)} questions",
        ]
        if materials.rubric:
            lines.append(f"✅ Rubric: {len(materials.rubric)} criteria")
        if materials.slide_outline:
            lines.append(f"✅ Slide outline: {len(materials.slide_outline)} slides")
        if materials.iep_notes:
            lines.append(f"✅ Differentiation notes: {len(materials.iep_notes)} accommodations")
        lines.append("")
        lines.append("_Reply 'export PDF' to download everything as a ready-to-print packet._")
        return "\n".join(lines)
    except Exception as e:
        return f"Trouble generating materials: {str(e)[:200]}"


async def _handle_generate_assessment(parsed: ParsedIntent, session: TeacherSession) -> str:
    topic = parsed.topic or (session.current_unit.topic if session.current_unit else "the current topic")
    return (
        f"📝 Creating assessment for: *{topic}*\n\n"
        "What type?\n"
        "• 'multiple choice' — 10-15 MC questions\n"
        "• 'short answer' — 5-8 written response questions\n"
        "• 'mixed' — combination of MC, short answer, and 1 essay\n"
        "• 'exit ticket' — 3 quick questions for end of class"
    )


async def _handle_generate_bellringer(parsed: ParsedIntent, session: TeacherSession) -> str:
    from eduagent.llm import LLMClient
    from eduagent.models import AppConfig

    topic = parsed.topic or (session.current_unit.topic if session.current_unit else "today's topic")
    persona = session.persona or TeacherPersona()
    config = route_model("bellringer", AppConfig.load())

    try:
        client = LLMClient(config)
        response = await client.generate(
            prompt=f"Create 3 different bell ringer / Do-Now prompts for a lesson on {topic} for grade {persona.grade_levels[0] if persona.grade_levels else '8'}. Each should take 3-5 minutes. Match this teacher style: {persona.tone}. Format as a numbered list.",
            system="You are an expert teacher. Be concise and practical.",
            temperature=0.7,
            max_tokens=400,
        )
        return f"🔔 *Bell Ringer Options for {topic}:*\n\n{response}"
    except Exception as e:
        return f"Trouble generating bell ringers: {str(e)[:200]}"


async def _handle_generate_differentiation(parsed: ParsedIntent, session: TeacherSession) -> str:
    lesson = session.current_lesson
    if not lesson:
        topic = parsed.topic or "the current lesson"
        return f"Tell me more about the lesson on *{topic}* first, or generate a lesson plan and I'll add differentiation notes to it."

    from eduagent.llm import LLMClient
    from eduagent.models import AppConfig

    config = route_model("differentiation", AppConfig.load())
    client = LLMClient(config)

    try:
        response = await client.generate(
            prompt=(
                f"Write specific differentiation strategies for this lesson:\n"
                f"Title: {lesson.title}\n"
                f"Objective: {lesson.objective}\n\n"
                "Provide:\n"
                "1. 3 accommodations for struggling learners (specific, not generic)\n"
                "2. 3 enrichment activities for advanced learners\n"
                "3. 2 accommodations for ELL students\n"
                "Be specific — mention the actual lesson content, not generic advice."
            ),
            system="You are an expert special education and differentiation specialist.",
            temperature=0.6,
            max_tokens=600,
        )
        return f"♿ *Differentiation for {lesson.title}:*\n\n{response}"
    except Exception as e:
        return f"Trouble generating differentiation notes: {str(e)[:200]}"


async def _handle_web_search(parsed: ParsedIntent, session: TeacherSession) -> str:
    try:
        from eduagent.search import search_for_teacher
        results = await search_for_teacher(parsed.raw, session.persona)
        return results
    except Exception:
        return (
            "I'd like to search the web for that, but web search isn't configured yet.\n\n"
            "Set your Tavily API key to enable search:\n"
            "`/config tavily YOUR_KEY`\n\n"
            "Or I can generate content without current examples — just ask!"
        )


async def _handle_search_standards(parsed: ParsedIntent, session: TeacherSession) -> str:
    from eduagent.standards import get_standards

    grade = parsed.grade or (session.persona.grade_levels[0] if session.persona and session.persona.grade_levels else None)
    subject = session.persona.subject_area if session.persona else None

    if not grade or not subject:
        return "Which grade and subject? (e.g., 'standards for 8th grade science')"

    standards = get_standards(grade=grade, subject=subject)
    if not standards:
        return f"I don't have standards loaded for {subject} grade {grade}. Try 'search for NGSS {subject} grade {grade}' and I'll look it up online."

    lines = [f"📋 *Standards: Grade {grade} {subject}*", ""]
    for s in standards[:8]:
        lines.append(f"• *{s.get('code', '')}* — {s.get('description', '')[:100]}")
    if len(standards) > 8:
        lines.append(f"_... and {len(standards) - 8} more_")
    return "\n".join(lines)


async def _handle_export(parsed: ParsedIntent, session: TeacherSession, fmt: str) -> str:
    if not session.current_lesson:
        return "Generate a lesson first, then I can export it."
    return (
        f"📄 Export as *{fmt.upper()}*\n\n"
        "Export functionality is available via the web interface.\n"
        "Run `eduagent serve` and visit http://localhost:8000 to download your materials."
    )


async def _handle_share_students(parsed: ParsedIntent, session: TeacherSession) -> str:
    if not session.current_lesson:
        return "Generate a lesson first, then I can create a student chatbot link for it."
    return (
        "🎓 *Student Chatbot*\n\n"
        "Once you run `eduagent serve`, your students can access a chatbot that answers questions about this lesson in your teaching voice.\n\n"
        "The embed code will be available at: http://localhost:8000"
    )


async def _handle_start_student_bot(parsed: ParsedIntent, session: TeacherSession) -> str:
    """Activate student bot for the current lesson, returns class code."""
    if not session.current_lesson:
        return (
            "Generate a lesson first, then I can activate the student bot for it.\n\n"
            "Try: 'write a lesson on photosynthesis'"
        )

    bot = StudentBot()

    # Check if teacher already has a class code in config
    class_code = session.config.get("class_code")
    if not class_code:
        class_code = bot.create_class(session.teacher_id)
        session.config["class_code"] = class_code
        session.save()

    # Set the active lesson
    lesson_json = session.current_lesson.model_dump_json()
    lesson_id = session.current_lesson.title
    await bot.set_active_lesson(class_code, lesson_id, session.teacher_id, lesson_json)

    return (
        f"🎓 *Student Bot Activated!*\n\n"
        f"📋 Class Code: `{class_code}`\n"
        f"📝 Active Lesson: {session.current_lesson.title}\n\n"
        f"*Share this with your students:*\n"
        f"Students can join using: `eduagent student-chat --class-code {class_code}`\n\n"
        f"*Teacher commands:*\n"
        f"• 'show me what students are asking' — see student questions\n"
        f"• 'set homework hint mode' — bot gives hints only, no direct answers\n"
        f"• 'start student bot for lesson N' — switch to a different lesson"
    )


async def _handle_show_student_report(parsed: ParsedIntent, session: TeacherSession) -> str:
    """Display student question report."""
    class_code = session.config.get("class_code")
    if not class_code:
        return "You haven't activated the student bot yet. Try: 'start student bot'"

    bot = StudentBot()
    report = await bot.get_student_report(class_code)

    lines = [
        "📊 *Student Activity Report*",
        f"Class Code: `{class_code}`",
        "",
        f"👥 Students: {report['student_count']}",
        f"💬 Total Messages: {report['total_messages']}",
    ]

    if report["recent_questions"]:
        lines.append("")
        lines.append("📝 *Recent Questions:*")
        for q in report["recent_questions"][:10]:
            lines.append(f"• _{q['student_id']}_: {q['question'][:100]}")
    else:
        lines.append("\nNo student questions yet.")

    return "\n".join(lines)


async def _handle_set_hint_mode(parsed: ParsedIntent, session: TeacherSession) -> str:
    """Toggle hint-only mode for student bot."""
    class_code = session.config.get("class_code")
    if not class_code:
        return "You haven't activated the student bot yet. Try: 'start student bot'"

    import re

    # Detect if turning off
    turning_off = bool(re.search(r"(disable|turn\s+off|deactivate|remove)", parsed.raw, re.IGNORECASE))

    bot = StudentBot()
    bot.set_hint_mode(class_code, not turning_off)

    if turning_off:
        return (
            "✅ Hint mode *disabled*. The student bot will now give full explanations and answers."
        )
    return (
        "✅ Hint mode *enabled*! The student bot will now:\n"
        "• Give hints and guiding questions instead of direct answers\n"
        "• Encourage students to think through problems step by step\n"
        "• Never reveal homework or assessment answers directly\n\n"
        "To turn off: 'disable hint mode'"
    )


async def _handle_freeform(message: str, session: TeacherSession) -> str:
    """Handle anything that didn't match a known intent — use LLM directly."""
    from eduagent.llm import LLMClient
    from eduagent.models import AppConfig

    config = route_model("quick_answer", AppConfig.load())
    client = LLMClient(config)

    persona_context = session.persona.to_prompt_context() if session.persona else "Teacher persona not yet configured."
    recent_context = session.get_context_for_llm(max_turns=4)

    system = (
        "You are EDUagent, an AI teaching assistant. You help K-12 teachers plan lessons, "
        "units, assessments, and curriculum. Be concise, practical, and helpful. "
        "If asked to generate something specific, do it. "
        f"\n\n{persona_context}"
    )

    messages = recent_context + [{"role": "user", "content": message}]

    try:
        response = await client.generate(
            prompt="\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages),
            system=system,
            temperature=0.7,
            max_tokens=800,
        )
        return response
    except Exception as e:
        return f"I ran into an issue: {str(e)[:150]}. Check your API key with `/status`."


# ── Status and help ───────────────────────────────────────────────────────────

def _show_status(session: TeacherSession) -> str:
    lines = ["⚙️ *EDUagent Status*", ""]
    if session.persona:
        lines.append(f"👩‍🏫 Persona: {session.persona.teaching_style.value.replace('_', ' ').title()} teacher")
        if session.persona.subject_area:
            lines.append(f"📚 Subject: {session.persona.subject_area}")
        if session.persona.grade_levels:
            lines.append(f"🎓 Grades: {', '.join(session.persona.grade_levels)}")
    else:
        lines.append("👩‍🏫 Persona: Not set up yet")

    if session.config.get("drive_url"):
        lines.append("☁️ Drive: Connected")
    elif session.config.get("materials_path"):
        lines.append(f"📁 Materials: {Path(session.config['materials_path']).name}")
    else:
        lines.append("📂 Materials: Not connected")

    config = AppConfig.load()
    lines.append(f"🤖 LLM: {config.provider.value}")

    if session.current_unit:
        lines.append(f"📖 Current unit: {session.current_unit.title}")
    if session.current_lesson:
        lines.append(f"📝 Current lesson: {session.current_lesson.title}")

    recent = session.get_recent_units(limit=3)
    if recent:
        lines.append("")
        lines.append("📚 Recent units:")
        for u in recent:
            lines.append(f"  • {u['title']} ({u['subject']}, Gr. {u['grade_level']})")

    return "\n".join(lines)


def _help_text() -> str:
    return (
        "🎓 *EDUagent — Your AI Teaching Assistant*\n\n"
        "*What I can do:*\n"
        "• Plan units and lessons in your teaching voice\n"
        "• Generate worksheets, assessments, and rubrics\n"
        "• Write differentiation notes (IEP accommodations, enrichment)\n"
        "• Find current news stories and resources for your lessons\n"
        "• Look up NGSS, Common Core, and other standards\n"
        "• Export to PDF, Google Classroom, or shareable links\n\n"
        "*Just talk to me naturally:*\n"
        "• 'Plan a 3-week unit on the American Revolution for 8th grade'\n"
        "• 'Write a lesson on photosynthesis'\n"
        "• 'Find a current news story about climate change'\n"
        "• 'Make a worksheet for today's lesson'\n\n"
        "*Setup:*\n"
        "• Share a Google Drive link to your lesson plans\n"
        "• Or tell me your local folder path\n"
        "• Or just describe your teaching style and we'll start fresh\n\n"
        "Reply `/status` to see your current setup."
    )


def _setup_guide() -> str:
    return (
        "⚙️ *Getting Set Up*\n\n"
        "*Step 1: Connect your materials* (pick one)\n"
        "• Share a Google Drive folder link with your lesson plans\n"
        "• Tell me a local folder path: '~/Documents/Teaching/'\n"
        "• Or skip this and describe your teaching style directly\n\n"
        "*Step 2: Choose your AI provider*\n"
        "• Anthropic (Claude) — best quality\n"
        "  Set key: send 'my anthropic key is sk-...'\n"
        "• OpenAI (GPT-4o) — solid alternative\n"
        "  Set key: send 'my openai key is sk-...'\n"
        "• Ollama Cloud — free, no key needed\n"
        "  Send: 'use ollama at https://your-ollama-url.com'\n\n"
        "*Step 3: Generate something!*\n"
        "Once connected, just tell me what you need.\n\n"
        "What subject and grade do you teach?"
    )
