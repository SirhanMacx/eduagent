"""EDUagent Telegram Bot — Standalone, no OpenClaw required.

Teachers set up their own bot via BotFather and run:
    eduagent bot --token YOUR_BOT_TOKEN

That's it. No OpenClaw, no gateway, no extensions.
EDUagent is the product.
"""

from __future__ import annotations

import asyncio
import enum
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from eduagent.bot_state import BotStateStore

logger = logging.getLogger(__name__)

RATING_CALLBACK_PREFIX = "rate:"
ACTION_CALLBACK_PREFIX = "action:"

# Error log path
_ERROR_LOG = Path.home() / ".eduagent" / "errors.log"


# ── Conversation state machine ────────────────────────────────────────────

class ConversationState(enum.Enum):
    IDLE = "idle"
    COLLECTING_LESSON_INFO = "collecting"
    GENERATING = "generating"
    DONE = "done"


class ChatState:
    """Per-chat state tracker."""

    def __init__(self) -> None:
        self.state = ConversationState.IDLE
        self.pending_topic: str = ""
        self.last_lesson_id: str = ""

    def is_busy(self) -> bool:
        return self.state == ConversationState.GENERATING


# Module-level state dict keyed by chat_id (in-memory cache)
_chat_states: dict[int, ChatState] = {}

# Persistent store — lazy-initialized to avoid side effects at import time
_state_store: "BotStateStore | None" = None


def _get_store() -> "BotStateStore":
    global _state_store
    if _state_store is None:
        from eduagent.bot_state import BotStateStore

        _state_store = BotStateStore()
    return _state_store


def _get_chat_state(chat_id: int) -> ChatState:
    if chat_id not in _chat_states:
        # Try to restore from persistent storage
        store = _get_store()
        row = store.get(chat_id)
        cs = ChatState()
        if row is not None:
            try:
                cs.state = ConversationState(row["state"])
            except (ValueError, KeyError):
                cs.state = ConversationState.IDLE
            cs.pending_topic = row.get("pending_topic", "")
            cs.last_lesson_id = row.get("last_lesson_id", "")
        _chat_states[chat_id] = cs
    return _chat_states[chat_id]


def _persist_chat_state(chat_id: int, cs: ChatState) -> None:
    """Write current in-memory state to the persistent store."""
    store = _get_store()
    store.save(
        chat_id,
        state=cs.state.value,
        pending_topic=cs.pending_topic,
        last_lesson_id=cs.last_lesson_id,
    )


def _log_error(error: Exception) -> None:
    """Append error to the errors.log file."""
    try:
        _ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(_ERROR_LOG, "a") as f:
            import datetime
            f.write(f"[{datetime.datetime.now(datetime.timezone.utc).isoformat()}] {type(error).__name__}: {error}\n")
    except Exception:
        pass


# ── Bot commands for BotFather registration ──────────────────────────────

BOT_COMMANDS = [
    ("lesson", "Generate a daily lesson"),
    ("unit", "Plan a unit"),
    ("assess", "Create an assessment"),
    ("worksheet", "Generate a worksheet"),
    ("progress", "Student progress report"),
    ("help", "Show all commands"),
    ("health", "System status"),
]


class EduAgentBot:
    """Standalone Telegram bot for EDUagent.

    Uses python-telegram-bot to run a native bot.
    Imports and reuses all generation logic from the core modules.

    Token resolution order:
        1. ``token`` constructor argument
        2. ``TELEGRAM_BOT_TOKEN`` environment variable
        3. Saved config (``eduagent config set-token TOKEN``)

    Webhook mode: pass ``webhook_url`` to ``start()`` to receive updates via
    HTTPS POST instead of long-polling. Useful for VPS / server deployments.
    """

    def __init__(
        self,
        token: str,
        data_dir: Optional[Path] = None,
        *,
        webhook_url: Optional[str] = None,
        webhook_port: int = 8443,
        webhook_secret: Optional[str] = None,
    ):
        self.token = token
        self.data_dir = data_dir or Path.home() / ".eduagent"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.webhook_url = webhook_url
        self.webhook_port = webhook_port
        self.webhook_secret = webhook_secret

    @classmethod
    def from_env(
        cls,
        data_dir: Optional[Path] = None,
        *,
        webhook_url: Optional[str] = None,
        webhook_port: int = 8443,
        webhook_secret: Optional[str] = None,
    ) -> "EduAgentBot":
        """Create a bot by resolving the token from the environment.

        Token resolution order:
            1. ``TELEGRAM_BOT_TOKEN`` environment variable
            2. Saved config (``eduagent config set-token TOKEN``)

        Raises ``ValueError`` if no token can be found.
        """
        import os

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
        return cls(
            token=token,
            data_dir=data_dir,
            webhook_url=webhook_url,
            webhook_port=webhook_port,
            webhook_secret=webhook_secret,
        )

    def start(
        self,
        *,
        webhook_url: Optional[str] = None,
        webhook_port: Optional[int] = None,
        webhook_secret: Optional[str] = None,
    ) -> None:
        """Start the bot — polling or webhook depending on configuration.

        Webhook mode is activated when ``webhook_url`` is provided (either here
        or via the constructor).  The bot will listen on ``webhook_port``
        (default 8443) for incoming HTTPS POST requests.

        Polling mode is the default — it works without any public URL or TLS,
        so it is ideal for local development and teacher laptops.
        """
        # Resolve per-call overrides vs constructor defaults
        effective_webhook = webhook_url or self.webhook_url
        effective_port = webhook_port if webhook_port is not None else self.webhook_port
        effective_secret = webhook_secret or self.webhook_secret
        try:
            from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
            from telegram.ext import (
                Application,
                CallbackQueryHandler,
                CommandHandler,
                MessageHandler,
                filters,
            )
        except ImportError:
            raise ImportError(
                "python-telegram-bot is required to run the Telegram bot.\n"
                "Install it with: pip install 'eduagent[telegram]'\n"
                "Or: pip install python-telegram-bot"
            )

        from eduagent.state import TeacherSession

        app = Application.builder().token(self.token).build()

        def _rating_keyboard(lesson_id: str) -> InlineKeyboardMarkup:
            """Build an inline keyboard with 1-5 star buttons + skip."""
            buttons = [
                InlineKeyboardButton(f"{'★' * i}", callback_data=f"{RATING_CALLBACK_PREFIX}{lesson_id}:{i}")
                for i in range(1, 6)
            ]
            skip_btn = InlineKeyboardButton("Skip", callback_data=f"{RATING_CALLBACK_PREFIX}{lesson_id}:0")
            return InlineKeyboardMarkup([buttons, [skip_btn]])

        def _post_generation_keyboard(lesson_id: str) -> InlineKeyboardMarkup:
            """Quick action buttons after generation."""
            return InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Rate this", callback_data=f"{RATING_CALLBACK_PREFIX}{lesson_id}:0_prompt"),
                    InlineKeyboardButton(
                        "Generate worksheet",
                        callback_data=f"{ACTION_CALLBACK_PREFIX}worksheet:{lesson_id}",
                    ),
                ],
            ])

        async def _send_response(update: Any, response: str) -> None:
            """Send a response, splitting long messages for Telegram's limit."""
            if len(response) <= 4096:
                await update.message.reply_text(response, parse_mode="Markdown")
            else:
                for chunk in [response[i:i + 4000] for i in range(0, len(response), 4000)]:
                    await update.message.reply_text(chunk, parse_mode="Markdown")

        async def _llm_call_with_retry(text: str, teacher_id: str) -> str:
            """Call LLM with one retry on failure."""
            from eduagent.openclaw_plugin import handle_message as process

            try:
                return await process(text, teacher_id=teacher_id)
            except Exception as first_err:
                _log_error(first_err)
                logger.warning(f"First attempt failed: {first_err}, retrying...")
                await asyncio.sleep(1)
                try:
                    return await process(text, teacher_id=teacher_id)
                except Exception as retry_err:
                    _log_error(retry_err)
                    raise

        async def handle_message(update: Any, context: Any) -> None:
            """Route every message through the EDUagent intent router."""
            if not update.message or not update.message.text:
                return

            chat_id = update.message.chat_id
            teacher_id = str(update.message.from_user.id)
            text = update.message.text
            state = _get_chat_state(chat_id)

            # If currently generating, tell user to wait
            if state.is_busy():
                await update.message.reply_text(
                    "Still working on your lesson -- almost done!"
                )
                return

            # Show typing indicator
            await update.message.chat.send_action("typing")

            state.state = ConversationState.GENERATING
            _persist_chat_state(chat_id, state)
            try:
                response = await _llm_call_with_retry(text, teacher_id)
            except Exception as e:
                logger.error(f"Error handling message: {e}")
                _log_error(e)
                response = (
                    "Couldn't generate right now. Try `/lesson` again in a minute."
                )
            finally:
                state.state = ConversationState.IDLE
                _persist_chat_state(chat_id, state)

            await _send_response(update, response)

            # Check if a lesson was just generated — offer rating
            try:
                from eduagent.openclaw_plugin import get_last_lesson_id
                lesson_id = get_last_lesson_id(teacher_id)
                if lesson_id:
                    state.last_lesson_id = lesson_id
                    state.state = ConversationState.DONE
                    _persist_chat_state(chat_id, state)
                    await update.message.reply_text(
                        "What would you like to do next?",
                        reply_markup=_post_generation_keyboard(lesson_id),
                    )
                    # Log to workspace daily notes
                    try:
                        from eduagent.workspace import append_daily_note
                        topic = text[:100] if text else "unknown topic"
                        append_daily_note(
                            f"Generated lesson via Telegram: {topic}",
                            category="lesson",
                        )
                    except Exception:
                        pass  # Workspace logging is best-effort
            except Exception:
                pass  # Rating prompt is best-effort

        async def handle_rating_callback(update: Any, context: Any) -> None:
            """Handle inline keyboard rating button presses."""
            query = update.callback_query
            if not query or not query.data or not query.data.startswith(RATING_CALLBACK_PREFIX):
                return

            await query.answer()

            data = query.data[len(RATING_CALLBACK_PREFIX):]
            parts = data.split(":")
            if len(parts) != 2:
                return

            lesson_id, rating_str = parts

            # Handle the "prompt for rating" button
            if rating_str == "0_prompt":
                await query.edit_message_text(
                    "How was this lesson? Rate it to help me improve:",
                    reply_markup=_rating_keyboard(lesson_id),
                )
                return

            try:
                rating = int(rating_str)
            except ValueError:
                return

            if rating == 0:
                await query.edit_message_text("Skipped rating. You can always rate later!")
                return

            try:
                from eduagent.analytics import rate_lesson
                success = rate_lesson(str(query.from_user.id), lesson_id, rating)
                if success:
                    stars = "★" * rating + "☆" * (5 - rating)
                    await query.edit_message_text(f"Thanks! Rated {stars} ({rating}/5)")
                    # Log rating to workspace
                    try:
                        from eduagent.workspace import append_daily_note, update_memory
                        append_daily_note(
                            f"Lesson {lesson_id[:8]} rated {rating}/5",
                            category="feedback",
                        )
                        if rating == 5:
                            update_memory(
                                "Lessons That Got 5-Star Ratings",
                                f"Lesson {lesson_id[:8]} (via Telegram)",
                            )
                    except Exception:
                        pass  # Workspace logging is best-effort
                else:
                    await query.edit_message_text("Couldn't find that lesson to rate.")
            except Exception as e:
                logger.error(f"Error saving rating: {e}")
                _log_error(e)
                await query.edit_message_text("Had trouble saving the rating. Try again later.")

        async def handle_action_callback(update: Any, context: Any) -> None:
            """Handle post-generation action buttons (worksheet, etc.)."""
            query = update.callback_query
            if not query or not query.data or not query.data.startswith(ACTION_CALLBACK_PREFIX):
                return

            await query.answer()

            data = query.data[len(ACTION_CALLBACK_PREFIX):]
            parts = data.split(":")
            if len(parts) != 2:
                return

            action, lesson_id = parts

            if action == "worksheet":
                teacher_id = str(query.from_user.id)
                await query.edit_message_text("Generating worksheet...")
                try:
                    response = await _llm_call_with_retry(
                        f"generate a worksheet for lesson {lesson_id}", teacher_id
                    )
                    await query.message.reply_text(response, parse_mode="Markdown")
                except Exception as e:
                    logger.error(f"Error generating worksheet: {e}")
                    _log_error(e)
                    await query.message.reply_text(
                        "Couldn't generate the worksheet right now. Try /worksheet."
                    )
            else:
                await query.edit_message_text(f"Unknown action: {action}")

        async def cmd_start(update: Any, context: Any) -> None:
            await update.message.reply_text(
                "Welcome to EDUagent!\n\n"
                "I'm your AI teaching assistant. I learn from your lesson plans "
                "and generate lessons, units, and materials in your exact teaching voice.\n\n"
                "To get started:\n"
                "- Share a folder path: my materials are in ~/Documents/Lessons/\n"
                "- Or just tell me what you teach: I teach 8th grade social studies\n\n"
                "Type /help to see what I can do.",
            )

        async def cmd_help(update: Any, context: Any) -> None:
            await update.message.reply_text(
                "EDUagent Commands\n\n"
                "Generate content:\n"
                "/lesson - Generate a daily lesson\n"
                "/unit - Plan a unit\n"
                "/assess - Create an assessment\n"
                "/worksheet - Generate a worksheet\n\n"
                "Setup:\n"
                "/status - See your profile and config\n"
                "/health - System status\n\n"
                "Student bot:\n"
                "start student bot for lesson 1 - get a class code for students",
            )

        async def cmd_status(update: Any, context: Any) -> None:
            teacher_id = str(update.message.from_user.id)
            from eduagent.openclaw_plugin import _show_status
            session = TeacherSession.load(teacher_id)
            await update.message.reply_text(_show_status(session))

        async def cmd_health(update: Any, context: Any) -> None:
            """Return system health: model, persona, lesson count, corpus size."""
            teacher_id = str(update.message.from_user.id)
            from eduagent.models import AppConfig
            cfg = AppConfig.load()

            provider = cfg.provider.value
            model = {
                "anthropic": cfg.anthropic_model,
                "openai": cfg.openai_model,
                "ollama": cfg.ollama_model,
            }.get(provider, "unknown")

            session = TeacherSession.load(teacher_id)
            has_persona = session.persona is not None

            lesson_count = 0
            corpus_size = 0
            try:
                from eduagent.state import _get_conn, init_db
                init_db()
                with _get_conn() as conn:
                    row = conn.execute(
                        "SELECT COUNT(*) as c FROM generated_lessons WHERE teacher_id = ?",
                        (teacher_id,),
                    ).fetchone()
                    lesson_count = row["c"] if row else 0
            except Exception:
                pass

            try:
                import sqlite3
                corpus_path = Path.home() / ".eduagent" / "corpus" / "corpus.db"
                if corpus_path.exists():
                    cconn = sqlite3.connect(str(corpus_path))
                    cconn.row_factory = sqlite3.Row
                    crow = cconn.execute("SELECT COUNT(*) as c FROM corpus_examples").fetchone()
                    corpus_size = crow["c"] if crow else 0
                    cconn.close()
            except Exception:
                pass

            health_text = (
                "EDUagent Health\n\n"
                f"Model: {model} ({provider})\n"
                f"Persona loaded: {'yes' if has_persona else 'no'}\n"
                f"Lessons generated: {lesson_count}\n"
                f"Corpus examples: {corpus_size}"
            )
            await update.message.reply_text(health_text)

        async def cmd_lesson(update: Any, context: Any) -> None:
            """Shortcut to generate a lesson."""
            chat_id = update.message.chat_id
            state = _get_chat_state(chat_id)
            state.state = ConversationState.COLLECTING_LESSON_INFO
            _persist_chat_state(chat_id, state)
            await update.message.reply_text(
                "What topic should the lesson be about? "
                "(e.g. 'photosynthesis for 6th grade' or 'causes of WWI')"
            )

        async def cmd_unit(update: Any, context: Any) -> None:
            """Shortcut to plan a unit."""
            await update.message.reply_text(
                "What topic should the unit cover? "
                "(e.g. 'The American Revolution for 8th grade, 3 weeks')"
            )

        async def cmd_assess(update: Any, context: Any) -> None:
            """Shortcut to create an assessment."""
            await update.message.reply_text(
                "What should the assessment cover? "
                "(e.g. 'Unit test on cell biology' or 'DBQ on industrialization')"
            )

        async def cmd_worksheet(update: Any, context: Any) -> None:
            """Shortcut to generate a worksheet."""
            await update.message.reply_text(
                "What topic is the worksheet for? "
                "(e.g. 'fractions practice for 5th grade')"
            )

        async def cmd_progress(update: Any, context: Any) -> None:
            """Show student progress report for the teacher's classes."""
            teacher_id = str(update.message.from_user.id)
            try:
                from eduagent.student_bot import StudentBot
                bot = StudentBot()

                # Find teacher's active classes
                from eduagent.state import _get_conn as _get_main_conn, init_db
                init_db()
                with _get_main_conn() as conn:
                    rows = conn.execute(
                        "SELECT class_code, name, topic FROM classes WHERE teacher_id = ?",
                        (teacher_id,),
                    ).fetchall()

                if not rows:
                    await update.message.reply_text(
                        "No active classes found. Start one with 'start student bot for [lesson]'."
                    )
                    return

                report_parts = ["Student Progress Report\n"]
                for row in rows:
                    code = row["class_code"]
                    class_name = row["name"] or code
                    report_parts.append(f"\nClass: {class_name} ({code})")
                    progress_list = bot.get_student_progress(code)
                    if not progress_list:
                        report_parts.append("  No student activity yet.")
                        continue

                    # Sort by most active
                    for p in progress_list:
                        name = p.get("student_name") or f"Student {p['student_id'][:8]}"
                        total = p.get("total_questions", 0)
                        struggles = p.get("struggle_topics", [])
                        last = p.get("last_active", "")[:16]
                        line = f"  {name}: {total} questions"
                        if last:
                            line += f" (last: {last})"
                        report_parts.append(line)
                        if struggles:
                            report_parts.append(f"    Struggling: {', '.join(struggles)}")

                    # Topic summary
                    all_topics: dict[str, int] = {}
                    for p in progress_list:
                        for topic, count in p.get("topics_asked", {}).items():
                            all_topics[topic] = all_topics.get(topic, 0) + count
                    if all_topics:
                        sorted_topics = sorted(all_topics.items(), key=lambda x: x[1], reverse=True)[:5]
                        report_parts.append("  Top topics asked about:")
                        for topic, count in sorted_topics:
                            report_parts.append(f"    {topic}: {count}x")

                await _send_response(update, "\n".join(report_parts))

            except Exception as e:
                logger.error(f"Error in /progress: {e}")
                _log_error(e)
                await update.message.reply_text(
                    "Couldn't generate progress report right now. Try again later."
                )

        # Register command menu with BotFather API
        async def _post_init(application: Any) -> None:
            """Called after the application is initialized — registers commands."""
            try:
                await application.bot.set_my_commands(
                    [BotCommand(cmd, desc) for cmd, desc in BOT_COMMANDS]
                )
                logger.info("Bot commands registered with Telegram.")
            except Exception as e:
                logger.warning(f"Could not register bot commands: {e}")

        app.post_init = _post_init

        # Register handlers
        app.add_handler(CommandHandler("start", cmd_start))
        app.add_handler(CommandHandler("help", cmd_help))
        app.add_handler(CommandHandler("status", cmd_status))
        app.add_handler(CommandHandler("health", cmd_health))
        app.add_handler(CommandHandler("lesson", cmd_lesson))
        app.add_handler(CommandHandler("unit", cmd_unit))
        app.add_handler(CommandHandler("assess", cmd_assess))
        app.add_handler(CommandHandler("worksheet", cmd_worksheet))
        app.add_handler(CommandHandler("progress", cmd_progress))
        app.add_handler(CallbackQueryHandler(handle_rating_callback, pattern=f"^{RATING_CALLBACK_PREFIX}"))
        app.add_handler(CallbackQueryHandler(handle_action_callback, pattern=f"^{ACTION_CALLBACK_PREFIX}"))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        logger.info("EDUagent bot starting...")
        print("EDUagent bot is running. Press Ctrl+C to stop.")
        print(f"   Data directory: {self.data_dir}")

        if effective_webhook:
            # Webhook mode: Telegram pushes updates to our HTTPS endpoint.
            # Great for VPS deployments; requires a valid TLS certificate or
            # a reverse proxy (nginx/Caddy) terminating TLS.
            print(f"   Mode: webhook → {effective_webhook}")
            logger.info("Starting in webhook mode: %s", effective_webhook)

            run_kwargs: dict = {
                "webhook_url": effective_webhook,
                "port": effective_port,
                "drop_pending_updates": True,
            }
            # Secret token prevents random POST requests from triggering the bot
            if effective_secret:
                run_kwargs["secret_token"] = effective_secret

            app.run_webhook(**run_kwargs)
        else:
            # Polling mode: the bot polls Telegram for new updates.
            # Works everywhere without any public URL — perfect for local dev
            # and teacher laptops behind NAT/firewalls.
            print("   Mode: polling")
            logger.info("Starting in polling mode")
            app.run_polling(drop_pending_updates=True)


def run_bot(
    token: str,
    data_dir: Optional[Path] = None,
    *,
    webhook_url: Optional[str] = None,
    webhook_port: int = 8443,
    webhook_secret: Optional[str] = None,
) -> None:
    """Run the EDUagent Telegram bot.

    Args:
        token: Telegram bot token from @BotFather.
        data_dir: Directory for persistent state (default: ~/.eduagent).
        webhook_url: If provided, run in webhook mode instead of polling.
            Must be a publicly reachable HTTPS URL
            (e.g. ``https://myserver.com/webhook``).
        webhook_port: Local port to listen on in webhook mode (default 8443).
        webhook_secret: Optional secret token to verify incoming webhook requests.
    """
    bot = EduAgentBot(
        token=token,
        data_dir=data_dir,
        webhook_url=webhook_url,
        webhook_port=webhook_port,
        webhook_secret=webhook_secret,
    )
    bot.start()
