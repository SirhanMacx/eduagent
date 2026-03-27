"""Reading report — analyze ingested documents and summarize what we learned.

Produces a report that feels like a colleague sharing observations, not a
database query.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from clawed.models import Document, TeacherPersona


def generate_reading_report(
    documents: list["Document"],
    persona: "TeacherPersona | None" = None,
) -> dict[str, Any]:
    """Analyze ingested documents and produce a structured reading report.

    Returns a dict with keys:
        teacher_details, signature_moves, topic_coverage, strengths,
        gaps, favorite_strategies, voice_patterns, assessment_patterns,
        interesting_finds, doc_stats.
    """
    report: dict[str, Any] = {
        "teacher_details": {},
        "signature_moves": [],
        "topic_coverage": {},
        "strengths": [],
        "gaps": [],
        "favorite_strategies": [],
        "voice_patterns": [],
        "assessment_patterns": [],
        "interesting_finds": [],
        "doc_stats": {},
    }

    if not documents:
        return report

    # Aggregate all text for analysis
    all_text = "\n".join(doc.content for doc in documents if doc.content)

    # ── Document stats ───────────────────────────────────────────────
    type_counts: Counter[str] = Counter()
    for doc in documents:
        ext = doc.doc_type.value.upper() if doc.doc_type else "UNKNOWN"
        type_counts[ext] += 1

    report["doc_stats"] = {
        "total": len(documents),
        "by_type": dict(type_counts.most_common()),
    }

    # ── Teacher name detection ───────────────────────────────────────
    name_pattern = re.compile(
        r"\b(Mr\.|Ms\.|Mrs\.|Dr\.)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)\b"
    )
    name_matches = name_pattern.findall(all_text)
    if name_matches:
        name_counter: Counter[str] = Counter()
        for prefix, surname in name_matches:
            name_counter[f"{prefix} {surname}"] += 1
        most_common_name, name_count = name_counter.most_common(1)[0]
        report["teacher_details"]["name"] = most_common_name
        report["teacher_details"]["name_occurrences"] = name_count

    # School name detection
    school_pattern = re.compile(
        r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+"
        r"(?:Middle|High|Elementary|Academy|School|Prep|Charter))"
        r"(?:\s+School)?\b"
    )
    school_matches = school_pattern.findall(all_text)
    if school_matches:
        school_counter: Counter[str] = Counter()
        for s in school_matches:
            school_counter[s] += 1
        report["teacher_details"]["school"] = school_counter.most_common(1)[0][0]

    # ── Voice patterns ───────────────────────────────────────────────
    # Opening phrases from Do Now / Warm-Up sections
    do_now_pattern = re.compile(
        r"(?:Do Now|Warm[- ]?Up|Bell ?Ringer)[:\s]*([^\n]{10,80})",
        re.IGNORECASE,
    )
    openers = do_now_pattern.findall(all_text)
    if openers:
        unique_openers = list(dict.fromkeys(openers[:10]))
        report["voice_patterns"].append(
            f"Often opens with: '{unique_openers[0].strip()}'"
        )

    # Address terms
    address_terms = {
        "friends": r"\bfriends\b",
        "scholars": r"\bscholars\b",
        "historians": r"\bhistorians\b",
        "scientists": r"\bscientists\b",
        "mathematicians": r"\bmathematicians\b",
        "students": r"\bstudents\b",
        "class": r"\bclass\b",
        "team": r"\bteam\b",
        "everybody": r"\beverybody\b",
        "everyone": r"\beveryone\b",
    }
    for term, pattern in address_terms.items():
        count = len(re.findall(pattern, all_text, re.IGNORECASE))
        if count >= 3:
            report["voice_patterns"].append(
                f"Calls students '{term}' ({count} times across your files)"
            )

    # ── Topic coverage ───────────────────────────────────────────────
    topics = {
        "American Revolution": r"American Revolution|Revolutionary War|1776|Declaration of Independence",
        "Civil War": r"Civil War|Gettysburg|Emancipation|Antebellum",
        "Constitution": r"Constitution|Bill of Rights|Amendments|Federalist",
        "WWI": r"World War I|WWI|Great War|Trench Warfare",
        "WWII": r"World War II|WWII|Holocaust|Pearl Harbor|D-Day",
        "Reconstruction": r"Reconstruction|Freedmen|Jim Crow|13th Amendment|14th Amendment|15th Amendment",
        "Immigration": r"Immigration|Ellis Island|Immigrants|Nativism",
        "Women's Suffrage": r"Women's Suffrage|19th Amendment|Seneca Falls|Susan B\. Anthony",
        "Civil Rights": r"Civil Rights|MLK|Martin Luther King|Brown v\. Board|Rosa Parks|Segregation",
        "Cold War": r"Cold War|Soviet|Cuban Missile|McCarthyism|Iron Curtain",
        "Industrialization": r"Industrialization|Industrial Revolution|Gilded Age|Robber Barons",
    }
    topic_counts: dict[str, int] = {}
    for topic, pattern in topics.items():
        count = len(re.findall(pattern, all_text, re.IGNORECASE))
        if count > 0:
            topic_counts[topic] = count

    report["topic_coverage"] = dict(
        sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
    )

    # Guess primary subject from topic coverage
    if topic_counts:
        report["teacher_details"]["subject_guess"] = "Social Studies"
    # Future: detect Science, Math, ELA from their respective topic patterns

    # Strengths = topics with significant coverage
    if topic_counts:
        sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
        report["strengths"] = [t[0] for t in sorted_topics[:5] if t[1] >= 3]

    # Gaps = topics with zero or near-zero coverage
    all_topics = set(topics.keys())
    covered = {t for t, c in topic_counts.items() if c >= 2}
    report["gaps"] = sorted(all_topics - covered)

    # ── Activity strategies ──────────────────────────────────────────
    strategies = {
        "Jigsaw": r"\bjigsaw\b",
        "DBQ": r"\bDBQ\b|Document[- ]Based Question",
        "Socratic Seminar": r"Socratic Seminar",
        "Think-Pair-Share": r"Think[- ]Pair[- ]Share",
        "Gallery Walk": r"Gallery Walk",
        "Debate": r"\bdebate\b",
        "Station Rotation": r"Station Rotation|Stations\b",
        "Primary Source Analysis": r"Primary Source|primary source",
    }
    strategy_counts: dict[str, int] = {}
    for strategy, pattern in strategies.items():
        count = len(re.findall(pattern, all_text, re.IGNORECASE))
        if count > 0:
            strategy_counts[strategy] = count

    report["favorite_strategies"] = [
        f"{s} ({c}x)"
        for s, c in sorted(strategy_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    # ── Assessment patterns ──────────────────────────────────────────
    exit_ticket_count = len(
        re.findall(r"Exit Ticket|exit ticket", all_text, re.IGNORECASE)
    )
    if exit_ticket_count:
        report["assessment_patterns"].append(
            f"Uses exit tickets ({exit_ticket_count} found)"
        )

    question_count = len(re.findall(r"\?\s", all_text))
    if question_count:
        report["assessment_patterns"].append(
            f"~{question_count} questions across all documents"
        )

    # ── Structural patterns (signature moves) ────────────────────────
    structural = {
        "AIM": r"\bAIM\b[:\s]",
        "Do Now": r"Do Now",
        "SWBAT": r"SWBAT|Students Will Be Able To",
        "Essential Question": r"Essential Question|EQ[:\s]",
    }
    for name, pattern in structural.items():
        count = len(re.findall(pattern, all_text, re.IGNORECASE))
        if count >= 2:
            report["signature_moves"].append(f"Uses {name} structure ({count}x)")

    # ── Interesting finds ────────────────────────────────────────────
    if report["doc_stats"]["total"] > 100:
        report["interesting_finds"].append(
            f"That's a LOT of materials — {report['doc_stats']['total']} files. "
            "You've clearly been at this a while."
        )

    if persona and persona.name and persona.name != "My Teaching Persona":
        if report["teacher_details"].get("name"):
            detected = report["teacher_details"]["name"]
            if detected.split()[-1] != persona.name.split()[-1]:
                report["interesting_finds"].append(
                    f"Your files reference {detected} — is that you, or a co-teacher?"
                )

    return report


def format_reading_report(report: dict[str, Any]) -> str:
    """Format the reading report as natural conversational text.

    Should feel like a colleague sharing observations, not a database query.
    """
    if not report or not report.get("doc_stats", {}).get("total"):
        return "I haven't read any of your files yet."

    lines: list[str] = []
    stats = report["doc_stats"]

    # File stats
    type_breakdown = ", ".join(
        f"{count} {ext}" for ext, count in stats.get("by_type", {}).items()
    )
    lines.append(
        f"I read through {stats['total']} files"
        + (f" ({type_breakdown})" if type_breakdown else "")
        + "."
    )

    # Teacher name
    teacher_name = report.get("teacher_details", {}).get("name")
    if teacher_name:
        lines.append(f"Your students know you as {teacher_name}.")

    # School
    school = report.get("teacher_details", {}).get("school")
    if school:
        lines.append(f"Looks like you're at {school}.")

    # Voice patterns
    if report.get("voice_patterns"):
        lines.append("")
        lines.append("A few things I noticed about your voice:")
        for vp in report["voice_patterns"][:5]:
            lines.append(f"- {vp}")

    # Signature moves
    if report.get("signature_moves"):
        lines.append("")
        lines.append("Your lesson structure:")
        for sm in report["signature_moves"][:5]:
            lines.append(f"- {sm}")

    # Topic coverage
    if report.get("strengths"):
        lines.append("")
        lines.append(
            "Your strongest coverage is in "
            + ", ".join(report["strengths"])
            + "."
        )

    # Strategies
    if report.get("favorite_strategies"):
        lines.append("")
        lines.append(
            "Your go-to strategies: "
            + ", ".join(report["favorite_strategies"][:5])
            + "."
        )

    # Assessment patterns
    if report.get("assessment_patterns"):
        lines.append("")
        for ap in report["assessment_patterns"]:
            lines.append(f"- {ap}")

    # Gaps
    if report.get("gaps"):
        lines.append("")
        lines.append(
            "I didn't find much on "
            + ", ".join(report["gaps"][:5])
            + " — is that covered in a different quarter?"
        )

    # Interesting finds
    if report.get("interesting_finds"):
        lines.append("")
        for find in report["interesting_finds"]:
            lines.append(find)

    return "\n".join(lines)
