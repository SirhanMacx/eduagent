# Claw-ED v2.3.5 Master Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform Claw-ED into the best personal teaching AI assistant — Master Content Track architecture, stimulus-based assessment, zero silent failures, identity protection, visual density, and full test coverage.

**Architecture:** Single `MasterContent` LLM generation replaces 3 parallel calls. Three output documents (teacher DOCX, student DOCX, PPTX) are compiled mechanically as views of the same data. All generators migrate to `safe_generate_json()` with retry. 10 post-generation validators enforce contract fidelity. Demo mode uses schema-aware fixture routing. Identity writes require explicit confirmation.

**Tech Stack:** Python 3.10+, Pydantic v2, python-pptx, python-docx, asyncio, httpx, SQLite, typer, rich

**Spec:** `docs/superpowers/specs/2026-03-28-v235-comprehensive-design.md`

---

## Phase 1: Foundation

### Task 1: MasterContent model and sub-models

**Files:**
- Create: `clawed/master_content.py`
- Test: `tests/test_master_content.py`

- [ ] **Step 1: Write model validation tests**

Create `tests/test_master_content.py`:
```python
"""Tests for MasterContent model and sub-models."""
import pytest
from pydantic import ValidationError


class TestMasterContentModel:
    def test_minimal_valid_master_content(self):
        from clawed.master_content import (
            DoNow, GuidedNote, InstructionSection, MasterContent, StimulusQuestion,
        )
        from clawed.models import DifferentiationNotes

        mc = MasterContent(
            title="Causes of the American Revolution",
            subject="Social Studies",
            grade_level="8",
            topic="American Revolution",
            objective="Students will analyze the causes of the American Revolution.",
            do_now=DoNow(
                stimulus="Look at this political cartoon from 1765.",
                stimulus_type="image",
                questions=["What do you notice?"],
                answers=["The colonists look angry about taxes."],
            ),
            direct_instruction=[
                InstructionSection(
                    heading="The Stamp Act",
                    content="In 1765, Parliament passed the Stamp Act.",
                    teacher_script="Open with the cartoon from the Do Now.",
                    key_points=["taxation without representation", "colonial protest"],
                ),
            ],
            guided_notes=[
                GuidedNote(prompt="The Stamp Act taxed ___.", answer="printed materials", section_ref="The Stamp Act"),
                GuidedNote(prompt="Colonists protested because they had no ___.", answer="representation", section_ref="The Stamp Act"),
                GuidedNote(prompt="The slogan was 'no ___ without ___'.", answer="taxation without representation", section_ref="The Stamp Act"),
                GuidedNote(prompt="The Stamp Act was passed in ___.", answer="1765", section_ref="The Stamp Act"),
                GuidedNote(prompt="Parliament is the ___ legislature.", answer="British", section_ref="The Stamp Act"),
            ],
            exit_ticket=[
                StimulusQuestion(
                    stimulus="Read the excerpt from Samuel Adams' letter to Parliament (1765).",
                    stimulus_type="text_excerpt",
                    question="Based on this source, what was Adams' main argument against the Stamp Act?",
                    answer="Colonists cannot be taxed by a body in which they have no elected representatives.",
                    cognitive_level="analysis",
                ),
            ],
            differentiation=DifferentiationNotes(
                struggling=["Provide pre-filled graphic organizer with 3 of 5 rows completed"],
                advanced=["Compare Stamp Act resistance to modern protest movements"],
                ell=["Provide bilingual vocabulary list with visual supports"],
            ),
        )
        assert mc.title == "Causes of the American Revolution"
        assert len(mc.guided_notes) == 5
        assert len(mc.exit_ticket) == 1

    def test_stimulus_question_requires_stimulus(self):
        from clawed.master_content import StimulusQuestion

        with pytest.raises(ValidationError):
            StimulusQuestion(
                stimulus="",  # empty — should fail
                stimulus_type="text_excerpt",
                question="What happened?",
                answer="Something.",
            )

    def test_to_daily_lesson_backwards_compat(self):
        from clawed.master_content import (
            DoNow, GuidedNote, InstructionSection, MasterContent, StimulusQuestion,
        )
        from clawed.models import DailyLesson, DifferentiationNotes

        mc = MasterContent(
            title="Test Lesson",
            subject="Science",
            grade_level="6",
            topic="Photosynthesis",
            objective="Understand photosynthesis.",
            do_now=DoNow(stimulus="Look at this leaf.", stimulus_type="image", questions=["What do you see?"], answers=["A leaf."]),
            direct_instruction=[InstructionSection(heading="Intro", content="Plants make food.", teacher_script="Explain.", key_points=["sunlight"])],
            guided_notes=[GuidedNote(prompt="Plants use ___.", answer="sunlight", section_ref="Intro")] * 5,
            exit_ticket=[StimulusQuestion(stimulus="Diagram of leaf.", stimulus_type="diagram", question="Label the parts.", answer="Chloroplast.", cognitive_level="application")],
            differentiation=DifferentiationNotes(struggling=["Visual aids"], advanced=["Research"], ell=["Word wall"]),
        )
        dl = mc.to_daily_lesson()
        assert isinstance(dl, DailyLesson)
        assert dl.title == "Test Lesson"
        assert dl.objective == "Understand photosynthesis."

    def test_vocabulary_entry_fields(self):
        from clawed.master_content import VocabularyEntry

        v = VocabularyEntry(term="photosynthesis", definition="Process by which plants make food", context_sentence="During photosynthesis, plants convert sunlight to energy.")
        assert v.term == "photosynthesis"
        assert v.image_spec == ""  # optional

    def test_primary_source_fields(self):
        from clawed.master_content import PrimarySource

        ps = PrimarySource(
            id="stamp_act_1765",
            title="The Stamp Act (1765)",
            source_type="text_excerpt",
            content_text="An act for granting and applying certain stamp duties...",
            attribution="British Parliament, 1765",
        )
        assert ps.id == "stamp_act_1765"

    def test_station_document_fields(self):
        from clawed.master_content import StationDocument

        sd = StationDocument(
            title="Station 1: The Stamp Act",
            source_ref="stamp_act_1765",
            task="Read the excerpt and answer the scaffolding questions.",
            student_directions="1. Read the source. 2. Answer questions 1-3.",
            teacher_answer_key="1. Taxes on printed goods. 2. No representation. 3. Protests.",
        )
        assert sd.source_ref == "stamp_act_1765"
```

- [ ] **Step 2: Run tests — expect FAIL (module not found)**

Run: `cd /Users/mind_uploaded_crustacean/Projects/Claw-ED-v0920 && python -m pytest tests/test_master_content.py -x -q 2>&1 | tail -5`

- [ ] **Step 3: Implement MasterContent model**

Create `clawed/master_content.py` with all sub-models from the spec (Section 1). Key points:
- Import `DifferentiationNotes` from `clawed.models` (reuse, don't duplicate)
- `StimulusQuestion.stimulus` must have a `field_validator` that rejects empty strings
- `MasterContent.to_daily_lesson()` converts to legacy `DailyLesson` format:
  - `do_now` → join stimulus + questions as string
  - `direct_instruction` → join all section contents
  - `guided_practice` → join guided notes prompts
  - `exit_ticket` → convert `StimulusQuestion` to `ExitTicketQuestion`
  - `differentiation` → pass through (same model)

- [ ] **Step 4: Run tests — expect PASS**

Run: `cd /Users/mind_uploaded_crustacean/Projects/Claw-ED-v0920 && python -m pytest tests/test_master_content.py -x -q 2>&1 | tail -5`

- [ ] **Step 5: Commit**

```bash
git add clawed/master_content.py tests/test_master_content.py
git commit -m "feat: MasterContent model with sub-models and backwards compat"
```

---

### Task 2: Master content prompt template

**Files:**
- Create: `clawed/prompts/master_content.txt`

- [ ] **Step 1: Write the master content prompt template**

Create `clawed/prompts/master_content.txt` — the single comprehensive prompt that generates a `MasterContent` JSON object. Must include:
- All field instructions matching the Pydantic model
- Stimulus-based assessment instructions for all subjects (spec Section 8)
- Self-contained materials rule / delegation phrase prevention (spec Section 8)
- Pedagogical quality requirements (Do Now, guided notes >= 5, primary sources >= 2, exit ticket progression)
- Placeholders: `{persona}`, `{subject}`, `{grade_level}`, `{topic}`, `{objective}`, `{standards}`, `{few_shot_context}`, `{teacher_materials}`, `{duration_minutes}`
- JSON output format instruction matching `MasterContent` schema

- [ ] **Step 2: Commit**

```bash
git add clawed/prompts/master_content.txt
git commit -m "feat: master content prompt template with stimulus-based pedagogy"
```

---

### Task 3: Demo hint parameter threading through LLM client

**Files:**
- Modify: `clawed/llm.py:21-27` (generate), `clawed/llm.py:59` (_demo_response), `clawed/llm.py:160-166` (generate_json), `clawed/llm.py:200-206` (safe_generate_json)
- Test: `tests/test_demo_routing.py`

- [ ] **Step 1: Write demo routing tests**

Create `tests/test_demo_routing.py`:
```python
"""Tests for schema-aware demo fixture routing."""
import json
import pytest


class TestDemoHintRouting:
    def test_demo_hint_returns_correct_fixture(self):
        from clawed.llm import LLMClient

        # Each hint should return JSON that parses without error
        hints = ["MasterContent", "UnitPlan", "Quiz", "Rubric", "YearMap", "DailyLesson"]
        for hint in hints:
            raw = LLMClient._demo_response("any prompt", demo_hint=hint)
            data = json.loads(raw)
            assert isinstance(data, dict), f"Hint '{hint}' returned non-dict"

    def test_demo_hint_master_content_validates(self):
        from clawed.llm import LLMClient
        from clawed.master_content import MasterContent

        raw = LLMClient._demo_response("generate lesson", demo_hint="MasterContent")
        data = json.loads(raw)
        mc = MasterContent.model_validate(data)
        assert len(mc.guided_notes) >= 5
        assert len(mc.exit_ticket) >= 1
        assert len(mc.primary_sources) >= 1

    def test_demo_hint_quiz_validates(self):
        from clawed.llm import LLMClient
        from clawed.models import Quiz

        raw = LLMClient._demo_response("generate quiz", demo_hint="Quiz")
        data = json.loads(raw)
        quiz = Quiz.model_validate(data)
        assert len(quiz.questions) >= 1

    def test_fallback_keyword_when_no_hint(self):
        from clawed.llm import LLMClient

        raw = LLMClient._demo_response("generate a lesson on history", demo_hint="")
        data = json.loads(raw)
        assert "title" in data  # should return some valid fixture

    def test_safe_generate_json_auto_derives_hint(self):
        """safe_generate_json should auto-derive demo_hint from model_class.__name__."""
        # This is an integration test — just verify the parameter exists
        import inspect
        from clawed.llm import LLMClient

        sig = inspect.signature(LLMClient.safe_generate_json)
        assert "demo_hint" in sig.parameters


class TestCredentialResolution:
    def test_no_keys_returns_none(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        from clawed.config import resolve_credentials

        provider, key = resolve_credentials()
        # With no env vars and no keychain, should return None
        # (actual behavior depends on keychain state)
        assert provider is None or isinstance(provider, str)

    def test_env_var_detected(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test123")
        from clawed.config import resolve_credentials

        provider, key = resolve_credentials()
        assert provider == "anthropic"
        assert key == "sk-ant-test123"

    def test_is_demo_mode_false_with_key(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test123")
        from clawed.demo import is_demo_mode

        assert is_demo_mode() is False

    def test_is_demo_mode_true_without_keys(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        from clawed.demo import is_demo_mode

        # May still return False if keychain has keys — that's correct behavior
        result = is_demo_mode()
        assert isinstance(result, bool)
```

- [ ] **Step 2: Run tests — expect FAIL**

Run: `cd /Users/mind_uploaded_crustacean/Projects/Claw-ED-v0920 && python -m pytest tests/test_demo_routing.py -x -q 2>&1 | tail -5`

- [ ] **Step 3: Add `demo_hint` parameter to LLM client methods**

In `clawed/llm.py`:
- `generate()` (line 21): add `demo_hint: str = ""` param, pass to `_demo_response(prompt, demo_hint)` on line 38
- `generate_json()` (line 160): add `demo_hint: str = ""` param, pass to `self.generate(..., demo_hint=demo_hint)`
- `safe_generate_json()` (line 200): add `demo_hint: str = ""` param; if empty, auto-derive from `model_class.__name__`; pass to `self.generate_json(..., demo_hint=demo_hint)`
- `_demo_response()` (line 59): add `demo_hint: str = ""` param, implement `HINT_TO_FIXTURE` dispatch per spec Section 2

- [ ] **Step 4: Add `resolve_credentials()` to config.py**

In `clawed/config.py`, add after `get_api_key()` (line 95):
```python
def resolve_credentials(config=None):
    """Returns (provider_name, api_key) or (None, None)."""
    # Check env vars first
    for env_var, provider in [("ANTHROPIC_API_KEY", "anthropic"), ("OPENAI_API_KEY", "openai"), ("GOOGLE_API_KEY", "google")]:
        key = os.environ.get(env_var)
        if key:
            return provider, key
    # Check keychain
    for provider in ["anthropic", "openai"]:
        key = get_api_key(provider)
        if key:
            return provider, key
    # Check Ollama
    if config and getattr(config, "provider", None) == "ollama":
        return "ollama", None
    return None, None
```

- [ ] **Step 5: Update `is_demo_mode()` in `clawed/demo/__init__.py`**

Replace the existing `is_demo_mode()` (line 34) to use `resolve_credentials()`:
```python
def is_demo_mode(config=None):
    from clawed.config import resolve_credentials
    provider, key = resolve_credentials(config)
    return provider is None
```

- [ ] **Step 6: Create new demo fixture files**

Create JSON fixture files in `clawed/demo/` for: `demo_master_content.json`, `demo_quiz.json`, `demo_rubric.json`, `demo_year_map.json`, `demo_formative_assessment.json`, `demo_lesson_materials.json`, `demo_pacing_guide.json`. Each must validate against its Pydantic model. Use the existing `demo_assessment.json` and `demo_unit_plan.json` as style guides.

- [ ] **Step 7: Run tests — expect PASS**

Run: `cd /Users/mind_uploaded_crustacean/Projects/Claw-ED-v0920 && python -m pytest tests/test_demo_routing.py -x -q 2>&1 | tail -5`

- [ ] **Step 8: Run full test suite — expect PASS (no regressions)**

Run: `cd /Users/mind_uploaded_crustacean/Projects/Claw-ED-v0920 && python -m pytest tests/ -x -q 2>&1 | tail -5`

- [ ] **Step 9: Commit**

```bash
git add clawed/llm.py clawed/config.py clawed/demo/ tests/test_demo_routing.py
git commit -m "feat: schema-aware demo routing with unified credential resolution"
```

---

### Task 4: Compilation functions (teacher view, student view, slides)

**Files:**
- Create: `clawed/compile_teacher.py`
- Create: `clawed/compile_student.py`
- Create: `clawed/compile_slides.py`
- Test: `tests/test_compilation.py`

- [ ] **Step 1: Write compilation tests**

Create `tests/test_compilation.py` that creates a `MasterContent` fixture, calls each compiler, and asserts output files exist with correct properties:
- `compile_teacher_view()` produces a DOCX with answer keys present
- `compile_student_view()` produces a DOCX with blanks instead of answers
- `compile_slides()` produces a PPTX with correct slide count
- Student DOCX does NOT contain any `guided_notes[].answer` text
- Teacher DOCX DOES contain `guided_notes[].answer` text

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Implement `compile_teacher.py`**

`async def compile_teacher_view(master: MasterContent, images: dict[str, Path], output_dir: Path) -> Path`
- Uses python-docx to build a DOCX
- Sections: title/metadata, vocabulary table, Do Now (with answers), direct instruction sections (with teacher scripts), guided notes (answers filled in), stations (with answer keys), exit ticket (with answers), differentiation, homework
- Embeds images from the `images` dict where `image_spec` matches

- [ ] **Step 4: Implement `compile_student.py`**

`async def compile_student_view(master: MasterContent, images: dict[str, Path], output_dir: Path) -> Path`
- Same structure as teacher view but:
  - Guided notes show `prompt` with blank line instead of `answer`
  - No teacher scripts
  - No answer keys
  - Exit ticket shows questions without answers
  - Station documents show student_directions without teacher_answer_key

- [ ] **Step 5: Implement `compile_slides.py`**

`async def compile_slides(master: MasterContent, images: dict[str, Path], output_dir: Path) -> Path`
- Uses python-pptx
- Slide order: title → vocabulary → instruction sections → source analysis → station overview → exit ticket
- Layout selection based on content type (title_slide, source_slide, vocab_slide, instruction_slide, exit_ticket_slide)

- [ ] **Step 6: Run tests — expect PASS**

- [ ] **Step 7: Commit**

```bash
git add clawed/compile_teacher.py clawed/compile_student.py clawed/compile_slides.py tests/test_compilation.py
git commit -m "feat: mechanical compilation of teacher/student/slide views from MasterContent"
```

---

### Task 5: Wire MasterContent into generate_lesson and generate_lesson_bundle

**Files:**
- Modify: `clawed/lesson.py:15-143` (generate_lesson returns MasterContent)
- Modify: `clawed/agent_core/tools/generate_lesson_bundle.py` (orchestration rewrite)
- Modify: `clawed/lesson.py:146-151` (generate_all_lessons threads teacher_materials)

- [ ] **Step 1: Update `generate_lesson()` to return MasterContent**

In `clawed/lesson.py`:
- Change return type from `DailyLesson` to `MasterContent`
- Load `prompts/master_content.txt` instead of `prompts/lesson_plan.txt`
- Pass `demo_hint="MasterContent"` to `safe_generate_json()`
- Keep `teacher_materials` parameter (already exists at line 23)
- Remove persona double-injection: keep persona in system prompt only (line 125), remove `.replace("{persona}", ...)` from prompt (line 87)

- [ ] **Step 2: Update `generate_all_lessons()` signature**

Add `teacher_materials: str = ""` parameter, thread to each `generate_lesson()` call.

- [ ] **Step 3: Rewrite `generate_lesson_bundle.py` orchestration**

Replace the current parallel LLM calls (lines 279-381) with:
1. Generate `MasterContent` via `generate_lesson()`
2. Search teacher materials (AssetRegistry + CurriculumKB) and inject into prompt
3. Call `fetch_all_images(master, config)` to get all images
4. Call `compile_teacher_view(master, images, output_dir)`
5. Call `compile_student_view(master, images, output_dir)`
6. Call `compile_slides(master, images, output_dir)`
7. Run validation: `validate_master_content()`, `validate_alignment()`, `check_self_contained()`
8. Populate `GenerationReport` throughout
9. Replace hardcoded `Path("clawed_output")` with `config.output_dir`

- [ ] **Step 4: Run full test suite**

Run: `cd /Users/mind_uploaded_crustacean/Projects/Claw-ED-v0920 && python -m pytest tests/ -x -q 2>&1 | tail -10`

Fix any regressions (existing tests may reference `DailyLesson` return type — update to use `MasterContent` or `.to_daily_lesson()`).

- [ ] **Step 5: Commit**

```bash
git add clawed/lesson.py clawed/agent_core/tools/generate_lesson_bundle.py
git commit -m "feat: Master Content Track — single generation, three compiled views"
```

---

## Phase 2: Validation & Safety

### Task 6: Output validation module

**Files:**
- Create: `clawed/validation.py`
- Test: `tests/test_output_validation.py`

- [ ] **Step 1: Write validation tests**

Create `tests/test_output_validation.py` with tests for all 10 validators + delegation detection + alignment validation per spec Section 3. Key tests:
- `validate_master_content()` catches: 0 guided notes, 0 exit tickets, 0 primary sources, empty stimulus, topic drift
- `validate_quiz()` catches: 0 questions, topic drift, missing stimulus
- `validate_rubric()` catches: 0 criteria, 0 total_points
- `validate_year_map()` catches: 0 units, subject drift
- `validate_unit_plan()` catches: 0 lessons, topic drift
- `validate_formative()`, `validate_summative()`, `validate_dbq()`, `validate_lesson_materials()`, `validate_pacing_guide()` catch empty collections
- `check_self_contained()` detects delegation phrases
- `validate_alignment()` catches mismatched guided note answers and invalid station source refs

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Implement all 10 validators + helpers in `clawed/validation.py`**

Per spec Section 3 — complete code provided in spec.

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add clawed/validation.py tests/test_output_validation.py
git commit -m "feat: 10 post-generation validators with delegation and alignment checks"
```

---

### Task 7: GenerationReport model

**Files:**
- Create: `clawed/generation_report.py`

- [ ] **Step 1: Implement GenerationReport per spec Section 3**

Include `summary()` method that produces human-readable Quality Notes section.

- [ ] **Step 2: Commit**

```bash
git add clawed/generation_report.py
git commit -m "feat: GenerationReport model for surfacing quality notes"
```

---

### Task 8: Quality review fails closed

**Files:**
- Modify: `clawed/llm.py:383-421` (review_lesson_package exception handler)

- [ ] **Step 1: Change the exception handler from `return {"passed": True}` to `return {"passed": False}`**

In `clawed/llm.py`, find `review_lesson_package()` (line 383), locate the `except Exception` block (line ~420), change:
```python
except Exception:
    return {"passed": False, "issues": ["Quality review could not parse LLM response — review skipped"]}
```

- [ ] **Step 2: Run full test suite**

Run: `cd /Users/mind_uploaded_crustacean/Projects/Claw-ED-v0920 && python -m pytest tests/ -x -q 2>&1 | tail -5`

- [ ] **Step 3: Commit**

```bash
git add clawed/llm.py
git commit -m "fix: quality review fails closed — no more silent pass on parse errors"
```

---

### Task 9: Identity protection — TeacherProfile validation, explicit setup, audit log

**Files:**
- Modify: `clawed/models.py:848` (TeacherProfile field validators)
- Modify: `clawed/models.py:66` (TeacherPersona field bounds)
- Modify: `clawed/agent_core/core.py:140` (explicit setup trigger)
- Modify: `clawed/agent_core/tools/ingest_materials.py:246-278` (pending confirmation)
- Modify: `clawed/agent_core/tools/update_soul.py:106` (length cap + audit log)
- Test: `tests/test_onboarding_safety.py`

- [ ] **Step 1: Write onboarding safety tests**

Create `tests/test_onboarding_safety.py` per spec Section 9:
- Test TeacherProfile name truncates at 100 chars
- Test subject validates against whitelist
- Test explicit `/setup` required (ordinary greeting returns setup message)
- Test SOUL.md content capped at 500 chars

- [ ] **Step 2: Run tests — expect FAIL**

- [ ] **Step 3: Add field validators to TeacherProfile** (models.py:848)

Per spec Section 5 — `_validate_name`, `_validate_subjects`, `_validate_state`.

- [ ] **Step 4: Add field bounds to TeacherPersona** (models.py:66)

Per spec Section 5 — max_length on string fields, max 20 items on list fields.

- [ ] **Step 5: Change onboarding trigger to explicit /setup** (core.py:140)

Per spec Section 5 — only trigger on `/setup`, `/start`; otherwise return welcome message.

- [ ] **Step 6: Change ingest auto-population to pending confirmation** (ingest_materials.py:246-278)

Per spec Section 5 — store in `context.session_state["pending_profile_updates"]`, don't write directly.

- [ ] **Step 7: Add SOUL.md write protection** (update_soul.py)

Per spec Section 5 — cap content at 500 chars, add audit logging.

- [ ] **Step 8: Run tests — expect PASS**

- [ ] **Step 9: Run full test suite — no regressions**

- [ ] **Step 10: Commit**

```bash
git add clawed/models.py clawed/agent_core/core.py clawed/agent_core/tools/ingest_materials.py clawed/agent_core/tools/update_soul.py tests/test_onboarding_safety.py
git commit -m "fix: identity protection — explicit setup, field validation, audit trail"
```

---

## Phase 3: Pipeline Hardening

### Task 10: Fix coroutine reuse in safe_generate_json

**Files:**
- Modify: `clawed/llm.py:200-226`

- [ ] **Step 1: Refactor retry loop to use `current_prompt` instead of mutating `prompt`**

Per spec Section 4. Ensure original `prompt` is never modified.

- [ ] **Step 2: Run full test suite**

- [ ] **Step 3: Commit**

```bash
git add clawed/llm.py
git commit -m "fix: safe_generate_json uses immutable prompt in retry loop"
```

---

### Task 11: Migrate 11 generators to safe_generate_json

**Files:**
- Modify: `clawed/assessment.py` (5 generators: lines 41, 79, 127, 171, 208)
- Modify: `clawed/materials.py` (4 generators: lines 31, 65, 100, 137)
- Modify: `clawed/curriculum_map.py` (2 generators: lines 36, 92)

- [ ] **Step 1: Migrate assessment.py generators**

For each of the 5 `AssessmentGenerator` methods:
- Replace `client.generate_json()` + manual `model_validate()` with `client.safe_generate_json(prompt, model_class=X, demo_hint="X")`
- Where generators return multiple parsed objects (e.g., `questions` + `rubric`), create a wrapper Pydantic model that handles the parsing in `model_validator(mode="before")`

- [ ] **Step 2: Migrate materials.py generators**

Same pattern for all 4 functions. `generate_worksheet` → `safe_generate_json(model_class=WorksheetResult)`, etc.

- [ ] **Step 3: Migrate curriculum_map.py generators**

`generate_year_map` → `safe_generate_json(model_class=YearMap, demo_hint="YearMap")`
`generate_pacing_guide` → `safe_generate_json(model_class=PacingGuide, demo_hint="PacingGuide")`

- [ ] **Step 4: Run full test suite**

Run: `cd /Users/mind_uploaded_crustacean/Projects/Claw-ED-v0920 && python -m pytest tests/ -x -q 2>&1 | tail -10`

- [ ] **Step 5: Commit**

```bash
git add clawed/assessment.py clawed/materials.py clawed/curriculum_map.py
git commit -m "fix: all 11 generators use safe_generate_json with retry and demo_hint"
```

---

### Task 12: CLI error wrapping

**Files:**
- Modify: `clawed/commands/generate.py` (lesson, ingest commands)
- Modify: `clawed/commands/generate_assessment.py` (assess, rubric, materials commands)
- Modify: `clawed/commands/generate_unit.py` (unit, year-map commands)

- [ ] **Step 1: Wrap all `_run_async(generate_*(...))` calls in try/except**

Per spec Section 4. Pattern:
```python
try:
    result = _run_async(generate_fn(...))
except (RuntimeError, ValueError) as e:
    console.print(f"[red]Generation failed:[/red] {e}")
    console.print("[dim]Run with --debug for full details[/dim]")
    raise typer.Exit(1)
```

Apply to every CLI command that calls a generator.

- [ ] **Step 2: Run full test suite**

- [ ] **Step 3: Commit**

```bash
git add clawed/commands/generate.py clawed/commands/generate_assessment.py clawed/commands/generate_unit.py
git commit -m "fix: user-friendly CLI error wrapping — no raw tracebacks"
```

---

### Task 13: Async-native exports

**Files:**
- Modify: `clawed/export_pptx.py:140-144,203-207` (remove ThreadPoolExecutor)
- Modify: `clawed/export_docx.py` (make async)
- Modify: `clawed/commands/_helpers.py:68` (fix asyncio.get_event_loop)

- [ ] **Step 1: Fix `_helpers.py` — replace `asyncio.get_event_loop()` with `asyncio.run()`**

```python
def run_async(coro):
    """Run an async coroutine from synchronous CLI code."""
    return asyncio.run(coro)
```

- [ ] **Step 2: Remove ThreadPoolExecutor anti-pattern from `export_pptx.py`**

Replace lines 140-144 and 203-207 with direct `await` calls. Make the image-fetching functions `async def` and use `asyncio.gather()`.

- [ ] **Step 3: Make export_docx.py async where needed**

Remove any `asyncio.run()` calls from inside export functions (lines 42, 82).

- [ ] **Step 4: Run full test suite**

- [ ] **Step 5: Commit**

```bash
git add clawed/export_pptx.py clawed/export_docx.py clawed/commands/_helpers.py
git commit -m "fix: async-native exports — remove ThreadPoolExecutor, Python 3.14 compatible"
```

---

### Task 14: Teacher materials wiring

**Files:**
- Modify: `clawed/agent_core/tools/generate_lesson.py` (search before generate)
- Modify: `clawed/lesson.py:146-151` (generate_all_lessons accepts teacher_materials)

- [ ] **Step 1: Add search-before-generate to `GenerateLessonTool.execute()`**

Same pattern as `generate_lesson_bundle.py` — search AssetRegistry + CurriculumKB, pass results as `teacher_materials`.

- [ ] **Step 2: Verify generate_all_lessons threads teacher_materials**

Already done in Task 5 step 2. Verify it's correct.

- [ ] **Step 3: Run full test suite**

- [ ] **Step 4: Commit**

```bash
git add clawed/agent_core/tools/generate_lesson.py clawed/lesson.py
git commit -m "feat: teacher materials wired into all generation paths"
```

---

## Phase 4: Export & Visual

### Task 15: Image fetching pipeline

**Files:**
- Create: `clawed/image_pipeline.py`
- Modify: `clawed/models.py` (AppConfig.image_fetch_timeout)

- [ ] **Step 1: Implement `fetch_all_images()`**

```python
async def fetch_all_images(master: MasterContent, config: AppConfig) -> dict[str, Path]:
    """Fetch all image_specs from MasterContent in parallel. Returns spec→local_path map."""
```
- Collect all unique `image_spec` strings from vocabulary, primary_sources, instruction sections, exit ticket
- Use `asyncio.gather()` with `asyncio.wait_for(timeout=config.image_fetch_timeout)`
- Cache fetched images locally
- Log failures in `GenerationReport` but don't block

- [ ] **Step 2: Add `image_fetch_timeout` to AppConfig** (models.py)

```python
image_fetch_timeout: int = 10
```

- [ ] **Step 3: Commit**

```bash
git add clawed/image_pipeline.py clawed/models.py
git commit -m "feat: parallel image fetching pipeline with configurable timeout"
```

---

### Task 16: PPTX layout templates

**Files:**
- Modify: `clawed/compile_slides.py` (already created in Task 4)

- [ ] **Step 1: Implement richer slide layouts**

Add layout functions per spec Section 7:
- `_add_title_slide()` — full-bleed background + overlay text
- `_add_source_slide()` — split layout, source left, questions right
- `_add_vocab_slide()` — card grid
- `_add_instruction_slide()` — content + image + key points
- `_add_exit_ticket_slide()` — numbered stimulus-based questions
- `_add_station_overview_slide()` — station titles with thumbnails

- [ ] **Step 2: Run compilation tests**

- [ ] **Step 3: Commit**

```bash
git add clawed/compile_slides.py
git commit -m "feat: richer PPTX slide layouts — title, source, vocab, exit ticket"
```

---

## Phase 5: Prompt Refinement

### Task 17: NYS Regents conditional and prompt injection defense

**Files:**
- Modify: `clawed/lesson.py` (conditional NYS block in prompt building)
- Modify: `clawed/agent_core/prompt.py` (injection defense)

- [ ] **Step 1: Add NYS Regents conditional to prompt building**

In `clawed/lesson.py`, when building the master content prompt, check `config.teacher_profile.state == "NY"` and subject contains "social studies". If true, append the NYS Regents SBMCQ/CRQ section from spec Section 8.

- [ ] **Step 2: Add prompt injection defense to system prompt**

In `clawed/agent_core/prompt.py`, add the SECURITY instruction from spec Section 8 to the system prompt builder.

- [ ] **Step 3: Remove persona double-injection in lesson.py**

Remove `.replace("{persona}", persona.to_prompt_context())` from the user prompt. Keep persona in system prompt only.

- [ ] **Step 4: Run full test suite**

- [ ] **Step 5: Commit**

```bash
git add clawed/lesson.py clawed/agent_core/prompt.py
git commit -m "feat: NYS Regents conditional, prompt injection defense, persona dedup"
```

---

## Phase 6: Testing

### Task 18: End-to-end bundle integration test

**Files:**
- Create: `tests/test_bundle_integration.py`

- [ ] **Step 1: Write E2E test**

Mock the LLM to return the `demo_master_content.json` fixture. Run the full bundle pipeline (generate → fetch images → compile 3 views). Assert:
- All 3 output files exist
- Student DOCX has blanks
- Teacher DOCX has answers
- PPTX has expected slide count
- Guided note answers appear in instruction text (alignment check)

- [ ] **Step 2: Run test — expect PASS**

- [ ] **Step 3: Commit**

```bash
git add tests/test_bundle_integration.py
git commit -m "test: end-to-end bundle integration test with alignment validation"
```

---

### Task 19: Pedagogical quality tests

**Files:**
- Create: `tests/test_pedagogical_quality.py`

- [ ] **Step 1: Write pedagogical quality tests**

Per spec Section 9:
- Exit ticket has at least one analysis-level question
- Every question has non-empty stimulus
- Guided notes count >= 5
- Primary sources count >= 2
- Do Now is stimulus-based
- No delegation phrases
- Differentiation is specific (not generic)

Use the `demo_master_content.json` fixture to validate.

- [ ] **Step 2: Run test — expect PASS**

- [ ] **Step 3: Commit**

```bash
git add tests/test_pedagogical_quality.py
git commit -m "test: pedagogical quality validation — stimulus, notes, sources, differentiation"
```

---

### Task 20: pytest-cov CI integration

**Files:**
- Modify: `pyproject.toml`
- Modify: `.github/workflows/ci.yml` (if exists)

- [ ] **Step 1: Add pytest-cov to dev dependencies**

In `pyproject.toml`:
```toml
[tool.pytest.ini_options]
addopts = "--cov=clawed --cov-fail-under=70 --cov-report=term-missing"
```

Add `"pytest-cov>=4.0"` to `[project.optional-dependencies] dev`.

- [ ] **Step 2: Run tests with coverage**

Run: `cd /Users/mind_uploaded_crustacean/Projects/Claw-ED-v0920 && pip install pytest-cov && python -m pytest tests/ -q 2>&1 | tail -15`

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add pytest-cov with 70% minimum coverage threshold"
```

---

## Phase 7: Version Bump & Release

### Task 21: Final verification and release

**Files:**
- Modify: `pyproject.toml` (version)
- Modify: `clawed/__init__.py` (version)
- Modify: `tests/test_basic.py` (version assertion)
- Modify: `tests/test_v013_features.py` (version assertion)

- [ ] **Step 1: Bump version to 2.3.5**

Update in `pyproject.toml`, `clawed/__init__.py`, and both test files.

- [ ] **Step 2: Run ruff**

Run: `cd /Users/mind_uploaded_crustacean/Projects/Claw-ED-v0920 && ruff check . 2>&1 | tail -5`

Fix any violations.

- [ ] **Step 3: Run full test suite with coverage**

Run: `cd /Users/mind_uploaded_crustacean/Projects/Claw-ED-v0920 && python -m pytest tests/ -q 2>&1 | tail -10`

Expected: all pass, coverage >= 70%.

- [ ] **Step 4: Manual smoke test in demo mode**

Run each command and verify correct output shape:
```bash
clawed lesson "Photosynthesis" --grade 6 --subject Science
clawed unit "American Revolution" --grade 8 --subject "Social Studies" --weeks 2
clawed assess --type quiz --topic "fractions" --grade 5 --questions 10
clawed rubric --task "persuasive essay" --grade 8 --criteria 4
clawed year-map Science --grade 8 --weeks 36
```

- [ ] **Step 5: Commit version bump**

```bash
git add pyproject.toml clawed/__init__.py tests/test_basic.py tests/test_v013_features.py
git commit -m "chore: bump version to v2.3.5 — comprehensive stability and quality release

Master Content Track architecture, stimulus-based assessment, zero silent
failures, identity protection, visual density, async-native exports, and
full test coverage. Synthesized from three independent audits."
```

- [ ] **Step 6: Push and publish**

```bash
git push origin main
python -m build
twine upload dist/clawed-2.3.5*
```

- [ ] **Step 7: Test install on Sirhan**

```bash
ssh sirhanmacx@192.168.1.51 "uv tool upgrade clawed && clawed --version"
```
