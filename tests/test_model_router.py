"""Tests for the smart model router."""

from eduagent.model_router import TASK_MODELS, route
from eduagent.models import AppConfig, LLMProvider


class TestTaskModelsMapping:
    def test_all_expected_task_types_exist(self):
        expected = [
            "quick_answer", "lesson_plan", "unit_plan", "materials",
            "persona_extract", "search", "bellringer", "differentiation",
        ]
        for task in expected:
            assert task in TASK_MODELS, f"Missing task type: {task}"

    def test_fast_tasks_use_fast_model(self):
        fast_tasks = ["quick_answer", "search", "bellringer", "persona_extract"]
        for task in fast_tasks:
            assert TASK_MODELS[task] == "qwen3.5:cloud"

    def test_strong_tasks_use_strong_model(self):
        strong_tasks = ["lesson_plan", "unit_plan", "materials", "differentiation"]
        for task in strong_tasks:
            assert TASK_MODELS[task] == "minimax-m2.7:cloud"


class TestRouteFunction:
    def test_route_returns_new_config(self):
        config = AppConfig(provider=LLMProvider.OLLAMA, ollama_model="llama3.2")
        routed = route("lesson_plan", config)
        assert routed is not config
        assert routed.ollama_model == "minimax-m2.7:cloud"

    def test_route_does_not_mutate_original(self):
        config = AppConfig(provider=LLMProvider.OLLAMA, ollama_model="llama3.2")
        route("lesson_plan", config)
        assert config.ollama_model == "llama3.2"

    def test_route_fast_task(self):
        config = AppConfig(provider=LLMProvider.OLLAMA, ollama_model="llama3.2")
        routed = route("bellringer", config)
        assert routed.ollama_model == "qwen3.5:cloud"

    def test_route_strong_task(self):
        config = AppConfig(provider=LLMProvider.OLLAMA, ollama_model="llama3.2")
        routed = route("unit_plan", config)
        assert routed.ollama_model == "minimax-m2.7:cloud"

    def test_route_unknown_task_falls_back_to_config_model(self):
        config = AppConfig(provider=LLMProvider.OLLAMA, ollama_model="my-custom-model")
        routed = route("unknown_task_type", config)
        assert routed.ollama_model == "my-custom-model"

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
        assert routed.provider == LLMProvider.OLLAMA

    def test_user_override_takes_precedence(self):
        config = AppConfig(
            provider=LLMProvider.OLLAMA,
            ollama_model="llama3.2",
            task_models={"bellringer": "my-custom-fast:cloud"},
        )
        routed = route("bellringer", config)
        assert routed.ollama_model == "my-custom-fast:cloud"

    def test_user_override_only_affects_specified_task(self):
        config = AppConfig(
            provider=LLMProvider.OLLAMA,
            ollama_model="llama3.2",
            task_models={"bellringer": "my-custom-fast:cloud"},
        )
        routed = route("lesson_plan", config)
        assert routed.ollama_model == "minimax-m2.7:cloud"

    def test_route_with_anthropic_provider(self):
        config = AppConfig(provider=LLMProvider.ANTHROPIC)
        routed = route("quick_answer", config)
        assert routed.ollama_model == "qwen3.5:cloud"
        assert routed.provider == LLMProvider.ANTHROPIC


class TestLandingPage:
    def test_landing_html_exists(self):
        from pathlib import Path
        landing = Path(__file__).parent.parent / "eduagent" / "landing" / "index.html"
        assert landing.exists()

    def test_landing_html_contains_key_content(self):
        from pathlib import Path
        landing = Path(__file__).parent.parent / "eduagent" / "landing" / "index.html"
        html = landing.read_text()
        assert "Your AI co-teacher" in html
        assert "Learns Your Voice" in html
        assert "50-State Standards" in html
        assert "Student Bot" in html
        assert "pip install eduagent" in html
        assert "github.com/SirhanMacx/eduagent" in html

    def test_landing_html_is_self_contained(self):
        from pathlib import Path
        landing = Path(__file__).parent.parent / "eduagent" / "landing" / "index.html"
        html = landing.read_text()
        # Should not link to external CSS/JS (except GitHub link)
        stripped = html.replace('href="https://github.com/SirhanMacx/eduagent"', "")
        assert '<link rel="stylesheet" href="http' not in stripped
        assert "<script src=" not in stripped
