"""Bot, serve, MCP server, chat, and student-chat commands."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.panel import Panel

from clawed.commands._helpers import _safe_progress, console
from clawed.commands._helpers import run_async as _run_async
from clawed.models import AppConfig, LLMProvider

bot_app = typer.Typer()


# ── Chat command ─────────────────────────────────────────────────────────


@bot_app.command()
def chat(
    teacher_id: str = typer.Option(
        "local-teacher", "--id", help="Teacher session ID"
    ),
) -> None:
    """Start an interactive chat session with Claw-ED in the terminal."""
    from clawed.onboarding import check_first_run

    check_first_run()

    from clawed.cli_chat import main as chat_main

    chat_main(teacher_id)


# ── Student chat command ─────────────────────────────────────────────────


@bot_app.command(name="student-chat")
def student_chat(
    class_code: str = typer.Option(
        ..., "--class-code", help="Class code from your teacher"
    ),
    student_id: str = typer.Option(
        "student-001", "--student-id", help="Your student ID"
    ),
) -> None:
    """Start a student chat session — ask questions about today's lesson."""
    from rich.live import Live
    from rich.prompt import Prompt
    from rich.spinner import Spinner

    from clawed.student_bot import StudentBot

    bot = StudentBot()
    class_info = bot.get_class(class_code)
    if not class_info:
        console.print(
            f"[red]Class code '{class_code}' not found.[/red]"
            " Check with your teacher."
        )
        raise typer.Exit(1)

    if not class_info.active_lesson_json:
        console.print(
            "[yellow]Your teacher hasn't activated a lesson yet."
            " Check back soon![/yellow]"
        )
        raise typer.Exit(1)

    import json as _json

    lesson_data = _json.loads(class_info.active_lesson_json)
    lesson_title = lesson_data.get("title", "Today's Lesson")

    console.print(
        Panel(
            f"*{lesson_title}*\n\n"
            f"Ask me anything about today's lesson!\n"
            f"Type '/quit' to exit.\n",
            title=(
                f"[bold green]Student Chat"
                f" — {class_code}[/bold green]"
            ),
            border_style="green",
            padding=(1, 2),
        )
    )

    while True:
        try:
            message = Prompt.ask("[bold cyan]You[/bold cyan]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/dim]")
            break

        text = message.strip()
        if not text:
            continue
        if text.lower() in ("/quit", "/exit", "quit", "exit"):
            console.print("[dim]Goodbye![/dim]")
            break

        with Live(
            Spinner(
                "dots",
                text="[dim]Thinking...[/dim]",
                style="green",
            ),
            console=console,
            transient=True,
        ):
            try:
                response = _run_async(
                    bot.handle_message(text, student_id, class_code)
                )
            except Exception as e:
                response = f"Oops, something went wrong: {e}"

        console.print()
        console.print(
            Panel(
                response,
                title="[bold green]Teacher[/bold green]",
                border_style="green",
                padding=(0, 1),
            )
        )
        console.print()


# ── MCP Server command ──────────────────────────────────────────────────


@bot_app.command(name="mcp-server")
def mcp_server() -> None:
    """Start the Claw-ED MCP server for tool integration.

    Uses stdio transport (the standard MCP transport). Connect to this
    server by launching the process and communicating over stdin/stdout.
    """
    from clawed.mcp_server import run_server

    console.print(
        Panel(
            "Starting MCP server (stdio transport)\n"
            "Tools: generate_lesson, generate_unit,"
            " ingest_materials, student_question,"
            " get_teacher_standards",
            title="[bold blue]Claw-ED MCP Server[/bold blue]",
            border_style="blue",
        )
    )
    run_server()


# ── First-run setup ──────────────────────────────────────────────────


def _first_run_setup() -> None:
    """Interactive first-run setup wizard. Only runs when no config exists."""
    from rich.prompt import Prompt

    from clawed.config import has_config, set_api_key, test_llm_connection

    if has_config():
        return

    console.print(
        Panel(
            "[bold]Welcome to Claw-ED![/bold]\n\n"
            "Let's get you set up in 2 minutes.",
            title="Setup",
            border_style="blue",
        )
    )

    # Provider selection
    provider_choice = Prompt.ask(
        "Which AI provider do you want to use?",
        choices=["ollama", "anthropic", "openai"],
        default="ollama",
    )

    cfg = AppConfig()
    cfg.provider = LLMProvider(provider_choice)

    # API key for cloud providers
    if provider_choice in ("anthropic", "openai"):
        api_key = Prompt.ask(
            f"Enter your {provider_choice.title()} API key",
            password=True,
        )
        if api_key.strip():
            set_api_key(provider_choice, api_key.strip())
            console.print("[green]API key saved securely.[/green]")

    # Test connection
    with _safe_progress(console=console) as progress:
        task = progress.add_task("Testing connection...", total=None)
        result = _run_async(test_llm_connection(cfg))
        progress.update(task, description="Done!")

    model = result.get("model", "")
    if result.get("connected"):
        console.print(f"[green]Connected to {model}[/green]")
    else:
        console.print(
            f"[yellow]Could not connect:"
            f" {result.get('error', 'unknown')}[/yellow]"
        )
        console.print(
            "[dim]You can update settings later at"
            " http://localhost:8000/settings[/dim]"
        )

    # Subject and grades
    subject = Prompt.ask("What subject do you teach?", default="Science")
    grades = Prompt.ask("What grade(s)?", default="8")

    cfg.save()

    console.print("\n[green]Configuration saved![/green]")
    console.print(
        f"[dim]Subject: {subject}, Grades: {grades}[/dim]\n"
    )


# ── Serve command ──────────────────────────────────────────────────────


@bot_app.command()
def serve(
    port: int = typer.Option(
        8000, "--port", "-p", help="Port to listen on"
    ),
    host: str = typer.Option(
        "127.0.0.1", "--host", "-h", help="Host to bind to"
    ),
    token: Optional[str] = typer.Option(
        None,
        "--token",
        "-t",
        envvar="TELEGRAM_BOT_TOKEN",
        help="Telegram bot token",
    ),
    tui: bool = typer.Option(
        False, "--tui", help="Launch the live TUI dashboard"
    ),
    skip_setup: bool = typer.Option(
        False, "--skip-setup", help="Skip first-run setup wizard"
    ),
    reload: bool = typer.Option(
        False, "--reload", help="Enable auto-reload for development"
    ),
):
    """Start the Claw-ED server.

    \b
    Modes:
      clawed serve --token TOKEN --tui   # Full TUI + gateway + web
      clawed serve --token TOKEN         # Gateway + web (no TUI, for VPS)
      clawed serve --tui                 # TUI only (no Telegram, demos)
      clawed serve                       # Web server only
    """
    if not skip_setup:
        _first_run_setup()

    cfg = AppConfig.load()

    # Resolve token from saved config if not provided
    if not token:
        token = cfg.telegram_bot_token

    if tui:
        _serve_with_tui(
            token=token or None, host=host, port=port, config=cfg
        )
    elif token:
        _serve_gateway_headless(
            token=token, host=host, port=port, config=cfg
        )
    else:
        import uvicorn

        console.print(
            Panel(
                f"[bold]Starting Claw-ED web server[/bold]\n"
                f"[cyan]http://{host}:{port}[/cyan]\n"
                f"Dashboard:"
                f" [cyan]http://{host}:{port}/dashboard[/cyan]\n"
                f"Generate:"
                f" [cyan]http://{host}:{port}/generate[/cyan]\n"
                f"Settings:"
                f" [cyan]http://{host}:{port}/settings[/cyan]",
                title="Claw-ED Server",
                border_style="green",
            )
        )
        uvicorn.run(
            "clawed.api.server:app",
            host=host,
            port=port,
            reload=reload,
        )


def _serve_with_tui(
    token: Optional[str],
    host: str,
    port: int,
    config: Optional[AppConfig] = None,
) -> None:
    """Launch the full TUI dashboard with gateway."""
    try:
        from clawed.gateway import EduAgentGateway
        from clawed.tui import EduAgentDashboard
    except ImportError as e:
        console.print(f"[red]Missing dependency:[/red] {e}")
        console.print("\nInstall TUI support with:")
        console.print("  [cyan]pip install 'clawed[tui]'[/cyan]")
        raise typer.Exit(1)

    gateway = EduAgentGateway(config=config)

    async def _run() -> None:
        tasks = [asyncio.create_task(gateway.start())]

        # Also start web server in background
        import uvicorn

        uv_config = uvicorn.Config(
            "clawed.api.server:app",
            host=host,
            port=port,
            log_level="warning",
        )
        server = uvicorn.Server(uv_config)
        tasks.append(asyncio.create_task(server.serve()))

        # TUI blocks until quit
        dashboard = EduAgentDashboard(gateway=gateway)
        tasks.append(asyncio.create_task(dashboard.run_async()))

        done, pending = await asyncio.wait(
            tasks, return_when=asyncio.FIRST_COMPLETED
        )
        for t in pending:
            t.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        await gateway.stop()

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped.[/yellow]")


def _serve_gateway_headless(
    token: str,
    host: str,
    port: int,
    config: Optional[AppConfig] = None,
) -> None:
    """Run gateway + web server without TUI (VPS mode)."""
    # Check for existing standalone bot instance
    import os

    from clawed.tg import _BOT_LOCK

    if _BOT_LOCK.exists():
        try:
            pid = int(_BOT_LOCK.read_text(encoding="utf-8").strip())
            if pid != os.getpid():
                try:
                    os.kill(pid, 0)
                    console.print(
                        f"[yellow]A standalone Telegram bot is already running (PID {pid}).[/yellow]\n"
                        "[yellow]Starting web server only. Stop the bot first if you want serve to manage it.[/yellow]"
                    )
                    # Fall back to web-only mode
                    import uvicorn

                    uvicorn.run("clawed.api.server:app", host=host, port=port)
                    return
                except OSError:
                    pass  # Process is dead, stale lock — proceed normally
        except (ValueError, OSError):
            pass  # Invalid lock file — proceed normally

    from clawed.gateway import EduAgentGateway

    gateway = EduAgentGateway(config=config)

    console.print(
        Panel(
            f"[bold green]Claw-ED Gateway[/bold green]\n\n"
            f"Telegram: connected\n"
            f"Web: [cyan]http://{host}:{port}[/cyan]\n\n"
            f"[dim]Press Ctrl+C to stop[/dim]",
            title="Claw-ED",
            border_style="green",
        )
    )

    async def _run() -> None:
        import uvicorn

        tasks = [asyncio.create_task(gateway.start())]
        uv_config = uvicorn.Config(
            "clawed.api.server:app",
            host=host,
            port=port,
            log_level="warning",
        )
        server = uvicorn.Server(uv_config)
        tasks.append(asyncio.create_task(server.serve()))
        done, pending = await asyncio.wait(
            tasks, return_when=asyncio.FIRST_COMPLETED
        )
        for t in pending:
            t.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        await gateway.stop()

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Gateway stopped.[/yellow]")


# ── Student bot command ──────────────────────────────────────────────


@bot_app.command(name="student-bot")
def student_bot_cmd(
    token: Optional[str] = typer.Option(
        None,
        "--token",
        "-t",
        envvar="STUDENT_BOT_TOKEN",
        help="Student bot token from @BotFather",
    ),
) -> None:
    """Run the student-facing Telegram bot (separate from the teacher bot)."""
    try:
        import telegram  # noqa: F401
    except ImportError:
        console.print(
            "[red]Telegram support requires python-telegram-bot.[/red]\n"
            "Install it with: [bold]pip install 'clawed[telegram]'[/bold]"
        )
        raise typer.Exit(1)

    from clawed.student_telegram_bot import StudentTelegramBot

    if not token:
        console.print(
            "[red]Error: provide --token or set"
            " STUDENT_BOT_TOKEN[/red]"
        )
        raise typer.Exit(1)

    console.print("[green]Starting student bot...[/green]")
    try:
        StudentTelegramBot(token).start()
    except KeyboardInterrupt:
        console.print("\n[yellow]Student bot stopped.[/yellow]")
    except ImportError as e:
        console.print(f"[red]Missing dependency:[/red] {e}")
        console.print(
            "\nInstall Telegram support with:"
            "\n  [cyan]pip install"
            " 'python-telegram-bot>=20.0'[/cyan]"
        )
        raise typer.Exit(1)


# ── Bot command ──────────────────────────────────────────────────────


@bot_app.command()
def bot(
    token: Optional[str] = typer.Option(
        None,
        "--token",
        "-t",
        envvar="TELEGRAM_BOT_TOKEN",
        help="Telegram bot token from @BotFather (or set TELEGRAM_BOT_TOKEN env var)",
    ),
    data_dir: Optional[str] = typer.Option(
        None,
        "--data-dir",
        help="Data directory (default: ~/.eduagent)",  # keep
    ),
    live: bool = typer.Option(
        False,
        "--live",
        help="Show a Rich live status display while running",
    ),
    webhook_url: Optional[str] = typer.Option(
        None,
        "--webhook-url",
        envvar="EDUAGENT_WEBHOOK_URL",
        help=(
            "Public HTTPS URL for webhook mode "
            "(e.g. https://myserver.com/telegram). "
            "Omit to use polling mode (works anywhere, no public URL needed)."
        ),
    ),
    webhook_port: int = typer.Option(
        8443,
        "--webhook-port",
        help="Local port to listen on in webhook mode (default: 8443).",
    ),
    webhook_secret: Optional[str] = typer.Option(
        None,
        "--webhook-secret",
        envvar="EDUAGENT_WEBHOOK_SECRET",
        help="Secret token to verify Telegram webhook requests.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Force start even if another instance appears to be running",
    ),
    legacy: bool = typer.Option(
        False,
        "--legacy",
        help="Use the legacy python-telegram-bot backend instead of the new httpx bot",
    ),
):
    """Start the Claw-ED Telegram bot.

    \b
    Get a bot token from @BotFather on Telegram, then run:

        # Polling mode — works on any machine, no public URL needed:
        clawed bot --token YOUR_TOKEN
        export TELEGRAM_BOT_TOKEN=YOUR_TOKEN && clawed bot

        # Webhook mode (legacy only) — for VPS/server deployments:
        clawed bot --token YOUR_TOKEN --webhook-url https://myserver.com/telegram --legacy

        # With live dashboard (legacy only):
        clawed bot --token YOUR_TOKEN --live --legacy

    Save the token permanently (so you don't have to pass it every time):
        clawed config set-token YOUR_TOKEN
        clawed bot
    """
    from clawed.onboarding import check_first_run

    check_first_run()

    # Resolve token: --token flag > TELEGRAM_BOT_TOKEN env > saved config
    if not token:
        cfg = AppConfig.load()
        token = cfg.telegram_bot_token
    if not token:
        console.print(
            "[red]No bot token found.[/red]\n\n"
            "Provide one of:\n"
            "  1. [cyan]clawed bot --token YOUR_TOKEN[/cyan]\n"
            "  2. [cyan]export"
            " TELEGRAM_BOT_TOKEN=YOUR_TOKEN[/cyan]\n"
            "  3. [cyan]clawed config set-token"
            " YOUR_TOKEN[/cyan]  (saves permanently)\n\n"
            "Get a token from @BotFather on Telegram."
        )
        raise typer.Exit(1)

    data_path = (
        Path(data_dir).expanduser().resolve() if data_dir else None
    )

    # Legacy mode: use python-telegram-bot (supports webhooks, live display)
    if legacy or live or webhook_url:
        console.print(
            "[yellow]Note: --legacy mode is deprecated and will be removed in v0.5. "
            "The default bot (without --legacy) is recommended.[/yellow]\n"
        )
        try:
            import telegram  # noqa: F401
        except ImportError:
            console.print(
                "[red]Legacy bot mode requires python-telegram-bot.[/red]\n"
                "Install it with: [bold]pip install 'clawed[telegram-legacy]'[/bold]\n"
                "Or use the default bot (no --legacy flag) which needs no extra deps."
            )
            raise typer.Exit(1)

        from clawed.telegram_bot import run_bot as run_legacy_bot

        if live:
            _bot_with_live_display(token=token, data_path=data_path)
        else:
            mode_line = (
                f"Webhook: [cyan]{webhook_url}[/cyan] (port {webhook_port})"
                if webhook_url
                else "Mode: polling (legacy)"
            )
            console.print(
                Panel(
                    f"[bold green]Claw-ED Telegram Bot (legacy)[/bold green]\n\n"
                    f"Starting bot...\n"
                    f"Data directory:"
                    f" {data_path or Path.home() / '.eduagent'}\n"
                    f"{mode_line}\n\n"
                    f"[dim]Press Ctrl+C to stop[/dim]",
                    title="Claw-ED",
                    border_style="green",
                )
            )

            try:
                run_legacy_bot(
                    token=token,
                    data_dir=data_path,
                    webhook_url=webhook_url,
                    webhook_port=webhook_port,
                    webhook_secret=webhook_secret or None,
                    force=force,
                )
            except RuntimeError as e:
                console.print(f"[red]{e}[/red]")
                raise typer.Exit(1)
            except KeyboardInterrupt:
                console.print("\n[yellow]Bot stopped.[/yellow]")
            except ImportError as e:
                console.print(f"[red]Missing dependency:[/red] {e}")
                console.print("\nInstall legacy Telegram support with:")
                console.print(
                    "  [cyan]pip install"
                    " 'clawed[telegram-legacy]'[/cyan]"
                )
                raise typer.Exit(1)
        return

    # Default mode: new lightweight httpx bot (no extra deps needed)
    from clawed.tg import run_bot as run_new_bot

    console.print(
        Panel(
            f"[bold green]Claw-ED Telegram Bot[/bold green]\n\n"
            f"Starting bot...\n"
            f"Data directory:"
            f" {data_path or Path.home() / '.eduagent'}\n"
            f"Mode: polling (httpx)\n\n"
            f"[dim]Press Ctrl+C to stop[/dim]",
            title="Claw-ED",
            border_style="green",
        )
    )

    try:
        run_new_bot(
            token=token,
            data_dir=data_path,
            force=force,
        )
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Bot stopped.[/yellow]")


def _bot_with_live_display(
    token: str, data_path: Optional[Path] = None
) -> None:
    """Run the Telegram bot with a Rich Live status panel."""
    import asyncio
    import time

    from rich.live import Live

    from clawed.gateway import EduAgentGateway

    gateway = EduAgentGateway()
    start_time = time.monotonic()

    def _make_display() -> Panel:
        elapsed = int(time.monotonic() - start_time)
        h, remainder = divmod(elapsed, 3600)
        m, s = divmod(remainder, 60)
        stats = gateway._gateway_stats
        sessions = len(gateway.active_sessions)
        return Panel(
            f"[bold green]Claw-ED Bot[/bold green]"
            f"  [dim]running[/dim]\n\n"
            f"  Messages:     {stats.messages_today}\n"
            f"  Generations:  {stats.generations_today}\n"
            f"  Errors:       {stats.errors_today}\n"
            f"  Sessions:     {sessions}\n"
            f"  Uptime:       {h}:{m:02d}:{s:02d}\n\n"
            f"[dim]Press Ctrl+C to stop[/dim]",
            title="Claw-ED",
            border_style="green",
        )

    try:
        with Live(
            _make_display(),
            console=console,
            refresh_per_second=1,
        ) as live_display:

            async def _run_with_refresh() -> None:
                await gateway.start()
                while True:
                    live_display.update(_make_display())
                    await asyncio.sleep(1)

            asyncio.run(_run_with_refresh())
    except KeyboardInterrupt:
        console.print("\n[yellow]Bot stopped.[/yellow]")
