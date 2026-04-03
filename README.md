# Claw-ED

**Your AI co-teacher. Feed it your files, get lessons in your voice.**

<p align="center">
  <a href="https://pypi.org/project/clawed/"><img src="https://img.shields.io/pypi/v/clawed?color=blue" alt="PyPI version"></a>
  <a href="https://pypi.org/project/clawed/"><img src="https://img.shields.io/pypi/pyversions/clawed" alt="Python versions"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green" alt="MIT License"></a>
  <a href="https://github.com/SirhanMacx/Claw-ED/stargazers"><img src="https://img.shields.io/github/stars/SirhanMacx/Claw-ED" alt="GitHub stars"></a>
  <a href="https://pepy.tech/project/clawed"><img src="https://static.pepy.tech/badge/clawed" alt="Downloads"></a>
</p>

<p align="center">
  <img src="docs/ed-mascot.png" alt="Ed — the Claw-ED mascot" width="280">
</p>

---

```bash
pip install clawed
clawed
```

That's it. Claw-ED detects your setup, walks you through picking an AI provider, and starts learning your teaching style. No config files, no environment variables, no developer knowledge needed.

---

## What It Does

Claw-ED reads your existing lesson plans, handouts, slideshows, and assessments. It extracts your pedagogical fingerprint — how you structure a Do Now, what graphic organizers you use, how you scaffold for ELL and IEP students, your questioning patterns, your signature teaching moves.

Then it generates new lessons that actually match. Same structure, same voice, same scaffolding.

```bash
clawed ingest ~/Documents/Lessons/        # Teach it your style
clawed lesson "The Missouri Compromise" -g 8 -s "US History"
```

**What you get:**

- Complete daily lesson plans in your format (DOCX, PPTX, PDF)
- Unit plans with essential questions and pacing
- Assessments aligned to your state standards (50 states supported)
- Differentiated materials for ELL, IEP, and gifted students
- Interactive HTML games and simulations
- Homework, rubrics, sub plans, parent communications
- A compiled curriculum wiki you can query
- Morning prep that runs before you wake up

---

## First-Run Experience

When you run `clawed` for the first time, you see a guided setup:

1. Pick your AI provider (Google Gemini free tier, Ollama Cloud, Claude, GPT, or local Ollama)
2. Paste your API key
3. Choose terminal chat or Telegram bot
4. Optionally point it at your curriculum folder

Then you're chatting with your AI co-teacher. No command line knowledge required.

---

## Commands

| Command | What it does |
|---------|-------------|
| `clawed` | Chat with your AI co-teacher |
| `clawed ingest <path>` | Teach it your style from your files |
| `clawed lesson "Topic" -g 8 -s "Subject"` | Generate a daily lesson plan |
| `clawed unit "Topic" -g 9 -w 3` | Plan a 3-week unit |
| `clawed full "Topic" -g 10` | Full package: unit + lessons + materials |
| `clawed materials -l lesson.json` | Generate supporting materials |
| `clawed assess "Topic" --type dbq` | Generate assessments (DBQ, quiz, rubric) |
| `clawed differentiate -l lesson.json` | Create IEP/504/ELL modifications |
| `clawed game create "Topic" -g 8` | Interactive HTML learning game |
| `clawed simulate create "Topic" -g 9` | Interactive HTML simulation |
| `clawed kb compile` | Compile your curriculum into a searchable wiki |
| `clawed kb query "question"` | Ask questions against your wiki |
| `clawed kb lint` | Check your wiki for stale or missing articles |
| `clawed standards list -g 8 -s "Math"` | Browse state standards |
| `clawed gap-analyze` | Find curriculum coverage gaps |
| `clawed score -l lesson.json` | Score lesson quality |
| `clawed bot` | Start Telegram bot (chat from your phone) |
| `clawed serve` | Web dashboard |
| `clawed demo` | Try it without an API key |
| `clawed setup` | Re-run the setup wizard |

---

## Curriculum Wiki

Claw-ED compiles your ingested materials into an organized markdown wiki. Think of it as a personal knowledge base built from your own curriculum.

```bash
clawed ingest ~/Documents/Curriculum/     # Ingest your files
clawed kb compile                          # Compile into wiki articles
clawed kb query "What primary sources do I have on the Civil War?"
clawed kb lint                             # Check for stale or missing articles
```

The wiki is stored as plain markdown files in `~/.eduagent/wiki/` — viewable in any text editor, Obsidian, or VS Code. Incremental compilation means only changed documents get reprocessed.

---

## AI Providers

Claw-ED works with any AI provider. Pick one during setup:

| Provider | Cost | Best for |
|----------|------|----------|
| Google Gemini | Free tier available | Getting started |
| Ollama Cloud | $20/month unlimited | Daily use |
| Ollama Local | Free | Complete privacy |
| OpenRouter | Pay-per-use | Access to any model |
| Anthropic Claude | ~$0.05/lesson | Opus 4.6 / Sonnet 4.6 |
| OpenAI GPT | ~$0.04/lesson | GPT-5.4 |

Run `clawed setup` anytime to switch providers.

---

## Voice Learning

Claw-ED doesn't use a generic "teacher tone." It extracts your specific patterns:

- **Teaching structure:** How you organize lessons (I Do / We Do / You Do, stations, jigsaw)
- **Questioning style:** Your progression from recall to analysis to evaluation
- **Scaffolding moves:** Sentence starters, graphic organizers, writing frames you use
- **Assessment patterns:** Your Do Now format, exit ticket style, essay scaffolds
- **Classroom personality:** Your humor, your catchphrases, your signature moves

---

## Standards Alignment

Built-in support for all 50 US states:

- Common Core (CCSS) — Math and ELA
- Next Generation Science Standards (NGSS)
- C3 Framework — Social Studies
- State-specific frameworks (NY NGLS, TX TEKS, CA CCSS, VA SOL, and more)

---

## Professional Export

- **DOCX** — Print-ready with headers, differentiation callouts, and images
- **PPTX** — Themed slideshows with voice narration (`--narrate`)
- **PDF** — Clean layout for distribution
- **HTML** — Interactive games and simulations

---

## Privacy

- **Local-first.** Your files stay on your machine.
- **API keys in OS keychain.** macOS Keychain, Windows Credential Manager, Linux Secret Service.
- **No telemetry, no data collection, no accounts.**
- **Your choice of provider.** Use free local models for complete privacy, or cloud for quality.

---

## For Developers

```bash
git clone https://github.com/SirhanMacx/Claw-ED.git
cd Claw-ED
pip install -e ".[dev]"
pytest tests/
```

**MCP Server** — Expose Claw-ED tools to Claude Code, VS Code, and other AI editors:

```bash
clawed mcp-server
```

**Python API:**

```python
from clawed.lesson import generate_lesson
from clawed.models import AppConfig

config = AppConfig.load()
lesson = await generate_lesson(
    lesson_number=1, unit=unit_plan,
    persona=persona, config=config,
)
```

---

## Community

Built by a teacher for teachers. 20,000+ installs.

- [GitHub Discussions](https://github.com/SirhanMacx/Claw-ED/discussions) — share, request, ask
- [Report issues](https://github.com/SirhanMacx/Claw-ED/issues)
- [Star the repo](https://github.com/SirhanMacx/Claw-ED)

---

MIT License. Free for personal and commercial use.

[GitHub](https://github.com/SirhanMacx/Claw-ED) | [PyPI](https://pypi.org/project/clawed/) | [Changelog](CHANGELOG.md)
