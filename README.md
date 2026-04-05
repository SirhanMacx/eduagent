# Claw-ED

**Ed is your AI co-teacher. He learns your voice, preps your materials, and gets better every day.**

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

## The Pitch

You're a teacher. You spend hours every week building lesson plans, handouts, slideshows, and assessments. You have hundreds of files across Google Drive, your laptop, and that USB drive from 2019.

Ed reads all of it. He extracts your teaching style — how you write a Do Now, what sources you use, how you scaffold for ELL students, your TEA paragraphs, your exit ticket format. Then he generates new lessons that sound like YOU wrote them.

```bash
pip install clawed
clawed
```

That's it. Ed introduces himself, asks about you, and starts working. Two commands. No config files.

---

## The CLI is the Product

Claw-ED is a **command-line teaching agent.** Not a web app. Not a chatbot wrapper. A real CLI tool that lives in your terminal and works like a colleague.

```
$ clawed

  🍎 Hey Mr. Maccarello! What are we working on today?

❯ Make me a lesson on the causes of the French Revolution for 10th grade

  Building your lesson now...
  Searching your materials for relevant content...
  Found 3 documents on this topic in your KB.
  Generating lesson package...

  ✓ Causes_of_the_French_Revolution_teacher.docx (6MB)
  ✓ Causes_of_the_French_Revolution_student.docx (6MB)
  ✓ Causes_of_the_French_Revolution_slides.pptx (5.2MB)

  All three files ready. Want me to start on tomorrow's lesson?
```

Ed also works from your phone via **Telegram** — same brain, same memory, same files. Ask him to prep tomorrow's lesson from the subway.

---

## What Makes Ed Different

**He's not a prompt wrapper.** Ed is a fully autonomous agent with 45+ tools:

- 🧠 **Learns your voice** — extracts your pedagogical fingerprint from your actual files
- 📚 **181K+ chunk knowledge base** — ONNX MiniLM embeddings with FTS5 search
- 🔍 **Searches your materials first** — before generating, always checks what you already have
- 🖼️ **Uses your images** — extracts photos, maps, diagrams from your PPTX/DOCX and reuses them
- 🌐 **Browses the web** — finds primary sources, current events, academic papers
- 📊 **Self-improving** — tracks quality, learns from your edits, distills insights into soul.md
- 🗂️ **Karpathy wiki** — compiles your curriculum into an organized, queryable wiki
- 🎮 **Interactive games** — generates self-contained HTML learning games
- 🤖 **Self-equipping** — can install packages, create custom tools, modify his own config
- 📱 **One brain** — CLI and Telegram share the same KB, memory, identity, and sessions

---

## Quick Start

```bash
pip install clawed
clawed
```

Ed will:
1. Ask you to pick an AI provider (Google free tier, Ollama, Claude, GPT, or local)
2. Learn your name, subjects, grades, and state
3. Ask for your curriculum folder
4. Start generating lessons in your voice

---

## Commands

```bash
# Talk to Ed
clawed                                    # Interactive chat

# Generate content
clawed lesson "Topic" -g 8 -s "Subject"  # Daily lesson plan
clawed unit "Topic" -g 9 -w 3            # 3-week unit
clawed full "Topic" -g 10                # Full package: unit + lessons + materials
clawed assess "Topic" --type crq          # Assessments (CRQ, DBQ, quiz, rubric)
clawed game create "Topic" -g 8           # Interactive HTML game
clawed simulate create "Topic" -g 9       # Interactive simulation
clawed differentiate -l lesson.json       # IEP/504/ELL modifications

# Knowledge base
clawed ingest ~/Documents/Lessons/        # Teach Ed your style
clawed kb compile                         # Compile curriculum wiki
clawed kb query "What sources do I have on the Civil War?"
clawed kb lint                            # Wiki health check

# System
clawed bot                                # Start Telegram bot
clawed drive auth                         # Connect Google Drive
clawed schedule list                      # View scheduled tasks
clawed setup                              # Re-run setup wizard
```

---

## AI Providers

Bring your own key. Ed works with anything:

| Provider | Model | Cost | Quality |
|----------|-------|------|---------|
| **Ollama Cloud** | minimax-m2.7 | ~$5/mo | Good |
| **Google** | Gemini 2.5 Flash | Free tier | Good |
| **Anthropic** | Claude Sonnet/Opus | ~$0.05/lesson | Excellent |
| **OpenAI** | GPT-4.1 | ~$0.03/lesson | Excellent |
| **Ollama Local** | Llama/Qwen/Gemma | Free (offline) | Varies |
| **OpenRouter** | Any model | Varies | Varies |

Or use **Claude Code's OAuth** — if you have Claude Code installed, Ed picks up the token automatically.

---

## How Ed Learns Your Voice

Ed doesn't generate generic lessons. He reads your files and extracts:

- **Lesson structure** — I Do / We Do / You Do, stations, gallery walks, Socratic seminars
- **Assessment patterns** — CRQ format, exit ticket style, Do Now structure, writing frameworks (TEA, RACE, CER)
- **Scaffolding moves** — sentence starters, graphic organizers, word banks
- **Source preferences** — primary sources you use, your favorite historians, document types
- **Classroom personality** — your humor, catchphrases, grouping strategies

This lives in `~/.eduagent/workspace/soul.md` — Ed's teaching soul. You can read it, edit it, or let Ed update it as he learns.

---

## The Karpathy Wiki

Inspired by [Andrej Karpathy's LLM wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). Ed compiles your raw curriculum files into organized markdown articles:

```bash
clawed ingest ~/Documents/Curriculum/     # Raw files → chunks
clawed kb compile                         # Chunks → wiki articles
clawed kb query "What primary sources do I have on imperialism?"
```

The wiki lives at `~/.eduagent/wiki/` — plain markdown, viewable in any editor or Obsidian.

---

## Self-Improvement

Ed gets better without being told. The self-distillation loop:

1. **Generate** → Ed creates a lesson
2. **Track** → Teacher rates it or edits it
3. **Analyze** → Ed detects patterns ("teacher always adds more scaffolding")
4. **Distill** → Ed writes rules to soul.md ("always include sentence starters for ELL")
5. **Improve** → Next lesson follows the new rules

Based on [Zhang et al. 2025](https://arxiv.org/abs/2604.01193) — self-distillation adapted for teaching.

---

## Privacy

- **Local-first.** Your files stay on your machine.
- **API keys in OS keychain.** Not in config files.
- **No telemetry. No accounts. No data collection.**
- **Your choice of provider.** Use fully offline Ollama for complete privacy.

---

## Contributing

Built by a teacher, for teachers. We're building a community.

```bash
git clone https://github.com/SirhanMacx/Claw-ED.git
cd Claw-ED
pip install -e ".[dev]"
pytest tests/
```

**Want to help?**
- Report bugs → [GitHub Issues](https://github.com/SirhanMacx/Claw-ED/issues)
- Share ideas → [GitHub Discussions](https://github.com/SirhanMacx/Claw-ED/discussions)
- Star the repo → [⭐ SirhanMacx/Claw-ED](https://github.com/SirhanMacx/Claw-ED)

**MCP Server** — Connect Ed to Claude Code, VS Code, or any MCP-compatible editor:
```bash
clawed mcp-server
```

---

MIT License. Free forever. Built in New York by a Social Studies teacher who got tired of spending Sundays on lesson plans.

[GitHub](https://github.com/SirhanMacx/Claw-ED) | [PyPI](https://pypi.org/project/clawed/) | [Changelog](CHANGELOG.md)
