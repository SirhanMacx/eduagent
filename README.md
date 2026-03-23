# EDUagent

> Your teaching files → your AI co-teacher.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![MIT License](https://img.shields.io/badge/License-MIT-green.svg)
![Works with Ollama](https://img.shields.io/badge/Ollama-supported-orange)

EDUagent ingests your existing curriculum materials and learns your teaching style, voice, and preferences. From a folder of your lesson plans, worksheets, and slides, it builds a digital version of you — one that can generate complete unit plans, daily lessons, and all supporting materials on demand.

---

## Why EDUagent?

| Without EDUagent | With EDUagent |
|---|---|
| Spend 2+ hours writing a single lesson plan from scratch | Generate a complete lesson plan in under a minute |
| Copy-paste templates that don't match your voice | AI learns YOUR teaching style, tone, and preferences |
| Manually align to CCSS / NGSS standards | Standards lookup built in — browse by grade and subject |
| Differentiation notes are an afterthought | IEP accommodations and differentiation generated automatically |
| Worksheets, quizzes, rubrics created separately | Full materials bundle generated alongside every lesson |
| Sharing means emailing Word docs | One command generates a shareable HTML page |

---

## What it does

EDUagent works in four steps:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  1. UPLOAD   │────▶│  2. LEARN   │────▶│  3. PLAN    │────▶│ 4. GENERATE │
│              │     │              │     │              │     │              │
│ Point at your│     │ AI extracts  │     │ You request  │     │ Full lesson  │
│ lesson plans,│     │ your teaching│     │ a unit on    │     │ plans, work- │
│ worksheets,  │     │ style, tone, │     │ any topic —  │     │ sheets, slide│
│ slides, PDFs │     │ vocabulary & │     │ EDUagent     │     │ outlines,    │
│              │     │ preferences  │     │ builds the   │     │ assessments, │
│              │     │ into a       │     │ unit plan    │     │ rubrics, IEP │
│              │     │ "persona"    │     │ in YOUR voice│     │ notes — all  │
│              │     │              │     │              │     │ in your voice│
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

1. **Upload** — Point EDUagent at a folder of your existing materials (PDF, DOCX, PPTX, TXT, MD, or a ZIP)
2. **Learn** — The AI reads your documents and extracts a structured teacher persona: your style, tone, vocabulary level, favorite strategies, and structural preferences
3. **Plan** — Request a unit on any topic. EDUagent generates a complete unit plan with essential questions, enduring understandings, daily lesson sequence, and assessment plan — all aligned to your persona
4. **Generate** — Expand any lesson into a full daily plan with Do-Now, direct instruction, guided practice, independent work, exit tickets, homework, and differentiation notes. Then generate all supporting materials: worksheets, quizzes, rubrics, slide outlines, and IEP accommodations

## Quickstart (5 minutes)

### Step 1: Install

```bash
pip install eduagent
```

### Step 2: Try the demo (no API key needed)

```bash
eduagent demo
# ╭──── EDUagent ────╮
# │ EDUagent Demo — no API key needed              │
# │ This is example output for: 8th Grade Science …│
# ╰─────────────────╯
#
#        Sample Unit Plan
# ┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
# ┃ Field                ┃ Value                                     ┃
# ┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
# │ Title                │ Life From Light: Understanding …           │
# │ Grade                │ 8th Grade Science                         │
# │ Duration             │ 2 weeks / 10 lessons                      │
# │ Essential Questions  │ How do plants convert light into food? …  │
# └──────────────────────┴───────────────────────────────────────────┘
```

Or open a beautiful HTML version in your browser:

```bash
eduagent demo --web
# Demo HTML saved: ~/eduagent_output/demo.html
# (opens in your default browser)
```

### Step 3: Point at your materials

```bash
eduagent ingest ~/Documents/my_lesson_plans/
# ╭──── Teacher Persona ────╮
# │ Style: Direct Instruction │
# │ Tone: warm and encouraging│
# │ Subject: Science          │
# │ Format: I Do / We Do / You Do│
# ╰──────────────────────────╯
```

### Step 4: Generate a full unit + all materials

```bash
eduagent full "Photosynthesis" --grade 8 --subject Science --weeks 3
# ╭──── Done! ────╮
# │ Unit: Life From Light: Understanding Photosynthesis │
# │ Lessons: 15   │
# │ Materials sets: 15│
# │ Output: ./eduagent_output│
# ╰───────────────╯
```

## Installation

**From PyPI:**

```bash
pip install eduagent
```

**Local development install:**

```bash
git clone https://github.com/SirhanMacx/eduagent.git
cd eduagent
pip install -e ".[dev]"
```

**Ollama (free, local, no API key needed):**

```bash
# Install Ollama: https://ollama.com
ollama pull llama3.2
eduagent config set-model ollama
```

## Configuration

Set the LLM backend:

```bash
eduagent config set-model anthropic  # Best quality (Claude Sonnet)
eduagent config set-model openai     # GPT-4o
eduagent config set-model ollama     # Free, local (Llama 3.2)
```

Override the specific model:

```bash
eduagent config set-model anthropic --model claude-opus-4-6
eduagent config set-model ollama --model mistral
```

**API keys** are read from environment variables:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
```

View current config:

```bash
eduagent config show
```

## Commands

| Command | Description |
|---------|-------------|
| `eduagent --version` | Print the current version |
| `eduagent demo` | Show sample output without an API key |
| `eduagent demo --web` | Generate an HTML demo page and open it in your browser |
| `eduagent ingest <path>` | Ingest teaching materials (folder, ZIP, or single file) and extract teacher persona |
| `eduagent persona show` | Display the current teacher persona |
| `eduagent unit <topic>` | Generate a complete unit plan with daily lesson sequence |
| `eduagent lesson <topic>` | Generate a detailed daily lesson plan for one lesson |
| `eduagent materials` | Generate all supporting materials (worksheet, quiz, rubric, slides, IEP notes) |
| `eduagent full <topic>` | End-to-end pipeline: unit plan + all lessons + all materials |
| `eduagent standards list --grade <G> --subject <S>` | List CCSS / NGSS / C3 standards for a grade and subject |
| `eduagent share --lesson-file <path>` | Generate a shareable HTML page from a saved lesson JSON |
| `eduagent config set-model <provider>` | Configure the LLM backend (anthropic, openai, ollama) |
| `eduagent config show` | Show current configuration |

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         CLI (typer + rich)                        │
│  eduagent ingest / unit / lesson / materials / full / config     │
│  eduagent demo / standards / share                               │
└───────┬──────────┬──────────┬──────────┬──────────┬──────────────┘
        │          │          │          │          │
        ▼          ▼          ▼          ▼          ▼
┌───────────┐┌──────────┐┌─────────┐┌──────────┐┌──────────┐
│ ingestor  ││ persona  ││ planner ││ lesson   ││ materials│
│           ││          ││         ││          ││          │
│ PDF/DOCX/ ││ Extract  ││ Unit    ││ Daily    ││ Worksheet│
│ PPTX/TXT  ││ teaching ││ plans   ││ lesson   ││ Quiz     │
│ → Document││ style    ││ with    ││ plans    ││ Rubric   │
│           ││ → Persona││ scope   ││ with     ││ Slides   │
│           ││          ││         ││ detail   ││ IEP notes│
└───────────┘└──────────┘└─────────┘└──────────┘└──────────┘
        │          │          │          │          │
        └──────────┴──────────┴──────────┴──────────┘
                              │
                    ┌─────────▼─────────┐
                    │    LLM Client     │
                    │                   │
                    │ Anthropic / OpenAI│
                    │ / Ollama          │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │    Exporter       │
                    │                   │
                    │ Markdown / PDF /  │
                    │ DOCX / HTML       │
                    └───────────────────┘
```

**Key modules:**

- **`models.py`** — Pydantic data models: `Document`, `TeacherPersona`, `UnitPlan`, `DailyLesson`, `LessonMaterials`, `AppConfig`
- **`ingestor.py`** — File ingestion pipeline (PDF via PyMuPDF, DOCX, PPTX, TXT/MD, ZIP)
- **`persona.py`** — Teacher persona extraction from ingested documents
- **`planner.py`** — Unit plan generation with LLM
- **`lesson.py`** — Daily lesson plan generation
- **`materials.py`** — Worksheet, assessment, rubric, slide outline, and IEP note generation
- **`standards.py`** — Built-in standards database (CCSS Math/ELA, NGSS, C3 Framework)
- **`exporter.py`** — Export to Markdown, PDF (reportlab), and DOCX (python-docx)
- **`llm.py`** — Unified async LLM client for Anthropic, OpenAI, and Ollama
- **`cli.py`** — Rich terminal interface with typer

## Features

- [x] Multi-format file ingestion (PDF, DOCX, PPTX, TXT, MD, ZIP)
- [x] AI-powered teacher persona extraction
- [x] Complete unit plan generation with essential questions and lesson sequence
- [x] Detailed daily lesson plans (Do-Now, instruction, practice, exit tickets)
- [x] Worksheet generation with answer keys
- [x] Assessment / quiz generation with rubrics
- [x] Slide deck outline generation with speaker notes
- [x] IEP accommodation and differentiation notes
- [x] Three LLM backends: Anthropic (Claude), OpenAI (GPT-4o), Ollama (local)
- [x] Export to Markdown, PDF, and DOCX
- [x] Full end-to-end pipeline (`eduagent full`)
- [x] Rich terminal UI with progress spinners and tables
- [x] Standards browser (CCSS, NGSS, C3 Framework)
- [x] Shareable HTML lesson pages
- [x] HTML demo page (`eduagent demo --web`)
- [ ] Google Classroom integration
- [ ] Real-time collaboration / co-planning
- [ ] Student-facing chatbot mode

## Roadmap

- [ ] Google Classroom integration
- [ ] Student-facing chatbot (ask the AI teacher questions)
- [ ] District-wide deployment (multi-teacher, admin dashboard)
- [ ] Differentiation AI (auto-generate IEP-aligned modifications)
- [ ] Parent communication generator
- [ ] Substitute teacher packet generator

## Contributing

Open to contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT — see [LICENSE](LICENSE) for details.
