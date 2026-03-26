# v0.8 Proactive + Extensibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add proactive scheduling (via `handle_system_event()`), custom teacher tools (YAML prompt-template), multi-step planner, native Google Slides/Docs creation, and Drive read for context ingestion.

**Architecture:** Scheduler daemon wires existing `EduScheduler` to the agent gateway via `handle_system_event()`. Custom tools loaded from `~/.eduagent/tools/` as YAML with prompt templates. Planner decomposes multi-step requests into sequential tool calls. Drive tools extended with native format creation and file reading.

**Tech Stack:** Python 3.10+, pytest, pytest-asyncio, APScheduler (already in deps), PyYAML (already in deps).

**Spec:** `docs/superpowers/specs/2026-03-25-v06-agent-core-design.md` Section 7 (v0.8)

---

## File Map

### New Files

| File | Responsibility |
|------|---------------|
| `clawed/agent_core/scheduler.py` | Wires EduScheduler to agent gateway via handle_system_event() |
| `clawed/agent_core/custom_tools.py` | Loads YAML prompt-template tools from ~/.eduagent/tools/ |
| `clawed/agent_core/planner.py` | Multi-step request decomposition |
| `clawed/agent_core/tools/drive_create_slides.py` | Native Google Slides creation |
| `clawed/agent_core/tools/drive_create_doc.py` | Native Google Docs creation |
| `clawed/agent_core/tools/drive_read.py` | Read files from Drive for context |
| `clawed/agent_core/tools/schedule_task.py` | Agent tool to create/manage scheduled tasks |
| `tests/test_scheduler_integration.py` | Scheduler + system event tests |
| `tests/test_custom_tools.py` | YAML tool loading tests |
| `tests/test_planner.py` | Multi-step planner tests |

### Modified Files

| File | Change |
|------|--------|
| `clawed/agent_core/core.py` | Enhance handle_system_event() to route through agent, load custom tools |
| `clawed/agent_core/tools/base.py` | Support loading custom YAML tools alongside Python tools |
| `clawed/commands/bot.py` | Wire scheduler into `clawed serve` |

---

## Task 1: Proactive Scheduler Integration

Wire the existing `EduScheduler` to the agent gateway via `handle_system_event()`.

**Files:**
- Create: `clawed/agent_core/scheduler.py`
- Modify: `clawed/agent_core/core.py` — enhance `handle_system_event()`
- Test: `tests/test_scheduler_integration.py`

Tests: system event routing, task execution through gateway, event types.
Implementation: `AgentScheduler` class wraps `EduScheduler`, calls `gateway.handle_system_event()` when tasks fire. Gateway routes system events to the agent loop with context about what triggered it.

Commit: `feat(scheduler): wire proactive scheduling to agent gateway`

---

## Task 2: Schedule Task Tool

Agent tool to create, list, and manage scheduled tasks.

**Files:**
- Create: `clawed/agent_core/tools/schedule_task.py`
- Test: Append to `tests/test_scheduler_integration.py`

Tests: schema validation, mocked execute for create/list/disable.
Implementation: Wraps `clawed.scheduler` functions (enable_task, disable_task, set_task_schedule, load_schedule_config).

Commit: `feat(scheduler): add schedule_task tool for agent`

---

## Task 3: Custom Teacher Tools (YAML)

Load YAML prompt-template tools from `~/.eduagent/tools/`.

**Files:**
- Create: `clawed/agent_core/custom_tools.py`
- Modify: `clawed/agent_core/tools/base.py` — add `discover_custom()` method
- Modify: `clawed/agent_core/core.py` — call `discover_custom()` in init
- Test: `tests/test_custom_tools.py`

Tests: YAML parsing, schema generation from YAML, execute with prompt template, broken YAML skipped, discovery integration.

YAML format:
```yaml
name: lab_safety_check
description: "Review a lesson for lab safety issues"
parameters:
  lesson_text:
    type: string
    description: "The lesson plan text"
prompt_template: |
  Review this lesson for lab safety: {lesson_text}
```

Implementation: `YAMLPromptTool` class wraps YAML into Tool protocol. Execute sends the filled prompt template to the LLM. `ToolRegistry.discover_custom(dir_path)` scans for `*.yml`/`*.yaml` files.

Commit: `feat(tools): add custom YAML prompt-template tools`

---

## Task 4: Multi-Step Planner

Decompose complex requests into sequential tool calls.

**Files:**
- Create: `clawed/agent_core/planner.py`
- Modify: `clawed/agent_core/loop.py` — support plan-aware execution
- Test: `tests/test_planner.py`

Tests: plan creation from description, plan serialization, plan execution with FakeLLM.

Implementation: The planner is not a separate system — it's a system prompt enhancement. When the agent receives a complex request ("prepare my week"), the system prompt instructs it to call tools sequentially. The planner module provides `build_planning_prompt()` that adds planning instructions to the system prompt when the message looks like a multi-step request.

Commit: `feat(planner): add multi-step request planning`

---

## Task 5: Drive Create Slides + Docs + Read

Extended Drive tools for native format creation and file reading.

**Files:**
- Create: `clawed/agent_core/tools/drive_create_slides.py`
- Create: `clawed/agent_core/tools/drive_create_doc.py`
- Create: `clawed/agent_core/tools/drive_read.py`
- Modify: `clawed/agent_core/drive/client.py` — add create_slides(), create_doc(), read_file()
- Test: Append to `tests/test_drive.py`

Tests: schema validation for all 3 tools, mocked execute, client method signatures.

Commit: `feat(drive): add native Slides/Docs creation and file reading`

---

## Task 6: Wire Scheduler into clawed serve

**Files:**
- Modify: `clawed/commands/bot.py` — start scheduler as async task in serve command when agent_gateway is ON

Tests: verify scheduler starts/stops with serve.

Commit: `feat(serve): start proactive scheduler when agent gateway is enabled`

---

## Task 7: Version Bump + Docs + Push

- Bump to 0.8.0 in pyproject.toml and __init__.py
- Update version assertions in tests
- Update CHANGELOG, README (roadmap, tool count, features), ARCHITECTURE, HANDOFF
- Run full suite, lint, push

Commit: `release: bump to v0.8.0 — proactive scheduling, custom tools, planner`
