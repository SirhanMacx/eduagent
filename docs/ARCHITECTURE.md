# EDUagent Architecture

This document describes the internal architecture of EDUagent — how messages flow through the system, what each module does, and how components connect.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACES                                   │
│                                                                             │
│  ┌─────────────┐   ┌──────────────────┐   ┌─────────────┐   ┌───────────┐ │
│  │  Telegram    │   │  Terminal REPL    │   │  Web UI     │   │  MCP      │ │
│  │  (OpenClaw)  │   │  (eduagent chat)  │   │  (FastAPI)  │   │  Server   │ │
│  └──────┬──────┘   └────────┬─────────┘   └──────┬──────┘   └─────┬─────┘ │
│         │                   │                     │                │        │
└─────────┼───────────────────┼─────────────────────┼────────────────┼────────┘
          │                   │                     │                │
          └───────────────────┼─────────────────────┘                │
                              ▼                                      ▼
                ┌──────────────────────────┐          ┌──────────────────────┐
                │   openclaw_plugin.py     │          │   mcp_server.py      │
                │                          │          │                      │
                │ ┌──────────────────────┐ │          │ Tools:               │
                │ │ router.py            │ │          │ • generate_lesson    │
                │ │ Intent detection &   │ │          │ • generate_unit      │
                │ │ parameter extraction │ │          │ • ingest_materials   │
                │ └──────────┬───────────┘ │          │ • student_question   │
                │            ▼             │          │ • get_standards      │
                │ ┌──────────────────────┐ │          └──────────┬───────────┘
                │ │ state.py             │ │                     │
                │ │ Session load/save    │ │                     │
                │ │ Conversation context │ │                     │
                │ └──────────┬───────────┘ │                     │
                │            ▼             │                     │
                │      _dispatch()         │◄────────────────────┘
                │   Route to handler       │
                └────────────┬─────────────┘
                             │
          ┌──────────┬───────┼───────┬──────────┬──────────┐
          ▼          ▼       ▼       ▼          ▼          ▼
   ┌───────────┐┌────────┐┌───────┐┌────────┐┌──────────┐┌───────────┐
   │ ingestor  ││persona ││planner││lesson  ││materials ││student_bot│
   │           ││        ││       ││        ││          ││           │
   │ PDF/DOCX/ ││Extract ││Unit   ││Daily   ││Worksheet ││Student Q&A│
   │ PPTX/ZIP/ ││teaching││plans  ││lesson  ││Quiz      ││in teacher │
   │ Drive     ││style   ││with   ││plans   ││Rubric    ││voice      │
   │           ││→ JSON  ││scope  ││with    ││Slides    ││           │
   │           ││        ││       ││detail  ││IEP notes ││           │
   └─────┬─────┘└───┬────┘└───┬───┘└───┬────┘└────┬─────┘└─────┬─────┘
         │          │         │        │          │            │
         └──────────┴─────────┼────────┴──────────┘            │
                              ▼                                │
              ┌─────────────────────────────┐                  │
              │        llm.py               │◄─────────────────┘
              │   Unified LLM Client        │
              │                             │
              │ ┌─────────────────────────┐ │
              │ │   model_router.py       │ │
              │ │ Task → model mapping    │ │
              │ │ quick tasks → fast model│ │
              │ │ heavy tasks → big model │ │
              │ └─────────────────────────┘ │
              │                             │
              │  Anthropic │ OpenAI │ Ollama │
              └──────────────┬──────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │  corpus.py   │  │  exporter.py │  │ standards.py │
  │              │  │              │  │              │
  │ Few-shot     │  │ MD / PDF /   │  │ CCSS / NGSS /│
  │ examples for │  │ DOCX / HTML  │  │ C3 Framework │
  │ prompt       │  │ export       │  │              │
  │ injection    │  │              │  │ state_       │
  │              │  │              │  │ standards.py │
  │              │  │              │  │ 50-state map │
  └──────────────┘  └──────────────┘  └──────────────┘
                             │
                             ▼
              ┌─────────────────────────────┐
              │      search.py              │
              │  Tavily API / DuckDuckGo    │
              │  Web search for resources   │
              └─────────────────────────────┘
```

---

## Data Flow: Teacher Message to Generated Output

This is the full journey of a teacher's message through the system.

### Step 1: Message Received

A teacher sends a message through any interface (Telegram, terminal, web):

```
"Plan a unit on photosynthesis for my 8th graders, 3 weeks"
```

### Step 2: Intent Parsing (`router.py`)

The router detects intent and extracts parameters using pattern matching:

```python
ParsedIntent(
    intent=Intent.GENERATE_UNIT,
    topic="photosynthesis",
    grade="8",
    weeks=3,
    subject=None  # inferred from persona or asked
)
```

**25+ intents recognized:** `GENERATE_UNIT`, `GENERATE_LESSON`, `GENERATE_MATERIALS`, `GENERATE_ASSESSMENT`, `GENERATE_BELLRINGER`, `WEB_SEARCH`, `SEARCH_STANDARDS`, `START_STUDENT_BOT`, `EXPORT_PDF`, `HELP`, and more.

### Step 3: Session Management (`state.py`)

The session manager loads the teacher's persistent state from SQLite:

```
teacher_sessions table:
├── teacher_id (primary key)
├── persona (JSON) ← TeacherPersona
├── config (JSON) ← AppConfig
├── current_unit (JSON) ← most recent UnitPlan
├── context (JSON) ← last 10 conversation turns
└── teacher_profile (JSON) ← state, subjects, grades
```

### Step 4: Dispatch to Handler (`openclaw_plugin.py`)

The main dispatcher routes to the appropriate handler function:

```
Intent.GENERATE_UNIT    → _handle_generate_unit()
Intent.GENERATE_LESSON  → _handle_generate_lesson()
Intent.GENERATE_MATERIALS → _handle_generate_materials()
Intent.CONNECT_DRIVE    → _handle_connect_drive()
Intent.WEB_SEARCH       → _handle_web_search()
Intent.START_STUDENT_BOT → _handle_start_student_bot()
...
```

### Step 5: Generation Engine

For a unit plan, `planner.py:plan_unit()` orchestrates:

```
1. Retrieve few-shot examples from corpus
   corpus.py:get_few_shot_context(subject, grade)
       ↓
2. Build prompt from template
   prompts/unit_plan.txt (Jinja2)
   + persona.to_prompt_context()     ← teaching style
   + few-shot examples               ← quality boost
   + standards context               ← state alignment
       ↓
3. Route to appropriate model
   model_router.py:route("unit_plan", config)
   → heavy task → strong model (e.g., minimax-m2.7:cloud)
       ↓
4. Call LLM
   llm.py:LLMClient.generate_json(prompt)
   → Anthropic / OpenAI / Ollama API
   → JSON repair if truncated
       ↓
5. Validate response
   UnitPlan.model_validate(json_response)
   → Pydantic validates all fields
       ↓
6. Persist to database
   database.py → units table
```

### Step 6: Response Formatting

The handler formats output for the interface:

- **Telegram:** Emoji-rich, no markdown tables, compact
- **Terminal:** Rich tables, syntax highlighting, color
- **Web:** HTML with CSS styling
- **MCP:** Raw JSON

### Step 7: Session Save

Updated context (user message + assistant response) is saved back to SQLite for conversation continuity.

---

## Module Reference

### Core Pipeline

| Module | Purpose | Key Functions |
|--------|---------|---------------|
| `models.py` | Pydantic data models | `TeacherPersona`, `UnitPlan`, `DailyLesson`, `LessonMaterials`, `AppConfig` |
| `router.py` | Intent detection & NLU | `parse_intent(message) → ParsedIntent` |
| `state.py` | SQLite session management | `TeacherSession.load()`, `.save()`, `.update_context()` |
| `persona.py` | Teaching style extraction | `extract_persona(documents) → TeacherPersona` |
| `planner.py` | Unit plan generation | `plan_unit(subject, grade, topic, ...) → UnitPlan` |
| `lesson.py` | Daily lesson generation | `generate_lesson(lesson_number, unit, ...) → DailyLesson` |
| `materials.py` | Supporting materials | `generate_worksheet()`, `generate_assessment()`, `generate_slides()`, `generate_iep_notes()` |

### Infrastructure

| Module | Purpose | Key Functions |
|--------|---------|---------------|
| `llm.py` | Unified LLM client | `LLMClient.generate()`, `.generate_json()` — supports Anthropic, OpenAI, Ollama |
| `model_router.py` | Task-based model selection | `route(task_type, config) → config` — fast models for Q&A, strong models for generation |
| `config.py` | Secure API key management | OS keyring → fallback file → env vars |
| `database.py` | SQLite storage layer | CRUD for teachers, units, lessons, feedback |
| `corpus.py` | Few-shot example store | `get_few_shot_context()`, `contribute_example()` |

### Input/Output

| Module | Purpose | Key Functions |
|--------|---------|---------------|
| `ingestor.py` | Multi-format file ingestion | `ingest_path(path) → list[Document]` — PDF, DOCX, PPTX, TXT, MD, ZIP |
| `drive.py` | Google Drive integration | `ingest_drive_folder(url) → list[Document]` |
| `exporter.py` | Export to multiple formats | `lesson_to_pdf()`, `lesson_to_docx()`, `lesson_to_html()`, `unit_to_markdown()` |
| `search.py` | Web search for teachers | `search_for_teacher()`, `find_lesson_resource()` — Tavily + DuckDuckGo |

### Standards

| Module | Purpose | Key Functions |
|--------|---------|---------------|
| `standards.py` | National standards database | `STANDARDS` dict — CCSS Math/ELA, NGSS, C3 Framework (~200+ standards) |
| `state_standards.py` | 50-state framework mapping | `STATE_STANDARDS_CONFIG`, `get_standards_context_for_prompt()` |

### Interfaces

| Module | Purpose |
|--------|---------|
| `openclaw_plugin.py` | Telegram bot entrypoint — `handle_message()` with full intent routing |
| `cli.py` | Terminal CLI via Typer — all commands (`unit`, `lesson`, `chat`, `serve`, etc.) |
| `cli_chat.py` | Interactive terminal REPL with Rich formatting |
| `api/server.py` | FastAPI web application with dashboard |
| `api/routes/` | REST API endpoints — generate, ingest, chat, feedback, export, settings |
| `mcp_server.py` | Model Context Protocol server — expose tools to AI agents |
| `student_bot.py` | Student Q&A chatbot — answers in teacher's voice |

### Quality & Feedback

| Module | Purpose |
|--------|---------|
| `quality.py` | Automated quality scoring of generated content |
| `feedback.py` | Teacher rating and feedback collection |
| `improver.py` | Prompt improvement loop based on feedback |
| `templates_lib.py` | Jinja2 template library for prompt rendering |

---

## How the Corpus Works

The corpus is a SQLite database (`~/.eduagent/corpus/corpus.db`) that stores high-quality teaching examples used for few-shot prompt injection.

```
┌──────────────────┐     ┌─────────────────────┐     ┌────────────────────┐
│ Teacher generates │────▶│ Teacher rates 4-5★  │────▶│ Example enters     │
│ a lesson/unit     │     │ (quality gate)       │     │ corpus database    │
└──────────────────┘     └─────────────────────┘     └─────────┬──────────┘
                                                               │
                                                               ▼
┌──────────────────┐     ┌─────────────────────┐     ┌────────────────────┐
│ Better output    │◄────│ Few-shot examples    │◄────│ Corpus retrieval   │
│ for next teacher │     │ injected into prompt │     │ by subject/grade   │
└──────────────────┘     └─────────────────────┘     └────────────────────┘
```

**Index fields:** `content_type`, `subject`, `grade_level`, `topic`, `quality_score`

**Quality gate:** Only examples rated ≥3.5 stars are used as few-shot context.

**Privacy:** Teacher identity is hashed — contributions are anonymous.

---

## How the Student Bot Connects

The student bot allows students to ask questions about their current lesson and receive answers in their teacher's voice.

```
┌───────────────┐
│ Teacher Setup │
│               │
│ 1. create_class() → class_code (e.g., "BIO-8A")
│ 2. set_active_lesson(class_code, lesson_json)
│ 3. set_hint_mode(class_code, True/False)
└───────┬───────┘
        │
        ▼
┌────────────────────────────────────────────────────────────────┐
│                    Student Interaction                          │
│                                                                │
│  Student: "I don't understand how chloroplasts make glucose"   │
│                              │                                 │
│                              ▼                                 │
│  ┌─────────────────────────────────────────────────────┐      │
│  │ StudentBot.handle_message(message, student_id, code)│      │
│  │                                                     │      │
│  │ 1. Load class info (teacher, active lesson)         │      │
│  │ 2. Load teacher persona from state                  │      │
│  │ 3. Build prompt:                                    │      │
│  │    • Teacher persona (voice/tone)                   │      │
│  │    • Active lesson content (context)                │      │
│  │    • Hint mode? → give hints, not answers           │      │
│  │    • Student's question                             │      │
│  │ 4. Call LLM → answer in teacher's voice             │      │
│  │ 5. Track question for teacher analytics             │      │
│  └─────────────────────────────────────────────────────┘      │
│                              │                                 │
│                              ▼                                 │
│  Bot: "Great question! Remember when we talked about the      │
│  light reactions yesterday? The chloroplast uses that light    │
│  energy to split water molecules..."                          │
│  (answers in teacher's voice, with lesson context)            │
└────────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────┐
│ Teacher Analytics │
│                   │
│ • What students asked about
│ • Common confusion points
│ • Question frequency by topic
└───────────────────┘
```

**Key design decisions:**

- **Hint mode:** When enabled, the bot gives hints and guiding questions instead of direct answers — designed for homework support
- **Lesson context:** The bot only has access to the currently active lesson, keeping responses focused and accurate
- **Teacher voice:** The persona is injected into every response, so the bot sounds like the teacher
- **Privacy:** Student messages are stored per-class, accessible only to the class teacher

---

## Model Router: Smart Model Selection

Not all tasks need the same model. Quick Q&A uses a fast model; lesson generation uses a stronger one.

```
Task Type           → Default Model          → Reasoning
─────────────────────────────────────────────────────────
quick_answer        → qwen3.5:cloud          → Speed matters, low complexity
bellringer          → qwen3.5:cloud          → Short, simple generation
persona_extract     → qwen3.5:cloud          → Pattern extraction
lesson_plan         → minimax-m2.7:cloud     → Needs depth and coherence
unit_plan           → minimax-m2.7:cloud     → Complex multi-part structure
materials           → minimax-m2.7:cloud     → Accuracy critical (answer keys)
differentiation     → minimax-m2.7:cloud     → Nuance required (IEP notes)
```

Teachers can override per-task via `AppConfig.task_models`.

---

## Database Schema

All data lives in SQLite (either `~/.eduagent/state.db` for sessions or the web app's `database.db`).

```
teacher_sessions
├── teacher_id TEXT PRIMARY KEY
├── persona TEXT (JSON)
├── config TEXT (JSON)
├── current_unit TEXT (JSON)
├── context TEXT (JSON) ← last 10 messages
└── teacher_profile TEXT (JSON)

generated_units
├── unit_id TEXT PRIMARY KEY
├── teacher_id TEXT
├── unit_json TEXT
├── rating INTEGER
└── created_at TIMESTAMP

generated_lessons
├── lesson_id TEXT PRIMARY KEY
├── teacher_id TEXT
├── lesson_json TEXT
├── materials_json TEXT
├── quality_score REAL
├── edit_count INTEGER
├── share_token TEXT
└── created_at TIMESTAMP

feedback
├── id INTEGER PRIMARY KEY
├── lesson_id TEXT
├── rating INTEGER
├── notes TEXT
└── sections_edited TEXT (JSON)

classes
├── class_code TEXT PRIMARY KEY
├── teacher_id TEXT
├── active_lesson TEXT (JSON)
└── hint_mode BOOLEAN

student_questions
├── id INTEGER PRIMARY KEY
├── student_id TEXT
├── class_code TEXT
├── question TEXT
├── answer TEXT
└── lesson_topic TEXT
```

---

## Configuration & Secrets

All storage defaults to `~/.eduagent/` but can be relocated by setting the
**`EDUAGENT_DATA_DIR`** environment variable. Every module that touches disk
(`auth.py`, `config.py`, `workspace.py`, `task_queue.py`, `corpus.py`,
`bot_state.py`) reads this variable at import time and falls back to
`~/.eduagent` when it is unset.

```
$EDUAGENT_DATA_DIR/          # default: ~/.eduagent/
├── config.json              # User preferences (provider, model, output dir, teacher profile)
├── secrets.json             # API keys (0600 permissions) — fallback if keyring unavailable
├── api_keys.json            # Hosted-mode API key → teacher_id mapping
├── state.db                 # Teacher sessions (SQLite)
├── task_queue.db            # Background task queue (SQLite)
├── bot_state.db             # Telegram bot conversation state (SQLite)
├── workspace/               # Teacher workspace (identity, soul, memory, notes)
└── corpus/
    └── corpus.db            # Few-shot examples (SQLite)
```

**API key resolution order:**

1. Environment variables (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `TAVILY_API_KEY`)
2. OS keyring (macOS Keychain, Linux Secret Service, Windows Credential Manager)
3. `$EDUAGENT_DATA_DIR/secrets.json`

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.10+ |
| Async HTTP | httpx |
| LLM APIs | anthropic, openai (+ Ollama via HTTP) |
| Data validation | Pydantic 2.x |
| CLI | Typer + Rich |
| Web framework | FastAPI + Uvicorn |
| Templating | Jinja2 |
| File ingestion | PyMuPDF (PDF), python-docx, python-pptx |
| PDF export | ReportLab |
| Database | SQLite (WAL mode) |
| MCP | mcp >= 1.0.0 |
| SSE | sse-starlette |
| Linting | Ruff |
| Testing | pytest + pytest-asyncio |
