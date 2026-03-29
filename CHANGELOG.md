# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [2.3.5] - 2026-03-28

Stability & Trustworthiness — contract fidelity across the entire generation pipeline.

### Added
- **Master Content Track** — `generate_master_content()` produces a single `MasterContent` object. Three output documents (teacher DOCX, student DOCX, slideshow PPTX) are compiled mechanically as views of the same data. Eliminates 3 parallel LLM calls, replaced by 1 generation + 3 mechanical compilations.
- **`MasterContent` model** with sub-models: `DoNow`, `InstructionSection`, `GuidedNote`, `PrimarySource`, `StationDocument`, `StimulusQuestion`, `VocabularyEntry`, `IndependentWork`. Backward-compatible via `.to_daily_lesson()` bridge.
- **Master content prompt** — comprehensive stimulus-based pedagogy prompt with self-contained materials rule, cognitive progression requirements, and subject-specific source type guidance.
- **Compilation functions** — `compile_teacher_view()`, `compile_student_view()`, `compile_slides()` produce print-ready documents without any LLM calls.
- **10 post-generation validators** — `validate_quiz()`, `validate_rubric()`, `validate_year_map()`, `validate_unit_plan()`, `validate_formative()`, `validate_summative()`, `validate_dbq()`, `validate_lesson_materials()`, `validate_pacing_guide()`, `validate_master_content()` with alignment checking and delegation phrase detection.
- **`GenerationReport` model** — accumulates warnings, quality review results, voice check results, and image counts throughout the pipeline.
- **Schema-aware demo routing** — `demo_hint` parameter threads through `generate()`, `generate_json()`, `safe_generate_json()`. Demo mode dispatches to correct fixture by model class name, not keyword matching. 7 new demo fixture files.
- **`resolve_credentials()`** — unified credential resolution: env vars → keychain → Ollama config.
- **Parallel image pipeline** — `fetch_all_images()` collects all `image_spec` strings from MasterContent, fetches in parallel via `asyncio.gather` with configurable timeout and local caching.
- **NYS Regents conditional** — when teacher state is NY and subject is Social Studies, exit ticket prompts include SBMCQ/CRQ format requirements.
- **Prompt injection defense** — system prompt includes security instruction to reject injected instructions from input text.
- **pytest-cov** — coverage configured with 55% regression floor.
- **17 new tests** — E2E bundle integration (10 tests) and pedagogical quality validation (7 tests).

### Changed
- **All 11 generators migrated to `safe_generate_json()`** — assessment.py (5), materials.py (4), curriculum_map.py (2). Automatic retry on Pydantic validation failure with error context in retry prompt.
- **`generate_lesson_bundle` rewritten** — uses Master Content Track: generate_master_content → validate → fetch images → compile three views. Replaced 3 parallel LLM calls with 1 generation + 3 mechanical compilations.
- **`generate_lesson()` bridges through `generate_master_content()`** — all ~20 callers get `DailyLesson` back, fully backward compatible.
- **Teacher materials wired into all paths** — `generate_all_lessons()` and `GenerateLessonTool` now search AssetRegistry + CurriculumKB before generation.
- **Persona double-injection removed** — persona kept in system prompt only, not duplicated in user prompt.
- **Async exports fixed** — replaced deprecated `asyncio.get_event_loop()` with `asyncio.run()`, added `_run_async_safe()` for correct sync/async call path handling. Python 3.14 compatible.

### Fixed
- **Quality review fails closed** — `review_lesson_package()` returns `passed: False` on parse errors instead of silently passing.
- **Coroutine reuse bug** — `safe_generate_json()` uses `current_prompt` instead of mutating the original prompt in retry loop.
- **Identity corruption** — onboarding gated behind explicit `/setup` or `/start`. TeacherProfile name/subject validated and truncated. SOUL.md writes audit-logged and capped at 500 chars.
- **CLI error wrapping** — all `_run_async(generate_*())` calls wrapped with `try/except` for user-friendly error messages instead of raw tracebacks.
- **`is_demo_mode()` checks keychain** — secure-store-only keys no longer trigger demo mode.

## [2.2.0] - 2026-03-27

Better Memory — deeper understanding of your teaching over time.

### Added
- **Long-term memory compression** — after every 20 episodes, older episodes are summarized into `memory_summary.md` highlights. Last 10 episodes kept verbatim, preventing unbounded episodic memory growth.
- **Cross-session context threading** — new sessions greet with continuity ("Last time we worked on the Age of Exploration unit. Want to continue?") using the most recent episode from episodic memory.
- **Preference drift detection** — rolling 10-lesson rating window comparison. Logs a warning to memory.md when average drops >0.5 stars, or a positive note when it improves >0.5 stars.
- `EpisodicMemory.get_latest_episode()` — retrieve the most recent episode for a teacher
- `EpisodicMemory.count_episodes()` — total episode count per teacher
- `EpisodicMemory.get_all_episodes()` — chronological episode retrieval with pagination
- `compress_old_episodes()` / `maybe_compress_episodes()` — rule-based episode compression (no LLM)
- `detect_preference_drift()` — rolling-window drift detection with automatic memory logging
- `last_session_summary` field in memory context loader
- "Drift Alerts" section in memory.md for tracking rating trends
- Comprehensive test suite for all three features

## [2.0.1] - 2026-03-27

Pedagogical fingerprint — "teacher voice" means how you teach, not just how you sound.

### Changed
- **TeacherPersona model expanded** — 7 new fields: `source_types`, `activity_patterns`, `scaffolding_moves`, `grouping_preferences`, `do_now_style`, `exit_ticket_style`, `signature_moves`
- **Persona extraction prompt rewritten** — Now extracts detailed pedagogical patterns: what sources the teacher uses, how they run activities, how they scaffold, their Do Now and exit ticket formats, and signature classroom moves
- **`to_prompt_context()` expanded** — Pedagogical fingerprint fields serialized as structured sections with explicit instructions (e.g. "Use these TYPES of sources", "replicate these structures")
- **Lesson generation prompt updated** — Explicit instructions to match source types, activity patterns, scaffolding moves, Do Now style, exit ticket format, and signature moves — not just tone/vocabulary

### Fixed
- "Teacher voice" was only surface-level (catchphrases, tone) — now captures the full pedagogical fingerprint
- Images working on Sirhan (LOC timeout is expected, Wikimedia fallback succeeds)

## [2.0.0] - 2026-03-27

The Real Teaching Agent — clean output, real voice matching, knowledge base integration.

### Changed
- **Sanitization rewrite** — `sanitize_text()` now strips XML tags (`<teacher prompt>`, `<transition>`, etc.), markdown formatting (`##`, `**`, `*`), HTML entities, and CJK leakage. Pre-compiled regexes for performance.
- **Voice injection** — Lesson generation system prompt now includes full persona context, SOUL.md (up to 2000 chars), and voice sample (cap raised from 500 to 2000 chars). No more generic "expert lesson plan writer."
- **KB results as structured context** — Teacher's existing materials injected as a dedicated `{teacher_materials}` section in the lesson prompt with 500-char excerpts and explicit instruction to build on prior work.
- **Images on by default** — `export_lesson_pptx()` default changed from `include_images=False` to `True`.
- **Anti-XML prompt instruction** — Lesson prompt template now explicitly tells the LLM to not use XML tags or pseudo-markup.
- **Sanitization everywhere** — All three export pipelines (DOCX lesson, DOCX handout, PPTX) now sanitize every text field before rendering.
- **Image pipeline logging** — PPTX export logs image fetch request/success counts for diagnosing failures.

### Fixed
- MiniMax M2.7 XML tag artifacts (`<teacher prompt>`, `<transition>`, `<activity structure>`) appearing in printed documents
- Persona/SOUL.md context never reaching the lesson generation LLM call
- KB search results buried in unit overview instead of structured prompt context
- Voice sample truncated to 500 chars (now 2000)

## [1.0.8] - 2026-03-27

Fix the foundations — reading report, KB search, image sourcing.

### Fixed
- Reading report no longer hallucinates teacher name from content (e.g., "Dr. King" from MLK lessons). Name detection now searches only document headers/footers, with historical figure exclusion.
- Voice pattern detection filters out lesson content ("Life in the Trench") — only keeps actual teacher greetings.
- Curriculum KB searched automatically before every lesson generation — no longer depends on the model remembering to call search_my_materials.
- Image sourcing uses entity extraction (Louis XIV, Palace of Versailles) instead of generic lesson title queries.
- More slides get images (up to 5 instead of 3).
- Vocabulary slide filters instructional directions more aggressively.

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
