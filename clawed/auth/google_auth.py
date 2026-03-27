"""Google Gemini authentication — API key or full browser OAuth2.

Resolution order:
1. Environment variables (GOOGLE_API_KEY / GEMINI_API_KEY)
2. OS keyring (stored by setup wizard or OAuth flow)
3. OAuth2 token file (~/.eduagent/google_oauth_token.json)
4. Full browser OAuth2 flow (opens browser, local callback server)
"""
from __future__ import annotations

import json
import logging
import os
import threading
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

logger = logging.getLogger(__name__)

# Google OAuth2 endpoints
_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"

# Installed-app / desktop client for Claw-ED (public client — no secret needed)
# Teachers can override with their own client_id via GOOGLE_CLIENT_ID env var
_DEFAULT_CLIENT_ID = "clawed-edu-app.apps.googleusercontent.com"
_REDIRECT_PORT = 8976
_REDIRECT_URI = f"http://localhost:{_REDIRECT_PORT}/callback"
_SCOPES = "https://www.googleapis.com/auth/generative-language"

_TOKEN_PATH = Path.home() / ".eduagent" / "google_oauth_token.json"


def get_google_api_key() -> str | None:
    """Resolve Google API key from env, keyring, or config."""
    key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    try:
        from clawed.config import get_api_key
        stored = get_api_key("google")
        if stored:
            return stored
    except Exception:
        pass
    return None


def get_google_oauth_token() -> str | None:
    """Get a valid OAuth2 access token, refreshing if needed."""
    if not _TOKEN_PATH.exists():
        return None
    try:
        data = json.loads(_TOKEN_PATH.read_text(encoding="utf-8"))
        # Check if token is expired
        expires_at = data.get("expires_at", 0)
        if datetime.now(timezone.utc).timestamp() < expires_at - 60:
            return data.get("access_token")
        # Try to refresh
        refresh_token = data.get("refresh_token")
        if refresh_token:
            return _refresh_token(refresh_token, data.get("client_id", _DEFAULT_CLIENT_ID))
    except Exception as e:
        logger.debug("OAuth token read failed: %s", e)
    return None


def get_google_credential() -> str | None:
    """Get any valid Google credential — API key or OAuth token."""
    api_key = get_google_api_key()
    if api_key:
        return api_key
    return get_google_oauth_token()


def has_google_credentials() -> bool:
    """Check if any Google credentials are available."""
    return get_google_credential() is not None


def run_google_oauth_flow(client_id: str | None = None) -> str:
    """Run the full browser OAuth2 flow.

    Opens the user's browser to the Google consent screen. A local
    HTTP server on localhost:8976 catches the callback with the auth
    code, exchanges it for tokens, and stores them securely.

    Returns the access token.

    Raises RuntimeError if the flow fails or times out.
    """
    cid = client_id or os.environ.get("GOOGLE_CLIENT_ID", _DEFAULT_CLIENT_ID)
    auth_code_holder: dict[str, Any] = {}
    error_holder: dict[str, str] = {}

    class _CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            if "code" in params:
                auth_code_holder["code"] = params["code"][0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(
                    b"<html><body><h2>Authenticated!</h2>"
                    b"<p>You can close this tab and return to Claw-ED.</p>"
                    b"</body></html>"
                )
            elif "error" in params:
                error_holder["error"] = params["error"][0]
                self.send_response(400)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(
                    b"<html><body><h2>Authentication failed</h2>"
                    b"<p>Please try again in Claw-ED.</p></body></html>"
                )
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format: str, *args: Any) -> None:
            pass  # Suppress HTTP server logs

    # Build authorization URL
    auth_params = urlencode({
        "client_id": cid,
        "redirect_uri": _REDIRECT_URI,
        "response_type": "code",
        "scope": _SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    })
    auth_url = f"{_AUTH_URL}?{auth_params}"

    # Start local server in a thread
    server = HTTPServer(("localhost", _REDIRECT_PORT), _CallbackHandler)
    server.timeout = 120  # 2 minute timeout

    def _serve():
        server.handle_request()  # Handle exactly one request

    thread = threading.Thread(target=_serve, daemon=True)
    thread.start()

    # Open browser
    print("\nOpening your browser to sign in with Google...")
    print(f"If the browser doesn't open, visit:\n{auth_url}\n")
    webbrowser.open(auth_url)

    # Wait for callback
    thread.join(timeout=130)
    server.server_close()

    if error_holder:
        raise RuntimeError(f"Google OAuth failed: {error_holder['error']}")
    if "code" not in auth_code_holder:
        raise RuntimeError("Google OAuth timed out. Please try again.")

    # Exchange auth code for tokens
    token_data = _exchange_code(auth_code_holder["code"], cid)
    _save_token(token_data, cid)
    return token_data["access_token"]


def _exchange_code(code: str, client_id: str) -> dict[str, Any]:
    """Exchange authorization code for access + refresh tokens."""
    resp = httpx.post(
        _TOKEN_URL,
        data={
            "code": code,
            "client_id": client_id,
            "redirect_uri": _REDIRECT_URI,
            "grant_type": "authorization_code",
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()


def _refresh_token(refresh_token: str, client_id: str) -> str | None:
    """Refresh an expired access token."""
    try:
        resp = httpx.post(
            _TOKEN_URL,
            data={
                "refresh_token": refresh_token,
                "client_id": client_id,
                "grant_type": "refresh_token",
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        # Update stored token
        token_data = {
            "access_token": data["access_token"],
            "refresh_token": refresh_token,  # Google doesn't always return a new one
            "expires_at": datetime.now(timezone.utc).timestamp() + data.get("expires_in", 3600),
            "client_id": client_id,
        }
        _save_token(token_data, client_id)
        return data["access_token"]
    except Exception as e:
        logger.debug("Token refresh failed: %s", e)
        return None


def _save_token(token_data: dict[str, Any], client_id: str) -> None:
    """Save OAuth tokens to disk."""
    _TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    save_data = {
        "access_token": token_data["access_token"],
        "refresh_token": token_data.get("refresh_token", ""),
        "expires_at": datetime.now(timezone.utc).timestamp() + token_data.get("expires_in", 3600),
        "client_id": client_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _TOKEN_PATH.write_text(json.dumps(save_data, indent=2), encoding="utf-8")
    # Restrict permissions
    try:
        _TOKEN_PATH.chmod(0o600)
    except OSError:
        pass
