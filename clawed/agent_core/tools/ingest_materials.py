"""Tool: ingest_materials — wraps clawed.ingestor.ingest_path."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from clawed.agent_core.context import AgentContext, ToolResult

logger = logging.getLogger(__name__)


class IngestMaterialsTool:
    """Ingest teaching materials from a folder or file to learn the teacher's style."""

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "ingest_materials",
                "description": (
                    "Ingest lesson plans and teaching materials from a folder "
                    "or file path. Extracts text and learns the teacher's style."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": (
                                "Path to a folder or file to ingest "
                                "(PDF, DOCX, PPTX, TXT, MD)"
                            ),
                        },
                    },
                    "required": ["path"],
                },
            },
        }

    async def execute(
        self, params: dict[str, Any], context: AgentContext
    ) -> ToolResult:
        from clawed.ingestor import ingest_path

        raw_path = params["path"]
        resolved = Path(raw_path).expanduser().resolve()

        if not resolved.exists():
            return ToolResult(
                text=f"Path not found: {raw_path}. Check the path and try again."
            )

        try:
            docs = ingest_path(resolved)
            if not docs:
                return ToolResult(
                    text=f"No supported files found in {raw_path}. "
                    "Supported formats: PDF, DOCX, PPTX, TXT, MD."
                )

            # Try to extract persona from ingested docs
            persona = None
            try:
                from clawed.persona import extract_persona, save_persona

                persona = await extract_persona(docs, context.config)
                save_persona(persona, Path.home() / ".eduagent")
            except Exception:
                pass

            # Generate reading report
            summary = f"Ingested {len(docs)} file(s) from {raw_path}."
            try:
                from clawed.reading_report import (
                    format_reading_report,
                    generate_reading_report,
                )

                report = generate_reading_report(docs, persona=persona)
                report_text = format_reading_report(report)
                if report_text:
                    summary = report_text
                    # Store the report for future system prompts
                    import os

                    data_dir = Path(
                        os.environ.get(
                            "EDUAGENT_DATA_DIR",
                            str(Path.home() / ".eduagent"),
                        )
                    )
                    report_path = data_dir / "workspace" / "reading_report.md"
                    report_path.parent.mkdir(parents=True, exist_ok=True)
                    report_path.write_text(report_text, encoding="utf-8")
            except Exception:
                # Fallback to basic summary if report generation fails
                if persona:
                    style = persona.teaching_style.value.replace("_", " ").title()
                    summary += f" Teaching style: {style}, Tone: {persona.tone}."
                else:
                    summary += " (Could not extract style patterns.)"

            # Update SOUL.md with what we learned
            try:
                soul_path = Path.home() / ".eduagent" / "workspace" / "SOUL.md"
                soul_path.parent.mkdir(parents=True, exist_ok=True)

                # Build soul updates from reading report
                soul_updates = []
                if report.get("teacher_details", {}).get("name_used"):
                    soul_updates.append(
                        f"Students know me as {report['teacher_details']['name_used']}"
                    )
                if report.get("voice_patterns"):
                    soul_updates.append(
                        "Voice patterns: " + "; ".join(report["voice_patterns"][:3])
                    )
                if report.get("favorite_strategies"):
                    soul_updates.append(
                        "Go-to strategies: " + ", ".join(report["favorite_strategies"][:4])
                    )
                if report.get("signature_moves"):
                    soul_updates.append(
                        "Signature moves: " + ", ".join(report["signature_moves"][:3])
                    )
                if report.get("assessment_patterns"):
                    soul_updates.append(
                        "Assessment style: " + "; ".join(report["assessment_patterns"][:2])
                    )

                if soul_updates:
                    from datetime import date

                    update_text = f"\n\n### Learned from files ({date.today().isoformat()})\n"
                    update_text += "\n".join(f"- {u}" for u in soul_updates) + "\n"

                    if soul_path.exists():
                        current = soul_path.read_text(encoding="utf-8")
                        if "## Agent Observations" in current:
                            current = current.replace(
                                "## Agent Observations",
                                f"## Agent Observations{update_text}",
                            )
                        else:
                            current += f"\n## Agent Observations{update_text}"
                        soul_path.write_text(current, encoding="utf-8")
                    else:
                        template = (
                            "# Teaching Identity\n\n"
                            "## Who I Am\n\n## My Teaching Philosophy\n\n"
                            "## My Voice\n\n## My Classroom Norms\n\n"
                            "## Assessment Approach\n\n"
                            "## What Makes My Teaching Mine\n\n"
                            f"## Agent Observations{update_text}"
                        )
                        soul_path.write_text(template, encoding="utf-8")
            except Exception as e:
                logger.debug("SOUL.md update failed: %s", e)

            return ToolResult(
                text=summary,
                data={"files_ingested": len(docs)},
                side_effects=[f"Ingested {len(docs)} files from {raw_path}"],
            )
        except Exception as e:
            return ToolResult(text=f"Failed to ingest materials: {e}")
