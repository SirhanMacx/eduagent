# EDUagent Platform Vision — The Full Build

## What We're Building

Not just a CLI tool. A self-improving educational intelligence platform.

**The thesis:** Every teacher's existing materials contain years of pedagogical wisdom. EDUagent extracts that wisdom, amplifies it, and feeds outcomes back into the system to make it smarter over time. The platform observes which lessons work, which formats resonate, which explanations land — and uses that signal to improve how it generates future content. Inspired by the Hyperagents paper (arXiv:2603.19461): the meta-level improvement process is itself improvable.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     EDUagent Platform                        │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Teacher UI  │  │  Student UI  │  │   Admin/Insights  │  │
│  │  (FastAPI +  │  │  (Chatbot +  │  │  (Usage, ratings, │  │
│  │  Jinja2)     │  │  Q&A)        │  │   prompt health)  │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         │                 │                    │             │
│  ┌──────▼─────────────────▼────────────────────▼──────────┐ │
│  │                   Core API (FastAPI)                    │ │
│  │  /ingest  /persona  /unit  /lesson  /materials          │ │
│  │  /chat    /feedback /improve  /export  /share           │ │
│  └──────────────────────┬──────────────────────────────────┘ │
│                         │                                     │
│  ┌──────────────────────▼──────────────────────────────────┐ │
│  │              Intelligence Layer                          │ │
│  │  PersonaEngine | UnitPlanner | LessonGen | MaterialsGen  │ │
│  │  StudentChatbot | FeedbackCollector | PromptEvolver      │ │
│  └──────────────────────┬──────────────────────────────────┘ │
│                         │                                     │
│  ┌──────────────────────▼──────────────────────────────────┐ │
│  │              Storage & State                             │ │
│  │  SQLite (teachers, lessons, feedback, prompt_versions)   │ │
│  │  Vector store (lesson embeddings for similarity search)  │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## Features to Build

### Phase 1: Web Platform (Today)
1. **FastAPI web server** — REST API + server-side rendered teacher dashboard
2. **Teacher onboarding flow** — Upload files via web UI (drag & drop), watch persona extraction happen in real-time
3. **Unit/Lesson generation UI** — Form-based interface, generated content displayed immediately
4. **Content library** — Browse, edit, export all generated units and lessons
5. **Student chatbot** — `/chat` endpoint where students ask questions about the current lesson; EDUagent answers in teacher's voice using lesson context

### Phase 2: Self-Improvement Loop
1. **Feedback collection** — Teachers rate generated content (thumbs up/down, star rating, free text notes)
2. **Outcome signals** — Track: which lessons get edited heavily (bad signal), which get used as-is (good signal)
3. **Prompt versioning** — Store prompt versions in DB with their performance metrics
4. **Prompt evolver** — Periodically analyze feedback, generate improved prompt variants, A/B test them
5. **Metacognitive layer** — The evolver can itself be evolved (Hyperagents pattern)

### Phase 3: Integrations
1. **Google Classroom export** (JSON format compatible with Classroom API)
2. **Canvas LMS export** (Common Cartridge format)
3. **PDF generation** (weasyprint, production-quality)
4. **DOCX generation** (python-docx, teacher-ready formatting)

### Phase 4: Multi-Teacher
1. **Teacher accounts** (simple username/password, no OAuth required initially)
2. **Shared content library** — Teachers in the same school can share units
3. **Persona blending** — Combine two teachers' styles for co-taught classes

---

## Build Instructions for Claude Code

### Project Structure (extend existing ~/Projects/eduagent/)

```
eduagent/
├── eduagent/
│   ├── (existing CLI modules)
│   ├── api/
│   │   ├── __init__.py
│   │   ├── server.py          # FastAPI app, all routes
│   │   ├── routes/
│   │   │   ├── ingest.py
│   │   │   ├── generate.py
│   │   │   ├── chat.py
│   │   │   ├── feedback.py
│   │   │   └── export.py
│   │   ├── templates/         # Jinja2 HTML templates
│   │   │   ├── base.html
│   │   │   ├── index.html     # Landing / onboarding
│   │   │   ├── dashboard.html # Teacher's content library
│   │   │   ├── generate.html  # Unit/lesson generation form
│   │   │   └── lesson.html    # View/edit a lesson
│   │   └── static/
│   │       ├── style.css      # Clean, minimal CSS (no frameworks)
│   │       └── app.js         # Minimal JS for form handling
│   ├── chat.py                # Student chatbot engine
│   ├── feedback.py            # Feedback collection + analysis
│   ├── improver.py            # Prompt improvement loop
│   └── database.py            # SQLite schema + queries
├── eduagent_data/             # Runtime data dir
│   ├── eduagent.db            # SQLite database
│   ├── personas/              # Saved persona JSON files
│   ├── units/                 # Generated unit JSON files
│   └── lessons/               # Generated lesson JSON files
└── tests/
    ├── test_basic.py          # (existing)
    ├── test_api.py            # API endpoint tests
    └── test_chat.py           # Chatbot tests
```

### Web UI Requirements

**Design:** Clean, teacher-friendly. White background, readable fonts (system fonts), minimal color (blue accent). NO external CSS frameworks — pure CSS. Must work on a school laptop with old Chrome.

**Dashboard page** shows:
- List of generated units with lesson count, date, subject/grade
- Quick "Generate New Unit" button
- Stats: X units generated, X lessons, X students chatted

**Generation form:**
- Topic input
- Grade dropdown (K-12)
- Subject dropdown
- Duration (weeks) slider
- Standards selector (from standards.py)
- Optional: paste existing materials directly in the browser
- "Generate" button → real-time streaming of generation progress (SSE or websocket)

**Lesson viewer:**
- Formatted lesson plan with all sections
- Edit buttons for each section (inline editing)
- Export: Download as PDF | DOCX | Markdown
- Share: Generate public link
- Rate: 👍 👎 with optional note

**Student chatbot widget:**
- Embeddable JS snippet teachers can paste into any LMS
- Simple chat interface
- Teacher sets the "active lesson" so the bot has context

### API Endpoints

```
POST /api/ingest          # Upload files, returns persona
GET  /api/persona         # Get current persona
POST /api/unit            # Generate unit plan
POST /api/lesson          # Generate single lesson
POST /api/materials       # Generate materials for lesson
POST /api/full            # End-to-end unit + all lessons + materials
POST /api/chat            # Student asks a question about a lesson
POST /api/feedback        # Teacher rates generated content
GET  /api/units           # List all generated units
GET  /api/lessons/{id}    # Get a specific lesson
GET  /api/export/{id}     # Export lesson as PDF/DOCX
GET  /api/share/{token}   # Public shareable lesson view
POST /api/improve         # Trigger prompt improvement cycle
```

### Database Schema (SQLite)

```sql
CREATE TABLE teachers (
    id TEXT PRIMARY KEY,
    name TEXT,
    persona_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE units (
    id TEXT PRIMARY KEY,
    teacher_id TEXT,
    title TEXT,
    subject TEXT,
    grade_level TEXT,
    topic TEXT,
    unit_json TEXT,
    rating INTEGER,  -- 1-5 stars
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE lessons (
    id TEXT PRIMARY KEY,
    unit_id TEXT,
    lesson_number INTEGER,
    title TEXT,
    lesson_json TEXT,
    materials_json TEXT,
    rating INTEGER,
    edit_count INTEGER DEFAULT 0,
    share_token TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE feedback (
    id TEXT PRIMARY KEY,
    lesson_id TEXT,
    rating INTEGER,  -- 1-5
    notes TEXT,
    sections_edited TEXT,  -- JSON list of which sections were changed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE prompt_versions (
    id TEXT PRIMARY KEY,
    prompt_type TEXT,  -- persona_extract, unit_plan, lesson_plan, etc.
    version INTEGER,
    prompt_text TEXT,
    avg_rating REAL,
    usage_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Chat Engine (chat.py)

The student chatbot:
1. Gets the current lesson JSON as context
2. Gets the teacher persona as system prompt
3. Answers in the teacher's voice ("Ms. Johnson would say...")
4. Knows: the lesson objectives, key concepts, vocabulary
5. Can: explain things differently, give examples, check for understanding

### Prompt Improver (improver.py)

```python
async def improve_prompts(feedback_window_days: int = 7):
    """
    Analyze recent feedback and generate improved prompt variants.
    
    1. Pull lessons with low ratings from last N days
    2. Pull teacher edit patterns (which sections get edited most)
    3. Ask LLM: "Given these examples of bad output and what teachers changed,
       how should the prompt be improved?"
    4. Generate 3 new prompt variants
    5. Store as prompt_versions with is_active=False
    6. Randomly assign new generations to test variants (A/B test)
    7. After 10 uses, promote winner to active
    """
```

### CLI additions

Add to cli.py:
- `eduagent serve` — starts the web server on localhost:8000
- `eduagent serve --port 3000 --host 0.0.0.0` — custom host/port
- `eduagent improve` — run one cycle of prompt improvement

### Quality Requirements

- All async (FastAPI + async LLM calls)
- Type hints everywhere
- Real HTML templates (not inline strings)
- CSS that actually looks good on a school computer
- Streaming generation (SSE) so teachers see progress in real-time
- Error handling that shows friendly messages in the UI
- Tests for API endpoints using httpx TestClient

### After building:

1. Run all tests — must pass
2. Run ruff check — must be clean  
3. git add -A && git commit -m "feat: web platform, student chatbot, feedback loop, prompt improver"
4. git push origin main
5. openclaw system event --text "Done: EDUagent web platform live — server, chatbot, feedback loop, self-improvement" --mode now
