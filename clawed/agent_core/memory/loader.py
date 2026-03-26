"""Memory context loader — assembles all 3 layers for the agent's system prompt."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def load_memory_context(teacher_id: str, current_message: str) -> dict[str, Any]:
    """Load all memory layers and assemble context for the system prompt."""
    # Layer 1: Identity
    identity_summary = ""
    try:
        from clawed.agent_core.memory.identity import load_identity_from_db

        db_identity = load_identity_from_db(teacher_id)
        persona = db_identity.get("persona")
        if persona:
            parts = []
            if persona.get("subject_area"):
                parts.append(persona["subject_area"])
            if persona.get("grade_levels"):
                parts.append(f"Grades {persona['grade_levels']}")
            if persona.get("teaching_style"):
                parts.append(persona["teaching_style"].replace("_", " "))
            identity_summary = ", ".join(parts)
    except Exception as e:
        logger.debug("Identity load failed: %s", e)

    # Layer 2: Curriculum state
    curriculum_summary = ""
    try:
        from clawed.agent_core.memory.curriculum import (
            load_curriculum_state,
            summarize_curriculum_state,
        )

        state = load_curriculum_state(teacher_id)
        curriculum_summary = summarize_curriculum_state(state)
    except Exception as e:
        logger.debug("Curriculum state load failed: %s", e)

    # Layer 3: Episodic memory
    relevant_episodes = ""
    try:
        from clawed.agent_core.memory.episodes import EpisodicMemory

        mem = EpisodicMemory()
        episodes = mem.recall(teacher_id, current_message, top_k=5)
        if episodes:
            relevant_episodes = "\n".join(
                f"- {ep['text']}"
                for ep in episodes
                if ep.get("similarity", 0) > 0.1
            )
    except Exception as e:
        logger.debug("Episodic recall failed: %s", e)

    # Existing improvement context (backward compat)
    improvement_context = ""
    try:
        from clawed.memory_engine import build_improvement_context

        improvement_context = build_improvement_context()
    except Exception as e:
        logger.debug("Improvement context load failed: %s", e)

    # Layer 4: Preferences
    preferences_summary = ""
    autonomy_summary = ""
    try:
        from clawed.agent_core.memory.preferences import extract_preferences, summarize_preferences
        prefs = extract_preferences(teacher_id)
        preferences_summary = summarize_preferences(prefs)
        autonomy_summary = prefs.get("autonomy_summary", "")
    except Exception as e:
        logger.debug("Preference extraction failed: %s", e)

    # Layer 5: Curriculum Knowledge Base
    curriculum_kb_context = ""
    try:
        from clawed.agent_core.memory.curriculum_kb import CurriculumKB

        kb = CurriculumKB()
        kb_results = kb.search(teacher_id, current_message, top_k=3)
        if kb_results:
            parts = []
            for r in kb_results:
                if r.get("similarity", 0) > 0.15:
                    parts.append(
                        f"- From '{r['doc_title']}': {r['chunk_text'][:200]}"
                    )
            if parts:
                curriculum_kb_context = "\n".join(parts)
    except Exception as e:
        logger.debug("Curriculum KB search failed: %s", e)

    return {
        "identity_summary": identity_summary,
        "curriculum_summary": curriculum_summary,
        "relevant_episodes": relevant_episodes,
        "improvement_context": improvement_context,
        "preferences_summary": preferences_summary,
        "autonomy_summary": autonomy_summary,
        "curriculum_kb_context": curriculum_kb_context,
    }
