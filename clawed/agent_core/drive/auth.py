"""Google OAuth flow + token persistence for Drive access."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_TOKEN_PATH = Path.home() / ".eduagent" / "drive_token.json"

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
]


def save_token(token_data: dict[str, Any],
               token_path: Path | None = None) -> None:
    """Persist OAuth token to disk."""
    path = token_path or _DEFAULT_TOKEN_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(token_data, indent=2), encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def load_token(token_path: Path | None = None) -> dict[str, Any] | None:
    """Load OAuth token from disk. Returns None if not found."""
    path = token_path or _DEFAULT_TOKEN_PATH
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load Drive token: %s", e)
        return None


def is_authenticated(token_path: Path | None = None) -> bool:
    """Check if a valid Drive token exists."""
    return load_token(token_path) is not None
