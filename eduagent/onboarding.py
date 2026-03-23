"""First-run onboarding wizard for EDUagent.

When a teacher runs `eduagent chat` or `eduagent bot` with no config,
this guided setup collects their teaching context, API key, and
optionally ingests existing lesson plans — so EDUagent is ready to
go in under two minutes.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from eduagent.config import has_config, set_api_key, test_llm_connection
from eduagent.models import AppConfig, LLMProvider, TeacherProfile
from eduagent.state_standards import STATE_STANDARDS_CONFIG

console = Console()

# Full state names for autocomplete / fuzzy matching
US_STATES: list[str] = sorted(
    {v["name"] for v in STATE_STANDARDS_CONFIG.values()}
)

# Reverse lookup: full name -> abbreviation
_STATE_NAME_TO_ABBR: dict[str, str] = {
    v["name"].lower(): k for k, v in STATE_STANDARDS_CONFIG.items()
}
# Also map abbreviations directly
for _abbr in STATE_STANDARDS_CONFIG:
    _STATE_NAME_TO_ABBR[_abbr.lower()] = _abbr


def _resolve_state(raw: str) -> str | None:
    """Resolve a state name or abbreviation to a two-letter code."""
    key = raw.strip().lower()
    if not key:
        return None
    if key in _STATE_NAME_TO_ABBR:
        return _STATE_NAME_TO_ABBR[key]
    # Fuzzy prefix match
    for name, abbr in _STATE_NAME_TO_ABBR.items():
        if name.startswith(key):
            return abbr
    return None


def _ask_state() -> str:
    """Prompt for state with validation against the 50-state list."""
    while True:
        raw = Prompt.ask(
            "\n[bold]What state are you in?[/bold]  [dim](name or abbreviation)[/dim]"
        )
        abbr = _resolve_state(raw)
        if abbr:
            full_name = STATE_STANDARDS_CONFIG[abbr]["name"]
            console.print(f"  [green]\u2713[/green] {full_name}")
            return abbr
        console.print(f"  [red]Couldn't match \"{raw}\".[/red] Try the full name or two-letter code.")


def _ask_provider() -> tuple[LLMProvider, str | None]:
    """Show provider options and collect an API key."""
    table = Table(title="Choose your AI backend", show_header=True, header_style="bold")
    table.add_column("#", style="dim", width=3)
    table.add_column("Provider")
    table.add_column("Cost")
    table.add_column("Notes")
    table.add_row("1", "Anthropic (Claude)", "Pay per token", "Best quality")
    table.add_row("2", "OpenAI (GPT-4o)", "Pay per token", "Widely used")
    table.add_row("3", "Ollama", "Free", "Runs locally \u2014 no API key needed")
    console.print()
    console.print(table)

    while True:
        choice = Prompt.ask("\n[bold]Pick a provider[/bold]", choices=["1", "2", "3"], default="1")
        if choice == "1":
            provider = LLMProvider.ANTHROPIC
            key = Prompt.ask("  [bold]Anthropic API key[/bold]  [dim](sk-ant-...)[/dim]")
            if not key.strip():
                console.print("  [red]API key cannot be empty.[/red]")
                continue
            return provider, key.strip()
        elif choice == "2":
            provider = LLMProvider.OPENAI
            key = Prompt.ask("  [bold]OpenAI API key[/bold]  [dim](sk-...)[/dim]")
            if not key.strip():
                console.print("  [red]API key cannot be empty.[/red]")
                continue
            return provider, key.strip()
        else:
            return LLMProvider.OLLAMA, None


def _test_connection(config: AppConfig) -> bool:
    """Test the LLM connection and show result."""
    console.print("\n  [dim]Testing connection...[/dim]")
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        result = loop.run_until_complete(test_llm_connection(config))
    except RuntimeError:
        result = asyncio.run(test_llm_connection(config))

    if result.get("connected"):
        console.print(f"  [green]\u2713 Connected![/green] {result.get('message', '')}")
        return True
    else:
        console.print(f"  [red]\u2717 Connection failed:[/red] {result.get('error', 'Unknown error')}")
        return False


def _ask_materials() -> str | None:
    """Optionally collect a materials path for ingestion."""
    console.print()
    raw = Prompt.ask(
        "[bold]Point me at your existing lesson plans[/bold]\n"
        "  [dim](folder path, or press Enter to skip)[/dim]",
        default="",
    )
    path_str = raw.strip()
    if not path_str:
        return None
    resolved = Path(path_str).expanduser().resolve()
    if not resolved.exists():
        console.print(f"  [red]Path not found:[/red] {resolved}")
        return None
    return str(resolved)


def _ingest_materials(path_str: str, config: AppConfig) -> None:
    """Run ingestion and show a quick persona summary."""
    from eduagent.ingestor import ingest_path
    from eduagent.persona import build_persona

    source = Path(path_str)
    console.print(f"\n  [dim]Reading files from {source}...[/dim]")

    docs = ingest_path(source)
    if not docs:
        console.print("  [yellow]No supported files found. You can ingest later with:[/yellow]")
        console.print("    [bold]eduagent ingest <path>[/bold]")
        return

    console.print(f"  [green]\u2713 Processed {len(docs)} files.[/green]")

    # Build persona from documents
    persona = build_persona(docs)
    console.print(
        Panel(
            persona.to_prompt_context(),
            title="[bold green]Your Teaching Profile[/bold green]",
            border_style="green",
            padding=(0, 1),
        )
    )


def run_onboarding() -> AppConfig:
    """Run the interactive first-run onboarding wizard.

    Returns the saved AppConfig so callers can proceed immediately.
    """
    console.print(
        Panel(
            "[bold]Welcome to EDUagent![/bold]\n\n"
            "I was built by a teacher, for teachers.\n"
            "Let's get you set up in about a minute.",
            title="[bold green]\U0001f393 EDUagent Setup[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
    )

    # ── Question 1: Subject(s) ──
    subjects_raw = Prompt.ask("\n[bold]What subject(s) do you teach?[/bold]")
    subjects = [s.strip() for s in subjects_raw.split(",") if s.strip()]

    # ── Question 2: Grade level(s) ──
    grades_raw = Prompt.ask("[bold]What grade level(s)?[/bold]")
    grade_levels = [g.strip() for g in grades_raw.split(",") if g.strip()]

    # ── Question 3: State ──
    state_abbr = _ask_state()

    # ── API key selection ──
    provider, api_key = _ask_provider()

    # Save key securely
    if api_key:
        set_api_key(provider.value, api_key)

    # Build and save config
    profile = TeacherProfile(
        subjects=subjects,
        grade_levels=grade_levels,
        state=state_abbr,
    )
    config = AppConfig(
        provider=provider,
        teacher_profile=profile,
    )
    config.save()

    # Test connection
    connected = _test_connection(config)
    if not connected and provider != LLMProvider.OLLAMA:
        console.print("  [yellow]You can update your key later with:[/yellow]")
        console.print(f"    [bold]eduagent config set-key {provider.value}[/bold]")

    # ── Materials (optional) ──
    materials_path = _ask_materials()
    if materials_path:
        profile.materials_paths = [materials_path]
        config.teacher_profile = profile
        config.save()
        _ingest_materials(materials_path, config)

    # ── Success ──
    console.print(
        Panel(
            "[bold green]You're all set![/bold green]\n\n"
            "Try asking: [italic]\"What topic do you want to plan?\"[/italic]\n\n"
            "[dim]Tip: Run [bold]eduagent ingest <path>[/bold] anytime to add more materials.[/dim]",
            title="[bold green]\u2705 Ready[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
    )

    return config


def check_first_run() -> bool:
    """Check if this is a first run and launch onboarding if needed.

    Returns True if onboarding ran (or was skipped), False if config
    already existed. Callers should proceed normally either way.
    """
    if has_config():
        return False

    try:
        run_onboarding()
    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]Setup cancelled. Run [bold]eduagent chat[/bold] again anytime.[/dim]")
    return True
