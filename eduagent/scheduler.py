"""APScheduler-based task scheduler for autonomous EDUagent behavior.

Gives EDUagent scheduled tasks like OpenClaw's cron jobs, adapted for teachers:
- morning-prep: review today's classes, auto-generate missing lessons
- weekly-plan: draft next week's lesson plans
- feedback-digest: summarize today's ratings and interactions
- memory-compress: compress old daily notes into memory highlights
- student-digest: summarize student bot interactions for the week

The scheduler is optional -- the app works fine without it running.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

# ── Config paths ───────────────────────────────────────────────────────

SCHEDULE_CONFIG_PATH = Path.home() / ".eduagent" / "schedule.json"


# ── Built-in task definitions ──────────────────────────────────────────

# All tasks start DISABLED. Teachers opt in to what they want.
# Schedules and enabled state are fully editable via CLI or schedule.json.
DEFAULT_TASKS: dict[str, dict[str, Any]] = {
    "morning-prep": {
        "description": "Review today's classes. Auto-generate missing lesson drafts and notify via Telegram.",
        "cron": {"hour": "6", "minute": "0"},
        "enabled": False,
    },
    "weekly-plan": {
        "description": "Draft next week's lesson plans based on unit pacing. Send summary via Telegram.",
        "cron": {"day_of_week": "sun", "hour": "19", "minute": "0"},
        "enabled": False,
    },
    "feedback-digest": {
        "description": "Summarize today's ratings and student interactions. Append to daily notes.",
        "cron": {"hour": "20", "minute": "0"},
        "enabled": False,
    },
    "memory-compress": {
        "description": "Compress old daily notes into memory.md highlights using the LLM.",
        "cron": {"day_of_week": "sun", "hour": "5", "minute": "0"},
        "enabled": False,
    },
    "student-digest": {
        "description": "Summarize student bot interactions for the week.",
        "cron": {"day_of_week": "fri", "hour": "16", "minute": "0"},
        "enabled": False,
    },
}


# ── Schedule config persistence ────────────────────────────────────────


def load_schedule_config() -> dict[str, dict[str, Any]]:
    """Load schedule config from disk, merging with defaults."""
    config = {}
    for name, task_def in DEFAULT_TASKS.items():
        config[name] = {
            "description": task_def["description"],
            "cron": dict(task_def["cron"]),
            "enabled": task_def["enabled"],
        }

    if SCHEDULE_CONFIG_PATH.exists():
        try:
            saved = json.loads(SCHEDULE_CONFIG_PATH.read_text(encoding="utf-8"))
            for name, overrides in saved.items():
                if name in config:
                    if "cron" in overrides:
                        config[name]["cron"] = overrides["cron"]
                    if "enabled" in overrides:
                        config[name]["enabled"] = overrides["enabled"]
                else:
                    # Custom task
                    config[name] = overrides
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load schedule config: %s", exc)

    return config


def save_schedule_config(config: dict[str, dict[str, Any]]) -> None:
    """Persist schedule config to disk."""
    SCHEDULE_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULE_CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")


def enable_task(name: str) -> bool:
    """Enable a scheduled task. Returns True if the task exists."""
    config = load_schedule_config()
    if name not in config:
        return False
    config[name]["enabled"] = True
    save_schedule_config(config)
    return True


def disable_task(name: str) -> bool:
    """Disable a scheduled task. Returns True if the task exists."""
    config = load_schedule_config()
    if name not in config:
        return False
    config[name]["enabled"] = False
    save_schedule_config(config)
    return True


def set_task_schedule(name: str, cron_expr: str) -> bool:
    """Set a task's cron schedule from a cron expression string.

    Accepts simplified cron: "6:00" (daily at 6am), "sun 19:00", etc.
    Also accepts full cron fields as key=value: "hour=6 minute=0".

    Returns True if the task exists and was updated.
    """
    config = load_schedule_config()
    if name not in config:
        return False

    cron_dict = _parse_cron_expr(cron_expr)
    config[name]["cron"] = cron_dict
    save_schedule_config(config)
    return True


def _parse_cron_expr(expr: str) -> dict[str, str]:
    """Parse a simplified cron expression into APScheduler cron kwargs.

    Formats:
      "6:00"          -> {"hour": "6", "minute": "0"}
      "sun 19:00"     -> {"day_of_week": "sun", "hour": "19", "minute": "0"}
      "hour=6 minute=0" -> {"hour": "6", "minute": "0"}
    """
    expr = expr.strip()

    # Key=value format
    if "=" in expr:
        result = {}
        for part in expr.split():
            if "=" in part:
                k, v = part.split("=", 1)
                result[k.strip()] = v.strip()
        return result

    parts = expr.split()

    # Day of week + time
    days = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
    if len(parts) == 2 and parts[0].lower() in days:
        day = parts[0].lower()
        time_parts = parts[1].split(":")
        return {
            "day_of_week": day,
            "hour": str(int(time_parts[0])),
            "minute": str(int(time_parts[1])) if len(time_parts) > 1 else "0",
        }

    # Just time
    if ":" in parts[0]:
        time_parts = parts[0].split(":")
        return {
            "hour": str(int(time_parts[0])),
            "minute": str(int(time_parts[1])) if len(time_parts) > 1 else "0",
        }

    return {"hour": expr, "minute": "0"}


# ── Task implementations (stubs that call existing eduagent functions) ──


async def _task_morning_prep() -> str:
    """Morning prep: check for missing lessons, auto-generate drafts."""
    from eduagent.workspace import append_daily_note

    append_daily_note("Morning prep task ran.", category="scheduler")

    # Check for lessons due today
    try:
        from eduagent.database import Database
        db = Database()
        stats = db.get_stats()
        summary = f"Morning prep: {stats.get('lessons', 0)} lessons in database, {stats.get('units', 0)} units."
        db.close()
    except Exception as exc:
        summary = f"Morning prep: could not query database ({exc})"

    append_daily_note(summary, category="morning-prep")
    logger.info("morning-prep: %s", summary)
    return summary


async def _task_weekly_plan() -> str:
    """Weekly plan: draft next week's lesson plans."""
    from eduagent.workspace import append_daily_note

    append_daily_note("Weekly plan task ran.", category="scheduler")
    summary = "Weekly plan: drafted outlines for next week (stub)."
    append_daily_note(summary, category="weekly-plan")
    logger.info("weekly-plan: %s", summary)
    return summary


async def _task_feedback_digest() -> str:
    """Feedback digest: summarize today's ratings and update the memory engine."""
    from eduagent.workspace import append_daily_note

    try:
        from eduagent.database import Database
        from eduagent.feedback import analyze_feedback

        db = Database()
        analysis = analyze_feedback(db, days=1)
        db.close()

        total = analysis.get("total_feedback", 0)
        avg = analysis.get("avg_rating", 0.0)
        summary = f"Feedback digest: {total} ratings today, avg {avg}/5."
    except Exception as exc:
        summary = f"Feedback digest: could not analyze ({exc})"

    # Update memory engine stats
    try:
        from eduagent.memory_engine import get_improvement_stats

        stats = get_improvement_stats()
        if stats["total_rated"] > 0:
            summary += (
                f" Memory engine: {stats['total_patterns']} patterns learned, "
                f"avg {stats['avg_rating']}/5, trend: {stats['trend']}."
            )
    except Exception as exc:
        logger.debug("Memory engine stats failed: %s", exc)

    append_daily_note(summary, category="feedback-digest")
    logger.info("feedback-digest: %s", summary)
    return summary


async def _task_memory_compress() -> str:
    """Memory compress: summarize old notes into memory highlights."""
    from eduagent.workspace import NOTES_DIR, append_daily_note

    # Count old notes files
    note_files = sorted(NOTES_DIR.glob("*.md")) if NOTES_DIR.exists() else []
    old_count = max(0, len(note_files) - 7)  # Keep last 7 days
    summary = f"Memory compress: {len(note_files)} note files, {old_count} eligible for compression (stub)."
    append_daily_note(summary, category="memory-compress")
    logger.info("memory-compress: %s", summary)
    return summary


async def _task_student_digest() -> str:
    """Student digest: summarize student interactions for the week."""
    from eduagent.workspace import append_daily_note

    try:
        from eduagent.state import _get_conn, init_db

        init_db()
        with _get_conn() as conn:
            row = conn.execute("SELECT COUNT(*) as c FROM student_questions").fetchone()
            q_count = row["c"] if row else 0
        summary = f"Student digest: {q_count} total student questions in database."
    except Exception as exc:
        summary = f"Student digest: could not query ({exc})"

    append_daily_note(summary, category="student-digest")
    logger.info("student-digest: %s", summary)
    return summary


# Map task names to their async implementations
TASK_IMPLEMENTATIONS: dict[str, Callable[[], Any]] = {
    "morning-prep": _task_morning_prep,
    "weekly-plan": _task_weekly_plan,
    "feedback-digest": _task_feedback_digest,
    "memory-compress": _task_memory_compress,
    "student-digest": _task_student_digest,
}


# ── Manual run ─────────────────────────────────────────────────────────


async def run_task(name: str) -> str:
    """Run a task immediately by name. Returns the task's summary string."""
    config = load_schedule_config()
    if name not in config:
        raise ValueError(f"Unknown task: {name}. Available: {', '.join(config.keys())}")

    impl = TASK_IMPLEMENTATIONS.get(name)
    if impl is None:
        raise ValueError(f"No implementation for task: {name}")

    from eduagent.workspace import append_daily_note

    append_daily_note(f"Manual run of '{name}' started.", category="scheduler")
    result = await impl()
    return result


# ── Scheduler class ────────────────────────────────────────────────────


class EduScheduler:
    """APScheduler-based task scheduler for EDUagent.

    Uses AsyncIOScheduler with CronTrigger for scheduled tasks.
    The scheduler is entirely optional and does not block normal usage.
    """

    def __init__(self) -> None:
        self._scheduler = None
        self._config = load_schedule_config()

    def _get_scheduler(self):
        """Lazy-init the APScheduler instance."""
        if self._scheduler is None:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            self._scheduler = AsyncIOScheduler()
        return self._scheduler

    def register_jobs(self) -> None:
        """Register all enabled tasks as APScheduler jobs."""
        from apscheduler.triggers.cron import CronTrigger

        scheduler = self._get_scheduler()

        for name, task_cfg in self._config.items():
            if not task_cfg.get("enabled", False):
                continue

            impl = TASK_IMPLEMENTATIONS.get(name)
            if impl is None:
                logger.warning("No implementation for task '%s', skipping.", name)
                continue

            cron_kwargs = task_cfg.get("cron", {})
            trigger = CronTrigger(**cron_kwargs)

            scheduler.add_job(
                impl,
                trigger=trigger,
                id=name,
                name=name,
                replace_existing=True,
            )
            logger.info("Registered task '%s' with cron %s", name, cron_kwargs)

    def start(self) -> None:
        """Start the scheduler (call from within a running event loop)."""
        scheduler = self._get_scheduler()
        self.register_jobs()
        scheduler.start()
        logger.info("EDUagent scheduler started with %d job(s).", len(scheduler.get_jobs()))

    def stop(self) -> None:
        """Stop the scheduler gracefully."""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("EDUagent scheduler stopped.")

    def get_jobs_info(self) -> list[dict[str, Any]]:
        """Return info about all configured tasks (enabled or not)."""
        info: list[dict[str, Any]] = []
        scheduler = self._get_scheduler() if self._scheduler else None

        for name, task_cfg in self._config.items():
            entry: dict[str, Any] = {
                "name": name,
                "description": task_cfg.get("description", ""),
                "cron": task_cfg.get("cron", {}),
                "enabled": task_cfg.get("enabled", False),
                "next_run": None,
            }

            # Get next run time from APScheduler if running
            if scheduler and scheduler.running:
                job = scheduler.get_job(name)
                if job and job.next_run_time:
                    entry["next_run"] = job.next_run_time.isoformat()

            info.append(entry)

        return info

    @property
    def running(self) -> bool:
        return self._scheduler is not None and self._scheduler.running
