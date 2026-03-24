"""Teaching Memory Engine -- learns from teacher feedback to improve generation.

The feedback loop:
1. Teacher rates a lesson (1-5 stars) + optional notes
2. Memory engine extracts what worked (5*) or what failed (1-2*)
3. Patterns stored in memory.md as structured sections
4. Next generation reads memory.md and injects it as context
5. Output quality improves over time

This is prompt-level RLHF: no model fine-tuning required, transparent
(teacher can read and edit memory.md), and compounds over time.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from eduagent.models import AppConfig

if TYPE_CHECKING:
    from eduagent.models import DailyLesson

logger = logging.getLogger(__name__)

# ── Sections in memory.md ────────────────────────────────────────────

SECTION_WHAT_WORKS = "What Works (from 5-star lessons)"
SECTION_WHAT_TO_AVOID = "What to Avoid (from 1-2-star lessons)"
SECTION_STRUCTURAL_PREFS = "Structural Preferences"
SECTION_TOPIC_NOTES = "Topic-Specific Notes"
SECTION_GENERATION_STATS = "Generation Statistics"

# Placeholders used in memory.md sections
_SECTION_PLACEHOLDERS: dict[str, str] = {
    SECTION_WHAT_WORKS: "*(Patterns from your highest-rated lessons appear here automatically.)*",
    SECTION_WHAT_TO_AVOID: "*(Patterns from your lowest-rated lessons appear here automatically.)*",
    SECTION_STRUCTURAL_PREFS: "*(How you prefer lessons structured -- learned from your edits.)*",
    SECTION_TOPIC_NOTES: "*(What works for specific subjects/topics.)*",
}


# ── Default memory template ──────────────────────────────────────────

DEFAULT_MEMORY_TEMPLATE = """\
# Teaching Memory

## What Works (from 5-star lessons)
*(Patterns from your highest-rated lessons appear here automatically.)*

## What to Avoid (from 1-2-star lessons)
*(Patterns from your lowest-rated lessons appear here automatically.)*

## Structural Preferences
*(How you prefer lessons structured -- learned from your edits.)*

## Topic-Specific Notes
*(What works for specific subjects/topics.)*

## Generation Statistics
- Total lessons rated: 0
- Average rating: --
- Rating trend: --
"""


# ── Pattern extraction (rule-based, no LLM needed) ──────────────────


def extract_lesson_patterns(
    lesson: "DailyLesson",
    rating: int,
    notes: str = "",
    edited_sections: list[str] | None = None,
    subject: str = "",
) -> list[dict[str, str]]:
    """Extract patterns from a rated lesson using rule-based heuristics.

    Returns a list of pattern dicts: {"type": ..., "pattern": ..., "section": ...}
    Each pattern is a short sentence describing what worked or what to avoid.

    Args:
        subject: The subject area (e.g. "Science", "History"). Used to tag
            patterns so they can be filtered during prompt injection, preventing
            cross-subject contamination.
    """
    patterns: list[dict[str, str]] = []
    edited = edited_sections or []
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Tag patterns with subject for cross-subject filtering
    subject_tag = f" [{subject}]" if subject else ""

    if rating == 5:
        # Extract what made it excellent
        patterns.append({
            "type": "positive",
            "pattern": f"Lesson '{lesson.title}' rated 5-star{subject_tag} ({timestamp})",
            "section": SECTION_WHAT_WORKS,
        })

        # Structural patterns from the lesson itself
        if lesson.do_now and len(lesson.do_now) > 50:
            _extract_do_now_pattern(lesson.do_now, patterns)
        if lesson.exit_ticket and len(lesson.exit_ticket) >= 3:
            patterns.append({
                "type": "positive",
                "pattern": "Exit tickets with 3+ questions work well",
                "section": SECTION_STRUCTURAL_PREFS,
            })
        if notes:
            patterns.append({
                "type": "positive",
                "pattern": f"Teacher note on 5-star lesson{subject_tag}: {notes[:200]}",
                "section": SECTION_WHAT_WORKS,
            })

    elif rating <= 2:
        # Extract what went wrong
        patterns.append({
            "type": "negative",
            "pattern": f"Lesson '{lesson.title}' rated {rating}-star{subject_tag} ({timestamp})",
            "section": SECTION_WHAT_TO_AVOID,
        })

        if notes:
            patterns.append({
                "type": "negative",
                "pattern": f"Teacher complaint{subject_tag}: {notes[:200]}",
                "section": SECTION_WHAT_TO_AVOID,
            })

        # Track which sections were edited (they needed fixing)
        for section_name in edited:
            patterns.append({
                "type": "structural",
                "pattern": f"Teacher edited '{section_name}' section{subject_tag} -- needs improvement",
                "section": SECTION_STRUCTURAL_PREFS,
            })

    elif rating == 4:
        # Good but not perfect -- note minor tweaks if notes provided
        if notes:
            patterns.append({
                "type": "positive",
                "pattern": f"4-star lesson '{lesson.title}': {notes[:150]}",
                "section": SECTION_TOPIC_NOTES,
            })
        if edited:
            for section_name in edited:
                patterns.append({
                    "type": "structural",
                    "pattern": f"Minor edit needed in '{section_name}' on 4-star lesson",
                    "section": SECTION_STRUCTURAL_PREFS,
                })

    # Rating 3 = neutral, don't learn from mediocre

    return patterns


def _extract_do_now_pattern(do_now_text: str, patterns: list[dict[str, str]]) -> None:
    """Identify structural patterns in a successful Do-Now section."""
    text_lower = do_now_text.lower()

    if "?" in do_now_text:
        q_count = do_now_text.count("?")
        if q_count >= 2:
            patterns.append({
                "type": "positive",
                "pattern": f"Do-Now with {q_count} questions works well",
                "section": SECTION_STRUCTURAL_PREFS,
            })
    if any(kw in text_lower for kw in ("predict", "prediction", "what do you think")):
        patterns.append({
            "type": "positive",
            "pattern": "Do-Now with prediction/anticipation questions gets high ratings",
            "section": SECTION_STRUCTURAL_PREFS,
        })
    if any(kw in text_lower for kw in ("reflect", "reflection", "yesterday", "last class")):
        patterns.append({
            "type": "positive",
            "pattern": "Do-Now with reflection on prior learning gets high ratings",
            "section": SECTION_STRUCTURAL_PREFS,
        })


# ── Memory.md read/write ─────────────────────────────────────────────


def _get_memory_path():
    """Get the memory.md path, respecting EDUAGENT_DATA_DIR."""
    from eduagent.workspace import MEMORY_PATH
    return MEMORY_PATH


def _read_memory() -> str:
    """Read memory.md, returning the default template if it doesn't exist."""
    path = _get_memory_path()
    if path.exists():
        return path.read_text(encoding="utf-8")
    return DEFAULT_MEMORY_TEMPLATE


def _write_memory(content: str) -> None:
    """Write content to memory.md, creating parent dirs if needed."""
    path = _get_memory_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _append_to_section(content: str, section_name: str, entry: str) -> str:
    """Append a bullet point to a section in memory.md content.

    If the section exists, inserts after the heading (replacing placeholder if present).
    If the section doesn't exist, appends it at the end.
    """
    heading = f"## {section_name}"

    if heading not in content:
        # Append new section before Generation Statistics (if present) or at end
        stats_heading = f"## {SECTION_GENERATION_STATS}"
        if stats_heading in content:
            content = content.replace(
                stats_heading,
                f"{heading}\n- {entry}\n\n{stats_heading}",
            )
        else:
            content = content.rstrip() + f"\n\n{heading}\n- {entry}\n"
        return content

    lines = content.split("\n")
    new_lines: list[str] = []
    found_heading = False
    inserted = False

    for line in lines:
        if line.strip() == heading or line.strip().startswith(heading):
            found_heading = True
            new_lines.append(line)
            continue

        if found_heading and not inserted:
            stripped = line.strip()
            # Check if this line is a placeholder
            if stripped.startswith("*(") and stripped.endswith(")*"):
                new_lines.append(f"- {entry}")
                inserted = True
                continue
            # Check if we've hit the next section
            elif stripped.startswith("## ") or stripped.startswith("# "):
                new_lines.append(f"- {entry}")
                new_lines.append("")
                inserted = True
                new_lines.append(line)
                continue
            else:
                new_lines.append(line)
                continue
        else:
            new_lines.append(line)

    if found_heading and not inserted:
        new_lines.append(f"- {entry}")

    return "\n".join(new_lines)


def _update_stats_section(content: str, total_rated: int, avg_rating: float, trend: str) -> str:
    """Update the Generation Statistics section in memory.md."""
    heading = f"## {SECTION_GENERATION_STATS}"
    avg_str = f"{avg_rating:.1f}" if avg_rating > 0 else "--"

    stats_block = (
        f"{heading}\n"
        f"- Total lessons rated: {total_rated}\n"
        f"- Average rating: {avg_str}\n"
        f"- Rating trend: {trend}\n"
    )

    if heading in content:
        # Replace entire stats section
        pattern = re.compile(
            r"## Generation Statistics\n(?:- .*\n)*",
            re.MULTILINE,
        )
        content = pattern.sub(stats_block, content)
    else:
        content = content.rstrip() + f"\n\n{stats_block}"

    return content


# ── Deduplication ────────────────────────────────────────────────────


def _is_duplicate_entry(content: str, entry: str) -> bool:
    """Check if an entry (or something very similar) already exists in memory.md."""
    # Exact match
    if f"- {entry}" in content:
        return True
    # Check if the core lesson title is already recorded
    # e.g. "Lesson 'Photosynthesis' rated 5-star" should not be added twice
    match = re.search(r"Lesson '([^']+)'", entry)
    if match:
        title = match.group(1)
        if title in content:
            return True
    return False


# ── Core API ─────────────────────────────────────────────────────────


def process_feedback(
    lesson: "DailyLesson",
    rating: int,
    notes: str = "",
    edited_sections: list[str] | None = None,
    subject: str = "",
) -> list[dict[str, str]]:
    """Process teacher feedback and update memory.md with learned patterns.

    This is the primary entry point for the feedback loop. Call it after
    every rating to incrementally build the teacher's preference profile.

    Args:
        lesson: The rated lesson.
        rating: 1-5 star rating.
        notes: Optional free-text feedback from the teacher.
        edited_sections: Optional list of section names the teacher edited.
        subject: The subject area (for cross-subject filtering in prompts).

    Returns:
        List of patterns that were extracted and stored.
    """
    rating = max(1, min(5, rating))

    # Rating 3 = neutral, skip
    if rating == 3:
        logger.debug("Rating 3 (neutral) for '%s' -- skipping pattern extraction", lesson.title)
        return []

    # Resolve subject: from parameter, persona config, or empty
    if not subject:
        try:
            cfg = AppConfig.load()
            if cfg.teacher_profile and cfg.teacher_profile.subjects:
                subject = cfg.teacher_profile.subjects[0]
        except Exception:
            pass

    # Extract patterns from the rated lesson
    patterns = extract_lesson_patterns(lesson, rating, notes, edited_sections, subject=subject)

    if not patterns:
        return []

    # Read current memory and apply patterns
    content = _read_memory()

    applied: list[dict[str, str]] = []
    for pattern in patterns:
        entry = pattern["pattern"]
        section = pattern["section"]

        # Skip duplicates
        if _is_duplicate_entry(content, entry):
            logger.debug("Skipping duplicate pattern: %s", entry[:80])
            continue

        content = _append_to_section(content, section, entry)
        applied.append(pattern)

    if applied:
        # Update stats
        stats = _compute_stats(content)
        content = _update_stats_section(
            content,
            total_rated=stats["total_rated"],
            avg_rating=stats["avg_rating"],
            trend=stats["trend"],
        )
        _write_memory(content)
        logger.info(
            "Memory updated: %d pattern(s) from %d-star rating of '%s'",
            len(applied), rating, lesson.title,
        )

    return applied


def build_improvement_context(
    subject: str = "",
    grade: str = "",
    topic: str = "",
) -> str:
    """Build a focused prompt injection from memory.md for the current generation.

    Reads memory.md and constructs a block of text that gets injected into
    the system prompt so the LLM knows the teacher's preferences.

    Args:
        subject: The subject being generated for (for topic-specific filtering).
        grade: The grade level.
        topic: The specific topic.

    Returns:
        A formatted string for prompt injection. Empty string if no useful
        content exists in memory.md.
    """
    content = _read_memory()

    # If memory only contains the default template with placeholders, return empty
    if _is_only_template(content):
        return ""

    parts: list[str] = []

    def _filter_by_subject(entries: list[str], subj: str) -> list[str]:
        """Filter entries to those relevant to the given subject.

        Entries tagged with [Subject] are only included if they match.
        Entries without a tag are always included (they're universal).
        """
        if not subj:
            return entries
        subj_lower = subj.lower()
        result = []
        for e in entries:
            # Check if entry has a subject tag like [Science] or [History]
            tag_match = re.search(r"\[([^\]]+)\]", e)
            if tag_match:
                tag = tag_match.group(1).lower()
                if subj_lower in tag or tag in subj_lower:
                    result.append(e)
                # Skip entries tagged for other subjects
            else:
                # No tag — universal pattern, always include
                result.append(e)
        return result

    # Extract "What Works" entries, filtered by subject
    works = _extract_section_entries(content, SECTION_WHAT_WORKS)
    works = _filter_by_subject(works, subject)
    if works:
        parts.append("What works well for this teacher:")
        for entry in works[-10:]:
            parts.append(f"  - {entry}")

    # Extract "What to Avoid" entries, filtered by subject
    avoid = _extract_section_entries(content, SECTION_WHAT_TO_AVOID)
    avoid = _filter_by_subject(avoid, subject)
    if avoid:
        parts.append("")
        parts.append("What to avoid:")
        for entry in avoid[-10:]:
            parts.append(f"  - {entry}")

    # Extract structural preferences (these are universal, no subject filter)
    structural = _extract_section_entries(content, SECTION_STRUCTURAL_PREFS)
    if structural:
        parts.append("")
        parts.append("Structural preferences:")
        for entry in structural[-8:]:
            parts.append(f"  - {entry}")

    # Extract topic-specific notes (filter by subject/topic if provided)
    topic_notes = _extract_section_entries(content, SECTION_TOPIC_NOTES)
    if topic_notes:
        relevant = topic_notes
        if subject or topic:
            # Filter to entries mentioning the subject or topic
            search_terms = [t.lower() for t in [subject, topic] if t]
            filtered = [
                n for n in topic_notes
                if any(term in n.lower() for term in search_terms)
            ]
            relevant = filtered if filtered else topic_notes[-5:]
        parts.append("")
        parts.append("Topic-specific notes:")
        for entry in relevant[-5:]:
            parts.append(f"  - {entry}")

    if not parts:
        return ""

    header = "=== Learning from Past Lessons ==="
    footer = "=== End Learning Context ==="
    return f"\n{header}\n" + "\n".join(parts) + f"\n{footer}\n"


def get_improvement_stats() -> dict[str, Any]:
    """Return statistics about the improvement loop.

    Returns:
        Dict with total_rated, avg_rating, trend, patterns_count,
        what_works_count, what_to_avoid_count.
    """
    content = _read_memory()
    stats = _compute_stats(content)

    works = _extract_section_entries(content, SECTION_WHAT_WORKS)
    avoid = _extract_section_entries(content, SECTION_WHAT_TO_AVOID)
    structural = _extract_section_entries(content, SECTION_STRUCTURAL_PREFS)
    topics = _extract_section_entries(content, SECTION_TOPIC_NOTES)

    stats["what_works_count"] = len(works)
    stats["what_to_avoid_count"] = len(avoid)
    stats["structural_count"] = len(structural)
    stats["topic_notes_count"] = len(topics)
    stats["total_patterns"] = len(works) + len(avoid) + len(structural) + len(topics)
    stats["what_works"] = works[-5:]
    stats["what_to_avoid"] = avoid[-5:]

    return stats


def reset_memory(confirm: bool = False) -> bool:
    """Reset memory.md to the default template. Requires confirm=True.

    Returns True if reset was performed.
    """
    if not confirm:
        return False
    _write_memory(DEFAULT_MEMORY_TEMPLATE)
    logger.info("Memory reset to default template.")
    return True


# ── Internal helpers ─────────────────────────────────────────────────


def _extract_section_entries(content: str, section_name: str) -> list[str]:
    """Extract bullet-point entries from a section in memory.md.

    Returns a list of entry strings (without the leading '- ').
    """
    heading = f"## {section_name}"
    if heading not in content:
        return []

    entries: list[str] = []
    in_section = False

    for line in content.split("\n"):
        stripped = line.strip()
        if stripped == heading or stripped.startswith(heading):
            in_section = True
            continue
        if in_section:
            if stripped.startswith("## ") or stripped.startswith("# "):
                break  # Next section
            if stripped.startswith("- "):
                entry = stripped[2:].strip()
                # Skip placeholders
                if entry.startswith("*(") and entry.endswith(")*"):
                    continue
                entries.append(entry)

    return entries


def _is_only_template(content: str) -> bool:
    """Check if memory.md only contains the default template with no real entries."""
    for section in [SECTION_WHAT_WORKS, SECTION_WHAT_TO_AVOID, SECTION_STRUCTURAL_PREFS, SECTION_TOPIC_NOTES]:
        entries = _extract_section_entries(content, section)
        if entries:
            return False
    return True


def _compute_stats(content: str) -> dict[str, Any]:
    """Compute stats from the memory.md content.

    Counts rated entries and computes average from the star mentions.
    """
    # Count rated lessons by counting star-rating mentions
    five_star = len(re.findall(r"rated 5-star", content))
    four_star = content.count("4-star lesson")
    one_two_star = len(re.findall(r"rated [12]-star", content))

    total_rated = five_star + four_star + one_two_star

    if total_rated == 0:
        return {"total_rated": 0, "avg_rating": 0.0, "trend": "--"}

    # Count 1-star and 2-star separately for accurate average
    one_star = len(re.findall(r"rated 1-star", content))
    two_star = len(re.findall(r"rated 2-star", content))
    # If we can't distinguish (old format), split evenly
    if one_star + two_star == 0 and one_two_star > 0:
        one_star = one_two_star // 2
        two_star = one_two_star - one_star

    total_score = (five_star * 5) + (four_star * 4) + (two_star * 2) + (one_star * 1)
    avg_rating = total_score / total_rated if total_rated else 0.0

    # Simple trend: if more 5-star than low, trending up
    if five_star > one_two_star:
        trend = "improving"
    elif one_two_star > five_star:
        trend = "needs attention"
    else:
        trend = "stable"

    return {
        "total_rated": total_rated,
        "avg_rating": round(avg_rating, 2),
        "trend": trend,
    }
