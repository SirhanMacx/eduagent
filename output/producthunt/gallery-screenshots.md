# EDUagent — Gallery Screenshots Guide

All screenshots should be **1270x952px**. Use a clean browser window (no bookmarks bar, minimal extensions). Dark mode preferred.

## Screenshot 1: Dashboard / Content Library

**What to show:** The main dashboard with several generated units and lessons visible.

**Setup:**
```bash
eduagent serve --skip-setup
# Navigate to http://localhost:8000/dashboard
```

**Before capturing:**
1. Generate 2-3 units: `eduagent full "American Revolution" --grade 8 --subject "Social Studies" --weeks 2`
2. Generate a science unit: `eduagent full "Photosynthesis" --grade 8 --subject Science --weeks 2`
3. The dashboard should show unit cards, lesson counts, and recent activity

## Screenshot 2: Lesson Output

**What to show:** A full lesson plan with do-now, direct instruction, guided practice, exit ticket, and differentiation.

**Setup:**
```bash
# Navigate to http://localhost:8000/lesson/<lesson_id>
# Use one of the lessons generated above
```

**Before capturing:** Make sure the lesson view shows all sections expanded. Scroll to show the do-now and at least the start of direct instruction.

## Screenshot 3: Student Chatbot

**What to show:** The student chatbot answering a question about a lesson in the teacher's voice.

**Setup:**
```bash
# Navigate to http://localhost:8000/students
# Or use the embeddable widget on any lesson page
```

**Before capturing:**
1. Activate a lesson for student chat
2. Ask: "Can you explain what taxation without representation means?"
3. Capture the response showing the teacher's voice and style

## Screenshot 4: Persona Setup

**What to show:** The persona extraction result after ingesting teaching materials.

**Setup:**
```bash
eduagent ingest ~/your-lesson-plans/
# Navigate to http://localhost:8000/profile
```

**Before capturing:** The profile page should show the extracted teaching style, tone, vocabulary level, structural preferences, and favorite strategies.

## Screenshot 5: Quality Score

**What to show:** A lesson with quality scoring showing the 6-dimension breakdown.

**Setup:**
```bash
# Navigate to a lesson that has been scored
# http://localhost:8000/lesson/<lesson_id>
```

**Before capturing:** The lesson detail page should show the quality score panel with scores for: objective clarity, do-now relevance, instruction depth, differentiation quality, exit ticket alignment, materials completeness.

## Tips

- Use `Cmd+Shift+4` (macOS) to capture exact dimensions, or resize browser to 1270x952
- Clean up any test data that looks messy
- Make sure the persona name shows as your actual name, not "local-teacher"
- Dark mode looks better in gallery — toggle it if available
