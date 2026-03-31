# Claw-ED

Your personal AI teaching agent. Runs on your machine, learns your voice, works while you sleep.

Built on the Hermes Agent framework (NousResearch). Open source. MIT license.

<p align="center">
  <a href="https://pypi.org/project/clawed/"><img src="https://img.shields.io/pypi/v/clawed?color=blue" alt="PyPI version"></a>
  <a href="https://pypi.org/project/clawed/"><img src="https://img.shields.io/pypi/pyversions/clawed" alt="Python versions"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green" alt="MIT License"></a>
  <a href="https://github.com/SirhanMacx/Claw-ED/stargazers"><img src="https://img.shields.io/github/stars/SirhanMacx/Claw-ED" alt="GitHub stars"></a>
  <a href="https://pepy.tech/project/clawed"><img src="https://static.pepy.tech/badge/clawed" alt="Downloads"></a>
</p>

---

## What's new in v2.3.9

**Multi-agent lesson generation.** Instead of one LLM call doing everything, `--multi-agent` spawns a team of three specialized agents: a Researcher who finds primary sources and historical context, a Writer who drafts the lesson in your voice, and a Reviewer who scores quality on voice fidelity, pedagogy, and differentiation — sending it back for revision if any dimension scores below 7/10. The result: higher-quality lessons with better sources and stronger voice matching.

```bash
clawed lesson "The Missouri Compromise" -g 8 --multi-agent
```

**Claude Code integration.** Claw-ED now auto-reads OAuth tokens from Claude Code's credential store (`~/.claude/.credentials.json`). If you have Claude Code installed, Claw-ED just works — no separate API key setup needed, and tokens auto-refresh. Claw-ED also works as an MCP server that Claude Code can use directly:

```bash
clawed mcp-server  # Add to Claude Code as an MCP tool
```

**Continuous improvement pipeline.** The new `clawed train` command lets your AI fleet (or you) continuously improve lesson quality:

```bash
clawed train --drive          # Ingest new files from Google Drive, refine persona
clawed train --path ./files   # Ingest local curriculum files
clawed train --benchmark -n 5 # Generate 5 lessons and score them
clawed train --full           # Drive ingest + benchmark
```

Persona refinement is now incremental — new voice markers merge with existing ones instead of overwriting. Your teaching identity gets richer over time.

**OAuth auth fix.** All Anthropic API calls now correctly detect OAuth tokens and use Bearer authentication with Claude Code identity headers. Fixes the 401 errors that affected fleet agents and Claw-ED direct usage.

---

## What's new in v2.3.8

**No more silent failures.** Every step of lesson generation now reports what happened — persona loading, material search, quality review, voice matching. If something fails, you'll know exactly what and why, with structured NLAH failure codes. Quality review runs automatically on every generated lesson and fails closed: if the review itself crashes, it reports failure instead of silently passing.

**Stricter quality gates.** Lessons now require at least 6 guided notes, 3 exit ticket questions, and 2 primary sources with actual text. Topic drift is caught automatically. Voice match scoring compares generated lessons against your teaching persona.

**Safer onboarding.** Teacher names and subjects are validated and truncated. Invalid grade levels get a re-prompt instead of being silently accepted. Demo mode can be forced with `CLAWED_DEMO=1` for presentations.

**Async cleanup.** Background ingestion no longer risks crashing on Python 3.12+ from nested event loops. The fix is shared across all async call sites.

---

## What's new in v2.3.7

**Real images in every lesson.** Image specs are now required for every primary source and instruction section across all subjects. The LLM generates specific search queries ("Thomas Nast Boss Tweed political cartoon 1871") instead of leaving the field blank. Teacher images are found first using a three-stage progressive search (full query, individual keywords, subject fallback) with filename-weighted scoring across up to 150 candidates. External sources (Library of Congress, Wikimedia Commons, Unsplash) fill in the rest with subject-aware routing.

**12 new file formats.** Your old `.doc`, `.ppt`, `.xls`, `.xlsx`, `.csv`, `.rtf`, `.html`, `.odt`, and `.odp` files are now parsed and indexed. Previously only 8 formats were supported -- teachers' archives spanning decades of file formats were 93% invisible to search. Now they're searchable.

**Search actually works.** Three fixes to the search pipeline: cross-transport teacher ID fallback (files ingested via CLI now appear in Telegram searches), asset search errors are logged instead of silently swallowed, and the agent is explicitly instructed to surface results to you. Topic tags are auto-extracted from filenames and content for better matching.

**Background file ingestion.** Send your files and keep chatting. The bot acknowledges immediately, processes everything in a background thread, sends progress updates ("Indexed 50/200 documents..."), and a summary when done. Max 3 concurrent ingestions, individual file failures don't abort the batch.

**DEEP-tier model for lesson generation.** MasterContent routes to the DEEP tier. With a capable model (Claude Sonnet 4.6, GPT-4o), lesson quality improves dramatically.

**Security hardened.** Path traversal protection on all file-reading tools. XSS escaping on the web dashboard. Thread-safe tool definitions. ZIP bomb protection. Debug info no longer leaked to users. Ingest paths restricted to home directory.

**50 MB lighter.** Removed unused `anthropic` and `openai` SDK dependencies. API key resolution unified across all code paths (env var + keyring + secrets file).

**Everything from v2.3.5 still applies:** Master Content Track, stimulus-based assessment, zero silent failures, parallel image pipeline, identity protection.

---

## What is this?

Claw-ED is a personal AI agent for teachers. It uses the same architecture as Hermes Agent -- SOUL.md for identity, layered memory, a workspace, cron jobs, tool use, and autonomous operation. The difference is what it knows: your lesson plans, your teaching style, your standards, your students.

You feed it your curriculum files and it learns your voice. Not a generic "teacher tone" -- your actual patterns, your vocabulary, the way you structure a Do Now or frame an essential question. Then it works: drafting lessons that sound like you wrote them, organizing your Google Drive, answering student questions in your voice, prepping your week before you wake up.

Everything runs on your own computer. Your files never leave your machine unless you choose a cloud LLM provider. No accounts, no subscriptions, no data collection. You own the agent, you own the data.

---

## How it works

```
Your files (PDF, DOCX, PPTX, DOC, PPT, XLS, XLSX, CSV, RTF, HTML, ODT, TXT, and more)
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

The agent's intelligence lives in its workspace files, not in a static prompt. Two plain text files and automatic memory control everything:

**`~/.eduagent/workspace/SOUL.md`** -- A living document the agent co-authors with you. It starts as a template, then evolves: when you feed the agent your files, it writes what it learned about your voice, strategies, and signature moves. When you set up your profile, it records your identity. You can read and edit SOUL.md at any time -- full transparency. The agent reads it at the start of every important interaction to remember who you are and how you work.

**`~/.eduagent/workspace/HEARTBEAT.md`** -- Autonomous task schedule. What the agent does on its own: morning prep, weekly planning, feedback digests. Edit to add or remove scheduled behaviors. The agent reads this to know what it should be doing without being asked.

**Memory (automatic)** -- Three-layer cognitive memory that builds over time. Identity layer (your teaching fingerprint), curriculum state (what you've covered), and episodic memory (past interactions recalled by semantic similarity). You do not edit this directly -- it learns from your usage.

The system prompt is thin -- it points to workspace files instead of carrying all context inline. This means more token budget goes to actual lesson generation, and the agent's identity can grow without hitting prompt limits.

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

The agent's intelligence lives in its workspace files, not in a static prompt. SOUL.md defines identity and evolves over time. HEARTBEAT.md defines the schedule. The system prompt is a thin pointer -- the workspace is the brain.

Claw-ED is agent-first. Natural-language messages go through an LLM that decides which tools to call. Deterministic operations (file ingestion, onboarding, approvals) bypass the agent for reliability.

```
Teacher's message (Telegram, CLI, TUI, Web)
        |
    Gateway
    |-- Control Plane (deterministic: files, callbacks, onboarding)
    |-- Agent Loop (LLM decides -> calls tools -> returns result)
              |                         |
        28 Tools (auto-discovered)   Workspace (the brain)
              |                       SOUL.md (identity, evolves)
        Curriculum KB                 HEARTBEAT.md (schedule)
        search_materials              reading_report.md
        ingest_materials              |
              |                   Memory (3-layer)
        Standards (50 states)     identity
        CCSS, NGSS, C3           curriculum state
        state-specific           episodic (embeddings)
        gap analysis
              |
    Professional exports (DOCX, PPTX, PDF, Google Slides/Docs)
```

Custom YAML tools live in `~/.eduagent/tools/`. Define a name, description, parameters, and prompt template -- no code needed. The tool registry auto-discovers them alongside the built-in tools.

---

## Privacy

- **Local-first.** Your files stay on your machine. The curriculum knowledge base is a local SQLite database, never uploaded.
- **API keys in OS keychain.** macOS Keychain, Linux Secret Service, Windows Credential Manager.
- **No telemetry, no data collection, no accounts.**
- **Cloud disclaimer:** When using cloud AI providers, prompts are sent to their APIs. Review your provider's data policy. For maximum privacy, use local Ollama.

---

Built by Mr. Mac — Social Studies Educator — Long Island, NY
