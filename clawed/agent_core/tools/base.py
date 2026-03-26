"""Tool protocol and registry for the agent core."""
from __future__ import annotations

import logging
from typing import Any, Protocol, runtime_checkable

from clawed.agent_core.context import AgentContext, ToolResult

logger = logging.getLogger(__name__)


@runtime_checkable
class Tool(Protocol):
    """Protocol that all agent tools must implement."""

    def schema(self) -> dict[str, Any]:
        """Return the JSON Schema definition the LLM sees."""
        ...

    async def execute(self, params: dict[str, Any], context: AgentContext) -> ToolResult:
        """Execute the tool and return a result."""
        ...


class ToolRegistry:
    """Discovers, registers, and dispatches tools."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool instance. Name extracted from schema."""
        name = tool.schema()["function"]["name"]
        self._tools[name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def tool_names(self) -> list[str]:
        return list(self._tools.keys())

    def schemas(self) -> list[dict[str, Any]]:
        return [t.schema() for t in self._tools.values()]

    async def execute(self, name: str, params: dict[str, Any],
                      context: AgentContext) -> ToolResult:
        """Execute a tool by name. Returns error ToolResult for unknown tools."""
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(text=f"Unknown tool: {name}")
        try:
            return await tool.execute(params, context)
        except Exception as e:
            logger.error("Tool %s failed: %s", name, e)
            return ToolResult(text=f"Tool {name} failed: {e}")
