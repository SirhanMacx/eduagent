# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

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
