"""Ingest routes — file upload and persona extraction."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

from eduagent.api.server import get_db
from eduagent.ingestor import ingest_path
from eduagent.persona import extract_persona

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
            dest = tmp_path / f.filename
            content = await f.read()
            dest.write_bytes(content)

        # Ingest all files
        documents = ingest_path(tmp_path)

    if not documents:
        return JSONResponse({"error": "No supported documents found in upload"}, status_code=400)

    # Extract persona
    try:
        persona = await extract_persona(documents)
    except Exception as e:
        return JSONResponse({"error": f"Persona extraction failed: {e}"}, status_code=500)

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

    persona_data = json.loads(teacher["persona_json"])
    return {"teacher_id": teacher["id"], "persona": persona_data}
