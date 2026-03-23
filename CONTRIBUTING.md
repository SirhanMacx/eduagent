# Contributing to EDUagent

Thanks for your interest in contributing! EDUagent is an open-source project and we welcome contributions of all kinds.

## Getting Started

1. Fork and clone the repo
2. Install in development mode:

```bash
pip install -e ".[dev]"
```

3. Run the tests:

```bash
pytest
```

## Making Changes

1. Create a branch for your work: `git checkout -b my-feature`
2. Make your changes
3. Run tests and linting:

```bash
pytest
ruff check .
```

4. Commit with a clear message describing what and why
5. Open a pull request against `main`

## What to Work On

- Check open issues for bugs and feature requests
- Look at the roadmap in README.md for planned features
- Improvements to prompts (in `eduagent/prompts/`) are always welcome
- Documentation improvements and example materials

## Code Style

- We use [Ruff](https://docs.astral.sh/ruff/) for linting (config in `pyproject.toml`)
- Line length: 100 characters
- Type hints are appreciated but not mandatory
- Keep functions focused and small

## Adding a New LLM Provider

1. Add the provider to `LLMProvider` enum in `models.py`
2. Add the API call method to `LLMClient` in `llm.py`
3. Update `cli.py` config commands to support the new provider
4. Add any new dependencies to `pyproject.toml`

## Questions?

Open an issue — we're happy to help.
