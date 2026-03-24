"""Allow running with: python -m clawed"""
import sys


def main():
    try:
        # Reconfigure stdout/stderr to UTF-8 on all platforms (Python 3.7+)
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

    # Map known errors to friendly messages
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
