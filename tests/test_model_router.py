"""Tests for the tier-based model router."""

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
        config = AppConfig(
            provider=LLMProvider.OLLAMA,
            ollama_model="llama3.2",
            task_models={"bellringer": "specific-bellringer-model"},
        )
        routed = route("bellringer", config)
        assert routed.ollama_model == "specific-bellringer-model"

    def test_task_models_override_beats_tier_override(self):
        config = AppConfig(
            provider=LLMProvider.OLLAMA,
            ollama_model="llama3.2",
            tier_models={"fast": "tier-fast-model"},
            task_models={"bellringer": "task-specific-model"},
        )
        routed = route("bellringer", config)
        assert routed.ollama_model == "task-specific-model"

    def test_route_with_anthropic_provider(self):
        config = AppConfig(provider=LLMProvider.ANTHROPIC)
        routed = route("quick_answer", config)
        assert routed.ollama_model == DEFAULT_TIER_MODELS["fast"]
        assert routed.provider == LLMProvider.ANTHROPIC


class TestLandingPage:
    def test_landing_html_exists(self):
        from pathlib import Path
        landing = Path(__file__).parent.parent / "clawed" / "landing" / "index.html"
        assert landing.exists()

    def test_landing_html_contains_key_content(self):
        from pathlib import Path
        landing = Path(__file__).parent.parent / "clawed" / "landing" / "index.html"
        html = landing.read_text()
        assert "Your AI co-teacher" in html
        assert "Trained on YOUR materials" in html
        assert "50 states" in html or "Standards" in html or "standard" in html.lower()
        assert "11pm" in html
        assert "pip install eduagent" in html
        assert "github.com/SirhanMacx/eduagent" in html

    def test_landing_html_is_self_contained(self):
        from pathlib import Path
        landing = Path(__file__).parent.parent / "clawed" / "landing" / "index.html"
        html = landing.read_text()
        # Should not link to external CSS/JS (except GitHub link)
        stripped = html.replace('href="https://github.com/SirhanMacx/eduagent"', "")
        assert '<link rel="stylesheet" href="http' not in stripped
        assert "<script src=" not in stripped
