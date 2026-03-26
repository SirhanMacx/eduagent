# Claw-ED v0.6 — Agent Core Architecture Design

**Date:** 2026-03-25
**Status:** Draft
**Goal:** Transform Claw-ED from a command-based lesson generator into an agentic teaching partner with cognitive memory, Google Drive integration, and proactive behavior.

---

## Vision

A teacher types `pip install clawed && clawed` and gets a colleague — an AI that knows their lessons, their style, their schedule, their standards, and them. It plans, generates, differentiates, publishes to Drive, collects feedback, and improves. It anticipates needs and acts with approval. It gets better every week.

## Target User

Individual teachers using personal accounts. No school IT, no district approval needed. Grassroots adoption — one teacher tells the next.

---

## 1. Agent Core Architecture

### 1.1 Overview

A new `clawed/agent_core/` package replaces the existing gateway/router/handler pipeline. Every message flows through the agent. No regex intent matching. The LLM decides what to do via tools.

```
Transport (Telegram, Web, TUI, CLI)
        |
   Agent Core
   +-- Memory Engine (load teacher context)
   +-- Planner (decompose multi-step requests)
   +-- Tool Executor (call tools, loop until done)
   +-- Approval Gate (hold for teacher review when needed)
   +-- Memory Writer (persist what happened)
        |
   GatewayResponse (same interface -- transports unchanged)
```

### 1.2 Core Module: `agent_core/core.py`

The brain. Replaces `gateway.py` + `router.py` + `agent.py`.

**Flow:**

1. Receive message + teacher_id from transport
2. Load memory context (identity, curriculum state, relevant episodes)
3. Assemble system prompt with memory context + tool definitions
4. Send to LLM with tool-use enabled
5. Execute tool-use loop (no fixed iteration cap — runs until agent completes or hits safety limit of 20 iterations)
6. Return GatewayResponse to transport
7. Write interaction to episodic memory, update curriculum state

**Full Gateway interface (preserving transport compatibility):**

```python
@dataclass
class AgentContext:
    """Passed to every tool — the agent's working state."""
    teacher_id: str
    config: AppConfig
    identity: dict            # Layer 1 memory snapshot
    curriculum_state: dict    # Layer 2 memory snapshot
    relevant_memories: list[str]  # Layer 3 semantic search results
    session_history: list[dict]   # current conversation turns
    pending_approvals: list[str]  # IDs of approvals awaiting response

@dataclass
class ToolResult:
    """What a tool returns to the agent."""
    text: str = ""
    files: list[Path] = field(default_factory=list)
    data: dict = field(default_factory=dict)          # structured data for chaining
    side_effects: list[str] = field(default_factory=list)  # logged to memory automatically

class Gateway:
    """New agent-first gateway. Same interface as old Gateway for transport compat."""

    async def handle(self, message: str, teacher_id: str,
                     files: list[Path] | None = None) -> GatewayResponse:
        """Primary entry — all messages flow through the agent."""

    async def handle_callback(self, callback_data: str,
                              teacher_id: str) -> GatewayResponse:
        """Button presses from Telegram inline keyboards, web UI actions, etc.
        The agent interprets the callback payload as a structured action.
        Also handles approval gate responses (callback_data prefixed with 'approve:' or 'reject:')."""

    async def emit(self, event_type: str, data: dict) -> None:
        """Event bus for TUI dashboard / monitoring."""

    @property
    def event_bus(self) -> asyncio.Queue:
        """Activity feed — consumed by TUI dashboard."""

    @property
    def active_sessions(self) -> dict[str, dict]:
        """Live session tracking for monitoring."""

    def stats(self) -> GatewayStats:
        """Today's counters + uptime — consumed by TUI StatsBar."""
```

Transports import `clawed.agent_core.Gateway` instead of `clawed.gateway.Gateway`. The old `clawed.gateway` module becomes a thin re-export shim during migration, then gets deleted.

### 1.3 Planner: `agent_core/planner.py`

For multi-step requests ("prepare my week," "create a unit with materials and upload to Drive"), the planner decomposes into a sequence of tool calls with dependencies.

For simple requests ("lesson on fractions"), the agent skips planning and calls the tool directly. The LLM decides whether planning is needed — no hardcoded threshold.

### 1.4 System Prompt Architecture

The agent's system prompt is assembled dynamically per interaction:

```
[Role] You are Claw-ED, a professional AI teaching partner for {teacher_name}.
[Identity] {loaded from identity memory — teaching style, subjects, grades, standards}
[Curriculum State] {what's been taught, what's coming, current week position}
[Relevant Memory] {semantic search results from episodic memory}
[Tools] {auto-generated from tool registry}
[Guidelines] {approval policies, Drive safety, proactive preferences}
```

### 1.5 Error Handling & Fallback Strategy

The agent core must never leave the teacher stranded:

**LLM API down:** Fall back to a non-agentic mode. Use the existing `generation.py` functions directly for known request types (lesson, unit, materials). Display: "I'm having trouble thinking right now, but I can still generate lessons. What do you need?"

**Tool throws an exception:** Catch the error, report it to the agent as a tool result ("Tool X failed: reason"), let the agent decide whether to retry, try a different approach, or report to the teacher. Never crash the loop.

**20-iteration safety limit hit:** Return what the agent has so far with a message: "I've been working on this for a while. Here's what I have so far — want me to continue?"

**Malformed LLM response:** Log it, retry once, then fall back to treating the response as plain text.

### 1.6 Model Routing Within the Agent

The agent loop itself runs on the configured provider's primary model (Anthropic Claude, OpenAI GPT-4, Ollama Cloud). When the agent calls tools that invoke generation (lesson, unit, materials), those tools internally use `model_router.route()` to select the appropriate tier model for the task. The agent doesn't need to know about model routing — tools handle it.

---

## 2. Tool System

### 2.1 Tool Registry

Every capability is a tool. Auto-discovered from `agent_core/tools/` directory + teacher custom tools from `~/.eduagent/tools/`.

**Phase 1 tools (MVP — ship first):**

```
agent_core/tools/
+-- registry.py           # discovers + registers all tools
+-- base.py               # Tool protocol: schema() + execute()
+-- generate_lesson.py    # wraps generation.py (calls lower-level functions directly, not through ParsedIntent)
+-- generate_unit.py      # wraps planner.py (unit planning)
+-- generate_materials.py # wraps materials.py
+-- generate_assessment.py
+-- search_standards.py   # wraps standards.py
+-- ingest_materials.py   # wraps ingestor.py
+-- export_document.py    # wraps export_pptx/docx/pdf
+-- drive_upload.py       # Google Drive upload
+-- drive_list.py         # browse teacher's Drive
+-- drive_organize.py     # create folders, move files
+-- read_memory.py        # query cognitive memory
+-- write_memory.py       # persist observations
+-- configure_profile.py  # save teacher profile
+-- request_approval.py   # pause and ask teacher to approve
+-- search_lessons.py     # query lesson history from DB
```

**Phase 2 tools (after core is stable):**

```
+-- drive_create_slides.py # native Google Slides (complex API)
+-- drive_create_doc.py   # native Google Docs (complex API)
+-- drive_read.py         # read files from Drive for context
+-- schedule_task.py      # create/manage scheduled jobs
+-- curriculum_map.py     # wraps curriculum_map.py
+-- gap_analysis.py       # wraps gaps handler logic
+-- sub_packet.py         # wraps sub_packet.py
+-- parent_comm.py        # wraps parent_comm.py
+-- student_insights.py   # query student question patterns
+-- create_tool.py        # agent creates custom tools for teacher
```

### 2.2 Tool Protocol

```python
class Tool(Protocol):
    def schema(self) -> dict:
        """JSON schema the LLM sees -- name, description, parameters."""
        ...

    async def execute(self, params: dict, context: AgentContext) -> ToolResult:
        """Execute the tool. Returns text, files, structured data, side_effects."""
        ...
```

### 2.3 Key Design Rules

- **Tools are thin wrappers.** `generate_lesson.py` calls the lower-level functions in `lesson.py` and `generation.py` directly (same pattern as the existing `tools.py` which bypasses `ParsedIntent` and calls `clawed.lesson.generate_lesson`). No reimplementation.
- **Auto-discovery.** Adding a capability = adding one file to `tools/`. No registration boilerplate.
- **`AgentContext`** passed to every tool (see Section 1.2 for full definition): teacher_id, memory snapshot, session, config. Tools don't load their own context.
- **`ToolResult`** is a concrete dataclass (see Section 1.2): text, files, data (structured, for chaining), and side_effects (logged to memory automatically).

### 2.4 Approval Gate

`request_approval` is a special tool. When the agent does something consequential (publish to Drive, send to students), it calls this tool to pause execution.

**Persistence model:**

```python
@dataclass
class PendingApproval:
    """Stored in ~/.eduagent/approvals/{id}.json while awaiting response."""
    id: str                    # UUID
    teacher_id: str
    created_at: str            # ISO timestamp
    action_description: str    # human-readable: "Upload 5 lessons to Drive/Claw-ED/Civics/"
    action_payload: dict       # serialized tool calls to execute on approval
    agent_state: dict          # conversation history + memory snapshot for resumption
    transport: str             # which transport to deliver the approval request to
    timeout_hours: int = 48    # auto-reject after this period
    status: str = "pending"    # pending | approved | rejected | expired
```

**Flow:**

1. Agent calls `request_approval` tool with action description + payload
2. Tool creates `PendingApproval`, persists to disk, returns a hold message to the teacher
3. Teacher sees: "I'd like to upload 5 lessons to Drive. Approve? [Yes] [No] [Edit first]"
4. Teacher responds (could be seconds or hours later)
5. Transport receives the response, recognizes it as an approval (via callback_data prefix `approve:{id}` or `reject:{id}`)
6. `handle_callback()` loads the PendingApproval, resumes the agent with the stored state
7. If approved: agent executes the stored action payload. If rejected: agent acknowledges and moves on.
8. If no response within `timeout_hours`: status set to `expired`, agent notifies on next interaction

**Telegram:** approval rendered as inline keyboard buttons. **Web/TUI:** rendered as action buttons. **CLI:** rendered as a prompt.

### 2.5 Custom Teacher Tools

Teachers create tools in `~/.eduagent/tools/` as YAML files. **v0.6 supports prompt-template tools only** (no arbitrary Python execution — security risk deferred to a future sandboxing design):

```yaml
name: lab_safety_check
description: "Review a science lesson and flag lab activities needing safety equipment or accommodations."
parameters:
  lesson_text:
    type: string
    description: "The lesson plan text to review"
prompt_template: |
  Review this lesson plan for lab safety...
```

The agent can create custom tools conversationally via the `create_tool` built-in tool. Teacher says "I always need to check labs for safety" and the agent creates the YAML.

---

## 3. Cognitive Memory System

### 3.1 Three Memory Layers

**Layer 1 — Identity (slow-changing)**

Teacher's persona, style, subjects, grades, state, standards, schedule patterns. Lives at `~/.eduagent/workspace/identity.md`. Already exists; gets enriched over time by the agent.

**Layer 2 — Curriculum State (weekly-changing)**

What's been taught, what's coming, unit plan position, standards coverage, lesson feedback history. Structured storage in `~/.eduagent/memory/curriculum.db` (SQLite).

**Relationship to existing `memory_engine.py`:** The existing memory engine (783 lines) tracks feedback patterns, builds improvement context, and maintains `memory.md`. This is **subsumed** by the new system. Its feedback tracking logic migrates into Layer 2 (curriculum state). Its `build_improvement_context()` output becomes part of the memory context window assembled in Section 1.4. The existing `llm.py` calls to `inject_workspace_context()` get replaced by the agent core's system prompt assembly — no double injection.

**Layer 3 — Episodic Memory (per-interaction)**

Conversations, observations, student question patterns, discovered preferences. Embedding-based semantic store for retrieval, compressed over time. Stored in `~/.eduagent/memory/episodes.db`.

### 3.2 Memory Flow

**Before every interaction:**

1. Load identity (always in context)
2. Query curriculum state ("what are we teaching this week")
3. Semantic search episodic memory using current message as query
4. Assemble memory context window for the agent's system prompt

**After every interaction:**

1. Store exchange as episode with embeddings
2. Update curriculum state if changed (lesson generated, feedback given)
3. Periodically compress old episodes into summaries (memory consolidation)

### 3.3 Embedding Strategy

**Default: bundled ONNX model, auto-downloaded on first use.**

Ship `all-MiniLM-L6-v2` as an ONNX model. Runs on CPU, ~10ms per embedding, no Ollama or cloud dependency. Works offline. Teacher never configures anything.

**Packaging decision:** `onnxruntime` goes in a `[memory]` extra (`pip install 'clawed[memory]'`). On first interaction, if the extra isn't installed, the agent falls back to keyword-based retrieval (TF-IDF over episode text) and suggests: "Install memory support for smarter recall: `pip install 'clawed[memory]'`". This avoids bloating the base install while making memory degradation graceful.

**Upgrade path:** If teacher has Ollama running locally, auto-detect and use `mxbai-embed-large` for better quality. If Ollama Cloud exposes embeddings, use that.

### 3.4 OpenViking Pattern

Same architectural pattern as OpenViking context engine:

- Embed text chunks with the ONNX/Ollama model
- Store embeddings + text in SQLite (no vector DB dependency)
- Cosine similarity search at query time
- Configurable context window size (default: top 10 relevant episodes)
- Compression: after 30 days, episodes get summarized by the LLM and the originals archived

---

## 4. Google Drive Integration

### 4.1 Scope

- Personal Google accounts only (no Workspace/domain auth)
- Drive file operations: upload, list, search, organize
- Native Google Docs/Slides creation (Phase 2 — start with file upload)
- Read files from Drive for context/ingestion (Phase 2)

### 4.2 Safety Model: Dedicated Service Account

To protect teachers from Google bot-activity bans:

1. Teacher creates a free Gmail for Claw-ED (e.g., `clawed.mrsmith@gmail.com`)
2. Teacher authenticates that account via OAuth
3. Teacher shares their working Drive folder with the Claw-ED account
4. All API activity happens on the service account — teacher's personal account untouched

**Onboarding:** Agent walks the teacher through this step-by-step during setup.

### 4.3 OAuth Flow

- OAuth consent screen via local browser
- Scopes: Drive (files), Docs (create/edit), Slides (create/edit)
- Token stored in OS keychain or `~/.eduagent/` with restricted permissions
- Refresh token persists — authenticate once

### 4.4 Rate Limiting

- Max API calls per hour (configurable, default conservative)
- Batch uploads instead of one-at-a-time
- Exponential backoff on 429s with teacher notification
- Daily activity cap with override option

### 4.5 Drive Tools

| Tool | Phase | Purpose |
|------|-------|---------|
| `drive_upload` | 1 | Upload generated files (PPTX, DOCX, PDF) to a Drive folder |
| `drive_list` | 1 | Browse Drive folders |
| `drive_organize` | 1 | Create folders, move files |
| `drive_create_slides` | 2 | Convert lesson/unit to native Google Slides |
| `drive_create_doc` | 2 | Convert lesson to native Google Doc |
| `drive_read` | 2 | Read a file from Drive for context |

---

## 5. Proactive Behavior & Scheduling

### 5.1 How It Works

The scheduler daemon runs inside `clawed serve` (async task) or standalone via `clawed agent --daemon`. The agent decides what to schedule based on memory and curriculum state — not predefined cron tasks.

### 5.2 Scheduler Architecture

**Task persistence:** Scheduled tasks stored in `~/.eduagent/schedule.db` (SQLite, not JSON — supports queries and concurrent access).

**Task execution:** When a scheduled task fires, the scheduler creates a synthetic message and routes it through `Gateway.handle()`:
- `teacher_id`: from the task record
- `message`: a structured instruction like `[SCHEDULED] Check if lessons are prepped for Monday 2026-03-30`
- The agent recognizes the `[SCHEDULED]` prefix and acts proactively, applying approval gates for consequential actions

**Dynamic task creation:** The `schedule_task` tool persists a new row to `schedule.db` with: teacher_id, trigger time/cron expression, action description, and whether the action requires approval.

### 5.3 Task Creation

Tasks created three ways:

1. **Teacher asks:** "Remind me to prep Friday's reteach"
2. **Agent infers from patterns:** "You always prep Sunday night — want me to draft Monday's lessons every Sunday at 6pm?"
3. **Agent infers from curriculum state:** unit plan says Week 12 starts Monday, no lessons generated, it's Saturday — agent drafts proactively

### 5.4 Proactive Actions

| Trigger | Action | Requires Approval |
|---------|--------|-------------------|
| Upcoming lessons not prepped | Draft lessons, notify teacher | Yes |
| Lesson taught, no feedback logged | Ask how it went | No |
| Student confusion patterns accumulate | Suggest reteach material | Yes |
| Weekly curriculum checkpoint | Coverage summary + gaps report | No |
| Teacher's scheduled reminder fires | Deliver drafted content | Configurable |

### 5.5 Delivery Channel

Proactive messages go through the teacher's preferred transport (detected by tracking which gets fastest responses). Telegram message, web notification, or TUI alert.

### 5.6 Teacher Controls

Preferences stored in identity memory:

- Quiet hours ("don't message me on weekends")
- Conditional triggers ("only prep if I haven't done it by Sunday 8pm")
- Per-action policies ("never auto-generate assessments, always ask first")
- Agent self-correction ("I noticed you never use vocabulary lists — want me to stop?")

### 5.7 Autonomy Progression

Ship with proactive-with-approval-gates (Option B). Design for eventual full autonomy (Option C):

- Track approval rates per action type
- When a teacher approves 95%+ of a specific action without edits, agent can offer: "Want me to handle this automatically from now on?"
- Teacher grants per-action autonomy, revocable anytime

---

## 6. The Closed Loop

Everything above powers one loop:

```
Plan -> Generate -> Differentiate -> Publish -> Teach -> Feedback -> Reteach -> Improve
```

### 6.1 Example Week

**Sunday 6pm** — Agent notices Monday's lessons unprepped. Checks curriculum state: 8th grade Civics, Week 3 (Bill of Rights). Drafts 5 lessons differentiated for 3 ELL + 1 IEP students from memory. Sends Telegram: "Your week is ready — review?"

**Monday 7am** — Teacher approves with one edit. Agent uploads 5 lessons to Drive as Google Slides + worksheets as Docs in `Drive/Claw-ED/Civics/Week 12/`.

**Monday 3pm** — Teacher: "Period 3 didn't get the amendment process." Agent logs to memory, responds: "Want me to restructure Tuesday to start with a reteach?"

**Tuesday** — Reteach lands. Teacher thumbs up. Agent notes: "amendment process needed scaffolding for Period 3. Direct instruction > inquiry for this topic."

**Wednesday** — Student bot gets 14 questions about ratification vs. amendment. Agent surfaces: "Students are confused about ratification vs. amendment. Add a comparison chart to Thursday?"

**Friday** — Weekly summary: "4/5 lessons taught. Bill of Rights 60% complete. Standards: NY SS 8.4a, 8.4b covered. Gap: 8.4c (judicial review) — scheduled next week. Student bot: 47 questions. Top confusion: ratification vs. amendment (resolved Thursday)."

**Next Sunday** — Agent drafts Week 4 incorporating everything learned. Ratification/amendment gets a dedicated mini-lesson.

### 6.2 Why This Is Agentic

- Agent decides what to reteach based on evidence, not a script
- Memory accumulates across weeks — generation improves
- Drive integration puts content where the teacher uses it
- Student insights feed back into generation — loop is closed
- Teacher's job is teaching and giving feedback — agent handles the rest

---

## 7. Migration Plan

### 7.1 What Gets Deleted

| File(s) | Replacement |
|---------|-------------|
| `gateway.py` | `agent_core/core.py` |
| `router.py` | Agent decides via tools (no regex) |
| `agent.py` | `agent_core/core.py` — the existing tool-use loop logic (provider-specific message formats, Anthropic/OpenAI/Ollama tool calling protocols) is **migrated** into the new core, not discarded |
| `handlers/*.py` (10 modules) | Logic migrates into `agent_core/tools/` |
| `tools.py` | `agent_core/tools/` (new tool registry) |
| `memory_engine.py` | Subsumed by `agent_core/memory/` — feedback tracking → Layer 2, improvement context → system prompt assembly |

### 7.2 What Stays Untouched

| File(s) | Reason |
|---------|--------|
| `generation.py` (816 lines) | Crown jewel. Tools wrap it. |
| `llm.py` | Agent core calls it. Remove `inject_workspace_context()` / `build_improvement_context()` calls — agent core handles memory injection via system prompt. |
| `models.py` | Pydantic schemas stable. |
| `export_pptx.py`, `export_docx.py`, `export_pdf.py` | Become tool executors. |
| `standards.py`, `state_standards.py` | Become tool executors. |
| `student_bot.py` | Stays as-is. |
| `transports/*.py` | Import path changes from `clawed.gateway` to `clawed.agent_core`. `handle_callback()` preserved. |
| `database.py`, `state.py` | Data layer stays. Memory adds alongside. |
| `onboarding.py` | Setup wizard stays. Agent enhances. |
| `cli.py`, `commands/*.py` | CLI stays. |
| `model_router.py` | Stays. Tools use it internally for tier-based model selection. |
| Test infrastructure | Tests update, not deleted. |

### 7.3 Web API Routes

The FastAPI routes in `clawed/api/routes/` currently bypass the Gateway for some operations (e.g., `routes/generate.py` calls generation functions directly). These routes are **preserved** for backward compatibility — the web dashboard continues to work. Over time, they can be migrated to use the agent gateway endpoint (`/api/gateway/chat`), but this is not required for v0.6.

### 7.4 Migration Strategy

1. Build `agent_core/` as new package alongside old code
2. Create new `Gateway` in `agent_core/core.py` with same `handle()` + `handle_callback()` + `stats()` + `event_bus` interface
3. Old `clawed/gateway.py` becomes a thin re-export shim (`from clawed.agent_core import Gateway`) during transition
4. Migrate handler logic into tools one at a time (each independently testable)
5. Flip transport imports to `clawed.agent_core.Gateway`
6. Delete old gateway/router/handlers/agent/memory_engine and the re-export shim
7. Update tests: test tools directly + integration tests through new core

### 7.5 New Dependencies

| Package | Purpose | Install Path |
|---------|---------|-------------|
| `onnxruntime` | Bundled embedding model for memory | `[memory]` extra |
| `google-api-python-client` | Drive API | `[google]` extra (already defined) |
| `google-auth-oauthlib` | OAuth flow | `[google]` extra (already defined) |

---

## 8. Success Criteria

The vision is achieved when a teacher can say:

> "Prepare next week's 8th grade civics unit, align it to NY standards, generate differentiated materials, publish to Drive, schedule reminders, track student questions, and show me what to reteach on Friday."

And the system does it — with approval gates where needed, memory of what worked before, and improvements based on accumulated feedback.

### 8.1 Measurable Outcomes

- **Every message routes through the agent** — zero regex intent matching
- **Memory persists across sessions** — agent references past interactions accurately
- **Drive integration works end-to-end** — lesson generated, approved, uploaded, editable in Google Slides
- **Proactive behavior fires** — agent initiates at least one unprompted action per week based on curriculum state
- **Closed loop completes** — feedback from Week N measurably influences Week N+1 generation
- **Custom tools work** — teacher can create and use a custom tool via conversation
- **Existing functionality preserved** — all current generation, export, student bot, and transport features work through the new architecture
- **Graceful degradation** — agent falls back to direct generation when LLM API is down; memory falls back to keyword search without ONNX
