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
from datetime import datetime
from pathlib import Path
from typing import Any

from clawed.agent_core.memory.embeddings import get_embedder

logger = logging.getLogger(__name__)

_DEFAULT_DB = Path.home() / ".eduagent" / "memory" / "curriculum_kb.db"
_CHUNK_SIZE = 500  # ~500 words per chunk
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
        """Split text into overlapping chunks of roughly _CHUNK_SIZE words."""
        words = text.split()
        if not words:
            return []
        chunk_words = _CHUNK_SIZE
        overlap_words = _CHUNK_OVERLAP
        chunks: list[str] = []
        start = 0
        while start < len(words):
            end = start + chunk_words
            chunk = " ".join(words[start:end])
            if chunk.strip():
                chunks.append(chunk.strip())
            start += chunk_words - overlap_words
        return chunks or ([text.strip()] if text.strip() else [])

    def index(
        self,
        teacher_id: str,
        doc_title: str,
        source_path: str,
        full_text: str,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """Chunk, embed, and store a document. Returns number of new chunks added."""
        chunks = self._chunk_text(full_text)
        added = 0
        meta_json = json.dumps(metadata or {})

        with sqlite3.connect(self._db_path) as conn:
            for chunk in chunks:
                chunk_hash = hashlib.sha256(chunk.encode()).hexdigest()[:32]
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
                "LIMIT 2000",
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

        scored = [s for s in scored if s["similarity"] > 0.05]
        logger.debug("KB search '%s': %d chunks scored, %d above threshold", query, len(rows), len(scored))
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
