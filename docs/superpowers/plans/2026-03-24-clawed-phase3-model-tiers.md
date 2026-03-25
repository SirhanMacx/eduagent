# Claw-ED Phase 3: Multi-Model Tier Routing — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace flat task→model mapping with a tier-based system (fast/work/deep) where tasks map to tiers and teachers configure which model serves each tier.

**Architecture:** Tasks map to one of three tiers. Each tier has a default model. Teachers override tier models in config (not individual tasks). The existing `route()` API signature stays the same so all 30+ call sites don't change. Intent detection moves to the `fast` tier to save cost.

**Tech Stack:** Python 3.10+, Pydantic 2, pytest

---

## File Structure

### Modified Files
- `clawed/model_router.py` — rewrite: add `ModelTier` enum, `TASK_TIERS` mapping, tier defaults, tier-aware `route()`
- `clawed/models.py` — add `tier_models` field to `AppConfig` (dict mapping tier name → model)
- `clawed/router.py` — use fast-tier model for intent detection (future: currently keyword-based, no LLM)
- `tests/test_model_router.py` — rewrite tests for tier-based routing

---

## Task 1: Add Tier Config to AppConfig

**Files:**
- Modify: `clawed/models.py`
- Modify: `tests/test_model_router.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_model_router.py`:

```python
class TestTierConfig:
    def test_appconfig_has_tier_models_field(self):
        config = AppConfig()
        assert hasattr(config, "tier_models")

    def test_tier_models_default_is_none(self):
        config = AppConfig()
        assert config.tier_models is None

    def test_tier_models_can_be_set(self):
        config = AppConfig(tier_models={"fast": "qwen3.5:cloud", "work": "claude-sonnet-4-6"})
        assert config.tier_models["fast"] == "qwen3.5:cloud"

    def test_tier_models_survives_json_roundtrip(self):
        config = AppConfig(tier_models={"fast": "qwen3.5:cloud"})
        json_str = config.model_dump_json()
        loaded = AppConfig.model_validate_json(json_str)
        assert loaded.tier_models == {"fast": "qwen3.5:cloud"}
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `.venv/bin/python3 -m pytest tests/test_model_router.py::TestTierConfig -v`

- [ ] **Step 3: Add the field to AppConfig**

In `clawed/models.py`, add after the `task_models` field (around line 630):

```python
    # Tier model overrides (e.g. {"fast": "qwen3.5:cloud", "work": "claude-sonnet-4-6", "deep": "claude-opus-4-6"})
    tier_models: Optional[dict[str, str]] = None
```

- [ ] **Step 4: Run tests — verify they pass**

- [ ] **Step 5: Commit**

```bash
git add clawed/models.py tests/test_model_router.py
git commit -m "feat: add tier_models config field to AppConfig"
```

---

## Task 2: Rewrite model_router.py with Tier System

**Files:**
- Modify: `clawed/model_router.py` — complete rewrite
- Modify: `tests/test_model_router.py` — update existing + add tier tests

The key: `route(task_type, config)` signature stays IDENTICAL. Internally it now resolves task → tier → model instead of task → model directly.

- [ ] **Step 1: Write the failing tests**

Replace the `TestTaskModelsMapping` and `TestRouteFunction` classes in `tests/test_model_router.py`:

```python
from clawed.model_router import (
    ModelTier,
    TASK_TIERS,
    DEFAULT_TIER_MODELS,
    resolve_tier,
    resolve_model,
    route,
)
from clawed.models import AppConfig, LLMProvider


class TestModelTier:
    def test_tier_enum_values(self):
        assert ModelTier.FAST.value == "fast"
        assert ModelTier.WORK.value == "work"
        assert ModelTier.DEEP.value == "deep"

    def test_all_tiers_have_defaults(self):
        for tier in ModelTier:
            assert tier.value in DEFAULT_TIER_MODELS


class TestTaskTiers:
    def test_fast_tasks(self):
        fast_tasks = ["intent_detection", "quick_answer", "search", "bellringer", "formatting"]
        for task in fast_tasks:
            assert TASK_TIERS[task] == ModelTier.FAST, f"{task} should be fast"

    def test_work_tasks(self):
        work_tasks = ["lesson_plan", "unit_plan", "materials", "differentiation",
                      "assessment", "year_map", "pacing_guide", "curriculum_gaps"]
        for task in work_tasks:
            assert TASK_TIERS[task] == ModelTier.WORK, f"{task} should be work"

    def test_deep_tasks(self):
        deep_tasks = ["persona_extract", "evaluation"]
        for task in deep_tasks:
            assert TASK_TIERS[task] == ModelTier.DEEP, f"{task} should be deep"

    def test_unknown_task_defaults_to_work(self):
        assert resolve_tier("totally_unknown_task") == ModelTier.WORK


class TestResolveTier:
    def test_known_task(self):
        assert resolve_tier("bellringer") == ModelTier.FAST

    def test_unknown_task(self):
        assert resolve_tier("something_new") == ModelTier.WORK


class TestResolveModel:
    def test_default_fast_model(self):
        config = AppConfig()
        model = resolve_model(ModelTier.FAST, config)
        assert model == DEFAULT_TIER_MODELS["fast"]

    def test_default_work_model(self):
        config = AppConfig()
        model = resolve_model(ModelTier.WORK, config)
        assert model == DEFAULT_TIER_MODELS["work"]

    def test_default_deep_model(self):
        config = AppConfig()
        model = resolve_model(ModelTier.DEEP, config)
        assert model == DEFAULT_TIER_MODELS["deep"]

    def test_teacher_tier_override(self):
        config = AppConfig(tier_models={"fast": "my-fast-model"})
        model = resolve_model(ModelTier.FAST, config)
        assert model == "my-fast-model"

    def test_teacher_tier_override_only_affects_specified(self):
        config = AppConfig(tier_models={"fast": "my-fast-model"})
        model = resolve_model(ModelTier.WORK, config)
        assert model == DEFAULT_TIER_MODELS["work"]


class TestRouteFunction:
    def test_route_returns_new_config(self):
        config = AppConfig(provider=LLMProvider.OLLAMA, ollama_model="llama3.2")
        routed = route("lesson_plan", config)
        assert routed is not config
        assert routed.ollama_model == DEFAULT_TIER_MODELS["work"]

    def test_route_does_not_mutate_original(self):
        config = AppConfig(provider=LLMProvider.OLLAMA, ollama_model="llama3.2")
        route("lesson_plan", config)
        assert config.ollama_model == "llama3.2"

    def test_route_fast_task(self):
        config = AppConfig(provider=LLMProvider.OLLAMA, ollama_model="llama3.2")
        routed = route("bellringer", config)
        assert routed.ollama_model == DEFAULT_TIER_MODELS["fast"]

    def test_route_work_task(self):
        config = AppConfig(provider=LLMProvider.OLLAMA, ollama_model="llama3.2")
        routed = route("unit_plan", config)
        assert routed.ollama_model == DEFAULT_TIER_MODELS["work"]

    def test_route_deep_task(self):
        config = AppConfig(provider=LLMProvider.OLLAMA, ollama_model="llama3.2")
        routed = route("persona_extract", config)
        assert routed.ollama_model == DEFAULT_TIER_MODELS["deep"]

    def test_route_unknown_task_falls_back_to_work_tier(self):
        config = AppConfig(provider=LLMProvider.OLLAMA, ollama_model="llama3.2")
        routed = route("unknown_task_type", config)
        assert routed.ollama_model == DEFAULT_TIER_MODELS["work"]

    def test_route_preserves_other_config_fields(self):
        config = AppConfig(
            provider=LLMProvider.OLLAMA,
            ollama_model="llama3.2",
            ollama_base_url="https://my-ollama.example.com",
            output_dir="/tmp/output",
        )
        routed = route("lesson_plan", config)
        assert routed.ollama_base_url == "https://my-ollama.example.com"
        assert routed.output_dir == "/tmp/output"

    def test_teacher_tier_override_via_route(self):
        config = AppConfig(
            provider=LLMProvider.OLLAMA,
            ollama_model="llama3.2",
            tier_models={"fast": "my-custom-fast"},
        )
        routed = route("bellringer", config)
        assert routed.ollama_model == "my-custom-fast"

    def test_legacy_task_models_override_still_works(self):
        """Backward compat: per-task overrides in task_models take precedence."""
        config = AppConfig(
            provider=LLMProvider.OLLAMA,
            ollama_model="llama3.2",
            task_models={"bellringer": "specific-bellringer-model"},
        )
        routed = route("bellringer", config)
        assert routed.ollama_model == "specific-bellringer-model"

    def test_task_models_override_beats_tier_override(self):
        """Per-task override takes precedence over tier override."""
        config = AppConfig(
            provider=LLMProvider.OLLAMA,
            ollama_model="llama3.2",
            tier_models={"fast": "tier-fast-model"},
            task_models={"bellringer": "task-specific-model"},
        )
        routed = route("bellringer", config)
        assert routed.ollama_model == "task-specific-model"
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `.venv/bin/python3 -m pytest tests/test_model_router.py -v -k "not TestLandingPage"`

- [ ] **Step 3: Rewrite model_router.py**

```python
# clawed/model_router.py
"""Tier-based model routing for Claw-ED.

Tasks map to tiers (fast/work/deep). Each tier has a default model.
Teachers configure which model serves each tier via AppConfig.tier_models.

Resolution order for a given task:
  1. config.task_models[task]    — per-task override (legacy, highest priority)
  2. config.tier_models[tier]    — teacher's tier preference
  3. DEFAULT_TIER_MODELS[tier]   — built-in defaults
"""
from __future__ import annotations

from enum import Enum

from clawed.models import AppConfig


class ModelTier(str, Enum):
    """The three model tiers. Fast is cheap, deep is powerful."""

    FAST = "fast"   # Intent detection, quick answers, formatting
    WORK = "work"   # Lesson plans, unit plans, materials, assessments
    DEEP = "deep"   # Persona extraction, evaluation, meta-analysis


# Task → tier mapping. Unknown tasks default to WORK.
TASK_TIERS: dict[str, ModelTier] = {
    # Fast tier — lightweight, <2s responses
    "intent_detection": ModelTier.FAST,
    "quick_answer": ModelTier.FAST,
    "search": ModelTier.FAST,
    "bellringer": ModelTier.FAST,
    "formatting": ModelTier.FAST,

    # Work tier — core generation, 5-30s responses
    "lesson_plan": ModelTier.WORK,
    "unit_plan": ModelTier.WORK,
    "materials": ModelTier.WORK,
    "differentiation": ModelTier.WORK,
    "iep_modification": ModelTier.WORK,
    "assessment": ModelTier.WORK,
    "year_map": ModelTier.WORK,
    "pacing_guide": ModelTier.WORK,
    "curriculum_gaps": ModelTier.WORK,

    # Deep tier — high-stakes analysis, quality matters most
    "persona_extract": ModelTier.DEEP,
    "evaluation": ModelTier.DEEP,
}

# Default model for each tier. Sensible defaults for Ollama Cloud.
DEFAULT_TIER_MODELS: dict[str, str] = {
    "fast": "qwen3.5:cloud",
    "work": "minimax-m2.7:cloud",
    "deep": "minimax-m2.7:cloud",
}


def resolve_tier(task_type: str) -> ModelTier:
    """Get the tier for a task. Unknown tasks default to WORK."""
    return TASK_TIERS.get(task_type, ModelTier.WORK)


def resolve_model(tier: ModelTier, config: AppConfig) -> str:
    """Get the model for a tier, respecting teacher overrides."""
    teacher_tiers = config.tier_models or {}
    return teacher_tiers.get(tier.value) or DEFAULT_TIER_MODELS[tier.value]


def route(task_type: str, config: AppConfig) -> AppConfig:
    """Return a config copy with the optimal model for this task type.

    Resolution order:
      1. config.task_models[task]    — per-task override (legacy compat)
      2. config.tier_models[tier]    — teacher's tier preference
      3. DEFAULT_TIER_MODELS[tier]   — built-in defaults
    """
    # Legacy per-task override takes highest priority
    user_task_overrides = config.task_models or {}
    if task_type in user_task_overrides:
        model = user_task_overrides[task_type]
    else:
        tier = resolve_tier(task_type)
        model = resolve_model(tier, config)

    routed = config.model_copy()
    routed.ollama_model = model
    return routed
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `.venv/bin/python3 -m pytest tests/test_model_router.py -v`
Expected: All pass

- [ ] **Step 5: Run full suite**

Run: `.venv/bin/python3 -m pytest tests/ -q --tb=line`
Expected: All 1250+ pass (the `route()` API is unchanged, so all 30+ call sites work)

- [ ] **Step 6: Commit**

```bash
git add clawed/model_router.py tests/test_model_router.py
git commit -m "feat: tier-based model routing (fast/work/deep) for Claw-ED"
```

---

## Task 3: Wire Intent Detection to Fast Tier (Future-Ready)

**Files:**
- Modify: `clawed/gateway.py` — add comment marking where LLM-based intent detection would use fast tier
- No code changes needed — intent detection is currently keyword-based (no LLM cost)

This task is documentation-only. The router currently uses regex patterns, not LLM calls. When we add LLM-based intent detection in the future, it should use `route("intent_detection", config)` to get the fast-tier model.

- [ ] **Step 1: Add a docstring note in gateway._dispatch**

In `clawed/gateway.py`, in the `_dispatch` method, after `parsed = parse_intent(message)`, add:

```python
        # NOTE: parse_intent() is currently keyword/regex-based (zero cost).
        # When upgraded to LLM-based detection, use:
        #   config = route("intent_detection", self.config)
        #   intent = await llm_detect_intent(message, config)
```

- [ ] **Step 2: Commit**

```bash
git add clawed/gateway.py
git commit -m "docs: mark intent detection for future fast-tier LLM routing"
```

---

## Summary

| Task | What | Risk |
|------|------|------|
| 1 | Add `tier_models` to AppConfig | Low — additive field |
| 2 | Rewrite model_router with tier system | Medium — 30+ call sites depend on `route()` API |
| 3 | Document future intent detection routing | None — comment only |

### The Tier System

| Tier | Purpose | Default Model | Example Tasks |
|------|---------|---------------|---------------|
| `fast` | Cheap, quick responses (<2s) | `qwen3.5:cloud` | intent detection, Q&A, bell ringers, search |
| `work` | Core generation (5-30s) | `minimax-m2.7:cloud` | lesson plans, unit plans, materials, assessments |
| `deep` | High-stakes analysis | `minimax-m2.7:cloud` | persona extraction, evaluation |

### Teacher Configuration

```json
{
  "tier_models": {
    "fast": "qwen3.5:cloud",
    "work": "claude-sonnet-4-6",
    "deep": "claude-opus-4-6"
  }
}
```

### Resolution Priority
1. `config.task_models["bellringer"]` — per-task override (legacy, highest priority)
2. `config.tier_models["fast"]` — teacher's tier preference
3. `DEFAULT_TIER_MODELS["fast"]` — built-in default
