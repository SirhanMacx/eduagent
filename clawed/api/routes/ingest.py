"""Ingest routes — file upload and persona extraction."""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

from clawed.api.deps import get_db
from clawed.ingestor import ingest_path
from clawed.persona import extract_persona

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ingest"])


@router.post("/ingest")
async def ingest_files(files: list[UploadFile] = File(...)):
    """Upload teaching materials and extract a teacher persona."""
    if not files:
        return JSONResponse({"error": "No files uploaded"}, status_code=400)

    # Save uploaded files to a temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        for f in files:
            # Sanitize filename to prevent path traversal
            raw_name = os.path.basename(f.filename or "upload")
            safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", raw_name) or "upload"
            dest = tmp_path / safe_name
            content = await f.read()
            dest.write_bytes(content)

        # Ingest all files
        documents = ingest_path(tmp_path)

    if not documents:
        return JSONResponse({"error": "No supported documents found in upload"}, status_code=400)

    # Extract persona
    try:
        persona = await extract_persona(documents)
    except Exception:
        logger.error("Persona extraction failed", exc_info=True)
        return JSONResponse({"error": "Persona extraction failed. Please try again."}, status_code=500)

    # Save to database
    db = get_db()
    persona_json = persona.model_dump_json()
    teacher_id = db.upsert_teacher(persona.name, persona_json)

    return {
        "teacher_id": teacher_id,
        "persona": persona.model_dump(),
        "documents_ingested": len(documents),
    }


@router.get("/persona")
async def get_persona():
    """Get the current teacher persona."""
    db = get_db()
    teacher = db.get_default_teacher()
    if not teacher or not teacher.get("persona_json"):
        return JSONResponse({"error": "No persona found. Upload teaching materials first."}, status_code=404)

    try:
        persona_data = json.loads(teacher["persona_json"])
    except (json.JSONDecodeError, TypeError) as exc:
        logger.warning("Failed to parse persona_json: %s", exc)
        return JSONResponse({"error": "Persona data is corrupted."}, status_code=500)
    return {"teacher_id": teacher["id"], "persona": persona_data}
