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
                # Override LLM-inferred name with configured teacher name
                try:
                    config = AppConfig.load()
                    if config.teacher_profile and config.teacher_profile.name:
                        persona.name = f"{config.teacher_profile.name} Teaching Persona"
                except Exception:
                    pass
                try:
                    _id_path = Path.home() / ".eduagent" / "workspace" / "identity.md"
                    if _id_path.exists():
                        import re as _re
                        _id_content = _id_path.read_text(encoding="utf-8")
                        _name_match = _re.match(r"^#\s+(.+)", _id_content)
                        if _name_match:
                            _tname = _name_match.group(1).strip()
                            if _tname and _tname != "Teacher":
                                persona.name = f"{_tname} Teaching Persona"
                except Exception:
                    pass
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

            # Index documents into curriculum knowledge base
            kb_info = ""
            try:
                from clawed.agent_core.memory.curriculum_kb import CurriculumKB
                kb = CurriculumKB()
                total_chunks = 0
                for doc in documents:
                    doc_type_val = doc.doc_type.value if hasattr(doc.doc_type, "value") else str(doc.doc_type)
                    chunks_added = kb.index(
                        teacher_id=teacher_id,
                        doc_title=doc.title,
                        source_path=doc.source_path or "",
                        full_text=doc.content,
                        metadata={"doc_type": doc_type_val},
                    )
                    total_chunks += chunks_added
                stats = kb.stats(teacher_id)
                kb_info = (
                    f"\n\nAdded to your curriculum library — I now have "
                    f"{stats['doc_count']} document(s) ({stats['chunk_count']} "
                    f"searchable sections). I'll reference your materials when "
                    f"creating new content."
                )
            except Exception as e:
                logger.debug("KB indexing skipped: %s", e)

            # Register assets (files, images, YouTube links) for search
            try:
                from clawed.asset_registry import AssetRegistry
                registry = AssetRegistry()
                asset_count = 0
                for doc in documents:
                    doc_type_val = doc.doc_type.value if hasattr(doc.doc_type, "value") else str(doc.doc_type)
                    extraction = None
                    if doc.source_path:
                        try:
                            from clawed.ingestor import extract_rich
                            extraction = extract_rich(Path(doc.source_path))
                        except Exception:
                            pass
                    aid = registry.register_asset(
                        teacher_id=teacher_id,
                        source_path=doc.source_path or "",
                        title=doc.title,
                        doc_type=doc_type_val,
                        text=doc.content,
                        extraction=extraction,
                    )
                    if aid:
                        asset_count += 1
                if asset_count:
                    kb_info += f" ({asset_count} files catalogued with images and links)"
            except Exception as e:
                logger.debug("Asset registration skipped: %s", e)

            return GatewayResponse(
                text=f"Ingested {len(documents)} document(s).{style_info}{kb_info}"
            )
        except Exception as e:
            logger.error("Ingestion failed: %s", e)
            return GatewayResponse(text=f"Ingestion failed: {e}")
