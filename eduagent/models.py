"""Pydantic data models for EDUagent."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class DocType(str, Enum):
    """Supported document types."""

    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    TXT = "txt"
    MD = "md"
    UNKNOWN = "unknown"


class Document(BaseModel):
    """A single ingested document with extracted text."""

    title: str
    content: str
    doc_type: DocType
    source_path: Optional[str] = None
    page_count: Optional[int] = None


class TeachingStyle(str, Enum):
    SOCRATIC = "socratic"
    DIRECT_INSTRUCTION = "direct_instruction"
    INQUIRY_BASED = "inquiry_based"
    PROJECT_BASED = "project_based"
    BLENDED = "blended"


class VocabularyLevel(str, Enum):
    ELEMENTARY = "elementary"
    GRADE_APPROPRIATE = "grade_appropriate"
    ACADEMIC = "academic"
    CASUAL = "casual"


class AssessmentStyle(str, Enum):
    RUBRIC_BASED = "rubric_based"
    POINT_BASED = "point_based"
    PORTFOLIO = "portfolio"
    STANDARDS_BASED = "standards_based"


class TeacherPersona(BaseModel):
    """Extracted teacher persona from curriculum materials."""

    name: str = "My Teaching Persona"
    teaching_style: TeachingStyle = TeachingStyle.DIRECT_INSTRUCTION
    vocabulary_level: VocabularyLevel = VocabularyLevel.GRADE_APPROPRIATE
    tone: str = "warm and encouraging"
    structural_preferences: list[str] = Field(
        default_factory=lambda: ["warm-ups", "exit tickets"]
    )
    assessment_style: AssessmentStyle = AssessmentStyle.RUBRIC_BASED
    preferred_lesson_format: str = "I Do / We Do / You Do"
    favorite_strategies: list[str] = Field(default_factory=list)
    subject_area: str = ""
    grade_levels: list[str] = Field(default_factory=list)
    voice_sample: str = ""

    def to_prompt_context(self) -> str:
        """Serialize persona into a string for LLM prompt injection."""
        return (
            f"Teacher Persona:\n"
            f"- Name: {self.name}\n"
            f"- Teaching Style: {self.teaching_style.value.replace('_', ' ').title()}\n"
            f"- Vocabulary Level: {self.vocabulary_level.value.replace('_', ' ').title()}\n"
            f"- Tone: {self.tone}\n"
            f"- Structural Preferences: {', '.join(self.structural_preferences)}\n"
            f"- Assessment Style: {self.assessment_style.value.replace('_', ' ').title()}\n"
            f"- Preferred Lesson Format: {self.preferred_lesson_format}\n"
            f"- Favorite Strategies: {', '.join(self.favorite_strategies) or 'None specified'}\n"
            f"- Subject Area: {self.subject_area or 'General'}\n"
            f"- Grade Levels: {', '.join(self.grade_levels) or 'Not specified'}\n"
            f"- Voice Sample: {self.voice_sample[:500] if self.voice_sample else 'None'}\n"
        )


class LessonBrief(BaseModel):
    """Brief description of a lesson within a unit plan."""

    lesson_number: int
    topic: str
    description: str
    lesson_type: str = "instruction"


class AssessmentPlan(BaseModel):
    """Assessment plan within a unit."""

    formative: list[str] = Field(default_factory=list)
    summative: list[str] = Field(default_factory=list)


class UnitPlan(BaseModel):
    """A complete unit plan."""

    title: str
    subject: str
    grade_level: str
    topic: str
    duration_weeks: int
    overview: str
    essential_questions: list[str] = Field(default_factory=list)
    enduring_understandings: list[str] = Field(default_factory=list)
    standards: list[str] = Field(default_factory=list)
    daily_lessons: list[LessonBrief] = Field(default_factory=list)
    assessment_plan: AssessmentPlan = Field(default_factory=AssessmentPlan)
    required_materials: list[str] = Field(default_factory=list)


class ExitTicketQuestion(BaseModel):
    """A single exit ticket question."""

    question: str
    expected_response: str = ""


class DifferentiationNotes(BaseModel):
    """Differentiation accommodations."""

    struggling: list[str] = Field(default_factory=list)
    advanced: list[str] = Field(default_factory=list)
    ell: list[str] = Field(default_factory=list)


class DailyLesson(BaseModel):
    """A complete daily lesson plan."""

    title: str
    lesson_number: int
    objective: str
    standards: list[str] = Field(default_factory=list)
    do_now: str = ""
    direct_instruction: str = ""
    guided_practice: str = ""
    independent_work: str = ""
    exit_ticket: list[ExitTicketQuestion] = Field(default_factory=list)
    homework: Optional[str] = None
    differentiation: DifferentiationNotes = Field(default_factory=DifferentiationNotes)
    materials_needed: list[str] = Field(default_factory=list)
    time_estimates: dict[str, int] = Field(
        default_factory=lambda: {
            "do_now": 5,
            "direct_instruction": 20,
            "guided_practice": 15,
            "independent_work": 10,
        }
    )


class WorksheetItem(BaseModel):
    """A single item on a worksheet."""

    item_number: int
    item_type: str = "short_answer"
    prompt: str
    answer_key: str = ""
    point_value: int = 1


class AssessmentQuestion(BaseModel):
    """A single assessment question."""

    question_number: int
    question_type: str = "multiple_choice"
    question: str
    choices: list[str] = Field(default_factory=list)
    correct_answer: str = ""
    point_value: int = 1


class RubricCriterion(BaseModel):
    """A single rubric criterion with levels."""

    criterion: str
    excellent: str = ""
    proficient: str = ""
    developing: str = ""
    beginning: str = ""


class SlideOutline(BaseModel):
    """Outline for a single slide."""

    slide_number: int
    title: str
    content_bullets: list[str] = Field(default_factory=list)
    speaker_notes: str = ""


class LessonMaterials(BaseModel):
    """All materials generated for a daily lesson."""

    lesson_title: str
    worksheet_items: list[WorksheetItem] = Field(default_factory=list)
    assessment_questions: list[AssessmentQuestion] = Field(default_factory=list)
    rubric: list[RubricCriterion] = Field(default_factory=list)
    slide_outline: list[SlideOutline] = Field(default_factory=list)
    iep_notes: list[str] = Field(default_factory=list)


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OLLAMA = "ollama"


class AppConfig(BaseModel):
    """Application configuration."""

    provider: LLMProvider = LLMProvider.ANTHROPIC
    anthropic_model: str = "claude-sonnet-4-6"
    openai_model: str = "gpt-4o"
    ollama_model: str = "llama3.2"
    ollama_base_url: str = "http://localhost:11434"
    output_dir: str = "./eduagent_output"
    include_homework: bool = True
    export_format: str = "markdown"

    @staticmethod
    def config_path() -> Path:
        return Path.home() / ".eduagent" / "config.json"

    @classmethod
    def load(cls) -> "AppConfig":
        """Load config from disk, or return defaults."""
        path = cls.config_path()
        if path.exists():
            return cls.model_validate_json(path.read_text())
        return cls()

    def save(self) -> None:
        """Persist config to disk."""
        path = self.config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2))
