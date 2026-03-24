"""Document export — generate PPTX, DOCX, and PDF from lesson plans.

Uses python-pptx for PowerPoint and python-docx for Word documents,
both of which are already project dependencies.  PDF is generated
from the DOCX via reportlab (also a dependency).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from eduagent.models import DailyLesson, TeacherPersona

logger = logging.getLogger(__name__)


# ── Color theme definitions ───────────────────────────────────────────

_COLOR_THEMES: dict[str, dict[str, str]] = {
    "history": {
        "primary": "8B4513",       # brown
        "secondary": "DAA520",     # gold
        "accent": "5C3317",        # dark brown
        "bg_light": "FFF8F0",      # cream
        "text_dark": "3E2723",     # deep brown
        "text_light": "FFFFFF",
    },
    "social studies": {
        "primary": "8B4513",
        "secondary": "DAA520",
        "accent": "5C3317",
        "bg_light": "FFF8F0",
        "text_dark": "3E2723",
        "text_light": "FFFFFF",
    },
    "science": {
        "primary": "2E8B57",       # sea green
        "secondary": "4682B4",     # steel blue
        "accent": "1B5E20",        # dark green
        "bg_light": "F0F8F5",      # mint
        "text_dark": "1B3A2D",
        "text_light": "FFFFFF",
    },
    "biology": {
        "primary": "2E8B57",
        "secondary": "4682B4",
        "accent": "1B5E20",
        "bg_light": "F0F8F5",
        "text_dark": "1B3A2D",
        "text_light": "FFFFFF",
    },
    "chemistry": {
        "primary": "2E8B57",
        "secondary": "4682B4",
        "accent": "1B5E20",
        "bg_light": "F0F8F5",
        "text_dark": "1B3A2D",
        "text_light": "FFFFFF",
    },
    "physics": {
        "primary": "2E8B57",
        "secondary": "4682B4",
        "accent": "1B5E20",
        "bg_light": "F0F8F5",
        "text_dark": "1B3A2D",
        "text_light": "FFFFFF",
    },
    "math": {
        "primary": "1E3A5F",       # navy
        "secondary": "4A90D9",     # blue
        "accent": "0D47A1",        # dark blue
        "bg_light": "F0F4FA",      # light blue
        "text_dark": "1A2A3A",
        "text_light": "FFFFFF",
    },
    "mathematics": {
        "primary": "1E3A5F",
        "secondary": "4A90D9",
        "accent": "0D47A1",
        "bg_light": "F0F4FA",
        "text_dark": "1A2A3A",
        "text_light": "FFFFFF",
    },
    "algebra": {
        "primary": "1E3A5F",
        "secondary": "4A90D9",
        "accent": "0D47A1",
        "bg_light": "F0F4FA",
        "text_dark": "1A2A3A",
        "text_light": "FFFFFF",
    },
    "ela": {
        "primary": "4A235A",       # purple
        "secondary": "7B1FA2",     # medium purple
        "accent": "311B92",        # deep purple
        "bg_light": "F5F0FA",      # lavender
        "text_dark": "2C1338",
        "text_light": "FFFFFF",
    },
    "english": {
        "primary": "4A235A",
        "secondary": "7B1FA2",
        "accent": "311B92",
        "bg_light": "F5F0FA",
        "text_dark": "2C1338",
        "text_light": "FFFFFF",
    },
    "language arts": {
        "primary": "4A235A",
        "secondary": "7B1FA2",
        "accent": "311B92",
        "bg_light": "F5F0FA",
        "text_dark": "2C1338",
        "text_light": "FFFFFF",
    },
}

_DEFAULT_THEME: dict[str, str] = {
    "primary": "1A365D",       # professional dark blue
    "secondary": "2B6CB0",     # medium blue
    "accent": "153E75",        # deep blue
    "bg_light": "F0F4FA",      # soft blue-white
    "text_dark": "1A202C",
    "text_light": "FFFFFF",
}


def get_color_theme(subject: str) -> dict[str, str]:
    """Return the color theme dict for a subject, or the default."""
    return _COLOR_THEMES.get(subject.strip().lower(), _DEFAULT_THEME)


# ── PowerPoint export ──────────────────────────────────────────────────


def _detect_subject(persona: "TeacherPersona") -> str:
    """Best-effort subject detection from persona fields."""
    subj = (persona.subject_area or "").strip().lower()
    if subj:
        return subj
    return ""


def _hex_to_rgb(hex_str: str):
    """Convert a hex color string to an RGBColor."""
    from pptx.dml.color import RGBColor

    return RGBColor(int(hex_str[:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))


def _add_shape_fill(shape, hex_color: str) -> None:
    """Fill a shape with a solid color."""
    fill = shape.fill
    fill.solid()
    fill.fore_color.rgb = _hex_to_rgb(hex_color)


def _set_text_props(run, font_size_pt: int, hex_color: str, bold: bool = False):
    """Set font properties on a text run."""
    from pptx.util import Pt

    run.font.size = Pt(font_size_pt)
    run.font.color.rgb = _hex_to_rgb(hex_color)
    run.font.bold = bold
    run.font.name = "Calibri"


def _try_fetch_images(topics: list[tuple[str, str]], subject: str) -> dict[str, Optional[Path]]:
    """Attempt to fetch images for multiple topics. Non-blocking, short timeout.

    Returns a dict mapping key -> Path | None.
    """
    from eduagent.slide_images import fetch_slide_image

    results: dict[str, Optional[Path]] = {}

    async def _fetch_all():
        for topic, key in topics:
            try:
                path = await asyncio.wait_for(
                    fetch_slide_image(topic, subject=subject),
                    timeout=5.0,
                )
                results[key] = path
            except Exception:
                results[key] = None

    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, _fetch_all())
                future.result(timeout=30)
        else:
            asyncio.run(_fetch_all())
    except Exception as e:
        logger.debug("Image fetching failed: %s", e)

    return results


def export_lesson_pptx(
    lesson: "DailyLesson",
    persona: "TeacherPersona",
    output_dir: Path | None = None,
) -> Path:
    """Generate a professional PowerPoint presentation from a lesson plan.

    Produces slides with subject-themed colors, proper typography, optional
    images (fetched from Unsplash when configured), and a polished layout.

    Returns the path to the saved .pptx file.
    """
    from pptx import Presentation
    from pptx.enum.text import PP_ALIGN
    from pptx.util import Emu, Inches, Pt

    subject = _detect_subject(persona)
    theme = get_color_theme(subject)

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    SLIDE_W = prs.slide_width
    SLIDE_H = prs.slide_height

    # ── Try to fetch images asynchronously ────────────────────────────
    image_topics: list[tuple[str, str]] = [(lesson.title, "title")]
    content_sections = [
        ("do_now", "Do Now", lesson.do_now),
        ("instruction", "Direct Instruction", lesson.direct_instruction),
        ("practice", "Guided Practice", lesson.guided_practice),
        ("independent", "Independent Work", lesson.independent_work),
    ]
    for key, _label, content in content_sections:
        if content:
            image_topics.append((_label + " " + lesson.title, key))

    images = _try_fetch_images(image_topics, subject)

    # ── Slide counter for footer ──────────────────────────────────────
    slide_num = [0]

    def _next_slide():
        """Get a blank slide layout and increment counter."""
        slide_num[0] += 1
        layout = prs.slide_layouts[6]  # blank layout
        return prs.slides.add_slide(layout)

    def _add_footer(slide, num: int):
        """Add slide number footer."""
        left = SLIDE_W - Inches(1.5)
        top = SLIDE_H - Inches(0.45)
        tb = slide.shapes.add_textbox(left, top, Inches(1.2), Inches(0.3))
        tf = tb.text_frame
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.RIGHT
        run = p.add_run()
        run.text = f"Slide {num}"
        _set_text_props(run, 10, "999999")

    def _add_accent_bar(slide, left, top, width, height, hex_color: str):
        """Add a colored rectangle accent bar."""
        shape = slide.shapes.add_shape(
            1,  # MSO_SHAPE.RECTANGLE
            left, top, width, height,
        )
        shape.line.fill.background()
        _add_shape_fill(shape, hex_color)
        return shape

    def _add_bg_image(slide, image_path: Path):
        """Add a full-slide background image with semi-transparent overlay."""
        pic = slide.shapes.add_picture(
            str(image_path), Emu(0), Emu(0), SLIDE_W, SLIDE_H,
        )
        # Move picture to back of shape tree
        sp = pic._element
        sp.getparent().remove(sp)
        slide.shapes._spTree.insert(2, sp)

        # Semi-transparent overlay for text readability
        from pptx.oxml.ns import qn

        overlay = slide.shapes.add_shape(
            1, Emu(0), Emu(0), SLIDE_W, SLIDE_H,
        )
        overlay.line.fill.background()
        fill_obj = overlay.fill
        fill_obj.solid()
        fill_obj.fore_color.rgb = _hex_to_rgb(theme["primary"])
        solid_fill = overlay._element.spPr.solidFill
        if solid_fill is not None:
            srgb = solid_fill.find(qn("a:srgbClr"))
            if srgb is None:
                srgb = solid_fill.find(qn("a:sysClr"))
            if srgb is not None:
                from lxml import etree

                alpha = etree.SubElement(srgb, qn("a:alpha"))
                alpha.set("val", "40000")  # 40% opacity

    def _add_sidebar_image(slide, image_path: Path):
        """Add an image in the right 30% of the slide as a sidebar."""
        img_left = int(SLIDE_W * 0.70)
        img_width = int(SLIDE_W * 0.28)
        img_top = Inches(1.2)
        img_height = int(SLIDE_H - Inches(1.8))
        try:
            slide.shapes.add_picture(
                str(image_path), img_left, img_top, img_width, img_height,
            )
        except Exception:
            pass  # Skip silently if image is corrupt

    # ── TITLE SLIDE ───────────────────────────────────────────────────
    slide = _next_slide()

    title_image = images.get("title")
    if title_image:
        _add_bg_image(slide, title_image)
        title_color = theme["text_light"]
        subtitle_color = "DDDDDD"
    else:
        bg = slide.background
        fill = bg.fill
        fill.solid()
        fill.fore_color.rgb = _hex_to_rgb(theme["primary"])
        title_color = theme["text_light"]
        subtitle_color = "CCCCCC"

    # Title text
    tb = slide.shapes.add_textbox(
        Inches(1.0), Inches(2.0), SLIDE_W - Inches(2.0), Inches(2.5),
    )
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    run = p.add_run()
    run.text = lesson.title
    _set_text_props(run, 44, title_color, bold=True)

    # Subtitle
    tb2 = slide.shapes.add_textbox(
        Inches(1.0), Inches(4.8), SLIDE_W - Inches(2.0), Inches(1.5),
    )
    tf2 = tb2.text_frame
    tf2.word_wrap = True
    p2 = tf2.paragraphs[0]
    p2.alignment = PP_ALIGN.LEFT
    run2 = p2.add_run()
    run2.text = (
        f"{persona.name or 'Teacher'}  |  "
        f"{date.today().strftime('%B %d, %Y')}  |  "
        f"Lesson {lesson.lesson_number}"
    )
    _set_text_props(run2, 22, subtitle_color)

    # Accent line under title
    _add_accent_bar(
        slide, Inches(1.0), Inches(4.55),
        Inches(3.0), Inches(0.06), theme["secondary"],
    )

    _add_footer(slide, slide_num[0])

    # ── OBJECTIVES SLIDE ──────────────────────────────────────────────
    slide = _next_slide()

    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = _hex_to_rgb("FFFFFF")

    # Title bar
    _add_accent_bar(
        slide, Emu(0), Emu(0), SLIDE_W, Inches(1.1), theme["primary"],
    )
    tb = slide.shapes.add_textbox(
        Inches(0.8), Inches(0.15), SLIDE_W - Inches(1.6), Inches(0.8),
    )
    tf = tb.text_frame
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = "Learning Objectives"
    _set_text_props(run, 32, theme["text_light"], bold=True)

    # Objective with checkmark
    obj_top = Inches(1.5)
    tb = slide.shapes.add_textbox(
        Inches(1.0), obj_top, SLIDE_W - Inches(2.0), Inches(1.5),
    )
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.space_after = Pt(12)
    run = p.add_run()
    run.text = f"SWBAT: {lesson.objective}"
    _set_text_props(run, 22, theme["text_dark"])

    # Standards in smaller text
    if lesson.standards:
        stds_top = Inches(3.5)
        tb = slide.shapes.add_textbox(
            Inches(1.0), stds_top, SLIDE_W - Inches(2.0), Inches(3.0),
        )
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        run = p.add_run()
        run.text = "Standards Addressed"
        _set_text_props(run, 16, "666666", bold=True)

        for std in lesson.standards[:5]:
            p = tf.add_paragraph()
            p.space_before = Pt(4)
            run = p.add_run()
            run.text = f"  {std}"
            _set_text_props(run, 15, "555555")

    _add_footer(slide, slide_num[0])

    # ── CONTENT SLIDE BUILDER ─────────────────────────────────────────

    def _build_content_slide(title: str, body_text: str, image_key: str = ""):
        """Build a professional content slide with optional sidebar image."""
        slide = _next_slide()

        bg = slide.background
        fill = bg.fill
        fill.solid()
        fill.fore_color.rgb = _hex_to_rgb("FFFFFF")

        # Top accent bar
        _add_accent_bar(
            slide, Emu(0), Emu(0), SLIDE_W, Inches(1.1), theme["primary"],
        )

        # Title
        tb = slide.shapes.add_textbox(
            Inches(0.8), Inches(0.15), SLIDE_W - Inches(1.6), Inches(0.8),
        )
        tf = tb.text_frame
        p = tf.paragraphs[0]
        run = p.add_run()
        run.text = title
        _set_text_props(run, 32, theme["text_light"], bold=True)

        # Side accent bar
        _add_accent_bar(
            slide, Inches(0.6), Inches(1.5),
            Inches(0.08), Inches(5.0), theme["secondary"],
        )

        # Check if image is available for sidebar
        img_path = images.get(image_key) if image_key else None
        text_width = SLIDE_W - Inches(2.0)
        if img_path:
            text_width = int(SLIDE_W * 0.63)
            _add_sidebar_image(slide, img_path)

        # Body text
        tb = slide.shapes.add_textbox(
            Inches(1.0), Inches(1.5), text_width, Inches(5.2),
        )
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.line_spacing = Pt(26)  # ~1.3 line spacing for 18pt
        run = p.add_run()
        run.text = body_text
        _set_text_props(run, 18, theme["text_dark"])

        _add_footer(slide, slide_num[0])
        return slide

    # ── DO NOW ────────────────────────────────────────────────────────
    if lesson.do_now:
        _build_content_slide("Do Now / Warm-Up", lesson.do_now, image_key="do_now")

    # ── DIRECT INSTRUCTION ────────────────────────────────────────────
    if lesson.direct_instruction:
        text = lesson.direct_instruction
        if len(text) > 600:
            chunks = _split_text(text, max_len=550)
            for i, chunk in enumerate(chunks, 1):
                suffix = f" ({i}/{len(chunks)})" if len(chunks) > 1 else ""
                _build_content_slide(
                    f"Direct Instruction{suffix}", chunk,
                    image_key="instruction" if i == 1 else "",
                )
        else:
            _build_content_slide("Direct Instruction", text, image_key="instruction")

    # ── GUIDED PRACTICE ───────────────────────────────────────────────
    if lesson.guided_practice:
        _build_content_slide("Guided Practice", lesson.guided_practice, image_key="practice")

    # ── INDEPENDENT WORK ──────────────────────────────────────────────
    if lesson.independent_work:
        _build_content_slide(
            "Independent Work / Practice", lesson.independent_work,
            image_key="independent",
        )

    # ── EXIT TICKET ───────────────────────────────────────────────────
    if lesson.exit_ticket:
        slide = _next_slide()

        bg = slide.background
        fill = bg.fill
        fill.solid()
        fill.fore_color.rgb = _hex_to_rgb("FFFFFF")

        _add_accent_bar(
            slide, Emu(0), Emu(0), SLIDE_W, Inches(1.1), theme["primary"],
        )
        tb = slide.shapes.add_textbox(
            Inches(0.8), Inches(0.15), SLIDE_W - Inches(1.6), Inches(0.8),
        )
        tf = tb.text_frame
        p = tf.paragraphs[0]
        run = p.add_run()
        run.text = "Exit Ticket"
        _set_text_props(run, 32, theme["text_light"], bold=True)

        # Questions as numbered cards
        q_top = Inches(1.5)
        for i, q in enumerate(lesson.exit_ticket, 1):
            card = slide.shapes.add_shape(
                1,
                Inches(1.0), q_top, SLIDE_W - Inches(2.0), Inches(1.0),
            )
            card.line.fill.background()
            _add_shape_fill(card, theme["bg_light"])

            circle = slide.shapes.add_shape(
                9,  # MSO_SHAPE.OVAL
                Inches(1.3), q_top + Inches(0.15),
                Inches(0.7), Inches(0.7),
            )
            circle.line.fill.background()
            _add_shape_fill(circle, theme["secondary"])
            circle.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
            run = circle.text_frame.paragraphs[0].add_run()
            run.text = str(i)
            _set_text_props(run, 20, theme["text_light"], bold=True)

            tb = slide.shapes.add_textbox(
                Inches(2.3), q_top + Inches(0.15),
                SLIDE_W - Inches(3.5), Inches(0.7),
            )
            tf = tb.text_frame
            tf.word_wrap = True
            run = tf.paragraphs[0].add_run()
            run.text = q.question
            _set_text_props(run, 18, theme["text_dark"])

            q_top += Inches(1.2)

        _add_footer(slide, slide_num[0])

    # ── CLOSING SLIDE ─────────────────────────────────────────────────
    slide = _next_slide()

    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = _hex_to_rgb(theme["primary"])

    if lesson.homework:
        tb = slide.shapes.add_textbox(
            Inches(1.0), Inches(1.5), SLIDE_W - Inches(2.0), Inches(1.5),
        )
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT
        run = p.add_run()
        run.text = "Homework"
        _set_text_props(run, 36, theme["text_light"], bold=True)

        _add_accent_bar(
            slide, Inches(1.0), Inches(3.0),
            Inches(3.0), Inches(0.06), theme["secondary"],
        )

        tb = slide.shapes.add_textbox(
            Inches(1.0), Inches(3.3), SLIDE_W - Inches(2.0), Inches(3.0),
        )
        tf = tb.text_frame
        tf.word_wrap = True
        run = tf.paragraphs[0].add_run()
        run.text = lesson.homework
        _set_text_props(run, 22, "DDDDDD")
    else:
        tb = slide.shapes.add_textbox(
            Inches(1.0), Inches(2.5), SLIDE_W - Inches(2.0), Inches(2.0),
        )
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        run = p.add_run()
        run.text = "Questions?"
        _set_text_props(run, 48, theme["text_light"], bold=True)

    # Footer with teacher name
    tb = slide.shapes.add_textbox(
        Inches(1.0), SLIDE_H - Inches(1.0),
        SLIDE_W - Inches(2.0), Inches(0.5),
    )
    tf = tb.text_frame
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = f"{persona.name or 'Teacher'}  |  Generated by EDUagent"
    _set_text_props(run, 12, "AAAAAA")

    _add_footer(slide, slide_num[0])

    # ── Save ──────────────────────────────────────────────────────────
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
