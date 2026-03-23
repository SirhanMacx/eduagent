---
name: eduagent
description: AI teaching assistant for K-12 educators. Use when a teacher asks
             for lesson plans, unit plans, worksheets, assessments, differentiation
             strategies, standards alignment, current events for lessons, or any
             education-related curriculum planning. Also handles student tutoring
             mode when a student asks about course content. Connects to Google
             Drive or local disk for curriculum ingestion.
---

# EDUagent — AI Teaching Assistant

## What It Does

EDUagent is an AI teaching partner that lives in your Telegram. It learns your teaching style from your existing lesson plans, then generates all your future curriculum materials in your exact voice.

It also powers a student-facing chatbot — students can ask questions about the current lesson and get answers the way their teacher would give them.

## Teacher Commands

Any natural language works. You don't need specific commands. But these are recognized:

**Setup**
- "connect my Google Drive" or share a Drive URL → ingests your curriculum
- "connect my folder /path/to/files" → ingests local materials
- `/setup` → guided configuration
- `/status` → shows current persona and config

**Generation**
- "plan a unit on [topic] for [grade] [subject], [N] weeks"
- "generate a lesson on [topic]"
- "make a worksheet for [topic]"
- "create an assessment for [unit]"
- "write differentiation notes for struggling learners"
- "suggest a bell ringer for tomorrow's lesson"

**Search & Research**
- "find a current news story about [topic] for my class"
- "what does NGSS say about [topic] for grade [N]?"
- "find a video resource on [topic]"

**Export**
- "export that as a PDF"
- "give me the Google Classroom version"
- "share that lesson with my students"

## Student Commands (when configured)

Students talk to a separate bot (same backend, different persona mode):
- Ask questions about the current lesson
- Request explanations in different ways
- Take a practice quiz
- Get hints (not direct answers)

## Setup Instructions

### Option 1: Talk to it (recommended)
Just message the bot: "Hi, I'm a 8th grade science teacher at Great Neck South. Here's my Google Drive folder: [link]"

### Option 2: Manual config
```bash
pip install eduagent
eduagent setup    # guided wizard
eduagent serve    # starts web UI at localhost:8000
```

### API Keys Required (choose one)
- **Anthropic** (best quality): `ANTHROPIC_API_KEY` env var or via `/setup`  
- **OpenAI** (GPT-4o): `OPENAI_API_KEY` env var or via `/setup`
- **Ollama Cloud** (free): URL + model name, no key needed

### Optional
- **Tavily API key** for web search: `TAVILY_API_KEY`
- **Google Drive**: share link or service account JSON

## How It Learns Your Style

EDUagent analyzes your existing materials and extracts:
- Your teaching style (direct instruction, Socratic, inquiry-based, etc.)
- Vocabulary level and tone
- Structural preferences (do you always use exit tickets? graphic organizers?)
- Assessment approach

Everything it generates afterward matches that profile. The output sounds like you wrote it — because it learned from you.

## Privacy

- Your materials are processed locally or via your chosen API
- Nothing is shared with third parties beyond your selected LLM provider
- API keys stored in OS keychain (not in config files)
- Google Drive content cached locally, never uploaded elsewhere
