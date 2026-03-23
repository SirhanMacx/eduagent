"""Unified LLM client supporting Anthropic, OpenAI, and Ollama backends."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

import httpx

from eduagent.models import AppConfig, LLMProvider


class LLMClient:
    """Unified async LLM client for all supported backends."""

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or AppConfig.load()

    async def generate(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Generate text from the configured LLM backend."""
        if self.config.provider == LLMProvider.ANTHROPIC:
            return await self._anthropic(prompt, system, temperature, max_tokens)
        elif self.config.provider == LLMProvider.OPENAI:
            return await self._openai(prompt, system, temperature, max_tokens)
        elif self.config.provider == LLMProvider.OLLAMA:
            return await self._ollama(prompt, system, temperature, max_tokens)
        raise ValueError(f"Unknown provider: {self.config.provider}")

    async def generate_json(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.4,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Generate and parse a JSON response from the LLM."""
        raw = await self.generate(prompt, system, temperature, max_tokens)
        # Extract JSON from markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Drop first line (```json or ```) and last line (```)
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)
        return json.loads(cleaned)

    # ── Anthropic ────────────────────────────────────────────────────────

    async def _anthropic(
        self, prompt: str, system: str, temperature: float, max_tokens: int
    ) -> str:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY not set. Export it or run: eduagent config set-model ollama"
            )
        async with httpx.AsyncClient(timeout=120.0) as client:
            body: dict[str, Any] = {
                "model": self.config.anthropic_model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system:
                body["system"] = system
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"]

    # ── OpenAI ───────────────────────────────────────────────────────────

    async def _openai(
        self, prompt: str, system: str, temperature: float, max_tokens: int
    ) -> str:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "OPENAI_API_KEY not set. Export it or run: eduagent config set-model ollama"
            )
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-type": "application/json",
                },
                json={
                    "model": self.config.openai_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    # ── Ollama ───────────────────────────────────────────────────────────

    async def _ollama(
        self, prompt: str, system: str, temperature: float, max_tokens: int
    ) -> str:
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(
                f"{self.config.ollama_base_url}/api/generate",
                json={
                    "model": self.config.ollama_model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["response"]
