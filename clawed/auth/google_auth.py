"""Google Gemini authentication — API key or OAuth."""
from __future__ import annotations

import os
import logging

logger = logging.getLogger(__name__)


def get_google_api_key() -> str | None:
    """Resolve Google API key from env, keyring, or config."""
    key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    try:
        from clawed.config import get_api_key
        return get_api_key("google")
    except Exception:
        return None


def has_google_credentials() -> bool:
    """Check if Google credentials are available."""
    return get_google_api_key() is not None
