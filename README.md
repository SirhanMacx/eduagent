# Claw-ED

**Meet Ed — your AI co-teacher. Feed him your files, get lessons in your voice.**

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

That's it. Ed introduces himself, walks you through picking an AI provider, and starts learning your teaching style. No config files, no environment variables, no developer knowledge needed.

---

## What Ed Does

Ed reads your existing lesson plans, handouts, slideshows, and assessments. He extracts your pedagogical fingerprint — how you structure a Do Now, what graphic organizers you use, how you scaffold for ELL and IEP students, your questioning patterns, your signature teaching moves.

Then he generates new lessons that actually match. Same structure, same voice, same scaffolding.

```bash
clawed ingest ~/Documents/Lessons/        # Teach him your style
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

When you run `clawed` for the first time, Ed greets you:

1. Pick your AI provider (Google Gemini free tier, Ollama Cloud, Claude, GPT, or local Ollama)
2. Paste your API key
3. Choose terminal chat or Telegram bot
4. Optionally point him at your curriculum folder

Then Ed starts asking about you — what you teach, your grade levels, your state. He learns your style from your files and generates content in your voice from day one.

---

## Commands

| Command | What it does |
|---------|-------------|
| `clawed` | Chat with Ed |
| `clawed ingest <path>` | Teach him your style from your files |
| `clawed lesson "Topic" -g 8 -s "Subject"` | Generate a daily lesson plan |
| `clawed unit "Topic" -g 9 -w 3` | Plan a 3-week unit |
| `clawed full "Topic" -g 10` | Full package: unit + lessons + materials |
| `clawed materials -l lesson.json` | Generate supporting materials |
| `clawed assess "Topic" --type dbq` | Generate assessments (DBQ, CRQ, quiz, rubric) |
| `clawed differentiate -l lesson.json` | Create IEP/504/ELL modifications |
| `clawed game create "Topic" -g 8` | Interactive HTML learning game |
| `clawed simulate create "Topic" -g 9` | Interactive HTML simulation |
| `clawed kb compile` | Compile your curriculum into a searchable wiki |
| `clawed kb query "question"` | Ask Ed questions about your wiki |
| `clawed kb lint` | Check your wiki for stale or missing articles |
| `clawed standards list -g 8 -s "Math"` | Browse state standards |
| `clawed gap-analyze` | Find curriculum coverage gaps |
| `clawed score -l lesson.json` | Score lesson quality |
| `clawed serve` | Web dashboard |
| `clawed demo` | Try Ed without an API key |
| `clawed setup` | Re-run the setup wizard |

---

## Telegram

Ed also works from your phone. During setup, he'll help you create a Telegram bot through @BotFather. Name the bot "Ed" (add a last name if you want — "Ed_History_Bot" or "Ed Smith"). The bot starts automatically in the background whenever you launch `clawed` — no extra terminal needed.

---

## Curriculum Wiki

Ed compiles your ingested materials into an organized markdown wiki.

```bash
clawed ingest ~/Documents/Curriculum/     # Feed him your files
clawed kb compile                          # He compiles wiki articles
clawed kb query "What primary sources do I have on the Civil War?"
clawed kb lint                             # Check for stale or missing articles
```

The wiki is stored as plain markdown in `~/.eduagent/wiki/` — viewable in any editor or Obsidian.

---

## AI Providers

Bring your own API key. Ed connects to any major provider:

- **Anthropic** — Claude Opus 4.6, Sonnet 4.6
- **OpenAI** — GPT-5.4, o3
- **Google** — Gemini 2.5 Flash, Pro
- **Ollama** — Cloud or local (Gemma 4, Llama 4, Qwen 3 — fully offline, free)
- **OpenRouter** — Access any model through a single key

Run `clawed setup` anytime to switch providers.

---

## Voice Learning

Ed doesn't use a generic "teacher tone." He extracts your specific patterns:

- **Teaching structure:** How you organize lessons (I Do / We Do / You Do, stations, jigsaw)
- **Questioning style:** Your progression from recall to analysis to evaluation
- **Scaffolding moves:** Sentence starters, graphic organizers, writing frames you use
- **Assessment patterns:** Your Do Now format, exit ticket style, CRQ structure, writing frameworks (TEA, RACE, CER)
- **Classroom personality:** Your humor, your catchphrases, your signature moves

---

## Standards Alignment

Ed knows every state's standards and testing formats:

- Common Core (CCSS) — Math and ELA
- Next Generation Science Standards (NGSS)
- C3 Framework — Social Studies
- State-specific: NY Regents (CRQ/DBQ), TX STAAR, CA CAASPP, MA MCAS, and 46 more

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

**MCP Server** — Expose Ed's tools to Claude Code, VS Code, and other AI editors:

```bash
clawed mcp-server
```

---

## Community

Built by a teacher for teachers. 20,000+ installs.

- [GitHub Discussions](https://github.com/SirhanMacx/Claw-ED/discussions)
- [Report issues](https://github.com/SirhanMacx/Claw-ED/issues)
- [Star the repo](https://github.com/SirhanMacx/Claw-ED)

---

MIT License. Free for personal and commercial use.

[GitHub](https://github.com/SirhanMacx/Claw-ED) | [PyPI](https://pypi.org/project/clawed/) | [Changelog](CHANGELOG.md)
