# EDUagent Build Prompt

You are building EDUagent — an open-source, OpenClaw-level AI teaching assistant platform. This is meant to transform education. The target user is a K-12 teacher who uploads their existing curriculum files and gets back a fully functional AI version of themselves that can generate all future lesson materials in their own voice and style.

## Vision
A teacher uploads a Google Drive folder, flash drive dump, or ZIP of their existing materials (lesson plans, worksheets, slides, notes, rubrics, tests). EDUagent ingests everything, learns their teaching style, and becomes a digital co-teacher that:
1. Plans full curriculum units aligned to standards
2. Generates daily lesson plans in the teacher's own voice
3. Produces ALL supporting materials (worksheets, slides, assessments, rubrics, differentiation notes)
4. Runs locally (Ollama) or via API (Anthropic/OpenAI)
5. Integrates with OpenClaw as a skill plugin

## Build the following complete project:

### 1. Project Structure
```
eduagent/
├── README.md                    # Comprehensive docs with quickstart
├── pyproject.toml               # Modern Python packaging
├── eduagent/
│   ├── __init__.py
│   ├── cli.py                   # Rich CLI with typer
│   ├── ingestor.py              # File ingestion pipeline
│   ├── persona.py               # Teacher persona extractor
│   ├── planner.py               # Unit/curriculum planner
│   ├── lesson.py                # Lesson plan generator
│   ├── materials.py             # Materials generator
│   ├── exporter.py              # Export to PDF, DOCX, Markdown
│   ├── models.py                # Pydantic data models
│   └── prompts/
│       ├── persona_extract.txt
│       ├── unit_plan.txt
│       ├── lesson_plan.txt
│       ├── worksheet.txt
│       ├── assessment.txt
│       └── differentiation.txt
├── examples/
│   ├── sample_materials/
│   └── outputs/
├── skills/
│   └── eduagent/
│       └── SKILL.md
└── tests/
    └── test_basic.py
```

### 2. Core Modules

**ingestor.py** — Accepts:
- Local directory path (recursive scan for .pdf, .docx, .pptx, .txt, .md)
- Google Drive URL (using google-api-python-client)
- ZIP file (extract then scan)
Extracts text content, preserves document titles and structure.
Uses PyMuPDF for PDFs, python-docx for DOCX, python-pptx for PPTX.
Outputs structured list of Document objects with title, content, doc_type.

**persona.py** — Analyzes ingested documents to build a TeacherPersona:
- Teaching style (Socratic, direct instruction, inquiry-based, project-based)
- Vocabulary level (grade-appropriate, academic, casual)
- Structural preferences (warm-ups, exit tickets, graphic organizers, group work)
- Assessment style (rubric-based, point-based, portfolio)
- Preferred lesson format
Uses LLM to analyze documents and extract as structured JSON.

**models.py** — Pydantic models for:
- Document, TeacherPersona, Unit, DailyLesson, LessonMaterials, Assessment, WorksheetItem

**planner.py** — Given: subject, grade_level, topic, standards (list), duration_weeks, persona
Generates a UnitPlan with:
- Unit overview and essential questions (3-5)
- Enduring understandings
- Daily lesson sequence with topics and brief descriptions
- Formative and summative assessment plan
- Required materials list

**lesson.py** — Given: lesson_topic, unit_context (UnitPlan), lesson_number, persona
Generates a DailyLesson with:
- Objective/Aim (SWBAT format)
- Standards alignment
- Do-Now / Warm-up (5 min)
- Direct Instruction notes (full teacher script/outline, 15-20 min)
- Guided Practice activity with instructions (15-20 min)
- Independent Work / Partner activity (10 min)
- Exit Ticket (3 questions)
- Homework (optional, toggleable)
- Differentiation notes (accommodations for struggling + enrichment for advanced)
All written in teacher persona voice.

**materials.py** — Given a DailyLesson, generates LessonMaterials:
- Student worksheet (complete, ready to print)
- Assessment / quiz (5-10 questions, MC/short answer/essay)
- Rubric (if written component)
- Slide deck outline (title + 6-8 content slides)
- IEP accommodation notes
All in teacher persona voice.

**cli.py** — Rich CLI using typer with commands:
- `eduagent ingest <path>` — ingest files, save persona
- `eduagent persona show` — display current teacher persona
- `eduagent unit <topic> --grade 8 --subject science --weeks 3` — plan a unit
- `eduagent lesson <topic> --unit-file unit.json --lesson-num 1` — generate a lesson
- `eduagent materials --lesson-file lesson.json` — generate all materials
- `eduagent full <topic> --grade 8 --subject science --weeks 3` — end-to-end
- `eduagent config set-model <ollama/anthropic/openai>` — configure LLM backend
Beautiful terminal output with Rich panels, progress bars, and tables.

**exporter.py** — Export to Markdown (default), PDF (weasyprint/reportlab), DOCX (python-docx).

### 3. LLM Backend
Support three backends via config:
1. **Anthropic** (claude-sonnet-4-6 by default) — best quality
2. **OpenAI** (gpt-4o by default)
3. **Ollama** (llama3.2 by default) — fully local, free

Unified LLMClient class with async support. API keys from env vars or ~/.eduagent/config.json.

### 4. Prompts
Write detailed, thoughtful system prompts for each generation task in the prompts/ directory. These prompts are the heart of the product. Each should instruct the model to use the teacher persona throughout, specify exact output format, and include examples of good output.

### 5. README.md
Write a comprehensive, compelling README:
- One-sentence pitch ("Your teaching files, your AI co-teacher")
- Installation (pip install eduagent + ollama quickstart)
- 5-minute quickstart with real example commands
- Architecture diagram (ASCII)
- Feature list with checkboxes
- Roadmap (Google Classroom integration, student-facing chatbot, district deployment)
- Contributing guide
- License: MIT

### 6. Example outputs
In examples/outputs/, create realistic example files:
- A sample unit plan for "8th Grade Photosynthesis Unit" (Markdown)
- A sample daily lesson plan (Markdown)
- A sample student worksheet (Markdown)

### 7. OpenClaw SKILL.md
Write a proper OpenClaw skill file so any OpenClaw user can use this as a plugin.

## Quality bar
This is an OpenClaw-level release. Code must be:
- Clean, typed Python with docstrings
- Properly packaged with pyproject.toml
- Actually runnable — implement the real logic, no placeholder stubs
- Well-commented where logic is non-obvious
- Tested at basic level

Do NOT cut corners. Do NOT leave TODOs without implementation. Build the real thing.

When completely finished, run this command:
openclaw system event --text "Done: EDUagent MVP built at ~/Projects/eduagent" --mode now
