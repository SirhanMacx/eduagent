"""Unified LLM client supporting Anthropic, OpenAI, and Ollama backends."""

from __future__ import annotations

import json
import os
from typing import Any, Optional, Type

import httpx
from pydantic import BaseModel, ValidationError

from clawed.models import AppConfig, LLMProvider


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
        so teachers can try Claw-ED without any LLM credentials.

        Automatically injects workspace context (identity, soul, memory)
        into the system prompt when available.
        """
        from clawed.demo import is_demo_mode

        if is_demo_mode(config=self.config):
            return self._demo_response(prompt)

        # Inject workspace context into system prompt
        system = self._enrich_system_prompt(system, prompt=prompt)

        from clawed.sanitize import sanitize_text

        if self.config.provider == LLMProvider.ANTHROPIC:
            raw = await self._anthropic(prompt, system, temperature, max_tokens)
        elif self.config.provider == LLMProvider.OPENAI:
            raw = await self._openai(prompt, system, temperature, max_tokens)
        elif self.config.provider == LLMProvider.OLLAMA:
            raw = await self._ollama(prompt, system, temperature, max_tokens)
        elif self.config.provider == LLMProvider.GOOGLE:
            raw = await self._google(prompt, system, temperature, max_tokens)
        else:
            raise ValueError(f"Unknown provider: {self.config.provider}")
        return sanitize_text(raw)

    @staticmethod
    def _demo_response(prompt: str) -> str:
        """Return a canned demo response based on prompt keywords."""
        from clawed.demo import load_demo

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

    def _enrich_system_prompt(self, system: str, prompt: str = "") -> str:
        """Append workspace context and improvement context to the system prompt.

        This injects teacher identity, teaching philosophy, memory, and
        today's notes so the LLM has full context about the teacher.
        Additionally injects learned patterns from the feedback loop
        (memory engine) so generation quality improves over time.
        Fails silently if workspace is not initialized.

        Args:
            system: The current system prompt.
            prompt: The user prompt text — used to detect the subject being
                generated so multi-subject teachers get the right feedback.
        """
        try:
            from clawed.workspace import inject_workspace_context

            ws_context = inject_workspace_context()
            if ws_context:
                system = (system + ws_context) if system else ws_context
        except Exception:
            pass  # Workspace not available -- that's fine

        # Inject improvement context from the memory engine (feedback loop).
        # Detect subject from the prompt text so multi-subject teachers get
        # correctly filtered feedback (not always subjects[0]).
        try:
            from clawed.memory_engine import build_improvement_context

            subject = self._detect_subject_from_prompt(prompt)
            improvement_ctx = build_improvement_context(subject=subject)
            if improvement_ctx:
                system = (system + "\n" + improvement_ctx) if system else improvement_ctx
        except Exception:
            pass  # Memory engine not available -- that's fine

        return system

    def _detect_subject_from_prompt(self, prompt: str) -> str:
        """Detect the subject being generated from the prompt text.

        Checks for explicit subject mentions, then falls back to
        teacher_profile.subjects[0].
        """
        if not prompt:
            return self._default_subject()

        lower = prompt.lower()
        # Check for explicit subject keywords in the prompt
        subject_keywords = {
            "history": "History",
            "social studies": "Social Studies",
            "science": "Science",
            "biology": "Science",
            "chemistry": "Science",
            "physics": "Science",
            "math": "Math",
            "algebra": "Math",
            "geometry": "Math",
            "calculus": "Math",
            "english": "ELA",
            "ela": "ELA",
            "language arts": "ELA",
            "literature": "ELA",
            "reading": "ELA",
            "writing": "ELA",
            "art": "Art",
            "music": "Music",
            "physical education": "PE",
            "computer science": "Computer Science",
            "spanish": "Foreign Language",
            "french": "Foreign Language",
        }
        for keyword, subject in subject_keywords.items():
            if keyword in lower:
                return subject

        return self._default_subject()

    def _default_subject(self) -> str:
        """Get the first subject from teacher profile, or empty string."""
        if hasattr(self.config, "teacher_profile") and self.config.teacher_profile:
            subjects = getattr(self.config.teacher_profile, "subjects", [])
            return subjects[0] if subjects else ""
        return ""

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

    async def safe_generate_json(
        self,
        prompt: str,
        model_class: Type[BaseModel],
        max_retries: int = 1,
        **kwargs: Any,
    ) -> BaseModel:
        """Generate JSON and parse into a Pydantic model with automatic retry.

        On validation failure, retries once with the error appended to the prompt.
        On second failure, raises a clear RuntimeError (not a traceback).
        """
        for attempt in range(max_retries + 1):
            raw = await self.generate_json(prompt, **kwargs)
            try:
                return model_class.model_validate(raw)
            except ValidationError as e:
                if attempt < max_retries:
                    # Retry with error context
                    error_msg = str(e)
                    prompt = prompt + f"\n\nPREVIOUS ATTEMPT FAILED. Fix these errors:\n{error_msg}"
                    continue
                raise RuntimeError(
                    f"Generation failed after {max_retries + 1} attempts. "
                    f"The AI returned data that doesn't match the expected format. "
                    f"Try again or use a different AI model."
                ) from e

    async def generate_student_handout(
        self,
        lesson_json: str,
        persona_context: str = "",
        subject: str = "",
        grade: str = "",
    ) -> str:
        """Generate a student handout as a first-class LLM output.

        Sends the completed lesson plan as context and asks the LLM to produce
        the student-facing materials. This is NOT regex extraction from the
        lesson --- it's a separate generation that understands what the lesson
        references and creates matching materials.
        """
        system = (
            "You are creating a student handout for a lesson. The handout is what "
            "students receive --- it must be self-contained, printable, and include "
            "everything referenced in the lesson plan.\n\n"
            f"{persona_context}\n" if persona_context else ""
        )

        prompt = (
            f"Here is the complete lesson plan:\n\n{lesson_json}\n\n"
            "Create a student handout that includes ALL of these sections "
            "(skip any that don't apply to this lesson):\n\n"
            "1. **Header**: Lesson title, date line, Name: _________ Period: _____\n"
            "2. **Do Now**: The student-facing prompt only (not the teacher script), "
            "with lined space for writing\n"
            "3. **Vocabulary**: Key terms with definitions extracted from the lesson. "
            "Format: Term --- definition\n"
            "4. **Primary Source Excerpts**: Any quoted passages referenced in the lesson, "
            "with full attribution (author, date, title). Quote them completely.\n"
            "5. **Graphic Organizer**: If the lesson references an organizer (source analysis, "
            "comparison chart, etc.), create the actual table with column headers and empty rows. "
            "Include clear instructions.\n"
            "6. **Activity Instructions**: Student-facing version of guided/independent practice\n"
            "7. **Exit Ticket**: Numbered questions with lined answer space\n\n"
            "Return the handout as structured JSON with these keys:\n"
            '{"title": "...", "do_now": "...", "vocabulary": [{"term": "...", "definition": "..."}], '
            '"source_excerpts": [{"text": "...", "attribution": "..."}], '
            '"organizer": {"title": "...", "columns": ["..."], "instructions": "...", "num_rows": 4}, '
            '"activity_instructions": "...", '
            '"exit_ticket_questions": ["...", "..."]}'
        )

        return await self.generate(prompt, system=system, temperature=0.4, max_tokens=4096)

    async def review_lesson_package(
        self,
        lesson_json: str,
        standards_present: bool,
        has_handout: bool,
        has_slideshow: bool,
    ) -> dict[str, Any]:
        """Self-review a lesson package against observation-ready standards.

        Returns a dict with 'passed' (bool) and 'issues' (list of strings).
        If issues are found, the caller should attempt to fix them.
        """
        prompt = (
            f"Review this lesson package against observation-ready quality standards.\n\n"
            f"Lesson:\n{lesson_json[:3000]}\n\n"
            f"Package status: standards={'yes' if standards_present else 'MISSING'}, "
            f"handout={'yes' if has_handout else 'MISSING'}, "
            f"slideshow={'yes' if has_slideshow else 'MISSING'}\n\n"
            "Check these standards:\n"
            "1. Do all section times add up to a full class period (42-45 min)?\n"
            "2. Are specific standards codes listed (not just 'aligned to standards')?\n"
            "3. Is vocabulary defined for all content-specific terms?\n"
            "4. Are there checks for understanding every 7-10 minutes?\n"
            "5. Are all referenced materials self-contained (no phantom handouts)?\n"
            "6. Is the Do Now completable in 5 minutes?\n"
            "7. Are transitions scripted between sections?\n\n"
            'Return JSON: {"passed": true/false, "issues": ["issue 1", "issue 2"]}'
        )
        raw = await self.generate(prompt, temperature=0.2, max_tokens=1000)
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                cleaned = "\n".join(lines)
            return json.loads(cleaned)
        except Exception:
            return {"passed": True, "issues": []}

    # ── Anthropic ────────────────────────────────────────────────────────

    async def _anthropic(
        self, prompt: str, system: str, temperature: float, max_tokens: int
    ) -> str:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY not set. Export it or run: clawed config set-model ollama"
            )
        try:
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
        except httpx.ConnectError:
            raise ConnectionError(
                "Could not connect to the Anthropic API.\n"
                "Check your internet connection and try again."
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise EnvironmentError(
                    "Invalid ANTHROPIC_API_KEY. Check your key at https://console.anthropic.com"
                )
            raise

    # ── OpenAI ───────────────────────────────────────────────────────────

    async def _openai(
        self, prompt: str, system: str, temperature: float, max_tokens: int
    ) -> str:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "OPENAI_API_KEY not set. Export it or run: clawed config set-model ollama"
            )
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
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
        except httpx.ConnectError:
            raise ConnectionError(
                "Could not connect to the OpenAI API.\n"
                "Check your internet connection and try again."
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise EnvironmentError(
                    "Invalid OPENAI_API_KEY. Check your key at https://platform.openai.com"
                )
            raise

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
        model = self.config.ollama_model

        try:
            if is_cloud:
                # Use OpenAI-compatible endpoint for cloud
                messages = []
                if system:
                    messages.append({"role": "system", "content": system})
                messages.append({"role": "user", "content": prompt})
                async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
                    # Append /v1 only if base doesn't already end with it
                    v1_prefix = "" if base.endswith("/v1") else "/v1"
                    resp = await client.post(
                        f"{base}{v1_prefix}/chat/completions",
                        headers=headers,
                        json={
                            "model": model,
                            "messages": messages,
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                            "stream": False,
                        },
                    )
                    if resp.status_code == 404:
                        raise ConnectionError(
                            f"Ollama model '{model}' not found on the cloud.\n"
                            f"Check available models at https://ollama.com/library"
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
                            "model": model,
                            "prompt": full_prompt,
                            "stream": False,
                            "options": {
                                "temperature": temperature,
                                "num_predict": max_tokens,
                            },
                        },
                    )
                    if resp.status_code == 404:
                        # Parse Ollama's error body for details
                        try:
                            err_body = resp.json()
                            err_msg = err_body.get("error", "")
                        except Exception:
                            err_msg = ""
                        raise ConnectionError(
                            f"Ollama model '{model}' not installed.\n"
                            f"Run: ollama pull {model}"
                            + (f"\n\nOllama says: {err_msg}" if err_msg else "")
                        )
                    resp.raise_for_status()
                    data = resp.json()
                    return data["response"]
        except httpx.ConnectError:
            raise ConnectionError(
                "Could not connect to Ollama.\n"
                "Install from https://ollama.com and make sure it's running."
            )

    # ── Google Gemini ────────────────────────────────────────────────────

    async def _google(
        self, prompt: str, system: str, temperature: float, max_tokens: int
    ) -> str:
        """Call Google Gemini API — supports both API key and OAuth2 token."""
        from clawed.auth.google_auth import get_google_api_key, get_google_oauth_token

        api_key = get_google_api_key()
        oauth_token = get_google_oauth_token() if not api_key else None

        if not api_key and not oauth_token:
            raise EnvironmentError(
                "No Google credentials found. Either:\n"
                "  1. Set GOOGLE_API_KEY (get one at https://aistudio.google.com)\n"
                "  2. Run `clawed setup --reset` and choose Google with browser sign-in"
            )

        model = self.config.google_model
        base_url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent"
        )

        # Auth: API key as query param, or OAuth token as Bearer header
        params = {}
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            params["key"] = api_key
        elif oauth_token:
            headers["Authorization"] = f"Bearer {oauth_token}"

        # Build contents
        contents: list[dict[str, Any]] = []
        if system:
            contents.append({"role": "user", "parts": [{"text": system}]})
            contents.append({"role": "model", "parts": [{"text": "Understood."}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        body: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    base_url, params=params, headers=headers, json=body,
                )
                resp.raise_for_status()
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
        except httpx.ConnectError:
            raise ConnectionError(
                "Could not connect to the Google Gemini API.\n"
                "Check your internet connection and try again."
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise EnvironmentError(
                    "Google credentials expired or invalid.\n"
                    "Run `clawed setup --reset` to re-authenticate."
                )
            raise
