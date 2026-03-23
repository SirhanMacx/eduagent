"""Waitlist manager — email capture for early access signups."""

from __future__ import annotations

import csv
import sqlite3
import uuid
from pathlib import Path
from typing import Any


def _default_db_path() -> Path:
    return Path("eduagent_data") / "eduagent.db"


def _ensure_dir(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


class WaitlistManager:
    """Manages early access signups."""

    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path) if db_path else _default_db_path()
        _ensure_dir(self.db_path)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._create_table()

    def _create_table(self) -> None:
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS waitlist (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE,
                role TEXT DEFAULT 'teacher',
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def add_signup(self, email: str, role: str = "teacher", notes: str = "") -> None:
        """Add email to waitlist SQLite table."""
        if "@" not in email or "." not in email:
            raise ValueError("Invalid email address.")
        wid = uuid.uuid4().hex[:12]
        self.conn.execute(
            "INSERT OR IGNORE INTO waitlist (id, email, role, notes) VALUES (?,?,?,?)",
            (wid, email, role, notes),
        )
        self.conn.commit()

    def export_csv(self, output_path: Path) -> None:
        """Export waitlist to CSV."""
        rows = self.list_all()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "email", "role", "notes", "created_at"])
            writer.writeheader()
            writer.writerows(rows)

    def count(self) -> int:
        """Return total signup count."""
        row = self.conn.execute("SELECT COUNT(*) as c FROM waitlist").fetchone()
        return row["c"] if row else 0

    def list_all(self) -> list[dict[str, Any]]:
        """Return all signups."""
        rows = self.conn.execute("SELECT * FROM waitlist ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        self.conn.close()
