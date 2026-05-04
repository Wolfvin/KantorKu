"""
KantorKu TUI App — Main Textual application.

The central TUI for coders, providing:
- Interactive chat with the Conductor
- Live worker status grid
- Real-time office event stream
- Provider health & circuit breaker dashboard
- Cost tracking overview
- Memory explorer (Ring1/Ring2/Ring3)
- DAG dependency visualization
- Briefing room transcript viewer
- Context pool prefetch status
- Task queue & DLQ management
- Observability (spans, metrics, traces)
- Alert system display
- Input history with up/down arrows
- Auto-reconnection on disconnect
- LLM streaming display

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
)
from kantorku.tui.markdown_renderer import (
    render_markdown,
    render_code,
    render_contract_summary,
    render_task_result,
)
from kantorku.tui.commands import handle_slash_command


# ── Widget Classes ──────────────────────────────────────────────────


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

        for w in self._workers:
            status = w.get("status", "unknown")
            color = STATUS_COLORS.get(status, "dim")
            icon = STATUS_ICONS.get(status, "?")
            status_str = f"[{color}]{icon} {status}[/{color}]"

            squad = w.get("squad", "")
            squad_color = SQUAD_COLORS.get(squad, "white")
            squad_str = f"[{squad_color}]{squad}[/{squad_color}]"

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

        for e in visible:
            ts = e.get("timestamp", "")
            if "T" in ts:
                ts = ts.split("T")[1][:8]

            event_type = e.get("type", "?")
            style, label = EVENT_STYLES.get(event_type, ("dim", event_type))
            type_str = f"[{style}]{label}[/{style}]"

            from_id = e.get("from", "")
            from_str = f"[bold]{from_id}[/bold]" if from_id else ""

            detail = e.get("content", "") or e.get("error", "") or ""
            files = e.get("files", [])
            if files:
                detail = f"files: {', '.join(files[:3])}"
            if not detail and e.get("todos"):
                detail = f"{len(e['todos'])} todo(s)"
            detail = detail[:40]

            table.add_row(ts, type_str, from_str, detail)

        self.update(table)


class HealthPanel(Static):
    """Provider health, circuit breaker, cost, queue, and alerts."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._providers: dict[str, dict] = {}
        self._cost: dict[str, Any] = {}
        self._queue: dict[str, Any] = {}
        self._alerts: list[dict] = []

    def update_data(
        self,
        providers: dict[str, dict] | None = None,
        cost: dict[str, Any] | None = None,
        queue: dict[str, Any] | None = None,
        alerts: list[dict] | None = None,
    ) -> None:
        if providers is not None:
            self._providers = providers
        if cost is not None:
            self._cost = cost
        if queue is not None:
            self._queue = queue
        if alerts is not None:
            self._alerts = alerts
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

        parts: list[Any] = [table]

        # Cost summary
        if self._cost:
            total = self._cost.get("total_cost_usd", 0)
            calls = self._cost.get("total_calls", 0)
            parts.append(Text.from_markup(
                f"\n[bold]Cost:[/bold] ${total:.4f} ({calls} calls)"
            ))

        # Queue info
        if self._queue:
            enabled = self._queue.get("enabled", False)
            if enabled:
                pending = self._queue.get("pending", 0)
                dlq = self._queue.get("dead_letter_count", 0)
                parts.append(Text.from_markup(
                    f"[bold]Queue:[/bold] {pending} pending, {dlq} DLQ"
                ))

        # Active alerts
        if self._alerts:
            critical = sum(1 for a in self._alerts if a.get("severity") == "critical")
            warning = sum(1 for a in self._alerts if a.get("severity") == "warning")
            if critical or warning:
                parts.append(Text.from_markup(
                    f"[red bold]{critical} critical[/red bold], [yellow]{warning} warnings[/yellow]"
                ))

        self.update(Group(*parts))


class ContractPanel(Static):
    """Shows current contract details using the theme system."""

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

        # Use the shared renderer
        self.update(Panel(
            render_contract_summary(data),
            title=f"Contract: {data.get('title', 'Untitled')}",
            border_style="green" if data.get("state") == "accepted" else "cyan",
        ))


class MemoryPanel(Static):
    """Three-Ring Memory explorer panel."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._ring1_stats: dict[str, Any] = {}
        self._ring2_stats: dict[str, Any] = {}
        self._contexts: list[dict] = []

    def update_data(
        self,
        ring1: dict[str, Any] | None = None,
        ring2: dict[str, Any] | None = None,
        contexts: list[dict] | None = None,
    ) -> None:
        if ring1 is not None:
            self._ring1_stats = ring1
        if ring2 is not None:
            self._ring2_stats = ring2
        if contexts is not None:
            self._contexts = contexts
        self._render()

    def _render(self) -> None:
        parts: list[Any] = []

        # Ring 1 (DuckDB — hot)
        ring1 = self._ring1_stats
        r1_rows = [
            f"[bold cyan]Ring 1 (DuckDB — Hot)[/bold cyan]",
            f"  Contexts: {ring1.get('context_count', '?')}",
            f"  Sessions: {ring1.get('session_count', '?')}",
            f"  Task Results: {ring1.get('task_result_count', '?')}",
            f"  History: {ring1.get('history_count', '?')}",
            f"  DB Size: {ring1.get('db_size_mb', '?')} MB",
        ]
        parts.append(Text.from_markup("\n".join(r1_rows)))

        # Ring 2 (SQLite+Parquet — warm)
        ring2 = self._ring2_stats
        r2_rows = [
            f"\n[bold magenta]Ring 2 (SQLite — Warm)[/bold magenta]",
            f"  Episodes: {ring2.get('episode_count', '?')}",
            f"  Lessons: {ring2.get('lesson_count', '?')}",
            f"  Audit Trails: {ring2.get('audit_trail_count', '?')}",
            f"  DB Size: {ring2.get('db_size_mb', '?')} MB",
        ]
        parts.append(Text.from_markup("\n".join(r2_rows)))

        # Ring 3 (GraphRAG — cold/stub)
        parts.append(Text.from_markup(
            "\n[bold dim]Ring 3 (Cognee GraphRAG — Cold)[/bold dim]\n"
            "  [dim]Not yet connected[/dim]"
        ))

        # Recent contexts
        if self._contexts:
            ctx_table = Table(
                title="Recent Contexts",
                show_header=True,
                header_style="bold cyan",
                border_style="dim",
                expand=True,
            )
            ctx_table.add_column("ID", width=12)
            ctx_table.add_column("Source", width=16)
            ctx_table.add_column("Tokens", width=8)
            ctx_table.add_column("Status", width=10)

            for ctx in self._contexts[:20]:
                ctx_table.add_row(
                    ctx.get("id", "?")[:12],
                    ctx.get("source", "?")[:16],
                    str(ctx.get("token_count", "?")),
                    ctx.get("status", "?"),
                )
            parts.append(ctx_table)

        self.update(Group(*parts))


class DAGPanel(Static):
    """Task dependency DAG visualization panel."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._groups: list[list[dict]] = []
        self._todos: list[dict] = []

    def update_dag(self, groups: list[list[dict]], todos: list[dict]) -> None:
        self._groups = groups
        self._todos = todos
        self._render()

    def _render(self) -> None:
        if not self._groups and not self._todos:
            self.update(Panel(
                "[dim]No DAG data yet[/dim]\n\n"
                "Accept a contract to see task dependencies.",
                title="DAG",
                border_style="dim",
            ))
            return

        tree = Tree("Task DAG", guide_style="cyan")

        if self._groups:
            for level, group in enumerate(self._groups):
                branch = tree.add(f"[bold]Level {level}[/bold] (parallel)")
                for task in group:
                    status = task.get("status", "pending")
                    icon = STATUS_ICONS.get(status, "?")
                    color = STATUS_COLORS.get(status, "dim")
                    desc = task.get("description", task.get("id", "?"))[:40]
                    assigned = task.get("assigned_to", "unassigned")
                    branch.add(f"[{color}]{icon}[/{color}] [{assigned}] {desc}")
        elif self._todos:
            # Simple list if no DAG groups
            for todo in self._todos:
                status = todo.get("status", "pending")
                icon = STATUS_ICONS.get(status, "?")
                color = STATUS_COLORS.get(status, "dim")
                desc = todo.get("description", "?")[:50]
                assigned = todo.get("assigned_to", "unassigned")
                tree.add(f"[{color}]{icon}[/{color}] [{assigned}] {desc}")

        # Critical path info
        parts: list[Any] = [tree]
        if self._todos:
            pending = sum(1 for t in self._todos if t.get("status") == "pending")
            in_progress = sum(1 for t in self._todos if t.get("status") == "in_progress")
            done = sum(1 for t in self._todos if t.get("status") == "done")
            failed = sum(1 for t in self._todos if t.get("status") == "failed")
            parts.append(Text.from_markup(
                f"\n[bold]Progress:[/bold] {done} done, {in_progress} active, "
                f"{pending} pending, {failed} failed"
            ))

        self.update(Group(*parts))


class BriefingPanel(Static):
    """Briefing room transcript panel showing team discussions."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._messages: list[dict] = []
        self._round: int = 0
        self._consensus: bool = False

    def update_briefing(
        self,
        messages: list[dict] | None = None,
        round_num: int | None = None,
        consensus: bool | None = None,
    ) -> None:
        if messages is not None:
            self._messages = messages
        if round_num is not None:
            self._round = round_num
        if consensus is not None:
            self._consensus = consensus
        self._render()

    def add_message(self, msg: dict) -> None:
        """Add a single briefing message."""
        self._messages.append(msg)
        self._render()

    def _render(self) -> None:
        if not self._messages:
            self.update(Panel(
                "[dim]No briefing yet[/dim]\n\n"
                "After accepting a contract, the team will discuss here.",
                title="Briefing Room",
                border_style="dim",
            ))
            return

        parts: list[Any] = []
        header = f"[bold cyan]Briefing Room[/bold cyan] — Round {self._round}"
        if self._consensus:
            header += " [green bold]CONSENSUS[/green bold]"
        parts.append(Text.from_markup(header + "\n"))

        for msg in self._messages[-30:]:
            from_id = msg.get("from", "?")
            content = msg.get("content", "")[:120]
            msg_type = msg.get("type", "message")

            type_colors = {
                "message": "white",
                "question": "yellow",
                "concern": "red",
                "suggestion": "cyan",
                "agreement": "green",
                "summary": "bold magenta",
                "decision": "bold green",
            }
            color = type_colors.get(msg_type, "white")
            parts.append(Text.from_markup(
                f"  [bold]{from_id}[/bold]: [{color}]{content}[/{color}]"
            ))

        self.update(Group(*parts))


class ContextPoolPanel(Static):
    """Context pool prefetch status panel."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._pool_status: dict[str, Any] = {}
        self._prefetch_queue: list[dict] = []

    def update_data(
        self,
        pool_status: dict[str, Any] | None = None,
        prefetch_queue: list[dict] | None = None,
    ) -> None:
        if pool_status is not None:
            self._pool_status = pool_status
        if prefetch_queue is not None:
            self._prefetch_queue = prefetch_queue
        self._render()

    def _render(self) -> None:
        parts: list[Any] = []

        pool = self._pool_status
        if pool:
            lines = [
                "[bold cyan]Context Pool[/bold cyan]",
                f"  Workers: {pool.get('worker_count', '?')}",
                f"  Queue Depth: {pool.get('queue_depth', '?')}",
                f"  Active Prefetch: {pool.get('active_prefetch', '?')}",
                f"  Completed: {pool.get('completed', '?')}",
                f"  Failed: {pool.get('failed', '?')}",
            ]
            parts.append(Text.from_markup("\n".join(lines)))
        else:
            parts.append(Text.from_markup(
                "[dim]Context pool not initialized[/dim]"
            ))

        if self._prefetch_queue:
            table = Table(
                title="Prefetch Queue",
                show_header=True,
                header_style="bold cyan",
                border_style="dim",
                expand=True,
            )
            table.add_column("ID", width=12)
            table.add_column("Status", width=10)
            table.add_column("Worker", width=16)
            table.add_column("Purpose", width=30)

            for item in self._prefetch_queue[:15]:
                table.add_row(
                    item.get("id", "?")[:12],
                    item.get("status", "?"),
                    item.get("worker_id", "?")[:16],
                    item.get("purpose", "?")[:30],
                )
            parts.append(table)

        self.update(Group(*parts))


class TaskQueuePanel(Static):
    """Task queue and dead letter queue panel."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._pending: list[dict] = []
        self._active: list[dict] = []
        self._dlq: list[dict] = []
        self._stats: dict[str, Any] = {}

    def update_data(
        self,
        pending: list[dict] | None = None,
        active: list[dict] | None = None,
        dlq: list[dict] | None = None,
        stats: dict[str, Any] | None = None,
    ) -> None:
        if pending is not None:
            self._pending = pending
        if active is not None:
            self._active = active
        if dlq is not None:
            self._dlq = dlq
        if stats is not None:
            self._stats = stats
        self._render()

    def _render(self) -> None:
        parts: list[Any] = []

        # Stats summary
        if self._stats:
            parts.append(Text.from_markup(
                f"[bold cyan]Task Queue[/bold cyan]  "
                f"Pending: {self._stats.get('pending', len(self._pending))}  "
                f"Active: {self._stats.get('active', len(self._active))}  "
                f"DLQ: {self._stats.get('dead_letter_count', len(self._dlq))}  "
                f"Total: {self._stats.get('total_processed', '?')}"
            ))
        else:
            parts.append(Text.from_markup(
                "[bold cyan]Task Queue[/bold cyan]  "
                f"Pending: {len(self._pending)}  Active: {len(self._active)}  "
                f"DLQ: {len(self._dlq)}"
            ))

        # Active tasks
        if self._active:
            table = Table(title="Active Tasks", show_header=True, header_style="bold green",
                         border_style="dim", expand=True)
            table.add_column("ID", width=10)
            table.add_column("Priority", width=8)
            table.add_column("Worker", width=16)
            table.add_column("Instruction", width=30)
            table.add_column("Retry", width=6)

            for t in self._active[:15]:
                table.add_row(
                    t.get("id", "?")[:10],
                    str(t.get("priority", 0)),
                    t.get("worker_id", "?")[:16],
                    (t.get("instruction", "?") or "?")[:30],
                    str(t.get("retry_count", 0)),
                )
            parts.append(table)

        # Dead letter queue
        if self._dlq:
            dlq_table = Table(title="Dead Letter Queue", show_header=True,
                             header_style="bold red", border_style="dim", expand=True)
            dlq_table.add_column("ID", width=10)
            dlq_table.add_column("Error", width=30)
            dlq_table.add_column("Retries", width=8)
            dlq_table.add_column("Last Attempt", width=16)

            for t in self._dlq[:10]:
                dlq_table.add_row(
                    t.get("id", "?")[:10],
                    (t.get("error", "?") or "?")[:30],
                    str(t.get("retry_count", "?")),
                    t.get("last_attempt", "?")[:16],
                )
            parts.append(dlq_table)

        if not self._active and not self._dlq:
            parts.append(Text.from_markup("\n[dim]No tasks in queue[/dim]"))

        self.update(Group(*parts))


class ObservabilityPanel(Static):
    """Observability panel: spans, metrics, traces."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._spans: list[dict] = []
        self._metrics: dict[str, Any] = {}

    def update_data(
        self,
        spans: list[dict] | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> None:
        if spans is not None:
            self._spans = spans
        if metrics is not None:
            self._metrics = metrics
        self._render()

    def _render(self) -> None:
        parts: list[Any] = []

        # Metrics summary
        if self._metrics:
            m = self._metrics
            lines = [
                "[bold cyan]Observability[/bold cyan]",
                f"  Total Requests: {m.get('total_requests', '?')}",
                f"  Avg Latency: {m.get('avg_latency_ms', '?')}ms",
                f"  P99 Latency: {m.get('p99_latency_ms', '?')}ms",
                f"  Error Rate: {m.get('error_rate', '?')}",
                f"  Cache Hit Rate: {m.get('cache_hit_rate', '?')}",
            ]
            parts.append(Text.from_markup("\n".join(lines)))

            # Per-provider metrics
            by_provider = m.get("by_provider", {})
            if by_provider:
                prov_table = Table(title="Provider Metrics", show_header=True,
                                  header_style="bold cyan", border_style="dim", expand=True)
                prov_table.add_column("Provider", width=14)
                prov_table.add_column("Calls", width=8)
                prov_table.add_column("Errors", width=8)
                prov_table.add_column("Avg Latency", width=12)
                prov_table.add_column("Tokens", width=10)

                for name, data in by_provider.items():
                    prov_table.add_row(
                        name,
                        str(data.get("calls", 0)),
                        str(data.get("failed_calls", 0)),
                        f"{data.get('avg_latency_ms', 0):.0f}ms",
                        str(data.get("total_tokens", 0)),
                    )
                parts.append(prov_table)

        # Recent spans
        if self._spans:
            span_table = Table(title="Recent Spans", show_header=True,
                              header_style="bold cyan", border_style="dim", expand=True)
            span_table.add_column("ID", width=8)
            span_table.add_column("Operation", width=20)
            span_table.add_column("Duration", width=10)
            span_table.add_column("Status", width=10)
            span_table.add_column("Provider", width=12)

            for s in self._spans[:20]:
                status = s.get("status", "?")
                status_color = "green" if status == "ok" else "red" if status == "error" else "dim"
                span_table.add_row(
                    s.get("span_id", "?")[:8],
                    s.get("operation", "?")[:20],
                    f"{s.get('duration_ms', 0):.0f}ms",
                    f"[{status_color}]{status}[/{status_color}]",
                    s.get("provider", "?")[:12],
                )
            parts.append(span_table)

        if not self._metrics and not self._spans:
            parts.append(Text.from_markup(
                "[dim]No observability data available[/dim]"
            ))

        self.update(Group(*parts))


class AlertsPanel(Static):
    """Alert system display panel."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._alerts: list[dict] = []

    def update_alerts(self, alerts: list[dict] | None = None) -> None:
        if alerts is not None:
            self._alerts = alerts
        self._render()

    def _render(self) -> None:
        if not self._alerts:
            self.update(Panel(
                "[green]No active alerts[/green]\n\nAll systems nominal.",
                title="Alerts",
                border_style="green",
            ))
            return

        table = Table(
            title=f"Active Alerts ({len(self._alerts)})",
            show_header=True,
            header_style="bold red",
            border_style="red",
            expand=True,
        )
        table.add_column("Severity", width=10)
        table.add_column("Source", width=16)
        table.add_column("Message", width=40)
        table.add_column("Time", width=10)

        for a in self._alerts:
            severity = a.get("severity", "warning")
            sev_color = "red bold" if severity == "critical" else "yellow"
            ts = a.get("timestamp", "")
            if isinstance(ts, (int, float)):
                ts = datetime.fromtimestamp(ts).strftime("%H:%M:%S")
            elif "T" in str(ts):
                ts = str(ts).split("T")[1][:8]

            table.add_row(
                f"[{sev_color}]{severity}[/{sev_color}]",
                a.get("source", "?")[:16],
                (a.get("message", "?") or "?")[:40],
                ts,
            )

        self.update(table)


# ── Main TUI Application ────────────────────────────────────────────


class KantorKuTUI(App):
    """
    KantorKu — Terminal UI for coders.

    A full-featured TUI that connects to the KantorKu multi-agent office
    and provides an interactive terminal interface for all framework features:
    - Chatting with the Conductor to negotiate contracts
    - Monitoring worker activity in real-time
    - Tracking provider health and costs
    - Viewing the office event stream
    - Exploring the 3-Ring memory system
    - Visualizing task DAG dependencies
    - Viewing briefing room discussions
    - Monitoring context pool prefetch status
    - Managing task queue and DLQ
    - Observing traces, metrics, and spans
    - Monitoring alerts
    """

    TITLE = "kantorku"
    SUB_TITLE = "Multi-Agent Office for Coders"

    CSS = f"""
    Screen {{
        layout: vertical;
    }}

    #main-container {{
        layout: horizontal;
        height: 1fr;
    }}

    #chat-panel {{
        width: 60%;
        height: 100%;
        border: solid {KANTORKU_THEME['primary']};
        border-title-color: {KANTORKU_THEME['primary']};
    }}

    #right-panel {{
        width: 40%;
        height: 100%;
    }}

    #chat-log {{
        height: 1fr;
        border: none;
        padding: 0 1;
    }}

    #chat-input-container {{
        height: auto;
        dock: bottom;
        padding: 0 1;
    }}

    #chat-input {{
        dock: bottom;
    }}

    #contract-area {{
        height: auto;
        max-height: 10;
        dock: top;
        border: solid {KANTORKU_THEME['success']};
        border-title-color: {KANTORKU_THEME['success']};
    }}

    TabbedContent {{
        height: 1fr;
    }}

    .status-bar {{
        dock: bottom;
        height: 1;
        background: $surface;
        color: $text;
    }}

    .connection-ok {{
        color: {KANTORKU_THEME['success']};
    }}

    .connection-err {{
        color: {KANTORKU_THEME['error']};
    }}

    .connection-connecting {{
        color: {KANTORKU_THEME['warning']};
    }}
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("ctrl+c", "cancel_input", "Cancel", show=True),
        Binding("tab", "cycle_tabs", "Switch Tab", show=False),
        Binding("up", "history_up", "History ↑", show=False),
        Binding("down", "history_down", "History ↓", show=False),
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
        self._is_streaming = False

        # Input history
        self._input_history: list[str] = []
        self._history_index: int = -1

        # Reconnection
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10
        self._reconnect_delay = 2.0  # seconds, exponential backoff

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Container(id="main-container"):
            # Left: Chat panel
            with Vertical(id="chat-panel"):
                yield ContractPanel(id="contract-area")
                yield RichLog(id="chat-log", highlight=True, markup=True, auto_scroll=True)
                with Horizontal(id="chat-input-container"):
                    yield Input(
                        placeholder="Type your message to the Conductor... (Enter to send, ↑/↓ for history)",
                        id="chat-input",
                    )

            # Right: Tabbed dashboard — all panels
            with Vertical(id="right-panel"):
                with TabbedContent():
                    with TabPane("Workers", id="tab-workers"):
                        yield WorkerGrid(id="worker-grid")
                    with TabPane("Events", id="tab-events"):
                        yield EventsStream(id="events-stream")
                    with TabPane("Health", id="tab-health"):
                        yield HealthPanel(id="health-panel")
                    with TabPane("Memory", id="tab-memory"):
                        yield MemoryPanel(id="memory-panel")
                    with TabPane("DAG", id="tab-dag"):
                        yield DAGPanel(id="dag-panel")
                    with TabPane("Briefing", id="tab-briefing"):
                        yield BriefingPanel(id="briefing-panel")
                    with TabPane("Pool", id="tab-pool"):
                        yield ContextPoolPanel(id="pool-panel")
                    with TabPane("Queue", id="tab-queue"):
                        yield TaskQueuePanel(id="queue-panel")
                    with TabPane("Observe", id="tab-observe"):
                        yield ObservabilityPanel(id="observe-panel")
                    with TabPane("Alerts", id="tab-alerts"):
                        yield AlertsPanel(id="alerts-panel")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize connection and start background workers."""
        self.title = f"kantorku — session {self._session_id}"
        self._add_system_message(
            f"[bold cyan]KantorKu TUI v0.4.0[/bold cyan]\n"
            f"Session: {self._session_id}\n"
            f"Server: {self.server_url}\n\n"
            f"[dim]Type a message and press Enter to chat with the Conductor.[/dim]\n"
            f"[dim]Slash commands: /help /status /workers /health /cost /memory /dag[/dim]\n"
            f"[dim]  /briefing /pool /queue /trace /hooks /cache /config /alerts[/dim]\n"
            f"[dim]  /export /theme /metrics /delegate /accept /revise /code /reset[/dim]\n"
            f"[dim]Quick commands: accept, yes, revise <feedback>[/dim]\n"
            f"[dim]Press Ctrl+Q to quit, Tab to switch panels, ↑/↓ for history.[/dim]\n"
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
                log.write(Text.from_markup(""))
            elif role == "result":
                log.write(Text.from_markup("[bold magenta]Result>[/bold magenta]"))
                log.write(render_markdown(content))
                log.write(Text.from_markup(""))
            elif role == "streaming":
                # Streaming chunks — write directly
                log.write(Text.from_markup(content))
            elif role == "task_result":
                # Use render_task_result for structured results
                log.write(render_task_result(content) if isinstance(content, dict) else render_markdown(str(content)))
                log.write(Text.from_markup(""))
            else:
                log.write(Text.from_markup(
                    f"[bold]{role}>[/bold] {content}"
                ))
        except NoMatches:
            pass

    def _add_streaming_chunk(self, chunk: str) -> None:
        """Handle a streaming LLM chunk — write incrementally."""
        self._streaming_text += chunk
        try:
            log = self.query_one("#chat-log", RichLog)
            # Start streaming marker
            if not self._is_streaming:
                self._is_streaming = True
                log.write(Text.from_markup("[dim cyan]Conductor (streaming)...[/dim cyan]"))

            # Write chunk as it arrives
            log.write(chunk)
        except NoMatches:
            pass

    def _finish_streaming(self) -> None:
        """Finish streaming and render the complete markdown."""
        if self._is_streaming and self._streaming_text:
            try:
                log = self.query_one("#chat-log", RichLog)
                # Render final markdown
                log.write(Text.from_markup(""))
                log.write(render_markdown(self._streaming_text))
                log.write(Text.from_markup(""))
            except NoMatches:
                pass

        self._is_streaming = False
        self._streaming_text = ""

    # ── Input History ──────────────────────────────────────────────

    def action_history_up(self) -> None:
        """Navigate up in input history."""
        if not self._input_history:
            return
        if self._history_index < len(self._input_history) - 1:
            self._history_index += 1
        try:
            chat_input = self.query_one("#chat-input", Input)
            idx = len(self._input_history) - 1 - self._history_index
            chat_input.value = self._input_history[idx]
        except NoMatches:
            pass

    def action_history_down(self) -> None:
        """Navigate down in input history."""
        if self._history_index > 0:
            self._history_index -= 1
            try:
                chat_input = self.query_one("#chat-input", Input)
                idx = len(self._input_history) - 1 - self._history_index
                chat_input.value = self._input_history[idx]
            except NoMatches:
                pass
        elif self._history_index == 0:
            self._history_index = -1
            try:
                chat_input = self.query_one("#chat-input", Input)
                chat_input.value = ""
            except NoMatches:
                pass

    # ── Connection ─────────────────────────────────────────────────

    @work(exclusive=True, exit_on_error=False)
    async def _connect(self) -> None:
        """Connect to the kantorku server."""
        self.connection_state = "connecting"
        self._add_system_message("[yellow]Connecting to server...[/yellow]")

        try:
            await self._connection.connect()
            self.connection_state = "connected"
            self._reconnect_attempts = 0  # Reset on successful connect
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
            # Auto-reconnect
            self._schedule_reconnect()

    def _schedule_reconnect(self) -> None:
        """Schedule a reconnection attempt with exponential backoff."""
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            self._add_system_message(
                f"[red bold]Max reconnection attempts ({self._max_reconnect_attempts}) reached.[/red bold]\n"
                f"[dim]Use /reset to try again or restart the TUI.[/dim]"
            )
            return

        delay = self._reconnect_delay * (2 ** self._reconnect_attempts)
        self._reconnect_attempts += 1

        self._add_system_message(
            f"[yellow]Reconnecting in {delay:.0f}s (attempt {self._reconnect_attempts}/{self._max_reconnect_attempts})...[/yellow]"
        )
        self._reconnect_worker(delay)

    @work(exclusive=True, exit_on_error=False, group="reconnect")
    async def _reconnect_worker(self, delay: float) -> None:
        """Wait and attempt reconnection."""
        await asyncio.sleep(delay)
        if self.connection_state != "connected":
            self._connect()

    @work(exclusive=True, exit_on_error=False, group="poll_status")
    async def _poll_status(self) -> None:
        """Periodically poll server status for all dashboard panels."""
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
                        alerts_data = health_data.get("alerts", {})
                        active_alerts = alerts_data.get("active", []) if isinstance(alerts_data, dict) else []
                        panel.update_data(providers=providers, cost=cost, alerts=active_alerts)
                    except NoMatches:
                        pass

                    # Update queue
                    queue_data = status.get("queue", status.get("task_queue", {}))
                    try:
                        queue_panel = self.query_one("#queue-panel", TaskQueuePanel)
                        queue_panel.update_data(
                            pending=queue_data.get("pending_items", []),
                            active=queue_data.get("active_items", []),
                            dlq=queue_data.get("dead_letter_items", []),
                            stats=queue_data,
                        )
                    except NoMatches:
                        pass

                    # Update pool
                    pool_data = status.get("pool", {})
                    try:
                        pool_panel = self.query_one("#pool-panel", ContextPoolPanel)
                        pool_panel.update_data(
                            pool_status=pool_data,
                            prefetch_queue=pool_data.get("queue", []),
                        )
                    except NoMatches:
                        pass

                # Fetch observability data (less frequent)
                try:
                    metrics = await self._connection.get_metrics()
                    observe_panel = self.query_one("#observe-panel", ObservabilityPanel)
                    observe_panel.update_data(metrics=metrics)
                except (NoMatches, Exception):
                    pass

                try:
                    spans_data = await self._connection.get_spans()
                    spans = spans_data.get("spans", []) if spans_data else []
                    observe_panel = self.query_one("#observe-panel", ObservabilityPanel)
                    observe_panel.update_data(spans=spans)
                except (NoMatches, Exception):
                    pass

                # Fetch memory stats
                try:
                    memory_data = await self._connection.get_memory_stats()
                    mem_panel = self.query_one("#memory-panel", MemoryPanel)
                    mem_panel.update_data(
                        ring1=memory_data.get("ring1", {}),
                        ring2=memory_data.get("ring2", {}),
                        contexts=memory_data.get("recent_contexts", []),
                    )
                except (NoMatches, Exception):
                    pass

                # Fetch alerts
                try:
                    health = await self._connection.get_health()
                    if health:
                        alerts = health.get("alerts", {})
                        active_alerts = alerts.get("active", []) if isinstance(alerts, dict) else []
                        alerts_panel = self.query_one("#alerts-panel", AlertsPanel)
                        alerts_panel.update_alerts(active_alerts)
                except (NoMatches, Exception):
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
                    self._finish_streaming()
                    self._add_chat_message("conductor", event.get("content", ""))
                elif event_type == "contract_ready":
                    contract = event.get("contract", event.get("todos", {}))
                    self.pending_contract = contract
                    try:
                        cp = self.query_one("#contract-area", ContractPanel)
                        cp.contract_data = contract
                    except NoMatches:
                        pass
                    # Update DAG panel
                    try:
                        dag_panel = self.query_one("#dag-panel", DAGPanel)
                        todos = contract.get("todos", []) if isinstance(contract, dict) else []
                        groups = contract.get("dag_groups", []) if isinstance(contract, dict) else []
                        dag_panel.update_dag(groups, todos)
                    except NoMatches:
                        pass
                    self._add_system_message(
                        "[green bold]Contract ready![/green bold] "
                        "Type [bold]accept[/bold] to approve or provide feedback."
                    )
                elif event_type == "work_done":
                    self._finish_streaming()
                    result = event.get("result", {})
                    self._add_system_message(
                        "[green bold]Work completed![/green bold]"
                    )
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
                elif event_type == "llm_stream_start":
                    self._streaming_text = ""
                    self._is_streaming = False
                elif event_type == "llm_stream_chunk":
                    chunk = event.get("content", event.get("chunk", ""))
                    if chunk:
                        self._add_streaming_chunk(chunk)
                elif event_type == "llm_stream_done":
                    self._finish_streaming()
                elif event_type == "briefing_message":
                    try:
                        bp = self.query_one("#briefing-panel", BriefingPanel)
                        bp.add_message(event)
                    except NoMatches:
                        pass
                elif event_type == "briefing_opened":
                    self._add_system_message(
                        "[magenta]Briefing room opened — team is discussing...[/magenta]"
                    )
                    try:
                        bp = self.query_one("#briefing-panel", BriefingPanel)
                        bp.update_briefing(round_num=1, consensus=False)
                    except NoMatches:
                        pass
                elif event_type == "worker_speak_up":
                    from_id = event.get("from", "worker")
                    content = event.get("content", "")
                    self._add_system_message(
                        f"[magenta]{from_id} speaks up:[/magenta] {content[:80]}"
                    )
                elif event_type == "context_fetch_done":
                    self._add_system_message(
                        f"[dim]Context prefetched: {event.get('source', '?')}[/dim]"
                    )
                elif event_type == "error_logged":
                    self._add_system_message(
                        f"[red]Error: {event.get('error', '?')}[/red]"
                    )

        except asyncio.CancelledError:
            pass
        except Exception as e:
            if self.connection_state == "connected":
                self._add_system_message(f"[yellow]Event stream error: {e}[/yellow]")
                self._schedule_reconnect()

    # ── Input Handling ─────────────────────────────────────────────

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user pressing Enter in the chat input."""
        message = event.value.strip()
        if not message:
            return

        # Clear input
        event.input.value = ""

        # Add to history
        self._input_history.append(message)
        self._history_index = -1

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
                    try:
                        dag_panel = self.query_one("#dag-panel", DAGPanel)
                        todos = contract.get("todos", []) if isinstance(contract, dict) else []
                        groups = contract.get("dag_groups", []) if isinstance(contract, dict) else []
                        dag_panel.update_dag(groups, todos)
                    except NoMatches:
                        pass
                    self._add_system_message(
                        "[green bold]Contract ready![/green bold] "
                        "Type [bold]accept[/bold] to approve or provide feedback."
                    )
                elif event_type == "llm_stream_chunk":
                    chunk = event.get("content", event.get("chunk", ""))
                    if chunk:
                        self._add_streaming_chunk(chunk)
                elif event_type == "llm_stream_done":
                    self._finish_streaming()
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

    # ── Actions ────────────────────────────────────────────────────

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


# ── Embedded Mode ───────────────────────────────────────────────────


class EmbeddedKantorKuTUI(KantorKuTUI):
    """
    KantorKu TUI in embedded mode — runs the Office directly in-process.

    No server needed. The TUI creates an Office instance and
    interacts with it directly. All framework features are accessible
    without a network connection.
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
                elif hasattr(event, '__dict__'):
                    data = event.__dict__
                else:
                    data = event

                # Add to events stream
                stream = self.query_one("#events-stream", EventsStream)
                stream.add_event(data)

                # Handle event types
                event_type = data.get("type", "")
                if event_type == "manager_message":
                    self._add_chat_message("conductor", data.get("content", ""))
                elif event_type == "contract_ready":
                    contract = data.get("contract", {})
                    self.pending_contract = contract
                    try:
                        cp = self.query_one("#contract-area", ContractPanel)
                        cp.contract_data = contract
                    except NoMatches:
                        pass
                    try:
                        dag_panel = self.query_one("#dag-panel", DAGPanel)
                        todos = contract.get("todos", []) if isinstance(contract, dict) else []
                        groups = contract.get("dag_groups", []) if isinstance(contract, dict) else []
                        dag_panel.update_dag(groups, todos)
                    except NoMatches:
                        pass
                    self._add_system_message(
                        "[green bold]Contract ready![/green bold] "
                        "Type [bold]accept[/bold] to approve."
                    )
                elif event_type == "work_done":
                    self._add_system_message("[green bold]Work completed![/green bold]")
                    result = data.get("result", {})
                    for tid, r in result.get("results", {}).items():
                        output = r.get("output", "")
                        if output:
                            self._add_chat_message("result", output[:2000])
                elif event_type == "briefing_message":
                    try:
                        bp = self.query_one("#briefing-panel", BriefingPanel)
                        bp.add_message(data)
                    except NoMatches:
                        pass
                elif event_type == "briefing_opened":
                    try:
                        bp = self.query_one("#briefing-panel", BriefingPanel)
                        bp.update_briefing(round_num=1, consensus=False)
                    except NoMatches:
                        pass
                elif event_type == "worker_speak_up":
                    from_id = data.get("from", "worker")
                    content = data.get("content", "")
                    self._add_system_message(
                        f"[magenta]{from_id} speaks up:[/magenta] {content[:80]}"
                    )
                elif event_type == "llm_stream_start":
                    self._streaming_text = ""
                    self._is_streaming = False
                elif event_type == "llm_stream_chunk":
                    chunk = data.get("content", data.get("chunk", ""))
                    if chunk:
                        self._add_streaming_chunk(chunk)
                elif event_type == "llm_stream_done":
                    self._finish_streaming()
                elif event_type == "task_done":
                    from_id = data.get("from", "worker")
                    files = data.get("files", [])
                    if files:
                        self._add_system_message(
                            f"[green]{from_id}[/green] produced: {', '.join(files)}"
                        )
                elif event_type == "task_failed":
                    from_id = data.get("from", "worker")
                    error = data.get("error", "unknown")
                    self._add_system_message(
                        f"[red]{from_id}[/red] failed: {error}"
                    )
                elif event_type == "context_fetch_done":
                    self._add_system_message(
                        f"[dim]Context prefetched: {data.get('source', '?')}[/dim]"
                    )
                elif event_type == "error_logged":
                    self._add_system_message(
                        f"[red]Error: {data.get('error', '?')}[/red]"
                    )

            except NoMatches:
                pass

        # Subscribe to the global event bus
        if hasattr(self._office, 'bus') and self._office.bus:
            self._office.bus.subscribe_global(on_event)

        # Periodic status update
        while self.connection_state == "connected":
            self._update_embedded_status()
            await asyncio.sleep(5)

    def _update_embedded_status(self) -> None:
        """Update all dashboard panels from embedded office."""
        if not self._office:
            return

        # Workers
        try:
            workers = self._office.get_worker_status()
            grid = self.query_one("#worker-grid", WorkerGrid)
            grid.update_workers(workers)
        except (NoMatches, Exception):
            pass

        # Health & cost
        try:
            cost = self._office.get_cost_report() if hasattr(self._office, 'cost_tracker') and self._office.cost_tracker else {}
            health_data = {}
            if hasattr(self._office, '_health') and self._office._health:
                ph = getattr(self._office._health, '_provider_health', {})
                health_data = {k: v.to_dict() for k, v in ph.items()}
            panel = self.query_one("#health-panel", HealthPanel)
            alerts = []
            if hasattr(self._office, '_health') and self._office._health:
                alerts = [a.to_dict() for a in self._office._health.alerts.get_active()]
            panel.update_data(providers=health_data, cost=cost, alerts=alerts)
        except (NoMatches, Exception):
            pass

        # Memory
        try:
            ring1_stats = {}
            ring2_stats = {}
            if hasattr(self._office, 'ring1') and self._office.ring1:
                ring1_stats = self._office.ring1.get_stats()
            if hasattr(self._office, 'ring2') and self._office.ring2:
                ring2_stats = self._office.ring2.get_stats()
            mem_panel = self.query_one("#memory-panel", MemoryPanel)
            mem_panel.update_data(ring1=ring1_stats, ring2=ring2_stats)
        except (NoMatches, Exception):
            pass

        # Observability
        try:
            metrics = {}
            if hasattr(self._office, 'get_metrics_summary'):
                metrics = self._office.get_metrics_summary()
            spans_data = []
            if hasattr(self._office, 'get_observability_spans'):
                spans_data = self._office.get_observability_spans(20)
            obs_panel = self.query_one("#observe-panel", ObservabilityPanel)
            obs_panel.update_data(metrics=metrics, spans=spans_data)
        except (NoMatches, Exception):
            pass

        # Alerts
        try:
            alerts = []
            if hasattr(self._office, '_health') and self._office._health:
                alerts = [a.to_dict() for a in self._office._health.alerts.get_active()]
            alerts_panel = self.query_one("#alerts-panel", AlertsPanel)
            alerts_panel.update_alerts(alerts)
        except (NoMatches, Exception):
            pass

        # Pool
        try:
            pool_data = {}
            if hasattr(self._office, 'get_pool_status'):
                pool_data = self._office.get_pool_status()
            pool_panel = self.query_one("#pool-panel", ContextPoolPanel)
            pool_panel.update_data(pool_status=pool_data)
        except (NoMatches, Exception):
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
                    try:
                        dag_panel = self.query_one("#dag-panel", DAGPanel)
                        todos = contract.get("todos", []) if isinstance(contract, dict) else []
                        groups = contract.get("dag_groups", []) if isinstance(contract, dict) else []
                        dag_panel.update_dag(groups, todos)
                    except NoMatches:
                        pass
                    self._add_system_message(
                        "[green bold]Contract ready![/green bold] "
                        "Type [bold]accept[/bold] to approve."
                    )
                elif event_type == "llm_stream_chunk":
                    chunk = event.get("content", event.get("chunk", ""))
                    if chunk:
                        self._add_streaming_chunk(chunk)
                elif event_type == "llm_stream_done":
                    self._finish_streaming()

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
        cost = self._office.get_cost_report() if hasattr(self._office, 'cost_tracker') and self._office.cost_tracker else {}

        lines = [
            f"[bold]Mode:[/bold] Embedded",
            f"[bold]Workers:[/bold] {len(workers)}",
            f"[bold]Session:[/bold] {self._session_id}",
        ]

        if cost:
            total = cost.get("total_cost_usd", 0)
            calls = cost.get("total_calls", 0)
            lines.append(f"[bold]Cost:[/bold] ${total:.4f} ({calls} calls)")

        # Memory stats
        if hasattr(self._office, 'ring1') and self._office.ring1:
            r1 = self._office.ring1.get_stats()
            lines.append(f"[bold]Ring1:[/bold] {r1.get('context_count', '?')} contexts")

        if hasattr(self._office, 'ring2') and self._office.ring2:
            r2 = self._office.ring2.get_stats()
            lines.append(f"[bold]Ring2:[/bold] {r2.get('episode_count', '?')} episodes")

        self._add_system_message("\n".join(lines))

    async def action_quit(self) -> None:
        """Clean shutdown of embedded office."""
        if self._office:
            try:
                await self._office.shutdown()
            except Exception:
                pass
        self.exit()
