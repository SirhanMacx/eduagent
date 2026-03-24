"""Student-facing Telegram bot — wraps the StudentBot engine.

Students join a class with a code from their teacher, then ask questions
about the lesson. The bot answers in the teacher's voice.

Separate from the teacher bot (telegram_bot.py). Run with:
    eduagent student-bot --token YOUR_STUDENT_BOT_TOKEN
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Error log path (separate from teacher bot)
_ERROR_LOG = Path.home() / ".eduagent" / "student_errors.log"

# Commands registered with BotFather
STUDENT_BOT_COMMANDS: list[tuple[str, str]] = [
    ("join", "Join a class with your class code"),
    ("topic", "See what your class is studying"),
    ("help", "Show all commands"),
    ("quit", "Leave your current class"),
]

# Module-level session store keyed by chat_id
_student_sessions: dict[int, dict[str, str]] = {}


def _get_session(chat_id: int) -> dict[str, str]:
    """Get or create a student session for a chat."""
    if chat_id not in _student_sessions:
        _student_sessions[chat_id] = {}
    return _student_sessions[chat_id]


def _log_error(error: Exception) -> None:
    """Append error to the student_errors.log file."""
    try:
        _ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(_ERROR_LOG, "a") as f:
            import datetime

            f.write(f"[{datetime.datetime.now(datetime.UTC).isoformat()}] {type(error).__name__}: {error}\n")
    except Exception:
        pass


async def _send_response(update: Any, text: str) -> None:
    """Send a response, splitting long messages for Telegram's 4096-char limit."""
    if len(text) <= 4096:
        await update.message.reply_text(text)
    else:
        for chunk in [text[i : i + 4000] for i in range(0, len(text), 4000)]:
            await update.message.reply_text(chunk)


class StudentTelegramBot:
    """Standalone Telegram bot for students.

    Students join with /join CODE, then ask free-text questions.
    The bot routes questions through the StudentBot engine.
    """

    def __init__(self, token: str) -> None:
        self.token = token

    async def start(self) -> None:
        """Build the Telegram application, register handlers, and start polling."""
        try:
            from telegram import BotCommand
            from telegram.ext import Application, CommandHandler, MessageHandler, filters
        except ImportError:
            raise ImportError(
                "python-telegram-bot is required to run the student bot.\n"
                "Install it with: pip install 'eduagent[telegram]'\n"
                "Or: pip install python-telegram-bot"
            )

        from eduagent.student_bot import StudentBot

        bot = StudentBot()
        app = Application.builder().token(self.token).build()

        # ── Command handlers ──────────────────────────────────────────

        async def cmd_start(update: Any, context: Any) -> None:
            """Welcome message — explain the bot and prompt for class code."""
            await update.message.reply_text(
                "Welcome to EDUagent Student Bot!\n\n"
                "I answer your questions about today's lesson — in your teacher's voice.\n\n"
                "To get started, use:\n"
                "  /join CODE  — join your class (e.g. /join AB-CDE-3)\n\n"
                "Once you've joined, just type your question and I'll help you out!\n"
                "Type /help to see all commands."
            )

        async def cmd_help(update: Any, context: Any) -> None:
            """Show all available commands."""
            await update.message.reply_text(
                "EDUagent Student Bot Commands\n\n"
                "/join CODE — Join a class with your class code\n"
                "/topic — See what your class is studying\n"
                "/help — Show this message\n"
                "/quit — Leave your current class\n\n"
                "After joining, just type your question!"
            )

        async def cmd_join(update: Any, context: Any) -> None:
            """Join a class with /join CODE."""
            chat_id = update.message.chat_id
            student_id = str(update.message.from_user.id)
            text = update.message.text.strip()

            # Extract code from "/join CODE"
            parts = text.split(maxsplit=1)
            if len(parts) < 2 or not parts[1].strip():
                await update.message.reply_text("Usage: /join CODE\n\nExample: /join AB-CDE-3")
                return

            code = parts[1].strip().upper()

            # Verify class exists and is not expired
            class_info = bot.get_class(code)
            if not class_info or bot.is_expired(code):
                await update.message.reply_text(
                    "That class code is not valid. Ask your teacher for a new one."
                )
                return

            # Enroll the student
            bot.register_student(student_id, code)

            # Save session
            session = _get_session(chat_id)
            session["class_code"] = code
            session["student_id"] = student_id

            teacher_name = class_info.name or "your teacher"
            topic = class_info.topic or "today's lesson"
            await update.message.reply_text(
                f"You joined {class_info.name or code}! "
                f"{teacher_name} is teaching {topic}. "
                f"Go ahead and ask me anything!"
            )

        async def cmd_topic(update: Any, context: Any) -> None:
            """Show current class and lesson topic."""
            chat_id = update.message.chat_id
            session = _get_session(chat_id)
            code = session.get("class_code")

            if not code:
                await update.message.reply_text(
                    "You haven't joined a class yet. Use /join CODE to connect to your class."
                )
                return

            class_info = bot.get_class(code)
            if not class_info:
                await update.message.reply_text(
                    "Your class is no longer available. Use /join CODE to join a new one."
                )
                return

            topic = class_info.topic or "No topic set yet"
            name = class_info.name or code
            await update.message.reply_text(f"Class: {name}\nTopic: {topic}")

        async def cmd_quit(update: Any, context: Any) -> None:
            """Leave the current class."""
            chat_id = update.message.chat_id
            session = _get_session(chat_id)

            if not session.get("class_code"):
                await update.message.reply_text("You're not in a class right now.")
                return

            class_name = session.get("class_code", "")
            session.clear()
            await update.message.reply_text(
                f"You left {class_name}. Use /join CODE to join another class."
            )

        async def handle_message(update: Any, context: Any) -> None:
            """Route free-text messages to the StudentBot engine."""
            if not update.message or not update.message.text:
                return

            chat_id = update.message.chat_id
            session = _get_session(chat_id)
            code = session.get("class_code")
            student_id = session.get("student_id", str(update.message.from_user.id))

            if not code:
                await update.message.reply_text(
                    "Use /join CODE first to connect to your class."
                )
                return

            # Show typing indicator
            await update.message.chat.send_action("typing")

            # Call StudentBot engine with retry
            try:
                answer = await bot.handle_message(update.message.text, student_id, code)
            except Exception as first_err:
                _log_error(first_err)
                logger.warning(f"First attempt failed: {first_err}, retrying...")
                await asyncio.sleep(1)
                try:
                    answer = await bot.handle_message(update.message.text, student_id, code)
                except Exception as retry_err:
                    _log_error(retry_err)
                    logger.error(f"Retry also failed: {retry_err}")
                    await update.message.reply_text(
                        "Hmm, I'm having trouble right now. Try asking again in a moment!"
                    )
                    return

            await _send_response(update, answer)

        # Register BotFather command menu
        async def _post_init(application: Any) -> None:
            """Register commands with Telegram after app init."""
            try:
                await application.bot.set_my_commands(
                    [BotCommand(cmd, desc) for cmd, desc in STUDENT_BOT_COMMANDS]
                )
                logger.info("Student bot commands registered with Telegram.")
            except Exception as e:
                logger.warning(f"Could not register student bot commands: {e}")

        app.post_init = _post_init

        # Register handlers
        app.add_handler(CommandHandler("start", cmd_start))
        app.add_handler(CommandHandler("help", cmd_help))
        app.add_handler(CommandHandler("join", cmd_join))
        app.add_handler(CommandHandler("topic", cmd_topic))
        app.add_handler(CommandHandler("quit", cmd_quit))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        logger.info("Student bot starting...")
        print("EDUagent student bot is running. Press Ctrl+C to stop.")

        await app.run_polling(drop_pending_updates=True)
