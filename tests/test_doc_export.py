"""Tests for doc_export.py — PPTX, DOCX, and PDF generation from lesson plans."""

from __future__ import annotations

from pathlib import Path

import pytest

from eduagent.models import (
    DailyLesson,
    DifferentiationNotes,
    ExitTicketQuestion,
    TeacherPersona,
)


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def sample_lesson() -> DailyLesson:
    """A realistic DailyLesson with all required fields populated."""
    return DailyLesson(
        title="The Causes of World War I",
        lesson_number=3,
        objective="Students will be able to identify the four main causes of WWI (MAIN).",
        standards=["D2.His.1.9-12", "D2.His.3.9-12"],
        do_now="List one thing you already know about World War I.",
        direct_instruction=(
            "World War I was triggered by a complex web of factors often summarized "
            "by the acronym MAIN: Militarism, Alliances, Imperialism, and Nationalism. "
            "Each of these forces contributed to rising tensions across Europe in the "
            "early 20th century."
        ),
        guided_practice=(
            "In pairs, analyze a political cartoon from 1914. Identify which MAIN "
            "factor the cartoon illustrates and explain your reasoning."
        ),
        independent_work=(
            "Complete the MAIN graphic organizer by writing a one-sentence summary "
            "and a real-world example for each factor."
        ),
        exit_ticket=[
            ExitTicketQuestion(
                question="Which MAIN factor do you think was most responsible for WWI? Why?",
                expected_response="Any of the four with supporting reasoning.",
            ),
        ],
        homework="Read pages 112-118 and take notes on the assassination of Archduke Franz Ferdinand.",
        differentiation=DifferentiationNotes(
            struggling=["Provide a pre-filled graphic organizer with word bank."],
            advanced=["Compare MAIN factors to causes of a modern conflict."],
            ell=["Provide translated key terms in Spanish."],
        ),
        materials_needed=["MAIN graphic organizer", "Political cartoon handout", "Textbook"],
        time_estimates={
            "do_now": 5,
            "direct_instruction": 15,
            "guided_practice": 15,
            "independent_work": 10,
        },
    )


@pytest.fixture
def sample_persona() -> TeacherPersona:
    """A simple teacher persona for export tests."""
    return TeacherPersona(
        name="Ms. Rivera",
        subject_area="Social Studies",
        grade_levels=["8"],
    )


@pytest.fixture
def minimal_lesson() -> DailyLesson:
    """A DailyLesson with only required fields and minimal optional data."""
    return DailyLesson(
        title="Quick Lesson",
        lesson_number=1,
        objective="SWBAT understand the basics.",
    )


@pytest.fixture
def long_title_lesson() -> DailyLesson:
    """A DailyLesson with a very long title for edge-case testing."""
    return DailyLesson(
        title="A" * 200,
        lesson_number=99,
        objective="Test extremely long title handling.",
        do_now="Warm-up activity.",
        direct_instruction="Instruction content " * 50,
        guided_practice="Practice content.",
        independent_work="Work content.",
    )


# ── PPTX export ──────────────────────────────────────────────────────


class TestPPTXExport:
    def test_generates_pptx_file(self, sample_lesson, sample_persona, tmp_path):
        from eduagent.doc_export import export_lesson_pptx

        path = export_lesson_pptx(sample_lesson, sample_persona, output_dir=tmp_path)
        assert path.exists()
        assert path.suffix == ".pptx"

    def test_pptx_is_nonempty(self, sample_lesson, sample_persona, tmp_path):
        from eduagent.doc_export import export_lesson_pptx

        path = export_lesson_pptx(sample_lesson, sample_persona, output_dir=tmp_path)
        assert path.stat().st_size > 0

    def test_pptx_has_correct_slide_count(self, sample_lesson, sample_persona, tmp_path):
        from pptx import Presentation

        from eduagent.doc_export import export_lesson_pptx

        path = export_lesson_pptx(sample_lesson, sample_persona, output_dir=tmp_path)
        prs = Presentation(str(path))
        # Title + Objectives + DoNow + DirectInstruction + GuidedPractice
        # + IndependentWork + ExitTicket + Homework = 8 slides
        assert len(prs.slides) >= 5  # At minimum title + objectives + 3 sections

    def test_pptx_minimal_lesson(self, minimal_lesson, sample_persona, tmp_path):
        from eduagent.doc_export import export_lesson_pptx

        path = export_lesson_pptx(minimal_lesson, sample_persona, output_dir=tmp_path)
        assert path.exists()
        assert path.stat().st_size > 0

    def test_pptx_long_title(self, long_title_lesson, sample_persona, tmp_path):
        from eduagent.doc_export import export_lesson_pptx

        path = export_lesson_pptx(long_title_lesson, sample_persona, output_dir=tmp_path)
        assert path.exists()
        assert path.stat().st_size > 0


# ── DOCX export ──────────────────────────────────────────────────────


class TestDOCXExport:
    def test_generates_docx_file(self, sample_lesson, sample_persona, tmp_path):
        from eduagent.doc_export import export_lesson_docx

        path = export_lesson_docx(sample_lesson, sample_persona, output_dir=tmp_path)
        assert path.exists()
        assert path.suffix == ".docx"

    def test_docx_is_nonempty(self, sample_lesson, sample_persona, tmp_path):
        from eduagent.doc_export import export_lesson_docx

        path = export_lesson_docx(sample_lesson, sample_persona, output_dir=tmp_path)
        assert path.stat().st_size > 0

    def test_docx_contains_lesson_title(self, sample_lesson, sample_persona, tmp_path):
        from docx import Document

        from eduagent.doc_export import export_lesson_docx

        path = export_lesson_docx(sample_lesson, sample_persona, output_dir=tmp_path)
        doc = Document(str(path))
        full_text = "\n".join(p.text for p in doc.paragraphs)
        assert "Causes of World War I" in full_text

    def test_docx_minimal_lesson(self, minimal_lesson, sample_persona, tmp_path):
        from eduagent.doc_export import export_lesson_docx

        path = export_lesson_docx(minimal_lesson, sample_persona, output_dir=tmp_path)
        assert path.exists()
        assert path.stat().st_size > 0

    def test_docx_long_title(self, long_title_lesson, sample_persona, tmp_path):
        from eduagent.doc_export import export_lesson_docx

        path = export_lesson_docx(long_title_lesson, sample_persona, output_dir=tmp_path)
        assert path.exists()
        assert path.stat().st_size > 0


# ── PDF export ────────────────────────────────────────────────────────


class TestPDFExport:
    def test_generates_pdf_file(self, sample_lesson, sample_persona, tmp_path):
        from eduagent.doc_export import export_lesson_pdf

        path = export_lesson_pdf(sample_lesson, sample_persona, output_dir=tmp_path)
        assert path.exists()
        assert path.suffix == ".pdf"

    def test_pdf_is_nonempty(self, sample_lesson, sample_persona, tmp_path):
        from eduagent.doc_export import export_lesson_pdf

        path = export_lesson_pdf(sample_lesson, sample_persona, output_dir=tmp_path)
        assert path.stat().st_size > 0

    def test_pdf_minimal_lesson(self, minimal_lesson, sample_persona, tmp_path):
        from eduagent.doc_export import export_lesson_pdf

        path = export_lesson_pdf(minimal_lesson, sample_persona, output_dir=tmp_path)
        assert path.exists()
        assert path.stat().st_size > 0

    def test_pdf_long_title(self, long_title_lesson, sample_persona, tmp_path):
        from eduagent.doc_export import export_lesson_pdf

        path = export_lesson_pdf(long_title_lesson, sample_persona, output_dir=tmp_path)
        assert path.exists()
        assert path.stat().st_size > 0
