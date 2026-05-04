"""
KantorKu TUI App — Main Textual application.

The central TUI for coders, providing:
- Interactive chat with the Conductor
- Live worker status grid
- Real-time office event stream
- Provider health & circuit breaker dashboard
- Cost tracking overview

Supports two modes:
1. Remote: Connect to a running kantorku server via WebSocket
2. Embedded: Run the Office directly in-process (no server needed)
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
    Label,
    RichLog,
    Static,
    TabbedContent,
    TabPane,
    DataTable,
)
from textual.worker import Worker, WorkerCancelled

from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from kantorku.tui.connection import OfficeConnection, ConnectionState
from kantorku.tui.themes import KANTORKU_THEME
from kantorku.tui.markdown_renderer import render_markdown, render_code
from kantorku.tui.commands import handle_slash_command


class WorkerGrid(Static):
    """Live grid showing all workers and their statuses."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._workers: list[dict[str, Any]] = []

    def update_workers(self, workers: list[dict[str, Any]]) -> None:
        """Update the worker grid with new data."""
        self._workers = workers
        self._render_grid()

    def _render_grid(self) -> None:
        table = Table(
            title="Workers",
            show_header=True,
            header_style="bold cyan",
            border_style="dim",
            expand=True,
            title_style="bold",
        )
        table.add_column("ID", style="bold", width=20)
        table.add_column("Status", width=12)
        table.add_column("Model", width=28)
        table.add_column("Squad", width=14)
        table.add_column("Role", width=24)

        status_icons = {
            "idle": "[dim]idle[/dim]",
            "thinking": "[yellow]thinking[/yellow]",
            "active": "[green bold]active[/green bold]",
            "done": "[green]done[/green]",
            "failed": "[red bold]failed[/red bold]",
        }

        squad_colors = {
            "coding": "[blue]coding[/blue]",
            "verification": "[magenta]verification[/magenta]",
            "support": "[yellow]support[/yellow]",
            "translation": "[cyan]translation[/cyan]",
        }

        for w in self._workers:
            status = w.get("status", "unknown")
            status_str = status_icons.get(status, f"[dim]{status}[/dim]")
            squad = w.get("squad", "")
            squad_str = squad_colors.get(squad, squad)
            model = w.get("model", "N/A") or "N/A"
            role = w.get("role", "") or w.get("display_name", "")

            table.add_row(
                w.get("id", "?"),
                status_str,
                model,
                squad_str,
                role[:24],
            )

        self.update(table)


class EventsStream(Static):
    """Real-time office event stream display."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._events: list[dict[str, Any]] = []
        self._max_events = 200

    def add_event(self, event: dict[str, Any]) -> None:
        """Add a new event to the stream."""
        self._events.append(event)
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]
        self._render_events()

    def _render_events(self) -> None:
        # Show last 40 events
        visible = self._events[-40:]

        table = Table(
            title="Office Events",
            show_header=True,
            header_style="bold cyan",
            border_style="dim",
            expand=True,
            title_style="bold",
            show_lines=False,
        )
        table.add_column("Time", width=10)
        table.add_column("Type", width=22)
        table.add_column("From", width=18)
        table.add_column("Detail", width=40)

        event_icons = {
            "briefing_opened": "[magenta]briefing[/magenta]",
            "plan_drafted": "[blue]plan[/blue]",
            "contract_ready": "[green bold]contract[/green bold]",
            "contract_accepted": "[green]accepted[/green]",
            "task_assigned": "[cyan]assigned[/cyan]",
            "task_started": "[yellow]started[/yellow]",
            "task_done": "[green bold]done[/green bold]",
            "task_failed": "[red bold]failed[/red bold]",
            "worker_speak_up": "[magenta]speak_up[/magenta]",
            "worker_dm": "[dim]dm[/dim]",
            "worker_broadcast": "[cyan]broadcast[/cyan]",
            "context_fetch_start": "[dim]fetch[/dim]",
            "context_fetch_done": "[dim]fetched[/dim]",
            "verify_design_start": "[magenta]v_design[/magenta]",
            "verify_design_done": "[magenta]v_design[/magenta]",
            "verify_engineer_start": "[magenta]v_engineer[/magenta]",
            "verify_engineer_done": "[magenta]v_engineer[/magenta]",
            "error_logged": "[red]error[/red]",
            "manager_message": "[green bold]manager[/green bold]",
            "manager_question": "[yellow bold]question[/yellow bold]",
            "llm_stream_start": "[dim]stream[/dim]",
            "llm_stream_chunk": "[dim]chunk[/dim]",
            "llm_stream_done": "[dim]stream_done[/dim]",
            "work_started": "[green bold]work[/green bold]",
            "work_done": "[green bold]work_done[/green bold]",
        }

        for e in visible:
            ts = e.get("timestamp", "")
            if "T" in ts:
                ts = ts.split("T")[1][:8]  # Just HH:MM:SS

            event_type = e.get("type", "?")
            type_str = event_icons.get(event_type, f"[dim]{event_type}[/dim]")

            from_id = e.get("from", "")
            if from_id:
                from_str = f"[bold]{from_id}[/bold]"
            else:
                from_str = ""

            # Build detail from content, error, or files
            detail = e.get("content", "") or e.get("error", "") or ""
            files = e.get("files", [])
            if files:
                detail = f"files: {', '.join(files[:3])}"
            if not detail and e.get("todos"):
                todos = e["todos"]
                detail = f"{len(todos)} todo(s)"
            detail = detail[:40]

            table.add_row(ts, type_str, from_str, detail)

        self.update(table)


class HealthPanel(Static):
    """Provider health and circuit breaker status."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._providers: dict[str, dict] = {}
        self._cost: dict[str, Any] = {}
        self._queue: dict[str, Any] = {}

    def update_data(
        self,
        providers: dict[str, dict] | None = None,
        cost: dict[str, Any] | None = None,
        queue: dict[str, Any] | None = None,
    ) -> None:
        if providers is not None:
            self._providers = providers
        if cost is not None:
            self._cost = cost
        if queue is not None:
            self._queue = queue
        self._render()

    def _render(self) -> None:
        # Provider table
        table = Table(
            title="Providers & Circuit Breakers",
            show_header=True,
            header_style="bold cyan",
            border_style="dim",
            expand=True,
            title_style="bold",
        )
        table.add_column("Provider", style="bold", width=14)
        table.add_column("Circuit", width=12)
        table.add_column("Calls", width=8)
        table.add_column("Success", width=10)
        table.add_column("Latency", width=10)
        table.add_column("Status", width=10)

        for name, data in self._providers.items():
            circuit = data.get("circuit_state", "closed")
            circuit_str = {
                "closed": "[green]closed[/green]",
                "open": "[red bold]OPEN[/red bold]",
                "half_open": "[yellow]half_open[/yellow]",
            }.get(circuit, circuit)

            total = data.get("total_calls", 0)
            failed = data.get("failed_calls", 0)
            success_rate = data.get("success_rate", 0)
            avg_lat = data.get("avg_latency_ms", 0)

            is_healthy = data.get("is_healthy", True)
            health_str = "[green]OK[/green]" if is_healthy else "[red]DOWN[/red]"

            table.add_row(
                name,
                circuit_str,
                str(total),
                f"{success_rate:.0%}" if total > 0 else "N/A",
                f"{avg_lat:.0f}ms" if avg_lat > 0 else "N/A",
                health_str,
            )

        if not self._providers:
            table.add_row("[dim]No providers[/dim]", "", "", "", "", "")

        # Cost summary
        cost_lines = []
        if self._cost:
            total = self._cost.get("total_cost_usd", 0)
            calls = self._cost.get("total_calls", 0)
            cost_lines.append(f"\n[bold]Cost:[/bold] ${total:.4f} ({calls} calls)")

        # Queue info
        queue_lines = []
        if self._queue:
            enabled = self._queue.get("enabled", False)
            if enabled:
                pending = self._queue.get("pending", 0)
                dlq = self._queue.get("dead_letter_count", 0)
                queue_lines.append(f"[bold]Queue:[/bold] {pending} pending, {dlq} DLQ")

        from rich.console import Group
        parts = [table]
        if cost_lines:
            parts.append(Text.from_markup("\n".join(cost_lines)))
        if queue_lines:
            parts.append(Text.from_markup("\n".join(queue_lines)))

        self.update(Group(*parts))


class ContractPanel(Static):
    """Shows current contract details."""

    contract_data: reactive[dict[str, Any]] = reactive({})

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    def watch_contract_data(self, data: dict[str, Any]) -> None:
        self._render_contract()

    def _render_contract(self) -> None:
        data = self.contract_data
        if not data:
            self.update(Panel(
                "[dim]No active contract[/dim]\n\n"
                "Send a message to the Conductor to start a negotiation.",
                title="Contract",
                border_style="dim",
            ))
            return

        title = data.get("title", "Untitled")
        description = data.get("description", "")
        state = data.get("state", "unknown")
        todos = data.get("todos", [])

        state_colors = {
            "drafting": "yellow",
            "proposed": "cyan",
            "negotiating": "yellow",
            "accepted": "green",
            "working": "blue",
            "verifying": "magenta",
            "done": "green bold",
            "failed": "red",
        }
        state_str = f"[{state_colors.get(state, 'white')}]{state}[/{state_colors.get(state, 'white')}]"

        lines = [
            f"[bold]{title}[/bold]",
            f"State: {state_str}",
            "",
            f"[dim]{description[:200]}[/dim]",
            "",
        ]

        if todos:
            lines.append(f"[bold]Tasks ({len(todos)}):[/bold]")
            for i, todo in enumerate(todos):
                tid = todo.get("id", f"t{i}")
                desc = todo.get("description", "")
                assigned = todo.get("assigned_to", "[dim]unassigned[/dim]")
                status = todo.get("status", "pending")
                status_icon = {
                    "pending": "[dim]○[/dim]",
                    "in_progress": "[yellow]◑[/yellow]",
                    "done": "[green]●[/green]",
                    "failed": "[red]●[/red]",
                }.get(status, "○")
                lines.append(
                    f"  {status_icon} [{assigned}] {desc[:50]}"
                )

        self.update(Panel(
            "\n".join(lines),
            title=f"Contract: {title}",
            border_style="green" if state == "accepted" else "cyan",
        ))


class KantorKuTUI(App):
    """
    KantorKu — Terminal UI for coders.

    A full-featured TUI that connects to the KantorKu multi-agent office
    and provides an interactive terminal interface for:
    - Chatting with the Conductor to negotiate contracts
    - Monitoring worker activity in real-time
    - Tracking provider health and costs
    - Viewing the office event stream
    """

    TITLE = "kantorku"
    SUB_TITLE = "Multi-Agent Office for Coders"

    CSS = """
    Screen {
        layout: vertical;
    }

    #main-container {
        layout: horizontal;
        height: 1fr;
    }

    #chat-panel {
        width: 60%;
        height: 100%;
        border: solid cyan;
        border-title-color: cyan;
    }

    #right-panel {
        width: 40%;
        height: 100%;
    }

    #chat-log {
        height: 1fr;
        border: none;
        padding: 0 1;
    }

    #chat-input-container {
        height: auto;
        dock: bottom;
        padding: 0 1;
    }

    #chat-input {
        dock: bottom;
    }

    #contract-area {
        height: auto;
        max-height: 10;
        dock: top;
        border: solid green;
        border-title-color: green;
    }

    TabbedContent {
        height: 1fr;
    }

    .status-bar {
        dock: bottom;
        height: 1;
        background: $surface;
        color: $text;
    }

    .connection-ok {
        color: green;
    }

    .connection-err {
        color: red;
    }

    .connection-connecting {
        color: yellow;
    }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("ctrl+c", "cancel_input", "Cancel", show=True),
        Binding("tab", "cycle_tabs", "Switch Tab", show=False),
    ]

    # Reactive state
    session_id: reactive[str] = reactive("")
    connection_state: reactive[str] = reactive("disconnected")
    pending_contract: reactive[dict] = reactive({})

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

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Container(id="main-container"):
            # Left: Chat panel
            with Vertical(id="chat-panel"):
                yield ContractPanel(id="contract-area")
                yield RichLog(id="chat-log", highlight=True, markup=True, auto_scroll=True)
                with Horizontal(id="chat-input-container"):
                    yield Input(
                        placeholder="Type your message to the Conductor... (Enter to send)",
                        id="chat-input",
                    )

            # Right: Tabbed dashboard
            with Vertical(id="right-panel"):
                with TabbedContent():
                    with TabPane("Workers", id="tab-workers"):
                        yield WorkerGrid(id="worker-grid")
                    with TabPane("Events", id="tab-events"):
                        yield EventsStream(id="events-stream")
                    with TabPane("Health", id="tab-health"):
                        yield HealthPanel(id="health-panel")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize connection and start background workers."""
        self.title = f"kantorku — session {self._session_id}"
        self._add_system_message(
            f"[bold cyan]KantorKu TUI v0.4.0[/bold cyan]\n"
            f"Session: {self._session_id}\n"
            f"Server: {self.server_url}\n\n"
            f"[dim]Type a message and press Enter to chat with the Conductor.[/dim]\n"
            f"[dim]Slash commands: /help /status /workers /health /cost /accept /revise /code /reset[/dim]\n"
            f"[dim]Quick commands: accept, yes, revise <feedback>[/dim]\n"
            f"[dim]Press Ctrl+Q to quit, Tab to switch panels.[/dim]\n"
        )
        self._connect()

    def _add_system_message(self, text: str) -> None:
        """Add a system message to the chat log."""
        try:
            log = self.query_one("#chat-log", RichLog)
            log.write(Text.from_markup(text))
        except NoMatches:
            pass

    def _add_chat_message(self, role: str, content: str) -> None:
        """Add a chat message to the log with proper formatting."""
        try:
            log = self.query_one("#chat-log", RichLog)
            if role == "user":
                log.write(Text.from_markup(
                    f"[bold green]You>[/bold green] {content}"
                ))
            elif role in ("conductor", "manager"):
                log.write(Text.from_markup("[bold cyan]Conductor>[/bold cyan]"))
                log.write(render_markdown(content))
                log.write(Text.from_markup(""))  # spacing
            elif role == "result":
                log.write(Text.from_markup("[bold magenta]Result>[/bold magenta]"))
                log.write(render_markdown(content))
                log.write(Text.from_markup(""))
            else:
                log.write(Text.from_markup(
                    f"[bold]{role}>[/bold] {content}"
                ))
        except NoMatches:
            pass

    def _add_streaming_chunk(self, chunk: str) -> None:
        """Handle a streaming LLM chunk."""
        self._streaming_text += chunk
        try:
            log = self.query_one("#chat-log", RichLog)
            # Remove last line if streaming, then re-render
            if hasattr(self, '_streaming_line_idx') and self._streaming_line_idx is not None:
                # We just append for now — RichLog doesn't support editing lines
                pass
            # Just write chunks as they come (simple approach)
        except NoMatches:
            pass

    @work(exclusive=True, exit_on_error=False)
    async def _connect(self) -> None:
        """Connect to the kantorku server."""
        self.connection_state = "connecting"
        self._add_system_message("[yellow]Connecting to server...[/yellow]")

        try:
            await self._connection.connect()
            self.connection_state = "connected"
            self._add_system_message("[green bold]Connected![/green bold]")

            # Start background workers
            self._poll_status()
            self._listen_events()

        except Exception as e:
            self.connection_state = "error"
            self._add_system_message(
                f"[red bold]Connection failed:[/red bold] {e}\n"
                f"[dim]Make sure the server is running: kantorku serve[/dim]"
            )

    @work(exclusive=True, exit_on_error=False, group="poll_status")
    async def _poll_status(self) -> None:
        """Periodically poll server status for workers and health."""
        while self.connection_state == "connected":
            try:
                status = await self._connection.get_status()
                if status:
                    # Update workers
                    workers = status.get("workers", [])
                    try:
                        grid = self.query_one("#worker-grid", WorkerGrid)
                        grid.update_workers(workers)
                    except NoMatches:
                        pass

                    # Update health
                    health_data = status.get("health", {})
                    providers = health_data.get("providers", {})
                    cost = status.get("cost", {})
                    try:
                        panel = self.query_one("#health-panel", HealthPanel)
                        panel.update_data(providers=providers, cost=cost)
                    except NoMatches:
                        pass

            except Exception:
                pass

            await asyncio.sleep(3)

    @work(exclusive=True, exit_on_error=False, group="listen_events")
    async def _listen_events(self) -> None:
        """Listen for real-time events from the server via SSE."""
        try:
            async for event in self._connection.listen_events():
                try:
                    stream = self.query_one("#events-stream", EventsStream)
                    stream.add_event(event)
                except NoMatches:
                    pass

                # Handle special events
                event_type = event.get("type", "")
                if event_type == "manager_message":
                    self._add_chat_message("conductor", event.get("content", ""))
                elif event_type == "contract_ready":
                    contract = event.get("contract", event.get("todos", {}))
                    self.pending_contract = contract
                    try:
                        cp = self.query_one("#contract-area", ContractPanel)
                        cp.contract_data = contract
                    except NoMatches:
                        pass
                    self._add_system_message(
                        "[green bold]Contract ready![/green bold] "
                        "Type [bold]accept[/bold] to approve or provide feedback."
                    )
                elif event_type == "work_done":
                    result = event.get("result", {})
                    self._add_system_message(
                        "[green bold]Work completed![/green bold]"
                    )
                    # Show results
                    results = result.get("results", {})
                    for tid, r in results.items():
                        output = r.get("output", "")
                        if output:
                            self._add_chat_message("result", output[:2000])
                elif event_type == "task_done":
                    from_id = event.get("from", "worker")
                    files = event.get("files", [])
                    if files:
                        self._add_system_message(
                            f"[green]{from_id}[/green] produced: {', '.join(files)}"
                        )
                elif event_type == "task_failed":
                    from_id = event.get("from", "worker")
                    error = event.get("error", "unknown error")
                    self._add_system_message(
                        f"[red]{from_id}[/red] failed: {error}"
                    )
                elif event_type == "llm_stream_chunk":
                    # Streaming chunks — collect them
                    pass

        except asyncio.CancelledError:
            pass
        except Exception as e:
            if self.connection_state == "connected":
                self._add_system_message(f"[yellow]Event stream error: {e}[/yellow]")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user pressing Enter in the chat input."""
        message = event.value.strip()
        if not message:
            return

        # Clear input
        event.input.value = ""

        # Handle slash commands
        if message.startswith("/"):
            result = await handle_slash_command(message, self)
            if result is not None:
                self._add_system_message(result)
                return

        # Handle special quick commands
        if message.lower() in ("accept", "yes", "y", "ok"):
            await self._send_accept()
            return

        if message.lower() in ("quit", "exit"):
            self.exit()
            return

        if message.lower().startswith("revise"):
            feedback = message[7:].strip()
            await self._send_revise(feedback or "Please revise the contract")
            return

        if message.lower() == "status":
            result = await handle_slash_command("/status", self)
            if result:
                self._add_system_message(result)
            return

        # Send as user message
        self._add_chat_message("user", message)
        await self._send_message(message)

    async def _send_message(self, message: str) -> None:
        """Send a user message to the Conductor."""
        if self.connection_state != "connected":
            self._add_system_message("[red]Not connected to server.[/red]")
            return

        try:
            async for event in self._connection.send_message(message):
                event_type = event.get("type", "")
                if event_type == "manager_message":
                    self._add_chat_message("conductor", event.get("content", ""))
                elif event_type == "contract_ready":
                    contract = event.get("contract", {})
                    self.pending_contract = contract
                    try:
                        cp = self.query_one("#contract-area", ContractPanel)
                        cp.contract_data = contract
                    except NoMatches:
                        pass
                    self._add_system_message(
                        "[green bold]Contract ready![/green bold] "
                        "Type [bold]accept[/bold] to approve or provide feedback."
                    )
        except Exception as e:
            self._add_system_message(f"[red]Error: {e}[/red]")

    async def _send_accept(self) -> None:
        """Accept the current contract."""
        if self.connection_state != "connected":
            self._add_system_message("[red]Not connected to server.[/red]")
            return

        if not self.pending_contract:
            self._add_system_message("[yellow]No contract to accept.[/yellow]")
            return

        self._add_system_message("[green]Accepting contract...[/green]")
        try:
            result = await self._connection.accept_contract()
            self._add_system_message(
                "[green bold]Contract accepted! Work started...[/green bold]"
            )
            if result:
                # Show work result if available
                results = result.get("results", {})
                for tid, r in results.items():
                    output = r.get("output", "")
                    if output:
                        self._add_chat_message("result", output[:2000])
        except Exception as e:
            self._add_system_message(f"[red]Error accepting contract: {e}[/red]")

    async def _send_revise(self, feedback: str) -> None:
        """Send a revision request for the current contract."""
        if self.connection_state != "connected":
            self._add_system_message("[red]Not connected to server.[/red]")
            return

        self._add_system_message(f"[yellow]Requesting revision: {feedback}[/yellow]")
        try:
            async for event in self._connection.revise_contract(feedback):
                event_type = event.get("type", "")
                if event_type == "manager_message":
                    self._add_chat_message("conductor", event.get("content", ""))
                elif event_type == "contract_ready":
                    contract = event.get("contract", {})
                    self.pending_contract = contract
                    try:
                        cp = self.query_one("#contract-area", ContractPanel)
                        cp.contract_data = contract
                    except NoMatches:
                        pass
                    self._add_system_message(
                        "[green bold]Revised contract ready![/green bold] "
                        "Type [bold]accept[/bold] to approve."
                    )
        except Exception as e:
            self._add_system_message(f"[red]Error: {e}[/red]")

    async def _show_status(self) -> None:
        """Show current office status."""
        if self.connection_state != "connected":
            self._add_system_message("[red]Not connected to server.[/red]")
            return

        try:
            status = await self._connection.get_status()
            workers = status.get("workers", [])
            health = status.get("health", {})
            cost = status.get("cost", {})

            lines = [
                f"[bold]Workers:[/bold] {len(workers)}",
                f"[bold]Session:[/bold] {self._session_id}",
                f"[bold]Connection:[/bold] {self.connection_state}",
            ]

            if cost:
                total = cost.get("total_cost_usd", 0)
                calls = cost.get("total_calls", 0)
                lines.append(f"[bold]Cost:[/bold] ${total:.4f} ({calls} calls)")

            providers = health.get("providers", {})
            for name, data in providers.items():
                healthy = data.get("is_healthy", True)
                status_icon = "[green]OK[/green]" if healthy else "[red]DOWN[/red]"
                lines.append(f"  {name}: {status_icon}")

            self._add_system_message("\n".join(lines))

        except Exception as e:
            self._add_system_message(f"[red]Error getting status: {e}[/red]")

    def action_cancel_input(self) -> None:
        """Cancel current input."""
        try:
            chat_input = self.query_one("#chat-input", Input)
            chat_input.value = ""
            chat_input.focus()
        except NoMatches:
            pass

    def action_cycle_tabs(self) -> None:
        """Cycle through the dashboard tabs."""
        try:
            tabs = self.query_one(TabbedContent)
            tabs.action_next_tab()
        except NoMatches:
            pass

    async def action_quit(self) -> None:
        """Clean shutdown."""
        try:
            await self._connection.disconnect()
        except Exception:
            pass
        self.exit()


class EmbeddedKantorKuTUI(KantorKuTUI):
    """
    KantorKu TUI in embedded mode — runs the Office directly in-process.

    No server needed. The TUI creates an Office instance and
    interacts with it directly. This is ideal for quick coding
    sessions where you just want to start working immediately.
    """

    def __init__(self, config_path: str | None = None, **kwargs: Any) -> None:
        super().__init__(server_url="embedded", config_path=config_path, **kwargs)
        self._office: Any = None

    @work(exclusive=True, exit_on_error=False)
    async def _connect(self) -> None:
        """Initialize the Office in embedded mode."""
        self.connection_state = "connecting"
        self._add_system_message("[yellow]Initializing Office (embedded mode)...[/yellow]")

        try:
            from kantorku.office import Office

            if self.config_path:
                self._office = Office.from_config(self.config_path)
            else:
                self._office = Office()

            await self._office.initialize()
            self.connection_state = "connected"
            self._add_system_message("[green bold]Office initialized (embedded)![/green bold]")

            # Subscribe to events
            self._listen_embedded_events()

            # Initial status update
            self._update_embedded_status()

        except Exception as e:
            self.connection_state = "error"
            self._add_system_message(
                f"[red bold]Office init failed:[/red bold] {e}\n"
                f"[dim]Check your kantorku.toml and API keys[/dim]"
            )

    @work(exclusive=True, exit_on_error=False, group="embedded_events")
    async def _listen_embedded_events(self) -> None:
        """Listen for events from the embedded office."""
        if not self._office:
            return

        async def on_event(event: Any) -> None:
            try:
                if hasattr(event, 'to_dict'):
                    data = event.to_dict()
                else:
                    data = event
                stream = self.query_one("#events-stream", EventsStream)
                stream.add_event(data)
            except NoMatches:
                pass

        self._office.bus.subscribe_global(on_event)

        # Keep running while connected
        while self.connection_state == "connected":
            await asyncio.sleep(1)

    def _update_embedded_status(self) -> None:
        """Update worker grid and health from embedded office."""
        if not self._office:
            return

        try:
            workers = self._office.get_worker_status()
            grid = self.query_one("#worker-grid", WorkerGrid)
            grid.update_workers(workers)
        except NoMatches:
            pass

        try:
            cost = self._office.get_cost_report() if self._office.cost_tracker else {}
            health_data = {}
            if hasattr(self._office, '_health') and self._office._health:
                health_data = self._office._health._provider_health
                health_data = {
                    k: v.to_dict() for k, v in health_data.items()
                }
            panel = self.query_one("#health-panel", HealthPanel)
            panel.update_data(providers=health_data, cost=cost)
        except NoMatches:
            pass

    async def _send_message(self, message: str) -> None:
        """Send a message to the embedded office."""
        if not self._office or self.connection_state != "connected":
            self._add_system_message("[red]Office not initialized.[/red]")
            return

        try:
            async for event in self._office.chat(self._session_id, message):
                event_type = event.get("type", "")
                if event_type == "manager_message":
                    self._add_chat_message("conductor", event.get("content", ""))
                elif event_type == "contract_ready":
                    contract = event.get("contract", {})
                    self.pending_contract = contract
                    try:
                        cp = self.query_one("#contract-area", ContractPanel)
                        cp.contract_data = contract
                    except NoMatches:
                        pass
                    self._add_system_message(
                        "[green bold]Contract ready![/green bold] "
                        "Type [bold]accept[/bold] to approve."
                    )

            # Update status after interaction
            self._update_embedded_status()

        except Exception as e:
            self._add_system_message(f"[red]Error: {e}[/red]")

    async def _send_accept(self) -> None:
        """Accept the contract in embedded mode."""
        if not self._office or not self.pending_contract:
            self._add_system_message("[yellow]No contract to accept.[/yellow]")
            return

        self._add_system_message("[green]Accepting contract...[/green]")
        try:
            result = await self._office.accept_and_run(self._session_id)
            self._add_system_message("[green bold]Work completed![/green bold]")

            results = result.get("results", {})
            for tid, r in results.items():
                output = r.get("output", "")
                if output:
                    self._add_chat_message("result", output[:2000])

            self._update_embedded_status()
        except Exception as e:
            self._add_system_message(f"[red]Error: {e}[/red]")

    async def _send_revise(self, feedback: str) -> None:
        """Revise the contract in embedded mode."""
        if not self._office:
            return

        try:
            async for event in self._office.revise(self._session_id, feedback):
                event_type = event.get("type", "")
                if event_type == "manager_message":
                    self._add_chat_message("conductor", event.get("content", ""))
                elif event_type == "contract_ready":
                    contract = event.get("contract", {})
                    self.pending_contract = contract
                    try:
                        cp = self.query_one("#contract-area", ContractPanel)
                        cp.contract_data = contract
                    except NoMatches:
                        pass
                    self._add_system_message(
                        "[green bold]Revised contract ready![/green bold] "
                        "Type [bold]accept[/bold] to approve."
                    )
        except Exception as e:
            self._add_system_message(f"[red]Error: {e}[/red]")

    async def _show_status(self) -> None:
        """Show embedded office status."""
        if not self._office:
            return

        self._update_embedded_status()
        workers = self._office.get_worker_status()
        cost = self._office.get_cost_report() if self._office.cost_tracker else {}

        lines = [
            f"[bold]Mode:[/bold] Embedded",
            f"[bold]Workers:[/bold] {len(workers)}",
            f"[bold]Session:[/bold] {self._session_id}",
        ]

        if cost:
            total = cost.get("total_cost_usd", 0)
            calls = cost.get("total_calls", 0)
            lines.append(f"[bold]Cost:[/bold] ${total:.4f} ({calls} calls)")

        self._add_system_message("\n".join(lines))

    async def action_quit(self) -> None:
        """Clean shutdown of embedded office."""
        if self._office:
            try:
                await self._office.shutdown()
            except Exception:
                pass
        self.exit()
