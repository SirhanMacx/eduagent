# I Built an AI Teaching Assistant That Learns From Your Own Lesson Plans

## Three weeks ago I built something I use every day

My co-founder Jon teaches 8th grade Social Studies at a public school on Long Island, New York. He has 9 years of lesson plans, worksheets, DBQs, and assessments — hundreds of files spread across two computers and a Google Drive folder.

Every week, he spends hours generating new materials that look and feel exactly like the ones he already has. The Do Now prompts in his voice. The guided questions structured the way he structures them. The rubrics that match his grading philosophy.

He's not lazy. He's efficient. And he knows exactly what he wants — he just needs it faster.

So I built EDUagent.

---

## What it does

EDUagent is an open-source AI teaching assistant that:

1. **Ingests your existing materials** — PDFs, DOCX, PPTX, folders, Google Drive links, ZIP files
2. **Extracts your teaching persona** — your style, vocabulary, structure, pedagogical approach
3. **Generates new materials in your exact voice** — not generic AI output, but *you*

The output sounds like you because it was trained on you.

Here's an actual Do Now generated from Jon's materials:

> Alright, friends, as you settle in, I want you to take out your notebook and answer this question on the board: 'What does freedom mean to you? Is there ever a time when following the rules is more important than being free?' Take 5 minutes to jot down your honest thoughts. There are no wrong answers here; I just want to hear your voice.

That's not a generic AI prompt. That's 9 years of teaching style distilled into one question.

---

## The technical architecture

```
Teacher uploads files
       ↓
ingestor.py → extracts text from PDF/DOCX/PPTX/TXT
       ↓
persona.py → LLM extracts teaching fingerprint:
  - style tags (inquiry-based, Socratic, direct instruction...)
  - structural preferences (AIM questions, Do Nows, exit tickets...)
  - vocabulary patterns and tone
  - assessment philosophy
       ↓
corpus.py → stores examples with quality scores
       ↓
lesson.py → generates new lessons injecting:
  - teacher persona
  - few-shot examples from corpus (4+ star lessons)
  - subject/grade context
  - standards alignment
       ↓
Output: full lesson plan, worksheet, rubric, IEP modifications
```

The feedback flywheel is the key: every time a teacher rates a generated lesson 4+ stars, it enters the corpus as a reference example. Future generations include it as "match this quality bar." The system gets better the more it's used.

---

## What's shipped right now (v0.1.1)

Install it:

```bash
pip install eduagent
```

Generate a lesson:

```bash
eduagent ingest ./my-lessons/
eduagent generate "The American Revolution" --grade 8
```

What you get:
- Full unit plan with essential questions and daily lesson sequence
- Daily lesson: AIM, Do Now, document analysis, direct instruction, guided practice, exit ticket
- Worksheets and assessments
- IEP/504 accommodations automatically generated
- Standards alignment (50-state auto-detection)

**Also built:**
- Standalone Telegram bot (`eduagent bot --token TOKEN`) — mobile generation on the go
- Web dashboard with streaming generation (`eduagent server`)
- Student chatbot — students ask questions, answers come back in the teacher's voice
- Background task queue for long-running generation (full 10-lesson unit)
- TUI dashboard (Textual)
- MCP server — callable from any AI agent framework
- Voice note transcription (Whisper)
- Subject skill libraries for Social Studies, Math, Science, ELA, History + 6 more

---

## The student side

This is the part I'm most excited about.

When Jon teaches a lesson, he can "activate" it for students. They get a class code. They join the student chatbot. When they have questions at 11pm while doing homework, they ask the bot — and it answers the way Mr. Mac would answer it.

Not a generic AI. Not a search engine. Their specific teacher's voice, available 24/7 in any language, for every student simultaneously.

```
Student: "Why did the British pass the Stamp Act?"
Bot (in teacher's voice): "Great question — and this is exactly what I want you thinking about. 
Let me push back a little: why do governments raise taxes at all? 
Think about what Britain had just spent the last decade doing..."
```

For ESL students. For kids who are afraid to ask in class. For parents helping with homework. For students learning English who understand better in their first language.

---

## What's next

**v0.2.0: Hosted version**
- No `pip install`, no terminal, no API keys
- Teacher signs up, uploads their folder, starts generating
- Google Classroom export
- Shareable lesson links

**The two-sided platform play:**
- Teacher side builds the moat (persona extraction, corpus, quality scores)
- Student side is the distribution (every student whose teacher uses it becomes a potential entry point to their parent, who tells another teacher)

---

## Get involved

- **GitHub:** https://github.com/SirhanMacx/eduagent (star it if you want to see this grow)
- **PyPI:** `pip install eduagent`
- **Landing page:** https://eduagent-landing.netlify.app (waitlist for hosted version)

EDUagent is MIT licensed. If you're a teacher, I want your feedback. If you're a developer, I want your PRs. If you work in EdTech and want to talk, I want that conversation.

The best AI tutor isn't a generic model. It's the teacher who already knows the student.

---

*Built with Anthropic Claude, FastAPI, python-telegram-bot, Textual, and 9 years of Great Neck South Social Studies materials.*
