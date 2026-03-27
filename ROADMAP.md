# Roadmap

## v1.0.0 -- Agent Core (current)

Claw-ED is a personal AI teaching agent. Everything below is shipped.

- [x] **Curriculum Knowledge Base** -- uploaded files chunked, embedded, searchable
- [x] **search_my_materials tool** -- agent searches your files before generating
- [x] **Custom agent naming** -- teachers name their AI partner during onboarding
- [x] **Google Gemini provider** via API key
- [x] **Professional exports** -- DOCX headers/footers, PPTX section dividers
- [x] **Autonomous personality** -- search-first, status narration, proactive suggestions
- [x] Persona extraction from curriculum files (PDF, DOCX, PPTX, TXT)
- [x] Unit planning with essential questions and lesson sequences
- [x] Daily lesson generation (AIM, Do Now, instruction, exit ticket)
- [x] Worksheets, assessments, and rubrics
- [x] IEP/504 accommodations and differentiation
- [x] 50-state standards alignment
- [x] Telegram bot, web dashboard, terminal chat, TUI
- [x] Student chatbot (answers in teacher's voice, with transparency disclosure)
- [x] Ollama Cloud, Google Gemini, Anthropic Claude, OpenAI GPT support
- [x] MCP server (callable from any AI agent)
- [x] Subject skill libraries (13 subjects)
- [x] Agent-first gateway with 25 typed tools
- [x] Approval gates for consequential actions
- [x] 3-layer cognitive memory (identity, curriculum state, episodic)
- [x] Google Drive integration (OAuth, upload, organize, native Slides/Docs)
- [x] Proactive scheduling daemon
- [x] Custom teacher tools (YAML prompt-template)
- [x] Multi-step planner for complex requests
- [x] Autonomy progression with approval rate tracking (SQLite-backed)
- [x] Student insights tool (confusion topic detection)
- [x] Teacher preference learning from feedback
- [x] Closed feedback loop (ratings improve future generation)

## v1.1.0 -- Better Memory

Deeper understanding of your teaching over time.

- [ ] Long-term memory compression -- summarize old episodes, keep what matters
- [ ] Cross-session context threading -- pick up where you left off across days
- [ ] Preference drift detection -- notice when your style evolves and adapt
- [ ] Improved curriculum state tracking -- unit-level progress, not just lesson-level

## v1.2.0 -- Beautiful Materials

Polished, teacher-selectable visual themes for all exports.

- [ ] Theme selection during onboarding (clean modern, elementary colorful, high school formal)
- [ ] PPTX: full themed slide masters with consistent branding
- [ ] DOCX: themed headers, callout styles, rubric tables
- [ ] Template sharing -- share and download community themes

## v1.3.0 -- Multi-Agent Collaboration

Claw-ED talks to other agents.

- [ ] Department-level agent coordination -- share curriculum maps across teachers
- [ ] Agent-to-agent handoff -- your agent talks to a department lead's agent
- [ ] Shared memory pools for team planning
- [ ] MCP interop with other OpenClaw agents

## v1.4.0 -- Classroom Automation

The agent manages more of the operational load.

- [ ] Automated pacing guide adherence -- agent flags when you are behind or ahead
- [ ] Smart assignment sequencing -- scaffolded difficulty progression
- [ ] Parent communication automation -- progress updates drafted on schedule
- [ ] Grade-book integration (read-only) for data-informed generation

---

Want to influence the roadmap? [Open an issue](https://github.com/SirhanMacx/Claw-ED/issues) or start a discussion.
