# Claw-ED

Your personal AI teaching agent. Runs on your machine, learns your voice, works while you sleep.

Built on the OpenClaw agent framework. Open source. MIT license.

<p align="center">
  <a href="https://pypi.org/project/clawed/"><img src="https://img.shields.io/pypi/v/clawed?color=blue" alt="PyPI"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.10+-blue" alt="Python 3.10+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green" alt="MIT License"></a>
  <a href="https://github.com/SirhanMacx/Claw-ED/stargazers"><img src="https://img.shields.io/github/stars/SirhanMacx/Claw-ED" alt="GitHub stars"></a>
</p>

---

## What is this?

Claw-ED is a personal AI agent for teachers. It uses the same architecture as other OpenClaw agents -- SOUL.md for identity, layered memory, a workspace, pulse jobs, tool use, and autonomous operation. The difference is what it knows: your lesson plans, your teaching style, your standards, your students.

You feed it your curriculum files and it learns your voice. Not a generic "teacher tone" -- your actual patterns, your vocabulary, the way you structure a Do Now or frame an essential question. Then it works: drafting lessons that sound like you wrote them, organizing your Google Drive, answering student questions in your voice, prepping your week before you wake up.

Everything runs on your own computer. Your files never leave your machine unless you choose a cloud LLM provider. No accounts, no subscriptions, no data collection. You own the agent, you own the data.

---

## How it works

```
Your files (PDFs, DOCX, PPTX, TXT)
        |
        v
Claw-ED learns your teaching style
  -- chunks and embeds every document
  -- extracts your voice, structure, vocabulary
        |
        v
You talk naturally
  "Prep my week"
  "Make a quiz on chapter 5"
  "What standards haven't I covered?"
        |
        v
Agent acts
  -- searches your materials first
  -- generates in your voice
  -- exports professional documents
  -- suggests next steps
        |
        v
You teach, give feedback, it improves
```

The agent has autonomous capabilities beyond chat. Morning prep runs before you wake up -- it checks your pacing guide and drafts the day's materials. Weekly planning assembles next week's lessons on Sunday evening. Memory improves over time: every rating, every edit, every approval teaches it what you want. The more you use it, the less you have to say.

---

## Setup

**Step 1: Install and run**

```bash
pip install clawed && clawed
```

**Step 2: First-run onboarding**

The terminal walks you through model selection (Ollama Cloud, Gemini, Claude, or GPT) and creates your workspace at `~/.eduagent/`.

**Step 3: Define your teaching identity**

Edit `~/.eduagent/workspace/SOUL.md` with your teaching philosophy, subject, grade levels, and how you want the agent to behave. This is the agent's personality file -- plain text, version-controllable, yours.

**Step 4: Feed it your files**

```bash
clawed ingest ~/Documents/Lessons/
```

The agent chunks every document into searchable sections and stores them in a local semantic database. When it generates, it searches your materials first.

**Step 5: Start using it**

```bash
clawed              # terminal chat
clawed bot --token TOKEN   # connect Telegram
clawed serve        # web dashboard
```

---

## Daily workflow

- Wake up, check Telegram -- the agent has drafted today's lessons overnight
- On the commute, message the bot: "make a quiz on chapter 5"
- In the copy room, export to DOCX and print
- After school, rate what worked and what didn't -- the agent learns
- Sunday evening, the agent drafts next week's plan based on your pacing guide

---

## Configuring your agent

Three plain text files control the agent's behavior:

**`~/.eduagent/workspace/SOUL.md`** -- The agent's identity. Your teaching philosophy, subject expertise, grade levels, communication style. Edit this to shape how the agent thinks and writes.

**`~/.eduagent/workspace/HEARTBEAT.md`** -- Autonomous task schedule. What the agent does on its own: morning prep, weekly planning, feedback digests. Edit to add or remove scheduled behaviors.

**Memory (automatic)** -- Three-layer cognitive memory that builds over time. Identity layer (your teaching fingerprint), curriculum state (what you've covered), and episodic memory (past interactions recalled by semantic similarity). You do not edit this directly -- it learns from your usage.

---

## Commands

| Command | What it does |
|---------|-------------|
| `clawed` | Start chatting with your agent |
| `clawed chat` | Terminal chat (explicit) |
| `clawed bot --token TOKEN` | Connect Telegram bot |
| `clawed serve` | Web dashboard |
| `clawed ingest <path>` | Feed files to the agent's knowledge base |
| `clawed unit "Topic" -g 8 -s "Subject"` | Generate a unit plan |
| `clawed lesson "Topic" -g 8 -s "Subject"` | Generate a lesson |
| `clawed lesson "Topic" --format pptx` | Export as PowerPoint |
| `clawed standards list -g 8 -s math` | Browse standards |
| `clawed gap-analyze -s "Math" -g 8` | Find curriculum gaps |
| `clawed demo` | See example output (no API key needed) |
| `clawed setup --reset` | Re-run setup |

Run `clawed --help` for the full list.

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
        search_materials  identity              CCSS, NGSS, C3
        ingest_materials  curriculum state      state-specific
                          episodic (embeddings)  gap analysis
              |
    Professional exports (DOCX, PPTX, PDF, Google Slides/Docs)
```

Custom YAML tools live in `~/.eduagent/tools/`. Define a name, description, parameters, and prompt template -- no code needed. The tool registry auto-discovers them alongside the 25 built-in tools.

---

## Privacy

- **Local-first.** Your files stay on your machine. The curriculum knowledge base is a local SQLite database, never uploaded.
- **API keys in OS keychain.** macOS Keychain, Linux Secret Service, Windows Credential Manager.
- **No telemetry, no data collection, no accounts.**
- **Cloud disclaimer:** When using cloud AI providers, prompts are sent to their APIs. Review your provider's data policy. For maximum privacy, use local Ollama.

---

Built by Mr. Mac — Social Studies Educator — Long Island, NY
