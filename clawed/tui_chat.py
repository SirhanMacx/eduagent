"""Claw-ED TUI Chat — full-screen terminal chat interface built with Textual.

Launch:
    clawed tui                      # interactive chat in terminal
    clawed tui --id my-teacher      # with custom teacher ID

A proper chat interface for teachers who prefer the terminal over Telegram
or the web UI. Routes all messages through the same Gateway.
"""

from __future__ import annotations

try:
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import VerticalScroll
    from textual.widgets import Footer, Input, Static
except ImportError:
    raise ImportError(
        "textual is required for the TUI chat.\n"
        "Install with: pip install 'clawed[tui]'\n"
        "Or: pip install textual"
    )

from clawed.gateway import Gateway
from clawed.state import TeacherSession


class ChatMessage(Static):
    """A single chat message bubble."""

    DEFAULT_CSS = """
    ChatMessage {
        margin: 0 0 1 0;
        padding: 0 2;
    }
    ChatMessage.user {
        margin-left: 8;
        color: $text;
    }
    ChatMessage.assistant {
        margin-right: 8;
        color: $text;
    }
    """

    def __init__(self, role: str, text: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._role = role
        self._text = text
        self.add_class(role)

    def compose(self) -> ComposeResult:
        if self._role == "user":
            label = "[bold blue]You[/bold blue]"
        else:
            label = "[bold green]Claw-ED[/bold green]"
        yield Static(f"{label}\n{self._text}")


class ThinkingIndicator(Static):
    """Animated thinking indicator."""

    DEFAULT_CSS = """
    ThinkingIndicator {
        margin: 0 0 1 0;
        padding: 0 2;
        color: $text-muted;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._frame = 0
        self._frames = ["Thinking.", "Thinking..", "Thinking..."]

    def on_mount(self) -> None:
        self.set_interval(0.4, self._animate)

    def _animate(self) -> None:
        self._frame = (self._frame + 1) % len(self._frames)
        self.update(f"[bold green]Claw-ED[/bold green]  [dim]{self._frames[self._frame]}[/dim]")


class ClawEDChat(App):
    """Claw-ED TUI — interactive chat in the terminal."""

    TITLE = "Claw-ED Chat"

    CSS = """
    Screen {
        layout: vertical;
        background: $surface;
    }
    #title-bar {
        height: 1;
        background: $accent;
        color: $text;
        text-align: center;
        text-style: bold;
    }
    #status-bar {
        height: 1;
        background: $panel;
        color: $text-muted;
        padding: 0 2;
    }
    #chat-area {
        height: 1fr;
        border: solid $primary;
        padding: 1 0;
    }
    #input-box {
        dock: bottom;
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "quit", "Quit", priority=True),
        Binding("ctrl+l", "clear_chat", "Clear chat"),
    ]

    def __init__(self, teacher_id: str = "local-teacher", **kwargs) -> None:
        super().__init__(**kwargs)
        self._teacher_id = teacher_id
        self._gateway = Gateway()
        self._session = TeacherSession.load(teacher_id)

    def compose(self) -> ComposeResult:
        yield Static("  [bold]Claw-ED Chat[/bold]", id="title-bar")
        status = self._build_status()
        yield Static(status, id="status-bar")
        yield VerticalScroll(id="chat-area")
        yield Input(placeholder="Type a message... (Esc to quit)", id="input-box")
        yield Footer()

    def _build_status(self) -> str:
        name = self._session.persona.name if self._session.persona else self._teacher_id
        provider = self._gateway.config.provider.value.title()
        return f"  {name}  |  {provider}  |  /quit to exit, /clear to reset"

    async def on_mount(self) -> None:
        self.query_one("#input-box", Input).focus()
        if self._session.is_new:
            # Auto-trigger onboarding greeting
            await self._send_message("hello", auto=True)
        else:
            chat_area = self.query_one("#chat-area", VerticalScroll)
            welcome = ChatMessage(
                "assistant",
                "Welcome back! Type anything to get started.\n"
                "Try: *plan a unit on photosynthesis* or *generate a quiz*",
            )
            await chat_area.mount(welcome)
            chat_area.scroll_end(animate=False)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return

        event.input.value = ""

        # Built-in commands
        if text.lower() in ("/quit", "/exit", "quit", "exit"):
            self.exit()
            return

        if text.lower() == "/clear":
            self._session = TeacherSession(teacher_id=self._teacher_id)
            self._session.save()
            chat_area = self.query_one("#chat-area", VerticalScroll)
            await chat_area.remove_children()
            self.notify("Session cleared")
            return

        await self._send_message(text)

    async def _send_message(self, text: str, auto: bool = False) -> None:
        chat_area = self.query_one("#chat-area", VerticalScroll)
        input_box = self.query_one("#input-box", Input)

        # Show user message (unless auto-triggered greeting)
        if not auto:
            user_msg = ChatMessage("user", text)
            await chat_area.mount(user_msg)
            chat_area.scroll_end(animate=False)

        # Show thinking indicator
        thinking = ThinkingIndicator(id="thinking")
        await chat_area.mount(thinking)
        chat_area.scroll_end(animate=False)
        input_box.disabled = True

        # Send to gateway
        try:
            result = await self._gateway.handle(text, self._teacher_id)
            response_text = result.text
        except Exception as e:
            response_text = f"Something went wrong: {e}"

        # Remove thinking, show response
        await thinking.remove()
        assistant_msg = ChatMessage("assistant", response_text)
        await chat_area.mount(assistant_msg)

        # Show file outputs
        if result and result.files:
            for f in result.files:
                file_msg = ChatMessage("assistant", f"[green]File saved:[/green] {f}")
                await chat_area.mount(file_msg)

        # Show button options as text
        if result and (result.button_rows or result.buttons):
            rows = result.button_rows or [result.buttons]
            options = [b.label for row in rows for b in row]
            opts_msg = ChatMessage("assistant", f"[dim]Options: {' | '.join(options)}[/dim]")
            await chat_area.mount(opts_msg)

        chat_area.scroll_end(animate=False)
        input_box.disabled = False
        input_box.focus()

    def action_clear_chat(self) -> None:
        """Clear chat and reset session via keybinding."""
        self._session = TeacherSession(teacher_id=self._teacher_id)
        self._session.save()
        chat_area = self.query_one("#chat-area", VerticalScroll)
        chat_area.remove_children()
        self.notify("Session cleared")


def run_tui_chat(teacher_id: str = "local-teacher") -> None:
    """Entry point — run the TUI chat app."""
    app = ClawEDChat(teacher_id=teacher_id)
    app.run()
