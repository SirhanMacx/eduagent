# Claw-ED Agent Handoff — Context for Continuation

**Date:** 2026-03-25
**Last commit:** See `git log --oneline -5`
**Tests:** 1300+ passed, 34 skipped
**PyPI:** v0.7.0
**Agent Core:** Feature-flagged. Enable with `clawed config set agent-gateway true`
**Memory:** 3-layer cognitive memory (identity, curriculum state, episodic with TF-IDF embeddings)
**Drive:** OAuth token persistence, rate-limited client, 3 agent tools (upload, list, organize)

---

## What Claw-ED Is

An AI teaching assistant for K-12 teachers. Teachers install it, configure an AI provider, upload their lesson plans, and Claw-ED learns their teaching style and generates lessons, units, worksheets, assessments — all in their voice.

**The vision:** Every teacher can type `pip install clawed && clawed` and have a working AI teaching assistant within 60 seconds. No technical knowledge required.

---

## Current Architecture

```
clawed/
├── gateway.py           # The brain — routes messages to handlers
├── agent.py             # Conversational agent with tool use (LLM calls tools)
├── tools.py             # 10 tools: generate_lesson, search_standards, configure_profile, ingest_folder, etc.
├── generation.py        # LLM-calling service layer (lesson, unit, quiz generation)
├── router.py            # Intent detection (keyword → Intent enum)
├── model_router.py      # Tier-based model routing (fast/work/deep)
├── handlers/            # One handler per intent domain (generate, export, feedback, etc.)
├── transports/          # Thin message shuttles
│   ├── telegram.py      # Teacher Telegram bot (httpx, no python-telegram-bot)
│   ├── student_telegram.py  # Student bot (httpx)
│   ├── cli.py           # Terminal chat transport
│   ├── web.py           # FastAPI web transport
│   └── openclaw.py      # OpenClaw skill transport
├── onboarding.py        # Setup wizards (quick_model_setup + run_setup_wizard)
├── cli.py               # Typer CLI — registers all commands
├── api/                 # FastAPI web server + routes + templates
│   ├── routes/setup.py  # Browser-based setup wizard at /setup
│   └── templates/       # setup.html, setup_done.html, dashboard, etc.
├── models.py            # Pydantic models (AppConfig, TeacherPersona, DailyLesson, etc.)
├── llm.py               # Unified LLM client (Anthropic/OpenAI/Ollama)
└── eduagent/            # Backward-compat shim (from eduagent import X → from clawed import X)
```

---

## The Critical Bug to Fix

### `clawed` command does NOT show the simple onboarding flow

**Expected behavior:**
1. New teacher types `clawed` → sees friendly AI provider menu → pastes key → drops into chat → agent introduces itself and learns about the teacher conversationally
2. Returning teacher types `clawed` → drops straight into chat

**Actual behavior on the user's machine:**
- `clawed` shows the help/command list instead of starting setup or chat
- This happens because `~/.eduagent/config.json` already exists from testing

**Root cause possibilities (investigate in order):**
1. Config file exists → takes "returning user" branch → `run_chat()` may be failing silently and falling through to `ctx.get_help()`
2. The `invoke_without_command=True` callback may not be firing correctly with Typer
3. The `run_chat()` import from `clawed.transports.cli` may have an issue

**The code is in `clawed/cli.py` lines 74-108:**
```python
@app.callback(invoke_without_command=True)
def main(ctx: typer.Context, ...):
    if ctx.invoked_subcommand is None:
        config_path = Path.home() / ".eduagent" / "config.json"
        if not config_path.exists():
            # New user → quick_model_setup() → run_chat()
        else:
            # Returning user → run_chat()
```

**To test:** Delete `~/.eduagent/config.json` and run `clawed` — it should show the setup menu. If it shows help instead, the callback isn't working.

---

## What Needs to Be Done (Priority Order)

### 1. Fix the `clawed` default command (CRITICAL)

The bare `clawed` command must work as described above. Debug why it's not. Possible fixes:
- Add error handling around `run_chat()` so failures don't silently show help
- Test with AND without `~/.eduagent/config.json`
- The `asyncio.run(run_chat())` might conflict with something

### 2. Perfect the agentic onboarding conversation

When a new user drops into chat, the agent should:
1. Greet them and ask what they'd like to call the assistant (suggest fun names)
2. Ask the teacher's name
3. Ask what they teach (subject, grade, state)
4. Ask if they have existing lesson plans (folder path or Drive link)
5. Use `configure_profile` tool to save their info
6. Use `ingest_folder` tool if they provide a path

The system prompt for new users is in `clawed/gateway.py` `_chat()` method — it detects `session.is_new` and uses an onboarding-specific prompt. The tools `configure_profile` and `ingest_folder` are in `clawed/tools.py`.

**Test this by:** Deleting config, running `clawed`, going through the model setup, then chatting. The agent should naturally ask about the teacher.

### 3. Polish `clawed setup` command

`clawed setup` runs `run_setup_wizard()` in `clawed/onboarding.py` (line 483). It's a 400-line function that works but feels clunky. The prompts need to be clearer, the flow needs to feel more guided. Compare it to `quick_model_setup()` which is already polished.

### 4. Remaining cleanup

- Replace remaining Unsplash references in docs with web search (partially done)
- The web setup wizard at `/setup` still works as an alternative (keep it)
- Consider: should `clawed` with existing config go to chat or show a brief status + menu?

---

## Key Design Principles

1. **Agentic, not form-based**: The agent configures itself through conversation, not forms
2. **One command**: `pip install clawed && clawed` — that's the entire setup
3. **Teacher-first**: Every message, prompt, and error should make sense to a non-technical person
4. **Plug and play**: Works on Mac and Windows, UTF-8 handled, file paths resolved
5. **The agent IS the product**: Not a command-line tool with an agent bolted on

---

## Testing

```bash
cd /Users/mind_uploaded_crustacean/Projects/eduagent
.venv/bin/python3 -m pytest tests/ -q --tb=short    # 1208 tests
.venv/bin/ruff check .                               # should be clean
.venv/bin/clawed --help                              # shows all commands
.venv/bin/clawed demo                                # works without API key
```

To test fresh onboarding:
```bash
rm ~/.eduagent/config.json    # reset config
.venv/bin/clawed              # should show model setup, then chat
```

---

## Files You'll Likely Touch

| File | Why |
|------|-----|
| `clawed/cli.py` | Fix the `clawed` default command flow |
| `clawed/onboarding.py` | Polish setup prompts |
| `clawed/gateway.py` | Onboarding system prompt for new users |
| `clawed/tools.py` | `configure_profile` and `ingest_folder` tools |
| `clawed/transports/cli.py` | The terminal chat transport |
| `clawed/agent.py` | The agent loop (tool calling) |

---

## What NOT to Change

- `clawed/models.py` — Pydantic schemas are stable
- `clawed/handlers/*.py` — Intent handlers work correctly
- `clawed/generation.py` — LLM generation pipeline is solid
- `clawed/router.py` — Intent detection works
- `tests/` — Don't delete tests, only add
