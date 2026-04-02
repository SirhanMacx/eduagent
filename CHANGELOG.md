# Changelog

## v4.2.2026.9 — Magnum Opus (2026-04-02)

### The Full Teaching Assistant Transformation

**Startup & Identity**
- Educational startup animation with gold/green/cream palette and apple logo
- "Claw-ED — Your AI co-teacher" identity throughout
- Zero "Claude Code" branding in any user-facing output

**AI Behavior**
- System prompt completely rewritten for teaching (pedagogy, standards, differentiation, Bloom's taxonomy)
- 14 teaching tools prioritized in tool array with searchHint metadata
- First-run agentic onboarding guides teachers through setup conversationally

**Multi-Provider Support**
- Python bridge routes non-Anthropic API calls (OpenAI, Google Gemini, Ollama)
- TypeScript bridge client with timeout, abort, and error handling
- Auth system bypasses OAuth for non-Anthropic providers, reads from ~/.eduagent/config.json

**Curriculum Ingestion**
- ODT/ODP: proper XML parsing with ElementTree (replaces naive tag stripping)
- XLS: 3-strategy extraction (xlrd → textutil → openpyxl)
- Corpus contribution wired into every ingest
- Topic tag extraction from filename + headings + content analysis
- DuckDuckGo VQD: retry logic with exponential backoff, 4th regex pattern

**Quality**
- 1673 tests passing, 0 failures
- Ruff clean across all modified files
- Lazy asyncio.Queue init for Python 3.9 compatibility
- Google model default aligned (gemini-2.5-flash) across TS and Python

## v4.2.2026.8 (2026-04-01)

- Re-enabled Ink TUI as primary UX
- Python CLI as fallback

## v4.2.2026.7 (2026-03-31)

- Python CLI as primary UX
- Hermes fleet overhaul
