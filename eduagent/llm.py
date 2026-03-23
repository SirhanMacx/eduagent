"""Unified LLM client supporting Anthropic, OpenAI, and Ollama backends."""

from __future__ import annotations

import json
import os
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
        """Generate text from the configured LLM backend.

        In demo mode (no API key configured), returns a canned sample lesson
        so teachers can try EDUagent without any LLM credentials.
        """
        from eduagent.demo import is_demo_mode

        if is_demo_mode():
            return self._demo_response(prompt)

        if self.config.provider == LLMProvider.ANTHROPIC:
            return await self._anthropic(prompt, system, temperature, max_tokens)
        elif self.config.provider == LLMProvider.OPENAI:
            return await self._openai(prompt, system, temperature, max_tokens)
        elif self.config.provider == LLMProvider.OLLAMA:
            return await self._ollama(prompt, system, temperature, max_tokens)
        raise ValueError(f"Unknown provider: {self.config.provider}")

    @staticmethod
    def _demo_response(prompt: str) -> str:
        """Return a canned demo response based on prompt keywords."""
        from eduagent.demo import load_demo

        prompt_lower = prompt.lower()
        if "assessment" in prompt_lower or "dbq" in prompt_lower:
            data = load_demo("assessment")
        elif "unit" in prompt_lower:
            data = load_demo("unit_plan")
        elif "science" in prompt_lower:
            data = load_demo("lesson_science_g6")
        else:
            data = load_demo("lesson_social_studies_g8")
        return json.dumps(data, indent=2)

    async def generate_json(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.4,
        max_tokens: int = 8192,
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
        # Step 1: try strict JSON parsing
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Step 2: fall back to json_repair for truncated/malformed JSON
        import json_repair

        try:
            result = json_repair.loads(cleaned)
            if isinstance(result, (dict, list)):
                return result
        except Exception:
            pass

        # Step 3: raise a clear error with raw LLM output for debugging
        preview = raw[:500] + ("..." if len(raw) > 500 else "")
        raise ValueError(
            f"LLM returned unparseable JSON. Raw output:\n{preview}"
        )

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
        # Support both local Ollama (no auth) and Ollama Cloud (Bearer token)
        api_key = getattr(self.config, "ollama_api_key", None) or os.environ.get("OLLAMA_API_KEY")
        headers = {}
        if api_key and api_key != "ollama":
            headers["Authorization"] = f"Bearer {api_key}"

        # Ollama Cloud uses OpenAI-compatible API; local uses /api/generate
        base = self.config.ollama_base_url.rstrip("/")
        is_cloud = "api.ollama.com" in base or "ollama.com" in base

        if is_cloud:
            # Use OpenAI-compatible endpoint for cloud
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            async with httpx.AsyncClient(timeout=300.0) as client:
                resp = await client.post(
                    f"{base}/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": self.config.ollama_model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "stream": False,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        else:
            # Local Ollama
            full_prompt = f"{system}\n\n{prompt}" if system else prompt
            async with httpx.AsyncClient(timeout=300.0) as client:
                resp = await client.post(
                    f"{base}/api/generate",
                    headers=headers,
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
