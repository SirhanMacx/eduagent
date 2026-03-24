"""Persistent bot state storage backed by SQLite.

Stores Telegram bot conversation states so they survive restarts.
Used by both telegram_bot.py (teacher bot) and student_telegram_bot.py.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class BotStateStore:
    """Read/write ChatState rows to ~/.eduagent/bot_state.db."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = db_path or (Path.home() / ".eduagent" / "bot_state.db")
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._ensure_table()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _ensure_table(self) -> None:
        conn = self._get_conn()
        conn.execute(
            """CREATE TABLE IF NOT EXISTS chat_states (
                chat_id INTEGER PRIMARY KEY,
                state TEXT NOT NULL DEFAULT 'idle',
                pending_topic TEXT NOT NULL DEFAULT '',
                last_lesson_id TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            )"""
        )
        conn.commit()

    def get(self, chat_id: int) -> Optional[dict]:
        """Load a chat state row, or None if not found."""
        row = self._get_conn().execute(
            "SELECT state, pending_topic, last_lesson_id, updated_at "
            "FROM chat_states WHERE chat_id = ?",
            (chat_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "state": row["state"],
            "pending_topic": row["pending_topic"],
            "last_lesson_id": row["last_lesson_id"],
            "updated_at": row["updated_at"],
        }

    def save(self, chat_id: int, *, state: str, pending_topic: str = "", last_lesson_id: str = "") -> None:
        """Upsert a chat state row."""
        now = datetime.now(timezone.utc).isoformat()
        self._get_conn().execute(
            """INSERT INTO chat_states (chat_id, state, pending_topic, last_lesson_id, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                state = excluded.state,
                pending_topic = excluded.pending_topic,
                last_lesson_id = excluded.last_lesson_id,
                updated_at = excluded.updated_at""",
            (chat_id, state, pending_topic, last_lesson_id, now),
        )
        self._get_conn().commit()

    def delete(self, chat_id: int) -> None:
        """Remove a chat state row."""
        self._get_conn().execute(
            "DELETE FROM chat_states WHERE chat_id = ?", (chat_id,)
        )
        self._get_conn().commit()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None


class StudentBotStateStore:
    """Read/write student session rows to ~/.eduagent/bot_state.db."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = db_path or (Path.home() / ".eduagent" / "bot_state.db")
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._ensure_table()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _ensure_table(self) -> None:
        conn = self._get_conn()
        conn.execute(
            """CREATE TABLE IF NOT EXISTS student_bot_sessions (
                chat_id INTEGER PRIMARY KEY,
                class_code TEXT NOT NULL DEFAULT '',
                student_id TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            )"""
        )
        conn.commit()

    def get(self, chat_id: int) -> Optional[dict[str, str]]:
        """Load a student session row, or None if not found."""
        row = self._get_conn().execute(
            "SELECT class_code, student_id, updated_at "
            "FROM student_bot_sessions WHERE chat_id = ?",
            (chat_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "class_code": row["class_code"],
            "student_id": row["student_id"],
            "updated_at": row["updated_at"],
        }

    def save(self, chat_id: int, *, class_code: str = "", student_id: str = "") -> None:
        """Upsert a student session row."""
        now = datetime.now(timezone.utc).isoformat()
        self._get_conn().execute(
            """INSERT INTO student_bot_sessions (chat_id, class_code, student_id, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                class_code = excluded.class_code,
                student_id = excluded.student_id,
                updated_at = excluded.updated_at""",
            (chat_id, class_code, student_id, now),
        )
        self._get_conn().commit()

    def delete(self, chat_id: int) -> None:
        """Remove a student session row."""
        self._get_conn().execute(
            "DELETE FROM student_bot_sessions WHERE chat_id = ?", (chat_id,)
        )
        self._get_conn().commit()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
