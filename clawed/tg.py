"""Backward compatibility — import from clawed.transports.telegram."""
from clawed.transports.telegram import *  # noqa: F401, F403
from clawed.transports.telegram import (  # noqa: F401, E402
    EduAgentTelegramBot,
    TelegramAPI,
    _BOT_LOCK,
    _check_bot_lock,
    _release_bot_lock,
    run_bot,
)
