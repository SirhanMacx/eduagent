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

### Step 1 — Check that Python is installed

Claw-ED runs on Python. Most Macs already have it. Here's how to check:

1. On a **Mac**: press `Cmd + Space`, type `Terminal`, hit Enter
2. On **Windows**: press the Windows key, type `cmd`, hit Enter
3. In the window that opens, type this and press Enter:
   ```
   python --version
   ```
   If you see something like `Python 3.11.2`, you're good. If you see an error, [download Python here](https://www.python.org/downloads/) — click the big yellow button and run the installer.

---

### Step 2 — Install Claw-ED

In the same Terminal window, type this and press Enter:

```
pip install clawed
```

Wait about 30 seconds. You'll see text scrolling — that's normal. When it stops and you see a `$` again, it worked.

> **Upgrading from EDUagent?** Claw-ED is the same project, renamed. `pip install clawed` replaces `pip install eduagent`. All your existing config, lesson files, and API keys continue to work. The `eduagent` command still works too.

---

### Step 3 — Get an AI key

Claw-ED needs an AI brain. We recommend **Ollama Cloud** ($20/month flat rate). See [Which AI should I use?](#-which-ai-should-i-use) below for setup, or to try **Anthropic Claude** with $5 free credit:

```
export ANTHROPIC_API_KEY=sk-ant-your-key-here   # Mac/Linux
set ANTHROPIC_API_KEY=sk-ant-your-key-here       # Windows
```

---

### Step 4 — Start Claw-ED

```
clawed chat
```

That's it. Claw-ED will ask what you teach, learn from your existing files, and start generating in your voice.

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
pip install 'clawed[telegram]'
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

Then open your browser and go to **http://localhost:8000** — you'll see a full dashboard.

---

## 📦 Installation options

```bash
pip install clawed                    # Core (terminal chat + web dashboard)
pip install 'clawed[telegram]'        # + Telegram bot for teacher and students
pip install 'clawed[voice]'           # + Voice note transcription (optional)
pip install 'clawed[all]'             # Everything (Telegram, voice, TUI, hosted)

# Requires Python 3.10+. Run: python --version
# Don't have Python? Download at https://python.org/downloads
```

## 🔧 Which AI should I use?

Claw-ED needs an AI brain. We recommend **Ollama Cloud** — $20/month flat rate, great quality, no surprises.

1. Go to [ollama.com](https://ollama.com) and create a free account (some free usage included)
2. Upgrade to the **$20/month** plan for unlimited use
3. Grab your API key: profile icon → **Settings** → **API Keys** → **Generate**
4. In Terminal:
   ```
   export OLLAMA_API_KEY=your-key-here
   clawed config set-model ollama
   ```

> **Prefer Anthropic Claude or OpenAI?** Those work too — see [Choosing a Model](docs/CHOOSING_A_MODEL.md) for the full comparison.

## 📋 Commands

| Command | What it does |
|---------|-------------|
| `clawed chat` | Start terminal chat |
| `clawed serve` | Start web dashboard |
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

Slides automatically include relevant academic images from Library of Congress, Wikimedia Commons, and Unsplash. No API keys needed. [Details →](docs/SLIDE_IMAGES.md)

## 🏗️ Architecture

```
Teacher's message (Telegram, CLI, Web, or OpenClaw)
        ↓
Gateway → Router → Handler (generate, export, feedback, onboard, ...)
        ↓
GatewayResponse (text, files, buttons)
        ↓
Teacher sees the result
```

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full handler and services breakdown.

## ✅ Features

- [x] Persona extraction — learns your teaching voice from your files
- [x] Unit plans, daily lessons, worksheets, assessments, rubrics
- [x] IEP/504 accommodations and differentiation
- [x] 50-state standards alignment
- [x] Telegram bot, web dashboard, student chatbot
- [x] PPTX, DOCX, PDF export with academic images
- [x] 12 subject skill libraries + custom YAML plugins
- [x] Teacher workspace, autonomous scheduler, self-improvement loop
- [x] Curriculum gap analyzer, voice consistency evaluation
- [x] Substitute packets, parent communications
- [x] MCP server (tools callable from any AI agent)
- [ ] Google Classroom export (coming soon)
- [ ] Hosted version (coming soon)

See [FEATURES.md](FEATURES.md) for the full list with details.

## 🔒 Privacy

- **Your files never leave your machine** unless you choose a cloud LLM
- **API keys stored in OS keychain** — not in config files, not in the repo
- **Google Drive:** Personal accounts only — never use school-issued accounts

## 🗺️ Roadmap

See [ROADMAP.md](ROADMAP.md) for the full plan. Highlights:

| Version | What's coming |
|---------|--------------|
| **v0.3.0** *(current)* | Claw-ED architecture — gateway, handlers, transports |
| **v0.4.0** | Hosted version — no install, no terminal, no API keys |
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
