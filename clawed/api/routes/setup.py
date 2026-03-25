"""Setup wizard routes — browser-based configuration for teachers."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from clawed.config import set_api_key
from clawed.models import AppConfig, LLMProvider, TeacherProfile

logger = logging.getLogger(__name__)

router = APIRouter(tags=["setup"])
_TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


@router.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request):
    html = (_TEMPLATE_DIR / "setup.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


@router.post("/api/setup")
async def handle_setup(
    request: Request,
    name: str = Form(""),
    subject: str = Form(""),
    grades: list[str] = Form([]),
    state: str = Form(""),
    provider: str = Form("skip"),
    api_key: str = Form(""),
    telegram_token: str = Form(""),
    files: list[UploadFile] = File([]),
):
    profile = TeacherProfile(
        name=name or "Teacher",
        subjects=[subject] if subject else [],
        grade_levels=grades,
        state=state,
    )
    llm_provider = LLMProvider.OLLAMA
    if provider == "anthropic":
        llm_provider = LLMProvider.ANTHROPIC
    elif provider == "openai":
        llm_provider = LLMProvider.OPENAI

    if api_key.strip() and provider != "skip":
        prov_key = "ollama" if provider == "ollama" else provider
        set_api_key(prov_key, api_key.strip())

    config = AppConfig(provider=llm_provider, teacher_profile=profile)
    if telegram_token.strip():
        config.telegram_bot_token = telegram_token.strip()
    if provider == "ollama" and api_key.strip():
        config.ollama_base_url = "https://api.ollama.com/v1"
        config.ollama_model = "minimax-m2.7:cloud"
    config.save()

    ingested_count = 0
    if files and files[0].filename:
        import tempfile

        from clawed.ingestor import ingest_path
        with tempfile.TemporaryDirectory() as tmpdir:
            for f in files:
                if f.filename:
                    dest = Path(tmpdir) / f.filename
                    content = await f.read()
                    dest.write_bytes(content)
            docs = ingest_path(tmpdir)
            ingested_count = len(docs)
            if docs:
                try:
                    from clawed.persona import extract_persona, save_persona
                    persona = await extract_persona(docs, config)
                    save_persona(persona, Path.home() / ".eduagent")
                except Exception as e:
                    logger.warning("Persona extraction failed: %s", e)

    try:
        from clawed.models import TeacherPersona
        from clawed.workspace import init_workspace
        persona = TeacherPersona(name=name, subject_area=subject)
        init_workspace(persona, config)
    except Exception:
        pass

    return RedirectResponse(
        url=f"/setup/done?name={name}&files={ingested_count}",
        status_code=303,
    )


@router.get("/setup/done", response_class=HTMLResponse)
async def setup_done(request: Request, name: str = "", files: int = 0):
    html = (_TEMPLATE_DIR / "setup_done.html").read_text(encoding="utf-8")
    html = html.replace("TEACHER_NAME_PLACEHOLDER", name or "Teacher")
    if files > 0:
        files_html = (
            f'<br><span class="highlight">{files} file(s) imported</span>'
            " — I'm already learning your style."
        )
    else:
        files_html = ""
    html = html.replace("FILES_PLACEHOLDER", files_html)
    return HTMLResponse(html)


@router.post("/api/setup/test-connection")
async def test_connection(request: Request):
    import os
    body = await request.json()
    provider = body.get("provider", "ollama")
    api_key = body.get("api_key", "")
    from clawed.config import test_llm_connection
    config = AppConfig()
    if provider == "anthropic":
        config.provider = LLMProvider.ANTHROPIC
    elif provider == "openai":
        config.provider = LLMProvider.OPENAI
    else:
        config.provider = LLMProvider.OLLAMA
        if api_key:
            config.ollama_base_url = "https://api.ollama.com/v1"
            config.ollama_model = "minimax-m2.7:cloud"
            config.ollama_api_key = api_key
    env_map = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY", "ollama": "OLLAMA_API_KEY"}
    env_key = env_map.get(provider, "")
    old_val = os.environ.get(env_key, "")
    if api_key and env_key:
        os.environ[env_key] = api_key
    try:
        result = await test_llm_connection(config)
        msg = result.get("message", result.get("error", ""))
        return JSONResponse({"connected": result.get("connected", False), "message": msg})
    except Exception as e:
        return JSONResponse({"connected": False, "message": str(e)})
    finally:
        if env_key:
            if old_val:
                os.environ[env_key] = old_val
            elif env_key in os.environ:
                del os.environ[env_key]
