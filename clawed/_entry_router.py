"""Claw-ED entry point router.

Routes to the TypeScript Ink TUI (if Node.js available) or falls back
to the Python typer CLI. The teacher never needs to know about this
routing — they just run `clawed`.

Usage:
    clawed                  → Interactive mode (Ink TUI or Python REPL)
    clawed lesson "Topic"   → Direct command (routes to Python --json if Ink TUI)
    clawed --python ...     → Force Python CLI (skip Node.js check)
    clawed daemon start     → Start background Telegram daemon
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def _find_bundled_cli_js() -> str | None:
    """Find the pre-built cli.js bundled in the package."""
    # Check package data directory
    pkg_dir = Path(__file__).parent
    cli_js = pkg_dir / "_cli_bundle" / "cli.js"
    if cli_js.exists():
        return str(cli_js)

    # Check if we're in a dev environment with the cli/ directory
    repo_root = pkg_dir.parent
    # Build output goes to cli/dist/cli.js
    for dev_path in [
        repo_root / "cli" / "dist" / "cli.js",
        repo_root / "cli" / "source" / "cli.js",
    ]:
        if dev_path.exists():
            return str(dev_path)

    return None


def _find_daemon_entry() -> str | None:
    """Find the daemon entry point."""
    pkg_dir = Path(__file__).parent
    repo_root = pkg_dir.parent

    # Dev environment
    daemon_ts = repo_root / "daemon" / "index.ts"
    daemon_js = repo_root / "daemon" / "dist" / "index.js"

    if daemon_js.exists():
        return str(daemon_js)
    if daemon_ts.exists():
        # Use ts-node or tsx for dev mode
        return str(daemon_ts)

    # Bundled daemon
    bundled = pkg_dir / "_cli_bundle" / "daemon.js"
    if bundled.exists():
        return str(bundled)

    return None


def _show_node_notice() -> None:
    """Show branded startup with Ed mascot when running in Python-only mode."""
    from clawed import __version__
    print()
    print("         \033[32m🎓\033[0m")
    print("    \033[31m🦞\033[0m  \033[31m████████\033[0m  \033[31m🦞\033[0m")
    print("   \033[31m██ ██████████ ██\033[0m")
    print("   \033[31m██\033[0m \033[37m◕\033[0m    \033[37m◕\033[0m \033[31m██\033[0m")
    print("   \033[31m██\033[0m  \033[37m╰──╯\033[0m  \033[31m██\033[0m")
    print("    \033[31m██████████\033[0m")
    print("     \033[33m┌─ Ed ─┐\033[0m")
    print()
    print(f"  \033[33mC L A W - E D  v{__version__}\033[0m")
    print("  \033[32mYour AI co-teacher\033[0m")
    print()
    print("  \033[90mRunning in Python mode. Install Node.js for the full TUI.\033[0m")
    print()


def _check_telegram_token() -> bool:
    """Return True if a Telegram bot token is configured, False otherwise.

    Reads ~/.eduagent/config.json directly — no clawed package imports.
    """
    import json

    config_path = Path.home() / ".eduagent" / "config.json"
    if not config_path.exists():
        return False
    try:
        data = json.loads(config_path.read_text())
        token = data.get("telegram_bot_token", "")
        return bool(token and token.strip())
    except (json.JSONDecodeError, OSError):
        return False


def _resolve_key_for_provider(provider: str, config: dict) -> str | None:
    """Find the best API key for a provider without importing heavy modules."""
    import json

    # 1. Already in env? User knows what they're doing — skip.
    env_map = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "google": "GOOGLE_API_KEY",
        "ollama": "OLLAMA_API_KEY",
    }
    env_var = env_map.get(provider)
    if env_var and os.environ.get(env_var):
        return os.environ[env_var]

    # 2. Anthropic: try Claude Code OAuth credentials
    if provider == "anthropic":
        for cred_path in [
            Path.home() / ".claude" / ".credentials.json",
            Path.home() / ".claude" / "credentials.json",
        ]:
            if cred_path.exists():
                try:
                    creds = json.loads(cred_path.read_text())
                    token = creds.get("claudeAiOauth", {}).get("accessToken")
                    if token:
                        return token
                except (json.JSONDecodeError, OSError):
                    pass

    # 3. Keyring
    try:
        import keyring
        val = keyring.get_password("clawed", f"{provider}_api_key")
        if val:
            return val
    except Exception:
        pass

    # 4. secrets.json
    secrets_path = Path.home() / ".eduagent" / "secrets.json"
    if secrets_path.exists():
        try:
            secrets = json.loads(secrets_path.read_text())
            val = secrets.get(f"{provider}_api_key")
            if val:
                return val
        except (json.JSONDecodeError, OSError):
            pass

    # 5. Inline in config (e.g. ollama_api_key field)
    key_field = f"{provider}_api_key"
    val = config.get(key_field)
    if val and val != "ollama-local":  # Skip sentinel value
        return val

    return None


def _inject_config_env() -> None:
    """Inject teacher's config into env vars so the Node CLI can authenticate.

    Reads ~/.eduagent/config.json and resolves the API key for the active
    provider, then sets the appropriate env var (ANTHROPIC_API_KEY, etc.)
    so the TS CLI picks it up instead of falling back to settings.json.

    Never crashes — a failure here just means the TS CLI tries its own
    auth flow (which may or may not work).
    """
    import json

    config_path = Path.home() / ".eduagent" / "config.json"
    if not config_path.exists():
        return  # First run — let onboarding handle it

    try:
        config = json.loads(config_path.read_text())
    except (json.JSONDecodeError, OSError):
        return

    provider = config.get("provider", "anthropic")
    os.environ.setdefault("CLAWED_PROVIDER", provider)

    # Resolve API key for the active provider
    key = _resolve_key_for_provider(provider, config)
    if key:
        env_var_map = {
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
            "google": "GOOGLE_API_KEY",
            "ollama": "OLLAMA_API_KEY",
        }
        env_var = env_var_map.get(provider)
        if env_var:
            os.environ.setdefault(env_var, key)
        # Google needs both GOOGLE_API_KEY and GEMINI_API_KEY
        if provider == "google":
            os.environ.setdefault("GEMINI_API_KEY", key)

    # Ollama base URL so the TS bridge knows where to connect
    if provider == "ollama":
        base = config.get("ollama_base_url", "")
        if base:
            os.environ.setdefault("OLLAMA_BASE_URL", base)


def _handle_daemon(args: list[str]) -> None:
    """Route daemon commands to the Node.js daemon process."""
    node = shutil.which("node")
    daemon_entry = _find_daemon_entry()

    if not node:
        print("The Telegram bot requires Node.js. Install from https://nodejs.org and try again.")
        sys.exit(1)

    if not daemon_entry:
        print("Telegram bot files not found. Try reinstalling: pip install --force-reinstall clawed")
        sys.exit(1)

    # Pre-check: Telegram token must be configured before spawning the daemon
    if not _check_telegram_token():
        print(
            "\nNo Telegram bot token found.\n"
            "\n"
            "To set up Telegram:\n"
            "1. Open Telegram and message @BotFather\n"
            "2. Send /newbot and follow the steps\n"
            "3. Copy the bot token\n"
            "4. Run: clawed config set-token --telegram YOUR_TOKEN\n"
        )
        sys.exit(0)

    # Check if it's a .ts file (dev mode) — use tsx or ts-node
    if daemon_entry.endswith(".ts"):
        tsx = shutil.which("tsx")
        if tsx:
            result = subprocess.run([tsx, daemon_entry] + args)
        else:
            result = subprocess.run([node, "--loader", "ts-node/esm", daemon_entry] + args)
    else:
        result = subprocess.run([node, daemon_entry] + args)

    sys.exit(result.returncode)


def main() -> None:
    """Entry point for the `clawed` command.

    Currently routes to the Python CLI for all interactive use.
    The TypeScript Ink TUI is available for --version only.
    """
    args = sys.argv[1:]

    # Route daemon commands to the Node.js daemon
    if args and args[0] == "daemon":
        _handle_daemon(args[1:])
        return

    # Allow forcing Python CLI
    if "--python" in args:
        args.remove("--python")
        sys.argv = [sys.argv[0]] + args

    # Use the Ink TUI for interactive mode — the full Claw-ED TUI
    node = shutil.which("node")
    cli_js = _find_bundled_cli_js()

    if node and cli_js:
        os.environ['CLAWED_MODE'] = '1'
        try:
            _inject_config_env()
        except Exception:
            pass  # Never block startup
        result = subprocess.run([node, cli_js] + args)
        sys.exit(result.returncode)
    else:
        if not args:
            _show_node_notice()
        _run_python_cli()


def _run_python_cli() -> None:
    """Run the Python typer CLI (fallback or forced mode)."""
    from clawed.cli import app
    app()


if __name__ == "__main__":
    main()
