"""Tool: generate_lesson_bundle — complete teaching package (lesson + handout + slides)."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from clawed.agent_core.context import AgentContext, ToolResult

logger = logging.getLogger(__name__)


class GenerateLessonBundleTool:
    """Generate a COMPLETE teaching package: lesson plan + student handout + slideshow."""

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "generate_lesson_bundle",
                "description": (
                    "Generate a COMPLETE teaching package for a topic: "
                    "a lesson plan (DOCX), a student handout (DOCX), and "
                    "a slideshow (PPTX). All three files are created at once. "
                    "IMPORTANT: Always call search_my_materials FIRST to find "
                    "the teacher's existing materials on this topic before "
                    "calling this tool."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "The lesson topic",
                        },
                        "grade": {
                            "type": "string",
                            "description": "Grade level (e.g. '8', 'K')",
                            "default": "8",
                        },
                        "subject": {
                            "type": "string",
                            "description": "Subject area",
                            "default": "General",
                        },
                        "activity_type": {
                            "type": "string",
                            "description": (
                                "Activity structure for the lesson"
                            ),
                            "enum": [
                                "jigsaw",
                                "socratic_seminar",
                                "document_analysis",
                                "debate",
                                "gallery_walk",
                                "station_rotation",
                                "direct_instruction",
                                "general",
                            ],
                            "default": "general",
                        },
                        "include_images": {
                            "type": "boolean",
                            "description": "Include academic images in the slideshow (default: true)",
                            "default": True,
                        },
                    },
                    "required": ["topic"],
                },
            },
        }

    async def execute(
        self, params: dict[str, Any], context: AgentContext
    ) -> ToolResult:
        from clawed.models import LessonBrief, TeacherPersona, UnitPlan
        from clawed.standards import get_standards_for_lesson

        topic = params["topic"]
        grade = params.get("grade", "8")
        subject = params.get("subject", "General")
        activity_type = params.get("activity_type", "general")
        include_images = params.get("include_images", True)

        # ── Load config & persona from context ───────────────────────
        config = context.config
        persona = TeacherPersona()
        if context.persona:
            try:
                persona = TeacherPersona(**context.persona)
            except Exception:
                pass

        # ── Load state standards if teacher profile has a state ───────
        state = ""
        if config.teacher_profile and config.teacher_profile.state:
            state = config.teacher_profile.state

        standards_list = get_standards_for_lesson(
            subject=subject,
            grade=grade,
            state=state,
            topic=topic,
        )

        # ── Search for teacher's existing materials (assets + KB) ─────
        kb_context = ""
        kb_prompt_section = ""

        # Asset-level search (complete files, YouTube links)
        try:
            from clawed.asset_registry import AssetRegistry
            registry = AssetRegistry()
            assets = registry.search_assets(context.teacher_id, topic, top_k=5)
            yt_links = registry.get_youtube_links(context.teacher_id, topic, top_k=3)
            if assets or yt_links:
                kb_prompt_section = registry.format_asset_summary(assets, yt_links)
                logger.info(
                    "Asset search found %d files, %d YouTube links for '%s'",
                    len(assets), len(yt_links), topic,
                )
        except Exception as e:
            logger.debug("Asset search failed: %s", e)

        # KB chunk-level search (text excerpts)
        try:
            from clawed.agent_core.memory.curriculum_kb import CurriculumKB
            kb = CurriculumKB()
            kb_results = kb.search(context.teacher_id, topic, top_k=3)
            if kb_results:
                kb_parts = [r for r in kb_results if r.get("similarity", 0) > 0.1]
                if kb_parts:
                    kb_context = (
                        "\n\nRelevant materials from the teacher's files:\n"
                        + "\n".join(
                            f"From '{r['doc_title']}': {r['chunk_text'][:200]}"
                            for r in kb_parts
                        )
                    )
                    chunk_section = "\n\n".join(
                        f"From \"{r['doc_title']}\":\n{r['chunk_text'][:500]}"
                        for r in kb_parts
                    )
                    if kb_prompt_section:
                        kb_prompt_section += "\n\n" + chunk_section
                    else:
                        kb_prompt_section = (
                            "Teacher's Existing Materials on This Topic\n"
                            "The teacher has created content on this topic before. "
                            "Reference and build on their existing work:\n\n"
                            + chunk_section
                            + "\n\nUse these materials as a foundation. "
                            "Reference the teacher's existing lessons, reuse their "
                            "graphic organizer formats, build on their approach."
                        )
                    logger.info("KB search found %d relevant chunks for '%s'", len(kb_parts), topic)
        except Exception as e:
            logger.debug("KB search failed: %s", e)

        # ── Build a UnitPlan with standards ──────────────────────────
        description = f"Introduction to {topic}"
        if activity_type and activity_type != "general":
            description = (
                f"{activity_type.replace('_', ' ').title()} lesson on {topic}"
            )

        unit = UnitPlan(
            title=f"{topic} Unit",
            subject=subject,
            grade_level=grade,
            topic=topic,
            duration_weeks=1,
            overview=f"A lesson on {topic}.{kb_context}",
            standards=standards_list,
            daily_lessons=[
                LessonBrief(
                    lesson_number=1,
                    topic=topic,
                    description=description,
                )
            ],
        )

        # ── Generate MasterContent ────────────────────────────────────
        from clawed.lesson import generate_master_content

        logger.info(
            "Generating master content for '%s' (grade=%s, subject=%s)",
            topic, grade, subject,
        )
        try:
            master = await generate_master_content(
                lesson_number=1,
                unit=unit,
                persona=persona,
                config=config,
                state=state,
                teacher_materials=kb_prompt_section,
            )
        except Exception as e:
            return ToolResult(text=f"Failed to generate lesson: {e}")

        # ── Validate ──────────────────────────────────────────────────
        from clawed.generation_report import GenerationReport
        from clawed.validation import check_self_contained, validate_alignment, validate_master_content

        report = GenerationReport()

        mc_errors = validate_master_content(master, topic)
        for err in mc_errors:
            report.warnings.append(err)
            logger.warning("Validation: %s", err)

        align_score, align_issues = validate_alignment(master)
        for issue in align_issues:
            report.warnings.append(issue)

        # Check all text for delegation phrases
        all_text = " ".join(
            s.content for s in master.direct_instruction
        )
        delegation = check_self_contained(all_text)
        for d in delegation:
            report.warnings.append(d)

        # ── Fetch images ──────────────────────────────────────────────
        images: dict[str, Path] = {}
        if include_images:
            try:
                from clawed.image_pipeline import fetch_all_images

                images = await fetch_all_images(master, config)
                report.images_embedded = len(images)
                logger.info("Fetched %d images", len(images))
            except Exception as e:
                logger.warning("Image fetch failed: %s", e)
                report.warnings.append(f"Image fetch failed: {e}")

        # ── Compile three views ───────────────────────────────────────
        output_dir = Path("clawed_output").resolve()
        if config and hasattr(config, "output_dir") and config.output_dir:
            output_dir = Path(config.output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        generated_files: list[Path] = []
        side_effects: list[str] = []
        errors: list[str] = []

        # 1. Teacher DOCX
        try:
            from clawed.compile_teacher import compile_teacher_view
            teacher_path = await compile_teacher_view(master, images, output_dir)
            generated_files.append(teacher_path)
            side_effects.append(f"Teacher lesson plan DOCX: {teacher_path.name}")
        except Exception as e:
            logger.error("Teacher DOCX compile failed: %s", e)
            errors.append(f"Teacher DOCX failed: {e}")

        # 2. Student DOCX
        try:
            from clawed.compile_student import compile_student_view
            student_path = await compile_student_view(master, images, output_dir)
            generated_files.append(student_path)
            side_effects.append(f"Student packet DOCX: {student_path.name}")
        except Exception as e:
            logger.error("Student DOCX compile failed: %s", e)
            errors.append(f"Student packet failed: {e}")

        # 3. Slideshow PPTX
        try:
            from clawed.compile_slides import compile_slides
            pptx_path = await compile_slides(master, images, output_dir)
            generated_files.append(pptx_path)
            side_effects.append(f"Slideshow PPTX: {pptx_path.name}")
        except Exception as e:
            logger.error("Slides compile failed: %s", e)
            errors.append(f"Slideshow PPTX failed: {e}")

        # ── Build response ─────────────────────────────────────────────
        lines = []

        if len(generated_files) == 3 and not errors:
            lines.append(f"Complete teaching package for: {master.title}")
            lines.append("All three files ready to print:")
            for se in side_effects:
                lines.append(f"  - {se}")
        elif generated_files:
            lines.append(f"Generated {len(generated_files)} of 3 files for: {master.title}")
            for se in side_effects:
                lines.append(f"  - {se}")
            if errors:
                lines.append("")
                for err in errors:
                    clean_err = str(err).split("\n")[0][:200]
                    lines.append(f"  Could not generate: {clean_err}")
                lines.append("Want me to try the failed item(s) again?")
        else:
            lines.append(f"Failed to generate teaching package for: {master.title}")
            for err in errors:
                lines.append(f"  - {err}")

        if kb_prompt_section:
            lines.append("\nReferenced your existing materials on this topic.")

        # Quality report
        if report.warnings:
            lines.append("\nQuality notes:")
            for w in report.warnings[:5]:
                lines.append(f"  - {w}")

        return ToolResult(
            text="\n".join(lines),
            files=generated_files,
            side_effects=side_effects,
        )
