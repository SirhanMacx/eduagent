# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [2.5.2] - 2026-04-01

Production-quality output release. Every teacher gets professional PPTX with real images, clean handouts, and working games.

### Added
- **Web scraping image source** — DuckDuckGo image search finds specific educational images (diagrams, maps, portraits) without API keys. Most comprehensive source in the pipeline.
- **5-source image pipeline** — teacher files, web scrape, Library of Congress, Wikimedia Commons, Unsplash. All enabled for all subjects. Teacher images always first.

### Changed
- **All generation routes to Opus (DEEP tier)** — every lesson, unit, assessment, game, and evaluation uses maximum intelligence. No more routing to weaker models. Default fallback also DEEP.
- **Handout is the default export format** — `clawed lesson` produces student-facing DOCX handout by default (was markdown).
- **Game compiler forces Opus** — games require code-capable models. Opus produces valid, interactive HTML every time.

### Fixed
- **Answer keys stripped from student handouts** — (Answer: X), Answer: ..., Expected: ... patterns removed from guided_practice and independent_work. Students never see answer keys.
- **Game HTML structure repair** — detects bare JavaScript not wrapped in script tags, strips duplicate DOCTYPE, wraps properly. Games render and play instead of showing blue screens.
- **Image relevance filtering** — eliminates irrelevant/dangerous images, anchors slide positions, extends verb blocklist for search queries.
- **Multi-agent pipeline config** — passes AppConfig correctly, handles None task_models.
- **PPTX crash fixes** — topic-map queries, slide positioning, presentation bug fixes.

## [2.5.1] - 2026-04-01

Interactive learning games and community gallery.

### Added
- **Interactive HTML learning games** — `clawed game create` generates unique single-file HTML games from lesson content. Every game is designed by the LLM from scratch — no templates, no repetition. Games use Three.js for 3D, work on phones/Chromebooks.
- **Student preference input** — `--students "they love Minecraft"` tells the LLM to design the game mechanic around what students are into.
- **Game style hints** — `--style "escape room"` gives creative direction.
- **`--game` flag on lesson command** — generate a game alongside any lesson.
- **`clawed game gallery`** — view all generated games locally.
- **Community Game & Lesson Gallery** — https://sirhanmacx.github.io/Claw-ED/games — browse and share games by grade, subject, topic. Teachers submit games via Discussions.
- **Gallery schema** — organized by type (game/lesson), grade, subject, topic, author.

## [2.5.0] - 2026-04-01

Teacher-first release — onboarding for any teacher, not just developers.

### Added
- **Google Gemini as primary onboarding option** — free tier, simplest setup for teachers
- **Demo mode in onboarding** — try Claw-ED without any API key
- **Differentiation enforcement** — 3-4 specific IEP/504 accommodations, 3-4 ELL scaffolds, 3-4 gifted extensions per lesson. No more generic "provide extra time"
- **RLHF auto-posting** — every generated lesson auto-posts to Starwisp for teacher feedback
- **Sirhan lesson-generator cron** — lesson engine generates 2 lessons/day from 26K curriculum files
- **Bob regents-prep cron** — daily lesson generation targeting closest Regents exam date

### Changed
- **Multi-agent generation is now default** (--single-agent flag for speed)
- **Cost messaging fixed** — Claude ~$0.10/lesson, GPT ~$0.15/lesson (was incorrectly showing ~$20+)
- **OpenRouter removed from onboarding** — banned per fleet policy, was confusing teachers
- **X outreach disabled** — not producing value without API credentials
- **Autonomous-growth reduced 6x→2x daily** — quality over quantity
- **Fleet crons optimized** — disabled 5 never-fired jobs, focused remaining jobs on value production

### Fixed
- Differentiation gap — lessons were scoring 2/5 on differentiation axis, prompt now enforces specific accommodations
- Onboarding cost copy — $20+/lesson was wrong, scared away teachers
- Fleet node thread delivery — 23 cron jobs on 3 machines were delivering to deleted Starwisp threads

## [2.4.0] - 2026-04-01

Fleet upgrade release — all 4 nodes producing autonomously, self-monitoring, self-improving.

### Added
- **Fleet-doctor daemon** — auto-checks all nodes every 6h, restarts dead gateways, re-syncs stale tokens, posts health reports to Starwisp
- **Regents prep auto-generation** — daily cron on Bob generates next-needed lesson based on curriculum state and Regents countdown
- **Quality review cron on Amber** — scores new lessons against 20-criterion rubric, flags anything below 56/80
- **Differentiation pack cron on Amber** — creates ELL/IEP/gifted variants for each new lesson
- **ArXiv scout cron on Bob** — daily AI/edtech research scan, posts findings to Starwisp Research thread
- **Voice scoring in CLI** — `clawed lesson` now shows voice match score after generation
- **Multi-agent teams rewritten** — replaced broken open-multi-agent with direct Anthropic SDK orchestration. 4 teams (coordinator, lesson, curriculum, quality) all functional
- **Token sync v2** — file-locked, validates token before pushing, auto-restarts dead gateways

### Changed
- Default export format: `docx` (was `markdown`). Jon's explicit requirement.
- All fleet machines now have Claw-ED v2.4.0 installed (Amber and Sirhan newly provisioned)
- Fleet-token-sync validates token with Haiku API call before distributing
- OpenRouter references removed from onboarding.py fallback

### Fixed
- Multi-agent teams.mjs import drift (open-multi-agent API changed, rewrote with @anthropic-ai/sdk)
- OAuth headers in multi-agent runner (was missing Claude Code identity headers)
- Sub-agent permission propagation (background agents now use direct execution instead of spawning)

## [2.3.9] - 2026-03-31

Multi-agent lesson generation, Claude Code integration, and continuous improvement pipeline.

### Added
- **Multi-agent lesson generation** — `--multi-agent` flag on `clawed lesson` and `clawed full`. Three specialized agents collaborate: Researcher (finds primary sources and context) → Writer (drafts MasterContent in teacher's voice) → Reviewer (scores quality, requests revision if any dimension < 7/10). Falls back to single-agent on error. New module: `clawed/multi_agent.py`.
- **Claude Code OAuth credential resolution** — `get_api_key("anthropic")` now auto-reads fresh tokens from `~/.claude/.credentials.json`. Eliminates expired-token errors when Claude Code is installed. Tokens are auto-refreshed by Claude Code.
- **`clawed train` command** — continuous improvement pipeline for fleet agents:
  - `--drive`: ingest from configured Google Drive folders, refine persona incrementally
  - `--path`: ingest from local curriculum files
  - `--benchmark -n N`: generate N lessons and score quality (voice, pedagogy, differentiation)
  - `--full`: drive ingest + benchmark in sequence
  - Saves training reports to `~/.eduagent/training/` as JSON
- **Incremental persona refinement** — `merge_persona()` in `persona.py` merges new persona traits with existing ones (union + dedup lists, preserve core identity). No more overwriting voice markers on re-ingest.
- **Multi-agent prompt templates** — `prompts/multi_agent_researcher.txt` (source finding, InSPECT analysis) and `prompts/multi_agent_reviewer.txt` (3-dimensional quality scoring rubric).

### Fixed
- **OAuth authentication** — all three Anthropic code paths (`agent.py`, `llm.py`, `config.py`) now detect OAuth tokens (`sk-ant-oat01-*`) and send `Authorization: Bearer` + Claude Code identity headers instead of `x-api-key`. Fixes 401 errors with Claude Code and Hermes OAuth tokens.
- **Transport test mocks** — `test_openclaw_transport.py` now patches `clawed.transports.hermes._get_gateway` (where the actual code lives) instead of the backward-compat shim. Fixes 3 of 4 previously failing tests.

### Changed
- Config: `teacher_profile.drive_urls` now populated with Jon's 25-26 Google Drive folder.
- Secrets: corrected Ollama API key format, updated Telegram bot token.

## [2.3.8] - 2026-03-30

NLAH contract alignment — explicit failures replace silent swallowing, quality gates fail closed.

### Added
- **NLAH failure taxonomy** — 13 structured failure codes (`FailureCode` enum) in `clawed/failure_codes.py`. All generation failures now report machine-parseable codes.
- **`CLAWED_DEMO=1` env var** — force demo mode regardless of stored API keys.
- **Voice match scoring** — `score_voice_match()` in `clawed/quality.py` scores lesson text against teacher persona (1.0-5.0). Logged as VOICE_MISMATCH warning if < 3.0.
- **`run_async_safe()` shared utility** — extracted from duplicated code in `export_pptx.py` and `export_docx.py` to `clawed/async_utils.py`.
- **Quality review in bundle pipeline** — `generate_lesson_bundle` now calls `review_lesson_package()` and `score_voice_match()` after compilation (NLAH Stage 4, non-blocking).
- **25 new tests** — failure codes, async utils, quality review fail-closed, NLAH validation gates, voice match, demo mode override, onboarding validation.

### Changed
- **Quality review fails closed** — `review_lesson_package()` now catches all exceptions (including LLM call failures) and returns `passed: False`. Completes the v2.3.5 fix which only handled parse errors.
- **Silent exceptions → explicit warnings** — `generate_lesson_bundle` now logs persona parse failures, KB search failures, and asset search failures at WARNING level with NLAH failure codes.
- **Onboarding input validation** — teacher name truncated to 100 chars with character filtering, grade validated as K/PK/1-12 with re-prompt on invalid input, subject truncated to 100 chars. Workspace init failures logged.
- **NLAH validation gates enforced** — `validate_master_content()` now requires guided_notes >= 6, primary_sources >= 2 (with non-empty text), exit_ticket questions >= 3. Topic drift check extended to include objective field.
- **SOUL.md path from config** — `lesson.py` and `agent_core/core.py` now use `EDUAGENT_DATA_DIR` env var instead of hardcoded `~/.eduagent/workspace/SOUL.md`.

### Fixed
- **Nested asyncio.run() in background ingest** — `generation.py` background thread now uses `run_async_safe()` instead of bare `asyncio.run()`, preventing RuntimeError on Python 3.12+.
- **GenerationReport timing** — Report now instantiated before persona/KB/asset search blocks so early warnings are captured.

## [2.3.7] - 2026-03-29

Image pipeline hardening, background ingestion, DEEP-tier model routing, security fixes, search improvements, 12 new file formats.

### Added
- **Progress notifications for lesson generation** — Telegram bot sends "Working on your lesson materials for [topic] — this usually takes 2-4 minutes!" before starting long-running generation.
- **Progress notifications for file ingestion** — Immediate acknowledgment on file upload, periodic updates ("Indexed 50/200 documents..."), and completion summary. Wired through `AgentContext.notify_progress()`.
- **Background ingestion threading** — File ingestion runs in a background thread (non-daemon). Bot returns immediately and stays responsive while indexing. Completion message sent via progress_callback.
- **`master_content` task type in model router** — MasterContent generation routes to DEEP tier instead of WORK tier.
- **12 new file formats for ingestion** — `.doc`, `.ppt`, `.xls`, `.xlsx`, `.csv`, `.rtf`, `.html`, `.htm`, `.odt`, `.odp` now supported alongside existing formats. Uses `textutil` (macOS), `openpyxl`, stdlib `csv`, `HTMLParser`, and ODF XML extraction with graceful fallbacks.
- **Topic tag extraction** — Assets now get auto-generated `topic_tags` from filename and content keywords during ingestion. Tags are searchable.
- **Cross-transport search fallback** — If `search_my_materials` finds nothing for the current teacher_id, it falls back to searching all teachers. Fixes materials ingested via CLI not appearing in Telegram searches.
- **Image cache cleanup** — Cached images older than 30 days are automatically pruned on session start. Prevents unbounded disk growth.
- **Concurrent ingestion limit** — Max 3 simultaneous ingestion threads via semaphore. Additional uploads are queued with a friendly message.
- **ZIP bomb protection** — Decompressed size checked before extraction (500 MB limit).

### Changed
- **MasterContent uses DEEP-tier model** — `generate_master_content()` and `generate_lesson()` default to `task_type="master_content"` (DEEP tier). Dramatically better output with capable models.
- **Image specs REQUIRED for all subjects** — Prompt updated: `image_spec` is mandatory for every `primary_source` and `direct_instruction` section across all subjects (not just Science/Social Studies). Includes good/bad examples and guidance on writing effective specs.
- **Political cartoon handling** — Explicit rules requiring detailed visual descriptions. Emoji and Unicode art banned.
- **Enhanced teacher image matching** — Three-stage progressive broadening: full query → individual keywords → subject fallback. Filename matches weighted higher. Scores up to 150 candidates.
- **Subject-aware image pipeline** — Subject flows through the entire chain: `image_pipeline.py` → `slide_images.py` → teacher image search, enabling subject-specific prioritization.
- **Image fetch timeout** — Per-image timeout bumped from 10s to 15s.
- **TF-IDF vocabulary capped at 10,000 tokens** — Prevents unbounded memory growth after ingesting large corpora. New tokens beyond the cap are treated as unknown.
- **KB search limit raised to 5,000 chunks** — Improved recall for larger knowledge bases.
- **Model router updated** — Anthropic tier defaults updated to current model IDs (Haiku 4.5, Sonnet 4.6, Opus 4.6).
- **Removed unused `anthropic` and `openai` dependencies** — ~50MB+ lighter install. The codebase uses raw httpx for all API calls.
- **API key resolution unified** — `llm.py` now uses `config.get_api_key()` (env var + keyring + secrets file) instead of only checking env vars. Teachers who stored keys via onboarding no longer hit key-not-found errors.
- **Agent prompt strengthened** — Explicit instruction: "If search_my_materials returns results, you MUST list them for the teacher. NEVER say 'I didn't find anything' if the tool returned materials."

### Fixed
- **Empty slideshows** — Root cause: LLM leaving `image_spec` empty. Now required with specific search term examples and Pydantic validation warnings.
- **Search results not surfaced (BUG 6)** — Three fixes: cross-transport teacher_id fallback, asset search error logging (was silently swallowed), and explicit prompt instruction to relay results.
- **93% of files missing from search (BUG 7)** — `SUPPORTED_EXTENSIONS` expanded from 8 to 20 formats. Legacy `.doc`, `.ppt`, `.xls`, `.rtf`, `.html`, `.odt`, `.odp`, `.csv`, `.xlsx` now parsed.
- **Empty topic_tags (BUG 8)** — Tags now auto-extracted from filename and content during asset registration and included in search scoring.
- **Bot unresponsive during ingestion** — Background threading with immediate return.
- **Duplicate notification on file upload** — Removed early Telegram ack; IngestHandler response is the sole notification.
- **Legacy gateway silent ingestion** — `progress_callback` now threaded through `_legacy_gateway.handle()` → `_dispatch()` → `IngestHandler.handle()`.
- **Per-file error resilience** — Individual file parse failures no longer abort the entire ingestion. Failed files are logged and counted in the completion summary.
- **httpx thread safety** — Background ingestion progress callbacks use a fresh `httpx.Client` per message instead of sharing the polling thread's client.
- **dashboard_password** — Added to `_SECRET_FIELDS` so it's stripped from plaintext config.

### Security
- **Path traversal in `read_workspace`** — Added `.resolve()` + containment check. Filenames like `../../etc/passwd` are now blocked.
- **`read_file` path bypass** — Replaced string prefix check with resolved path containment.
- **Unrestricted ingest paths** — `ingest_materials` tool now restricted to home directory with 500-file cap.
- **XSS in lessons page** — All LLM-generated content escaped with `html.escape()` before HTML rendering.
- **TOOL_DEFINITIONS race condition** — Module-global monkey-patching now protected by threading.Lock.
- **Debug info exposure** — Exception class names and messages no longer leaked to users. Errors logged server-side only.

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
