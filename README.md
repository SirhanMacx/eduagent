<p align="center">
  <h1 align="center">Claw-ED 🎓</h1>
  <p align="center"><strong>Your teaching files, your AI co-teacher.</strong></p>
  <p align="center">Open-source AI assistant that learns from your lesson plans and generates new ones in your exact teaching voice.</p>
  <p align="center">No cloud service. No vendor lock-in. Your materials stay on your machine.</p>
</p>

<p align="center">
  <a href="https://pypi.org/project/eduagent/"><img src="https://img.shields.io/pypi/v/eduagent?label=PyPI%20(eduagent)&color=blue" alt="PyPI"></a>
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

### Step 3 — Get an AI key (free to start)

Claw-ED needs an AI brain. The easiest option is **Anthropic Claude** — you get $5 free credit, no credit card required.

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

> **Prefer ChatGPT?** Use `OPENAI_API_KEY=` instead. **Want free?** [Install Ollama](https://ollama.com) and run `clawed config set-model ollama` — no API key needed.

---

### Step 4 — Start Claw-ED

```
clawed chat
```

That's it. Claw-ED will ask you a few questions about what you teach, then you can point it at your existing lesson plans (or just start from scratch).

**Example:**
```
Claw-ED: What do you teach?
You: 9th grade Global History in New York

Claw-ED: Do you have any lesson plans or materials I can learn from?
You: yes, they're in my Documents/Teaching folder

Claw-ED: Analyzing 246 files... I can see your style now.
  You love Socratic questioning, primary sources, and AIM questions.
  Ready to help — what do you need?

You: write a do now for tomorrow's lesson on the causes of WWI
Claw-ED: Here's your Do Now...
```

> **Note:** The `eduagent` command still works as an alias for `clawed`. Use whichever you prefer.

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

**Bonus: Student bot (your students ask questions, get your answers)**

You can create a *second* bot for your students. They join with a class code you create — then they can ask questions about the lesson and get answers in your teaching voice, any time of day.

1. Repeat Step 1 above to create a second bot (e.g., `mrsmith_students_bot`)
2. Copy the new token
3. In Terminal:
   ```
   clawed student-bot --token PASTE-STUDENT-BOT-TOKEN-HERE
   ```
4. In your teacher bot, type: `/create-class` to get a class code
5. Share the code and your student bot username with your students
6. Students open Telegram, find your student bot, send `/join YOUR-CODE` and start asking questions

---

### 🌐 Prefer a website interface?

```
clawed serve
```

Then open your browser and go to **http://localhost:8000** — you'll see a full dashboard.

---

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

Claw-ED is the tool — it needs an AI brain to do the thinking. Think of it like a car: Claw-ED is the car, and the AI is the engine. **You pick the engine and pay for it directly.** Nothing goes through our servers.

---

**Option 1 — Anthropic Claude (best quality, pay per use)**

Claude is widely considered the best AI for writing and nuanced instruction. Two models to choose from:

- **Claude Sonnet 4.6** — excellent quality, more affordable. Great for daily lesson planning.
- **Claude Opus 4.6** — the smartest available. Noticeably better output, noticeably more expensive.

Setup:
1. Go to [console.anthropic.com](https://console.anthropic.com) and create an account
2. Add a credit card (you only pay for what you use — no subscription)
3. Click **API Keys** in the left sidebar → **Create Key** → copy it
4. In Terminal: `export ANTHROPIC_API_KEY=sk-ant-your-key-here`

> Cost depends entirely on how much you use it. Light use (a few lessons a week): **$10–30/month**. Heavy daily use: **$100–200/month**. Opus 4.6 is roughly 5× more expensive than Sonnet — only worth it if output quality is your top priority.

---

**Option 2 — OpenAI GPT-5.4 (professional grade, pay per use)**

The company behind ChatGPT. GPT-5.4 is highly capable and produces professional-quality output.

Setup:
1. Go to [platform.openai.com](https://platform.openai.com) and create an account
2. Add a credit card under **Billing**
3. Click **API Keys** → **Create new secret key** → copy it
4. In Terminal: `export OPENAI_API_KEY=sk-your-key-here`

> GPT-5.4 is powerful but the cost adds up fast. Light use: **$10–30/month**. Heavy daily use: **$100–200/month**. No monthly cap — you pay for every token.

---

**Option 3 — Ollama Cloud with MiniMax M2.7 (~$20/month flat rate)**

Ollama is a platform that gives you access to powerful AI for a flat monthly fee — no surprise bills. MiniMax M2.7 is an excellent model for education: smart, fast, and great at learning your teaching voice.

Setup:
1. Go to [ollama.com](https://ollama.com) and create a free account
2. There is some free usage to try it before committing
3. Upgrade to the **$20/month** plan for unlimited use
4. Find your API key: log in → click your profile icon (top right) → **Settings** → **API Keys** → **Generate**
5. In Terminal: `export OLLAMA_API_KEY=your-key-here` then `clawed config set-model ollama`

> **Best value for most teachers.** Flat rate, no surprises, and MiniMax M2.7 is excellent at capturing your specific teaching style.

---

**Option 4 — Local model on your own computer (⚠️ not recommended)**

You can run a small AI model entirely on your computer — free, no internet needed. The catch: local models are significantly less intelligent than cloud options. They often struggle to capture your teaching voice or write naturally. Most teachers will be disappointed with the results.

If you want to try anyway, we recommend the **Qwen 3.5 series**:

| Your computer | Recommended model | Command to install |
|--------------|-------------------|--------------------|
| Basic laptop (8GB RAM) | Qwen 3.5 4B | `ollama pull qwen3.5:4b` |
| Modern Mac or PC (16GB RAM) | Qwen 3.5 9B | `ollama pull qwen3.5:9b` |
| High-end workstation (32GB+ RAM) | Qwen 3.5 32B | `ollama pull qwen3.5:32b` |

Then run: `clawed config set-model ollama`

> Start with Option 3 if cost is your concern — $20/month for cloud is far better than a free local model.

---

**Bottom line:** Most teachers should start with **Option 3 (Ollama cloud, $20/month)**. Flat rate, great quality, no surprises. If you want the best possible output regardless of cost, use **Option 1 with Claude Sonnet 4.6**.

## 📋 Commands

| Command | What it does |
|---------|-------------|
| `clawed chat` | Start terminal chat |
| `clawed bot --token TOKEN` | Start teacher Telegram bot |
| `clawed student-bot --token TOKEN` | Start student Telegram bot |
| `clawed serve` | Start web dashboard |
| `clawed ingest <path>` | Learn from your lesson plans |
| `clawed persona show` | See what Claw-ED learned about you |
| `clawed unit "Topic" -g 8 -s "Subject"` | Generate a unit plan |
| `clawed lesson "Topic" -g 8 -s "Subject"` | Generate a single lesson |
| `clawed materials -l lesson.json` | Generate worksheet + assessment |
| `clawed sub-packet -d 2026-03-24` | Generate a substitute teacher packet |
| `clawed standards list -g 8 -s math` | Browse your state's standards |
| `clawed demo` | See example output (no API key needed) |
| `clawed lesson "Topic" -g 8 -s "Subject" --format pptx` | Generate a PowerPoint presentation |
| `clawed lesson "Topic" -g 8 -s "Subject" --format docx` | Generate a Word document |
| `clawed lesson "Topic" -g 8 -s "Subject" --format pdf` | Generate a PDF |
| `clawed workspace init` | Set up your teacher workspace (identity, memory, notes) |
| `clawed schedule list` | View autonomous task schedule |
| `clawed skills list` | Browse subject-specific teaching strategies |
| `clawed gap-analyze -s "Math" -g 8` | Find curriculum gaps against standards |
| `clawed evaluate --lessons 5` | Test voice consistency across generated lessons |
| `clawed config set-unsplash-key KEY` | Enable slide images (free) |

### 🖼️ Academic Images — Built In, No Setup Required

Claw-ED automatically finds relevant academic images for your slides and handouts. **No API keys needed.** It searches these sources in order:

| Source | Best for | Cost | Key needed? |
|--------|----------|------|-------------|
| **Library of Congress** | History, Social Studies, Civics | Free | No |
| **Wikimedia Commons** | Science, Art, Music, all subjects | Free | No |
| **Unsplash** (fallback) | Modern photos, generic visuals | Free | Optional |

**How it works:** When you generate a lesson with `--format pptx` or `--format docx`, Claw-ED searches for images that match your topic and subject. A lesson on "The American Revolution" gets historical paintings and primary source documents from the Library of Congress. A lesson on "Photosynthesis" gets scientific diagrams from Wikimedia Commons.

**What you get:**
- **Title slide:** Full-bleed academic image with dark overlay for readability
- **Content slides:** Sidebar images (right 35%) matched to key concepts
- **Student handouts (DOCX):** Embedded images alongside relevant sections
- **No images?** Slides still look professional — subject-themed colors, clean typography, proper layouts

**Image caching:** Every image is cached locally at `~/.clawed/cache/images/` so the same topic never re-downloads. Searches have a 5-second timeout — if a source is slow, it's skipped gracefully.

**Want even more images?** Optionally add an Unsplash key for modern photography:
```bash
clawed config set-unsplash-key YOUR_KEY   # from unsplash.com/developers (free)
```

## 🏗️ Architecture

```
Teacher's message (Telegram, CLI, Web, or OpenClaw)
        ↓ transport layer
Gateway.handle(text, teacher_id)
        ↓ router.py (intent detection)
Handler (one per domain):
  handlers/generate.py  → Lessons, units, materials
  handlers/export.py    → PPTX, DOCX, PDF, handouts
  handlers/feedback.py  → Ratings + memory loop
  handlers/onboard.py   → New teacher setup
  handlers/schedule.py  → Automated tasks
  handlers/gaps.py      → Curriculum gap analysis
  handlers/standards.py → Standards lookup
  handlers/ingest.py    → File ingestion
        ↓
GatewayResponse (text, files, buttons)
        ↓ transport renders it
Teacher sees the result

Services (used by handlers):
  llm.py           → Unified LLM client (Anthropic/OpenAI/Ollama)
  model_router.py  → Tier-based routing (fast/work/deep)
  persona.py       → Teaching style extraction
  memory_engine.py → Self-improvement from feedback
  workspace.py     → Teacher workspace (identity, soul, memory)
  doc_export.py    → Professional document generation
```

## ✅ Features

- [x] Persona extraction from your curriculum files
- [x] Unit planning with essential questions + lesson sequence
- [x] Daily lesson generation (AIM, Do Now, instruction, exit ticket)
- [x] Worksheets, assessments, rubrics
- [x] IEP/504 accommodation generation
- [x] 50-state standards alignment (auto-applies your state's standards)
- [x] Telegram bot (standalone, no other tools required)
- [x] Web dashboard with streaming generation
- [x] Student chatbot (students ask questions in teacher's voice)
- [x] Voice note transcription (optional: `pip install 'clawed[voice]'`)
- [x] School/department curriculum sharing
- [x] Substitute teacher packet generator
- [x] Parent communication generator
- [x] Subject skill libraries (12 subjects: Social Studies, Math, Science, ELA, History, Art, Music, PE, CS, Foreign Language, Library, Special Ed)
- [x] Custom YAML skill plugins (add your own subject)
- [x] Professional PowerPoint export with subject-themed design and optional Unsplash images
- [x] Word document and PDF export
- [x] Teacher workspace (identity, memory, daily notes, student profiles)
- [x] Autonomous scheduler (morning prep, weekly planning, feedback digest)
- [x] Curriculum gap analyzer (compare materials against standards)
- [x] Voice consistency evaluation
- [x] Self-improvement loop (gets better the more it's used)
- [x] Per-student progress tracking and struggle detection
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

Claw-ED was created by **Mr. Mac** — 9 years teaching Social Studies in Long Island, NY school districts. This isn't a startup's idea of what teachers need. It's a tool built by someone who writes lesson plans every week, knows what a good Do Now looks like, and got tired of starting from scratch.

Mr. Mac is the primary user and the reason this exists. Every feature was built because he needed it.

---

<p align="center">
  <strong>If Claw-ED saves you time, <a href="https://github.com/SirhanMacx/Claw-ED/stargazers">star it on GitHub</a></strong> so other teachers can find it.
</p>
