"""PowerPoint (PPTX) export for lesson plans.

Generates professional, subject-themed slide decks with academic images.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from clawed.async_utils import run_async_safe
from clawed.export_theme import _hex_to_rgb, _resolve_output, get_color_theme

if TYPE_CHECKING:
    from clawed.models import DailyLesson, TeacherPersona

logger = logging.getLogger(__name__)


# ── PPTX helpers ──────────────────────────────────────────────────────


def _detect_subject(persona: "TeacherPersona") -> str:
    """Best-effort subject detection from persona fields."""
    subj = (persona.subject_area or "").strip().lower()
    if subj:
        return subj
    return ""


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


def _section_divider(prs, slide_num, text, theme, slide_w, slide_h):
    """Create a clean section divider slide with accent background."""
    from pptx.enum.text import PP_ALIGN
    from pptx.util import Inches, Pt

    slide_num[0] += 1
    layout = prs.slide_layouts[6]  # blank layout
    slide = prs.slides.add_slide(layout)

    # Accent background
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = _hex_to_rgb(theme["accent"])

    # Large centered text
    tb = slide.shapes.add_textbox(
        Inches(1.5), Inches(2.5), slide_w - Inches(3.0), Inches(2.5),
    )
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = text
    run.font.size = Pt(44)
    run.font.color.rgb = _hex_to_rgb(theme["primary"])
    run.font.bold = True
    run.font.name = "Calibri"

    # Footer with slide number
    left = slide_w - Inches(1.5)
    top = slide_h - Inches(0.45)
    tb_footer = slide.shapes.add_textbox(left, top, Inches(1.2), Inches(0.3))
    p_f = tb_footer.text_frame.paragraphs[0]
    p_f.alignment = PP_ALIGN.RIGHT
    run_f = p_f.add_run()
    run_f.text = str(slide_num[0])
    _set_text_props(run_f, 10, "999999")


# ── Image fetching ────────────────────────────────────────────────────


def _try_fetch_images(topics: list[tuple[str, str]], subject: str) -> dict[str, Optional[Path]]:
    """Attempt to fetch images for multiple topics. Non-blocking, short timeout.

    Returns a dict mapping key -> Path | None.
    """
    from clawed.slide_images import fetch_slide_image

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
        run_async_safe(_fetch_all())
    except Exception as e:
        logger.debug("Image fetching failed: %s", e)

    return results


def _try_fetch_content_images(
    items: list[tuple[str, str, str]],
    subject: str,
    max_images: int = 4,
) -> dict[str, Optional[Path]]:
    """Fetch images based on slide *content* text, not just the lesson title.

    Each item is ``(content_text, fallback_topic, key)``.  Stops after
    ``max_images`` successful fetches to avoid slowing down generation.

    Returns a dict mapping key -> Path | None.
    """
    from clawed.slide_images import fetch_content_image, fetch_slide_image

    results: dict[str, Optional[Path]] = {}

    async def _fetch_all():
        found = 0
        for content_text, fallback_topic, key in items:
            if found >= max_images:
                results[key] = None
                continue
            try:
                if content_text:
                    path = await asyncio.wait_for(
                        fetch_content_image(
                            content_text,
                            subject=subject,
                            fallback_topic=fallback_topic,
                        ),
                        timeout=5.0,
                    )
                else:
                    # Title slide: use topic-based search
                    path = await asyncio.wait_for(
                        fetch_slide_image(fallback_topic, subject=subject),
                        timeout=5.0,
                    )
                results[key] = path
                if path:
                    found += 1
            except Exception:
                results[key] = None

    try:
        run_async_safe(_fetch_all())
    except Exception as e:
        logger.debug("Content image fetching failed: %s", e)

    return results


# ── Main export function ──────────────────────────────────────────────


def export_lesson_pptx(
    lesson: "DailyLesson",
    persona: "TeacherPersona",
    output_dir: Path | None = None,
    agent_name: str = "Claw-ED",
    include_images: bool = True,
) -> Path:
    """Generate a professional PowerPoint presentation from a lesson plan.

    Produces a polished, school-board-ready slide deck with:
    - Subject-themed color palette
    - Large readable fonts for projection on classroom screens
    - Academic images (LOC, Wikimedia, Unsplash) where available
    - Clean, modern, minimal design -- NOT busy or cluttered
    - Consistent visual language throughout

    Returns the path to the saved .pptx file.
    """
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import PP_ALIGN
    from pptx.util import Emu, Inches, Pt

    from clawed.sanitize import sanitize_text

    # Sanitize all lesson text fields before rendering to slides
    lesson.title = sanitize_text(lesson.title)
    lesson.objective = sanitize_text(lesson.objective)
    lesson.do_now = sanitize_text(lesson.do_now) if lesson.do_now else ""
    lesson.direct_instruction = sanitize_text(lesson.direct_instruction) if lesson.direct_instruction else ""
    lesson.guided_practice = sanitize_text(lesson.guided_practice) if lesson.guided_practice else ""
    lesson.independent_work = sanitize_text(lesson.independent_work) if lesson.independent_work else ""
    if lesson.homework:
        lesson.homework = sanitize_text(lesson.homework)
    for q in lesson.exit_ticket:
        q.question = sanitize_text(q.question)
        q.expected_response = sanitize_text(q.expected_response)
    lesson.standards = [sanitize_text(s) for s in lesson.standards]
    lesson.materials_needed = [sanitize_text(m) for m in lesson.materials_needed]

    # Resolve teacher display name
    teacher_display_name = ""
    if persona and persona.name and persona.name != "My Teaching Persona":
        teacher_display_name = persona.name
    else:
        try:
            from clawed.models import AppConfig as _AppConfig
            _cfg = _AppConfig.load()
            if _cfg.teacher_profile and _cfg.teacher_profile.name:
                teacher_display_name = _cfg.teacher_profile.name
        except Exception:
            pass
    if not teacher_display_name:
        teacher_display_name = "Teacher"

    subject = _detect_subject(persona)
    theme = get_color_theme(subject)

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    slide_w = prs.slide_width
    slide_h = prs.slide_height

    # ── Try to fetch images asynchronously (entity-based queries) ────
    # Extracts named entities (people, places, documents) from lesson content
    # and searches for those specifically. Up to 5 images per deck.
    # Images on: Title (bg), Do Now (accent), Direct Instruction (sidebar)
    # No images on: Objectives, Guided Practice, Exit Ticket, Closing
    if include_images:
        from clawed.slide_images import extract_image_subjects
        entities = extract_image_subjects(lesson)
        image_items: list[tuple[str, str, str]] = []
        for i, entity in enumerate(entities[:5]):
            key = f"entity_{i}"
            image_items.append((entity["query"], entity["query"], key))

        # Ensure we have at least a title image
        if not image_items:
            image_items = [("", lesson.title, "title")]

        images = _try_fetch_content_images(image_items, subject, max_images=5)
        logger.info(
            "Image fetch: %d items requested, %d returned",
            len(image_items),
            len([v for v in images.values() if v]),
        )
    else:
        images = {}
        logger.info("Generating PPTX with include_images=%s", include_images)

    # ── Shared layout helpers ─────────────────────────────────────────
    slide_num = [0]

    def _next_slide():
        slide_num[0] += 1
        layout = prs.slide_layouts[6]  # blank layout
        return prs.slides.add_slide(layout)

    def _add_footer(slide, num: int):
        left = slide_w - Inches(1.5)
        top = slide_h - Inches(0.45)
        tb = slide.shapes.add_textbox(left, top, Inches(1.2), Inches(0.3))
        p = tb.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.RIGHT
        run = p.add_run()
        run.text = str(num)
        _set_text_props(run, 10, "999999")

    def _bar(slide, left, top, width, height, hex_color: str):
        shape = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, left, top, width, height,
        )
        shape.line.fill.background()
        _add_shape_fill(shape, hex_color)
        return shape

    def _rounded_card(slide, left, top, width, height, hex_color: str):
        shape = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height,
        )
        shape.line.fill.background()
        _add_shape_fill(shape, hex_color)
        # Subtle shadow
        try:
            shape.shadow.inherit = False
            shadow = shape.shadow
            shadow.visible = True
            shadow.blur_radius = Pt(4)
            shadow.distance = Pt(2)
        except Exception:
            pass
        return shape

    def _white_bg(slide):
        bg = slide.background
        fill = bg.fill
        fill.solid()
        fill.fore_color.rgb = _hex_to_rgb("FFFFFF")

    def _tinted_bg(slide, hex_color: str):
        bg = slide.background
        fill = bg.fill
        fill.solid()
        fill.fore_color.rgb = _hex_to_rgb(hex_color)

    def _add_bg_image(slide, image_path: Path, overlay_alpha: str = "30000"):
        """Full-bleed background image with dark gradient overlay."""
        pic = slide.shapes.add_picture(
            str(image_path), Emu(0), Emu(0), slide_w, slide_h,
        )
        sp = pic._element
        sp.getparent().remove(sp)
        slide.shapes._spTree.insert(2, sp)

        from pptx.oxml.ns import qn

        overlay = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Emu(0), Emu(0), slide_w, slide_h,
        )
        overlay.line.fill.background()
        fill_obj = overlay.fill
        fill_obj.solid()
        fill_obj.fore_color.rgb = _hex_to_rgb(theme.get("bg_dark", theme["primary"]))
        solid_fill = overlay._element.spPr.solidFill
        if solid_fill is not None:
            srgb = solid_fill.find(qn("a:srgbClr"))
            if srgb is None:
                srgb = solid_fill.find(qn("a:sysClr"))
            if srgb is not None:
                from lxml import etree
                alpha = etree.SubElement(srgb, qn("a:alpha"))
                alpha.set("val", overlay_alpha)

    def _add_sidebar_image(slide, image_path: Path, caption: str = ""):
        img_left = int(slide_w * 0.65)
        img_width = int(slide_w * 0.33)
        img_top = Inches(1.4)
        img_height = int(slide_h - Inches(2.4))
        try:
            slide.shapes.add_picture(
                str(image_path), img_left, img_top, img_width, img_height,
            )
            if caption:
                cap_tb = slide.shapes.add_textbox(
                    img_left, img_top + img_height + Inches(0.05),
                    img_width, Inches(0.35),
                )
                cap_p = cap_tb.text_frame.paragraphs[0]
                cap_p.alignment = PP_ALIGN.CENTER
                cap_run = cap_p.add_run()
                cap_run.text = caption
                _set_text_props(cap_run, 9, "888888")
                cap_run.font.italic = True
        except Exception:
            pass

    def _add_accent_image(slide, image_path: Path, caption: str = ""):
        """Add a smaller accent image in the bottom-right area."""
        img_left = slide_w - Inches(4.0)
        img_top = slide_h - Inches(3.2)
        img_width = Inches(3.5)
        img_height = Inches(2.2)
        try:
            slide.shapes.add_picture(
                str(image_path), img_left, img_top, img_width, img_height,
            )
            if caption:
                cap_tb = slide.shapes.add_textbox(
                    img_left, img_top + img_height + Inches(0.05),
                    img_width, Inches(0.3),
                )
                cap_p = cap_tb.text_frame.paragraphs[0]
                cap_p.alignment = PP_ALIGN.CENTER
                cap_run = cap_p.add_run()
                cap_run.text = caption
                _set_text_props(cap_run, 9, "888888")
                cap_run.font.italic = True
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════════════════
    # SLIDE 1: TITLE
    # Full-bleed image (or solid primary bg) with lesson title overlay
    # ═══════════════════════════════════════════════════════════════════
    slide = _next_slide()

    title_image = images.get("entity_0")
    if title_image:
        _add_bg_image(slide, title_image, overlay_alpha="30000")  # 70% dark overlay
    else:
        bg = slide.background
        fill = bg.fill
        fill.solid()
        fill.fore_color.rgb = _hex_to_rgb(theme.get("bg_dark", theme["primary"]))
        # Gradient effect: lighter bar at bottom
        _bar(slide, Emu(0), int(slide_h * 0.7), slide_w, int(slide_h * 0.3), theme["primary"])

    # Lesson title -- 44pt white bold, centered
    tb = slide.shapes.add_textbox(
        Inches(1.5), Inches(1.5), slide_w - Inches(3.0), Inches(2.5),
    )
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = lesson.title
    _set_text_props(run, 44, theme["text_light"], bold=True)

    # Aim -- the driving question, centered below title
    aim_text = lesson.objective
    if aim_text and not aim_text.lower().startswith("students will"):
        aim_display = f"Aim: {aim_text}"
    elif aim_text:
        aim_display = aim_text
    else:
        aim_display = ""
    if aim_display:
        tb_aim = slide.shapes.add_textbox(
            Inches(1.5), Inches(4.0), slide_w - Inches(3.0), Inches(1.0),
        )
        tf_aim = tb_aim.text_frame
        tf_aim.word_wrap = True
        p_aim = tf_aim.paragraphs[0]
        p_aim.alignment = PP_ALIGN.CENTER
        run_aim = p_aim.add_run()
        run_aim.text = aim_display
        _set_text_props(run_aim, 20, "EEEEEE")
        run_aim.font.italic = True

    # Subtitle: "Teacher Name | Date" -- 16pt
    tb2 = slide.shapes.add_textbox(
        Inches(1.5), Inches(5.2), slide_w - Inches(3.0), Inches(0.8),
    )
    tf2 = tb2.text_frame
    tf2.word_wrap = True
    p2 = tf2.paragraphs[0]
    p2.alignment = PP_ALIGN.CENTER
    run2 = p2.add_run()
    run2.text = (
        f"{teacher_display_name}  |  "
        f"{date.today().strftime('%B %d, %Y')}"
    )
    _set_text_props(run2, 16, "BBBBBB")

    # Bottom accent bar in subject color
    _bar(slide, Emu(0), slide_h - Inches(0.15), slide_w, Inches(0.15), theme["secondary"])

    _add_footer(slide, slide_num[0])

    # ═══════════════════════════════════════════════════════════════════
    # SLIDE 2: OBJECTIVES
    # Clean white bg, left accent bar, SWBAT in colored card
    # ═══════════════════════════════════════════════════════════════════
    slide = _next_slide()
    _white_bg(slide)

    # Left accent bar (4px, subject color)
    _bar(slide, Inches(0.5), Inches(0.8), Inches(0.06), Inches(5.5), theme["primary"])

    # "Today's Objectives" header -- 36pt, subject color
    tb = slide.shapes.add_textbox(
        Inches(1.0), Inches(0.8), slide_w - Inches(2.0), Inches(1.0),
    )
    p = tb.text_frame.paragraphs[0]
    run = p.add_run()
    run.text = "Today's Objectives"
    _set_text_props(run, 36, theme["primary"], bold=True)

    # SWBAT card -- colored rounded rectangle
    _rounded_card(
        slide,
        Inches(1.0), Inches(2.2),
        slide_w - Inches(2.0), Inches(1.8),
        theme["accent"],
    )
    tb = slide.shapes.add_textbox(
        Inches(1.4), Inches(2.5), slide_w - Inches(2.8), Inches(1.2),
    )
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.space_after = Pt(12)
    run = p.add_run()
    run.text = f"SWBAT: {lesson.objective}"
    _set_text_props(run, 24, theme["text_dark"], bold=True)

    # Standards below in 16pt gray
    if lesson.standards:
        tb = slide.shapes.add_textbox(
            Inches(1.0), Inches(4.4), slide_w - Inches(2.0), Inches(2.5),
        )
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        run = p.add_run()
        run.text = "Standards Addressed"
        _set_text_props(run, 16, "888888", bold=True)

        for std in lesson.standards[:3]:
            p = tf.add_paragraph()
            p.space_before = Pt(6)
            run = p.add_run()
            run.text = f"  {std}"
            _set_text_props(run, 16, "666666")

    _add_footer(slide, slide_num[0])

    # ═══════════════════════════════════════════════════════════════════
    # SLIDE 3: DO NOW / WARM-UP
    # Light tint bg, "Do Now" badge, question text, timer
    # ═══════════════════════════════════════════════════════════════════
    if lesson.do_now:
        slide = _next_slide()
        _tinted_bg(slide, theme["accent"])

        # "Do Now" badge -- rounded rectangle, subject color, white text
        badge = _rounded_card(
            slide,
            Inches(0.8), Inches(0.6),
            Inches(2.5), Inches(0.7),
            theme["primary"],
        )
        badge_tf = badge.text_frame
        badge_tf.paragraphs[0].alignment = PP_ALIGN.CENTER
        run = badge_tf.paragraphs[0].add_run()
        run.text = "Do Now"
        _set_text_props(run, 22, theme["text_light"], bold=True)

        # Question / prompt text -- 28pt, dark, good line spacing
        # Do Now uses accent image (small, bottom-right) not sidebar
        do_now_img = images.get("entity_1")

        tb = slide.shapes.add_textbox(
            Inches(0.8), Inches(1.8), slide_w - Inches(2.0), Inches(3.2),
        )
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.line_spacing = Pt(38)
        run = p.add_run()
        # Brief prompt on slide face, full text in speaker notes
        dn_text = lesson.do_now
        if len(dn_text) > 250:
            cutoff = dn_text[:250].rfind(". ")
            dn_display = dn_text[:cutoff + 1] if cutoff > 80 else dn_text[:250].rsplit(" ", 1)[0] + "..."
        else:
            dn_display = dn_text
        run.text = dn_display
        _set_text_props(run, 28, theme["text_dark"])

        # Full Do Now in speaker notes
        if len(dn_text) > 250:
            notes_slide = slide.notes_slide
            notes_tf = notes_slide.notes_text_frame
            notes_tf.text = dn_text

        if do_now_img:
            from clawed.slide_images import _extract_key_concepts
            concepts = _extract_key_concepts(lesson.do_now)
            caption = ", ".join(concepts[:2]) if concepts else ""
            _add_accent_image(slide, do_now_img, caption=caption)

        # Timer indicator
        minutes = lesson.time_estimates.get("do_now", 5)
        tb_timer = slide.shapes.add_textbox(
            slide_w - Inches(2.5), slide_h - Inches(1.0),
            Inches(2.0), Inches(0.5),
        )
        p_t = tb_timer.text_frame.paragraphs[0]
        p_t.alignment = PP_ALIGN.RIGHT
        run_t = p_t.add_run()
        run_t.text = f"{minutes} minutes"
        _set_text_props(run_t, 16, "888888")

        _add_footer(slide, slide_num[0])

    # ═══════════════════════════════════════════════════════════════════
    # SLIDE 4: DIRECT INSTRUCTION (student-facing summary)
    # Full script goes into speaker notes; slide face shows brief summary.
    # Additional slides for vocabulary terms and source excerpts if found.
    # ═══════════════════════════════════════════════════════════════════
    if lesson.direct_instruction:
        di_text = lesson.direct_instruction

        # ── Summary slide ──────────────────────────────────────────
        slide = _next_slide()
        _white_bg(slide)

        # "Direct Instruction" badge (subject color, rounded)
        badge = _rounded_card(
            slide,
            Inches(0.8), Inches(0.6),
            Inches(4.5), Inches(0.7),
            theme["primary"],
        )
        badge_tf = badge.text_frame
        badge_tf.paragraphs[0].alignment = PP_ALIGN.CENTER
        run = badge_tf.paragraphs[0].add_run()
        run.text = "Direct Instruction"
        _set_text_props(run, 22, theme["text_light"], bold=True)

        # Side accent bar
        _bar(slide, Inches(0.6), Inches(1.7), Inches(0.06), Inches(5.0), theme["secondary"])

        # Sidebar image if available
        img_path = images.get("entity_2")
        text_width = slide_w - Inches(2.0)
        if img_path:
            text_width = int(slide_w * 0.60)
            from clawed.slide_images import _extract_key_concepts
            concepts = _extract_key_concepts(di_text)
            caption = ", ".join(concepts[:2]) if concepts else ""
            _add_sidebar_image(slide, img_path, caption=caption)

        # Brief summary on the slide face (first sentence or ~150 chars)
        first_sentence_match = re.match(r"^(.+?[.!?])\s", di_text)
        if first_sentence_match and len(first_sentence_match.group(1)) <= 200:
            summary_text = first_sentence_match.group(1)
        else:
            summary_text = di_text[:150].rsplit(" ", 1)[0] + " ..."

        tb = slide.shapes.add_textbox(
            Inches(1.0), Inches(1.8), text_width, Inches(4.5),
        )
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.line_spacing = Pt(36)
        run = p.add_run()
        run.text = summary_text
        _set_text_props(run, 26, theme["text_dark"])

        # Full DI script in speaker notes
        notes_slide = slide.notes_slide
        notes_tf = notes_slide.notes_text_frame
        notes_tf.text = di_text

        _add_footer(slide, slide_num[0])

        # ── Vocabulary slide ───────────────────────────────────────
        # Prefer structured vocabulary from v2.3 model fields
        vocab_pairs: list[tuple[str, str]] = []
        if hasattr(lesson, "vocabulary") and lesson.vocabulary:
            for vt in lesson.vocabulary:
                term = getattr(vt, "term", "") if hasattr(vt, "term") else vt.get("term", "")
                defn = getattr(vt, "definition", "") if hasattr(vt, "definition") else vt.get("definition", "")
                if term and defn:
                    vocab_pairs.append((term, defn))

        # Fallback: regex extraction from DI text
        if not vocab_pairs:
            di_text_raw = lesson.direct_instruction or ""
            vocab_patterns = re.findall(
                r'\*\*([A-Z][^*]{2,30})\*\*\s*[-—:]+\s*([^*\n]{15,200})',
                di_text_raw,
            )
            if not vocab_patterns:
                vocab_patterns = re.findall(
                    r'(?:^|\n)\s*\*?\*?([A-Z][a-z]+(?:\s+[A-Za-z]+){0,3})\*?\*?\s*[-—:]+\s+'
                    r'([A-Za-z][^\n]{15,200})',
                    di_text_raw,
                )
            INSTRUCTIONAL_WORDS = {
                "check", "ask", "call", "facilitate", "transition", "minutes",
                "discuss", "display", "distribute", "brief", "move", "moved",
                "students", "responses", "excellent", "turn", "now", "let",
                "today", "good", "morning", "scholars", "friends", "class",
                "next", "first", "take", "look", "read", "write", "complete",
            }
            vocab_pairs = [
                (term.strip(), defn.strip()) for term, defn in vocab_patterns
                if 1 <= len(term.split()) <= 4
                and len(defn.split()) >= 3
                and not any(w in defn.lower().split()[:3] for w in INSTRUCTIONAL_WORDS)
                and not any(w in term.lower().split() for w in INSTRUCTIONAL_WORDS)
            ]

        if vocab_pairs:
            slide = _next_slide()
            _white_bg(slide)

            # "Key Vocabulary" badge
            badge = _rounded_card(
                slide,
                Inches(0.8), Inches(0.6),
                Inches(3.5), Inches(0.7),
                theme["secondary"],
            )
            badge_tf = badge.text_frame
            badge_tf.paragraphs[0].alignment = PP_ALIGN.CENTER
            run = badge_tf.paragraphs[0].add_run()
            run.text = "Key Vocabulary"
            _set_text_props(run, 22, theme["text_light"], bold=True)

            # Left accent bar
            _bar(slide, Inches(0.6), Inches(1.7), Inches(0.06), Inches(5.0), theme["primary"])

            # Vocabulary terms in large readable font
            tb = slide.shapes.add_textbox(
                Inches(1.0), Inches(1.8), slide_w - Inches(2.0), Inches(5.0),
            )
            tf = tb.text_frame
            tf.word_wrap = True

            for idx, (term, definition) in enumerate(vocab_pairs[:8]):
                p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
                p.space_before = Pt(10)
                p.line_spacing = Pt(36)
                # Bold term
                run_term = p.add_run()
                run_term.text = term.strip()
                _set_text_props(run_term, 24, theme["primary"], bold=True)
                # Definition
                run_def = p.add_run()
                run_def.text = f"  \u2014  {definition.strip()}"
                _set_text_props(run_def, 24, theme["text_dark"])

            _add_footer(slide, slide_num[0])

        # ── Source excerpt slides (if quoted passages detected) ─────
        # Try multiple quote patterns: curly quotes, straight quotes, markdown bold
        source_quotes: list[tuple[str, str]] = []
        for pattern in [
            r'\u201c([^\u201d]{30,500})\u201d[^\n]*?(?:[-\u2014]\s*(.+?)(?:\n|$))',
            r'"([^"]{30,500})"[^\n]*?(?:[-\u2014]\s*(.+?)(?:\n|$))',
            r"['\u2018]([^'\u2019]{30,500})['\u2019][^\n]*?(?:[-\u2014]\s*(.+?)(?:\n|$))",
        ]:
            source_quotes = re.findall(pattern, di_text)
            if source_quotes:
                break

        source_img_idx = 3  # Start from entity_3 for source slides
        for quote_text, attribution in source_quotes[:3]:
            slide = _next_slide()
            _tinted_bg(slide, theme["accent"])

            # "Source Excerpt" badge
            badge = _rounded_card(
                slide,
                Inches(0.8), Inches(0.6),
                Inches(3.5), Inches(0.7),
                theme["primary"],
            )
            badge_tf = badge.text_frame
            badge_tf.paragraphs[0].alignment = PP_ALIGN.CENTER
            run = badge_tf.paragraphs[0].add_run()
            run.text = "Source Excerpt"
            _set_text_props(run, 22, theme["text_light"], bold=True)

            # Add image if available (use remaining entity images)
            src_img = images.get(f"entity_{source_img_idx}")
            text_width = slide_w - Inches(2.0)
            if src_img:
                text_width = int(slide_w * 0.58)
                _add_sidebar_image(slide, src_img)
            source_img_idx += 1

            # Quoted text in large italic font
            tb = slide.shapes.add_textbox(
                Inches(1.5), Inches(2.0), text_width, Inches(3.5),
            )
            tf = tb.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT
            p.line_spacing = Pt(36)
            run = p.add_run()
            run.text = f"\u201c{quote_text.strip()}\u201d"
            _set_text_props(run, 24, theme["text_dark"])
            run.font.italic = True

            # Attribution below
            if attribution and attribution.strip():
                tb_attr = slide.shapes.add_textbox(
                    Inches(1.5), Inches(5.8), text_width, Inches(0.6),
                )
                p_attr = tb_attr.text_frame.paragraphs[0]
                p_attr.alignment = PP_ALIGN.RIGHT
                run_attr = p_attr.add_run()
                run_attr.text = f"\u2014 {attribution.strip()}"
                _set_text_props(run_attr, 18, "666666")

            _add_footer(slide, slide_num[0])

    # ═══════════════════════════════════════════════════════════════════
    # SECTION DIVIDER: "Let's Practice Together"
    # ═══════════════════════════════════════════════════════════════════
    if lesson.guided_practice:
        gp_min = lesson.time_estimates.get("guided_practice", 15)
        _section_divider(
            prs, slide_num, f"Let's Practice Together\n({gp_min} minutes)",
            theme, slide_w, slide_h,
        )

    # ═══════════════════════════════════════════════════════════════════
    # GUIDED PRACTICE -- "Your Turn" header
    # ═══════════════════════════════════════════════════════════════════
    if lesson.guided_practice:
        slide = _next_slide()
        _tinted_bg(slide, "F5F5F5")  # very light gray

        # "Your Turn" badge
        badge = _rounded_card(
            slide,
            Inches(0.8), Inches(0.6),
            Inches(3.0), Inches(0.7),
            theme["secondary"],
        )
        badge_tf = badge.text_frame
        badge_tf.paragraphs[0].alignment = PP_ALIGN.CENTER
        run = badge_tf.paragraphs[0].add_run()
        run.text = "Your Turn"
        _set_text_props(run, 22, theme["text_light"], bold=True)

        # No image on Guided Practice -- keep clean for readability

        # Brief student-facing instructions on slide face (first 2-3 sentences)
        gp_text = lesson.guided_practice
        gp_summary = gp_text
        if len(gp_text) > 250:
            cutoff = gp_text[:250].rfind(". ")
            if cutoff > 80:
                gp_summary = gp_text[:cutoff + 1]
            else:
                gp_summary = gp_text[:250].rsplit(" ", 1)[0] + "..."

        tb = slide.shapes.add_textbox(
            Inches(0.8), Inches(1.8), slide_w - Inches(2.0), Inches(4.5),
        )
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.line_spacing = Pt(34)
        run = p.add_run()
        run.text = gp_summary
        _set_text_props(run, 24, theme["text_dark"])

        # Full guided practice in speaker notes
        notes_slide = slide.notes_slide
        notes_tf = notes_slide.notes_text_frame
        notes_tf.text = gp_text

        # Time estimate
        minutes = lesson.time_estimates.get("guided_practice", 15)
        tb_time = slide.shapes.add_textbox(
            slide_w - Inches(2.5), slide_h - Inches(1.0),
            Inches(2.0), Inches(0.5),
        )
        p_t = tb_time.text_frame.paragraphs[0]
        p_t.alignment = PP_ALIGN.RIGHT
        run_t = p_t.add_run()
        run_t.text = f"{minutes} minutes"
        _set_text_props(run_t, 16, "888888")

        _add_footer(slide, slide_num[0])

    # ═══════════════════════════════════════════════════════════════════
    # INDEPENDENT WORK -- "Independent Practice" header
    # ═══════════════════════════════════════════════════════════════════
    if lesson.independent_work:
        slide = _next_slide()
        _white_bg(slide)

        # "Independent Practice" badge
        badge = _rounded_card(
            slide,
            Inches(0.8), Inches(0.6),
            Inches(4.5), Inches(0.7),
            theme["primary"],
        )
        badge_tf = badge.text_frame
        badge_tf.paragraphs[0].alignment = PP_ALIGN.CENTER
        run = badge_tf.paragraphs[0].add_run()
        run.text = "Independent Practice"
        _set_text_props(run, 22, theme["text_light"], bold=True)

        # Left accent bar
        _bar(slide, Inches(0.6), Inches(1.7), Inches(0.06), Inches(5.0), theme["secondary"])

        # No image on Independent Work -- keep clean for readability

        # Brief student-facing instructions on slide face
        iw_text = lesson.independent_work
        iw_summary = iw_text
        if len(iw_text) > 250:
            cutoff = iw_text[:250].rfind(". ")
            if cutoff > 80:
                iw_summary = iw_text[:cutoff + 1]
            else:
                iw_summary = iw_text[:250].rsplit(" ", 1)[0] + "..."

        tb = slide.shapes.add_textbox(
            Inches(1.0), Inches(1.8), slide_w - Inches(2.0), Inches(4.5),
        )
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.line_spacing = Pt(34)
        run = p.add_run()
        run.text = iw_summary
        _set_text_props(run, 24, theme["text_dark"])

        # Full independent work in speaker notes
        notes_slide = slide.notes_slide
        notes_tf = notes_slide.notes_text_frame
        notes_tf.text = iw_text

        # Time estimate in corner
        minutes = lesson.time_estimates.get("independent_work", 10)
        _rounded_card(
            slide,
            slide_w - Inches(3.0), slide_h - Inches(1.2),
            Inches(2.2), Inches(0.6),
            theme["accent"],
        )
        tb_time = slide.shapes.add_textbox(
            slide_w - Inches(3.0), slide_h - Inches(1.2),
            Inches(2.2), Inches(0.6),
        )
        p_t = tb_time.text_frame.paragraphs[0]
        p_t.alignment = PP_ALIGN.CENTER
        run_t = p_t.add_run()
        run_t.text = f"{minutes} minutes"
        _set_text_props(run_t, 16, theme["text_dark"])

        _add_footer(slide, slide_num[0])

    # ═══════════════════════════════════════════════════════════════════
    # SECTION DIVIDER: "Show What You Know"
    # ═══════════════════════════════════════════════════════════════════
    if lesson.exit_ticket:
        _section_divider(prs, slide_num, "Show What You Know\n(Exit Ticket)", theme, slide_w, slide_h)

    # ═══════════════════════════════════════════════════════════════════
    # EXIT TICKET -- distinctive assessment design
    # Colored banner header, numbered question cards with shadow
    # ═══════════════════════════════════════════════════════════════════
    if lesson.exit_ticket:
        slide = _next_slide()
        _white_bg(slide)

        # Full-width colored banner for "Exit Ticket"
        _bar(slide, Emu(0), Emu(0), slide_w, Inches(1.2), theme["primary"])
        tb = slide.shapes.add_textbox(
            Inches(0.8), Inches(0.15), slide_w - Inches(1.6), Inches(0.9),
        )
        p = tb.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT
        run = p.add_run()
        run.text = "Exit Ticket"
        _set_text_props(run, 36, theme["text_light"], bold=True)

        # Numbered question cards
        q_top = Inches(1.6)
        for i, q in enumerate(lesson.exit_ticket, 1):
            # Card background (rounded rectangle with shadow)
            _rounded_card(
                slide,
                Inches(1.0), q_top,
                slide_w - Inches(2.0), Inches(1.1),
                theme["accent"],
            )

            # Number circle
            circle = slide.shapes.add_shape(
                MSO_SHAPE.OVAL,
                Inches(1.3), q_top + Inches(0.15),
                Inches(0.7), Inches(0.7),
            )
            circle.line.fill.background()
            _add_shape_fill(circle, theme["secondary"])
            circle.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
            run = circle.text_frame.paragraphs[0].add_run()
            run.text = str(i)
            _set_text_props(run, 22, theme["text_light"], bold=True)

            # Question text
            tb = slide.shapes.add_textbox(
                Inches(2.3), q_top + Inches(0.15),
                slide_w - Inches(3.8), Inches(0.8),
            )
            tf = tb.text_frame
            tf.word_wrap = True
            run = tf.paragraphs[0].add_run()
            # Truncate long questions for slide readability
            q_text = q.question
            if len(q_text) > 120:
                q_text = q_text[:120].rsplit(" ", 1)[0] + "..."
            run.text = q_text
            _set_text_props(run, 20, theme["text_dark"])

            q_top += Inches(1.3)

        # "Turn in before you leave" footer note
        tb = slide.shapes.add_textbox(
            Inches(0.8), slide_h - Inches(0.9),
            slide_w - Inches(1.6), Inches(0.4),
        )
        p = tb.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        run = p.add_run()
        run.text = "Turn in before you leave"
        _set_text_props(run, 14, "888888")

        _add_footer(slide, slide_num[0])

    # ═══════════════════════════════════════════════════════════════════
    # CLOSING SLIDE -- Homework or Key Takeaway
    # ═══════════════════════════════════════════════════════════════════
    slide = _next_slide()
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = _hex_to_rgb(theme.get("bg_dark", theme["primary"]))

    if lesson.homework:
        # "Tonight's Homework" with details
        tb = slide.shapes.add_textbox(
            Inches(1.5), Inches(1.5), slide_w - Inches(3.0), Inches(1.5),
        )
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT
        run = p.add_run()
        run.text = "Tonight's Homework"
        _set_text_props(run, 36, theme["text_light"], bold=True)

        _bar(
            slide, Inches(1.5), Inches(3.2),
            Inches(4.0), Inches(0.06), theme["secondary"],
        )

        tb = slide.shapes.add_textbox(
            Inches(1.5), Inches(3.6), slide_w - Inches(3.0), Inches(3.0),
        )
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.line_spacing = Pt(30)
        run = p.add_run()
        # Brief homework summary on slide, full in notes
        hw_text = lesson.homework
        if len(hw_text) > 200:
            cutoff = hw_text[:200].rfind(". ")
            hw_display = hw_text[:cutoff + 1] if cutoff > 60 else hw_text[:200].rsplit(" ", 1)[0] + "..."
        else:
            hw_display = hw_text
        run.text = hw_display
        _set_text_props(run, 22, "DDDDDD")
        if len(hw_text) > 200:
            notes_slide = slide.notes_slide
            notes_tf = notes_slide.notes_text_frame
            notes_tf.text = f"HOMEWORK (full text):\n{hw_text}"
    else:
        # "Key Takeaway" or "Questions?"
        tb = slide.shapes.add_textbox(
            Inches(1.5), Inches(2.5), slide_w - Inches(3.0), Inches(2.0),
        )
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        run = p.add_run()
        run.text = "Questions?"
        _set_text_props(run, 48, theme["text_light"], bold=True)

    # Teacher name and subject in footer
    teacher_subject = subject.title() if subject else "Education"
    tb = slide.shapes.add_textbox(
        Inches(1.0), slide_h - Inches(1.0),
        slide_w - Inches(2.0), Inches(0.5),
    )
    p = tb.text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = f"{teacher_display_name}  |  {teacher_subject}"
    _set_text_props(run, 14, "888888")

    # Watermark
    tb_wm = slide.shapes.add_textbox(
        Inches(1.0), slide_h - Inches(0.55),
        slide_w - Inches(2.0), Inches(0.3),
    )
    p_wm = tb_wm.text_frame.paragraphs[0]
    p_wm.alignment = PP_ALIGN.CENTER
    run_wm = p_wm.add_run()
    run_wm.text = f"Generated by {agent_name}"
    _set_text_props(run_wm, 10, "666666")

    _add_footer(slide, slide_num[0])

    # ── Save ──────────────────────────────────────────────────────────
    out = _resolve_output(output_dir, lesson, ".pptx")
    prs.save(str(out))
    return out
