"""Dynamic model discovery for all providers.

Lists available models from Ollama Cloud, OpenRouter, and other
providers via their APIs. Used by the /models command and the
switch_model agent tool.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def list_ollama_models(
    base_url: str = "http://localhost:11434",
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    """List available Ollama models (local or cloud).

    Returns: [{"name": "gemma4:31b-cloud", "size": ..., "family": ...}]
    """
    import requests

    base = base_url.rstrip("/")
    headers = {}
    if api_key and api_key not in ("ollama-local", "ollama", "local"):
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        resp = requests.get(
            f"{base}/api/tags", headers=headers, timeout=10,
        )
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            return [
                {
                    "name": m.get("name", ""),
                    "size": m.get("size", 0),
                    "family": m.get("details", {}).get("family", ""),
                    "parameter_size": m.get("details", {}).get(
                        "parameter_size", ""
                    ),
                }
                for m in models
                if m.get("name")
            ]
    except Exception as e:
        logger.debug("Ollama model listing failed: %s", e)

    return []


def list_openrouter_models(
    api_key: str | None = None,
    free_only: bool = False,
) -> list[dict[str, Any]]:
    """List available OpenRouter models.

    The /models endpoint is public (no auth needed for listing).
    Set free_only=True to filter for models with zero cost.
    """
    import requests

    try:
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        resp = requests.get(
            "https://openrouter.ai/api/v1/models",
            headers=headers, timeout=15,
        )
        if resp.status_code != 200:
            return []

        models = resp.json().get("data", [])
        result = []
        for m in models:
            pricing = m.get("pricing", {})
            prompt_cost = pricing.get("prompt", "0")
            completion_cost = pricing.get("completion", "0")
            is_free = str(prompt_cost) == "0" and str(completion_cost) == "0"

            if free_only and not is_free:
                continue

            result.append({
                "id": m.get("id", ""),
                "name": m.get("name", m.get("id", "")),
                "context_length": m.get("context_length", 0),
                "free": is_free,
                "prompt_cost": prompt_cost,
                "completion_cost": completion_cost,
            })

        return result

    except Exception as e:
        logger.debug("OpenRouter model listing failed: %s", e)
        return []


# Known models for providers without listing APIs
ANTHROPIC_MODELS = [
    {"name": "claude-sonnet-4-6", "tier": "work"},
    {"name": "claude-opus-4-6", "tier": "deep"},
    {"name": "claude-haiku-3.5", "tier": "fast"},
]

OPENAI_MODELS = [
    {"name": "gpt-4.1", "tier": "deep"},
    {"name": "gpt-4.1-mini", "tier": "fast"},
    {"name": "gpt-4.1-nano", "tier": "fast"},
    {"name": "o3", "tier": "deep"},
    {"name": "o4-mini", "tier": "work"},
]

GOOGLE_MODELS = [
    {"name": "gemini-2.5-flash", "tier": "fast"},
    {"name": "gemini-2.5-pro", "tier": "deep"},
]


def list_all_models(config: Any = None) -> dict[str, list[dict]]:
    """List models from all configured providers.

    Returns: {"ollama": [...], "openrouter": [...], "anthropic": [...], ...}
    """
    from clawed.config import get_api_key

    result: dict[str, list[dict]] = {}

    # Ollama (dynamic discovery)
    if config:
        ollama_key = get_api_key("ollama")
        base = getattr(config, "ollama_base_url", "http://localhost:11434")
        models = list_ollama_models(base, ollama_key)
        if models:
            result["ollama"] = models

    # OpenRouter (dynamic discovery)
    or_key = get_api_key("openrouter")
    or_models = list_openrouter_models(or_key, free_only=(not or_key))
    if or_models:
        result["openrouter"] = or_models[:30]  # Cap at 30

    # Static lists for API-key providers
    if get_api_key("anthropic"):
        result["anthropic"] = ANTHROPIC_MODELS
    if get_api_key("openai"):
        result["openai"] = OPENAI_MODELS
    if get_api_key("google"):
        result["google"] = GOOGLE_MODELS

    # Always show Ollama cloud models even without key
    # (free tier may be available)
    if "ollama" not in result:
        result["ollama"] = [
            {"name": "gemma4:31b-cloud", "tier": "deep"},
            {"name": "qwen3.5:cloud", "tier": "fast"},
            {"name": "llama4-scout:cloud", "tier": "work"},
            {"name": "minimax-m2.7:cloud", "tier": "work"},
        ]

    return result
