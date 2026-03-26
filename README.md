<p align="center">
  <h1 align="center">Claw-ED</h1>
  <p align="center"><strong>Your AI teaching partner.</strong></p>
  <p align="center">An agentic AI that learns your teaching style, generates lessons in your voice, and handles the work so you can focus on your students.</p>
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

## What is Claw-ED?

Claw-ED is an AI agent for teachers. Not a chatbot. Not a template library. An agent that knows your teaching style, your standards, your students — and acts on that knowledge.

```
You: "Prep my week"

Claw-ED:
  → Checks your curriculum map (8th grade Civics, Week 3: Bill of Rights)
  → Generates 5 differentiated lessons in your voice
  → Creates worksheets, assessments, and slides
  → Exports to PPTX, DOCX, or PDF
  → [Coming v0.7] Uploads to your Google Drive
  → Asks: "Period 3 struggled with amendments last week. Want me to add a reteach?"
```

It learns from your existing lesson plans, aligns to your state's standards, and gets better every time you give feedback.

---

## How it works

```
Your lesson plans (PDFs, DOCX, PPTX, TXT)
        ↓
Claw-ED reads them and learns your teaching fingerprint:
  • Teaching style (inquiry-based, direct instruction, Socratic...)
  • Structural preferences (Do Nows, exit tickets, AIM questions...)
  • Vocabulary level and tone
  • Assessment approach
        ↓
You talk to it naturally — it decides what tools to use:
  • "Plan a 2-week unit on WWI for my 10th graders"
  • "Make a quiz on chapter 5"
  • "Export yesterday's lesson as slides"
  • "What standards haven't I covered yet?"
        ↓
Claw-ED acts — generates content, searches standards, exports files
        ↓
You teach. You give feedback. It improves.
```

### Real output

Generated for an 8th grade Social Studies class studying the American Revolution:

**Unit plan:**

```
Unit: "Liberty and Loyalty: The American Revolution"
Duration: 2 weeks (10 lessons)

Essential Questions:
  1. Was war inevitable?
  2. What defines freedom?
  3. How do ideas change the world?
  4. When is rebellion justified?
```

**Lesson 1 — Do Now (verbatim from generation):**

> Alright, friends, as you settle in, I want you to take out your notebook and answer this question on the board: 'What does freedom mean to you? Is there ever a time when following the rules is more important than being free?' Take 5 minutes to jot down your honest thoughts. There are no wrong answers here; I just want to hear your voice.

Every lesson includes differentiation, exit tickets, and homework — all in the teacher's voice.

---

## Getting Started

```bash
pip install clawed
clawed
```

That's it. Claw-ED walks you through setup in 60 seconds:
1. **Pick your AI provider** — we recommend Ollama Cloud ($20/month flat rate)
2. **Meet your agent** — it introduces itself and asks about you: name, subject, grade, state
3. **Share your files** (optional) — point it at a folder and it learns your voice

### Other ways to use it

| Method | Command |
|--------|---------|
| **Terminal chat** | `clawed` or `clawed chat` |
| **Web dashboard** | `clawed serve` → open `http://localhost:8000` |
| **Full-screen TUI** | `pip install 'clawed[tui]'` → `clawed serve &` → `clawed tui` |
| **Telegram bot** | `clawed bot --token YOUR_TOKEN` ([setup guide](docs/BOT_SETUP.md)) |
| **Student bot** | Students join with class codes, ask questions in your voice |

---

## Architecture

Claw-ED is agent-first. Every natural-language message goes through an LLM that decides which tools to call. Deterministic operations (file ingestion, onboarding, button callbacks) bypass the agent for reliability.

```
Teacher's message (Telegram, CLI, TUI, Web)
        ↓
    Gateway
    ├── Control Plane (deterministic: files, callbacks, onboarding)
    └── Agent Loop (LLM decides → calls tools → returns result)
              ↓
        21 Tools
        generate_lesson · generate_unit · generate_materials
        generate_assessment · search_standards · export_document
        ingest_materials · configure_profile · request_approval
        search_lessons · curriculum_map · gap_analysis
        sub_packet · parent_comm · drive_upload · drive_list
        drive_organize · drive_create_slides · drive_create_doc
        drive_read · schedule_task
              ↓
    GatewayResponse → Teacher sees the result
```

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full breakdown.

---

## What it can do

### Generation
- Unit plans, daily lessons, worksheets, assessments, rubrics — all in your voice
- IEP/504 accommodations and differentiation (struggling, advanced, ELL)
- Substitute teacher packets and parent communications
- PPTX slides with academic images, DOCX handouts, PDF exports

### Standards
- 50-state standards alignment (CCSS, NGSS, C3, state-specific frameworks)
- Curriculum gap analyzer — find what you haven't covered yet
- Standards search — look up specific standards by subject and grade

### Agent capabilities
- Agent-first gateway — LLM decides what tools to call, no hardcoded routing
- 21 typed tools auto-discovered from the tool registry
- Approval gates — agent asks before consequential actions
- 3-layer cognitive memory — identity, curriculum state, episodic recall
- Google Drive integration — upload, list, organize, native Slides/Docs, read
- Proactive scheduling — automated morning prep, weekly planning, feedback digests
- Custom teacher tools — define your own tools in YAML, no code needed
- Multi-step planner — "prepare my week" decomposes into sequential tool calls

### Surfaces
- Terminal chat, full-screen TUI, web dashboard, Telegram bot
- Student chatbot — students join with class codes, ask questions, get answers in your voice
- MCP server — expose tools to any AI agent
- REST API for custom integrations

### Coming next

| Version | What's coming |
|---------|--------------|
| **v0.8.0** *(current)* | Proactive scheduling, custom teacher tools, multi-step planner, native Slides/Docs, 21 tools |
| **v0.9.0** | Autonomy progression, closed loop (plan → generate → publish → feedback → reteach) |
| **v1.0.0** | District deployment with admin dashboard and SSO |

---

## Commands

| Command | What it does |
|---------|-------------|
| `clawed` | First run: setup. Returning: drops into chat with your agent |
| `clawed chat` | Terminal chat |
| `clawed tui` | Full-screen TUI chat (connects to running gateway) |
| `clawed serve` | Web server — dashboard, onboarding wizard, API |
| `clawed bot --token TOKEN` | Telegram bot |
| `clawed ingest <path>` | Learn from your lesson plans |
| `clawed unit "Topic" -g 8 -s "Subject"` | Generate a unit plan |
| `clawed lesson "Topic" -g 8 -s "Subject"` | Generate a single lesson |
| `clawed lesson "Topic" --format pptx` | Export as PowerPoint, Word, or PDF |
| `clawed standards list -g 8 -s math` | Browse your state's standards |
| `clawed gap-analyze -s "Math" -g 8` | Find curriculum gaps |
| `clawed demo` | See example output (no API key needed) |

Run `clawed --help` for the full list.

---

## Installation

```bash
pip install clawed                    # Everything you need
pip install 'clawed[tui]'             # + Full-screen terminal chat (Textual)
pip install 'clawed[voice]'           # + Voice note transcription
pip install 'clawed[all]'             # Everything

# Requires Python 3.10+
```

### Which AI provider?

Claw-ED works with any provider. The setup wizard walks you through it.

**We recommend [Ollama Cloud](https://ollama.com)** — $20/month Pro subscription gives you API access to dozens of models with a flat rate. No per-token billing, no surprises. Great for experimenting with different models to find what works best for your subject.

| Provider | Best models | Cost | Best for |
|----------|------------|------|----------|
| **Ollama Cloud** (recommended) | qwen3.5, deepseek-v3.2, nemotron, llama4, minimax-m2.7 | $20/month flat | Daily use, experimenting with models |
| **Anthropic** | Claude Opus 4.6, Claude Sonnet 4.6 | ~$20+/lesson | Best output quality, expensive |
| **OpenAI** | GPT-5.4, o3 | ~$20+/lesson | Best output quality, expensive |

Claude and GPT produce the best lesson output, but frontier model pricing is steep — a single lesson with differentiation and materials can cost $20 or more in API calls. Ollama Cloud lets you generate as much as you want for a fixed $20/month.

**Switch models anytime:**

```bash
clawed config set-model ollama        # use Ollama Cloud
clawed config set-model anthropic     # use Claude
clawed config set-model openai        # use OpenAI
```

Teachers are encouraged to experiment — try different models and see which one writes lessons closest to your voice.

---

## Privacy

- **Your files stay on your machine** unless you choose a cloud LLM
- **API keys stored in OS keychain** when `keyring` is installed, otherwise in `~/.eduagent/` with restrictive permissions
- **No telemetry, no data collection, no accounts**

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Subject matter experts welcome — if you know how great lessons are structured in your subject, open a PR.

## License

MIT. Open source.

---

**Built by a teacher.** Claw-ED was created by **Mr. Mac** — 9 years teaching Social Studies in Long Island, NY. Not a startup's idea of what teachers need. A tool built by someone who writes lesson plans every week and got tired of starting from scratch.

<p align="center">
  <strong>If Claw-ED saves you time, <a href="https://github.com/SirhanMacx/Claw-ED/stargazers">star it on GitHub</a></strong> so other teachers can find it.
</p>
