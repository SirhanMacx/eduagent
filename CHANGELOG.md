# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.0.7] - 2026-03-27

Superhuman materials — output that competes with commercial curriculum.

### Changed
- Images re-enabled in slideshow by default (smarter academic sourcing)
- Section divider slides ("Let's Practice Together", "Show What You Know")
- Differentiation in DOCX uses colored callout boxes (yellow/blue/green)
- Lesson-at-a-glance timing table at top of lesson plan
- File names include lesson topic (not generic lesson_01)
- Vocabulary slide filters out instructional directions
- Title slide gradient effect when no image available
- Agent narrates before long-running tools ("Building your package now...")
- Handout includes visual material descriptions where images are referenced

### Fixed
- Vocabulary slide script leakage (CHECK FOR UNDERSTANDING appearing as vocab term)
- Handout silently dropping image references
- include_images=False hardcoded in bundle tool

## [1.0.0] - 2026-03-26

Claw-ED is a personal AI teaching agent, not a product.

### Removed
- Waitlist system (email capture, waitlist API routes)
- Hosted/multi-tenant deployment mode (gunicorn, rate limiting, API key middleware)
- Landing pages and marketing assets
- Browser-based setup wizard (replaced by terminal-first onboarding)
- slowapi rate limiting dependency

### Changed
- README rewritten as agent documentation, not product page
- pyproject.toml description updated to reflect agent identity
- First-run simplified: workspace templates, no browser wizard
- Identity: "personal AI teaching agent" not "AI co-teacher product"

### Kept
- All 25 agent tools, generation pipeline, memory system, export pipeline
- Standards alignment (50 states), subject skills (13 subjects)
- Google Drive integration, Telegram bot, student chatbot
- Curriculum Knowledge Base (v0.9.20 feature, carried forward)
- Custom agent naming, Google Gemini provider, professional exports

## [0.9.20] - 2026-03-26

### Added
- **Curriculum Knowledge Base** — uploaded files are chunked, embedded, and stored as a local semantic database. The agent searches your materials before every generation, grounding output in your own prior work. Powered by Ollama embeddings (mxbai-embed-large) with TF-IDF fallback.
- **search_my_materials tool** — agent explicitly searches teacher's uploaded curriculum files by topic, returning ranked excerpts with source attribution
- **Custom agent naming** — teachers name their AI partner during onboarding (Sage, Coach, or anything). Agent refers to itself by the chosen name in all interactions.
- **Google Gemini provider** — use your Google AI Studio API key (free at https://aistudio.google.com/apikey). Gemini Flash for fast tasks, Gemini Pro for deep generation.
- **Professional export templates** — DOCX exports with headers (teacher name, subject, date), footers (page numbers, agent branding), and consistent Calibri typography. PPTX exports with section divider slides between lesson phases.
- **IEP/ELL callout boxes** — differentiation sections in DOCX use shaded backgrounds for visual distinction
- **Post-generation export guarantee** — if the LLM forgets to call export_document, files are still delivered
- **Configurable max agent iterations** — `AppConfig.max_agent_iterations` (default 20) for complex curriculum planning
- **Web dashboard basic auth** — optional `dashboard_password` in config
- **25 agent tools** (added search_my_materials, configure_profile gains agent_name)

### Changed
- **System prompt rewritten** — search-first behavior (always check curriculum KB), status narration ("Searching your files..."), proactive suggestions ("Want me to create a worksheet?"), colleague personality
- **Approval tracker migrated to SQLite** — single GROUP BY query replaces per-file JSON globbing
- **Episodic memory recall bounded** — 90-day recency filter + LIMIT 200 in SQL before cosine ranking
- **LLM adapter cleaned up** — no more monkey-patching of global TOOL_DEFINITIONS
- **Ingest handler enriched** — returns curriculum library stats after indexing ("I now have 15 documents, 230 searchable sections")
- **Memory loader** — new curriculum_kb_context layer injected into system prompt

### Fixed
- Episodic memory O(n) scaling for teachers with hundreds of interactions
- Approval tracking performance with large approval histories

## [0.9.0] - 2026-03-25

### Added
- **Autonomy progression** — `ApprovalTracker` monitors accept/reject rates per action type. When a teacher approves 95%+ of a specific action (with 10+ samples), the agent offers to auto-approve that action type.
- **Student insights tool** — `student_insights` queries student question patterns, groups by lesson topic, surfaces top confusion areas for reteaching decisions
- **Teacher preference learning** — `extract_preferences()` pulls signals from feedback history (ratings, edited sections), memory engine patterns, and approval tracker. Preferences rendered in the system prompt.
- **Closed feedback loop** — proven end-to-end: generate → feedback → store episode → next generation references the feedback. Rich episode metadata (interaction type, tool calls, message length).
- **Autonomy context in system prompt** — agent sees approval rate summaries and can offer auto-approval for consistently-approved actions
- **22 agent tools total** (added student_insights)

## [0.8.0] - 2026-03-25

### Added
- **Proactive scheduling** — `AgentScheduler` wires `EduScheduler` to the agent gateway via `handle_system_event()`. 5 built-in tasks (morning-prep, weekly-plan, feedback-digest, memory-compress, student-digest). Scheduler starts automatically with `clawed serve` when agent gateway is enabled.
- **Schedule task tool** — agent can create, list, enable, and disable scheduled tasks conversationally
- **Custom teacher tools** — YAML prompt-template tools loaded from `~/.eduagent/tools/`. Teachers define name, description, parameters, and prompt template in YAML. `ToolRegistry.discover_custom()` auto-loads them alongside built-in tools.
- **Multi-step planner** — system prompt enhancement for complex requests ("prepare my week"). Detects planning keywords and injects step-by-step execution instructions.
- **Native Google Slides creation** — `drive_create_slides` tool creates native Google Slides presentations
- **Native Google Docs creation** — `drive_create_doc` tool creates native Google Docs
- **Drive file reading** — `drive_read` tool reads file content from Drive for context ingestion
- **21 agent tools total** (up from 17)

### Removed
- Stale `output/` directory (old ProductHunt/beta launch marketing files)
- Stale `skills/eduagent/` directory (old OpenClaw skill file)
- Stale `docs/internal/` directory (old build prompts and architecture notes)
- Superseded pre-v0.6 implementation plans

## [0.7.0] - 2026-03-25

### Added
- **3-layer cognitive memory system** — identity (workspace/DB), curriculum state (DB projections), and episodic memory (embedding-based semantic search with TF-IDF fallback)
- **Episodic memory** stores every agent interaction and recalls relevant past conversations using semantic similarity. Teacher-isolated — each teacher's memory is separate.
- **Memory context loader** assembles all 3 layers + existing improvement context into a unified system prompt. Graceful degradation if any layer fails.
- **`[memory]` install extra** — `pip install 'clawed[memory]'` for ONNX-based embeddings (TF-IDF works without it)
- **Google Drive auth** — OAuth token persistence with 0600 permissions, `is_authenticated()` check, interactive auth flow placeholder
- **Drive client** with sliding-window rate limiter (configurable max requests/hour), `list_files()`, `upload_file()`, `create_folder()`
- **3 Drive tools** for the agent: `drive_upload`, `drive_list`, `drive_organize` — auto-discovered by the tool registry (17 tools total)
- **Drive config** — `drive_root_folder` and `drive_token_path` fields in `AppConfig`

### Changed
- Agent system prompt now includes curriculum progress and relevant past interactions from episodic memory
- Each agent interaction is automatically stored as an episode for future recall
- `build_system_prompt()` accepts `curriculum_summary` and `relevant_episodes` parameters

## [0.6.0] - 2026-03-25

### Added
- **Agent-first gateway** — new `clawed/agent_core/` package with control-plane pre-router and LLM-driven tool-use loop. Natural-language messages flow through the agent; deterministic paths (files, callbacks, onboarding) stay deterministic.
- **Typed tool registry** — 15 tools auto-discovered from `agent_core/tools/`, each wrapping existing generation/export/standards functions with the `Tool` protocol (`schema()` + `execute()`)
- **Approval gate** — `PendingApproval` persistence model with `ApprovalManager` for pause/resume/expire lifecycle across all transports
- **FakeLLM test harness** — deterministic LLM mock for testing agent behavior without real API calls
- **Feature flag** — `agent_gateway` flag in `AppConfig` toggles between legacy and agent gateway. Flag OFF = identical old behavior. Flag ON = agent-first routing.
- **Compatibility shim** — `clawed/gateway.py` transparently routes to legacy or agent gateway based on flag. All existing imports (`EduAgentGateway`, `ActivityEvent`, `GatewayStats`) continue to work.
- **System prompt assembly** — `build_system_prompt()` loads teacher context from canonical sources (database, persona, memory engine) into a dynamic system prompt
- **TUI chat** — `clawed tui` command provides full-screen terminal chat via Textual, connecting to the running gateway over HTTP
- **`/api/gateway/chat`** endpoint for transport clients

### Changed
- `clawed serve` now shows the onboarding wizard for new users (not the marketing landing page)
- Privacy claim updated — clarifies keyring is optional for API key storage
- Bare `clawed` command now respects `EDUAGENT_DATA_DIR` environment variable

### Fixed
- TUI pip install hint no longer eaten by Rich markup
- Dockerfile now copies `clawed/` package (was missing, only had `eduagent/`)

## [0.5.0] - 2026-03-25

### Removed
- **Legacy Telegram bot** (`telegram_bot.py`, 913 lines) — the deprecated `--legacy` and `--live` bot flags have been removed. All Telegram functionality now uses the gateway-based httpx transport (`clawed/transports/telegram.py`).
- `telegram-legacy` optional dependency removed

### Note
- The student bot (`student_telegram_bot.py`) still uses python-telegram-bot and is unchanged
- `pip install 'clawed[telegram]'` still works for the student bot

## [0.1.3] - 2026-03-24

### Added
- **Student Class Code System** — teachers create class codes with `clawed class create`, students join via Telegram `/join`, teacher revokes with `clawed class revoke`
  - Database tables: `class_codes`, `student_enrollments`, `student_questions` with full CRUD
  - CLI: `clawed class create/list/stats/revoke/qr/report`
  - Web: `GET /student/{class_code}` with QR code, class info, and Telegram link
  - Weekly progress reports with anonymized student activity and topic analysis
- **Telegram Bot Polish** — production-ready Telegram bot with full state machine
  - `/health` command: model, persona, lesson count, corpus size
  - `setMyCommands` on startup for BotFather menu registration
  - Conversation state machine: IDLE → COLLECTING → GENERATING → DONE
  - Error recovery: retry with backoff, friendly fallback messages, error logging
  - Busy state handling: "Still working on your lesson" during generation
  - Post-generation quick actions: [Rate this] [Generate worksheet]
- **Onboarding Flow Polish** — smooth first-run experience
  - Persona preview with confirmation: "I learned that you teach... Is this right?"
  - Model auto-detection: Anthropic API key → OpenAI API key → Ollama (with preferred model)
  - Auto-generate sample lesson on first setup
  - Rich progress bars during file ingestion
- **Web Dashboard v2** — key missing pages filled
  - Lesson list page (`/lessons`) with subject and grade filters
  - Persona/settings page (`/settings`) with class codes management
  - Student chatbot embed snippet on lesson pages with copy button
  - Profile page (`/profile`) with standards framework info
  - Analytics page with daily lesson/question charts
- 55+ new tests covering all 4 feature waves

## [0.1.2] - 2026-03-24

### Added
- **Sub Packet Generator** (`eduagent/sub_packet.py`) — complete substitute teacher packets with class overview, schedule, step-by-step lesson instructions, student notes, materials checklist, and emergency info
  - CLI: `clawed sub --class "Period 3 Global Studies" --grade 8 --subject "Social Studies" --topic "WWI Document Analysis" --date "March 25, 2026"`
  - API: `POST /api/sub-packet`
  - Markdown rendering with printable formatting
- **Parent Communication Generator** (`eduagent/parent_comm.py`) — professional parent emails for 6 communication types: progress updates, behavior concerns, positive notes, upcoming units, permission requests, general updates
  - CLI: `clawed parent-comm --type progress --student-desc "a student struggling with document analysis" --context "Unit 4 WWI"`
  - API: `POST /api/parent-comm`
- Dashboard "Teacher Tools" row with Generate Sub Packet and Parent Communication buttons
- 33 new tests (test_sub_packet.py, test_parent_comm.py) — total: 910 passing

## [0.1.1] - 2026-03-24

### Added
- Background task queue (`eduagent/task_queue.py`) — submit long-running generation jobs (lessons, units, worksheets, assessments) and check back later
- CLI commands: `clawed queue submit`, `clawed queue status`, `clawed queue list`, `clawed queue worker`
- 6 new subject skills (Art, Music, PE, CS, Health, Economics)
- Custom YAML skill plugin system
- Persistent bot state across restarts
- Windows UTF-8 compatibility improvements

### Fixed
- Resolved all ruff lint issues (line lengths, unused imports, type annotations)
- Added `apscheduler` to dev dependencies
- Pinned dependency versions for stability

## [0.1.0] - 2026-03-23

### Added
- Persona extraction from teacher curriculum files (PDFs, DOCX, PPTX, TXT)
- Unit planning with essential questions and lesson sequences
- Daily lesson generation (AIM, Do Now, instruction, exit ticket)
- Worksheets, assessments, and rubrics generation
- IEP/504 accommodation and tiered assignment generation
- 50-state standards alignment with auto-detection
- Telegram bot for standalone mobile access
- Web dashboard with streaming generation
- Student chatbot — students ask questions in teacher's voice
- Voice note transcription via Whisper
- School/department curriculum sharing
- Substitute teacher packet generator
- Parent communication generator
- Subject skill libraries (Social Studies, Math, Science, ELA, History)
- Self-improvement loop (gets better the more it's used)
- MCP server (tools callable from any AI agent)
- Ollama support (free local LLM) alongside Anthropic and OpenAI
- Model router for multi-provider LLM selection
- Terminal chat, web dashboard, and Telegram delivery modes
- Google Drive connector (personal accounts only)
- Demo mode (no API key required)
- GitHub community infrastructure (CI, issue templates, PR template)
