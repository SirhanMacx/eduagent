"""SQLite database layer for EDUagent web platform."""

from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path
from typing import Any, Optional


def _default_db_path() -> Path:
    return Path("eduagent_data") / "eduagent.db"


def _ensure_dir(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


class Database:
    """Thin wrapper around SQLite for EDUagent storage."""

    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path) if db_path else _default_db_path()
        _ensure_dir(self.db_path)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._create_tables()

    def _create_tables(self) -> None:
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS teachers (
                id TEXT PRIMARY KEY,
                name TEXT,
                persona_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS units (
                id TEXT PRIMARY KEY,
                teacher_id TEXT,
                title TEXT,
                subject TEXT,
                grade_level TEXT,
                topic TEXT,
                unit_json TEXT,
                rating INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS lessons (
                id TEXT PRIMARY KEY,
                unit_id TEXT,
                lesson_number INTEGER,
                title TEXT,
                lesson_json TEXT,
                materials_json TEXT,
                scores_json TEXT,
                rating INTEGER,
                edit_count INTEGER DEFAULT 0,
                share_token TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY,
                lesson_id TEXT,
                rating INTEGER,
                notes TEXT,
                sections_edited TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS prompt_versions (
                id TEXT PRIMARY KEY,
                prompt_type TEXT,
                version INTEGER,
                prompt_text TEXT,
                avg_rating REAL,
                usage_count INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                lesson_id TEXT,
                role TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self.conn.commit()
        self._migrate()

    def _migrate(self) -> None:
        """Apply any schema migrations for existing databases."""
        # Add scores_json column if it doesn't exist
        try:
            self.conn.execute("SELECT scores_json FROM lessons LIMIT 1")
        except Exception:
            self.conn.execute("ALTER TABLE lessons ADD COLUMN scores_json TEXT")
            self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # ── helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _new_id() -> str:
        return uuid.uuid4().hex[:12]

    @staticmethod
    def _new_token() -> str:
        return uuid.uuid4().hex

    def _fetchone(self, sql: str, params: tuple = ()) -> Optional[dict[str, Any]]:
        row = self.conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    def _fetchall(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    # ── teachers ─────────────────────────────────────────────────────

    def upsert_teacher(self, name: str, persona_json: str, teacher_id: str | None = None) -> str:
        tid = teacher_id or self._new_id()
        self.conn.execute(
            """INSERT INTO teachers (id, name, persona_json) VALUES (?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET name=excluded.name, persona_json=excluded.persona_json""",
            (tid, name, persona_json),
        )
        self.conn.commit()
        return tid

    def get_teacher(self, teacher_id: str) -> Optional[dict[str, Any]]:
        return self._fetchone("SELECT * FROM teachers WHERE id=?", (teacher_id,))

    def get_default_teacher(self) -> Optional[dict[str, Any]]:
        return self._fetchone("SELECT * FROM teachers ORDER BY created_at DESC LIMIT 1")

    # ── units ────────────────────────────────────────────────────────

    def insert_unit(
        self, teacher_id: str, title: str, subject: str, grade_level: str, topic: str, unit_json: str,
    ) -> str:
        uid = self._new_id()
        self.conn.execute(
            "INSERT INTO units (id, teacher_id, title, subject, grade_level, topic, unit_json) VALUES (?,?,?,?,?,?,?)",
            (uid, teacher_id, title, subject, grade_level, topic, unit_json),
        )
        self.conn.commit()
        return uid

    def get_unit(self, unit_id: str) -> Optional[dict[str, Any]]:
        return self._fetchone("SELECT * FROM units WHERE id=?", (unit_id,))

    def list_units(self, teacher_id: str | None = None) -> list[dict[str, Any]]:
        if teacher_id:
            return self._fetchall("SELECT * FROM units WHERE teacher_id=? ORDER BY created_at DESC", (teacher_id,))
        return self._fetchall("SELECT * FROM units ORDER BY created_at DESC")

    def rate_unit(self, unit_id: str, rating: int) -> None:
        self.conn.execute("UPDATE units SET rating=? WHERE id=?", (rating, unit_id))
        self.conn.commit()

    # ── lessons ──────────────────────────────────────────────────────

    def insert_lesson(
        self, unit_id: str, lesson_number: int, title: str, lesson_json: str,
        materials_json: str | None = None,
    ) -> str:
        lid = self._new_id()
        token = self._new_token()
        self.conn.execute(
            "INSERT INTO lessons (id, unit_id, lesson_number, title, lesson_json, materials_json, share_token)"
            " VALUES (?,?,?,?,?,?,?)",
            (lid, unit_id, lesson_number, title, lesson_json, materials_json, token),
        )
        self.conn.commit()
        return lid

    def get_lesson(self, lesson_id: str) -> Optional[dict[str, Any]]:
        return self._fetchone("SELECT * FROM lessons WHERE id=?", (lesson_id,))

    def get_lesson_by_token(self, token: str) -> Optional[dict[str, Any]]:
        return self._fetchone("SELECT * FROM lessons WHERE share_token=?", (token,))

    def list_lessons(self, unit_id: str) -> list[dict[str, Any]]:
        return self._fetchall("SELECT * FROM lessons WHERE unit_id=? ORDER BY lesson_number", (unit_id,))

    def update_lesson_json(self, lesson_id: str, lesson_json: str) -> None:
        self.conn.execute(
            "UPDATE lessons SET lesson_json=?, edit_count=edit_count+1 WHERE id=?",
            (lesson_json, lesson_id),
        )
        self.conn.commit()

    def update_lesson_materials(self, lesson_id: str, materials_json: str) -> None:
        self.conn.execute("UPDATE lessons SET materials_json=? WHERE id=?", (materials_json, lesson_id))
        self.conn.commit()

    def update_lesson_scores(self, lesson_id: str, scores_json: str) -> None:
        self.conn.execute("UPDATE lessons SET scores_json=? WHERE id=?", (scores_json, lesson_id))
        self.conn.commit()

    def rate_lesson(self, lesson_id: str, rating: int) -> None:
        self.conn.execute("UPDATE lessons SET rating=? WHERE id=?", (rating, lesson_id))
        self.conn.commit()

    def count_lessons(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) as c FROM lessons").fetchone()
        return row["c"] if row else 0

    # ── feedback ─────────────────────────────────────────────────────

    def insert_feedback(self, lesson_id: str, rating: int, notes: str = "", sections_edited: str = "[]") -> str:
        fid = self._new_id()
        self.conn.execute(
            "INSERT INTO feedback (id, lesson_id, rating, notes, sections_edited) VALUES (?,?,?,?,?)",
            (fid, lesson_id, rating, notes, sections_edited),
        )
        self.conn.commit()
        return fid

    def get_feedback_for_lesson(self, lesson_id: str) -> list[dict[str, Any]]:
        return self._fetchall("SELECT * FROM feedback WHERE lesson_id=? ORDER BY created_at DESC", (lesson_id,))

    def get_recent_feedback(self, days: int = 7) -> list[dict[str, Any]]:
        return self._fetchall(
            "SELECT * FROM feedback WHERE created_at >= datetime('now', ? || ' days') ORDER BY created_at DESC",
            (f"-{days}",),
        )

    def get_low_rated_lessons(self, max_rating: int = 2, days: int = 7) -> list[dict[str, Any]]:
        return self._fetchall(
            """SELECT l.*, f.rating as feedback_rating, f.notes as feedback_notes
               FROM lessons l JOIN feedback f ON l.id = f.lesson_id
               WHERE f.rating <= ? AND f.created_at >= datetime('now', ? || ' days')
               ORDER BY f.rating ASC""",
            (max_rating, f"-{days}"),
        )

    # ── prompt versions ──────────────────────────────────────────────

    def insert_prompt_version(self, prompt_type: str, version: int, prompt_text: str) -> str:
        pid = self._new_id()
        self.conn.execute(
            "INSERT INTO prompt_versions (id, prompt_type, version, prompt_text) VALUES (?,?,?,?)",
            (pid, prompt_type, version, prompt_text),
        )
        self.conn.commit()
        return pid

    def get_active_prompt(self, prompt_type: str) -> Optional[dict[str, Any]]:
        return self._fetchone(
            "SELECT * FROM prompt_versions WHERE prompt_type=? AND is_active=1 ORDER BY version DESC LIMIT 1",
            (prompt_type,),
        )

    def get_prompt_versions(self, prompt_type: str) -> list[dict[str, Any]]:
        return self._fetchall(
            "SELECT * FROM prompt_versions WHERE prompt_type=? ORDER BY version DESC",
            (prompt_type,),
        )

    def update_prompt_stats(self, prompt_id: str, avg_rating: float, usage_count: int) -> None:
        self.conn.execute(
            "UPDATE prompt_versions SET avg_rating=?, usage_count=? WHERE id=?",
            (avg_rating, usage_count, prompt_id),
        )
        self.conn.commit()

    def promote_prompt(self, prompt_id: str, prompt_type: str) -> None:
        self.conn.execute("UPDATE prompt_versions SET is_active=0 WHERE prompt_type=?", (prompt_type,))
        self.conn.execute("UPDATE prompt_versions SET is_active=1 WHERE id=?", (prompt_id,))
        self.conn.commit()

    # ── chat messages ────────────────────────────────────────────────

    def insert_chat_message(self, lesson_id: str, role: str, content: str) -> str:
        mid = self._new_id()
        self.conn.execute(
            "INSERT INTO chat_messages (id, lesson_id, role, content) VALUES (?,?,?,?)",
            (mid, lesson_id, role, content),
        )
        self.conn.commit()
        return mid

    def get_chat_history(self, lesson_id: str, limit: int = 20) -> list[dict[str, Any]]:
        return self._fetchall(
            "SELECT * FROM chat_messages WHERE lesson_id=? ORDER BY created_at DESC LIMIT ?",
            (lesson_id, limit),
        )

    def count_chat_sessions(self) -> int:
        row = self.conn.execute("SELECT COUNT(DISTINCT lesson_id) as c FROM chat_messages WHERE role='user'").fetchone()
        return row["c"] if row else 0

    # ── stats ────────────────────────────────────────────────────────

    def get_stats(self) -> dict[str, int]:
        units = self.conn.execute("SELECT COUNT(*) as c FROM units").fetchone()["c"]
        lessons = self.conn.execute("SELECT COUNT(*) as c FROM lessons").fetchone()["c"]
        chats = self.count_chat_sessions()
        return {"units": units, "lessons": lessons, "chats": chats}
