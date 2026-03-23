"""EDUagent Telegram Bot — Standalone, no OpenClaw required.

Teachers set up their own bot via BotFather and run:
    eduagent bot --token YOUR_BOT_TOKEN

That's it. No OpenClaw, no gateway, no extensions.
EDUagent is the product.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class EduAgentBot:
    """Standalone Telegram bot for EDUagent.

    Uses python-telegram-bot to run a native bot.
    Imports and reuses all generation logic from the core modules.
    """

    def __init__(self, token: str, data_dir: Optional[Path] = None):
        self.token = token
        self.data_dir = data_dir or Path.home() / ".eduagent"
        self.data_dir.mkdir(parents=True, exist_ok=True)

    async def start(self) -> None:
        """Start the bot and begin polling for messages."""
        try:
            from telegram.ext import (
                Application,
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

        async def handle_message(update, context):
            """Route every message through the EDUagent intent router."""
            if not update.message or not update.message.text:
                return

            teacher_id = str(update.message.from_user.id)
            text = update.message.text

            # Show typing indicator
            await update.message.chat.send_action("typing")

            try:
                from eduagent.openclaw_plugin import handle_message as process
                response = await process(text, teacher_id=teacher_id)
            except Exception as e:
                logger.error(f"Error handling message: {e}")
                response = (
                    "I ran into an issue processing that. "
                    "Check your API key with `/status` or try again."
                )

            # Split long responses (Telegram 4096 char limit)
            if len(response) <= 4096:
                await update.message.reply_text(response, parse_mode="Markdown")
            else:
                # Send in chunks
                for chunk in [response[i:i+4000] for i in range(0, len(response), 4000)]:
                    await update.message.reply_text(chunk, parse_mode="Markdown")

        async def cmd_start(update, context):
            await update.message.reply_text(
                "🎓 *Welcome to EDUagent!*\n\n"
                "I'm your AI teaching assistant. I learn from your lesson plans "
                "and generate lessons, units, and materials in your exact teaching voice.\n\n"
                "To get started:\n"
                "• Share a folder path: `my materials are in ~/Documents/Lessons/`\n"
                "• Or just tell me what you teach: `I teach 8th grade social studies`\n\n"
                "Type `/help` to see what I can do.",
                parse_mode="Markdown"
            )

        async def cmd_help(update, context):
            await update.message.reply_text(
                "🎓 *EDUagent Commands*\n\n"
                "*Generate content:*\n"
                "• Plan a unit on \\[topic\\] for \\[grade\\]\n"
                "• Generate a lesson on \\[topic\\]\n"
                "• Make a worksheet for \\[topic\\]\n"
                "• Create an assessment\n"
                "• Write a sub packet for tomorrow\n\n"
                "*Research:*\n"
                "• Find a current news story about \\[topic\\]\n"
                "• What standards apply to \\[topic\\] for grade \\[N\\]?\n\n"
                "*Setup:*\n"
                "• `/status` — see your profile and config\n"
                "• `/setup` — guided configuration\n\n"
                "*Student bot:*\n"
                "• `start student bot for lesson 1` — get a class code for students",
                parse_mode="Markdown"
            )

        async def cmd_status(update, context):
            teacher_id = str(update.message.from_user.id)
            from eduagent.openclaw_plugin import _show_status
            session = TeacherSession.load(teacher_id)
            await update.message.reply_text(_show_status(session), parse_mode="Markdown")

        # Register handlers
        app.add_handler(CommandHandler("start", cmd_start))
        app.add_handler(CommandHandler("help", cmd_help))
        app.add_handler(CommandHandler("status", cmd_status))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        logger.info("EDUagent bot starting...")
        print("🎓 EDUagent bot is running. Press Ctrl+C to stop.")
        print(f"   Data directory: {self.data_dir}")

        await app.run_polling(drop_pending_updates=True)


async def run_bot(token: str, data_dir: Optional[Path] = None) -> None:
    """Run the EDUagent Telegram bot."""
    bot = EduAgentBot(token=token, data_dir=data_dir)
    await bot.start()
