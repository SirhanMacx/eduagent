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
    from eduagent.api.routes.school import router as school_router
    from eduagent.api.routes.settings import router as settings_router

    app.include_router(ingest_router, prefix="/api")
    app.include_router(generate_router, prefix="/api")
    app.include_router(chat_router, prefix="/api")
    app.include_router(feedback_router, prefix="/api")
    app.include_router(export_router, prefix="/api")
    app.include_router(settings_router, prefix="/api")
    app.include_router(school_router, prefix="/api")

    # ── Page routes (server-side rendered) ───────────────────────────

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        db = get_db()
        stats = db.get_stats()
        teacher = db.get_default_teacher()
        has_persona = teacher is not None and teacher.get("persona_json") is not None
        onboarding_complete = db.is_onboarding_complete()

        # If persona exists and onboarding is done, show dashboard-style home
        persona_data = None
        if teacher and teacher.get("persona_json"):
            try:
                persona_data = json.loads(teacher["persona_json"])
            except (json.JSONDecodeError, TypeError):
                pass

        return templates.TemplateResponse(request, "index.html", {
            "stats": stats,
            "has_persona": has_persona,
            "onboarding_complete": onboarding_complete,
            "teacher_id": teacher["id"] if teacher else None,
            "persona": persona_data,
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
        persona_data = None
        if teacher and teacher.get("persona_json"):
            try:
                persona_data = json.loads(teacher["persona_json"])
                persona_name = persona_data.get("name", "")
            except (json.JSONDecodeError, TypeError):
                pass

        # Build recent activity feed (last 10 items: units + lessons)
        recent_items: list[dict] = []
        for u in units[:10]:
            recent_items.append({
                "type": "unit",
                "title": u["title"],
                "id": u["id"],
                "date": (u.get("created_at") or "")[:10],
            })
        for u in units[:5]:
            for lesson in db.list_lessons(u["id"])[:3]:
                recent_items.append({
                    "type": "lesson",
                    "title": lesson["title"] or f"Lesson {lesson.get('lesson_number', '')}",
                    "id": lesson["id"],
                    "date": (lesson.get("created_at") or "")[:10],
                })
        # Sort by date descending and take top 10
        recent_items.sort(key=lambda x: x["date"], reverse=True)
        recent_items = recent_items[:10]

        # Find active lesson (most recently shared)
        active_lesson = None
        for u in units[:5]:
            for lesson in db.list_lessons(u["id"]):
                if lesson.get("share_token"):
                    active_lesson = lesson
                    break
            if active_lesson:
                break

        # Teacher profile from config
        config_school = ""
        try:
            from eduagent.models import AppConfig
            cfg = AppConfig.load()
            config_school = cfg.teacher_profile.school
        except Exception:
            pass

        return templates.TemplateResponse(request, "dashboard.html", {
            "stats": stats,
            "units": units,
            "persona_name": persona_name,
            "persona": persona_data,
            "recent_items": recent_items,
            "active_lesson": active_lesson,
            "config_school": config_school,
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

    @app.get("/settings", response_class=HTMLResponse)
    async def settings_page(request: Request):
        from eduagent.config import get_api_key, mask_api_key
        from eduagent.models import AppConfig
        from eduagent.state_standards import (
            get_framework_description,
            list_states,
        )

        cfg = AppConfig.load()
        db = get_db()
        teacher = db.get_default_teacher()
        persona_data = None
        if teacher and teacher.get("persona_json"):
            try:
                persona_data = json.loads(teacher["persona_json"])
            except (json.JSONDecodeError, TypeError):
                pass

        teacher_state = cfg.teacher_profile.state if hasattr(cfg, "teacher_profile") else ""
        teacher_subjects = cfg.teacher_profile.subjects if hasattr(cfg, "teacher_profile") else []
        teacher_grades = cfg.teacher_profile.grade_levels if hasattr(cfg, "teacher_profile") else []

        # Build framework info for selected state
        state_frameworks = []
        if teacher_state:
            from eduagent.state_standards import STATE_STANDARDS_CONFIG
            state_cfg = STATE_STANDARDS_CONFIG.get(teacher_state, {})
            for subj_key in ("math", "ela", "science", "social_studies"):
                code = state_cfg.get(subj_key, "")
                if code:
                    state_frameworks.append({
                        "label": subj_key.replace("_", " ").title(),
                        "code": code,
                        "description": get_framework_description(code),
                    })

        return templates.TemplateResponse(request, "settings.html", {
            "config": cfg,
            "persona": persona_data,
            "anthropic_key_masked": mask_api_key(get_api_key("anthropic")),
            "openai_key_masked": mask_api_key(get_api_key("openai")),
            "states": list_states(),
            "teacher_state": teacher_state,
            "teacher_subjects": teacher_subjects,
            "teacher_grades": teacher_grades,
            "state_frameworks": state_frameworks,
        })

    @app.get("/stats", response_class=HTMLResponse)
    async def stats_page(request: Request):
        db = get_db()
        teacher = db.get_default_teacher()
        teacher_id = teacher["id"] if teacher else "local-teacher"

        from eduagent.analytics import get_teacher_stats
        stats_data = get_teacher_stats(teacher_id)

        return templates.TemplateResponse(request, "stats.html", {
            "stats": stats_data,
            "teacher_id": teacher_id,
        })

    @app.get("/lesson/{lesson_id}", response_class=HTMLResponse)
    async def lesson_page(request: Request, lesson_id: str):
        db = get_db()
        lesson_row = db.get_lesson(lesson_id)
        if not lesson_row:
            return HTMLResponse("<h1>Lesson not found</h1>", status_code=404)
        lesson_data = json.loads(lesson_row["lesson_json"]) if lesson_row["lesson_json"] else {}
        materials_data = json.loads(lesson_row["materials_json"]) if lesson_row.get("materials_json") else None
        scores_data = json.loads(lesson_row["scores_json"]) if lesson_row.get("scores_json") else None
        feedback_list = db.get_feedback_for_lesson(lesson_id)
        return templates.TemplateResponse(request, "lesson.html", {
            "lesson": lesson_row,
            "lesson_data": lesson_data,
            "materials": materials_data,
            "scores": scores_data,
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

    @app.get("/analytics", response_class=HTMLResponse)
    async def analytics_page(request: Request):
        from eduagent.analytics import get_teacher_stats

        db = get_db()
        teacher = db.get_default_teacher()
        teacher_id = teacher["id"] if teacher else "local-teacher"
        stats_data = get_teacher_stats(teacher_id)

        # Topic frequency — count lessons per title
        topic_frequency: list[dict] = []
        try:
            from eduagent.state import _get_conn, init_db

            init_db()
            conn = _get_conn()
            conn.row_factory = __import__("sqlite3").Row
            rows = conn.execute(
                "SELECT title as topic, COUNT(*) as count FROM generated_lessons"
                " WHERE teacher_id = ? AND title IS NOT NULL"
                " GROUP BY title ORDER BY count DESC LIMIT 10",
                (teacher_id,),
            ).fetchall()
            topic_frequency = [{"topic": r["topic"], "count": r["count"]} for r in rows]
            conn.close()
        except Exception:
            pass

        # Student question frequency by hour
        question_by_hour: dict[int, int] = {}
        try:
            init_db()
            conn = _get_conn()
            conn.row_factory = __import__("sqlite3").Row
            rows = conn.execute(
                "SELECT CAST(strftime('%H', created_at) AS INTEGER) as hour, COUNT(*) as count"
                " FROM chat_messages WHERE role='user'"
                " GROUP BY hour ORDER BY hour",
            ).fetchall()
            question_by_hour = {r["hour"]: r["count"] for r in rows}
            conn.close()
        except Exception:
            pass

        # Quality trend — weekly average ratings
        quality_trend: list[dict] = []
        try:
            init_db()
            conn = _get_conn()
            conn.row_factory = __import__("sqlite3").Row
            rows = conn.execute(
                "SELECT strftime('%Y-W%W', created_at) as week, AVG(rating) as avg_rating"
                " FROM generated_lessons"
                " WHERE teacher_id = ? AND rating IS NOT NULL"
                " GROUP BY week ORDER BY week DESC LIMIT 12",
                (teacher_id,),
            ).fetchall()
            quality_trend = [
                {
                    "week": r["week"],
                    "week_short": r["week"][-3:] if r["week"] else "",
                    "avg_rating": round(r["avg_rating"], 1),
                }
                for r in reversed(rows)
            ]
            conn.close()
        except Exception:
            pass

        # Top student questions this week
        top_questions: list[dict] = []
        try:
            init_db()
            conn = _get_conn()
            conn.row_factory = __import__("sqlite3").Row
            rows = conn.execute(
                "SELECT content as question, COUNT(*) as count"
                " FROM chat_messages WHERE role='user'"
                " AND created_at >= datetime('now', '-7 days')"
                " GROUP BY content ORDER BY count DESC LIMIT 10",
            ).fetchall()
            top_questions = [{"question": r["question"], "count": r["count"]} for r in rows]
            conn.close()
        except Exception:
            pass

        # Teacher usage by day of week
        usage_by_day: dict[str, int] = {}
        try:
            init_db()
            conn = _get_conn()
            conn.row_factory = __import__("sqlite3").Row
            day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
            rows = conn.execute(
                "SELECT CAST(strftime('%w', created_at) AS INTEGER) as dow, COUNT(*) as count"
                " FROM generated_lessons WHERE teacher_id = ?"
                " GROUP BY dow ORDER BY dow",
                (teacher_id,),
            ).fetchall()
            usage_by_day = {day_names[r["dow"]]: r["count"] for r in rows}
            conn.close()
        except Exception:
            pass

        return templates.TemplateResponse(request, "analytics.html", {
            "stats": stats_data,
            "topic_frequency": topic_frequency,
            "question_by_hour": question_by_hour,
            "quality_trend": quality_trend,
            "top_questions": top_questions,
            "usage_by_day": usage_by_day,
        })

    @app.get("/profile", response_class=HTMLResponse)
    async def profile_page(request: Request):
        from eduagent.config import get_api_key, mask_api_key
        from eduagent.models import AppConfig
        from eduagent.state_standards import (
            get_framework_description,
            list_states,
        )

        cfg = AppConfig.load()
        db = get_db()
        teacher = db.get_default_teacher()
        persona_data = None
        if teacher and teacher.get("persona_json"):
            try:
                persona_data = json.loads(teacher["persona_json"])
            except (json.JSONDecodeError, TypeError):
                pass

        profile = cfg.teacher_profile

        # Build framework info for selected state
        state_frameworks = []
        if profile.state:
            from eduagent.state_standards import STATE_STANDARDS_CONFIG

            state_cfg = STATE_STANDARDS_CONFIG.get(profile.state, {})
            for subj_key in ("math", "ela", "science", "social_studies"):
                code = state_cfg.get(subj_key, "")
                if code:
                    state_frameworks.append({
                        "label": subj_key.replace("_", " ").title(),
                        "code": code,
                        "description": get_framework_description(code),
                    })

        # Mask telegram token
        telegram_token_masked = ""
        if cfg.telegram_bot_token:
            telegram_token_masked = mask_api_key(cfg.telegram_bot_token)

        return templates.TemplateResponse(request, "profile.html", {
            "profile": profile,
            "persona": persona_data,
            "states": list_states(),
            "state_frameworks": state_frameworks,
            "anthropic_key_masked": mask_api_key(get_api_key("anthropic")),
            "openai_key_masked": mask_api_key(get_api_key("openai")),
            "telegram_token_masked": telegram_token_masked,
        })

    return app


# Module-level app for `uvicorn eduagent.api.server:app`
app = create_app()
