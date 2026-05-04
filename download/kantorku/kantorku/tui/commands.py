"""
Slash Commands — Quick commands for the TUI.

Provides a comprehensive /commands system for coders to quickly
interact with every aspect of the KantorKu office.

Commands:
    /help          — Show available commands
    /status        — Show office status
    /accept        — Accept current contract
    /revise ...    — Revise contract with feedback
    /workers       — Show worker grid
    /health        — Show provider health
    /cost          — Show cost report
    /sessions      — List active sessions
    /reset         — Reset current session
    /code ...      — Quick code task (auto-accept)
    /ask ...       — Ask the Conductor a question
    /memory        — Show memory stats (Ring1/Ring2/Ring3)
    /briefing      — Show briefing room transcript
    /dag           — Show task dependency graph
    /pool          — Show context pool status
    /queue         — Show task queue & DLQ
    /trace         — Show recent spans/traces
    /metrics       — Show observability metrics
    /hooks         — List registered hooks
    /cache         — Show cache stats
    /config        — View current configuration
    /alerts        — Show active alerts
    /delegate      — View worker delegations
    /export        — Export session to file
    /theme         — Switch color theme
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable


@dataclass
class SlashCommand:
    """A slash command definition."""
    name: str
    description: str
    usage: str
    handler: Callable[..., Awaitable[str]]


# Command registry
COMMANDS: dict[str, SlashCommand] = {}


def command(name: str, description: str, usage: str = ""):
    """Decorator to register a slash command handler."""
    def decorator(func: Callable[..., Awaitable[str]]) -> Callable[..., Awaitable[str]]:
        COMMANDS[name] = SlashCommand(
            name=name,
            description=description,
            usage=usage or f"/{name}",
            handler=func,
        )
        return func
    return decorator


def get_help_text() -> str:
    """Get formatted help text for all slash commands."""
    lines = [
        "[bold cyan]KantorKu Slash Commands:[/bold cyan]",
        "",
        "[bold]Chat & Contracts:[/bold]",
    ]
    max_name = max(len(name) for name in COMMANDS) if COMMANDS else 0

    # Group commands by category
    categories = {
        "Chat & Contracts": ["accept", "ask", "code", "revise"],
        "Monitoring": ["status", "workers", "health", "cost", "alerts", "sessions"],
        "Memory & Data": ["memory", "cache", "dag", "briefing", "pool", "queue"],
        "Observability": ["trace", "metrics", "hooks", "config"],
        "Session": ["reset", "export", "delegate", "theme"],
    }

    for cat, cmd_names in categories.items():
        cat_cmds = [(n, COMMANDS[n]) for n in cmd_names if n in COMMANDS]
        if cat_cmds:
            lines.append(f"\n[bold]{cat}:[/bold]")
            for name, cmd in cat_cmds:
                lines.append(
                    f"  [bold green]/{name:<{max_name}}[/bold green]  {cmd.description}"
                )
                if cmd.usage and cmd.usage != f"/{name}":
                    lines.append(f"  {'':>{max_name + 2}}  [dim]{cmd.usage}[/dim]")

    # Add uncategorized
    categorized = set()
    for names in categories.values():
        categorized.update(names)

    uncategorized = [(n, COMMANDS[n]) for n in sorted(COMMANDS.keys()) if n not in categorized]
    if uncategorized:
        lines.append(f"\n[bold]Other:[/bold]")
        for name, cmd in uncategorized:
            lines.append(
                f"  [bold green]/{name:<{max_name}}[/bold green]  {cmd.description}"
            )

    lines.append("")
    lines.append("[dim]Type a message without / to chat with the Conductor[/dim]")
    lines.append("[dim]Use ↑/↓ arrows to browse input history[/dim]")
    return "\n".join(lines)


async def handle_slash_command(
    text: str,
    tui: Any,
) -> str | None:
    """
    Parse and execute a slash command.

    Args:
        text: The full input text (starting with /)
        tui: The TUI app instance for context

    Returns:
        Response string, or None if not a slash command
    """
    text = text.strip()
    if not text.startswith("/"):
        return None

    parts = text[1:].split(None, 1)
    cmd_name = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    if cmd_name == "help":
        return get_help_text()

    if cmd_name not in COMMANDS:
        return f"[red]Unknown command: /{cmd_name}[/red]\n[dim]Type /help for available commands[/dim]"

    cmd = COMMANDS[cmd_name]
    return await cmd.handler(tui, args)


# ── Helper ──────────────────────────────────────────────────────────


def _is_remote(tui: Any) -> bool:
    """Check if TUI is in remote (server) mode."""
    return hasattr(tui, '_connection') and tui._connection._http_client is not None


def _is_embedded(tui: Any) -> bool:
    """Check if TUI is in embedded mode."""
    return hasattr(tui, '_office') and tui._office is not None


# ── Command Handlers ────────────────────────────────────────────────


@command("status", "Show office status", "/status")
async def cmd_status(tui: Any, args: str) -> str:
    """Show current office status."""
    lines = [
        "[bold]Office Status[/bold]",
        f"  Session:    {tui._session_id}",
        f"  Connection: {tui.connection_state}",
    ]

    if _is_remote(tui):
        try:
            status = await tui._connection.get_status()
            if status:
                workers = status.get("workers", [])
                lines.append(f"  Workers:    {len(workers)}")
                lines.append(f"  Mode:       Remote")

                cost = status.get("cost", {})
                if cost:
                    total = cost.get("total_cost_usd", 0)
                    calls = cost.get("total_calls", 0)
                    lines.append(f"  Cost:       ${total:.4f} ({calls} calls)")

                pool = status.get("pool", {})
                if pool:
                    lines.append(f"  Pool:       {pool.get('worker_count', '?')} workers")
        except Exception:
            lines.append("  [dim](status unavailable)[/dim]")

    elif _is_embedded(tui):
        workers = tui._office.get_worker_status()
        lines.append(f"  Workers:    {len(workers)}")
        lines.append(f"  Mode:       Embedded")

        if hasattr(tui._office, 'ring1') and tui._office.ring1:
            r1 = tui._office.ring1.get_stats()
            lines.append(f"  Ring1:      {r1.get('context_count', '?')} contexts")

        if hasattr(tui._office, 'cost_tracker') and tui._office.cost_tracker:
            cost = tui._office.get_cost_report()
            total = cost.get("total_cost_usd", 0)
            calls = cost.get("total_calls", 0)
            lines.append(f"  Cost:       ${total:.4f} ({calls} calls)")

    return "\n".join(lines)


@command("accept", "Accept current contract", "/accept")
async def cmd_accept(tui: Any, args: str) -> str:
    """Accept the current contract."""
    if not tui.pending_contract:
        return "[yellow]No contract to accept.[/yellow]"

    await tui._send_accept()
    return "[green]Contract accepted![/green]"


@command("revise", "Revise contract with feedback", "/revise <feedback>")
async def cmd_revise(tui: Any, args: str) -> str:
    """Revise the current contract."""
    if not args:
        return "[yellow]Usage: /revise <your feedback>[/yellow]"

    await tui._send_revise(args)
    return f"[yellow]Revision requested: {args}[/yellow]"


@command("workers", "Show worker status grid", "/workers")
async def cmd_workers(tui: Any, args: str) -> str:
    """Show all workers and their status."""
    from rich.table import Table
    from io import StringIO
    from rich.console import Console
    from kantorku.tui.themes import STATUS_COLORS, STATUS_ICONS

    table = Table(title="Workers", show_header=True)
    table.add_column("ID", style="bold")
    table.add_column("Status")
    table.add_column("Model")
    table.add_column("Squad")
    table.add_column("Role")

    if _is_remote(tui):
        try:
            status = await tui._connection.get_status()
            workers = status.get("workers", []) if status else []
        except Exception:
            workers = []
    elif _is_embedded(tui):
        workers = tui._office.get_worker_status()
    else:
        workers = []

    if not workers:
        return "[dim]No workers available[/dim]"

    for w in workers:
        status = w.get("status", "?")
        color = STATUS_COLORS.get(status, "dim")
        icon = STATUS_ICONS.get(status, "?")
        s = f"[{color}]{icon} {status}[/{color}]"
        table.add_row(
            w.get("id", "?"),
            s,
            w.get("model", "N/A") or "N/A",
            w.get("squad", "") or "",
            w.get("role", "")[:30] or "",
        )

    console = Console(file=StringIO(), force_terminal=True)
    console.print(table)
    return console.file.getvalue()


@command("health", "Show provider health dashboard", "/health")
async def cmd_health(tui: Any, args: str) -> str:
    """Show provider health and circuit breaker status."""
    lines = ["[bold]Provider Health[/bold]", ""]

    if _is_remote(tui):
        try:
            health = await tui._connection.get_health()
            if health:
                providers = health.get("providers", {})
                for name, data in providers.items():
                    circuit = data.get("circuit_state", "closed")
                    healthy = data.get("is_healthy", True)
                    lat = data.get("avg_latency_ms", 0)

                    icon = "[green]OK[/green]" if healthy else "[red]DOWN[/red]"
                    cb = {"closed": "[green]closed[/green]", "open": "[red bold]OPEN[/red bold]", "half_open": "[yellow]half_open[/yellow]"}.get(circuit, circuit)

                    lines.append(f"  {name:14s} {icon}  circuit:{cb}  latency:{lat:.0f}ms")

                alerts = health.get("alerts", {})
                if isinstance(alerts, dict):
                    active = alerts.get("total_active", 0)
                    critical = alerts.get("critical", 0)
                    if active > 0:
                        lines.append(f"\n  [red]{active} active alerts ({critical} critical)[/red]")
        except Exception:
            lines.append("  [dim](health unavailable)[/dim]")

    elif _is_embedded(tui):
        try:
            if hasattr(tui._office, '_health') and tui._office._health:
                for name, status in tui._office._health._provider_health.items():
                    d = status.to_dict()
                    circuit = d.get("circuit_state", "closed")
                    healthy = d.get("is_healthy", True)
                    lat = d.get("avg_latency_ms", 0)
                    icon = "[green]OK[/green]" if healthy else "[red]DOWN[/red]"
                    cb = {"closed": "[green]closed[/green]", "open": "[red bold]OPEN[/red bold]", "half_open": "[yellow]half_open[/yellow]"}.get(circuit, circuit)
                    lines.append(f"  {name:14s} {icon}  circuit:{cb}  latency:{lat:.0f}ms")

                alerts = tui._office._health.alerts.get_active()
                if alerts:
                    lines.append(f"\n  [red]{len(alerts)} active alerts[/red]")
            else:
                lines.append("  [dim]Health checker not available[/dim]")
        except Exception as e:
            lines.append(f"  [dim](health error: {e})[/dim]")
    else:
        lines.append("  [dim]Not connected[/dim]")

    return "\n".join(lines)


@command("cost", "Show cost tracking report", "/cost")
async def cmd_cost(tui: Any, args: str) -> str:
    """Show LLM cost report."""
    lines = ["[bold]Cost Report[/bold]", ""]

    if _is_remote(tui):
        try:
            cost = await tui._connection.get_cost()
            if cost:
                total = cost.get("total_cost_usd", 0)
                calls = cost.get("total_calls", 0)
                by_model = cost.get("by_model", {})

                lines.append(f"  Total: ${total:.4f} ({calls} calls)")

                if by_model:
                    lines.append("")
                    lines.append("  [bold]By Model:[/bold]")
                    for model, data in by_model.items():
                        m_cost = data.get("cost_usd", 0)
                        m_calls = data.get("calls", 0)
                        lines.append(f"    {model:30s} ${m_cost:.4f} ({m_calls} calls)")
        except Exception:
            lines.append("  [dim](cost unavailable)[/dim]")

    elif _is_embedded(tui):
        try:
            if hasattr(tui._office, 'cost_tracker') and tui._office.cost_tracker:
                cost = tui._office.get_cost_report()
                total = cost.get("total_cost_usd", 0)
                calls = cost.get("total_calls", 0)
                by_model = cost.get("by_model", {})
                lines.append(f"  Total: ${total:.4f} ({calls} calls)")
                if by_model:
                    lines.append("")
                    lines.append("  [bold]By Model:[/bold]")
                    for model, data in by_model.items():
                        m_cost = data.get("cost_usd", 0)
                        m_calls = data.get("calls", 0)
                        lines.append(f"    {model:30s} ${m_cost:.4f} ({m_calls} calls)")
            else:
                lines.append("  [dim]Cost tracking not enabled[/dim]")
        except Exception as e:
            lines.append(f"  [dim](cost error: {e})[/dim]")
    else:
        lines.append("  [dim]Not connected[/dim]")

    return "\n".join(lines)


@command("sessions", "List active sessions", "/sessions")
async def cmd_sessions(tui: Any, args: str) -> str:
    """List active sessions."""
    lines = ["[bold]Active Sessions[/bold]", ""]

    if _is_remote(tui):
        try:
            sessions = await tui._connection.get_sessions()
            if sessions:
                for s in sessions:
                    sid = s.get("session_id", "?")
                    state = s.get("state", "?")
                    title = s.get("contract_title", "")
                    lines.append(f"  {sid:12s} [{state}] {title}")
            else:
                lines.append("  [dim]No active sessions[/dim]")
        except Exception:
            lines.append("  [dim](sessions unavailable)[/dim]")

    elif _is_embedded(tui):
        lines.append(f"  {tui._session_id:12s} [green]current[/green]")
        if hasattr(tui._office, 'conductor') and hasattr(tui._office.conductor, '_sessions'):
            for sid in tui._office.conductor._sessions:
                if sid != tui._session_id:
                    lines.append(f"  {sid:12s} [dim]active[/dim]")
    else:
        lines.append(f"  {tui._session_id:12s} [current]")

    return "\n".join(lines)


@command("reset", "Reset current session", "/reset")
async def cmd_reset(tui: Any, args: str) -> str:
    """Reset the current session."""
    import uuid
    old_session = tui._session_id
    tui._session_id = uuid.uuid4().hex[:12]
    tui.pending_contract = {}

    try:
        cp = tui.query_one("#contract-area")
        cp.contract_data = {}
    except Exception:
        pass

    return (
        f"[yellow]Session reset![/yellow]\n"
        f"  Old: {old_session}\n"
        f"  New: {tui._session_id}"
    )


@command("code", "Quick code task (auto-accept)", "/code <task description>")
async def cmd_code(tui: Any, args: str) -> str:
    """Quick code task — sends message and auto-accepts contract."""
    if not args:
        return "[yellow]Usage: /code <task description>[/yellow]\n[dim]Example: /code implement a rate limiter in Rust[/dim]"

    await tui._send_message(args)

    if tui.pending_contract:
        await tui._send_accept()
        return "[green]Code task submitted and accepted![/green]"

    return "[yellow]Waiting for contract...[/yellow]"


@command("ask", "Ask the Conductor a question", "/ask <question>")
async def cmd_ask(tui: Any, args: str) -> str:
    """Ask the Conductor a question."""
    if not args:
        return "[yellow]Usage: /ask <question>[/yellow]"

    await tui._send_message(args)
    return ""  # Response will come via events


@command("memory", "Show 3-Ring memory stats", "/memory")
async def cmd_memory(tui: Any, args: str) -> str:
    """Show memory system statistics."""
    lines = ["[bold cyan]Three-Ring Memory[/bold cyan]", ""]

    if _is_remote(tui):
        try:
            memory_data = await tui._connection.get_memory_stats()
            if memory_data:
                ring1 = memory_data.get("ring1", {})
                ring2 = memory_data.get("ring2", {})

                lines.append("[bold]Ring 1 (DuckDB — Hot):[/bold]")
                lines.append(f"  Contexts: {ring1.get('context_count', '?')}")
                lines.append(f"  Sessions: {ring1.get('session_count', '?')}")
                lines.append(f"  Task Results: {ring1.get('task_result_count', '?')}")
                lines.append(f"  History: {ring1.get('history_count', '?')}")
                lines.append(f"  DB Size: {ring1.get('db_size_mb', '?')} MB")

                lines.append("")
                lines.append("[bold]Ring 2 (SQLite — Warm):[/bold]")
                lines.append(f"  Episodes: {ring2.get('episode_count', '?')}")
                lines.append(f"  Lessons: {ring2.get('lesson_count', '?')}")
                lines.append(f"  Audit Trails: {ring2.get('audit_trail_count', '?')}")
                lines.append(f"  DB Size: {ring2.get('db_size_mb', '?')} MB")

                lines.append("")
                lines.append("[dim]Ring 3 (Cognee GraphRAG — Cold): Not yet connected[/dim]")
            else:
                lines.append("  [dim]Memory data unavailable[/dim]")
        except Exception:
            lines.append("  [dim](memory stats unavailable)[/dim]")

    elif _is_embedded(tui):
        try:
            if hasattr(tui._office, 'ring1') and tui._office.ring1:
                r1 = tui._office.ring1.get_stats()
                lines.append("[bold]Ring 1 (DuckDB — Hot):[/bold]")
                lines.append(f"  Contexts: {r1.get('context_count', '?')}")
                lines.append(f"  Sessions: {r1.get('session_count', '?')}")
                lines.append(f"  Task Results: {r1.get('task_result_count', '?')}")
                lines.append(f"  History: {r1.get('history_count', '?')}")
                lines.append(f"  DB Size: {r1.get('db_size_mb', '?')} MB")
            else:
                lines.append("  [dim]Ring 1 not available[/dim]")

            lines.append("")
            if hasattr(tui._office, 'ring2') and tui._office.ring2:
                r2 = tui._office.ring2.get_stats()
                lines.append("[bold]Ring 2 (SQLite — Warm):[/bold]")
                lines.append(f"  Episodes: {r2.get('episode_count', '?')}")
                lines.append(f"  Lessons: {r2.get('lesson_count', '?')}")
                lines.append(f"  Audit Trails: {r2.get('audit_trail_count', '?')}")
                lines.append(f"  DB Size: {r2.get('db_size_mb', '?')} MB")
            else:
                lines.append("  [dim]Ring 2 not available[/dim]")

            lines.append("")
            lines.append("[dim]Ring 3 (Cognee GraphRAG — Cold): Not yet connected[/dim]")
        except Exception as e:
            lines.append(f"  [dim](memory error: {e})[/dim]")
    else:
        lines.append("  [dim]Not connected[/dim]")

    return "\n".join(lines)


@command("briefing", "Show briefing room transcript", "/briefing")
async def cmd_briefing(tui: Any, args: str) -> str:
    """Show the latest briefing room discussion."""
    lines = ["[bold magenta]Briefing Room[/bold magenta]", ""]

    try:
        bp = tui.query_one("#briefing-panel")
        if hasattr(bp, '_messages') and bp._messages:
            for msg in bp._messages[-20:]:
                from_id = msg.get("from", "?")
                content = msg.get("content", "")[:100]
                msg_type = msg.get("type", "message")
                lines.append(f"  [bold]{from_id}[/bold]: {content}")
        else:
            lines.append("  [dim]No briefing messages yet[/dim]")
            lines.append("  [dim]Accept a contract to start a team briefing[/dim]")
    except Exception:
        lines.append("  [dim]Briefing panel not available[/dim]")

    return "\n".join(lines)


@command("dag", "Show task dependency graph", "/dag")
async def cmd_dag(tui: Any, args: str) -> str:
    """Show task dependency DAG."""
    lines = ["[bold cyan]Task DAG[/bold cyan]", ""]

    try:
        dp = tui.query_one("#dag-panel")
        if hasattr(dp, '_todos') and dp._todos:
            for todo in dp._todos:
                status = todo.get("status", "pending")
                icon = {"pending": "[dim]○[/dim]", "in_progress": "[yellow]◑[/yellow]",
                        "done": "[green]●[/green]", "failed": "[red]●[/red]"}.get(status, "○")
                desc = todo.get("description", "?")[:50]
                assigned = todo.get("assigned_to", "unassigned")
                lines.append(f"  {icon} [{assigned}] {desc}")

            pending = sum(1 for t in dp._todos if t.get("status") == "pending")
            in_progress = sum(1 for t in dp._todos if t.get("status") == "in_progress")
            done = sum(1 for t in dp._todos if t.get("status") == "done")
            failed = sum(1 for t in dp._todos if t.get("status") == "failed")
            lines.append(f"\n  [bold]Progress:[/bold] {done} done, {in_progress} active, {pending} pending, {failed} failed")
        else:
            lines.append("  [dim]No DAG data yet[/dim]")
            lines.append("  [dim]Accept a contract to see task dependencies[/dim]")
    except Exception:
        lines.append("  [dim]DAG panel not available[/dim]")

    return "\n".join(lines)


@command("pool", "Show context pool status", "/pool")
async def cmd_pool(tui: Any, args: str) -> str:
    """Show context pool prefetch status."""
    lines = ["[bold cyan]Context Pool[/bold cyan]", ""]

    if _is_remote(tui):
        try:
            status = await tui._connection.get_status()
            pool = status.get("pool", {}) if status else {}
            if pool:
                lines.append(f"  Workers: {pool.get('worker_count', '?')}")
                lines.append(f"  Queue Depth: {pool.get('queue_depth', '?')}")
                lines.append(f"  Active Prefetch: {pool.get('active_prefetch', '?')}")
                lines.append(f"  Completed: {pool.get('completed', '?')}")
                lines.append(f"  Failed: {pool.get('failed', '?')}")
            else:
                lines.append("  [dim]Pool data unavailable[/dim]")
        except Exception:
            lines.append("  [dim](pool stats unavailable)[/dim]")

    elif _is_embedded(tui):
        try:
            if hasattr(tui._office, 'get_pool_status'):
                pool = tui._office.get_pool_status()
                lines.append(f"  Workers: {pool.get('worker_count', '?')}")
                lines.append(f"  Queue Depth: {pool.get('queue_depth', '?')}")
                lines.append(f"  Active Prefetch: {pool.get('active_prefetch', '?')}")
                lines.append(f"  Completed: {pool.get('completed', '?')}")
                lines.append(f"  Failed: {pool.get('failed', '?')}")
            else:
                lines.append("  [dim]Pool not available[/dim]")
        except Exception:
            lines.append("  [dim](pool error)[/dim]")
    else:
        lines.append("  [dim]Not connected[/dim]")

    return "\n".join(lines)


@command("queue", "Show task queue & DLQ", "/queue")
async def cmd_queue(tui: Any, args: str) -> str:
    """Show task queue status."""
    lines = ["[bold cyan]Task Queue[/bold cyan]", ""]

    try:
        qp = tui.query_one("#queue-panel")
        if hasattr(qp, '_stats') and qp._stats:
            s = qp._stats
            lines.append(f"  Pending: {s.get('pending', len(qp._pending))}")
            lines.append(f"  Active: {s.get('active', len(qp._active))}")
            lines.append(f"  DLQ: {s.get('dead_letter_count', len(qp._dlq))}")
            lines.append(f"  Total Processed: {s.get('total_processed', '?')}")
        else:
            lines.append(f"  Pending: {len(qp._pending) if hasattr(qp, '_pending') else 0}")
            lines.append(f"  Active: {len(qp._active) if hasattr(qp, '_active') else 0}")
            lines.append(f"  DLQ: {len(qp._dlq) if hasattr(qp, '_dlq') else 0}")

        # Show DLQ entries
        if hasattr(qp, '_dlq') and qp._dlq:
            lines.append("")
            lines.append("[bold red]Dead Letter Queue:[/bold red]")
            for t in qp._dlq[:5]:
                lines.append(f"  {t.get('id', '?')[:10]}: {t.get('error', '?')[:40]}")
    except Exception:
        lines.append("  [dim]Queue panel not available[/dim]")

    return "\n".join(lines)


@command("trace", "Show recent spans/traces", "/trace [limit]")
async def cmd_trace(tui: Any, args: str) -> str:
    """Show recent tracing spans."""
    lines = ["[bold cyan]Traces[/bold cyan]", ""]
    limit = 20
    if args and args.isdigit():
        limit = min(int(args), 100)

    if _is_remote(tui):
        try:
            spans_data = await tui._connection.get_spans(limit)
            spans = spans_data.get("spans", []) if spans_data else []
            if spans:
                for s in spans[:limit]:
                    op = s.get("operation", "?")[:20]
                    dur = s.get("duration_ms", 0)
                    status = s.get("status", "?")
                    s_color = "green" if status == "ok" else "red" if status == "error" else "dim"
                    lines.append(f"  {op:20s} [{s_color}]{status}[/{s_color}] {dur:.0f}ms")
            else:
                lines.append("  [dim]No spans recorded[/dim]")
        except Exception:
            lines.append("  [dim](spans unavailable)[/dim]")

    elif _is_embedded(tui):
        try:
            if hasattr(tui._office, 'get_observability_spans'):
                spans = tui._office.get_observability_spans(limit)
                if spans:
                    for s in spans[:limit]:
                        op = s.get("operation", "?")[:20]
                        dur = s.get("duration_ms", 0)
                        status = s.get("status", "?")
                        s_color = "green" if status == "ok" else "red" if status == "error" else "dim"
                        lines.append(f"  {op:20s} [{s_color}]{status}[/{s_color}] {dur:.0f}ms")
                else:
                    lines.append("  [dim]No spans recorded[/dim]")
            else:
                lines.append("  [dim]Observability not available[/dim]")
        except Exception:
            lines.append("  [dim](trace error)[/dim]")
    else:
        lines.append("  [dim]Not connected[/dim]")

    return "\n".join(lines)


@command("metrics", "Show observability metrics", "/metrics")
async def cmd_metrics(tui: Any, args: str) -> str:
    """Show observability metrics summary."""
    lines = ["[bold cyan]Metrics[/bold cyan]", ""]

    if _is_remote(tui):
        try:
            metrics = await tui._connection.get_metrics()
            if metrics:
                lines.append(f"  Total Requests: {metrics.get('total_requests', '?')}")
                lines.append(f"  Avg Latency: {metrics.get('avg_latency_ms', '?')}ms")
                lines.append(f"  P99 Latency: {metrics.get('p99_latency_ms', '?')}ms")
                lines.append(f"  Error Rate: {metrics.get('error_rate', '?')}")
                lines.append(f"  Cache Hit Rate: {metrics.get('cache_hit_rate', '?')}")

                by_provider = metrics.get("by_provider", {})
                if by_provider:
                    lines.append("")
                    lines.append("  [bold]By Provider:[/bold]")
                    for name, data in by_provider.items():
                        calls = data.get("calls", 0)
                        errors = data.get("failed_calls", 0)
                        lat = data.get("avg_latency_ms", 0)
                        tokens = data.get("total_tokens", 0)
                        lines.append(f"    {name:14s} {calls} calls, {errors} errors, {lat:.0f}ms, {tokens} tokens")
            else:
                lines.append("  [dim]No metrics available[/dim]")
        except Exception:
            lines.append("  [dim](metrics unavailable)[/dim]")

    elif _is_embedded(tui):
        try:
            if hasattr(tui._office, 'get_metrics_summary'):
                metrics = tui._office.get_metrics_summary()
                lines.append(f"  Total Requests: {metrics.get('total_requests', '?')}")
                lines.append(f"  Avg Latency: {metrics.get('avg_latency_ms', '?')}ms")
                lines.append(f"  Error Rate: {metrics.get('error_rate', '?')}")
            else:
                lines.append("  [dim]Metrics not available[/dim]")
        except Exception:
            lines.append("  [dim](metrics error)[/dim]")
    else:
        lines.append("  [dim]Not connected[/dim]")

    return "\n".join(lines)


@command("hooks", "List registered hooks", "/hooks")
async def cmd_hooks(tui: Any, args: str) -> str:
    """List all registered lifecycle hooks."""
    lines = ["[bold cyan]Lifecycle Hooks[/bold cyan]", ""]

    if _is_embedded(tui) and tui._office:
        if hasattr(tui._office, 'hooks') and tui._office.hooks:
            hooks_list = tui._office.hooks.list_hooks()
            if hooks_list:
                for hook_type, callbacks in hooks_list.items():
                    lines.append(f"  [bold]{hook_type}[/bold]")
                    for cb in callbacks:
                        lines.append(f"    {cb}")
            else:
                lines.append("  [dim]No hooks registered[/dim]")
        else:
            lines.append("  [dim]Hooks system not available[/dim]")
    else:
        # Show available hook types
        try:
            from kantorku.hooks import HookType
            lines.append("  [bold]Available Hook Points:[/bold]")
            for ht in HookType:
                lines.append(f"    {ht.value}")
            lines.append("")
            lines.append("  [dim]Hook registration only available in embedded mode[/dim]")
        except ImportError:
            lines.append("  [dim]Hooks module not available[/dim]")

    return "\n".join(lines)


@command("cache", "Show cache statistics", "/cache")
async def cmd_cache(tui: Any, args: str) -> str:
    """Show LLM response cache statistics."""
    lines = ["[bold cyan]LLM Cache[/bold cyan]", ""]

    if _is_embedded(tui) and tui._office:
        if hasattr(tui._office, '_cache') and tui._office._cache:
            cache = tui._office._cache
            stats = cache.get_stats() if hasattr(cache, 'get_stats') else {}
            lines.append(f"  Hits: {stats.get('hits', '?')}")
            lines.append(f"  Misses: {stats.get('misses', '?')}")
            lines.append(f"  Hit Rate: {stats.get('hit_rate', '?')}")
            lines.append(f"  Size: {stats.get('size', '?')}")
            lines.append(f"  Backend: {stats.get('backend', '?')}")
        else:
            lines.append("  [dim]Cache not enabled[/dim]")
    elif _is_remote(tui):
        lines.append("  [dim]Cache stats only available in embedded mode[/dim]")
        lines.append("  [dim]Use /metrics for cache hit rate[/dim]")
    else:
        lines.append("  [dim]Not connected[/dim]")

    return "\n".join(lines)


@command("config", "View current configuration", "/config")
async def cmd_config(tui: Any, args: str) -> str:
    """View current KantorKu configuration."""
    lines = ["[bold cyan]Configuration[/bold cyan]", ""]

    if _is_embedded(tui) and tui._office:
        if hasattr(tui._office, 'config') and tui._office.config:
            config = tui._office.config
            if hasattr(config, 'to_dict'):
                cdict = config.to_dict()
            elif hasattr(config, '__dict__'):
                cdict = config.__dict__
            else:
                cdict = {}

            # Show key config sections
            if 'server' in cdict or hasattr(config, 'server'):
                server = cdict.get('server', getattr(config, 'server', {}))
                if hasattr(server, '__dict__'):
                    server = server.__dict__
                lines.append("[bold]Server:[/bold]")
                for k, v in (server if isinstance(server, dict) else {}).items():
                    lines.append(f"  {k}: {v}")

            if 'memory' in cdict or hasattr(config, 'memory'):
                memory = cdict.get('memory', getattr(config, 'memory', {}))
                if hasattr(memory, '__dict__'):
                    memory = memory.__dict__
                lines.append("[bold]Memory:[/bold]")
                for k, v in (memory if isinstance(memory, dict) else {}).items():
                    lines.append(f"  {k}: {v}")

            if 'workers' in cdict or hasattr(config, 'workers'):
                workers_cfg = cdict.get('workers', getattr(config, 'workers', []))
                lines.append(f"[bold]Workers:[/bold] {len(workers_cfg) if isinstance(workers_cfg, list) else 'configured'}")

            # Show config file path
            if tui.config_path:
                lines.append(f"\n  [dim]Config file: {tui.config_path}[/dim]")
        else:
            lines.append("  [dim]Configuration not available[/dim]")
    else:
        lines.append(f"  Server: {tui.server_url}")
        lines.append(f"  Session: {tui._session_id}")
        if tui.config_path:
            lines.append(f"  Config: {tui.config_path}")
        else:
            lines.append("  [dim]No config file specified[/dim]")

    return "\n".join(lines)


@command("alerts", "Show active alerts", "/alerts")
async def cmd_alerts(tui: Any, args: str) -> str:
    """Show active health alerts."""
    lines = ["[bold cyan]Alerts[/bold cyan]", ""]

    if _is_remote(tui):
        try:
            health = await tui._connection.get_health()
            if health:
                alerts_data = health.get("alerts", {})
                if isinstance(alerts_data, dict):
                    active = alerts_data.get("active", [])
                    if active:
                        for a in active:
                            severity = a.get("severity", "warning")
                            sev_color = "red bold" if severity == "critical" else "yellow"
                            lines.append(f"  [{sev_color}]{severity}[/{sev_color}] {a.get('source', '?')}: {a.get('message', '?')[:60]}")
                    else:
                        lines.append("  [green]No active alerts[/green]")
        except Exception:
            lines.append("  [dim](alerts unavailable)[/dim]")

    elif _is_embedded(tui):
        try:
            if hasattr(tui._office, '_health') and tui._office._health:
                alerts = tui._office._health.alerts.get_active()
                if alerts:
                    for a in alerts:
                        d = a.to_dict()
                        severity = d.get("severity", "warning")
                        sev_color = "red bold" if severity == "critical" else "yellow"
                        lines.append(f"  [{sev_color}]{severity}[/{sev_color}] {d.get('source', '?')}: {d.get('message', '?')[:60]}")
                else:
                    lines.append("  [green]No active alerts — all systems nominal[/green]")
            else:
                lines.append("  [dim]Alert system not available[/dim]")
        except Exception:
            lines.append("  [dim](alerts error)[/dim]")
    else:
        lines.append("  [dim]Not connected[/dim]")

    return "\n".join(lines)


@command("delegate", "View worker delegations", "/delegate")
async def cmd_delegate(tui: Any, args: str) -> str:
    """View worker-to-worker delegations."""
    lines = ["[bold cyan]Delegations[/bold cyan]", ""]

    if _is_embedded(tui) and tui._office:
        if hasattr(tui._office, 'delegation_manager') and tui._office.delegation_manager:
            dm = tui._office.delegation_manager
            active = dm.get_active_delegations() if hasattr(dm, 'get_active_delegations') else []
            if active:
                for d in active:
                    lines.append(f"  {d.get('from_worker', '?')} → {d.get('to_worker', '?')}: {d.get('task', '?')[:40]}")
            else:
                lines.append("  [dim]No active delegations[/dim]")
        else:
            lines.append("  [dim]Delegation manager not available[/dim]")
    else:
        lines.append("  [dim]Delegation info only available in embedded mode[/dim]")
        lines.append("  [dim]Workers delegate sub-tasks to each other automatically[/dim]")

    return "\n".join(lines)


@command("export", "Export session to file", "/export [filename]")
async def cmd_export(tui: Any, args: str) -> str:
    """Export the current session to a JSON file."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = args.strip() or f"kantorku_session_{tui._session_id}_{timestamp}.json"
    if not filename.startswith("/"):
        filename = os.path.join(os.path.expanduser("~"), filename)

    session_data = {
        "session_id": tui._session_id,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "connection_state": tui.connection_state,
        "server_url": tui.server_url,
        "pending_contract": tui.pending_contract,
        "input_history": tui._input_history[-50:],
    }

    # Add embedded office data if available
    if _is_embedded(tui):
        try:
            workers = tui._office.get_worker_status()
            session_data["workers"] = workers
            if hasattr(tui._office, 'cost_tracker') and tui._office.cost_tracker:
                session_data["cost_report"] = tui._office.get_cost_report()
        except Exception:
            pass

    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True) if os.path.dirname(filename) else None
        with open(filename, "w") as f:
            json.dump(session_data, f, indent=2, default=str)
        return f"[green]Session exported to:[/green] {filename}"
    except Exception as e:
        return f"[red]Export failed:[/red] {e}"


@command("theme", "Switch color theme", "/theme [dark|light|kantorku]")
async def cmd_theme(tui: Any, args: str) -> str:
    """Switch the TUI color theme."""
    from kantorku.tui.themes import KANTORKU_THEME

    theme_name = args.strip().lower() or "kantorku"

    themes = {
        "kantorku": KANTORKU_THEME,
        "dark": {
            "primary": "#58a6ff",
            "secondary": "#bc8cff",
            "accent": "#f0883e",
            "success": "#3fb950",
            "error": "#f85149",
            "warning": "#d29922",
            "info": "#58a6ff",
            "muted": "#8b949e",
            "background": "#0d1117",
            "surface": "#161b22",
            "text": "#c9d1d9",
        },
        "light": {
            "primary": "#0969da",
            "secondary": "#8250df",
            "accent": "#bf8700",
            "success": "#1a7f37",
            "error": "#cf222e",
            "warning": "#9a6700",
            "info": "#0969da",
            "muted": "#656d76",
            "background": "#ffffff",
            "surface": "#f6f8fa",
            "text": "#1f2328",
        },
    }

    if theme_name not in themes:
        available = ", ".join(themes.keys())
        return f"[yellow]Unknown theme: {theme_name}[/yellow]\n[dim]Available: {available}[/dim]"

    theme = themes[theme_name]

    # Apply to CSS dynamically
    tui.CSS = f"""
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
        border: solid {theme['primary']};
        border-title-color: {theme['primary']};
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

    #contract-area {{
        height: auto;
        max-height: 10;
        dock: top;
        border: solid {theme['success']};
        border-title-color: {theme['success']};
    }}
    """

    # Force re-render
    try:
        tui.screen.styles.update(tui.CSS)
    except Exception:
        pass

    return f"[green]Theme switched to:[/green] {theme_name}"
