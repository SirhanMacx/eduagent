"""LLM and API key config commands — registered on config_app."""

from __future__ import annotations

from typing import Optional

import typer
from rich.panel import Panel

from clawed.commands._helpers import console
from clawed.commands.config import config_app
from clawed.models import AppConfig, LLMProvider


@config_app.command("set-model")
def config_set_model(
    provider: str = typer.Argument(
        ..., help="LLM provider: anthropic, openai, or ollama"
    ),
    model: Optional[str] = typer.Option(
        None, "--model", "-m", help="Model name override"
    ),
):
    """Configure the LLM backend."""
    try:
        llm_provider = LLMProvider(provider.lower())
    except ValueError:
        console.print(
            f"[red]Unknown provider: {provider}[/red]."
            " Use: anthropic, openai, ollama"
        )
        raise typer.Exit(1)

    cfg = AppConfig.load()
    cfg.provider = llm_provider

    if model:
        if llm_provider == LLMProvider.ANTHROPIC:
            cfg.anthropic_model = model
        elif llm_provider == LLMProvider.OPENAI:
            cfg.openai_model = model
        elif llm_provider == LLMProvider.OLLAMA:
            cfg.ollama_model = model

    cfg.save()
    model_name = model or {
        LLMProvider.ANTHROPIC: cfg.anthropic_model,
        LLMProvider.OPENAI: cfg.openai_model,
        LLMProvider.OLLAMA: cfg.ollama_model,
    }[llm_provider]

    console.print(
        Panel(
            f"[bold]Provider:[/bold] {llm_provider.value}\n"
            f"[bold]Model:[/bold] {model_name}",
            title="Configuration Updated",
        )
    )

    # Ping the provider to verify connectivity
    import httpx as _httpx

    if llm_provider == LLMProvider.OLLAMA:
        try:
            resp = _httpx.get(
                f"{cfg.ollama_base_url.rstrip('/')}/api/version", timeout=5,
            )
            version = resp.json().get("version", "unknown")
            console.print(f"[green]Connected to Ollama v{version}[/green]")
        except Exception:
            console.print(
                "[yellow]Warning: Can't reach Ollama at "
                f"{cfg.ollama_base_url}. Is it running?[/yellow]"
            )
    elif llm_provider == LLMProvider.ANTHROPIC:
        import os as _os
        key = _os.environ.get("ANTHROPIC_API_KEY", "")
        if key and key.startswith("sk-"):
            console.print("[green]API key format looks valid.[/green]")
        elif not key:
            console.print(
                "[yellow]Warning: ANTHROPIC_API_KEY not set. "
                "Export it before generating.[/yellow]"
            )
    elif llm_provider == LLMProvider.OPENAI:
        import os as _os
        key = _os.environ.get("OPENAI_API_KEY", "")
        if key and key.startswith("sk-"):
            console.print("[green]API key format looks valid.[/green]")
        elif not key:
            console.print(
                "[yellow]Warning: OPENAI_API_KEY not set. "
                "Export it before generating.[/yellow]"
            )


@config_app.command("set-token")
def config_set_token(
    token: str = typer.Argument(
        ..., help="Telegram bot token from @BotFather"
    ),
):
    """Save your Telegram bot token so you don't need to pass it every time.

    After saving, just run:

        clawed bot

    No --token flag needed.
    """
    cfg = AppConfig.load()
    cfg.telegram_bot_token = token
    cfg.save()
    masked = (
        token[:5] + "..." + token[-4:] if len(token) > 12 else "***"
    )
    console.print(
        Panel(
            f"[bold green]Token saved![/bold green]\n\n"
            f"Token: {masked}\n\n"
            f"You can now start the bot with just:\n"
            f"  [cyan]clawed bot[/cyan]",
            title="Telegram Bot Token",
        )
    )


@config_app.command("set-unsplash-key")
def config_set_unsplash_key(
    key: str = typer.Argument(
        ..., help="Unsplash Access Key for slide images"
    ),
):
    """Save your Unsplash API key for fetching slide background images.

    Get a free key at https://unsplash.com/developers (50 requests/hour).

    After saving, PPTX exports will automatically include relevant
    educational images on slides.  Without a key, slides still look
    great -- just without photos.
    """
    from clawed.config import set_api_key

    set_api_key("unsplash", key)
    masked = key[:5] + "..." + key[-4:] if len(key) > 12 else "***"
    console.print(
        Panel(
            f"[bold green]Unsplash key saved![/bold green]\n\n"
            f"Key: {masked}\n\n"
            f"PPTX exports will now include images.\n"
            f"To remove: [cyan]unset UNSPLASH_ACCESS_KEY[/cyan]",
            title="Unsplash API Key",
        )
    )


@config_app.command("show")
def config_show():
    """Show current configuration."""
    from clawed.config import get_api_key

    cfg = AppConfig.load()
    token_display = "Not set"
    if cfg.telegram_bot_token:
        t = cfg.telegram_bot_token
        token_display = t[:5] + "..." + t[-4:] if len(t) > 12 else "***"
    unsplash_key = get_api_key("unsplash")
    unsplash_display = "Not set"
    if unsplash_key:
        unsplash_display = (
            unsplash_key[:5] + "..." + unsplash_key[-4:]
            if len(unsplash_key) > 12
            else "***"
        )
    console.print(
        Panel(
            f"[bold]Provider:[/bold] {cfg.provider.value}\n"
            f"[bold]Anthropic Model:[/bold] {cfg.anthropic_model}\n"
            f"[bold]OpenAI Model:[/bold] {cfg.openai_model}\n"
            f"[bold]Ollama Model:[/bold] {cfg.ollama_model}\n"
            f"[bold]Ollama URL:[/bold] {cfg.ollama_base_url}\n"
            f"[bold]Output Dir:[/bold] {cfg.output_dir}\n"
            f"[bold]Export Format:[/bold] {cfg.export_format}\n"
            f"[bold]Include Homework:[/bold] {cfg.include_homework}\n"
            f"[bold]Telegram Token:[/bold] {token_display}\n"
            f"[bold]Unsplash Key:[/bold] {unsplash_display}",
            title="Claw-ED Configuration",
        )
    )
