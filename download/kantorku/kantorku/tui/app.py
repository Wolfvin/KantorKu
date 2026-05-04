"""
KantorKu TUI App — 3-Panel Office Interface.

The central TUI for coders, providing a natural office workflow:
- Left Panel:   Chat with the Manager (Conductor) + Interrupt button
- Center Panel: Workers brainstorming & executing live
- Right Panel:  Contract display + Accept/Revise actions

Supports two modes:
1. Remote: Connect to a running kantorku server via WebSocket
2. Embedded: Run the Office directly in-process (no server needed)

Slash commands still work as secondary tools — type /help for list.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.events import Key
from textual.reactive import reactive
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    RichLog,
    Static,
    TabbedContent,
    TabPane,
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
    SQUAD_COLORS,
    STATUS_ICONS,
    STATUS_COLORS,
    EVENT_STYLES,
    CONTRACT_STATE_COLORS,
    PANEL_STATE_ICONS,
    WORKERS_PHASE_STYLES,
)
from kantorku.tui.markdown_renderer import (
    render_markdown,
    render_code,
    render_contract_summary,
    render_task_result,
)
from kantorku.tui.commands import handle_slash_command


# ── Widget Classes ──────────────────────────────────────────────────


class ContractDisplay(Static):
    """Right panel — shows current contract with Accept/Revise actions."""

    contract_data: reactive[dict[str, Any]] = reactive({})
    contract_state: reactive[str] = reactive("idle")
    work_result: reactive[dict[str, Any]] = reactive({})

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    def watch_contract_data(self, data: dict[str, Any]) -> None:
        self._render()

    def watch_contract_state(self, state: str) -> None:
        self._render()

    def watch_work_result(self, data: dict[str, Any]) -> None:
        self._render()

    def _render(self) -> None:
        parts: list[Any] = []

        # Header with state
        state = self.contract_state
        state_color = CONTRACT_STATE_COLORS.get(state, "dim")
        state_icon = {
            "idle": "💤",
            "manager_thinking": "🤔",
            "clarifying": "💬",
            "contract_presented": "📋",
            "team_review": "👥",
            "todo_review": "📝",
            "client_feedback": "🔄",
            "working": "⚡",
            "done": "✅",
            "failed": "❌",
        }.get(state, "❓")

        parts.append(Text.from_markup(
            f"[{state_color} bold]{state_icon} {state.upper()}[/{state_color} bold]"
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

            # Todos
            todos = data.get("todos", [])
            if todos:
                parts.append(Text.from_markup(f"\n[bold]Tasks ({len(todos)}):[/bold]"))
                for todo in todos:
                    desc = todo.get("description", "")
                    assigned = todo.get("assigned_to", "unassigned")
                    status = todo.get("status", "pending")
                    icon = STATUS_ICONS.get(status, "○")
                    color = STATUS_COLORS.get(status, "dim")
                    parts.append(Text.from_markup(
                        f"  [{color}]{icon}[/{color}] [{assigned}] {desc[:50]}"
                    ))

                # Progress bar
                done = sum(1 for t in todos if t.get("status") == "done")
                total = len(todos)
                pct = int((done / total) * 100) if total > 0 else 0
                bar_len = 20
                filled = int(bar_len * done / total) if total > 0 else 0
                bar = "█" * filled + "░" * (bar_len - filled)
                parts.append(Text.from_markup(
                    f"\n[bold]Progress:[/bold] [{bar}] {pct}% ({done}/{total})"
                ))

            # Team feedback
            team_feedback = data.get("team_feedback_rounds", [])
            if team_feedback:
                parts.append(Text.from_markup(
                    f"\n[bold magenta]Team Feedback:[/bold magenta] {len(team_feedback)} round(s)"
                ))
                for i, round_data in enumerate(team_feedback[-2:]):
                    concerns = round_data.get("concerns", [])
                    decisions = round_data.get("decisions", [])
                    if concerns:
                        parts.append(Text.from_markup(
                            f"  Round {i+1}: [yellow]{len(concerns)} concern(s)[/yellow]"
                        ))
                    if decisions:
                        for d in decisions[:2]:
                            parts.append(Text.from_markup(f"  [green]✓ {d[:40]}[/green]"))

            # Actions based on state
            parts.append(Text.from_markup(""))
            if state == "contract_presented":
                parts.append(Text.from_markup(
                    "[bold green]▸ Type /accept to approve[/bold green]\n"
                    "[bold yellow]▸ Type /revise <feedback> to request changes[/bold yellow]"
                ))
            elif state == "working":
                parts.append(Text.from_markup(
                    "[bold green]▸ Workers are executing...[/bold green]\n"
                    "[bold yellow]▸ Type /interrupt to pause and talk to Manager[/bold yellow]"
                ))
            elif state in ("team_review", "todo_review"):
                parts.append(Text.from_markup(
                    f"[bold magenta]▸ Team is reviewing the plan...[/bold magenta]"
                ))
            elif state == "done":
                parts.append(Text.from_markup(
                    "[bold green]▸ Work complete! Start a new task by typing a message.[/bold green]"
                ))
        else:
            parts.append(Text.from_markup(
                "\n[dim]No active contract yet.[/dim]\n\n"
                "[dim]Send a message to the Manager\n"
                "in the left panel to start.[/dim]"
            ))

        # Work result
        result = self.work_result
        if result:
            parts.append(Text.from_markup("\n[bold green]━━━ Result ━━━[/bold green]"))
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
            "working": "green",
            "done": "green",
            "failed": "red",
        }.get(state, "yellow")

        self.update(Panel(
            Group(*parts),
            title="Contract",
            border_style=border_color,
            padding=(0, 1),
        ))


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
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._entries: list[dict[str, Any]] = []
        self._max_entries = 500
        self._round: int = 0
        self._phase: str = ""  # idle, briefing, execution, verification, done

    def add_event(self, event: dict[str, Any]) -> None:
        """Add an office event to the live stream."""
        event_type = event.get("type", "")

        # Only show worker-relevant events in center panel
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
        }

        if event_type not in relevant_types:
            return

        self._entries.append(event)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]
        self._render_stream()

    def add_system_message(self, message: str, style: str = "dim") -> None:
        """Add a system/phase message to the stream."""
        self._entries.append({
            "type": "system",
            "content": message,
            "style": style,
        })
        self._render_stream()

    def clear(self) -> None:
        self._entries.clear()
        self._render_stream()

    def _render_stream(self) -> None:
        if not self._entries:
            self.update(Panel(
                "[dim]Workers will appear here once a contract is accepted.[/dim]\n\n"
                "[dim]You'll see:\n"
                "  • Briefing room discussion\n"
                "  • Task assignments & execution\n"
                "  • Worker DMs and concerns\n"
                "  • LLM streaming output\n"
                "  • Verification results[/dim]",
                title="Workers Live",
                border_style="dim",
                padding=(0, 1),
            ))
            return

        parts: list[Any] = []

        # Phase indicator
        if self._phase:
            phase_colors = {
                "briefing": "magenta bold",
                "execution": "green bold",
                "verification": "blue bold",
                "done": "green",
            }
            phase_icons = {
                "briefing": "👥 BRIEFING",
                "execution": "⚡ EXECUTING",
                "verification": "🔍 VERIFYING",
                "done": "✅ COMPLETE",
            }
            pc = phase_colors.get(self._phase, "dim")
            pi = phase_icons.get(self._phase, self._phase.upper())
            parts.append(Text.from_markup(f"[{pc}]{pi}[/{pc}]\n"))

        visible = self._entries[-50:]  # Show last 50 entries

        for e in visible:
            event_type = e.get("type", "")

            if event_type == "system":
                style = e.get("style", "dim")
                parts.append(Text.from_markup(f"[{style}]{e.get('content', '')}[/{style}]"))
                continue

            if event_type == "briefing_opened":
                from_id = e.get("from", "conductor")
                content = e.get("content", "")
                parts.append(Text.from_markup(
                    f"  [bold magenta]📢 {from_id}:[/bold magenta] {content[:80]}"
                ))

            elif event_type == "plan_drafted":
                parts.append(Text.from_markup(
                    "  [bold blue]📋 Plan drafted for team review[/bold blue]"
                ))

            elif event_type == "plan_revised":
                reason = e.get("reason", "")
                parts.append(Text.from_markup(
                    f"  [yellow]📋 Plan revised: {reason[:60]}[/yellow]"
                ))

            elif event_type == "worker_speak_up":
                from_id = e.get("from", "?")
                content = e.get("content", "")
                parts.append(Text.from_markup(
                    f"  [magenta]💬 {from_id}:[/magenta] {content[:100]}"
                ))

            elif event_type == "worker_dm":
                from_id = e.get("from", "?")
                to_id = e.get("to", "?")
                content = e.get("content", "")
                parts.append(Text.from_markup(
                    f"  [dim]✉ {from_id} → {to_id}: {content[:80]}[/dim]"
                ))

            elif event_type == "worker_broadcast":
                from_id = e.get("from", "?")
                content = e.get("content", "")
                parts.append(Text.from_markup(
                    f"  [cyan]📢 {from_id}: {content[:80]}[/cyan]"
                ))

            elif event_type == "task_assigned":
                to_id = e.get("to", "?")
                content = e.get("content", "")
                parts.append(Text.from_markup(
                    f"  [cyan]➡ {to_id}: {content[:70]}[/cyan]"
                ))

            elif event_type == "task_started":
                from_id = e.get("from", "?")
                parts.append(Text.from_markup(
                    f"  [yellow]◐ {from_id} started working...[/yellow]"
                ))

            elif event_type == "task_done":
                from_id = e.get("from", "?")
                files = e.get("files", [])
                files_str = f" → {', '.join(files[:3])}" if files else ""
                parts.append(Text.from_markup(
                    f"  [green]✓ {from_id} done{files_str}[/green]"
                ))

            elif event_type == "task_failed":
                from_id = e.get("from", "?")
                error = e.get("error", "")
                parts.append(Text.from_markup(
                    f"  [red bold]✗ {from_id} failed: {error[:60]}[/red bold]"
                ))

            elif event_type in ("context_fetch_start", "context_fetch_done"):
                instance = e.get("instance", "?")
                query = e.get("query", "")[:40]
                if event_type == "context_fetch_start":
                    parts.append(Text.from_markup(
                        f"  [dim]🔍 Pool-{instance}: fetching \"{query}\"[/dim]"
                    ))
                else:
                    parts.append(Text.from_markup(
                        f"  [dim]✓ Pool-{instance}: fetched[/dim]"
                    ))

            elif event_type == "verify_design_start":
                parts.append(Text.from_markup(
                    "  [magenta]🔍 Design verification starting...[/magenta]"
                ))

            elif event_type == "verify_design_done":
                approved = e.get("approved", True)
                issues = e.get("issues", [])
                icon = "✓" if approved else "✗"
                color = "green" if approved else "red"
                parts.append(Text.from_markup(
                    f"  [{color}]{icon} Design review: {len(issues)} issue(s)[/{color}]"
                ))

            elif event_type == "verify_engineer_start":
                parts.append(Text.from_markup(
                    "  [magenta]🔍 Engineering verification starting...[/magenta]"
                ))

            elif event_type == "verify_engineer_done":
                approved = e.get("approved", True)
                issues = e.get("issues", [])
                icon = "✓" if approved else "✗"
                color = "green" if approved else "red"
                parts.append(Text.from_markup(
                    f"  [{color}]{icon} Engineering review: {len(issues)} issue(s)[/{color}]"
                ))

            elif event_type == "error_logged":
                lesson = e.get("lesson", "")
                parts.append(Text.from_markup(
                    f"  [red]⚠ Error: {lesson[:80]}[/red]"
                ))

            elif event_type == "skill_updated":
                worker = e.get("worker", "?")
                lesson = e.get("lesson", "")
                parts.append(Text.from_markup(
                    f"  [cyan]📚 {worker} learned: {lesson[:60]}[/cyan]"
                ))

            elif event_type == "llm_stream_start":
                from_id = e.get("from", "?")
                model = e.get("model", "")
                parts.append(Text.from_markup(
                    f"  [dim]◐ {from_id} thinking ({model})...[/dim]"
                ))

            elif event_type == "llm_stream_chunk":
                chunk = e.get("chunk", "")
                if chunk:
                    parts.append(Text.from_markup(f"  [dim]{chunk}[/dim]"))

            elif event_type == "llm_stream_done":
                from_id = e.get("from", "?")
                parts.append(Text.from_markup(
                    f"  [dim]✓ {from_id} stream complete[/dim]"
                ))

            elif event_type == "contract_accepted":
                parts.append(Text.from_markup(
                    "  [bold green]✓ Contract accepted — work begins![/bold green]"
                ))

            elif event_type == "delegation_request":
                parts.append(Text.from_markup(
                    f"  [cyan]↗ Delegation: {e.get('content', '')[:60]}[/cyan]"
                ))

            elif event_type == "delegation_result":
                parts.append(Text.from_markup(
                    f"  [cyan]↙ Delegation result: {e.get('content', '')[:60]}[/cyan]"
                ))

        self.update(Panel(
            Group(*parts),
            title="Workers Live",
            border_style=KANTORKU_THEME["secondary"],
            padding=(0, 1),
        ))


# ── Main TUI Application ────────────────────────────────────────────


class KantorKuTUI(App):
    """
    KantorKu — 3-Panel Office Interface for Coders.

    Natural office workflow:
    1. Chat with Manager in LEFT panel
    2. Watch workers brainstorm/execute in CENTER panel
    3. Review & accept contracts in RIGHT panel
    4. Hit INTERRUPT to pause and talk to Manager again

    Slash commands still work as secondary tools — /help for list.
    """

    TITLE = "kantorku"
    SUB_TITLE = "3-Panel Office"

    CSS = f"""
    Screen {{
        layout: vertical;
    }}

    #main-container {{
        layout: horizontal;
        height: 1fr;
    }}

    #left-panel {{
        width: 30%;
        height: 100%;
        border: solid {KANTORKU_THEME['primary']};
        border-title-color: {KANTORKU_THEME['primary']};
    }}

    #center-panel {{
        width: 40%;
        height: 100%;
        border: solid {KANTORKU_THEME['secondary']};
        border-title-color: {KANTORKU_THEME['secondary']};
    }}

    #right-panel {{
        width: 30%;
        height: 100%;
        border: solid {KANTORKU_THEME['accent']};
        border-title-color: {KANTORKU_THEME['accent']};
    }}

    #manager-log {{
        height: 1fr;
        border: none;
        padding: 0 1;
    }}

    #workers-log {{
        height: 1fr;
        border: none;
        padding: 0 1;
    }}

    #contract-scroll {{
        height: 1fr;
    }}

    #input-bar {{
        height: auto;
        dock: bottom;
        padding: 0 1;
    }}

    #chat-input {{
        dock: bottom;
    }}

    #interrupt-btn {{
        dock: bottom;
        margin: 0 1;
        background: {KANTORKU_THEME['warning']};
        color: $text;
    }}

    #interrupt-btn:hover {{
        background: {KANTORKU_THEME['error']};
    }}
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("ctrl+c", "cancel_input", "Cancel", show=True),
        Binding("ctrl+a", "accept_contract", "Accept", show=False),
        Binding("ctrl+r", "revise_contract", "Revise", show=False),
        Binding("ctrl+i", "interrupt", "Interrupt", show=False),
        Binding("tab", "focus_next_panel", "Next Panel", show=False),
        Binding("up", "history_up", "History ↑", show=False),
        Binding("down", "history_down", "History ↓", show=False),
    ]

    # Reactive state
    session_id: reactive[str] = reactive("")
    connection_state: reactive[str] = reactive("disconnected")
    pending_contract: reactive[dict] = reactive({})
    contract_state: reactive[str] = reactive("idle")

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
                yield Button(
                    "⚡ INTERRUPT — Talk to Manager",
                    id="interrupt-btn",
                    variant="warning",
                )
                with Horizontal(id="input-bar"):
                    yield Input(
                        placeholder="Talk to Manager... (/help for commands)",
                        id="chat-input",
                    )

            # ── Center Panel: Workers Live ──
            with Vertical(id="center-panel"):
                yield WorkersLiveStream(id="workers-live")

            # ── Right Panel: Contract ──
            with Vertical(id="right-panel"):
                with VerticalScroll(id="contract-scroll"):
                    yield ContractDisplay(id="contract-display")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize connection and start background workers."""
        self.title = f"kantorku — session {self._session_id}"
        self._add_manager_message(
            f"[bold cyan]KantorKu TUI v0.5.0 — 3-Panel Office[/bold cyan]\n"
            f"Session: {self._session_id}\n"
            f"Server: {self.server_url}\n\n"
            f"[bold]How it works:[/bold]\n"
            f"  [bold cyan]Left[/bold cyan]   → Chat with Manager (you're here)\n"
            f"  [bold magenta]Center[/bold magenta] → Watch workers brainstorm & execute\n"
            f"  [bold yellow]Right[/bold yellow]  → Review & accept contracts\n\n"
            f"[dim]Type a message and press Enter to start.\n"
            f"Slash commands: /help for full list\n"
            f"Shortcuts: Ctrl+A=Accept  Ctrl+R=Revise  Ctrl+I=Interrupt[/dim]"
        )

        # Connect to server
        self._connect_and_listen()

    # ── Connection & Background Workers ─────────────────────────────

    @work(exclusive=True, name="connect_and_listen")
    async def _connect_and_listen(self) -> None:
        """Connect to server and start listening for events."""
        try:
            await self._connection.connect()
            self.connection_state = "connected"
            self._add_manager_message("[green]✓ Connected to server[/green]")

            # Start event listener
            self._event_listener_running = True
            await self._listen_office_events()

        except ConnectionError as e:
            self.connection_state = "error"
            self._add_manager_message(
                f"[red]✗ Connection failed: {e}[/red]\n"
                f"[dim]Retrying in {self._reconnect_delay}s...[/dim]"
            )
            await self._auto_reconnect()
        except Exception as e:
            self.connection_state = "error"
            self._add_manager_message(f"[red]Error: {e}[/red]")

    async def _listen_office_events(self) -> None:
        """Listen to the office event stream and route to center panel."""
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

        # Center panel: all worker activity
        try:
            workers_live = self.query_one("#workers-live", WorkersLiveStream)
            workers_live.add_event(event)
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
            self._add_manager_message(
                f"[bold green]✓ Work complete![/bold green]"
            )
            try:
                contract_display = self.query_one("#contract-display", ContractDisplay)
                contract_display.work_result = result
                contract_display.contract_state = "done"
                self.contract_state = "done"
            except NoMatches:
                pass

        elif event_type == "error":
            msg = event.get("message", "Unknown error")
            self._add_manager_message(f"[red bold]✗ Error: {msg}[/red bold]")

    def _handle_contract_event(self, event: dict[str, Any]) -> None:
        """Handle contract-related events — update right panel."""
        event_type = event.get("type", "")

        try:
            contract_display = self.query_one("#contract-display", ContractDisplay)
        except NoMatches:
            return

        if event_type == "contract_ready":
            contract = event.get("contract", {})
            contract_display.contract_data = contract
            contract_display.contract_state = "contract_presented"
            self.pending_contract = contract
            self.contract_state = "contract_presented"
            self._add_manager_message(
                f"[bold cyan]📋 Contract ready![/bold cyan] "
                f"Review it in the right panel.\n"
                f"[bold green]/accept[/bold green] to approve  |  "
                f"[bold yellow]/revise <feedback>[/bold yellow] to request changes\n"
                f"[dim]Or press Ctrl+A / Ctrl+R[/dim]"
            )

        elif event_type == "contract_accepted":
            contract_display.contract_state = "working"
            self.contract_state = "working"

        elif event_type == "work_started":
            contract_display.contract_state = "working"
            self.contract_state = "working"

    # ── Input Handling ──────────────────────────────────────────────

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input — send message or handle slash command."""
        if event.input.id != "chat-input":
            return

        text = event.value.strip()
        if not text:
            return

        # Clear input
        event.input.value = ""

        # Add to history
        self._input_history.append(text)
        self._history_index = -1

        # Check for slash commands
        if text.startswith("/"):
            result = await handle_slash_command(text, self)
            if result:
                self._add_manager_message(result)
            return

        # Send as regular message to Manager
        self._add_manager_message(f"[bold]You:[/bold] {text}")
        await self._send_message(text)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "interrupt-btn":
            self._do_interrupt()

    # ── Key Bindings ────────────────────────────────────────────────

    def action_accept_contract(self) -> None:
        """Ctrl+A — Accept current contract."""
        if self.pending_contract:
            asyncio.create_task(self._send_accept())
        else:
            self._add_manager_message("[yellow]No contract to accept yet.[/yellow]")

    def action_revise_contract(self) -> None:
        """Ctrl+R — Request contract revision."""
        if self.pending_contract:
            self._add_manager_message(
                "[yellow]Type your revision feedback, e.g.:[/yellow]\n"
                "[dim]/revise I want more detail on the API design[/dim]"
            )
        else:
            self._add_manager_message("[yellow]No contract to revise yet.[/yellow]")

    def action_interrupt(self) -> None:
        """Ctrl+I — Interrupt current work and talk to Manager."""
        self._do_interrupt()

    def _do_interrupt(self) -> None:
        """Interrupt current work."""
        if self.contract_state == "working":
            self._add_manager_message(
                "[bold yellow]⚡ INTERRUPT — Pausing work to talk to Manager[/bold yellow]"
            )
            self.contract_state = "client_feedback"
            try:
                contract_display = self.query_one("#contract-display", ContractDisplay)
                contract_display.contract_state = "client_feedback"
            except NoMatches:
                pass
            try:
                workers_live = self.query_one("#workers-live", WorkersLiveStream)
                workers_live.add_system_message(
                    "⚡ INTERRUPT — Client paused work for discussion", "yellow bold"
                )
            except NoMatches:
                pass
        else:
            self._add_manager_message(
                "[dim]No active work to interrupt. Just type your message![/dim]"
            )

    def action_focus_next_panel(self) -> None:
        """Tab — Cycle focus between panels."""
        focused = self.focused
        if focused and focused.id == "chat-input":
            self.query_one("#workers-live").focus()
        elif focused and hasattr(focused, 'id') and 'workers' in str(focused.id):
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
            try:
                inp = self.query_one("#chat-input", Input)
                inp.value = self._input_history[idx]
            except NoMatches:
                pass
        elif self._history_index == 0:
            self._history_index = -1
            try:
                inp = self.query_one("#chat-input", Input)
                inp.value = ""
            except NoMatches:
                pass

    def action_cancel_input(self) -> None:
        """Ctrl+C — Cancel current input or streaming."""
        try:
            inp = self.query_one("#chat-input", Input)
            inp.value = ""
        except NoMatches:
            pass

    # ── Message Sending ─────────────────────────────────────────────

    async def _send_message(self, message: str) -> None:
        """Send a message to the Manager via WebSocket."""
        try:
            async for event in self._connection.send_message(message):
                event_type = event.get("type", "")

                if event_type == "manager_message":
                    content = event.get("content", "")
                    self._add_manager_message(
                        f"[bold green]Manager:[/bold green] {content}"
                    )
                    self.contract_state = "clarifying"
                    try:
                        cd = self.query_one("#contract-display", ContractDisplay)
                        cd.contract_state = "clarifying"
                    except NoMatches:
                        pass

                elif event_type == "contract_ready":
                    contract = event.get("contract", {})
                    self.pending_contract = contract
                    self.contract_state = "contract_presented"
                    try:
                        cd = self.query_one("#contract-display", ContractDisplay)
                        cd.contract_data = contract
                        cd.contract_state = "contract_presented"
                    except NoMatches:
                        pass
                    self._add_manager_message(
                        f"[bold cyan]📋 Contract ready![/bold cyan] "
                        f"Review it in the right panel.\n"
                        f"[bold green]/accept[/bold green] | [bold yellow]/revise <feedback>[/bold yellow]"
                    )

                elif event_type == "error":
                    msg = event.get("message", "Unknown error")
                    self._add_manager_message(f"[red bold]✗ {msg}[/red bold]")

        except ConnectionError as e:
            self._add_manager_message(
                f"[red]Connection lost: {e}[/red]\n"
                f"[dim]Will try to reconnect...[/dim]"
            )
            self.connection_state = "disconnected"
            await self._auto_reconnect()

    async def _send_accept(self) -> None:
        """Accept the current contract."""
        if not self.pending_contract:
            self._add_manager_message("[yellow]No contract to accept.[/yellow]")
            return

        self._add_manager_message(
            "[bold green]✓ Contract accepted! Workers are starting...[/bold green]"
        )

        try:
            workers_live = self.query_one("#workers-live", WorkersLiveStream)
            workers_live.add_system_message(
                "✓ Contract accepted — Briefing room opening...", "green bold"
            )
            workers_live._phase = "briefing"
        except NoMatches:
            pass

        try:
            cd = self.query_one("#contract-display", ContractDisplay)
            cd.contract_state = "working"
            self.contract_state = "working"
        except NoMatches:
            pass

        result = await self._connection.accept_contract()

        if result and result.get("type") == "error":
            self._add_manager_message(f"[red]Accept failed: {result.get('message', '')}[/red]")
            self.contract_state = "contract_presented"
            try:
                cd = self.query_one("#contract-display", ContractDisplay)
                cd.contract_state = "contract_presented"
            except NoMatches:
                pass
        elif result:
            self._add_manager_message("[bold green]✓ Work complete![/bold green]")
            self.contract_state = "done"
            try:
                cd = self.query_one("#contract-display", ContractDisplay)
                cd.work_result = result
                cd.contract_state = "done"
                workers_live = self.query_one("#workers-live", WorkersLiveStream)
                workers_live._phase = "done"
                workers_live.add_system_message("✅ All work complete!", "green bold")
            except NoMatches:
                pass

    async def _send_revise(self, feedback: str) -> None:
        """Request a contract revision."""
        if not self.pending_contract:
            self._add_manager_message("[yellow]No contract to revise.[/yellow]")
            return

        self._add_manager_message(
            f"[bold yellow]↻ Requesting revision:[/bold yellow] {feedback}"
        )

        try:
            cd = self.query_one("#contract-display", ContractDisplay)
            cd.contract_state = "clarifying"
            self.contract_state = "clarifying"
        except NoMatches:
            pass

        async for event in self._connection.revise_contract(feedback):
            event_type = event.get("type", "")

            if event_type == "manager_message":
                content = event.get("content", "")
                self._add_manager_message(
                    f"[bold green]Manager:[/bold green] {content}"
                )

            elif event_type == "contract_ready":
                contract = event.get("contract", {})
                self.pending_contract = contract
                self.contract_state = "contract_presented"
                try:
                    cd = self.query_one("#contract-display", ContractDisplay)
                    cd.contract_data = contract
                    cd.contract_state = "contract_presented"
                except NoMatches:
                    pass
                self._add_manager_message(
                    f"[bold cyan]📋 Revised contract ready![/bold cyan] "
                    f"Review in right panel."
                )

            elif event_type == "error":
                msg = event.get("message", "Unknown error")
                self._add_manager_message(f"[red]✗ {msg}[/red]")

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
                self._add_manager_message("[green]✓ Reconnected![/green]")
                # Restart event listener
                self._event_listener_running = True
                await self._listen_office_events()
                return
            except ConnectionError:
                continue
            except Exception:
                continue

        self._add_manager_message(
            f"[red bold]✗ Could not reconnect after {self._max_reconnect_attempts} attempts.[/red bold]\n"
            f"[dim]Check your server and restart the TUI.[/dim]"
        )

    # ── Embedded Mode Support ──────────────────────────────────────

    def _update_embedded_status(self) -> None:
        """Update panels with embedded office data."""
        office = getattr(self, '_office', None)
        if not office:
            return

        try:
            cd = self.query_one("#contract-display", ContractDisplay)

            # Update worker status
            if hasattr(office, 'get_worker_status'):
                workers = office.get_worker_status()
                # Could update a status line

            # Update pool status
            if hasattr(office, 'get_pool_status'):
                pool = office.get_pool_status()

            # Update cost
            if hasattr(office, 'cost_tracker') and office.cost_tracker:
                cost = office.cost_tracker.get_report()

        except NoMatches:
            pass


class EmbeddedKantorKuTUI(KantorKuTUI):
    """
    KantorKu TUI in embedded mode — runs Office in-process.

    No server needed. Everything runs locally.
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
                "[green]✓ Embedded Office initialized![/green]\n"
                f"[dim]Workers: {len(self._office.registry.all_worker_ids)}[/dim]"
            )

            # Subscribe to event bus
            self._event_listener_running = True
            await self._listen_embedded_events()

        except Exception as e:
            self.connection_state = "error"
            self._add_manager_message(f"[red bold]✗ Failed to start: {e}[/red bold]")

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

    async def _send_message(self, message: str) -> None:
        """Send message using embedded Office."""
        if not self._office:
            self._add_manager_message("[red]Office not initialized[/red]")
            return

        try:
            async for event in self._office.chat(self._session_id, message):
                event_type = event.get("type", "")

                if event_type == "manager_message":
                    content = event.get("content", "")
                    self._add_manager_message(
                        f"[bold green]Manager:[/bold green] {content}"
                    )
                    self.contract_state = "clarifying"
                    try:
                        cd = self.query_one("#contract-display", ContractDisplay)
                        cd.contract_state = "clarifying"
                    except NoMatches:
                        pass

                elif event_type == "contract_ready":
                    contract = event.get("contract", {})
                    self.pending_contract = contract
                    self.contract_state = "contract_presented"
                    try:
                        cd = self.query_one("#contract-display", ContractDisplay)
                        cd.contract_data = contract
                        cd.contract_state = "contract_presented"
                    except NoMatches:
                        pass
                    self._add_manager_message(
                        f"[bold cyan]📋 Contract ready![/bold cyan] "
                        f"Review in right panel."
                    )

        except Exception as e:
            self._add_manager_message(f"[red]Error: {e}[/red]")

    async def _send_accept(self) -> None:
        """Accept contract using embedded Office."""
        if not self._office:
            return

        self._add_manager_message(
            "[bold green]✓ Contract accepted! Workers starting...[/bold green]"
        )

        try:
            workers_live = self.query_one("#workers-live", WorkersLiveStream)
            workers_live.add_system_message(
                "✓ Contract accepted — Briefing room opening...", "green bold"
            )
            workers_live._phase = "briefing"
        except NoMatches:
            pass

        try:
            cd = self.query_one("#contract-display", ContractDisplay)
            cd.contract_state = "working"
            self.contract_state = "working"
        except NoMatches:
            pass

        try:
            result = await self._office.accept_and_run(self._session_id)

            self._add_manager_message("[bold green]✓ Work complete![/bold green]")
            self.contract_state = "done"

            try:
                cd = self.query_one("#contract-display", ContractDisplay)
                cd.work_result = result
                cd.contract_state = "done"
                workers_live = self.query_one("#workers-live", WorkersLiveStream)
                workers_live._phase = "done"
                workers_live.add_system_message("✅ All work complete!", "green bold")
            except NoMatches:
                pass

        except Exception as e:
            self._add_manager_message(f"[red]Work failed: {e}[/red]")
            self.contract_state = "failed"
            try:
                cd = self.query_one("#contract-display", ContractDisplay)
                cd.contract_state = "failed"
            except NoMatches:
                pass

    async def _send_revise(self, feedback: str) -> None:
        """Revise contract using embedded Office."""
        if not self._office:
            return

        self._add_manager_message(
            f"[bold yellow]↻ Requesting revision:[/bold yellow] {feedback}"
        )

        try:
            cd = self.query_one("#contract-display", ContractDisplay)
            cd.contract_state = "clarifying"
            self.contract_state = "clarifying"
        except NoMatches:
            pass

        async for event in self._office.revise(self._session_id, feedback):
            event_type = event.get("type", "")

            if event_type == "manager_message":
                self._add_manager_message(
                    f"[bold green]Manager:[/bold green] {event.get('content', '')}"
                )
            elif event_type == "contract_ready":
                contract = event.get("contract", {})
                self.pending_contract = contract
                self.contract_state = "contract_presented"
                try:
                    cd = self.query_one("#contract-display", ContractDisplay)
                    cd.contract_data = contract
                    cd.contract_state = "contract_presented"
                except NoMatches:
                    pass
                self._add_manager_message(
                    f"[bold cyan]📋 Revised contract ready![/bold cyan]"
                )
