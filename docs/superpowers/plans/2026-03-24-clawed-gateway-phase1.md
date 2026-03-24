# Claw-ED Phase 1: Gateway Extraction — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract all business logic from `tg.py` (1816 lines) into a transport-agnostic `Gateway` class, then slim `tg.py` to ~150 lines that just shuttles messages to/from the gateway. All existing tests keep passing. No rename yet — everything stays in `eduagent/`.

**Architecture:** The gateway receives `(text, teacher_id, files?)` from any transport and returns a `GatewayResponse` dataclass. The Telegram transport renders that response (text, files, buttons, typing indicators). Intent detection, onboarding, export, scheduling, ratings, gaps — all move to gateway handlers. The existing `openclaw_plugin.py` already handles most intent dispatch; the gateway wraps it and adds the transport-agnostic response layer that tg.py currently owns (keyboards, progress UX, file handling, onboarding state machine).

**Tech Stack:** Python 3.10+, httpx, Pydantic 2, pytest, pytest-asyncio

---

## File Structure

### New Files
- `eduagent/gateway_response.py` — `GatewayResponse`, `Button` dataclasses + response builders
- `eduagent/handlers/__init__.py` — Handler registry
- `eduagent/handlers/generate.py` — Lesson/unit generation with progress
- `eduagent/handlers/export.py` — Multi-format export (PPTX, DOCX, handout, PDF)
- `eduagent/handlers/feedback.py` — Rating + memory engine integration
- `eduagent/handlers/schedule.py` — Schedule management (enable/disable/parse)
- `eduagent/handlers/gaps.py` — Curriculum gap analysis
- `eduagent/handlers/onboard.py` — Multi-step onboarding state machine
- `eduagent/handlers/standards.py` — Standards lookup
- `eduagent/handlers/ingest.py` — File/path ingestion
- `eduagent/handlers/misc.py` — Demo, persona, settings, progress, model switch (small handlers)
- `tests/test_gateway_response.py` — Tests for GatewayResponse
- `tests/test_handlers.py` — Tests for all handlers
- `tests/test_tg_slim.py` — Tests for the slimmed transport
- `tests/test_gateway_brain.py` — Tests for the rewritten gateway

### Modified Files
- `eduagent/gateway.py` — Rewrite: becomes the brain, delegates to handlers, manages sessions + onboarding state
- `eduagent/router.py` — Add missing intents (DEMO, GAP_ANALYSIS, SWITCH_MODEL, SCHEDULE) + keyword patterns to match tg.py's `_detect_intent`
- `eduagent/tg.py` — Slim to ~200 lines: TelegramAPI + render loop, delegates everything to gateway
- `eduagent/openclaw_plugin.py` — Minor: handlers call its existing functions rather than duplicating

### Unchanged Files
- `eduagent/models.py`, `eduagent/router.py`, `eduagent/model_router.py`
- `eduagent/llm.py`, `eduagent/memory_engine.py`, `eduagent/workspace.py`
- `eduagent/lesson.py`, `eduagent/doc_export.py`, `eduagent/persona.py`
- `eduagent/state.py`, `eduagent/bot_state.py`, `eduagent/scheduler.py`
- `eduagent/standards.py`, `eduagent/curriculum_map.py`, `eduagent/analytics.py`
- All prompt templates, skills, demo data

---

## Task 1: GatewayResponse Dataclass

**Files:**
- Create: `eduagent/gateway_response.py`
- Create: `tests/test_gateway_response.py`

This is the transport-agnostic response that every handler returns. Transports render it however they want (Telegram: send_message + send_document + reply_markup; Web: JSON; CLI: print).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_gateway_response.py
"""Tests for GatewayResponse — the transport-agnostic response type."""
from pathlib import Path

from eduagent.gateway_response import Button, GatewayResponse


class TestGatewayResponse:
    def test_text_only_response(self):
        r = GatewayResponse(text="Hello teacher")
        assert r.text == "Hello teacher"
        assert r.files == []
        assert r.buttons == []
        assert r.typing is False
        assert r.progress == ""

    def test_response_with_files(self):
        r = GatewayResponse(text="Here's your lesson", files=[Path("/tmp/lesson.pptx")])
        assert len(r.files) == 1
        assert r.files[0].name == "lesson.pptx"

    def test_response_with_buttons(self):
        b = Button(label="Rate 5★", callback_data="rate:abc:5")
        r = GatewayResponse(text="Rate this lesson?", buttons=[b])
        assert r.buttons[0].label == "Rate 5★"
        assert r.buttons[0].callback_data == "rate:abc:5"

    def test_button_defaults(self):
        b = Button(label="Click me", callback_data="action:do_thing")
        assert b.url is None

    def test_progress_response(self):
        r = GatewayResponse(text="", typing=True, progress="Generating lesson...")
        assert r.typing is True
        assert r.progress == "Generating lesson..."

    def test_empty_response(self):
        r = GatewayResponse.empty()
        assert r.text == ""
        assert r.files == []

    def test_response_has_content(self):
        assert GatewayResponse(text="hi").has_content is True
        assert GatewayResponse(text="").has_content is False
        assert GatewayResponse(text="", files=[Path("/tmp/x.pdf")]).has_content is True

    def test_button_rows(self):
        """Buttons can be grouped into rows for keyboard layout."""
        row1 = [Button(label="Slides", callback_data="export:slides"),
                Button(label="Handout", callback_data="export:handout")]
        row2 = [Button(label="Rate", callback_data="rate:prompt")]
        r = GatewayResponse(text="Done!", button_rows=[row1, row2])
        assert len(r.button_rows) == 2
        assert len(r.button_rows[0]) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/mind_uploaded_crustacean/Projects/eduagent && python -m pytest tests/test_gateway_response.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'eduagent.gateway_response'`

- [ ] **Step 3: Implement GatewayResponse**

```python
# eduagent/gateway_response.py
"""Transport-agnostic response type for the Claw-ED gateway.

Every handler returns a GatewayResponse. Transports render it:
  - Telegram: send_message + send_document + reply_markup
  - Web API: JSON serialization
  - CLI: rich.print + file paths
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Button:
    """An action button that transports render as inline keyboards, HTML buttons, etc."""

    label: str
    callback_data: str
    url: str | None = None


@dataclass
class GatewayResponse:
    """What the gateway returns to any transport."""

    text: str = ""
    files: list[Path] = field(default_factory=list)
    buttons: list[Button] = field(default_factory=list)
    button_rows: list[list[Button]] = field(default_factory=list)
    typing: bool = False
    progress: str = ""

    @property
    def has_content(self) -> bool:
        return bool(self.text or self.files)

    @classmethod
    def empty(cls) -> GatewayResponse:
        return cls()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/mind_uploaded_crustacean/Projects/eduagent && python -m pytest tests/test_gateway_response.py -v`
Expected: All 9 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/mind_uploaded_crustacean/Projects/eduagent
git add eduagent/gateway_response.py tests/test_gateway_response.py
git commit -m "feat: add GatewayResponse dataclass for transport-agnostic responses"
```

---

## Task 2: Handler Registry + Onboarding Handler

**Files:**
- Create: `eduagent/handlers/__init__.py`
- Create: `eduagent/handlers/onboard.py`
- Create: `tests/test_handlers.py`

The onboarding handler is the most complex state machine in tg.py (lines 1156-1263). It tracks multi-step conversational setup: ask_subject → ask_grade → ask_name → ask_model → done.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_handlers.py
"""Tests for gateway handlers."""
import pytest
from eduagent.gateway_response import GatewayResponse
from eduagent.handlers.onboard import OnboardHandler, OnboardState


class TestOnboardHandler:
    def setup_method(self):
        self.handler = OnboardHandler()

    @pytest.mark.asyncio
    async def test_start_onboarding_asks_subject(self):
        r = await self.handler.step("teacher_1", "hi")
        assert isinstance(r, GatewayResponse)
        assert "subject" in r.text.lower() or "teach" in r.text.lower()

    @pytest.mark.asyncio
    async def test_subject_then_asks_grade(self):
        await self.handler.step("t1", "hi")  # → ask_subject
        r = await self.handler.step("t1", "math")  # → ask_grade
        assert "grade" in r.text.lower()

    @pytest.mark.asyncio
    async def test_grade_then_asks_name(self):
        await self.handler.step("t1", "hi")
        await self.handler.step("t1", "science")
        r = await self.handler.step("t1", "8th grade")
        assert "name" in r.text.lower()

    @pytest.mark.asyncio
    async def test_full_onboarding_flow(self):
        await self.handler.step("t1", "hi")
        await self.handler.step("t1", "history")
        await self.handler.step("t1", "10")
        r = await self.handler.step("t1", "Ms. Rivera")
        # After name, onboarding completes (model selection removed — defaults to ollama)
        assert r.has_content

    @pytest.mark.asyncio
    async def test_is_onboarding(self):
        assert not self.handler.is_onboarding("t1")
        await self.handler.step("t1", "hi")
        assert self.handler.is_onboarding("t1")

    @pytest.mark.asyncio
    async def test_combined_subject_and_grade(self):
        """User says '8th grade math' in one message — should skip grade step."""
        await self.handler.step("t1", "hi")
        r = await self.handler.step("t1", "8th grade math")
        # Should jump to ask_name since both subject and grade were parsed
        assert "name" in r.text.lower()

    @pytest.mark.asyncio
    async def test_onboarding_state_cleared_after_complete(self):
        await self.handler.step("t1", "hi")
        await self.handler.step("t1", "math")
        await self.handler.step("t1", "6")
        await self.handler.step("t1", "Mr. Smith")
        assert not self.handler.is_onboarding("t1")

    def test_onboard_state_enum(self):
        assert OnboardState.ASK_SUBJECT.value == "ask_subject"
        assert OnboardState.DONE.value == "done"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/mind_uploaded_crustacean/Projects/eduagent && python -m pytest tests/test_handlers.py::TestOnboardHandler -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create handler registry**

```python
# eduagent/handlers/__init__.py
"""Gateway handlers — one per intent domain.

Each handler is a callable: async (message, session, intent) -> GatewayResponse
"""
```

- [ ] **Step 4: Implement OnboardHandler**

Extract the onboarding state machine from `tg.py` lines 1156-1263 and the parsing helpers from lines 384-427 into a transport-agnostic handler.

```python
# eduagent/handlers/onboard.py
"""Multi-step onboarding for new teachers.

State machine: ask_subject → ask_grade → ask_name → done.
Extracted from tg.py lines 1156-1263.
"""
from __future__ import annotations

import re
from enum import Enum

from eduagent.gateway_response import GatewayResponse
from eduagent.models import AppConfig, LLMProvider, TeacherProfile


class OnboardState(Enum):
    ASK_SUBJECT = "ask_subject"
    ASK_GRADE = "ask_grade"
    ASK_NAME = "ask_name"
    DONE = "done"


def _parse_grade_and_subject(text: str) -> tuple[str, str]:
    """Parse '8th grade math' into (grade, subject).

    Copied verbatim from tg.py lines 384-422 to preserve exact behavior.
    Returns (grade, subject) where either may be empty string if not found.
    """
    text = text.strip()
    grade = ""
    subject = text

    # Match patterns like "8th grade", "5th grade", "grade 8", "8th"
    grade_match = re.search(
        r'(?:(\d{1,2})(?:st|nd|rd|th)?\s*grade)|(?:grade\s*(\d{1,2}))',
        text,
        re.IGNORECASE,
    )
    if grade_match:
        grade = grade_match.group(1) or grade_match.group(2)
        # Remove the grade portion to isolate subject
        subject = text[:grade_match.start()] + text[grade_match.end():]
        subject = subject.strip().strip("-,. ")

    # Capitalize subject nicely
    if subject:
        subject = subject.strip()
        words = subject.split()
        capitalized = []
        for w in words:
            if w.upper() in ("AP", "IB", "ELA"):
                capitalized.append(w.upper())
            else:
                capitalized.append(w.capitalize())
        subject = " ".join(capitalized)

    return grade, subject


class OnboardHandler:
    """Manages conversational onboarding state per teacher."""

    def __init__(self):
        self._state: dict[str, dict] = {}

    def is_onboarding(self, teacher_id: str) -> bool:
        return teacher_id in self._state

    async def step(self, teacher_id: str, text: str) -> GatewayResponse:
        """Advance onboarding by one step. Returns response for this step."""
        if teacher_id not in self._state:
            self._state[teacher_id] = {
                "step": OnboardState.ASK_SUBJECT,
                "subject": None,
                "grade": None,
                "name": None,
            }
            return GatewayResponse(
                text=(
                    "Welcome! Let's get you set up.\n\n"
                    "What subject do you teach? "
                    "(You can say something like '8th grade math')"
                ),
            )

        state = self._state[teacher_id]
        current = state["step"]

        if current == OnboardState.ASK_SUBJECT:
            grade, subject = _parse_grade_and_subject(text)
            state["subject"] = subject if subject else text.strip().title()
            if grade:  # grade is "" if not found
                state["grade"] = grade
                state["step"] = OnboardState.ASK_NAME
                return GatewayResponse(
                    text=f"Got it — {state['subject']}, grade {grade}.\n\nWhat's your name?"
                )
            state["step"] = OnboardState.ASK_GRADE
            return GatewayResponse(
                text=f"Great — {state['subject']}!\n\nWhat grade level do you teach?"
            )

        if current == OnboardState.ASK_GRADE:
            grade_match = re.search(r"(\d{1,2})", text)
            if grade_match:
                state["grade"] = grade_match.group(1)
            elif re.search(r"(?:kindergarten|kinder|pre-?k)", text, re.IGNORECASE):
                state["grade"] = "K"
            else:
                state["grade"] = text.strip()
            state["step"] = OnboardState.ASK_NAME
            return GatewayResponse(
                text=f"Grade {state['grade']} — got it.\n\nWhat's your name?"
            )

        if current == OnboardState.ASK_NAME:
            state["name"] = text.strip()
            return self._complete_onboarding(teacher_id)

        return GatewayResponse(text="Something went wrong with setup. Try /start again.")

    def _complete_onboarding(self, teacher_id: str) -> GatewayResponse:
        """Finalize onboarding: create TeacherProfile + AppConfig, save, clean up."""
        state = self._state[teacher_id]

        profile = TeacherProfile(
            name=state["name"],
            subjects=[state["subject"]],
            grade_levels=[state["grade"]],
        )
        config = AppConfig.load()
        config.teacher_profile = profile
        config.save()

        # Initialize workspace if available
        try:
            from eduagent.workspace import init_workspace
            from eduagent.models import TeacherPersona

            persona = TeacherPersona(name=state["name"], subject_area=state["subject"])
            init_workspace(persona, config)
        except Exception:
            pass

        del self._state[teacher_id]

        return GatewayResponse(
            text=(
                f"You're all set, {state['name']}!\n\n"
                f"Subject: {state['subject']}\n"
                f"Grade: {state['grade']}\n\n"
                "Try: 'plan a unit on [topic]' or 'make a lesson on [topic]'"
            ),
        )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/mind_uploaded_crustacean/Projects/eduagent && python -m pytest tests/test_handlers.py::TestOnboardHandler -v`
Expected: All 8 tests PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/mind_uploaded_crustacean/Projects/eduagent
git add eduagent/handlers/__init__.py eduagent/handlers/onboard.py tests/test_handlers.py
git commit -m "feat: extract onboarding state machine from tg.py into handlers/onboard.py"
```

---

## Task 3: Generate Handler (Lesson + Unit with Progress)

**Files:**
- Create: `eduagent/handlers/generate.py`
- Modify: `tests/test_handlers.py` — add TestGenerateHandler

This extracts the lesson/unit generation flow from tg.py lines 1697-1766 (progress UX + LLM call) into a handler that returns GatewayResponse.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_handlers.py`:

```python
from unittest.mock import AsyncMock, patch
from eduagent.handlers.generate import GenerateHandler


class TestGenerateHandler:
    def setup_method(self):
        self.handler = GenerateHandler()

    @pytest.mark.asyncio
    async def test_generate_lesson_returns_response(self):
        with patch("eduagent.handlers.generate.handle_message", new_callable=AsyncMock) as mock_hm:
            mock_hm.return_value = "Here is your lesson on photosynthesis..."
            r = await self.handler.lesson("photosynthesis", "teacher_1")
            assert isinstance(r, GatewayResponse)
            assert "photosynthesis" in r.text.lower()
            mock_hm.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_generate_unit_returns_response(self):
        with patch("eduagent.handlers.generate.handle_message", new_callable=AsyncMock) as mock_hm:
            mock_hm.return_value = "Unit plan for WWI..."
            r = await self.handler.unit("World War I", "teacher_1")
            assert isinstance(r, GatewayResponse)
            assert r.has_content

    @pytest.mark.asyncio
    async def test_generate_with_post_gen_buttons(self):
        with patch("eduagent.handlers.generate.handle_message", new_callable=AsyncMock) as mock_hm:
            mock_hm.return_value = "Lesson content..."
            with patch("eduagent.handlers.generate.get_last_lesson_id", return_value="lesson_abc"):
                r = await self.handler.lesson("fractions", "teacher_1")
                # Should include export/rating buttons
                assert len(r.button_rows) > 0 or len(r.buttons) > 0

    @pytest.mark.asyncio
    async def test_generate_error_returns_friendly_message(self):
        with patch("eduagent.handlers.generate.handle_message", new_callable=AsyncMock) as mock_hm:
            mock_hm.side_effect = RuntimeError("LLM timeout")
            r = await self.handler.lesson("topic", "teacher_1")
            assert "issue" in r.text.lower() or "error" in r.text.lower() or "try again" in r.text.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/mind_uploaded_crustacean/Projects/eduagent && python -m pytest tests/test_handlers.py::TestGenerateHandler -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement GenerateHandler**

```python
# eduagent/handlers/generate.py
"""Lesson and unit generation handler.

Wraps openclaw_plugin.handle_message with transport-agnostic response
building (post-generation buttons, error handling).

Extracted from tg.py lines 1697-1766.
"""
from __future__ import annotations

import logging

from eduagent.gateway_response import Button, GatewayResponse
from eduagent.openclaw_plugin import get_last_lesson_id, handle_message

logger = logging.getLogger(__name__)


def _post_generation_buttons(lesson_id: str) -> list[list[Button]]:
    """Build export + rating button rows for post-generation UX."""
    export_row = [
        Button(label="Slides", callback_data=f"action:export_slides:{lesson_id}"),
        Button(label="Handout", callback_data=f"action:export_handout:{lesson_id}"),
        Button(label="Word Doc", callback_data=f"action:export_doc:{lesson_id}"),
    ]
    action_row = [
        Button(label="Rate this lesson", callback_data=f"rate:{lesson_id}:0_prompt"),
        Button(label="Worksheet", callback_data=f"action:worksheet:{lesson_id}"),
    ]
    return [export_row, action_row]


class GenerateHandler:
    """Handles lesson and unit generation requests."""

    async def lesson(self, topic: str, teacher_id: str) -> GatewayResponse:
        """Generate a lesson on the given topic."""
        try:
            response_text = await handle_message(
                f"generate a lesson on {topic}",
                teacher_id=teacher_id,
            )
        except Exception as e:
            logger.error("Lesson generation failed: %s", e)
            return GatewayResponse(
                text="I ran into an issue generating that lesson. Please try again."
            )

        # Build post-generation buttons if we have a lesson ID
        button_rows = []
        lesson_id = get_last_lesson_id(teacher_id)
        if lesson_id:
            button_rows = _post_generation_buttons(lesson_id)

        return GatewayResponse(text=response_text, button_rows=button_rows)

    async def unit(self, topic: str, teacher_id: str) -> GatewayResponse:
        """Generate a unit plan on the given topic."""
        try:
            response_text = await handle_message(
                f"plan a unit on {topic}",
                teacher_id=teacher_id,
            )
        except Exception as e:
            logger.error("Unit generation failed: %s", e)
            return GatewayResponse(
                text="I ran into an issue planning that unit. Please try again."
            )

        return GatewayResponse(text=response_text)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/mind_uploaded_crustacean/Projects/eduagent && python -m pytest tests/test_handlers.py::TestGenerateHandler -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/mind_uploaded_crustacean/Projects/eduagent
git add eduagent/handlers/generate.py tests/test_handlers.py
git commit -m "feat: extract lesson/unit generation into handlers/generate.py"
```

---

## Task 4: Export Handler

**Files:**
- Create: `eduagent/handlers/export.py`
- Modify: `tests/test_handlers.py` — add TestExportHandler

Extracts tg.py `_do_export()` (lines 1623-1693) into a handler that returns files in GatewayResponse.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_handlers.py`:

```python
from eduagent.handlers.export import ExportHandler


class TestExportHandler:
    def setup_method(self):
        self.handler = ExportHandler()

    @pytest.mark.asyncio
    async def test_export_unknown_format(self):
        r = await self.handler.export("lesson_123", "teacher_1", "unknown_format")
        assert "don't support" in r.text.lower() or "not supported" in r.text.lower() or "format" in r.text.lower()

    @pytest.mark.asyncio
    async def test_export_no_lesson_found(self):
        r = await self.handler.export("nonexistent_id", "teacher_1", "slides")
        assert "couldn't find" in r.text.lower() or "no lesson" in r.text.lower()

    @pytest.mark.asyncio
    async def test_export_slides_calls_pptx(self):
        """When a lesson is found, export_lesson_pptx is called and file returned."""
        from eduagent.models import DailyLesson
        lesson = DailyLesson(
            title="Test Lesson", lesson_number=1, objective="Test",
            do_now="Test", direct_instruction="Test",
            guided_practice="Test", independent_work="Test",
        )
        with patch("eduagent.handlers.export._load_lesson", return_value=lesson):
            with patch("eduagent.handlers.export.export_lesson_pptx") as mock_export:
                from pathlib import Path
                mock_export.return_value = Path("/tmp/test.pptx")
                r = await self.handler.export("lesson_123", "teacher_1", "slides")
                assert len(r.files) == 1
                mock_export.assert_called_once()

    def test_supported_formats(self):
        assert "slides" in ExportHandler.SUPPORTED_FORMATS
        assert "handout" in ExportHandler.SUPPORTED_FORMATS
        assert "doc" in ExportHandler.SUPPORTED_FORMATS
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/mind_uploaded_crustacean/Projects/eduagent && python -m pytest tests/test_handlers.py::TestExportHandler -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement ExportHandler**

```python
# eduagent/handlers/export.py
"""Multi-format lesson export handler.

Supports: slides (PPTX), handout, doc (DOCX), pdf.
Extracted from tg.py lines 1623-1693.
"""
from __future__ import annotations

import logging
from pathlib import Path

from eduagent.gateway_response import GatewayResponse
from eduagent.models import DailyLesson, TeacherPersona

logger = logging.getLogger(__name__)


def _load_lesson(lesson_id: str, teacher_id: str) -> DailyLesson | None:
    """Load a lesson from the database by ID."""
    try:
        from eduagent.state import _get_conn
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT lesson_json FROM generated_lessons WHERE id = ? AND teacher_id = ?",
                (lesson_id, teacher_id),
            ).fetchone()
            if row:
                import json
                return DailyLesson.model_validate_json(row["lesson_json"])
    except Exception as e:
        logger.debug("Could not load lesson %s: %s", lesson_id, e)
    return None


def _load_persona(teacher_id: str) -> TeacherPersona | None:
    """Load teacher persona from session state."""
    try:
        from eduagent.state import TeacherSession
        session = TeacherSession.load(teacher_id)
        return session.persona
    except Exception:
        return None


class ExportHandler:
    """Handles lesson export to various formats."""

    SUPPORTED_FORMATS = {"slides", "handout", "doc", "pdf"}

    async def export(
        self, lesson_id: str, teacher_id: str, fmt: str
    ) -> GatewayResponse:
        """Export a lesson in the requested format."""
        if fmt not in self.SUPPORTED_FORMATS:
            return GatewayResponse(
                text=f"Format '{fmt}' is not supported. Try: slides, handout, doc, or pdf."
            )

        lesson = _load_lesson(lesson_id, teacher_id)
        if not lesson:
            return GatewayResponse(text="I couldn't find that lesson. Generate one first!")

        persona = _load_persona(teacher_id)
        output_dir = Path.home() / ".eduagent" / "exports"
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            file_path = await self._do_export(lesson, persona, output_dir, fmt)
            caption = {
                "slides": "Here are your slides!",
                "handout": "Here's the student handout!",
                "doc": "Here's the full lesson plan document!",
                "pdf": "Here's your lesson as a PDF!",
            }.get(fmt, "Here's your export!")

            return GatewayResponse(text=caption, files=[file_path])
        except Exception as e:
            logger.error("Export failed: %s", e)
            return GatewayResponse(text=f"Export failed: {e}")

    async def _do_export(
        self,
        lesson: DailyLesson,
        persona: TeacherPersona | None,
        output_dir: Path,
        fmt: str,
    ) -> Path:
        """Run the actual export. Returns the output file path."""
        from eduagent.doc_export import (
            export_lesson_docx,
            export_lesson_pdf,
            export_lesson_pptx,
            export_student_handout,
        )

        if fmt == "slides":
            return export_lesson_pptx(lesson, persona, output_dir)
        elif fmt == "handout":
            return export_student_handout(lesson, persona, output_dir)
        elif fmt == "doc":
            return export_lesson_docx(lesson, persona, output_dir)
        elif fmt == "pdf":
            return export_lesson_pdf(lesson, persona, output_dir)
        else:
            raise ValueError(f"Unknown export format: {fmt}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/mind_uploaded_crustacean/Projects/eduagent && python -m pytest tests/test_handlers.py::TestExportHandler -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/mind_uploaded_crustacean/Projects/eduagent
git add eduagent/handlers/export.py tests/test_handlers.py
git commit -m "feat: extract export logic into handlers/export.py"
```

---

## Task 5: Feedback Handler (Ratings + Memory Loop)

**Files:**
- Create: `eduagent/handlers/feedback.py`
- Modify: `tests/test_handlers.py` — add TestFeedbackHandler

Extracts tg.py `_handle_rating()` (lines 1501-1582) into a handler.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_handlers.py`:

```python
from eduagent.handlers.feedback import FeedbackHandler


class TestFeedbackHandler:
    def setup_method(self):
        self.handler = FeedbackHandler()

    @pytest.mark.asyncio
    async def test_rate_lesson_valid(self):
        with patch("eduagent.handlers.feedback.rate_lesson") as mock_rate:
            with patch("eduagent.handlers.feedback.memory_process"):
                r = await self.handler.rate("lesson_abc", "teacher_1", 5)
                assert r.has_content
                assert "5" in r.text or "star" in r.text.lower() or "thank" in r.text.lower()
                mock_rate.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_lesson_skip(self):
        r = await self.handler.rate("lesson_abc", "teacher_1", 0)
        assert "skip" in r.text.lower() or r.text == ""

    @pytest.mark.asyncio
    async def test_rate_prompt_returns_buttons(self):
        r = self.handler.rating_prompt("lesson_abc")
        assert len(r.buttons) > 0 or len(r.button_rows) > 0

    @pytest.mark.asyncio
    async def test_feedback_summary(self):
        # Real analytics returns: overall_avg_rating, rated_lessons, streak
        with patch("eduagent.handlers.feedback.get_teacher_stats", return_value={
            "overall_avg_rating": 4.2, "rated_lessons": 10, "streak": 3,
            "total_lessons": 15, "total_units": 3, "total_feedback": 8,
            "rating_distribution": {1: 0, 2: 1, 3: 2, 4: 4, 5: 3},
        }):
            r = await self.handler.summary("teacher_1")
            assert "4.2" in r.text or "rating" in r.text.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/mind_uploaded_crustacean/Projects/eduagent && python -m pytest tests/test_handlers.py::TestFeedbackHandler -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement FeedbackHandler**

```python
# eduagent/handlers/feedback.py
"""Rating and feedback handler with memory engine integration.

Extracted from tg.py lines 1501-1582.
"""
from __future__ import annotations

import logging

from eduagent.gateway_response import Button, GatewayResponse

logger = logging.getLogger(__name__)


def _lazy_rate_lesson(user_id, lesson_id, rating):
    from eduagent.analytics import rate_lesson
    return rate_lesson(user_id, lesson_id, rating)


def _lazy_get_teacher_stats(teacher_id):
    from eduagent.analytics import get_teacher_stats
    return get_teacher_stats(teacher_id)


# Module-level aliases for patching in tests
rate_lesson = _lazy_rate_lesson
get_teacher_stats = _lazy_get_teacher_stats


def memory_process(lesson, rating, notes=None, edited_sections=None, subject=None):
    """Feed the memory engine. Imported lazily."""
    try:
        from eduagent.memory_engine import process_feedback
        return process_feedback(lesson, rating, notes, edited_sections, subject)
    except Exception as e:
        logger.debug("Memory engine skipped: %s", e)
        return []


class FeedbackHandler:
    """Handles lesson ratings and feedback summary."""

    def rating_prompt(self, lesson_id: str) -> GatewayResponse:
        """Return a response with star-rating buttons."""
        buttons = [
            Button(label=f"{'★' * i}{'☆' * (5 - i)}", callback_data=f"rate:{lesson_id}:{i}")
            for i in range(1, 6)
        ]
        buttons.append(Button(label="Skip", callback_data=f"rate:{lesson_id}:0"))
        return GatewayResponse(
            text="How was this lesson?",
            button_rows=[buttons[:3], buttons[3:]],
        )

    async def rate(
        self, lesson_id: str, teacher_id: str, rating: int
    ) -> GatewayResponse:
        """Record a rating and feed the memory engine."""
        if rating == 0:
            return GatewayResponse(text="Skipped rating.")

        try:
            rate_lesson(teacher_id, lesson_id, rating)
        except Exception as e:
            logger.error("Rating save failed: %s", e)

        # Feed memory engine (fire and forget)
        try:
            from eduagent.state import _get_conn
            with _get_conn() as conn:
                row = conn.execute(
                    "SELECT lesson_json FROM generated_lessons WHERE id = ?",
                    (lesson_id,),
                ).fetchone()
                if row:
                    from eduagent.models import DailyLesson
                    lesson = DailyLesson.model_validate_json(row["lesson_json"])
                    memory_process(lesson, rating)
        except Exception as e:
            logger.debug("Memory loop skipped: %s", e)

        stars = "★" * rating + "☆" * (5 - rating)
        return GatewayResponse(text=f"Thanks! Rated {stars} ({rating}/5)")

    async def summary(self, teacher_id: str) -> GatewayResponse:
        """Show feedback summary stats.

        Note: analytics.get_teacher_stats returns keys:
        overall_avg_rating, rated_lessons, streak, total_lessons, etc.
        """
        try:
            stats = get_teacher_stats(teacher_id)
            avg = stats.get("overall_avg_rating", 0)
            total = stats.get("rated_lessons", 0)
            streak = stats.get("streak", 0)
            return GatewayResponse(
                text=(
                    f"Your feedback summary:\n"
                    f"Average rating: {avg:.1f}/5\n"
                    f"Lessons rated: {total}\n"
                    f"Current streak: {streak}"
                ),
            )
        except Exception as e:
            logger.error("Feedback summary failed: %s", e)
            return GatewayResponse(text="No feedback data yet. Rate some lessons first!")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/mind_uploaded_crustacean/Projects/eduagent && python -m pytest tests/test_handlers.py::TestFeedbackHandler -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/mind_uploaded_crustacean/Projects/eduagent
git add eduagent/handlers/feedback.py tests/test_handlers.py
git commit -m "feat: extract feedback/rating logic into handlers/feedback.py"
```

---

## Task 6: Schedule, Gaps, Standards, and Ingest Handlers

**Files:**
- Create: `eduagent/handlers/schedule.py`
- Create: `eduagent/handlers/gaps.py`
- Create: `eduagent/handlers/standards.py`
- Create: `eduagent/handlers/ingest.py`
- Modify: `tests/test_handlers.py` — add tests for each

These are simpler handlers — mostly wrapping existing service calls.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_handlers.py`:

```python
from eduagent.handlers.schedule import ScheduleHandler
from eduagent.handlers.gaps import GapsHandler
from eduagent.handlers.standards import StandardsHandler
from eduagent.handlers.ingest import IngestHandler


class TestScheduleHandler:
    def setup_method(self):
        self.handler = ScheduleHandler()

    @pytest.mark.asyncio
    async def test_show_schedule(self):
        with patch("eduagent.handlers.schedule.load_schedule_config", return_value={
            "tasks": {"morning-prep": {"enabled": True, "cron": {"hour": "6", "minute": "0"}}}
        }):
            r = await self.handler.show("teacher_1")
            assert r.has_content
            assert "morning" in r.text.lower()

    @pytest.mark.asyncio
    async def test_disable_task(self):
        with patch("eduagent.handlers.schedule.disable_task") as mock_dis:
            r = await self.handler.disable("teacher_1", "morning-prep")
            assert r.has_content
            mock_dis.assert_called_once()


class TestGapsHandler:
    def setup_method(self):
        self.handler = GapsHandler()

    @pytest.mark.asyncio
    async def test_gaps_returns_response(self):
        with patch("eduagent.handlers.gaps.handle_message", new_callable=AsyncMock) as mock_hm:
            mock_hm.return_value = "You're missing: fractions, decimals"
            r = await self.handler.analyze("teacher_1")
            assert r.has_content


class TestStandardsHandler:
    def setup_method(self):
        self.handler = StandardsHandler()

    @pytest.mark.asyncio
    async def test_lookup_standards(self):
        # get_standards returns list[tuple[str, str, str]] = (code, description, band)
        with patch("eduagent.handlers.standards.get_standards", return_value=[
            ("CCSS.MATH.6.NS.1", "Divide fractions", "6-8")
        ]):
            r = await self.handler.lookup("math", "6")
            assert r.has_content
            assert "CCSS" in r.text or "standard" in r.text.lower()

    @pytest.mark.asyncio
    async def test_no_standards_found(self):
        with patch("eduagent.handlers.standards.get_standards", return_value=[]):
            r = await self.handler.lookup("underwater basket weaving", "99")
            assert "no standards" in r.text.lower() or "couldn't find" in r.text.lower()


class TestIngestHandler:
    def setup_method(self):
        self.handler = IngestHandler()

    @pytest.mark.asyncio
    async def test_ingest_returns_instructions_when_no_files(self):
        r = await self.handler.handle(teacher_id="teacher_1", files=[])
        assert "upload" in r.text.lower() or "drag" in r.text.lower() or "send" in r.text.lower()

    @pytest.mark.asyncio
    async def test_ingest_with_path(self):
        with patch("eduagent.handlers.ingest.ingest_path") as mock_ingest:
            mock_ingest.return_value = [{"title": "doc1", "content": "stuff"}]
            with patch("eduagent.handlers.ingest.extract_persona", new_callable=AsyncMock):
                r = await self.handler.handle(
                    teacher_id="teacher_1",
                    files=[],
                    path="/tmp/test_lessons",
                )
                assert r.has_content
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/mind_uploaded_crustacean/Projects/eduagent && python -m pytest tests/test_handlers.py -k "Schedule or Gaps or Standards or Ingest" -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement ScheduleHandler**

```python
# eduagent/handlers/schedule.py
"""Schedule management handler.

Extracted from tg.py lines 948-1026.
"""
from __future__ import annotations

import logging
import re

from eduagent.gateway_response import GatewayResponse
from eduagent.scheduler import disable_task, load_schedule_config, save_schedule_config

logger = logging.getLogger(__name__)


def _cron_to_human(cron: dict) -> str:
    """Convert cron dict to human-readable string."""
    hour = int(cron.get("hour", 0))
    minute = int(cron.get("minute", 0))
    day = cron.get("day_of_week", "")
    ampm = "AM" if hour < 12 else "PM"
    display_hour = hour if hour <= 12 else hour - 12
    if display_hour == 0:
        display_hour = 12
    time_str = f"{display_hour}:{minute:02d} {ampm}"
    if day:
        return f"{day.title()} at {time_str}"
    return f"Daily at {time_str}"


class ScheduleHandler:
    """Manages scheduled task configuration."""

    async def show(self, teacher_id: str) -> GatewayResponse:
        """Show current schedule."""
        config = load_schedule_config()
        tasks = config.get("tasks", {})
        if not tasks:
            return GatewayResponse(text="No scheduled tasks configured.")

        lines = ["Your scheduled tasks:\n"]
        for name, task in tasks.items():
            status = "enabled" if task.get("enabled") else "disabled"
            cron = task.get("cron", {})
            time_str = _cron_to_human(cron) if cron else "not set"
            lines.append(f"  {name}: {status} ({time_str})")
        return GatewayResponse(text="\n".join(lines))

    async def disable(self, teacher_id: str, task_name: str) -> GatewayResponse:
        """Disable a scheduled task."""
        try:
            disable_task(task_name)
            return GatewayResponse(text=f"Disabled '{task_name}'.")
        except Exception as e:
            return GatewayResponse(text=f"Could not disable '{task_name}': {e}")

    async def enable(
        self, teacher_id: str, task_name: str, time_str: str = ""
    ) -> GatewayResponse:
        """Enable a scheduled task, optionally setting time."""
        from eduagent.scheduler import enable_task, set_task_schedule

        enable_task(task_name)
        if time_str:
            set_task_schedule(task_name, time_str)
        return GatewayResponse(text=f"Enabled '{task_name}'.")
```

- [ ] **Step 4: Implement GapsHandler**

```python
# eduagent/handlers/gaps.py
"""Curriculum gap analysis handler.

Extracted from tg.py lines 1030-1127.
"""
from __future__ import annotations

import logging

from eduagent.gateway_response import GatewayResponse
from eduagent.openclaw_plugin import handle_message

logger = logging.getLogger(__name__)


class GapsHandler:
    """Identifies curriculum gaps based on existing lessons vs standards."""

    async def analyze(self, teacher_id: str) -> GatewayResponse:
        """Run gap analysis for the teacher."""
        try:
            response = await handle_message("curriculum gap analysis", teacher_id=teacher_id)
            return GatewayResponse(text=response)
        except Exception as e:
            logger.error("Gap analysis failed: %s", e)
            return GatewayResponse(text="Gap analysis failed. Make sure you have lessons and standards configured.")
```

- [ ] **Step 5: Implement StandardsHandler**

```python
# eduagent/handlers/standards.py
"""Standards lookup handler.

Extracted from tg.py lines 916-945.
"""
from __future__ import annotations

import logging

from eduagent.gateway_response import GatewayResponse

logger = logging.getLogger(__name__)

# Lazy import to avoid circular deps
def get_standards(subject, grade):
    from eduagent.standards import get_standards as _get_standards
    return _get_standards(subject, grade)


class StandardsHandler:
    """Looks up educational standards by subject and grade."""

    async def lookup(self, subject: str, grade: str, limit: int = 15) -> GatewayResponse:
        """Look up standards for a subject and grade level.

        Note: get_standards returns list[tuple[str, str, str]] = (code, description, grade_band).
        """
        standards = get_standards(subject, grade)
        if not standards:
            return GatewayResponse(
                text=f"No standards found for {subject} grade {grade}."
            )

        lines = [f"Standards for {subject.title()} Grade {grade}:\n"]
        for code, desc, band in standards[:limit]:
            lines.append(f"  {code}: {desc}")

        if len(standards) > limit:
            lines.append(f"\n  ...and {len(standards) - limit} more")

        return GatewayResponse(text="\n".join(lines))
```

- [ ] **Step 6: Implement IngestHandler**

```python
# eduagent/handlers/ingest.py
"""File and path ingestion handler.

Extracted from tg.py lines 1361-1481.
"""
from __future__ import annotations

import logging
from pathlib import Path

from eduagent.gateway_response import GatewayResponse

logger = logging.getLogger(__name__)

# Lazy imports for patching
def ingest_path(path, **kwargs):
    from eduagent.ingestor import ingest_path as _ingest
    return _ingest(path, **kwargs)


async def extract_persona(documents, config=None):
    from eduagent.persona import extract_persona as _extract
    return await _extract(documents, config)


class IngestHandler:
    """Handles file ingestion and persona extraction."""

    async def handle(
        self,
        teacher_id: str,
        files: list[Path] | None = None,
        path: str | None = None,
    ) -> GatewayResponse:
        """Ingest uploaded files or a local path."""
        if not files and not path:
            return GatewayResponse(
                text=(
                    "Send me your teaching files (PDF, DOCX, PPTX, TXT) "
                    "or paste a folder path and I'll learn your teaching style."
                ),
            )

        target = Path(path).expanduser().resolve() if path else None
        documents = []

        try:
            if target and target.exists():
                documents = ingest_path(str(target))
            elif files:
                for f in files:
                    documents.extend(ingest_path(str(f)))

            if not documents:
                return GatewayResponse(text="No documents found to ingest.")

            # Extract persona from documents
            try:
                from eduagent.models import AppConfig
                persona = await extract_persona(documents, AppConfig.load())
                from eduagent.persona import save_persona
                save_persona(persona, Path.home() / ".eduagent")
                style_info = f"\nLearned teaching style: {persona.teaching_style}"
                if persona.tone:
                    style_info += f", Tone: {persona.tone}"
                if persona.subject_area:
                    style_info += f", Subject: {persona.subject_area}"
            except Exception as e:
                logger.debug("Persona extraction skipped: %s", e)
                style_info = ""

            return GatewayResponse(
                text=f"Ingested {len(documents)} document(s).{style_info}"
            )
        except Exception as e:
            logger.error("Ingestion failed: %s", e)
            return GatewayResponse(text=f"Ingestion failed: {e}")
```

- [ ] **Step 7: Run all handler tests**

Run: `cd /Users/mind_uploaded_crustacean/Projects/eduagent && python -m pytest tests/test_handlers.py -v`
Expected: All tests PASS

- [ ] **Step 8: Commit**

```bash
cd /Users/mind_uploaded_crustacean/Projects/eduagent
git add eduagent/handlers/schedule.py eduagent/handlers/gaps.py eduagent/handlers/standards.py eduagent/handlers/ingest.py tests/test_handlers.py
git commit -m "feat: extract schedule, gaps, standards, ingest handlers from tg.py"
```

---

## Task 6b: Misc Handlers + Router Intent Gaps

**Files:**
- Create: `eduagent/handlers/misc.py`
- Modify: `eduagent/router.py` — add missing intents
- Modify: `tests/test_handlers.py` — add TestMiscHandlers

The reviewer identified that tg.py's `_detect_intent` handles intents (demo, model, schedule, gaps, export_slides/handout/doc) that have NO equivalent in `router.py`'s `Intent` enum. These must be added to prevent silent routing failures. Also, tg.py commands for demo, persona, settings, progress, and model switching need handlers.

- [ ] **Step 1: Add missing intents to router.py**

Add to the `Intent` enum in `eduagent/router.py` (after line 59):

```python
    # Additional intents (from tg.py _detect_intent)
    DEMO = "demo"
    GAP_ANALYSIS = "gap_analysis"
    SWITCH_MODEL = "switch_model"
    SCHEDULE = "schedule"
    SHOW_PERSONA = "show_persona"
    SHOW_SETTINGS = "show_settings"
    SHOW_PROGRESS = "show_progress"
    SHOW_FEEDBACK = "show_feedback"
    EXPORT_SLIDES = "export_slides"
    EXPORT_HANDOUT = "export_handout"
    EXPORT_DOC = "export_doc"
```

And add keyword patterns + routing in `parse_intent()` to catch the keywords that `_detect_intent` in tg.py currently handles (demo, model switch, schedule verbs, gap analysis, export format keywords). The existing patterns in router.py lines 79-219 cover most generation intents but miss these operational ones.

- [ ] **Step 2: Write the failing tests for misc handlers**

Append to `tests/test_handlers.py`:

```python
from eduagent.handlers.misc import DemoHandler, PersonaHandler, SettingsHandler, ProgressHandler


class TestMiscHandlers:
    @pytest.mark.asyncio
    async def test_demo_handler(self):
        with patch("eduagent.handlers.misc.handle_message", new_callable=AsyncMock) as mock_hm:
            mock_hm.return_value = "Here's a sample lesson..."
            handler = DemoHandler()
            r = await handler.run("teacher_1")
            assert r.has_content

    @pytest.mark.asyncio
    async def test_persona_handler(self):
        handler = PersonaHandler()
        with patch("eduagent.handlers.misc.TeacherSession") as mock_session_cls:
            mock_session = mock_session_cls.load.return_value
            mock_session.persona = None
            r = await handler.show("teacher_1")
            assert r.has_content  # Shows "no persona" message

    @pytest.mark.asyncio
    async def test_settings_handler(self):
        handler = SettingsHandler()
        r = await handler.show("teacher_1")
        assert r.has_content

    @pytest.mark.asyncio
    async def test_progress_handler(self):
        handler = ProgressHandler()
        r = await handler.show("teacher_1")
        assert r.has_content
```

- [ ] **Step 3: Implement misc handlers**

```python
# eduagent/handlers/misc.py
"""Small handlers for demo, persona, settings, progress, model switch.

These are the tg.py commands that don't warrant their own file.
"""
from __future__ import annotations

import logging

from eduagent.gateway_response import GatewayResponse

logger = logging.getLogger(__name__)


# Lazy imports
async def handle_message(text, **kwargs):
    from eduagent.openclaw_plugin import handle_message as _hm
    return await _hm(text, **kwargs)


class DemoHandler:
    async def run(self, teacher_id: str) -> GatewayResponse:
        try:
            text = await handle_message(
                "generate a sample lesson on photosynthesis for 6th grade science",
                teacher_id=teacher_id,
            )
            return GatewayResponse(text=text)
        except Exception as e:
            return GatewayResponse(text=f"Demo failed: {e}")


class PersonaHandler:
    async def show(self, teacher_id: str) -> GatewayResponse:
        try:
            from eduagent.state import TeacherSession
            session = TeacherSession.load(teacher_id)
            if not session.persona:
                return GatewayResponse(
                    text="No teaching persona yet. Upload some lesson files and I'll learn your style!"
                )
            p = session.persona
            lines = [
                f"Your teaching persona:",
                f"  Style: {p.teaching_style}",
                f"  Tone: {p.tone}",
                f"  Subject: {p.subject_area}",
            ]
            if p.favorite_strategies:
                lines.append(f"  Strategies: {', '.join(p.favorite_strategies[:3])}")
            return GatewayResponse(text="\n".join(lines))
        except Exception as e:
            return GatewayResponse(text=f"Could not load persona: {e}")


class SettingsHandler:
    async def show(self, teacher_id: str) -> GatewayResponse:
        try:
            from eduagent.models import AppConfig
            config = AppConfig.load()
            lines = [
                "Your settings:",
                f"  Provider: {config.provider}",
                f"  Model: {config.ollama_model}",
                f"  Output: {config.output_dir}",
                f"  Export format: {config.export_format}",
            ]
            if config.teacher_profile:
                tp = config.teacher_profile
                lines.append(f"  Name: {tp.name}")
                lines.append(f"  Subjects: {', '.join(tp.subjects)}")
                lines.append(f"  Grades: {', '.join(tp.grade_levels)}")
            return GatewayResponse(text="\n".join(lines))
        except Exception as e:
            return GatewayResponse(text=f"Could not load settings: {e}")


class ProgressHandler:
    async def show(self, teacher_id: str) -> GatewayResponse:
        try:
            from eduagent.analytics import get_teacher_stats
            stats = get_teacher_stats(teacher_id)
            lines = [
                "Your progress:",
                f"  Lessons generated: {stats.get('total_lessons', 0)}",
                f"  Units planned: {stats.get('total_units', 0)}",
                f"  Lessons rated: {stats.get('rated_lessons', 0)}",
                f"  Average rating: {stats.get('overall_avg_rating', 0):.1f}/5",
            ]
            return GatewayResponse(text="\n".join(lines))
        except Exception as e:
            return GatewayResponse(text="No progress data yet. Generate some lessons first!")


class ModelSwitchHandler:
    async def switch(self, teacher_id: str, text: str) -> GatewayResponse:
        try:
            from eduagent.models import AppConfig, LLMProvider
            config = AppConfig.load()
            lower = text.lower()
            if "ollama" in lower:
                config.provider = LLMProvider.OLLAMA
            elif "anthropic" in lower:
                config.provider = LLMProvider.ANTHROPIC
            elif "openai" in lower:
                config.provider = LLMProvider.OPENAI
            else:
                return GatewayResponse(text="Supported providers: ollama, anthropic, openai")
            config.save()
            return GatewayResponse(text=f"Switched to {config.provider.value}.")
        except Exception as e:
            return GatewayResponse(text=f"Could not switch model: {e}")
```

- [ ] **Step 4: Run tests**

Run: `cd /Users/mind_uploaded_crustacean/Projects/eduagent && python -m pytest tests/test_handlers.py::TestMiscHandlers -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/mind_uploaded_crustacean/Projects/eduagent
git add eduagent/handlers/misc.py eduagent/router.py tests/test_handlers.py
git commit -m "feat: add misc handlers (demo/persona/settings/progress/model) and missing router intents"
```

---

## Task 7: Rewrite Gateway as the Brain

**Files:**
- Modify: `eduagent/gateway.py` — complete rewrite to orchestrate handlers
- Create: `tests/test_gateway_brain.py` — tests for the new gateway

This is the core task. The gateway becomes the single entry point: `gateway.handle(text, teacher_id, files?) → GatewayResponse`. It uses the router for intent detection, the onboard handler for new users, and dispatches to the appropriate handler.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_gateway_brain.py
"""Tests for the rewritten gateway — the brain of Claw-ED."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from eduagent.gateway import Gateway
from eduagent.gateway_response import GatewayResponse


class TestGatewayHandle:
    def setup_method(self):
        self.gw = Gateway()

    @pytest.mark.asyncio
    async def test_handle_returns_gateway_response(self):
        with patch.object(self.gw, "_dispatch", new_callable=AsyncMock) as mock_d:
            mock_d.return_value = GatewayResponse(text="Hello!")
            r = await self.gw.handle("hi", "teacher_1")
            assert isinstance(r, GatewayResponse)
            assert r.text == "Hello!"

    @pytest.mark.asyncio
    async def test_new_teacher_enters_onboarding(self):
        with patch("eduagent.gateway.has_config", return_value=False):
            r = await self.gw.handle("hello", "new_teacher")
            assert "subject" in r.text.lower() or "teach" in r.text.lower()

    @pytest.mark.asyncio
    async def test_existing_teacher_skips_onboarding(self):
        with patch("eduagent.gateway.has_config", return_value=True):
            with patch.object(self.gw, "_dispatch", new_callable=AsyncMock) as mock_d:
                mock_d.return_value = GatewayResponse(text="Lesson response")
                r = await self.gw.handle("lesson on fractions", "teacher_1")
                assert r.text == "Lesson response"
                mock_d.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_onboarding_continues_across_messages(self):
        with patch("eduagent.gateway.has_config", return_value=False):
            r1 = await self.gw.handle("hi", "t1")
            assert "subject" in r1.text.lower() or "teach" in r1.text.lower()
            r2 = await self.gw.handle("math", "t1")
            assert "grade" in r2.text.lower()

    @pytest.mark.asyncio
    async def test_callback_handling(self):
        """Gateway can handle callback data (button presses)."""
        with patch("eduagent.gateway.has_config", return_value=True):
            r = await self.gw.handle_callback(
                "rate:lesson_abc:5", "teacher_1"
            )
            assert isinstance(r, GatewayResponse)


class TestGatewayStats:
    def setup_method(self):
        self.gw = Gateway()

    @pytest.mark.asyncio
    async def test_stats_increment(self):
        with patch("eduagent.gateway.has_config", return_value=True):
            with patch.object(self.gw, "_dispatch", new_callable=AsyncMock) as mock_d:
                mock_d.return_value = GatewayResponse(text="ok")
                await self.gw.handle("hello", "t1")
                stats = await self.gw.stats()
                assert stats["messages_today"] >= 1

    @pytest.mark.asyncio
    async def test_initial_stats(self):
        stats = await self.gw.stats()
        assert stats["messages_today"] == 0
        assert "uptime_seconds" in stats


class TestGatewayEventBus:
    def setup_method(self):
        self.gw = Gateway()

    @pytest.mark.asyncio
    async def test_events_emitted(self):
        with patch("eduagent.gateway.has_config", return_value=True):
            with patch.object(self.gw, "_dispatch", new_callable=AsyncMock) as mock_d:
                mock_d.return_value = GatewayResponse(text="ok")
                await self.gw.handle("hi", "t1")
                assert not self.gw.event_bus.empty()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/mind_uploaded_crustacean/Projects/eduagent && python -m pytest tests/test_gateway_brain.py -v`
Expected: FAIL — Gateway class doesn't have `handle()` method yet

- [ ] **Step 3: Rewrite gateway.py**

Replace the contents of `eduagent/gateway.py` entirely. Preserve `ActivityEvent` and `GatewayStats` but rewrite `EduAgentGateway` → `Gateway`.

```python
# eduagent/gateway.py
"""The brain of Claw-ED — transport-agnostic message gateway.

Every message from every transport goes through:
    gateway.handle(text, teacher_id, files?) → GatewayResponse

The gateway handles:
  - Onboarding detection (new teacher? → onboard handler)
  - Intent detection (router.parse_intent)
  - Dispatch to the right handler
  - Event emission for TUI/monitoring
  - Session tracking

Transports (Telegram, Web, CLI) just render the GatewayResponse.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from eduagent.config import has_config
from eduagent.gateway_response import GatewayResponse
from eduagent.handlers.export import ExportHandler
from eduagent.handlers.feedback import FeedbackHandler
from eduagent.handlers.gaps import GapsHandler
from eduagent.handlers.generate import GenerateHandler
from eduagent.handlers.ingest import IngestHandler
from eduagent.handlers.misc import (
    DemoHandler,
    ModelSwitchHandler,
    PersonaHandler,
    ProgressHandler,
    SettingsHandler,
)
from eduagent.handlers.onboard import OnboardHandler
from eduagent.handlers.schedule import ScheduleHandler
from eduagent.handlers.standards import StandardsHandler
from eduagent.models import AppConfig
from eduagent.router import Intent, parse_intent

logger = logging.getLogger(__name__)


# ── Data classes (preserved from original) ───────────────────────────


@dataclass
class ActivityEvent:
    """A single event for the TUI activity feed."""

    timestamp: float
    event_type: str
    actor: str
    message: str
    data: dict = field(default_factory=dict)


@dataclass
class GatewayStats:
    """Live counters for the gateway dashboard."""

    messages_today: int = 0
    generations_today: int = 0
    errors_today: int = 0
    _start_time: float = field(default_factory=time.monotonic)

    @property
    def uptime_seconds(self) -> float:
        return time.monotonic() - self._start_time


# ── Gateway ──────────────────────────────────────────────────────────


class Gateway:
    """The brain of Claw-ED. Transport-agnostic."""

    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or AppConfig.load()
        self.event_bus: asyncio.Queue[ActivityEvent] = asyncio.Queue(maxsize=500)
        self.active_sessions: dict[str, dict] = {}
        self._stats = GatewayStats()

        # Handlers
        self._onboard = OnboardHandler()
        self._generate = GenerateHandler()
        self._export = ExportHandler()
        self._feedback = FeedbackHandler()
        self._schedule = ScheduleHandler()
        self._gaps = GapsHandler()
        self._standards = StandardsHandler()
        self._ingest = IngestHandler()
        self._demo = DemoHandler()
        self._persona = PersonaHandler()
        self._settings = SettingsHandler()
        self._progress = ProgressHandler()
        self._model_switch = ModelSwitchHandler()

    # ── Public API ───────────────────────────────────────────────────

    async def handle(
        self,
        message: str,
        teacher_id: str,
        files: list[Path] | None = None,
    ) -> GatewayResponse:
        """Process any message from any transport."""
        self._stats.messages_today += 1
        self.active_sessions[teacher_id] = {
            "last_activity": datetime.now().isoformat(),
        }
        await self.emit("message_received", {
            "teacher_id": teacher_id,
            "text": message[:200],
        })

        try:
            # Onboarding check
            if self._onboard.is_onboarding(teacher_id):
                return await self._onboard.step(teacher_id, message)

            if not has_config():
                return await self._onboard.step(teacher_id, message)

            # Dispatch based on intent
            return await self._dispatch(message, teacher_id, files)

        except Exception as e:
            logger.error("Gateway error: %s", e)
            self._stats.errors_today += 1
            await self.emit("error", {"teacher_id": teacher_id, "message": str(e)})
            return GatewayResponse(
                text="I ran into an issue processing that. Please try again."
            )

    async def handle_callback(
        self, callback_data: str, teacher_id: str
    ) -> GatewayResponse:
        """Handle button press callbacks (rate:id:5, action:export_slides:id, etc.)."""
        parts = callback_data.split(":")

        if parts[0] == "rate" and len(parts) >= 3:
            lesson_id = parts[1]
            rating_str = parts[2]
            if rating_str == "0_prompt":
                return self._feedback.rating_prompt(lesson_id)
            try:
                rating = int(rating_str)
            except ValueError:
                return GatewayResponse(text="Invalid rating.")
            return await self._feedback.rate(lesson_id, teacher_id, rating)

        if parts[0] == "action" and len(parts) >= 3:
            action = parts[1]
            lesson_id = parts[2]
            if action.startswith("export_"):
                fmt = action.replace("export_", "")
                return await self._export.export(lesson_id, teacher_id, fmt)
            if action == "worksheet":
                return await self._generate.lesson(f"worksheet for lesson {lesson_id}", teacher_id)

        return GatewayResponse(text="Unknown action.")

    async def stats(self) -> dict:
        """Return live stats. Kept async for backward compat with existing tests."""
        s = self._stats
        return {
            "messages_today": s.messages_today,
            "generations_today": s.generations_today,
            "errors_today": s.errors_today,
            "uptime_seconds": s.uptime_seconds,
            "active_sessions": len(self.active_sessions),
        }

    # ── Internal dispatch ────────────────────────────────────────────

    async def _dispatch(
        self,
        message: str,
        teacher_id: str,
        files: list[Path] | None = None,
    ) -> GatewayResponse:
        """Route a message to the appropriate handler based on intent."""
        # File ingestion
        if files:
            return await self._ingest.handle(teacher_id, files)

        # Path detection (user typed a filesystem path)
        if self._looks_like_path(message):
            return await self._ingest.handle(teacher_id, path=message.strip())

        # Parse intent
        parsed = parse_intent(message)
        intent = parsed.intent

        await self.emit("generation_started", {"teacher_id": teacher_id, "intent": intent.value})

        # Route to handler
        if intent == Intent.GENERATE_LESSON:
            self._stats.generations_today += 1
            return await self._generate.lesson(parsed.topic or message, teacher_id)

        if intent == Intent.GENERATE_UNIT:
            self._stats.generations_today += 1
            return await self._generate.unit(parsed.topic or message, teacher_id)

        if intent in (
            Intent.GENERATE_MATERIALS,
            Intent.GENERATE_ASSESSMENT,
            Intent.GENERATE_BELLRINGER,
            Intent.GENERATE_DIFFERENTIATION,
            Intent.GENERATE_YEAR_MAP,
            Intent.GENERATE_PACING_GUIDE,
        ):
            self._stats.generations_today += 1
            return await self._generate.lesson(message, teacher_id)

        if intent == Intent.SEARCH_STANDARDS:
            return await self._standards.lookup(
                parsed.subject or "", parsed.grade or ""
            )

        if intent == Intent.EXPORT_PDF:
            return await self._export.export("last", teacher_id, "pdf")

        if intent == Intent.EXPORT_SLIDES:
            return await self._export.export("last", teacher_id, "slides")

        if intent == Intent.EXPORT_HANDOUT:
            return await self._export.export("last", teacher_id, "handout")

        if intent == Intent.EXPORT_DOC:
            return await self._export.export("last", teacher_id, "doc")

        if intent == Intent.GAP_ANALYSIS:
            return await self._gaps.analyze(teacher_id)

        if intent == Intent.SCHEDULE:
            return await self._schedule.show(teacher_id)

        if intent == Intent.DEMO:
            return await self._demo.run(teacher_id)

        if intent == Intent.SHOW_PERSONA:
            return await self._persona.show(teacher_id)

        if intent == Intent.SHOW_SETTINGS:
            return await self._settings.show(teacher_id)

        if intent == Intent.SHOW_PROGRESS:
            return await self._progress.show(teacher_id)

        if intent == Intent.SHOW_FEEDBACK:
            return await self._feedback.summary(teacher_id)

        if intent == Intent.SWITCH_MODEL:
            return await self._model_switch.switch(teacher_id, message)

        if intent == Intent.HELP:
            return self._help_response()

        if intent == Intent.SHOW_STATUS:
            return await self._status_response(teacher_id)

        if intent == Intent.SETUP:
            return await self._onboard.step(teacher_id, message)

        # Fallback: general LLM conversation
        return await self._chat(message, teacher_id)

    async def _chat(self, message: str, teacher_id: str) -> GatewayResponse:
        """Fallback: send to LLM for general conversation."""
        try:
            from eduagent.openclaw_plugin import handle_message
            response = await handle_message(message, teacher_id=teacher_id)
            return GatewayResponse(text=response)
        except Exception as e:
            logger.error("Chat fallback failed: %s", e)
            return GatewayResponse(text="I couldn't process that. Please try again.")

    def _help_response(self) -> GatewayResponse:
        return GatewayResponse(
            text=(
                "Here's what I can do:\n\n"
                "  'plan a unit on [topic]' — create a multi-week unit\n"
                "  'lesson on [topic]' — generate a daily lesson\n"
                "  'make a worksheet' — create student materials\n"
                "  'standards for [subject] [grade]' — look up standards\n"
                "  'curriculum gaps' — find what you're missing\n"
                "  'export slides/handout/doc' — export last lesson\n\n"
                "Just type naturally — I'll figure out what you need."
            ),
        )

    async def _status_response(self, teacher_id: str) -> GatewayResponse:
        try:
            from eduagent.openclaw_plugin import _show_status
            from eduagent.state import TeacherSession
            session = TeacherSession.load(teacher_id)
            return GatewayResponse(text=_show_status(session))
        except Exception as e:
            return GatewayResponse(text=f"Could not load status: {e}")

    @staticmethod
    def _looks_like_path(text: str) -> bool:
        """Detect if the message looks like a filesystem path."""
        stripped = text.strip()
        return (
            stripped.startswith("/") and not stripped.startswith("/help")
            and not stripped.startswith("/start")
            and not stripped.startswith("/status")
            and "/" in stripped[1:]
        ) or stripped.startswith("~/")

    # ── Events ───────────────────────────────────────────────────────

    async def emit(self, event_type: str, data: dict | None = None) -> None:
        event = ActivityEvent(
            timestamp=time.time(),
            event_type=event_type,
            actor=data.get("teacher_id", "system") if data else "system",
            message=data.get("text", data.get("message", event_type)) if data else event_type,
            data=data or {},
        )
        if self.event_bus.full():
            try:
                self.event_bus.get_nowait()
            except asyncio.QueueEmpty:
                pass
        await self.event_bus.put(event)

    # ── Backward compatibility ───────────────────────────────────────

    async def process_message(self, text: str, teacher_id: str = "cli",
                              teacher_name: str = "Teacher") -> str:
        """Backward-compatible: process message and return text string."""
        r = await self.handle(text, teacher_id)
        return r.text

    async def start(self) -> None:
        """Backward-compatible start (no-op — transports start themselves)."""
        self._running = True
        await self.emit("system", {"message": "Gateway started"})


# The old EduAgentGateway API is preserved for the TUI
EduAgentGateway = Gateway
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/mind_uploaded_crustacean/Projects/eduagent && python -m pytest tests/test_gateway_brain.py -v`
Expected: All tests PASS

- [ ] **Step 5: Run existing gateway tests to verify backward compat**

Run: `cd /Users/mind_uploaded_crustacean/Projects/eduagent && python -m pytest tests/test_gateway.py -v`
Expected: Tests should still PASS (may need minor adjustments for renamed class — `EduAgentGateway` alias exists)

- [ ] **Step 6: Fix any backward compatibility issues in test_gateway.py**

The `EduAgentGateway` alias, `process_message()`, `start()`, `emit()` (public), and `stats()` (async) are all preserved in the Gateway class for backward compat. If tests fail, check that they use `await` for `stats()` and call `emit()` (not `_emit()`).

- [ ] **Step 7: Run all gateway tests**

Run: `cd /Users/mind_uploaded_crustacean/Projects/eduagent && python -m pytest tests/test_gateway.py tests/test_gateway_brain.py -v`
Expected: All PASS

- [ ] **Step 8: Commit**

```bash
cd /Users/mind_uploaded_crustacean/Projects/eduagent
git add eduagent/gateway.py tests/test_gateway_brain.py
git commit -m "feat: rewrite gateway as transport-agnostic brain with handler dispatch"
```

---

## Task 8: Slim tg.py to a Thin Transport

**Files:**
- Modify: `eduagent/tg.py` — slim from 1816 to ~200 lines
- Create: `tests/test_tg_slim.py` — tests for the slim transport

This is the payoff: tg.py becomes a thin Telegram message shuttle that delegates everything to the gateway.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_tg_slim.py
"""Tests for the slimmed Telegram transport."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from eduagent.gateway_response import Button, GatewayResponse


class TestTelegramTransport:
    """Test the thin Telegram transport layer."""

    def test_import(self):
        from eduagent.tg import EduAgentTelegramBot, TelegramAPI, run_bot
        assert EduAgentTelegramBot is not None
        assert TelegramAPI is not None

    def test_telegram_api_init(self):
        from eduagent.tg import TelegramAPI
        api = TelegramAPI("fake_token")
        assert api.token == "fake_token"
        api.close()

    def test_bot_creates_gateway(self):
        from eduagent.tg import EduAgentTelegramBot
        bot = EduAgentTelegramBot("fake_token")
        assert bot.gateway is not None

    def test_render_text_only(self):
        from eduagent.tg import EduAgentTelegramBot
        bot = EduAgentTelegramBot("fake_token")
        api = MagicMock()
        r = GatewayResponse(text="Hello")
        bot._send_response(api, 12345, r)
        api.send_message.assert_called_once()

    def test_render_with_files(self):
        from eduagent.tg import EduAgentTelegramBot
        bot = EduAgentTelegramBot("fake_token")
        api = MagicMock()
        r = GatewayResponse(text="Here's your file", files=[Path("/tmp/test.pptx")])
        bot._send_response(api, 12345, r)
        api.send_message.assert_called_once()
        api.send_document.assert_called_once()

    def test_render_with_buttons(self):
        from eduagent.tg import EduAgentTelegramBot
        bot = EduAgentTelegramBot("fake_token")
        api = MagicMock()
        r = GatewayResponse(
            text="Rate?",
            button_rows=[[Button(label="5★", callback_data="rate:x:5")]],
        )
        bot._send_response(api, 12345, r)
        call_kwargs = api.send_message.call_args
        assert call_kwargs is not None
        # reply_markup should be set when buttons exist
        assert "reply_markup" in str(call_kwargs)

    def test_render_empty_response(self):
        from eduagent.tg import EduAgentTelegramBot
        bot = EduAgentTelegramBot("fake_token")
        api = MagicMock()
        r = GatewayResponse.empty()
        bot._send_response(api, 12345, r)
        # Empty response should not send anything
        api.send_message.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/mind_uploaded_crustacean/Projects/eduagent && python -m pytest tests/test_tg_slim.py -v`
Expected: FAIL — `bot.gateway` doesn't exist, `_send_response` doesn't exist

- [ ] **Step 3: Rewrite tg.py as a thin transport**

Replace `eduagent/tg.py` with a slim version. Keep `TelegramAPI` (the httpx wrapper — it's well-tested and works), keep `_check_bot_lock`/`_release_bot_lock`, but replace the 1300-line `EduAgentTelegramBot` with a ~100-line transport that delegates to `Gateway`.

```python
# eduagent/tg.py
"""Thin Telegram transport — delegates everything to the gateway.

Uses httpx (sync) for reliable Windows compatibility.
The transport's only job is: receive updates → gateway.handle() → render response.

Usage:
    from eduagent.tg import run_bot
    run_bot()
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import tempfile
import time
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_API_BASE = "https://api.telegram.org"
_MAX_MESSAGE_LENGTH = 4096
_BOT_LOCK = Path.home() / ".eduagent" / "bot.lock"
_ERROR_LOG = Path.home() / ".eduagent" / "errors.log"


def _log_error(error: Exception) -> None:
    try:
        _ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(_ERROR_LOG, "a") as f:
            import datetime
            f.write(
                f"[{datetime.datetime.now(datetime.timezone.utc).isoformat()}] "
                f"{type(error).__name__}: {error}\n"
            )
    except Exception:
        pass


def _check_bot_lock(force: bool = False) -> None:
    if _BOT_LOCK.exists():
        try:
            pid = int(_BOT_LOCK.read_text(encoding="utf-8").strip())
            if pid != os.getpid():
                try:
                    os.kill(pid, 0)
                    if not force:
                        raise RuntimeError(
                            f"Another bot instance is already running (PID {pid}). "
                            f"Stop it first or use --force."
                        )
                    logger.warning("Force-removing stale lock for PID %d", pid)
                except OSError:
                    logger.info("Removing stale bot lock (PID %d)", pid)
        except (ValueError, OSError):
            logger.info("Removing invalid bot lock file")
    _BOT_LOCK.parent.mkdir(parents=True, exist_ok=True)
    _BOT_LOCK.write_text(str(os.getpid()), encoding="utf-8")


def _release_bot_lock() -> None:
    try:
        if _BOT_LOCK.exists():
            pid = int(_BOT_LOCK.read_text(encoding="utf-8").strip())
            if pid == os.getpid():
                _BOT_LOCK.unlink()
    except Exception:
        pass


# ── Telegram API (unchanged — sync httpx wrapper) ───────────────────


class TelegramAPI:
    """Thin sync wrapper around the Telegram Bot API."""

    def __init__(self, token: str, timeout: float = 60.0):
        self.token = token
        self._base = f"{_API_BASE}/bot{token}"
        self._client = httpx.Client(timeout=httpx.Timeout(timeout, connect=15.0))

    def close(self) -> None:
        self._client.close()

    def _call(self, method: str, **params: Any) -> dict:
        params = {k: v for k, v in params.items() if v is not None}
        for attempt in range(3):
            try:
                resp = self._client.post(f"{self._base}/{method}", json=params)
                data = resp.json()
                if data.get("ok"):
                    return data.get("result", {})
                logger.warning("Telegram API error: %s", data.get("description"))
                return {}
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as e:
                if attempt < 2:
                    time.sleep(2**attempt)
                else:
                    _log_error(e)
                    return {}
        return {}

    def get_me(self) -> dict:
        return self._call("getMe")

    def get_updates(self, offset: int = 0, timeout: int = 30) -> list:
        return self._call("getUpdates", offset=offset, timeout=timeout) or []

    def send_message(self, chat_id: int, text: str, parse_mode: str | None = None,
                     reply_markup: dict | None = None) -> dict:
        if len(text) <= _MAX_MESSAGE_LENGTH:
            return self._call("sendMessage", chat_id=chat_id, text=text,
                            parse_mode=parse_mode, reply_markup=reply_markup)
        result = {}
        for i in range(0, len(text), 4000):
            chunk = text[i:i + 4000]
            markup = reply_markup if i + 4000 >= len(text) else None
            result = self._call("sendMessage", chat_id=chat_id, text=chunk,
                              parse_mode=parse_mode, reply_markup=markup)
        return result

    def send_document(self, chat_id: int, file_path: Path, caption: str | None = None) -> dict:
        with open(file_path, "rb") as f:
            resp = self._client.post(
                f"{self._base}/sendDocument",
                data={"chat_id": chat_id, **({"caption": caption} if caption else {})},
                files={"document": (file_path.name, f)},
            )
        data = resp.json()
        return data.get("result", {})

    def send_chat_action(self, chat_id: int, action: str = "typing") -> dict:
        return self._call("sendChatAction", chat_id=chat_id, action=action)

    def answer_callback_query(self, callback_query_id: str, text: str | None = None) -> dict:
        return self._call("answerCallbackQuery", callback_query_id=callback_query_id, text=text)

    def get_file(self, file_id: str) -> dict:
        return self._call("getFile", file_id=file_id)

    def download_file(self, file_path: str, local_path: Path) -> None:
        url = f"{_API_BASE}/file/bot{self.token}/{file_path}"
        resp = self._client.get(url)
        local_path.write_bytes(resp.content)

    def set_my_commands(self, commands: list[dict]) -> dict:
        return self._call("setMyCommands", commands=commands)


# ── Telegram Transport ───────────────────────────────────────────────


class EduAgentTelegramBot:
    """Thin Telegram transport — receives updates, delegates to Gateway, renders responses."""

    COMMANDS = [
        {"command": "start", "description": "Get started"},
        {"command": "help", "description": "Show help"},
        {"command": "status", "description": "Your profile & settings"},
    ]

    def __init__(self, token: str, data_dir: str | Path | None = None):
        self.token = token
        self.data_dir = Path(data_dir or Path.home() / ".eduagent")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        from eduagent.gateway import Gateway
        self.gateway = Gateway()
        self.api = TelegramAPI(token)
        self._running = False

    @classmethod
    def from_env(cls, data_dir=None):
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not token:
            from eduagent.models import AppConfig
            config = AppConfig.load()
            token = config.telegram_bot_token
        if not token:
            raise ValueError("No Telegram bot token found")
        return cls(token, data_dir)

    def run(self, force: bool = False) -> None:
        """Start polling loop."""
        _check_bot_lock(force)
        self._running = True

        def _shutdown(sig, frame):
            self._running = False

        signal.signal(signal.SIGINT, _shutdown)
        signal.signal(signal.SIGTERM, _shutdown)
        self.api.set_my_commands(self.COMMANDS)

        logger.info("Telegram transport started (polling)")
        offset = 0
        try:
            while self._running:
                updates = self.api.get_updates(offset=offset, timeout=30)
                for update in updates:
                    offset = update["update_id"] + 1
                    self._process_update(update)
        finally:
            _release_bot_lock()
            self.api.close()

    def _process_update(self, update: dict) -> None:
        """Route update to gateway, render response."""
        if "callback_query" in update:
            cb = update["callback_query"]
            chat_id = cb["message"]["chat"]["id"]
            teacher_id = str(cb["from"]["id"])
            data = cb.get("data", "")
            self.api.answer_callback_query(cb["id"])
            response = asyncio.run(self.gateway.handle_callback(data, teacher_id))
            self._send_response(self.api, chat_id, response)
            return

        msg = update.get("message", {})
        if not msg:
            return

        chat_id = msg["chat"]["id"]
        teacher_id = str(msg.get("from", {}).get("id", "unknown"))
        text = msg.get("text", "")

        # File handling
        files = []
        if msg.get("document"):
            files = self._download_files(msg)

        # Show typing while gateway processes
        self.api.send_chat_action(chat_id)

        response = asyncio.run(self.gateway.handle(text, teacher_id, files=files or None))
        self._send_response(self.api, chat_id, response)

    def _download_files(self, msg: dict) -> list[Path]:
        """Download attached files from Telegram."""
        files = []
        doc = msg.get("document", {})
        file_id = doc.get("file_id")
        if not file_id:
            return files
        file_info = self.api.get_file(file_id)
        if not file_info:
            return files
        file_name = doc.get("file_name", "document")
        local = Path(tempfile.mkdtemp()) / file_name
        self.api.download_file(file_info["file_path"], local)
        files.append(local)
        return files

    def _send_response(self, api: TelegramAPI, chat_id: int, response) -> None:
        """Render a GatewayResponse to Telegram."""
        from eduagent.gateway_response import GatewayResponse
        if not isinstance(response, GatewayResponse) or not response.has_content:
            return

        # Build inline keyboard from button_rows
        reply_markup = None
        rows = response.button_rows
        if not rows and response.buttons:
            rows = [response.buttons]
        if rows:
            keyboard = []
            for row in rows:
                keyboard.append([
                    {"text": b.label, **({"url": b.url} if b.url else {"callback_data": b.callback_data})}
                    for b in row
                ])
            reply_markup = {"inline_keyboard": keyboard}

        if response.text:
            api.send_message(chat_id, response.text, reply_markup=reply_markup)

        for file_path in response.files:
            api.send_document(chat_id, file_path)


def run_bot(token: str | None = None, data_dir=None, *, force: bool = False) -> None:
    """Public entry point for the Telegram bot."""
    if token:
        bot = EduAgentTelegramBot(token, data_dir)
    else:
        bot = EduAgentTelegramBot.from_env(data_dir)
    bot.run(force=force)
```

- [ ] **Step 4: Run slim transport tests**

Run: `cd /Users/mind_uploaded_crustacean/Projects/eduagent && python -m pytest tests/test_tg_slim.py -v`
Expected: All 7 tests PASS

- [ ] **Step 5: Run existing tg tests**

Run: `cd /Users/mind_uploaded_crustacean/Projects/eduagent && python -m pytest tests/test_telegram_bot.py -v`
Expected: Mostly PASS — some may need adjustments for changed API surface

- [ ] **Step 6: Fix any broken telegram bot tests**

The existing `test_telegram_bot.py` tests the `telegram_bot.py` file (python-telegram-bot based), NOT `tg.py`. Verify which module each test imports and fix accordingly.

- [ ] **Step 7: Commit**

```bash
cd /Users/mind_uploaded_crustacean/Projects/eduagent
git add eduagent/tg.py tests/test_tg_slim.py
git commit -m "refactor: slim tg.py to thin transport delegating to Gateway"
```

---

## Task 9: Full Test Suite Green Check

**Files:**
- Modify: various test files as needed
- No new files

Run the complete test suite and fix any breakage from the refactoring.

- [ ] **Step 1: Run the full test suite**

Run: `cd /Users/mind_uploaded_crustacean/Projects/eduagent && python -m pytest tests/ -v --tb=short 2>&1 | head -100`

- [ ] **Step 2: Fix any import errors**

Common issues:
- Tests importing `from eduagent.gateway import EduAgentGateway` → alias exists, should work
- Tests importing `from eduagent.tg import _detect_intent` → moved to router; fix imports
- Tests referencing `gateway.start()` → backward compat method added

For each failure, fix the minimal amount needed.

- [ ] **Step 3: Fix any behavioral test failures**

Tests that directly call tg.py internal methods (like `_handle_onboarding`, `_cmd_lesson`) will break because those methods no longer exist. Update these tests to call the equivalent handler or gateway method instead.

- [ ] **Step 4: Run tests again to confirm all green**

Run: `cd /Users/mind_uploaded_crustacean/Projects/eduagent && python -m pytest tests/ -v --tb=short`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/mind_uploaded_crustacean/Projects/eduagent
git add -u
git commit -m "fix: update tests for gateway extraction refactoring"
```

---

## Task 10: Wire Up Existing Transports

**Files:**
- Modify: `eduagent/gateway.py` — minor: re-export for backward compat
- Modify: `eduagent/cli_chat.py` — update to use Gateway.handle()
- Modify: `eduagent/api/routes/chat.py` — update to use Gateway.handle()

Ensure all existing entry points (CLI, Web API) use the new gateway.

- [ ] **Step 1: Check how cli_chat.py currently works**

Read `eduagent/cli_chat.py` and see what it calls.

- [ ] **Step 2: Update cli_chat.py to use Gateway**

Replace direct `openclaw_plugin.handle_message()` calls with `gateway.handle()`, rendering `GatewayResponse.text` to the terminal.

- [ ] **Step 3: Check how web API routes work**

Read `eduagent/api/routes/chat.py` to see what it calls.

- [ ] **Step 4: Update web API to use Gateway**

Replace direct calls with `gateway.handle()`, serializing `GatewayResponse` to JSON.

- [ ] **Step 5: Run full test suite**

Run: `cd /Users/mind_uploaded_crustacean/Projects/eduagent && python -m pytest tests/ -v --tb=short`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/mind_uploaded_crustacean/Projects/eduagent
git add eduagent/cli_chat.py eduagent/api/routes/chat.py
git commit -m "refactor: wire CLI and Web API to use Gateway.handle()"
```

---

## Summary

| Task | What | LOC Created | LOC Removed |
|------|------|-------------|-------------|
| 1 | GatewayResponse dataclass | ~45 | 0 |
| 2 | OnboardHandler | ~120 | 0 |
| 3 | GenerateHandler | ~70 | 0 |
| 4 | ExportHandler | ~95 | 0 |
| 5 | FeedbackHandler | ~100 | 0 |
| 6 | Schedule/Gaps/Standards/Ingest | ~200 | 0 |
| 6b | Misc handlers + Router intents | ~150 | 0 |
| 7 | Rewrite Gateway | ~280 | ~248 |
| 8 | Slim tg.py | ~200 | ~1600 |
| 9 | Fix test suite | ~50 | ~50 |
| 10 | Wire up transports | ~30 | ~30 |

**Net result:** tg.py goes from 1816 → ~200 lines. Gateway becomes the brain (~280 lines). Handlers total ~735 lines across 9 files. All logic is transport-agnostic and testable in isolation.

### Known Regressions / Follow-up Items
- **Onboarding simplified:** Model selection step removed (defaults to config). Add back as optional in Phase 2.
- **Typing indicators:** tg.py's periodic typing thread during long generation is not replicated. The gateway sets `GatewayResponse.typing=True` but the transport doesn't poll. Add typing thread in transport for Phase 2.
- **Message editing:** tg.py uses `edit_message_text` for rating callbacks. The slim transport always sends new messages. Restore edit behavior in Phase 2.
- **LLM retry/timeout:** tg.py's `_llm_call` had ThreadPoolExecutor + retry + 120s timeout. GenerateHandler's `handle_message` call has no retry. Add retry wrapper in Phase 2.
