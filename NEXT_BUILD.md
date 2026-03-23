# EDUagent Next Build Wave

Build the following features on top of the existing codebase at ~/Projects/eduagent/. All code must be clean, typed, tested, committed, and pushed when done.

## Feature 1: Real-time Streaming Generation (SSE)

The current web UI submits a form and waits. Make it stream.

In `eduagent/api/server.py` and `eduagent/api/routes/generate.py`:
- Add a `GET /api/stream/unit` and `GET /api/stream/lesson` endpoint using FastAPI's `StreamingResponse` with `text/event-stream` content type
- Stream progress events as the LLM generates: `data: {"status": "generating_lesson_1", "progress": 20}\n\n`
- In `eduagent/api/static/app.js`, use EventSource to consume the stream and update a progress bar + live-preview div in the UI
- Show a spinning indicator with status text: "Planning unit structure...", "Generating Lesson 1...", "Writing materials...", etc.

## Feature 2: Google Classroom Export

Add `eduagent/api/routes/export.py` endpoint:
- `POST /api/export/{lesson_id}/classroom` — generates a Google Classroom-compatible JSON payload
- The format should be a `CourseWork` resource compatible with the Google Classroom API (v1)
- Include: title, description (the lesson objective), materials (worksheet as attachment description), due date (optional), max points
- Return the JSON so a teacher can paste it into a script or future OAuth flow
- Add `eduagent export classroom --lesson-file lesson.json` CLI command

## Feature 3: Embeddable Student Chatbot Widget

Create `eduagent/api/static/widget.js`:
- A self-contained JS widget (no dependencies) that teachers paste into any webpage, Google Site, or LMS
- The snippet: `<script src="http://localhost:8000/static/widget.js" data-lesson-id="abc123"></script>`
- Creates a floating chat button (bottom-right corner) that expands into a chat panel
- Sends messages to `/api/chat` with the lesson_id
- Styled cleanly (inline CSS, no conflicts with host page)
- Shows teacher name and subject in the chat header ("Ask Ms. Johnson about Cell Biology")

## Feature 4: Lesson Quality Score Engine

Add `eduagent/quality.py`:

```python
class LessonQualityScore:
    """Score a generated lesson plan on multiple dimensions."""
    
    dimensions = [
        "objective_clarity",      # Is the SWBAT measurable and specific?
        "do_now_relevance",       # Does the warm-up connect to the objective?
        "instruction_depth",      # Is the direct instruction substantive?
        "differentiation_quality", # Are accommodations specific, not generic?
        "exit_ticket_alignment",  # Do exit ticket questions test the objective?
        "materials_completeness", # Does the worksheet cover key concepts?
    ]
    
    async def score(self, lesson: DailyLesson, materials: LessonMaterials) -> dict:
        """Score each dimension 1-5 with brief explanation."""
        # Use LLM to score each dimension
        # Return: {dimension: {score: int, explanation: str}, overall: float}
```

- Add `eduagent score --lesson-file lesson.json` CLI command
- Display as a rich table with scores and explanations
- Store scores in the lessons table in the DB
- Show score on the lesson view page in the web UI (color-coded: green 4-5, yellow 3, red 1-2)

## Feature 5: Lesson Plan Diff / Improvement Suggestions

Add to `eduagent/improver.py`:

```python
async def suggest_improvements(lesson: DailyLesson, feedback_notes: str = "") -> list[str]:
    """
    Given a lesson plan (and optional teacher feedback),
    generate 3-5 specific, actionable improvement suggestions.
    Each suggestion targets a specific section and explains the change.
    """
```

- Add UI: on the lesson view page, a "Suggest Improvements" button
- Shows a panel with 3-5 specific suggestions like:
  - "Your Do-Now doesn't connect to today's objective. Consider: 'What do you think happens when a plant is kept in the dark for a week?'"
  - "The exit ticket question 3 is too easy — it only checks recall. Add a synthesis question."

## Feature 6: Bulk Generation — Full Course

Add `eduagent/api/routes/generate.py`:
- `POST /api/course` — given a subject + grade + full-year topic list, generate an entire course structure
- Input: `{subject, grade_level, topics: ["Topic 1", "Topic 2", ...], weeks_per_topic: 2}`
- Output: A course map with units for each topic, daily lesson titles for each unit
- This is the "full year plan" feature — a teacher uploads their pacing guide and gets back a year of lesson titles organized by unit
- Add CLI: `eduagent course --subject science --grade 8 --topics-file pacing_guide.txt`

## Feature 7: Lesson Template System

Add `eduagent/templates_lib.py` (not to be confused with Jinja2 templates):
- A library of lesson structure templates beyond "I Do / We Do / You Do"
- Include: Socratic Seminar, Jigsaw, Think-Pair-Share, Project-Based, Flipped Classroom, Station Rotation
- Each template defines: timing structure, section names, expected student activities
- Add `eduagent templates list` CLI command showing all templates
- In the web UI generation form, add a "Lesson Structure" dropdown that populates from this library
- When a template is selected, use it as a constraint in the lesson generation prompt

## Feature 8: Export to PDF (production quality)

Currently using basic export. Replace with weasyprint for professional PDF output:
- Proper header with school logo placeholder, teacher name, date
- Section dividers
- Print-optimized CSS (no dark backgrounds, high contrast)
- Page breaks at appropriate points (each major section starts on a new page if space is tight)
- Worksheet on a separate page automatically

Add to `eduagent/exporter.py`:
```python
async def export_lesson_pdf(lesson: DailyLesson, materials: LessonMaterials, output_path: Path) -> Path:
    """Export using weasyprint for professional print-quality PDF."""
```

## After all features:

1. `python -m pytest tests/ -v` — all must pass (add tests for new features)
2. `python -m ruff check eduagent/ --fix` — clean
3. `git add -A && git commit -m "feat: streaming gen, Classroom export, chatbot widget, quality scoring, improvement suggestions, course planner, lesson templates, PDF export"`
4. `git push origin main`
5. `openclaw system event --text "Done: EDUagent v0.1.2 — 8 new features, streaming, quality scoring, full course planning" --mode now`
