# EDUagent 🎓

> Your teaching files → your AI co-teacher.

EDUagent ingests your existing curriculum materials and learns your teaching style, voice, and preferences. From a folder of your lesson plans, worksheets, and slides, it builds a digital version of you — one that can generate complete unit plans, daily lessons, and all supporting materials on demand.

[![PyPI version](https://img.shields.io/pypi/v/eduagent)](https://pypi.org/project/eduagent/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

---

## ✨ What it does

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

## 🚀 Quickstart (5 minutes)

### Step 1: Install

```bash
pip install eduagent
```

### Step 2: Point at your materials

```bash
eduagent ingest ~/Documents/my_lesson_plans/
```

```
╭──── EDUagent ────╮
│ Ingesting materials from /Users/you/Documents/my_lesson_plans │
╰──────────────────╯

  Ingested Documents
 ┏━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━┓
 ┃ # ┃ Title                    ┃ Type ┃      Size ┃
 ┡━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━┩
 │ 1 │ Cell Division Unit       │ DOCX │ 4,231 chars│
 │ 2 │ Photosynthesis Slides    │ PPTX │ 2,890 chars│
 │ 3 │ Weekly Warmups           │ PDF  │ 1,456 chars│
 └───┴──────────────────────────┴──────┴───────────┘

╭──── Teacher Persona ────╮
│ Style: Direct Instruction│
│ Tone: warm and encouraging│
│ Subject: Science         │
│ Format: I Do / We Do / You Do│
╰─────────────────────────╯
```

### Step 3: Generate a unit

```bash
eduagent unit "Photosynthesis" --grade 8 --subject Science --weeks 3
```

### Step 4: Get all materials (unit + every lesson + worksheets + assessments)

```bash
eduagent full "Photosynthesis" --grade 8 --subject Science --weeks 3
```

```
╭──── Done! ────╮
│ Unit: Life From Light: Understanding Photosynthesis │
│ Lessons: 15   │
│ Materials sets: 15│
│ Output: ./eduagent_output│
╰───────────────╯
```

## 📦 Installation

**From PyPI:**

```bash
pip install eduagent
```

**Local development install:**

```bash
git clone https://github.com/eduagent/eduagent.git
cd eduagent
pip install -e ".[dev]"
```

**Ollama (free, local, no API key needed):**

```bash
# Install Ollama: https://ollama.com
ollama pull llama3.2
eduagent config set-model ollama
```

## 🔧 Configuration

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

## 📋 Commands

| Command | Description |
|---------|-------------|
| `eduagent ingest <path>` | Ingest teaching materials (folder, ZIP, or single file) and extract teacher persona |
| `eduagent persona show` | Display the current teacher persona |
| `eduagent unit <topic>` | Generate a complete unit plan with daily lesson sequence |
| `eduagent lesson <topic>` | Generate a detailed daily lesson plan for one lesson |
| `eduagent materials` | Generate all supporting materials for a lesson (worksheet, quiz, rubric, slides, IEP notes) |
| `eduagent full <topic>` | End-to-end pipeline: unit plan + all lessons + all materials |
| `eduagent config set-model <provider>` | Configure the LLM backend (anthropic, openai, ollama) |
| `eduagent config show` | Show current configuration |

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         CLI (typer + rich)                        │
│  eduagent ingest / unit / lesson / materials / full / config     │
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
                    │ DOCX              │
                    └───────────────────┘
```

**Key modules:**

- **`models.py`** — Pydantic data models: `Document`, `TeacherPersona`, `UnitPlan`, `DailyLesson`, `LessonMaterials`, `AppConfig`
- **`ingestor.py`** — File ingestion pipeline (PDF via PyMuPDF, DOCX, PPTX, TXT/MD, ZIP)
- **`persona.py`** — Teacher persona extraction from ingested documents
- **`planner.py`** — Unit plan generation with LLM
- **`lesson.py`** — Daily lesson plan generation
- **`materials.py`** — Worksheet, assessment, rubric, slide outline, and IEP note generation
- **`exporter.py`** — Export to Markdown, PDF (reportlab), and DOCX (python-docx)
- **`llm.py`** — Unified async LLM client for Anthropic, OpenAI, and Ollama
- **`cli.py`** — Rich terminal interface with typer

## ✅ Features

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
- [ ] Google Classroom integration
- [ ] Real-time collaboration / co-planning
- [ ] Standards auto-alignment (CCSS, NGSS)
- [ ] Student-facing chatbot mode

## 🗺️ Roadmap

- [ ] Google Classroom integration
- [ ] Student-facing chatbot (ask the AI teacher questions)
- [ ] District-wide deployment (multi-teacher, admin dashboard)
- [ ] Standards database (auto-align to CCSS, NGSS, state standards)
- [ ] Differentiation AI (auto-generate IEP-aligned modifications)
- [ ] Parent communication generator
- [ ] Substitute teacher packet generator

## 🤝 Contributing

Open to contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT — see [LICENSE](LICENSE) for details.
