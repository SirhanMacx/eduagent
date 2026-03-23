# Screenshots Needed for ProductHunt Gallery

All images should be 1270x760px. Use a clean terminal theme (dark background, large font).

---

## Screenshot 1: Hero — The Pitch (Gallery Position 1)

**What to capture:** Terminal showing the full persona extraction flow.

```bash
eduagent ingest ~/Documents/Teaching/
```

**What it shows:** EDUagent analyzing 246 files, then printing the Teaching Profile summary:
- Style: Inquiry-based
- Format: AIM → Do Now → Document Analysis → Guided Practice
- Loves: Primary sources, DBQs, Socratic questioning
- Goes by: Mr. Mac

**Caption:** "Point it at your lesson plans. It learns your voice."

---

## Screenshot 2: Unit Plan Generation (Gallery Position 2)

**What to capture:** Terminal output of a full unit plan.

```bash
eduagent unit "Causes of World War I" --grade 10 --weeks 2
```

**What it shows:** The generated unit plan with essential questions, lesson sequence, and pacing.

**Caption:** "Ask for a unit. Get your voice back — not a textbook's."

---

## Screenshot 3: Daily Lesson Output (Gallery Position 3)

**What to capture:** A single generated lesson plan, showing the AIM question, Do Now, instruction sequence, and exit ticket.

```bash
eduagent lesson "Alliance system and the outbreak of WWI" --grade 10
```

**What it shows:** Full lesson with:
- AIM: "How did the alliance system turn a regional conflict into a world war?"
- Do Now with primary source excerpt
- Guided practice with document analysis
- Exit ticket

**Caption:** "Every lesson matches your format — AIM questions, Do Nows, exit tickets."

---

## Screenshot 4: Voice Match Side-by-Side (Gallery Position 4)

**What to capture:** Split-screen or two terminal panes:
- Left: An original teacher lesson plan (from the ingested files)
- Right: EDUagent-generated lesson on a different topic

**What it shows:** The tone, vocabulary, and structure matching between real and generated content.

**Caption:** "Left: a real lesson plan. Right: EDUagent's output. Same teacher voice."

---

## Screenshot 5: Student Bot in Action (Gallery Position 5)

**What to capture:** Terminal showing the student chat interface.

```bash
eduagent student-chat
```

**Show this exchange:**
```
Student: I don't understand what imperialism means
EDUagent: Think about it this way — remember when we talked about how
countries competed for colonies in Africa? What were they trying to get
out of that? Start there.
```

**Caption:** "Students ask questions. They get answers in your teaching voice — not ChatGPT's."

---

## Screenshot 6: Standards Alignment (Gallery Position 6)

**What to capture:** Generated lesson with auto-tagged standards.

```bash
eduagent lesson "Westward Expansion" --grade 8 --state NY --show-standards
```

**What it shows:** Lesson output with aligned NY state standards codes displayed alongside content.

**Caption:** "Auto-aligns to your state's standards. All 50 states supported."

---

## Bonus: Web Dashboard (if ready)

**What to capture:** Browser showing `http://localhost:8000` with a lesson generating in real-time (streaming text).

```bash
eduagent serve
```

**Caption:** "Web dashboard for teachers who prefer clicking to typing."

---

## Technical Notes

- Use iTerm2 or Warp with a clean dark theme for terminal screenshots
- Font size: 14-16pt minimum (readable on mobile)
- Crop to remove window chrome or use a mockup frame
- For the side-by-side, consider using a tool like Shottr or CleanShot for annotation
- Export at 2x resolution (2540x1520) and let ProductHunt downscale for sharpness
