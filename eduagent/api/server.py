"""FastAPI web server for EDUagent — REST API + server-side rendered teacher dashboard."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from eduagent.database import Database

# Paths
_PKG_DIR = Path(__file__).parent
_TEMPLATE_DIR = _PKG_DIR / "templates"
_STATIC_DIR = _PKG_DIR / "static"

# Shared state
_db: Database | None = None


def get_db() -> Database:
    global _db
    if _db is None:
        _db = Database()
    return _db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    global _db
    _db = Database()
    yield
    if _db:
        _db.close()
        _db = None


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="EDUagent",
        description="Your teaching files, your AI co-teacher.",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Static files
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

    # Templates
    templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))

    # ── Import and include API routers ───────────────────────────────

    from eduagent.api.routes.chat import router as chat_router
    from eduagent.api.routes.export import router as export_router
    from eduagent.api.routes.feedback import router as feedback_router
    from eduagent.api.routes.generate import router as generate_router
    from eduagent.api.routes.ingest import router as ingest_router

    app.include_router(ingest_router, prefix="/api")
    app.include_router(generate_router, prefix="/api")
    app.include_router(chat_router, prefix="/api")
    app.include_router(feedback_router, prefix="/api")
    app.include_router(export_router, prefix="/api")

    # ── Page routes (server-side rendered) ───────────────────────────

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        db = get_db()
        stats = db.get_stats()
        teacher = db.get_default_teacher()
        has_persona = teacher is not None
        return templates.TemplateResponse(request, "index.html", {
            "stats": stats,
            "has_persona": has_persona,
        })

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard(request: Request):
        db = get_db()
        stats = db.get_stats()
        units = db.list_units()
        # Enrich units with lesson counts
        for u in units:
            u["lesson_count"] = len(db.list_lessons(u["id"]))
        teacher = db.get_default_teacher()
        persona_name = ""
        if teacher and teacher.get("persona_json"):
            try:
                persona_name = json.loads(teacher["persona_json"]).get("name", "")
            except (json.JSONDecodeError, TypeError):
                pass
        return templates.TemplateResponse(request, "dashboard.html", {
            "stats": stats,
            "units": units,
            "persona_name": persona_name,
        })

    @app.get("/generate", response_class=HTMLResponse)
    async def generate_page(request: Request):
        from eduagent.standards import STANDARDS
        db = get_db()
        teacher = db.get_default_teacher()
        has_persona = teacher is not None
        subjects = list(STANDARDS.keys())
        return templates.TemplateResponse(request, "generate.html", {
            "has_persona": has_persona,
            "subjects": subjects,
        })

    @app.get("/lesson/{lesson_id}", response_class=HTMLResponse)
    async def lesson_page(request: Request, lesson_id: str):
        db = get_db()
        lesson_row = db.get_lesson(lesson_id)
        if not lesson_row:
            return HTMLResponse("<h1>Lesson not found</h1>", status_code=404)
        lesson_data = json.loads(lesson_row["lesson_json"]) if lesson_row["lesson_json"] else {}
        materials_data = json.loads(lesson_row["materials_json"]) if lesson_row.get("materials_json") else None
        feedback_list = db.get_feedback_for_lesson(lesson_id)
        return templates.TemplateResponse(request, "lesson.html", {
            "lesson": lesson_row,
            "lesson_data": lesson_data,
            "materials": materials_data,
            "feedback_list": feedback_list,
            "share_url": f"/share/{lesson_row['share_token']}",
        })

    @app.get("/share/{token}", response_class=HTMLResponse)
    async def share_page(request: Request, token: str):
        db = get_db()
        lesson_row = db.get_lesson_by_token(token)
        if not lesson_row:
            return HTMLResponse("<h1>Lesson not found</h1>", status_code=404)
        lesson_data = json.loads(lesson_row["lesson_json"]) if lesson_row["lesson_json"] else {}
        return templates.TemplateResponse(request, "lesson.html", {
            "lesson": lesson_row,
            "lesson_data": lesson_data,
            "materials": None,
            "feedback_list": [],
            "share_url": f"/share/{token}",
            "is_shared": True,
        })

    return app


# Module-level app for `uvicorn eduagent.api.server:app`
app = create_app()
