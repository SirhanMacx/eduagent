"""Self-equipping tools — Ed can install deps and create tools for himself."""

from __future__ import annotations

import logging
import subprocess
import sys
from typing import Any

from clawed.agent_core.context import AgentContext, ToolResult

logger = logging.getLogger(__name__)


class InstallPackageTool:
    """Install a Python package that Ed needs."""

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "install_package",
                "description": (
                    "Install a Python package that's needed for a task. "
                    "Only use when a required package is missing. "
                    "Ed checks before importing and installs gracefully."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "package_name": {
                            "type": "string",
                            "description": "PyPI package name (e.g., 'matplotlib', 'pandas')",
                        },
                        "reason": {
                            "type": "string",
                            "description": "Why this package is needed",
                        },
                    },
                    "required": ["package_name"],
                },
            },
        }

    async def execute(
        self, params: dict[str, Any], context: AgentContext
    ) -> ToolResult:
        package = params.get("package_name", "").strip()
        reason = params.get("reason", "")

        if not package:
            return ToolResult(text="ERROR: package_name is required")

        # Safety: block dangerous packages
        blocked = {"os", "sys", "subprocess", "shutil", "pathlib"}
        if package.lower() in blocked:
            return ToolResult(text=f"Cannot install '{package}' — it's a built-in module.")

        # Check if already available
        try:
            __import__(package.replace("-", "_"))
            return ToolResult(text=f"'{package}' is already installed and available.")
        except ImportError:
            pass

        # Install
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--user", package],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0:
                msg = f"Successfully installed '{package}'."
                if reason:
                    msg += f" (Needed for: {reason})"
                logger.info("Self-equip: installed %s", package)
                return ToolResult(text=msg)
            else:
                return ToolResult(text=f"Failed to install '{package}': {result.stderr[:500]}")
        except subprocess.TimeoutExpired:
            return ToolResult(text=f"Installation of '{package}' timed out.")
        except Exception as e:
            return ToolResult(text=f"Installation failed: {e}")


class CreateCustomToolTool:
    """Create a custom YAML-based tool template."""

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "create_custom_tool",
                "description": (
                    "Create a custom tool that Ed can use in future conversations. "
                    "The tool is saved as a YAML template in ~/.eduagent/tools/ "
                    "and automatically loaded on next startup. "
                    "Use when the teacher needs a specialized capability."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tool_name": {
                            "type": "string",
                            "description": "Snake_case name for the tool (e.g., 'vocab_quiz_generator')",
                        },
                        "description": {
                            "type": "string",
                            "description": "What the tool does",
                        },
                        "prompt_template": {
                            "type": "string",
                            "description": "The LLM prompt template for the tool. Use {topic}, {grade}, {subject} as placeholders.",
                        },
                    },
                    "required": ["tool_name", "description", "prompt_template"],
                },
            },
        }

    async def execute(
        self, params: dict[str, Any], context: AgentContext
    ) -> ToolResult:
        import os
        from pathlib import Path

        import yaml

        name = params.get("tool_name", "").strip()
        desc = params.get("description", "").strip()
        template = params.get("prompt_template", "").strip()

        if not all([name, desc, template]):
            return ToolResult(text="ERROR: tool_name, description, and prompt_template are all required")

        # Sanitize name
        import re
        name = re.sub(r"[^a-z0-9_]", "_", name.lower())

        data_dir = os.environ.get("EDUAGENT_DATA_DIR", str(Path.home() / ".eduagent"))
        tools_dir = Path(data_dir) / "tools"
        tools_dir.mkdir(parents=True, exist_ok=True)

        tool_path = tools_dir / f"{name}.yaml"
        tool_data = {
            "name": name,
            "description": desc,
            "prompt_template": template,
            "parameters": {
                "topic": {"type": "string", "description": "The topic", "required": True},
                "grade": {"type": "string", "description": "Grade level"},
                "subject": {"type": "string", "description": "Subject area"},
            },
        }

        tool_path.write_text(yaml.dump(tool_data, default_flow_style=False), encoding="utf-8")
        logger.info("Created custom tool: %s at %s", name, tool_path)

        return ToolResult(
            text=f"Created custom tool '{name}' at {tool_path}.\n"
            f"It will be available on next startup. Description: {desc}"
        )
