"""Document export — generate PPTX, DOCX, and PDF from lesson plans.

Uses python-pptx for PowerPoint and python-docx for Word documents,
both of which are already project dependencies.  PDF is generated
from the DOCX via reportlab (also a dependency).
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from eduagent.models import DailyLesson, TeacherPersona

logger = logging.getLogger(__name__)


# ── PowerPoint export ──────────────────────────────────────────────────


def export_lesson_pptx(
    lesson: "DailyLesson",
    persona: "TeacherPersona",
    output_dir: Path | None = None,
) -> Path:
    """Generate a PowerPoint presentation from a lesson plan.

    Returns the path to the saved .pptx file.
    """
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.enum.text import PP_ALIGN

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    def _add_slide(title: str, body: str, layout_idx: int = 1):
        """Add a slide with a title and body text."""
        layout = prs.slide_layouts[layout_idx]
        slide = prs.slides.add_slide(layout)
        slide.shapes.title.text = title
        tf = slide.placeholders[1].text_frame
        tf.text = body
        for para in tf.paragraphs:
            para.font.size = Pt(18)
        return slide

    # Title slide
    title_layout = prs.slide_layouts[0]
    title_slide = prs.slides.add_slide(title_layout)
    title_slide.shapes.title.text = lesson.title
    subtitle = title_slide.placeholders[1]
    subtitle.text = (
        f"{persona.name or 'Teacher'}\n"
        f"{date.today().strftime('%B %d, %Y')}\n"
        f"Lesson {lesson.lesson_number}"
    )

    # Objectives slide
    objectives_text = f"SWBAT: {lesson.objective}"
    if lesson.standards:
        objectives_text += "\n\nStandards:\n" + "\n".join(
            f"  - {s}" for s in lesson.standards[:5]
        )
    _add_slide("Learning Objectives", objectives_text)

    # Do Now / Warm-up
    if lesson.do_now:
        _add_slide("Do Now / Warm-Up", lesson.do_now)

    # Direct Instruction — split into chunks if long
    if lesson.direct_instruction:
        text = lesson.direct_instruction
        if len(text) > 600:
            # Split into multiple slides
            chunks = _split_text(text, max_len=550)
            for i, chunk in enumerate(chunks, 1):
                suffix = f" ({i}/{len(chunks)})" if len(chunks) > 1 else ""
                _add_slide(f"Direct Instruction{suffix}", chunk)
        else:
            _add_slide("Direct Instruction", text)

    # Guided Practice
    if lesson.guided_practice:
        _add_slide("Guided Practice", lesson.guided_practice)

    # Independent Work
    if lesson.independent_work:
        _add_slide("Independent Work / Practice", lesson.independent_work)

    # Exit Ticket
    if lesson.exit_ticket:
        et_text = "\n".join(
            f"{i}. {q.question}" for i, q in enumerate(lesson.exit_ticket, 1)
        )
        _add_slide("Exit Ticket", et_text)

    # Homework (if any)
    if lesson.homework:
        _add_slide("Homework", lesson.homework)

    # Save
    out = _resolve_output(output_dir, lesson, ".pptx")
    prs.save(str(out))
    return out


# ── Word document export ───────────────────────────────────────────────


def export_lesson_docx(
    lesson: "DailyLesson",
    persona: "TeacherPersona",
    output_dir: Path | None = None,
) -> Path:
    """Generate a Word document from a lesson plan.

    Returns the path to the saved .docx file.
    """
    from docx import Document
    from docx.shared import Inches, Pt

    doc = Document()

    # Title
    title_para = doc.add_heading(lesson.title, level=0)
    doc.add_paragraph(
        f"Teacher: {persona.name or 'Teacher'}  |  "
        f"Lesson {lesson.lesson_number}  |  "
        f"{date.today().strftime('%B %d, %Y')}"
    )

    # Standards table
    if lesson.standards:
        doc.add_heading("Standards Addressed", level=2)
        table = doc.add_table(rows=1, cols=1)
        table.style = "Light Grid Accent 1"
        hdr = table.rows[0].cells
        hdr[0].text = "Standard"
        for std in lesson.standards:
            row = table.add_row().cells
            row[0].text = std

    # Objective
    doc.add_heading("Objective (SWBAT)", level=2)
    doc.add_paragraph(lesson.objective)

    # Materials
    if lesson.materials_needed:
        doc.add_heading("Materials Needed", level=2)
        for m in lesson.materials_needed:
            doc.add_paragraph(m, style="List Bullet")

    # Lesson Sections
    sections = [
        ("Do Now / Warm-Up", lesson.do_now),
        ("Direct Instruction", lesson.direct_instruction),
        ("Guided Practice", lesson.guided_practice),
        ("Independent Work", lesson.independent_work),
    ]
    for heading, content in sections:
        if content:
            time_key = heading.lower().replace(" / warm-up", "").replace(" ", "_")
            minutes = lesson.time_estimates.get(time_key, "")
            time_label = f" ({minutes} min)" if minutes else ""
            doc.add_heading(f"{heading}{time_label}", level=2)
            doc.add_paragraph(content)

    # Exit Ticket
    if lesson.exit_ticket:
        doc.add_heading("Exit Ticket", level=2)
        for i, q in enumerate(lesson.exit_ticket, 1):
            doc.add_paragraph(f"{i}. {q.question}")

    # Differentiation
    diff = lesson.differentiation
    if diff:
        doc.add_heading("Differentiation", level=2)
        if diff.struggling:
            doc.add_paragraph(f"Struggling learners: {diff.struggling}")
        if diff.advanced:
            doc.add_paragraph(f"Advanced learners: {diff.advanced}")
        if diff.ell:
            doc.add_paragraph(f"ELL support: {diff.ell}")

    # Homework
    if lesson.homework:
        doc.add_heading("Homework", level=2)
        doc.add_paragraph(lesson.homework)

    # Footer
    doc.add_paragraph("")
    footer = doc.add_paragraph("Generated by EDUagent")
    footer.runs[0].font.size = Pt(8)

    out = _resolve_output(output_dir, lesson, ".docx")
    doc.save(str(out))
    return out


# ── PDF export ─────────────────────────────────────────────────────────


def export_lesson_pdf(
    lesson: "DailyLesson",
    persona: "TeacherPersona",
    output_dir: Path | None = None,
) -> Path:
    """Generate a PDF from a lesson plan via reportlab.

    Returns the path to the saved .pdf file.
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    out = _resolve_output(output_dir, lesson, ".pdf")

    doc = SimpleDocTemplate(
        str(out),
        pagesize=letter,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=1 * inch,
        rightMargin=1 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "LessonTitle",
        parent=styles["Title"],
        fontSize=20,
        spaceAfter=6,
    )
    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=14,
        spaceBefore=12,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=11,
        leading=15,
        spaceAfter=6,
    )
    meta_style = ParagraphStyle(
        "Meta",
        parent=styles["Normal"],
        fontSize=9,
        textColor="#555555",
        spaceAfter=12,
    )

    story = []

    # Title
    story.append(Paragraph(_esc(lesson.title), title_style))
    story.append(
        Paragraph(
            _esc(
                f"Teacher: {persona.name or 'Teacher'}  |  "
                f"Lesson {lesson.lesson_number}  |  "
                f"{date.today().strftime('%B %d, %Y')}"
            ),
            meta_style,
        )
    )

    # Objective
    story.append(Paragraph("Objective (SWBAT)", heading_style))
    story.append(Paragraph(_esc(lesson.objective), body_style))

    # Standards
    if lesson.standards:
        story.append(Paragraph("Standards", heading_style))
        for s in lesson.standards:
            story.append(Paragraph(f"- {_esc(s)}", body_style))

    # Sections
    sections = [
        ("Do Now / Warm-Up", lesson.do_now),
        ("Direct Instruction", lesson.direct_instruction),
        ("Guided Practice", lesson.guided_practice),
        ("Independent Work", lesson.independent_work),
    ]
    for heading, content in sections:
        if content:
            story.append(Paragraph(_esc(heading), heading_style))
            story.append(Paragraph(_esc(content), body_style))

    # Exit Ticket
    if lesson.exit_ticket:
        story.append(Paragraph("Exit Ticket", heading_style))
        for i, q in enumerate(lesson.exit_ticket, 1):
            story.append(Paragraph(f"{i}. {_esc(q.question)}", body_style))

    # Homework
    if lesson.homework:
        story.append(Paragraph("Homework", heading_style))
        story.append(Paragraph(_esc(lesson.homework), body_style))

    # Footer
    story.append(Spacer(1, 24))
    footer_style = ParagraphStyle(
        "Footer", parent=styles["Normal"], fontSize=8, textColor="#888888"
    )
    story.append(Paragraph("Generated by EDUagent", footer_style))

    doc.build(story)
    return out


# ── Helpers ────────────────────────────────────────────────────────────


def _resolve_output(output_dir: Path | None, lesson: "DailyLesson", ext: str) -> Path:
    """Build the output file path."""
    if output_dir is None:
        output_dir = Path("eduagent_output").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    safe = f"lesson_{lesson.lesson_number:02d}"
    return output_dir / f"{safe}{ext}"


def _split_text(text: str, max_len: int = 550) -> list[str]:
    """Split long text into chunks at sentence boundaries."""
    sentences = text.replace("\n", " ").split(". ")
    chunks: list[str] = []
    current = ""
    for s in sentences:
        candidate = f"{current}. {s}" if current else s
        if len(candidate) > max_len and current:
            chunks.append(current.strip())
            current = s
        else:
            current = candidate
    if current.strip():
        chunks.append(current.strip())
    return chunks or [text]


def _esc(text: str) -> str:
    """Escape text for reportlab XML-based Paragraphs."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
