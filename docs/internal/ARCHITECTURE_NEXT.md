# Claw-ED: OpenClaw for Education — Architecture Plan

## The Vision

Claw-ED is EDUagent rebuilt on OpenClaw's architecture. Instead of a monolithic Python bot that does everything, it's a **gateway-first system** where Telegram, web, CLI, and future transports are thin message shuttles that all talk to one smart gateway.

## Current Problems

1. `tg.py` is 1,600+ lines doing: Telegram API, intent detection, lesson generation, export, scheduling, onboarding, ratings, file handling, gap analysis, model switching — ALL in one file
2. `openclaw_plugin.py` is a proto-gateway but duplicates logic with tg.py
3. Adding a new transport (Discord, WhatsApp, SMS) means copying 1,000+ lines
4. Business logic is tangled with transport logic

## Target Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     TRANSPORTS (thin)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐ │
│  │ Telegram  │  │ Web API  │  │   CLI    │  │  OpenClaw   │ │
│  │ ~150 LOC  │  │ FastAPI  │  │  Typer   │  │  Plugin     │ │
│  └─────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬──────┘ │
│        │              │              │               │        │
│        ▼              ▼              ▼               ▼        │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                    GATEWAY                                │ │
│  │                                                           │ │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │ │
│  │  │   Router     │  │  Session Mgr  │  │  Auth/Identity │  │ │
│  │  │  (intents)   │  │  (per-user)   │  │  (teacher ID)  │  │ │
│  │  └──────┬──────┘  └──────┬───────┘  └───────┬────────┘  │ │
│  │         │                │                   │           │ │
│  │         ▼                ▼                   ▼           │ │
│  │  ┌─────────────────────────────────────────────────────┐ │ │
│  │  │                   HANDLERS                           │ │ │
│  │  │  generate_lesson()  generate_unit()  run_gap_analysis│ │ │
│  │  │  manage_schedule()  process_rating() handle_ingest() │ │ │
│  │  │  show_standards()   export_lesson()  onboard_user()  │ │ │
│  │  └──────────────────────┬──────────────────────────────┘ │ │
│  │                         │                                │ │
│  │                         ▼                                │ │
│  │  ┌─────────────────────────────────────────────────────┐ │ │
│  │  │                   SERVICES                           │ │ │
│  │  │  LLM Client    Memory Engine    Scheduler            │ │ │
│  │  │  Workspace     Ingestor         Persona              │ │ │
│  │  │  Standards     Skills           Doc Export            │ │ │
│  │  └─────────────────────────────────────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### 1. Gateway is the brain
Every message goes: `Transport → Gateway.handle(message, teacher_id) → Response`

The gateway returns a `GatewayResponse` that the transport renders:
```python
@dataclass
class GatewayResponse:
    text: str                           # Main response text
    files: list[Path] = field(...)      # Files to send (PPTX, DOCX, etc.)
    buttons: list[Button] = field(...)  # Action buttons (rate, export, etc.)
    typing: bool = False                # Show typing indicator
    progress: str = ""                  # Progress update text
```

Transports don't know about lessons, personas, or LLMs. They just render GatewayResponse.

### 2. Naming: Claw-ED

```
Package name: clawed
PyPI: pip install clawed
CLI: clawed
GitHub: SirhanMacx/clawed
Import: from clawed.gateway import Gateway
```

The old `eduagent` package becomes a thin wrapper that imports from `clawed` for backward compatibility.

### 3. Multi-model routing (from OpenClaw)
```python
class ModelRouter:
    """Route requests to the right model based on task type."""

    TASK_TIERS = {
        "intent_detection": "fast",    # Ollama local or cheap cloud
        "lesson_generation": "work",   # Sonnet, GPT-4o
        "persona_extraction": "deep",  # Opus, GPT-4
        "formatting": "fast",
        "evaluation": "deep",
    }

    def route(self, task: str) -> LLMClient:
        tier = self.TASK_TIERS.get(task, "work")
        return self.clients[tier]
```

Teachers configure tiers in config, or use sensible defaults.

### 4. Gateway handles
```python
class Gateway:
    """The brain of Claw-ED. Transport-agnostic."""

    async def handle(self, message: str, teacher_id: str,
                     files: list[Path] = None) -> GatewayResponse:
        """Process any message from any transport."""
        session = self.sessions.get(teacher_id)

        # Onboarding check
        if not session.is_configured():
            return self._onboard_step(session, message)

        # Intent detection (fast model)
        intent = await self.router.detect_intent(message)

        # Route to handler
        handler = self.handlers.get(intent.action)
        if handler:
            return await handler(message, session, intent)

        # Fallback: conversational LLM
        return await self._chat(message, session)
```

### 5. Session management (from OpenClaw's workspace)
```python
class TeacherSession:
    teacher_id: str
    persona: TeacherPersona
    config: AppConfig
    memory: MemoryEngine
    workspace: Workspace
    last_lesson: DailyLesson | None
    onboard_state: dict
```

### 6. Transports are tiny
```python
# clawed/transports/telegram.py (~150 lines)
class TelegramTransport:
    def __init__(self, token: str, gateway: Gateway):
        self.token = token
        self.gateway = gateway
        self.api = TelegramAPI(token)

    def run(self):
        """Sync polling loop."""
        while True:
            updates = self.api.get_updates(timeout=30)
            for update in updates:
                self._handle_update(update)

    def _handle_update(self, update):
        msg = update.get("message", {})
        text = msg.get("text", "")
        teacher_id = str(msg["from"]["id"])
        chat_id = msg["chat"]["id"]

        # Files?
        files = self._download_files(msg) if msg.get("document") else []

        # Gateway does ALL the thinking
        response = asyncio.run(
            self.gateway.handle(text, teacher_id, files=files)
        )

        # Render the response
        self._send_response(chat_id, response)

    def _send_response(self, chat_id, response):
        if response.text:
            self.api.send_message(chat_id, response.text)
        for file in response.files:
            self.api.send_document(chat_id, file)
        if response.buttons:
            self.api.send_keyboard(chat_id, response.buttons)
```

## Migration Plan

### Phase 1: Create gateway (no rename yet)
1. Create `eduagent/gateway.py` — extract all logic from tg.py
2. Slim tg.py to a thin transport that calls gateway.handle()
3. Web API routes call the same gateway
4. All tests still pass against existing `eduagent` package name

### Phase 2: Rename to Claw-ED
1. Create `clawed/` package alongside `eduagent/`
2. `eduagent/__init__.py` becomes: `from clawed import *` (backward compat)
3. Update pyproject.toml: name = "clawed", entry points = "clawed"
4. Both `clawed` and `eduagent` CLI commands work
5. GitHub repo rename: SirhanMacx/clawed

### Phase 3: Multi-model routing
1. Add `ModelRouter` with tier-based routing
2. Fast model for intent detection (saves $$)
3. Work model for generation
4. Deep model for persona extraction and evaluation

### Phase 4: OpenClaw plugin
1. Create `clawed/transports/openclaw.py` — Claw-ED as an OpenClaw skill
2. Manfred can use Claw-ED tools directly through his OpenClaw gateway
3. Teachers who already use OpenClaw get Claw-ED automatically

## File Structure
```
clawed/
├── __init__.py
├── gateway.py              # The brain — all business logic
├── router.py               # Intent detection + routing
├── session.py              # Per-teacher session management
├── model_router.py         # Multi-model tier routing
├── handlers/               # One handler per intent
│   ├── generate.py         # Lesson, unit, materials generation
│   ├── ingest.py           # File ingestion
│   ├── schedule.py         # Scheduling management
│   ├── feedback.py         # Rating and memory loop
│   ├── export.py           # PPTX, DOCX, PDF, handout
│   ├── standards.py        # Standards lookup
│   ├── onboard.py          # New teacher setup
│   └── gaps.py             # Curriculum gap analysis
├── transports/             # Thin message shuttles
│   ├── telegram.py         # ~150 lines
│   ├── web.py              # FastAPI routes
│   ├── cli.py              # Typer commands
│   └── openclaw.py         # OpenClaw plugin transport
├── services/               # Shared services
│   ├── llm.py              # LLM client
│   ├── memory.py           # Memory engine
│   ├── workspace.py        # Teacher workspace
│   ├── persona.py          # Persona extraction
│   ├── skills.py           # Subject skills
│   └── images.py           # Academic image sourcing
├── models.py               # Pydantic models (unchanged)
├── io.py                   # Central file I/O
└── prompts/                # Prompt templates
```

## What Stays the Same
- All Pydantic models (DailyLesson, UnitPlan, TeacherPersona, etc.)
- All prompt templates
- All subject skills
- All standards data
- The memory engine
- The workspace system
- The scheduler
- Document export (PPTX, DOCX, PDF, handouts)
- Image sourcing
- 1200+ tests (re-pointed to new imports)

## What Changes
- tg.py (1600 lines) → telegram.py (150 lines) + gateway.py (500 lines)
- openclaw_plugin.py → gateway handlers
- Intent detection moves to gateway
- All transport-specific code isolated to transport modules
- Package name: eduagent → clawed (with backward compat)
