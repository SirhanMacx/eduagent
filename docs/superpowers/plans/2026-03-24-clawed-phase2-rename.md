# Claw-ED Phase 2: Rename to clawed — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename the package from `eduagent` to `clawed` while maintaining full backward compatibility — both `from clawed import X` and `from eduagent import X` work, both `clawed` and `eduagent` CLI commands work, all 1238 tests pass.

**Architecture:** Move the source directory `eduagent/` → `clawed/` via git mv, mass-replace all internal imports, then create a thin `eduagent/` shim package that re-exports from `clawed`. Hatchling builds both packages. This is the approach specified in ARCHITECTURE_NEXT.md: "eduagent/__init__.py becomes: from clawed import *".

**Tech Stack:** Python 3.10+, hatchling, pytest

---

## File Structure

### Moved (git mv)
- `eduagent/` → `clawed/` (entire directory tree — 90+ .py files, prompts/, demo/, api/, handlers/, skills/, etc.)

### Created
- `eduagent/__init__.py` — backward-compat shim: `from clawed import *`
- `eduagent/_compat.py` — import redirector that maps `eduagent.X` → `clawed.X`

### Modified
- `pyproject.toml` — package name, entry points, build config
- `tests/conftest.py` — update monkeypatch paths from `eduagent.` → `clawed.`
- All `.py` files in `clawed/` — replace `from eduagent.` → `from clawed.`
- All `.py` files in `tests/` — replace `from eduagent.` → `from clawed.` (except backward-compat tests)

---

## Task 1: Move Source Directory

**Files:**
- Move: `eduagent/` → `clawed/`

This is a single git mv operation that preserves history.

- [ ] **Step 1: git mv the package**

```bash
cd /Users/mind_uploaded_crustacean/Projects/eduagent
git mv eduagent clawed
```

- [ ] **Step 2: Verify the move**

```bash
ls clawed/__init__.py clawed/gateway.py clawed/models.py clawed/handlers/
```

Expected: All files present in `clawed/`

- [ ] **Step 3: Commit the move**

```bash
git add -A
git commit -m "refactor: rename eduagent/ directory to clawed/"
```

---

## Task 2: Mass Replace Internal Imports

**Files:**
- Modify: All `.py` files in `clawed/` (~90 files)

Every internal import like `from eduagent.models import X` or `import eduagent.config` needs to become `from clawed.models import X` or `import clawed.config`.

- [ ] **Step 1: Run sed replacement on all Python files in clawed/**

```bash
cd /Users/mind_uploaded_crustacean/Projects/eduagent

# Replace "from eduagent." with "from clawed." in all .py files under clawed/
find clawed -name "*.py" -exec sed -i '' 's/from eduagent\./from clawed./g' {} +

# Replace "import eduagent." with "import clawed."
find clawed -name "*.py" -exec sed -i '' 's/import eduagent\./import clawed./g' {} +

# Replace string literals like "eduagent.state.DEFAULT_DATA_DIR" used in monkeypatch
find clawed -name "*.py" -exec sed -i '' 's/"eduagent\./"clawed./g' {} +
```

- [ ] **Step 2: Fix the __init__.py version/description**

Edit `clawed/__init__.py` to update the package identity:

```python
"""Claw-ED — Your teaching files, your AI co-teacher."""

__version__ = "0.3.0"
__author__ = "Jon Maccarello & Claw-ED contributors"
__description__ = "Your teaching files, your AI co-teacher"

# Central I/O — re-exported for convenience
from clawed.io import output_dir as output_dir  # noqa: F401
from clawed.io import read_text as read_text  # noqa: F401
from clawed.io import safe_filename as safe_filename  # noqa: F401
from clawed.io import save_output as save_output  # noqa: F401
from clawed.io import write_text as write_text  # noqa: F401


def _safe_filename(title: str) -> str:
    """.. deprecated:: 0.2.0 Use :func:`clawed.io.safe_filename` instead."""
    return safe_filename(title, max_len=50)
```

- [ ] **Step 3: Fix __main__.py**

Edit `clawed/__main__.py`:

```python
"""Allow running with: python -m clawed"""
import sys


def main():
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")

        from clawed.cli import app
        app()
    except KeyboardInterrupt:
        sys.exit(130)
    except SystemExit:
        raise
    except Exception as e:
        _handle_error(e)
        sys.exit(1)


def _handle_error(e):
    from rich.console import Console
    console = Console(stderr=True)
    name = type(e).__name__
    msg = str(e)
    if "UnicodeEncodeError" in name or "UnicodeDecodeError" in name:
        console.print("[red]Encoding error.[/red] Fix: set PYTHONIOENCODING=utf-8")
    elif "ConnectionError" in name or "ConnectError" in name:
        console.print("[red]Can't reach the AI model.[/red] Is Ollama running? Try: ollama serve")
    elif "ValidationError" in name:
        console.print("[red]The AI returned unexpected data.[/red] Try again -- LLM outputs vary.")
    elif "FileNotFoundError" in name:
        console.print(f"[red]File not found:[/red] {msg}")
    elif "401" in msg or "403" in msg or "authentication" in msg.lower():
        console.print("[red]Authentication failed.[/red] Check your API key: clawed config show")
    elif "404" in msg and "model" in msg.lower():
        console.print(f"[red]Model not found.[/red] {msg}")
    else:
        console.print(f"[red]Error:[/red] {msg}")
        console.print("[dim]Run with --verbose for details, or report at github.com/SirhanMacx/clawed/issues[/dim]")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Verify no stale references remain in clawed/**

```bash
grep -rn "from eduagent\." clawed/ --include="*.py" | head -20
grep -rn "import eduagent\." clawed/ --include="*.py" | head -20
```

Expected: No matches (all replaced)

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor: replace all internal imports from eduagent to clawed"
```

---

## Task 3: Create Backward-Compatible eduagent Shim Package

**Files:**
- Create: `eduagent/__init__.py`
- Create: `eduagent/_compat.py`

The shim makes `from eduagent.anything import X` transparently resolve to `from clawed.anything import X`. This uses Python's import hook system so we don't need to manually create a shim file for every submodule.

- [ ] **Step 1: Write the test**

```python
# tests/test_backward_compat.py
"""Tests that the old eduagent imports still work after rename to clawed."""
import pytest


class TestBackwardCompat:
    def test_import_clawed_package(self):
        import clawed
        assert hasattr(clawed, "__version__")

    def test_import_eduagent_package(self):
        import eduagent
        assert hasattr(eduagent, "__version__")

    def test_versions_match(self):
        import clawed
        import eduagent
        assert clawed.__version__ == eduagent.__version__

    def test_import_submodule_via_eduagent(self):
        from eduagent.models import AppConfig
        from clawed.models import AppConfig as ClawedAppConfig
        assert AppConfig is ClawedAppConfig

    def test_import_gateway_via_eduagent(self):
        from eduagent.gateway import Gateway
        from clawed.gateway import Gateway as ClawedGateway
        assert Gateway is ClawedGateway

    def test_import_gateway_response_via_eduagent(self):
        from eduagent.gateway_response import GatewayResponse, Button
        assert GatewayResponse is not None
        assert Button is not None

    def test_import_handler_via_eduagent(self):
        from eduagent.handlers.onboard import OnboardHandler
        from clawed.handlers.onboard import OnboardHandler as ClawedOnboard
        assert OnboardHandler is ClawedOnboard

    def test_import_router_via_eduagent(self):
        from eduagent.router import Intent, parse_intent
        from clawed.router import Intent as ClawedIntent
        assert Intent is ClawedIntent

    def test_import_io_functions_from_eduagent(self):
        from eduagent import output_dir, safe_filename
        assert callable(safe_filename)

    def test_import_deep_submodule(self):
        from eduagent.handlers.generate import GenerateHandler
        from clawed.handlers.generate import GenerateHandler as CG
        assert GenerateHandler is CG

    def test_import_skills_subpackage(self):
        from eduagent.skills.base import SubjectSkill
        from clawed.skills.base import SubjectSkill as CS
        assert SubjectSkill is CS
```

- [ ] **Step 2: Create the import hook shim**

```python
# eduagent/_compat.py
"""Import hook that redirects eduagent.* imports to clawed.* modules.

This allows all existing code that does `from eduagent.X import Y`
to transparently work after the package rename to clawed.
"""
from __future__ import annotations

import importlib
import sys
from importlib.abc import MetaPathFinder, Loader
from importlib.machinery import ModuleSpec


class _EduagentRedirectFinder(MetaPathFinder):
    """Intercepts `import eduagent.X` and redirects to `import clawed.X`."""

    _PREFIX = "eduagent."

    def find_module(self, fullname, path=None):
        if fullname == "eduagent" or fullname.startswith(self._PREFIX):
            return self
        return None

    def find_spec(self, fullname, path, target=None):
        if fullname == "eduagent":
            return None  # Let the real eduagent/__init__.py load normally
        if fullname.startswith(self._PREFIX):
            clawed_name = "clawed" + fullname[len("eduagent"):]
            return ModuleSpec(fullname, _EduagentRedirectLoader(clawed_name))
        return None


class _EduagentRedirectLoader(Loader):
    """Loads the clawed.* module and installs it as eduagent.* too."""

    def __init__(self, clawed_name: str):
        self._clawed_name = clawed_name

    def create_module(self, spec):
        return None  # Use default semantics

    def exec_module(self, module):
        # Import the real clawed module
        real = importlib.import_module(self._clawed_name)
        # Make the eduagent.X module point to the same object
        module.__dict__.update(real.__dict__)
        module.__spec__ = real.__spec__
        module.__loader__ = self
        module.__path__ = getattr(real, "__path__", [])
        module.__file__ = getattr(real, "__file__", None)
        # Also register in sys.modules so sub-imports work
        sys.modules[module.__name__] = module


def install():
    """Install the import redirect hook. Idempotent."""
    for finder in sys.meta_path:
        if isinstance(finder, _EduagentRedirectFinder):
            return
    sys.meta_path.insert(0, _EduagentRedirectFinder())
```

- [ ] **Step 3: Create eduagent/__init__.py shim**

```python
# eduagent/__init__.py
"""Backward-compatibility shim — the real package is now `clawed`.

All imports like `from eduagent.X import Y` are transparently
redirected to `from clawed.X import Y` via the import hook.
"""
from eduagent._compat import install as _install_compat
_install_compat()

from clawed import *  # noqa: F401, F403, E402
from clawed import __version__, __author__, __description__  # noqa: E402
```

- [ ] **Step 4: Run backward compat tests**

Run: `cd /Users/mind_uploaded_crustacean/Projects/eduagent && .venv/bin/python3 -m pytest tests/test_backward_compat.py -v`
Expected: All 12 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/mind_uploaded_crustacean/Projects/eduagent
git add eduagent/__init__.py eduagent/_compat.py tests/test_backward_compat.py
git commit -m "feat: add eduagent backward-compat shim redirecting to clawed"
```

---

## Task 4: Update pyproject.toml

**Files:**
- Modify: `pyproject.toml`

Update the package name, version, entry points, and build configuration to support both the `clawed` and `eduagent` packages.

- [ ] **Step 1: Update pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "clawed"
version = "0.3.0"
description = "Your teaching files, your AI co-teacher. Upload curriculum materials, get a digital co-teacher that generates lessons in your voice."
readme = "README.md"
license = "MIT"
requires-python = ">=3.10"
authors = [
    { name = "Jon Maccarello & Claw-ED contributors" },
]
keywords = ["education", "teachers", "lesson-plans", "ai", "teaching", "clawed"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Education",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Education",
]
dependencies = [
    "typer>=0.9.0,<1.0",
    "rich>=13.0.0",
    "pydantic>=2.0.0,<3.0",
    "httpx>=0.25.0,<1.0",
    "anthropic>=0.40.0,<1.0",
    "openai>=1.0.0",
    "PyMuPDF>=1.23.0",
    "python-docx>=1.0.0",
    "python-pptx>=0.6.21",
    "reportlab>=4.0.0",
    "Jinja2>=3.1.0",
    "fastapi>=0.110.0,<1.0",
    "uvicorn[standard]>=0.27.0",
    "python-multipart>=0.0.6",
    "sse-starlette>=1.6.0",
    "mcp>=1.0.0",
    "json-repair>=0.30.0",
    "slowapi>=0.1.9,<1.0",
    "pyyaml>=6.0,<7.0",
    "apscheduler>=3.10.0,<4.0",
]

[project.optional-dependencies]
telegram-legacy = ["python-telegram-bot>=20.8"]
telegram = ["python-telegram-bot>=20.8"]
google = ["google-api-python-client>=2.0.0", "google-auth-oauthlib>=1.0.0"]
voice = ["faster-whisper>=0.10.0"]
tui = ["textual>=0.56.0"]
all = [
    "python-telegram-bot>=20.0",
    "faster-whisper>=0.10.0",
    "textual>=0.56.0",
    "keyring>=24.0.0",
    "uvicorn[standard]>=0.27.0",
    "gunicorn>=21.0.0",
]
hosted = ["uvicorn[standard]>=0.27.0", "gunicorn>=21.0.0"]
pdf = ["weasyprint>=60.0"]
keyring = ["keyring>=24.0.0"]
dev = ["pytest>=7.0.0", "pytest-asyncio>=0.21.0", "ruff>=0.1.0", "apscheduler>=3.10.0,<4.0", "faster-whisper>=0.10.0"]

[project.scripts]
clawed = "clawed.cli:app"
eduagent = "clawed.cli:app"

[project.urls]
Homepage = "https://github.com/SirhanMacx/clawed"
Documentation = "https://github.com/SirhanMacx/clawed#readme"
Issues = "https://github.com/SirhanMacx/clawed/issues"

[tool.hatch.build.targets.wheel]
packages = ["clawed", "eduagent"]

[tool.setuptools.package-data]
clawed = ["prompts/*.txt", "demo/*.json"]

[tool.ruff]
line-length = 120
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]

[tool.ruff.lint.per-file-ignores]
"clawed/doc_export.py" = ["N806"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

- [ ] **Step 2: Reinstall in dev mode**

```bash
cd /Users/mind_uploaded_crustacean/Projects/eduagent
.venv/bin/pip install -e ".[dev]"
```

- [ ] **Step 3: Verify both CLI commands work**

```bash
.venv/bin/clawed --help
.venv/bin/eduagent --help
```

Both should show the same CLI help.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "feat: update pyproject.toml for clawed package with dual CLI entry points"
```

---

## Task 5: Update Test Suite Imports

**Files:**
- Modify: All `.py` files in `tests/` (~40 files)
- Modify: `tests/conftest.py`

Tests should import from `clawed` (the canonical package) while the backward-compat test verifies `eduagent` imports still work.

- [ ] **Step 1: Mass replace test imports**

```bash
cd /Users/mind_uploaded_crustacean/Projects/eduagent

# Replace imports in test files
find tests -name "*.py" -not -name "test_backward_compat.py" -exec sed -i '' 's/from eduagent\./from clawed./g' {} +
find tests -name "*.py" -not -name "test_backward_compat.py" -exec sed -i '' 's/import eduagent\./import clawed./g' {} +

# Replace monkeypatch string references
find tests -name "*.py" -not -name "test_backward_compat.py" -exec sed -i '' 's/"eduagent\./"clawed./g' {} +
```

- [ ] **Step 2: Update conftest.py**

The conftest monkeypatches `"eduagent.state.DEFAULT_DATA_DIR"` etc. — these need to become `"clawed.state.DEFAULT_DATA_DIR"`.

Verify after sed:
```bash
grep "eduagent" tests/conftest.py
```
Expected: Only `EDUAGENT_DATA_DIR` env var name (which is a runtime config, not an import path — keep it as-is).

- [ ] **Step 3: Run full test suite**

```bash
.venv/bin/python3 -m pytest tests/ -q --tb=line 2>&1 | tail -10
```

Expected: 1238+ passed, 1 pre-existing failure (faster-whisper), ~34 skipped

- [ ] **Step 4: Commit**

```bash
git add tests/
git commit -m "refactor: update all test imports from eduagent to clawed"
```

---

## Task 6: Verify and Clean Up

- [ ] **Step 1: Verify canonical imports work**

```bash
.venv/bin/python3 -c "from clawed.gateway import Gateway; print('Gateway:', Gateway)"
.venv/bin/python3 -c "from clawed.handlers.generate import GenerateHandler; print('OK')"
.venv/bin/python3 -c "from clawed import __version__; print('clawed', __version__)"
```

- [ ] **Step 2: Verify backward compat imports work**

```bash
.venv/bin/python3 -c "from eduagent.gateway import Gateway; print('Gateway via eduagent:', Gateway)"
.venv/bin/python3 -c "from eduagent.handlers.generate import GenerateHandler; print('OK')"
.venv/bin/python3 -c "from eduagent import __version__; print('eduagent', __version__)"
```

- [ ] **Step 3: Verify no orphaned eduagent references in clawed/**

```bash
grep -rn "eduagent" clawed/ --include="*.py" | grep -v "EDUAGENT_DATA_DIR" | grep -v "# eduagent" | grep -v "eduagent Contributors"
```

Expected: Only env var references (`EDUAGENT_DATA_DIR`) and comments — no import statements.

Note: `EDUAGENT_DATA_DIR` is a user-facing environment variable name that should NOT be renamed (it would break existing deployments). It stays as-is.

- [ ] **Step 4: Run full test suite one final time**

```bash
.venv/bin/python3 -m pytest tests/ -q --tb=line
```

Expected: All green (except pre-existing faster-whisper failure)

- [ ] **Step 5: Commit any remaining fixes**

```bash
git add -A
git commit -m "chore: Phase 2 complete — package renamed to clawed with backward compat"
```

---

## Summary

| Task | What | Risk |
|------|------|------|
| 1 | git mv eduagent → clawed | Low — single operation |
| 2 | Mass replace internal imports | Medium — sed could miss edge cases |
| 3 | Create eduagent shim package | Medium — import hook must work for deep submodules |
| 4 | Update pyproject.toml | Low — config change |
| 5 | Update test imports | Medium — same sed risk as Task 2 |
| 6 | Verify everything works | Low — just verification |

### What stays the same
- `EDUAGENT_DATA_DIR` env var (user-facing, don't break deployments)
- `~/.eduagent/` data directory (user data, don't move)
- All functionality — this is purely a naming change

### What changes
- Package name: `eduagent` → `clawed` (canonical)
- PyPI name: `clawed`
- CLI: `clawed` (primary) + `eduagent` (backward compat)
- Imports: `from clawed import X` (primary) + `from eduagent import X` (backward compat)
- Version: 0.2.0 → 0.3.0
