"""
KantorKu TUI App — 3-Panel Chat-Driven Office Interface.

The central TUI for coders, providing a natural office workflow:
- Left Panel:   Chat with the Manager (Conductor) + Disrupt button
- Center Panel: Tabbed views — Workers, Briefing, DAG, Events
- Right Panel:  Contract display + Accept/Revise BUTTONS

Primary interaction is CHAT — type naturally, Manager handles the rest.
Slash commands still work as secondary tools — type /help for list.

Contract Flow:
    When a contract is presented in the RIGHT panel:
      - Click ACCEPT → Contract is finalized and displayed as ACCEPTED
      - Click REVISE → Enter revision mode: write feedback →
        Manager brainstorms with workers → new contract presented
      - Or type naturally: "yes"/"ok"/"accept" → Accept
                           "revise"/"change X" → Revise with feedback

Supports two modes:
1. Remote: Connect to a running kantorku server via WebSocket
2. Embedded: Run the Office directly in-process (no server needed)
"""

from __future__ import annotations

import asyncio
import json
import re
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.command import CommandPalette, Hit, Provider
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    RichLog,
    Static,
    TabbedContent,
    TabPane,
    TextArea,
    Collapsible,
)
from textual.worker import WorkerCancelled

from rich.console import Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from kantorku.tui.connection import OfficeConnection, ConnectionState
from kantorku.tui.themes import (
    KANTORKU_THEME,
    KANTORKU_THEMES,
    get_theme,
    list_themes,
    SQUAD_COLORS,
    STATUS_ICONS,
    STATUS_COLORS,
    EVENT_STYLES,
    CONTRACT_STATE_COLORS,
    PANEL_STATE_ICONS,
    WORKERS_PHASE_STYLES,
    BRAILLE_SPINNER,
)
from kantorku.tui.markdown_renderer import (
    render_markdown,
    render_code,
    render_contract_summary,
    render_task_result,
)
from kantorku.tui.commands import handle_slash_command, COMMANDS


# ── Natural Language Action Parser ──────────────────────────────────

# Patterns that map to contract actions
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

# ── Filter category mappings ────────────────────────────────────────

FILTER_CATEGORIES: dict[str, set[str]] = {
    "tasks": {
        "task_assigned", "task_started", "task_done",
        "task_failed", "task_recovered", "task_timeout",
    },
    "briefing": {
        "briefing_opened", "plan_drafted", "plan_revised",
        "worker_speak_up", "worker_dm", "worker_broadcast",
    },
    "errors": {
        "error_logged", "circuit_open", "rate_limit_hit", "cost_warning",
    },
    "llm": {
        "llm_stream_start", "llm_stream_chunk", "llm_stream_done",
    },
}


# ── Contract State Enum ─────────────────────────────────────────────


class ContractState(str, Enum):
    """All contract lifecycle states.

    Extends str so all string comparisons still work:
        ContractState.IDLE == "idle"  →  True
    """
    IDLE = "idle"
    MANAGER_THINKING = "manager_thinking"
    CLARIFYING = "clarifying"
    CONTRACT_PRESENTED = "contract_presented"
    AWAITING_REVISION = "awaiting_revision"
    TEAM_REVIEW = "team_review"
    TODO_REVIEW = "todo_review"
    CLIENT_FEEDBACK = "client_feedback"
    WORKING = "working"
    VERIFYING = "verifying"
    ACCEPTED = "accepted"
    DONE = "done"
    FAILED = "failed"


def parse_nl_action(text: str, contract_state: str) -> str | None:
    """
    Parse natural language input to detect contract actions.

    Returns:
        "accept" if user wants to accept the contract
        "revise" if user wants to revise the contract (remaining text = feedback)
        "interrupt" if user wants to interrupt work
        None if no action detected (regular chat message)
    """
    stripped = text.strip()
    if not stripped:
        return None

    # Only parse actions when relevant
    if contract_state in (ContractState.CONTRACT_PRESENTED, ContractState.AWAITING_REVISION):
        if ACCEPT_PATTERNS.match(stripped):
            return "accept"
        if REVISE_PATTERNS.match(stripped):
            return "revise"

    if contract_state == ContractState.WORKING:
        if INTERRUPT_PATTERNS.match(stripped):
            return "interrupt"

    return None


# ── Command Palette Provider ────────────────────────────────────────


class KantorKuCommandProvider(Provider):
    """Command palette provider that searches over all 40+ slash commands."""

    @property
    def _app_ref(self) -> Any:
        """Get the KantorKuTUI app reference."""
        return self.app

    async def search(self, query: str) -> AsyncIterator[Hit]:
        """Search COMMANDS dict for matches against the query."""
        # Import here to avoid circular at module level
        from kantorku.tui.commands import COMMANDS

        matcher = self.matcher(query)
        for name, cmd in COMMANDS.items():
            # Match against command name and description
            searchable = f"{name} {cmd.description}"
            match = matcher.match(searchable)
            if match > 0:
                yield Hit(
                    match,
                    matcher.highlight(f"/{name} — {cmd.description}"),
                    self._execute_command(name),
                    name=f"/{name}",
                    help_text=cmd.usage,
                )

    async def _execute_command(self, cmd_name: str) -> None:
        """Execute a slash command from the command palette."""
        app = self._app_ref
        try:
            inp = app.query_one("#chat-input", Input)
            inp.value = f"/{cmd_name}"
            # Simulate submit
            await app.on_input_submitted(Input.Submitted(inp, f"/{cmd_name}"))
        except Exception:
            # Fallback: just run the command directly
            result = await handle_slash_command(f"/{cmd_name}", app)
            if result:
                app._add_manager_message(result)


# ── Confirm Dialog ──────────────────────────────────────────────────


class ConfirmDialog(ModalScreen[bool]):
    """Modal confirmation dialog for destructive actions."""

    CSS = """
    ConfirmDialog {
        align: center middle;
    }

    ConfirmDialog > Vertical {
        width: 60;
        height: auto;
        max-height: 20;
        border: tall $warning;
        background: $surface;
        padding: 1 2;
    }

    ConfirmDialog #confirm-message {
        text-align: center;
        margin-bottom: 1;
    }

    ConfirmDialog #confirm-buttons {
        height: auto;
        margin-top: 1;
    }

    ConfirmDialog #confirm-yes {
        background: $error;
        color: $text;
        text-style: bold;
        margin-right: 2;
        border: tall $error;
    }

    ConfirmDialog #confirm-no {
        background: $primary;
        color: $text;
        text-style: bold;
        border: tall $primary;
    }
    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._message = message

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(self._message, id="confirm-message")
            with Horizontal(id="confirm-buttons"):
                yield Button("Yes, I'm sure", id="confirm-yes", variant="error")
                yield Button("Cancel", id="confirm-no", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-yes":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def key_escape(self) -> None:
        self.dismiss(False)


# ── Shortcuts Cheatsheet Screen ─────────────────────────────────────


class ShortcutsScreen(ModalScreen[None]):
    """Modal screen showing all keyboard shortcuts in a nice table."""

    CSS = """
    ShortcutsScreen {
        align: center middle;
    }

    ShortcutsScreen > Vertical {
        width: 70;
        height: auto;
        max-height: 30;
        border: tall $accent;
        background: $surface;
        padding: 1 2;
    }

    ShortcutsScreen #shortcuts-title {
        text-align: center;
        margin-bottom: 1;
    }

    ShortcutsScreen #shortcuts-scroll {
        height: auto;
        max-height: 22;
    }

    ShortcutsScreen #shortcuts-close {
        margin-top: 1;
        background: $primary;
        color: $text;
        border: tall $primary;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("[bold cyan]Keyboard Shortcuts[/bold cyan]", id="shortcuts-title")
            with VerticalScroll(id="shortcuts-scroll"):
                yield Static(self._build_shortcuts_table(), id="shortcuts-table")
            yield Button("Close (Esc)", id="shortcuts-close", variant="primary")

    def _build_shortcuts_table(self) -> str:
        """Build a formatted shortcuts reference."""
        shortcuts = [
            ("Ctrl+P", "Command Palette", "Search all slash commands"),
            ("Ctrl+Q", "Quit", "Exit the application"),
            ("Ctrl+A", "Accept Contract", "Accept the current contract"),
            ("Ctrl+R", "Revise Contract", "Enter revision mode"),
            ("Ctrl+I", "Disrupt", "Interrupt current work"),
            ("Ctrl+M", "Multi-line Input", "Toggle single/multi-line input"),
            ("Ctrl+Shift+T", "Switch Theme", "Cycle through color themes"),
            ("Ctrl+F", "Focus Mode", "Toggle focus mode (chat only)"),
            ("Escape", "Cancel", "Cancel current input / close dialog"),
            ("F1", "Shortcuts", "Show this cheatsheet"),
            ("Tab", "Next Panel", "Cycle focus between panels"),
            ("Up/Down", "History", "Navigate input history"),
        ]
        lines = ["[bold]Shortcut        Action                  Description[/bold]", ""]
        for key, action, desc in shortcuts:
            lines.append(f"  [bold green]{key:15s}[/bold green] [cyan]{action:22s}[/cyan] [dim]{desc}[/dim]")
        lines.append("")
        lines.append("[bold]Natural Language:[/bold]")
        lines.append("  [bold green]'yes'/'ok'[/bold green]       Accept contract")
        lines.append("  [bold yellow]'revise'/'no'[/bold yellow]     Request revision")
        lines.append("  [bold red]'stop'/'wait'[/bold red]        Disrupt work")
        lines.append("")
        lines.append("[bold]Multi-line Mode:[/bold]")
        lines.append("  [bold green]Ctrl+M[/bold green]           Toggle multi-line input")
        lines.append("  [bold green]Ctrl+Enter[/bold green]       Send in multi-line mode")
        lines.append("")
        lines.append("[dim]Press Esc or click Close to dismiss[/dim]")
        return "\n".join(lines)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "shortcuts-close":
            self.dismiss(None)

    def key_escape(self) -> None:
        self.dismiss(None)


# ── Widget Classes ──────────────────────────────────────────────────


class ContractDisplay(Static):
    """Right panel — shows current contract with Accept/Revise BUTTONS.

    States:
        idle               — No contract yet
        manager_thinking   — Manager is processing
        clarifying         — Manager asking questions
        contract_presented — Contract shown, Accept/Revise visible
        awaiting_revision  — User clicked Revise, writing feedback
        team_review        — Team reviewing the plan
        todo_review        — Team reviewing tasks
        client_feedback    — Client (user) giving feedback
        working            — Contract accepted, workers executing
        verifying          — Workers verifying results
        accepted           — Contract finalized (accepted by user)
        done               — Work complete
        failed             — Work failed
    """

    contract_data: reactive[dict[str, Any]] = reactive({})
    contract_state: reactive[str] = reactive("idle")
    work_result: reactive[dict[str, Any]] = reactive({})
    revision_count: reactive[int] = reactive(0)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    def on_mount(self) -> None:
        self._refresh()

    def watch_contract_data(self, data: dict[str, Any]) -> None:
        self._refresh()

    def watch_contract_state(self, state: str) -> None:
        self._refresh()

    def watch_work_result(self, data: dict[str, Any]) -> None:
        self._refresh()

    def watch_revision_count(self, count: int) -> None:
        self._refresh()

    def _refresh(self) -> None:
        parts: list[Any] = []

        # Header with state — coder-style icons (no emoji)
        state = self.contract_state
        state_color = CONTRACT_STATE_COLORS.get(state, "dim")
        state_icon = {
            "idle": "\u25cb",           # ○
            "manager_thinking": "\u25d0",  # ◐
            "clarifying": "\u25c7",     # ◇
            "contract_presented": "\u25c8",  # ◈
            "awaiting_revision": "\u270f",   # ✏
            "team_review": "\u253c",    # ┼
            "todo_review": "\u253c",    # ┼
            "client_feedback": "\u21bb",  # ↻
            "working": "\u26a1",        # ⚡
            "verifying": "\u25c7",      # ◇
            "accepted": "\u2713",       # ✓
            "done": "\u2713",           # ✓
            "failed": "\u2717",         # ✗
        }.get(state, "\u2753")

        state_labels = {
            "contract_presented": "CONTRACT PRESENTED",
            "awaiting_revision": "AWAITING YOUR REVISION",
            "accepted": "CONTRACT ACCEPTED",
        }
        state_label = state_labels.get(state, state.upper())

        parts.append(Text.from_markup(
            f"[{state_color} bold]{state_icon} {state_label}[/{state_color} bold]"
        ))

        # Revision count badge
        if self.revision_count > 0 and state in ("contract_presented", "awaiting_revision", "accepted", "working"):
            parts.append(Text.from_markup(
                f"[dim]Revision #{self.revision_count}[/dim]"
            ))

        # Contract details
        data = self.contract_data
        if data:
            parts.append(Text.from_markup(""))
            title = data.get("title", "Untitled")
            description = data.get("description", "")
            parts.append(Text.from_markup(f"[bold cyan]{title}[/bold cyan]"))
            if description:
                parts.append(Text.from_markup(f"[dim]{description[:200]}[/dim]"))

            # Use Rich Tree for collapsible sections
            tree = Tree("\U0001f4cb Contract", guide_style="dim")
            tree.expanded = True

            # ── Tasks Branch (expanded by default) ──
            todos = data.get("todos", [])
            if todos:
                tasks_branch = tree.add(f"\U0001f4dd Tasks ({len(todos)})", style="bold cyan")
                for todo in todos:
                    desc = todo.get("description", "")
                    assigned = todo.get("assigned_to", "unassigned")
                    status = todo.get("status", "pending")
                    icon = STATUS_ICONS.get(status, "\u25cb")
                    color = STATUS_COLORS.get(status, "dim")
                    squad = todo.get("squad", "")
                    squad_str = f" [{SQUAD_COLORS.get(squad, 'dim')}]{squad}[/]" if squad else ""
                    tasks_branch.add(f"[{color}]{icon}[/{color}] [{assigned}]{squad_str} {desc[:50]}")

                # Progress bar on tasks branch
                done_count = sum(1 for t in todos if t.get("status") == "done")
                total = len(todos)
                pct = int((done_count / total) * 100) if total > 0 else 0
                bar_len = 20
                filled = min(int(bar_len * done_count / total), bar_len) if total > 0 else 0
                filled = max(filled, 0)  # Guard against negative
                bar = "\u2588" * filled + "\u2591" * (bar_len - filled)
                tasks_branch.add(f"[bold]Progress:[/bold] [{bar}] {pct}% ({done_count}/{total})")

            # ── Team Feedback Branch (collapsed by default) ──
            team_feedback = data.get("team_feedback_rounds", [])
            if team_feedback:
                feedback_branch = tree.add(f"\U0001f4ac Team Feedback ({len(team_feedback)} round(s))", style="bold magenta")
                for i, round_data in enumerate(team_feedback[-2:]):
                    concerns = round_data.get("concerns", [])
                    decisions = round_data.get("decisions", [])
                    if concerns:
                        feedback_branch.add(f"Round {i+1}: [yellow]{len(concerns)} concern(s)[/yellow]")
                    if decisions:
                        for d in decisions[:2]:
                            feedback_branch.add(f"[green]\u2713 {d[:40]}[/green]")

            # ── Result Branch (collapsed by default) ──
            result = self.work_result
            if result:
                result_branch = tree.add("\U0001f4ca Result", style="bold green")
                results_data = result.get("results", {})
                if results_data:
                    for tid, r in list(results_data.items())[:5]:
                        rstatus = r.get("status", "?")
                        output = r.get("output", "")[:100]
                        sc = "green" if rstatus == "done" else "red"
                        result_branch.add(f"[{sc}]{rstatus}[/{sc}] {output}")

            parts.append(tree)

            # ── State-specific action instructions ──
            parts.append(Text.from_markup(""))
            if state == ContractState.CONTRACT_PRESENTED:
                parts.append(Text.from_markup(
                    "[bold green]\u25b8 Click [ACCEPT] below or type 'yes'/'ok'[/bold green]\n"
                    "[bold yellow]\u25b8 Click [REVISE] below or type your feedback[/bold yellow]"
                ))
            elif state == ContractState.AWAITING_REVISION:
                parts.append(Text.from_markup(
                    "[bold yellow]\u25b8 Write your revision feedback below...[/bold yellow]\n"
                    "[dim]The Manager will brainstorm with workers and present a new contract[/dim]"
                ))
            elif state == ContractState.ACCEPTED:
                parts.append(Text.from_markup(
                    "[bold green]\u2501\u2501\u2501 CONTRACT ACCEPTED \u2501\u2501\u2501[/bold green]\n"
                    "[dim]Workers are now executing the tasks...[/dim]"
                ))
            elif state == ContractState.WORKING:
                parts.append(Text.from_markup(
                    "[bold green]\u25b8 Workers are executing...[/bold green]\n"
                    "[bold yellow]\u25b8 Click [DISRUPT] or type 'stop' to pause[/bold yellow]"
                ))
            elif state in (ContractState.TEAM_REVIEW, ContractState.TODO_REVIEW):
                parts.append(Text.from_markup(
                    f"[bold magenta]\u25b8 Team is reviewing the plan...[/bold magenta]"
                ))
            elif state == ContractState.DONE:
                parts.append(Text.from_markup(
                    "[bold green]\u25b8 Work complete! Type a new task to start.[/bold green]"
                ))
        else:
            parts.append(Text.from_markup(
                "\n[dim]No active contract yet.[/dim]\n\n"
                "[dim]Chat with the Manager in\n"
                "the left panel to start.[/dim]\n\n"
                "[dim]Just type what you need\n"
                "and press Enter.[/dim]"
            ))

        # Work result (also shown at top level if no tree)
        result = self.work_result
        if result and not data:
            parts.append(Text.from_markup("\n[bold green]\u2501\u2501\u2501 Result \u2501\u2501\u2501[/bold green]"))
            results_data = result.get("results", {})
            if results_data:
                for tid, r in list(results_data.items())[:5]:
                    status = r.get("status", "?")
                    output = r.get("output", "")[:100]
                    sc = "green" if status == "done" else "red"
                    parts.append(Text.from_markup(
                        f"  [{sc}]{status}[/{sc}] {output}"
                    ))

        border_color = {
            "idle": "dim",
            "contract_presented": "cyan",
            "awaiting_revision": "yellow",
            "working": "green",
            "accepted": "green",
            "done": "green",
            "failed": "red",
        }.get(state, "yellow")

        self.update(Panel(
            Group(*parts),
            title="Contract",
            border_style=border_color,
            padding=(0, 1),
        ))


# ── Event Filter Bar ────────────────────────────────────────────────


class EventFilterBar(Horizontal):
    """Horizontal bar of toggle buttons that filter which event types
    are shown in the WorkersLiveStream."""

    CSS = """
    #event-filter-bar {
        height: auto;
        dock: top;
        padding: 0;
        background: $surface;
    }
    .filter-btn {
        margin: 0 1;
        height: 1;
        min-width: 0;
    }
    .filter-btn.active {
        text-style: bold;
    }
    """

    def compose(self) -> ComposeResult:
        yield Button("All", id="filter-all", classes="filter-btn active")
        yield Button("Tasks", id="filter-tasks", classes="filter-btn")
        yield Button("Briefing", id="filter-briefing", classes="filter-btn")
        yield Button("Errors", id="filter-errors", classes="filter-btn")
        yield Button("LLM", id="filter-llm", classes="filter-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Toggle filter state when a filter button is clicked."""
        btn_id = event.button.id or ""
        try:
            workers_live = self.app.query_one("#workers-live", WorkersLiveStream)
        except NoMatches:
            return

        if btn_id == "filter-all":
            # Reset: show everything
            workers_live._active_filters = set(FILTER_CATEGORIES.keys())
            self._update_button_states(workers_live._active_filters)
        else:
            category = btn_id.replace("filter-", "")
            if category in workers_live._active_filters:
                workers_live._active_filters.discard(category)
            else:
                workers_live._active_filters.add(category)
            self._update_button_states(workers_live._active_filters)

        workers_live._schedule_render()

    def _update_button_states(self, active_filters: set[str]) -> None:
        """Update button CSS classes based on active filters."""
        all_active = active_filters == set(FILTER_CATEGORIES.keys())
        try:
            btn_all = self.query_one("#filter-all", Button)
            if all_active:
                btn_all.add_class("active")
            else:
                btn_all.remove_class("active")
        except NoMatches:
            pass

        for category in FILTER_CATEGORIES:
            try:
                btn = self.query_one(f"#filter-{category}", Button)
                if category in active_filters:
                    btn.add_class("active")
                else:
                    btn.remove_class("active")
            except NoMatches:
                pass


# ── Thinking Indicator Widget ────────────────────────────────────────


class ThinkingIndicator(Static):
    """Pulsing spinner widget shown when the Manager is thinking.

    Shows a smooth braille animation: ⣾ → ⣽ → ⣻ → ⢿ → ⡿ → ⣟ → ⣯ → ⣷
    8-frame braille is smoother than 4-frame ◐◓◑◒.
    Hidden by default; call start(message)/stop() to control.
    """

    CSS = """
    #thinking-indicator {
        height: auto;
        dock: bottom;
        padding: 0 1;
        color: yellow;
        text-style: bold;
        display: none;
    }
    """

    _SPINNER_CHARS = BRAILLE_SPINNER

    def __init__(self, **kwargs: Any) -> None:
        super().__init__("", **kwargs)
        self._spinner_index: int = 0
        self._message: str = "Manager thinking"
        self._timer: Any = None

    def start(self, message: str = "Manager thinking") -> None:
        """Start the pulsing animation."""
        self._message = message
        self._spinner_index = 0
        self.display = True
        self._update_spinner()
        if self._timer is not None:
            self._timer.stop()
        self._timer = self.set_interval(0.25, self._tick_spinner)

    def stop(self) -> None:
        """Stop the animation and hide."""
        self.display = False
        if self._timer is not None:
            self._timer.stop()
            self._timer = None

    def _tick_spinner(self) -> None:
        """Advance the spinner one step."""
        self._spinner_index = (self._spinner_index + 1) % len(self._SPINNER_CHARS)
        self._update_spinner()

    def _update_spinner(self) -> None:
        """Update the displayed text with current spinner char."""
        char = self._SPINNER_CHARS[self._spinner_index]
        self.update(f"{char} {self._message}...")


# ── Event Renderers ──────────────────────────────────────────────────

EVENT_RENDERERS: dict[str, Any] = {}
"""Dispatch dict mapping event type strings to renderer callables.

Each renderer takes a dict (the event data) and returns a Rich Text
object or None (to skip the event).
"""


def _register_event_renderer(event_type: str):
    """Decorator to register an event renderer function."""
    def decorator(func):
        EVENT_RENDERERS[event_type] = func
        return func
    return decorator


@_register_event_renderer("briefing_opened")
def _render_briefing_opened(e: dict) -> Text | None:
    from_id = e.get("from", "conductor")
    content = e.get("content", "")
    return Text.from_markup(f"  [bold magenta]\U0001f4e2 {from_id}:[/bold magenta] {content[:80]}")


@_register_event_renderer("plan_drafted")
def _render_plan_drafted(e: dict) -> Text | None:
    return Text.from_markup("  [bold blue]\U0001f4cb Plan drafted for team review[/bold blue]")


@_register_event_renderer("plan_revised")
def _render_plan_revised(e: dict) -> Text | None:
    reason = e.get("reason", "")
    return Text.from_markup(f"  [yellow]\U0001f4cb Plan revised: {reason[:60]}[/yellow]")


@_register_event_renderer("revision_requested")
def _render_revision_requested(e: dict) -> Text | None:
    feedback = e.get("feedback", "")
    return Text.from_markup(f"  [yellow bold]\u270f\ufe0f Revision requested: {feedback[:60]}[/yellow bold]")


@_register_event_renderer("manager_brainstorming")
def _render_manager_brainstorming(e: dict) -> Text | None:
    return Text.from_markup("  [bold cyan]\U0001f4ad Manager brainstorming with workers...[/bold cyan]")


@_register_event_renderer("worker_speak_up")
def _render_worker_speak_up(e: dict) -> Text | None:
    from_id = e.get("from", "?")
    content = e.get("content", "")
    return Text.from_markup(f"  [magenta]\U0001f4ac {from_id}:[/magenta] {content[:100]}")


@_register_event_renderer("worker_dm")
def _render_worker_dm(e: dict) -> Text | None:
    from_id = e.get("from", "?")
    to_id = e.get("to", "?")
    content = e.get("content", "")
    return Text.from_markup(f"  [dim]\u2709 {from_id} \u2192 {to_id}: {content[:80]}[/dim]")


@_register_event_renderer("worker_broadcast")
def _render_worker_broadcast(e: dict) -> Text | None:
    from_id = e.get("from", "?")
    content = e.get("content", "")
    return Text.from_markup(f"  [cyan]\U0001f4e2 {from_id}: {content[:80]}[/cyan]")


@_register_event_renderer("task_assigned")
def _render_task_assigned(e: dict) -> Text | None:
    to_id = e.get("to", "?")
    content = e.get("content", "")
    return Text.from_markup(f"  [cyan]\u27a1 {to_id}: {content[:70]}[/cyan]")


@_register_event_renderer("task_started")
def _render_task_started(e: dict) -> Text | None:
    from_id = e.get("from", "?")
    return Text.from_markup(f"  [yellow]\u25d0 {from_id} started working...[/yellow]")


@_register_event_renderer("task_done")
def _render_task_done(e: dict) -> Text | None:
    from_id = e.get("from", "?")
    files = e.get("files", [])
    files_str = f" \u2192 {', '.join(files[:3])}" if files else ""
    return Text.from_markup(f"  [green]\u2713 {from_id} done{files_str}[/green]")


@_register_event_renderer("task_failed")
def _render_task_failed(e: dict) -> Text | None:
    from_id = e.get("from", "?")
    error = e.get("error", "")
    return Text.from_markup(f"  [red bold]\u2717 {from_id} failed: {error[:60]}[/red bold]")


@_register_event_renderer("task_recovered")
def _render_task_recovered(e: dict) -> Text | None:
    from_id = e.get("from", "?")
    return Text.from_markup(f"  [green]\u21bb {from_id} recovered[/green]")


@_register_event_renderer("task_timeout")
def _render_task_timeout(e: dict) -> Text | None:
    from_id = e.get("from", "?")
    return Text.from_markup(f"  [red]\u23f1 {from_id} timed out[/red]")


@_register_event_renderer("context_fetch_start")
def _render_context_fetch_start(e: dict) -> Text | None:
    instance = e.get("instance", "?")
    query = e.get("query", "")[:40]
    return Text.from_markup(f"  [dim]\U0001f50d Pool-{instance}: fetching \"{query}\"[/dim]")


@_register_event_renderer("context_fetch_done")
def _render_context_fetch_done(e: dict) -> Text | None:
    instance = e.get("instance", "?")
    return Text.from_markup(f"  [dim]\u2713 Pool-{instance}: fetched[/dim]")


@_register_event_renderer("verify_design_start")
def _render_verify_design_start(e: dict) -> Text | None:
    return Text.from_markup("  [magenta]\U0001f50d Design verification starting...[/magenta]")


@_register_event_renderer("verify_design_done")
def _render_verify_design_done(e: dict) -> Text | None:
    approved = e.get("approved", True)
    issues = e.get("issues", [])
    icon = "\u2713" if approved else "\u2717"
    color = "green" if approved else "red"
    return Text.from_markup(f"  [{color}]{icon} Design review: {len(issues)} issue(s)[/{color}]")


@_register_event_renderer("verify_engineer_start")
def _render_verify_engineer_start(e: dict) -> Text | None:
    return Text.from_markup("  [magenta]\U0001f50d Engineering verification starting...[/magenta]")


@_register_event_renderer("verify_engineer_done")
def _render_verify_engineer_done(e: dict) -> Text | None:
    approved = e.get("approved", True)
    issues = e.get("issues", [])
    icon = "\u2713" if approved else "\u2717"
    color = "green" if approved else "red"
    return Text.from_markup(f"  [{color}]{icon} Engineering review: {len(issues)} issue(s)[/{color}]")


@_register_event_renderer("error_logged")
def _render_error_logged(e: dict) -> Text | None:
    lesson = e.get("lesson", "")
    return Text.from_markup(f"  [red]\u26a0 Error: {lesson[:80]}[/red]")


@_register_event_renderer("skill_updated")
def _render_skill_updated(e: dict) -> Text | None:
    worker = e.get("worker", "?")
    lesson = e.get("lesson", "")
    return Text.from_markup(f"  [cyan]\U0001f4da {worker} learned: {lesson[:60]}[/cyan]")


@_register_event_renderer("llm_stream_start")
def _render_llm_stream_start(e: dict) -> Text | None:
    from_id = e.get("from", "?")
    model = e.get("model", "")
    return Text.from_markup(f"  [dim]\u25d0 {from_id} thinking ({model})...[/dim]")


@_register_event_renderer("llm_stream_chunk")
def _render_llm_stream_chunk(e: dict) -> Text | None:
    chunk = e.get("chunk", "")
    if chunk:
        return Text.from_markup(f"  [dim]{chunk}[/dim]")
    return None


@_register_event_renderer("llm_stream_done")
def _render_llm_stream_done(e: dict) -> Text | None:
    from_id = e.get("from", "?")
    return Text.from_markup(f"  [dim]\u2713 {from_id} stream complete[/dim]")


@_register_event_renderer("contract_accepted")
def _render_contract_accepted(e: dict) -> Text | None:
    return Text.from_markup("  [bold green]\u2713 Contract accepted \u2014 work begins![/bold green]")


@_register_event_renderer("delegation_request")
def _render_delegation_request(e: dict) -> Text | None:
    return Text.from_markup(f"  [cyan]\u2197 Delegation: {e.get('content', '')[:60]}[/cyan]")


@_register_event_renderer("delegation_result")
def _render_delegation_result(e: dict) -> Text | None:
    return Text.from_markup(f"  [cyan]\u2199 Delegation result: {e.get('content', '')[:60]}[/cyan]")


@_register_event_renderer("checkpoint_saved")
def _render_checkpoint_saved(e: dict) -> Text | None:
    return Text.from_markup("  [green]\U0001f4be Checkpoint saved[/green]")


@_register_event_renderer("crash_recovered")
def _render_crash_recovered(e: dict) -> Text | None:
    return Text.from_markup("  [yellow bold]\U0001f504 Crash recovered[/yellow bold]")


@_register_event_renderer("circuit_open")
def _render_circuit_open(e: dict) -> Text | None:
    provider = e.get("provider", "?")
    return Text.from_markup(f"  [red bold]\u26a1 Circuit OPEN: {provider}[/red bold]")


@_register_event_renderer("circuit_closed")
def _render_circuit_closed(e: dict) -> Text | None:
    provider = e.get("provider", "?")
    return Text.from_markup(f"  [green]\u2713 Circuit closed: {provider}[/green]")


@_register_event_renderer("rate_limit_hit")
def _render_rate_limit_hit(e: dict) -> Text | None:
    provider = e.get("provider", "?")
    return Text.from_markup(f"  [yellow]\u23f0 Rate limit: {provider}[/yellow]")


@_register_event_renderer("cost_warning")
def _render_cost_warning(e: dict) -> Text | None:
    msg = e.get("message", "Cost threshold approached")
    return Text.from_markup(f"  [yellow bold]\U0001f4b8 {msg[:60]}[/yellow bold]")


@_register_event_renderer("worker_hired")
def _render_worker_hired(e: dict) -> Text | None:
    worker_id = e.get("worker_id", "?")
    return Text.from_markup(f"  [green bold]\U0001f91d Hired: {worker_id}[/green bold]")


@_register_event_renderer("worker_fired")
def _render_worker_fired(e: dict) -> Text | None:
    worker_id = e.get("worker_id", "?")
    return Text.from_markup(f"  [red bold]\U0001f6ae Fired: {worker_id}[/red bold]")


@_register_event_renderer("middleware_before")
def _render_middleware_before(e: dict) -> Text | None:
    name = e.get("middleware", "?")
    return Text.from_markup(f"  [dim blue]\u2192 {name}[/dim blue]")


@_register_event_renderer("middleware_after")
def _render_middleware_after(e: dict) -> Text | None:
    name = e.get("middleware", "?")
    return Text.from_markup(f"  [dim blue]\u2190 {name}[/dim blue]")


# ── Workers Live Stream ─────────────────────────────────────────────


class WorkersLiveStream(Static):
    """Center panel — live stream of worker activity.

    Shows:
    - Briefing room discussions
    - Worker speak_up / concerns / suggestions
    - Task assignment & execution
    - Worker DMs and broadcasts
    - LLM streaming chunks
    - Context prefetch status
    - Verification progress
    - Checkpoint / recovery events
    - Circuit breaker events
    - Worker lifecycle (hire/fire)
    - Cost warnings
    - Delegation

    Supports filtering by event category via _active_filters.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._entries: list[dict[str, Any]] = []
        self._max_entries = 500  # Memory buffer; visible display shows last 50
        self._round: int = 0
        self._phase: str = ""  # idle, briefing, execution, verification, done

        # Active filters — defaults to all categories active
        self._active_filters: set[str] = set(FILTER_CATEGORIES.keys())

        # Render throttle (20fps max)
        self._last_render_time: float = 0.0
        self._dirty: bool = False
        self._pending_render: Any = None
        self._render_cooldown: float = 0.05

    def _event_matches_filter(self, event_type: str) -> bool:
        """Check if an event type passes the active filters."""
        # System messages always pass
        if event_type == "system":
            return True

        # Find which category this event type belongs to
        for category, types in FILTER_CATEGORIES.items():
            if event_type in types:
                return category in self._active_filters

        # Events not in any filter category are always shown
        return True

    def add_event(self, event: dict[str, Any]) -> None:
        """Add an office event to the live stream."""
        event_type = event.get("type", "")

        # Show ALL relevant worker events in center panel
        relevant_types = {
            "briefing_opened", "plan_drafted", "plan_revised",
            "worker_speak_up", "worker_dm", "worker_broadcast",
            "task_assigned", "task_started", "task_done", "task_failed",
            "context_fetch_start", "context_fetch_done",
            "verify_design_start", "verify_design_done",
            "verify_engineer_start", "verify_engineer_done",
            "error_logged", "skill_updated",
            "llm_stream_start", "llm_stream_chunk", "llm_stream_done",
            "contract_accepted",
            "delegation_request", "delegation_result",
            # v0.6.0 additions
            "checkpoint_saved", "crash_recovered",
            "circuit_open", "circuit_closed",
            "rate_limit_hit", "cost_warning",
            "worker_hired", "worker_fired",
            "task_recovered", "task_timeout",
            "middleware_before", "middleware_after",
            # v0.7.0 — revision brainstorming
            "revision_requested", "manager_brainstorming",
            # v0.8.0 — work completion
            "work_done",
        }

        if event_type not in relevant_types:
            return

        self._entries.append(event)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]
        self._schedule_render()

    def add_system_message(self, message: str, style: str = "dim") -> None:
        """Add a system/phase message to the stream."""
        self._entries.append({
            "type": "system",
            "content": message,
            "style": style,
        })
        self._schedule_render()

    def clear(self) -> None:
        self._entries.clear()
        self._render_stream()

    def _schedule_render(self) -> None:
        """Throttled render — max 20fps."""
        import time
        now = time.monotonic()
        if now - self._last_render_time >= self._render_cooldown:
            self._render_stream()
            self._last_render_time = now
        else:
            self._dirty = True
            if self._pending_render is None:
                self._pending_render = self.set_timer(
                    self._render_cooldown, self._flush_pending_render
                )

    def _flush_pending_render(self) -> None:
        """Flush a dirty render after the cooldown."""
        import time
        self._pending_render = None
        if self._dirty:
            self._dirty = False
            self._render_stream()
            self._last_render_time = time.monotonic()

    def _render_stream(self) -> None:
        if not self._entries:
            self.update(Panel(
                "[dim]Workers will appear here once a contract is accepted.[/dim]\n\n"
                "[dim]You'll see:\n"
                "  \u2022 Briefing room discussion\n"
                "  \u2022 Task assignments & execution\n"
                "  \u2022 Worker DMs and concerns\n"
                "  \u2022 LLM streaming output\n"
                "  \u2022 Verification results[/dim]",
                title="Workers Live",
                border_style="dim",
                padding=(0, 1),
            ))
            return

        parts: list[Any] = []

        # Phase indicator
        if self._phase:
            phase_style = WORKERS_PHASE_STYLES.get(
                self._phase, ("dim", self._phase.upper())
            )
            pc, pi = phase_style
            parts.append(Text.from_markup(f"[{pc}]{pi}[/{pc}]\n"))

        # Filter indicator
        if self._active_filters != set(FILTER_CATEGORIES.keys()):
            active_names = sorted(self._active_filters)
            parts.append(Text.from_markup(
                f"[dim]Filter: {', '.join(active_names)}[/dim]\n"
            ))

        visible = self._entries[-50:]  # Show last 50 entries

        for e in visible:
            event_type = e.get("type", "")

            # Apply filter
            if not self._event_matches_filter(event_type):
                continue

            # System messages — inline render (not in dispatch dict)
            if event_type == "system":
                style = e.get("style", "dim")
                parts.append(Text.from_markup(f"[{style}]{e.get('content', '')}[/{style}]"))
                continue

            # Dispatch to registered renderer
            renderer = EVENT_RENDERERS.get(event_type)
            if renderer:
                result = renderer(e)
                if result:
                    parts.append(result)
            # else: skip unknown events

        self.update(Panel(
            Group(*parts),
            title="Workers Live",
            border_style=KANTORKU_THEME["secondary"],
            padding=(0, 1),
        ))

        # Auto-scroll: try to scroll the parent container to the bottom
        try:
            parent = self.parent
            if parent and hasattr(parent, 'scroll_end'):
                parent.scroll_end(animate=False)
        except Exception:
            pass


# ── Briefing Panel ──────────────────────────────────────────────────


class BriefingPanel(Static):
    """Briefing room panel — shows briefing conversation as a chat thread.

    Accumulates briefing_opened, worker_speak_up, manager_brainstorming,
    plan_drafted, and plan_revised events and renders them as a conversation.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._messages: list[dict[str, Any]] = []

    def add_event(self, event: dict[str, Any]) -> None:
        """Add a briefing-relevant event."""
        event_type = event.get("type", "")

        briefing_types = {
            "briefing_opened", "worker_speak_up", "manager_brainstorming",
            "plan_drafted", "plan_revised",
        }
        if event_type not in briefing_types:
            return

        self._messages.append(event)
        self._render_messages()

    def _render_messages(self) -> None:
        """Render the briefing conversation."""
        if not self._messages:
            self.update(Panel(
                "[dim]Briefing room messages will appear here\n"
                "when a contract is accepted.[/dim]",
                title="Briefing Room",
                border_style="dim",
                padding=(0, 1),
            ))
            return

        parts: list[Any] = []
        for msg in self._messages:
            event_type = msg.get("type", "")

            if event_type == "briefing_opened":
                from_id = msg.get("from", "conductor")
                content = msg.get("content", "")
                parts.append(Text.from_markup(
                    f"[bold magenta]\U0001f4e2 {from_id}:[/bold magenta] {content[:120]}"
                ))

            elif event_type == "worker_speak_up":
                from_id = msg.get("from", "?")
                content = msg.get("content", "")
                parts.append(Text.from_markup(
                    f"  [magenta]\U0001f4ac {from_id}:[/magenta] {content[:120]}"
                ))

            elif event_type == "manager_brainstorming":
                parts.append(Text.from_markup(
                    "  [bold cyan]\U0001f4ad Manager brainstorming with workers...[/bold cyan]"
                ))

            elif event_type == "plan_drafted":
                parts.append(Text.from_markup(
                    "  [bold blue]\U0001f4cb Plan drafted for team review[/bold blue]"
                ))

            elif event_type == "plan_revised":
                reason = msg.get("reason", "")
                parts.append(Text.from_markup(
                    f"  [yellow]\U0001f4cb Plan revised: {reason[:80]}[/yellow]"
                ))

        self.update(Panel(
            Group(*parts),
            title="Briefing Room",
            border_style=KANTORKU_THEME["secondary"],
            padding=(0, 1),
        ))

    def clear(self) -> None:
        """Clear the briefing messages."""
        self._messages.clear()
        self._render_messages()


# ── DAG Panel ───────────────────────────────────────────────────────


class DAGPanel(Static):
    """DAG / Task dependency tree panel.

    Shows a Rich Tree of task dependencies.
    Receives task_assigned, task_done, task_failed events and builds
    a visual task tree.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._tasks: dict[str, dict[str, Any]] = {}
        self._groups: dict[str, list[str]] = {}  # squad -> [task_ids]
        self._critical_path: list[str] = []

    def update_dag(
        self,
        groups: dict[str, list[str]] | None = None,
        todos: list[dict[str, Any]] | None = None,
        critical_path: list[str] | None = None,
    ) -> None:
        """Update the DAG with new task information."""
        if groups is not None:
            self._groups = groups
        if todos is not None:
            for todo in todos:
                tid = todo.get("id", todo.get("description", "?"))
                self._tasks[tid] = todo
        if critical_path is not None:
            self._critical_path = critical_path
        self._render_dag()

    def add_event(self, event: dict[str, Any]) -> None:
        """Update task status from events."""
        event_type = event.get("type", "")

        if event_type == "task_assigned":
            to_id = event.get("to", "?")
            content = event.get("content", "")
            squad = event.get("squad", "")
            tid = event.get("task_id", content[:30])
            self._tasks[tid] = {
                "description": content,
                "assigned_to": to_id,
                "status": "assigned",
                "squad": squad,
            }
            if squad:
                if squad not in self._groups:
                    self._groups[squad] = []
                if tid not in self._groups[squad]:
                    self._groups[squad].append(tid)

        elif event_type == "task_done":
            from_id = event.get("from", "?")
            # Find task by worker
            for tid, task in self._tasks.items():
                if task.get("assigned_to") == from_id and task.get("status") != "done":
                    task["status"] = "done"
                    break

        elif event_type == "task_failed":
            from_id = event.get("from", "?")
            for tid, task in self._tasks.items():
                if task.get("assigned_to") == from_id and task.get("status") != "failed":
                    task["status"] = "failed"
                    break

        self._render_dag()

    def _render_dag(self) -> None:
        """Render the task dependency tree with ASCII box-drawing characters."""
        if not self._tasks:
            self.update(Panel(
                "[dim]Task dependency tree will appear here\n"
                "once tasks are assigned.[/dim]",
                title="DAG \u2014 Task Dependency Tree",
                border_style="dim",
                padding=(0, 1),
            ))
            return

        tree = Tree("\U0001f5c2 Task Dependency Tree")

        if self._groups:
            for squad, task_ids in self._groups.items():
                squad_color = SQUAD_COLORS.get(squad, "dim")
                branch = tree.add(f"[{squad_color} bold]\u2588 {squad}[/{squad_color} bold]")
                for i, tid in enumerate(task_ids):
                    task = self._tasks.get(tid, {})
                    desc = task.get("description", tid)[:50]
                    status = task.get("status", "pending")
                    assigned = task.get("assigned_to", "?")
                    icon = STATUS_ICONS.get(status, "\u25cb")
                    color = STATUS_COLORS.get(status, "dim")
                    # Use box-drawing chars for visual hierarchy
                    is_last = (i == len(task_ids) - 1)
                    prefix = "\u2514\u2500" if is_last else "\u251c\u2500"  # └─ or ├─
                    branch.add(
                        f"[dim]{prefix}[/dim] [{color}]{icon}[/{color}] "
                        f"{desc} [dim][{assigned}][/dim]"
                    )
        else:
            # No groups — just list tasks flat with box-drawing
            for i, (tid, task) in enumerate(self._tasks.items()):
                desc = task.get("description", tid)[:50]
                status = task.get("status", "pending")
                assigned = task.get("assigned_to", "?")
                icon = STATUS_ICONS.get(status, "\u25cb")
                color = STATUS_COLORS.get(status, "dim")
                is_last = (i == len(self._tasks) - 1)
                prefix = "\u2514\u2500" if is_last else "\u251c\u2500"
                tree.add(
                    f"[dim]{prefix}[/dim] [{color}]{icon}[/{color}] "
                    f"{desc} [dim][{assigned}][/dim]"
                )

        # Show critical path if available
        parts: list[Any] = [tree]
        if self._critical_path:
            cp_str = " \u2192 ".join(self._critical_path[:8])
            parts.append(Text.from_markup(
                f"\n[bold red]\u26a1 Critical Path:[/bold red] {cp_str}"
            ))

        # Summary
        total = len(self._tasks)
        done = sum(1 for t in self._tasks.values() if t.get("status") == "done")
        failed = sum(1 for t in self._tasks.values() if t.get("status") == "failed")
        parts.append(Text.from_markup(
            f"\n[dim]Tasks: {total} total, {done} done, {failed} failed[/dim]"
        ))

        self.update(Panel(
            Group(*parts),
            title="DAG \u2014 Task Dependency Tree",
            border_style=KANTORKU_THEME["secondary"],
            padding=(0, 1),
        ))

    def clear(self) -> None:
        """Clear the DAG."""
        self._tasks.clear()
        self._groups.clear()
        self._critical_path.clear()
        self._render_dag()


# ── Event Log Panel ─────────────────────────────────────────────────


class EventLogPanel(RichLog):
    """Event log panel — shows ALL events as scrollable, searchable text.

    Unlike WorkersLiveStream which filters by relevant types, this panel
    receives every event that flows through the system.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            highlight=True,
            markup=True,
            auto_scroll=True,
            **kwargs,
        )

    def add_event(self, event: dict[str, Any]) -> None:
        """Log an event to the panel."""
        event_type = event.get("type", "unknown")
        ts = event.get("timestamp", "")

        # Format timestamp
        if ts:
            try:
                if isinstance(ts, str):
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    ts_str = dt.strftime("%H:%M:%S")
                else:
                    ts_str = str(ts)[:8]
            except Exception:
                ts_str = str(ts)[:8]
        else:
            ts_str = datetime.now().strftime("%H:%M:%S")

        # Color-code by event type
        type_colors = {
            "task_": "cyan",
            "briefing_": "magenta",
            "worker_": "green",
            "manager_": "bold cyan",
            "llm_": "dim",
            "error": "red",
            "circuit_": "red bold",
            "rate_": "yellow",
            "cost_": "yellow bold",
            "contract_": "bold green",
            "work_": "green bold",
            "revision_": "yellow",
            "verify_": "magenta",
            "context_": "dim",
            "delegation_": "cyan",
            "checkpoint_": "green",
            "crash_": "yellow bold",
            "middleware_": "dim blue",
        }

        color = "dim"
        for prefix, c in type_colors.items():
            if event_type.startswith(prefix):
                color = c
                break

        # Build the log line
        summary_parts = []
        for key in ("from", "to", "content", "worker_id", "provider", "message", "error", "reason"):
            val = event.get(key)
            if val:
                summary_parts.append(f"{key}={str(val)[:40]}")

        summary = " ".join(summary_parts)
        if summary:
            summary = f" {summary}"

        self.write(Text.from_markup(
            f"[dim]{ts_str}[/dim] [{color}]{event_type}[/{color}]{summary}"
        ))


# ── Main TUI Application ────────────────────────────────────────────


class KantorKuTUI(App):
    """
    KantorKu — 3-Panel Chat-Driven Office Interface for Coders.

    Natural office workflow — chat is PRIMARY:
    1. Chat with Manager in LEFT panel (just type naturally)
    2. Watch workers brainstorm/execute in CENTER panel (tabbed views)
    3. Review & accept contracts in RIGHT panel (click buttons or type)
    4. Hit DISRUPT to pause and talk to Manager again

    Center Panel Tabs:
      - Workers: Filtered live stream of worker activity
      - Briefing: Conversation view of briefing room
      - DAG: Task dependency tree visualization
      - Events: Unfiltered scrollable event log

    Contract Accept/Revise Flow:
      - Contract presented → Click ACCEPT or type "yes" → Contract finalized
      - Contract presented → Click REVISE or type feedback →
        Manager brainstorms with workers → New contract presented with Accept/Revise

    Natural Language Actions:
      Contract presented? Type "yes", "ok", "accept" to approve.
      Want changes? Type "revise", "change X", "I want Y" to revise.
      Working? Type "stop", "wait", "pause" to disrupt.

    Slash commands still work as secondary tools — /help for list.
    """

    TITLE = "\u26a1 kantorku"
    SUB_TITLE = "Chat-Driven Office"

    COMMANDS = App.COMMANDS | {KantorKuCommandProvider}

    @staticmethod
    def _build_css(theme: dict[str, str]) -> str:
        """Build the full CSS string from a theme dict — Premium Coder Aesthetic."""
        border_dim = theme.get('border_dim', theme.get('surface', '#1e293b'))
        glow = theme.get('glow', theme['primary'])
        return f"""
    Screen {{
        layout: vertical;
        background: {theme['background']};
    }}

    /* ── Custom Header ── */
    Header {{
        background: {theme['surface']};
        border-bottom: tall {theme['primary']};
        padding: 0 1;
    }}

    Header .header--title {{
        color: {theme['primary']};
        text-style: bold;
    }}

    Header .header--icon {{
        color: {theme['primary']};
    }}

    /* ── Main 3-Panel Container ── */
    #main-container {{
        layout: horizontal;
        height: 1fr;
    }}

    /* ── Left Panel: Manager Chat ── */
    #left-panel {{
        width: 30%;
        height: 100%;
        border: tall {theme['primary']};
        border-title-color: {theme['primary']};
        border-title-background: {theme['surface']};
        background: {theme['background']};
    }}

    /* ── Center Panel: Tabbed Views ── */
    #center-panel {{
        width: 40%;
        height: 100%;
        border: tall {theme['secondary']};
        border-title-color: {theme['secondary']};
        border-title-background: {theme['surface']};
        background: {theme['background']};
    }}

    /* ── Right Panel: Contract ── */
    #right-panel {{
        width: 30%;
        height: 100%;
        border: tall {theme['accent']};
        border-title-color: {theme['accent']};
        border-title-background: {theme['surface']};
        background: {theme['background']};
    }}

    /* ── Manager Chat Log ── */
    #manager-log {{
        height: 1fr;
        border: none;
        padding: 0 1;
        scrollbar-size: 1 1;
        scrollbar-color: {theme['primary']} 30%;
    }}

    /* ── Contract Scroll Area ── */
    #contract-scroll {{
        height: 1fr;
        scrollbar-size: 1 1;
        scrollbar-color: {theme['accent']} 30%;
    }}

    /* ── Input Area ── */
    #input-bar {{
        height: auto;
        dock: bottom;
        padding: 0 1;
        background: {theme['surface']};
        border-top: tall {theme['primary']} 40%;
    }}

    #chat-input {{
        dock: bottom;
        background: {theme['surface']};
        border: tall {border_dim};
        color: {theme['text']};
    }}

    #chat-input:focus {{
        border: tall {theme['primary']} 60%;
    }}

    #multiline-input {{
        dock: bottom;
        height: 5;
        display: none;
        background: {theme['surface']};
        border: tall {border_dim};
        color: {theme['text']};
    }}

    #multiline-input:focus {{
        border: tall {theme['primary']} 60%;
    }}

    #multiline-input.multiline-active {{
        border: tall {theme['accent']} 80%;
        background: {theme['accent']} 5%;
    }}

    #input-mode-indicator {{
        height: 1;
        dock: bottom;
        padding: 0 1;
        color: {theme['muted']};
    }}

    #action-hints {{
        height: 1;
        dock: bottom;
        padding: 0 1;
        color: {theme['muted']};
    }}

    /* ── Lifecycle Breadcrumb ── */
    #lifecycle-breadcrumb {{
        height: 1;
        padding: 0 1;
        color: {theme['muted']};
        background: {theme['surface']};
        border-bottom: tall {border_dim};
    }}

    /* ── DISRUPT Button ── Neon danger style */
    #disrupt-btn {{
        dock: bottom;
        margin: 0 1;
        background: {theme['warning']} 15%;
        color: {theme['warning']};
        text-style: bold;
        border: tall {theme['warning']};
    }}

    #disrupt-btn:hover {{
        background: {theme['error']} 25%;
        color: {theme['error']};
        border: tall {theme['error']};
    }}

    /* ── Action Bar (Accept/Revise) ── */
    #action-bar {{
        dock: bottom;
        height: auto;
        padding: 0 1;
        background: {theme['surface']};
    }}

    /* ── ACCEPT Button ── Neon success glow */
    #accept-btn {{
        background: {theme['success']} 15%;
        color: {theme['success']};
        text-style: bold;
        margin-right: 1;
        border: tall {theme['success']};
    }}

    #accept-btn:hover {{
        background: {theme['success']} 30%;
        border: tall {theme['success']};
        text-style: bold;
    }}

    #accept-btn:disabled {{
        background: {theme['surface']};
        color: {theme['muted']};
        text-style: not bold;
        border: tall {border_dim};
    }}

    /* ── REVISE Button ── Neon accent glow */
    #revise-btn {{
        background: {theme['accent']} 15%;
        color: {theme['accent']};
        text-style: bold;
        border: tall {theme['accent']};
    }}

    #revise-btn:hover {{
        background: {theme['accent']} 30%;
        border: tall {theme['accent']};
        text-style: bold;
    }}

    #revise-btn:disabled {{
        background: {theme['surface']};
        color: {theme['muted']};
        text-style: not bold;
        border: tall {border_dim};
    }}

    /* ── Center Panel Tabs ── */
    #center-tabs {{
        height: 1fr;
    }}

    #center-tabs > TabPane {{
        padding: 0 1;
    }}

    TabbedContent Tabs {{
        background: {theme['surface']};
    }}

    TabbedContent Tabs Tab {{
        color: {theme['muted']};
    }}

    TabbedContent Tabs Tab:hover {{
        color: {theme['text']};
        background: {theme['primary']} 15%;
    }}

    TabbedContent Tabs Tab.-active {{
        color: {theme['primary']};
        text-style: bold;
        background: {theme['primary']} 10%;
    }}

    /* ── Workers Scroll ── */
    #workers-scroll {{
        height: 1fr;
        scrollbar-size: 1 1;
        scrollbar-color: {theme['secondary']} 30%;
    }}

    /* ── Event Filter Bar ── */
    #event-filter-bar {{
        height: auto;
        dock: top;
        padding: 0;
        background: {theme['surface']};
        border-bottom: tall {border_dim};
    }}

    .filter-btn {{
        margin: 0 1;
        height: 1;
        min-width: 0;
        background: transparent;
        color: {theme['muted']};
        border: none;
    }}

    .filter-btn.active {{
        text-style: bold;
        color: {theme['primary']};
        background: {theme['primary']} 10%;
    }}

    .filter-btn:hover {{
        color: {theme['text']};
        background: {theme['primary']} 15%;
    }}

    /* ── Bottom Status Bar ── Premium HUD style */
    #status-bar {{
        dock: bottom;
        height: 1;
        background: {theme['surface']};
        color: {theme['muted']};
        padding: 0 1;
    }}

    #bottom-status-bar {{
        height: 1;
        background: {theme['surface']};
        color: {theme['muted']};
        padding: 0 1;
        border-top: tall {border_dim};
    }}

    #bottom-status-bar Static {{
        width: auto;
    }}

    #status-conn {{
        color: {theme['success']};
    }}

    #status-conn.disconnected {{
        color: {theme['error']};
    }}

    #status-session {{
        color: {theme['muted']};
    }}

    #status-cost {{
        color: {theme['warning']};
    }}

    #status-calls {{
        color: {theme['muted']};
    }}

    #status-phase {{
        color: {theme['info']};
    }}

    /* ── Footer ── */
    Footer {{
        background: {theme['surface']};
        border-top: tall {border_dim};
        color: {theme['muted']};
    }}

    Footer .footer--key {{
        color: {theme['primary']};
    }}

    Footer .footer--description {{
        color: {theme['muted']};
    }}

    /* ── Scrollbar global ── */
    * {{
        scrollbar-size: 1 1;
    }}

    /* ── RichLog scrollbar ── */
    RichLog {{
        scrollbar-size: 1 1;
        scrollbar-color: {theme['primary']} 30%;
    }}

    /* ── Vertical Scroll ── */
    VerticalScroll {{
        scrollbar-size: 1 1;
        scrollbar-color: {theme['primary']} 30%;
    }}

    /* ── Focus ring ── */
    Widget:focus {{
        border: tall {glow} 60%;
    }}

    /* ── Notification toast ── */
    Notification {{
        background: {theme['surface']};
        border: tall {theme['primary']};
        color: {theme['text']};
    }}
    """

    # Initialize CSS with default theme
    CSS = _build_css.__func__(KANTORKU_THEME)

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("ctrl+p", "command_palette", "Commands", show=True),
        Binding("f1", "show_shortcuts", "Shortcuts", show=True),
        Binding("escape", "cancel_input", "Cancel", show=True),
        Binding("ctrl+a", "accept_contract", "Accept", show=False),
        Binding("ctrl+r", "revise_contract", "Revise", show=False),
        Binding("ctrl+i", "disrupt", "Disrupt", show=False),
        Binding("ctrl+m", "toggle_multiline", "Multi-line", show=False),
        Binding("ctrl+shift+t", "switch_theme", "Theme", show=False),
        Binding("ctrl+f", "toggle_focus_mode", "Focus", show=False),
        Binding("tab", "focus_next_panel", "Next Panel", show=False),
        Binding("up", "history_up", "History \u2191", show=False),
        Binding("down", "history_down", "History \u2193", show=False),
    ]

    # Reactive state
    session_id: reactive[str] = reactive("")
    connection_state: reactive[str] = reactive("disconnected")
    pending_contract: reactive[dict] = reactive({})
    contract_state: reactive[str] = reactive("idle")

    # Destructive commands that require confirmation
    DESTRUCTIVE_COMMANDS = {"fire", "reset", "queue-purge"}

    def __init__(
        self,
        server_url: str = "http://localhost:8000",
        config_path: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.server_url = server_url
        self.config_path = config_path
        self._session_id = uuid.uuid4().hex[:12]
        self.session_id = self._session_id
        self._connection = OfficeConnection(server_url, self._session_id)
        self._streaming_text = ""
        self._is_streaming = False

        # Input history
        self._input_history: list[str] = []
        self._history_index: int = -1

        # Reconnection
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10
        self._reconnect_delay = 2.0

        # Worker event listener
        self._event_listener_running = False

        # Cost tracking for status
        self._total_cost: float = 0.0
        self._total_calls: int = 0

        # Revision tracking
        self._revision_count: int = 0
        self._revision_feedback: str = ""

        # Auto-accept flag for /code and /run
        self._auto_accept_pending: bool = False

        # Pending destructive command (awaiting confirmation)
        self._pending_destructive_cmd: str | None = None
        self._pending_destructive_args: str = ""

        # Multi-line input mode
        self._multiline_mode: bool = False

        # Current theme name
        self._current_theme: str = "synthwave"

        # Focus mode (hide center+right panels)
        self._focus_mode: bool = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Container(id="main-container"):
            # ── Left Panel: Manager Chat ──
            with Vertical(id="left-panel"):
                yield RichLog(
                    id="manager-log",
                    highlight=True,
                    markup=True,
                    auto_scroll=True,
                )
                yield ThinkingIndicator(id="thinking-indicator")
                yield Button(
                    "\u26a1 DISRUPT \u2014 Talk to Manager",
                    id="disrupt-btn",
                    variant="warning",
                )
                with Horizontal(id="input-bar"):
                    yield Input(
                        placeholder="Talk to Manager...",
                        id="chat-input",
                    )
                    yield TextArea(
                        id="multiline-input",
                    )
                    yield Static("[dim]Single-line | Ctrl+M to toggle[/dim]", id="input-mode-indicator")
                    yield Static("[dim]Type a task... /help for commands  Ctrl+P=Commands  F1=Help[/dim]", id="action-hints")

            # ── Center Panel: Tabbed Views ──
            with Vertical(id="center-panel"):
                with TabbedContent(id="center-tabs"):
                    with TabPane("Workers", id="workers-tab"):
                        yield EventFilterBar(id="event-filter-bar")
                        with VerticalScroll(id="workers-scroll"):
                            yield WorkersLiveStream(id="workers-live")
                    with TabPane("Briefing", id="briefing-tab"):
                        yield BriefingPanel(id="briefing-panel")
                    with TabPane("DAG", id="dag-tab"):
                        yield DAGPanel(id="dag-panel")
                    with TabPane("Events", id="events-tab"):
                        yield EventLogPanel(id="events-panel")

            # ── Right Panel: Contract + Buttons ──
            with Vertical(id="right-panel"):
                yield Static("", id="lifecycle-breadcrumb")
                with VerticalScroll(id="contract-scroll"):
                    yield ContractDisplay(id="contract-display")
                with Horizontal(id="action-bar"):
                    yield Button(
                        "\u2713 ACCEPT",
                        id="accept-btn",
                        variant="success",
                    )
                    yield Button(
                        "\u270f REVISE",
                        id="revise-btn",
                        variant="warning",
                    )

        # ── Enhanced Status Bar ──
        with Horizontal(id="bottom-status-bar"):
            yield Static("\u25cf", id="status-conn")
            yield Static(f" {self._session_id}", id="status-session")
            yield Static(" $0.0000", id="status-cost")
            yield Static(" 0 calls", id="status-calls")
            yield Static(" idle", id="status-phase")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize connection and start background workers."""
        self.title = f"\u26a1 kantorku \u2014 {self._session_id}"
        self._add_manager_message(
            f"[bold {KANTORKU_THEME['primary']}]\u250c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500[/]\n"
            f"[bold {KANTORKU_THEME['primary']}]\u2502[/] [bold]KantorKu v0.9.0[/]  [dim]\u2014  Chat-Driven Office for Coders[/]\n"
            f"[bold {KANTORKU_THEME['primary']}]\u2502[/] [dim]session:[/dim] {self._session_id}  [dim]\u2502[/dim]  [dim]server:[/dim] {self.server_url}\n"
            f"[bold {KANTORKU_THEME['primary']}]\u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500[/]\n"
            f"\n"
            f"[bold]Panels:[/]\n"
            f"  [{KANTORKU_THEME['primary']}]\u258c[/] Left    \u2192 Chat with Manager (just type!)\n"
            f"  [{KANTORKU_THEME['secondary']}]\u258c[/] Center  \u2192 Workers / Briefing / DAG / Events\n"
            f"  [{KANTORKU_THEME['accent']}]\u258c[/] Right   \u2192 Review contracts & Accept/Revise\n"
            f"\n"
            f"[bold {KANTORKU_THEME['success']}]Contract flow:[/]\n"
            f"  Contract \u2192 [{KANTORKU_THEME['success']}]ACCEPT[/] to finalize \u2502 [{KANTORKU_THEME['accent']}]REVISE[/] to change \u2502 [{KANTORKU_THEME['warning']}]DISRUPT[/] to pause\n"
            f"\n"
            f"[dim]Natural language: 'yes'/'ok' = accept, 'revise'/'change X' = revise, 'stop' = disrupt\n"
            f"Shortcuts: Ctrl+P Commands \u2502 Ctrl+A Accept \u2502 Ctrl+R Revise \u2502 Ctrl+I Disrupt \u2502 F1 Help \u2502 Ctrl+Shift+T Theme[/dim]"
        )

        # Hide action buttons initially (no contract)
        self._update_action_buttons()

        # Initialize status bar
        self._update_status_bar()

        # Initialize input mode indicator
        self._update_input_mode_indicator()

        # Initialize action hints
        self._update_action_hints()

        # Initialize lifecycle breadcrumb
        self._update_lifecycle_breadcrumb()

        # Connect to server
        self._connect_and_listen()

    # ── State Machine ────────────────────────────────────────────────

    def _set_contract_state(self, new_state: str) -> None:
        """Centralize ALL contract state transitions.

        Sets self.contract_state, updates ContractDisplay,
        and refreshes UI (action buttons, placeholder, subtitle).
        """
        self.contract_state = new_state
        try:
            cd = self.query_one("#contract-display", ContractDisplay)
            cd.contract_state = new_state
        except NoMatches:
            pass

        # Update thinking indicator
        try:
            indicator = self.query_one("#thinking-indicator", ThinkingIndicator)
            if new_state == ContractState.MANAGER_THINKING:
                indicator.start("Manager thinking")
            else:
                indicator.stop()
        except NoMatches:
            pass

        self._update_action_buttons()
        self._update_input_placeholder()
        self._update_subtitle()
        self._update_status_bar()
        self._update_action_hints()
        self._update_lifecycle_breadcrumb()

    # ── Action Button Management ─────────────────────────────────────

    def _update_action_buttons(self) -> None:
        """Show/hide Accept/Revise buttons based on contract state."""
        try:
            accept_btn = self.query_one("#accept-btn", Button)
            revise_btn = self.query_one("#revise-btn", Button)
        except NoMatches:
            return

        if self.contract_state == ContractState.CONTRACT_PRESENTED:
            accept_btn.display = True
            revise_btn.display = True
            accept_btn.disabled = False
            revise_btn.disabled = False
        elif self.contract_state == ContractState.AWAITING_REVISION:
            # Hide both during revision — user types feedback instead
            accept_btn.display = False
            revise_btn.display = False
        elif self.contract_state == ContractState.WORKING:
            accept_btn.display = False
            revise_btn.display = False
        elif self.contract_state == ContractState.ACCEPTED:
            accept_btn.display = False
            revise_btn.display = False
        else:
            accept_btn.display = False
            revise_btn.display = False

    def _update_input_placeholder(self) -> None:
        """Change input placeholder based on current state."""
        try:
            inp = self.query_one("#chat-input", Input)
        except NoMatches:
            return

        placeholders = {
            ContractState.IDLE: "Talk to Manager...",
            ContractState.MANAGER_THINKING: "Manager is thinking...",
            ContractState.CLARIFYING: "Answer the Manager...",
            ContractState.CONTRACT_PRESENTED: "Type 'yes' to accept / type feedback to revise...",
            ContractState.AWAITING_REVISION: "Write your revision feedback here...",
            ContractState.TEAM_REVIEW: "Team is reviewing...",
            ContractState.TODO_REVIEW: "Team is reviewing tasks...",
            ContractState.CLIENT_FEEDBACK: "Give feedback to Manager...",
            ContractState.WORKING: "Type 'stop' to disrupt / or chat with Manager...",
            ContractState.VERIFYING: "Workers are verifying...",
            ContractState.ACCEPTED: "Contract accepted! Workers starting...",
            ContractState.DONE: "Start a new task...",
            ContractState.FAILED: "Try again or ask Manager...",
        }
        inp.placeholder = placeholders.get(self.contract_state, "Talk to Manager...")

    def _update_subtitle(self) -> None:
        """Update the app subtitle with current state info — coder-style HUD."""
        state_icons = {
            ContractState.IDLE: "\u25cb",           # ○
            ContractState.MANAGER_THINKING: "\u25d0",  # ◐
            ContractState.CLARIFYING: "\u25c7",     # ◇
            ContractState.CONTRACT_PRESENTED: "\u25c8",  # ◈
            ContractState.AWAITING_REVISION: "\u270f",   # ✏
            ContractState.WORKING: "\u26a1",        # ⚡
            ContractState.ACCEPTED: "\u2713",       # ✓
            ContractState.DONE: "\u2713",           # ✓
            ContractState.FAILED: "\u2717",         # ✗
        }
        icon = state_icons.get(self.contract_state, "\u25cb")
        conn = "\u2713" if self.connection_state == "connected" else "\u2717"
        cost_str = f"${self._total_cost:.4f}" if self._total_cost > 0 else ""
        rev_str = f" rev:{self._revision_count}" if self._revision_count > 0 else ""
        self.sub_title = f"{icon} {self.contract_state} | conn:{conn}{rev_str} | {cost_str}"

    def _update_status_bar(self) -> None:
        """Update the enhanced bottom status bar with connection, cost, calls, and phase."""
        try:
            conn_el = self.query_one("#status-conn", Static)
            session_el = self.query_one("#status-session", Static)
            cost_el = self.query_one("#status-cost", Static)
            calls_el = self.query_one("#status-calls", Static)
            phase_el = self.query_one("#status-phase", Static)
        except NoMatches:
            return

        # Connection indicator — green dot if connected, red if not
        if self.connection_state == "connected":
            conn_el.update("\u25cf")  # filled circle (green via CSS)
            conn_el.remove_class("disconnected")
        else:
            conn_el.update("\u25cb")  # empty circle (red via CSS)
            conn_el.add_class("disconnected")

        # Session ID
        session_el.update(f" {self._session_id}")

        # Cost counter
        cost_el.update(f" ${self._total_cost:.4f}")

        # Call count
        calls_el.update(f" {self._total_calls} calls")

        # Phase indicator
        phase_el.update(f" {self.contract_state}")

    # ── Theme Switching ─────────────────────────────────────────────

    def _apply_theme(self, theme_name: str) -> None:
        """Apply a named theme, rebuild CSS, and refresh."""
        theme = get_theme(theme_name)
        self._current_theme = theme_name
        self.CSS = self._build_css(theme)
        self.refresh_css()
        self.notify(f"Theme: {theme_name}", severity="information")

    def action_switch_theme(self) -> None:
        """Ctrl+Shift+T — Cycle through available themes."""
        theme_names = list_themes()
        try:
            idx = theme_names.index(self._current_theme)
            next_idx = (idx + 1) % len(theme_names)
        except ValueError:
            next_idx = 0
        self._apply_theme(theme_names[next_idx])

    # ── Focus Mode ──────────────────────────────────────────────────

    def action_toggle_focus_mode(self) -> None:
        """Ctrl+F — Toggle focus mode (hide center+right, expand left)."""
        self._focus_mode = not self._focus_mode
        try:
            left_panel = self.query_one("#left-panel")
            center_panel = self.query_one("#center-panel")
            right_panel = self.query_one("#right-panel")
        except NoMatches:
            return

        if self._focus_mode:
            center_panel.display = False
            right_panel.display = False
            left_panel.styles.width = "100%"
            self.notify("Focus mode ON", severity="information")
        else:
            center_panel.display = True
            right_panel.display = True
            left_panel.styles.width = "30%"
            self.notify("Focus mode OFF", severity="information")

    # ── Context-Aware Action Hints ──────────────────────────────────

    def _update_action_hints(self) -> None:
        """Update the action hints bar based on current contract state."""
        try:
            hints_el = self.query_one("#action-hints", Static)
        except NoMatches:
            return

        state = self.contract_state
        hints = {
            ContractState.IDLE: "[dim]Type a task... /help for commands  Ctrl+P=Commands  F1=Help[/dim]",
            ContractState.MANAGER_THINKING: "[dim]Manager is thinking...[/dim]",
            ContractState.CLARIFYING: "[dim]Answer the Manager's question...[/dim]",
            ContractState.CONTRACT_PRESENTED: "[bold green]Enter=Accept[/]  [bold yellow]Type feedback=Revise[/]  [dim]Ctrl+A/R[/]",
            ContractState.AWAITING_REVISION: "[bold yellow]Write feedback + Enter[/]  [dim]Esc=Cancel revision[/]",
            ContractState.TEAM_REVIEW: "[dim]Team is reviewing...[/dim]",
            ContractState.TODO_REVIEW: "[dim]Team is reviewing tasks...[/dim]",
            ContractState.CLIENT_FEEDBACK: "[dim]Type to talk to Manager...[/dim]",
            ContractState.WORKING: "[bold yellow]Ctrl+I=Disrupt[/]  [dim]Type to talk to Manager[/]",
            ContractState.VERIFYING: "[dim]Workers are verifying...[/]",
            ContractState.ACCEPTED: "[dim]Workers starting...[/dim]",
            ContractState.DONE: "[dim]Type a new task...[/]",
            ContractState.FAILED: "[dim]Try again or ask Manager...[/]",
        }
        hints_el.update(hints.get(state, "[dim]Type a task...[/dim]"))

    # ── Lifecycle Breadcrumb ────────────────────────────────────────

    def _update_lifecycle_breadcrumb(self) -> None:
        """Update the lifecycle breadcrumb showing contract phases."""
        try:
            bc_el = self.query_one("#lifecycle-breadcrumb", Static)
        except NoMatches:
            return

        phases = [
            ("IDLE", "idle"),
            ("THINKING", "manager_thinking"),
            ("CONTRACT", "contract_presented"),
            ("REVIEW", "awaiting_revision"),
            ("WORKING", "working"),
            ("VERIFYING", "verifying"),
            ("DONE", "done"),
        ]

        # Map contract states to phase index
        state_to_phase = {
            ContractState.IDLE: 0,
            ContractState.MANAGER_THINKING: 1,
            ContractState.CLARIFYING: 1,
            ContractState.CONTRACT_PRESENTED: 2,
            ContractState.AWAITING_REVISION: 3,
            ContractState.TEAM_REVIEW: 3,
            ContractState.TODO_REVIEW: 3,
            ContractState.CLIENT_FEEDBACK: 3,  # Feedback during review phase
            ContractState.WORKING: 4,
            ContractState.ACCEPTED: 4,
            ContractState.VERIFYING: 5,
            ContractState.DONE: 6,
            ContractState.FAILED: 6,  # Failed is also a terminal state → DONE phase
        }

        current_idx = state_to_phase.get(self.contract_state, 0)
        is_failed = self.contract_state == ContractState.FAILED

        parts = []
        for i, (label, _state) in enumerate(phases):
            if i < current_idx:
                parts.append(f"[green]\u2713 {label}[/green]")
            elif i == current_idx:
                if is_failed:
                    parts.append(f"[bold red]\u2717 FAILED[/]")
                else:
                    parts.append(f"[bold {KANTORKU_THEME['primary']}]\u25b6 {label}[/]")
            else:
                parts.append(f"[dim]{label}[/dim]")

        bc_el.update(f" \u2502 ".join(parts))

    # ── Multi-line Input Mode ────────────────────────────────────────

    def _update_input_mode_indicator(self) -> None:
        """Update the mode indicator showing current input mode."""
        try:
            indicator = self.query_one("#input-mode-indicator", Static)
        except NoMatches:
            return

        if self._multiline_mode:
            indicator.update(
                f"[bold {KANTORKU_THEME['accent']}][MULTI][/bold {KANTORKU_THEME['accent']}] "
                f"Ctrl+Enter to send | Ctrl+M to toggle"
            )
            # Change input border to accent color for visual distinction
            try:
                multi_input = self.query_one("#multiline-input", TextArea)
                multi_input.add_class("multiline-active")
            except NoMatches:
                pass
        else:
            indicator.update("[dim]Single-line | Ctrl+M to toggle[/dim]")
            # Remove active styling
            try:
                multi_input = self.query_one("#multiline-input", TextArea)
                multi_input.remove_class("multiline-active")
            except NoMatches:
                pass

    def action_toggle_multiline(self) -> None:
        """Ctrl+M — Toggle between single-line Input and multi-line TextArea."""
        self._multiline_mode = not self._multiline_mode

        try:
            single_input = self.query_one("#chat-input", Input)
            multi_input = self.query_one("#multiline-input", TextArea)
        except NoMatches:
            return

        if self._multiline_mode:
            # Transfer value from single-line to multi-line
            current_text = single_input.value
            single_input.display = False
            multi_input.display = True
            multi_input.load_text(current_text)
            multi_input.focus()
        else:
            # Transfer value from multi-line to single-line
            current_text = multi_input.text
            multi_input.display = False
            single_input.display = True
            single_input.value = current_text.replace("\n", " ")
            single_input.focus()

        self._update_input_mode_indicator()

    def on_key(self, event: Any) -> None:
        """Handle key events — intercept Ctrl+Enter in multi-line mode."""
        if self._multiline_mode and event.key == "ctrl+enter":
            try:
                multi_input = self.query_one("#multiline-input", TextArea)
            except NoMatches:
                return

            text = multi_input.text.strip()
            if text:
                multi_input.load_text("")
                # Process the text the same way as Input.Submitted
                asyncio.create_task(self._process_input_text(text))
            event.prevent_default()
            event.stop()

    async def _process_input_text(self, text: str) -> None:
        """Process input text from either Input or TextArea."""
        # Add to history
        self._input_history.append(text)
        self._history_index = -1

        # Check for slash commands first
        if text.startswith("/"):
            result = await self._handle_slash_command_with_confirm(text)
            if result:
                self._add_manager_message(result)
            return

        # ── Check for natural language actions ──

        # If in awaiting_revision state, ANY input is revision feedback
        if self.contract_state == ContractState.AWAITING_REVISION:
            self._add_manager_message(f"[bold]You (revision):[/bold] {text}")
            await self._send_revise(text)
            return

        nl_action = parse_nl_action(text, self.contract_state)

        if nl_action == "accept":
            self._add_manager_message(f"[bold]You:[/bold] {text}  \u2192 [green]Accepting contract[/green]")
            await self._send_accept()
            return

        if nl_action == "revise":
            # Extract feedback: strip the action word, keep the rest
            feedback = text
            for prefix in ("revise", "change", "modify", "update", "alter", "redo",
                          "no", "nope", "nah", "reject", "deny", "not quite", "not really"):
                if feedback.lower().startswith(prefix):
                    remainder = feedback[len(prefix):].strip()
                    if remainder:
                        feedback = remainder
                    break
            self._add_manager_message(f"[bold]You:[/bold] {text}  \u2192 [yellow]Requesting revision[/yellow]")
            await self._send_revise(feedback if feedback != text else text)
            return

        if nl_action == "interrupt":
            self._add_manager_message(f"[bold]You:[/bold] {text}  \u2192 [yellow]Disrupting work[/yellow]")
            self._do_disrupt()
            return

        # Send as regular message to Manager
        self._add_manager_message(f"[bold]You:[/bold] {text}")
        await self._send_message(text)

    # ── Connection & Background Workers ─────────────────────────────

    @work(exclusive=True, name="connect_and_listen")
    async def _connect_and_listen(self) -> None:
        """Connect to server and start listening for events."""
        try:
            await self._connection.connect()
            self.connection_state = "connected"
            self._add_manager_message("[green]\u2713 Connected to server[/green]")
            self._update_subtitle()
            self._update_status_bar()

            # Start event listener
            self._event_listener_running = True
            await self._listen_office_events()

        except ConnectionError as e:
            self.connection_state = "error"
            self._add_manager_message(
                f"[red]\u2717 Connection failed: {e}[/red]\n"
                f"[dim]Retrying in {self._reconnect_delay}s...[/dim]"
            )
            self._update_subtitle()
            self._update_status_bar()
            await self._auto_reconnect()
        except Exception as e:
            self.connection_state = "error"
            self._add_manager_message(f"[red]Error: {e}[/red]")
            self._update_subtitle()
            self._update_status_bar()

    async def _listen_office_events(self) -> None:
        """Listen to the office event stream and route to panels."""
        try:
            async for event in self._connection.listen_events():
                if not self._event_listener_running:
                    break
                self._route_office_event(event)
        except Exception as e:
            if self._event_listener_running:
                self._add_manager_message(f"[yellow]Event stream ended: {e}[/yellow]")

    def _route_office_event(self, event: dict[str, Any]) -> None:
        """Route an office event to the appropriate panel."""
        event_type = event.get("type", "")

        # ── Workers Live Stream (center panel - Workers tab) ──
        try:
            workers_live = self.query_one("#workers-live", WorkersLiveStream)
            workers_live.add_event(event)
        except NoMatches:
            pass

        # ── Briefing Panel (center panel - Briefing tab) ──
        briefing_types = {
            "briefing_opened", "worker_speak_up", "manager_brainstorming",
            "plan_drafted", "plan_revised",
        }
        if event_type in briefing_types:
            try:
                briefing_panel = self.query_one("#briefing-panel", BriefingPanel)
                briefing_panel.add_event(event)
            except NoMatches:
                pass

        # ── DAG Panel (center panel - DAG tab) ──
        dag_types = {"task_assigned", "task_done", "task_failed"}
        if event_type in dag_types:
            try:
                dag_panel = self.query_one("#dag-panel", DAGPanel)
                dag_panel.add_event(event)
            except NoMatches:
                pass

        # ── Event Log Panel (center panel - Events tab) ── ALL events
        try:
            events_panel = self.query_one("#events-panel", EventLogPanel)
            events_panel.add_event(event)
        except NoMatches:
            pass

        # Update phase based on event type
        phase_map = {
            "briefing_opened": "briefing",
            "plan_drafted": "briefing",
            "worker_speak_up": "briefing",
            "contract_accepted": "execution",
            "task_assigned": "execution",
            "task_started": "execution",
            "task_done": "execution",
            "task_failed": "execution",
            "verify_design_start": "verification",
            "verify_engineer_start": "verification",
            "revision_requested": "briefing",
            "manager_brainstorming": "briefing",
        }
        new_phase = phase_map.get(event_type)
        if new_phase:
            try:
                workers_live = self.query_one("#workers-live", WorkersLiveStream)
                workers_live._phase = new_phase
            except NoMatches:
                pass

        # Right panel: contract state updates
        contract_events = {
            "contract_ready", "contract_accepted", "work_started",
            "work_done", "plan_drafted", "plan_revised",
        }
        if event_type in contract_events:
            self._handle_contract_event(event)

        # Manager messages go to left panel
        if event_type == "manager_message":
            content = event.get("content", "")
            self._add_manager_message(f"[bold green]Manager:[/bold green] {content}")

        elif event_type == "manager_question":
            content = event.get("content", "")
            self._add_manager_message(f"[bold yellow]Manager asks:[/bold yellow] {content}")

        elif event_type == "work_done":
            result = event.get("result", {})
            self._set_contract_state("done")
            try:
                cd = self.query_one("#contract-display", ContractDisplay)
                cd.work_result = result
                workers_live = self.query_one("#workers-live", WorkersLiveStream)
                workers_live._phase = "done"
                workers_live.add_system_message("\u2705 All work complete!", "green bold")
            except NoMatches:
                pass
            self._add_manager_message("[bold green]\u2713 Work complete![/bold green]")
            self.notify("Work complete!", severity="information")

        elif event_type == "error":
            msg = event.get("message", "Unknown error")
            self._add_manager_message(f"[red bold]\u2717 Error: {msg}[/red bold]")

        # ── Notification/Toast System ──
        # Track cost updates from events and send notifications
        elif event_type == "circuit_open":
            provider = event.get("provider", "?")
            self.notify(f"Circuit OPEN: {provider}", severity="error")

        elif event_type == "circuit_closed":
            provider = event.get("provider", "?")
            self.notify(f"Circuit closed: {provider}", severity="information")

        elif event_type == "cost_warning":
            cost = event.get("cost_usd", 0)
            if cost:
                self._total_cost = cost
            msg = event.get("message", "Cost threshold approached")
            self.notify(f"Cost: {msg}", severity="warning")
            self._update_subtitle()
            self._update_status_bar()

        elif event_type == "worker_hired":
            worker_id = event.get("worker_id", "?")
            self.notify(f"Hired: {worker_id}", severity="information")

        elif event_type == "worker_fired":
            worker_id = event.get("worker_id", "?")
            self.notify(f"Fired: {worker_id}", severity="information")

        elif event_type == "rate_limit_hit":
            provider = event.get("provider", "?")
            self._total_calls += 1
            self._update_status_bar()

    def _handle_contract_event(self, event: dict[str, Any]) -> None:
        """Handle contract-related events — update right panel."""
        event_type = event.get("type", "")

        if event_type == "contract_ready":
            contract = event.get("contract", {})
            try:
                cd = self.query_one("#contract-display", ContractDisplay)
                cd.contract_data = contract
                cd.revision_count = self._revision_count
            except NoMatches:
                pass
            self.pending_contract = contract
            self._set_contract_state("contract_presented")
            self.notify("Contract ready! Review in right panel", severity="information")

            if self._revision_count > 0:
                self._add_manager_message(
                    f"[bold cyan]\U0001f4cb Revised contract ready! (Rev #{self._revision_count})[/bold cyan]\n"
                    f"Review it in the right panel.\n"
                    f"[bold green]Click \u2713 ACCEPT[/bold green] to finalize  |  "
                    f"[bold yellow]Click \u270f REVISE[/bold yellow] to request more changes\n"
                    f"[dim]Or type 'yes'/'ok' to accept, or type feedback to revise[/dim]"
                )
            else:
                self._add_manager_message(
                    f"[bold cyan]\U0001f4cb Contract ready![/bold cyan] "
                    f"Review it in the right panel.\n"
                    f"[bold green]Click \u2713 ACCEPT[/bold green] to finalize  |  "
                    f"[bold yellow]Click \u270f REVISE[/bold yellow] to request changes\n"
                    f"[dim]Or type 'yes'/'ok' to accept, or type feedback to revise[/dim]"
                )

        elif event_type == "contract_accepted":
            self._set_contract_state("accepted")

        elif event_type == "work_started":
            self._set_contract_state("working")

        elif event_type == "work_done":
            result = event.get("result", {})
            self._set_contract_state("done")
            try:
                cd = self.query_one("#contract-display", ContractDisplay)
                cd.work_result = result
                workers_live = self.query_one("#workers-live", WorkersLiveStream)
                workers_live._phase = "done"
                workers_live.add_system_message("\u2705 All work complete!", "green bold")
            except NoMatches:
                pass
            self._add_manager_message("[bold green]\u2713 Work complete![/bold green]")

    # ── Input Handling ──────────────────────────────────────────────

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input — parse NL actions, slash commands, or chat."""
        if event.input.id != "chat-input":
            return

        text = event.value.strip()
        if not text:
            return

        # Clear input
        event.input.value = ""

        await self._process_input_text(text)

    async def _handle_slash_command_with_confirm(self, text: str) -> str | None:
        """Handle slash commands, with confirmation for destructive ones."""
        parts = text[1:].split(None, 1)
        cmd_name = parts[0].lower() if parts else ""
        args = parts[1] if len(parts) > 1 else ""

        # Check if this is a destructive command requiring confirmation
        if cmd_name in self.DESTRUCTIVE_COMMANDS:
            self._pending_destructive_cmd = cmd_name
            self._pending_destructive_args = args
            # Push confirm dialog
            confirm_msg = f"Are you sure you want to /{cmd_name}?"
            if cmd_name == "fire" and args:
                confirm_msg = f"Are you sure you want to fire worker '{args}'?"
            elif cmd_name == "reset":
                confirm_msg = "Are you sure you want to reset the session? This cannot be undone."
            elif cmd_name == "queue-purge":
                confirm_msg = "Are you sure you want to purge the task queue?"

            def _on_confirm(confirmed: bool) -> None:
                if confirmed:
                    asyncio.create_task(self._execute_destructive_command())
                else:
                    self._add_manager_message("[dim]Cancelled.[/dim]")
                    self._pending_destructive_cmd = None
                    self._pending_destructive_args = ""

            self.push_screen(ConfirmDialog(confirm_msg), _on_confirm)
            return None

        # Handle /briefing command — switch to Briefing tab
        if cmd_name == "briefing":
            try:
                tabs = self.query_one("#center-tabs", TabbedContent)
                tabs.active = "briefing-tab"
            except NoMatches:
                pass

        # Handle /dag command — switch to DAG tab
        if cmd_name == "dag":
            try:
                tabs = self.query_one("#center-tabs", TabbedContent)
                tabs.active = "dag-tab"
            except NoMatches:
                pass

        # Non-destructive: execute normally
        return await handle_slash_command(text, self)

    async def _execute_destructive_command(self) -> None:
        """Execute a confirmed destructive command."""
        cmd_name = self._pending_destructive_cmd
        args = self._pending_destructive_args
        self._pending_destructive_cmd = None
        self._pending_destructive_args = ""

        if not cmd_name:
            return

        text = f"/{cmd_name}" + (f" {args}" if args else "")
        result = await handle_slash_command(text, self)
        if result:
            self._add_manager_message(result)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "disrupt-btn":
            self._do_disrupt()
        elif event.button.id == "accept-btn":
            self._add_manager_message("[bold green]\u2713 Accepting contract...[/bold green]")
            asyncio.create_task(self._send_accept())
        elif event.button.id == "revise-btn":
            # Enter revision mode — user will type feedback in the chat input
            self._enter_revision_mode()

    # ── Revision Mode ───────────────────────────────────────────────

    def _enter_revision_mode(self) -> None:
        """Enter revision mode — prompt user for feedback.

        When REVISE is clicked:
        1. Contract state → awaiting_revision
        2. Hide Accept/Revise buttons
        3. Change input placeholder to "Write your revision feedback..."
        4. Focus the input field
        5. User types feedback → _send_revise() → Manager brainstorms → new contract
        """
        if not self.pending_contract:
            self._add_manager_message("[yellow]No contract to revise yet. Chat with the Manager first![/yellow]")
            return

        self._set_contract_state("awaiting_revision")

        self._add_manager_message(
            "[bold yellow]\u270f\ufe0f REVISE MODE[/bold yellow]\n"
            "[yellow]Write your revision feedback below and press Enter.[/yellow]\n"
            "[dim]The Manager will brainstorm with the workers and present a new contract.[/dim]"
        )

        # Focus the input
        if self._multiline_mode:
            try:
                multi_input = self.query_one("#multiline-input", TextArea)
                multi_input.focus()
            except NoMatches:
                pass
        else:
            try:
                inp = self.query_one("#chat-input", Input)
                inp.focus()
            except NoMatches:
                pass

    # ── Key Bindings ────────────────────────────────────────────────

    def action_accept_contract(self) -> None:
        """Ctrl+A — Accept current contract."""
        if self.contract_state in (ContractState.CONTRACT_PRESENTED, ContractState.AWAITING_REVISION):
            asyncio.create_task(self._send_accept())
        else:
            self._add_manager_message("[yellow]No contract to accept yet. Chat with the Manager first![/yellow]")

    def action_revise_contract(self) -> None:
        """Ctrl+R — Enter revision mode."""
        if self.contract_state == ContractState.CONTRACT_PRESENTED:
            self._enter_revision_mode()
        else:
            self._add_manager_message("[yellow]No contract to revise yet.[/yellow]")

    def action_disrupt(self) -> None:
        """Ctrl+I — Disrupt current work and talk to Manager."""
        self._do_disrupt()

    def action_show_shortcuts(self) -> None:
        """F1 — Show keyboard shortcuts cheatsheet."""
        self.push_screen(ShortcutsScreen())

    def _do_disrupt(self) -> None:
        """Disrupt current work — pause and talk to Manager."""
        if self.contract_state in (ContractState.WORKING, ContractState.TEAM_REVIEW, ContractState.TODO_REVIEW, ContractState.VERIFYING, ContractState.ACCEPTED):
            self._add_manager_message(
                "[bold yellow]\u26a1 DISRUPT \u2014 Pausing work to talk to Manager[/bold yellow]"
            )
            self._set_contract_state("client_feedback")
            try:
                workers_live = self.query_one("#workers-live", WorkersLiveStream)
                workers_live.add_system_message(
                    "\u26a1 DISRUPT \u2014 Client paused work for discussion", "yellow bold"
                )
            except NoMatches:
                pass
        else:
            self._add_manager_message(
                "[dim]No active work to disrupt. Just type your message![/dim]"
            )

    def action_focus_next_panel(self) -> None:
        """Tab — Cycle focus between panels."""
        focused = self.focused
        if focused and focused.id == "chat-input":
            try:
                tabs = self.query_one("#center-tabs", TabbedContent)
                tabs.focus()
            except NoMatches:
                pass
        elif focused and hasattr(focused, 'id') and ('workers' in str(focused.id) or 'tab' in str(focused.id).lower()):
            self.query_one("#contract-scroll").focus()
        else:
            self.query_one("#chat-input").focus()

    def action_history_up(self) -> None:
        """Up arrow — Navigate input history."""
        if not self._input_history:
            return
        if self._history_index < len(self._input_history) - 1:
            self._history_index += 1
            idx = len(self._input_history) - 1 - self._history_index
            if self._multiline_mode:
                try:
                    multi_input = self.query_one("#multiline-input", TextArea)
                    multi_input.load_text(self._input_history[idx])
                except NoMatches:
                    pass
            else:
                try:
                    inp = self.query_one("#chat-input", Input)
                    inp.value = self._input_history[idx]
                except NoMatches:
                    pass

    def action_history_down(self) -> None:
        """Down arrow — Navigate input history."""
        if self._history_index > 0:
            self._history_index -= 1
            idx = len(self._input_history) - 1 - self._history_index
            if self._multiline_mode:
                try:
                    multi_input = self.query_one("#multiline-input", TextArea)
                    multi_input.load_text(self._input_history[idx])
                except NoMatches:
                    pass
            else:
                try:
                    inp = self.query_one("#chat-input", Input)
                    inp.value = self._input_history[idx]
                except NoMatches:
                    pass
        elif self._history_index == 0:
            self._history_index = -1
            if self._multiline_mode:
                try:
                    multi_input = self.query_one("#multiline-input", TextArea)
                    multi_input.load_text("")
                except NoMatches:
                    pass
            else:
                try:
                    inp = self.query_one("#chat-input", Input)
                    inp.value = ""
                except NoMatches:
                    pass

    def action_cancel_input(self) -> None:
        """Ctrl+C — Cancel current input or streaming."""
        if self._multiline_mode:
            try:
                multi_input = self.query_one("#multiline-input", TextArea)
                multi_input.load_text("")
            except NoMatches:
                pass
        else:
            try:
                inp = self.query_one("#chat-input", Input)
                inp.value = ""
            except NoMatches:
                pass

        # If in revision mode, cancel back to contract_presented
        if self.contract_state == ContractState.AWAITING_REVISION:
            self._set_contract_state("contract_presented")
            self._add_manager_message("[dim]Revision cancelled. Accept/Revise buttons are back.[/dim]")

    # ── Message Sending ─────────────────────────────────────────────

    async def _send_message(self, message: str) -> None:
        """Send a message to the Manager via WebSocket."""
        self._set_contract_state("manager_thinking")

        try:
            async for event in self._connection.send_message(message):
                event_type = event.get("type", "")

                if event_type == "manager_message":
                    content = event.get("content", "")
                    self._add_manager_message(
                        f"[bold green]Manager:[/bold green] {content}"
                    )
                    self._set_contract_state("clarifying")

                elif event_type == "manager_question":
                    content = event.get("content", "")
                    self._add_manager_message(
                        f"[bold yellow]Manager asks:[/bold yellow] {content}"
                    )

                elif event_type == "contract_ready":
                    contract = event.get("contract", {})
                    self.pending_contract = contract
                    try:
                        cd = self.query_one("#contract-display", ContractDisplay)
                        cd.contract_data = contract
                        cd.revision_count = self._revision_count
                    except NoMatches:
                        pass
                    self._set_contract_state("contract_presented")
                    self._add_manager_message(
                        f"[bold cyan]\U0001f4cb Contract ready![/bold cyan] "
                        f"Review in right panel.\n"
                        f"[bold green]Click \u2713 ACCEPT[/bold green] to finalize  |  "
                        f"[bold yellow]Click \u270f REVISE[/bold yellow] to request changes"
                    )
                    self.notify("Contract ready! Review in right panel", severity="information")
                    # Auto-accept if /code or /run requested it
                    if getattr(self, '_auto_accept_pending', False):
                        self._auto_accept_pending = False
                        asyncio.create_task(self._send_accept())

                elif event_type == "error":
                    msg = event.get("message", "Unknown error")
                    self._add_manager_message(f"[red bold]\u2717 {msg}[/red bold]")

        except ConnectionError as e:
            self._add_manager_message(
                f"[red]Connection lost: {e}[/red]\n"
                f"[dim]Will try to reconnect...[/dim]"
            )
            self.connection_state = "disconnected"
            self._update_subtitle()
            self._update_status_bar()
            await self._auto_reconnect()

    async def _send_accept(self) -> None:
        """Accept the current contract — finalize and display in right panel.

        When Accept is clicked:
        1. Contract state → accepted
        2. Right panel shows the contract with "CONTRACT ACCEPTED" status
        3. Accept/Revise buttons hidden
        4. Workers begin execution (state → working)
        """
        if not self.pending_contract:
            self._add_manager_message("[yellow]No contract to accept.[/yellow]")
            return

        # Reset revision count for next contract cycle
        self._revision_count = 0

        self._add_manager_message(
            "[bold green]\u2713 Contract accepted! Workers are starting...[/bold green]"
        )

        # Show ACCEPTED state in right panel
        try:
            cd = self.query_one("#contract-display", ContractDisplay)
            cd.revision_count = 0
        except NoMatches:
            pass
        self._set_contract_state("accepted")

        try:
            workers_live = self.query_one("#workers-live", WorkersLiveStream)
            workers_live.add_system_message(
                "\u2713 Contract accepted \u2014 Briefing room opening...", "green bold"
            )
            workers_live._phase = "briefing"
        except NoMatches:
            pass

        # Send accept to server
        result = await self._connection.accept_contract()

        if result and result.get("type") == "error":
            self._add_manager_message(f"[red]Accept failed: {result.get('message', '')}[/red]")
            self._set_contract_state("contract_presented")
        elif result:
            # Transition to working state — do NOT set "done" immediately;
            # the work_done event will handle that transition.
            self._set_contract_state("working")

    async def _send_revise(self, feedback: str) -> None:
        """Request a contract revision.

        When Revise is triggered:
        1. Increment revision counter
        2. Send revision feedback to Manager
        3. Manager brainstorms with workers (shown in center panel)
        4. Manager asks clarifying questions if needed
        5. New contract presented with Accept/Revise buttons again
        """
        if not self.pending_contract:
            self._add_manager_message("[yellow]No contract to revise.[/yellow]")
            return

        self._revision_count += 1
        self._revision_feedback = feedback

        self._add_manager_message(
            f"[bold yellow]\u21bb Requesting revision (#{self._revision_count}):[/bold yellow] {feedback}"
        )

        # Show brainstorming in center panel
        try:
            workers_live = self.query_one("#workers-live", WorkersLiveStream)
            workers_live.add_system_message(
                f"\u270f\ufe0f Revision #{self._revision_count}: {feedback[:60]}", "yellow bold"
            )
            workers_live.add_event({
                "type": "revision_requested",
                "feedback": feedback,
            })
            workers_live.add_event({
                "type": "manager_brainstorming",
            })
            workers_live._phase = "briefing"
        except NoMatches:
            pass

        # Also add to briefing panel
        try:
            briefing_panel = self.query_one("#briefing-panel", BriefingPanel)
            briefing_panel.add_event({
                "type": "manager_brainstorming",
            })
        except NoMatches:
            pass

        # Set state to clarifying (Manager is thinking about revision)
        try:
            cd = self.query_one("#contract-display", ContractDisplay)
            cd.revision_count = self._revision_count
        except NoMatches:
            pass
        self._set_contract_state("manager_thinking")

        # Send revision request to server
        async for event in self._connection.revise_contract(feedback):
            event_type = event.get("type", "")

            if event_type == "manager_message":
                content = event.get("content", "")
                self._add_manager_message(
                    f"[bold green]Manager:[/bold green] {content}"
                )

            elif event_type == "manager_question":
                content = event.get("content", "")
                self._add_manager_message(
                    f"[bold yellow]Manager asks:[/bold yellow] {content}"
                )
                # Manager is asking a question — set to clarifying
                self._set_contract_state("clarifying")

            elif event_type == "contract_ready":
                contract = event.get("contract", {})
                self.pending_contract = contract
                try:
                    cd = self.query_one("#contract-display", ContractDisplay)
                    cd.contract_data = contract
                    cd.revision_count = self._revision_count
                except NoMatches:
                    pass
                self._set_contract_state("contract_presented")
                self._add_manager_message(
                    f"[bold cyan]\U0001f4cb Revised contract ready! (Rev #{self._revision_count})[/bold cyan]\n"
                    f"Review it in the right panel.\n"
                    f"[bold green]Click \u2713 ACCEPT[/bold green] to finalize  |  "
                    f"[bold yellow]Click \u270f REVISE[/bold yellow] for more changes"
                )
                self.notify("Contract ready! Review in right panel", severity="information")

            elif event_type == "error":
                msg = event.get("message", "Unknown error")
                self._add_manager_message(f"[red]\u2717 {msg}[/red]")

    # ── Helpers ─────────────────────────────────────────────────────

    def _add_manager_message(self, content: str) -> None:
        """Add a message to the Manager chat log (left panel)."""
        try:
            log = self.query_one("#manager-log", RichLog)
            log.write(Text.from_markup(content))
        except NoMatches:
            pass

    async def _auto_reconnect(self) -> None:
        """Attempt to reconnect with exponential backoff."""
        while self._reconnect_attempts < self._max_reconnect_attempts:
            self._reconnect_attempts += 1
            delay = self._reconnect_delay * (2 ** (self._reconnect_attempts - 1))
            self._add_manager_message(
                f"[dim]Reconnecting ({self._reconnect_attempts}/{self._max_reconnect_attempts}) "
                f"in {delay:.0f}s...[/dim]"
            )
            await asyncio.sleep(delay)

            try:
                await self._connection.connect()
                self.connection_state = "connected"
                self._reconnect_attempts = 0
                self._update_subtitle()  # Set connection_state BEFORE subtitle
                self._update_status_bar()
                self._add_manager_message("[green]\u2713 Reconnected![/green]")
                # Restart event listener
                self._event_listener_running = True
                await self._listen_office_events()
                return
            except ConnectionError:
                continue
            except Exception:
                continue

        self._add_manager_message(
            f"[red bold]\u2717 Could not reconnect after {self._max_reconnect_attempts} attempts.[/red bold]\n"
            f"[dim]Check your server and restart the TUI.[/dim]"
        )

    # ── Embedded Mode Support ──────────────────────────────────────

    def _update_embedded_status(self) -> None:
        """Update panels with embedded office data."""
        office = getattr(self, '_office', None)
        if not office:
            return

        try:
            # Update worker status in the workers live stream panel
            if hasattr(office, 'get_worker_status'):
                workers = office.get_worker_status()
                try:
                    wls = self.query_one("#workers-live", WorkersLiveStream)
                    if hasattr(wls, '_workers_status'):
                        wls._workers_status = {
                            w.get("id", f"worker-{i}"): w
                            for i, w in enumerate(workers)
                        }
                except NoMatches:
                    pass

            # Update pool status
            if hasattr(office, 'get_pool_status'):
                pool = office.get_pool_status()

            # Update cost
            if hasattr(office, 'cost_tracker') and office.cost_tracker:
                cost = office.cost_tracker.get_report()
                if cost:
                    self._total_cost = cost.get("total_cost_usd", 0)
                    self._total_calls = cost.get("total_calls", 0)
                    self._update_subtitle()
                    self._update_status_bar()

        except NoMatches:
            pass


class EmbeddedKantorKuTUI(KantorKuTUI):
    """
    KantorKu TUI in embedded mode — runs Office in-process.

    No server needed. Everything runs locally.
    Same chat-driven UX as remote mode.
    """

    def __init__(self, config_path: str | None = None, **kwargs: Any) -> None:
        super().__init__(server_url="embedded", config_path=config_path, **kwargs)
        self._office: Any = None

    @work(exclusive=True, name="embedded_init")
    async def _connect_and_listen(self) -> None:
        """Initialize embedded Office instead of connecting to server."""
        try:
            from kantorku.office import Office

            self._add_manager_message("[bold cyan]Starting embedded Office...[/bold cyan]")

            if self.config_path:
                self._office = Office.from_config(self.config_path)
            else:
                self._office = Office()

            await self._office.initialize()
            self.connection_state = "connected"
            self._add_manager_message(
                "[green]\u2713 Embedded Office initialized![/green]\n"
                f"[dim]Workers: {len(self._office.registry.all_worker_ids)}[/dim]"
            )
            self._update_subtitle()
            self._update_status_bar()

            # Subscribe to event bus
            self._event_listener_running = True
            await self._listen_embedded_events()

        except Exception as e:
            self.connection_state = "error"
            self._add_manager_message(f"[red bold]\u2717 Failed to start: {e}[/red bold]")
            self._update_subtitle()
            self._update_status_bar()
            # Auto-reconnect for embedded mode
            await self._embedded_reconnect()

    async def _embedded_reconnect(self) -> None:
        """Attempt to reinitialize the embedded Office on failure.

        Uses exponential backoff: 2s, 4s, 8s, 16s, 32s (capped at 60s).
        This prevents spam-reconnect when the Office crashes repeatedly.
        """
        max_attempts = 5
        base_delay = 2.0
        max_delay = 60.0
        for attempt in range(1, max_attempts + 1):
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            self._add_manager_message(
                f"[dim]Retrying embedded init ({attempt}/{max_attempts}) in {delay:.0f}s...[/dim]"
            )
            await asyncio.sleep(delay)
            try:
                from kantorku.office import Office
                if self.config_path:
                    self._office = Office.from_config(self.config_path)
                else:
                    self._office = Office()
                await self._office.initialize()
                self.connection_state = "connected"
                self._add_manager_message("[green]\u2713 Embedded Office reconnected![/green]")
                self._update_subtitle()
                self._update_status_bar()
                self._event_listener_running = True
                await self._listen_embedded_events()
                return
            except Exception as e:
                self._add_manager_message(f"[red]Retry {attempt} failed: {e}[/red]")
        self._add_manager_message(
            "[red bold]\u2717 Could not initialize embedded Office after retries.[/red bold]\n"
            "[dim]Check your config and restart.[/dim]"
        )

    async def _listen_embedded_events(self) -> None:
        """Listen to embedded office events."""
        if not self._office:
            return

        bus = self._office.bus
        session_id = self._session_id

        try:
            async with bus.subscribe(session_id) as events:
                async for event in events:
                    if not self._event_listener_running:
                        break
                    self._route_office_event(event.to_dict())
        except Exception as e:
            if self._event_listener_running:
                self._add_manager_message(f"[yellow]Event stream ended: {e}[/yellow]")
                # Attempt reconnect if stream ended unexpectedly
                await self._embedded_reconnect()

    async def _send_message(self, message: str) -> None:
        """Send message using embedded Office."""
        if not self._office:
            self._add_manager_message("[red]Office not initialized[/red]")
            return

        self._set_contract_state("manager_thinking")

        try:
            async for event in self._office.chat(self._session_id, message):
                event_type = event.get("type", "")

                if event_type == "manager_message":
                    content = event.get("content", "")
                    self._add_manager_message(
                        f"[bold green]Manager:[/bold green] {content}"
                    )
                    self._set_contract_state("clarifying")

                elif event_type == "manager_question":
                    content = event.get("content", "")
                    self._add_manager_message(
                        f"[bold yellow]Manager asks:[/bold yellow] {content}"
                    )

                elif event_type == "contract_ready":
                    contract = event.get("contract", {})
                    self.pending_contract = contract
                    try:
                        cd = self.query_one("#contract-display", ContractDisplay)
                        cd.contract_data = contract
                        cd.revision_count = self._revision_count
                    except NoMatches:
                        pass
                    self._set_contract_state("contract_presented")
                    self._add_manager_message(
                        f"[bold cyan]\U0001f4cb Contract ready![/bold cyan] "
                        f"Review in right panel.\n"
                        f"[bold green]Click \u2713 ACCEPT[/bold green] to finalize  |  "
                        f"[bold yellow]Click \u270f REVISE[/bold yellow] for changes"
                    )
                    self.notify("Contract ready! Review in right panel", severity="information")
                    # Auto-accept if /code or /run requested it
                    if getattr(self, '_auto_accept_pending', False):
                        self._auto_accept_pending = False
                        asyncio.create_task(self._send_accept())

                elif event_type == "error":
                    msg = event.get("message", "Unknown error")
                    self._add_manager_message(f"[red bold]\u2717 {msg}[/red bold]")

        except Exception as e:
            self._add_manager_message(f"[red]Error: {e}[/red]")

    async def _send_accept(self) -> None:
        """Accept contract using embedded Office."""
        if not self._office:
            self._add_manager_message("[red]Office not initialized[/red]")
            return

        if not self.pending_contract:
            self._add_manager_message("[yellow]No contract to accept.[/yellow]")
            return

        self._revision_count = 0

        self._add_manager_message(
            "[bold green]\u2713 Contract accepted! Workers are starting...[/bold green]"
        )

        # Show ACCEPTED state
        try:
            cd = self.query_one("#contract-display", ContractDisplay)
            cd.revision_count = 0
        except NoMatches:
            pass
        self._set_contract_state("accepted")

        try:
            workers_live = self.query_one("#workers-live", WorkersLiveStream)
            workers_live.add_system_message(
                "\u2713 Contract accepted \u2014 Briefing room opening...", "green bold"
            )
            workers_live._phase = "briefing"
        except NoMatches:
            pass

        try:
            result = await self._office.accept_contract(self._session_id)

            if result and result.get("type") == "error":
                self._add_manager_message(f"[red]Accept failed: {result.get('message', '')}[/red]")
                self._set_contract_state("contract_presented")
            elif result:
                # Transition to working — do NOT set "done" immediately;
                # the work_done event will handle that transition.
                self._set_contract_state("working")

        except Exception as e:
            self._add_manager_message(f"[red]Accept error: {e}[/red]")

    async def _send_revise(self, feedback: str) -> None:
        """Request contract revision using embedded Office."""
        if not self._office:
            self._add_manager_message("[red]Office not initialized[/red]")
            return

        if not self.pending_contract:
            self._add_manager_message("[yellow]No contract to revise.[/yellow]")
            return

        self._revision_count += 1

        self._add_manager_message(
            f"[bold yellow]\u21bb Requesting revision (#{self._revision_count}):[/bold yellow] {feedback}"
        )

        # Show brainstorming in center panel
        try:
            workers_live = self.query_one("#workers-live", WorkersLiveStream)
            workers_live.add_system_message(
                f"\u270f\ufe0f Revision #{self._revision_count}: {feedback[:60]}", "yellow bold"
            )
            workers_live.add_event({
                "type": "revision_requested",
                "feedback": feedback,
            })
            workers_live.add_event({
                "type": "manager_brainstorming",
            })
            workers_live._phase = "briefing"
        except NoMatches:
            pass

        # Also add to briefing panel
        try:
            briefing_panel = self.query_one("#briefing-panel", BriefingPanel)
            briefing_panel.add_event({
                "type": "manager_brainstorming",
            })
        except NoMatches:
            pass

        try:
            cd = self.query_one("#contract-display", ContractDisplay)
            cd.revision_count = self._revision_count
        except NoMatches:
            pass
        self._set_contract_state("manager_thinking")

        try:
            async for event in self._office.revise_contract(self._session_id, feedback):
                event_type = event.get("type", "")

                if event_type == "manager_message":
                    content = event.get("content", "")
                    self._add_manager_message(
                        f"[bold green]Manager:[/bold green] {content}"
                    )

                elif event_type == "manager_question":
                    content = event.get("content", "")
                    self._add_manager_message(
                        f"[bold yellow]Manager asks:[/bold yellow] {content}"
                    )
                    self._set_contract_state("clarifying")

                elif event_type == "contract_ready":
                    contract = event.get("contract", {})
                    self.pending_contract = contract
                    try:
                        cd = self.query_one("#contract-display", ContractDisplay)
                        cd.contract_data = contract
                        cd.revision_count = self._revision_count
                    except NoMatches:
                        pass
                    self._set_contract_state("contract_presented")
                    self._add_manager_message(
                        f"[bold cyan]\U0001f4cb Revised contract ready! (Rev #{self._revision_count})[/bold cyan]\n"
                        f"Review it in the right panel.\n"
                        f"[bold green]Click \u2713 ACCEPT[/bold green] to finalize  |  "
                        f"[bold yellow]Click \u270f REVISE[/bold yellow] for more changes"
                    )
                    self.notify("Contract ready! Review in right panel", severity="information")

                elif event_type == "error":
                    msg = event.get("message", "Unknown error")
                    self._add_manager_message(f"[red]\u2717 {msg}[/red]")

        except Exception as e:
            self._add_manager_message(f"[red]Revision error: {e}[/red]")
