<p align="center">
  <h1 align="center">EDUagent 🎓</h1>
  <p align="center"><strong>Your teaching files, your AI co-teacher.</strong></p>
  <p align="center">Open-source AI assistant that learns from your lesson plans and generates new ones in your exact teaching voice.</p>
  <p align="center">No cloud service. No vendor lock-in. Your materials stay on your machine.</p>
</p>

<p align="center">
  <a href="https://github.com/SirhanMacx/eduagent/actions/workflows/ci.yml"><img src="https://github.com/SirhanMacx/eduagent/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/eduagent/"><img src="https://img.shields.io/pypi/v/eduagent?color=blue" alt="PyPI"></a>
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

## 🚀 Getting Started

**Never used a terminal? No problem.** We'll walk you through everything step by step.

---

### Step 1 — Check that Python is installed

EDUagent runs on Python. Most Macs already have it. Here's how to check:

1. On a **Mac**: press `Cmd + Space`, type `Terminal`, hit Enter
2. On **Windows**: press the Windows key, type `cmd`, hit Enter
3. In the window that opens, type this and press Enter:
   ```
   python --version
   ```
   If you see something like `Python 3.11.2`, you're good. If you see an error, [download Python here](https://www.python.org/downloads/) — click the big yellow button and run the installer.

---

### Step 2 — Install EDUagent

In the same Terminal window, type this and press Enter:

```
pip install eduagent
```

Wait about 30 seconds. You'll see text scrolling — that's normal. When it stops and you see a `$` again, it worked.

---

### Step 3 — Get an AI key (free to start)

EDUagent needs an AI brain. The easiest option is **Anthropic Claude** — you get $5 free credit, no credit card required.

1. Go to [console.anthropic.com](https://console.anthropic.com) and create a free account
2. Click **API Keys** in the left sidebar → **Create Key**
3. Copy the key (starts with `sk-ant-...`)
4. Back in Terminal, type this (replace the key with yours):
   - **Mac/Linux:**
     ```
     export ANTHROPIC_API_KEY=sk-ant-your-key-here
     ```
   - **Windows:**
     ```
     set ANTHROPIC_API_KEY=sk-ant-your-key-here
     ```

> **Prefer ChatGPT?** Use `OPENAI_API_KEY=` instead. **Want free?** [Install Ollama](https://ollama.com) and run `eduagent config set-model ollama` — no API key needed.

---

### Step 4 — Start EDUagent

```
eduagent chat
```

That's it. EDUagent will ask you a few questions about what you teach, then you can point it at your existing lesson plans (or just start from scratch).

**Example:**
```
EDUagent: What do you teach?
You: 9th grade Global History in New York

EDUagent: Do you have any lesson plans or materials I can learn from?
You: yes, they're in my Documents/Teaching folder

EDUagent: Analyzing 246 files... I can see your style now.
  You love Socratic questioning, primary sources, and AIM questions.
  Ready to help — what do you need?

You: write a do now for tomorrow's lesson on the causes of WWI
EDUagent: Here's your Do Now...
```

---

### 📱 Want it on your phone? (Telegram bot)

Once EDUagent is working on your computer, you can set up a Telegram bot so you can generate lessons from your phone during your commute or prep period.

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` — follow the prompts to name your bot
3. BotFather gives you a token (looks like `123456:ABC-DEF...`) — copy it
4. In Terminal:
   ```
   pip install 'eduagent[telegram]'
   eduagent bot --token PASTE-YOUR-TOKEN-HERE
   ```
5. Find your new bot in Telegram and start chatting

> **Student bot:** Your students can also have their own bot that answers questions in your voice. See [FEATURES.md](FEATURES.md) for setup.

---

### 🌐 Prefer a website interface?

```
eduagent serve
```

Then open your browser and go to **http://localhost:8000** — you'll see a full dashboard.

---

---

## 📦 Installation options

```bash
pip install eduagent                    # Core (terminal chat + web dashboard)
pip install 'eduagent[telegram]'        # + Telegram bot for teacher and students
pip install 'eduagent[voice]'           # + Voice note transcription
pip install 'eduagent[all]'             # Everything

# Requires Python 3.10+. Run: python --version
# Don't have Python? Download at https://python.org/downloads
```

## 🔧 Which AI should I use?

EDUagent works with several AI providers. **You keep your own API key** — nothing goes through our servers.

| Provider | Cost | How to get a key |
|----------|------|-----------------|
| **Anthropic (Claude)** — recommended | $5 free, then pay-as-you-go | [console.anthropic.com](https://console.anthropic.com) → API Keys |
| **OpenAI (GPT-4o)** | Pay-as-you-go | [platform.openai.com](https://platform.openai.com) → API Keys |
| **Ollama** — 100% free | Free (runs on your computer) | [ollama.com](https://ollama.com) — download and install |

For most teachers, **Anthropic Claude** is the best balance of quality and cost. A typical month of daily use costs $2–5.

## 📋 Commands

| Command | What it does |
|---------|-------------|
| `eduagent chat` | Start terminal chat |
| `eduagent bot --token TOKEN` | Start teacher Telegram bot |
| `eduagent student-bot --token TOKEN` | Start student Telegram bot |
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

Security & reliability:
  API keys stored in OS keychain (keyring) — never in config.json
  JSON repair via json-repair package for resilient LLM output parsing
  Thread-safe SQLite with per-operation connections and context managers
  SQL injection guards on all dynamic queries
  CORS middleware + slowapi rate limiting on API endpoints
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

EDUagent was created by **Mr. Mac** — 9 years teaching Social Studies in Long Island, NY school districts. This isn't a startup's idea of what teachers need. It's a tool built by someone who writes lesson plans every week, knows what a good Do Now looks like, and got tired of starting from scratch.

Mr. Mac is the primary user and the reason this exists. Every feature was built because he needed it.

---

<p align="center">
  <strong>If EDUagent saves you time, <a href="https://github.com/SirhanMacx/eduagent/stargazers">star it on GitHub</a></strong> so other teachers can find it.
</p>
