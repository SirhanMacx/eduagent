"""Tests for the cognitive memory system."""
from clawed.agent_core.memory.identity import load_identity, load_identity_from_db


class TestIdentityLayer:
    def test_load_identity_no_workspace(self, tmp_path, monkeypatch):
        monkeypatch.setattr("clawed.agent_core.memory.identity.IDENTITY_PATH",
                            tmp_path / "nonexistent" / "identity.md")
        result = load_identity()
        assert isinstance(result, dict)
        assert result.get("name", "") == ""

    def test_load_identity_with_file(self, tmp_path, monkeypatch):
        ws = tmp_path / "workspace"
        ws.mkdir(parents=True)
        identity_file = ws / "identity.md"
        identity_file.write_text("# Ms. Smith\nSubject: Science\nGrade: 8\nStyle: inquiry-based\n")
        monkeypatch.setattr("clawed.agent_core.memory.identity.IDENTITY_PATH", identity_file)
        result = load_identity()
        assert result["name"] == "Ms. Smith"
        assert "inquiry-based" in result["raw"]

    def test_load_identity_from_db_no_teacher(self, tmp_path, monkeypatch):
        monkeypatch.setenv("EDUAGENT_DATA_DIR", str(tmp_path))
        result = load_identity_from_db("nonexistent-teacher")
        assert isinstance(result, dict)
        assert result.get("name", "") == ""


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
            "recent_feedback": [],
        }
        summary = summarize_curriculum_state(state)
        assert "3 units" in summary
        assert "photosynthesis" in summary

    def test_summarize_empty_state(self):
        from clawed.agent_core.memory.curriculum import summarize_curriculum_state
        state = {
            "units_generated": 0, "lessons_generated": 0,
            "recent_topics": [], "standards_covered": [],
            "avg_rating": 0.0, "recent_feedback": [],
        }
        summary = summarize_curriculum_state(state)
        assert summary == ""
