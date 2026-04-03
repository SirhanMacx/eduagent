# Claw-ED

**The agentic layer for education. Your AI co-teacher that lives in the terminal.**

<p align="center">
  <a href="https://pypi.org/project/clawed/"><img src="https://img.shields.io/pypi/v/clawed?color=blue" alt="PyPI version"></a>
  <a href="https://pypi.org/project/clawed/"><img src="https://img.shields.io/pypi/pyversions/clawed" alt="Python versions"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green" alt="MIT License"></a>
  <a href="https://github.com/SirhanMacx/Claw-ED/stargazers"><img src="https://img.shields.io/github/stars/SirhanMacx/Claw-ED" alt="GitHub stars"></a>
  <a href="https://pepy.tech/project/clawed"><img src="https://static.pepy.tech/badge/clawed" alt="Downloads"></a>
</p>

<p align="center">
  <img src="docs/ed-mascot.png" alt="Ed — the Claw-ED mascot. A red apple with lobster claws, graduation cap, and diploma." width="280">
</p>

---

Claw-ED is a persistent AI teaching assistant that lives in your terminal and on your phone. Talk naturally — "make me a lesson on WWI for my 8th graders" — and it generates complete lesson packages in your voice. Not a chatbot. An agent that knows your curriculum, your standards, your students, and your teaching style.

Beautiful interactive terminal with animated braille-art logo, always-on Telegram bot, multi-provider LLM support (Anthropic, OpenAI, Google, Ollama).

```bash
pip install clawed
```

---

## For Teachers

**Feed it your files. Get lessons in your voice.**

```bash
clawed ingest ~/Documents/Lessons/   # Teach it your style
clawed lesson "The Missouri Compromise" -g 8 -s "US History"   # Generate a lesson
```

Claw-ED reads your existing lesson plans, handouts, slideshows, and assessments. It extracts your pedagogical fingerprint: how you structure a Do Now, what graphic organizers you use, how you scaffold for ELL and IEP students, your favorite primary source types, your questioning patterns, your signature teaching moves.

Then it generates new lessons that match. Not "inspired by" — actually match. Same structure, same voice, same scaffolding, same assessment alignment.

**What you get:**

- Complete daily lesson plans in your format (DOCX, PPTX, PDF)
- Unit plans with essential questions and pacing
- Assessments aligned to your state standards (50 states supported)
- Differentiated materials for ELL, IEP, and gifted students
- Homework, rubrics, sub plans, parent communications
- Gap analysis showing what standards you haven't covered
- Morning prep that runs before you wake up

**What makes it different:**

- **Your voice, not generic AI.** Lessons sound like you, not like a chatbot.
- **Auto-detects your setup.** Finds existing OAuth tokens, API keys, and local models automatically.
- **Works with any AI provider.** Anthropic (OAuth + API), OpenAI, Google Gemini, Codex, Antigravity, Ollama (local + cloud), or custom endpoints.
- **Gets better over time.** Rate lessons, give feedback — it learns what you want.
- **Open source.** MIT license. Free forever.

---

## Quick Start

```bash
# Install
pip install clawed

# First run — picks your AI provider and creates your workspace
clawed

# Feed it your curriculum files (PDF, DOCX, PPTX, and 20+ formats)
clawed ingest ~/Documents/Lessons/

# Generate
clawed lesson "Causes of World War I" -g 10 -s "Global History"
clawed unit "The Renaissance" -g 9 -s "Global History" -w 3
clawed full "Westward Expansion" -g 8 -s "US History"
```

---

## What's New in v4.2

- **Beautiful interactive terminal.** Animated startup, educational color palette, polished Ink/React TUI
- **Agentic onboarding.** First run auto-detects your providers, then the AI guides you through setup conversationally
- **Multi-provider support.** Anthropic (OAuth + API), OpenAI, Google Gemini, Ollama (local + cloud) — all from one CLI
- **Smarter ingestion.** Proper ODT/ODP parsing, XLS extraction, automatic topic tagging, corpus contribution on every ingest
- **Better image search.** Retry logic for DuckDuckGo, graceful fallback through 5 image sources
- **Teaching-first AI.** System prompt completely rewritten for pedagogy — standards, differentiation, Bloom's taxonomy, voice matching
- **14 teaching tools prioritized.** The AI reaches for lesson generation before file operations

---

## How It Works

```
Your curriculum files (PDF, DOCX, PPTX, and 20+ formats)
        |
        v
  Claw-ED learns your teaching style
    - Extracts your voice, structure, vocabulary
    - Maps your pedagogical fingerprint
    - Builds a searchable knowledge base
        |
        v
  You talk naturally
    "Prep my week"
    "Make a quiz on chapter 5"
    "What standards haven't I covered?"
        |
        v
  The agent acts
    - Searches your existing materials first
    - Generates in your voice
    - Exports professional documents
    - Aligns to your state standards
        |
        v
  You teach, give feedback, it improves
```

---

## Commands

| Command | What it does |
|---------|-------------|
| `clawed` | Chat with your agent |
| `clawed ingest <path>` | Teach it your style from your files |
| `clawed lesson "Topic" -g 8 -s "Subject"` | Generate a daily lesson plan |
| `clawed lesson "Topic" --multi-agent` | Multi-agent generation (higher quality) |
| `clawed unit "Topic" -g 9 -w 3` | Plan a 3-week unit |
| `clawed full "Topic" -g 10` | Full package: unit + lessons + materials |
| `clawed materials -l lesson.json` | Generate supporting materials |
| `clawed assess "Topic" --type dbq` | Generate assessments (DBQ, quiz, rubric) |
| `clawed differentiate -l lesson.json` | Create IEP/504/ELL modifications |
| `clawed standards list -g 8 -s "Math"` | Browse state standards |
| `clawed gap-analyze` | Find curriculum gaps |
| `clawed train --benchmark -n 5` | Score lesson quality |
| `clawed daemon start` | Start always-on Telegram bot (background) |
| `clawed daemon stop` | Stop the Telegram daemon |
| `clawed daemon status` | Show daemon uptime and health |
| `clawed serve` | Web dashboard |
| `clawed mcp-server` | MCP server (for Claude Code integration) |
| `clawed game create "Topic" -g 8` | Generate an interactive HTML learning game |
| `clawed game create "Topic" --style "escape room"` | Game with specific style |
| `clawed game create "Topic" --students "they love Minecraft"` | Game matching student interests |
| `clawed game gallery` | View all your generated games |
| `clawed demo` | Try it without an API key |

---

## Features

### Voice Learning

Claw-ED doesn't use a generic "teacher tone." It extracts your specific patterns from your files:

- **Teaching structure:** How you organize lessons (I Do / We Do / You Do, stations, jigsaw, etc.)
- **Questioning style:** Your progression from recall to analysis to evaluation
- **Scaffolding moves:** Sentence starters, graphic organizers, writing frames you actually use
- **Assessment patterns:** Your Do Now format, exit ticket style, essay scaffolds
- **Classroom personality:** Your humor, your catchphrases, your signature moves

### Standards Alignment

Built-in support for all 50 US states:

- Common Core (CCSS) — Math and ELA
- Next Generation Science Standards (NGSS)
- C3 Framework — Social Studies
- State-specific frameworks (NY NGLS, TX TEKS, CA CCSS, VA SOL, and more)
- Automatic gap analysis against your state's standards

### Multi-Agent Generation

For higher-quality output, the `--multi-agent` flag activates a three-agent pipeline:

1. **Researcher** — Finds primary sources, historical context, and key arguments
2. **Writer** — Drafts the lesson in your voice using your pedagogical fingerprint
3. **Reviewer** — Scores voice fidelity, pedagogy, and differentiation. Sends back for revision if quality is below threshold.

### Professional Export

- **DOCX** — Print-ready with headers, differentiation callouts, and images
- **PPTX** — Themed slideshows with section dividers and academic images
- **PDF** — Clean layout for distribution
- **Google Docs/Slides** — Direct export via Google Drive integration

### Differentiation

Every lesson can be automatically differentiated:

- **ELL support:** Simplified vocabulary, sentence frames, visual organizers
- **IEP modifications:** Chunked tasks, explicit instructions, modified assessments
- **504 accommodations:** Extended time, preferential seating, scribe access
- **Gifted extensions:** Deeper inquiry, independent research, cross-topic connections

### Interactive Learning Games

Every lesson can generate an interactive HTML game as an extension activity:

```bash
clawed game create "The Missouri Compromise" -g 8 -s "US History"
clawed game create "Photosynthesis" -g 6 --students "they love Minecraft"
clawed game create "The Renaissance" -g 9 --style "escape room"
```

Every game is unique — the AI designs the mechanic, visuals, and interaction from scratch based on the lesson content and your students' interests. No templates. Games are single-file HTML that works on phones, Chromebooks, and any browser.

Browse community games: [Game Gallery](https://sirhanmacx.github.io/Claw-ED/games)

### Autonomous Operation

Claw-ED can work while you sleep:

- **Morning prep** — Drafts today's materials before you wake up
- **Weekly planning** — Assembles next week's lessons on Sunday evening
- **Continuous improvement** — Ingests new files, refines your persona, measures quality
- **Telegram bot** — Message it from your phone anytime

---

## Architecture

```
Teacher (Terminal or Phone)
       |
  ┌────┴─────┐
  │ Ink TUI  │  ←── Beautiful interactive terminal (TypeScript)
  │  or      │
  │ Telegram │  ←── Always-on thin client via background daemon
  └────┬─────┘
       |
  Multi-Provider LLM Router
  (Anthropic | OpenAI | Google | Ollama)
       |
  ↕ tool_use / function_calling
       |
  14 Claw-ED Tools (TypeScript → Python subprocess)
       |
  Python Engine (lesson, game, export, standards, persona, ...)
       |
  Professional exports (DOCX, PPTX, HTML games, PDF)
```

**Key design decisions:**

- **Agent-first.** Natural language goes through an LLM that decides which tools to call. No rigid command parsing.
- **Master Content Track.** One LLM generation produces a unified `MasterContent` object. Teacher view, student packet, and slideshow are compiled mechanically — no redundant AI calls.
- **Subprocess bridge.** TypeScript CLI calls Python engine via `python3 -m clawed <cmd> --json`. Clean separation, independent testing, single install.
- **Multi-provider.** Teacher picks their provider (free Ollama to premium Claude). Claw-ED picks the best model within it.
- **Always-on daemon.** Background process keeps Telegram bot online. Teachers generate lessons from their phone.
- **Subject-specific skills.** 13 built-in subject skills (Math, Science, History, ELA, Music, Art, PE, CS, Foreign Language, Library, Special Ed, and more) tune the generation for each discipline's pedagogy.

---

## Privacy

- **Local-first.** Your files stay on your machine. The knowledge base is a local database.
- **API keys in OS keychain.** macOS Keychain, Linux Secret Service, Windows Credential Manager.
- **No telemetry, no data collection, no accounts.**
- **Your choice of AI provider.** Use free local models (Ollama) for complete privacy, or cloud providers (Claude, GPT, Gemini) for maximum quality.

---

## AI Providers

Recommended: **Ollama Cloud** with Minimax M2.7 ($20/month unlimited). Claw-ED also accepts API keys from other providers:

- **Ollama Cloud** — Minimax M2.7, Kimi K2.5, and other cloud models. $20/month unlimited.
- **Ollama Local** — Run any model locally for free (Llama 3.3, Qwen, etc.)
- **OpenRouter** — Access any model (Claude, GPT, Gemini, open-source) via openrouter.ai
- **Google Gemini** — Free tier available via ai.google.dev
- **OpenAI** — GPT-4o and newer via platform.openai.com
- **Anthropic** — Claude Sonnet/Opus via console.anthropic.com

Run `clawed setup` to pick your provider and enter your API key.

---

## For Developers

### Contributing

```bash
git clone https://github.com/SirhanMacx/Claw-ED.git
cd Claw-ED
pip install -e ".[dev]"
pytest tests/
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines and [ARCHITECTURE.md](docs/ARCHITECTURE.md) for system design.

### MCP Server

Claw-ED exposes its tools as an MCP server for integration with Claude Code, VS Code, and other AI-powered editors:

```bash
clawed mcp-server
```

### Custom Tools

Define custom tools in `~/.eduagent/tools/` using YAML templates — no code required:

```yaml
name: bell_ringer
description: Generate a warm-up question for the start of class
parameters:
  topic: string
  grade: string
prompt: |
  Generate a bell ringer question about {topic} for grade {grade}.
  Use a visual stimulus or thought experiment. Never use recall questions.
```

### API

```python
from clawed.lesson import generate_lesson
from clawed.models import AppConfig

config = AppConfig.load()
lesson = await generate_lesson(
    lesson_number=1,
    unit=unit_plan,
    persona=persona,
    config=config,
)
```

---

## Community

Claw-ED is built by a teacher for teachers. Join the conversation:

- **[GitHub Discussions](https://github.com/SirhanMacx/Claw-ED/discussions)** — share how you use Claw-ED, request features, ask questions
- **[Report issues](https://github.com/SirhanMacx/Claw-ED/issues)** — bugs, feature requests, quality feedback
- **[Star the repo](https://github.com/SirhanMacx/Claw-ED)** — it helps other teachers find us

14,000+ installs and growing. The agentic layer for education starts here.

---

## License

MIT License. Free for personal and commercial use.

Built by educators, for educators. The agentic layer for education.

[GitHub](https://github.com/SirhanMacx/Claw-ED) | [PyPI](https://pypi.org/project/clawed/) | [Game Gallery](https://sirhanmacx.github.io/Claw-ED/games) | [Discussions](https://github.com/SirhanMacx/Claw-ED/discussions) | [Changelog](CHANGELOG.md)
