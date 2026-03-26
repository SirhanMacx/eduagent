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
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_episodes_teacher ON episodes(teacher_id)"
            )

    def store(
        self,
        teacher_id: str,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Store an episode with its embedding."""
        embedding = self._embedder.embed(text)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT INTO episodes (teacher_id, text, embedding, metadata, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    teacher_id,
                    text,
                    json.dumps(embedding),
                    json.dumps(metadata or {}),
                    datetime.now().isoformat(),
                ),
            )

    def recall(
        self,
        teacher_id: str,
        query: str,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Recall the most relevant episodes using semantic similarity."""
        query_embedding = self._embedder.embed(query)

        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT text, embedding, metadata, created_at "
                "FROM episodes WHERE teacher_id = ? "
                "AND created_at > date('now', '-90 days') "
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
                "text": row["text"],
                "metadata": json.loads(row["metadata"]),
                "created_at": row["created_at"],
                "similarity": sim,
            })

        scored.sort(key=lambda x: x["similarity"], reverse=True)
        return scored[:top_k]
