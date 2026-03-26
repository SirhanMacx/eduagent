"""Pydantic data models for Claw-ED."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class DocType(str, Enum):
    """Supported document types."""

    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    TXT = "txt"
    MD = "md"
    NOTEBOOK = "notebook"
    XBK = "xbk"
    FLIPCHART = "flipchart"
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
    LECTURE_DISCUSSION = "lecture_discussion"
    WORKSHOP = "workshop"
    FLIPPED = "flipped"
    COOPERATIVE = "cooperative"
    DIFFERENTIATED = "differentiated"


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
    COMPETENCY_BASED = "competency_based"
    MASTERY_BASED = "mastery_based"
    PARTICIPATION_BASED = "participation_based"


class TeacherPersona(BaseModel):
    """Extracted teacher persona from curriculum materials."""

    name: str = "My Teaching Persona"
    teaching_style: TeachingStyle = TeachingStyle.DIRECT_INSTRUCTION

    @field_validator("teaching_style", mode="before")
    @classmethod
    def _coerce_teaching_style(cls, v):
        """Map unrecognized LLM-generated styles to the closest enum value."""
        if isinstance(v, TeachingStyle):
            return v
        if isinstance(v, str):
            # Try exact match first
            try:
                return TeachingStyle(v)
            except ValueError:
                pass
            # Fuzzy map common LLM outputs to valid enum values
            aliases = {
                "lecture": "lecture_discussion",
                "discussion": "lecture_discussion",
                "lecture_based": "lecture_discussion",
                "collaborative": "cooperative",
                "experiential": "inquiry_based",
                "constructivist": "inquiry_based",
                "problem_based": "project_based",
                "student_centered": "inquiry_based",
                "teacher_centered": "direct_instruction",
                "traditional": "direct_instruction",
                "hybrid": "blended",
                "mixed": "blended",
            }
            normalized = v.lower().strip().replace("-", "_").replace(" ", "_")
            if normalized in aliases:
                return TeachingStyle(aliases[normalized])
            # Last resort: default to blended
            return TeachingStyle.BLENDED
        return v

    vocabulary_level: VocabularyLevel = VocabularyLevel.GRADE_APPROPRIATE

    @field_validator("vocabulary_level", mode="before")
    @classmethod
    def _coerce_vocabulary_level(cls, v):
        """Map unrecognized vocabulary levels to the closest enum value."""
        if isinstance(v, VocabularyLevel):
            return v
        if isinstance(v, str):
            try:
                return VocabularyLevel(v)
            except ValueError:
                pass
            normalized = v.lower().strip().replace("-", "_").replace(" ", "_")
            # Try with normalization
            for member in VocabularyLevel:
                if member.value == normalized:
                    return member
            return VocabularyLevel.GRADE_APPROPRIATE
        return v

    tone: str = "warm and encouraging"
    structural_preferences: list[str] = Field(
        default_factory=lambda: ["warm-ups", "exit tickets"]
    )
    assessment_style: AssessmentStyle = AssessmentStyle.RUBRIC_BASED

    @field_validator("assessment_style", mode="before")
    @classmethod
    def _coerce_assessment_style(cls, v):
        """Map unrecognized assessment styles to the closest enum value."""
        if isinstance(v, AssessmentStyle):
            return v
        if isinstance(v, str):
            try:
                return AssessmentStyle(v)
            except ValueError:
                pass
            aliases = {
                "points_based": "point_based",
                "points": "point_based",
                "rubric": "rubric_based",
                "rubrics": "rubric_based",
                "standards": "standards_based",
                "standard_based": "standards_based",
                "competency": "competency_based",
                "mastery": "mastery_based",
                "participation": "participation_based",
                "performance_based": "rubric_based",
                "grade_based": "point_based",
                "grading": "point_based",
            }
            normalized = v.lower().strip().replace("-", "_").replace(" ", "_")
            if normalized in aliases:
                return AssessmentStyle(aliases[normalized])
            return AssessmentStyle.RUBRIC_BASED
        return v
    preferred_lesson_format: str = "I Do / We Do / You Do"
    favorite_strategies: list[str] = Field(default_factory=list)
    subject_area: str = ""
    grade_levels: list[str] = Field(default_factory=list)
    voice_sample: str = ""
    voice_examples: list[str] = Field(default_factory=list)

    def to_prompt_context(self) -> str:
        """Serialize persona into a string for LLM prompt injection."""
        lines = [
            "Teacher Persona:",
            f"- Name: {self.name}",
            f"- Teaching Style: {self.teaching_style.value.replace('_', ' ').title()}",
            f"- Vocabulary Level: {self.vocabulary_level.value.replace('_', ' ').title()}",
            f"- Tone: {self.tone}",
            f"- Structural Preferences: {', '.join(self.structural_preferences)}",
            f"- Assessment Style: {self.assessment_style.value.replace('_', ' ').title()}",
            f"- Preferred Lesson Format: {self.preferred_lesson_format}",
            f"- Favorite Strategies: {', '.join(self.favorite_strategies) or 'None specified'}",
            f"- Subject Area: {self.subject_area or 'General'}",
            f"- Grade Levels: {', '.join(self.grade_levels) or 'Not specified'}",
            f"- Voice Sample: {self.voice_sample[:500] if self.voice_sample else 'None'}",
        ]
        if self.voice_examples:
            lines.append("")
            lines.append("=== Voice Examples (write like this) ===")
            for i, example in enumerate(self.voice_examples[:5], 1):
                lines.append(f'Example {i}: "{example}"')
            lines.append("")
            lines.append(
                "Your writing MUST match the voice and style shown in the Voice Examples above. "
                "Use the same vocabulary, sentence structure, and tone."
            )
        return "\n".join(lines) + "\n"


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


class IEPProfile(BaseModel):
    """A student's IEP (Individualized Education Program) profile.

    Contains disability information, required accommodations, modifications,
    and annual goals — everything a teacher needs to differentiate a lesson
    for this student.
    """

    student_name: str
    disability_type: str = ""
    accommodations: list[str] = Field(default_factory=list)
    modifications: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)


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


class School(BaseModel):
    """A school deployment — groups teachers for curriculum sharing."""

    school_id: str = ""
    name: str = ""
    district: str = ""
    state: str = ""
    grade_levels: list[str] = Field(default_factory=list)


class SharedContentEntry(BaseModel):
    """A unit or lesson shared to a school's curriculum library."""

    id: str = ""
    school_id: str = ""
    teacher_id: str = ""
    teacher_name: str = ""
    content_type: str = "unit"  # "unit" or "lesson"
    content_id: str = ""
    title: str = ""
    subject: str = ""
    grade_level: str = ""
    department: str = ""
    rating: Optional[int] = None
    shared_at: str = ""


class ScheduleBlock(BaseModel):
    """A single time block in the daily schedule."""

    time: str
    period: str
    class_name: str
    notes: str = ""


class BehavioralNote(BaseModel):
    """Behavioral context for a class period."""

    period: str
    class_dynamics: str
    seating_chart: str = "See printed seating chart on teacher desk."
    accommodations: list[str] = Field(default_factory=list)
    key_students: list[str] = Field(default_factory=list)


class SubLessonInstructions(BaseModel):
    """Step-by-step lesson instructions written for a substitute."""

    period: str
    lesson_title: str
    objective: str
    step_by_step: list[str] = Field(default_factory=list)
    materials_needed: list[str] = Field(default_factory=list)
    backup_activity: str = ""
    answer_key_location: str = ""


class SubPacket(BaseModel):
    """A complete substitute teacher packet."""

    teacher_name: str
    date: str
    school: str = ""
    schedule: list[ScheduleBlock] = Field(default_factory=list)
    behavioral_notes: list[BehavioralNote] = Field(default_factory=list)
    lesson_instructions: list[SubLessonInstructions] = Field(default_factory=list)
    emergency_contacts: list[str] = Field(default_factory=lambda: [
        "Main Office: ext. 100",
        "Nurse: ext. 150",
        "Nearest Teacher (for emergencies): See posted list by door",
    ])
    emergency_procedures: str = (
        "Fire drill: exit via nearest marked exit, proceed to designated area. "
        "Lockdown: lock door, lights off, students against interior wall away from windows."
    )
    general_notes: str = ""
    materials_checklist: list[str] = Field(default_factory=list)


class ProgressUpdate(BaseModel):
    """A parent communication progress update in the teacher's voice."""

    student_name: str
    greeting: str
    strengths: list[str] = Field(default_factory=list)
    areas_to_grow: list[str] = Field(default_factory=list)
    specific_examples: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)
    closing: str = ""


# ── Assessment intelligence models ─────────────────────────────────────


class QuestionType(str, Enum):
    """Types of assessment questions."""

    MULTIPLE_CHOICE = "multiple_choice"
    SHORT_ANSWER = "short_answer"
    TRUE_FALSE = "true_false"
    ESSAY = "essay"
    DBQ = "dbq"
    FILL_IN_BLANK = "fill_in_the_blank"


class RubricLevel(BaseModel):
    """A single level within a rubric row (e.g. '4 — Exceeds')."""

    score: int
    label: str
    descriptors: list[str] = Field(default_factory=list)


class Rubric(BaseModel):
    """A complete rubric for any written task. 4-point scale."""

    task_description: str
    criteria: list[RubricCriterion] = Field(default_factory=list)
    total_points: int = 0


class FormativeAssessment(BaseModel):
    """Exit-ticket style formative assessment — checks ONE lesson's objective."""

    lesson_title: str
    objective: str
    questions: list[AssessmentQuestion] = Field(default_factory=list)
    answer_key: dict[int, str] = Field(default_factory=dict)
    time_minutes: int = 5


class SummativeQuestion(BaseModel):
    """A question in a summative assessment with Bloom's level tag."""

    question_number: int
    question_type: str = "multiple_choice"
    blooms_level: str = "remember"
    question: str
    choices: list[str] = Field(default_factory=list)
    correct_answer: str = ""
    point_value: int = 1
    standard_aligned: str = ""


class SummativeAssessment(BaseModel):
    """Unit test — mix of MC, short answer, DBQ/essay aligned to all unit objectives."""

    unit_title: str
    subject: str
    grade_level: str
    objectives: list[str] = Field(default_factory=list)
    questions: list[SummativeQuestion] = Field(default_factory=list)
    rubric: list[RubricCriterion] = Field(default_factory=list)
    total_points: int = 0
    time_minutes: int = 45


class DBQDocument(BaseModel):
    """A primary source document within a DBQ assessment."""

    document_number: int
    title: str
    source: str = ""
    date: str = ""
    content: str = ""
    scaffolding_questions: list[str] = Field(default_factory=list)


class DBQAssessment(BaseModel):
    """Document-Based Question — NYS Regents style.

    Includes background paragraph, primary source documents with scaffolding
    questions, extended response prompt, and a model answer.
    """

    topic: str
    grade_level: str
    background: str = ""
    documents: list[DBQDocument] = Field(default_factory=list)
    essay_prompt: str = ""
    model_answer: str = ""
    rubric: list[RubricCriterion] = Field(default_factory=list)
    time_minutes: int = 60


class Quiz(BaseModel):
    """Short quiz — teacher-specified format mix."""

    topic: str
    grade_level: str
    questions: list[AssessmentQuestion] = Field(default_factory=list)
    answer_key: dict[int, str] = Field(default_factory=dict)
    total_points: int = 0
    time_minutes: int = 15


# ── Year-level curriculum planning models ─────────────────────────────────


class YearMapUnit(BaseModel):
    """A single unit within the full-year curriculum map."""

    unit_number: int
    title: str
    duration_weeks: int
    essential_questions: list[str] = Field(default_factory=list)
    standards: list[str] = Field(default_factory=list)
    description: str = ""


class BigIdea(BaseModel):
    """A big idea that connects across multiple units in the year."""

    idea: str
    connected_units: list[int] = Field(default_factory=list)


class AssessmentCalendarEntry(BaseModel):
    """A planned assessment on the year calendar."""

    unit_number: int
    assessment_type: str = "summative"  # formative, summative, benchmark, diagnostic
    title: str
    week: int


class YearMap(BaseModel):
    """A full-year curriculum map — the top-level planning document."""

    subject: str
    grade_level: str
    school_year: str = ""
    total_weeks: int = 36
    units: list[YearMapUnit] = Field(default_factory=list)
    big_ideas: list[BigIdea] = Field(default_factory=list)
    assessment_calendar: list[AssessmentCalendarEntry] = Field(default_factory=list)


class SchoolCalendarEvent(BaseModel):
    """A school calendar event (holiday, break, PD day)."""

    date: str  # ISO date
    end_date: str = ""  # For multi-day events like breaks
    event: str
    type: str = "holiday"  # holiday, break, pd_day, half_day, testing


class PacingWeek(BaseModel):
    """A single week in the pacing guide."""

    week_number: int
    start_date: str  # ISO date
    end_date: str  # ISO date
    unit_title: str
    unit_number: int
    topics: list[str] = Field(default_factory=list)
    notes: str = ""  # holidays, testing windows, etc.


class PacingGuide(BaseModel):
    """A week-by-week pacing guide with actual calendar dates."""

    subject: str
    grade_level: str
    school_year: str = ""
    start_date: str  # ISO date of first instructional day
    weeks: list[PacingWeek] = Field(default_factory=list)


class CurriculumGap(BaseModel):
    """An identified gap in curriculum coverage vs. standards."""

    standard: str
    description: str
    severity: str = "medium"  # low, medium, high
    suggestion: str = ""


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OLLAMA = "ollama"


class TeacherProfile(BaseModel):
    """Teacher-specific configuration that auto-tailors all generation.

    This is the key to personalization — when a teacher sets their profile,
    every lesson plan, unit, worksheet, and assessment is automatically
    aligned to their state standards, subjects, and grade levels.
    """

    name: str = ""
    school: str = ""

    # What they teach
    subjects: list[str] = Field(default_factory=list)
    grade_levels: list[str] = Field(default_factory=list)

    # Standards framework (determines which standards to reference)
    # Options: "CCSS", "NGSS", "C3", "NY_SS", "TX_TEKS", "CA_FRAMEWORKS", "custom"
    standards_framework: str = "CCSS"
    state: str = ""  # e.g., "NY", "CA", "TX" — used to select state-specific standards

    # Teaching context
    class_size: Optional[int] = None
    has_iep_students: bool = True
    has_ell_students: bool = True
    school_year: str = "2025-26"

    # Materials paths (where their curriculum lives)
    materials_paths: list[str] = Field(default_factory=list)  # Local paths
    drive_urls: list[str] = Field(default_factory=list)       # Google Drive URLs

    # API keys (stored here for portability, keyring preferred)
    tavily_api_key: Optional[str] = None

    def get_standards_prefix(self) -> str:
        """Get the standards code prefix for this teacher's framework."""
        mapping = {
            "CCSS": "CCSS",
            "NGSS": "NGSS",
            "C3": "C3",
            "NY_SS": "NYS-SS",
            "TX_TEKS": "TEKS",
        }
        return mapping.get(self.standards_framework, self.standards_framework)

    def describe(self) -> str:
        """Human-readable profile summary for LLM prompts."""
        parts = []
        if self.name:
            parts.append(f"Teacher: {self.name}")
        if self.school:
            parts.append(f"School: {self.school}")
        if self.subjects:
            parts.append(f"Subjects: {', '.join(self.subjects)}")
        if self.grade_levels:
            parts.append(f"Grades: {', '.join(self.grade_levels)}")
        if self.standards_framework:
            parts.append(f"Standards: {self.standards_framework}")
        if self.state:
            parts.append(f"State: {self.state}")
        if self.has_iep_students:
            parts.append("Has IEP students: Yes")
        if self.has_ell_students:
            parts.append("Has ELL students: Yes")
        return "\n".join(parts) if parts else "Profile not configured"

    def get_standards_context(self) -> str:
        """Generate standards context string for LLM prompt injection.

        Uses the teacher's state, subjects, and grade levels to produce
        a block of text describing applicable standards frameworks.
        """
        if not self.state:
            return ""
        from clawed.state_standards import get_standards_context_for_prompt

        return get_standards_context_for_prompt(
            self.state, self.subjects, self.grade_levels
        )


class AppConfig(BaseModel):
    """Application configuration."""

    provider: LLMProvider = LLMProvider.ANTHROPIC
    anthropic_model: str = "claude-sonnet-4-6"
    openai_model: str = "gpt-4o"
    ollama_model: str = "llama3.2"
    ollama_base_url: str = "http://localhost:11434"
    output_dir: str = "./clawed_output"
    include_homework: bool = True
    agent_gateway: bool = True
    export_format: str = "markdown"
    drive_root_folder: str = ""
    drive_token_path: str = ""

    # Ollama API key (for cloud Ollama)
    ollama_api_key: Optional[str] = None

    # Telegram bot token (persisted so teachers don't re-enter it every time)
    telegram_bot_token: Optional[str] = None

    # Per-task model overrides (e.g. {"bellringer": "qwen3.5:cloud"})
    task_models: Optional[dict[str, str]] = None

    # Tier model overrides (e.g. {"fast": "qwen3.5:cloud", "work": "claude-sonnet-4-6", "deep": "claude-opus-4-6"})
    tier_models: Optional[dict[str, str]] = None

    # Teacher profile — the key to auto-tailoring
    teacher_profile: TeacherProfile = Field(default_factory=TeacherProfile)

    @staticmethod
    def config_path() -> Path:
        import os
        env_dir = os.environ.get("EDUAGENT_DATA_DIR")
        if env_dir:
            return Path(env_dir) / "config.json"
        return Path.home() / ".eduagent" / "config.json"

    # Fields that contain secrets and must never be written to the JSON
    # config file.  They are stored via keyring (preferred) or env vars
    # only.  See clawed/config.py for the secure storage helpers.
    _SECRET_FIELDS: tuple[str, ...] = (
        "ollama_api_key",
        "telegram_bot_token",
    )

    @classmethod
    def load(cls) -> "AppConfig":
        """Load config from disk, or return defaults.

        After loading the JSON config, hydrate secret fields from the
        secure store (keyring > env var).  This ensures API keys are
        never read from the plaintext JSON file.
        """
        path = cls.config_path()
        if path.exists():
            cfg = cls.model_validate_json(path.read_text(encoding="utf-8"))
        else:
            cfg = cls()

        # Honor OLLAMA_URL env var as an alias for ollama_base_url
        import os
        ollama_url_env = os.environ.get("OLLAMA_URL")
        if ollama_url_env and cfg.ollama_base_url == "http://localhost:11434":
            cfg.ollama_base_url = ollama_url_env

        # Hydrate secrets from secure storage
        from clawed.config import get_api_key

        if not cfg.ollama_api_key:
            cfg.ollama_api_key = get_api_key("ollama")
        if not cfg.telegram_bot_token:
            cfg.telegram_bot_token = get_api_key("telegram")
        # Teacher-profile tavily key
        if (
            cfg.teacher_profile
            and not cfg.teacher_profile.tavily_api_key
        ):
            cfg.teacher_profile.tavily_api_key = get_api_key("tavily")

        return cfg

    def save(self) -> None:
        """Persist config to disk.

        Secret fields (API keys, tokens) are stripped before writing so
        they never end up in the plaintext JSON config file.  Use
        clawed.config.set_api_key() to store secrets securely.
        """
        # Move secrets to the secure store before writing
        from clawed.config import set_api_key

        if self.ollama_api_key:
            set_api_key("ollama", self.ollama_api_key)
        if self.telegram_bot_token:
            set_api_key("telegram", self.telegram_bot_token)
        if (
            self.teacher_profile
            and self.teacher_profile.tavily_api_key
        ):
            set_api_key("tavily", self.teacher_profile.tavily_api_key)

        # Serialize, stripping secret fields so they are never on disk
        data = self.model_dump()
        for field in self._SECRET_FIELDS:
            data.pop(field, None)
        # Also strip tavily from the nested teacher profile
        tp = data.get("teacher_profile")
        if tp and isinstance(tp, dict):
            tp.pop("tavily_api_key", None)

        import json

        path = self.config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


class StudentProgress(BaseModel):
    """Per-student progress tracking model."""

    student_name: str = ""
    student_id: str = ""
    class_code: str = ""
    topics_asked: dict[str, int] = Field(default_factory=dict)
    total_questions: int = 0
    last_active: str = ""  # ISO datetime string
    struggle_topics: list[str] = Field(default_factory=list)

    def record_question(self, topic: str) -> None:
        """Record a question about a topic, updating counts and struggle detection."""
        from datetime import datetime, timezone

        self.total_questions += 1
        self.last_active = datetime.now(timezone.utc).isoformat()
        topic_key = topic.strip().lower() if topic else "general"
        self.topics_asked[topic_key] = self.topics_asked.get(topic_key, 0) + 1
        # Mark as struggle topic if asked 3+ times
        if self.topics_asked[topic_key] >= 3 and topic_key not in self.struggle_topics:
            self.struggle_topics.append(topic_key)
