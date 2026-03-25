"""Thin Telegram transport — delegates all logic to the Gateway.

Uses httpx (sync) for reliable cross-platform compatibility.
The bot is a ~200-line polling loop that:
  1. Receives updates from Telegram
  2. Delegates to Gateway.handle() / Gateway.handle_callback()
  3. Renders GatewayResponse back to Telegram

Usage:
    from clawed.transports.telegram import EduAgentTelegramBot
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
from typing import Any

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


# ── Thin transport ────────────────────────────────────────────────────


class EduAgentTelegramBot:
    """Thin Telegram transport — delegates everything to the Gateway."""

    COMMANDS = [
        {"command": "start", "description": "Welcome and setup guide"},
        {"command": "help", "description": "List all commands"},
        {"command": "lesson", "description": "Generate a daily lesson"},
        {"command": "unit", "description": "Plan a unit"},
        {"command": "export", "description": "Export last lesson"},
        {"command": "schedule", "description": "Manage reminders"},
        {"command": "gaps", "description": "Curriculum gap analysis"},
        {"command": "demo", "description": "Show demo lesson"},
    ]

    def __init__(self, token: str, data_dir: Path | None = None):
        self.token = token
        self.data_dir = data_dir or Path.home() / ".eduagent"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.api = TelegramAPI(token)
        self._running = False

        from clawed.gateway import Gateway
        self.gateway = Gateway()

    @classmethod
    def from_env(cls, data_dir: Path | None = None) -> EduAgentTelegramBot:
        """Create a bot by resolving the token from the environment."""
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not token:
            try:
                from clawed.models import AppConfig
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

        def _signal_handler(sig, frame):
            self._running = False
        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)

        self.api.set_my_commands(self.COMMANDS)
        me = self.api.get_me()
        bot_name = me.get("username", "unknown")
        logger.info("Bot @%s started, entering polling loop", bot_name)
        print(f"Claw-ED bot @{bot_name} is running. Press Ctrl+C to stop.")

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
        """Route an update through the Gateway."""
        try:
            if "callback_query" in update:
                cb = update["callback_query"]
                chat_id = cb["message"]["chat"]["id"]
                teacher_id = str(cb["from"]["id"])
                data = cb.get("data", "")
                self.api.answer_callback_query(cb["id"])
                response = asyncio.run(
                    self.gateway.handle_callback(data, teacher_id)
                )
                self._send_response(self.api, chat_id, response)

            elif "message" in update:
                msg = update["message"]
                chat_id = msg["chat"]["id"]
                teacher_id = str(msg["from"]["id"])

                # Download attached files
                files = self._download_files(msg)

                text = msg.get("text", "")
                self.api.send_chat_action(chat_id, "typing")
                response = asyncio.run(
                    self.gateway.handle(text, teacher_id, files=files or None)
                )
                self._send_response(self.api, chat_id, response)

        except Exception as e:
            logger.error("Error processing update: %s", e)
            _log_error(e)

    def _download_files(self, msg: dict) -> list[Path]:
        """Download any attached documents from a Telegram message."""
        files: list[Path] = []
        doc = msg.get("document")
        if not doc:
            return files

        file_info = self.api.get_file(doc["file_id"])
        tg_path = file_info.get("file_path")
        if not tg_path:
            return files

        suffix = Path(doc.get("file_name", "file")).suffix or ""
        local = Path(tempfile.mktemp(suffix=suffix, dir=self.data_dir / "downloads"))
        local.parent.mkdir(parents=True, exist_ok=True)
        if self.api.download_file(tg_path, local):
            files.append(local)
        return files

    def _send_response(self, api: TelegramAPI, chat_id: int, response: Any) -> None:
        """Render a GatewayResponse to Telegram messages."""
        from clawed.gateway_response import GatewayResponse

        if not isinstance(response, GatewayResponse) or not response.has_content:
            return

        reply_markup = None
        rows = response.button_rows
        if not rows and response.buttons:
            rows = [response.buttons]
        if rows:
            keyboard = []
            for row in rows:
                keyboard.append([
                    {
                        "text": b.label,
                        **({"url": b.url} if b.url else {"callback_data": b.callback_data}),
                    }
                    for b in row
                ])
            reply_markup = {"inline_keyboard": keyboard}

        if response.text:
            api.send_message(chat_id, response.text, reply_markup=reply_markup)

        for file_path in response.files:
            api.send_document(chat_id, file_path)


def run_bot(token: str | None = None, force: bool = False) -> None:
    """Entry point — create and run the bot."""
    if token:
        bot = EduAgentTelegramBot(token)
    else:
        bot = EduAgentTelegramBot.from_env()
    bot.run(force=force)
