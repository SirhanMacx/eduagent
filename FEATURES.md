# Agent Capabilities

Claw-ED is a personal AI teaching agent. These are the things it can do.

---

## Curriculum Knowledge Base

Feed the agent your lesson plans, handouts, unit plans, and slides. It chunks every document into searchable sections and stores them in a local semantic database. When you ask for anything, it searches your materials first -- grounding every generation in your own prior work.

Powered by Ollama embeddings (mxbai-embed-large) with TF-IDF fallback for offline use.

---

## Voice Learning

The agent reads your files and extracts your teaching fingerprint -- style, tone, vocabulary, structure, assessment preferences. Generated content sounds like you wrote it, not like a generic AI template.

---

## Generation -- in your voice

- Unit plans with essential questions and daily lesson sequences
- Daily lessons (AIM, Do Now, instruction, guided practice, exit ticket)
- Worksheets, quizzes, rubrics, and DBQ prompts
- IEP/504 accommodations and differentiation (struggling, advanced, ELL)
- Substitute teacher packets and parent communications
- Professional PPTX slides with section dividers
- Polished DOCX with headers, footers, and IEP/ELL callout boxes

---

## Standards Alignment -- 50 states

- CCSS, NGSS, C3, and state-specific frameworks
- Curriculum gap analyzer -- find what you have not covered yet
- Standards search by subject and grade

---

## Autonomous Behavior

The agent does not just respond to commands. It takes initiative:

- **Search-first:** Searches your curriculum files before every generation
- **Status narration:** "Searching your files... Found 3 related lessons. Generating now..."
- **Proactive suggestions:** "I made your lesson. Want me to create a matching worksheet?"
- **Scheduled tasks:** Morning prep, weekly planning, feedback digests -- configurable in HEARTBEAT.md
- **Multi-step planning:** Complex requests like "prepare my week" trigger a step-by-step execution plan
- **Autonomy progression:** After consistent approvals, the agent offers to auto-approve routine actions

---

## Interfaces

| Method | How to use it |
|--------|--------------|
| **Terminal chat** | `clawed` or `clawed chat` |
| **Telegram bot** | `clawed bot --token TOKEN` |
| **Web dashboard** | `clawed serve` |
| **Full-screen TUI** | `pip install 'clawed[tui]'` then `clawed tui` |
| **Student bot** | Students join with class codes, ask questions in your voice |
| **MCP server** | Expose tools to any AI agent |

---

## 3-Layer Cognitive Memory

| Layer | What it stores | How it works |
|-------|---------------|-------------|
| **Identity** | Teaching style, subject, grades, voice | Persona extraction from your files |
| **Curriculum** | Current unit, pacing state, coverage | SQLite projections |
| **Episodic** | Past interactions, semantic recall | Embedding model (Ollama / TF-IDF) |

Memory improves over time. Ratings, edits, and approvals all feed back into future generations.

---

## Safety Guardrails

- Approval gates for consequential actions (publishing, sharing with students)
- Student-facing output always requires teacher review
- Closed feedback loop: ratings improve future generation
- Custom teacher tools via YAML -- no code needed, full agent integration

---

## Privacy

- Your files never leave your machine (unless you choose a cloud LLM)
- Curriculum knowledge base is local SQLite -- never uploaded
- API keys stored in OS keychain
- No telemetry, no tracking, no data collection
- Works fully offline with local Ollama
