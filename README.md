# EDUagent 🎓

> Your teaching files → your AI co-teacher.

EDUagent is an open-source AI assistant for teachers. It learns from your existing lesson plans, and from that point on generates lessons, units, worksheets, and assessments in your exact teaching voice — your vocabulary, your structure, your pedagogical approach.

No cloud service. No vendor lock-in. Your materials stay on your machine.

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![MIT License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-225%20passing-brightgreen)](tests/)

---

## ✨ What it does

```
Your 9 years of lesson plans
        ↓
EDUagent reads them and learns your teaching fingerprint:
  • Teaching style (inquiry-based, direct instruction, Socratic...)
  • Structural preferences (AIM questions, Do Nows, exit tickets...)
  • Vocabulary level and tone
  • Assessment approach
        ↓
You ask: "Plan a 3-week unit on WWI for my 10th graders"
        ↓
EDUagent generates:
  • Full unit plan with essential questions
  • 15 daily lesson plans in YOUR voice
  • Student worksheets, assessments, rubrics
  • IEP/504 accommodations
  • Differentiation for struggling/advanced/ELL students
```

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

## 📦 Installation

```bash
pip install eduagent                    # Core (terminal chat + web)
pip install 'eduagent[telegram]'        # + Telegram bot
pip install 'eduagent[voice]'           # + Voice note transcription
pip install 'eduagent[all]'             # Everything
```

## 🔧 LLM Backend (choose one)

EDUagent works with any of these. You bring your own API key — nothing is shared with us.

| Provider | Quality | Cost | Setup |
|----------|---------|------|-------|
| **Ollama** (recommended) | ⭐⭐⭐⭐⭐ | Free / ~$20/mo cloud | `eduagent config set-model ollama` |
| **Anthropic** (Claude) | ⭐⭐⭐⭐⭐ | Pay per token | `export ANTHROPIC_API_KEY=sk-...` |
| **OpenAI** (GPT-4o) | ⭐⭐⭐⭐ | Pay per token | `export OPENAI_API_KEY=sk-...` |

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
  telegram_bot.py  → Telegram
  api/server.py    → Web dashboard
  cli.py           → Terminal
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

## 🔒 Privacy

- **Your files never leave your machine** unless you choose a cloud LLM
- **API keys stored in OS keychain** — not in config files, not in the repo
- **Google Drive:** Personal accounts only. Never use school-issued Google accounts — your district's IT policy almost certainly prohibits third-party OAuth, and we don't want to be the reason you get a call from your principal.

## 🗺️ Roadmap

- [ ] Hosted version: no installation, school-safe, $10/teacher/month
- [ ] Google Classroom one-click export (personal accounts)
- [ ] iOS/Android app
- [ ] District-wide deployment with admin dashboard
- [ ] Multi-language support (Spanish, Mandarin, French)
- [ ] Standards auto-update (live sync with state DOE)

## 🤝 Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md). First issues are labeled `good first issue`.

Subject matter experts welcome: if you know how great lessons are structured in your subject, open a PR for `eduagent/skills/your_subject.py`.

## 📄 License

MIT. Build on it, sell it, use it in your classroom. Just don't be evil.

---

*Built by a teacher, for teachers. Jon Maccarello — 9 years, Great Neck South — is the primary user and the reason this exists.*
