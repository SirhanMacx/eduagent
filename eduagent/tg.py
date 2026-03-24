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
import signal
import tempfile
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
    """Quick action buttons after generation."""
    return {
        "inline_keyboard": [
            [
                {"text": "Rate this", "callback_data": f"rate:{lesson_id}:0_prompt"},
                {"text": "Generate worksheet", "callback_data": f"action:worksheet:{lesson_id}"},
            ],
        ]
    }


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
        {"command": "export", "description": "Re-export last lesson"},
        {"command": "feedback", "description": "Recent ratings summary"},
        {"command": "standards", "description": "Look up standards"},
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
        }

        handler = handlers.get(cmd)
        if handler:
            handler(chat_id, msg, args)
        else:
            self.api.send_message(
                chat_id,
                f"Unknown command: /{cmd}\nType /help to see available commands.",
            )

    def _cmd_start(self, chat_id: int, msg: dict, args: str) -> None:
        self.api.send_message(
            chat_id,
            "Welcome to EDUagent!\n\n"
            "I'm your AI teaching assistant. I learn from your lesson plans "
            "and generate lessons, units, and materials in your exact teaching voice.\n\n"
            "Quick setup:\n"
            "1. Send me a lesson file (PDF, DOCX, PPTX) so I can learn your style\n"
            "2. Then use /lesson to generate a lesson on any topic\n\n"
            "Type /help to see everything I can do.",
        )

    def _cmd_help(self, chat_id: int, msg: dict, args: str) -> None:
        self.api.send_message(
            chat_id,
            "EDUagent Commands\n\n"
            "Generate content:\n"
            "  /lesson <topic> - Generate a daily lesson\n"
            "  /unit <topic> - Plan a unit\n"
            "  /demo - Show sample lesson output\n\n"
            "Setup:\n"
            "  /ingest - How to send teaching materials\n"
            "  /persona - Show current teaching persona\n"
            "  /settings - Show current config\n"
            "  /standards <subject> <grade> - Look up standards\n\n"
            "Reports:\n"
            "  /progress - Student progress report\n"
            "  /feedback - Recent ratings summary\n"
            "  /export - Re-export last lesson\n\n"
            "Tip: just send me a file to ingest your teaching materials!",
        )

    def _cmd_lesson(self, chat_id: int, msg: dict, args: str) -> None:
        if not args:
            self.api.send_message(
                chat_id,
                "What topic should the lesson be about?\n"
                "Example: /lesson photosynthesis for 6th grade",
            )
            return

        self.api.send_chat_action(chat_id, "typing")
        teacher_id = str(msg["from"]["id"])
        try:
            response = self._llm_call(args, teacher_id)
            self.api.send_message(chat_id, response)
            # Offer rating
            self._try_offer_rating(chat_id, teacher_id)
        except Exception as e:
            logger.error("Error generating lesson: %s", e)
            _log_error(e)
            self.api.send_message(
                chat_id,
                "Couldn't generate right now. Try /lesson again in a minute.",
            )

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
        lesson_id = self._last_lesson_id.get(chat_id)
        if not lesson_id:
            self.api.send_message(
                chat_id,
                "No recent lesson to export. Generate one with /lesson first.",
            )
            return
        self.api.send_message(
            chat_id,
            f"To export as PPTX/DOCX/PDF, use the CLI:\n"
            f"  eduagent export --lesson-id {lesson_id} --format pptx",
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

    # ── Message handler ───────────────────────────────────────────────

    def _handle_message(self, msg: dict) -> None:
        """Route free-text messages through the LLM."""
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "").strip()
        if not text:
            return

        teacher_id = str(msg["from"]["id"])
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
                        memory_process(_fb_lesson, rating)
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

    # ── LLM call helper ───────────────────────────────────────────────

    def _llm_call(self, text: str, teacher_id: str) -> str:
        """Call the LLM with one retry on failure."""
        from eduagent.openclaw_plugin import handle_message as process

        try:
            return asyncio.run(process(text, teacher_id=teacher_id))
        except Exception as first_err:
            _log_error(first_err)
            logger.warning("First attempt failed: %s, retrying...", first_err)
            time.sleep(1)
            try:
                return asyncio.run(process(text, teacher_id=teacher_id))
            except Exception as retry_err:
                _log_error(retry_err)
                raise

    def _try_offer_rating(self, chat_id: int, teacher_id: str) -> None:
        """Try to offer rating buttons if a lesson was just generated."""
        try:
            from eduagent.openclaw_plugin import get_last_lesson_id
            lesson_id = get_last_lesson_id(teacher_id)
            if lesson_id:
                self._last_lesson_id[chat_id] = lesson_id
                self.api.send_message(
                    chat_id,
                    "What would you like to do next?",
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
