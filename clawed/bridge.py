"""Bridge module for TS CLI -> Python provider routing.

Called via subprocess from the TypeScript CLI when the active provider
is not Anthropic (i.e. openai, google, ollama).  Reads a JSON request
on stdin, calls the appropriate LLM through the existing Python engine,
and writes a JSON response to stdout.

Protocol (stdin JSON):
  {
    "messages": [{"role": "user", "content": "..."}],
    "system":   "optional system prompt",
    "provider": "openai",         # from config if omitted
    "model":    "gpt-4o",         # from config if omitted
    "max_tokens": 4096,
    "temperature": 0.7
  }

Protocol (stdout JSON):
  {
    "status":  "success" | "error",
    "content": "the LLM response text",
    "model":   "gpt-4o",
    "usage":   {"input_tokens": 123, "output_tokens": 456},
    "error":   null | "description"
  }
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from typing import Any

logger = logging.getLogger(__name__)


def _inject_api_keys() -> None:
    """Load API keys from ~/.eduagent/secrets.json into environment.

    The Python LLM clients read from env vars (OPENAI_API_KEY, GOOGLE_API_KEY,
    etc.). The TS CLI stores keys in secrets.json, so we need to bridge them.
    Only sets vars that aren't already in the environment.
    """
    from pathlib import Path

    secrets_path = Path(
        os.environ.get("EDUAGENT_DATA_DIR", str(Path.home() / ".eduagent"))
    ) / "secrets.json"

    if not secrets_path.exists():
        return

    try:
        secrets = json.loads(secrets_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return

    env_map = {
        "openai_api_key": "OPENAI_API_KEY",
        "google_api_key": "GOOGLE_API_KEY",
        "gemini_api_key": "GEMINI_API_KEY",
        "anthropic_api_key": "ANTHROPIC_API_KEY",
        "ollama_api_key": "OLLAMA_API_KEY",
    }

    for secret_key, env_var in env_map.items():
        if secret_key in secrets and secrets[secret_key] and env_var not in os.environ:
            os.environ[env_var] = secrets[secret_key]


def _build_config(provider: str | None, model: str | None):
    """Load AppConfig, optionally overriding provider/model."""
    from clawed.models import AppConfig, LLMProvider

    # Ensure API keys are available
    _inject_api_keys()

    config = AppConfig.load()

    if provider:
        try:
            config.provider = LLMProvider(provider)
        except ValueError:
            raise ValueError(f"Unknown provider: {provider}")

    if model:
        # Set the right model field based on provider
        if config.provider == LLMProvider.OPENAI:
            config.openai_model = model
        elif config.provider == LLMProvider.GOOGLE:
            config.google_model = model
        elif config.provider == LLMProvider.OLLAMA:
            config.ollama_model = model
        elif config.provider == LLMProvider.ANTHROPIC:
            config.anthropic_model = model

    return config


async def _handle_chat(request: dict[str, Any]) -> dict[str, Any]:
    """Process a single chat request and return a response dict."""
    from clawed.llm import LLMClient

    provider = request.get("provider")
    model = request.get("model")
    messages = request.get("messages", [])
    system = request.get("system", "")
    max_tokens = request.get("max_tokens", 4096)
    temperature = request.get("temperature", 0.7)

    try:
        config = _build_config(provider, model)
    except ValueError as exc:
        return {
            "status": "error",
            "content": "",
            "model": model or "",
            "usage": {"input_tokens": 0, "output_tokens": 0},
            "error": str(exc),
        }

    # Build the prompt from messages array
    # For simple chat: take the last user message as prompt
    prompt_parts: list[str] = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if isinstance(content, list):
            # Handle structured content blocks
            text_parts = [
                b.get("text", "") for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            ]
            content = "\n".join(text_parts)
        if role == "user":
            prompt_parts.append(content)
        elif role == "assistant":
            prompt_parts.append(f"[Previous assistant response: {content[:200]}...]")

    prompt = "\n\n".join(prompt_parts) if prompt_parts else ""

    try:
        client = LLMClient(config=config)
        response_text = await client.generate(
            prompt=prompt,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Determine actual model used
        used_model = model
        if not used_model:
            if config.provider.value == "openai":
                used_model = config.openai_model
            elif config.provider.value == "google":
                used_model = config.google_model
            elif config.provider.value == "ollama":
                used_model = config.ollama_model
            elif config.provider.value == "anthropic":
                used_model = config.anthropic_model

        return {
            "status": "success",
            "content": response_text,
            "model": used_model or "",
            "usage": {
                "input_tokens": len(prompt.split()),  # rough estimate
                "output_tokens": len(response_text.split()),
            },
            "error": None,
        }

    except Exception as exc:
        logger.exception("Bridge chat error")
        return {
            "status": "error",
            "content": "",
            "model": model or "",
            "usage": {"input_tokens": 0, "output_tokens": 0},
            "error": f"{type(exc).__name__}: {exc}",
        }


def _run_chat_stdin() -> None:
    """Read request from stdin, process, write response to stdout."""
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            _write_error("Empty input on stdin")
            return

        request = json.loads(raw)
    except json.JSONDecodeError as exc:
        _write_error(f"Invalid JSON on stdin: {exc}")
        return

    result = asyncio.run(_handle_chat(request))
    sys.stdout.write(json.dumps(result))
    sys.stdout.flush()


def _run_chat_args(provider: str, model: str) -> None:
    """Interactive single-shot chat from CLI args (for testing)."""
    print(f"Bridge ready: provider={provider}, model={model}", file=sys.stderr)
    print("Enter message (Ctrl+D to send):", file=sys.stderr)
    prompt = sys.stdin.read().strip()
    if not prompt:
        _write_error("No prompt provided")
        return

    request = {
        "messages": [{"role": "user", "content": prompt}],
        "provider": provider,
        "model": model,
    }
    result = asyncio.run(_handle_chat(request))
    sys.stdout.write(json.dumps(result))
    sys.stdout.flush()


def _write_error(msg: str) -> None:
    result = {
        "status": "error",
        "content": "",
        "model": "",
        "usage": {"input_tokens": 0, "output_tokens": 0},
        "error": msg,
    }
    sys.stdout.write(json.dumps(result))
    sys.stdout.flush()


def main() -> None:
    """Entry point for `python -m clawed.bridge`."""
    parser = argparse.ArgumentParser(description="Claw-ED Python LLM bridge")
    sub = parser.add_subparsers(dest="command")

    chat_parser = sub.add_parser("chat", help="Process a chat request")
    chat_parser.add_argument("--provider", default=None, help="LLM provider")
    chat_parser.add_argument("--model", default=None, help="Model name")
    chat_parser.add_argument(
        "--stdin", action="store_true", default=True,
        help="Read full JSON request from stdin (default)",
    )

    args = parser.parse_args()

    if args.command == "chat":
        if args.stdin and args.provider is None:
            _run_chat_stdin()
        elif args.provider:
            _run_chat_args(args.provider, args.model or "")
        else:
            _run_chat_stdin()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
