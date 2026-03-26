# v0.6 Agent Gateway Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put the existing agent loop behind the Gateway contract with a typed tool registry, approval gate, control-plane pre-router, and feature-flagged rollout.

**Architecture:** New `clawed/agent_core/` package alongside existing code. Feature flag in `AppConfig` toggles between legacy gateway and new agent gateway. Control plane pre-routes deterministic paths (files, callbacks, onboarding) before handing natural-language messages to the agent loop. Tools are thin wrappers around existing generation/export/standards functions.

**Tech Stack:** Python 3.10+, pytest, pytest-asyncio. No new dependencies — reuses existing `llm.py`, `generation.py`, `models.py`.

**Spec:** `docs/superpowers/specs/2026-03-25-v06-agent-core-design.md`

---

## File Map

### New Files

| File | Responsibility |
|------|---------------|
| `clawed/agent_core/__init__.py` | Package init, exports Gateway |
| `clawed/agent_core/core.py` | New Gateway class: control plane + agent loop |
| `clawed/agent_core/context.py` | `AgentContext`, `ToolResult` dataclasses |
| `clawed/agent_core/loop.py` | Agent tool-use loop (migrated from `agent.py`) |
| `clawed/agent_core/prompt.py` | System prompt assembly from canonical sources |
| `clawed/agent_core/approvals.py` | `PendingApproval` model + `ApprovalManager` |
| `clawed/agent_core/tools/__init__.py` | Package init |
| `clawed/agent_core/tools/base.py` | `Tool` protocol + `ToolRegistry` |
| `clawed/agent_core/tools/generate_lesson.py` | Wraps `clawed.lesson.generate_lesson` |
| `clawed/agent_core/tools/generate_unit.py` | Wraps `clawed.planner` |
| `clawed/agent_core/tools/generate_materials.py` | Wraps `clawed.materials` |
| `clawed/agent_core/tools/generate_assessment.py` | Wraps generation for quizzes |
| `clawed/agent_core/tools/search_standards.py` | Wraps `clawed.standards` |
| `clawed/agent_core/tools/ingest_materials.py` | Wraps `clawed.ingestor` |
| `clawed/agent_core/tools/export_document.py` | Wraps export_pptx/docx/pdf |
| `clawed/agent_core/tools/configure_profile.py` | Wraps profile/persona save |
| `clawed/agent_core/tools/request_approval.py` | Approval gate tool |
| `clawed/agent_core/tools/search_lessons.py` | Queries database for lesson history |
| `clawed/agent_core/tools/curriculum_map.py` | Wraps curriculum_map.py |
| `clawed/agent_core/tools/gap_analysis.py` | Wraps gaps handler |
| `clawed/agent_core/tools/sub_packet.py` | Wraps sub_packet.py |
| `clawed/agent_core/tools/parent_comm.py` | Wraps parent_comm.py |
| `clawed/agent_core/fake_llm.py` | FakeLLM test harness |
| `clawed/_legacy_gateway.py` | Renamed from current `gateway.py` |
| `tests/test_agent_core.py` | Core gateway + control plane tests |
| `tests/test_tool_registry.py` | Tool protocol + registry tests |
| `tests/test_approvals.py` | Approval persistence tests |
| `tests/test_agent_loop.py` | Agent loop with FakeLLM tests |
| `tests/test_feature_flag.py` | Flag ON/OFF parity tests |

### Modified Files

| File | Change |
|------|--------|
| `clawed/gateway.py` | Rewritten as feature-flag shim |
| `clawed/models.py` | Add `agent_gateway: bool = False` field to `AppConfig` |

---

## Task 1: Data Types — AgentContext and ToolResult

**Files:**
- Create: `clawed/agent_core/__init__.py`
- Create: `clawed/agent_core/context.py`
- Test: `tests/test_agent_core.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_agent_core.py
"""Tests for agent_core data types."""
from pathlib import Path

from clawed.agent_core.context import AgentContext, ToolResult


class TestToolResult:
    def test_defaults(self):
        r = ToolResult()
        assert r.text == ""
        assert r.files == []
        assert r.data == {}
        assert r.side_effects == []

    def test_with_values(self):
        r = ToolResult(text="done", files=[Path("/tmp/a.pdf")], side_effects=["created file"])
        assert r.text == "done"
        assert len(r.files) == 1
        assert r.side_effects == ["created file"]


class TestAgentContext:
    def test_construction(self):
        from clawed.models import AppConfig
        ctx = AgentContext(
            teacher_id="t1",
            config=AppConfig(),
            teacher_profile={"name": "Ms. Smith"},
            persona=None,
            session_history=[],
            improvement_context="",
        )
        assert ctx.teacher_id == "t1"
        assert ctx.teacher_profile["name"] == "Ms. Smith"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python3 -m pytest tests/test_agent_core.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'clawed.agent_core'`

- [ ] **Step 3: Write the implementation**

```python
# clawed/agent_core/__init__.py
"""Claw-ED Agent Core — agent-first gateway with typed tools."""
```

```python
# clawed/agent_core/context.py
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


@dataclass
class ToolResult:
    """What a tool returns to the agent."""
    text: str = ""
    files: list[Path] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    side_effects: list[str] = field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python3 -m pytest tests/test_agent_core.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Lint**

Run: `.venv/bin/ruff check clawed/agent_core/`

- [ ] **Step 6: Commit**

```bash
git add clawed/agent_core/__init__.py clawed/agent_core/context.py tests/test_agent_core.py
git commit -m "feat(agent_core): add AgentContext and ToolResult data types"
```

---

## Task 2: Tool Protocol and Registry

**Files:**
- Create: `clawed/agent_core/tools/__init__.py`
- Create: `clawed/agent_core/tools/base.py`
- Test: `tests/test_tool_registry.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_tool_registry.py
"""Tests for the tool protocol and registry."""
import pytest

from clawed.agent_core.context import AgentContext, ToolResult
from clawed.agent_core.tools.base import Tool, ToolRegistry


class _DummyTool:
    """A minimal tool for testing the registry."""
    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "dummy",
                "description": "A test tool",
                "parameters": {"type": "object", "properties": {}},
            },
        }

    async def execute(self, params: dict, context: AgentContext) -> ToolResult:
        return ToolResult(text="dummy result")


class TestToolRegistry:
    def test_register_and_list(self):
        reg = ToolRegistry()
        reg.register(_DummyTool())
        names = reg.tool_names()
        assert "dummy" in names

    def test_get_tool(self):
        reg = ToolRegistry()
        tool = _DummyTool()
        reg.register(tool)
        assert reg.get("dummy") is tool

    def test_get_unknown_returns_none(self):
        reg = ToolRegistry()
        assert reg.get("nonexistent") is None

    def test_schemas(self):
        reg = ToolRegistry()
        reg.register(_DummyTool())
        schemas = reg.schemas()
        assert len(schemas) == 1
        assert schemas[0]["function"]["name"] == "dummy"

    @pytest.mark.asyncio
    async def test_execute(self):
        from clawed.models import AppConfig
        reg = ToolRegistry()
        reg.register(_DummyTool())
        ctx = AgentContext(
            teacher_id="t1", config=AppConfig(),
            teacher_profile={}, persona=None,
            session_history=[], improvement_context="",
        )
        result = await reg.execute("dummy", {}, ctx)
        assert result.text == "dummy result"

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self):
        from clawed.models import AppConfig
        reg = ToolRegistry()
        ctx = AgentContext(
            teacher_id="t1", config=AppConfig(),
            teacher_profile={}, persona=None,
            session_history=[], improvement_context="",
        )
        result = await reg.execute("nonexistent", {}, ctx)
        assert "Unknown tool" in result.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python3 -m pytest tests/test_tool_registry.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# clawed/agent_core/tools/__init__.py
"""Agent core tools — auto-discovered tool registry."""
```

```python
# clawed/agent_core/tools/base.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python3 -m pytest tests/test_tool_registry.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Lint and commit**

```bash
.venv/bin/ruff check clawed/agent_core/tools/
git add clawed/agent_core/tools/ tests/test_tool_registry.py
git commit -m "feat(agent_core): add Tool protocol and ToolRegistry"
```

---

## Task 3: FakeLLM Test Harness

**Files:**
- Create: `clawed/agent_core/fake_llm.py`
- Test: `tests/test_agent_loop.py` (partial — just FakeLLM tests here)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_agent_loop.py
"""Tests for the agent loop with FakeLLM."""
import pytest

from clawed.agent_core.fake_llm import FakeLLM


class TestFakeLLM:
    @pytest.mark.asyncio
    async def test_text_response(self):
        llm = FakeLLM([{"type": "text", "content": "Hello!"}])
        resp = await llm.generate(messages=[], tools=None, system="")
        assert resp["type"] == "text"
        assert resp["content"] == "Hello!"

    @pytest.mark.asyncio
    async def test_tool_call_response(self):
        llm = FakeLLM([{
            "type": "tool_calls",
            "tool_calls": [{"id": "1", "name": "generate_lesson", "arguments": {"topic": "fractions"}}],
        }])
        resp = await llm.generate(messages=[], tools=None, system="")
        assert resp["type"] == "tool_calls"
        assert resp["tool_calls"][0]["name"] == "generate_lesson"

    @pytest.mark.asyncio
    async def test_sequence(self):
        llm = FakeLLM([
            {"type": "tool_calls", "tool_calls": [{"id": "1", "name": "search_standards", "arguments": {}}]},
            {"type": "text", "content": "Found standards."},
        ])
        r1 = await llm.generate(messages=[], tools=None, system="")
        assert r1["type"] == "tool_calls"
        r2 = await llm.generate(messages=[], tools=None, system="")
        assert r2["type"] == "text"

    @pytest.mark.asyncio
    async def test_exhausted_raises(self):
        llm = FakeLLM([{"type": "text", "content": "only one"}])
        await llm.generate(messages=[], tools=None, system="")
        with pytest.raises(StopIteration):
            await llm.generate(messages=[], tools=None, system="")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python3 -m pytest tests/test_agent_loop.py::TestFakeLLM -v`
Expected: FAIL

- [ ] **Step 3: Write the implementation**

```python
# clawed/agent_core/fake_llm.py
"""Fake LLM for deterministic testing of the agent loop.

Usage:
    llm = FakeLLM([
        {"type": "tool_calls", "tool_calls": [{"id": "1", "name": "search_standards", "arguments": {}}]},
        {"type": "text", "content": "Here are the standards."},
    ])
    response = await llm.generate(messages, tools, system)
"""
from __future__ import annotations

from typing import Any


class FakeLLM:
    """Deterministic LLM responses for testing agent behavior."""

    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self._responses = iter(responses)

    async def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        system: str = "",
    ) -> dict[str, Any]:
        """Return the next scripted response."""
        return next(self._responses)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python3 -m pytest tests/test_agent_loop.py::TestFakeLLM -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add clawed/agent_core/fake_llm.py tests/test_agent_loop.py
git commit -m "feat(agent_core): add FakeLLM test harness"
```

---

## Task 4: Approval Gate — PendingApproval + ApprovalManager

**Files:**
- Create: `clawed/agent_core/approvals.py`
- Test: `tests/test_approvals.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_approvals.py
"""Tests for the approval gate persistence and lifecycle."""
import json
import time

import pytest

from clawed.agent_core.approvals import ApprovalManager, PendingApproval


class TestPendingApproval:
    def test_to_json_roundtrip(self):
        pa = PendingApproval(
            teacher_id="t1",
            action_description="Upload 5 lessons to Drive",
            action_payload={"tool": "drive_upload", "args": {"path": "/lessons"}},
            agent_state={"history": [{"role": "user", "content": "prep my week"}]},
            transport="telegram",
        )
        data = pa.to_dict()
        loaded = PendingApproval.from_dict(data)
        assert loaded.id == pa.id
        assert loaded.teacher_id == "t1"
        assert loaded.status == "pending"
        assert loaded.action_payload["tool"] == "drive_upload"

    def test_auto_generates_id(self):
        pa = PendingApproval(
            teacher_id="t1", action_description="test",
            action_payload={}, agent_state={}, transport="cli",
        )
        assert len(pa.id) > 0


class TestApprovalManager:
    def test_create_and_load(self, tmp_path):
        mgr = ApprovalManager(base_dir=tmp_path)
        pa = mgr.create(
            teacher_id="t1",
            action_description="Upload lessons",
            action_payload={"tool": "upload"},
            agent_state={"history": []},
            transport="telegram",
        )
        loaded = mgr.load(pa.id)
        assert loaded is not None
        assert loaded.action_description == "Upload lessons"

    def test_approve(self, tmp_path):
        mgr = ApprovalManager(base_dir=tmp_path)
        pa = mgr.create(
            teacher_id="t1", action_description="test",
            action_payload={}, agent_state={}, transport="cli",
        )
        mgr.approve(pa.id)
        loaded = mgr.load(pa.id)
        assert loaded.status == "approved"

    def test_reject(self, tmp_path):
        mgr = ApprovalManager(base_dir=tmp_path)
        pa = mgr.create(
            teacher_id="t1", action_description="test",
            action_payload={}, agent_state={}, transport="cli",
        )
        mgr.reject(pa.id)
        loaded = mgr.load(pa.id)
        assert loaded.status == "rejected"

    def test_load_nonexistent_returns_none(self, tmp_path):
        mgr = ApprovalManager(base_dir=tmp_path)
        assert mgr.load("nonexistent-id") is None

    def test_pending_for_teacher(self, tmp_path):
        mgr = ApprovalManager(base_dir=tmp_path)
        mgr.create(teacher_id="t1", action_description="a",
                    action_payload={}, agent_state={}, transport="cli")
        mgr.create(teacher_id="t1", action_description="b",
                    action_payload={}, agent_state={}, transport="cli")
        mgr.create(teacher_id="t2", action_description="c",
                    action_payload={}, agent_state={}, transport="cli")
        pending = mgr.pending_for_teacher("t1")
        assert len(pending) == 2

    def test_expire_old(self, tmp_path):
        mgr = ApprovalManager(base_dir=tmp_path)
        pa = mgr.create(
            teacher_id="t1", action_description="old",
            action_payload={}, agent_state={}, transport="cli",
            timeout_hours=0,  # expires immediately
        )
        expired = mgr.expire_old()
        assert len(expired) >= 1
        loaded = mgr.load(pa.id)
        assert loaded.status == "expired"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python3 -m pytest tests/test_approvals.py -v`
Expected: FAIL

- [ ] **Step 3: Write the implementation**

```python
# clawed/agent_core/approvals.py
"""Approval gate — persistence and lifecycle for pending teacher approvals."""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_DIR = Path.home() / ".eduagent" / "approvals"


@dataclass
class PendingApproval:
    """A pending approval awaiting teacher response."""
    teacher_id: str
    action_description: str
    action_payload: dict[str, Any]
    agent_state: dict[str, Any]
    transport: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    timeout_hours: int = 48
    status: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "teacher_id": self.teacher_id,
            "created_at": self.created_at,
            "action_description": self.action_description,
            "action_payload": self.action_payload,
            "agent_state": self.agent_state,
            "transport": self.transport,
            "timeout_hours": self.timeout_hours,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PendingApproval:
        return cls(
            id=data["id"],
            teacher_id=data["teacher_id"],
            created_at=data["created_at"],
            action_description=data["action_description"],
            action_payload=data["action_payload"],
            agent_state=data["agent_state"],
            transport=data["transport"],
            timeout_hours=data.get("timeout_hours", 48),
            status=data.get("status", "pending"),
        )


class ApprovalManager:
    """Manages PendingApproval lifecycle — create, persist, load, resolve."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._dir = base_dir or _DEFAULT_DIR
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, approval_id: str) -> Path:
        return self._dir / f"{approval_id}.json"

    def create(self, *, teacher_id: str, action_description: str,
               action_payload: dict, agent_state: dict,
               transport: str, timeout_hours: int = 48) -> PendingApproval:
        pa = PendingApproval(
            teacher_id=teacher_id,
            action_description=action_description,
            action_payload=action_payload,
            agent_state=agent_state,
            transport=transport,
            timeout_hours=timeout_hours,
        )
        self._save(pa)
        return pa

    def load(self, approval_id: str) -> PendingApproval | None:
        path = self._path(approval_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return PendingApproval.from_dict(data)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to load approval %s: %s", approval_id, e)
            return None

    def approve(self, approval_id: str) -> PendingApproval | None:
        return self._update_status(approval_id, "approved")

    def reject(self, approval_id: str) -> PendingApproval | None:
        return self._update_status(approval_id, "rejected")

    def pending_for_teacher(self, teacher_id: str) -> list[PendingApproval]:
        results = []
        for path in self._dir.glob("*.json"):
            pa = self.load(path.stem)
            if pa and pa.teacher_id == teacher_id and pa.status == "pending":
                results.append(pa)
        return results

    def expire_old(self) -> list[PendingApproval]:
        expired = []
        now = datetime.now()
        for path in self._dir.glob("*.json"):
            pa = self.load(path.stem)
            if pa and pa.status == "pending":
                created = datetime.fromisoformat(pa.created_at)
                if now - created > timedelta(hours=pa.timeout_hours):
                    self._update_status(pa.id, "expired")
                    pa.status = "expired"
                    expired.append(pa)
        return expired

    def _update_status(self, approval_id: str, status: str) -> PendingApproval | None:
        pa = self.load(approval_id)
        if pa is None:
            return None
        pa.status = status
        self._save(pa)
        return pa

    def _save(self, pa: PendingApproval) -> None:
        path = self._path(pa.id)
        path.write_text(json.dumps(pa.to_dict(), indent=2), encoding="utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python3 -m pytest tests/test_approvals.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add clawed/agent_core/approvals.py tests/test_approvals.py
git commit -m "feat(agent_core): add approval gate with persistence and lifecycle"
```

---

## Task 5: System Prompt Assembly

**Files:**
- Create: `clawed/agent_core/prompt.py`
- Test: Add to `tests/test_agent_core.py`

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_agent_core.py

class TestPromptAssembly:
    def test_builds_prompt_with_teacher_name(self):
        from clawed.agent_core.prompt import build_system_prompt
        prompt = build_system_prompt(
            teacher_name="Ms. Smith",
            identity_summary="8th grade Science, inquiry-based",
            improvement_context="Students struggle with graphs",
            tool_names=["generate_lesson", "search_standards"],
        )
        assert "Ms. Smith" in prompt
        assert "inquiry-based" in prompt
        assert "graphs" in prompt

    def test_builds_prompt_without_improvement_context(self):
        from clawed.agent_core.prompt import build_system_prompt
        prompt = build_system_prompt(
            teacher_name="Teacher",
            identity_summary="",
            improvement_context="",
            tool_names=[],
        )
        assert "Claw-ED" in prompt
        assert "Teacher" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python3 -m pytest tests/test_agent_core.py::TestPromptAssembly -v`
Expected: FAIL

- [ ] **Step 3: Write the implementation**

```python
# clawed/agent_core/prompt.py
"""System prompt assembly for the agent core.

Reads from canonical sources (database, workspace, memory_engine)
and builds a dynamic system prompt per interaction.
"""
from __future__ import annotations


def build_system_prompt(
    *,
    teacher_name: str,
    identity_summary: str,
    improvement_context: str,
    tool_names: list[str],
) -> str:
    """Assemble the agent's system prompt from canonical context."""
    sections = [
        f"You are Claw-ED, a professional AI teaching partner for {teacher_name}.",
        "You help teachers plan lessons, generate materials, find standards, "
        "and manage their classroom. You are warm, knowledgeable, and proactive.",
        "",
        "When the teacher asks you to do something, use your tools. "
        "Do not describe what you would do — actually do it by calling the appropriate tool.",
    ]

    if identity_summary:
        sections.append(f"\n## About This Teacher\n{identity_summary}")

    if improvement_context:
        sections.append(f"\n## What Works for This Teacher\n{improvement_context}")

    if tool_names:
        sections.append(
            f"\n## Available Tools\n"
            f"You have {len(tool_names)} tools: {', '.join(tool_names)}. "
            f"Use them to take action rather than just suggesting."
        )

    sections.append(
        "\n## Guidelines\n"
        "- Ask ONE question at a time, keep responses concise (2-3 sentences)\n"
        "- When generating content, call the tool immediately — don't ask for confirmation first\n"
        "- For consequential actions (publishing, sharing), use the request_approval tool\n"
        "- If you can't help with something, say so honestly"
    )

    return "\n".join(sections)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python3 -m pytest tests/test_agent_core.py::TestPromptAssembly -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add clawed/agent_core/prompt.py tests/test_agent_core.py
git commit -m "feat(agent_core): add system prompt assembly from canonical sources"
```

---

## Task 6: Agent Loop (migrated from agent.py)

**Files:**
- Create: `clawed/agent_core/loop.py`
- Test: Extend `tests/test_agent_loop.py`

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_agent_loop.py

from clawed.agent_core.context import AgentContext, ToolResult
from clawed.agent_core.fake_llm import FakeLLM
from clawed.agent_core.loop import run_agent_loop
from clawed.agent_core.tools.base import ToolRegistry
from clawed.models import AppConfig


class _EchoTool:
    def schema(self):
        return {"type": "function", "function": {
            "name": "echo", "description": "Echo back",
            "parameters": {"type": "object", "properties": {
                "text": {"type": "string"},
            }},
        }}

    async def execute(self, params, context):
        return ToolResult(text=f"echoed: {params.get('text', '')}")


def _make_ctx():
    return AgentContext(
        teacher_id="t1", config=AppConfig(),
        teacher_profile={}, persona=None,
        session_history=[], improvement_context="",
    )


class TestAgentLoop:
    @pytest.mark.asyncio
    async def test_text_only_response(self):
        llm = FakeLLM([{"type": "text", "content": "Hello teacher!"}])
        reg = ToolRegistry()
        result = await run_agent_loop(
            message="hi", system="You are helpful.", context=_make_ctx(),
            llm=llm, registry=reg,
        )
        assert result.text == "Hello teacher!"

    @pytest.mark.asyncio
    async def test_tool_call_then_text(self):
        llm = FakeLLM([
            {"type": "tool_calls", "tool_calls": [
                {"id": "1", "name": "echo", "arguments": {"text": "hello"}},
            ]},
            {"type": "text", "content": "I echoed hello for you."},
        ])
        reg = ToolRegistry()
        reg.register(_EchoTool())
        result = await run_agent_loop(
            message="echo hello", system="", context=_make_ctx(),
            llm=llm, registry=reg,
        )
        assert result.text == "I echoed hello for you."

    @pytest.mark.asyncio
    async def test_safety_limit(self):
        """Agent hits iteration limit when LLM keeps calling tools forever."""
        infinite_tools = [
            {"type": "tool_calls", "tool_calls": [
                {"id": str(i), "name": "echo", "arguments": {"text": "loop"}},
            ]}
            for i in range(25)
        ]
        llm = FakeLLM(infinite_tools)
        reg = ToolRegistry()
        reg.register(_EchoTool())
        result = await run_agent_loop(
            message="loop", system="", context=_make_ctx(),
            llm=llm, registry=reg, max_iterations=20,
        )
        assert "iteration" in result.text.lower() or "working" in result.text.lower()

    @pytest.mark.asyncio
    async def test_unknown_tool_handled(self):
        llm = FakeLLM([
            {"type": "tool_calls", "tool_calls": [
                {"id": "1", "name": "nonexistent_tool", "arguments": {}},
            ]},
            {"type": "text", "content": "Sorry, I couldn't do that."},
        ])
        reg = ToolRegistry()
        result = await run_agent_loop(
            message="do something", system="", context=_make_ctx(),
            llm=llm, registry=reg,
        )
        assert result.text == "Sorry, I couldn't do that."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python3 -m pytest tests/test_agent_loop.py::TestAgentLoop -v`
Expected: FAIL

- [ ] **Step 3: Write the implementation**

```python
# clawed/agent_core/loop.py
"""Agent tool-use loop — the core reasoning engine.

Migrated from clawed/agent.py. Supports Anthropic, OpenAI, and Ollama
tool-calling protocols via the injected LLM interface.
"""
from __future__ import annotations

import logging
from typing import Any, Protocol

from clawed.agent_core.context import AgentContext, ToolResult
from clawed.agent_core.tools.base import ToolRegistry
from clawed.gateway_response import GatewayResponse

logger = logging.getLogger(__name__)

_DEFAULT_MAX_ITERATIONS = 20


class LLMInterface(Protocol):
    """What the loop needs from an LLM — generate() with tool support."""
    async def generate(
        self, messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        system: str = "",
    ) -> dict[str, Any]: ...


async def run_agent_loop(
    *,
    message: str,
    system: str,
    context: AgentContext,
    llm: LLMInterface,
    registry: ToolRegistry,
    max_iterations: int = _DEFAULT_MAX_ITERATIONS,
    conversation_history: list[dict[str, Any]] | None = None,
) -> GatewayResponse:
    """Run the agent tool-use loop until completion or safety limit.

    Returns a GatewayResponse with the agent's final text and any files
    produced by tools.
    """
    messages: list[dict[str, Any]] = list(conversation_history or [])
    messages.append({"role": "user", "content": message})

    all_files = []
    all_side_effects = []
    tool_schemas = registry.schemas() or None

    for iteration in range(max_iterations):
        response = await llm.generate(messages=messages, tools=tool_schemas, system=system)

        if response["type"] == "text":
            return GatewayResponse(text=response["content"], files=all_files)

        if response["type"] == "tool_calls":
            tool_calls = response["tool_calls"]

            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": tool_calls,
            })

            for tc in tool_calls:
                name = tc["name"]
                args = tc.get("arguments", {})
                logger.info("Agent calling tool: %s(%s)", name, args)

                result = await registry.execute(name, args, context)

                all_files.extend(result.files)
                all_side_effects.extend(result.side_effects)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", name),
                    "content": result.text or result.data or "",
                })
            continue

    return GatewayResponse(
        text="I've been working on this for a while. Here's what I have so far — want me to continue?",
        files=all_files,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python3 -m pytest tests/test_agent_loop.py -v`
Expected: PASS (all 8 tests — 4 FakeLLM + 4 AgentLoop)

- [ ] **Step 5: Commit**

```bash
git add clawed/agent_core/loop.py tests/test_agent_loop.py
git commit -m "feat(agent_core): add agent tool-use loop with safety limit"
```

---

## Task 7: First Tool — generate_lesson

**Files:**
- Create: `clawed/agent_core/tools/generate_lesson.py`
- Test: Extend `tests/test_tool_registry.py`

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_tool_registry.py

class TestGenerateLessonTool:
    def test_schema_valid(self):
        from clawed.agent_core.tools.generate_lesson import GenerateLessonTool
        tool = GenerateLessonTool()
        s = tool.schema()
        assert s["function"]["name"] == "generate_lesson"
        assert "topic" in s["function"]["parameters"]["properties"]

    @pytest.mark.asyncio
    async def test_execute_returns_tool_result(self):
        """Verify the tool returns a ToolResult (may fail on LLM call — we patch it)."""
        from unittest.mock import AsyncMock, patch
        from clawed.agent_core.tools.generate_lesson import GenerateLessonTool
        from clawed.models import AppConfig

        tool = GenerateLessonTool()
        ctx = AgentContext(
            teacher_id="t1", config=AppConfig(),
            teacher_profile={}, persona=None,
            session_history=[], improvement_context="",
        )
        # Patch the underlying lesson generator to avoid real LLM calls
        with patch("clawed.agent_core.tools.generate_lesson.generate_lesson", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = type("Lesson", (), {"model_dump": lambda self: {"title": "Fractions", "sections": []}})()
            result = await tool.execute({"topic": "fractions"}, ctx)
        assert isinstance(result, ToolResult)
        assert "Fractions" in result.text or "fractions" in result.text.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python3 -m pytest tests/test_tool_registry.py::TestGenerateLessonTool -v`
Expected: FAIL

- [ ] **Step 3: Write the implementation**

```python
# clawed/agent_core/tools/generate_lesson.py
"""Tool: generate_lesson — wraps clawed.lesson.generate_lesson."""
from __future__ import annotations

import json
from typing import Any

from clawed.agent_core.context import AgentContext, ToolResult


class GenerateLessonTool:
    """Generate a complete daily lesson plan on a topic."""

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "generate_lesson",
                "description": "Generate a complete daily lesson plan on a topic. "
                    "Returns a structured lesson with Do Now, instruction, activities, "
                    "exit ticket, and differentiation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "description": "The lesson topic"},
                        "grade": {"type": "string", "description": "Grade level (e.g. '8', 'K')", "default": "8"},
                        "subject": {"type": "string", "description": "Subject area", "default": "General"},
                    },
                    "required": ["topic"],
                },
            },
        }

    async def execute(self, params: dict[str, Any], context: AgentContext) -> ToolResult:
        from clawed.lesson import generate_lesson
        from clawed.models import AppConfig, LessonBrief, TeacherPersona, UnitPlan

        topic = params["topic"]
        grade = params.get("grade", "8")
        subject = params.get("subject", "General")

        config = context.config
        persona = None
        if context.persona:
            try:
                persona = TeacherPersona(**context.persona)
            except Exception:
                persona = TeacherPersona()

        unit = UnitPlan(
            title=f"{topic} Unit", subject=subject, grade_level=grade, topic=topic,
            duration_weeks=1, overview=f"A lesson on {topic}.",
            daily_lessons=[LessonBrief(lesson_number=1, topic=topic, description=f"Introduction to {topic}")],
        )

        try:
            lesson = await generate_lesson(
                lesson_number=1,
                unit=unit,
                persona=persona or TeacherPersona(),
                config=config,
            )
            lesson_data = lesson.model_dump()
            title = lesson_data.get("title", topic)
            return ToolResult(
                text=f"Generated lesson: {title}\n\n{json.dumps(lesson_data, indent=2)[:2000]}",
                data=lesson_data,
                side_effects=[f"Generated lesson on {topic}"],
            )
        except Exception as e:
            return ToolResult(text=f"Failed to generate lesson: {e}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python3 -m pytest tests/test_tool_registry.py::TestGenerateLessonTool -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add clawed/agent_core/tools/generate_lesson.py tests/test_tool_registry.py
git commit -m "feat(agent_core): add generate_lesson tool wrapping existing pipeline"
```

---

## Task 8: Remaining Tools (batch — same pattern as Task 7)

**Files:**
- Create: All remaining tool files listed in spec Section 3.1
- Test: Add schema validation for each to `tests/test_tool_registry.py`

Each tool follows the exact same pattern as `generate_lesson.py`: thin wrapper calling existing lower-level functions. For each tool: implement, write schema validation test AND a mocked execute test (patch the underlying function to avoid real LLM calls, verify `ToolResult` is returned), commit.

**Important:** Check the actual function signature of each wrapped function before writing the tool. The existing `tools.py` `execute_tool()` function (lines 215-242) shows which lower-level functions to call and their parameter names. Use those as reference, not the handler layer.

- [ ] **Step 1: Create `generate_unit.py`** wrapping `clawed.planner`. Test schema + mocked execute. Commit.
- [ ] **Step 2: Create `generate_materials.py`** wrapping `clawed.materials`. Test schema + mocked execute. Commit.
- [ ] **Step 3: Create `generate_assessment.py`** wrapping quiz generation. Test schema + mocked execute. Commit.
- [ ] **Step 4: Create `search_standards.py`** wrapping `clawed.standards`. Test schema + mocked execute. Commit.
- [ ] **Step 5: Create `ingest_materials.py`** wrapping `clawed.ingestor`. Test schema + mocked execute. Commit.
- [ ] **Step 6: Create `export_document.py`** wrapping export_pptx/docx/pdf. Test schema + mocked execute. Commit.
- [ ] **Step 7: Create `configure_profile.py`** wrapping profile/persona save. Test schema + mocked execute. Commit.
- [ ] **Step 8: Create `request_approval.py`** using `ApprovalManager`. Test schema + execute (no mock needed — uses ApprovalManager directly). Commit.
- [ ] **Step 9: Create `search_lessons.py`** querying `database.py`. Test schema + mocked execute. Commit.
- [ ] **Step 10: Create `curriculum_map.py`** wrapping curriculum_map. Test schema + mocked execute. Commit.
- [ ] **Step 11: Create `gap_analysis.py`** wrapping gaps handler. Test schema + mocked execute. Commit.
- [ ] **Step 12: Create `sub_packet.py`** wrapping sub_packet. Test schema + mocked execute. Commit.
- [ ] **Step 13: Create `parent_comm.py`** wrapping parent_comm. Test schema + mocked execute. Commit.
- [ ] **Step 14: Add auto-discovery to `ToolRegistry`** — add `ToolRegistry.discover(package_path)` method that scans a directory for modules containing classes ending in `Tool` that implement the `Tool` protocol. Wrap imports in try/except to skip broken modules with a warning. Test: discovery finds all 15 built-in tools. Commit.

---

## Task 9: Feature Flag + Gateway Shim

**Files:**
- Modify: `clawed/models.py` — add `agent_gateway` field
- Rename: `clawed/gateway.py` → `clawed/_legacy_gateway.py`
- Create: `clawed/gateway.py` (shim)
- Test: `tests/test_feature_flag.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_feature_flag.py
"""Tests for feature flag routing between legacy and agent gateway."""
import pytest

from clawed.models import AppConfig


class TestFeatureFlag:
    def test_flag_defaults_to_false(self):
        cfg = AppConfig()
        assert cfg.agent_gateway is False

    def test_legacy_gateway_when_flag_off(self):
        from clawed.gateway import Gateway
        gw = Gateway(config=AppConfig(agent_gateway=False))
        assert gw.__class__.__module__ == "clawed._legacy_gateway"

    def test_shim_reexports_compat_names(self):
        from clawed.gateway import EduAgentGateway, ActivityEvent, GatewayStats
        assert EduAgentGateway is not None
        assert ActivityEvent is not None
        assert GatewayStats is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python3 -m pytest tests/test_feature_flag.py -v`
Expected: FAIL

- [ ] **Step 3: Add flag to AppConfig**

In `clawed/models.py`, add to the `AppConfig` class (near other bool fields):

```python
agent_gateway: bool = False
```

- [ ] **Step 4: Rename gateway.py**

```bash
git mv clawed/gateway.py clawed/_legacy_gateway.py
```

- [ ] **Step 5: Write the shim**

```python
# clawed/gateway.py
"""Feature-flag shim — routes to legacy or agent gateway.

Re-exports all public names from the legacy gateway so existing
imports (EduAgentGateway, ActivityEvent, GatewayStats) keep working.
"""
from __future__ import annotations

from clawed._legacy_gateway import (  # noqa: F401 — re-exports
    ActivityEvent,
    GatewayStats,
)
from clawed.models import AppConfig


def Gateway(*args, **kwargs):
    """Factory that returns the appropriate Gateway based on config."""
    config = kwargs.get("config") or (args[0] if args else None)
    if config is None:
        config = AppConfig.load()

    if getattr(config, "agent_gateway", False):
        from clawed.agent_core.core import Gateway as AgentGateway
        return AgentGateway(config=config)

    from clawed._legacy_gateway import Gateway as LegacyGateway
    return LegacyGateway(config=config)


# Backward compatibility alias
EduAgentGateway = Gateway
```

- [ ] **Step 6: Fix imports in _legacy_gateway.py**

The renamed file needs no changes — all its internal imports are absolute (`from clawed.config import ...`).

- [ ] **Step 7: Run full test suite with flag OFF**

Run: `.venv/bin/python3 -m pytest tests/ -q --tb=short`
Expected: All 1208+ tests PASS (legacy behavior unchanged)

- [ ] **Step 8: Commit**

```bash
git add clawed/models.py clawed/gateway.py clawed/_legacy_gateway.py tests/test_feature_flag.py
git commit -m "feat: add feature flag shim for agent gateway rollout"
```

---

## Task 10: Agent Core Gateway — the new core.py

**Files:**
- Create: `clawed/agent_core/core.py`
- Test: Add to `tests/test_agent_core.py`

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_agent_core.py

class TestAgentGateway:
    @pytest.mark.asyncio
    async def test_handle_returns_gateway_response(self):
        from clawed.agent_core.core import Gateway as AgentGateway
        from clawed.models import AppConfig

        gw = AgentGateway(config=AppConfig(agent_gateway=True))
        # Patch the agent loop to avoid real LLM calls
        from unittest.mock import AsyncMock, patch
        from clawed.gateway_response import GatewayResponse
        with patch.object(gw, "_agent_loop", new_callable=AsyncMock) as mock_loop:
            mock_loop.return_value = GatewayResponse(text="Hello!")
            result = await gw.handle("hi", "t1")
        assert result.text == "Hello!"

    @pytest.mark.asyncio
    async def test_file_routes_to_ingest(self):
        from pathlib import Path
        from clawed.agent_core.core import Gateway as AgentGateway
        from clawed.models import AppConfig
        from unittest.mock import AsyncMock, patch
        from clawed.gateway_response import GatewayResponse

        gw = AgentGateway(config=AppConfig(agent_gateway=True))
        with patch.object(gw, "_ingest_handler", new_callable=AsyncMock) as mock_ingest:
            mock_ingest.return_value = GatewayResponse(text="Ingested!")
            result = await gw.handle("hi", "t1", files=[Path("/tmp/test.pdf")])
        mock_ingest.assert_called_once()

    @pytest.mark.asyncio
    async def test_callback_routes_approval(self):
        from clawed.agent_core.core import Gateway as AgentGateway
        from clawed.models import AppConfig
        from unittest.mock import AsyncMock, patch
        from clawed.gateway_response import GatewayResponse

        gw = AgentGateway(config=AppConfig(agent_gateway=True))
        with patch.object(gw._approval_manager, "load", return_value=None):
            result = await gw.handle_callback("approve:abc123", "t1")
        # Should handle gracefully even if approval not found
        assert result.text  # some response text

    def test_has_event_bus(self):
        from clawed.agent_core.core import Gateway as AgentGateway
        from clawed.models import AppConfig
        gw = AgentGateway(config=AppConfig(agent_gateway=True))
        assert gw.event_bus is not None

    @pytest.mark.asyncio
    async def test_has_stats(self):
        from clawed.agent_core.core import Gateway as AgentGateway
        from clawed.models import AppConfig
        gw = AgentGateway(config=AppConfig(agent_gateway=True))
        s = await gw.stats()
        assert "messages_today" in s

    def test_has_backward_compat_methods(self):
        from clawed.agent_core.core import Gateway as AgentGateway
        from clawed.models import AppConfig
        gw = AgentGateway(config=AppConfig(agent_gateway=True))
        assert hasattr(gw, "process_message")
        assert hasattr(gw, "start")
        assert hasattr(gw, "stop")
        assert hasattr(gw, "handle_system_event")

    def test_feature_flag_on_routes_here(self):
        """Moved from Task 9 — requires core.py to exist."""
        from clawed.gateway import Gateway
        from clawed.models import AppConfig
        gw = Gateway(config=AppConfig(agent_gateway=True))
        assert gw.__class__.__module__ == "clawed.agent_core.core"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python3 -m pytest tests/test_agent_core.py::TestAgentGateway -v`
Expected: FAIL

- [ ] **Step 3: Write the implementation**

Build `clawed/agent_core/core.py` — the new Gateway. This is the largest single file. Follow the spec Section 2.2 pattern exactly.

**Constructor:**
```python
def __init__(self, config: AppConfig | None = None):
    self.config = config or AppConfig.load()
    self.event_bus: asyncio.Queue = asyncio.Queue(maxsize=500)
    self.active_sessions: dict[str, dict] = {}
    self._stats = GatewayStats()
    self._running = False

    # Control-plane handlers (reuse existing)
    from clawed.handlers.ingest import IngestHandler
    from clawed.handlers.onboard import OnboardHandler
    self._ingest = IngestHandler()
    self._onboard = OnboardHandler()

    # Agent subsystems
    self._approval_manager = ApprovalManager()
    self._registry = ToolRegistry()
    self._registry.discover(Path(__file__).parent / "tools")

    # Callback handlers (deterministic — migrated from legacy gateway)
    from clawed.handlers.export import ExportHandler
    from clawed.handlers.feedback import FeedbackHandler
    self._export = ExportHandler()
    self._feedback = FeedbackHandler()
    self._callback_handlers = {
        "rate": self._handle_rate_callback,
        "action": self._handle_action_callback,
    }
```

**Context loading in `_agent_loop()` — reads from canonical sources:**
```python
async def _agent_loop(self, message: str, teacher_id: str) -> GatewayResponse:
    from clawed.database import Database
    from clawed.memory_engine import build_improvement_context
    from clawed.state import TeacherSession

    # Load from canonical sources
    db = Database()
    teacher = db.get_default_teacher()
    persona_data = None
    if teacher and teacher.get("persona_json"):
        import json
        persona_data = json.loads(teacher["persona_json"])

    session = TeacherSession.load(teacher_id)
    improvement_ctx = build_improvement_context(teacher_id)

    context = AgentContext(
        teacher_id=teacher_id,
        config=self.config,
        teacher_profile=dict(teacher) if teacher else {},
        persona=persona_data,
        session_history=session.history if hasattr(session, 'history') else [],
        improvement_context=improvement_ctx or "",
    )

    system = build_system_prompt(
        teacher_name=persona_data.get("name", "Teacher") if persona_data else "Teacher",
        identity_summary=...,  # build from persona_data
        improvement_context=context.improvement_context,
        tool_names=self._registry.tool_names(),
    )

    # Create real LLM adapter or use injected one (for testing)
    llm = self._llm or _create_llm_adapter(self.config)

    return await run_agent_loop(
        message=message, system=system, context=context,
        llm=llm, registry=self._registry,
    )
```

**Backward-compat methods (must be present for existing callers):**
```python
async def process_message(self, text: str, teacher_id: str = "cli",
                          teacher_name: str = "Teacher") -> str:
    """Backward-compatible: process message and return text string."""
    r = await self.handle(text, teacher_id)
    return r.text

async def start(self) -> None:
    """Backward-compatible start."""
    self._running = True
    await self.emit("system", {"message": "Gateway started"})

async def stop(self) -> None:
    """Shut down the gateway."""
    self._running = False
    await self.emit("system", {"message": "Gateway stopped"})

async def handle_system_event(self, event_type: str, teacher_id: str,
                               payload: dict) -> GatewayResponse:
    """Structured entrypoint for scheduled tasks and system triggers.
    Not a synthetic chat message — a typed event. Placeholder for v0.8 scheduler."""
    return GatewayResponse(text=f"System event '{event_type}' received (not yet handled).")
```

**`stats()` — keep as async for backward compat with existing callers that `await` it:**
```python
async def stats(self) -> dict:
    s = self._stats
    return {
        "messages_today": s.messages_today,
        "generations_today": s.generations_today,
        "errors_today": s.errors_today,
        "uptime_seconds": s.uptime_seconds,
        "active_sessions": len(self.active_sessions),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python3 -m pytest tests/test_agent_core.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Run full suite with flag ON**

Run: `CLAWED_AGENT_GATEWAY=1 .venv/bin/python3 -m pytest tests/ -q --tb=short`
Expected: Most tests pass. Some gateway-specific tests may need adaptation.

- [ ] **Step 6: Commit**

```bash
git add clawed/agent_core/core.py tests/test_agent_core.py
git commit -m "feat(agent_core): add Gateway with control plane and agent loop"
```

---

## Task 11: Integration Test — Full Flag ON/OFF Parity

**Files:**
- Test: `tests/test_feature_flag.py` (extend)

- [ ] **Step 1: Write integration tests**

Test that with flag OFF, all existing behavior is preserved. Test that with flag ON, basic chat + tool calling works through the full stack.

- [ ] **Step 2: Run full suite both ways**

```bash
.venv/bin/python3 -m pytest tests/ -q --tb=short          # flag OFF
CLAWED_AGENT_GATEWAY=1 .venv/bin/python3 -m pytest tests/ -q --tb=short  # flag ON
```

- [ ] **Step 3: Fix any failures, commit**

```bash
git add -A
git commit -m "test: integration tests for feature flag ON/OFF parity"
```

---

## Task 12: Final Lint + Full Suite + Push

- [ ] **Step 1: Lint everything**

Run: `.venv/bin/ruff check clawed/agent_core/ tests/test_agent_core.py tests/test_tool_registry.py tests/test_approvals.py tests/test_agent_loop.py tests/test_feature_flag.py`

- [ ] **Step 2: Full test suite**

Run: `.venv/bin/python3 -m pytest tests/ -q --tb=short`
Expected: All tests pass, zero regressions

- [ ] **Step 3: Push**

```bash
git push
```
