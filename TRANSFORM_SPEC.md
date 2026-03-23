# EDUagent — Full Transformation Spec

## What This Is Now

EDUagent is an **OpenClaw skill** — a teacher-facing AI assistant that lives in Telegram (and optionally the web) and feels like talking to a knowledgeable teaching partner.

Teachers don't install software. They add a bot to Telegram, send it their Google Drive link once, and from then on they just talk to it. It knows their curriculum, their teaching style, and can search the web. It generates everything they need — lesson plans, units, worksheets, assessments — in their exact voice.

**Design principle:** It should feel exactly like OpenClaw but built for teachers. Conversational, smart, zero friction.

---

## Architecture

```
Teacher's Telegram
       │
       ▼
OpenClaw Gateway (handles Telegram, routing, plugins)
       │
       ▼
EDUagent OpenClaw Skill (SKILL.md + plugin)
       │
       ├── Google Drive connector (read files once permission granted)
       ├── Local disk reader (if running locally)
       ├── Web search (via Tavily/Brave — find current events, standards docs)
       ├── LLM client (Anthropic / OpenAI / Cloud Ollama — API key only, no local install)
       ├── Persona engine (extract teaching style from files)
       ├── Generation engines (unit, lesson, materials, assessment)
       └── Storage (SQLite — personas, generated content, conversation state)
```

---

## User Experience

### First conversation:
```
Teacher: hi, I'm a teacher

EDUagent: Hey! I'm your AI teaching assistant. I can generate lesson plans,
          unit plans, worksheets, and assessments — all in your exact teaching
          voice, once you share some of your existing materials with me.

          To get started: share a link to a Google Drive folder with some of
          your lesson plans, or paste the path to a folder on your computer.

          What subject and grade do you teach?
```

### After setup:
```
Teacher: plan a unit on photosynthesis for my 8th graders, 3 weeks

EDUagent: Planning your photosynthesis unit... 🌿

          Here's the structure I'm thinking:

          **Life From Light — 3-Week Unit (8th Grade Science)**
          ...

          Does this match what you had in mind, or want me to adjust anything?
```

### With web search:
```
Teacher: find me a current news story I can use to kick off the unit

EDUagent: Found a few good ones:

          1. "Scientists track how forests responded to 2025 heat records" 
             (Nature, Jan 2026) — connects directly to photosynthesis stress
          ...
```

---

## What to Build

### 1. Transform the Python package into an OpenClaw plugin

Create `eduagent/openclaw_plugin.py`:
- Exposes a `handle_message(text: str, context: dict) -> str` function
- This is what OpenClaw calls when a teacher sends a message
- Maintains conversation state (current persona, current lesson being worked on)
- Routes intent: "plan a unit" → planner, "search for" → web_search, "generate worksheet" → materials
- Returns formatted Telegram-friendly text (no markdown tables, use bullet lists)

Create `skills/eduagent/SKILL.md` (replace existing):
```markdown
---
name: eduagent
description: AI teaching assistant for K-12 educators. Generates lesson plans,
             unit plans, worksheets, and assessments in the teacher's exact voice.
             Connects to Google Drive or local files. Use when a teacher asks for
             lesson plans, curriculum planning, assessments, or education help.
---
```

### 2. Config via conversation (no CLI wizard needed)

Teachers configure via Telegram:
```
/setup — starts guided setup conversation
/config key anthropic sk-xxxx — set API key
/config drive https://drive.google.com/drive/... — set Google Drive folder
/config path /Users/jon/Teaching/ — set local folder
/status — show current config and persona summary
```

Store config in `~/.eduagent/config.json` (same pattern as AppConfig, but driven by chat).

### 3. Google Drive integration

`eduagent/drive.py`:
- Accept a Google Drive folder URL or share link
- Use the Drive API (service account OR oauth flow — provide both options)
- Download all .pdf, .docx, .pptx files from the folder
- Cache locally in `~/.eduagent/drive_cache/`
- Re-sync on command: `/sync drive`

For teachers who can't do OAuth: accept a "Download as ZIP" from Drive and process that.

### 4. Web search

`eduagent/search.py` (already exists in workspace scripts — adapt it):
- Use Tavily API (key from config or env var)
- Functions: `search_web(query)`, `search_news(query)`, `search_standards(grade, subject)`
- Teachers trigger: "find me a news story about...", "what does NGSS say about...", "find a video on..."
- EDUagent automatically searches when generating lessons to find current, relevant examples

### 5. Clean up the CLI

Keep the CLI as a power-user interface but make it optional:
- `eduagent serve` — still works, starts the web UI (keep for teachers who prefer it)
- `eduagent chat` — starts a local terminal chat session (same logic as Telegram handler)
- `eduagent setup` — runs guided config (for headless/server installs)
- All the generation commands stay (`unit`, `lesson`, `materials`, etc.)

### 6. Telegram-optimized output formatting

The current generation outputs use markdown that doesn't render well in Telegram.

Create `eduagent/formatter.py`:
```python
def format_for_telegram(content: dict, content_type: str) -> str:
    """Format generated content for Telegram — no markdown tables, use bullets."""

def format_for_web(content: dict, content_type: str) -> str:
    """Format for web UI — full HTML."""

def format_for_export(content: dict, format: str) -> bytes:
    """Format for file download — PDF, DOCX, Markdown."""
```

### 7. Conversation state management

`eduagent/state.py`:
```python
class TeacherSession:
    teacher_id: str
    persona: TeacherPersona | None
    current_unit: UnitPlan | None
    current_lesson: DailyLesson | None
    context_stack: list  # What we're working on
    last_activity: datetime
```

Store sessions in SQLite. When a teacher says "make the exit ticket harder", the agent knows which lesson we're talking about.

### 8. Intent router

`eduagent/router.py`:
```python
INTENTS = {
    "generate_unit": [...keywords...],
    "generate_lesson": [...],
    "generate_materials": [...],
    "generate_assessment": [...],
    "web_search": ["find", "search", "what does", "news about"],
    "show_persona": ["what do you know about me", "my teaching style"],
    "setup": ["setup", "configure", "connect drive"],
    "export": ["download", "export", "pdf", "share"],
    "help": ["help", "what can you do"],
}

async def route(message: str, session: TeacherSession) -> Response:
    """Route teacher message to appropriate handler."""
```

For anything ambiguous, ask a clarifying question. Teachers shouldn't have to use specific commands.

### 9. Installation as a proper OpenClaw skill

The skill should be installable via:
```bash
clawhub install eduagent
```

Or manually: copy `skills/eduagent/` into `~/.openclaw/skills/eduagent/`

The SKILL.md should tell OpenClaw:
- When to activate (any teacher-related message)
- What tools it needs (web search, file access)
- How to configure it

---

## What to Keep from Current Codebase

- `eduagent/models.py` — all Pydantic models, keep as-is
- `eduagent/ingestor.py` — file ingestion, keep as-is
- `eduagent/persona.py` — persona extraction, keep as-is
- `eduagent/planner.py` — unit planner, keep as-is
- `eduagent/lesson.py` — lesson generator, keep as-is
- `eduagent/materials.py` — materials generator, keep as-is
- `eduagent/llm.py` — LLM client, keep as-is
- `eduagent/standards.py` — standards library, keep as-is
- `eduagent/quality.py` — quality scorer, keep as-is
- `eduagent/exporter.py` — export engines, keep as-is
- `eduagent/api/` — keep the FastAPI web server as an optional interface

## What to Add

- `eduagent/openclaw_plugin.py` — main plugin entrypoint
- `eduagent/router.py` — intent routing
- `eduagent/state.py` — conversation state
- `eduagent/formatter.py` — output formatting per channel
- `eduagent/drive.py` — Google Drive connector
- `eduagent/search.py` — web search integration
- `skills/eduagent/SKILL.md` — updated OpenClaw skill file

## Config Structure

`~/.eduagent/config.json`:
```json
{
  "provider": "anthropic",
  "anthropic_api_key": "sk-...",
  "openai_api_key": null,
  "ollama_url": "http://localhost:11434",
  "ollama_model": "llama3.2",
  "google_drive_url": null,
  "local_materials_path": null,
  "teacher_name": "Ms. Johnson",
  "default_subject": "Science",
  "default_grade": "8",
  "tavily_api_key": null
}
```

API keys stored via `keyring` (OS keychain) with fallback to config file with restricted permissions.

---

## After Building:

1. `python -m pytest tests/ -v` — all must pass
2. `python -m ruff check eduagent/ --fix` — clean
3. Update README: "EDUagent is an OpenClaw skill for teachers. Install OpenClaw, add the skill, connect your Google Drive, and start chatting."
4. `git add -A && git commit -m "feat: transform to OpenClaw skill — Telegram-native, Google Drive, web search, conversation state"`
5. `git push origin main`
6. `openclaw system event --text "Done: EDUagent transformed — OpenClaw skill, Telegram-native, Google Drive, web search" --mode now`
