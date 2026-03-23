---
name: eduagent
description: AI teaching assistant — upload curriculum files and generate lesson plans, unit plans, worksheets, and assessments in your teaching voice. Use when: teacher needs to plan a unit, generate a lesson, create materials, or build assessments. Runs locally with Ollama or via API.
---

# EDUagent Skill

## When to Use

Use this skill when a teacher or educator needs to:

- **Plan a curriculum unit** from scratch on any topic
- **Generate a daily lesson plan** with Do-Now, instruction, practice, exit tickets
- **Create supporting materials** — worksheets, quizzes, rubrics, slide outlines, IEP notes
- **Ingest existing teaching materials** to learn the teacher's voice and style
- **Run the full pipeline** — unit plan + all lessons + all materials in one command

## How to Use

### 1. Ingest materials (one-time setup)

Point EDUagent at a folder of existing lesson plans, worksheets, or slides. It extracts a "teacher persona" — your style, tone, vocabulary, and preferences.

```bash
eduagent ingest ~/Documents/my_lesson_plans/
```

Supports: PDF, DOCX, PPTX, TXT, MD, ZIP archives.

### 2. Generate a unit plan

```bash
eduagent unit "Photosynthesis" --grade 8 --subject Science --weeks 3
```

Produces a complete unit plan with:
- Essential questions and enduring understandings
- Daily lesson sequence (topic + description for each day)
- Assessment plan (formative + summative)
- Standards alignment

### 3. Generate a single lesson

```bash
eduagent lesson "Intro to Photosynthesis" --unit-file ./eduagent_output/unit_*.json --lesson-num 1
```

Produces a detailed daily plan:
- SWBAT objective
- Do-Now warm-up
- Direct instruction (teacher-script style)
- Guided practice activity
- Independent work
- Exit ticket questions with expected responses
- Homework assignment
- Differentiation notes (struggling, advanced, ELL)

### 4. Generate all materials for a lesson

```bash
eduagent materials --lesson-file ./eduagent_output/lesson_01.json
```

Produces:
- Student worksheet with answer key
- Assessment questions (multiple choice, short answer)
- Scoring rubric
- Slide deck outline with speaker notes
- IEP accommodation notes

### 5. Full pipeline (everything at once)

```bash
eduagent full "Photosynthesis" --grade 8 --subject Science --weeks 3
```

Generates: unit plan → every daily lesson → all materials for every lesson.

## What Gets Generated

```
eduagent_output/
├── persona.json                    # Your extracted teaching persona
├── unit_life_from_light.json       # Unit plan (JSON)
├── life_from_light.md              # Unit plan (Markdown)
├── lesson_01.json                  # Lesson plans (JSON)
├── lesson_01.md                    # Lesson plans (Markdown)
├── materials_intro_to_photo.json   # Materials (JSON)
├── materials_intro_to_photo.md     # Materials (Markdown)
└── ...
```

Export formats: `--format markdown` (default), `--format pdf`, `--format docx`

## Setup

### Option A: Ollama (free, local, no API key)

```bash
pip install eduagent
ollama pull llama3.2
eduagent config set-model ollama
```

### Option B: Anthropic (best quality)

```bash
pip install eduagent
export ANTHROPIC_API_KEY="sk-ant-..."
eduagent config set-model anthropic
```

### Option C: OpenAI

```bash
pip install eduagent
export OPENAI_API_KEY="sk-..."
eduagent config set-model openai
```

## Example Workflow

```bash
# 1. First time: ingest your materials
eduagent ingest ~/Google\ Drive/8th\ Grade\ Science/

# 2. Plan a new unit
eduagent unit "Chemical Reactions" --grade 8 --subject Science --weeks 2

# 3. Generate everything
eduagent full "Chemical Reactions" --grade 8 --subject Science --weeks 2 --format pdf

# 4. Check your persona
eduagent persona show

# 5. Adjust the LLM backend
eduagent config set-model ollama --model mistral
```
