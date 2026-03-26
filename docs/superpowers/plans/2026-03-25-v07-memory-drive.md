# v0.7 Memory + Drive Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 3-layer cognitive memory (identity, curriculum state, episodic with embeddings) and Google Drive integration (OAuth on teacher's account, upload/list/organize) to the agent core.

**Architecture:** Memory system replaces `memory_engine.py` with structured layers: identity (workspace file), curriculum state (SQLite projections from existing DB), and episodic memory (embedding-based semantic search using bundled ONNX model with TF-IDF fallback). Drive integration adds OAuth flow for teacher's personal Google account with rate limiting and approval gates for uploads. Both integrate into the existing agent core from v0.6.

**Tech Stack:** Python 3.10+, pytest, pytest-asyncio, onnxruntime (optional `[memory]` extra), google-api-python-client + google-auth-oauthlib (existing `[google]` extra), SQLite for episodic storage.

**Spec:** `docs/superpowers/specs/2026-03-25-v06-agent-core-design.md` Section 7 (v0.7)

---

## File Map

### New Files

| File | Responsibility |
|------|---------------|
| `clawed/agent_core/memory/__init__.py` | Package init |
| `clawed/agent_core/memory/identity.py` | Layer 1: load teacher identity from workspace |
| `clawed/agent_core/memory/curriculum.py` | Layer 2: curriculum state projections from canonical DB |
| `clawed/agent_core/memory/episodes.py` | Layer 3: episodic memory with embedding search |
| `clawed/agent_core/memory/embeddings.py` | Embedding provider (ONNX bundled, Ollama upgrade, TF-IDF fallback) |
| `clawed/agent_core/memory/loader.py` | Context loader: assembles all 3 layers into prompt context |
| `clawed/agent_core/tools/drive_upload.py` | Tool: upload files to Google Drive |
| `clawed/agent_core/tools/drive_list.py` | Tool: browse Drive folders |
| `clawed/agent_core/tools/drive_organize.py` | Tool: create folders, move files |
| `clawed/agent_core/drive/__init__.py` | Package init |
| `clawed/agent_core/drive/auth.py` | Google OAuth flow + token persistence |
| `clawed/agent_core/drive/client.py` | Drive API client with rate limiting |
| `tests/test_memory.py` | Memory system tests |
| `tests/test_drive.py` | Drive integration tests |

### Modified Files

| File | Change |
|------|--------|
| `clawed/agent_core/core.py` | Replace `_load_improvement_context()` with new memory loader |
| `clawed/agent_core/prompt.py` | Accept richer memory context (curriculum state, recent episodes) |
| `pyproject.toml` | Add `onnxruntime` to new `[memory]` extra, add `[memory]` to `[all]` |
| `clawed/models.py` | Add `drive_root_folder` and `drive_token_path` to AppConfig |

---

## Phase A: Cognitive Memory

### Task 1: Memory Package + Identity Layer

**Files:**
- Create: `clawed/agent_core/memory/__init__.py`
- Create: `clawed/agent_core/memory/identity.py`
- Test: `tests/test_memory.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_memory.py
"""Tests for the cognitive memory system."""
import pytest

from clawed.agent_core.memory.identity import load_identity


class TestIdentityLayer:
    def test_load_identity_no_workspace(self, tmp_path, monkeypatch):
        monkeypatch.setattr("clawed.agent_core.memory.identity.WORKSPACE_DIR", tmp_path / "nonexistent")
        result = load_identity()
        assert isinstance(result, dict)
        assert result.get("name", "") == ""

    def test_load_identity_with_persona(self, tmp_path, monkeypatch):
        monkeypatch.setenv("EDUAGENT_DATA_DIR", str(tmp_path))
        # Create a minimal identity file
        ws = tmp_path / "workspace"
        ws.mkdir(parents=True)
        (ws / "identity.md").write_text("# Ms. Smith\nSubject: Science\nGrade: 8\nStyle: inquiry-based\n")
        monkeypatch.setattr("clawed.agent_core.memory.identity.IDENTITY_PATH", ws / "identity.md")
        result = load_identity()
        assert "Ms. Smith" in result.get("raw", "")

    def test_load_identity_from_database(self, tmp_path, monkeypatch):
        monkeypatch.setenv("EDUAGENT_DATA_DIR", str(tmp_path))
        from clawed.agent_core.memory.identity import load_identity_from_db
        result = load_identity_from_db("nonexistent-teacher")
        assert isinstance(result, dict)
```

- [ ] **Step 2: Run test — confirm fail**
- [ ] **Step 3: Write implementation**

```python
# clawed/agent_core/memory/__init__.py
"""Cognitive memory system — 3-layer context for the agent."""

# clawed/agent_core/memory/identity.py
"""Layer 1: Teacher identity — slow-changing profile and persona."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# These get monkeypatched in tests via conftest.py
from clawed.workspace import IDENTITY_PATH, WORKSPACE_DIR


def load_identity() -> dict[str, Any]:
    """Load teacher identity from workspace identity.md file."""
    result: dict[str, Any] = {"name": "", "raw": "", "subjects": [], "grades": [], "style": ""}
    try:
        if IDENTITY_PATH.exists():
            raw = IDENTITY_PATH.read_text(encoding="utf-8")
            result["raw"] = raw
            # Extract name from first heading
            for line in raw.splitlines():
                if line.startswith("# "):
                    result["name"] = line[2:].strip()
                    break
    except Exception as e:
        logger.debug("Could not load identity: %s", e)
    return result


def load_identity_from_db(teacher_id: str) -> dict[str, Any]:
    """Load teacher profile and persona from canonical database."""
    result: dict[str, Any] = {"name": "", "persona": None, "profile": {}}
    try:
        from clawed.database import Database
        db = Database()
        teacher = db.get_default_teacher()
        if teacher:
            result["profile"] = dict(teacher)
            if teacher.get("persona_json"):
                result["persona"] = json.loads(teacher["persona_json"])
                result["name"] = result["persona"].get("name", "")
    except Exception as e:
        logger.debug("Could not load teacher from DB: %s", e)
    return result
```

- [ ] **Step 4: Run test — confirm pass**
- [ ] **Step 5: Lint and commit**

```bash
git add clawed/agent_core/memory/ tests/test_memory.py
git commit -m "feat(memory): add Layer 1 — identity loader from workspace and DB"
```

---

### Task 2: Curriculum State Layer

**Files:**
- Create: `clawed/agent_core/memory/curriculum.py`
- Test: Append to `tests/test_memory.py`

- [ ] **Step 1: Write failing test**

```python
class TestCurriculumStateLayer:
    def test_load_curriculum_state_empty(self, tmp_path, monkeypatch):
        monkeypatch.setenv("EDUAGENT_DATA_DIR", str(tmp_path))
        from clawed.agent_core.memory.curriculum import load_curriculum_state
        state = load_curriculum_state("nonexistent-teacher")
        assert isinstance(state, dict)
        assert state["units_generated"] == 0
        assert state["lessons_generated"] == 0
        assert state["recent_topics"] == []

    def test_summarize_curriculum_state(self):
        from clawed.agent_core.memory.curriculum import summarize_curriculum_state
        state = {
            "units_generated": 3,
            "lessons_generated": 15,
            "recent_topics": ["photosynthesis", "cell division"],
            "standards_covered": ["NGSS MS-LS1-5", "NGSS MS-LS1-6"],
            "avg_rating": 4.2,
        }
        summary = summarize_curriculum_state(state)
        assert "3 units" in summary
        assert "photosynthesis" in summary
```

- [ ] **Step 2: Run test — confirm fail**
- [ ] **Step 3: Write implementation**

```python
# clawed/agent_core/memory/curriculum.py
"""Layer 2: Curriculum state — projections from canonical database."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def load_curriculum_state(teacher_id: str) -> dict[str, Any]:
    """Load curriculum state from the canonical database.

    This is a read-only projection — the database is the source of truth.
    """
    state: dict[str, Any] = {
        "units_generated": 0,
        "lessons_generated": 0,
        "recent_topics": [],
        "standards_covered": [],
        "avg_rating": 0.0,
        "recent_feedback": [],
    }
    try:
        from clawed.database import Database
        db = Database()
        stats = db.get_stats()
        state["units_generated"] = stats.get("units", 0)
        state["lessons_generated"] = stats.get("lessons", 0)

        # Recent units for topic extraction
        units = db.list_units()
        state["recent_topics"] = [u.get("title", "") for u in units[:5] if u.get("title")]
    except Exception as e:
        logger.debug("Could not load curriculum state: %s", e)
    return state


def summarize_curriculum_state(state: dict[str, Any]) -> str:
    """Summarize curriculum state for the system prompt."""
    parts = []
    if state["units_generated"]:
        parts.append(f"You've generated {state['units_generated']} units and {state['lessons_generated']} lessons together.")
    if state["recent_topics"]:
        parts.append(f"Recent topics: {', '.join(state['recent_topics'][:5])}.")
    if state["standards_covered"]:
        parts.append(f"Standards covered so far: {', '.join(state['standards_covered'][:10])}.")
    if state["avg_rating"]:
        parts.append(f"Average lesson rating: {state['avg_rating']:.1f}/5.")
    if state["recent_feedback"]:
        parts.append(f"Recent feedback: {'; '.join(state['recent_feedback'][:3])}.")
    return " ".join(parts) if parts else ""
```

- [ ] **Step 4: Run test — confirm pass**
- [ ] **Step 5: Commit**

```bash
git add clawed/agent_core/memory/curriculum.py tests/test_memory.py
git commit -m "feat(memory): add Layer 2 — curriculum state projections from DB"
```

---

### Task 3: Embedding Provider (ONNX + TF-IDF fallback)

**Files:**
- Create: `clawed/agent_core/memory/embeddings.py`
- Modify: `pyproject.toml` — add `[memory]` extra
- Test: Append to `tests/test_memory.py`

- [ ] **Step 1: Write failing test**

```python
class TestEmbeddingProvider:
    def test_tfidf_fallback_embed(self):
        from clawed.agent_core.memory.embeddings import get_embedder
        embedder = get_embedder()  # should fall back to TF-IDF without onnxruntime
        vec = embedder.embed("photosynthesis is the process of converting light to energy")
        assert isinstance(vec, list)
        assert len(vec) > 0
        assert all(isinstance(x, float) for x in vec)

    def test_tfidf_similarity(self):
        from clawed.agent_core.memory.embeddings import get_embedder
        embedder = get_embedder()
        v1 = embedder.embed("photosynthesis in plants")
        v2 = embedder.embed("plant energy from sunlight")
        v3 = embedder.embed("the american revolution war")
        sim_related = embedder.cosine_similarity(v1, v2)
        sim_unrelated = embedder.cosine_similarity(v1, v3)
        assert sim_related > sim_unrelated  # related texts should be more similar

    def test_embed_batch(self):
        from clawed.agent_core.memory.embeddings import get_embedder
        embedder = get_embedder()
        vecs = embedder.embed_batch(["hello world", "foo bar"])
        assert len(vecs) == 2
```

- [ ] **Step 2: Run test — confirm fail**
- [ ] **Step 3: Add `[memory]` extra to pyproject.toml**

Add to `[project.optional-dependencies]`:
```toml
memory = ["onnxruntime>=1.16.0"]
```
Add `"onnxruntime>=1.16.0"` to the `all` list.

- [ ] **Step 4: Write implementation**

```python
# clawed/agent_core/memory/embeddings.py
"""Embedding providers for episodic memory.

Default: TF-IDF (no dependencies, always works).
Upgrade: ONNX all-MiniLM-L6-v2 (pip install 'clawed[memory]').
Upgrade: Ollama mxbai-embed-large (if Ollama running locally).
"""
from __future__ import annotations

import logging
import math
from typing import Protocol

logger = logging.getLogger(__name__)


class Embedder(Protocol):
    def embed(self, text: str) -> list[float]: ...
    def embed_batch(self, texts: list[str]) -> list[list[float]]: ...
    def cosine_similarity(self, a: list[float], b: list[float]) -> float: ...


class TFIDFEmbedder:
    """Simple TF-IDF based embedder — no dependencies, always available."""

    def __init__(self) -> None:
        self._vocab: dict[str, int] = {}
        self._next_idx = 0

    def embed(self, text: str) -> list[float]:
        tokens = text.lower().split()
        for t in tokens:
            if t not in self._vocab:
                self._vocab[t] = self._next_idx
                self._next_idx += 1
        vec = [0.0] * len(self._vocab)
        for t in tokens:
            vec[self._vocab[t]] += 1.0
        # L2 normalize
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]

    def cosine_similarity(self, a: list[float], b: list[float]) -> float:
        # Pad shorter vector
        max_len = max(len(a), len(b))
        a = a + [0.0] * (max_len - len(a))
        b = b + [0.0] * (max_len - len(b))
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
        norm_b = math.sqrt(sum(x * x for x in b)) or 1.0
        return dot / (norm_a * norm_b)


def get_embedder() -> TFIDFEmbedder:
    """Get the best available embedder.

    Returns ONNX embedder if available, otherwise TF-IDF fallback.
    """
    try:
        # Future: try ONNX first, then Ollama
        # For now: always TF-IDF (ONNX model download not yet implemented)
        raise ImportError("ONNX not yet configured")
    except ImportError:
        logger.debug("Using TF-IDF embedder (install 'clawed[memory]' for better recall)")
        return TFIDFEmbedder()
```

- [ ] **Step 5: Run test — confirm pass**
- [ ] **Step 6: Commit**

```bash
git add clawed/agent_core/memory/embeddings.py pyproject.toml tests/test_memory.py
git commit -m "feat(memory): add embedding provider with TF-IDF fallback"
```

---

### Task 4: Episodic Memory Layer

**Files:**
- Create: `clawed/agent_core/memory/episodes.py`
- Test: Append to `tests/test_memory.py`

- [ ] **Step 1: Write failing test**

```python
class TestEpisodicMemory:
    def test_store_and_recall(self, tmp_path):
        from clawed.agent_core.memory.episodes import EpisodicMemory
        mem = EpisodicMemory(db_path=tmp_path / "episodes.db")
        mem.store("t1", "I taught photosynthesis today and it went well")
        mem.store("t1", "Students struggled with the light reactions diagram")
        mem.store("t1", "The American Revolution unit is starting next week")

        results = mem.recall("t1", "photosynthesis", top_k=2)
        assert len(results) <= 2
        # photosynthesis-related entries should rank higher
        assert any("photosynthesis" in r["text"] for r in results)

    def test_recall_empty(self, tmp_path):
        from clawed.agent_core.memory.episodes import EpisodicMemory
        mem = EpisodicMemory(db_path=tmp_path / "episodes.db")
        results = mem.recall("t1", "anything", top_k=5)
        assert results == []

    def test_store_with_metadata(self, tmp_path):
        from clawed.agent_core.memory.episodes import EpisodicMemory
        mem = EpisodicMemory(db_path=tmp_path / "episodes.db")
        mem.store("t1", "Great lesson on fractions", metadata={"type": "feedback", "rating": 5})
        results = mem.recall("t1", "fractions")
        assert len(results) == 1
        assert results[0]["metadata"]["rating"] == 5

    def test_teacher_isolation(self, tmp_path):
        from clawed.agent_core.memory.episodes import EpisodicMemory
        mem = EpisodicMemory(db_path=tmp_path / "episodes.db")
        mem.store("t1", "Teacher 1 content")
        mem.store("t2", "Teacher 2 content")
        results = mem.recall("t1", "content")
        assert len(results) == 1
        assert "Teacher 1" in results[0]["text"]
```

- [ ] **Step 2: Run test — confirm fail**
- [ ] **Step 3: Write implementation**

```python
# clawed/agent_core/memory/episodes.py
"""Layer 3: Episodic memory — embedding-based semantic search over interactions."""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from clawed.agent_core.memory.embeddings import get_embedder

logger = logging.getLogger(__name__)

_DEFAULT_DB = Path.home() / ".eduagent" / "memory" / "episodes.db"


class EpisodicMemory:
    """Stores and recalls teacher interaction episodes with semantic search."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or _DEFAULT_DB
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._embedder = get_embedder()
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    teacher_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_episodes_teacher ON episodes(teacher_id)")

    def store(self, teacher_id: str, text: str, metadata: dict[str, Any] | None = None) -> None:
        """Store an episode with its embedding."""
        embedding = self._embedder.embed(text)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT INTO episodes (teacher_id, text, embedding, metadata, created_at) VALUES (?, ?, ?, ?, ?)",
                (teacher_id, text, json.dumps(embedding), json.dumps(metadata or {}), datetime.now().isoformat()),
            )

    def recall(self, teacher_id: str, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """Recall the most relevant episodes for a query using semantic similarity."""
        query_embedding = self._embedder.embed(query)

        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, text, embedding, metadata, created_at FROM episodes WHERE teacher_id = ?",
                (teacher_id,),
            ).fetchall()

        if not rows:
            return []

        scored = []
        for row in rows:
            stored_embedding = json.loads(row["embedding"])
            sim = self._embedder.cosine_similarity(query_embedding, stored_embedding)
            scored.append({
                "text": row["text"],
                "metadata": json.loads(row["metadata"]),
                "created_at": row["created_at"],
                "similarity": sim,
            })

        scored.sort(key=lambda x: x["similarity"], reverse=True)
        return scored[:top_k]
```

- [ ] **Step 4: Run test — confirm pass**
- [ ] **Step 5: Commit**

```bash
git add clawed/agent_core/memory/episodes.py tests/test_memory.py
git commit -m "feat(memory): add Layer 3 — episodic memory with semantic search"
```

---

### Task 5: Memory Context Loader + Agent Integration

**Files:**
- Create: `clawed/agent_core/memory/loader.py`
- Modify: `clawed/agent_core/core.py` — replace `_load_improvement_context()` with memory loader
- Modify: `clawed/agent_core/prompt.py` — accept richer context
- Test: Append to `tests/test_memory.py`

- [ ] **Step 1: Write failing test**

```python
class TestMemoryLoader:
    def test_load_full_context(self, tmp_path, monkeypatch):
        monkeypatch.setenv("EDUAGENT_DATA_DIR", str(tmp_path))
        from clawed.agent_core.memory.loader import load_memory_context
        ctx = load_memory_context("test-teacher", "What should I teach tomorrow?")
        assert isinstance(ctx, dict)
        assert "identity_summary" in ctx
        assert "curriculum_summary" in ctx
        assert "relevant_episodes" in ctx
        assert "improvement_context" in ctx

    def test_load_memory_context_graceful_on_empty(self, tmp_path, monkeypatch):
        monkeypatch.setenv("EDUAGENT_DATA_DIR", str(tmp_path))
        from clawed.agent_core.memory.loader import load_memory_context
        ctx = load_memory_context("nonexistent", "hello")
        # Should return empty strings, not crash
        assert ctx["identity_summary"] == "" or isinstance(ctx["identity_summary"], str)
```

- [ ] **Step 2: Run test — confirm fail**
- [ ] **Step 3: Write implementation**

```python
# clawed/agent_core/memory/loader.py
"""Memory context loader — assembles all 3 layers for the agent's system prompt."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def load_memory_context(teacher_id: str, current_message: str) -> dict[str, Any]:
    """Load all memory layers and assemble context for the system prompt.

    Returns a dict with keys: identity_summary, curriculum_summary,
    relevant_episodes, improvement_context.
    """
    # Layer 1: Identity
    identity_summary = ""
    try:
        from clawed.agent_core.memory.identity import load_identity, load_identity_from_db
        file_identity = load_identity()
        db_identity = load_identity_from_db(teacher_id)
        name = db_identity.get("name") or file_identity.get("name", "")
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
        from clawed.agent_core.memory.curriculum import load_curriculum_state, summarize_curriculum_state
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
                f"- {ep['text']}" for ep in episodes if ep.get("similarity", 0) > 0.1
            )
    except Exception as e:
        logger.debug("Episodic recall failed: %s", e)

    # Existing improvement context (from memory_engine.py — kept for backward compat)
    improvement_context = ""
    try:
        from clawed.memory_engine import build_improvement_context
        improvement_context = build_improvement_context()
    except Exception as e:
        logger.debug("Improvement context load failed: %s", e)

    return {
        "identity_summary": identity_summary,
        "curriculum_summary": curriculum_summary,
        "relevant_episodes": relevant_episodes,
        "improvement_context": improvement_context,
    }
```

- [ ] **Step 4: Run test — confirm pass**
- [ ] **Step 5: Update `core.py` to use memory loader**

In `clawed/agent_core/core.py`, replace `_load_improvement_context()` call in `_agent_loop()` with:
```python
from clawed.agent_core.memory.loader import load_memory_context
memory_ctx = load_memory_context(teacher_id, message)
```

Update the `build_system_prompt()` call to pass the richer context.

- [ ] **Step 6: Update `prompt.py` to accept richer context**

Add `curriculum_summary` and `relevant_episodes` parameters to `build_system_prompt()`. Add corresponding sections:
```python
if curriculum_summary:
    sections.append(f"\n## Curriculum Progress\n{curriculum_summary}")
if relevant_episodes:
    sections.append(f"\n## Relevant Past Interactions\n{relevant_episodes}")
```

- [ ] **Step 7: Store episodes after each interaction**

In `core.py` `_agent_loop()`, after the agent responds, store the exchange:
```python
try:
    from clawed.agent_core.memory.episodes import EpisodicMemory
    mem = EpisodicMemory()
    mem.store(teacher_id, f"Teacher: {message}\nClaw-ED: {result.text[:500]}")
except Exception:
    pass
```

- [ ] **Step 8: Run all memory tests + full suite**
- [ ] **Step 9: Commit**

```bash
git add clawed/agent_core/memory/loader.py clawed/agent_core/core.py clawed/agent_core/prompt.py tests/test_memory.py
git commit -m "feat(memory): integrate 3-layer memory into agent core"
```

---

## Phase B: Google Drive Integration

### Task 6: Drive Auth — OAuth Flow + Token Persistence

**Files:**
- Create: `clawed/agent_core/drive/__init__.py`
- Create: `clawed/agent_core/drive/auth.py`
- Modify: `clawed/models.py` — add Drive config fields
- Test: `tests/test_drive.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_drive.py
"""Tests for Google Drive integration."""
import pytest


class TestDriveAuth:
    def test_token_save_and_load(self, tmp_path):
        from clawed.agent_core.drive.auth import save_token, load_token
        token_data = {"access_token": "ya29.abc", "refresh_token": "1//xyz", "expiry": "2026-04-01T00:00:00"}
        save_token(token_data, token_path=tmp_path / "drive_token.json")
        loaded = load_token(token_path=tmp_path / "drive_token.json")
        assert loaded["access_token"] == "ya29.abc"

    def test_load_token_missing(self, tmp_path):
        from clawed.agent_core.drive.auth import load_token
        result = load_token(token_path=tmp_path / "nonexistent.json")
        assert result is None

    def test_is_authenticated(self, tmp_path):
        from clawed.agent_core.drive.auth import is_authenticated, save_token
        assert not is_authenticated(token_path=tmp_path / "nope.json")
        save_token({"access_token": "test", "refresh_token": "test"}, token_path=tmp_path / "token.json")
        assert is_authenticated(token_path=tmp_path / "token.json")
```

- [ ] **Step 2: Run test — confirm fail**
- [ ] **Step 3: Add Drive config to models.py**

Add to `AppConfig`:
```python
drive_root_folder: str = ""  # Google Drive folder ID for uploads
drive_token_path: str = ""   # Path to OAuth token (default: ~/.eduagent/drive_token.json)
```

- [ ] **Step 4: Write implementation**

```python
# clawed/agent_core/drive/__init__.py
"""Google Drive integration for Claw-ED."""

# clawed/agent_core/drive/auth.py
"""Google OAuth flow + token persistence for Drive access."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_TOKEN_PATH = Path.home() / ".eduagent" / "drive_token.json"

# OAuth scopes needed for Drive file management
SCOPES = [
    "https://www.googleapis.com/auth/drive.file",  # files created by app only
]


def save_token(token_data: dict[str, Any], token_path: Path | None = None) -> None:
    """Persist OAuth token to disk."""
    path = token_path or _DEFAULT_TOKEN_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(token_data, indent=2), encoding="utf-8")
    # Restrict permissions
    try:
        path.chmod(0o600)
    except OSError:
        pass


def load_token(token_path: Path | None = None) -> dict[str, Any] | None:
    """Load OAuth token from disk. Returns None if not found."""
    path = token_path or _DEFAULT_TOKEN_PATH
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load Drive token: %s", e)
        return None


def is_authenticated(token_path: Path | None = None) -> bool:
    """Check if a valid Drive token exists."""
    return load_token(token_path) is not None


async def authenticate_interactive(token_path: Path | None = None) -> dict[str, Any]:
    """Run the OAuth flow interactively — opens browser for consent.

    Requires: pip install 'clawed[google]'
    """
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        raise ImportError(
            "Google Drive support requires: pip install 'clawed[google]'"
        )

    # For development/personal use, use a local OAuth client
    # Teachers will authenticate their own Google account
    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": "PLACEHOLDER_CLIENT_ID",
                "client_secret": "PLACEHOLDER_CLIENT_SECRET",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        },
        scopes=SCOPES,
    )
    creds = flow.run_local_server(port=0)
    token_data = {
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
    }
    save_token(token_data, token_path)
    return token_data
```

- [ ] **Step 5: Run test — confirm pass**
- [ ] **Step 6: Commit**

```bash
git add clawed/agent_core/drive/ clawed/models.py tests/test_drive.py
git commit -m "feat(drive): add OAuth token persistence and auth helpers"
```

---

### Task 7: Drive Client with Rate Limiting

**Files:**
- Create: `clawed/agent_core/drive/client.py`
- Test: Append to `tests/test_drive.py`

- [ ] **Step 1: Write failing test**

```python
class TestDriveClient:
    def test_rate_limiter_allows_initial(self):
        from clawed.agent_core.drive.client import RateLimiter
        rl = RateLimiter(max_per_hour=100)
        assert rl.allow()

    def test_rate_limiter_blocks_excess(self):
        from clawed.agent_core.drive.client import RateLimiter
        rl = RateLimiter(max_per_hour=2)
        assert rl.allow()
        assert rl.allow()
        assert not rl.allow()  # third should be blocked

    @pytest.mark.asyncio
    async def test_client_not_authenticated(self, tmp_path):
        from clawed.agent_core.drive.client import DriveClient
        client = DriveClient(token_path=tmp_path / "nope.json")
        with pytest.raises(RuntimeError, match="not authenticated"):
            await client.list_files()
```

- [ ] **Step 2: Run test — confirm fail**
- [ ] **Step 3: Write implementation**

```python
# clawed/agent_core/drive/client.py
"""Google Drive API client with rate limiting."""
from __future__ import annotations

import logging
import time
from collections import deque
from pathlib import Path
from typing import Any

from clawed.agent_core.drive.auth import is_authenticated, load_token

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple sliding-window rate limiter."""

    def __init__(self, max_per_hour: int = 60) -> None:
        self._max = max_per_hour
        self._timestamps: deque[float] = deque()

    def allow(self) -> bool:
        now = time.monotonic()
        # Remove timestamps older than 1 hour
        while self._timestamps and now - self._timestamps[0] > 3600:
            self._timestamps.popleft()
        if len(self._timestamps) >= self._max:
            return False
        self._timestamps.append(now)
        return True


class DriveClient:
    """Google Drive file operations with rate limiting."""

    def __init__(self, token_path: Path | None = None, max_per_hour: int = 60) -> None:
        self._token_path = token_path
        self._limiter = RateLimiter(max_per_hour=max_per_hour)

    def _get_service(self):
        if not is_authenticated(self._token_path):
            raise RuntimeError("Google Drive not authenticated. Run: clawed drive auth")
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
        except ImportError:
            raise ImportError("Google Drive support requires: pip install 'clawed[google]'")

        token_data = load_token(self._token_path)
        creds = Credentials(
            token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
        )
        return build("drive", "v3", credentials=creds)

    def _check_rate(self) -> None:
        if not self._limiter.allow():
            raise RuntimeError("Drive rate limit exceeded. Try again later.")

    async def list_files(self, folder_id: str = "root", max_results: int = 20) -> list[dict[str, Any]]:
        self._check_rate()
        service = self._get_service()
        query = f"'{folder_id}' in parents and trashed=false"
        results = service.files().list(
            q=query, pageSize=max_results,
            fields="files(id, name, mimeType, modifiedTime)",
        ).execute()
        return results.get("files", [])

    async def upload_file(self, file_path: Path, folder_id: str = "root",
                          file_name: str | None = None) -> dict[str, Any]:
        self._check_rate()
        service = self._get_service()
        from googleapiclient.http import MediaFileUpload

        name = file_name or file_path.name
        file_metadata = {"name": name, "parents": [folder_id]}
        media = MediaFileUpload(str(file_path))
        result = service.files().create(
            body=file_metadata, media_body=media, fields="id, name, webViewLink",
        ).execute()
        return result

    async def create_folder(self, name: str, parent_id: str = "root") -> dict[str, Any]:
        self._check_rate()
        service = self._get_service()
        file_metadata = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        }
        result = service.files().create(body=file_metadata, fields="id, name").execute()
        return result
```

- [ ] **Step 4: Run test — confirm pass**
- [ ] **Step 5: Commit**

```bash
git add clawed/agent_core/drive/client.py tests/test_drive.py
git commit -m "feat(drive): add Drive client with rate limiting"
```

---

### Task 8: Drive Tools for Agent

**Files:**
- Create: `clawed/agent_core/tools/drive_upload.py`
- Create: `clawed/agent_core/tools/drive_list.py`
- Create: `clawed/agent_core/tools/drive_organize.py`
- Test: Append to `tests/test_drive.py`

- [ ] **Step 1: Write failing tests** for all three tools (schema validation + mocked execute)

- [ ] **Step 2: Write implementations** — each tool is a thin wrapper around `DriveClient` methods. `drive_upload` uses the `request_approval` pattern from v0.6 to confirm before uploading.

- [ ] **Step 3: Run tests — confirm pass**

- [ ] **Step 4: Verify auto-discovery** finds the new tools (should go from 14 → 17)

```python
from clawed.gateway import Gateway
from clawed.models import AppConfig
gw = Gateway(config=AppConfig(agent_gateway=True))
assert len(gw._registry.tool_names()) == 17
assert "drive_upload" in gw._registry.tool_names()
```

- [ ] **Step 5: Commit**

```bash
git add clawed/agent_core/tools/drive_*.py tests/test_drive.py
git commit -m "feat(drive): add drive_upload, drive_list, drive_organize tools"
```

---

## Phase C: Housekeeping

### Task 9: Version Bump + Tests + Full Suite

- [ ] **Step 1: Bump version** — `pyproject.toml` and `clawed/__init__.py` to `0.7.0`
- [ ] **Step 2: Update version assertions** in `tests/test_basic.py` and `tests/test_v013_features.py`
- [ ] **Step 3: Run full test suite** — `.venv/bin/python3 -m pytest tests/ -q --tb=short`
- [ ] **Step 4: Lint** — `.venv/bin/ruff check clawed/agent_core/memory/ clawed/agent_core/drive/`
- [ ] **Step 5: Commit**

```bash
git commit -m "release: bump to v0.7.0 — cognitive memory + Google Drive"
```

---

### Task 10: README + CHANGELOG + Docs Update

- [ ] **Step 1: Update CHANGELOG.md** — add v0.7.0 entry with memory and Drive additions
- [ ] **Step 2: Update README.md** — update roadmap table (v0.7.0 is now current), move Drive and memory from "coming next" to features list, update tool count (14 → 17)
- [ ] **Step 3: Update ARCHITECTURE.md** — add memory system to the architecture diagram, add Drive as a tool category
- [ ] **Step 4: Update AGENT_HANDOFF.md** — update version, test count, new capabilities
- [ ] **Step 5: Update landing page** if it mentions version or capabilities
- [ ] **Step 6: Commit**

```bash
git add README.md CHANGELOG.md docs/
git commit -m "docs: update README, CHANGELOG, architecture for v0.7.0"
```

---

### Task 11: Push

- [ ] **Step 1: Final full suite** — `.venv/bin/python3 -m pytest tests/ -q --tb=short`
- [ ] **Step 2: Push** — `git push`
