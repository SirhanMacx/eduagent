# Changelog

## v4.3.2026.13 -- Maturity Push (2026-04-02)

### Documentation & Code Quality

**Architecture docs rewritten**
- `docs/ARCHITECTURE.md` fully rewritten for v4.3: accurate system diagram, entry router responsibilities, agent core flow, master content track, compilation pipeline, data storage layout, multi-provider auth chain, and curriculum wiki architecture
- Removed all references to v0.6 architecture and non-existent modules

**Model guide updated**
- `docs/CHOOSING_A_MODEL.md` updated with current model names (Claude Opus/Sonnet 4.6, GPT-5.4, Gemini 2.5 Flash/Pro)
- Added Google Gemini as a standalone option
- Replaced Qwen 3.5 with Gemma 4 as the recommended local model
- Removed all pricing information
- Ed referred to by name throughout

**Bot setup guide updated**
- `docs/BOT_SETUP.md` updated to document background auto-start behavior
- Added "How Background Auto-Start Works" section explaining the daemon lifecycle
- Removed "leave terminal open" advice (no longer needed with daemon mode)
- Ed referred to by name throughout

**Entry router docstrings**
- Added clear 2-3 line docstrings to all functions in `clawed/_entry_router.py`

**Contributing guide updated**
- `CONTRIBUTING.md` updated with command module split pattern
- Documents `clawed/commands/` directory structure and the rule that new commands go in focused modules, not in `generate.py`

## v4.2.2026.9 -- Magnum Opus (2026-04-02)

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
