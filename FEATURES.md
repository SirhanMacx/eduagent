# Features

EDUagent learns your teaching voice and generates lessons, units, worksheets, and assessments that sound like *you* wrote them.

---

## Persona Extraction

EDUagent reads your existing lesson plans and builds a profile of your teaching fingerprint — your style, structure, vocabulary, and pedagogical approach.

<!-- Screenshot: Terminal showing persona extraction from ~/Documents/Teaching/ -->
![Persona Extraction](docs/screenshots/persona-extraction.png)

---

## Unit Planning

Generate multi-week unit plans with essential questions, daily lesson sequences, and assessment plans — all aligned to your state standards.

```
Unit: "Chain Reaction: Unpacking the Causes of World War I"
Essential Questions:
  • Was WWI inevitable, or could it have been prevented?
  • How do alliances protect nations versus provoke conflict?
  • What role did nationalism play in the outbreak of WWI?

Daily Lessons (10):
  1. Nationalism in Europe
  2. The Alliance System
  3. Imperialism and Rivalries
  4. Militarism and Arms Race
  5. Assassination of Franz Ferdinand
  6. July Crisis and Ultimatums
  7. Chain Reaction: War Spread
  8. Perspectives: Who Was to Blame?
  9. Document-Based Investigation
  10. Unit Assessment and Reflection
```

---

## Daily Lesson Generation

Each lesson includes a Do Now, direct instruction, guided practice, independent work, exit ticket, homework, and differentiation — written in your voice.

<!-- Screenshot: Terminal showing a generated lesson -->
![Lesson Generation](docs/screenshots/lesson-generation.png)

**Real output from EDUagent** (American Revolution unit, 8th grade Social Studies):

> **Do-Now / Warm-Up (5 min)**
>
> Alright, friends, as you settle in, I want you to take out your notebook and answer this question on the board: 'What does freedom mean to you? Is there ever a time when following the rules is more important than being free?' Take 5 minutes to jot down your honest thoughts. There are no wrong answers here; I just want to hear your voice.

> **Direct Instruction**
>
> Alright, friends, today we're starting one of my favorite units in all of history. We're going to answer a question that sounds simple but is actually incredible: How did ordinary people decide to risk everything for freedom? I want you to really sit with this for a second.

---

## Worksheets and Assessments

Generate worksheets, quizzes, rubrics, and DBQ prompts that match your unit's scope and sequence.

<!-- Screenshot: Generated worksheet output -->
![Materials Generation](docs/screenshots/materials-generation.png)

---

## Student Chatbot

Students message the bot and get answers in your teaching voice — like having you available 24/7. The bot stays within the scope of what you've taught.

<!-- Screenshot: Student bot conversation on Telegram -->
![Student Bot](docs/screenshots/student-bot.png)

---

## Telegram Bot

Your co-teacher lives in your pocket. Message your bot on Telegram to generate lessons, get unit ideas, or prep materials — from anywhere.

<!-- Screenshot: Telegram bot conversation -->
![Telegram Bot](docs/screenshots/telegram-bot.png)

---

## Web Dashboard

Full-featured web interface with streaming generation, lesson history, analytics, and profile management.

<!-- Screenshot: Web dashboard showing lesson generation -->
![Web Dashboard](docs/screenshots/web-dashboard.png)

---

## TUI Dashboard

Rich terminal interface for power users who prefer the command line.

<!-- Screenshot: TUI dashboard -->
![TUI Dashboard](docs/screenshots/tui-dashboard.png)

---

## Standards Alignment

Automatic alignment to your state's learning standards. Supports all 50 states with auto-detection.

---

## Differentiation

Every lesson includes differentiation for:
- **Struggling learners** — scaffolded materials, sentence starters, graphic organizers
- **Advanced learners** — extension activities, deeper analysis prompts
- **ELL students** — bilingual word banks, visual supports, translation tools

---

## IEP/504 Accommodations

Generate accommodation modifications aligned to specific IEP goals and 504 plans.

---

## Privacy First

- Your files never leave your machine (unless you choose a cloud LLM)
- API keys stored in OS keychain
- No telemetry, no tracking, no data collection
- Works fully offline with Ollama
