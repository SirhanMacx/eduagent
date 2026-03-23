# EDUagent Next Build Wave — Student Bot & Telegram Live

Build the following features on top of the existing codebase at ~/Projects/eduagent/. All code must be clean, typed, tested, committed, and pushed when done.

## Feature 1: Student Extension — Polished Standalone Experience

The student bot already exists in `eduagent/student_bot.py` and `eduagent/student_cli.py`. This wave makes it production-quality.

### 1a. Class Code System (teacher-controlled)

In `eduagent/student_bot.py` and `eduagent/database.py`:
- Teachers create class codes: `eduagent class create --name "Period 3 Global Studies" --topic "Unit 4: WWI" --expires 2026-06-15`
- Class code is a 6-character alphanumeric (e.g., `MR-MAC-3`)
- Teacher can restrict what the student bot knows: `--lessons "lesson_ids" --units "unit_ids"`
- Students join with: `/join MR-MAC-3` in the Telegram student bot
- Teacher can revoke access: `eduagent class revoke --code MR-MAC-3 --student student_id`
- Teacher sees student activity: `eduagent class stats --code MR-MAC-3`

Add to `eduagent/database.py`:
```python
# Tables needed:
# class_codes: id, code, teacher_id, name, topic, allowed_lesson_ids (JSON), expires_at, created_at
# student_enrollments: id, student_id, class_code, enrolled_at, last_active
# student_questions: id, student_id, class_code, question, answer, created_at
```

### 1b. Student Web View

Add `GET /student/{class_code}` — a minimal web page showing:
- Class name and teacher name
- "Scan to chat on Telegram" QR code (linking to the student bot)
- Recent lesson topics the class is studying
- No student data shown (privacy)

Add CLI: `eduagent class qr --code MR-MAC-3 --output qr.png` — generates QR code image

### 1c. Student Progress Report

Teachers can pull a weekly report: `eduagent class report --code MR-MAC-3 --week 2026-W12`
Shows:
- Questions asked per student (anonymized count)
- Most common topics students asked about
- Questions the bot couldn't answer well (low confidence)
- Recommended: "Students struggled with X — consider reviewing it"

## Feature 2: Telegram Bot — Live Integration Test

The `eduagent/telegram_bot.py` exists but may not have been tested with a real token. Make it bulletproof.

### 2a. Health Check Command

Add `/health` command to the Telegram bot:
- Returns: current model, persona loaded (yes/no), lesson count, corpus size
- Format: clean text response, no markdown breaks in Telegram

### 2b. Command Menu Registration

When bot starts, register the command menu with BotFather API:
```
/lesson - Generate a daily lesson
/unit - Plan a unit
/assess - Create an assessment
/worksheet - Generate a worksheet
/help - Show all commands
/health - System status
```

Use `setMyCommands` API call on startup.

### 2c. Conversation State Machine

Currently the bot may lose context between messages. Fix it:
- In `eduagent/telegram_bot.py`, use a state dict keyed by `chat_id`
- States: IDLE → COLLECTING_LESSON_INFO → GENERATING → DONE
- If user sends a message mid-generation, respond: "Still working on your lesson — almost done!"
- After generation, offer quick actions: [Rate this] [Generate worksheet] [Export PDF]

### 2d. Error Recovery

- If LLM call fails, retry once with backoff
- If retry fails: "Couldn't generate right now. Try `/lesson` again in a minute."
- Log errors to `~/.eduagent/errors.log`
- Never show raw exception tracebacks to users

### 2e. Integration Test

Add `tests/test_telegram_integration.py`:
- Mock the Telegram API calls
- Test: /start → welcome message
- Test: /lesson → bot asks for topic → user responds → lesson generated
- Test: /health → returns status string
- Test: error recovery (LLM fails → retry → fallback message)

## Feature 3: Onboarding Flow Polish

The `eduagent/onboarding.py` exists. Make the first-run experience smooth.

### 3a. Step-by-step wizard improvements

Current: asks for files, extracts persona, done.
Add:
- After persona extraction, show a preview: "I learned that you teach 8th grade Social Studies using inquiry-based learning. Your signature move is the DBQ. Is this right? [y/n]"
- If n: ask for correction, re-extract with feedback
- After confirmation, auto-generate ONE sample lesson so the teacher immediately sees value
- End with: "Setup complete! Here's how to use me..." (show 3 key commands)

### 3b. Model auto-detection

On first run, detect what's available:
- Check for `ANTHROPIC_API_KEY` in environment
- Check for `OPENAI_API_KEY` in environment  
- Check if Ollama is running: `curl http://localhost:11434/api/tags`
- If Ollama: check if minimax-m2.7, llama3.2, or mistral is available
- Auto-select best available model, tell user what was chosen
- If nothing: tell user how to set up (don't fail silently)

### 3c. Progress bar during ingestion

Current: ingestion is silent. Add progress indication:
- Use `rich.progress` for file ingestion
- Show: "Reading lesson_plan_unit4.docx... (47/246 files)"
- Show: "Extracting teaching style patterns..."
- Show: "✓ Persona saved — Mr. Mac profile ready"

## Feature 4: Web Dashboard — Key Missing Pieces

Review `eduagent/api/` and complete these specific gaps:

### 4a. Lesson list page

`GET /lessons` page should show:
- All generated lessons, newest first
- Filterable by subject, grade, date
- Each row: title, date, quality score (if scored), share button
- "Generate New Lesson" button prominent

### 4b. Persona profile page

`GET /settings` page should show:
- Current persona (name, school, subjects, grade levels, style)
- "Re-ingest files" button
- Current model + option to switch
- Class codes management

### 4c. Student chatbot embed snippet

On the lesson view page, add:
- "Embed Student Chat" section
- Shows the `<script>` snippet pre-filled with the lesson ID
- One-click copy button
- Preview of what the widget looks like

## After all features:

1. `python -m pytest tests/ -q --tb=short` — all must pass (add tests for new features)
2. `python -m ruff check eduagent/ --fix` — clean
3. `git add -A && git commit -m "feat: student class codes, Telegram health/commands/state, onboarding polish, dashboard gaps"`
4. `git push origin main`
5. `openclaw system event --text "Done: EDUagent student extension, Telegram polish, onboarding wizard, dashboard — tests passing" --mode now`
