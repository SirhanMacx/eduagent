"""Compile interactive HTML learning games from lesson content.

Every game is unique — the LLM designs the mechanic, visuals, and
interaction based on the lesson content, teacher's style, and student
preferences. No templates. No repetition.

The compiler:
1. Extracts game-worthy content from MasterContent
2. Asks the LLM to design and code a complete single-file HTML game
3. Validates the output (loads, contains educational content)
4. Falls back to regeneration if the game is broken

Usage:
    from clawed.compile_game import compile_game
    path = await compile_game(master, persona, output_dir)
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from clawed.io import safe_filename
from clawed.llm import LLMClient
from clawed.master_content import MasterContent
from clawed.model_router import route as route_model
from clawed.models import AppConfig, TeacherPersona

logger = logging.getLogger(__name__)

GAME_SYSTEM_PROMPT = """\
You are an expert educational game developer. You create single-file HTML \
games that teach through play. Every game you make is UNIQUE — different \
mechanic, different visual style, different interaction pattern.

RULES:
- Output ONLY the complete HTML file. No explanation, no markdown fencing.
- The file must be self-contained: all CSS and JS inline.
- You may use a Three.js CDN link for 3D: \
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
- The game MUST work on phones, tablets, Chromebooks (responsive, touch).
- The game MUST be genuinely FUN — not a boring quiz with buttons.
- Include scoring, feedback, progression (levels or rounds).
- Use modern CSS (gradients, animations, shadows) for visual polish.
- Include a start screen with the lesson title and instructions.
- Include an end screen with score and "play again" button.
- ALL educational content must be embedded as data in the JS.
- Add a small footer: "Made with Claw-ED — github.com/SirhanMacx/Claw-ED"

WHAT MAKES A GREAT LEARNING GAME:
- The mechanic TEACHES, not just tests. Students learn through the gameplay.
- Wrong answers give feedback that explains WHY it's wrong.
- Difficulty progresses — start easy, get harder.
- Visual and audio feedback (CSS animations, color changes, shake effects).
- Time pressure is optional but adds excitement when appropriate.
- Multiplayer/competitive elements are great if they fit.
"""


def _extract_game_content(master: MasterContent) -> str:
    """Extract educational content from MasterContent for game generation."""
    parts = [
        f"LESSON: {master.title}",
        f"SUBJECT: {master.subject}",
        f"GRADE: {master.grade_level}",
        f"TOPIC: {master.topic}",
        f"OBJECTIVE: {master.objective}",
    ]

    if master.vocabulary:
        parts.append("\nVOCABULARY:")
        for v in master.vocabulary:
            parts.append(
                f"  - {v.term}: {v.definition}"
                + (f" (context: {v.context_sentence})" if v.context_sentence else "")
            )

    if master.guided_notes:
        parts.append("\nKEY FACTS (fill-in-the-blank):")
        for note in master.guided_notes:
            parts.append(f"  - Q: {note.prompt} → A: {note.answer}")

    if master.exit_ticket:
        parts.append("\nQUIZ QUESTIONS:")
        for i, q in enumerate(master.exit_ticket, 1):
            parts.append(f"  {i}. {q.question}")
            if hasattr(q, "expected_answer") and q.expected_answer:
                parts.append(f"     Answer: {q.expected_answer}")

    if master.primary_sources:
        parts.append("\nPRIMARY SOURCES:")
        for src in master.primary_sources:
            parts.append(f"  - {src.title} ({src.source_type})")
            if hasattr(src, "content_text") and src.content_text:
                parts.append(f"    Text: {src.content_text[:300]}...")

    if master.direct_instruction:
        parts.append("\nKEY CONCEPTS:")
        for section in master.direct_instruction:
            parts.append(f"  - {section.heading}")
            if hasattr(section, "key_points") and section.key_points:
                for pt in section.key_points[:3]:
                    parts.append(f"    • {pt}")

    return "\n".join(parts)


def _validate_game_html(html: str, master: MasterContent) -> list[str]:
    """Validate that the generated HTML is a working game."""
    issues = []

    if not html or len(html) < 500:
        issues.append("HTML is too short to be a real game")

    if "<html" not in html.lower():
        issues.append("Missing <html> tag")

    if "<script" not in html.lower():
        issues.append("Missing <script> tag — no JavaScript")

    if "function" not in html and "=>" not in html:
        issues.append("No JavaScript functions found")

    # Check that educational content is embedded
    topic_words = master.topic.lower().split()[:3]
    html_lower = html.lower()
    found_topic = any(w in html_lower for w in topic_words if len(w) > 3)
    if not found_topic:
        issues.append(
            f"Topic words ({', '.join(topic_words)}) not found in game"
        )

    if master.vocabulary:
        first_term = master.vocabulary[0].term.lower()
        if first_term not in html_lower:
            issues.append(
                f"First vocabulary term '{first_term}' not in game"
            )

    return issues


async def compile_game(
    master: MasterContent,
    persona: TeacherPersona | None = None,
    output_dir: Path | None = None,
    config: AppConfig | None = None,
    student_preferences: str = "",
    game_style: str = "",
) -> Path:
    """Generate a unique interactive HTML game from lesson content.

    The LLM designs the game mechanic, visuals, and interaction from
    scratch every time. No templates.

    Args:
        master: The lesson's MasterContent (source of truth).
        persona: Teacher persona for voice/style matching.
        output_dir: Where to save the .html file.
        config: App config for model routing.
        student_preferences: What students are into ("they love Among Us",
            "obsessed with Minecraft", "competitive, love team challenges").
        game_style: Specific game style request ("jeopardy", "escape room",
            "battle royale quiz", etc.). If empty, LLM decides.

    Returns:
        Path to the generated .html game file.
    """
    if output_dir is None:
        output_dir = Path("./clawed_output")
    output_dir.mkdir(parents=True, exist_ok=True)

    config = config or AppConfig.load()
    config = route_model("game_generate", config)
    client = LLMClient(config)

    # Build the game generation prompt
    content = _extract_game_content(master)

    prompt_parts = [
        "Design and code a COMPLETE, UNIQUE, single-file HTML learning "
        "game for this lesson.\n",
        content,
    ]

    if student_preferences:
        prompt_parts.append(
            f"\nSTUDENT PREFERENCES: {student_preferences}\n"
            "Design the game mechanic to match what these students enjoy. "
            "If they like a specific game, use a similar mechanic but "
            "with educational content."
        )

    if game_style:
        prompt_parts.append(
            f"\nREQUESTED STYLE: {game_style}\n"
            "Use this style as inspiration but make it your own."
        )
    else:
        prompt_parts.append(
            "\nNo specific style requested — surprise me. Be creative. "
            "Pick a game mechanic that FITS this specific lesson content. "
            "A timeline lesson should have different gameplay than a "
            "vocabulary lesson. Think about what mechanic actually helps "
            "students LEARN this material."
        )

    if persona:
        prompt_parts.append(
            f"\nTEACHER'S STYLE: {persona.tone or 'engaging'}\n"
            f"Grade level: {master.grade_level}\n"
            "Match the difficulty and humor to this teacher and grade."
        )

    prompt = "\n".join(prompt_parts)

    # Generate with retry
    max_attempts = 2
    for attempt in range(max_attempts):
        try:
            html = await client.generate(
                prompt=prompt,
                system=GAME_SYSTEM_PROMPT,
                temperature=0.8,  # Creative — we want variety
                max_tokens=12000,
            )

            # Clean: strip markdown fencing if present
            html = html.strip()
            if html.startswith("```"):
                html = re.sub(r"^```\w*\n?", "", html)
                html = re.sub(r"\n?```$", "", html)
            html = html.strip()

            # Validate
            issues = _validate_game_html(html, master)
            if issues and attempt < max_attempts - 1:
                logger.warning(
                    "Game validation issues (attempt %d): %s",
                    attempt + 1,
                    "; ".join(issues),
                )
                prompt += (
                    "\n\nPREVIOUS ATTEMPT HAD ISSUES: "
                    + "; ".join(issues)
                    + "\nFix these issues. Output ONLY the complete HTML."
                )
                continue

            if issues:
                logger.warning(
                    "Game has issues but using anyway: %s",
                    "; ".join(issues),
                )

            # Save
            fname = f"game_{safe_filename(master.title)}.html"
            game_path = output_dir / fname
            game_path.write_text(html, encoding="utf-8")

            logger.info(
                "Game compiled: %s (%d bytes)",
                game_path.name,
                len(html),
            )
            return game_path

        except Exception as e:
            logger.error("Game generation failed (attempt %d): %s", attempt + 1, e)
            if attempt == max_attempts - 1:
                raise

    # Should never reach here
    raise RuntimeError("Game generation failed after all attempts")
