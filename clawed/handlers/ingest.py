"""File and path ingestion handler. Extracted from tg.py lines 1361-1481."""
from __future__ import annotations

import logging
from pathlib import Path

from clawed.gateway_response import GatewayResponse

logger = logging.getLogger(__name__)

MAX_INGEST_FILES = 500

def ingest_path(path, **kwargs):
    from clawed.ingestor import ingest_path as _ingest
    return _ingest(path, **kwargs)

async def extract_persona(documents, config=None):
    from clawed.persona import extract_persona as _extract
    return await _extract(documents, config)

class IngestHandler:
    async def handle(
        self, teacher_id: str, files: list[Path] | None = None, path: str | None = None,
    ) -> GatewayResponse:
        if not files and not path:
            return GatewayResponse(
                text="Send me your teaching files (PDF, DOCX, PPTX, TXT) or paste a folder path "
                "and I'll learn your teaching style."
            )
        target = Path(path).expanduser().resolve() if path else None
        documents = []
        try:
            # Guard: check total file count before ingesting a directory
            if target and target.is_dir():
                all_files = list(target.rglob("*"))
                all_files = [f for f in all_files if f.is_file()]
                if len(all_files) > MAX_INGEST_FILES:
                    logger.warning(
                        "Ingestion path has %d files, truncating to %d",
                        len(all_files), MAX_INGEST_FILES,
                    )
                    return GatewayResponse(
                        text=f"Found {len(all_files)} files, which exceeds the "
                             f"maximum of {MAX_INGEST_FILES}. Please narrow the "
                             f"folder or split into smaller batches."
                    )
            if files and len(files) > MAX_INGEST_FILES:
                return GatewayResponse(
                    text=f"Received {len(files)} files, which exceeds the "
                         f"maximum of {MAX_INGEST_FILES}. Please send fewer files."
                )

            if target and target.exists():
                documents = ingest_path(str(target))
            elif files:
                for f in files:
                    documents.extend(ingest_path(str(f)))
            if not documents:
                return GatewayResponse(text="No documents found to ingest.")
            try:
                from clawed.models import AppConfig
                persona = await extract_persona(documents, AppConfig.load())
                from clawed.persona import save_persona
                save_persona(persona, Path.home() / ".eduagent")
                style_info = f"\nLearned teaching style: {persona.teaching_style}"
                if persona.tone:
                    style_info += f", Tone: {persona.tone}"
                if persona.subject_area:
                    style_info += f", Subject: {persona.subject_area}"
            except Exception as e:
                logger.debug("Persona extraction skipped: %s", e)
                style_info = ""
            return GatewayResponse(text=f"Ingested {len(documents)} document(s).{style_info}")
        except Exception as e:
            logger.error("Ingestion failed: %s", e)
            return GatewayResponse(text=f"Ingestion failed: {e}")
