# EDUagent Next Build Wave — Launch Prep

Build the following features on top of the existing codebase at ~/Projects/eduagent/. All code must be clean, typed, tested, committed, and pushed when done.

## Feature 1: Real Landing Page (eduagent/landing/)

The project already has a `landing/` directory stub. Build it out.

Create `eduagent/landing/index.html` — a production-quality static landing page:
- Headline: "Your AI co-teacher that sounds like you"
- Subhead: "EDUagent learns from your curriculum files and generates lessons, worksheets, and assessments in your exact teaching voice."
- Hero section with terminal/CLI demo (animated typewriter showing `pip install eduagent && eduagent setup`)
- Three value props:
  1. "Trained on YOUR materials" — not generic AI, learns your 9 years of lessons
  2. "Generates in your voice" — do-nows, exit tickets, DBQs — the way you write them
  3. "Students get you at 11pm" — chatbot answers questions the way their teacher would
- How it works: 3 steps (install → ingest → generate)
- Early access CTA: email capture form (use a Netlify form or Formspree endpoint `https://formspree.io/f/placeholder`)
- Footer: GitHub link, "Open Source" badge
- Fully self-contained HTML (inline CSS, no external deps except Google Fonts CDN)
- Mobile responsive, clean design (dark theme preferred — teachers grade at night)

Save to `eduagent/landing/index.html`

Add CLI command: `eduagent landing --serve` — serves the landing page on port 8080
Add route to existing API server: `GET /` → serve the landing page (redirect / to /dashboard if logged in)

## Feature 2: ProductHunt Launch Kit

Create `output/producthunt/` directory with:

**`launch-checklist.md`:**
- Pre-launch: submit to "coming soon", get 20+ supporters, schedule for Tuesday 12:01 AM PST
- Gallery: 5 screenshots needed (dashboard, lesson output, student bot, persona setup, quality score)
- Tagline options (5 variations, 60 chars max)
- Description (260 chars for PH)
- Topics: Education, Artificial Intelligence, Productivity, Developer Tools

**`gallery-screenshots.md`:**
- Instructions for Jon to capture each screenshot
- Exact URLs/commands to run to generate demo content first
- Dimensions: 1270x952px

**`maker-comment.md`:**
- Jon's first comment as maker (authentic, not salesy)
- References his 9 years at Great Neck South
- Explains the personal frustration that led to building this
- 200-300 words

**`hunter-outreach.md`:**
- 5 potential hunters with brief rationale (look for EdTech/AI educators who hunt frequently)
- Template DM to send to potential hunters

**`communities.md`:**
- 15 communities to post in on launch day
- Include: r/Teachers, r/edtech, r/LocalLLaMA, HN, specific Discord servers
- Timing: stagger posts across 6 hours

## Feature 3: Demo Mode — No API Key Required

Teachers shouldn't need an API key just to try it. Add a demo mode.

In `eduagent/llm.py`:
- Detect when no API key is configured
- In demo mode, return canned example outputs (pre-written lesson plans stored in `eduagent/demo/`)
- The demo lessons should look real and high quality — use Jon's actual teaching style

Create `eduagent/demo/` with:
- `demo_lesson_social_studies_g8.json` — a full lesson plan (aim, do-now, instruction, exit ticket, worksheet)
- `demo_lesson_science_g6.json`
- `demo_unit_plan.json` — a 3-lesson unit
- `demo_assessment.json` — a 10-question DBQ-style assessment

In CLI: `eduagent demo` — generates and displays a full sample lesson without any API key or files

In web UI: If no API key, show demo mode banner: "Running in demo mode — configure your LLM key to generate real lessons"

## Feature 4: Email Capture Backend

Teachers who visit the landing page should be tracked.

Create `eduagent/waitlist.py`:
```python
class WaitlistManager:
    """Manages early access signups."""
    
    def add_signup(self, email: str, role: str = "teacher", notes: str = "") -> None:
        """Add email to waitlist SQLite table."""
    
    def export_csv(self, output_path: Path) -> None:
        """Export waitlist to CSV."""
    
    def count(self) -> int:
        """Return total signup count."""
```

- Store in SQLite (same `~/.eduagent/eduagent.db`)
- Add API route: `POST /api/waitlist` — accepts `{email, role}`
- Add CLI: `eduagent waitlist --count` / `eduagent waitlist --export waitlist.csv`
- Wire the landing page form to POST to `/api/waitlist`
- Return count in landing page: "Join 47 teachers on the early access list" (pull from DB)

## Feature 5: Shareable Lesson URLs

A teacher generates a lesson and wants to share it with a colleague. Add sharing.

In `eduagent/database.py`:
- Add `share_token` column to `lessons` table (UUID, nullable)
- Add method: `create_share_link(lesson_id: int) -> str` — generates UUID token, stores it
- Add method: `get_by_share_token(token: str) -> Optional[DailyLesson]`

In `eduagent/api/routes/lessons.py`:
- `POST /api/lessons/{lesson_id}/share` → returns `{share_url: "http://localhost:8000/shared/abc123"}`
- `GET /shared/{token}` → public view of lesson (no auth required, read-only)

In web UI:
- "Share" button on lesson view page
- Copies share URL to clipboard
- Public view shows lesson in clean print-friendly layout (no sidebar)

Add CLI: `eduagent share --lesson-id 5` → prints shareable URL

## After all features:

1. `python -m pytest tests/ -v --tb=short` — all must pass (add tests for new features)
2. `python -m ruff check eduagent/ --fix` — clean
3. `git add -A && git commit -m "feat: landing page, ProductHunt kit, demo mode, email capture, shareable lesson URLs"`
4. `git push origin main`
5. Report: what's done, test count, any issues found
