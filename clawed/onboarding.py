"""First-run onboarding wizard for Claw-ED.

When a teacher runs `clawed chat` or `clawed bot` with no config,
this guided setup collects their teaching context, API key, and
optionally ingests existing lesson plans — so Claw-ED is ready to
go in under two minutes.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from clawed.commands._helpers import _safe_progress, console
from clawed.config import has_config, set_api_key, test_llm_connection
from clawed.models import AppConfig, LLMProvider, TeacherProfile
from clawed.state_standards import STATE_STANDARDS_CONFIG

logger = logging.getLogger(__name__)

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


def _detect_available_models() -> tuple[LLMProvider | None, str]:
    """Auto-detect what LLM backends are available.

    Checks: ANTHROPIC_API_KEY, OPENAI_API_KEY, Ollama running locally.
    Returns (provider, description) or (None, message).
    """
    # Check Anthropic
    if os.environ.get("ANTHROPIC_API_KEY"):
        return LLMProvider.ANTHROPIC, "Anthropic API key found in environment"

    # Check OpenAI
    if os.environ.get("OPENAI_API_KEY"):
        return LLMProvider.OPENAI, "OpenAI API key found in environment"

    # Check Ollama
    try:
        import httpx
        resp = httpx.get("http://localhost:11434/api/tags", timeout=3.0)
        if resp.status_code == 200:
            data = resp.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            # Prefer these models in order
            preferred = ["minimax-m2.7", "llama3.2", "mistral"]
            for pref in preferred:
                for model in models:
                    if pref in model:
                        return LLMProvider.OLLAMA, f"Ollama running with {model}"
            if models:
                return LLMProvider.OLLAMA, f"Ollama running with {models[0]}"
            return LLMProvider.OLLAMA, "Ollama running (no models pulled yet)"
    except Exception:
        pass

    return None, (
        "No LLM backend detected.\n"
        "  Set ANTHROPIC_API_KEY or OPENAI_API_KEY in your environment,\n"
        "  or install Ollama (https://ollama.ai) and run: ollama pull llama3.2"
    )


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
    """Run ingestion with a progress bar and show persona summary."""
    from clawed.ingestor import ingest_path
    from clawed.persona import build_persona

    source = Path(path_str)

    # Count files first for progress bar
    supported_exts = {".pdf", ".docx", ".pptx", ".txt", ".md"}
    all_files = [
        f for f in source.rglob("*")
        if f.is_file() and f.suffix.lower() in supported_exts
    ]

    if not all_files:
        console.print("  [yellow]No supported files found. You can ingest later with:[/yellow]")
        console.print("    [bold]clawed ingest <path>[/bold]")
        return

    with _safe_progress(console=console) as progress:
        task = progress.add_task(
            f"Reading files from {source.name}...",
            total=len(all_files),
        )
        docs = ingest_path(source)
        progress.update(task, completed=len(all_files), description="Files processed")

    console.print(f"  [green]\u2713 Processed {len(docs)} files.[/green]")

    console.print("  [dim]Extracting teaching style patterns...[/dim]")
    persona = build_persona(docs)

    console.print(
        Panel(
            persona.to_prompt_context(),
            title="[bold green]Your Teaching Profile[/bold green]",
            border_style="green",
            padding=(0, 1),
        )
    )
    console.print(f"  [green]\u2713 Persona saved — {persona.name or 'Teacher'} profile ready[/green]")

    return persona


def _show_persona_preview(subjects: list[str], grade_levels: list[str], state_abbr: str) -> bool:
    """Show a preview of what we learned and ask for confirmation."""
    from clawed.state_standards import STATE_STANDARDS_CONFIG
    state_name = STATE_STANDARDS_CONFIG.get(state_abbr, {}).get("name", state_abbr)

    preview = (
        f"I learned that you teach {', '.join(grade_levels)} grade "
        f"{', '.join(subjects)} in {state_name}."
    )
    console.print(f"\n  [bold]{preview}[/bold]")
    confirm = Prompt.ask("  Is this right?", choices=["y", "n"], default="y")
    return confirm.lower() == "y"


def run_onboarding() -> AppConfig:
    """Run the interactive first-run onboarding wizard.

    Returns the saved AppConfig so callers can proceed immediately.
    """
    console.print(
        Panel(
            "[bold]Welcome to Claw-ED![/bold]\n\n"
            "I was built by a teacher, for teachers.\n"
            "Let's get you set up in about a minute.",
            title="[bold green]\U0001f393 Claw-ED Setup[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
    )

    # ── Model auto-detection ──
    detected_provider, detect_msg = _detect_available_models()
    if detected_provider:
        console.print(f"\n  [green]\u2713 Auto-detected:[/green] {detect_msg}")

    # ── Question 1: Subject(s) ──
    subjects_raw = Prompt.ask("\n[bold]What subject(s) do you teach?[/bold]")
    subjects = [s.strip() for s in subjects_raw.split(",") if s.strip()]

    # ── Question 2: Grade level(s) ──
    grades_raw = Prompt.ask("[bold]What grade level(s)?[/bold]")
    grade_levels = [g.strip() for g in grades_raw.split(",") if g.strip()]

    # ── Question 3: State ──
    state_abbr = _ask_state()

    # ── Preview and confirm ──
    confirmed = _show_persona_preview(subjects, grade_levels, state_abbr)
    if not confirmed:
        console.print("  [dim]Let's try again.[/dim]")
        subjects_raw = Prompt.ask("[bold]What subject(s) do you teach?[/bold]")
        subjects = [s.strip() for s in subjects_raw.split(",") if s.strip()]
        grades_raw = Prompt.ask("[bold]What grade level(s)?[/bold]")
        grade_levels = [g.strip() for g in grades_raw.split(",") if g.strip()]
        state_abbr = _ask_state()

    # ── API key selection ──
    if detected_provider and detected_provider != LLMProvider.OLLAMA:
        # Auto-detected a cloud provider, use it
        provider = detected_provider
        api_key = None  # Already in env
        console.print(f"  [green]\u2713 Using {provider.value} from environment.[/green]")
    elif detected_provider == LLMProvider.OLLAMA:
        provider = LLMProvider.OLLAMA
        api_key = None
        console.print("  [green]\u2713 Using local Ollama.[/green]")
    else:
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
        console.print(f"    [bold]clawed config set-key {provider.value}[/bold]")

    # ── Materials (optional) ──
    materials_path = _ask_materials()
    if materials_path:
        profile.materials_paths = [materials_path]
        config.teacher_profile = profile
        config.save()
        _ingest_materials(materials_path, config)

    # ── Auto-generate a sample lesson ──
    if connected:
        console.print("\n  [dim]Generating a sample lesson so you can see Claw-ED in action...[/dim]")
        try:
            from clawed.llm import LLMClient
            client = LLMClient(config)

            topic = subjects[0] if subjects else "Science"
            grade = grade_levels[0] if grade_levels else "8"

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                sample = loop.run_until_complete(
                    client.generate(
                        f"Generate a brief 3-sentence lesson opening (do-now/bell-ringer) "
                        f"for {grade} grade {topic}. Keep it concise.",
                        temperature=0.7,
                        max_tokens=300,
                    )
                )
            finally:
                loop.close()

            if sample and len(sample) > 10:
                console.print(
                    Panel(
                        sample.strip(),
                        title="[bold cyan]Sample Lesson Opening[/bold cyan]",
                        border_style="cyan",
                        padding=(0, 1),
                    )
                )
        except Exception:
            pass  # Sample lesson is best-effort

    # ── Success ──
    console.print(
        Panel(
            "[bold green]Setup complete! Here's how to use me:[/bold green]\n\n"
            "  [bold]clawed chat[/bold]         \u2014 Start an interactive session\n"
            "  [bold]clawed ingest <path>[/bold] \u2014 Feed me your lesson plans\n"
            "  [bold]clawed serve[/bold]         \u2014 Launch the web dashboard\n\n"
            "[dim]Tip: Run [bold]clawed ingest <path>[/bold] anytime to add more materials.[/dim]",
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

    import sys
    if not sys.stdin.isatty():
        # Background mode (e.g. bot launched via cron/systemd) — skip interactive setup
        logger.info("Non-interactive mode, skipping onboarding wizard")
        # Create a minimal default config so the app can proceed
        try:
            cfg = AppConfig()
            cfg.save()
        except Exception:
            pass
        return True

    try:
        run_onboarding()
    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]Setup cancelled. Run [bold]clawed chat[/bold] again anytime.[/dim]")
    return True
