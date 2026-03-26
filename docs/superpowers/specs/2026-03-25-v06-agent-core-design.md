# Claw-ED — Agent Core Architecture Spec

**Date:** 2026-03-25 (revised 2026-03-26)
**Status:** Implemented (v0.6-v0.9 shipped)
**Goal:** Agent-first teaching partner with cognitive memory, Google Drive integration, proactive scheduling, autonomy progression, and closed feedback loop.

---

## Vision (Full — multi-milestone)

A teacher types `pip install clawed && clawed` and gets a colleague — an AI that knows their lessons, their style, their schedule, their standards, and them. It plans, generates, differentiates, publishes to Drive, collects feedback, and improves. It anticipates needs and acts with approval. It gets better every week.

## Implementation Status

| Feature | Version | Status |
|---------|---------|--------|
| Agent gateway with control-plane pre-router | v0.6 | Shipped |
| Typed tool registry (22 tools, auto-discovery) | v0.6 | Shipped |
| Approval gate with persistence and resumption | v0.6 | Shipped |
| Feature-flagged rollout with compatibility shim | v0.6 | Shipped |
| FakeLLM test harness | v0.6 | Shipped |
| 3-layer cognitive memory (identity, curriculum, episodic) | v0.7 | Shipped |
| TF-IDF embedding search with ONNX upgrade path | v0.7 | Shipped |
| Google Drive auth (OAuth, token persistence) | v0.7 | Shipped |
| Drive tools (upload, list, organize) | v0.7 | Shipped |
| Proactive scheduling daemon | v0.8 | Shipped |
| Custom teacher YAML tools | v0.8 | Shipped |
| Multi-step planner | v0.8 | Shipped |
| Native Google Slides/Docs creation | v0.8 | Shipped |
| Drive file reading | v0.8 | Shipped |
| Autonomy progression (approval rate tracking) | v0.9 | Shipped |
| Student insights tool | v0.9 | Shipped |
| Teacher preference learning | v0.9 | Shipped |
| Closed feedback loop | v0.9 | Shipped |

**Remaining for v1.0:** District deployment, admin dashboard, SSO, multi-tenancy, RBAC.

## Target User

Individual teachers using personal accounts. No school IT, no district approval needed.

---

## 1. State Ownership

Before any architectural change, every piece of state has one canonical owner. Memory layers and new systems are **derived indexes/projections** — never sources of truth.

| State | Canonical Owner | Read By |
|-------|----------------|---------|
| Teacher profile (subjects, grades, state, school) | `models.py` → `AppConfig.teacher_profile` → `~/.eduagent/config.json` | Agent context loader, generation, API routes |
| Teacher persona (teaching style, voice, preferences) | `database.py` → `teachers.persona_json` | Agent system prompt, generation tools |
| Teacher name | `database.py` → `teachers.name` (display) + `AppConfig.teacher_profile.name` (config) | Both sources; persona_json takes precedence when available |
| App config (provider, model, API keys, settings) | `models.py` → `AppConfig` → `~/.eduagent/config.json` | Agent core, tools, transports |
| Units and lessons (generated content) | `database.py` → `units`, `lessons` tables | Tools, web routes, export |
| Lesson feedback and ratings | `database.py` → `feedback` table | Agent context, analytics, preference learning |
| Student questions and chat history | `state.py` → `chat_messages`, `student_questions` tables | Student bot, student_insights tool |
| Class codes | `state.py` → `classes` table | Student bot, tools |
| Student enrollments | `database.py` → `student_enrollments` table | Student bot, class management |
| Live conversation state (current session) | `state.py` → `TeacherSession` (in-memory + SQLite) | Agent core, transports |
| Pending approvals | `agent_core/approvals.py` → `~/.eduagent/approvals/` (JSON files) | Agent core, transports, ApprovalTracker |
| Approval rates (per-action-type) | Derived from `~/.eduagent/approvals/*.json` by `ApprovalTracker` | Autonomy progression, system prompt |
| Workspace identity | `~/.eduagent/workspace/identity.md` (file) | Agent system prompt |
| Improvement context (feedback patterns) | `memory_engine.py` → `memory.md` | Agent system prompt |
| Episodic memory (interactions) | `agent_core/memory/episodes.py` → `~/.eduagent/memory/episodes.db` | Agent context loader (semantic recall) |
| Curriculum state | Derived projection from `database.py` → `units`, `lessons` | Agent system prompt |
| Teacher preferences | Derived from feedback + approvals by `agent_core/memory/preferences.py` | Agent system prompt |
| Scheduled tasks | `~/.eduagent/schedule.json` via `scheduler.py` | AgentScheduler, schedule_task tool |
| Custom tools | `~/.eduagent/tools/*.yml` via `agent_core/custom_tools.py` | ToolRegistry (auto-discovered) |

**Note on teacher profile ownership:** The `database.py` `teachers` table has only `id`, `name`, and `persona_json` columns. Structured profile fields (subjects, grades, state, school) live in `AppConfig.teacher_profile` (persisted to `config.json`). This is the current reality — a future migration could consolidate these, but for now both are canonical for their respective scopes.

**Rule:** Tools read from canonical owners. Tools write to canonical owners. The agent core assembles context from canonical sources into the system prompt. Memory layers (episodic, curriculum state, preferences) are derived projections — never primary sources of truth.

---

## 2. Agent Core Architecture

### 2.1 Overview

A new `clawed/agent_core/` package sits behind the existing Gateway contract. Natural-language messages flow through the agent. Deterministic system paths (files, callbacks, setup) stay deterministic.

```
Transport (Telegram, Web, TUI, CLI)
        |
   Gateway (agent_core/core.py)
   +-- Control Plane (pre-router)
   |   +-- File/path ingestion  -> IngestHandler (deterministic)
   |   +-- Callbacks/buttons    -> handle_callback (deterministic)
   |   +-- Onboarding/setup     -> OnboardHandler (deterministic)
   |   +-- Approval responses   -> ApprovalManager (deterministic)
   |
   +-- Agent Loop (natural-language messages only)
   |   +-- Context Loader (teacher profile, persona, recent history)
   |   +-- Tool Executor (call tools, loop until done)
   |   +-- Approval Gate (hold for teacher review when needed)
   |
   +-- Event Bus (TUI dashboard / monitoring)
        |
   GatewayResponse (same interface -- transports unchanged)
```

### 2.2 Control-Plane Pre-Router

Not everything needs the LLM. The control plane handles deterministic paths before the agent loop:

```python
async def handle(self, message: str, teacher_id: str,
                 files: list[Path] | None = None) -> GatewayResponse:

    # 1. File ingestion — deterministic
    if files or _looks_like_path(message):
        return await self._ingest.handle(message, teacher_id, files)

    # 2. Onboarding — deterministic state machine
    if self._onboard.is_onboarding(teacher_id):
        return await self._onboard.step(teacher_id, message)

    # 3. Everything else — agent loop
    return await self._agent_loop(message, teacher_id)
```

```python
async def handle_callback(self, callback_data: str,
                          teacher_id: str) -> GatewayResponse:

    # 1. Approval responses — deterministic
    if callback_data.startswith(("approve:", "reject:")):
        return await self._approval_manager.handle(callback_data, teacher_id)

    # 2. Known action callbacks (export, rate, etc.) — deterministic
    if ":" in callback_data:
        action, payload = callback_data.split(":", 1)
        if action in self._callback_handlers:
            return await self._callback_handlers[action](payload, teacher_id)

    # 3. Unknown callbacks — route to agent
    return await self._agent_loop(f"[callback] {callback_data}", teacher_id)
```

**Why:** Onboarding must be a reliable state machine, not an LLM improvisation. File ingestion is a deterministic I/O operation. Approval responses need guaranteed routing. These paths don't benefit from agent reasoning and must never be broken by LLM flakiness.

### 2.3 Agent Loop

For natural-language messages, the agent runs a tool-use loop. This **migrates** the existing logic from `agent.py` (provider-specific tool-calling protocols for Anthropic, OpenAI, Ollama) into the new core — not a rewrite.

**Flow:**

1. Load teacher context from canonical sources (AppConfig.teacher_profile, persona_json from DB, session history, memory layers)
2. Assemble system prompt with context + tool definitions
3. Send to LLM with tool-use enabled
4. Execute tool-use loop (safety limit: 20 iterations)
5. Return GatewayResponse
6. Log interaction to conversation history

### 2.4 System Prompt Architecture

```
[Role] You are Claw-ED, a professional AI teaching partner for {teacher_name}.
[Identity] {from AppConfig.teacher_profile: subjects, grades, state + from persona_json: teaching style}
[Recent Context] {from state.py: recent conversation turns, what was generated recently}
[Improvement Context] {from memory_engine: feedback patterns, what works for this teacher}
[Tools] {auto-generated from tool registry}
[Guidelines] {approval policies, behavioral preferences}
```

**Context loading** (as shipped in v0.9) reads from all canonical sources: `AppConfig.teacher_profile` for structured profile, `persona_json` from the DB, `memory_engine.py` for improvement context, 3-layer cognitive memory (identity, curriculum, episodic), teacher preferences from feedback/approvals, and autonomy summaries from the ApprovalTracker.

### 2.5 Full Gateway Interface

```python
@dataclass
class AgentContext:
    """Passed to every tool — the agent's working state."""
    teacher_id: str
    config: AppConfig
    teacher_profile: dict      # from database.py canonical source
    persona: dict | None       # from database.py canonical source
    session_history: list[dict]  # current conversation turns
    improvement_context: str   # from memory_engine (existing)

@dataclass
class ToolResult:
    """What a tool returns to the agent."""
    text: str = ""
    files: list[Path] = field(default_factory=list)
    data: dict = field(default_factory=dict)
    side_effects: list[str] = field(default_factory=list)

class Gateway:
    """Agent-first gateway with control-plane pre-router."""

    async def handle(self, message: str, teacher_id: str,
                     files: list[Path] | None = None) -> GatewayResponse

    async def handle_callback(self, callback_data: str,
                              teacher_id: str) -> GatewayResponse

    async def handle_system_event(self, event_type: str,
                                  teacher_id: str,
                                  payload: dict) -> GatewayResponse:
        """Structured entrypoint for scheduled tasks, system triggers, etc.
        Not a synthetic chat message — a typed event with explicit semantics."""

    async def emit(self, event_type: str, data: dict) -> None

    @property
    def event_bus(self) -> asyncio.Queue

    @property
    def active_sessions(self) -> dict[str, dict]

    def stats(self) -> GatewayStats
```

### 2.6 Error Handling & Fallback

**LLM API down:** Fall back to non-agentic mode. Use `generation.py` directly for known request patterns. Display: "I'm having trouble thinking right now, but I can still generate lessons. What do you need?"

**Tool exception:** Catch, report to agent as tool result ("Tool X failed: reason"), let agent decide to retry or report. Never crash the loop.

**20-iteration safety limit:** Return partial results with: "I've been working on this for a while. Here's what I have so far — want me to continue?"

**Malformed LLM response:** Log, retry once, fall back to plain text.

### 2.7 Model Routing

Agent loop runs on the configured provider's primary model. When tools invoke generation (lesson, unit, materials), they internally use `model_router.route()` for tier-based model selection. Agent doesn't know about tiers.

---

## 3. Tool System

### 3.1 Tool Registry

Auto-discovered from `agent_core/tools/`. One file per tool.

```
agent_core/tools/
+-- registry.py            # discovers + registers all tools
+-- base.py                # Tool protocol: schema() + execute()
+-- generate_lesson.py     # wraps lesson.py/generation.py directly (bypasses ParsedIntent)
+-- generate_unit.py       # wraps planner.py (unit planning)
+-- generate_materials.py  # wraps materials.py
+-- generate_assessment.py
+-- search_standards.py    # wraps standards.py
+-- ingest_materials.py    # wraps ingestor.py
+-- export_document.py     # wraps export_pptx/docx/pdf
+-- configure_profile.py   # wraps profile/persona logic
+-- request_approval.py    # approval gate (see Section 4)
+-- search_lessons.py      # query lesson history from database.py
+-- curriculum_map.py      # wraps curriculum_map.py
+-- gap_analysis.py        # wraps gaps handler logic
+-- sub_packet.py          # wraps sub_packet.py
+-- parent_comm.py         # wraps parent_comm.py
```

### 3.2 Tool Protocol

```python
class Tool(Protocol):
    def schema(self) -> dict:
        """JSON schema the LLM sees — name, description, parameters."""
        ...

    async def execute(self, params: dict, context: AgentContext) -> ToolResult:
        """Execute the tool."""
        ...
```

### 3.3 Key Design Rules

- **Tools are thin wrappers.** Call lower-level functions directly (same pattern as existing `tools.py` which bypasses `ParsedIntent`). No reimplementation.
- **Auto-discovery.** Adding a capability = adding one file. No registration boilerplate.
- **`AgentContext`** passed to every tool. Tools read state from canonical owners (database, config) — they don't maintain their own state stores.
- **`ToolResult`** carries text, files, data (for chaining), and side_effects (for logging).

---

## 4. Approval Gate

### 4.1 Persistence Model

```python
@dataclass
class PendingApproval:
    """Stored in ~/.eduagent/approvals/{id}.json while awaiting response."""
    id: str                    # UUID
    teacher_id: str
    created_at: str            # ISO timestamp
    action_description: str    # human-readable
    action_payload: dict       # serialized tool calls to execute on approval
    agent_state: dict          # conversation history for resumption
    transport: str             # which transport to deliver to
    timeout_hours: int = 48
    status: str = "pending"    # pending | approved | rejected | expired
```

### 4.2 Flow

1. Agent calls `request_approval` tool with action description + payload
2. Tool creates `PendingApproval`, persists to `~/.eduagent/approvals/{id}.json`
3. Teacher sees: "I'd like to [action]. Approve? [Yes] [No] [Edit first]"
4. Teacher responds (seconds or hours later)
5. Control plane receives callback `approve:{id}` or `reject:{id}` — deterministic handling, no LLM needed
6. `ApprovalManager` loads the PendingApproval, resumes agent with stored state
7. Approved: execute stored payload. Rejected: acknowledge and move on.
8. No response within `timeout_hours`: expire, notify on next interaction

**Transport rendering:** Telegram → inline keyboard. Web/TUI → action buttons. CLI → prompt.

---

## 5. Rollout Strategy

### 5.1 Feature Flag

```python
# In AppConfig (models.py)
agent_gateway: bool = False  # default OFF — old gateway behavior
```

Enabled by setting `"agent_gateway": true` in `~/.eduagent/config.json` (edit the file directly or set it via Python: `AppConfig.load()` → set field → `.save()`).

**Not yet implemented:** env var `CLAWED_AGENT_GATEWAY=1` is documented but `AppConfig.load()` does not currently read it — the flag only works via `config.json`. A CLI command (`clawed config set-agent-gateway`) and env var support are future enhancements.

**Flag OFF:** Old `gateway.py` handles everything. Zero behavior change.
**Flag ON:** New `agent_core.Gateway` handles everything. Old gateway not loaded.

The flag allows instant rollback if the new gateway has issues. Remove the flag and the old code once v0.6 is stable.

### 5.2 Compatibility Shim

During migration, `clawed/gateway.py` becomes:

```python
from clawed.models import AppConfig

def Gateway(*args, **kwargs):
    cfg = AppConfig.load()
    if cfg.agent_gateway:
        from clawed.agent_core.core import Gateway as AgentGateway
        return AgentGateway(*args, **kwargs)
    from clawed._legacy_gateway import LegacyGateway
    return LegacyGateway(*args, **kwargs)
```

Transports don't change their imports at all. The shim routes to old or new based on the flag.

### 5.3 Fake-LLM Test Harness

A `FakeLLM` class for deterministic testing of the agent loop:

```python
class FakeLLM:
    """Deterministic LLM responses for testing agent behavior."""

    def __init__(self, responses: list[dict]):
        """Each response is a dict with 'text' and/or 'tool_calls'."""
        self._responses = iter(responses)

    async def generate(self, messages, tools=None):
        return next(self._responses)
```

**Required test coverage before flag can be enabled:**

| Test Category | What |
|---------------|------|
| Tool schema validation | Every tool's `schema()` produces valid JSON Schema |
| Tool execution | Every tool's `execute()` returns valid `ToolResult` against existing test data |
| Approval persistence | Create, persist, load, resume, expire |
| Control-plane routing | Files → ingest (not agent). Callbacks → handler (not agent). Onboarding → state machine (not agent). |
| Agent loop basics | FakeLLM → tool call → tool result → response. Multi-turn. Error recovery. Safety limit. |
| Transport compat: Telegram | `handle_callback()` for button presses, inline keyboards |
| Transport compat: Web | `/api/gateway/chat` endpoint works with new core |
| Transport compat: CLI | `run_chat()` works with new core |
| Transport compat: TUI | Stats, event_bus, session tracking |
| Fallback | LLM down → direct generation. Tool failure → agent recovery. |
| Flag OFF parity | Old gateway behavior unchanged when flag is off |

### 5.4 Migration Sequence

1. Rename current `gateway.py` → `_legacy_gateway.py`
2. Create new `gateway.py` as the feature-flag shim (Section 5.2)
3. Build `agent_core/` alongside — core, tools, approval manager
4. Build fake-LLM test harness, write all tests from Section 5.3
5. All tests pass with flag OFF (old behavior) AND flag ON (new behavior)
6. Ship with flag OFF by default
7. Enable flag, validate in real use
8. Once stable: delete `_legacy_gateway.py`, `router.py`, `handlers/`, old `agent.py`, old `tools.py`

---

## 6. Migration Details

### 6.1 What Gets Renamed/Replaced

| File(s) | Action |
|---------|--------|
| `gateway.py` | Renamed to `_legacy_gateway.py`. New `gateway.py` is the feature-flag shim. |
| `router.py` | Kept (used by legacy gateway). Deleted after flag removal. |
| `agent.py` | Tool-use loop logic **migrated** into `agent_core/core.py`. Provider-specific protocols preserved. |
| `handlers/*.py` | Logic migrates into `agent_core/tools/`. Kept until flag removal. |
| `tools.py` | Replaced by `agent_core/tools/`. Kept until flag removal. |

### 6.2 What Stays Untouched

| File(s) | Reason |
|---------|--------|
| `generation.py` | Crown jewel. Tools wrap it. |
| `llm.py` | Agent core calls it. Remove `inject_workspace_context()` calls (agent core handles context injection). |
| `models.py` | Pydantic schemas stable. Add `agent_gateway` flag. |
| `export_*.py` | Become tool executors. |
| `standards.py`, `state_standards.py` | Become tool executors. |
| `student_bot.py` | Stays as-is. |
| `transports/*.py` | No changes — shim handles routing. |
| `database.py`, `state.py` | Canonical data layer. Unchanged. |
| `memory_engine.py` | Stays for v0.6. Agent reads its output. Replaced in v0.7. |
| `onboarding.py` | Control plane routes to it. Unchanged. |
| `cli.py`, `commands/*.py` | CLI stays. |
| `model_router.py` | Tools use internally. |
| `scheduler.py` | Stays as-is for v0.6. Replaced in v0.8. |

### 6.3 Web API Routes

FastAPI routes in `clawed/api/routes/` that bypass the Gateway (e.g., `routes/generate.py`) are **preserved**. The web dashboard continues to work unchanged. These routes can migrate to the agent gateway endpoint in a later milestone.

---

## 7. Remaining Work (v1.0 — District Deployment)

Everything below is NOT yet implemented.

- Multi-tenancy with per-teacher data isolation (migrate from SQLite to PostgreSQL or add tenant_id)
- RBAC — role-based access control with admin/teacher/student roles enforced in routes
- SSO integration (Google Workspace for Education, Clever, ClassLink)
- Admin dashboard — school-level analytics, teacher roster, content moderation
- Audit logging — who did what, when, to which resource
- FERPA/COPPA posture — data retention policies, consent flows
- Hosted deployment path — Docker/Kubernetes with proper secrets management

---

## 8. Success Criteria (v0.9 — Current)

The agent-first individual teacher experience is complete when:

- **Agent handles natural-language messages** — teacher chats naturally, agent calls the right tools (22 tools available)
- **Deterministic paths stay deterministic** — file ingestion, onboarding, callbacks bypass the agent
- **Approval gate works end-to-end** — agent pauses, persists, resumes after teacher approval
- **Memory persists across sessions** — 3-layer cognitive memory (identity, curriculum, episodic)
- **Drive integration works** — OAuth, upload, list, organize, native Slides/Docs, read
- **Proactive scheduling fires** — scheduled tasks route through `handle_system_event()`
- **Custom tools work** — teacher defines YAML prompt-template tools, agent discovers them
- **Autonomy progression** — approval rates tracked, auto-approval offered at 95%+
- **Closed loop completes** — feedback from session N influences session N+1 generation
- **Student insights feed back** — confusion topics from student questions inform reteaching
- **Feature flag works** — flag OFF = legacy behavior, flag ON = agent behavior
- **1337 tests pass** — full suite green with FakeLLM harness, no regressions
