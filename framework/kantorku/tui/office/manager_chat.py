"""
ManagerChatPanel — Left panel chat interface with the Manager (Conductor).

Displays a conversation thread between the user and the Manager with
role-based styling, natural language action parsing, and contract
action buttons.

Layout:
    ┌──────────────────────────────────────┐
    │  MANAGER CHAT            [⚡DISRUPT] │
    │  ─────────────────────────────────── │
    │                                      │
    │  Manager: I understand you need...   │
    │                                      │
    │  You: yes, that's right              │
    │                                      │
    │  Manager: Here's the contract...     │
    │                                      │
    │  ─────────────────────────────────── │
    │  [✓ ACCEPT]  [✏ REVISE]  [⚡DISRUPT]│
    │  ─────────────────────────────────── │
    │  ⣾ Manager thinking...               │
    │  ─────────────────────────────────── │
    │  > Type your message...     [Send]   │
    └──────────────────────────────────────┘

Natural Language Actions:
    - "yes"/"ok"/"accept" → Accept contract
    - "no"/"revise"/"change" → Revise contract
    - "stop"/"halt"/"interrupt" → Interrupt work
"""

from __future__ import annotations

import re
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, Input, Static

from rich.console import Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from kantorku.tui.themes import (
    BRAILLE_SPINNER,
    CONTRACT_STATE_COLORS,
    KANTORKU_THEME,
)

# ── Natural Language Action Patterns ──────────────────────────────────

ACCEPT_PATTERNS = re.compile(
    r"^(yes|yeah|yep|ok|okay|accept|approve|go ahead|go for it|do it|"
    r"let'?s go|sure|sounds good|perfect|lg|lfg|ship it|"
    r"looks good|agree|confirmed|confirm|proceed|execute)\s*[!.!]*$",
    re.IGNORECASE,
)

REVISE_PATTERNS = re.compile(
    r"^(no|nope|nah|revise|change|modify|update|alter|redo|reject|deny|"
    r"not quite|not really|i want|i need|i prefer|instead|"
    r"could you|can you|please change|please update|but)\b",
    re.IGNORECASE,
)

INTERRUPT_PATTERNS = re.compile(
    r"^(stop|halt|pause|wait|hold on|hold up|interrupt|disrupt|break|cancel)\b",
    re.IGNORECASE,
)


# ── CSS ────────────────────────────────────────────────────────────────

_CSS = """
ManagerChatPanel {
    layout: vertical;
    height: 1fr;
}

#chat-header {
    height: 1;
    padding: 0 1;
    color: $primary;
    text-style: bold;
    background: $primary 8%;
    border-bottom: tall $primary 30%;
}

#chat-log {
    height: 1fr;
    scrollbar-size: 1 1;
    padding: 0 1;
}

#chat-actions {
    height: auto;
    dock: bottom;
    padding: 0 1;
    background: $surface;
    border-top: tall $primary 20%;
    layout: horizontal;
    gap: 1;
}

#thinking-indicator-chat {
    height: auto;
    dock: bottom;
    padding: 0 1;
    color: yellow;
    text-style: bold;
    display: none;
}

#chat-input-bar {
    height: auto;
    dock: bottom;
    padding: 0 1;
    background: $surface;
    border-top: tall $primary 20%;
    layout: horizontal;
}

#chat-input {
    width: 1fr;
}

#chat-send-btn {
    min-width: 6;
    background: $primary 15%;
    color: $primary;
    text-style: bold;
    border: tall $primary 30%;
}

#chat-send-btn:hover {
    background: $primary 30%;
    color: $text;
}

#accept-action-btn {
    background: $success 15%;
    color: $success;
    text-style: bold;
    border: tall $success;
}

#accept-action-btn:hover {
    background: $success 30%;
}

#revise-action-btn {
    background: $warning 15%;
    color: $warning;
    text-style: bold;
    border: tall $warning;
}

#revise-action-btn:hover {
    background: $warning 30%;
}

#disrupt-action-btn {
    background: $error 15%;
    color: $error;
    text-style: bold;
    border: tall $error;
}

#disrupt-action-btn:hover {
    background: $error 30%;
}
"""


class ManagerChatPanel(Static):
    """Left panel — chat with the Manager (Conductor).

    Displays messages with role-based styling:
    - manager: blue/bold
    - user: green
    - system: dim

    Provides contract action buttons: Accept, Revise, Interrupt.
    Supports natural language action parsing.
    Auto-scrolls to bottom on new messages.
    Shows a braille spinner while waiting for Manager response.

    Messages:
        UserMessage: Emitted when user sends a message
        ActionRequested: Emitted when a contract action is detected
    """

    CSS = _CSS

    # ── Messages ───────────────────────────────────────────────────

    class UserMessage(Message):
        """Posted when the user sends a chat message."""

        def __init__(self, text: str) -> None:
            super().__init__()
            self.text: str = text

    class ActionRequested(Message):
        """Posted when a contract action is requested (accept/revise/interrupt)."""

        def __init__(self, action: str, feedback: str = "") -> None:
            super().__init__()
            self.action: str = action  # "accept", "revise", "interrupt"
            self.feedback: str = feedback

    # ── Reactives ──────────────────────────────────────────────────

    contract_state: reactive[str] = reactive("idle")
    _is_thinking: reactive[bool] = reactive(False)

    # ── Init ───────────────────────────────────────────────────────

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._messages: list[dict[str, Any]] = []
        self._spinner_index: int = 0
        self._spinner_timer: Any = None
        self._input_history: list[str] = []
        self._history_index: int = -1

    # ── Compose ────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Static("MANAGER", id="chat-header")
        with VerticalScroll(id="chat-log"):
            yield Static(id="chat-log-content")
        yield Static("", id="thinking-indicator-chat")
        with Horizontal(id="chat-actions"):
            yield Button("\u2713 Accept", id="accept-action-btn")
            yield Button("\u270f Revise", id="revise-action-btn")
            yield Button("\u26a1 Disrupt", id="disrupt-action-btn")
        with Horizontal(id="chat-input-bar"):
            yield Input(
                placeholder="Type your message...",
                id="chat-input",
            )
            yield Button("Send", id="chat-send-btn")

    # ── Lifecycle ──────────────────────────────────────────────────

    def on_mount(self) -> None:
        """Initialize display and focus input."""
        self._render_messages()
        self._update_action_buttons()
        try:
            chat_input = self.query_one("#chat-input", Input)
            chat_input.focus()
        except Exception:
            pass

    # ── Public API ─────────────────────────────────────────────────

    def add_manager_message(self, content: str) -> None:
        """Add a message from the Manager to the chat."""
        self._messages.append({
            "role": "manager",
            "content": content,
        })
        self._render_messages()
        self._scroll_to_bottom()

    def add_user_message(self, content: str) -> None:
        """Add a message from the user to the chat."""
        self._messages.append({
            "role": "user",
            "content": content,
        })
        self._render_messages()
        self._scroll_to_bottom()

    def add_system_message(self, content: str, style: str = "dim") -> None:
        """Add a system message to the chat."""
        self._messages.append({
            "role": "system",
            "content": content,
            "style": style,
        })
        self._render_messages()
        self._scroll_to_bottom()

    def start_thinking(self, message: str = "Manager thinking") -> None:
        """Show the braille spinner while Manager is processing."""
        self._is_thinking = True
        self._thinking_message = message
        self._spinner_index = 0
        try:
            indicator = self.query_one("#thinking-indicator-chat", Static)
            indicator.display = True
            self._update_spinner()
            if self._spinner_timer is not None:
                self._spinner_timer.stop()
            self._spinner_timer = self.set_interval(0.25, self._tick_spinner)
        except Exception:
            pass

    def stop_thinking(self) -> None:
        """Stop the thinking spinner."""
        self._is_thinking = False
        try:
            indicator = self.query_one("#thinking-indicator-chat", Static)
            indicator.display = False
            if self._spinner_timer is not None:
                self._spinner_timer.stop()
                self._spinner_timer = None
        except Exception:
            pass

    def clear_chat(self) -> None:
        """Clear all chat messages."""
        self._messages.clear()
        self._render_messages()

    # ── Reactive Watchers ──────────────────────────────────────────

    def watch_contract_state(self, state: str) -> None:
        """Update action buttons when contract state changes."""
        self._update_action_buttons()

    # ── Event Handlers ─────────────────────────────────────────────

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in the chat input."""
        if event.input.id != "chat-input":
            return

        text = event.value.strip()
        if not text:
            return

        event.input.value = ""

        # Save to history
        self._input_history.append(text)
        self._history_index = len(self._input_history)

        # Check for slash commands
        if text.startswith("/"):
            self.post_message(self.UserMessage(text))
            return

        # Check for natural language actions
        action = self._parse_nl_action(text)
        if action:
            self.add_user_message(text)
            if action == "accept":
                self.post_message(self.ActionRequested("accept"))
            elif action == "revise":
                # Extract feedback from the text (everything after the action word)
                feedback = text
                self.post_message(self.ActionRequested("revise", feedback))
            elif action == "interrupt":
                self.post_message(self.ActionRequested("interrupt"))
        else:
            # Regular chat message
            self.add_user_message(text)
            self.post_message(self.UserMessage(text))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        btn_id = event.button.id or ""

        if btn_id == "chat-send-btn":
            try:
                chat_input = self.query_one("#chat-input", Input)
                text = chat_input.value.strip()
                if text:
                    chat_input.value = ""
                    self._input_history.append(text)
                    self._history_index = len(self._input_history)

                    action = self._parse_nl_action(text)
                    if action:
                        self.add_user_message(text)
                        if action == "accept":
                            self.post_message(self.ActionRequested("accept"))
                        elif action == "revise":
                            self.post_message(self.ActionRequested("revise", text))
                        elif action == "interrupt":
                            self.post_message(self.ActionRequested("interrupt"))
                    else:
                        self.add_user_message(text)
                        self.post_message(self.UserMessage(text))
            except Exception:
                pass

        elif btn_id == "accept-action-btn":
            self.post_message(self.ActionRequested("accept"))

        elif btn_id == "revise-action-btn":
            self.post_message(self.ActionRequested("revise"))

        elif btn_id == "disrupt-action-btn":
            self.post_message(self.ActionRequested("interrupt"))

    def key_up(self) -> None:
        """Navigate input history upward."""
        if self._history_index > 0:
            self._history_index -= 1
            self._set_input_from_history()

    def key_down(self) -> None:
        """Navigate input history downward."""
        if self._history_index < len(self._input_history) - 1:
            self._history_index += 1
            self._set_input_from_history()
        elif self._history_index == len(self._input_history) - 1:
            self._history_index = len(self._input_history)
            try:
                chat_input = self.query_one("#chat-input", Input)
                chat_input.value = ""
            except Exception:
                pass

    # ── Internal ───────────────────────────────────────────────────

    def _parse_nl_action(self, text: str) -> str | None:
        """Parse natural language input for contract actions."""
        stripped = text.strip()
        if not stripped:
            return None

        state = self.contract_state

        if state in ("contract_presented", "awaiting_revision"):
            if ACCEPT_PATTERNS.match(stripped):
                return "accept"
            if REVISE_PATTERNS.match(stripped):
                return "revise"

        if state == "working":
            if INTERRUPT_PATTERNS.match(stripped):
                return "interrupt"

        return None

    def _update_action_buttons(self) -> None:
        """Enable/disable action buttons based on contract state."""
        state = self.contract_state

        try:
            accept_btn = self.query_one("#accept-action-btn", Button)
            revise_btn = self.query_one("#revise-action-btn", Button)
            disrupt_btn = self.query_one("#disrupt-action-btn", Button)

            # Accept/Revise only visible when contract is presented or awaiting revision
            can_accept = state in ("contract_presented", "awaiting_revision")
            can_revise = state in ("contract_presented", "awaiting_revision")
            can_disrupt = state in ("working", "verifying")

            accept_btn.disabled = not can_accept
            revise_btn.disabled = not can_revise
            disrupt_btn.disabled = not can_disrupt

            accept_btn.display = can_accept or state == "idle"
            revise_btn.display = can_revise or state == "idle"
            disrupt_btn.display = can_disrupt or state == "idle"

        except Exception:
            pass

    def _render_messages(self) -> None:
        """Render the chat conversation with role-based styling."""
        try:
            log_content = self.query_one("#chat-log-content", Static)
        except Exception:
            return

        if not self._messages:
            log_content.update(
                Panel(
                    "[dim]Chat with the Manager to start.\n\n"
                    "Just type what you need\n"
                    "and press Enter.[/dim]",
                    border_style="dim",
                    padding=(0, 1),
                )
            )
            return

        parts: list[Any] = []

        for msg in self._messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            style = msg.get("style", "dim")

            if role == "manager":
                parts.append(Text.from_markup(
                    f"[bold blue]Manager:[/bold blue] {content}"
                ))
                parts.append(Text.from_markup(""))

            elif role == "user":
                parts.append(Text.from_markup(
                    f"[green]You:[/green] {content}"
                ))
                parts.append(Text.from_markup(""))

            elif role == "system":
                parts.append(Text.from_markup(
                    f"[{style}]{content}[/{style}]"
                ))
                parts.append(Text.from_markup(""))

        # Action hints based on state
        state = self.contract_state
        if state == "contract_presented":
            parts.append(Text.from_markup(
                "[bold green]\u25b8 Type 'yes'/'ok' or click Accept[/bold green]\n"
                "[bold yellow]\u25b8 Type feedback or click Revise[/bold yellow]"
            ))
        elif state == "awaiting_revision":
            parts.append(Text.from_markup(
                "[bold yellow]\u25b8 Write your revision feedback...[/bold yellow]"
            ))
        elif state == "working":
            parts.append(Text.from_markup(
                "[bold yellow]\u25b8 Type 'stop' or click Disrupt to pause[/bold yellow]"
            ))

        log_content.update(Group(*parts))

    def _scroll_to_bottom(self) -> None:
        """Auto-scroll the chat log to the bottom."""
        try:
            log = self.query_one("#chat-log", VerticalScroll)
            log.scroll_end(animate=False)
        except Exception:
            pass

    def _tick_spinner(self) -> None:
        """Advance the braille spinner one step."""
        self._spinner_index = (self._spinner_index + 1) % len(BRAILLE_SPINNER)
        self._update_spinner()

    def _update_spinner(self) -> None:
        """Update the spinner display."""
        char = BRAILLE_SPINNER[self._spinner_index]
        message = getattr(self, "_thinking_message", "Manager thinking")
        try:
            indicator = self.query_one("#thinking-indicator-chat", Static)
            indicator.update(f"{char} {message}...")
        except Exception:
            pass

    def _set_input_from_history(self) -> None:
        """Set the input value from history."""
        if 0 <= self._history_index < len(self._input_history):
            try:
                chat_input = self.query_one("#chat-input", Input)
                chat_input.value = self._input_history[self._history_index]
            except Exception:
                pass
