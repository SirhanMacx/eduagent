"""Core data types for the agent system."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from clawed.models import AppConfig


@dataclass
class AgentContext:
    """Passed to every tool — the agent's working state."""

    teacher_id: str
    config: AppConfig
    teacher_profile: dict[str, Any]
    persona: dict[str, Any] | None
    session_history: list[dict[str, Any]]
    improvement_context: str
    agent_name: str = "Claw-ED"


@dataclass
class ToolResult:
    """What a tool returns to the agent."""

    text: str = ""
    files: list[Path] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    side_effects: list[str] = field(default_factory=list)
