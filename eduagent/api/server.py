"""FastAPI web server for EDUagent — REST API + server-side rendered teacher dashboard."""

from __future__ import annotations

import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from eduagent.database import Database

logger = logging.getLogger(__name__)

# Paths
_PKG_DIR = Path(__file__).parent
_TEMPLATE_DIR = _PKG_DIR / "templates"
_STATIC_DIR = _PKG_DIR / "static"

# Rate limiter (shared across the app)
limiter = Limiter(key_func=get_remote_address)

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

    # Rate limiting middleware
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # CORS middleware — restrict origins in production via EDUAGENT_CORS_ORIGINS env var
    cors_origins_raw = os.environ.get("EDUAGENT_CORS_ORIGINS", "")
    cors_origins = [o.strip() for o in cors_origins_raw.split(",") if o.strip()] if cors_origins_raw else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
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
    from eduagent.api.routes.lessons import router as lessons_router
    from eduagent.api.routes.school import router as school_router
    from eduagent.api.routes.settings import router as settings_router
    from eduagent.api.routes.tools import router as tools_router
    from eduagent.api.routes.waitlist import router as waitlist_router

    app.include_router(ingest_router, prefix="/api")
    app.include_router(generate_router, prefix="/api")
    app.include_router(chat_router, prefix="/api")
    app.include_router(feedback_router, prefix="/api")
    app.include_router(export_router, prefix="/api")
    app.include_router(settings_router, prefix="/api")
    app.include_router(school_router, prefix="/api")
    app.include_router(lessons_router, prefix="/api")
    app.include_router(tools_router, prefix="/api")
    app.include_router(waitlist_router, prefix="/api")

    # ── Page routes (server-side rendered) ───────────────────────────

    # Landing page path
    landing_dir = Path(__file__).parent.parent / "landing"

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        db = get_db()
        teacher = db.get_default_teacher()
        has_persona = teacher is not None and teacher.get("persona_json") is not None
        onboarding_complete = db.is_onboarding_complete()

        # If logged in (persona exists and onboarding done), redirect to dashboard
        if has_persona and onboarding_complete:
            return RedirectResponse(url="/dashboard", status_code=302)

        # Otherwise serve the landing page
        landing_file = landing_dir / "index.html"
        if landing_file.exists():
            return HTMLResponse(landing_file.read_text())

        # Fallback to template-based index
        stats = db.get_stats()
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
            "active_nav": "home",
        })

    @app.get("/landing", response_class=HTMLResponse)
    async def landing_page():
        """Always serve the landing page (bypasses redirect)."""
        landing_file = landing_dir / "index.html"
        if landing_file.exists():
            return HTMLResponse(landing_file.read_text())
        return HTMLResponse("<h1>Landing page not found</h1>", status_code=404)

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
            "active_nav": "home",
        })

    @app.get("/lessons", response_class=HTMLResponse)
    async def lessons_list_page(request: Request):
        """Lesson list page: all generated lessons, filterable, newest first."""
        db = get_db()
        subject_filter = request.query_params.get("subject", "")
        grade_filter = request.query_params.get("grade", "")

        # Gather all lessons across all units
        all_lessons: list[dict] = []
        units = db.list_units()
        for u in units:
            if subject_filter and u.get("subject", "").lower() != subject_filter.lower():
                continue
            if grade_filter and u.get("grade_level", "").lower() != grade_filter.lower():
                continue
            for lesson in db.list_lessons(u["id"]):
                lesson_data = {}
                if lesson.get("lesson_json"):
                    try:
                        lesson_data = json.loads(lesson["lesson_json"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                quality_score = None
                if lesson.get("scores_json"):
                    try:
                        scores = json.loads(lesson["scores_json"])
                        quality_score = scores.get("overall") or scores.get("total")
                    except (json.JSONDecodeError, TypeError):
                        pass
                all_lessons.append({
                    "id": lesson["id"],
                    "title": lesson.get("title") or lesson_data.get("title") or "Untitled",
                    "subject": u.get("subject", ""),
                    "grade_level": u.get("grade_level", ""),
                    "date": (lesson.get("created_at") or "")[:10],
                    "quality_score": quality_score,
                    "rating": lesson.get("rating"),
                    "share_token": lesson.get("share_token"),
                })

        # Sort newest first
        all_lessons.sort(key=lambda x: x["date"], reverse=True)

        # Get unique subjects and grades for filters
        all_subjects = sorted({u.get("subject", "") for u in units if u.get("subject")})
        all_grades = sorted({u.get("grade_level", "") for u in units if u.get("grade_level")})

        # Build a simple HTML page
        rows_html = ""
        for les in all_lessons:
            score_display = f"{les['quality_score']}" if les.get("quality_score") else "-"
            rating_display = f"{'*' * les['rating']}" if les.get("rating") else "-"
            share_btn = f'<a href="/shared/{les["share_token"]}">Share</a>' if les.get("share_token") else ""
            rows_html += (
                f"<tr>"
                f"<td><a href='/lesson/{les['id']}'>{les['title']}</a></td>"
                f"<td>{les['subject']}</td>"
                f"<td>{les['grade_level']}</td>"
                f"<td>{les['date']}</td>"
                f"<td>{score_display}</td>"
                f"<td>{rating_display}</td>"
                f"<td>{share_btn}</td>"
                f"</tr>"
            )

        filter_html = ""
        if all_subjects:
            opts = "".join(
                f"<option value='{s}' {'selected' if s == subject_filter else ''}>{s}</option>"
                for s in all_subjects
            )
            filter_html += (
                "<select name='subject' onchange='this.form.submit()'>"
                f"<option value=''>All Subjects</option>{opts}</select> "
            )
        if all_grades:
            opts = "".join(
                f"<option value='{g}' {'selected' if g == grade_filter else ''}>{g}</option>"
                for g in all_grades
            )
            filter_html += (
                "<select name='grade' onchange='this.form.submit()'>"
                f"<option value=''>All Grades</option>{opts}</select>"
            )

        count_msg = (
            f"<p style='color:#999;margin-top:24px'>Showing {len(all_lessons)} lesson(s)</p>"
            if all_lessons
            else "<p>No lessons yet. <a href='/generate'>Generate one.</a></p>"
        )
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Lessons - EDUagent</title>
<style>
body {{ font-family: -apple-system, system-ui, sans-serif;
  max-width: 1000px; margin: 20px auto; padding: 0 20px; }}
h1 {{ color: #1a73e8; }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ padding: 10px 12px; text-align: left;
  border-bottom: 1px solid #e0e0e0; }}
th {{ background: #f5f5f5; font-weight: 600; }}
tr:hover {{ background: #f8f9fa; }}
a {{ color: #1a73e8; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
.btn {{ display: inline-block; background: #1a73e8; color: white;
  padding: 10px 24px; border-radius: 6px;
  text-decoration: none; margin: 12px 0; }}
select {{ padding: 6px 10px; border-radius: 4px;
  border: 1px solid #ccc; margin-right: 8px; }}
.filters {{ margin: 16px 0; }}
</style></head><body>
<h1>All Lessons</h1>
<a href="/generate" class="btn">Generate New Lesson</a>
<form class="filters" method="get">{filter_html}</form>
<table>
<tr><th>Title</th><th>Subject</th><th>Grade</th>
<th>Date</th><th>Score</th><th>Rating</th><th></th></tr>
{rows_html}
</table>
{count_msg}
</body></html>"""
        return HTMLResponse(html)

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
            "active_nav": "generate",
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

        # Get class codes for management
        class_codes_list: list[dict] = []
        try:
            from eduagent.state import _get_conn as _state_conn2
            from eduagent.state import init_db as _state_init2
            _state_init2()
            teacher_id_for_codes = teacher["id"] if teacher else "local-teacher"
            with _state_conn2() as sconn2:
                cc_rows2 = sconn2.execute(
                    "SELECT class_code, name, topic, expires_at, created_at FROM classes WHERE teacher_id = ?",
                    (teacher_id_for_codes,),
                ).fetchall()
                class_codes_list = [dict(r) for r in cc_rows2]
        except Exception:
            pass

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
            "class_codes": class_codes_list,
            "active_nav": "settings",
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
        try:
            lesson_data = json.loads(lesson_row["lesson_json"]) if lesson_row["lesson_json"] else {}
        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning("Failed to parse lesson_json for %s: %s", lesson_id, exc)
            lesson_data = {}
        try:
            materials_data = json.loads(lesson_row["materials_json"]) if lesson_row.get("materials_json") else None
        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning("Failed to parse materials_json for %s: %s", lesson_id, exc)
            materials_data = None
        try:
            scores_data = json.loads(lesson_row["scores_json"]) if lesson_row.get("scores_json") else None
        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning("Failed to parse scores_json for %s: %s", lesson_id, exc)
            scores_data = None
        feedback_list = db.get_feedback_for_lesson(lesson_id)
        # Build embed snippet for student chatbot
        embed_snippet = (
            f'<script src="/static/student-chat-widget.js" '
            f'data-lesson-id="{lesson_id}" '
            f'data-api-url="/api/chat"></script>'
        )

        # Get class codes for this lesson (if any are active)
        class_codes = []
        try:
            from eduagent.state import _get_conn as _state_conn
            from eduagent.state import init_db as _state_init
            _state_init()
            with _state_conn() as sconn:
                cc_rows = sconn.execute(
                    "SELECT class_code, name FROM classes WHERE active_lesson_id = ?",
                    (lesson_id,),
                ).fetchall()
                class_codes = [{"code": r["class_code"], "name": r["name"]} for r in cc_rows]
        except Exception:
            pass

        return templates.TemplateResponse(request, "lesson.html", {
            "lesson": lesson_row,
            "lesson_data": lesson_data,
            "materials": materials_data,
            "scores": scores_data,
            "feedback_list": feedback_list,
            "share_url": f"/shared/{lesson_row['share_token']}",
            "embed_snippet": embed_snippet,
            "class_codes": class_codes,
        })

    @app.get("/share/{token}", response_class=HTMLResponse)
    @app.get("/shared/{token}", response_class=HTMLResponse)
    async def share_page(request: Request, token: str):
        db = get_db()
        lesson_row = db.get_lesson_by_token(token)
        if not lesson_row:
            return HTMLResponse("<h1>Lesson not found</h1>", status_code=404)
        try:
            lesson_data = json.loads(lesson_row["lesson_json"]) if lesson_row["lesson_json"] else {}
        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning("Failed to parse shared lesson_json for token %s: %s", token, exc)
            lesson_data = {}
        return templates.TemplateResponse(request, "lesson.html", {
            "lesson": lesson_row,
            "lesson_data": lesson_data,
            "materials": None,
            "feedback_list": [],
            "share_url": f"/shared/{token}",
            "is_shared": True,
        })

    @app.get("/student/{class_code}", response_class=HTMLResponse)
    async def student_class_page(request: Request, class_code: str):
        """Minimal student-facing page for a class code."""
        from eduagent.state import _get_conn, init_db
        init_db()
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM classes WHERE class_code = ?", (class_code,)
            ).fetchone()

        if not row:
            return HTMLResponse("<h1>Class not found</h1>", status_code=404)

        class_name = row["name"] if "name" in row.keys() else class_code
        class_topic = row["topic"] if "topic" in row.keys() else ""
        teacher_id = row["teacher_id"]

        # Get teacher name
        teacher_name = teacher_id
        db = get_db()
        teacher = db.get_teacher(teacher_id)
        if teacher:
            teacher_name = teacher.get("name") or teacher_id

        # Get recent lesson topics from active lesson
        lesson_topics = []
        if row["active_lesson_json"]:
            try:
                lesson_data = json.loads(row["active_lesson_json"])
                lesson_topics.append(lesson_data.get("title", ""))
            except (json.JSONDecodeError, TypeError):
                pass

        bot_link = f"https://t.me/eduagent_bot?start={class_code}"

        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{class_name or class_code} - EDUagent</title>
<style>
body {{
  font-family: -apple-system, system-ui, sans-serif;
  max-width: 600px; margin: 40px auto;
  padding: 0 20px; background: #f8f9fa;
}}
.card {{
  background: white; border-radius: 12px; padding: 32px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1); text-align: center;
}}
h1 {{ color: #1a73e8; margin-bottom: 8px; }}
.teacher {{ color: #666; margin-bottom: 24px; }}
.code {{
  font-size: 2em; font-weight: bold; color: #1a73e8;
  background: #e8f0fe; padding: 12px 24px; border-radius: 8px;
  display: inline-block; margin: 16px 0; letter-spacing: 2px;
}}
.qr {{ margin: 24px 0; }}
.qr img {{ max-width: 200px; }}
.topic {{
  background: #e8f5e9; padding: 8px 16px;
  border-radius: 6px; margin: 8px 4px; display: inline-block;
}}
.join-btn {{
  display: inline-block; background: #1a73e8; color: white;
  padding: 14px 32px; border-radius: 8px;
  text-decoration: none; font-size: 1.1em; margin-top: 16px;
}}
.join-btn:hover {{ background: #1557b0; }}
.privacy {{ color: #999; font-size: 0.85em; margin-top: 24px; }}
</style></head><body>
<div class="card">
<h1>{class_name or class_code}</h1>
<p class="teacher">Teacher: {teacher_name}</p>
<div class="code">{class_code}</div>
{''.join(f'<span class="topic">{t}</span>' for t in lesson_topics if t)}
{f'<p><strong>Current Topic:</strong> {class_topic}</p>' if class_topic else ''}
<p style="margin-top:24px"><strong>Scan to chat on Telegram:</strong></p>
<div class="qr"><img src="https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={bot_link}" alt="QR Code"></div>
<a href="{bot_link}" class="join-btn">Open in Telegram</a>
<p class="privacy">No student data is displayed on this page.</p>
</div></body></html>"""

        return HTMLResponse(html)

    @app.get("/analytics", response_class=HTMLResponse)
    async def analytics_page(request: Request):
        from eduagent.analytics import get_teacher_stats

        db = get_db()
        teacher = db.get_default_teacher()
        teacher_id = teacher["id"] if teacher else "local-teacher"
        stats_data = get_teacher_stats(teacher_id)

        def _safe_query(sql: str, params: tuple = ()) -> list[dict]:
            """Run a read query against state DB, returning list of Row dicts."""
            try:
                from eduagent.state import _get_conn, init_db
                init_db()
                with _get_conn() as conn:
                    rows = conn.execute(sql, params).fetchall()
                    result = [dict(r) for r in rows]
                return result
            except Exception:
                return []

        # Topic frequency
        topic_frequency = _safe_query(
            "SELECT title as topic, COUNT(*) as count FROM generated_lessons"
            " WHERE teacher_id = ? AND title IS NOT NULL"
            " GROUP BY title ORDER BY count DESC LIMIT 10",
            (teacher_id,),
        )

        # Daily lessons generated (last 7 days)
        daily_lessons: list[dict] = []
        day_names_short = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        today = datetime.now().date()
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            daily_lessons.append({
                "date": d.isoformat(),
                "label": day_names_short[d.weekday()],
                "count": 0,
            })
        rows = _safe_query(
            "SELECT DATE(created_at) as day, COUNT(*) as count FROM generated_lessons"
            " WHERE teacher_id = ? AND created_at >= datetime('now', '-7 days')"
            " GROUP BY day ORDER BY day",
            (teacher_id,),
        )
        day_counts = {r["day"]: r["count"] for r in rows}
        for item in daily_lessons:
            item["count"] = day_counts.get(item["date"], 0)

        # Daily student questions (last 7 days)
        daily_questions: list[dict] = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            daily_questions.append({
                "date": d.isoformat(),
                "label": day_names_short[d.weekday()],
                "count": 0,
            })
        q_rows = _safe_query(
            "SELECT DATE(created_at) as day, COUNT(*) as count FROM chat_messages"
            " WHERE role='user' AND created_at >= datetime('now', '-7 days')"
            " GROUP BY day ORDER BY day",
        )
        q_counts = {r["day"]: r["count"] for r in q_rows}
        for item in daily_questions:
            item["count"] = q_counts.get(item["date"], 0)

        # Quality trend — weekly average ratings
        quality_trend_rows = _safe_query(
            "SELECT strftime('%Y-W%W', created_at) as week, AVG(rating) as avg_rating"
            " FROM generated_lessons"
            " WHERE teacher_id = ? AND rating IS NOT NULL"
            " GROUP BY week ORDER BY week DESC LIMIT 12",
            (teacher_id,),
        )
        quality_trend = [
            {
                "week": r["week"],
                "week_short": r["week"][-3:] if r.get("week") else "",
                "avg_rating": round(r["avg_rating"], 1) if r.get("avg_rating") else 0,
            }
            for r in reversed(quality_trend_rows)
        ]

        # Top student questions this week
        top_questions = _safe_query(
            "SELECT content as question, COUNT(*) as count"
            " FROM chat_messages WHERE role='user'"
            " AND created_at >= datetime('now', '-7 days')"
            " GROUP BY content ORDER BY count DESC LIMIT 10",
        )

        return templates.TemplateResponse(request, "analytics.html", {
            "stats": stats_data,
            "topic_frequency": topic_frequency,
            "daily_lessons": daily_lessons,
            "daily_questions": daily_questions,
            "quality_trend": quality_trend,
            "top_questions": top_questions,
            "active_nav": "analytics",
        })

    @app.get("/library", response_class=HTMLResponse)
    async def library_page(request: Request):
        """Library view — all units and lessons, aliased from dashboard."""
        db = get_db()
        stats = db.get_stats()
        units = db.list_units()
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
        recent_items.sort(key=lambda x: x["date"], reverse=True)
        recent_items = recent_items[:10]

        active_lesson = None
        for u in units[:5]:
            for lesson in db.list_lessons(u["id"]):
                if lesson.get("share_token"):
                    active_lesson = lesson
                    break
            if active_lesson:
                break

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
            "active_nav": "library",
        })

    @app.get("/students", response_class=HTMLResponse)
    async def students_page(request: Request):
        """Students page — chat activity and student engagement."""
        db = get_db()
        stats = db.get_stats()

        # Gather per-lesson chat stats
        lesson_chats: list[dict] = []
        units = db.list_units()
        for u in units[:10]:
            for lesson in db.list_lessons(u["id"]):
                history = db.get_chat_history(lesson["id"], limit=100)
                user_msgs = [m for m in history if m.get("role") == "user"]
                if user_msgs:
                    lesson_chats.append({
                        "lesson_title": lesson.get("title") or "Untitled",
                        "lesson_id": lesson["id"],
                        "question_count": len(user_msgs),
                        "last_question": (user_msgs[0].get("created_at") or "")[:16] if user_msgs else "",
                    })
        lesson_chats.sort(key=lambda x: x["question_count"], reverse=True)

        return templates.TemplateResponse(request, "students.html", {
            "stats": stats,
            "lesson_chats": lesson_chats[:20],
            "active_nav": "students",
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
