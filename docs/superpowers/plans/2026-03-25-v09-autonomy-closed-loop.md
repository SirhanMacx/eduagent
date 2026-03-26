# v0.9 Autonomy + Closed Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add autonomy progression (track approval rates, offer auto-approval), student insights tool, teacher preference learning, and close the feedback loop so generation improves from week to week.

**Architecture:** Approval tracker monitors accept/reject rates per action type and offers auto-approval when confidence is high. Student insights tool queries student_questions table for confusion patterns. Preference learner extracts signals from ratings, edited sections, and approvals — stores them in episodic memory and renders them in the system prompt. The closed loop connects feedback → memory → improved generation.

**Tech Stack:** Python 3.10+, pytest, pytest-asyncio. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-03-25-v06-agent-core-design.md` Section 7 (v0.9)

---

## Task 1: Approval Tracker — Rate Monitoring + Auto-Approval Offers

Track approval/rejection rates per action type. When a teacher approves 95%+ of a specific action without edits, the agent can offer auto-approval.

**Files:**
- Create: `clawed/agent_core/autonomy.py`
- Modify: `clawed/agent_core/approvals.py` — log action type on approve/reject
- Test: `tests/test_autonomy.py`

Implementation: `ApprovalTracker` reads all resolved approvals, computes per-action-type rates, and `should_offer_auto(action_type)` returns True when rate > 0.95 with >= 10 samples.

Commit: `feat(autonomy): add approval rate tracking and auto-approval offers`

---

## Task 2: Student Insights Tool

Agent tool that queries student question patterns to surface confusion topics for reteaching.

**Files:**
- Create: `clawed/agent_core/tools/student_insights.py`
- Test: Append to `tests/test_autonomy.py`

Implementation: Queries `student_questions` table grouped by `lesson_topic`, counts frequency, identifies top confusion areas. Returns structured insights: "14 students asked about ratification vs. amendment this week."

Commit: `feat(tools): add student_insights tool for confusion detection`

---

## Task 3: Teacher Preference Learning

Extract preference signals from feedback (ratings, edited sections, approval patterns) and store them as structured episodes. Render preferences in the system prompt so the agent adapts.

**Files:**
- Create: `clawed/agent_core/memory/preferences.py`
- Modify: `clawed/agent_core/memory/loader.py` — add preferences to context
- Modify: `clawed/agent_core/prompt.py` — add preferences section
- Test: Append to `tests/test_memory.py`

Implementation: `extract_preferences(teacher_id)` queries feedback history, approval history, and episodic memory to build a preferences summary. Examples: "Teacher always edits the Do Now section" → "Prefers shorter Do Nows." "Teacher never uses vocabulary lists" → "Skip vocabulary lists." "Teacher approves drive uploads without review" → auto-approve candidate.

Commit: `feat(memory): add teacher preference learning from feedback and approvals`

---

## Task 4: Closed Loop — Feedback Flows Into Generation

Wire it all together: feedback from Week N influences Week N+1 generation. The agent references what worked, what didn't, and what students struggled with.

**Files:**
- Modify: `clawed/agent_core/core.py` — after agent loop, store richer episodes with feedback metadata
- Modify: `clawed/agent_core/memory/loader.py` — include preferences + student insights in context
- Test: `tests/test_closed_loop.py`

Implementation: Integration test that simulates the full loop: generate → rate → store feedback → next generation references the feedback.

Commit: `feat(loop): close the feedback loop — generation improves from feedback`

---

## Task 5: Version Bump + Docs + Push

- Bump to 0.9.0
- Update CHANGELOG, README, ARCHITECTURE, HANDOFF
- Update tool count
- Run full suite, lint, push

Commit: `release: bump to v0.9.0 — autonomy progression + closed loop`
