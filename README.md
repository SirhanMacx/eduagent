<p align="center">
  <h1 align="center">EDUagent 🎓</h1>
  <p align="center"><strong>Your teaching files, your AI co-teacher.</strong></p>
  <p align="center">Open-source AI assistant that learns from your lesson plans and generates new ones in your exact teaching voice.</p>
  <p align="center">No cloud service. No vendor lock-in. Your materials stay on your machine.</p>
</p>

<p align="center">
  <a href="https://github.com/SirhanMacx/eduagent/actions/workflows/ci.yml"><img src="https://github.com/SirhanMacx/eduagent/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/eduagent/"><img src="https://img.shields.io/pypi/v/eduagent?color=blue" alt="PyPI"></a>
  <a href="https://pypi.org/project/eduagent/"><img src="https://img.shields.io/pypi/dm/eduagent?color=green" alt="PyPI Downloads"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.10+-blue" alt="Python 3.10+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green" alt="MIT License"></a>
  <a href="https://github.com/SirhanMacx/eduagent/stargazers"><img src="https://img.shields.io/github/stars/SirhanMacx/eduagent" alt="GitHub stars"></a>
</p>

<p align="center">
  <a href="#-quickstart-5-minutes">Quickstart</a> · <a href="FEATURES.md">Features</a> · <a href="ROADMAP.md">Roadmap</a> · <a href="CONTRIBUTING.md">Contributing</a>
</p>

---

> **If EDUagent helps your teaching, [give it a star](https://github.com/SirhanMacx/eduagent/stargazers).** It helps other teachers find it.

---

## How it works

```
Your lesson plans (PDFs, DOCX, PPTX, TXT)
        ↓
EDUagent reads them and learns your teaching fingerprint:
  • Teaching style (inquiry-based, direct instruction, Socratic...)
  • Structural preferences (AIM questions, Do Nows, exit tickets...)
  • Vocabulary level and tone
  • Assessment approach
        ↓
You ask: "Plan a 2-week unit on WWI for my 10th graders"
        ↓
EDUagent generates:
  • Full unit plan with essential questions
  • 10 daily lesson plans in YOUR voice
  • Student worksheets, assessments, rubrics
  • IEP/504 accommodations
  • Differentiation for struggling/advanced/ELL students
```

## Real output

This is actual EDUagent output — not mockups. Generated for an 8th grade Social Studies class studying the American Revolution.

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

**Lesson 1 — Direct Instruction (verbatim):**

> Alright, friends, today we're starting one of my favorite units in all of history. We're going to answer a question that sounds simple but is actually incredible: How did ordinary people decide to risk everything for freedom? I want you to really sit with this for a second.

**Lesson 2 — Do Now (verbatim):**

> Alright, friends, settle in. Grab your notebooks. I want you to think about this: Have you ever had to pay for something or follow a rule that you didn't agree with? Maybe a chore you didn't want to do, or a fee you thought was unfair? Write down: 1) What was the rule or cost? 2) How did it make you feel? 3) Did you speak up against it? You have 5 minutes. Let's get those minds warming up.

Every lesson includes differentiation, exit tickets, and homework — all in the teacher's voice. See [FEATURES.md](FEATURES.md) for more.

---

## 🚀 Quickstart (5 minutes)

### Terminal chat (fastest way to try it)

```bash
pip install eduagent
export ANTHROPIC_API_KEY=sk-...   # or OPENAI_API_KEY, or use Ollama (free)
eduagent chat
```

```
You: I teach 9th grade Global History at a public high school in New York
EDUagent: Great! I'm ready to help. Share some of your lesson plans and I'll learn your style.

You: my materials are in ~/Documents/Teaching/
EDUagent: Analyzing 246 files... done.

  📚 Your Teaching Profile
  • Style: Inquiry-based
  • Format: AIM → Do Now → Document Analysis → Guided Practice
  • Loves: Primary sources, DBQs, Socratic questioning
  • Goes by: Mr. Mac

You: plan a unit on the causes of WWI, 2 weeks
EDUagent: Planning your unit... 🌿

  Unit: "Chain Reaction: Unpacking the Causes of World War I"
  Essential Questions:
  • Was WWI inevitable, or could it have been prevented?
  • How do alliances protect nations versus how do they provoke conflict?
  ...
```

### Telegram bot (best for daily use)

```bash
pip install 'eduagent[telegram]'
# Get a bot token from @BotFather on Telegram
eduagent bot --token YOUR_BOT_TOKEN
```

Then message your bot on Telegram — same experience, always in your pocket.

### Web dashboard

```bash
eduagent serve
# Opens at http://localhost:8000
```

---

## 🐳 Quick Deploy

### One-line installer (Mac/Linux)

```bash
curl -fsSL https://raw.githubusercontent.com/eduagent/eduagent/main/scripts/install.sh | bash
```

Detects your OS, installs Python if needed, installs EDUagent, and walks you through API key + Telegram setup.

### Docker (no Python required)

```bash
# 1. Clone or create a folder
mkdir eduagent && cd eduagent

# 2. Create a .env file with your keys
cat > .env <<EOF
ANTHROPIC_API_KEY=sk-ant-your-key-here
TELEGRAM_BOT_TOKEN=your-token-here
EOF

# 3. Start everything
docker compose up -d
```

Web dashboard at http://localhost:8000, Telegram bot running in the background.

See [docs/DOCKER_SETUP.md](docs/DOCKER_SETUP.md) for the full guide (assumes zero Docker knowledge).

---

## 📦 Installation

Available on PyPI — install with one command:

```bash
pip install eduagent                    # Core (terminal chat + web)
pip install 'eduagent[telegram]'        # + Telegram bot
pip install 'eduagent[voice]'           # + Voice note transcription
pip install 'eduagent[all]'             # Everything
```

> **Requires Python 3.10+.** Run `python --version` to check. If needed, [install Python](https://python.org/downloads).

## 🔧 LLM Backend (choose one)

EDUagent works with any of these. You bring your own API key — nothing is shared with us.

| Provider | Quality | Cost | Setup |
|----------|---------|------|-------|
| **Ollama** (recommended) | ★★★★★ | Free / ~$20/mo cloud | `eduagent config set-model ollama` |
| **Anthropic** (Claude) | ★★★★★ | Pay per token | `export ANTHROPIC_API_KEY=sk-...` |
| **OpenAI** (GPT-4o) | ★★★★ | Pay per token | `export OPENAI_API_KEY=sk-...` |

```bash
eduagent config set-model ollama      # Use local/cloud Ollama
eduagent config set-model anthropic   # Use Claude
eduagent config set-model openai      # Use GPT-4o
```

## 📋 Commands

| Command | What it does |
|---------|-------------|
| `eduagent chat` | Start terminal chat |
| `eduagent bot --token TOKEN` | Start Telegram bot |
| `eduagent serve` | Start web dashboard |
| `eduagent ingest <path>` | Learn from your lesson plans |
| `eduagent persona show` | See what EDUagent learned about you |
| `eduagent unit <topic>` | Generate a unit plan |
| `eduagent lesson <topic>` | Generate a single lesson |
| `eduagent materials` | Generate worksheet + assessment |
| `eduagent sub-packet` | Generate a substitute teacher packet |
| `eduagent standards list` | Browse your state's standards |
| `eduagent demo` | See example output (no API key needed) |

## 🏗️ Architecture

```
Teacher's files (PDFs, DOCX, PPTX, TXT)
        ↓ ingestor.py
Document corpus
        ↓ persona.py
TeacherPersona (style, structure, voice)
        ↓
Generation pipeline:
  planner.py → UnitPlan
  lesson.py  → DailyLesson
  materials.py → Worksheet + Assessment
  differentiation.py → IEP/504 modifications

Delivery:
  commands/bot.py      → Telegram bot
  commands/generate.py → Generation CLI commands
  commands/config.py   → Config & API key management
  commands/export.py   → Export (PDF, Classroom, share)
  api/server.py        → Web dashboard (FastAPI)
  cli.py               → Entry point (~100 lines)

Security:
  API keys stored in OS keychain (keyring) — never in config.json
  JSON repair via json-repair package for resilient LLM output parsing
```

## ✅ Features

- [x] Persona extraction from your curriculum files
- [x] Unit planning with essential questions + lesson sequence
- [x] Daily lesson generation (AIM, Do Now, instruction, exit ticket)
- [x] Worksheets, assessments, rubrics
- [x] IEP/504 accommodation generation
- [x] 50-state standards alignment (auto-detects your state)
- [x] Telegram bot (standalone, no other tools required)
- [x] Web dashboard with streaming generation
- [x] Student chatbot (students ask questions in teacher's voice)
- [x] Voice note transcription
- [x] School/department curriculum sharing
- [x] Substitute teacher packet generator
- [x] Parent communication generator
- [x] Subject skill libraries (Social Studies, Math, Science, ELA, History)
- [x] Self-improvement loop (gets better the more it's used)
- [x] MCP server (tools callable from any AI agent)
- [ ] Google Classroom export (personal accounts only — never school accounts)
- [ ] Hosted version (coming soon)

See [FEATURES.md](FEATURES.md) for detailed descriptions and screenshots.

## 🔒 Privacy

- **Your files never leave your machine** unless you choose a cloud LLM
- **API keys stored in OS keychain** — not in config files, not in the repo
- **Google Drive:** Personal accounts only. Never use school-issued Google accounts — your district's IT policy almost certainly prohibits third-party OAuth, and we don't want to be the reason you get a call from your principal.

## 🗺️ Roadmap

See [ROADMAP.md](ROADMAP.md) for the full plan. Highlights:

| Version | What's coming |
|---------|--------------|
| **v0.2.0** | Hosted version — no install, no terminal, no API keys |
| **v0.3.0** | iOS and Android apps |
| **v1.0.0** | District deployment with admin dashboard and SSO |

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). First issues are labeled `good first issue`.

Subject matter experts welcome: if you know how great lessons are structured in your subject, open a PR for `eduagent/skills/your_subject.py`.

## 📄 License

MIT. Build on it, sell it, use it in your classroom. Just don't be evil.

---

## 👨‍🏫 Built by a teacher

EDUagent was created by **Jon Maccarello** — 9 years teaching Social Studies at Great Neck South Middle School. This isn't a startup's idea of what teachers need. It's a tool built by someone who writes lesson plans every week, knows what a good Do Now looks like, and got tired of starting from scratch.

Jon is the primary user and the reason this exists. Every feature was built because he needed it.

---

<p align="center">
  <strong>If EDUagent saves you time, <a href="https://github.com/SirhanMacx/eduagent/stargazers">star it on GitHub</a></strong> so other teachers can find it.
</p>
