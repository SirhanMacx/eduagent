# EDUagent ProductHunt Gallery Screenshots

All screenshots should be **1270x952px**. Use a clean browser window or terminal with no personal bookmarks or tabs visible. Dark mode is fine but be consistent across all 5 images.

---

## Pre-Screenshot Setup

Before capturing screenshots, generate demo content so the screens look populated and real.

### Step 1: Start EDUagent with demo materials

```bash
cd ~/Projects/eduagent

# Make sure you have your real lesson plans in the input directory
# (or use the demo set if you prefer not to show real student names)
cp -r demo/sample-lessons/ input/

# Run persona extraction first so the persona is populated
python -m eduagent extract --input-dir input/ --verbose

# Generate a demo lesson for screenshots
python -m eduagent generate \
  --topic "Causes of World War I" \
  --grade 8 \
  --subject "Social Studies" \
  --lessons 3
```

### Step 2: Start the web dashboard

```bash
python -m eduagent web --port 8080
```

Open `http://localhost:8080` in your browser.

### Step 3: Start the student bot (for screenshot 3)

```bash
python -m eduagent bot --platform web --port 8081
```

Open `http://localhost:8081` in a separate browser window.

---

## Screenshot 1: Web Dashboard (Hero Image)

**What to show:** The main dashboard with a lesson generation in progress, streaming text visible.

**How to capture:**

1. Open `http://localhost:8080` in Chrome or Arc
2. Resize browser window to exactly **1270x952px**
   - On Mac: use the Rectangle app, or in DevTools press Cmd+Shift+M and set device dimensions
   - Alternatively: `window.resizeTo(1270, 952)` in console (works in some browsers)
3. Start generating a new lesson:
   - Topic: "The American Revolution: Causes and Consequences"
   - Grade: 8
   - Subject: Social Studies
4. Capture the screenshot **while text is streaming** — this shows the AI in action
5. The sidebar should show your lesson history (generate a few lessons beforehand so it's not empty)

**What viewers should see at a glance:** A polished web interface with real lesson content streaming in. This is the first image people see — it should immediately communicate "this generates lessons."

**File:** Save as `gallery-01-dashboard.png`

---

## Screenshot 2: Lesson Output

**What to show:** A fully generated lesson displaying the teacher's authentic voice — Do Now, Direct Instruction, exit ticket, differentiation section.

**How to capture:**

1. Open a completed lesson in the web dashboard (or use terminal output)
2. Scroll to show the Do Now and Direct Instruction sections — these are the most compelling because they show the teacher's voice
3. Make sure the "Alright, friends" phrasing or similar voice markers are visible
4. If using the web dashboard, expand the lesson view to fill the screen
5. If using terminal output instead:
   ```bash
   python -m eduagent generate \
     --topic "The American Revolution" \
     --grade 8 \
     --subject "Social Studies" \
     --output-format markdown \
     --output output/demo-lesson.md
   ```
   Then open the markdown in a previewer or the web UI

**What viewers should see at a glance:** Real lesson content that clearly sounds like a specific teacher, not generic AI slop. The voice should feel human and warm.

**File:** Save as `gallery-02-lesson-output.png`

---

## Screenshot 3: Student Chatbot

**What to show:** A student asking the chatbot a question about a lesson, and the bot responding in the teacher's voice and staying within the taught material's scope.

**How to capture:**

1. Open the student bot interface at `http://localhost:8081`
   - Or use the Telegram bot if you have it running — a Telegram screenshot looks more "real-world"
2. Send these messages to create a good conversation thread:
   - Student: "I don't really understand why the colonists were so mad about the Stamp Act. Like, it was just a tax?"
   - (Let the bot respond in your teaching voice)
   - Student: "Oh okay, so it was more about the principle than the money?"
   - (Let the bot respond)
3. Capture the full conversation showing 2-3 exchanges
4. Make sure the bot's responses sound like you, not like ChatGPT

**What viewers should see at a glance:** A student getting personalized help from an AI that sounds like their actual teacher. This is the "wow" screenshot.

**File:** Save as `gallery-03-student-bot.png`

---

## Screenshot 4: Persona Setup

**What to show:** The persona extraction process — EDUagent analyzing uploaded lesson plans and building the teaching fingerprint.

**How to capture:**

Option A — Terminal (recommended, looks more "developer tool"):
```bash
python -m eduagent extract --input-dir input/ --verbose 2>&1 | head -60
```
Capture the terminal showing:
- Files being scanned (PDFs, DOCX, PPTX listed)
- Teaching style detected (e.g., "inquiry-based", "Socratic")
- Structural patterns found (e.g., "Do Now", "AIM question", "exit ticket")
- Vocabulary analysis results
- Final persona summary

Option B — Web dashboard:
1. Go to the Profile/Persona section of the web UI
2. Show the persona card with extracted teaching traits
3. Make sure it shows style, structure preferences, vocabulary level, etc.

**What viewers should see at a glance:** The system analyzing real lesson files and extracting a meaningful teaching profile. This communicates "it actually learns from YOUR materials."

**File:** Save as `gallery-04-persona-setup.png`

---

## Screenshot 5: Quality Score

**What to show:** The quality scoring panel that evaluates generated lessons for fidelity to the teacher's voice, pedagogical soundness, and differentiation coverage.

**How to capture:**

1. Generate a lesson and view its quality score:
   ```bash
   python -m eduagent generate \
     --topic "Causes of World War I" \
     --grade 8 \
     --subject "Social Studies" \
     --score
   ```
   Or open a generated lesson in the web UI and look at the quality panel.
2. The screen should show:
   - **Voice Fidelity Score** — how closely the output matches the teacher's style
   - **Pedagogical Score** — lesson structure, Bloom's taxonomy alignment, engagement
   - **Differentiation Score** — coverage of struggling, advanced, ELL learners
   - **Overall Score** with a visual indicator (progress bar, letter grade, etc.)
   - Specific improvement suggestions if available
3. Capture with scores visible and at least one suggestion/breakdown visible

**What viewers should see at a glance:** This isn't just blind generation — there's a quality feedback loop. This builds trust.

**File:** Save as `gallery-05-quality-score.png`

---

## Final Checklist

- [ ] All 5 screenshots are exactly 1270x952px
- [ ] No personal bookmarks, tabs, or sensitive info visible
- [ ] No student names or real student data visible anywhere
- [ ] Consistent styling (all dark mode or all light mode)
- [ ] Text is legible at ProductHunt thumbnail size (test by shrinking to 50%)
- [ ] Gallery order: Dashboard, Lesson Output, Student Bot, Persona Setup, Quality Score
- [ ] Upload to ProductHunt in this exact order (first image becomes the thumbnail)
