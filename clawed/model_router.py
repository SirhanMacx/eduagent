"""Tier-based model routing for Claw-ED.

Tasks map to tiers (fast/work/deep). Each tier has a default model.
Teachers configure which model serves each tier via AppConfig.tier_models.

Resolution order for a given task:
  1. config.task_models[task]    -- per-task override (legacy, highest priority)
  2. config.tier_models[tier]    -- teacher's tier preference
  3. DEFAULT_TIER_MODELS[tier]   -- built-in defaults
"""
from __future__ import annotations

from enum import Enum

from clawed.models import AppConfig


class ModelTier(str, Enum):
    """The three model tiers. Fast is cheap, deep is powerful."""

    FAST = "fast"
    WORK = "work"
    DEEP = "deep"


TASK_TIERS: dict[str, ModelTier] = {
    # Fast tier
    "intent_detection": ModelTier.FAST,
    "quick_answer": ModelTier.FAST,
    "search": ModelTier.FAST,
    "bellringer": ModelTier.FAST,
    "formatting": ModelTier.FAST,

    # Deep tier — maximum intelligence for everything that matters
    "lesson_plan": ModelTier.DEEP,
    "unit_plan": ModelTier.DEEP,
    "materials": ModelTier.DEEP,
    "differentiation": ModelTier.DEEP,
    "iep_modification": ModelTier.DEEP,
    "assessment": ModelTier.DEEP,
    "year_map": ModelTier.DEEP,
    "pacing_guide": ModelTier.DEEP,
    "curriculum_gaps": ModelTier.DEEP,
    "persona_extract": ModelTier.DEEP,
    "evaluation": ModelTier.DEEP,
    "master_content": ModelTier.DEEP,
    "game_generate": ModelTier.DEEP,
    "simulation_generate": ModelTier.DEEP,
    "multi_agent": ModelTier.DEEP,
}

DEFAULT_TIER_MODELS: dict[str, str] = {
    "fast": "qwen3.5:cloud",
    "work": "minimax-m2.7:cloud",
    "deep": "minimax-m2.7:cloud",
}

# Per-provider tier defaults (used when the teacher selects a provider).
PROVIDER_TIER_MODELS: dict[str, dict[str, str]] = {
    "ollama": DEFAULT_TIER_MODELS,
    "anthropic": {
        "fast": "claude-opus-4-20250514",
        "work": "claude-opus-4-20250514",
        "deep": "claude-opus-4-20250514",
    },
    "openai": {
        "fast": "gpt-4o-mini",
        "work": "gpt-4o",
        "deep": "gpt-4o",
    },
    "google": {
        "fast": "gemini-2.5-flash",
        "work": "gemini-2.5-flash",
        "deep": "gemini-2.5-pro",
    },
}


def resolve_tier(task_type: str) -> ModelTier:
    """Get the tier for a task. Unknown tasks default to WORK."""
    return TASK_TIERS.get(task_type, ModelTier.DEEP)


def resolve_model(tier: ModelTier, config: AppConfig) -> str:
    """Get the model for a tier, respecting teacher overrides and provider."""
    teacher_tiers = config.tier_models or {}
    if teacher_tiers.get(tier.value):
        return teacher_tiers[tier.value]
    # Use provider-specific defaults if available
    provider_key = config.provider.value if hasattr(config.provider, "value") else str(config.provider)
    provider_defaults = PROVIDER_TIER_MODELS.get(provider_key, DEFAULT_TIER_MODELS)
    return provider_defaults.get(tier.value, DEFAULT_TIER_MODELS[tier.value])


def route(task_type: str, config: AppConfig) -> AppConfig:
    """Return a config copy with the optimal model for this task type.

    Resolution order:
      1. config.task_models[task]    -- per-task override (legacy compat)
      2. config.tier_models[tier]    -- teacher's tier preference
      3. DEFAULT_TIER_MODELS[tier]   -- built-in defaults
    """
    user_task_overrides = config.task_models or {}
    if task_type in user_task_overrides:
        model = user_task_overrides[task_type]
    else:
        tier = resolve_tier(task_type)
        model = resolve_model(tier, config)

    routed = config.model_copy()

    # Write to the correct provider-specific model field
    from clawed.models import LLMProvider
    _provider_model_fields = {
        LLMProvider.ANTHROPIC: "anthropic_model",
        LLMProvider.OPENAI: "openai_model",
        LLMProvider.OLLAMA: "ollama_model",
        LLMProvider.GOOGLE: "google_model",
        LLMProvider.OPENROUTER: "openrouter_model",
    }
    field = _provider_model_fields.get(routed.provider, "ollama_model")
    setattr(routed, field, model)
    return routed
