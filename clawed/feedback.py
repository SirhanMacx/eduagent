"""Feedback collection and analysis for the self-improvement loop."""

from __future__ import annotations

import json
from typing import Any

from clawed.database import Database


def collect_feedback(
    db: Database,
    lesson_id: str,
    rating: int,
    notes: str = "",
    sections_edited: list[str] | None = None,
) -> str:
    """Record teacher feedback for a generated lesson.

    Args:
        db: Database instance.
        lesson_id: The lesson being rated.
        rating: 1-5 star rating.
        notes: Optional free-text feedback.
        sections_edited: Optional list of section names that were edited.

    Returns:
        The feedback record ID.
    """
    rating = max(1, min(5, rating))
    edited_json = json.dumps(sections_edited or [])
    return db.insert_feedback(lesson_id, rating, notes, edited_json)


def analyze_feedback(db: Database, days: int = 7) -> dict[str, Any]:
    """Analyze recent feedback to identify improvement areas.

    Returns a summary dict with:
        - avg_rating: average rating over the window
        - total_feedback: number of feedback entries
        - low_rated_count: lessons rated <= 2
        - most_edited_sections: sections that get edited most
        - common_complaints: extracted themes from notes
    """
    recent = db.get_recent_feedback(days)
    if not recent:
        return {
            "avg_rating": 0.0,
            "total_feedback": 0,
            "low_rated_count": 0,
            "most_edited_sections": [],
            "sample_notes": [],
        }

    ratings = [f["rating"] for f in recent if f["rating"] is not None]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0.0

    # Count section edits
    section_counts: dict[str, int] = {}
    for f in recent:
        try:
            sections = json.loads(f.get("sections_edited", "[]"))
            for s in sections:
                section_counts[s] = section_counts.get(s, 0) + 1
        except (json.JSONDecodeError, TypeError):
            pass

    sorted_sections = sorted(section_counts.items(), key=lambda x: x[1], reverse=True)

    # Collect sample notes from low-rated entries
    low_rated = [f for f in recent if f["rating"] is not None and f["rating"] <= 2]
    sample_notes = [f["notes"] for f in low_rated if f.get("notes")][:10]

    return {
        "avg_rating": round(avg_rating, 2),
        "total_feedback": len(recent),
        "low_rated_count": len(low_rated),
        "most_edited_sections": [s[0] for s in sorted_sections[:5]],
        "sample_notes": sample_notes,
    }
