"""Tests for bot state persistence (SQLite-backed)."""

from __future__ import annotations

import pytest

from eduagent.bot_state import BotStateStore, StudentBotStateStore


class TestBotStateStore:
    @pytest.fixture
    def store(self, tmp_path):
        db_path = tmp_path / "test_bot_state.db"
        s = BotStateStore(db_path=db_path)
        yield s
        s.close()

    def test_get_returns_none_for_missing(self, store):
        assert store.get(99999) is None

    def test_save_and_get(self, store):
        store.save(123, state="generating", pending_topic="photosynthesis", last_lesson_id="L1")
        row = store.get(123)
        assert row is not None
        assert row["state"] == "generating"
        assert row["pending_topic"] == "photosynthesis"
        assert row["last_lesson_id"] == "L1"
        assert row["updated_at"]  # non-empty timestamp

    def test_save_upsert_updates_existing(self, store):
        store.save(123, state="idle")
        store.save(123, state="done", last_lesson_id="L5")
        row = store.get(123)
        assert row["state"] == "done"
        assert row["last_lesson_id"] == "L5"

    def test_delete(self, store):
        store.save(456, state="idle")
        assert store.get(456) is not None
        store.delete(456)
        assert store.get(456) is None

    def test_delete_nonexistent_is_noop(self, store):
        # Should not raise
        store.delete(99999)

    def test_multiple_chat_ids(self, store):
        store.save(1, state="idle")
        store.save(2, state="generating")
        store.save(3, state="done")
        assert store.get(1)["state"] == "idle"
        assert store.get(2)["state"] == "generating"
        assert store.get(3)["state"] == "done"

    def test_default_empty_strings(self, store):
        store.save(789, state="idle")
        row = store.get(789)
        assert row["pending_topic"] == ""
        assert row["last_lesson_id"] == ""

    def test_creates_parent_directory(self, tmp_path):
        nested = tmp_path / "nested" / "dir" / "bot_state.db"
        s = BotStateStore(db_path=nested)
        s.save(1, state="idle")
        assert s.get(1) is not None
        s.close()

    def test_survives_reopen(self, tmp_path):
        db_path = tmp_path / "persist.db"
        s1 = BotStateStore(db_path=db_path)
        s1.save(42, state="collecting", pending_topic="WWI causes")
        s1.close()

        s2 = BotStateStore(db_path=db_path)
        row = s2.get(42)
        assert row is not None
        assert row["state"] == "collecting"
        assert row["pending_topic"] == "WWI causes"
        s2.close()


class TestStudentBotStateStore:
    @pytest.fixture
    def store(self, tmp_path):
        db_path = tmp_path / "test_student_state.db"
        s = StudentBotStateStore(db_path=db_path)
        yield s
        s.close()

    def test_get_returns_none_for_missing(self, store):
        assert store.get(99999) is None

    def test_save_and_get(self, store):
        store.save(100, class_code="AB-CDE-3", student_id="stu-001")
        row = store.get(100)
        assert row is not None
        assert row["class_code"] == "AB-CDE-3"
        assert row["student_id"] == "stu-001"

    def test_upsert(self, store):
        store.save(100, class_code="OLD-CODE", student_id="stu-001")
        store.save(100, class_code="NEW-CODE", student_id="stu-001")
        row = store.get(100)
        assert row["class_code"] == "NEW-CODE"

    def test_delete(self, store):
        store.save(200, class_code="XY-ZZZ-1", student_id="stu-002")
        store.delete(200)
        assert store.get(200) is None

    def test_survives_reopen(self, tmp_path):
        db_path = tmp_path / "student_persist.db"
        s1 = StudentBotStateStore(db_path=db_path)
        s1.save(50, class_code="MR-MAC-P3", student_id="stu-050")
        s1.close()

        s2 = StudentBotStateStore(db_path=db_path)
        row = s2.get(50)
        assert row is not None
        assert row["class_code"] == "MR-MAC-P3"
        assert row["student_id"] == "stu-050"
        s2.close()
