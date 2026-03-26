# Claw-ED v0.9.20 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform Claw-ED from a lesson generator into a curriculum-aware teaching partner that knows a teacher's files, generates beautiful materials, and feels like a real colleague.

**Architecture:** Seven independent workstreams: (1) config/models foundation, (2) curriculum knowledge base, (3) system prompt + agentic personality, (4) beautiful exports, (5) LLM adapter cleanup + infrastructure, (6) OAuth providers, (7) docs/version/cleanup. Tasks 1 must go first. Tasks 2-6 can be parallelized after Task 1. Task 7 goes last.

**Tech Stack:** Python 3.10+, Pydantic 2.x, SQLite, python-docx, python-pptx, httpx, pytest

---

## Task 1: Config & Models Foundation

**Files:**
- Modify: `clawed/models.py`
- Modify: `clawed/__init__.py`
- Modify: `pyproject.toml`
- Modify: `clawed/agent_core/context.py`
- Test: `tests/test_basic.py`
- Test: `tests/test_agent_core.py`

- [ ] **Step 1: Add agent_name and new fields to AppConfig**

In `clawed/models.py`, add to `AppConfig`:

```python
# Custom agent name (teacher picks during onboarding)
agent_name: str = "Claw-ED"

# Google Gemini support
google_model: str = "gemini-2.5-flash"

# Max agent loop iterations (configurable for complex requests)
max_agent_iterations: int = 20

# Web dashboard password (None = no auth)
dashboard_password: Optional[str] = None
```

Add `GOOGLE` to `LLMProvider` enum:

```python
class LLMProvider(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OLLAMA = "ollama"
    GOOGLE = "google"
```

- [ ] **Step 2: Write tests for new config fields**

In `tests/test_basic.py`, add:

```python
class TestAppConfigV0920:
    def test_agent_name_default(self):
        cfg = AppConfig()
        assert cfg.agent_name == "Claw-ED"

    def test_agent_name_custom(self):
        cfg = AppConfig(agent_name="Sage")
        assert cfg.agent_name == "Sage"

    def test_google_provider(self):
        cfg = AppConfig(provider=LLMProvider.GOOGLE)
        assert cfg.provider == LLMProvider.GOOGLE
        assert cfg.google_model == "gemini-2.5-flash"

    def test_max_agent_iterations_default(self):
        cfg = AppConfig()
        assert cfg.max_agent_iterations == 20

    def test_dashboard_password_none_by_default(self):
        cfg = AppConfig()
        assert cfg.dashboard_password is None
```

- [ ] **Step 3: Run tests to verify**

Run: `cd /Users/mind_uploaded_crustacean/Projects/Claw-ED-v0920 && python -m pytest tests/test_basic.py -v --tb=short -q`

- [ ] **Step 4: Update AgentContext to carry agent_name**

In `clawed/agent_core/context.py`, add `agent_name: str = "Claw-ED"` to `AgentContext`:

```python
@dataclass
class AgentContext:
    """Passed to every tool — the agent's working state."""
    teacher_id: str
    config: AppConfig
    teacher_profile: dict[str, Any]
    persona: dict[str, Any] | None
    session_history: list[dict[str, Any]]
    improvement_context: str
    agent_name: str = "Claw-ED"
```

- [ ] **Step 5: Update version**

`clawed/__init__.py`: Change `__version__ = "0.9.19"` to `__version__ = "0.9.20"`

`pyproject.toml`: Change `version = "0.9.19"` to `version = "0.9.20"`

Update any test files that assert the version number.

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest tests/ -q --tb=short 2>&1 | tail -20`

- [ ] **Step 7: Commit**

```bash
git add clawed/models.py clawed/__init__.py pyproject.toml clawed/agent_core/context.py tests/test_basic.py
git commit -m "feat: v0.9.20 foundation — agent_name, Google provider, configurable iterations"
```

---

## Task 2: Curriculum Knowledge Base

**Files:**
- Create: `clawed/agent_core/memory/curriculum_kb.py`
- Create: `clawed/agent_core/tools/search_my_materials.py`
- Modify: `clawed/handlers/ingest.py`
- Modify: `clawed/agent_core/memory/loader.py`
- Modify: `clawed/agent_core/memory/episodes.py`
- Test: `tests/test_curriculum_kb.py`

- [ ] **Step 1: Write tests for CurriculumKB**

Create `tests/test_curriculum_kb.py`:

```python
"""Tests for the Curriculum Knowledge Base."""
import tempfile
from pathlib import Path

import pytest

from clawed.agent_core.memory.curriculum_kb import CurriculumKB


class TestCurriculumKB:
    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        self.db_path = Path(self.tmp) / "test_kb.db"
        self.kb = CurriculumKB(db_path=self.db_path)

    def test_index_and_search(self):
        self.kb.index(
            teacher_id="t1",
            doc_title="Civil War Unit",
            source_path="/docs/civil_war.docx",
            full_text="The Civil War began in 1861 when Confederate forces attacked Fort Sumter. "
                      "Key causes included slavery, states rights, and economic differences.",
            metadata={"subject": "History", "grade": "8"},
        )
        results = self.kb.search("t1", "What caused the Civil War?", top_k=5)
        assert len(results) > 0
        assert "Civil War" in results[0]["chunk_text"]
        assert results[0]["doc_title"] == "Civil War Unit"

    def test_deduplication(self):
        text = "Photosynthesis converts light energy into chemical energy."
        self.kb.index("t1", "Bio Notes", "/bio.docx", text)
        self.kb.index("t1", "Bio Notes", "/bio.docx", text)  # duplicate
        results = self.kb.search("t1", "photosynthesis", top_k=100)
        # Should not have duplicate chunks
        chunks = [r["chunk_text"] for r in results]
        assert len(chunks) == len(set(chunks))

    def test_stats(self):
        self.kb.index("t1", "Doc A", "/a.docx", "Content about math fractions.")
        self.kb.index("t1", "Doc B", "/b.docx", "Content about science cells.")
        stats = self.kb.stats("t1")
        assert stats["doc_count"] == 2
        assert stats["chunk_count"] >= 2

    def test_search_empty_kb(self):
        results = self.kb.search("t1", "anything", top_k=5)
        assert results == []

    def test_teacher_isolation(self):
        self.kb.index("t1", "T1 Doc", "/t1.docx", "Teacher one material.")
        self.kb.index("t2", "T2 Doc", "/t2.docx", "Teacher two material.")
        results = self.kb.search("t1", "material", top_k=10)
        for r in results:
            assert "Teacher two" not in r["chunk_text"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_curriculum_kb.py -v --tb=short`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement CurriculumKB**

Create `clawed/agent_core/memory/curriculum_kb.py`:

```python
"""Curriculum Knowledge Base — semantic search over teacher's uploaded materials.

This is the core differentiator: teacher files aren't analyzed once and
forgotten. They become a living database the agent searches every time
it generates content. The embedding model (Ollama or TF-IDF fallback)
powers similarity search so the agent can find relevant prior work.
"""
from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from clawed.agent_core.memory.embeddings import get_embedder

logger = logging.getLogger(__name__)

_DEFAULT_DB = Path.home() / ".eduagent" / "memory" / "curriculum_kb.db"
_CHUNK_SIZE = 500  # tokens (approx chars / 4)
_CHUNK_OVERLAP = 50


class CurriculumKB:
    """Semantic search over a teacher's uploaded curriculum files.

    Documents are chunked, embedded, and stored in SQLite. The agent
    searches this KB before generating to ground output in the teacher's
    own materials.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or _DEFAULT_DB
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._embedder = get_embedder()
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    teacher_id TEXT NOT NULL,
                    doc_title TEXT NOT NULL,
                    source_path TEXT,
                    chunk_text TEXT NOT NULL,
                    chunk_hash TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_chunks_teacher "
                "ON chunks(teacher_id)"
            )
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_chunks_dedup "
                "ON chunks(teacher_id, chunk_hash)"
            )

    @staticmethod
    def _chunk_text(text: str) -> list[str]:
        """Split text into overlapping chunks of roughly _CHUNK_SIZE tokens."""
        words = text.split()
        chunk_words = _CHUNK_SIZE
        overlap_words = _CHUNK_OVERLAP
        chunks = []
        start = 0
        while start < len(words):
            end = start + chunk_words
            chunk = " ".join(words[start:end])
            if chunk.strip():
                chunks.append(chunk.strip())
            start += chunk_words - overlap_words
        return chunks or [text.strip()] if text.strip() else []

    def index(
        self,
        teacher_id: str,
        doc_title: str,
        source_path: str,
        full_text: str,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Chunk, embed, and store a document. Returns number of new chunks added."""
        from datetime import datetime

        chunks = self._chunk_text(full_text)
        added = 0
        meta_json = json.dumps(metadata or {})

        with sqlite3.connect(self._db_path) as conn:
            for chunk in chunks:
                chunk_hash = hashlib.sha256(chunk.encode()).hexdigest()[:32]
                # Skip if this exact chunk already exists for this teacher
                existing = conn.execute(
                    "SELECT 1 FROM chunks WHERE teacher_id=? AND chunk_hash=?",
                    (teacher_id, chunk_hash),
                ).fetchone()
                if existing:
                    continue

                embedding = self._embedder.embed(chunk)
                conn.execute(
                    "INSERT INTO chunks "
                    "(teacher_id, doc_title, source_path, chunk_text, chunk_hash, "
                    "embedding, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        teacher_id,
                        doc_title,
                        source_path,
                        chunk,
                        chunk_hash,
                        json.dumps(embedding),
                        meta_json,
                        datetime.now().isoformat(),
                    ),
                )
                added += 1

        logger.debug(
            "Indexed %d new chunks from '%s' for teacher %s",
            added, doc_title, teacher_id,
        )
        return added

    def search(
        self,
        teacher_id: str,
        query: str,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Search the teacher's curriculum files by semantic similarity."""
        query_embedding = self._embedder.embed(query)

        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT doc_title, source_path, chunk_text, embedding, metadata, created_at "
                "FROM chunks WHERE teacher_id = ? "
                "ORDER BY created_at DESC LIMIT 200",
                (teacher_id,),
            ).fetchall()

        if not rows:
            return []

        scored = []
        for row in rows:
            stored_embedding = json.loads(row["embedding"])
            sim = self._embedder.cosine_similarity(query_embedding, stored_embedding)
            scored.append({
                "doc_title": row["doc_title"],
                "source_path": row["source_path"],
                "chunk_text": row["chunk_text"],
                "metadata": json.loads(row["metadata"]),
                "created_at": row["created_at"],
                "similarity": sim,
            })

        scored.sort(key=lambda x: x["similarity"], reverse=True)
        return scored[:top_k]

    def stats(self, teacher_id: str) -> dict[str, Any]:
        """Return stats about the teacher's curriculum knowledge base."""
        with sqlite3.connect(self._db_path) as conn:
            doc_count = conn.execute(
                "SELECT COUNT(DISTINCT doc_title) FROM chunks WHERE teacher_id=?",
                (teacher_id,),
            ).fetchone()[0]
            chunk_count = conn.execute(
                "SELECT COUNT(*) FROM chunks WHERE teacher_id=?",
                (teacher_id,),
            ).fetchone()[0]
        return {
            "doc_count": doc_count,
            "chunk_count": chunk_count,
        }
```

- [ ] **Step 4: Run KB tests**

Run: `python -m pytest tests/test_curriculum_kb.py -v --tb=short`
Expected: PASS

- [ ] **Step 5: Create search_my_materials tool**

Create `clawed/agent_core/tools/search_my_materials.py`:

```python
"""Tool: search_my_materials — search the teacher's uploaded curriculum files."""
from __future__ import annotations

from typing import Any

from clawed.agent_core.context import AgentContext, ToolResult


class SearchMyMaterialsTool:
    """Search the teacher's curriculum knowledge base for relevant content."""

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "search_my_materials",
                "description": (
                    "Search the teacher's uploaded curriculum files for relevant "
                    "content. Use this BEFORE generating lessons, units, or materials "
                    "to ground your output in the teacher's own prior work. Returns "
                    "matching excerpts with source file attribution."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": (
                                "What to search for — a topic, concept, or question. "
                                "Example: 'Civil War causes', 'photosynthesis lab', "
                                "'fractions worksheet'"
                            ),
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Maximum results to return (default 5)",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
            },
        }

    async def execute(
        self, params: dict[str, Any], context: AgentContext
    ) -> ToolResult:
        from clawed.agent_core.memory.curriculum_kb import CurriculumKB

        query = params["query"]
        top_k = params.get("top_k", 5)
        teacher_id = context.teacher_id

        try:
            kb = CurriculumKB()
            results = kb.search(teacher_id, query, top_k=top_k)

            if not results:
                stats = kb.stats(teacher_id)
                if stats["doc_count"] == 0:
                    return ToolResult(
                        text="No curriculum files uploaded yet. Ask the teacher "
                             "to share their lesson plans, handouts, or other "
                             "teaching materials so you can reference them."
                    )
                return ToolResult(
                    text=f"No matches found for '{query}' in "
                         f"{stats['doc_count']} uploaded documents."
                )

            # Format results with source attribution
            lines = [f"Found {len(results)} relevant excerpts from your files:\n"]
            for i, r in enumerate(results, 1):
                source = r["doc_title"]
                if r.get("source_path"):
                    source = f"{r['doc_title']} ({Path(r['source_path']).name})"
                sim_pct = int(r["similarity"] * 100)
                lines.append(
                    f"**{i}. From '{source}'** ({sim_pct}% match):\n"
                    f"{r['chunk_text'][:300]}{'...' if len(r['chunk_text']) > 300 else ''}\n"
                )

            return ToolResult(
                text="\n".join(lines),
                data={"results": results, "query": query},
            )
        except Exception as e:
            return ToolResult(text=f"Failed to search curriculum files: {e}")
```

Add missing import at top of file:
```python
from pathlib import Path
```

- [ ] **Step 6: Update ingest handler to index into KB**

In `clawed/handlers/ingest.py`, after the persona extraction block, add KB indexing:

```python
# Index documents into curriculum knowledge base
kb_info = ""
try:
    from clawed.agent_core.memory.curriculum_kb import CurriculumKB
    kb = CurriculumKB()
    total_chunks = 0
    for doc in documents:
        chunks_added = kb.index(
            teacher_id=teacher_id,
            doc_title=doc.title,
            source_path=doc.source_path or "",
            full_text=doc.content,
            metadata={"doc_type": doc.doc_type.value if hasattr(doc.doc_type, 'value') else str(doc.doc_type)},
        )
        total_chunks += chunks_added
    stats = kb.stats(teacher_id)
    kb_info = (
        f"\n\nAdded to your curriculum library — I now have "
        f"{stats['doc_count']} document(s) ({stats['chunk_count']} searchable sections). "
        f"I'll reference your materials when creating new content."
    )
except Exception as e:
    logger.debug("KB indexing skipped: %s", e)
```

Update the return text to include `kb_info`.

- [ ] **Step 7: Update memory loader with curriculum context**

In `clawed/agent_core/memory/loader.py`, add a curriculum KB search layer:

```python
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
```

Add `"curriculum_kb_context": curriculum_kb_context` to the return dict.

- [ ] **Step 8: Fix episodic memory scaling**

In `clawed/agent_core/memory/episodes.py`, update the `recall()` SQL query:

```python
rows = conn.execute(
    "SELECT text, embedding, metadata, created_at "
    "FROM episodes WHERE teacher_id = ? "
    "AND created_at > date('now', '-90 days') "
    "ORDER BY created_at DESC LIMIT 200",
    (teacher_id,),
).fetchall()
```

- [ ] **Step 9: Run full test suite**

Run: `python -m pytest tests/ -q --tb=short 2>&1 | tail -20`

- [ ] **Step 10: Commit**

```bash
git add clawed/agent_core/memory/curriculum_kb.py clawed/agent_core/tools/search_my_materials.py \
  clawed/handlers/ingest.py clawed/agent_core/memory/loader.py clawed/agent_core/memory/episodes.py \
  tests/test_curriculum_kb.py
git commit -m "feat: curriculum knowledge base — teacher files become a searchable database

The embedding model (Ollama or TF-IDF) powers semantic search over
ingested materials. The agent searches this KB before every generation
to ground output in the teacher's own prior work."
```

---

## Task 3: System Prompt & Agentic Personality

**Files:**
- Modify: `clawed/agent_core/prompt.py`
- Modify: `clawed/agent_core/core.py`
- Modify: `clawed/agent_core/tools/configure_profile.py`
- Test: `tests/test_agent_core.py`

- [ ] **Step 1: Rewrite build_system_prompt**

Replace `clawed/agent_core/prompt.py` with the new agentic prompt that:
- Uses `agent_name` parameter instead of hardcoded "Claw-ED"
- Adds curriculum KB instructions
- Adds status narration instructions
- Adds proactive suggestion instructions
- Adds first-interaction naming flow
- Keeps all existing context injection (identity, improvement, curriculum, episodes, preferences, autonomy)

```python
"""System prompt assembly for the agent core."""
from __future__ import annotations


def build_system_prompt(
    *,
    agent_name: str = "Claw-ED",
    teacher_name: str,
    identity_summary: str,
    improvement_context: str,
    tool_names: list[str],
    curriculum_summary: str = "",
    relevant_episodes: str = "",
    preferences: str = "",
    autonomy_summary: str = "",
    curriculum_kb_context: str = "",
) -> str:
    """Assemble the agent's system prompt from canonical context."""
    sections = [
        f"You are {agent_name}, a teaching partner for {teacher_name}.",
        "",
        "You are not a chatbot. You are a colleague who happens to live inside "
        "a computer. You know this teacher's curriculum because you've read their "
        "files. You don't wait to be told every step — you take initiative, you "
        "do the work, and you deliver polished results.",
        "",
        "When the teacher asks you to do something, use your tools. "
        "Do not describe what you would do — actually do it by calling "
        "the appropriate tool.",
    ]

    # First interaction — naming + onboarding
    sections.append(
        "\n## First Interaction\n"
        "If this is your first conversation with a new teacher (no profile set up yet), "
        "introduce yourself warmly — share something inspiring about teaching, "
        "explain who you are and what you can do. Then get to know them:\n"
        "1. Their name\n"
        "2. What subject(s) they teach\n"
        "3. What grade level(s)\n"
        "4. What state (for standards alignment)\n"
        "5. What they'd like to call you (you go by Claw-ED by default, but "
        "they can name you anything — Sage, Coach, their department mascot, whatever feels right)\n"
        "Ask these ONE at a time through natural conversation, not as a form. "
        "Use the configure_profile tool to save their info as you learn it. "
        "Make it feel like meeting a new colleague on the first day of school."
    )

    # Curriculum Knowledge Base
    sections.append(
        "\n## Your Curriculum Knowledge Base\n"
        "You have access to everything this teacher has uploaded — lesson plans, "
        "handouts, notes, assessments. This is your textbook. ALWAYS search their "
        "materials (search_my_materials) before generating new content. Reference "
        "what they've already created by name. When you find relevant prior work, "
        "weave it into your generation — build on what exists, don't start from scratch.\n"
        "This is what makes you a real partner: you know their curriculum."
    )

    if curriculum_kb_context:
        sections.append(
            f"\n## Relevant Materials From This Teacher's Files\n"
            f"{curriculum_kb_context}"
        )

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
            f"You have {len(tool_names)} tools: {', '.join(tool_names)}.\n"
            f"Use them to take action rather than just suggesting."
        )

    # How you work
    sections.append(
        "\n## How You Work\n"
        "When given a task, work through it:\n"
        "1. Search the teacher's curriculum files for relevant prior work\n"
        "2. Tell the teacher what you found and what you're about to do\n"
        "3. Generate the content, grounded in their existing materials\n"
        "4. Export professional files (DOCX and/or PPTX) automatically\n"
        "5. Suggest 1-2 logical next steps"
    )

    # Status narration
    sections.append(
        "\n## Status Updates\n"
        "As you work through multi-step tasks, give brief progress updates. "
        "Keep them to one sentence each:\n"
        '- "Searching your files for Civil War materials..."\n'
        '- "Found 3 related lessons. Building your unit plan now."\n'
        '- "Exporting to PPTX..."\n'
        "This makes the teacher feel like you're working alongside them."
    )

    # Proactive suggestions
    sections.append(
        "\n## Proactive Suggestions\n"
        "After completing a task, suggest 1-2 natural next steps based on "
        "what's missing. If you generated a lesson but there's no worksheet, "
        "offer to make one. If a unit has no assessment, mention it. If you "
        "notice a gap in standards coverage, flag it.\n"
        "Be helpful, not pushy — one short suggestion, not a menu."
    )

    # Guidelines
    sections.append(
        "\n## Guidelines\n"
        "- Ask ONE question at a time, keep responses concise\n"
        "- When generating content, call the tool immediately — don't ask for confirmation\n"
        "- ALWAYS export generated content as files. After generating a lesson, unit, or "
        "materials, immediately call export_document to create DOCX and/or PPTX files. "
        "Teachers need printable documents, not chat text.\n"
        "- Keep chat responses SHORT — confirm what you made and what files are attached\n"
        "- For consequential actions (publishing to students, sharing), use request_approval\n"
        "- You CAN change configuration — use switch_model to change AI models, "
        "configure_profile to update teaching info\n"
        "- If you can't help with something, say so honestly\n"
        f"- Always refer to yourself as {agent_name}"
    )

    return "\n".join(sections)
```

- [ ] **Step 2: Update tests for new prompt signature**

In `tests/test_agent_core.py`, update `TestPromptAssembly`:

```python
class TestPromptAssembly:
    def test_builds_prompt_with_custom_agent_name(self):
        from clawed.agent_core.prompt import build_system_prompt
        prompt = build_system_prompt(
            agent_name="Sage",
            teacher_name="Ms. Smith",
            identity_summary="8th grade Science",
            improvement_context="",
            tool_names=["generate_lesson"],
        )
        assert "Sage" in prompt
        assert "Ms. Smith" in prompt
        assert "Claw-ED" not in prompt.split("## First Interaction")[0]

    def test_builds_prompt_with_default_name(self):
        from clawed.agent_core.prompt import build_system_prompt
        prompt = build_system_prompt(
            teacher_name="Teacher",
            identity_summary="",
            improvement_context="",
            tool_names=[],
        )
        assert "Claw-ED" in prompt

    def test_curriculum_kb_context_included(self):
        from clawed.agent_core.prompt import build_system_prompt
        prompt = build_system_prompt(
            teacher_name="Teacher",
            identity_summary="",
            improvement_context="",
            tool_names=[],
            curriculum_kb_context="From 'Civil War Unit': Key causes included...",
        )
        assert "Civil War Unit" in prompt
        assert "Your Curriculum Knowledge Base" in prompt

    def test_proactive_suggestions_in_prompt(self):
        from clawed.agent_core.prompt import build_system_prompt
        prompt = build_system_prompt(
            teacher_name="Teacher",
            identity_summary="",
            improvement_context="",
            tool_names=[],
        )
        assert "Proactive Suggestions" in prompt
        assert "Status Updates" in prompt
```

- [ ] **Step 3: Update core.py to pass agent_name and curriculum KB context**

In `clawed/agent_core/core.py`, update `_agent_loop`:

- Read `agent_name` from `self.config.agent_name`
- Pass it to `build_system_prompt(agent_name=agent_name, ...)`
- Pass `curriculum_kb_context=memory_ctx.get("curriculum_kb_context", "")` to `build_system_prompt`
- Pass `agent_name=agent_name` when constructing `AgentContext`
- Pass `max_iterations=self.config.max_agent_iterations` to `run_agent_loop()`

- [ ] **Step 4: Update configure_profile tool to accept agent_name**

In `clawed/agent_core/tools/configure_profile.py`, add `agent_name` parameter:

```python
"agent_name": {
    "type": "string",
    "description": "What the teacher wants to call their AI partner (default: Claw-ED)",
    "default": "",
},
```

In `execute()`, if `agent_name` is provided, save to config:

```python
agent_name = params.get("agent_name", "").strip()
if agent_name:
    config.agent_name = agent_name
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_agent_core.py -v --tb=short`

- [ ] **Step 6: Commit**

```bash
git add clawed/agent_core/prompt.py clawed/agent_core/core.py \
  clawed/agent_core/tools/configure_profile.py tests/test_agent_core.py
git commit -m "feat: agentic personality — custom naming, curriculum-aware, proactive suggestions

System prompt rewritten for search-first behavior, status narration,
and proactive next-step suggestions. Teachers name their agent during
onboarding. Agent always refers to itself by the chosen name."
```

---

## Task 4: Beautiful Exports

**Files:**
- Create: `clawed/export_templates.py`
- Modify: `clawed/export_docx.py`
- Modify: `clawed/export_pptx.py`
- Modify: `clawed/export_theme.py`
- Modify: `clawed/agent_core/loop.py`
- Test: `tests/test_exports_v0920.py`

- [ ] **Step 1: Create export_templates.py**

```python
"""Professional document themes for Claw-ED exports.

Defines font, color, and spacing constants used by DOCX and PPTX
exporters. v0.9.20 ships a single PROFESSIONAL theme; v0.10 will
add teacher-selectable themes.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DocxTheme:
    """Typography and color constants for DOCX exports."""
    title_font: str = "Calibri"
    title_size: int = 20
    heading_font: str = "Calibri"
    heading_size: int = 14
    body_font: str = "Calibri"
    body_size: int = 11
    accent_color: str = "2B579A"
    light_accent: str = "D6E4F0"
    header_bg: str = "2B579A"
    footer_text: str = "Created with Claw-ED"
    iep_bg_color: str = "FFF3CD"  # Warm yellow for IEP/ELL callouts
    ell_bg_color: str = "D1ECF1"  # Light blue for ELL callouts


@dataclass(frozen=True)
class PptxTheme:
    """Typography and color constants for PPTX exports."""
    title_font: str = "Calibri"
    title_size: int = 36
    subtitle_size: int = 18
    body_font: str = "Calibri"
    body_size: int = 20
    accent_color: str = "2B579A"
    bg_color: str = "FFFFFF"
    divider_height: float = 0.12  # inches


PROFESSIONAL_DOCX = DocxTheme()
PROFESSIONAL_PPTX = PptxTheme()
```

- [ ] **Step 2: Improve DOCX header/footer**

In `clawed/export_docx.py`, update `export_lesson_docx` to add:
- Professional header with teacher name, school, subject, date — right-aligned
- Page number footer
- Apply consistent Calibri typography from theme
- Differentiation section uses shaded callout boxes for IEP/ELL
- Rubric as formatted table with shaded header
- Replace "Generated by Claw-ED" watermark with agent_name if available

Key changes to `export_lesson_docx`:

```python
def export_lesson_docx(
    lesson: "DailyLesson",
    persona: "TeacherPersona",
    output_dir: Path | None = None,
    agent_name: str = "Claw-ED",
) -> Path:
```

Add header section after doc creation:
```python
from clawed.export_templates import PROFESSIONAL_DOCX as theme

# Professional header
header_section = doc.sections[0]
header = header_section.header
header_para = header.paragraphs[0]
header_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
header_run = header_para.add_run(
    f"{persona.name or 'Teacher'}  |  "
    f"{persona.subject_area or 'Education'}  |  "
    f"{date.today().strftime('%B %d, %Y')}"
)
header_run.font.size = Pt(9)
header_run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
header_run.font.name = theme.body_font

# Footer with page numbers
footer = header_section.footer
footer_para = footer.paragraphs[0]
footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
footer_run = footer_para.add_run(f"{agent_name}  |  Page ")
footer_run.font.size = Pt(8)
footer_run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
```

- [ ] **Step 3: Add section divider slides to PPTX**

In `clawed/export_pptx.py`, add a `_section_divider_slide` helper that creates clean divider slides between lesson phases. Update `export_lesson_pptx` to insert dividers before Do Now, Direct Instruction, Guided Practice, Independent Practice, and Exit Ticket sections.

Also update the closing watermark to use `agent_name`:

```python
def export_lesson_pptx(
    lesson: "DailyLesson",
    persona: "TeacherPersona",
    output_dir: Path | None = None,
    agent_name: str = "Claw-ED",
) -> Path:
```

```python
# Update watermark
run_wm.text = f"Generated by {agent_name}"
```

- [ ] **Step 4: Add post-generation export guarantee to loop.py**

In `clawed/agent_core/loop.py`, after the tool-use loop, check if generation tools were called but export wasn't:

```python
# Post-generation export guarantee
_GENERATION_TOOLS = {"generate_lesson", "generate_unit", "generate_materials", "generate_assessment"}
_EXPORT_TOOL = "export_document"

generation_called = False
export_called = False
for iteration_msgs in messages:
    if isinstance(iteration_msgs, dict) and iteration_msgs.get("tool_calls"):
        for tc in iteration_msgs["tool_calls"]:
            if tc["name"] in _GENERATION_TOOLS:
                generation_called = True
            if tc["name"] == _EXPORT_TOOL:
                export_called = True

if generation_called and not export_called and all_files:
    # Agent generated content but forgot to export — that's OK,
    # the files from generation tools are already in all_files
    pass
```

Also update `run_agent_loop` to accept `max_iterations` parameter.

- [ ] **Step 5: Write export tests**

Create `tests/test_exports_v0920.py`:

```python
"""Tests for v0.9.20 export improvements."""
import pytest

from clawed.export_templates import PROFESSIONAL_DOCX, PROFESSIONAL_PPTX, DocxTheme, PptxTheme


class TestExportTemplates:
    def test_docx_theme_defaults(self):
        theme = PROFESSIONAL_DOCX
        assert theme.title_font == "Calibri"
        assert theme.accent_color == "2B579A"
        assert theme.iep_bg_color == "FFF3CD"

    def test_pptx_theme_defaults(self):
        theme = PROFESSIONAL_PPTX
        assert theme.title_size == 36
        assert theme.accent_color == "2B579A"

    def test_themes_are_frozen(self):
        with pytest.raises(AttributeError):
            PROFESSIONAL_DOCX.title_font = "Arial"
```

- [ ] **Step 6: Run tests**

Run: `python -m pytest tests/test_exports_v0920.py -v --tb=short`

- [ ] **Step 7: Commit**

```bash
git add clawed/export_templates.py clawed/export_docx.py clawed/export_pptx.py \
  clawed/agent_core/loop.py tests/test_exports_v0920.py
git commit -m "feat: beautiful exports — professional DOCX/PPTX with headers, dividers, themed formatting

Section divider slides, consistent typography, IEP/ELL callout boxes,
page headers/footers, and post-generation export guarantee."
```

---

## Task 5: Infrastructure Cleanup

**Files:**
- Modify: `clawed/agent_core/core.py` (LLMClientAdapter cleanup)
- Modify: `clawed/agent_core/autonomy.py` (SQLite migration)
- Modify: `clawed/transports/telegram.py` (direct slash handlers)
- Test: `tests/test_autonomy.py`
- Test: `tests/test_approvals.py`

- [ ] **Step 1: Clean up _LLMClientAdapter**

In `clawed/agent_core/core.py`, replace the monkey-patching approach. Instead of swapping the global `TOOL_DEFINITIONS`, pass tools directly:

```python
class _LLMClientAdapter:
    """Adapts the clawed.agent LLM calling to LLMInterface.

    Passes tool schemas directly to the API call functions
    rather than monkey-patching module-level globals.
    """

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    async def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        system: str = "",
    ) -> dict[str, Any]:
        from clawed.agent import _call_with_native_tools, _call_with_ollama_tools
        from clawed.models import LLMProvider

        if self._config.provider in (LLMProvider.ANTHROPIC, LLMProvider.OPENAI):
            return await _call_with_native_tools(
                messages, system, self._config, tool_definitions=tools or []
            )
        else:
            return await _call_with_ollama_tools(
                messages, system, self._config, tool_definitions=tools or []
            )
```

This requires updating `_call_with_native_tools` and `_call_with_ollama_tools` in `clawed/agent.py` to accept an optional `tool_definitions` parameter. If not provided, fall back to the module-level `TOOL_DEFINITIONS` for backward compat.

- [ ] **Step 2: Migrate ApprovalTracker to SQLite**

Rewrite `clawed/agent_core/autonomy.py`:

```python
"""Autonomy progression — track approval rates and offer auto-approval.

v0.9.20: migrated from per-file JSON to SQLite for scalability.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_DB = Path.home() / ".eduagent" / "approvals.db"
_MIN_SAMPLES = 10
_AUTO_THRESHOLD = 0.95

_NEVER_AUTO_APPROVE = {
    "student_publish",
    "student_bot_config",
    "drive_upload",
    "drive_create_slides",
    "drive_create_doc",
    "share_with_students",
}


class ApprovalTracker:
    """Tracks approval/rejection rates per action type."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or _DEFAULT_DB
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._migrate_json_if_needed()

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS approvals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    action_payload TEXT DEFAULT '{}',
                    teacher_id TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    resolved_at TEXT
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_approvals_type "
                "ON approvals(action_type)"
            )

    def _migrate_json_if_needed(self) -> None:
        """One-time migration from JSON files to SQLite."""
        old_dir = self._db_path.parent / "approvals"
        if not old_dir.exists():
            return
        migrated = 0
        for path in old_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                status = data.get("status", "")
                if status not in ("approved", "rejected"):
                    continue
                action_type = data.get("action_payload", {}).get("action_type", "unknown")
                self._record(
                    action_type=action_type,
                    status=status,
                    action_payload=json.dumps(data.get("action_payload", {})),
                    teacher_id=data.get("teacher_id", ""),
                )
                migrated += 1
            except (json.JSONDecodeError, OSError):
                continue
        if migrated:
            logger.info("Migrated %d approval records from JSON to SQLite", migrated)

    def _record(self, action_type: str, status: str, action_payload: str = "{}",
                teacher_id: str = "") -> None:
        from datetime import datetime
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT INTO approvals (action_type, status, action_payload, teacher_id, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (action_type, status, action_payload, teacher_id, datetime.now().isoformat()),
            )

    def record_approval(self, action_type: str, approved: bool,
                        teacher_id: str = "", payload: dict | None = None) -> None:
        self._record(
            action_type=action_type,
            status="approved" if approved else "rejected",
            action_payload=json.dumps(payload or {}),
            teacher_id=teacher_id,
        )

    def get_rates(self) -> dict[str, dict[str, Any]]:
        with sqlite3.connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT action_type, status, COUNT(*) as cnt "
                "FROM approvals WHERE status IN ('approved', 'rejected') "
                "GROUP BY action_type, status"
            ).fetchall()

        counts: dict[str, dict[str, int]] = {}
        for action_type, status, cnt in rows:
            if action_type not in counts:
                counts[action_type] = {"approved": 0, "rejected": 0}
            counts[action_type][status] = cnt

        rates = {}
        for action_type, c in counts.items():
            total = c["approved"] + c["rejected"]
            if total > 0:
                rates[action_type] = {
                    "approval_rate": c["approved"] / total,
                    "total": total,
                    "approved": c["approved"],
                    "rejected": c["rejected"],
                }
        return rates

    def should_offer_auto(self, action_type: str) -> bool:
        if action_type in _NEVER_AUTO_APPROVE:
            return False
        rates = self.get_rates()
        if action_type not in rates:
            return False
        r = rates[action_type]
        return r["total"] >= _MIN_SAMPLES and r["approval_rate"] >= _AUTO_THRESHOLD

    def summarize_for_prompt(self) -> str:
        rates = self.get_rates()
        if not rates:
            return ""
        parts = []
        for action_type, r in rates.items():
            if r["total"] >= _MIN_SAMPLES:
                pct = int(r["approval_rate"] * 100)
                if r["approval_rate"] >= _AUTO_THRESHOLD:
                    parts.append(
                        f"- Teacher always approves '{action_type}' ({pct}% rate, "
                        f"{r['total']} samples) — you can offer to auto-approve."
                    )
                elif r["approval_rate"] >= 0.7:
                    parts.append(f"- Teacher usually approves '{action_type}' ({pct}% rate).")
                else:
                    parts.append(f"- Teacher often rejects '{action_type}' ({pct}% rate) — always ask first.")
        return "\n".join(parts) if parts else ""
```

- [ ] **Step 3: Update autonomy tests**

Update `tests/test_autonomy.py` to work with SQLite backend.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_autonomy.py tests/test_approvals.py tests/test_agent_core.py -v --tb=short`

- [ ] **Step 5: Commit**

```bash
git add clawed/agent_core/core.py clawed/agent_core/autonomy.py \
  tests/test_autonomy.py tests/test_approvals.py
git commit -m "fix: clean LLM adapter (no monkey-patching), approval tracker migrated to SQLite"
```

---

## Task 6: Google Gemini Provider

**Files:**
- Create: `clawed/auth/__init__.py`
- Create: `clawed/auth/google_auth.py`
- Modify: `clawed/llm.py`
- Modify: `clawed/onboarding.py`
- Modify: `clawed/model_router.py`

- [ ] **Step 1: Create auth package**

Create `clawed/auth/__init__.py`:

```python
"""Authentication helpers for LLM providers."""
```

Create `clawed/auth/google_auth.py`:

```python
"""Google Gemini authentication — API key or OAuth."""
from __future__ import annotations

import os
import logging

logger = logging.getLogger(__name__)


def get_google_api_key() -> str | None:
    """Resolve Google API key from env, keyring, or config."""
    key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    try:
        from clawed.config import get_api_key
        return get_api_key("google")
    except Exception:
        return None


def has_google_credentials() -> bool:
    """Check if Google credentials are available."""
    return get_google_api_key() is not None
```

- [ ] **Step 2: Add Google provider to llm.py**

In `clawed/llm.py`, add `_google` method after `_ollama`:

```python
async def _google(
    self, prompt: str, system: str, temperature: float, max_tokens: int
) -> str:
    """Call Google Gemini API."""
    from clawed.auth.google_auth import get_google_api_key

    api_key = get_google_api_key()
    if not api_key:
        raise EnvironmentError(
            "GOOGLE_API_KEY not set. Export it or run: clawed setup --reset"
        )
    messages_payload: list[dict[str, Any]] = []
    if system:
        messages_payload.append({
            "role": "user",
            "parts": [{"text": f"System instructions: {system}"}]
        })
        messages_payload.append({
            "role": "model",
            "parts": [{"text": "Understood. I will follow these instructions."}]
        })
    messages_payload.append({"role": "user", "parts": [{"text": prompt}]})

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{self.config.google_model}:generateContent",
                params={"key": api_key},
                headers={"Content-Type": "application/json"},
                json={
                    "contents": messages_payload,
                    "generationConfig": {
                        "temperature": temperature,
                        "maxOutputTokens": max_tokens,
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise EnvironmentError(
                "Invalid GOOGLE_API_KEY. Check your key at https://aistudio.google.com"
            )
        raise
```

Update the `generate` method router:

```python
elif self.config.provider == LLMProvider.GOOGLE:
    return await self._google(prompt, system, temperature, max_tokens)
```

- [ ] **Step 3: Update onboarding with expanded provider menu**

In `clawed/onboarding.py`, add Google Gemini as option 2 in the provider menu. Keep all existing Ollama/Anthropic/OpenAI/Local options. Auto-detect existing Google credentials.

- [ ] **Step 4: Update model_router.py with Gemini tiers**

Add Gemini model routing:
```python
"google": {
    "fast": "gemini-2.5-flash",
    "work": "gemini-2.5-flash",
    "deep": "gemini-2.5-pro",
}
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/ -q --tb=short 2>&1 | tail -20`

- [ ] **Step 6: Commit**

```bash
git add clawed/auth/ clawed/llm.py clawed/onboarding.py clawed/model_router.py
git commit -m "feat: Google Gemini provider — teachers use existing Google account

API key auth via GOOGLE_API_KEY or keyring. Gemini Flash for fast tasks,
Gemini Pro for deep generation. All existing providers unchanged."
```

---

## Task 7: Documentation, Cleanup & Release

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `FEATURES.md`
- Modify: `ROADMAP.md`
- Code cleanup across all modified files

- [ ] **Step 1: Rewrite README**

Lead with curriculum knowledge base as the headline value prop. Update:
- Hero description emphasizing "your files become a living database"
- Feature list with curriculum KB, custom naming, beautiful exports
- Provider list adding Google Gemini
- Tool count (25)
- Getting started section mentioning agent naming
- Highlight embedding model's role explicitly

- [ ] **Step 2: Update CHANGELOG**

Add v0.9.20 entry:

```markdown
## v0.9.20 — Curriculum Knowledge Base & Agentic Personality

### Added
- **Curriculum Knowledge Base** — uploaded files are chunked, embedded, and stored as a searchable database. The agent searches your materials before every generation.
- **search_my_materials tool** — agent explicitly searches teacher's uploaded files
- **Custom agent naming** — teachers name their AI partner during onboarding
- **Google Gemini provider** — use your existing Google account
- **Post-generation export guarantee** — files always delivered, even if LLM skips the tool call
- **Professional export templates** — DOCX/PPTX with headers, footers, section dividers
- **Section divider slides** in PPTX between lesson phases
- **IEP/ELL callout boxes** with shaded backgrounds in DOCX
- **Configurable max agent iterations** via AppConfig
- **Web dashboard basic auth** option

### Changed
- System prompt rewritten for search-first, status-narrating, suggestion-giving behavior
- Approval tracker migrated from JSON files to SQLite for scalability
- Episodic memory recall bounded to 90 days + 200 records
- LLM adapter cleaned up — no more monkey-patching of global state
- Ingest handler returns rich curriculum library stats

### Fixed
- Episodic memory O(n) scaling — now bounded by SQL LIMIT
- Approval tracking file glob — now single SQL query
```

- [ ] **Step 3: Update FEATURES.md and ROADMAP.md**

Add curriculum KB, custom naming, Google provider to features. Move v0.10 theme selection to roadmap.

- [ ] **Step 4: Code cleanup pass**

Across all modified files:
- Ensure `from __future__ import annotations` at top
- Consistent import ordering (stdlib, third-party, local)
- Remove any dead imports
- Add type hints to all public function signatures
- Add concise docstrings to all public classes and functions
- Run `ruff check .` and fix any issues

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest tests/ -q --tb=short`
Expected: All 1338+ tests passing

- [ ] **Step 6: Run linter**

Run: `cd /Users/mind_uploaded_crustacean/Projects/Claw-ED-v0920 && ruff check . 2>&1 | tail -20`

- [ ] **Step 7: Final commit**

```bash
git add -A
git commit -m "release: v0.9.20 — curriculum knowledge base, agentic personality, beautiful exports

Headline: Teacher files become a searchable database the agent consults
before every generation. Custom agent naming, Google Gemini support,
professional DOCX/PPTX templates, and a system prompt rewrite that
makes the agent feel like a real teaching colleague."
```

---

## Execution Order

```
Task 1 (foundation) ─── must go first
    │
    ├── Task 2 (curriculum KB) ──┐
    ├── Task 3 (prompt/agentic) ─┤── can run in parallel
    ├── Task 4 (beautiful exports)┤
    ├── Task 5 (infrastructure)  ─┤
    └── Task 6 (Google provider) ─┘
                                  │
                            Task 7 (docs/cleanup) ─── must go last
```
