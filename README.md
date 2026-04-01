# Claw-ED

**Your AI co-teacher. Learns your voice. Generates lessons that sound like you wrote them.**

<p align="center">
  <a href="https://pypi.org/project/clawed/"><img src="https://img.shields.io/pypi/v/clawed?color=blue" alt="PyPI version"></a>
  <a href="https://pypi.org/project/clawed/"><img src="https://img.shields.io/pypi/pyversions/clawed" alt="Python versions"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green" alt="MIT License"></a>
  <a href="https://github.com/SirhanMacx/Claw-ED/stargazers"><img src="https://img.shields.io/github/stars/SirhanMacx/Claw-ED" alt="GitHub stars"></a>
  <a href="https://pepy.tech/project/clawed"><img src="https://static.pepy.tech/badge/clawed" alt="Downloads"></a>
</p>

---

Claw-ED is an open-source AI teaching assistant that learns your actual teaching style from your curriculum files. Not a generic lesson template generator — a personal agent that captures your voice, your scaffolding patterns, your assessment style, and your classroom personality. It generates complete lesson packages that your colleagues would swear you wrote yourself.

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
- **Your files stay on your machine.** Local-first architecture. No accounts, no subscriptions, no data collection.
- **Works with any AI provider.** Claude, GPT, Gemini, Ollama (free local models), or your own fine-tuned model.
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
| `clawed bot --token TOKEN` | Connect Telegram bot |
| `clawed serve` | Web dashboard |
| `clawed mcp-server` | MCP server (for Claude Code integration) |
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

### Autonomous Operation

Claw-ED can work while you sleep:

- **Morning prep** — Drafts today's materials before you wake up
- **Weekly planning** — Assembles next week's lessons on Sunday evening
- **Continuous improvement** — Ingests new files, refines your persona, measures quality
- **Telegram bot** — Message it from your phone anytime

---

## Architecture

```
Teacher (Telegram, CLI, Web, MCP)
       |
   Gateway (feature-flag router)
   |-- Control Plane (deterministic: files, onboarding, export)
   |-- Agent Loop (LLM with 28 typed tools)
              |                        |
       Tool Registry              Workspace
       - generate_lesson          - SOUL.md (identity)
       - search_materials         - HEARTBEAT.md (schedule)
       - generate_assessment      - Memory (3-layer cognitive)
       - curriculum_map           |
       - export_document     Curriculum KB
       - 23 more tools       (semantic search over your files)
              |
       Professional exports (DOCX, PPTX, PDF, Google Docs)
```

**Key design decisions:**

- **Agent-first.** Natural language goes through an LLM that decides which tools to call. No rigid command parsing.
- **Master Content Track.** One LLM generation produces a unified `MasterContent` object. Teacher view, student packet, and slideshow are compiled mechanically — no redundant AI calls.
- **Fail-closed quality gates.** Every generation is validated. If quality review crashes, it reports failure instead of silently passing.
- **Subject-specific skills.** 13 built-in subject skills (Math, Science, History, ELA, Music, Art, PE, CS, Foreign Language, Library, Special Ed, and more) tune the generation for each discipline's pedagogy.

---

## Privacy

- **Local-first.** Your files stay on your machine. The knowledge base is a local database.
- **API keys in OS keychain.** macOS Keychain, Linux Secret Service, Windows Credential Manager.
- **No telemetry, no data collection, no accounts.**
- **Your choice of AI provider.** Use free local models (Ollama) for complete privacy, or cloud providers (Claude, GPT, Gemini) for maximum quality.

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

## License

MIT License. Free for personal and commercial use.

Built by educators, for educators.

[GitHub](https://github.com/SirhanMacx/Claw-ED) | [PyPI](https://pypi.org/project/clawed/) | [Changelog](CHANGELOG.md)
