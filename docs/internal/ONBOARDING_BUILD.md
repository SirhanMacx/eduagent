# EDUagent — Onboarding + Config Build

Build guided teacher onboarding and a settings/config UI. This is what turns EDUagent from a dev tool into something a real teacher can use on day one — no terminal required.

## Feature 1: Guided Onboarding Flow (Web)

Replace the current index.html with a multi-step onboarding wizard. When a teacher visits for the first time (no persona saved), they see the wizard. When they have a persona, they go straight to the dashboard.

### Step 1: Welcome Screen
- Big headline: "Turn your lesson plans into an AI co-teacher."
- Sub-headline: "EDUagent learns from your existing materials and generates lessons, units, and worksheets in your exact teaching voice."
- Two paths:
  - "I have lesson plan files to upload" → Step 2A (file upload)
  - "I'll start from scratch" → Step 2B (quick persona form)
- Show a live demo preview (animated GIF placeholder or the static demo HTML)

### Step 2A: File Upload
- Large drag-and-drop zone: "Drop your lesson plans, worksheets, slides, or notes here"
- Supported formats: PDF, DOCX, PPTX, TXT, Markdown, ZIP
- File list shows as files are added with remove button
- Progress bar during upload
- "Analyze My Materials" button
- Redirect to Step 3 after upload completes

### Step 2B: Quick Persona Form
- "Tell us about your teaching style" 
- Fields: Name, Subject area, Grade level(s), Teaching style dropdown (Direct instruction / Socratic / Inquiry-based / Project-based), "What's your favorite lesson structure?" text area
- "Create My Persona" button
- Redirect to Step 3 after creation

### Step 3: Meet Your AI Persona
- Show the extracted persona in a friendly card format
- "Here's what EDUagent learned about you:"
  - Teaching style badge
  - Vocabulary level
  - Structural preferences as tags
  - Sample quote from their materials (if available)
- "Does this sound like you?" with thumbs up/down
- If thumbs down: show editable fields
- "Let's generate your first lesson →" button

### Step 4: Generate Your First Lesson
- Simple form: Topic, Grade, Subject (pre-filled from persona), Duration (1 lesson / 1 week / 2 weeks)
- Big "Generate!" button
- Real-time streaming progress (use the SSE endpoint from v0.1.2)
- Show the generated lesson preview as it streams in

### Step 5: Success / What's Next
- "🎉 Your first lesson is ready!"
- Three action cards:
  1. "Export to PDF" button
  2. "Share with students" button (copy embeddable chatbot link)
  3. "Go to Dashboard" button
- "Want to generate a full unit?" → link to unit generation

### Onboarding State Tracking
In `database.py`, add an `onboarding` table:
```sql
CREATE TABLE IF NOT EXISTS onboarding_state (
    teacher_id TEXT PRIMARY KEY,
    step_completed INTEGER DEFAULT 0,
    completed_at TIMESTAMP
);
```

Add a cookie/session for `teacher_id` (simple UUID, no auth needed for v1 — single-teacher local deployment).

## Feature 2: Settings / Config Page

Add `eduagent/api/templates/settings.html` and route `GET /settings`.

### Settings Page Sections:

#### LLM Provider
- Radio buttons: Anthropic / OpenAI / Ollama (Local — Free)
- When Anthropic selected: text input for API key (masked), model dropdown (claude-opus-4-5, claude-sonnet-4-5, etc.)
- When OpenAI selected: API key input, model dropdown (gpt-4o, gpt-4o-mini, etc.)
- When Ollama selected: URL input (default: http://localhost:11434), model name input (default: llama3.2)
- "Test Connection" button → calls `GET /api/settings/test-connection`
  - Shows: ✅ Connected — claude-opus-4-5 is ready / ❌ Connection failed: API key invalid
- "Save Settings" button

#### Generation Defaults
- Default grade level dropdown
- Default subject dropdown
- Include homework toggle (on/off)
- Export format: Markdown / PDF / DOCX

#### Your Persona
- Show current persona summary
- "Re-analyze materials" button → re-runs ingestion
- "Edit persona manually" button → editable form

#### Danger Zone
- "Clear all generated content" button (with confirmation dialog)
- "Reset EDUagent" button (clears everything, re-runs onboarding)

## Feature 3: API Key Management (secure storage)

In `eduagent/config.py` (new file, replaces AppConfig.load()):
- Store API keys in OS keychain (macOS: keychain, Linux: secret service, fallback: ~/.eduagent/secrets.json with 0600 permissions)
- Use `keyring` library for cross-platform secret storage
- Never log or display full API keys
- In settings UI: show masked key (sk-...abc123), with "Change" button

## Feature 4: Health Check + Status Dashboard

Add `GET /api/health` endpoint:
```json
{
  "status": "ok",
  "llm_provider": "anthropic",
  "llm_model": "claude-opus-4-5", 
  "llm_connected": true,
  "persona_loaded": true,
  "units_generated": 3,
  "lessons_generated": 15,
  "db_size_mb": 0.4,
  "version": "0.1.2"
}
```

Add a small status bar to the base template (bottom of every page):
- Green dot + "Connected" or red dot + "Not connected — check settings"
- Click to open settings page

## Feature 5: First-Run CLI Setup Wizard

When a teacher runs `eduagent serve` for the first time (no config exists):
```
🎓 Welcome to EDUagent!

Let's get you set up in 2 minutes.

? Which AI provider do you want to use?
  ❯ Ollama (free, runs locally — recommended for privacy)
    Anthropic (Claude — best quality, requires API key)
    OpenAI (GPT-4o — requires API key)

? Enter your Anthropic API key: ****

✓ Connected to claude-opus-4-5

? What subject do you teach? Science
? What grade(s)? 8-10

✓ Configuration saved!

🚀 Starting EDUagent at http://localhost:8000
   Open your browser to get started.
```

Use `rich.prompt` for interactive prompts. Only runs on first launch.

## Navigation Improvements

Update `base.html` navigation:
- Home (dashboard)
- Generate (unit/lesson form)
- My Library (all generated content)
- ⚙️ Settings
- ? Help (links to README)

Add breadcrumbs to all pages.

## Mobile Responsiveness

The current CSS is desktop-only. Add basic responsive CSS:
- At < 768px: stack columns, full-width cards
- Navigation becomes hamburger menu
- Tables become card lists
- Font sizes adjust

## After all features:

1. `python -m pytest tests/ -v` — all must pass (add tests for new routes + config)
2. `python -m ruff check eduagent/ --fix` — clean
3. `git add -A && git commit -m "feat: teacher onboarding wizard, settings page, first-run CLI setup, health check, mobile responsive"`
4. `git push origin main`
5. `openclaw system event --text "Done: EDUagent onboarding + config — a real teacher can use this now" --mode now`
