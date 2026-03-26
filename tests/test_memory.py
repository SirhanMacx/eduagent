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
