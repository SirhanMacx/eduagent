"""Basic tests for EDUagent models and core functionality."""

import pytest
from pathlib import Path

from eduagent.models import (
    AppConfig,
    AssessmentPlan,
    AssessmentQuestion,
    DailyLesson,
    DifferentiationNotes,
    DocType,
    Document,
    ExitTicketQuestion,
    LessonBrief,
    LessonMaterials,
    LLMProvider,
    RubricCriterion,
    SlideOutline,
    TeacherPersona,
    TeachingStyle,
    UnitPlan,
    VocabularyLevel,
    WorksheetItem,
)


# ── Document model ──────────────────────────────────────────────────


class TestDocumentModel:
    def test_create_document(self):
        doc = Document(
            title="Cell Division Notes",
            content="Mitosis is a process of cell division...",
            doc_type=DocType.DOCX,
            source_path="/tmp/cell_division.docx",
            page_count=3,
        )
        assert doc.title == "Cell Division Notes"
        assert doc.content == "Mitosis is a process of cell division..."
        assert doc.doc_type == DocType.DOCX
        assert doc.source_path == "/tmp/cell_division.docx"
        assert doc.page_count == 3

    def test_document_optional_fields(self):
        doc = Document(
            title="Quick Note",
            content="Some text",
            doc_type=DocType.TXT,
        )
        assert doc.source_path is None
        assert doc.page_count is None

    def test_doc_type_values(self):
        assert DocType.PDF.value == "pdf"
        assert DocType.DOCX.value == "docx"
        assert DocType.PPTX.value == "pptx"
        assert DocType.TXT.value == "txt"
        assert DocType.MD.value == "md"
        assert DocType.UNKNOWN.value == "unknown"


# ── TeacherPersona model ────────────────────────────────────────────


class TestTeacherPersonaDefaults:
    def test_default_persona_is_sane(self):
        persona = TeacherPersona()
        assert persona.name == "My Teaching Persona"
        assert persona.teaching_style == TeachingStyle.DIRECT_INSTRUCTION
        assert persona.vocabulary_level == VocabularyLevel.GRADE_APPROPRIATE
        assert persona.tone == "warm and encouraging"
        assert "warm-ups" in persona.structural_preferences
        assert "exit tickets" in persona.structural_preferences
        assert persona.assessment_style.value == "rubric_based"
        assert persona.preferred_lesson_format == "I Do / We Do / You Do"
        assert persona.favorite_strategies == []
        assert persona.subject_area == ""
        assert persona.grade_levels == []
        assert persona.voice_sample == ""

    def test_custom_persona(self):
        persona = TeacherPersona(
            name="Ms. Johnson",
            teaching_style=TeachingStyle.SOCRATIC,
            vocabulary_level=VocabularyLevel.ACADEMIC,
            tone="challenging but supportive",
            subject_area="Physics",
            grade_levels=["11", "12"],
            favorite_strategies=["think-pair-share", "Socratic seminar"],
        )
        assert persona.name == "Ms. Johnson"
        assert persona.teaching_style == TeachingStyle.SOCRATIC
        assert persona.subject_area == "Physics"
        assert len(persona.grade_levels) == 2
        assert "think-pair-share" in persona.favorite_strategies


# ── Persona to_prompt_context ────────────────────────────────────────


class TestPersonaToPromptContext:
    def test_prompt_context_contains_expected_fields(self):
        persona = TeacherPersona(
            name="Mr. Rivera",
            teaching_style=TeachingStyle.INQUIRY_BASED,
            vocabulary_level=VocabularyLevel.CASUAL,
            tone="enthusiastic and energetic",
            subject_area="History",
            grade_levels=["6", "7"],
            favorite_strategies=["gallery walk", "jigsaw"],
            structural_preferences=["warm-ups", "exit tickets", "think-pair-share"],
        )
        ctx = persona.to_prompt_context()

        assert "Mr. Rivera" in ctx
        assert "Inquiry Based" in ctx
        assert "Casual" in ctx
        assert "enthusiastic and energetic" in ctx
        assert "History" in ctx
        assert "6" in ctx
        assert "7" in ctx
        assert "gallery walk" in ctx
        assert "jigsaw" in ctx
        assert "warm-ups" in ctx
        assert "Teacher Persona:" in ctx

    def test_prompt_context_handles_empty_strategies(self):
        persona = TeacherPersona()
        ctx = persona.to_prompt_context()
        assert "None specified" in ctx

    def test_prompt_context_handles_empty_subject(self):
        persona = TeacherPersona()
        ctx = persona.to_prompt_context()
        assert "General" in ctx

    def test_prompt_context_truncates_voice_sample(self):
        persona = TeacherPersona(voice_sample="x" * 1000)
        ctx = persona.to_prompt_context()
        # Voice sample should be truncated to 500 chars
        assert "x" * 500 in ctx
        assert "x" * 501 not in ctx


# ── Ingest path validation ──────────────────────────────────────────


class TestIngestPathNonexistent:
    def test_raises_file_not_found_for_nonexistent_path(self):
        from eduagent.ingestor import ingest_path

        with pytest.raises(FileNotFoundError):
            ingest_path(Path("/tmp/definitely_does_not_exist_eduagent_test"))

    def test_raises_file_not_found_for_nonexistent_directory(self):
        from eduagent.ingestor import ingest_directory

        with pytest.raises(FileNotFoundError):
            ingest_directory(Path("/tmp/no_such_dir_eduagent_9999"))


# ── AppConfig defaults ──────────────────────────────────────────────


class TestAppConfigDefaults:
    def test_default_config_values(self):
        config = AppConfig()
        assert config.provider == LLMProvider.ANTHROPIC
        assert config.anthropic_model == "claude-sonnet-4-6"
        assert config.openai_model == "gpt-4o"
        assert config.ollama_model == "llama3.2"
        assert config.ollama_base_url == "http://localhost:11434"
        assert config.output_dir == "./eduagent_output"
        assert config.include_homework is True
        assert config.export_format == "markdown"

    def test_config_path_is_in_home_dir(self):
        path = AppConfig.config_path()
        assert ".eduagent" in str(path)
        assert "config.json" in str(path)

    def test_custom_config(self):
        config = AppConfig(
            provider=LLMProvider.OLLAMA,
            ollama_model="mistral",
            include_homework=False,
            export_format="pdf",
        )
        assert config.provider == LLMProvider.OLLAMA
        assert config.ollama_model == "mistral"
        assert config.include_homework is False
        assert config.export_format == "pdf"


# ── UnitPlan model ──────────────────────────────────────────────────


class TestUnitPlanModel:
    def test_create_unit_plan_with_required_fields(self):
        unit = UnitPlan(
            title="Life From Light: Understanding Photosynthesis",
            subject="Science",
            grade_level="8",
            topic="Photosynthesis",
            duration_weeks=3,
            overview="A three-week unit exploring how plants convert light energy into chemical energy.",
            essential_questions=[
                "How do plants make their own food?",
                "Why does photosynthesis matter to all life?",
            ],
            enduring_understandings=[
                "Photosynthesis converts light energy into chemical energy.",
            ],
            daily_lessons=[
                LessonBrief(
                    lesson_number=1,
                    topic="Intro to Photosynthesis",
                    description="Big picture overview of photosynthesis.",
                    lesson_type="instruction",
                ),
                LessonBrief(
                    lesson_number=2,
                    topic="Energy From the Sun",
                    description="How sunlight reaches plants.",
                    lesson_type="instruction",
                ),
            ],
            assessment_plan=AssessmentPlan(
                formative=["Exit tickets", "Lab report"],
                summative=["Unit test"],
            ),
        )
        assert unit.title == "Life From Light: Understanding Photosynthesis"
        assert unit.duration_weeks == 3
        assert len(unit.essential_questions) == 2
        assert len(unit.daily_lessons) == 2
        assert unit.daily_lessons[0].lesson_number == 1
        assert unit.assessment_plan.formative[0] == "Exit tickets"
        assert unit.assessment_plan.summative[0] == "Unit test"

    def test_unit_plan_empty_optionals(self):
        unit = UnitPlan(
            title="Test Unit",
            subject="Math",
            grade_level="5",
            topic="Fractions",
            duration_weeks=2,
            overview="A short unit on fractions.",
        )
        assert unit.essential_questions == []
        assert unit.daily_lessons == []
        assert unit.standards == []
        assert unit.required_materials == []
        assert unit.assessment_plan.formative == []
        assert unit.assessment_plan.summative == []


# ── LessonMaterials model ───────────────────────────────────────────


class TestLessonMaterialsModel:
    def test_create_lesson_materials(self):
        materials = LessonMaterials(
            lesson_title="Intro to Photosynthesis",
            worksheet_items=[
                WorksheetItem(
                    item_number=1,
                    item_type="fill_in_the_blank",
                    prompt="Photosynthesis uses _____, _____, and _____ to make glucose.",
                    answer_key="sunlight, water, carbon dioxide",
                    point_value=2,
                ),
                WorksheetItem(
                    item_number=2,
                    item_type="short_answer",
                    prompt="Why is photosynthesis important?",
                    answer_key="It produces oxygen and is the base of food chains.",
                    point_value=3,
                ),
            ],
            assessment_questions=[
                AssessmentQuestion(
                    question_number=1,
                    question_type="multiple_choice",
                    question="Which is an output of photosynthesis?",
                    choices=["A) Water", "B) Carbon dioxide", "C) Glucose", "D) Sunlight"],
                    correct_answer="C",
                    point_value=1,
                ),
            ],
            rubric=[
                RubricCriterion(
                    criterion="Understanding of photosynthesis",
                    excellent="Accurately explains all inputs, outputs, and significance",
                    proficient="Explains most inputs and outputs correctly",
                    developing="Identifies some components but with errors",
                    beginning="Cannot identify basic components",
                ),
            ],
            slide_outline=[
                SlideOutline(
                    slide_number=1,
                    title="What is Photosynthesis?",
                    content_bullets=["Definition", "Why it matters"],
                    speaker_notes="Start with the Do-Now question.",
                ),
            ],
            iep_notes=["Provide word bank for fill-in-the-blank items"],
        )
        assert materials.lesson_title == "Intro to Photosynthesis"
        assert len(materials.worksheet_items) == 2
        assert materials.worksheet_items[0].point_value == 2
        assert len(materials.assessment_questions) == 1
        assert materials.assessment_questions[0].correct_answer == "C"
        assert len(materials.rubric) == 1
        assert "Accurately" in materials.rubric[0].excellent
        assert len(materials.slide_outline) == 1
        assert len(materials.iep_notes) == 1

    def test_lesson_materials_empty(self):
        materials = LessonMaterials(lesson_title="Empty Lesson")
        assert materials.worksheet_items == []
        assert materials.assessment_questions == []
        assert materials.rubric == []
        assert materials.slide_outline == []
        assert materials.iep_notes == []
