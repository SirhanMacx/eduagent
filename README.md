<p align="center">
  <h1 align="center">Claw-ED 🎓</h1>
  <p align="center"><strong>Your teaching files, your AI co-teacher.</strong></p>
  <p align="center">Open-source AI assistant that learns from your lesson plans and generates new ones in your exact teaching voice.</p>
  <p align="center">No cloud service. No vendor lock-in. Your materials stay on your machine.</p>
</p>

<p align="center">
  <a href="https://pypi.org/project/clawed/"><img src="https://img.shields.io/pypi/v/clawed?color=blue" alt="PyPI"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.10+-blue" alt="Python 3.10+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green" alt="MIT License"></a>
  <a href="https://github.com/SirhanMacx/Claw-ED/stargazers"><img src="https://img.shields.io/github/stars/SirhanMacx/Claw-ED" alt="GitHub stars"></a>
</p>

<p align="center">
  <a href="https://sirhanmacx.github.io/Claw-ED/">Website</a> · <a href="#-getting-started">Quickstart</a> · <a href="FEATURES.md">Features</a> · <a href="ROADMAP.md">Roadmap</a> · <a href="CONTRIBUTING.md">Contributing</a>
</p>

<p align="center">
  <strong>🌐 <a href="https://sirhanmacx.github.io/Claw-ED/">sirhanmacx.github.io/Claw-ED</a></strong>
</p>

---

> **If Claw-ED helps your teaching, [give it a star](https://github.com/SirhanMacx/Claw-ED/stargazers).** It helps other teachers find it.

---

## How it works

```
Your lesson plans (PDFs, DOCX, PPTX, TXT)
        ↓
Claw-ED reads them and learns your teaching fingerprint:
  • Teaching style (inquiry-based, direct instruction, Socratic...)
  • Structural preferences (AIM questions, Do Nows, exit tickets...)
  • Vocabulary level and tone
  • Assessment approach
        ↓
You ask: "Plan a 2-week unit on WWI for my 10th graders"
        ↓
Claw-ED generates:
  • Full unit plan with essential questions
  • 10 daily lesson plans in YOUR voice
  • Student worksheets, assessments, rubrics
  • IEP/504 accommodations
  • Differentiation for struggling/advanced/ELL students
```

## Real output

This is actual Claw-ED output — not mockups. Generated for an 8th grade Social Studies class studying the American Revolution.

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

Every lesson includes differentiation, exit tickets, and homework — all in the teacher's voice. See [FEATURES.md](FEATURES.md) for more.

---

## 🚀 Getting Started

**Never used a terminal? No problem.** We'll walk you through everything step by step.

---

### Step 1 — Install Python (if you don't have it)

- **Mac**: Open Terminal (`Cmd + Space`, type "Terminal", hit Enter). Type `python3 --version`. If you see `Python 3.x.x`, you're good. If not, [download Python here](https://www.python.org/downloads/) — click the yellow button and run the installer.
- **Windows**: Press the Windows key, type "cmd", hit Enter. Type `python --version`. If you see an error, [download Python here](https://www.python.org/downloads/) — click the yellow button, run the installer, and **check "Add Python to PATH"** during setup.

### Step 2 — Install and run

In the same Terminal or Command Prompt window:

```
pip install clawed
clawed
```

That's it. Claw-ED walks you through setup right in the terminal:
1. **Pick your AI provider** — we recommend Ollama Cloud ($20/month flat rate). Paste your API key.
2. **Meet your assistant** — Claw-ED introduces itself and asks about you: your name, what you teach, your grade level, and state (for standards alignment).
3. **Share your files** (optional) — point Claw-ED at a folder of lesson plans and it learns your teaching voice.

The whole thing takes about 60 seconds. No config files, no environment variables.

> **Prefer a visual setup?** Run `clawed serve` and open `http://localhost:8000` — new users see the browser-based onboarding wizard automatically.

> **Upgrading from EDUagent?** `pip install clawed` replaces `pip install eduagent`. All your existing config and files continue to work.

---

### 📱 Want it on your phone? (Telegram bot)

Once Claw-ED is set up, you can connect it to Telegram so you can generate lessons from your phone — during your commute, in the copy room, wherever.

**What is Telegram?** It's a free messaging app (like iMessage or WhatsApp). You need the app on your phone and an account. Download it at [telegram.org](https://telegram.org) if you don't have it yet.

**Step 1 — Create your teacher bot**

1. Open Telegram on your phone
2. In the search bar, type **@BotFather** and tap the result (it has a blue checkmark)
3. Tap **Start**, then send this message: `/newbot`
4. It will ask for a name — type something like `My Lesson Planner`
5. It will ask for a username — type something like `mrsmith_lessons_bot` (must end in `bot`)
6. BotFather will send you a **token** — a long string like `7412836591:AAHdqTqFEe...`
7. Copy that token (hold down on it, select Copy)

**Step 2 — Connect it to Claw-ED**

In Terminal on your computer:
```
clawed bot --token PASTE-YOUR-TOKEN-HERE
```

Leave that Terminal window open (the bot runs as long as the window is open). Now open Telegram, find your new bot, and send it a message — it should respond!

> **Keep it running:** For the bot to work when your computer is closed, you'll need to run it on a server. For most teachers, just running it during school hours is fine.

---

**Student bot:** Create a second bot for students — they join with a class code and can ask questions in your teaching voice. See [BOT_SETUP.md](docs/BOT_SETUP.md) for full student bot instructions.

---

### 🌐 Prefer a website interface?

```
clawed serve
```

Then open your browser and go to **http://localhost:8000**. New teachers see the onboarding wizard; returning teachers land on the dashboard.

### 💻 Prefer a full-screen terminal chat? (TUI)

If you don't want Telegram or a browser, the TUI gives you a rich chat interface right in your terminal — connected to the same gateway:

```bash
pip install 'clawed[tui]'
clawed serve &          # start the gateway in the background
clawed tui              # connect the TUI chat
```

The TUI supports the same onboarding, lesson generation, and all tools. No Telegram required.

---

## 📦 Installation options

```bash
pip install clawed                    # Everything you need (chat, bot, web dashboard)
pip install 'clawed[tui]'             # + Full-screen terminal chat (Textual)
pip install 'clawed[voice]'           # + Voice note transcription
pip install 'clawed[all]'             # Everything (TUI, voice, hosted)

# Requires Python 3.10+. Run: python --version
# Don't have Python? Download at https://python.org/downloads
```

## 🔧 Which AI should I use?

The setup wizard lets you choose your AI provider. We recommend **Ollama Cloud** — $20/month flat rate, great quality, no surprises. Sign up at [ollama.com](https://ollama.com), grab your API key from Settings, and paste it in the wizard.

> **Prefer Anthropic Claude or OpenAI?** Those work too — the wizard supports all three. See [Choosing a Model](docs/CHOOSING_A_MODEL.md) for a detailed comparison.

### 🔍 Web Search (optional)

Claw-ED can search the web to find current events, articles, and resources for your lessons. Free options:

| Provider | Cost | Setup |
|----------|------|-------|
| **DuckDuckGo** | Free, no key needed | Works out of the box |
| **Brave Search** | Free (1000/month) | [Get a key](https://api.search.brave.com/) → `clawed config set-search-key YOUR_KEY` |

> Web search is optional — Claw-ED works great without it.

## 📋 Commands

| Command | What it does |
|---------|-------------|
| `clawed` | First run: quick setup + AI introduces itself. Returning: drops into chat |
| `clawed chat` | Start terminal chat |
| `clawed tui` | Full-screen TUI chat — connects to running gateway (no Telegram needed) |
| `clawed serve` | Start web server (onboarding wizard for new users, dashboard for returning) |
| `clawed bot --token TOKEN` | Start teacher Telegram bot |
| `clawed ingest <path>` | Learn from your lesson plans |
| `clawed unit "Topic" -g 8 -s "Subject"` | Generate a unit plan |
| `clawed lesson "Topic" -g 8 -s "Subject"` | Generate a single lesson |
| `clawed lesson "Topic" ... --format pptx\|docx\|pdf` | Export as PowerPoint, Word, or PDF |
| `clawed materials -l lesson.json` | Generate worksheet + assessment |
| `clawed standards list -g 8 -s math` | Browse your state's standards |
| `clawed gap-analyze -s "Math" -g 8` | Find curriculum gaps against standards |
| `clawed demo` | See example output (no API key needed) |

Run `clawed --help` for the full command list.

### 🖼️ Academic Images — Built In

Slides automatically include relevant academic images from Library of Congress, Wikimedia Commons, and web search. No API keys needed. [Details →](docs/SLIDE_IMAGES.md)

## 🏗️ Architecture

```
Teacher's message (Telegram, CLI, TUI, Web, or OpenClaw)
        ↓
Gateway (agent_core)
  ├── Control Plane (deterministic: files, callbacks, onboarding)
  └── Agent Loop (natural language → LLM with tool use)
        ↓
Tools (generate_lesson, search_standards, export, ...)
        ↓
GatewayResponse (text, files, buttons)
        ↓
Teacher sees the result
```

The agent decides what to do via tool calling — no regex intent matching. Deterministic operations (file ingestion, onboarding, callbacks) bypass the agent for reliability. Enable with `clawed config set agent-gateway true`.

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full breakdown.

## ✅ Features

- [x] Persona extraction — learns your teaching voice from your files
- [x] Unit plans, daily lessons, worksheets, assessments, rubrics
- [x] IEP/504 accommodations and differentiation
- [x] 50-state standards alignment
- [x] Telegram bot, web dashboard, TUI chat, student chatbot
- [x] PPTX, DOCX, PDF export with academic images
- [x] 12 subject skill libraries + custom YAML plugins
- [x] Teacher workspace, autonomous scheduler, self-improvement loop
- [x] Curriculum gap analyzer, voice consistency evaluation
- [x] Substitute packets, parent communications
- [x] MCP server (tools callable from any AI agent)
- [x] Agent-first gateway with typed tool registry (v0.6)
- [x] Approval gates for consequential actions (v0.6)
- [ ] Google Drive integration (v0.7)
- [ ] Cognitive memory — learns your patterns over time (v0.7)
- [ ] Proactive scheduling — preps your week automatically (v0.8)
- [ ] Google Classroom export (future)

See [FEATURES.md](FEATURES.md) for the full list with details.

## 🔒 Privacy

- **Your files never leave your machine** unless you choose a cloud LLM
- **API keys stored in OS keychain** when `keyring` is installed (`pip install 'clawed[keyring]'`), otherwise in `~/.eduagent/` with restrictive permissions — never in the repo
- **Google Drive:** Personal accounts only — never use school-issued accounts

## 🗺️ Roadmap

See [ROADMAP.md](ROADMAP.md) for the full plan. Highlights:

| Version | What's coming |
|---------|--------------|
| **v0.6.0** *(current)* | Agent-first gateway, typed tool registry, approval gates, feature-flagged rollout |
| **v0.7.0** | Google Drive integration, cognitive memory (embedding-based) |
| **v0.8.0** | Proactive scheduling, custom teacher tools, multi-step planner |
| **v1.0.0** | District deployment with admin dashboard and SSO |

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). First issues are labeled `good first issue`.

Subject matter experts welcome: if you know how great lessons are structured in your subject, open a PR for `clawed/skills/your_subject.py`.

## 📄 License

MIT. Build on it, sell it, use it in your classroom. Just don't be evil.

---

## 👨‍🏫 Built by a teacher

Claw-ED was created by **Mr. Mac** — 9 years teaching Social Studies in Long Island, NY. Not a startup's idea of what teachers need. A tool built by someone who writes lesson plans every week and got tired of starting from scratch.

---

<p align="center">
  <strong>If Claw-ED saves you time, <a href="https://github.com/SirhanMacx/Claw-ED/stargazers">star it on GitHub</a></strong> so other teachers can find it.
</p>
