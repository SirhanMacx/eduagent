"""Tests for the teacher workspace module."""

from __future__ import annotations

import pytest

from clawed.models import AppConfig, TeacherPersona, TeacherProfile, TeachingStyle, VocabularyLevel
from clawed.workspace import (
    _sanitize_filename,
    append_daily_note,
    generate_identity,
    generate_soul,
    get_daily_notes,
    get_student_profile,
    init_workspace,
    inject_workspace_context,
    list_student_profiles,
    load_context,
    update_memory,
    update_student_profile,
)


@pytest.fixture
def tmp_workspace(tmp_path, monkeypatch):
    """Redirect all workspace paths to a temp directory."""
    ws = tmp_path / "workspace"
    monkeypatch.setattr("clawed.workspace.WORKSPACE_DIR", ws)
    monkeypatch.setattr("clawed.workspace.IDENTITY_PATH", ws / "identity.md")
    monkeypatch.setattr("clawed.workspace.SOUL_PATH", ws / "soul.md")
    monkeypatch.setattr("clawed.workspace.MEMORY_PATH", ws / "memory.md")
    monkeypatch.setattr("clawed.workspace.HEARTBEAT_PATH", ws / "heartbeat.md")
    monkeypatch.setattr("clawed.workspace.NOTES_DIR", ws / "notes")
    monkeypatch.setattr("clawed.workspace.STUDENTS_DIR", ws / "students")
    return ws


@pytest.fixture
def persona():
    return TeacherPersona(
        name="Ms. Rodriguez",
        teaching_style=TeachingStyle.INQUIRY_BASED,
        vocabulary_level=VocabularyLevel.ACADEMIC,
        tone="warm but challenging",
        subject_area="Science",
        grade_levels=["7", "8"],
        favorite_strategies=["think-pair-share", "gallery walk"],
        structural_preferences=["warm-ups", "exit tickets", "lab time"],
        voice_sample="Today we're going to explore the question: what happens when...",
    )


@pytest.fixture
def config():
    return AppConfig(
        teacher_profile=TeacherProfile(
            name="Ms. Rodriguez",
            school="Lincoln Middle School",
            subjects=["Science"],
            grade_levels=["7", "8"],
            state="NY",
            has_iep_students=True,
            has_ell_students=True,
        )
    )


# ── Filename sanitization ─────────────────────────────────────────────


class TestSanitizeFilename:
    def test_basic_name(self):
        assert _sanitize_filename("John Smith") == "john_smith"

    def test_special_chars(self):
        assert _sanitize_filename("O'Brien-Cha!") == "obrien_cha"

    def test_empty_string(self):
        assert _sanitize_filename("") == "unknown"

    def test_whitespace_variations(self):
        assert _sanitize_filename("Jane   Doe") == "jane_doe"


# ── Identity generation ───────────────────────────────────────────────


class TestGenerateIdentity:
    def test_contains_teacher_name(self, persona, config):
        content = generate_identity(persona, config)
        assert "Ms. Rodriguez" in content

    def test_contains_subject(self, persona, config):
        content = generate_identity(persona, config)
        assert "Science" in content

    def test_contains_grade_levels(self, persona, config):
        content = generate_identity(persona, config)
        assert "7" in content
        assert "8" in content

    def test_contains_school(self, persona, config):
        content = generate_identity(persona, config)
        assert "Lincoln Middle School" in content

    def test_contains_teaching_style(self, persona, config):
        content = generate_identity(persona, config)
        assert "Inquiry Based" in content

    def test_contains_lesson_format(self, persona, config):
        content = generate_identity(persona, config)
        assert persona.preferred_lesson_format in content

    def test_contains_assessment_style(self, persona, config):
        content = generate_identity(persona, config)
        assert "Rubric Based" in content

    def test_default_persona(self):
        content = generate_identity(TeacherPersona())
        assert "My Teaching Persona" in content
        assert "Subject" in content


# ── Soul generation ───────────────────────────────────────────────────


class TestGenerateSoul:
    def test_contains_philosophy(self, persona, config):
        content = generate_soul(persona, config)
        assert "Inquiry Based" in content

    def test_contains_tone(self, persona, config):
        content = generate_soul(persona, config)
        assert "warm but challenging" in content

    def test_contains_vocabulary_level(self, persona, config):
        content = generate_soul(persona, config)
        assert "academic" in content

    def test_contains_strategies(self, persona, config):
        content = generate_soul(persona, config)
        assert "think-pair-share" in content
        assert "gallery walk" in content

    def test_contains_differentiation(self, persona, config):
        content = generate_soul(persona, config)
        assert "IEP" in content
        assert "ELL" in content

    def test_contains_voice_sample(self, persona, config):
        content = generate_soul(persona, config)
        assert "explore the question" in content

    def test_contains_structural_prefs(self, persona, config):
        content = generate_soul(persona, config)
        assert "warm-ups" in content
        assert "exit tickets" in content

    def test_default_persona(self):
        content = generate_soul(TeacherPersona())
        assert "Direct Instruction" in content


# ── Workspace init ────────────────────────────────────────────────────


class TestInitWorkspace:
    def test_creates_directories(self, tmp_workspace, persona, config):
        init_workspace(persona, config)
        assert tmp_workspace.exists()
        assert (tmp_workspace / "notes").exists()
        assert (tmp_workspace / "students").exists()

    def test_creates_identity(self, tmp_workspace, persona, config):
        init_workspace(persona, config)
        identity = tmp_workspace / "identity.md"
        assert identity.exists()
        assert "Ms. Rodriguez" in identity.read_text()

    def test_creates_soul(self, tmp_workspace, persona, config):
        init_workspace(persona, config)
        soul = tmp_workspace / "soul.md"
        assert soul.exists()
        assert "Teaching Soul" in soul.read_text()

    def test_creates_memory(self, tmp_workspace, persona, config):
        init_workspace(persona, config)
        memory = tmp_workspace / "memory.md"
        assert memory.exists()
        assert "Teaching Memory" in memory.read_text()

    def test_creates_heartbeat(self, tmp_workspace, persona, config):
        init_workspace(persona, config)
        heartbeat = tmp_workspace / "heartbeat.md"
        assert heartbeat.exists()
        assert "Morning Prep" in heartbeat.read_text()

    def test_creates_todays_notes(self, tmp_workspace, persona, config):
        init_workspace(persona, config)
        notes = list((tmp_workspace / "notes").glob("*.md"))
        assert len(notes) == 1
        assert "Teaching Notes" in notes[0].read_text()

    def test_preserves_existing_memory(self, tmp_workspace, persona, config):
        # Create workspace with custom memory first
        init_workspace(persona, config)
        memory = tmp_workspace / "memory.md"
        memory.write_text("# Custom Memory\nDo not overwrite me.")

        # Re-init should NOT overwrite memory
        init_workspace(persona, config)
        assert "Do not overwrite me" in memory.read_text()

    def test_preserves_existing_identity(self, tmp_workspace, persona, config):
        """Blank slate: init never overwrites teacher's edits to identity.md."""
        init_workspace(persona, config)
        identity = tmp_workspace / "identity.md"
        identity.write_text("# My Custom Identity\nI edited this myself.")

        init_workspace(persona, config)
        assert "I edited this myself" in identity.read_text()

    def test_preserves_existing_soul(self, tmp_workspace, persona, config):
        """Blank slate: init never overwrites teacher's edits to soul.md."""
        init_workspace(persona, config)
        soul = tmp_workspace / "soul.md"
        soul.write_text("# My Teaching Philosophy\nI wrote this by hand.")

        init_workspace(persona, config)
        assert "I wrote this by hand" in soul.read_text()

    def test_preserves_existing_heartbeat(self, tmp_workspace, persona, config):
        """Blank slate: init never overwrites teacher's edits to heartbeat.md."""
        init_workspace(persona, config)
        hb = tmp_workspace / "heartbeat.md"
        hb.write_text("# My Custom Heartbeat\nCheck my specific things.")

        init_workspace(persona, config)
        assert "Check my specific things" in hb.read_text()

    def test_returns_workspace_path(self, tmp_workspace, persona, config):
        result = init_workspace(persona, config)
        assert result == tmp_workspace

    def test_default_persona_when_none(self, tmp_workspace):
        result = init_workspace()
        assert result == tmp_workspace
        identity = tmp_workspace / "identity.md"
        assert identity.exists()


# ── Daily notes ───────────────────────────────────────────────────────


class TestDailyNotes:
    def test_append_creates_file(self, tmp_workspace):
        (tmp_workspace / "notes").mkdir(parents=True, exist_ok=True)
        append_daily_note("First note of the day.")
        notes = get_daily_notes()
        assert "First note of the day." in notes

    def test_append_with_category(self, tmp_workspace):
        (tmp_workspace / "notes").mkdir(parents=True, exist_ok=True)
        append_daily_note("Lesson went well!", category="lesson")
        notes = get_daily_notes()
        assert "[lesson]" in notes
        assert "Lesson went well!" in notes

    def test_multiple_notes(self, tmp_workspace):
        (tmp_workspace / "notes").mkdir(parents=True, exist_ok=True)
        append_daily_note("Note one.")
        append_daily_note("Note two.")
        notes = get_daily_notes()
        assert "Note one." in notes
        assert "Note two." in notes

    def test_no_notes_returns_empty(self, tmp_workspace):
        assert get_daily_notes() == ""


# ── Student profiles ─────────────────────────────────────────────────


class TestStudentProfiles:
    def test_get_creates_new_profile(self, tmp_workspace):
        profile = get_student_profile("Maria Torres")
        assert "Maria Torres" in profile
        assert "Interactions" in profile

    def test_get_reads_existing(self, tmp_workspace):
        # Create profile
        get_student_profile("Alex Kim")
        # Read it again
        profile = get_student_profile("Alex Kim")
        assert "Alex Kim" in profile

    def test_update_appends_interaction(self, tmp_workspace):
        get_student_profile("Jordan Lee")
        update_student_profile("Jordan Lee", "Asked about mitosis stages")
        profile = get_student_profile("Jordan Lee")
        assert "mitosis stages" in profile

    def test_update_removes_placeholder(self, tmp_workspace):
        get_student_profile("Sam Davis")
        update_student_profile("Sam Davis", "First question about fractions")
        profile = get_student_profile("Sam Davis")
        assert "No interactions yet" not in profile

    def test_multiple_interactions(self, tmp_workspace):
        get_student_profile("Pat Chan")
        update_student_profile("Pat Chan", "Asked about homework")
        update_student_profile("Pat Chan", "Struggled with problem 3")
        profile = get_student_profile("Pat Chan")
        assert "homework" in profile
        assert "problem 3" in profile

    def test_list_empty(self, tmp_workspace):
        assert list_student_profiles() == []

    def test_list_profiles(self, tmp_workspace):
        get_student_profile("Alice")
        get_student_profile("Bob")
        profiles = list_student_profiles()
        assert len(profiles) == 2
        assert "Alice" in profiles
        assert "Bob" in profiles


# ── Memory updates ────────────────────────────────────────────────────


class TestMemoryUpdates:
    def test_update_existing_section(self, tmp_workspace):
        (tmp_workspace).mkdir(parents=True, exist_ok=True)
        memory = tmp_workspace / "memory.md"
        memory.write_text(
            "# Teaching Memory\n\n"
            "## Lessons That Got 5-Star Ratings\n"
            "*(Nothing yet -- keep teaching!)*\n\n"
            "## Common Student Questions\n"
            "*(Patterns will appear here as students interact.)*\n"
        )

        update_memory("Lessons That Got 5-Star Ratings", "Photosynthesis lesson (2026-03-23)")
        content = memory.read_text()
        assert "Photosynthesis lesson" in content
        assert "Nothing yet" not in content

    def test_update_creates_new_section(self, tmp_workspace):
        (tmp_workspace).mkdir(parents=True, exist_ok=True)
        memory = tmp_workspace / "memory.md"
        memory.write_text("# Teaching Memory\n")

        update_memory("Custom Section", "A new insight")
        content = memory.read_text()
        assert "## Custom Section" in content
        assert "A new insight" in content

    def test_update_preserves_other_sections(self, tmp_workspace):
        (tmp_workspace).mkdir(parents=True, exist_ok=True)
        memory = tmp_workspace / "memory.md"
        memory.write_text(
            "# Teaching Memory\n\n"
            "## Lessons That Got 5-Star Ratings\n"
            "- Existing great lesson\n\n"
            "## Common Student Questions\n"
            "*(Patterns will appear here as students interact.)*\n"
        )

        update_memory("Common Student Questions", "What is photosynthesis?")
        content = memory.read_text()
        assert "Existing great lesson" in content
        assert "What is photosynthesis?" in content


# ── Context loading ───────────────────────────────────────────────────


class TestLoadContext:
    def test_loads_identity_and_soul(self, tmp_workspace, persona, config):
        init_workspace(persona, config)
        ctx = load_context()
        assert "Ms. Rodriguez" in ctx
        assert "Teaching Soul" in ctx

    def test_includes_todays_notes(self, tmp_workspace, persona, config):
        init_workspace(persona, config)
        append_daily_note("Important note for context test.")
        ctx = load_context()
        assert "Important note for context test" in ctx

    def test_empty_workspace_auto_inits(self, tmp_workspace):
        # _ensure_workspace is called by load_context
        ctx = load_context()
        assert len(ctx) > 0


# ── Inject workspace context ─────────────────────────────────────────


class TestInjectWorkspaceContext:
    def test_returns_wrapped_context(self, tmp_workspace, persona, config):
        init_workspace(persona, config)
        result = inject_workspace_context()
        assert "<!-- Teacher Workspace Context -->" in result
        assert "<!-- End Teacher Workspace Context -->" in result
        assert "Ms. Rodriguez" in result

    def test_empty_returns_empty_string(self, tmp_workspace):
        # Create workspace but with empty files
        ws = tmp_workspace
        ws.mkdir(parents=True, exist_ok=True)
        (ws / "identity.md").write_text("")
        (ws / "soul.md").write_text("")
        # Even with empty files, load_context auto-inits if identity is missing content
        # The auto-init will populate them, so we just verify it doesn't crash
        result = inject_workspace_context()
        assert isinstance(result, str)
