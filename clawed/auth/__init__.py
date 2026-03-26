"""Authentication helpers for LLM providers.

Also contains the simple API key authentication middleware for hosted mode.

Checks the ``Authorization: Bearer <key>`` header against a configured
set of API keys and resolves the associated teacher_id.

Keys are stored in ~/.eduagent/api_keys.json as a simple mapping:
    {"sk-abc123": "teacher_42", "sk-def456": "teacher_99"}
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

_BASE_DIR = Path(os.environ.get("EDUAGENT_DATA_DIR", str(Path.home() / ".eduagent")))
_KEYS_PATH = _BASE_DIR / "api_keys.json"

# In-memory cache of api_key -> teacher_id
_api_keys: dict[str, str] = {}


def _load_keys() -> dict[str, str]:
    """Load API keys from disk."""
    global _api_keys
    if _KEYS_PATH.exists():
        try:
            _api_keys = json.loads(_KEYS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            _api_keys = {}
    return _api_keys


def _save_keys(keys: dict[str, str]) -> None:
    """Persist API keys to disk."""
    global _api_keys
    _api_keys = keys
    _KEYS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _KEYS_PATH.write_text(json.dumps(keys, indent=2), encoding="utf-8")


def register_api_key(api_key: str, teacher_id: str) -> None:
    """Register a new API key for a teacher."""
    keys = _load_keys()
    keys[api_key] = teacher_id
    _save_keys(keys)


def revoke_api_key(api_key: str) -> bool:
    """Revoke an API key. Returns True if the key existed."""
    keys = _load_keys()
    if api_key in keys:
        del keys[api_key]
        _save_keys(keys)
        return True
    return False


def resolve_teacher_id(api_key: str) -> Optional[str]:
    """Look up the teacher_id for an API key, or None if invalid."""
    if not _api_keys:
        _load_keys()
    return _api_keys.get(api_key)


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Middleware that checks Authorization: Bearer <key> and injects teacher_id.

    Paths listed in ``exempt_paths`` skip authentication (health checks, docs, etc.).
    The resolved teacher_id is stored in ``request.state.teacher_id``.
    """

    def __init__(self, app, exempt_paths: Optional[list[str]] = None) -> None:  # type: ignore[override]
        super().__init__(app)
        self.exempt_paths = set(exempt_paths or ["/health", "/docs", "/openapi.json"])

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip auth for exempt paths
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"error": "Missing or invalid Authorization header. Use: Bearer <api_key>"},
            )

        api_key = auth_header[len("Bearer "):].strip()
        teacher_id = resolve_teacher_id(api_key)

        if teacher_id is None:
            return JSONResponse(
                status_code=403,
                content={"error": "Invalid API key."},
            )

        # Attach teacher_id to request state for downstream handlers
        request.state.teacher_id = teacher_id
        return await call_next(request)
