"""Tool: ingest_materials — wraps clawed.ingestor.ingest_path."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from clawed.agent_core.context import AgentContext, ToolResult


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

            return ToolResult(
                text=summary,
                data={"files_ingested": len(docs)},
                side_effects=[f"Ingested {len(docs)} files from {raw_path}"],
            )
        except Exception as e:
            return ToolResult(text=f"Failed to ingest materials: {e}")
