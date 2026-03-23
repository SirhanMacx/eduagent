# Contributing to EDUagent

Thanks for your interest in making EDUagent better! Whether you're a teacher with ideas, a developer who wants to add features, or someone who found a bug — we'd love your help.

---

## Table of Contents

- [Getting Started](#getting-started)
- [How to Add a New Subject Skill](#how-to-add-a-new-subject-skill)
- [How to Add State Standards](#how-to-add-state-standards)
- [How to Contribute a Lesson Template](#how-to-contribute-a-lesson-template)
- [Code Style Guide](#code-style-guide)
- [Pull Request Checklist](#pull-request-checklist)
- [Good First Issues](#good-first-issues)
- [Questions?](#questions)

---

## Getting Started

1. **Fork and clone** the repo:

```bash
git clone https://github.com/SirhanMacx/eduagent.git
cd eduagent
```

2. **Install in development mode** (includes test and lint tools):

```bash
pip install -e ".[dev]"
```

3. **Run the test suite** to make sure everything works:

```bash
pytest
```

4. **Run the linter:**

```bash
ruff check .
```

5. **Create a branch** for your work:

```bash
git checkout -b my-feature
```

---

## How to Add a New Subject Skill

EDUagent generates curriculum materials across subjects. Each subject is supported through prompt templates, standards alignment, and corpus examples. To add or improve a subject:

### 1. Add or update prompts

Prompt templates live in `eduagent/prompts/`. Each file is a plain-text Jinja2 template:

```
eduagent/prompts/
├── unit_plan.txt          # Unit plan generation
├── lesson_plan.txt        # Daily lesson generation
├── worksheet.txt          # Worksheet/practice problems
├── assessment.txt         # Quiz/test items
├── differentiation.txt    # IEP/differentiation notes
└── persona_extract.txt    # Teacher persona extraction
```

To improve output for a specific subject (e.g., adding better science lab prompts):

1. Open the relevant prompt template (e.g., `lesson_plan.txt`)
2. Add subject-specific instructions within the existing template structure using Jinja2 conditionals:
   ```
   {% if subject == "Science" %}
   Include a hands-on lab or demonstration activity in the guided practice section.
   {% endif %}
   ```
3. Test by generating a lesson: `eduagent lesson "your topic" --grade 8 --subject Science`

### 2. Add standards for the subject

If your subject needs new national standards, add them to `eduagent/standards.py`:

```python
# In the STANDARDS dict, add entries:
"Art": [
    ("VA.CR.1", "Generate and conceptualize artistic ideas and work", "K-12"),
    ("VA.CR.2", "Organize and develop artistic ideas and work", "K-12"),
    # ...
]
```

### 3. Add corpus examples

High-quality examples improve generation. See [How to Contribute a Lesson Template](#how-to-contribute-a-lesson-template) below.

### 4. Test your changes

```bash
pytest
ruff check .
```

---

## How to Add State Standards

EDUagent maps all 50 US states to their standards frameworks. The mapping lives in two files:

### `eduagent/state_standards.py`

Contains `STATE_STANDARDS_CONFIG` — a dict mapping state abbreviations to framework names per subject:

```python
STATE_STANDARDS_CONFIG = {
    "NY": {
        "name": "New York",
        "math": "NY_NGLS",
        "ela": "NY_NGLS",
        "science": "NGSS",
        "social_studies": "NY_SS",
    },
    # ... all 50 states + DC
}
```

To add or update a state's standards:

1. **Find the official framework name** for the state and subject (e.g., "TX_TEKS" for Texas math)
2. **Add the mapping** in `STATE_STANDARDS_CONFIG`
3. **Add a framework description** in `FRAMEWORK_DESCRIPTIONS`:
   ```python
   FRAMEWORK_DESCRIPTIONS = {
       "TX_TEKS": "Texas Essential Knowledge and Skills",
       # ...
   }
   ```
4. **Test:** `pytest tests/test_state_standards.py`

### `eduagent/standards.py`

Contains the actual standard codes and descriptions in the `STANDARDS` dict. To add specific standards for a new framework:

1. Add entries keyed by subject name with `(code, description, grade_band)` tuples
2. Grade bands: `"K-2"`, `"3-5"`, `"6-8"`, `"9-12"`, or `"K-12"`

---

## How to Contribute a Lesson Template

Lesson templates are example materials that improve generation quality through few-shot learning. The corpus stores high-quality examples that get injected into LLM prompts.

### Via the corpus system

1. Generate a lesson with EDUagent
2. Rate it highly (4-5 stars) — high-rated content automatically enters the few-shot corpus
3. Edit the generated content to fix any issues before rating

### Via code contribution

Add examples directly to the corpus module in `eduagent/corpus.py`:

1. Create a JSON file matching the `DailyLesson` or `UnitPlan` schema (see `eduagent/models.py`)
2. Include realistic, high-quality content appropriate for the grade level
3. Ensure standards alignment is accurate
4. Submit as a PR with the example in `examples/`

### What makes a good template

- Accurate standards alignment for the stated grade and subject
- Realistic time estimates that add up to a class period
- Meaningful differentiation (not just "provide extra time")
- Clear, actionable exit ticket questions
- Age-appropriate vocabulary and activities

---

## Code Style Guide

### Tools

- **Linter/Formatter:** [Ruff](https://docs.astral.sh/ruff/) (config in `pyproject.toml`)
- **Tests:** [pytest](https://docs.pytest.org/) with [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio)

### Rules

| Rule | Detail |
|------|--------|
| **Line length** | 120 characters max |
| **Python version** | 3.10+ (use `\|` union types, `match` statements are OK) |
| **Type hints** | Appreciated but not mandatory. Use them on public APIs. |
| **Docstrings** | Required on public functions and classes. One-liner for simple functions, Google-style for complex ones. |
| **Imports** | Sorted by Ruff (`I` rules). stdlib → third-party → local. |
| **Functions** | Small, focused, single responsibility. If a function exceeds ~50 lines, consider splitting. |
| **Async** | All LLM-calling code must be `async`. Use `httpx` for HTTP, not `requests`. |
| **Data models** | Use Pydantic `BaseModel` for structured data. Define in `models.py`. |
| **Error handling** | Let exceptions propagate unless you can handle them meaningfully. Don't silence errors. |
| **Naming** | `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_CASE` for constants. |

### Running checks

```bash
# Lint
ruff check .

# Auto-fix lint issues
ruff check --fix .

# Format
ruff format .

# Tests
pytest

# Tests with verbose output
pytest -v

# Single test file
pytest tests/test_basic.py
```

### Project structure conventions

```
eduagent/
├── models.py          # All Pydantic data models
├── llm.py             # LLM client (add provider support here)
├── prompts/           # LLM prompt templates (Jinja2 .txt files)
├── api/               # FastAPI web server
│   ├── routes/        # API route handlers
│   ├── templates/     # Jinja2 HTML templates
│   └── static/        # CSS/JS assets
└── tests/             # pytest test files (test_*.py)
```

---

## Pull Request Checklist

Before submitting a PR, verify:

- [ ] **Tests pass:** `pytest` completes with no failures
- [ ] **Linter passes:** `ruff check .` reports no errors
- [ ] **New code has tests:** if you added a feature, add a test in `tests/`
- [ ] **Prompts tested:** if you changed a prompt template, generate sample output and verify quality
- [ ] **No secrets committed:** no API keys, tokens, or credentials in the diff
- [ ] **Commit messages are clear:** describe *what* and *why*, not just *how*
- [ ] **PR description explains the change:** what problem it solves, how to test it
- [ ] **Breaking changes documented:** if you changed a public API or data model, note it in the PR

### Commit message format

```
type: short description

Longer explanation if needed.

Examples:
  feat: add bell ringer generation for math
  fix: handle empty PDF files in ingestor
  docs: add architecture diagram to docs
  test: add student bot message routing tests
  refactor: extract LLM retry logic into helper
```

---

## Good First Issues

New to EDUagent? These are great places to start:

| Issue | Description | Skills needed |
|-------|-------------|---------------|
| **Improve a prompt** | Pick any template in `eduagent/prompts/` and improve its output for a subject you know well | Teaching knowledge |
| **Add example materials** | Contribute high-quality lesson examples to `examples/` | Teaching knowledge |
| **Add missing state standards** | Fill in specific standard codes for a state framework you're familiar with | Education standards knowledge |
| **Better error messages** | Find a confusing error path and add a helpful message | Python |
| **Add export format** | Add Google Slides or PowerPoint export to `exporter.py` | Python, file formats |
| **Improve test coverage** | Add tests for untested functions (check with `pytest --co`) | Python, pytest |
| **Accessibility audit** | Review the web dashboard HTML templates for a11y issues | HTML, accessibility |
| **Ollama model support** | Test and document which Ollama models work best for each task | Ollama, testing |
| **Documentation fixes** | Fix typos, clarify instructions, add examples to guides | Writing |

---

## Questions?

- **Open an issue** on GitHub — we're happy to help
- **Check existing issues** for context on planned work
- **Read the architecture docs** at [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for a deep dive into how EDUagent works

We appreciate every contribution, whether it's a one-line typo fix or a major feature. Thank you!
