"""Tool: generate_lesson_bundle — complete teaching package (lesson + handout + slides)."""
from __future__ import annotations

import json
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
                    "a slideshow (PPTX). All three files are created at once."
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
        from clawed.lesson import generate_lesson
        from clawed.models import LessonBrief, TeacherPersona, UnitPlan
        from clawed.sanitize import sanitize_text
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

        # ── Generate the lesson ──────────────────────────────────────
        logger.info(
            "Generating lesson bundle for '%s' (grade=%s, subject=%s, images=%s)",
            topic, grade, subject, include_images,
        )
        try:
            lesson = await generate_lesson(
                lesson_number=1,
                unit=unit,
                persona=persona,
                config=config,
                state=state,
                teacher_materials=kb_prompt_section,
            )
        except Exception as e:
            return ToolResult(text=f"Failed to generate lesson: {e}")

        # ── Sanitize all text fields ─────────────────────────────────
        lesson.title = sanitize_text(lesson.title)
        lesson.objective = sanitize_text(lesson.objective)
        lesson.do_now = sanitize_text(lesson.do_now)
        lesson.direct_instruction = sanitize_text(lesson.direct_instruction)
        lesson.guided_practice = sanitize_text(lesson.guided_practice)
        lesson.independent_work = sanitize_text(lesson.independent_work)
        if lesson.homework:
            lesson.homework = sanitize_text(lesson.homework)

        # ── Ensure standards are populated ───────────────────────────
        if not lesson.standards and standards_list:
            lesson.standards = standards_list

        # ── Self-review against observation-ready standards ──────────
        lesson_json_str = json.dumps(lesson.model_dump(), indent=2)
        try:
            from clawed.llm import LLMClient

            llm_client = LLMClient(config)
            review = await llm_client.review_lesson_package(
                lesson_json_str,
                standards_present=bool(lesson.standards),
                has_handout=True,
                has_slideshow=True,
            )
            if not review.get("passed", True) and review.get("issues"):
                # Log issues for transparency
                issues_text = "; ".join(review["issues"][:3])
                logger.info("Self-review found issues: %s", issues_text)
        except Exception:
            pass  # Review is best-effort, don't block on failure

        # ── Export all three files ────────────────────────────────────
        output_dir = Path("clawed_output").resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        generated_files: list[Path] = []
        side_effects: list[str] = []
        errors: list[str] = []

        # 1. Lesson plan DOCX
        try:
            from clawed.export_docx import export_lesson_docx

            docx_path = export_lesson_docx(lesson, persona, output_dir)
            generated_files.append(docx_path)
            side_effects.append(f"Lesson plan DOCX: {docx_path.name}")
        except Exception as e:
            logger.error("Lesson DOCX export failed: %s", e)
            errors.append(f"Lesson plan DOCX failed: {e}")

        # 2. Generate student handout via LLM (first-class output, not regex extraction)
        try:
            import json_repair

            from clawed.llm import LLMClient

            llm_client = LLMClient(config)
            handout_raw = await llm_client.generate_student_handout(
                lesson_json_str,
                persona_context=persona.to_prompt_context(),
                subject=subject,
                grade=grade,
            )
            # Parse handout JSON
            handout_cleaned = handout_raw.strip()
            if handout_cleaned.startswith("```"):
                lines = handout_cleaned.split("\n")
                lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                handout_cleaned = "\n".join(lines)
            try:
                handout_data = json.loads(handout_cleaned)
            except json.JSONDecodeError:
                handout_data = json_repair.loads(handout_cleaned)

            from clawed.export_handout import export_handout_docx

            handout_path = export_handout_docx(handout_data, subject=subject)
            if handout_path:
                generated_files.append(Path(handout_path))
                side_effects.append(f"Student handout DOCX: {Path(handout_path).name}")
        except Exception as handout_err:
            logger.warning("LLM handout generation failed, falling back: %s", handout_err)
            # Fallback to regex-based handout
            try:
                from clawed.export_docx import export_student_handout

                handout_path = export_student_handout(lesson, persona, output_dir)
                if handout_path:
                    generated_files.append(Path(handout_path))
                    side_effects.append(f"Student handout DOCX: {Path(handout_path).name}")
            except Exception:
                pass

        # 3. Slideshow PPTX
        try:
            from clawed.export_pptx import export_lesson_pptx

            pptx_path = export_lesson_pptx(lesson, persona, output_dir, include_images=include_images)
            generated_files.append(pptx_path)
            side_effects.append(f"Slideshow PPTX: {pptx_path.name}")
        except Exception as e:
            logger.error("PPTX export failed: %s", e)
            errors.append(f"Slideshow PPTX failed: {e}")

        # ── Build response ───────────────────────────────────────────
        lines = [f"Generated teaching package for: {lesson.title}\n"]
        if generated_files:
            lines.append("Files created:")
            for f in generated_files:
                lines.append(f"  - {f}")
        if kb_context:
            lines.append("\nReferenced your existing materials on this topic.")
        if errors:
            lines.append("\nErrors:")
            for err in errors:
                lines.append(f"  - {err}")

        return ToolResult(
            text="\n".join(lines),
            files=generated_files,
            side_effects=side_effects,
        )
