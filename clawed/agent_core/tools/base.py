"""Tool protocol and registry for the agent core."""
from __future__ import annotations

import importlib
import inspect
import logging
from pathlib import Path
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
            return ToolResult(
                text=f"ERROR: Tool '{name}' failed and did NOT complete. "
                     f"Reason: {e}. "
                     f"Do NOT tell the teacher this action succeeded — it did not. "
                     f"Either retry with corrected parameters or tell the teacher "
                     f"what went wrong."
            )

    def discover_custom(self, dir_path: Path) -> None:
        """Load custom YAML prompt-template tools from a directory."""
        if not dir_path.exists():
            return
        from clawed.agent_core.custom_tools import YAMLPromptTool

        for yaml_file in sorted(dir_path.glob("*.y*ml")):
            tool = YAMLPromptTool.from_file(yaml_file)
            if tool is not None:
                self.register(tool)
                logger.debug("Loaded custom tool: %s", yaml_file.name)

    def discover(self, package_path: Path) -> None:
        """Auto-discover and register tool classes from a package directory.

        Scans ``package_path`` for Python modules, imports each one, and
        registers any class whose name ends with ``Tool`` and that has both
        ``schema()`` and ``execute()`` methods.

        Broken modules are skipped with a warning.
        """
        package_path = Path(package_path)
        # Determine the dotted package name from the path
        # e.g. /…/clawed/agent_core/tools → clawed.agent_core.tools
        parts: list[str] = []
        cur = package_path
        while True:
            init_file = cur / "__init__.py"
            if not init_file.exists():
                break
            parts.insert(0, cur.name)
            cur = cur.parent
        package_name = ".".join(parts) if parts else ""

        for py_file in sorted(package_path.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            module_name = py_file.stem
            fq_name = f"{package_name}.{module_name}" if package_name else module_name
            try:
                mod = importlib.import_module(fq_name)
            except Exception as exc:
                logger.warning("Skipping broken tool module %s: %s", fq_name, exc)
                continue

            for _attr_name, obj in inspect.getmembers(mod, inspect.isclass):
                if (
                    _attr_name.endswith("Tool")
                    and hasattr(obj, "schema")
                    and hasattr(obj, "execute")
                    and obj.__module__ == mod.__name__
                    and not getattr(obj, "_is_protocol", False)
                ):
                    try:
                        instance = obj()
                        self.register(instance)
                        logger.debug("Discovered tool: %s", _attr_name)
                    except Exception as exc:
                        logger.warning(
                            "Failed to instantiate tool %s: %s", _attr_name, exc
                        )
