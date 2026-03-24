# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.1] - 2026-03-24

### Added
- Background task queue (`eduagent/task_queue.py`) — submit long-running generation jobs (lessons, units, worksheets, assessments) and check back later
- CLI commands: `eduagent queue submit`, `eduagent queue status`, `eduagent queue list`, `eduagent queue worker`
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
