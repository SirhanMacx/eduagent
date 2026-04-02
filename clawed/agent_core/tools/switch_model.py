"""Tool: switch_model — change the AI model or list available models."""
from __future__ import annotations

from typing import Any

from clawed.agent_core.context import AgentContext, ToolResult


class SwitchModelTool:
    """Switch the AI model or list available models."""

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "switch_model",
                "description": "Switch the AI model or list available models. "
                    "Use action='list' to show available models, "
                    "action='switch' with model_name to change.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["list", "switch", "current"],
                            "description": "list=show models, switch=change model, current=show active",
                        },
                        "model_name": {
                            "type": "string",
                            "description": "Model to switch to (for action=switch)",
                        },
                    },
                    "required": ["action"],
                },
            },
        }

    async def execute(self, params: dict[str, Any], context: AgentContext) -> ToolResult:
        action = params.get("action", "current")
        config = context.config

        if action == "current":
            provider = config.provider.value
            if provider == "ollama":
                model = config.ollama_model
            elif provider == "anthropic":
                model = config.anthropic_model
            else:
                model = config.openai_model
            return ToolResult(
                text=f"Current model: {model} (provider: {provider})",
                data={"model": model, "provider": provider},
            )

        if action == "list":
            models = []
            if config.provider.value == "ollama":
                try:
                    import httpx
                    base = config.ollama_base_url.rstrip("/")
                    headers = {}
                    if config.ollama_api_key:
                        headers["Authorization"] = f"Bearer {config.ollama_api_key}"
                    # Try cloud endpoint first
                    from clawed.config import is_ollama_cloud
                    if is_ollama_cloud(base):
                        resp = httpx.get(
                            f"{base}/api/tags",
                            headers=headers,
                            timeout=10.0,
                            follow_redirects=True,
                        )
                    else:
                        resp = httpx.get(f"{base}/api/tags", timeout=5.0)
                    if resp.status_code == 200:
                        models = [m["name"] for m in resp.json().get("models", [])]
                except Exception as e:
                    return ToolResult(text=f"Could not list models: {e}")

            if models:
                current = config.ollama_model
                lines = ["Available models:"]
                for m in models:
                    marker = " (active)" if m == current else ""
                    lines.append(f"  - {m}{marker}")
                return ToolResult(text="\n".join(lines), data={"models": models})
            return ToolResult(text="No models found or provider doesn't support listing.")

        if action == "switch":
            model_name = params.get("model_name", "")
            if not model_name:
                return ToolResult(text="Please specify a model name.")

            from clawed.models import AppConfig
            cfg = AppConfig.load()
            if cfg.provider.value == "ollama":
                cfg.ollama_model = model_name
            elif cfg.provider.value == "anthropic":
                cfg.anthropic_model = model_name
            elif cfg.provider.value == "openai":
                cfg.openai_model = model_name
            cfg.save()

            return ToolResult(
                text=f"Switched to {model_name}. New generations will use this model.",
                side_effects=[f"Model switched to {model_name}"],
            )

        return ToolResult(text=f"Unknown action: {action}")
