# v2.3.3 Quality Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a quality layer that makes Claw-ED output trustworthy enough for a teacher to hand directly to students and defend in front of an administrator without reviewing every line.

**Architecture:** 11 phases executed sequentially. Each phase modifies 1-3 files, runs lint+tests after. No infrastructure changes — only quality/intelligence improvements to existing modules. The prompt templates use `.replace()` rendering (NOT Jinja2) — subject-conditional logic is achieved by adding multi-subject instruction blocks that the LLM selects from based on `{subject}`. New persona field `handout_style` flows through extraction → storage → generation via `.replace("{handout_style}", ...)`. Voice validation is lightweight rule-based checks, not full LLM evaluation.

**Tech Stack:** Python 3.10+, Pydantic models, `.replace()`-rendered prompt templates, async LLM calls via `clawed.llm.LLMClient`, pytest, ruff

**What NOT to touch:** `clawed/agent_core/` structure, `gateway.py`, `_legacy_gateway.py`, `router.py`, `model_router.py`, `standards.py`, `state_standards.py`, `clawed/skills/`, transports (Telegram/CLI/web/TUI).

---

## File Map

### Files to Modify
| File | Phase | Change |
|------|-------|--------|
| `clawed/reading_report.py` | 1 | Add LLM second-pass after regex analysis |
| `clawed/models.py` | 2 | Add `handout_style` field to `TeacherPersona` |
| `clawed/prompts/persona_extract.txt` | 2 | Add handout style extraction instructions |
| `clawed/prompts/student_packet.txt` | 2 | Add `{handout_style}` conditional block |
| `clawed/memory_engine.py` | 3 | Add `evolve_persona()` function |
| `clawed/agent_core/tools/update_soul.py` | 5 | Add dedup check before appending |
| `clawed/workspace.py` | 5 | Add `consolidate_soul()` function |
| `clawed/agent_core/tools/generate_lesson_bundle.py` | 4,6 | Add voice check + honest error reporting |
| `clawed/slide_images.py` | 8 | Enhance `_fetch_teacher_image` context search |
| `clawed/asset_registry.py` | 8 | Store slide context text during ingestion |
| `clawed/prompts/lesson_plan.txt` | 9 | Add subject-conditional sections |
| `clawed/prompts/student_packet.txt` | 9 | Add subject-conditional station language |
| `clawed/prompts/admin_lesson_plan.txt` | 9 | Add subject-conditional content knowledge |
| `tests/test_handout_export.py` | 10 | Fix `_handout.docx` → `_packet.docx` assertion |
| `pyproject.toml` | 11 | Bump version to 2.3.3 |
| `clawed/__init__.py` | 11 | Bump `__version__` to "2.3.3" |
| `ROADMAP.md` | 11 | Update shipped features |

### Files to Create
| File | Phase | Purpose |
|------|-------|---------|
| `clawed/voice_check.py` | 4 | Lightweight post-generation voice validation |
| `clawed/persona_evolution.py` | 3 | Persona fingerprint evolution logic |
| `tests/test_lesson_quality.py` | 7 | Pedagogical quality assertions on DailyLesson |
| `tests/test_student_packet_quality.py` | 7 | Structural quality assertions on StudentPacket |
| `tests/test_voice_check.py` | 4 | Tests for voice validation |
| `tests/test_reading_report_llm.py` | 1 | Tests for LLM-enhanced reading report |
| `tests/test_persona_evolution.py` | 3 | Tests for persona evolution |
| `tests/test_soul_consolidation.py` | 5 | Tests for SOUL.md consolidation |

---

## Task 1: Phase 1 — LLM-Enhanced Reading Report

**Files:**
- Modify: `clawed/reading_report.py`
- Create: `tests/test_reading_report_llm.py`

The current `generate_reading_report()` is regex-only. We add a second LLM pass that sends 5-10 representative document excerpts and the regex data to produce qualitative observations.

- [ ] **Step 1: Write test for LLM-enhanced reading report**

Create `tests/test_reading_report_llm.py`:

```python
"""Tests for LLM-enhanced reading report."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from clawed.models import DocType, Document
from clawed.reading_report import generate_reading_report, _select_representative_excerpts, _build_llm_reading_prompt


def _make_docs(n: int = 5) -> list[Document]:
    """Create n sample documents with varied content."""
    topics = [
        ("American Revolution Lesson Plan", "Do Now: Imagine you are a colonial farmer in 1773. "
         "Your tea is being taxed without your say. Friends, today we explore why ordinary people "
         "chose to rebel. SWBAT analyze primary sources from the Revolution..."),
        ("Civil War DBQ Activity", "Scholars, let's dig into these documents. "
         "Station A: Frederick Douglass speech excerpt. Station B: Lincoln's letter to Horace Greeley. "
         "Exit Ticket: How did views on slavery evolve during the war?"),
        ("Constitution Jigsaw", "Friends, today each expert group gets a different amendment. "
         "Your job is to become the expert and teach your home group. "
         "Think-pair-share: Why did the founders include a Bill of Rights?"),
        ("Women's Suffrage Gallery Walk", "Gallery Walk stations around the room. "
         "Station 1: Seneca Falls Declaration of Sentiments 1848. "
         "Graphic organizer: Document / Author's Claim / Evidence / Significance"),
        ("Reconstruction Assessment", "Summative: 3 part assessment. "
         "Part 1: Multiple choice on 13th-15th Amendments. "
         "Part 2: DBQ with Freedmen's Bureau documents. Part 3: Essay."),
    ]
    docs = []
    for i in range(min(n, len(topics))):
        title, content = topics[i]
        docs.append(Document(title=title, content=content, doc_type=DocType.DOCX))
    return docs


def test_select_representative_excerpts_picks_varied_docs():
    docs = _make_docs(5)
    excerpts = _select_representative_excerpts(docs, max_excerpts=3)
    assert len(excerpts) == 3
    # Each excerpt should be a dict with 'title' and 'content'
    assert all("title" in e and "content" in e for e in excerpts)


def test_build_llm_reading_prompt_includes_regex_data():
    regex_report = {"topic_coverage": {"Civil War": 5}, "favorite_strategies": ["Jigsaw (3x)"]}
    excerpts = [{"title": "Lesson 1", "content": "Do Now: Think about freedom..."}]
    prompt = _build_llm_reading_prompt(regex_report, excerpts)
    assert "Civil War" in prompt
    assert "Jigsaw" in prompt
    assert "Do Now: Think about freedom" in prompt
    assert "genuine observations" in prompt.lower() or "distinctive" in prompt.lower()


def test_generate_reading_report_without_llm_still_works():
    """Regex-only fallback: report works without LLM config."""
    docs = _make_docs(3)
    report = generate_reading_report(docs)
    assert report["doc_stats"]["total"] == 3
    assert isinstance(report.get("llm_observations"), (list, type(None)))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/mind_uploaded_crustacean/Projects/Claw-ED-v0920 && python -m pytest tests/test_reading_report_llm.py -v`
Expected: FAIL — `_select_representative_excerpts` and `_build_llm_reading_prompt` don't exist yet.

- [ ] **Step 3: Add helper functions to reading_report.py**

In `clawed/reading_report.py`, add after the imports:

```python
import logging
from clawed.models import AppConfig

logger = logging.getLogger(__name__)
```

Then add before `generate_reading_report`:

```python
def _select_representative_excerpts(
    documents: list["Document"],
    max_excerpts: int = 8,
) -> list[dict[str, str]]:
    """Pick diverse document excerpts for LLM analysis.

    Prioritizes variety: different topics, document types, and time periods.
    """
    if not documents:
        return []

    # Group by doc_type to ensure variety
    by_type: dict[str, list] = {}
    for doc in documents:
        key = doc.doc_type.value if doc.doc_type else "unknown"
        by_type.setdefault(key, []).append(doc)

    selected: list[dict[str, str]] = []
    seen_titles: set[str] = set()

    # Round-robin across types
    type_lists = list(by_type.values())
    idx = 0
    while len(selected) < max_excerpts and type_lists:
        bucket = type_lists[idx % len(type_lists)]
        if bucket:
            doc = bucket.pop(0)
            if doc.title not in seen_titles and doc.content.strip():
                seen_titles.add(doc.title)
                selected.append({
                    "title": doc.title,
                    "content": doc.content[:2000],
                    "doc_type": doc.doc_type.value if doc.doc_type else "unknown",
                })
        else:
            type_lists.pop(idx % len(type_lists))
            if not type_lists:
                break
            continue
        idx += 1

    return selected


def _build_llm_reading_prompt(
    regex_report: dict,
    excerpts: list[dict[str, str]],
) -> str:
    """Build the prompt for LLM qualitative analysis of teacher documents."""
    # Summarize regex findings
    regex_summary_parts = []
    if regex_report.get("topic_coverage"):
        topics = ", ".join(f"{t} ({c}x)" for t, c in list(regex_report["topic_coverage"].items())[:8])
        regex_summary_parts.append(f"Topic coverage: {topics}")
    if regex_report.get("favorite_strategies"):
        regex_summary_parts.append(f"Strategies used: {', '.join(regex_report['favorite_strategies'][:6])}")
    if regex_report.get("signature_moves"):
        regex_summary_parts.append(f"Structural patterns: {', '.join(regex_report['signature_moves'][:4])}")
    if regex_report.get("voice_patterns"):
        regex_summary_parts.append(f"Voice patterns: {', '.join(regex_report['voice_patterns'][:3])}")

    regex_block = "\n".join(f"- {p}" for p in regex_summary_parts) if regex_summary_parts else "No statistical data available."

    # Format excerpts
    excerpt_blocks = []
    for i, exc in enumerate(excerpts, 1):
        excerpt_blocks.append(
            f"--- Document {i}: {exc['title']} ({exc.get('doc_type', 'unknown')}) ---\n"
            f"{exc['content'][:1500]}\n"
        )
    excerpts_text = "\n".join(excerpt_blocks)

    return f"""You are reading a teacher's actual lesson plans and curriculum materials. Based on these samples, share 3-5 genuine observations about their teaching practice.

## Statistical Summary (from automated analysis)
{regex_block}

## Document Excerpts
{excerpts_text}

## Instructions
Be specific — reference particular lessons or patterns you noticed. Don't just restate the statistics above. Notice what's distinctive. Consider:
- How the teacher's style shows through in their materials
- The quality and sophistication of their activities (not just names but how they structure them)
- What their Do Nows actually look like (connecting to students' lives? review questions? provocative prompts?)
- Whether their assessments align to their instruction
- Anything genuinely surprising or distinctive about their practice

Respond with ONLY a JSON array of 3-5 observation strings. Each observation should be 1-3 sentences.
Example: ["This teacher consistently uses analogy-based Do Nows that...", "The jigsaw activities show unusual sophistication..."]"""
```

- [ ] **Step 4: Add async LLM pass to generate_reading_report**

At the end of `generate_reading_report()`, before `return report`, add:

```python
    # ── LLM qualitative analysis (optional second pass) ───────────────
    report["llm_observations"] = None
    excerpts = _select_representative_excerpts(documents)
    if excerpts:
        report["_excerpts_for_llm"] = excerpts

    return report
```

Then add a new async function:

```python
async def enhance_reading_report_with_llm(
    report: dict[str, Any],
    config: "AppConfig | None" = None,
) -> dict[str, Any]:
    """Add qualitative LLM observations to an existing regex-based report.

    Call this after generate_reading_report(). Falls back gracefully if the
    LLM call fails — the report is still usable with just regex data.
    """
    excerpts = report.pop("_excerpts_for_llm", None)
    if not excerpts:
        return report

    try:
        from clawed.llm import LLMClient

        cfg = config or AppConfig.load()
        client = LLMClient(cfg)
        prompt = _build_llm_reading_prompt(report, excerpts)

        data = await client.generate_json(
            prompt=prompt,
            system="You are an expert instructional coach analyzing a teacher's curriculum materials. Respond only with a JSON array of observation strings.",
            temperature=0.4,
            max_tokens=800,
        )

        if isinstance(data, list):
            report["llm_observations"] = [str(obs) for obs in data[:5]]
            logger.info("LLM reading report: %d observations generated", len(report["llm_observations"]))
        elif isinstance(data, dict) and "observations" in data:
            report["llm_observations"] = data["observations"][:5]
    except Exception as e:
        logger.warning("LLM reading report enhancement failed (falling back to regex-only): %s", e)
        report["llm_observations"] = None

    return report
```

- [ ] **Step 5: Update format_reading_report to include LLM observations**

In `format_reading_report()`, add before the "Interesting finds" section:

```python
    # LLM qualitative observations
    if report.get("llm_observations"):
        lines.append("")
        lines.append("Here's what stood out to me after reading your materials:")
        for obs in report["llm_observations"]:
            lines.append(f"- {obs}")
```

- [ ] **Step 6: Run tests**

Run: `cd /Users/mind_uploaded_crustacean/Projects/Claw-ED-v0920 && python -m pytest tests/test_reading_report_llm.py -v`
Expected: PASS

- [ ] **Step 7: Run full lint + test suite**

Run: `cd /Users/mind_uploaded_crustacean/Projects/Claw-ED-v0920 && ruff check . && python -m pytest tests/ -q --tb=short`

- [ ] **Step 8: Commit**

```bash
git add clawed/reading_report.py tests/test_reading_report_llm.py
git commit -m "feat: LLM-enhanced reading report with qualitative observations"
```

---

## Task 2: Phase 2 — Student Packet Matches Teacher's Handout Style

**Files:**
- Modify: `clawed/models.py:166` — add `handout_style` field to `TeacherPersona`
- Modify: `clawed/prompts/persona_extract.txt` — add handout style extraction
- Modify: `clawed/prompts/student_packet.txt` — add `{handout_style}` conditional

- [ ] **Step 1: Add `handout_style` field to TeacherPersona**

In `clawed/models.py`, after line ~202 (after `signature_moves` field), add:

```python
    handout_style: str = ""
    """Description of the teacher's handout/worksheet style, e.g.
    'Dense text packets with primary source excerpts and marginal annotations'
    or 'Graphic organizer-heavy with minimal text, always includes an image hook'."""
```

- [ ] **Step 2: Update persona_extract.txt**

In `clawed/prompts/persona_extract.txt`, add as item 19 before the Output Format section:

```
19. **Handout Style** — If the teacher's materials include handouts, worksheets, or student packets, describe their format. Examples: "Dense text packets with primary source excerpts and marginal annotations", "Graphic organizer-heavy with minimal text, always includes an image hook on page one", "Guided notes with fill-in-the-blank during lecture, followed by independent source analysis", "Minimal handouts — most work is done on separate paper with teacher-provided prompts". If no handouts are present, leave empty.
```

And add `"handout_style": "Guided notes with fill-in-the-blank, followed by source analysis with graphic organizer"` to the JSON output format example.

- [ ] **Step 3: Update `to_prompt_context()` in TeacherPersona**

In `clawed/models.py`, in `to_prompt_context()`, add after the signature_moves block (around line 252):

```python
        if self.handout_style:
            lines.append(f"\n=== Handout Style ===\n{self.handout_style}")
            lines.append("Student packets must match this format.")
```

- [ ] **Step 4: Update student_packet.txt to include handout_style placeholder**

In `clawed/prompts/student_packet.txt`, after `## Teacher Persona` / `{persona}`, add a new section:

```
## Handout Style
{handout_style_block}
```

This uses `.replace()` rendering — the actual conditional text is built in Python, not in the template.

- [ ] **Step 5: Wire handout_style into the student packet generation call**

In `clawed/llm.py`, in the `generate_student_packet` method (line ~296), the template is rendered with `.replace()`. Add the handout_style injection after the existing `.replace()` chain:

```python
        # Build the handout style block
        handout_style = ""
        if persona_context:
            # Extract handout_style from persona context if present
            import re
            hs_match = re.search(r"=== Handout Style ===\n(.+?)(?:\n===|\Z)", persona_context, re.DOTALL)
            if hs_match:
                handout_style = hs_match.group(1).strip()

        if handout_style:
            handout_style_block = (
                f"This teacher's handout style: {handout_style}. "
                "Match this format. If the teacher uses guided notes, include them. "
                "If they use graphic organizers, lead with those. If they prefer "
                "dense source packets, make the sources the centerpiece. "
                "Don't impose a format the teacher wouldn't recognize as their own."
            )
        else:
            handout_style_block = "No specific handout style detected — use the default format below."

        prompt = (
            prompt_template
            .replace("{lesson_json}", lesson_json[:6000])
            .replace("{persona}", persona_context)
            .replace("{handout_style_block}", handout_style_block)
        )
```

This replaces the existing 3-line `.replace()` chain at lines 296-299.

- [ ] **Step 6: Run lint + tests**

Run: `cd /Users/mind_uploaded_crustacean/Projects/Claw-ED-v0920 && ruff check . && python -m pytest tests/ -q --tb=short`

- [ ] **Step 7: Commit**

```bash
git add clawed/models.py clawed/prompts/persona_extract.txt clawed/prompts/student_packet.txt
git commit -m "feat: student packet matches teacher's handout style"
```

---

## Task 3: Phase 3 — Pedagogical Fingerprint Evolution

**Files:**
- Create: `clawed/persona_evolution.py`
- Create: `tests/test_persona_evolution.py`

- [ ] **Step 1: Write tests for persona evolution**

Create `tests/test_persona_evolution.py`:

```python
"""Tests for pedagogical fingerprint evolution."""
from __future__ import annotations

from unittest.mock import patch

from clawed.models import DailyLesson, ExitTicketQuestion, TeacherPersona
from clawed.persona_evolution import (
    _analyze_rating_patterns,
    _compare_personas,
    _build_candidate_changes,
)


def _make_persona() -> TeacherPersona:
    return TeacherPersona(
        teaching_style="direct_instruction",
        do_now_style="recall questions from prior class",
        source_types=["textbook excerpts"],
        activity_patterns=["lecture with note-taking"],
    )


def _make_lesson(title: str = "Test Lesson", do_now: str = "Recall: What did we learn yesterday?") -> DailyLesson:
    return DailyLesson(
        title=title,
        lesson_number=1,
        objective="SWBAT analyze",
        do_now=do_now,
        exit_ticket=[
            ExitTicketQuestion(question="Q1?", expected_response="A1"),
            ExitTicketQuestion(question="Q2?", expected_response="A2"),
        ],
    )


def test_compare_personas_detects_changes():
    old = _make_persona()
    new = TeacherPersona(
        teaching_style="socratic",
        do_now_style="provocative scenario questions",
        source_types=["primary source documents", "political cartoons"],
        activity_patterns=["Socratic seminar", "document analysis"],
    )
    changes = _compare_personas(old, new)
    assert len(changes) > 0
    assert any("teaching_style" in c["field"] for c in changes)


def test_compare_personas_no_changes():
    p = _make_persona()
    changes = _compare_personas(p, p)
    assert len(changes) == 0


def test_analyze_rating_patterns_needs_minimum_data():
    # Less than 10 ratings should return no patterns
    ratings = [(4, "Good lesson"), (5, "Great")] * 3
    patterns = _analyze_rating_patterns(ratings)
    assert patterns == []


def test_build_candidate_changes_from_ingestion():
    old = _make_persona()
    new = TeacherPersona(
        teaching_style="socratic",
        do_now_style="provocative scenario questions",
    )
    candidates = _build_candidate_changes(old, new, source="ingestion")
    assert all(c["source"] == "ingestion" for c in candidates)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/mind_uploaded_crustacean/Projects/Claw-ED-v0920 && python -m pytest tests/test_persona_evolution.py -v`

- [ ] **Step 3: Implement persona_evolution.py**

Create `clawed/persona_evolution.py`:

```python
"""Pedagogical fingerprint evolution — the persona learns and adapts over time.

Compares stored persona against new evidence (ingested files, rating patterns)
and proposes conservative updates. Changes are tracked as candidates and only
applied when evidence is consistent across multiple data points.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from clawed.models import TeacherPersona

logger = logging.getLogger(__name__)

# Fields that can evolve
_EVOLVABLE_FIELDS = [
    "teaching_style", "do_now_style", "exit_ticket_style",
    "source_types", "activity_patterns", "scaffolding_moves",
    "signature_moves", "handout_style",
]

# How many consistent signals before a candidate change is applied
_CONFIRMATION_THRESHOLD = 2


def _candidates_path() -> Path:
    """Path to the candidate changes JSON file."""
    import os
    base = Path(os.environ.get("EDUAGENT_DATA_DIR", str(Path.home() / ".eduagent")))
    return base / "persona_candidates.json"


def _load_candidates() -> list[dict[str, Any]]:
    path = _candidates_path()
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
    return []


def _save_candidates(candidates: list[dict[str, Any]]) -> None:
    path = _candidates_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(candidates, indent=2), encoding="utf-8")


def _compare_personas(
    old: "TeacherPersona", new: "TeacherPersona",
) -> list[dict[str, Any]]:
    """Compare two personas and return a list of field-level changes."""
    changes = []
    for field_name in _EVOLVABLE_FIELDS:
        old_val = getattr(old, field_name, None)
        new_val = getattr(new, field_name, None)
        if old_val != new_val and new_val:
            changes.append({
                "field": field_name,
                "old_value": old_val,
                "new_value": new_val,
            })
    return changes


def _build_candidate_changes(
    old: "TeacherPersona",
    new: "TeacherPersona",
    source: str = "ingestion",
) -> list[dict[str, Any]]:
    """Build candidate change entries from a persona comparison."""
    changes = _compare_personas(old, new)
    timestamp = datetime.now(timezone.utc).isoformat()
    return [
        {
            "field": c["field"],
            "old_value": _serialize(c["old_value"]),
            "new_value": _serialize(c["new_value"]),
            "source": source,
            "timestamp": timestamp,
            "confirmations": 1,
        }
        for c in changes
    ]


def _serialize(val: Any) -> Any:
    """Make a value JSON-serializable."""
    if hasattr(val, "value"):  # Enum
        return val.value
    return val


def _analyze_rating_patterns(
    ratings: list[tuple[int, str]],
) -> list[dict[str, Any]]:
    """Analyze rating+notes patterns for persona evolution signals.

    Needs at least 10 ratings to produce meaningful patterns.
    """
    if len(ratings) < 10:
        return []

    # Count high vs low rated lesson characteristics from notes
    high_notes = [note for rating, note in ratings if rating >= 4 and note]
    low_notes = [note for rating, note in ratings if rating <= 2 and note]

    patterns = []
    # Look for consistent themes in high-rated notes
    if len(high_notes) >= 3:
        patterns.append({
            "field": "activity_patterns",
            "signal": f"High-rated lessons ({len(high_notes)} entries) share common themes",
            "source": "ratings",
        })

    return patterns


def record_ingestion_changes(
    old_persona: "TeacherPersona",
    new_persona: "TeacherPersona",
) -> list[dict[str, Any]]:
    """Record candidate changes from a new file ingestion.

    Called after persona extraction on new files. Compares against stored
    persona and tracks changes. Returns the list of candidates recorded.
    """
    new_candidates = _build_candidate_changes(old_persona, new_persona, source="ingestion")
    if not new_candidates:
        return []

    existing = _load_candidates()

    for nc in new_candidates:
        # Check if this field change already has a candidate
        match = next(
            (c for c in existing if c["field"] == nc["field"]
             and _serialize(c["new_value"]) == _serialize(nc["new_value"])),
            None,
        )
        if match:
            match["confirmations"] = match.get("confirmations", 1) + 1
            match["timestamp"] = nc["timestamp"]
        else:
            existing.append(nc)

    _save_candidates(existing)
    return new_candidates


def get_confirmed_changes() -> list[dict[str, Any]]:
    """Return candidate changes that have met the confirmation threshold."""
    candidates = _load_candidates()
    return [c for c in candidates if c.get("confirmations", 1) >= _CONFIRMATION_THRESHOLD]


def apply_confirmed_changes(persona: "TeacherPersona") -> tuple["TeacherPersona", list[str]]:
    """Apply confirmed changes to a persona and return descriptions of what changed.

    Returns (updated_persona, list_of_change_descriptions).
    """
    confirmed = get_confirmed_changes()
    if not confirmed:
        return persona, []

    descriptions = []
    data = persona.model_dump()

    for change in confirmed:
        field = change["field"]
        new_val = change["new_value"]
        old_val = change.get("old_value")

        if field in data:
            data[field] = new_val
            descriptions.append(
                f"Updated {field.replace('_', ' ')}: "
                f"was '{old_val}', now '{new_val}'"
            )

    # Remove applied candidates
    candidates = _load_candidates()
    remaining = [c for c in candidates if c.get("confirmations", 1) < _CONFIRMATION_THRESHOLD]
    _save_candidates(remaining)

    from clawed.models import TeacherPersona as TP
    updated = TP(**data)
    return updated, descriptions
```

- [ ] **Step 4: Run tests**

Run: `cd /Users/mind_uploaded_crustacean/Projects/Claw-ED-v0920 && python -m pytest tests/test_persona_evolution.py -v`

- [ ] **Step 5: Wire persona evolution into ingestion pipeline**

Find the ingestion handler where persona extraction happens. In `clawed/handlers/ingest.py` (or wherever `extract_persona` is called after file ingestion), add after the persona is extracted and saved:

```python
        # Track persona evolution candidates
        try:
            from clawed.persona_evolution import record_ingestion_changes
            if old_persona and new_persona:
                candidates = record_ingestion_changes(old_persona, new_persona)
                if candidates:
                    logger.info("Recorded %d persona evolution candidates", len(candidates))
        except Exception as e:
            logger.debug("Persona evolution tracking failed: %s", e)
```

Also wire into the feedback handler. In `clawed/memory_engine.py`, in `process_feedback()`, after `detect_preference_drift(rating)` (around line 396), add:

```python
    # Check if persona evolution should trigger (after 10+ ratings)
    try:
        from clawed.persona_evolution import get_confirmed_changes, apply_confirmed_changes
        confirmed = get_confirmed_changes()
        if confirmed:
            from clawed.persona import load_persona
            from clawed.commands._helpers import persona_path
            pp = persona_path()
            if pp.exists():
                persona = load_persona(pp)
                updated, descriptions = apply_confirmed_changes(persona)
                if descriptions:
                    # Save updated persona
                    pp.write_text(updated.model_dump_json(indent=2), encoding="utf-8")
                    # Log to SOUL.md
                    from clawed.workspace import SOUL_PATH
                    if SOUL_PATH.exists():
                        soul_content = SOUL_PATH.read_text(encoding="utf-8")
                        for desc in descriptions:
                            entry = f"\n\n*({datetime.now(timezone.utc).strftime('%Y-%m-%d')})* Fingerprint updated: {desc}\n"
                            soul_content = soul_content.replace("## Agent Observations", "## Agent Observations" + entry, 1)
                        SOUL_PATH.write_text(soul_content, encoding="utf-8")
                    logger.info("Persona evolution applied: %s", "; ".join(descriptions))
    except Exception as e:
        logger.debug("Persona evolution check failed: %s", e)
```

- [ ] **Step 6: Run full lint + test suite**

Run: `cd /Users/mind_uploaded_crustacean/Projects/Claw-ED-v0920 && ruff check . && python -m pytest tests/ -q --tb=short`

- [ ] **Step 7: Commit**

```bash
git add clawed/persona_evolution.py tests/test_persona_evolution.py clawed/memory_engine.py
git commit -m "feat: pedagogical fingerprint evolution with candidate tracking and SOUL.md logging"
```

---

## Task 4: Phase 4 — Voice Validation After Generation

**Files:**
- Create: `clawed/voice_check.py`
- Create: `tests/test_voice_check.py`
- Modify: `clawed/agent_core/tools/generate_lesson_bundle.py`

- [ ] **Step 1: Write tests for voice check**

Create `tests/test_voice_check.py`:

```python
"""Tests for lightweight voice validation."""
from __future__ import annotations

from clawed.models import TeacherPersona
from clawed.voice_check import check_voice_match, VoiceCheckResult


def _persona_with_voice() -> TeacherPersona:
    return TeacherPersona(
        name="Mr. Mac",
        voice_sample="Alright friends, let's dig into this primary source today. "
                     "Your job is to become a detective — read carefully and find the evidence.",
        do_now_style="scenario or analogy that previews the lesson concept without naming it",
        preferred_lesson_format="Do Now / Mini-Lesson / Guided Practice / Independent Work / Exit Ticket",
        signature_moves=["Always calls students 'friends'", "Reads sources aloud with dramatic emphasis"],
    )


def test_address_term_present():
    persona = _persona_with_voice()
    result = check_voice_match(
        persona=persona,
        do_now="Friends, imagine you just discovered a letter in your attic from 1776...",
        direct_instruction_opening="Alright friends, let's look at this document together...",
    )
    assert result.address_term_ok is True


def test_address_term_missing():
    persona = _persona_with_voice()
    result = check_voice_match(
        persona=persona,
        do_now="Scholars, what do you think happened in 1776?",
        direct_instruction_opening="Good morning students, today we will learn...",
    )
    assert result.address_term_ok is False
    assert "friends" in result.issues[0].lower()


def test_do_now_style_mismatch():
    persona = _persona_with_voice()
    # persona says "scenario or analogy" but do_now is a recall question
    result = check_voice_match(
        persona=persona,
        do_now="What do you remember about the causes of the American Revolution from yesterday?",
        direct_instruction_opening="Friends, let's continue...",
    )
    assert result.do_now_style_ok is False


def test_do_now_style_match():
    persona = _persona_with_voice()
    result = check_voice_match(
        persona=persona,
        do_now="Imagine you wake up and every book in your house has been burned. Write 2-3 sentences about how this feels.",
        direct_instruction_opening="Friends, that scenario you just wrote about...",
    )
    assert result.do_now_style_ok is True


def test_overall_pass():
    persona = _persona_with_voice()
    result = check_voice_match(
        persona=persona,
        do_now="Friends, imagine you are a merchant traveling the Silk Road in 1200...",
        direct_instruction_opening="Alright friends, that scenario you just imagined...",
    )
    assert result.passed is True
    assert len(result.issues) == 0


def test_no_voice_sample_skips_gracefully():
    persona = TeacherPersona()  # No voice data
    result = check_voice_match(
        persona=persona,
        do_now="What do you know about the topic?",
        direct_instruction_opening="Today we will learn...",
    )
    assert result.passed is True  # No voice data = nothing to check against
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/mind_uploaded_crustacean/Projects/Claw-ED-v0920 && python -m pytest tests/test_voice_check.py -v`

- [ ] **Step 3: Implement voice_check.py**

Create `clawed/voice_check.py`:

```python
"""Lightweight post-generation voice validation.

Checks whether generated lesson content matches the teacher's persona
without requiring an LLM call. Uses rule-based pattern matching on
address terms, Do Now style, and lesson structure.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from clawed.models import TeacherPersona


@dataclass
class VoiceCheckResult:
    """Result of a voice validation check."""

    address_term_ok: bool = True
    do_now_style_ok: bool = True
    structure_ok: bool = True
    passed: bool = True
    issues: list[str] = field(default_factory=list)


# Do Now styles and their indicator patterns
_RECALL_INDICATORS = [
    r"\bwhat do you (?:remember|know|recall)\b",
    r"\blist (?:three|3|the)\b",
    r"\bdefine\b",
    r"\byesterday\b.*\bwhat\b",
    r"\blast class\b.*\bwhat\b",
]

_SCENARIO_INDICATORS = [
    r"\bimagine\b",
    r"\bpretend\b",
    r"\bwhat if\b",
    r"\bwhat would you\b",
    r"\byou (?:are|just|wake|discover)",
    r"\bscenario\b",
]

_OPINION_INDICATORS = [
    r"\bdo you (?:think|believe|agree)\b",
    r"\bshould\b.*\?",
    r"\bis it (?:fair|right|just)\b",
]


def _detect_do_now_type(text: str) -> str:
    """Classify a Do Now as 'recall', 'scenario', 'opinion', or 'other'."""
    lower = text.lower()
    for pattern in _SCENARIO_INDICATORS:
        if re.search(pattern, lower):
            return "scenario"
    for pattern in _RECALL_INDICATORS:
        if re.search(pattern, lower):
            return "recall"
    for pattern in _OPINION_INDICATORS:
        if re.search(pattern, lower):
            return "opinion"
    return "other"


def _extract_address_terms(text: str) -> list[str]:
    """Extract student address terms from text (e.g., 'friends', 'scholars')."""
    terms = []
    candidates = [
        "friends", "scholars", "historians", "scientists",
        "mathematicians", "students", "class", "team",
        "everybody", "everyone",
    ]
    lower = text.lower()
    for term in candidates:
        if re.search(rf"\b{term}\b", lower):
            terms.append(term)
    return terms


def check_voice_match(
    persona: "TeacherPersona",
    do_now: str = "",
    direct_instruction_opening: str = "",
) -> VoiceCheckResult:
    """Run lightweight voice checks against the teacher's persona.

    Does NOT require an LLM call. Checks:
    1. Address term consistency (if persona uses 'friends', output should too)
    2. Do Now style match (scenario vs recall vs opinion)
    3. Basic structural patterns

    Returns a VoiceCheckResult with pass/fail and specific issues.
    """
    result = VoiceCheckResult()

    # If persona has no voice data, skip all checks
    has_voice_data = bool(
        persona.voice_sample or persona.do_now_style or persona.signature_moves
    )
    if not has_voice_data:
        return result

    combined_text = f"{do_now} {direct_instruction_opening}"

    # ── Check 1: Address terms ────────────────────────────────────────
    persona_terms = _extract_address_terms(persona.voice_sample or "")
    # Also check signature_moves for address term mentions
    for move in persona.signature_moves:
        persona_terms.extend(_extract_address_terms(move))
    persona_terms = list(dict.fromkeys(persona_terms))  # dedupe, preserve order

    if persona_terms:
        output_terms = _extract_address_terms(combined_text)
        # Check if any of the persona's preferred terms appear in output
        if not any(t in output_terms for t in persona_terms):
            result.address_term_ok = False
            result.issues.append(
                f"Expected address term '{persona_terms[0]}' but found "
                f"'{output_terms[0] if output_terms else 'none'}' instead"
            )

    # ── Check 2: Do Now style ─────────────────────────────────────────
    if persona.do_now_style and do_now:
        persona_style_lower = persona.do_now_style.lower()
        generated_type = _detect_do_now_type(do_now)

        # Map persona description to expected type
        if any(w in persona_style_lower for w in ("scenario", "analogy", "imagine", "hypothetical")):
            expected_type = "scenario"
        elif any(w in persona_style_lower for w in ("recall", "review", "yesterday", "prior")):
            expected_type = "recall"
        elif any(w in persona_style_lower for w in ("opinion", "debate", "provocative")):
            expected_type = "opinion"
        else:
            expected_type = None

        if expected_type and generated_type != expected_type and generated_type != "other":
            result.do_now_style_ok = False
            result.issues.append(
                f"Do Now style mismatch: persona prefers '{expected_type}' "
                f"but generated Do Now appears to be '{generated_type}'"
            )

    # ── Overall pass/fail ─────────────────────────────────────────────
    result.passed = result.address_term_ok and result.do_now_style_ok and result.structure_ok
    return result
```

- [ ] **Step 4: Run tests**

Run: `cd /Users/mind_uploaded_crustacean/Projects/Claw-ED-v0920 && python -m pytest tests/test_voice_check.py -v`

- [ ] **Step 5: Wire voice check into generate_lesson_bundle.py**

In `clawed/agent_core/tools/generate_lesson_bundle.py`, after the self-review block (around line 233) and before "Generate student packet + admin plan in parallel", add:

```python
        # ── Voice validation ──────────────────────────────────────────
        voice_notes: list[str] = []
        try:
            from clawed.voice_check import check_voice_match

            voice_result = check_voice_match(
                persona=persona,
                do_now=lesson.do_now,
                direct_instruction_opening=lesson.direct_instruction[:500] if lesson.direct_instruction else "",
            )
            if not voice_result.passed:
                for issue in voice_result.issues:
                    voice_notes.append(issue)
                    logger.info("Voice check issue: %s", issue)
        except Exception as e:
            logger.debug("Voice check failed: %s", e)
```

Then in the response builder at the bottom, add after the errors block:

```python
        if voice_notes:
            lines.append("\nVoice match notes:")
            for note in voice_notes:
                lines.append(f"  - {note}")
            lines.append("Want me to adjust the lesson to better match your voice?")
```

- [ ] **Step 6: Run full lint + test suite**

Run: `cd /Users/mind_uploaded_crustacean/Projects/Claw-ED-v0920 && ruff check . && python -m pytest tests/ -q --tb=short`

- [ ] **Step 7: Commit**

```bash
git add clawed/voice_check.py tests/test_voice_check.py clawed/agent_core/tools/generate_lesson_bundle.py
git commit -m "feat: lightweight voice validation after lesson generation"
```

---

## Task 5: Phase 5 — SOUL.md Consolidation

**Files:**
- Modify: `clawed/workspace.py` — add `consolidate_soul()`
- Modify: `clawed/agent_core/tools/update_soul.py` — add dedup check
- Create: `tests/test_soul_consolidation.py`

- [ ] **Step 1: Write tests**

Create `tests/test_soul_consolidation.py`:

```python
"""Tests for SOUL.md consolidation and dedup."""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from clawed.workspace import consolidate_soul, _deduplicate_entry


def test_deduplicate_entry_detects_substring_match():
    existing = "## Agent Observations\n\n*(2026-03-01)* Voice patterns: calls students 'friends'\n"
    assert _deduplicate_entry(existing, "Voice patterns: calls students 'friends'", "## Agent Observations") is True


def test_deduplicate_entry_allows_new_content():
    existing = "## Agent Observations\n\n*(2026-03-01)* Uses jigsaw activities\n"
    assert _deduplicate_entry(existing, "Uses Socratic seminar frequently", "## Agent Observations") is False


def test_consolidate_soul_backs_up(tmp_path):
    soul = tmp_path / "soul.md"
    soul.write_text("# Teaching Identity\n\n## Agent Observations\n\n"
                     "*(2026-01-01)* Voice: calls students 'friends'\n"
                     "*(2026-01-15)* Voice: calls students 'friends'\n"
                     "*(2026-02-01)* Voice: calls students 'friends'\n"
                     "*(2026-02-15)* Uses jigsaw with expert groups\n")

    with patch("clawed.workspace.SOUL_PATH", soul):
        # Mock the LLM call to return consolidated content
        async def mock_generate(*a, **kw):
            return ("# Teaching Identity\n\n## Agent Observations\n\n"
                    "- Voice: calls students 'friends'\n"
                    "- Uses jigsaw with expert groups\n")

        import asyncio
        with patch("clawed.workspace._llm_consolidate_soul", mock_generate):
            asyncio.run(consolidate_soul())

    # Backup should exist
    backup = tmp_path / "soul.md.bak"
    assert backup.exists()
    # Original should be updated (shorter)
    assert soul.read_text().count("friends") == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/mind_uploaded_crustacean/Projects/Claw-ED-v0920 && python -m pytest tests/test_soul_consolidation.py -v`

- [ ] **Step 3: Add consolidation to workspace.py**

In `clawed/workspace.py`, add:

```python
def _deduplicate_entry(content: str, new_entry: str, section_header: str) -> bool:
    """Check if a substantially similar entry already exists in a section.

    Returns True if a duplicate is found (i.e., the entry should NOT be appended).
    Uses simple substring matching — good enough for catching repeated observations.
    """
    # Extract the section content
    if section_header not in content:
        return False

    section_start = content.index(section_header) + len(section_header)
    # Find next section or end
    next_section = content.find("\n## ", section_start)
    section_text = content[section_start:next_section] if next_section != -1 else content[section_start:]

    # Check for substantial overlap (core phrase matching)
    # Strip date prefixes like "(2026-03-01)" for comparison
    clean_entry = re.sub(r"\(\d{4}-\d{2}-\d{2}\)\s*", "", new_entry).strip().lower()
    clean_section = re.sub(r"\(\d{4}-\d{2}-\d{2}\)\s*", "", section_text).strip().lower()

    # If the core content (ignoring dates) is already present
    if clean_entry in clean_section:
        return True

    # Check if >70% of words overlap with any existing line
    entry_words = set(clean_entry.split())
    if not entry_words:
        return False

    for line in clean_section.split("\n"):
        line_words = set(line.strip().split())
        if not line_words:
            continue
        overlap = len(entry_words & line_words)
        if entry_words and overlap / len(entry_words) > 0.7:
            return True

    return False


async def _llm_consolidate_soul(content: str) -> str:
    """Send SOUL.md to LLM for consolidation."""
    from clawed.llm import LLMClient
    from clawed.models import AppConfig

    client = LLMClient(AppConfig.load())
    return await client.generate(
        prompt=content,
        system=(
            "This is a teaching identity document that has accumulated observations over time. "
            "Consolidate it: merge duplicates, remove contradictions (keep the most recent), "
            "and produce a clean, concise version. Preserve the section structure. "
            "Keep specific details (names, schools, patterns) but eliminate redundancy. "
            "Return ONLY the consolidated markdown document."
        ),
        temperature=0.2,
        max_tokens=2000,
    )


_SOUL_SIZE_THRESHOLD = 3000  # characters


async def consolidate_soul() -> bool:
    """Consolidate SOUL.md by merging duplicates and removing redundancy.

    Saves a backup as SOUL.md.bak before overwriting.
    Returns True if consolidation was performed.
    """
    if not SOUL_PATH.exists():
        return False

    content = SOUL_PATH.read_text(encoding="utf-8")
    if len(content) < _SOUL_SIZE_THRESHOLD:
        return False

    # Save backup
    backup_path = SOUL_PATH.with_suffix(".md.bak")
    backup_path.write_text(content, encoding="utf-8")

    try:
        consolidated = await _llm_consolidate_soul(content)
        if consolidated and len(consolidated) > 50:
            SOUL_PATH.write_text(consolidated, encoding="utf-8")
            logger.info("SOUL.md consolidated: %d -> %d chars", len(content), len(consolidated))
            return True
    except Exception as e:
        logger.warning("SOUL.md consolidation failed: %s", e)
        # Restore from backup if something went wrong
        if backup_path.exists():
            SOUL_PATH.write_text(backup_path.read_text(encoding="utf-8"), encoding="utf-8")

    return False
```

Add `import logging` and `logger = logging.getLogger(__name__)` at the top of workspace.py if not present.

- [ ] **Step 4: Update update_soul.py to check for duplicates**

In `clawed/agent_core/tools/update_soul.py`:

First, fix the path inconsistency — replace the hardcoded path (line 95):
```python
        soul_path = Path.home() / ".eduagent" / "workspace" / "SOUL.md"
```
with:
```python
        from clawed.workspace import SOUL_PATH
        soul_path = SOUL_PATH
```

Then, in the `execute` method, before the write (around line 108), add a dedup check:

```python
        # Check for duplicate before appending
        from clawed.workspace import _deduplicate_entry
        if _deduplicate_entry(current, content, header):
            return ToolResult(
                text=f"Observation already exists in SOUL.md section '{section_key}' — skipping duplicate.",
            )
```

- [ ] **Step 5: Run tests**

Run: `cd /Users/mind_uploaded_crustacean/Projects/Claw-ED-v0920 && python -m pytest tests/test_soul_consolidation.py -v`

- [ ] **Step 6: Run full lint + test suite**

Run: `cd /Users/mind_uploaded_crustacean/Projects/Claw-ED-v0920 && ruff check . && python -m pytest tests/ -q --tb=short`

- [ ] **Step 7: Commit**

```bash
git add clawed/workspace.py clawed/agent_core/tools/update_soul.py tests/test_soul_consolidation.py
git commit -m "feat: SOUL.md consolidation and deduplication"
```

---

## Task 6: Phase 6 — Honest Error Reporting

**Files:**
- Modify: `clawed/agent_core/tools/generate_lesson_bundle.py`

- [ ] **Step 1: Replace the response builder in generate_lesson_bundle.py**

Replace the current response builder (lines ~326-343) with explicit error reporting:

```python
        # ── Build honest response ─────────────────────────────────────
        successful = [s for s in side_effects]
        lines = []

        if len(generated_files) == 3 and not errors:
            lines.append(f"Complete teaching package for: {lesson.title}")
            lines.append("All three files ready to print:")
            for se in successful:
                lines.append(f"  - {se}")
        elif generated_files:
            lines.append(f"Generated {len(generated_files)} of 3 files for: {lesson.title}")
            for se in successful:
                lines.append(f"  - {se}")
            if errors:
                lines.append("")
                for err in errors:
                    # Frame as actionable info, not stack traces
                    clean_err = str(err).split("\n")[0][:200]
                    lines.append(f"  Could not generate: {clean_err}")
                lines.append("Want me to try the failed item(s) again?")
        else:
            lines.append(f"Failed to generate teaching package for: {lesson.title}")
            for err in errors:
                lines.append(f"  - {err}")

        # Note if student packet used fallback
        if not student_packet and "Student packet" in " ".join(side_effects):
            lines.append("")
            lines.append(
                "Note: The student packet was generated using a simpler method — "
                "it may not have full graphic organizers. Let me know if you'd like me to regenerate it."
            )

        if kb_context:
            lines.append("\nReferenced your existing materials on this topic.")

        # Self-review findings
        try:
            if review and not review.get("passed", True) and review.get("issues"):
                lines.append("")
                lines.append("Quality notes:")
                for issue in review["issues"][:3]:
                    lines.append(f"  - {issue}")
        except NameError:
            pass

        if voice_notes:
            lines.append("\nVoice match notes:")
            for note in voice_notes:
                lines.append(f"  - {note}")
            lines.append("Want me to adjust the lesson to better match your voice?")
```

- [ ] **Step 2: Run full lint + test suite**

Run: `cd /Users/mind_uploaded_crustacean/Projects/Claw-ED-v0920 && ruff check . && python -m pytest tests/ -q --tb=short`

- [ ] **Step 3: Commit**

```bash
git add clawed/agent_core/tools/generate_lesson_bundle.py
git commit -m "feat: honest error reporting — teacher sees what succeeded and what failed"
```

---

## Task 7: Phase 7 — Pedagogical Quality Tests

**Files:**
- Create: `tests/test_lesson_quality.py`
- Create: `tests/test_student_packet_quality.py`

- [ ] **Step 1: Create test_lesson_quality.py**

Create `tests/test_lesson_quality.py` with fixtures and tests. The tests validate `DailyLesson` model instances against pedagogical standards — no LLM needed.

```python
"""Pedagogical quality tests for DailyLesson structured data.

These tests validate that generated lessons meet observation-ready standards.
They operate on DailyLesson model instances — no LLM required.
"""
from __future__ import annotations

import re

import pytest

from clawed.models import DailyLesson, DifferentiationNotes, ExitTicketQuestion


# ── Fixtures: good and bad lesson examples ─────────────────────────────


def _good_lesson() -> DailyLesson:
    """A well-formed lesson that should pass all quality checks."""
    return DailyLesson(
        title="The Causes of the American Revolution",
        lesson_number=1,
        objective="Students will be able to analyze three primary causes of colonial unrest by examining source documents and identifying grievances.",
        standards=["NYS SS 8.2a", "CCSS.RH.6-8.2"],
        do_now="Imagine your family has to pay a new tax on every drink of water. You had no say in this decision. Write 2-3 sentences: How would you react? (4 minutes)",
        direct_instruction=(
            "Alright friends, that scenario you just wrote about? That's exactly how colonists felt. "
            "Let's look at three key acts that pushed them toward revolution. "
            "First, the Stamp Act of 1765. Say: 'The British Parliament passed this without any colonial representatives present.' "
            "Think-pair-share: Why would taxation without representation be such a big deal? (2 minutes) "
            "Now let's look at this excerpt from the Declaration of Independence: "
            "'He has imposed Taxes on us without our Consent.' "
            "Cold call: [Student], what does 'consent' mean here? "
            "Good — consent means agreement or permission. So the colonists are saying... "
            "Second act: the Quartering Act. Soldiers living in your house. "
            "Turn and tell your partner: How is this different from the Stamp Act? (1 minute)"
        ),
        guided_practice=(
            "In your groups of 4, you each have a different document. Person A has the Stamp Act text. "
            "Person B has a letter from Samuel Adams. Person C has a merchant's diary entry. "
            "Person D has a British Parliament speech defending the taxes. "
            "Read your document silently (3 minutes), then teach your group what you learned (2 minutes each). "
            "Fill in the graphic organizer as you listen: Document / Author's Claim / Evidence / Significance."
        ),
        independent_work=(
            "Using your completed graphic organizer, write a 4-5 sentence paragraph answering: "
            "Which grievance was most likely to push colonists toward revolution? "
            "Use evidence from at least two documents. "
            "Early finisher extension: How might a British loyalist have responded to these grievances?"
        ),
        exit_ticket=[
            ExitTicketQuestion(question="Name two specific acts that angered the colonists.", expected_response="Stamp Act and Quartering Act (or Tea Act, Intolerable Acts)"),
            ExitTicketQuestion(question="Why was 'no taxation without representation' such a powerful idea?", expected_response="Colonists believed they had a right to consent to laws affecting them; being taxed without elected representatives violated their rights as English citizens."),
            ExitTicketQuestion(question="If you were a colonial leader in 1774, would you push for independence or try to negotiate? Use evidence from today's lesson.", expected_response="Strong answers reference specific documents/acts and weigh costs of rebellion vs negotiation."),
        ],
        differentiation=DifferentiationNotes(
            struggling=["Provide sentence starters: 'The colonists were angry because...'", "Pre-highlighted key phrases in each document", "Reduced graphic organizer with 2 columns instead of 4"],
            advanced=["Compare colonial grievances to a modern civil rights movement", "Analyze the British perspective using Document D"],
            ell=["Vocabulary preview card with 'tax', 'representation', 'consent' in English and Spanish cognates", "Paired with bilingual partner for document analysis"],
        ),
        materials_needed=["4 document excerpts (printed)", "Graphic organizer handout", "Exit ticket half-sheets"],
        time_estimates={"do_now": 4, "direct_instruction": 18, "guided_practice": 15, "independent_work": 10, "exit_ticket": 3},
    )


def _bad_lesson() -> DailyLesson:
    """A poorly-formed lesson that should fail quality checks."""
    return DailyLesson(
        title="American Revolution",
        lesson_number=1,
        objective="Students will understand the American Revolution.",
        standards=[],
        do_now="What do you know about the American Revolution?",
        direct_instruction="Teacher will discuss the causes of the American Revolution. Students will take notes. Check for understanding periodically.",
        guided_practice="Students will work in groups to discuss the reading.",
        independent_work="Complete the worksheet. Distribute the organizer.",
        exit_ticket=[ExitTicketQuestion(question="What did you learn today?")],
        differentiation=DifferentiationNotes(
            struggling=["Provide scaffolding", "Offer support"],
            advanced=["Extend learning"],
            ell=[],
        ),
        time_estimates={"do_now": 5, "direct_instruction": 25, "guided_practice": 15, "independent_work": 10},
    )


# ── Tests ──────────────────────────────────────────────────────────────


def test_times_add_up_to_class_period():
    """Total time across all sections must equal the class period (default 50 min)."""
    lesson = _good_lesson()
    total = sum(lesson.time_estimates.values())
    assert 42 <= total <= 55, f"Total time {total} min is outside 42-55 min range"


def test_times_bad_lesson_may_exceed():
    lesson = _bad_lesson()
    total = sum(lesson.time_estimates.values())
    assert total == 55, f"Bad lesson total is {total}"  # 5+25+15+10 = 55 > 50


def test_do_now_has_time_estimate():
    """The Do Now must have an explicit time estimate."""
    lesson = _good_lesson()
    assert "do_now" in lesson.time_estimates
    assert lesson.time_estimates["do_now"] > 0


def test_do_now_time_is_reasonable():
    """A Do Now should be 3-7 minutes."""
    lesson = _good_lesson()
    t = lesson.time_estimates.get("do_now", 0)
    assert 3 <= t <= 7, f"Do Now time {t} min is outside 3-7 min range"


def test_exit_ticket_has_questions():
    """Exit ticket must have at least 2 questions."""
    lesson = _good_lesson()
    assert len(lesson.exit_ticket) >= 2


def test_exit_ticket_bad_lesson_has_one():
    lesson = _bad_lesson()
    assert len(lesson.exit_ticket) < 2


def test_exit_ticket_has_expected_responses():
    """Every exit ticket question should have an expected response."""
    lesson = _good_lesson()
    for q in lesson.exit_ticket:
        assert q.expected_response, f"Exit ticket question '{q.question[:40]}' has no expected response"


def test_exit_ticket_bad_lesson_missing_responses():
    lesson = _bad_lesson()
    missing = [q for q in lesson.exit_ticket if not q.expected_response]
    assert len(missing) > 0


def test_standards_not_empty():
    """Standards list must not be empty when state is configured."""
    lesson = _good_lesson()
    assert len(lesson.standards) > 0


def test_standards_bad_lesson_empty():
    lesson = _bad_lesson()
    assert len(lesson.standards) == 0


def test_differentiation_is_specific():
    """Differentiation notes must contain specific strategies, not generic phrases."""
    lesson = _good_lesson()
    generic_phrases = ["provide scaffolding", "offer support", "extend learning", "provide extra"]
    all_diff = (
        lesson.differentiation.struggling
        + lesson.differentiation.advanced
        + lesson.differentiation.ell
    )
    for item in all_diff:
        assert not any(g in item.lower() for g in generic_phrases), (
            f"Generic differentiation: '{item}'"
        )


def test_differentiation_bad_lesson_is_generic():
    lesson = _bad_lesson()
    generic_phrases = ["provide scaffolding", "offer support", "extend learning"]
    all_diff = lesson.differentiation.struggling + lesson.differentiation.advanced
    generic_count = sum(
        1 for item in all_diff
        if any(g in item.lower() for g in generic_phrases)
    )
    assert generic_count > 0


def test_lesson_has_check_for_understanding():
    """Direct instruction must contain at least one specific check-for-understanding moment."""
    lesson = _good_lesson()
    di = lesson.direct_instruction.lower()
    cfu_indicators = [
        "think-pair-share", "turn and tell", "cold call", "thumbs up",
        "show me", "whiteboard", "pair-share", "tell your partner",
        "turn to your", "quick write",
    ]
    assert any(ind in di for ind in cfu_indicators), (
        "Direct instruction has no specific check-for-understanding activity"
    )


def test_bad_lesson_lacks_specific_cfu():
    lesson = _bad_lesson()
    di = lesson.direct_instruction.lower()
    cfu_indicators = [
        "think-pair-share", "turn and tell", "cold call", "thumbs up",
        "show me", "whiteboard", "pair-share", "tell your partner",
    ]
    # "check for understanding" as a phrase doesn't count
    assert not any(ind in di for ind in cfu_indicators)


def test_vocabulary_is_defined_in_instruction():
    """Any content-specific term in the objective should appear with context in instruction."""
    lesson = _good_lesson()
    # Extract key nouns from objective (words >5 chars, capitalized or domain-specific)
    objective_terms = re.findall(r'\b([A-Z][a-z]{4,}|[a-z]{6,})\b', lesson.objective)
    # Filter to content-specific terms (not function words)
    skip = {"students", "should", "analyze", "identify", "explain", "compare", "evaluate",
            "understand", "examine", "describe", "demonstrate", "applying", "examining"}
    content_terms = [t for t in objective_terms if t.lower() not in skip]
    if content_terms:
        di_lower = lesson.direct_instruction.lower()
        for term in content_terms[:3]:  # Check top 3 content terms
            assert term.lower() in di_lower, (
                f"Objective term '{term}' not found in direct instruction"
            )


def test_materials_referenced_are_described():
    """If the lesson says 'distribute the organizer,' the practice must describe what's on it."""
    lesson = _good_lesson()
    if "organizer" in lesson.independent_work.lower() or "organizer" in lesson.guided_practice.lower():
        # The organizer should be described somewhere
        combined = lesson.guided_practice + " " + lesson.independent_work
        assert "column" in combined.lower() or "row" in combined.lower() or "chart" in combined.lower(), (
            "Organizer referenced but not described"
        )
```

- [ ] **Step 2: Create test_student_packet_quality.py**

Create `tests/test_student_packet_quality.py`:

```python
"""Structural quality tests for StudentPacket data."""
from __future__ import annotations

import pytest

from clawed.models import (
    GuidedNotesBlank,
    GraphicOrganizerSpec,
    PrimarySourceDocument,
    StudentPacket,
    VocabularyTerm,
)


def _good_packet() -> StudentPacket:
    return StudentPacket(
        title="Causes of the American Revolution — Student Packet",
        aim="How did British policies push colonists toward revolution?",
        do_now_prompt="Imagine your family must pay a new tax on water. You had no say. Write 2-3 sentences: How do you react?",
        do_now_response_lines=4,
        vocabulary=[
            VocabularyTerm(term="Taxation", definition="A required payment to the government"),
            VocabularyTerm(term="Representation", definition="Having someone speak on your behalf in government"),
            VocabularyTerm(term="Grievance", definition="A formal complaint about unfair treatment"),
        ],
        guided_notes=[
            GuidedNotesBlank(sentence_with_blank="The ________ Act of 1765 taxed all printed materials.", answer="Stamp"),
            GuidedNotesBlank(sentence_with_blank="Colonists argued there should be no taxation without ________.", answer="representation"),
        ],
        stations=[
            PrimarySourceDocument(
                document_label="DOCUMENT 1: The Stamp Act (1765)",
                title="The Stamp Act",
                author="British Parliament",
                date="1765",
                context="Parliament passed this act to raise revenue from the colonies after the French and Indian War.",
                full_text="An act for granting and applying certain stamp duties, and other duties, in the British colonies and plantations in America... imposing duties on vellum, parchment, and paper used in the colonies.",
                analysis_questions=["What items were taxed?", "Why would colonists object?", "How does this connect to the idea of consent?"],
            ),
        ],
        graphic_organizer=GraphicOrganizerSpec(
            title="Document Analysis Chart",
            instructions="As you read each document, fill in one row.",
            columns=["Document", "Author's Claim", "Evidence", "Significance"],
            num_rows=3,
        ),
        exit_ticket_questions=["Name two British acts that angered colonists.", "Why was 'no taxation without representation' powerful?"],
        sentence_starters=["The colonists were angry because...", "This is significant because..."],
    )


def _bad_packet() -> StudentPacket:
    return StudentPacket(
        title="Revolution Packet",
        do_now_prompt="",
        vocabulary=[],
        stations=[
            PrimarySourceDocument(
                document_label="Document 1",
                full_text="See textbook page 45.",
                analysis_questions=["Discuss."],
            ),
        ],
        exit_ticket_questions=["What did you learn?"],
    )


def test_packet_has_do_now():
    packet = _good_packet()
    assert packet.do_now_prompt, "Packet must have a Do Now prompt"
    assert len(packet.do_now_prompt) > 10


def test_bad_packet_missing_do_now():
    packet = _bad_packet()
    assert not packet.do_now_prompt


def test_packet_has_vocabulary():
    packet = _good_packet()
    assert len(packet.vocabulary) >= 2


def test_exit_ticket_has_multiple_questions():
    packet = _good_packet()
    assert len(packet.exit_ticket_questions) >= 2


def test_bad_packet_exit_ticket_too_few():
    packet = _bad_packet()
    assert len(packet.exit_ticket_questions) < 2


def test_source_excerpts_are_substantive():
    """Station sources must have real text, not just references."""
    packet = _good_packet()
    for station in packet.stations:
        assert len(station.full_text) > 30, f"Station '{station.document_label}' has too-short source text"
        assert "see textbook" not in station.full_text.lower(), "Source must be quoted, not referenced"
        assert "see page" not in station.full_text.lower()


def test_bad_packet_sources_are_references():
    packet = _bad_packet()
    refs = [s for s in packet.stations if "see " in s.full_text.lower() or len(s.full_text) < 30]
    assert len(refs) > 0


def test_graphic_organizer_has_columns():
    packet = _good_packet()
    assert packet.graphic_organizer is not None
    assert len(packet.graphic_organizer.columns) >= 2
```

- [ ] **Step 3: Run tests**

Run: `cd /Users/mind_uploaded_crustacean/Projects/Claw-ED-v0920 && python -m pytest tests/test_lesson_quality.py tests/test_student_packet_quality.py -v`
Expected: PASS for good lessons, PASS for bad lesson detection.

- [ ] **Step 4: Run full lint + test suite**

Run: `cd /Users/mind_uploaded_crustacean/Projects/Claw-ED-v0920 && ruff check . && python -m pytest tests/ -q --tb=short`

- [ ] **Step 5: Commit**

```bash
git add tests/test_lesson_quality.py tests/test_student_packet_quality.py
git commit -m "feat: pedagogical quality tests — automated checks for lesson structure"
```

---

## Task 8: Phase 8 — Smarter Image Reuse

**Files:**
- Modify: `clawed/slide_images.py` — enhance `_fetch_teacher_image` to search context text
- Modify: `clawed/asset_registry.py` — store slide context text during image extraction

- [ ] **Step 1: Enhance _fetch_teacher_image in slide_images.py**

The current implementation (line ~478) already searches `context_text` from the `asset_images` table. The key improvement is to make the keyword matching smarter — use the slide's surrounding text (title + body + notes) instead of just the document title.

In `_fetch_teacher_image`, replace the simple keyword overlap scoring with:

```python
        # Score using both keyword overlap AND semantic proximity
        best_path: Optional[str] = None
        best_score = 0
        for row in rows:
            context = (row["context_text"] or "").lower()
            title = (row["title"] or "").lower()
            combined = f"{context} {title}"

            # Exact phrase match gets bonus
            query_lower = query.lower()
            score = 0
            if query_lower in combined:
                score += 5

            # Keyword overlap
            score += sum(2 for kw in keywords if kw in combined)

            # Partial word matches (e.g., "suffrage" matches "suffragist")
            score += sum(0.5 for kw in keywords if any(kw in word or word in kw for word in combined.split()) and kw not in combined)

            if score > best_score:
                best_score = score
                best_path = row["image_path"]

        if best_path and best_score >= 2 and Path(best_path).exists():
```

- [ ] **Step 2: Ensure asset_registry stores slide context during ingestion**

Check `clawed/asset_registry.py` for the image extraction code — it should store `context_text` (slide title + body text + notes) alongside each extracted image in the `asset_images` table. If the `context_text` column already exists and is populated during PPTX ingestion, this step is done. If not, add context storage.

- [ ] **Step 3: Run full lint + test suite**

Run: `cd /Users/mind_uploaded_crustacean/Projects/Claw-ED-v0920 && ruff check . && python -m pytest tests/ -q --tb=short`

- [ ] **Step 4: Commit**

```bash
git add clawed/slide_images.py clawed/asset_registry.py
git commit -m "feat: smarter image reuse — search slide context text, not just titles"
```

---

## Task 9: Phase 9 — Subject-Conditional Prompts

**Files:**
- Modify: `clawed/prompts/lesson_plan.txt`
- Modify: `clawed/prompts/student_packet.txt`
- Modify: `clawed/prompts/admin_lesson_plan.txt`

This phase adds subject-conditional instructions within existing templates. No new files. No separate templates per subject. The templates already receive `{subject}` — we add conditional blocks.

- [ ] **Step 1: Update lesson_plan.txt — subject-conditional instructions**

In `clawed/prompts/lesson_plan.txt`, locate the `### Principle 1: Embedded Real Content` section (~line 45-51). It already has subject-conditional examples. Make the quality standards section at the bottom also conditional:

After the existing quality standard `2. **Primary sources must be quoted in full.**`, wrap it and add alternatives:

Replace:
```
2. **Primary sources must be quoted in full.** If using a primary source, include the complete excerpt with attribution (author, date, title). Do not write "[Insert primary source here]" — find or compose an appropriate excerpt.
```

With:
```
2. **Subject-specific content standards:**
   - For history and social studies: Primary sources must be quoted in full with attribution (author, date, title). Do not write "[Insert primary source here]."
   - For math: Worked examples must be fully solved step-by-step with think-aloud annotations. Do not write "students will solve equations" — show the actual equations with solutions.
   - For science: Lab procedures must include specific measurements, materials quantities, and expected observations. Phenomenon descriptions must be concrete, not abstract.
   - For ELA: Include the actual passage, poem excerpt, or mentor sentence — not "students will read a text."
```

- [ ] **Step 2: Update student_packet.txt — subject-conditional stations**

In `clawed/prompts/student_packet.txt`, update section 4 (Station Documents / Primary Sources):

After the current station instructions, add:

```
Note on subject adaptation:
- If the subject is history or social studies: stations should feature primary source documents with full text, context, and sourcing questions.
- If the subject is math: stations should feature problem sets with worked examples at increasing difficulty. Each station covers a different problem type.
- If the subject is science: stations should feature data tables, lab observations, or phenomenon descriptions. Each station presents different data to analyze.
- If the subject is ELA: stations should feature different text excerpts (poetry, prose, nonfiction) with comprehension and analysis questions.
Match the station format to the subject. Do not use primary source document analysis for a math lesson.
```

- [ ] **Step 3: Update admin_lesson_plan.txt — subject-conditional content knowledge**

In `clawed/prompts/admin_lesson_plan.txt`, update section 4 (Teacher Content Knowledge):

Replace:
```
4. **Teacher Content Knowledge** — 2-3 paragraphs of background information the teacher should know about the topic beyond what's in the lesson. This is the "expert knowledge" section — historical context, historiographic debates, connections to other units.
```

With:
```
4. **Teacher Content Knowledge** — 2-3 paragraphs of background information the teacher should know about the topic beyond what's in the lesson. Adapt to the subject:
   - For history/social studies: historical context, historiographic debates, connections to other units.
   - For math: common student misconceptions about this concept and how to address them, alternative solution methods, connections to prerequisite and future skills.
   - For science: current scientific understanding beyond the grade level, common student misconceptions, real-world applications of the concept.
   - For ELA: literary criticism perspectives, author background, connections to other texts and genres.
```

- [ ] **Step 4: Run full lint + test suite**

Run: `cd /Users/mind_uploaded_crustacean/Projects/Claw-ED-v0920 && ruff check . && python -m pytest tests/ -q --tb=short`

- [ ] **Step 5: Commit**

```bash
git add clawed/prompts/lesson_plan.txt clawed/prompts/student_packet.txt clawed/prompts/admin_lesson_plan.txt
git commit -m "feat: subject-conditional prompts — math, science, ELA no longer forced into SS format"
```

---

## Task 10: Phase 10 — Fix Stale Handout Test

**Files:**
- Modify: `tests/test_handout_export.py:40`

- [ ] **Step 1: Check what the current export function returns**

Read `clawed/export_handout.py` to see what filename pattern `export_handout_docx` produces. The test expects `_handout.docx` in the filename but the file may now be `_packet.docx`.

- [ ] **Step 2: Update the assertion**

In `tests/test_handout_export.py`, line 40, change:
```python
        assert "handout" in path.name.lower()
```
to:
```python
        assert "handout" in path.name.lower() or "packet" in path.name.lower()
```

- [ ] **Step 3: Run the specific test**

Run: `cd /Users/mind_uploaded_crustacean/Projects/Claw-ED-v0920 && python -m pytest tests/test_handout_export.py -v`

- [ ] **Step 4: Commit**

```bash
git add tests/test_handout_export.py
git commit -m "fix: update stale handout test assertion for _packet.docx filename"
```

---

## Task 11: Phase 11 — Version Bump, Test, Commit, Push

**Files:**
- Modify: `pyproject.toml:7`
- Modify: `clawed/__init__.py:20`
- Modify: `ROADMAP.md`

- [ ] **Step 1: Bump version in pyproject.toml**

Change line 7:
```toml
version = "2.3.3"
```

- [ ] **Step 2: Bump version in __init__.py**

Change line 20:
```python
__version__ = "2.3.3"
```

- [ ] **Step 3: Update ROADMAP.md**

In the `## v1.1.0 -- Better Memory (shipped as v2.2.0)` section, add:
```markdown
- [x] Voice validation after generation — automatic checks for address terms, Do Now style, structure
- [x] Pedagogical fingerprint evolution — persona updates when new files are ingested or rating patterns shift
```

Add a new section after v1.1.0:
```markdown
## v2.3.3 -- Quality Layer

Output trustworthy enough to hand directly to students.

- [x] LLM-enhanced reading report — qualitative observations alongside regex data
- [x] Student packet matches teacher's handout style (new persona field)
- [x] Pedagogical fingerprint evolves with new evidence
- [x] Voice validation after generation (address terms, Do Now style, structure)
- [x] SOUL.md consolidation — deduplicates observations, stays concise
- [x] Honest error reporting — teacher sees what succeeded and what failed
- [x] Lesson quality tests — automated checks for time, standards, differentiation
- [x] Smarter image reuse — searches slide context text, not just document titles
- [x] Subject-conditional prompts — math gets worked examples, science gets lab procedures
```

- [ ] **Step 4: Run full lint + test suite**

Run: `cd /Users/mind_uploaded_crustacean/Projects/Claw-ED-v0920 && ruff check . && python -m pytest tests/ -q --tb=short`
Expected: ALL PASS

- [ ] **Step 5: Fix any failures**

If any tests fail, fix them before proceeding.

- [ ] **Step 6: Commit everything**

```bash
git add -A
git commit -m "v2.3.3: quality layer — voice validation, smart reading reports, honest errors

- Reading report uses LLM to produce qualitative observations alongside regex data
- Student packet respects teacher's handout style (new persona field, conditional format)
- Pedagogical fingerprint updates when new files are ingested or rating patterns shift
- Voice check after generation: verifies address terms, Do Now style, structural match
- SOUL.md consolidation: deduplicates observations, keeps it concise
- Honest error reporting: tells the teacher what succeeded and what failed
- Lesson quality tests: automated checks for time, standards, differentiation specificity
- Smarter image reuse: searches slide context text, not just document titles
- Subject-conditional prompts: math gets worked examples, science gets lab procedures
- Fix stale handout test assertion"
```

- [ ] **Step 7: Push to remote**

```bash
git push origin main
```

---

## Quality Checklist (from the prompt)

After implementation, verify each question can be answered "yes":

| Question | Phase |
|----------|-------|
| Did I actually read this teacher's work, or did I just count keywords? | 1 |
| Does the student packet look like something this specific teacher would create? | 2 |
| Would I notice if this teacher's style changed over six months? | 3 |
| Does this lesson actually sound like this teacher, and can I prove it? | 4 |
| Is SOUL.md a concise identity document or an append-only log? | 5 |
| Does the teacher know exactly what they got and what they didn't? | 6 |
| Would these quality checks catch the problems I found in the v1.0.0 Women's Suffrage lesson? | 7 |
| Could a math teacher use this without feeling like it was built for a history teacher? | 9 |
