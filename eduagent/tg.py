"""Lightweight Telegram bot -- no python-telegram-bot dependency.

Uses httpx (sync) for reliable Windows compatibility. Replaces the
457-dependency python-telegram-bot which had event loop conflicts,
TLS failures, and zero-retry bootstrap on Windows.

Usage:
    from eduagent.tg import EduAgentTelegramBot
    bot = EduAgentTelegramBot(token="YOUR_TOKEN")
    bot.run()
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import signal
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable

import httpx

logger = logging.getLogger(__name__)

_API_BASE = "https://api.telegram.org"
_MAX_MESSAGE_LENGTH = 4096

# Lock file for preventing multiple bot instances
_BOT_LOCK = Path.home() / ".eduagent" / "bot.lock"

# Error log path
_ERROR_LOG = Path.home() / ".eduagent" / "errors.log"


def _log_error(error: Exception) -> None:
    """Append error to the errors.log file."""
    try:
        _ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(_ERROR_LOG, "a") as f:
            import datetime
            f.write(
                f"[{datetime.datetime.now(datetime.timezone.utc).isoformat()}] "
                f"{type(error).__name__}: {error}\n"
            )
    except Exception:
        pass


def _check_bot_lock(force: bool = False) -> None:
    """Check if another bot instance is running."""
    if _BOT_LOCK.exists():
        try:
            pid = int(_BOT_LOCK.read_text(encoding="utf-8").strip())
            if pid != os.getpid():
                try:
                    os.kill(pid, 0)
                    if not force:
                        raise RuntimeError(
                            f"Another bot instance is already running (PID {pid}). "
                            f"Stop it first or use --force."
                        )
                    logger.warning("Force-removing stale lock for PID %d", pid)
                except OSError:
                    logger.info("Removing stale bot lock (PID %d)", pid)
        except (ValueError, OSError):
            logger.info("Removing invalid bot lock file")

    _BOT_LOCK.parent.mkdir(parents=True, exist_ok=True)
    _BOT_LOCK.write_text(str(os.getpid()), encoding="utf-8")


def _release_bot_lock() -> None:
    """Remove the lock file on shutdown."""
    try:
        if _BOT_LOCK.exists():
            pid = int(_BOT_LOCK.read_text(encoding="utf-8").strip())
            if pid == os.getpid():
                _BOT_LOCK.unlink()
    except Exception:
        pass


class TelegramAPI:
    """Thin sync wrapper around the Telegram Bot API using httpx."""

    def __init__(self, token: str, timeout: float = 60.0):
        self.token = token
        self._base = f"{_API_BASE}/bot{token}"
        self._client = httpx.Client(timeout=httpx.Timeout(timeout, connect=15.0))

    def close(self) -> None:
        self._client.close()

    def _call(self, method: str, **params: Any) -> dict:
        """Call a Telegram Bot API method with retry on network errors."""
        url = f"{self._base}/{method}"
        # Remove None values
        data = {k: v for k, v in params.items() if v is not None}

        last_err: Exception | None = None
        for attempt in range(3):
            try:
                resp = self._client.post(url, json=data)
                result = resp.json()
                if result.get("ok"):
                    return result.get("result", {})
                else:
                    err_msg = result.get("description", "Unknown error")
                    logger.warning("Telegram API error: %s", err_msg)
                    return {}
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as e:
                last_err = e
                wait = 2 ** attempt
                logger.warning(
                    "Network error on attempt %d: %s. Retrying in %ds...",
                    attempt + 1, e, wait,
                )
                time.sleep(wait)
            except Exception as e:
                logger.error("Unexpected error calling %s: %s", method, e)
                _log_error(e)
                return {}

        if last_err:
            logger.error("Failed after 3 retries: %s", last_err)
            _log_error(last_err)
        return {}

    def get_me(self) -> dict:
        return self._call("getMe")

    def get_updates(self, offset: int = 0, timeout: int = 30) -> list[dict]:
        result = self._call("getUpdates", offset=offset, timeout=timeout)
        return result if isinstance(result, list) else []

    def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str | None = None,
        reply_markup: dict | None = None,
    ) -> dict:
        # Split long messages
        if len(text) > _MAX_MESSAGE_LENGTH:
            chunks = [text[i:i + 4000] for i in range(0, len(text), 4000)]
            result = {}
            for chunk in chunks:
                result = self._call(
                    "sendMessage",
                    chat_id=chat_id,
                    text=chunk,
                    parse_mode=parse_mode,
                )
            return result

        return self._call(
            "sendMessage",
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup,
        )

    def send_document(
        self,
        chat_id: int,
        file_path: Path,
        caption: str | None = None,
    ) -> dict:
        """Send a document file to a chat."""
        url = f"{self._base}/sendDocument"
        try:
            with open(file_path, "rb") as f:
                files = {"document": (file_path.name, f)}
                data: dict[str, Any] = {"chat_id": chat_id}
                if caption:
                    data["caption"] = caption
                resp = self._client.post(url, data=data, files=files)
                result = resp.json()
                if result.get("ok"):
                    return result.get("result", {})
                logger.warning("Telegram API error: %s", result.get("description", ""))
                return {}
        except Exception as e:
            logger.error("Error sending document: %s", e)
            _log_error(e)
            return {}

    def send_chat_action(self, chat_id: int, action: str = "typing") -> dict:
        return self._call("sendChatAction", chat_id=chat_id, action=action)

    def answer_callback_query(
        self, callback_query_id: str, text: str | None = None,
    ) -> dict:
        return self._call(
            "answerCallbackQuery",
            callback_query_id=callback_query_id,
            text=text,
        )

    def edit_message_text(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        reply_markup: dict | None = None,
    ) -> dict:
        return self._call(
            "editMessageText",
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup,
        )

    def get_file(self, file_id: str) -> dict:
        return self._call("getFile", file_id=file_id)

    def download_file(self, file_path: str, local_path: Path) -> bool:
        """Download a file from Telegram servers."""
        url = f"{_API_BASE}/file/bot{self.token}/{file_path}"
        try:
            resp = self._client.get(url)
            resp.raise_for_status()
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(resp.content)
            return True
        except Exception as e:
            logger.error("Error downloading file: %s", e)
            return False

    def set_my_commands(self, commands: list[dict]) -> dict:
        return self._call("setMyCommands", commands=commands)


def _rating_keyboard(lesson_id: str) -> dict:
    """Build an inline keyboard with 1-5 star buttons + skip."""
    buttons = [
        {"text": "\u2605" * i, "callback_data": f"rate:{lesson_id}:{i}"}
        for i in range(1, 6)
    ]
    skip_btn = {"text": "Skip", "callback_data": f"rate:{lesson_id}:0"}
    return {"inline_keyboard": [buttons, [skip_btn]]}


def _post_generation_keyboard(lesson_id: str) -> dict:
    """Quick action buttons after lesson generation — includes export options."""
    return {
        "inline_keyboard": [
            [
                {"text": "Slides", "callback_data": f"action:export_slides:{lesson_id}"},
                {"text": "Handout", "callback_data": f"action:export_handout:{lesson_id}"},
                {"text": "Word Doc", "callback_data": f"action:export_doc:{lesson_id}"},
            ],
            [
                {"text": "Rate this lesson", "callback_data": f"rate:{lesson_id}:0_prompt"},
                {"text": "Worksheet", "callback_data": f"action:worksheet:{lesson_id}"},
            ],
        ]
    }


def _detect_intent(text: str) -> tuple[str | None, str]:
    """Fast keyword-based intent detection.

    Returns (command, args) or (None, text) to fall through to LLM.
    """
    lower = text.lower()

    # Lesson generation
    if any(phrase in lower for phrase in [
        "make a lesson", "create a lesson", "generate a lesson",
        "lesson on ", "lesson about ", "lesson for ",
        "build a lesson", "write a lesson",
    ]):
        return "lesson", text

    # Unit generation
    if any(phrase in lower for phrase in [
        "make a unit", "create a unit", "unit on ",
        "unit about ", "plan a unit", "build a unit",
    ]):
        return "unit", text

    # Export requests
    if any(phrase in lower for phrase in [
        "export slides", "make slides", "create slides",
        "powerpoint", "pptx", "slide deck",
        "can i see the slides", "give me slides",
    ]):
        return "export_slides", text
    if any(phrase in lower for phrase in [
        "export handout", "make a handout", "create a handout",
        "student handout", "student worksheet", "print",
        "make a handout for this", "handout for this",
    ]):
        return "export_handout", text
    if any(phrase in lower for phrase in [
        "export doc", "word doc", "docx", "export word",
    ]):
        return "export_doc", text

    # Standards
    if any(phrase in lower for phrase in [
        "what standards", "which standards",
        "standards for", "standards cover",
    ]):
        return "standards", text

    # Demo
    if any(phrase in lower for phrase in [
        "show me what you", "demo", "example lesson",
        "sample lesson", "what can you do",
    ]):
        return "demo", ""

    # Help/getting started
    if any(phrase in lower for phrase in [
        "how do i", "get started", "help me set up",
        "what do i do first", "how does this work",
    ]):
        return "help", ""

    # Gaps / curriculum analysis
    if any(phrase in lower for phrase in [
        "what am i missing", "curriculum gaps", "what haven't i covered",
        "what havent i covered", "gap analysis",
    ]):
        return "gaps", text

    # Model switching
    if any(phrase in lower for phrase in [
        "switch to ollama", "use ollama", "change model",
        "switch to anthropic", "use anthropic",
        "switch to openai", "use openai",
    ]):
        return "model", text

    # Schedule intent — requires a scheduling VERB + task context.
    # Must not hijack normal messages like "what should I teach every Friday?"
    _schedule_verbs = [
        "remind me", "send me a digest", "send me a report", "send me student",
        "send me feedback", "send me a summary",
        "morning reminder", "stop reminder", "cancel reminder",
        "what's scheduled", "whats scheduled", "my schedule",
        "cancel all reminder",
    ]
    # Enable/disable/stop + specific task name = scheduling
    _schedule_actions = [
        "stop morning prep", "stop weekly plan", "stop student digest",
        "stop feedback digest", "stop memory compress",
        "enable morning prep", "enable weekly plan", "enable student digest",
        "enable feedback digest",
        "disable morning prep", "disable weekly plan", "disable student digest",
        "disable feedback digest",
        "turn on morning prep", "turn off morning prep",
        "turn on weekly plan", "turn off weekly plan",
        "set morning prep", "set weekly plan", "set student digest",
        "set feedback digest",
    ]
    if any(phrase in lower for phrase in _schedule_verbs + _schedule_actions):
        return "schedule", text
    # Also catch "morning prep at <time>" but NOT bare "every friday"
    if re.search(r"(morning prep|weekly plan|student digest|feedback digest)\s+(at|to)\b", lower):
        return "schedule", text

    return None, text  # Fall through to LLM


# ── Onboarding state machine ──────────────────────────────────────────

ONBOARD_ASK_SUBJECT = "ask_subject"
ONBOARD_ASK_GRADE = "ask_grade"
ONBOARD_ASK_NAME = "ask_name"
ONBOARD_ASK_MODEL = "ask_model"
ONBOARD_DONE = "done"


def _parse_grade_and_subject(text: str) -> tuple[str, str]:
    """Try to extract both a grade level and subject from a single message.

    Returns (grade, subject) where either may be empty if not found.
    Examples:
        "8th grade social studies" -> ("8", "Social Studies")
        "AP Chemistry" -> ("", "AP Chemistry")
        "5th grade math" -> ("5", "Math")
    """
    text = text.strip()
    grade = ""
    subject = text

    # Match patterns like "8th grade", "5th grade", "grade 8", "8th"
    grade_match = re.search(
        r'(?:(\d{1,2})(?:st|nd|rd|th)?\s*grade)|(?:grade\s*(\d{1,2}))',
        text,
        re.IGNORECASE,
    )
    if grade_match:
        grade = grade_match.group(1) or grade_match.group(2)
        # Remove the grade portion to isolate subject
        subject = text[:grade_match.start()] + text[grade_match.end():]
        subject = subject.strip().strip("-,. ")

    # Capitalize subject nicely
    if subject:
        subject = subject.strip()
        # Title-case but preserve "AP", "IB", etc.
        words = subject.split()
        capitalized = []
        for w in words:
            if w.upper() in ("AP", "IB", "ELA"):
                capitalized.append(w.upper())
            else:
                capitalized.append(w.capitalize())
        subject = " ".join(capitalized)

    return grade, subject


# ── Schedule parsing helpers ──────────────────────────────────────────


def _parse_schedule_time(text: str) -> dict:
    """Parse '7am', '7:30 PM', 'evening', 'morning', 'afternoon'."""
    text = text.lower().strip()

    # Named times
    named = {
        "morning": "7:00", "evening": "19:00",
        "afternoon": "15:00", "night": "20:00",
    }
    for name, time_val in named.items():
        if name in text:
            h, m = time_val.split(":")
            return {"hour": h, "minute": m}

    # Explicit time: "7am", "7:30pm", "19:00"
    match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', text)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2) or "0")
        ampm = match.group(3)
        if ampm == "pm" and hour < 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
        return {"hour": str(hour), "minute": str(minute)}

    return {"hour": "7", "minute": "0"}  # default morning


def _parse_day_of_week(text: str) -> str:
    """Extract day of week from text, or empty string for daily."""
    days = {
        "monday": "mon", "tuesday": "tue", "wednesday": "wed",
        "thursday": "thu", "friday": "fri", "saturday": "sat",
        "sunday": "sun",
    }
    text_lower = text.lower()
    for name, abbr in days.items():
        if name in text_lower:
            return abbr
    return ""


def _cron_to_human(cron: dict) -> str:
    """Convert {'hour': '7', 'minute': '0'} to 'Daily at 7:00 AM'."""
    hour = int(cron.get("hour", "0"))
    minute = int(cron.get("minute", "0"))
    am_pm = "AM" if hour < 12 else "PM"
    display_hour = hour if hour <= 12 else hour - 12
    if display_hour == 0:
        display_hour = 12
    time_str = f"{display_hour}:{minute:02d} {am_pm}"

    dow = cron.get("day_of_week", "")
    if dow:
        days = {
            "mon": "Monday", "tue": "Tuesday", "wed": "Wednesday",
            "thu": "Thursday", "fri": "Friday", "sat": "Saturday",
            "sun": "Sunday",
        }
        return f"{days.get(dow, dow.title())}s at {time_str}"
    return f"Daily at {time_str}"


def _match_task_name(text: str) -> str | None:
    """Match natural language to a task name."""
    lower = text.lower()
    if any(w in lower for w in ["morning", "prep", "daily prep"]):
        return "morning-prep"
    if any(w in lower for w in ["weekly", "week plan", "lesson plan"]):
        return "weekly-plan"
    if any(w in lower for w in ["feedback", "rating"]):
        return "feedback-digest"
    if any(w in lower for w in ["memory", "compress", "notes"]):
        return "memory-compress"
    if any(w in lower for w in ["student", "question", "digest"]):
        return "student-digest"
    return None


class EduAgentTelegramBot:
    """Standalone Telegram bot using httpx (sync) -- no python-telegram-bot needed.

    Token resolution order:
        1. ``token`` constructor argument
        2. ``TELEGRAM_BOT_TOKEN`` environment variable
        3. Saved config (``eduagent config set-token TOKEN``)
    """

    # Bot commands for BotFather registration
    COMMANDS = [
        {"command": "start", "description": "Welcome and setup guide"},
        {"command": "help", "description": "List all commands"},
        {"command": "lesson", "description": "Generate a daily lesson"},
        {"command": "unit", "description": "Plan a unit"},
        {"command": "persona", "description": "Show current teaching persona"},
        {"command": "ingest", "description": "Instructions for sending files"},
        {"command": "settings", "description": "Show current config"},
        {"command": "demo", "description": "Show demo lesson output"},
        {"command": "progress", "description": "Student progress report"},
        {"command": "export", "description": "Export last lesson (slides/handout/doc)"},
        {"command": "feedback", "description": "Recent ratings summary"},
        {"command": "standards", "description": "Look up standards"},
        {"command": "schedule", "description": "Manage scheduled reminders"},
        {"command": "gaps", "description": "Curriculum gap analysis"},
    ]

    def __init__(
        self,
        token: str,
        data_dir: Path | None = None,
    ):
        self.token = token
        self.data_dir = data_dir or Path.home() / ".eduagent"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.api = TelegramAPI(token)
        self._running = False
        self._last_lesson_id: dict[int, str] = {}
        self._last_lesson_data: dict[int, Any] = {}
        # Onboarding state per chat: {chat_id: {"step": ..., "subject": ..., ...}}
        self._onboard_state: dict[int, dict] = {}

    @classmethod
    def from_env(cls, data_dir: Path | None = None) -> "EduAgentTelegramBot":
        """Create a bot by resolving the token from the environment."""
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not token:
            try:
                from eduagent.models import AppConfig
                cfg = AppConfig.load()
                token = cfg.telegram_bot_token
            except Exception:
                pass
        if not token:
            raise ValueError(
                "No Telegram bot token found.\n"
                "Set the TELEGRAM_BOT_TOKEN environment variable or run:\n"
                "  eduagent config set-token YOUR_TOKEN"
            )
        return cls(token=token, data_dir=data_dir)

    def run(self, force: bool = False) -> None:
        """Start the polling loop. Blocks until SIGINT/SIGTERM."""
        _check_bot_lock(force=force)

        import atexit
        atexit.register(_release_bot_lock)

        # Set up signal handlers for clean shutdown
        def _signal_handler(sig, frame):
            self._running = False
        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)

        # Register commands with Telegram
        self.api.set_my_commands(self.COMMANDS)

        me = self.api.get_me()
        bot_name = me.get("username", "unknown")
        logger.info("Bot @%s started, entering polling loop", bot_name)
        print(f"EDUagent bot @{bot_name} is running. Press Ctrl+C to stop.")
        print(f"   Data directory: {self.data_dir}")
        print("   Mode: polling (httpx)")

        self._running = True
        offset = 0
        while self._running:
            try:
                updates = self.api.get_updates(offset=offset, timeout=30)
                for update in updates:
                    offset = update["update_id"] + 1
                    self._process_update(update)
            except Exception as e:
                logger.error("Error in polling loop: %s", e)
                _log_error(e)
                time.sleep(2)

        print("\nBot stopped.")
        _release_bot_lock()
        self.api.close()

    def _process_update(self, update: dict) -> None:
        """Route an update to the appropriate handler."""
        try:
            if "callback_query" in update:
                self._handle_callback(update["callback_query"])
            elif "message" in update:
                msg = update["message"]
                if "document" in msg:
                    self._handle_document(msg)
                elif "text" in msg:
                    text = msg["text"]
                    if text.startswith("/"):
                        self._handle_command(msg)
                    else:
                        self._handle_message(msg)
        except Exception as e:
            logger.error("Error processing update: %s", e)
            _log_error(e)

    # ── Command handlers ──────────────────────────────────────────────

    def _handle_command(self, msg: dict) -> None:
        """Dispatch slash commands."""
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower().lstrip("/").split("@")[0]
        args = parts[1] if len(parts) > 1 else ""

        handlers: dict[str, Callable] = {
            "start": self._cmd_start,
            "help": self._cmd_help,
            "lesson": self._cmd_lesson,
            "unit": self._cmd_unit,
            "persona": self._cmd_persona,
            "ingest": self._cmd_ingest,
            "settings": self._cmd_settings,
            "demo": self._cmd_demo,
            "progress": self._cmd_progress,
            "export": self._cmd_export,
            "feedback": self._cmd_feedback,
            "standards": self._cmd_standards,
            "schedule": self._cmd_schedule,
            "gaps": self._cmd_gaps,
        }

        handler = handlers.get(cmd)
        if handler:
            handler(chat_id, msg, args)
        else:
            self.api.send_message(
                chat_id,
                f"Unknown command: /{cmd}\nType /help to see available commands.",
            )

    def _has_config(self) -> bool:
        """Check if a config file already exists (teacher already onboarded)."""
        from eduagent.models import AppConfig
        return AppConfig.config_path().exists()

    def _cmd_start(self, chat_id: int, msg: dict, args: str) -> None:
        if self._has_config():
            # Already set up -- show the normal welcome
            self.api.send_message(
                chat_id,
                "Hey! I'm EDUagent -- think of me as that colleague down the hall "
                "who always has a lesson idea ready.\n\n"
                "Here's how I work: share some of your teaching materials (just drag "
                "files into this chat), and I'll learn your style. After that, I can "
                "generate lessons, units, handouts, and slides that sound like YOU "
                "wrote them.\n\n"
                "Quick commands:\n"
                "/lesson [topic] -- Generate a lesson\n"
                "/unit [topic] -- Plan a full unit\n"
                "/schedule -- Set up reminders\n"
                "/gaps -- See what you haven't covered yet\n"
                "/demo -- See what I can do (no setup needed)\n"
                "/help -- All commands\n\n"
                "Or just tell me what you need in plain English. "
                "I'm pretty good at figuring it out.",
            )
            return

        # No config -- start conversational onboarding
        self._onboard_state[chat_id] = {"step": ONBOARD_ASK_SUBJECT}
        self.api.send_message(
            chat_id,
            "Hey! Let's get you set up. What subject do you teach?",
        )

    def _cmd_help(self, chat_id: int, msg: dict, args: str) -> None:
        self.api.send_message(
            chat_id,
            "EDUagent Commands\n\n"
            "Generate content:\n"
            "  /lesson <topic> -- Generate a daily lesson\n"
            "  /unit <topic> -- Plan a full unit\n"
            "  /demo -- See sample lesson output\n\n"
            "Export formats:\n"
            "  /export slides -- PowerPoint presentation\n"
            "  /export handout -- Student worksheet (DOCX)\n"
            "  /export doc -- Full lesson plan (Word)\n\n"
            "Setup & customize:\n"
            "  /ingest -- How to send teaching materials\n"
            "  /persona -- Show current teaching persona\n"
            "  /settings -- Show current config\n"
            "  /standards <subject> <grade> -- Look up standards\n"
            "  /schedule -- Manage scheduled reminders\n"
            "  /gaps -- Curriculum gap analysis\n\n"
            "Reports:\n"
            "  /progress -- Student progress report\n"
            "  /feedback -- Recent ratings summary\n\n"
            "You can also say things like:\n"
            '  "switch to ollama"\n'
            '  "remind me to prep lessons every Sunday evening"\n'
            '  "what am I missing?"\n\n'
            "Or just type what you need -- I understand plain English too!",
        )

    def _cmd_lesson(self, chat_id: int, msg: dict, args: str) -> None:
        if not args:
            self.api.send_message(
                chat_id,
                "What topic should the lesson be about?\n"
                "Example: /lesson photosynthesis for 6th grade",
            )
            return

        teacher_id = str(msg["from"]["id"])
        self._generate_with_progress(chat_id, teacher_id, args)

    def _cmd_unit(self, chat_id: int, msg: dict, args: str) -> None:
        if not args:
            self.api.send_message(
                chat_id,
                "What topic should the unit cover?\n"
                "Example: /unit The American Revolution for 8th grade, 3 weeks",
            )
            return

        self.api.send_chat_action(chat_id, "typing")
        teacher_id = str(msg["from"]["id"])
        try:
            response = self._llm_call(f"plan a unit on {args}", teacher_id)
            self.api.send_message(chat_id, response)
        except Exception as e:
            logger.error("Error planning unit: %s", e)
            _log_error(e)
            self.api.send_message(
                chat_id,
                "Couldn't generate right now. Try again in a minute.",
            )

    def _cmd_persona(self, chat_id: int, msg: dict, args: str) -> None:
        try:
            from eduagent.commands._helpers import load_persona_or_exit
            persona = load_persona_or_exit()
            self.api.send_message(chat_id, persona.to_prompt_context())
        except SystemExit:
            self.api.send_message(
                chat_id,
                "No persona found yet. Send me a teaching file first!",
            )
        except Exception:
            self.api.send_message(
                chat_id,
                "No persona found yet. Send me a teaching file to get started.",
            )

    def _cmd_ingest(self, chat_id: int, msg: dict, args: str) -> None:
        self.api.send_message(
            chat_id,
            "Send me a file (PDF, DOCX, PPTX, TXT, or MD) and I'll learn "
            "your teaching style from it.\n\n"
            "Just drag and drop a file into this chat!",
        )

    def _cmd_settings(self, chat_id: int, msg: dict, args: str) -> None:
        try:
            from eduagent.models import AppConfig
            cfg = AppConfig.load()
            provider = cfg.provider.value
            model = {
                "anthropic": cfg.anthropic_model,
                "openai": cfg.openai_model,
                "ollama": cfg.ollama_model,
            }.get(provider, "unknown")
            self.api.send_message(
                chat_id,
                f"EDUagent Settings\n\n"
                f"Provider: {provider}\n"
                f"Model: {model}\n"
                f"Output: {cfg.output_dir}\n"
                f"Format: {cfg.export_format}\n"
                f"Homework: {'yes' if cfg.include_homework else 'no'}",
            )
        except Exception:
            self.api.send_message(chat_id, "Could not load settings.")

    def _cmd_demo(self, chat_id: int, msg: dict, args: str) -> None:
        self.api.send_chat_action(chat_id, "typing")
        teacher_id = str(msg["from"]["id"])
        try:
            response = self._llm_call("generate a demo lesson on photosynthesis for 6th grade science", teacher_id)
            self.api.send_message(chat_id, response)
        except Exception as e:
            _log_error(e)
            self.api.send_message(chat_id, "Could not generate demo right now.")

    def _cmd_progress(self, chat_id: int, msg: dict, args: str) -> None:
        teacher_id = str(msg["from"]["id"])
        try:
            from eduagent.student_bot import StudentBot
            bot = StudentBot()

            from eduagent.state import _get_conn, init_db
            init_db()
            with _get_conn() as conn:
                rows = conn.execute(
                    "SELECT class_code, name, topic FROM classes WHERE teacher_id = ?",
                    (teacher_id,),
                ).fetchall()

            if not rows:
                self.api.send_message(
                    chat_id,
                    "No active classes found. Create one with the CLI:\n"
                    "  eduagent class create --name 'Period 3'",
                )
                return

            parts = ["Student Progress Report\n"]
            for row in rows:
                code = row["class_code"]
                name = row["name"] or code
                parts.append(f"\nClass: {name} ({code})")
                progress = bot.get_student_progress(code)
                if not progress:
                    parts.append("  No student activity yet.")
                    continue
                for p in progress:
                    sname = p.get("student_name") or f"Student {p['student_id'][:8]}"
                    total = p.get("total_questions", 0)
                    parts.append(f"  {sname}: {total} questions")

            self.api.send_message(chat_id, "\n".join(parts))
        except Exception as e:
            logger.error("Error in /progress: %s", e)
            _log_error(e)
            self.api.send_message(chat_id, "Could not generate progress report.")

    def _cmd_export(self, chat_id: int, msg: dict, args: str) -> None:
        """Handle /export command with format argument."""
        lesson_id = self._last_lesson_id.get(chat_id)
        if not lesson_id:
            self.api.send_message(
                chat_id,
                "No recent lesson to export. Generate one with /lesson first.",
            )
            return

        fmt = args.strip().lower() if args else ""

        if fmt in ("slides", "pptx"):
            self._do_export(chat_id, lesson_id, "pptx")
        elif fmt in ("handout", "worksheet"):
            self._do_export(chat_id, lesson_id, "handout")
        elif fmt in ("doc", "docx", "word"):
            self._do_export(chat_id, lesson_id, "docx")
        elif fmt in ("pdf",):
            self._do_export(chat_id, lesson_id, "pdf")
        else:
            # No format specified — show options
            self.api.send_message(
                chat_id,
                "What format would you like?\n\n"
                "/export slides -- PowerPoint presentation\n"
                "/export handout -- Student worksheet\n"
                "/export doc -- Full lesson plan (Word)\n"
                "/export pdf -- PDF document",
            )

    def _cmd_feedback(self, chat_id: int, msg: dict, args: str) -> None:
        teacher_id = str(msg["from"]["id"])
        try:
            from eduagent.analytics import get_teacher_stats
            data = get_teacher_stats(teacher_id)
            avg = data["overall_avg_rating"]
            total = data["rated_lessons"]
            if not total:
                self.api.send_message(
                    chat_id,
                    "No ratings yet! Generate a lesson and rate it to see feedback here.",
                )
                return
            stars = "\u2605" * round(avg) + "\u2606" * (5 - round(avg))
            self.api.send_message(
                chat_id,
                f"Rating Summary\n\n"
                f"Average: {stars} ({avg:.1f}/5)\n"
                f"Total rated: {total} lessons\n"
                f"Streak: {data['streak']} day(s)",
            )
        except Exception as e:
            _log_error(e)
            self.api.send_message(chat_id, "Could not load feedback data.")

    def _cmd_standards(self, chat_id: int, msg: dict, args: str) -> None:
        parts = args.split()
        if len(parts) < 2:
            self.api.send_message(
                chat_id,
                "Usage: /standards <subject> <grade>\n"
                "Example: /standards math 8",
            )
            return

        subject = parts[0]
        grade = parts[1]
        try:
            from eduagent.standards import get_standards
            results = get_standards(subject, grade)
            if not results:
                self.api.send_message(
                    chat_id, f"No standards found for {subject} grade {grade}.",
                )
                return
            lines = [f"Standards for {subject} grade {grade}:\n"]
            for code, desc, band in results[:15]:
                lines.append(f"  {code}: {desc}")
            if len(results) > 15:
                lines.append(f"\n...and {len(results) - 15} more.")
            self.api.send_message(chat_id, "\n".join(lines))
        except Exception as e:
            _log_error(e)
            self.api.send_message(chat_id, f"Could not look up standards: {e}")

    # ── Schedule command ──────────────────────────────────────────────

    def _cmd_schedule(self, chat_id: int, msg: dict, args: str) -> None:
        """Handle /schedule command and natural language schedule requests."""
        from eduagent.scheduler import (
            disable_task,
            load_schedule_config,
            save_schedule_config,
        )

        if not args:
            # Show current schedule
            config = load_schedule_config()
            lines = ["Your scheduled tasks:\n"]
            for name, task in config.items():
                status = "ON" if task["enabled"] else "OFF"
                cron = task["cron"]
                time_str = _cron_to_human(cron)
                lines.append(f"  {status}  {task['description'][:50]} -- {time_str}")
            lines.append("\nExamples:")
            lines.append('  "morning prep at 7am"')
            lines.append('  "student digest every Friday"')
            lines.append('  "stop morning prep"')
            self.api.send_message(chat_id, "\n".join(lines))
            return

        lower = args.lower()

        # Cancel / stop / disable
        if any(w in lower for w in ["stop", "cancel", "disable"]):
            if "all" in lower:
                config = load_schedule_config()
                for name in config:
                    config[name]["enabled"] = False
                save_schedule_config(config)
                self.api.send_message(chat_id, "All scheduled tasks disabled.")
                return

            task_name = _match_task_name(lower)
            if task_name:
                if disable_task(task_name):
                    self.api.send_message(chat_id, f"Disabled: {task_name}")
                else:
                    self.api.send_message(chat_id, f"Could not find task: {task_name}")
            else:
                self.api.send_message(
                    chat_id,
                    "Which task? Try: stop morning prep, stop student digest, "
                    "stop weekly plan, or cancel all",
                )
            return

        # Enable / set schedule
        task_name = _match_task_name(lower)
        if not task_name:
            # Try to guess from context
            self.api.send_message(
                chat_id,
                "I'm not sure which task you mean. Available tasks:\n"
                "  morning-prep, weekly-plan, feedback-digest, "
                "memory-compress, student-digest\n\n"
                "Try: /schedule morning prep at 7am",
            )
            return

        time_dict = _parse_schedule_time(lower)
        dow = _parse_day_of_week(lower)
        if dow:
            time_dict["day_of_week"] = dow

        config = load_schedule_config()
        config[task_name]["cron"] = time_dict
        config[task_name]["enabled"] = True
        save_schedule_config(config)

        human_time = _cron_to_human(time_dict)
        desc = config[task_name]["description"][:50]
        self.api.send_message(
            chat_id,
            f"Scheduled! {desc}\n{human_time}",
        )

    # ── Gaps command ──────────────────────────────────────────────────

    def _cmd_gaps(self, chat_id: int, msg: dict, args: str) -> None:
        """Run curriculum gap analysis and send results."""
        self.api.send_chat_action(chat_id, "typing")

        try:
            from eduagent.curriculum_map import CurriculumMapper
            from eduagent.models import AppConfig, TeacherPersona

            cfg = AppConfig.load()
            profile = cfg.teacher_profile

            # Need subject and grade to look up standards
            subjects = profile.subjects if profile.subjects else ["General"]
            grades = profile.grade_levels if profile.grade_levels else ["8"]

            # Load existing materials from BOTH databases:
            # 1. state.py generated_lessons (bot-generated via Telegram)
            # 2. database.py lessons (web/CLI-generated)
            existing = []
            try:
                from eduagent.state import _get_conn as _state_conn
                from eduagent.state import init_db as _state_init_db
                _state_init_db()
                with _state_conn() as conn:
                    rows = conn.execute(
                        "SELECT title FROM generated_lessons ORDER BY created_at DESC LIMIT 50"
                    ).fetchall()
                    existing.extend(r["title"] for r in rows if r["title"])
            except Exception:
                pass
            try:
                from eduagent.database import Database
                db = Database()
                web_lessons = db._fetchall("SELECT title FROM lessons ORDER BY created_at DESC LIMIT 50")
                existing.extend(r["title"] for r in web_lessons if r.get("title"))
                db.close()
            except Exception:
                pass

            # Get standards
            from eduagent.standards import get_standards
            subject = subjects[0]
            grade = grades[0]
            standards_list = get_standards(subject, grade)
            if not standards_list:
                self.api.send_message(
                    chat_id,
                    f"No standards found for {subject} grade {grade}. "
                    "Try setting your profile with /start.",
                )
                return

            standards = [f"{code}: {desc}" for code, desc, _ in standards_list[:20]]

            # Load persona
            try:
                from eduagent.commands._helpers import load_persona_or_exit
                persona = load_persona_or_exit()
            except (SystemExit, Exception):
                persona = TeacherPersona()

            engine = CurriculumMapper(cfg)
            gaps = asyncio.run(
                engine.identify_curriculum_gaps(existing, standards, persona)
            )

            if not gaps:
                self.api.send_message(
                    chat_id,
                    f"Looking good! No major gaps found for {subject} grade {grade}.",
                )
                return

            lines = [f"Gap Analysis: {subject} Grade {grade}\n"]
            for gap in gaps[:10]:
                severity = gap.severity.upper() if gap.severity else "MEDIUM"
                lines.append(f"  [{severity}] {gap.standard}")
                lines.append(f"    {gap.description}")
                if gap.suggestion:
                    lines.append(f"    Suggestion: {gap.suggestion}")
                lines.append("")

            if len(gaps) > 10:
                lines.append(f"...and {len(gaps) - 10} more gaps.")

            self.api.send_message(chat_id, "\n".join(lines))

        except Exception as e:
            logger.error("Error in /gaps: %s", e)
            _log_error(e)
            self.api.send_message(
                chat_id,
                "Couldn't run gap analysis right now. "
                "Make sure your profile is set up (/settings).",
            )

    # ── Model switch command ──────────────────────────────────────────

    def _cmd_model_switch(self, chat_id: int, text: str) -> None:
        """Switch the LLM provider from a natural language request."""
        from eduagent.models import AppConfig, LLMProvider

        lower = text.lower()
        if "ollama" in lower:
            provider = "ollama"
        elif "anthropic" in lower:
            provider = "anthropic"
        elif "openai" in lower:
            provider = "openai"
        else:
            self.api.send_message(
                chat_id,
                "Which AI? Type: ollama, anthropic, or openai",
            )
            return

        cfg = AppConfig.load()
        cfg.provider = LLMProvider(provider)
        cfg.save()
        self.api.send_message(
            chat_id,
            f"Switched to {provider}! All future lessons will use this.",
        )

    # ── Onboarding handler ────────────────────────────────────────────

    def _handle_onboarding(self, chat_id: int, msg: dict, text: str) -> None:
        """Process a message during the conversational onboarding flow."""
        state = self._onboard_state[chat_id]
        step = state["step"]

        if step == ONBOARD_ASK_SUBJECT:
            # Try to parse both grade and subject from a single message
            grade, subject = _parse_grade_and_subject(text)
            if not subject:
                self.api.send_message(chat_id, "I didn't catch that. What subject do you teach?")
                return

            state["subject"] = subject

            if grade:
                # Got both -- skip grade question
                state["grade"] = grade
                state["step"] = ONBOARD_ASK_NAME
                self.api.send_message(
                    chat_id,
                    f"{subject}, got it! And grade {grade} -- perfect.\n"
                    "What's your name? (I'll use it on your lesson plans)",
                )
            else:
                state["step"] = ONBOARD_ASK_GRADE
                self.api.send_message(
                    chat_id,
                    f"{subject}, got it! What grade level?",
                )

        elif step == ONBOARD_ASK_GRADE:
            # Extract grade number
            grade_match = re.search(r'(\d{1,2})', text)
            if grade_match:
                state["grade"] = grade_match.group(1)
            else:
                # Accept text like "K", "kindergarten", "pre-k"
                state["grade"] = text.strip()

            state["step"] = ONBOARD_ASK_NAME
            self.api.send_message(
                chat_id,
                "What's your name? (I'll use it on your lesson plans)",
            )

        elif step == ONBOARD_ASK_NAME:
            state["name"] = text.strip()
            state["step"] = ONBOARD_ASK_MODEL
            self.api.send_message(
                chat_id,
                f"Great, {state['name']}! Last question -- which AI should I use?\n\n"
                "  Ollama -- Free, runs on your computer (needs ollama.com installed)\n"
                "  Anthropic -- Best quality, ~$20/month (needs API key)\n"
                "  OpenAI -- Good quality, ~$20/month (needs API key)\n\n"
                'Type "ollama", "anthropic", or "openai" (you can change this later)',
            )

        elif step == ONBOARD_ASK_MODEL:
            lower = text.lower().strip()
            from eduagent.models import AppConfig, LLMProvider, TeacherProfile

            if "ollama" in lower:
                provider = LLMProvider.OLLAMA
            elif "anthropic" in lower:
                provider = LLMProvider.ANTHROPIC
            elif "openai" in lower:
                provider = LLMProvider.OPENAI
            else:
                self.api.send_message(
                    chat_id,
                    'I need one of: "ollama", "anthropic", or "openai"',
                )
                return

            # Build and save config
            profile = TeacherProfile(
                name=state.get("name", ""),
                subjects=[state.get("subject", "")],
                grade_levels=[state.get("grade", "")],
            )
            config = AppConfig(
                provider=provider,
                teacher_profile=profile,
            )
            config.save()

            # Clean up onboarding state
            state["step"] = ONBOARD_DONE
            del self._onboard_state[chat_id]

            subject = state.get("subject", "your subject")
            grade = state.get("grade", "")
            name = state.get("name", "")
            provider_name = provider.value.title()

            grade_display = f"Grade: {grade}\n" if grade else ""

            self.api.send_message(
                chat_id,
                f"All set! Here's what I know about you:\n"
                f"  Subject: {subject}\n"
                f"  {grade_display}"
                f"  Name: {name}\n"
                f"  AI: {provider_name}\n\n"
                "Now drop some of your lesson files in here (PDF, DOCX, PPTX) "
                "and I'll learn your teaching style. Or just try:\n"
                f'/lesson "The American Revolution"',
            )

    # ── Message handler ───────────────────────────────────────────────

    def _handle_message(self, msg: dict) -> None:
        """Route free-text messages through intent detection, then LLM fallback.

        If the message looks like a local folder path we hand it off to
        ``_handle_connect_local`` in the background so the bot stays
        responsive during large ingestions.
        """
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "").strip()
        if not text:
            return

        teacher_id = str(msg["from"]["id"])

        # Check if this chat is in onboarding flow
        if chat_id in self._onboard_state:
            self._handle_onboarding(chat_id, msg, text)
            return

        # Detect folder-path messages and run ingestion in a background thread
        if self._looks_like_path(text):
            self._handle_path_ingestion(chat_id, teacher_id, text)
            return

        # Try fast keyword-based intent detection before falling back to LLM
        intent, intent_args = _detect_intent(text)

        if intent == "lesson":
            self._generate_with_progress(chat_id, teacher_id, intent_args)
            return
        elif intent == "unit":
            self.api.send_chat_action(chat_id, "typing")
            try:
                response = self._llm_call(f"plan a unit on {intent_args}", teacher_id)
                self.api.send_message(chat_id, response)
            except Exception as e:
                _log_error(e)
                self.api.send_message(chat_id, "Couldn't generate right now. Try again in a minute.")
            return
        elif intent == "standards":
            self.api.send_chat_action(chat_id, "typing")
            try:
                response = self._llm_call(intent_args, teacher_id)
                self.api.send_message(chat_id, response)
            except Exception as e:
                _log_error(e)
                self.api.send_message(chat_id, "Couldn't look that up right now.")
            return
        elif intent == "demo":
            self._cmd_demo(chat_id, msg, "")
            return
        elif intent == "help":
            self._cmd_help(chat_id, msg, "")
            return
        elif intent in ("export_slides", "export_handout", "export_doc"):
            lesson_id = self._last_lesson_id.get(chat_id)
            if not lesson_id:
                self.api.send_message(
                    chat_id,
                    "No recent lesson to export. Generate one first with /lesson.",
                )
                return
            fmt_map = {
                "export_slides": "pptx",
                "export_handout": "handout",
                "export_doc": "docx",
            }
            self._do_export(chat_id, lesson_id, fmt_map[intent])
            return
        elif intent == "gaps":
            self._cmd_gaps(chat_id, msg, "")
            return
        elif intent == "model":
            self._cmd_model_switch(chat_id, text)
            return
        elif intent == "schedule":
            self._cmd_schedule(chat_id, msg, text)
            return

        # Fall through to LLM for anything else
        self.api.send_chat_action(chat_id, "typing")

        try:
            response = self._llm_call(text, teacher_id)
            self.api.send_message(chat_id, response)
            self._try_offer_rating(chat_id, teacher_id)
        except Exception as e:
            logger.error("Error handling message: %s", e)
            _log_error(e)
            self.api.send_message(
                chat_id,
                "Couldn't generate right now. Try /lesson again in a minute.",
            )

    @staticmethod
    def _looks_like_path(text: str) -> bool:
        """Return True if *text* appears to be a filesystem path."""
        stripped = text.strip().strip("'\"")
        return (
            stripped.startswith(("/", "~/", "C:\\"))
            or (
                os.sep in stripped
                and not stripped.startswith("http")
                and len(stripped.split()) <= 3
            )
        )

    def _handle_path_ingestion(
        self, chat_id: int, teacher_id: str, text: str,
    ) -> None:
        """Spawn a background thread that ingests files from *text* path."""
        resolved = Path(text.strip().strip("'\"")).expanduser().resolve()
        self.api.send_message(
            chat_id,
            f"Scanning {resolved.name}/... I'll message you when I'm done.",
        )

        def _notify(message: str) -> None:
            self.api.send_message(chat_id, message)

        def _run():
            try:
                from eduagent.openclaw_plugin import _handle_connect_local
                from eduagent.router import Intent, ParsedIntent
                from eduagent.state import TeacherSession

                session = TeacherSession.load(teacher_id)
                parsed = ParsedIntent(
                    intent=Intent.CONNECT_LOCAL,
                    raw=text,
                    url=text.strip().strip("'\""),
                )
                # Run the async handler synchronously inside the thread
                result = asyncio.run(
                    _handle_connect_local(
                        parsed, session, notify_callback=_notify,
                    )
                )
                # The initial "Scanning..." message was already sent.
                # If there is no callback (small dirs), send the result.
                if result and "I'll message you" not in result:
                    _notify(result)
            except Exception as e:
                logger.error("Background ingestion error: %s", e)
                _log_error(e)
                _notify(f"Had trouble processing {resolved.name}/: {str(e)[:150]}")

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    # ── Document handler ──────────────────────────────────────────────

    def _handle_document(self, msg: dict) -> None:
        """Handle file uploads for ingestion."""
        chat_id = msg["chat"]["id"]
        doc = msg.get("document", {})
        file_name = doc.get("file_name", "unknown")
        supported_exts = {".pdf", ".docx", ".pptx", ".txt", ".md"}
        ext = Path(file_name).suffix.lower()

        if ext not in supported_exts:
            self.api.send_message(
                chat_id,
                f"I can't process {ext} files yet. "
                f"Supported: {', '.join(sorted(supported_exts))}",
            )
            return

        self.api.send_message(chat_id, f"Got {file_name}! Processing...")
        self.api.send_chat_action(chat_id, "typing")

        try:
            file_info = self.api.get_file(doc["file_id"])
            file_path = file_info.get("file_path", "")
            if not file_path:
                self.api.send_message(chat_id, "Could not download the file.")
                return

            with tempfile.TemporaryDirectory() as tmpdir:
                local_path = Path(tmpdir) / file_name
                if not self.api.download_file(file_path, local_path):
                    self.api.send_message(chat_id, "Failed to download the file.")
                    return

                from eduagent.ingestor import ingest_path
                documents = ingest_path(local_path)

                if not documents:
                    self.api.send_message(
                        chat_id,
                        "Couldn't extract content from that file. Try a different format?",
                    )
                    return

                from eduagent.commands._helpers import output_dir
                from eduagent.persona import extract_persona, save_persona

                persona = asyncio.run(extract_persona(documents))
                save_persona(persona, output_dir())

                self.api.send_message(
                    chat_id,
                    f"Learned from {file_name}!\n\n"
                    f"Teaching style: {persona.teaching_style.value.replace('_', ' ').title()}\n"
                    f"Tone: {persona.tone}\n"
                    f"Subject: {persona.subject_area}\n\n"
                    "Send more files to improve my understanding, or /lesson to generate!",
                )
        except Exception as e:
            logger.error("Error ingesting file: %s", e)
            _log_error(e)
            self.api.send_message(
                chat_id,
                "Had trouble processing that file. Try again or use a different format.",
            )

    # ── Callback handler ──────────────────────────────────────────────

    def _handle_callback(self, callback: dict) -> None:
        """Handle inline keyboard button presses."""
        query_id = callback.get("id", "")
        data = callback.get("data", "")
        msg = callback.get("message", {})
        chat_id = msg.get("chat", {}).get("id", 0)
        message_id = msg.get("message_id", 0)
        user_id = callback.get("from", {}).get("id", 0)

        self.api.answer_callback_query(query_id)

        if data.startswith("rate:"):
            self._handle_rating(chat_id, message_id, user_id, data)
        elif data.startswith("action:"):
            self._handle_action(chat_id, message_id, user_id, data)

    def _handle_rating(
        self, chat_id: int, message_id: int, user_id: int, data: str,
    ) -> None:
        """Handle rating button presses."""
        parts = data[len("rate:"):].split(":")
        if len(parts) != 2:
            return

        lesson_id, rating_str = parts

        if rating_str == "0_prompt":
            self.api.edit_message_text(
                chat_id, message_id,
                "How was this lesson? Rate it to help me improve:",
                reply_markup=_rating_keyboard(lesson_id),
            )
            return

        try:
            rating = int(rating_str)
        except ValueError:
            return

        if rating == 0:
            self.api.edit_message_text(
                chat_id, message_id,
                "Skipped rating. You can always rate later!",
            )
            return

        try:
            from eduagent.analytics import rate_lesson
            success = rate_lesson(str(user_id), lesson_id, rating)
            if success:
                stars = "\u2605" * rating + "\u2606" * (5 - rating)
                self.api.edit_message_text(
                    chat_id, message_id,
                    f"Thanks! Rated {stars} ({rating}/5)",
                )
                # Feed the memory engine for prompt-level improvement
                try:
                    from eduagent.memory_engine import process_feedback as memory_process
                    from eduagent.models import DailyLesson
                    from eduagent.state import _get_conn, init_db
                    init_db()
                    with _get_conn() as _fb_conn:
                        _fb_row = _fb_conn.execute(
                            "SELECT lesson_json FROM generated_lessons WHERE id = ?",
                            (lesson_id,),
                        ).fetchone()
                    if _fb_row and _fb_row["lesson_json"]:
                        _fb_lesson = DailyLesson.model_validate_json(_fb_row["lesson_json"])
                        # Resolve subject from the lesson's unit, not teacher profile
                        _subject = ""
                        try:
                            with _get_conn() as _subj_conn:
                                _unit_row = _subj_conn.execute(
                                    "SELECT u.subject FROM generated_units u "
                                    "JOIN generated_lessons l ON l.unit_id = u.id "
                                    "WHERE l.id = ?",
                                    (lesson_id,),
                                ).fetchone()
                                if _unit_row and _unit_row["subject"]:
                                    _subject = _unit_row["subject"]
                        except Exception:
                            pass
                        memory_process(_fb_lesson, rating, subject=_subject)
                except Exception:
                    pass  # Memory engine is best-effort
            else:
                self.api.edit_message_text(
                    chat_id, message_id,
                    "Couldn't find that lesson to rate.",
                )
        except Exception as e:
            logger.error("Error saving rating: %s", e)
            _log_error(e)
            self.api.edit_message_text(
                chat_id, message_id,
                "Had trouble saving the rating. Try again later.",
            )

    def _handle_action(
        self, chat_id: int, message_id: int, user_id: int, data: str,
    ) -> None:
        """Handle post-generation action buttons."""
        parts = data[len("action:"):].split(":")
        if len(parts) != 2:
            return

        action, lesson_id = parts

        if action == "worksheet":
            self.api.edit_message_text(
                chat_id, message_id, "Generating worksheet...",
            )
            try:
                response = self._llm_call(
                    f"generate a worksheet for lesson {lesson_id}",
                    str(user_id),
                )
                self.api.send_message(chat_id, response)
            except Exception as e:
                logger.error("Error generating worksheet: %s", e)
                _log_error(e)
                self.api.send_message(
                    chat_id,
                    "Couldn't generate the worksheet right now. Try /lesson.",
                )
        elif action in ("export_slides", "export_handout", "export_doc"):
            fmt_map = {
                "export_slides": "pptx",
                "export_handout": "handout",
                "export_doc": "docx",
            }
            self.api.edit_message_text(
                chat_id, message_id, f"Exporting {action.replace('export_', '')}...",
            )
            self._do_export(chat_id, lesson_id, fmt_map[action])

    # ── Export helper ─────────────────────────────────────────────────

    def _do_export(self, chat_id: int, lesson_id: str, fmt: str) -> None:
        """Export a lesson to the given format and send the file."""
        self.api.send_chat_action(chat_id, "upload_document")

        try:
            from eduagent.models import DailyLesson, TeacherPersona
            from eduagent.state import _get_conn, init_db

            init_db()

            # Load lesson from DB
            lesson_data = self._last_lesson_data.get(chat_id)
            if not lesson_data:
                with _get_conn() as conn:
                    row = conn.execute(
                        "SELECT lesson_json FROM generated_lessons WHERE id = ?",
                        (lesson_id,),
                    ).fetchone()
                if row and row["lesson_json"]:
                    lesson_data = DailyLesson.model_validate_json(row["lesson_json"])
                else:
                    self.api.send_message(
                        chat_id,
                        "Could not find the lesson data. Try generating a new lesson first.",
                    )
                    return

            # Load persona
            try:
                from eduagent.commands._helpers import load_persona_or_exit
                persona = load_persona_or_exit()
            except (SystemExit, Exception):
                persona = TeacherPersona()

            # Do the export
            with tempfile.TemporaryDirectory() as tmpdir:
                out_dir = Path(tmpdir)
                if fmt == "pptx":
                    from eduagent.doc_export import export_lesson_pptx
                    path = export_lesson_pptx(lesson_data, persona, out_dir)
                elif fmt == "handout":
                    from eduagent.doc_export import export_student_handout
                    path = export_student_handout(lesson_data, persona, out_dir)
                elif fmt == "docx":
                    from eduagent.doc_export import export_lesson_docx
                    path = export_lesson_docx(lesson_data, persona, out_dir)
                elif fmt == "pdf":
                    from eduagent.doc_export import export_lesson_pdf
                    path = export_lesson_pdf(lesson_data, persona, out_dir)
                else:
                    self.api.send_message(chat_id, f"Unknown format: {fmt}")
                    return

                fmt_labels = {
                    "pptx": "Slides",
                    "handout": "Student Handout",
                    "docx": "Word Document",
                    "pdf": "PDF",
                }
                self.api.send_document(
                    chat_id, path,
                    caption=f"{fmt_labels.get(fmt, fmt)} for: {lesson_data.title}",
                )
        except Exception as e:
            logger.error("Error exporting lesson: %s", e)
            _log_error(e)
            self.api.send_message(
                chat_id,
                f"Had trouble exporting. You can also export from the CLI:\n"
                f"  eduagent lesson \"topic\" --format {fmt}",
            )

    # ── Generation with progress feedback ─────────────────────────────

    def _generate_with_progress(
        self, chat_id: int, teacher_id: str, topic: str,
    ) -> None:
        """Generate a lesson with periodic typing indicators and a rich response."""
        # Send initial progress message
        self.api.send_chat_action(chat_id, "typing")

        # Start a background thread that sends typing actions periodically
        stop_typing = threading.Event()

        def _typing_loop():
            while not stop_typing.is_set():
                self.api.send_chat_action(chat_id, "typing")
                stop_typing.wait(timeout=4.0)

        typing_thread = threading.Thread(target=_typing_loop, daemon=True)
        typing_thread.start()

        try:
            response = self._llm_call(topic, teacher_id)
            stop_typing.set()
            typing_thread.join(timeout=2)

            self.api.send_message(chat_id, response)

            # Try to build a rich follow-up with export options
            self._try_offer_rating(chat_id, teacher_id)

        except Exception as e:
            stop_typing.set()
            typing_thread.join(timeout=2)
            logger.error("Error generating lesson: %s", e)
            _log_error(e)
            self.api.send_message(
                chat_id,
                "Couldn't generate right now. Try /lesson again in a minute.",
            )

    # ── LLM call helper ───────────────────────────────────────────────

    def _llm_call(self, text: str, teacher_id: str) -> str:
        """Call the LLM with one retry on failure.

        Runs in a thread to avoid blocking the Telegram polling loop.
        If the call takes too long (>120s), times out gracefully.
        """
        from concurrent.futures import ThreadPoolExecutor
        from concurrent.futures import TimeoutError as FutureTimeout

        from eduagent.openclaw_plugin import handle_message as process

        def _run() -> str:
            try:
                return asyncio.run(process(text, teacher_id=teacher_id))
            except Exception as first_err:
                _log_error(first_err)
                logger.warning("First attempt failed: %s, retrying...", first_err)
                time.sleep(1)
                return asyncio.run(process(text, teacher_id=teacher_id))

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_run)
            try:
                return future.result(timeout=120)
            except FutureTimeout:
                raise RuntimeError(
                    "That's taking too long -- try a smaller request "
                    "or a more specific topic."
                )
            except Exception:
                raise

    def _try_offer_rating(self, chat_id: int, teacher_id: str) -> None:
        """Try to offer export + rating buttons if a lesson was just generated."""
        try:
            from eduagent.openclaw_plugin import get_last_lesson_id
            lesson_id = get_last_lesson_id(teacher_id)
            if lesson_id:
                self._last_lesson_id[chat_id] = lesson_id
                # Try to cache the lesson data for export
                try:
                    from eduagent.models import DailyLesson
                    from eduagent.state import _get_conn, init_db
                    init_db()
                    with _get_conn() as conn:
                        row = conn.execute(
                            "SELECT lesson_json FROM generated_lessons WHERE id = ?",
                            (lesson_id,),
                        ).fetchone()
                    if row and row["lesson_json"]:
                        self._last_lesson_data[chat_id] = (
                            DailyLesson.model_validate_json(row["lesson_json"])
                        )
                except Exception:
                    pass  # Caching is best-effort
                self.api.send_message(
                    chat_id,
                    "Download as:  Slides | Handout | Word Doc\n"
                    "Rate this lesson to help me improve:",
                    reply_markup=_post_generation_keyboard(lesson_id),
                )
        except Exception:
            pass  # Rating prompt is best-effort


def run_bot(
    token: str,
    data_dir: Path | None = None,
    *,
    force: bool = False,
) -> None:
    """Run the new lightweight EDUagent Telegram bot.

    Args:
        token: Telegram bot token from @BotFather.
        data_dir: Directory for persistent state (default: ~/.eduagent).
        force: If True, remove stale lock and start even if another instance exists.
    """
    bot = EduAgentTelegramBot(token=token, data_dir=data_dir)
    bot.run(force=force)
