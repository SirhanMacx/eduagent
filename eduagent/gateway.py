"""Lightweight async message gateway for EDUagent.

Handles Telegram polling, manages teacher sessions, routes messages
to the generation engine. Emits events that the TUI can subscribe to
for live display.

    gateway = EduAgentGateway(token="...", config=config)
    await gateway.start()           # start Telegram + event loop
    event = await gateway.event_bus.get()  # TUI reads events
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from eduagent.models import AppConfig

logger = logging.getLogger(__name__)


# ── Data classes ──────────────────────────────────────────────────────


@dataclass
class ActivityEvent:
    """A single event for the TUI activity feed."""

    timestamp: float
    event_type: str  # message_received, generation_started, generation_complete, error, system
    actor: str
    message: str
    data: dict = field(default_factory=dict)


@dataclass
class GatewayStats:
    """Live counters for the gateway dashboard."""

    messages_today: int = 0
    generations_today: int = 0
    errors_today: int = 0
    _start_time: float = field(default_factory=time.monotonic)

    @property
    def uptime_seconds(self) -> float:
        return time.monotonic() - self._start_time


# ── Gateway ───────────────────────────────────────────────────────────


class EduAgentGateway:
    """Lightweight async gateway for EDUagent.

    Handles Telegram polling, manages teacher sessions, routes messages.
    Emits events that the TUI can subscribe to for live display.
    """

    def __init__(self, token: Optional[str] = None, config: Optional[AppConfig] = None):
        self.token = token
        self.config = config or AppConfig.load()
        self.event_bus: asyncio.Queue[ActivityEvent] = asyncio.Queue(maxsize=500)
        self.active_sessions: dict[str, dict] = {}
        self._gateway_stats = GatewayStats()
        self._running = False
        self._telegram_app = None

    # ── Events ────────────────────────────────────────────────────────

    async def emit(self, event_type: str, data: Optional[dict] = None) -> None:
        """Emit an event for TUI consumption.

        Event types: message_received, generation_started,
                     generation_complete, error, system
        """
        event = ActivityEvent(
            timestamp=time.time(),
            event_type=event_type,
            actor=data.get("teacher_name", "system") if data else "system",
            message=data.get("text", data.get("message", event_type)) if data else event_type,
            data=data or {},
        )
        # Drop oldest if full
        if self.event_bus.full():
            try:
                self.event_bus.get_nowait()
            except asyncio.QueueEmpty:
                pass
        await self.event_bus.put(event)

    async def stats(self) -> dict:
        """Return live stats: messages today, generations today, active sessions."""
        s = self._gateway_stats
        return {
            "messages_today": s.messages_today,
            "generations_today": s.generations_today,
            "errors_today": s.errors_today,
            "uptime_seconds": s.uptime_seconds,
            "active_sessions": len(self.active_sessions),
        }

    # ── Telegram ──────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start the gateway (Telegram polling mode).

        If no token, runs in demo mode — no Telegram, only events for TUI.
        """
        self._running = True
        await self.emit("system", {"message": f"Gateway started ({'telegram' if self.token else 'demo'} mode)"})

        if not self.token:
            logger.info("Gateway running in demo mode (no Telegram token)")
            return

        try:
            from telegram import Update
            from telegram.ext import (
                Application,
                CommandHandler,
                MessageHandler,
                filters,
            )
        except ImportError:
            await self.emit("error", {"message": "python-telegram-bot not installed"})
            raise ImportError(
                "python-telegram-bot is required for Telegram support.\n"
                "Install with: pip install 'eduagent[telegram]'"
            )

        app = Application.builder().token(self.token).build()
        self._telegram_app = app
        gw = self  # closure ref

        async def _handle_message(update: Update, context) -> None:
            if not update.message or not update.message.text:
                return
            teacher_id = str(update.message.from_user.id)
            teacher_name = update.message.from_user.first_name or "Teacher"
            text = update.message.text

            gw._gateway_stats.messages_today += 1
            gw.active_sessions[teacher_id] = {
                "name": teacher_name,
                "last_activity": datetime.now().isoformat(),
            }
            await gw.emit("message_received", {
                "teacher_id": teacher_id,
                "teacher_name": teacher_name,
                "text": text[:200],
            })

            await update.message.chat.send_action("typing")

            try:
                await gw.emit("generation_started", {"teacher_name": teacher_name})
                from eduagent.openclaw_plugin import handle_message as process
                response = await process(text, teacher_id=teacher_id)
                gw._gateway_stats.generations_today += 1
                await gw.emit("generation_complete", {
                    "teacher_name": teacher_name,
                    "response_length": len(response),
                })
            except Exception as e:
                logger.error("Gateway message error: %s", e)
                gw._gateway_stats.errors_today += 1
                await gw.emit("error", {"teacher_name": teacher_name, "message": str(e)})
                response = "I ran into an issue processing that. Check your API key with `/status` or try again."

            if len(response) <= 4096:
                await update.message.reply_text(response, parse_mode="Markdown")
            else:
                for chunk in [response[i:i + 4000] for i in range(0, len(response), 4000)]:
                    await update.message.reply_text(chunk, parse_mode="Markdown")

        async def _cmd_start(update: Update, context) -> None:
            await update.message.reply_text(
                "\U0001f393 *Welcome to EDUagent!*\n\n"
                "I'm your AI teaching assistant. Send me a message to get started.\n"
                "Type `/help` to see what I can do.",
                parse_mode="Markdown",
            )

        async def _cmd_help(update: Update, context) -> None:
            await update.message.reply_text(
                "\U0001f393 *EDUagent Commands*\n\n"
                "Just type naturally:\n"
                "\u2022 Plan a unit on [topic]\n"
                "\u2022 Generate a lesson on [topic]\n"
                "\u2022 Make a worksheet\n\n"
                "`/status` \u2014 your profile\n"
                "`/help` \u2014 this message",
                parse_mode="Markdown",
            )

        async def _cmd_status(update: Update, context) -> None:
            teacher_id = str(update.message.from_user.id)
            from eduagent.openclaw_plugin import _show_status
            from eduagent.state import TeacherSession
            session = TeacherSession.load(teacher_id)
            await update.message.reply_text(_show_status(session), parse_mode="Markdown")

        app.add_handler(CommandHandler("start", _cmd_start))
        app.add_handler(CommandHandler("help", _cmd_help))
        app.add_handler(CommandHandler("status", _cmd_status))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _handle_message))

        logger.info("Gateway starting Telegram polling...")
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)

    async def stop(self) -> None:
        """Gracefully shut down Telegram polling."""
        self._running = False
        if self._telegram_app:
            await self._telegram_app.updater.stop()
            await self._telegram_app.stop()
            await self._telegram_app.shutdown()
        await self.emit("system", {"message": "Gateway stopped"})

    async def process_message(self, text: str, teacher_id: str = "cli", teacher_name: str = "Teacher") -> str:
        """Process a message directly (non-Telegram — for TUI demo mode)."""
        self._gateway_stats.messages_today += 1
        self.active_sessions[teacher_id] = {
            "name": teacher_name,
            "last_activity": datetime.now().isoformat(),
        }
        await self.emit("message_received", {"teacher_name": teacher_name, "text": text[:200]})

        try:
            await self.emit("generation_started", {"teacher_name": teacher_name})
            from eduagent.openclaw_plugin import handle_message as process
            response = await process(text, teacher_id=teacher_id)
            self._gateway_stats.generations_today += 1
            await self.emit("generation_complete", {"teacher_name": teacher_name, "response_length": len(response)})
            return response
        except Exception as e:
            logger.error("process_message error: %s", e)
            self._gateway_stats.errors_today += 1
            await self.emit("error", {"teacher_name": teacher_name, "message": str(e)})
            return f"Error: {e}"
