"""Tests for the EDUagent FastAPI web platform."""

import json

import pytest
from fastapi.testclient import TestClient

from eduagent.api.server import create_app
from eduagent.database import Database


@pytest.fixture
def db(tmp_path):
    """Create a temporary database for testing."""
    db = Database(tmp_path / "test.db")
    yield db
    db.close()


@pytest.fixture
def app(db):
    """Create a test app with the temp database injected."""
    import eduagent.api.server as srv

    old_db = srv._db
    srv._db = db
    test_app = create_app()
    yield test_app
    srv._db = old_db


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


# ── Database tests ────────────────────────────────────────────────────


class TestDatabase:
    def test_upsert_and_get_teacher(self, db):
        tid = db.upsert_teacher("Ms. Smith", '{"name": "Ms. Smith"}')
        assert len(tid) == 12
        teacher = db.get_teacher(tid)
        assert teacher is not None
        assert teacher["name"] == "Ms. Smith"
        assert json.loads(teacher["persona_json"])["name"] == "Ms. Smith"

    def test_get_default_teacher(self, db):
        assert db.get_default_teacher() is None
        db.upsert_teacher("Teacher One", '{"name": "One"}')
        db.upsert_teacher("Teacher Two", '{"name": "Two"}')
        default = db.get_default_teacher()
        assert default is not None

    def test_insert_and_get_unit(self, db):
        tid = db.upsert_teacher("T", '{}')
        uid = db.insert_unit(tid, "Test Unit", "Science", "8", "Cells", '{"title": "Test Unit"}')
        assert len(uid) == 12
        unit = db.get_unit(uid)
        assert unit["title"] == "Test Unit"
        assert unit["subject"] == "Science"

    def test_list_units(self, db):
        tid = db.upsert_teacher("T", '{}')
        db.insert_unit(tid, "Unit A", "Math", "5", "Fractions", '{}')
        db.insert_unit(tid, "Unit B", "Science", "8", "Cells", '{}')
        units = db.list_units()
        assert len(units) == 2

    def test_insert_and_get_lesson(self, db):
        tid = db.upsert_teacher("T", '{}')
        uid = db.insert_unit(tid, "U", "S", "8", "T", '{}')
        lid = db.insert_lesson(uid, 1, "Lesson 1", '{"title": "Lesson 1"}')
        lesson = db.get_lesson(lid)
        assert lesson is not None
        assert lesson["title"] == "Lesson 1"
        assert lesson["share_token"] is not None

    def test_lesson_share_token(self, db):
        tid = db.upsert_teacher("T", '{}')
        uid = db.insert_unit(tid, "U", "S", "8", "T", '{}')
        lid = db.insert_lesson(uid, 1, "L1", '{}')
        lesson = db.get_lesson(lid)
        by_token = db.get_lesson_by_token(lesson["share_token"])
        assert by_token is not None
        assert by_token["id"] == lid

    def test_update_lesson_json(self, db):
        tid = db.upsert_teacher("T", '{}')
        uid = db.insert_unit(tid, "U", "S", "8", "T", '{}')
        lid = db.insert_lesson(uid, 1, "L1", '{"v": 1}')
        db.update_lesson_json(lid, '{"v": 2}')
        lesson = db.get_lesson(lid)
        assert json.loads(lesson["lesson_json"])["v"] == 2
        assert lesson["edit_count"] == 1

    def test_feedback_crud(self, db):
        tid = db.upsert_teacher("T", '{}')
        uid = db.insert_unit(tid, "U", "S", "8", "T", '{}')
        lid = db.insert_lesson(uid, 1, "L1", '{}')
        fid = db.insert_feedback(lid, 4, "Great!", '["objective"]')
        assert len(fid) == 12
        feedback = db.get_feedback_for_lesson(lid)
        assert len(feedback) == 1
        assert feedback[0]["rating"] == 4
        assert feedback[0]["notes"] == "Great!"

    def test_prompt_versions(self, db):
        pid = db.insert_prompt_version("lesson_plan", 1, "version 1 text")
        assert len(pid) == 12
        active = db.get_active_prompt("lesson_plan")
        assert active is not None
        assert active["version"] == 1

    def test_promote_prompt(self, db):
        db.insert_prompt_version("lesson_plan", 1, "v1")
        p2 = db.insert_prompt_version("lesson_plan", 2, "v2")
        db.promote_prompt(p2, "lesson_plan")
        active = db.get_active_prompt("lesson_plan")
        assert active["id"] == p2

    def test_chat_messages(self, db):
        tid = db.upsert_teacher("T", '{}')
        uid = db.insert_unit(tid, "U", "S", "8", "T", '{}')
        lid = db.insert_lesson(uid, 1, "L1", '{}')
        db.insert_chat_message(lid, "user", "What is photosynthesis?")
        db.insert_chat_message(lid, "assistant", "It's a process...")
        history = db.get_chat_history(lid)
        assert len(history) == 2
        assert db.count_chat_sessions() == 1

    def test_stats(self, db):
        stats = db.get_stats()
        assert stats["units"] == 0
        assert stats["lessons"] == 0
        assert stats["chats"] == 0


# ── Page routes ───────────────────────────────────────────────────────


class TestPageRoutes:
    def test_index_page(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "EDUagent" in resp.text

    def test_dashboard_page(self, client):
        resp = client.get("/dashboard")
        assert resp.status_code == 200
        assert "Dashboard" in resp.text

    def test_generate_page(self, client):
        resp = client.get("/generate")
        assert resp.status_code == 200
        assert "Generate" in resp.text

    def test_lesson_page_404(self, client):
        resp = client.get("/lesson/nonexistent")
        assert resp.status_code == 404
        assert "not found" in resp.text.lower()

    def test_share_page_404(self, client):
        resp = client.get("/share/badtoken")
        assert resp.status_code == 404
        assert "not found" in resp.text.lower()


# ── API routes ────────────────────────────────────────────────────────


class TestAPIRoutes:
    def test_get_persona_no_teacher(self, client):
        resp = client.get("/api/persona")
        assert resp.status_code == 404

    def test_get_persona_with_teacher(self, client, db):
        db.upsert_teacher("Ms. T", '{"name": "Ms. T", "teaching_style": "direct_instruction"}')
        resp = client.get("/api/persona")
        assert resp.status_code == 200
        data = resp.json()
        assert data["persona"]["name"] == "Ms. T"

    def test_list_units_empty(self, client):
        resp = client.get("/api/units")
        assert resp.status_code == 200
        assert resp.json()["units"] == []

    def test_list_units_with_data(self, client, db):
        tid = db.upsert_teacher("T", '{}')
        db.insert_unit(tid, "Unit A", "Math", "5", "Fractions", '{}')
        resp = client.get("/api/units")
        assert resp.status_code == 200
        assert len(resp.json()["units"]) == 1

    def test_list_lessons_empty(self, client, db):
        tid = db.upsert_teacher("T", '{}')
        uid = db.insert_unit(tid, "U", "S", "8", "T", '{}')
        resp = client.get(f"/api/lessons/{uid}")
        assert resp.status_code == 200
        assert resp.json()["lessons"] == []

    def test_feedback_invalid_rating(self, client, db):
        tid = db.upsert_teacher("T", '{}')
        uid = db.insert_unit(tid, "U", "S", "8", "T", '{}')
        lid = db.insert_lesson(uid, 1, "L1", '{}')
        resp = client.post("/api/feedback", json={"lesson_id": lid, "rating": 0})
        assert resp.status_code == 400

    def test_feedback_lesson_not_found(self, client):
        resp = client.post("/api/feedback", json={"lesson_id": "fake", "rating": 4})
        assert resp.status_code == 404

    def test_feedback_success(self, client, db):
        tid = db.upsert_teacher("T", '{}')
        uid = db.insert_unit(tid, "U", "S", "8", "T", '{}')
        lid = db.insert_lesson(uid, 1, "L1", '{}')
        resp = client.post("/api/feedback", json={"lesson_id": lid, "rating": 4, "notes": "Good!"})
        assert resp.status_code == 200
        assert "feedback_id" in resp.json()

    def test_get_feedback(self, client, db):
        tid = db.upsert_teacher("T", '{}')
        uid = db.insert_unit(tid, "U", "S", "8", "T", '{}')
        lid = db.insert_lesson(uid, 1, "L1", '{}')
        db.insert_feedback(lid, 5, "Awesome")
        resp = client.get(f"/api/feedback/{lid}")
        assert resp.status_code == 200
        assert len(resp.json()["feedback"]) == 1

    def test_feedback_analysis(self, client, db):
        resp = client.get("/api/feedback-analysis")
        assert resp.status_code == 200
        assert "analysis" in resp.json()

    def test_export_lesson_not_found(self, client):
        resp = client.get("/api/export/fake")
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data

    def test_export_lesson_markdown(self, client, db):
        from eduagent.models import DailyLesson

        tid = db.upsert_teacher("T", '{}')
        uid = db.insert_unit(tid, "U", "S", "8", "T", '{}')
        lesson = DailyLesson(title="Test", lesson_number=1, objective="Learn things")
        lid = db.insert_lesson(uid, 1, "Test", lesson.model_dump_json())
        resp = client.get(f"/api/export/{lid}?fmt=markdown")
        assert resp.status_code == 200
        assert "Test" in resp.text

    def test_export_unsupported_format(self, client, db):
        from eduagent.models import DailyLesson

        tid = db.upsert_teacher("T", '{}')
        uid = db.insert_unit(tid, "U", "S", "8", "T", '{}')
        lesson = DailyLesson(title="Test", lesson_number=1, objective="Learn things")
        lid = db.insert_lesson(uid, 1, "Test", lesson.model_dump_json())
        resp = client.get(f"/api/export/{lid}?fmt=xml")
        data = resp.json()
        assert "error" in data

    def test_share_api_not_found(self, client):
        resp = client.get("/api/share/badtoken")
        data = resp.json()
        assert "error" in data

    def test_share_api_success(self, client, db):
        tid = db.upsert_teacher("T", '{}')
        uid = db.insert_unit(tid, "U", "S", "8", "T", '{}')
        lid = db.insert_lesson(uid, 1, "L1", '{"title": "Hello"}')
        lesson = db.get_lesson(lid)
        token = lesson["share_token"]
        resp = client.get(f"/api/share/{token}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "L1"

    def test_unit_generation_no_persona(self, client):
        resp = client.post("/api/unit", json={"topic": "Cells"})
        assert resp.status_code == 400

    def test_lesson_generation_no_persona(self, client):
        resp = client.post("/api/lesson", json={"unit_id": "fake", "lesson_number": 1})
        assert resp.status_code == 400

    def test_materials_generation_no_persona(self, client):
        resp = client.post("/api/materials", json={"lesson_id": "fake"})
        assert resp.status_code == 400

    def test_chat_lesson_not_found(self, client):
        resp = client.post("/api/chat", json={"lesson_id": "fake", "question": "What?"})
        assert resp.status_code == 404

    def test_chat_no_persona(self, client, db):
        tid = db.upsert_teacher("T", None)  # No persona JSON
        uid = db.insert_unit(tid, "U", "S", "8", "T", '{}')
        lid = db.insert_lesson(uid, 1, "L1", '{}')
        resp = client.post("/api/chat", json={"lesson_id": lid, "question": "What?"})
        assert resp.status_code == 400


# ── Lesson page with data ────────────────────────────────────────────


class TestLessonPage:
    def test_lesson_page_renders(self, client, db):
        from eduagent.models import DailyLesson

        tid = db.upsert_teacher("T", '{"name": "T"}')
        uid = db.insert_unit(tid, "U", "Science", "8", "Cells", '{}')
        lesson = DailyLesson(
            title="Cell Structure",
            lesson_number=1,
            objective="Learn about cells",
            do_now="Draw a cell",
            direct_instruction="Cells are the basic unit of life.",
            guided_practice="Label the cell diagram.",
            independent_work="Complete the worksheet.",
        )
        lid = db.insert_lesson(uid, 1, "Cell Structure", lesson.model_dump_json())
        resp = client.get(f"/lesson/{lid}")
        assert resp.status_code == 200
        assert "Cell Structure" in resp.text
        assert "Learn about cells" in resp.text

    def test_share_page_renders(self, client, db):
        from eduagent.models import DailyLesson

        tid = db.upsert_teacher("T", '{"name": "T"}')
        uid = db.insert_unit(tid, "U", "Science", "8", "Cells", '{}')
        lesson = DailyLesson(title="Shared Lesson", lesson_number=1, objective="Test")
        lid = db.insert_lesson(uid, 1, "Shared Lesson", lesson.model_dump_json())
        row = db.get_lesson(lid)
        resp = client.get(f"/share/{row['share_token']}")
        assert resp.status_code == 200
        assert "Shared Lesson" in resp.text
