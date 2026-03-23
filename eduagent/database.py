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

            CREATE TABLE IF NOT EXISTS onboarding_state (
                teacher_id TEXT PRIMARY KEY,
                step_completed INTEGER DEFAULT 0,
                completed_at TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS schools (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                district TEXT DEFAULT '',
                state TEXT DEFAULT '',
                grade_levels_json TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS school_teachers (
                school_id TEXT NOT NULL,
                teacher_id TEXT NOT NULL,
                role TEXT DEFAULT 'teacher',
                department TEXT DEFAULT '',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (school_id, teacher_id)
            );

            CREATE TABLE IF NOT EXISTS shared_content (
                id TEXT PRIMARY KEY,
                school_id TEXT NOT NULL,
                teacher_id TEXT NOT NULL,
                content_type TEXT NOT NULL,
                content_id TEXT NOT NULL,
                title TEXT NOT NULL,
                subject TEXT DEFAULT '',
                grade_level TEXT DEFAULT '',
                department TEXT DEFAULT '',
                rating INTEGER,
                shared_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS iep_profiles (
                id TEXT PRIMARY KEY,
                teacher_id TEXT NOT NULL,
                student_name TEXT NOT NULL,
                disability_type TEXT DEFAULT '',
                accommodations_json TEXT DEFAULT '[]',
                modifications_json TEXT DEFAULT '[]',
                goals_json TEXT DEFAULT '[]',
                active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

    # ── onboarding ─────────────────────────────────────────────────

    def get_onboarding(self, teacher_id: str) -> Optional[dict[str, Any]]:
        return self._fetchone("SELECT * FROM onboarding_state WHERE teacher_id=?", (teacher_id,))

    def upsert_onboarding(self, teacher_id: str, step_completed: int) -> None:
        if step_completed >= 5:
            self.conn.execute(
                """INSERT INTO onboarding_state (teacher_id, step_completed, completed_at)
                   VALUES (?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(teacher_id) DO UPDATE SET
                       step_completed=excluded.step_completed,
                       completed_at=CURRENT_TIMESTAMP""",
                (teacher_id, step_completed),
            )
        else:
            self.conn.execute(
                """INSERT INTO onboarding_state (teacher_id, step_completed)
                   VALUES (?, ?)
                   ON CONFLICT(teacher_id) DO UPDATE SET step_completed=excluded.step_completed""",
                (teacher_id, step_completed),
            )
        self.conn.commit()

    def is_onboarding_complete(self) -> bool:
        row = self._fetchone("SELECT * FROM onboarding_state WHERE step_completed >= 5 LIMIT 1")
        return row is not None

    def clear_all_generated(self) -> None:
        """Clear all generated content (units, lessons, materials, feedback, chats)."""
        self.conn.executescript("""
            DELETE FROM lessons;
            DELETE FROM units;
            DELETE FROM feedback;
            DELETE FROM chat_messages;
        """)
        self.conn.commit()

    def reset_all(self) -> None:
        """Full reset — clear everything including teachers and onboarding."""
        self.conn.executescript("""
            DELETE FROM lessons;
            DELETE FROM units;
            DELETE FROM feedback;
            DELETE FROM chat_messages;
            DELETE FROM prompt_versions;
            DELETE FROM teachers;
            DELETE FROM onboarding_state;
            DELETE FROM shared_content;
            DELETE FROM school_teachers;
            DELETE FROM schools;
        """)
        self.conn.commit()

    def db_size_mb(self) -> float:
        """Get the database file size in MB."""
        try:
            return self.db_path.stat().st_size / (1024 * 1024)
        except OSError:
            return 0.0

    # ── schools ────────────────────────────────────────────────────────

    def create_school(  # noqa: E501
        self, name: str, district: str = "", state: str = "", grade_levels: list[str] | None = None,
    ) -> str:
        sid = self._new_id()
        import json as _json
        self.conn.execute(
            "INSERT INTO schools (id, name, district, state, grade_levels_json) VALUES (?,?,?,?,?)",
            (sid, name, district, state, _json.dumps(grade_levels or [])),
        )
        self.conn.commit()
        return sid

    def get_school(self, school_id: str) -> Optional[dict[str, Any]]:
        return self._fetchone("SELECT * FROM schools WHERE id=?", (school_id,))

    def list_schools(self) -> list[dict[str, Any]]:
        return self._fetchall("SELECT * FROM schools ORDER BY created_at DESC")

    def add_teacher_to_school(
        self, school_id: str, teacher_id: str, role: str = "teacher", department: str = "",
    ) -> None:
        self.conn.execute(
            """INSERT INTO school_teachers (school_id, teacher_id, role, department) VALUES (?,?,?,?)
               ON CONFLICT(school_id, teacher_id) DO UPDATE SET role=excluded.role, department=excluded.department""",
            (school_id, teacher_id, role, department),
        )
        self.conn.commit()

    def remove_teacher_from_school(self, school_id: str, teacher_id: str) -> None:
        self.conn.execute("DELETE FROM school_teachers WHERE school_id=? AND teacher_id=?", (school_id, teacher_id))
        self.conn.commit()

    def list_school_teachers(self, school_id: str) -> list[dict[str, Any]]:
        return self._fetchall(
            """SELECT st.*, t.name as teacher_name FROM school_teachers st
               LEFT JOIN teachers t ON st.teacher_id = t.id
               WHERE st.school_id=? ORDER BY st.joined_at""",
            (school_id,),
        )

    def get_teacher_school(self, teacher_id: str) -> Optional[dict[str, Any]]:
        row = self._fetchone(
            """SELECT s.*, st.role, st.department FROM schools s
               JOIN school_teachers st ON s.id = st.school_id
               WHERE st.teacher_id=? LIMIT 1""",
            (teacher_id,),
        )
        return row

    # ── shared content ────────────────────────────────────────────────

    def share_content(
        self, school_id: str, teacher_id: str, content_type: str, content_id: str,
        title: str, subject: str = "", grade_level: str = "", department: str = "",
    ) -> str:
        sid = self._new_id()
        self.conn.execute(
            """INSERT INTO shared_content
               (id, school_id, teacher_id, content_type, content_id, title, subject, grade_level, department)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (sid, school_id, teacher_id, content_type, content_id, title, subject, grade_level, department),
        )
        self.conn.commit()
        return sid

    def get_shared_library(self, school_id: str, department: str = "", limit: int = 50) -> list[dict[str, Any]]:
        if department:
            return self._fetchall(
                """SELECT sc.*, t.name as teacher_name FROM shared_content sc
                   LEFT JOIN teachers t ON sc.teacher_id = t.id
                   WHERE sc.school_id=? AND sc.department=?
                   ORDER BY sc.rating DESC NULLS LAST, sc.shared_at DESC LIMIT ?""",
                (school_id, department, limit),
            )
        return self._fetchall(
            """SELECT sc.*, t.name as teacher_name FROM shared_content sc
               LEFT JOIN teachers t ON sc.teacher_id = t.id
               WHERE sc.school_id=?
               ORDER BY sc.rating DESC NULLS LAST, sc.shared_at DESC LIMIT ?""",
            (school_id, limit),
        )

    def rate_shared_content(self, shared_id: str, rating: int) -> None:
        self.conn.execute("UPDATE shared_content SET rating=? WHERE id=?", (rating, shared_id))
        self.conn.commit()

    # ── IEP profiles ────────────────────────────────────────────────

    def upsert_iep_profile(
        self, teacher_id: str, student_name: str, disability_type: str = "",
        accommodations_json: str = "[]", modifications_json: str = "[]",
        goals_json: str = "[]", profile_id: str | None = None,
    ) -> str:
        pid = profile_id or self._new_id()
        self.conn.execute(
            """INSERT INTO iep_profiles (id, teacher_id, student_name, disability_type,
                   accommodations_json, modifications_json, goals_json)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET
                   student_name=excluded.student_name,
                   disability_type=excluded.disability_type,
                   accommodations_json=excluded.accommodations_json,
                   modifications_json=excluded.modifications_json,
                   goals_json=excluded.goals_json,
                   updated_at=CURRENT_TIMESTAMP""",
            (pid, teacher_id, student_name, disability_type, accommodations_json, modifications_json, goals_json),
        )
        self.conn.commit()
        return pid

    def get_iep_profile(self, profile_id: str) -> Optional[dict[str, Any]]:
        return self._fetchone("SELECT * FROM iep_profiles WHERE id=?", (profile_id,))

    def list_iep_profiles(self, teacher_id: str, active_only: bool = True) -> list[dict[str, Any]]:
        if active_only:
            return self._fetchall(
                "SELECT * FROM iep_profiles WHERE teacher_id=? AND active=1 ORDER BY student_name",
                (teacher_id,),
            )
        return self._fetchall(
            "SELECT * FROM iep_profiles WHERE teacher_id=? ORDER BY student_name",
            (teacher_id,),
        )

    def deactivate_iep_profile(self, profile_id: str) -> None:
        self.conn.execute(
            "UPDATE iep_profiles SET active=0, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (profile_id,),
        )
        self.conn.commit()

    def delete_iep_profile(self, profile_id: str) -> None:
        self.conn.execute("DELETE FROM iep_profiles WHERE id=?", (profile_id,))
        self.conn.commit()

    # ── stats ────────────────────────────────────────────────────────

    def get_stats(self) -> dict[str, int]:
        units = self.conn.execute("SELECT COUNT(*) as c FROM units").fetchone()["c"]
        lessons = self.conn.execute("SELECT COUNT(*) as c FROM lessons").fetchone()["c"]
        chats = self.count_chat_sessions()
        return {"units": units, "lessons": lessons, "chats": chats}
