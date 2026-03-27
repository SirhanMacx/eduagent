<p align="center">
  <h1 align="center">Claw-ED</h1>
  <p align="center"><strong>Your AI teaching partner.</strong></p>
  <p align="center">An agentic AI that learns your curriculum, generates lessons in your voice, and works alongside you — not just for you.</p>
</p>

<p align="center">
  <a href="https://pypi.org/project/clawed/"><img src="https://img.shields.io/pypi/v/clawed?color=blue" alt="PyPI"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.10+-blue" alt="Python 3.10+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green" alt="MIT License"></a>
  <a href="https://github.com/SirhanMacx/Claw-ED/stargazers"><img src="https://img.shields.io/github/stars/SirhanMacx/Claw-ED" alt="GitHub stars"></a>
</p>

<p align="center">
  <a href="#-getting-started">Quickstart</a> · <a href="FEATURES.md">Features</a> · <a href="ROADMAP.md">Roadmap</a> · <a href="CONTRIBUTING.md">Contributing</a>
</p>

---

## Your curriculum files are the database

Most AI tools for teachers generate content from scratch. Claw-ED does something different: **your uploaded lesson plans, handouts, and materials become a searchable knowledge base that the agent consults every time it generates.**

Upload your files once. The embedding model chunks every document into searchable sections and stores them in a local semantic database. When you ask for a lesson on the Civil War, Claw-ED doesn't start from nothing — it searches your own prior work first, finds your 2024 unit plan, references your vocabulary choices, and builds on what you've already created.

```
Your files (PDFs, DOCX, PPTX, TXT)
        |
        v
  Embedding model chunks + indexes every document
  (Ollama mxbai-embed-large, or TF-IDF fallback)
        |
        v
  Curriculum Knowledge Base (local SQLite)
  -- 500-word chunks with semantic embeddings
  -- Deduplicated, searchable by topic
  -- Teacher-isolated (your files, your data)
        |
        v
  Agent searches YOUR materials before every generation
  "Found 3 related lessons from your files. Building on those now..."
```

**This is the difference.** Your AI partner knows your curriculum because it has read every file you've shared.

---

## What is Claw-ED?

Not a chatbot. Not a template library. A teaching colleague that lives inside your computer — one that knows your style, your standards, your students, and takes initiative.

```
You: "Prep my week"

Claw-ED:
  Searching your curriculum files for Week 3 content...
  Found your Civics pacing guide and last year's Bill of Rights unit.
  Generating 5 lessons grounded in your materials...
  Exporting to PPTX and DOCX...
  Done! 5 lesson plans + slides attached.

  I noticed you don't have an assessment for this unit yet.
  Want me to create a quiz covering amendments 1-10?
```

You name it. You teach it your style. It gets better every week.

---

## Getting Started

```bash
pip install clawed
clawed
```

Setup takes 30 seconds:
1. **Pick your AI provider** — Ollama Cloud, Google Gemini, Claude, or GPT
2. **Authenticate** — paste an API key, or sign in with your Google account (browser OAuth)
3. **Choose your interface** — Telegram bot (recommended), terminal, or web dashboard
4. **Name your agent** — it goes by Claw-ED, but you can call it anything: Sage, Coach, your department mascot

Then send it your lesson plans. It learns your voice and builds your curriculum knowledge base.

### Which AI provider?

| Provider | Auth | Cost | Best for |
|----------|------|------|----------|
| **Ollama Cloud** (recommended) | API key | $20/month flat | Daily use — unlimited lessons |
| **Google Gemini** | API key or browser sign-in | Free tier / pay-as-you-go | Teachers with Google accounts |
| **Anthropic Claude** | API key | ~$20+/lesson | Best output quality |
| **OpenAI GPT** | API key | ~$20+/lesson | Best output quality |
| **Local Ollama** | None (free) | Free | Privacy-first, runs on your machine |

**Switch providers anytime:** `clawed setup --reset`

### Interfaces

| Method | Command |
|--------|---------|
| **Terminal chat** | `clawed` or `clawed chat` |
| **Web dashboard** | `clawed serve` |
| **Telegram bot** | `clawed bot` (token saved during setup) |
| **Full-screen TUI** | `pip install 'clawed[tui]'` then `clawed tui` |
| **Student bot** | Students join with class codes, ask questions in your voice |
| **MCP server** | Expose tools to any AI agent |
| **REST API** | Custom integrations via `clawed serve` |

---

## How it works

### 1. Upload your curriculum

Send Claw-ED your lesson plans, handouts, unit plans, slides — anything you've created. It reads them and learns two things:

- **Your teaching fingerprint** — style, tone, vocabulary, structure, assessment preferences
- **Your curriculum content** — every document gets chunked, embedded, and indexed into a searchable knowledge base

### 2. Talk naturally

Tell it what you need. The agent decides which tools to call:

- "Plan a 2-week unit on WWI for my 10th graders"
- "Make a quiz on chapter 5"
- "What standards haven't I covered yet?"
- "Find what I taught about photosynthesis last year"

### 3. It works, you teach

The agent searches your files, generates content grounded in your materials, exports professional DOCX/PPTX files, and suggests what to do next. You give feedback. It gets better.

---

## Architecture

Claw-ED is agent-first. Natural-language messages go through an LLM that decides which tools to call. Deterministic operations (file ingestion, onboarding, approvals) bypass the agent for reliability.

```
Teacher's message (Telegram, CLI, TUI, Web)
        |
    Gateway
    |-- Control Plane (deterministic: files, callbacks, onboarding)
    |-- Agent Loop (LLM decides -> calls tools -> returns result)
              |
        25 Tools (auto-discovered)
              |
        Curriculum KB     Memory (3-layer)     Standards (50 states)
        search_my_materials  identity             CCSS, NGSS, C3
        ingest_materials     curriculum state      state-specific
                             episodic (embeddings)  gap analysis
              |
    Professional exports (DOCX, PPTX, PDF, Google Slides/Docs)
```

### 25 agent tools

| Category | Tools |
|----------|-------|
| **Curriculum KB** | `search_my_materials`, `ingest_materials` |
| **Generation** | `generate_lesson`, `generate_unit`, `generate_materials`, `generate_assessment` |
| **Standards** | `search_standards`, `curriculum_map`, `gap_analysis` |
| **Export** | `export_document` |
| **Google Drive** | `drive_upload`, `drive_create_slides`, `drive_create_doc`, `drive_list`, `drive_organize`, `drive_read` |
| **Profile** | `configure_profile`, `switch_model` |
| **Safety** | `request_approval`, `schedule_task` |
| **Student** | `student_insights` |
| **Communication** | `parent_comm`, `sub_packet`, `search_lessons` |

### 3-layer cognitive memory

| Layer | What it stores | Powered by |
|-------|---------------|------------|
| **Identity** | Teaching style, subject, grades, voice samples | Persona extraction |
| **Curriculum** | Current unit, pacing state, what's been covered | SQLite |
| **Episodic** | Past interactions, semantic recall | Embedding model (Ollama / TF-IDF) |
| **Curriculum KB** | Every uploaded file, chunked and searchable | Embedding model + SQLite |

### Safety guardrails

- **Approval gates** for consequential actions (publishing, sharing with students)
- **Never auto-approved:** Student-facing output, Drive publishing — always requires teacher review
- **Autonomy progression:** After 10+ consistent approvals, agent offers to auto-approve routine actions
- Closed feedback loop: ratings improve future generation

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full breakdown.

---

## What it can do

### Generation — in your voice
- Unit plans, daily lessons, worksheets, assessments, rubrics
- IEP/504 accommodations and differentiation (struggling, advanced, ELL)
- Substitute teacher packets and parent communications
- Professional PPTX slides with academic images and section dividers
- Polished DOCX with headers, footers, and IEP/ELL callout boxes

### Standards — 50 states
- CCSS, NGSS, C3, and state-specific frameworks
- Curriculum gap analyzer
- Standards search by subject and grade

### Agent behavior
- **Search-first:** Agent searches your curriculum files before generating
- **Status narration:** "Searching your files... Found 3 related lessons. Generating now..."
- **Proactive suggestions:** "I made your lesson. Want me to create a matching worksheet?"
- **Custom naming:** Your agent, your name — Sage, Coach, whatever feels right
- Multi-step planner for complex requests ("prepare my week")
- Custom teacher tools via YAML — no code needed
- Proactive scheduling — morning prep, weekly planning, feedback digests

---

## Commands

| Command | What it does |
|---------|-------------|
| `clawed` | First run: setup. Returning: chat with your agent |
| `clawed chat` | Terminal chat |
| `clawed serve` | Web dashboard |
| `clawed bot` | Telegram bot |
| `clawed ingest <path>` | Add files to your curriculum knowledge base |
| `clawed unit "Topic" -g 8 -s "Subject"` | Generate a unit plan |
| `clawed lesson "Topic" -g 8 -s "Subject"` | Generate a lesson |
| `clawed lesson "Topic" --format pptx` | Export as PowerPoint |
| `clawed standards list -g 8 -s math` | Browse standards |
| `clawed gap-analyze -s "Math" -g 8` | Find curriculum gaps |
| `clawed demo` | See example output (no API key needed) |
| `clawed setup --reset` | Re-run setup wizard |

Run `clawed --help` for the full list.

---

## Installation

```bash
pip install clawed                    # Everything you need
pip install 'clawed[tui]'             # + Full-screen terminal chat
pip install 'clawed[voice]'           # + Voice note transcription
pip install 'clawed[google]'          # + Google Drive integration
pip install 'clawed[all]'             # Everything

# Requires Python 3.10+
```

---

## Privacy & Compliance

- **Your files stay on your machine** unless you choose a cloud LLM provider
- **Curriculum knowledge base is local** — SQLite database on your disk, never uploaded
- **API keys stored in OS keychain** (macOS Keychain, Linux Secret Service, Windows Credential Manager)
- **OAuth tokens stored with restrictive permissions** (0600)
- **No telemetry, no data collection, no accounts**
- **Student bot transparency:** Clearly labeled as AI — students know they're talking to an assistant
- **Not yet FERPA/COPPA certified.** Do not use with real student PII until district-level controls ship (v1.0). Use with your own lesson materials and anonymized content.
- **Cloud disclaimer:** When using cloud AI providers, lesson prompts are sent to their APIs. Review your provider's data policy. For maximum privacy, use local Ollama.

---

## Roadmap

| Version | Status | What's in it |
|---------|--------|-------------|
| **v0.9.20** | **Current** | Curriculum knowledge base, custom agent naming, Google Gemini + browser OAuth, professional exports, agentic personality, 25 tools |
| **v1.0.0** | Planned | District deployment — admin dashboard, SSO, RBAC, FERPA/COPPA compliance |

See [ROADMAP.md](ROADMAP.md) for details.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Subject matter experts welcome — if you know how great lessons are structured in your subject, open a PR.

## License

MIT. Open source. Free forever.

---

**Built by a teacher.** Claw-ED was created by **Mr. Mac** — 9 years teaching Social Studies in Long Island, NY. Not a startup's idea of what teachers need. A tool built by someone who writes lesson plans every week and got tired of starting from scratch.

**This is bigger than one teacher.** Every educator deserves an AI partner that knows their curriculum and respects their craft. Claw-ED is the agentic layer for education — open source, teacher-owned, and built to scale to every classroom in the world.

<p align="center">
  <strong>If Claw-ED saves you time, <a href="https://github.com/SirhanMacx/Claw-ED/stargazers">star it on GitHub</a></strong> so other teachers can find it.
</p>
