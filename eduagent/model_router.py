"""Smart model routing — picks the optimal LLM for each task type.

Lightweight tasks (Q&A, bell ringers, search) go to a fast model.
Heavy tasks (lesson plans, unit plans, materials) go to a strong model.
Teachers can override per-task via AppConfig.task_models.
"""

from __future__ import annotations

from eduagent.models import AppConfig

# Default task → model mapping.
# These are sensible defaults for Ollama Cloud; users can override in config.
TASK_MODELS: dict[str, str] = {
    "quick_answer": "qwen3.5:cloud",
    "lesson_plan": "minimax-m2.7:cloud",
    "unit_plan": "minimax-m2.7:cloud",
    "materials": "minimax-m2.7:cloud",
    "persona_extract": "qwen3.5:cloud",
    "search": "qwen3.5:cloud",
    "bellringer": "qwen3.5:cloud",
    "differentiation": "minimax-m2.7:cloud",
    "iep_modification": "minimax-m2.7:cloud",
    "assessment": "minimax-m2.7:cloud",
}


def route(task_type: str, config: AppConfig) -> AppConfig:
    """Return a config copy with the optimal model for this task type.

    Lookup order:
      1. config.task_models (user overrides)
      2. TASK_MODELS (built-in defaults)
      3. config.ollama_model (unchanged fallback)
    """
    user_overrides = config.task_models or {}
    model = user_overrides.get(task_type) or TASK_MODELS.get(task_type) or config.ollama_model
    routed = config.model_copy()
    routed.ollama_model = model
    return routed
