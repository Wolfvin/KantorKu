"""
Slash Commands — Complete command system for the KantorKu TUI.

40+ commands covering ALL framework features:

Chat & Contracts: /accept /ask /code /revise /run /interrupt
Monitoring: /status /workers /health /cost /alerts /sessions
Memory & Data: /memory /cache /context /dag /briefing /pool /queue
Observability: /trace /metrics /hooks /config /middleware
Worker Lifecycle: /hire /fire /hotplug /worker-info /generate-worker
Task Control: /enqueue /cancel /dlq /queue-purge
Provider: /provider /circuit-reset /rate-limit
Persistence: /checkpoint /recover /snapshot /snapshots
Session: /reset /export /delegate /theme /transcript /settings
Redteam: /redteam /stm /autotune /classify /godmode /score /parseltongue
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable


@dataclass
class SlashCommand:
    name: str
    description: str
    usage: str
    handler: Callable[..., Awaitable[str]]


COMMANDS: dict[str, SlashCommand] = {}


def command(name: str, description: str, usage: str = ""):
    def decorator(func: Callable[..., Awaitable[str]]) -> Callable[..., Awaitable[str]]:
        COMMANDS[name] = SlashCommand(name=name, description=description,
                                       usage=usage or f"/{name}", handler=func)
        return func
    return decorator


def get_help_text() -> str:
    max_name = max(len(n) for n in COMMANDS) if COMMANDS else 0
    categories = {
        "Chat & Contracts": ["accept", "ask", "code", "revise", "run", "interrupt"],
        "Monitoring": ["status", "workers", "health", "cost", "alerts", "sessions"],
        "Memory & Data": ["memory", "cache", "context", "dag", "briefing", "pool", "queue"],
        "Observability": ["trace", "metrics", "hooks", "config", "middleware"],
        "Worker Lifecycle": ["hire", "fire", "hotplug", "worker-info", "generate-worker"],
        "Task Control": ["enqueue", "cancel", "dlq", "queue-purge"],
        "Provider": ["provider", "circuit-reset", "rate-limit"],
        "Persistence": ["checkpoint", "recover", "snapshot", "snapshots"],
        "Redteam": ["redteam", "stm", "autotune", "classify", "godmode", "score", "parseltongue"],
        "Session": ["reset", "export", "delegate", "theme", "transcript", "settings"],
    }
    lines = ["[bold cyan]KantorKu Slash Commands:[/bold cyan]", ""]
    for cat, cmd_names in categories.items():
        cat_cmds = [(n, COMMANDS[n]) for n in cmd_names if n in COMMANDS]
        if cat_cmds:
            lines.append(f"[bold]{cat}:[/bold]")
            for name, cmd in cat_cmds:
                lines.append(f"  [bold green]/{name:<{max_name}}[/bold green]  {cmd.description}")
                if cmd.usage and cmd.usage != f"/{name}":
                    lines.append(f"  {'':>{max_name + 2}}  [dim]{cmd.usage}[/dim]")
    lines.append("")
    lines.append("[dim]↑/↓ = history  Tab = switch panels  Enter = send[/dim]")
    return "\n".join(lines)


async def handle_slash_command(text: str, tui: Any) -> str | None:
    text = text.strip()
    if not text.startswith("/"):
        return None
    parts = text[1:].split(None, 1)
    cmd_name = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""
    if cmd_name == "help":
        return get_help_text()
    if cmd_name not in COMMANDS:
        return f"[red]Unknown: /{cmd_name}[/red]\n[dim]/help for commands[/dim]"
    return await COMMANDS[cmd_name].handler(tui, args)


def _remote(tui: Any) -> bool:
    return hasattr(tui, '_connection') and tui._connection._http_client is not None

def _embedded(tui: Any) -> bool:
    return hasattr(tui, '_office') and tui._office is not None

def _office(tui: Any) -> Any:
    return getattr(tui, '_office', None)


def _redteam_allowed(tui: Any) -> bool:
    """Check if redteam commands are enabled."""
    # Check config flag, default to True for solo dev
    if hasattr(tui, '_office') and tui._office:
        config = getattr(tui._office, 'config', None)
        if config and hasattr(config, 'redteam_enabled'):
            return config.redteam_enabled
    # Check environment variable
    return os.environ.get("KANTORKU_REDTEAM_ENABLED", "true").lower() in ("true", "1", "yes")


def _redteam_gate(tui: Any) -> str | None:
    """Returns error message if redteam is disabled, None if allowed."""
    if not _redteam_allowed(tui):
        return "[red bold]Redteam commands are disabled.[/red bold]\n[dim]Set KANTORKU_REDTEAM_ENABLED=true or enable in config.[/dim]"
    return None


# ═══════════════════════════════════════════════════════════════════
# Chat & Contracts
# ═══════════════════════════════════════════════════════════════════

@command("accept", "Accept current contract (or Ctrl+A)", "/accept")
async def cmd_accept(tui: Any, args: str) -> str:
    if not tui.pending_contract:
        return "[yellow]No contract to accept yet. Chat with the Manager first![/yellow]"
    await tui._send_accept()
    return "[green]Contract accepted! Workers are starting...[/green]"

@command("revise", "Revise contract with feedback (or Ctrl+R)", "/revise <feedback>")
async def cmd_revise(tui: Any, args: str) -> str:
    if not args:
        return "[yellow]Usage: /revise <feedback>[/yellow]\n[dim]Example: /revise I want more detail on the API design[/dim]"
    await tui._send_revise(args)
    return f"[yellow]Revision requested: {args}[/yellow]"

@command("interrupt", "Interrupt work and talk to Manager (or Ctrl+I)", "/interrupt [reason]")
async def cmd_interrupt(tui: Any, args: str) -> str:
    tui._do_disrupt()
    return "[yellow]⚡ Interrupting... You can now talk to the Manager.[/yellow]"

@command("code", "Quick code task (auto-accept)", "/code <task>")
async def cmd_code(tui: Any, args: str) -> str:
    if not args:
        return "[yellow]Usage: /code <task>[/yellow]\n[dim]Example: /code implement a rate limiter[/dim]"
    await tui._send_message(args)
    # Contract will arrive asynchronously — set a flag for auto-accept
    tui._auto_accept_pending = True
    return "[green]Code task sent. Will auto-accept when contract arrives.[/green]"

@command("ask", "Ask the Conductor a question", "/ask <question>")
async def cmd_ask(tui: Any, args: str) -> str:
    if not args:
        return "[yellow]Usage: /ask <question>[/yellow]"
    await tui._send_message(args)
    return ""

@command("run", "One-shot: send + auto-accept + stream result", "/run <message>")
async def cmd_run(tui: Any, args: str) -> str:
    """One-shot run: send message, auto-accept contract, wait for result."""
    if not args:
        return "[yellow]Usage: /run <message>[/yellow]\n[dim]Sends message, auto-accepts, waits for work done[/dim]"
    await tui._send_message(args)
    # Contract will arrive asynchronously — set a flag for auto-accept
    tui._auto_accept_pending = True
    return "[green]Task sent. Will auto-accept when contract arrives.[/green]"


# ═══════════════════════════════════════════════════════════════════
# Monitoring
# ═══════════════════════════════════════════════════════════════════

@command("status", "Show office status", "/status")
async def cmd_status(tui: Any, args: str) -> str:
    lines = ["[bold]Office Status[/bold]",
             f"  Session:    {tui._session_id}",
             f"  Connection: {tui.connection_state}"]
    if _remote(tui):
        try:
            status = await tui._connection.get_status()
            if status:
                lines.append(f"  Workers:    {len(status.get('workers', []))}")
                lines.append(f"  Mode:       Remote")
                cost = status.get("cost", {})
                if cost:
                    lines.append(f"  Cost:       ${cost.get('total_cost_usd', 0):.4f} ({cost.get('total_calls', 0)} calls)")
                pool = status.get("pool", {})
                if pool:
                    lines.append(f"  Pool:       {pool.get('worker_count', '?')} workers")
        except Exception:
            lines.append("  [dim](unavailable)[/dim]")
    elif _embedded(tui):
        o = _office(tui)
        lines.append(f"  Workers:    {len(o.get_worker_status())}")
        lines.append(f"  Mode:       Embedded")
        if hasattr(o, 'cost_tracker') and o.cost_tracker:
            cost = o.get_cost_report()
            lines.append(f"  Cost:       ${cost.get('total_cost_usd', 0):.4f}")
        if hasattr(o, 'ring1') and o.ring1:
            r1 = o.ring1.get_stats()
            lines.append(f"  Ring1:      {r1.get('context_count', '?')} contexts")
    return "\n".join(lines)

@command("workers", "Show worker status grid", "/workers")
async def cmd_workers(tui: Any, args: str) -> str:
    from rich.table import Table
    from io import StringIO
    from rich.console import Console
    from kantorku.tui.themes import STATUS_COLORS, STATUS_ICONS
    table = Table(title="Workers", show_header=True)
    table.add_column("ID", style="bold"); table.add_column("Status")
    table.add_column("Model"); table.add_column("Squad"); table.add_column("Role")
    if _remote(tui):
        try:
            status = await tui._connection.get_status()
            workers = status.get("workers", []) if status else []
        except Exception:
            workers = []
    elif _embedded(tui):
        workers = _office(tui).get_worker_status()
    else:
        workers = []
    if not workers:
        return "[dim]No workers[/dim]"
    for w in workers:
        s = w.get("status", "?")
        c = STATUS_COLORS.get(s, "dim"); ic = STATUS_ICONS.get(s, "?")
        table.add_row(w.get("id", "?"), f"[{c}]{ic} {s}[/{c}]",
                      w.get("model", "N/A") or "N/A", w.get("squad", ""), w.get("role", "")[:30])
    console = Console(file=StringIO(), force_terminal=True)
    console.print(table)
    return console.file.getvalue()

@command("health", "Show provider health", "/health")
async def cmd_health(tui: Any, args: str) -> str:
    lines = ["[bold]Provider Health[/bold]", ""]
    if _remote(tui):
        try:
            h = await tui._connection.get_health()
            if h:
                for n, d in h.get("providers", {}).items():
                    icon = "[green]OK[/green]" if d.get("is_healthy") else "[red]DOWN[/red]"
                    cb = d.get("circuit_state", "closed")
                    cb_s = {"closed": "[green]closed[/green]", "open": "[red bold]OPEN[/red bold]",
                            "half_open": "[yellow]half_open[/yellow]"}.get(cb, cb)
                    lines.append(f"  {n:14s} {icon}  circuit:{cb_s}  lat:{d.get('avg_latency_ms',0):.0f}ms")
                alerts = h.get("alerts", {})
                if isinstance(alerts, dict) and alerts.get("total_active", 0) > 0:
                    lines.append(f"\n  [red]{alerts['total_active']} alerts ({alerts.get('critical',0)} critical)[/red]")
        except Exception:
            lines.append("  [dim](unavailable)[/dim]")
    elif _embedded(tui):
        o = _office(tui)
        if hasattr(o, '_health') and o._health:
            for n, s in o._health._provider_health.items():
                d = s.to_dict()
                icon = "[green]OK[/green]" if d.get("is_healthy") else "[red]DOWN[/red]"
                lines.append(f"  {n:14s} {icon}  circuit:{d.get('circuit_state','?')}  lat:{d.get('avg_latency_ms',0):.0f}ms")
        else:
            lines.append("  [dim]No health checker[/dim]")
    else:
        lines.append("  [dim]Not connected[/dim]")
    return "\n".join(lines)

@command("cost", "Show cost report", "/cost [full|model|worker|session]")
async def cmd_cost(tui: Any, args: str) -> str:
    from kantorku.tui.markdown_renderer import render_cost_breakdown
    from io import StringIO
    from rich.console import Console
    mode = args.strip().lower() or "full"
    if _remote(tui):
        try:
            cost = await tui._connection.get_cost()
            if cost:
                g = render_cost_breakdown(cost, mode)
                console = Console(file=StringIO(), force_terminal=True)
                console.print(g)
                return console.file.getvalue()
        except Exception:
            return "[dim](cost unavailable)[/dim]"
    elif _embedded(tui):
        o = _office(tui)
        if hasattr(o, 'cost_tracker') and o.cost_tracker:
            cost = o.get_cost_report()
            g = render_cost_breakdown(cost, mode)
            console = Console(file=StringIO(), force_terminal=True)
            console.print(g)
            return console.file.getvalue()
        return "[dim]Cost tracking not enabled[/dim]"
    return "[dim]Not connected[/dim]"

@command("alerts", "Show active alerts", "/alerts")
async def cmd_alerts(tui: Any, args: str) -> str:
    lines = ["[bold]Alerts[/bold]", ""]
    if _remote(tui):
        try:
            h = await tui._connection.get_health()
            if h:
                active = h.get("alerts", {}).get("active", []) if isinstance(h.get("alerts"), dict) else []
                if active:
                    for a in active:
                        sev = a.get("severity", "warning")
                        sc = "red bold" if sev == "critical" else "yellow"
                        lines.append(f"  [{sc}]{sev}[/{sc}] {a.get('source','?')}: {a.get('message','?')[:60]}")
                else:
                    lines.append("  [green]No active alerts[/green]")
        except Exception:
            lines.append("  [dim](unavailable)[/dim]")
    elif _embedded(tui):
        o = _office(tui)
        if hasattr(o, '_health') and o._health:
            alerts = o._health.alerts.get_active()
            if alerts:
                for a in alerts:
                    d = a.to_dict()
                    sev = d.get("severity", "warning")
                    sc = "red bold" if sev == "critical" else "yellow"
                    lines.append(f"  [{sc}]{sev}[/{sc}] {d.get('source','?')}: {d.get('message','?')[:60]}")
            else:
                lines.append("  [green]No active alerts[/green]")
    return "\n".join(lines)

@command("sessions", "List active sessions", "/sessions")
async def cmd_sessions(tui: Any, args: str) -> str:
    lines = ["[bold]Sessions[/bold]", ""]
    if _remote(tui):
        try:
            sessions = await tui._connection.get_sessions()
            for s in (sessions or []):
                lines.append(f"  {s.get('session_id','?'):12s} [{s.get('state','?')}] {s.get('contract_title','')}")
            if not sessions:
                lines.append("  [dim]None[/dim]")
        except Exception:
            lines.append("  [dim](unavailable)[/dim]")
    elif _embedded(tui):
        lines.append(f"  {tui._session_id:12s} [green]current[/green]")
        o = _office(tui)
        if o and hasattr(o, 'conductor') and hasattr(o.conductor, '_sessions'):
            for sid in o.conductor._sessions:
                if sid != tui._session_id:
                    lines.append(f"  {sid:12s} [dim]active[/dim]")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# Memory & Data
# ═══════════════════════════════════════════════════════════════════

@command("memory", "Show 3-Ring memory stats", "/memory")
async def cmd_memory(tui: Any, args: str) -> str:
    lines = ["[bold cyan]Three-Ring Memory[/bold cyan]", ""]
    if _remote(tui):
        try:
            m = await tui._connection.get_memory_stats()
            if m:
                r1, r2 = m.get("ring1", {}), m.get("ring2", {})
                lines.append("[bold]Ring 1 (DuckDB):[/bold]")
                for k in ["context_count", "session_count", "task_result_count", "history_count", "db_size_mb"]:
                    lines.append(f"  {k}: {r1.get(k, '?')}")
                lines.append("\n[bold]Ring 2 (SQLite):[/bold]")
                for k in ["episode_count", "lesson_count", "audit_trail_count", "db_size_mb"]:
                    lines.append(f"  {k}: {r2.get(k, '?')}")
                lines.append("\n[dim]Ring 3 (Cognee): Not yet connected[/dim]")
        except Exception:
            lines.append("  [dim](unavailable)[/dim]")
    elif _embedded(tui):
        o = _office(tui)
        for ring_name, attr in [("Ring 1", "ring1"), ("Ring 2", "ring2")]:
            ring = getattr(o, attr, None)
            if ring:
                s = ring.get_stats()
                lines.append(f"[bold]{ring_name}:[/bold]")
                for k, v in s.items():
                    lines.append(f"  {k}: {v}")
            else:
                lines.append(f"  [dim]{ring_name} not available[/dim]")
            lines.append("")
        lines.append("[dim]Ring 3 (Cognee): Not yet connected[/dim]")
    return "\n".join(lines)

@command("cache", "Show cache stats", "/cache [clear]")
async def cmd_cache(tui: Any, args: str) -> str:
    lines = ["[bold cyan]LLM Cache[/bold cyan]", ""]
    if args.strip().lower() == "clear":
        if _embedded(tui):
            o = _office(tui)
            if hasattr(o, '_cache') and o._cache:
                o._cache.clear()
                return "[green]Cache cleared![/green]"
            return "[yellow]Cache not available[/yellow]"
        return "[yellow]Cache clear only in embedded mode[/yellow]"
    if _embedded(tui):
        o = _office(tui)
        if hasattr(o, '_cache') and o._cache:
            cache = o._cache
            stats = cache.get_stats() if hasattr(cache, 'get_stats') else {}
            lines.append(f"  Hits: {stats.get('hits', '?')}")
            lines.append(f"  Misses: {stats.get('misses', '?')}")
            lines.append(f"  Hit Rate: {stats.get('hit_rate', '?')}")
            lines.append(f"  Size: {stats.get('size', '?')}")
            lines.append(f"  Backend: {stats.get('backend', '?')}")
        else:
            lines.append("  [dim]Cache not enabled[/dim]")
    elif _remote(tui):
        lines.append("  [dim]Cache stats only in embedded mode[/dim]")
        lines.append("  [dim]Use /metrics for cache hit rate[/dim]")
    return "\n".join(lines)

@command("context", "Browse context from Ring1", "/context [task_id]")
async def cmd_context(tui: Any, args: str) -> str:
    """Browse stored context from Ring1 memory."""
    lines = ["[bold cyan]Context Browser[/bold cyan]", ""]
    if _embedded(tui):
        o = _office(tui)
        if hasattr(o, 'ring1') and o.ring1:
            if args.strip():
                # Get specific context
                try:
                    ctx = await o.ring1.get_context(args.strip())
                    if ctx:
                        lines.append(f"  [bold]ID:[/bold] {ctx.get('id', '?')}")
                        lines.append(f"  [bold]Source:[/bold] {ctx.get('source', '?')}")
                        lines.append(f"  [bold]Tokens:[/bold] {ctx.get('token_count', '?')}")
                        content = ctx.get('content', '')
                        lines.append(f"  [bold]Content:[/bold] {content[:200]}...")
                    else:
                        lines.append(f"  [dim]Context '{args.strip()}' not found[/dim]")
                except Exception as e:
                    lines.append(f"  [dim]Error: {e}[/dim]")
            else:
                # List recent contexts
                try:
                    stats = o.ring1.get_stats()
                    lines.append(f"  Total contexts: {stats.get('context_count', '?')}")
                    lines.append(f"  [dim]Use /context <task_id> to inspect specific context[/dim]")
                except Exception:
                    lines.append("  [dim]Ring1 stats unavailable[/dim]")
        else:
            lines.append("  [dim]Ring1 not available[/dim]")
    elif _remote(tui):
        lines.append("  [dim]Context browsing only in embedded mode[/dim]")
    return "\n".join(lines)

@command("dag", "Show task dependency graph", "/dag [critical]")
async def cmd_dag(tui: Any, args: str) -> str:
    from io import StringIO
    from rich.console import Console
    from kantorku.tui.markdown_renderer import render_dag_tree
    try:
        dp = tui.query_one("#dag-panel")
        groups = getattr(dp, '_groups', [])
        todos = getattr(dp, '_todos', [])
        show_cp = args.strip().lower() == "critical"
        cp = None
        if show_cp and _embedded(tui):
            try:
                from kantorku.dag import DAGResolver
                nodes = [type('TaskNode', (), t) for t in todos] if todos else []
                resolver = DAGResolver()
                for t in todos:
                    resolver.add_task(t.get("id", "?"), t.get("depends_on", []))
                cp = resolver.get_critical_path()
            except Exception:
                pass
        tree = render_dag_tree(groups, todos, cp)
        console = Console(file=StringIO(), force_terminal=True)
        console.print(tree)
        return console.file.getvalue()
    except Exception:
        return "[dim]DAG panel not available[/dim]"

@command("briefing", "Show briefing room transcript", "/briefing")
async def cmd_briefing(tui: Any, args: str) -> str:
    lines = ["[bold magenta]Briefing Room[/bold magenta]", ""]
    try:
        bp = tui.query_one("#briefing-panel")
        msgs = getattr(bp, '_messages', [])
        if msgs:
            for msg in msgs[-20:]:
                fid = msg.get("from", "?")
                content = msg.get("content", "")[:100]
                lines.append(f"  [bold]{fid}[/bold]: {content}")
        else:
            lines.append("  [dim]No briefing yet — accept a contract[/dim]")
    except Exception:
        lines.append("  [dim]Briefing panel not available[/dim]")
    return "\n".join(lines)

@command("pool", "Show context pool status", "/pool")
async def cmd_pool(tui: Any, args: str) -> str:
    lines = ["[bold cyan]Context Pool[/bold cyan]", ""]
    if _remote(tui):
        try:
            status = await tui._connection.get_status()
            pool = status.get("pool", {}) if status else {}
            if pool:
                for k in ["worker_count", "queue_depth", "active_prefetch", "completed", "failed"]:
                    lines.append(f"  {k}: {pool.get(k, '?')}")
        except Exception:
            lines.append("  [dim](unavailable)[/dim]")
    elif _embedded(tui):
        o = _office(tui)
        if hasattr(o, 'get_pool_status'):
            pool = o.get_pool_status()
            for k in ["worker_count", "queue_depth", "active_prefetch", "completed", "failed"]:
                lines.append(f"  {k}: {pool.get(k, '?')}")
        else:
            lines.append("  [dim]Pool not available[/dim]")
    return "\n".join(lines)

@command("queue", "Show task queue & DLQ", "/queue")
async def cmd_queue(tui: Any, args: str) -> str:
    lines = ["[bold cyan]Task Queue[/bold cyan]", ""]
    try:
        qp = tui.query_one("#queue-panel")
        stats = getattr(qp, '_stats', {})
        pending = len(getattr(qp, '_pending', []))
        active = len(getattr(qp, '_active', []))
        dlq = len(getattr(qp, '_dlq', []))
        lines.append(f"  Pending: {stats.get('pending', pending)}")
        lines.append(f"  Active: {stats.get('active', active)}")
        lines.append(f"  DLQ: {stats.get('dead_letter_count', dlq)}")
        lines.append(f"  Total Processed: {stats.get('total_processed', '?')}")
        dlq_items = getattr(qp, '_dlq', [])
        if dlq_items:
            lines.append("\n  [bold red]Dead Letter Queue:[/bold red]")
            for t in dlq_items[:5]:
                lines.append(f"    {t.get('id','?')[:10]}: {t.get('error','?')[:40]}")
    except Exception:
        lines.append("  [dim]Queue panel not available[/dim]")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# Observability
# ═══════════════════════════════════════════════════════════════════

@command("trace", "Show recent spans/traces", "/trace [limit]")
async def cmd_trace(tui: Any, args: str) -> str:
    lines = ["[bold cyan]Traces[/bold cyan]", ""]
    limit = min(int(args) if args.isdigit() else 20, 100)
    if _remote(tui):
        try:
            data = await tui._connection.get_spans(limit)
            spans = data.get("spans", []) if data else []
            for s in spans[:limit]:
                op = s.get("operation", "?")[:20]
                dur = s.get("duration_ms", 0)
                st = s.get("status", "?")
                sc = "green" if st == "ok" else "red" if st == "error" else "dim"
                lines.append(f"  {op:20s} [{sc}]{st}[/{sc}] {dur:.0f}ms")
            if not spans:
                lines.append("  [dim]No spans[/dim]")
        except Exception:
            lines.append("  [dim](unavailable)[/dim]")
    elif _embedded(tui):
        o = _office(tui)
        if hasattr(o, 'get_observability_spans'):
            spans = o.get_observability_spans(limit)
            for s in (spans or [])[:limit]:
                op = s.get("operation", "?")[:20]
                dur = s.get("duration_ms", 0)
                st = s.get("status", "?")
                sc = "green" if st == "ok" else "red" if st == "error" else "dim"
                lines.append(f"  {op:20s} [{sc}]{st}[/{sc}] {dur:.0f}ms")
    return "\n".join(lines)

@command("metrics", "Show observability metrics", "/metrics")
async def cmd_metrics(tui: Any, args: str) -> str:
    lines = ["[bold cyan]Metrics[/bold cyan]", ""]
    if _remote(tui):
        try:
            m = await tui._connection.get_metrics()
            if m:
                for k in ["total_requests", "avg_latency_ms", "p99_latency_ms", "error_rate", "cache_hit_rate"]:
                    lines.append(f"  {k}: {m.get(k, '?')}")
                for name, d in m.get("by_provider", {}).items():
                    lines.append(f"    {name}: {d.get('calls',0)} calls, {d.get('avg_latency_ms',0):.0f}ms")
        except Exception:
            lines.append("  [dim](unavailable)[/dim]")
    elif _embedded(tui):
        o = _office(tui)
        if hasattr(o, 'get_metrics_summary'):
            m = o.get_metrics_summary()
            for k in ["total_requests", "avg_latency_ms", "error_rate"]:
                lines.append(f"  {k}: {m.get(k, '?')}")
    return "\n".join(lines)

@command("hooks", "List/manage lifecycle hooks", "/hooks [clear]")
async def cmd_hooks(tui: Any, args: str) -> str:
    lines = ["[bold cyan]Lifecycle Hooks[/bold cyan]", ""]
    if args.strip().lower() == "clear":
        if _embedded(tui):
            o = _office(tui)
            if hasattr(o, 'hooks') and o.hooks:
                o.hooks.clear()
                return "[green]All hooks cleared![/green]"
            return "[yellow]No hooks to clear[/yellow]"
        return "[yellow]Only in embedded mode[/yellow]"
    if _embedded(tui):
        o = _office(tui)
        if hasattr(o, 'hooks') and o.hooks:
            hooks_list = o.hooks.list_hooks()
            if hooks_list:
                for ht, cbs in hooks_list.items():
                    lines.append(f"  [bold]{ht}[/bold]")
                    for cb in cbs:
                        lines.append(f"    {cb}")
            else:
                lines.append("  [dim]No hooks registered[/dim]")
        else:
            lines.append("  [dim]Hooks not available[/dim]")
    else:
        try:
            from kantorku.hooks import HookType
            lines.append("  [bold]Available Hook Points:[/bold]")
            for ht in HookType:
                lines.append(f"    {ht.value}")
            lines.append("\n  [dim]Registration only in embedded mode[/dim]")
        except ImportError:
            lines.append("  [dim]Hooks module not available[/dim]")
    return "\n".join(lines)

@command("config", "View current configuration", "/config")
async def cmd_config(tui: Any, args: str) -> str:
    lines = ["[bold cyan]Configuration[/bold cyan]", ""]
    if _embedded(tui):
        o = _office(tui)
        if hasattr(o, 'config') and o.config:
            config = o.config
            cdict = config.to_dict() if hasattr(config, 'to_dict') else config.__dict__
            for section_name in ["server", "memory", "pool", "workers"]:
                section = cdict.get(section_name, getattr(config, section_name, None))
                if section:
                    sd = section.__dict__ if hasattr(section, '__dict__') else section
                    if isinstance(sd, dict):
                        lines.append(f"[bold]{section_name}:[/bold]")
                        for k, v in sd.items():
                            lines.append(f"  {k}: {v}")
            if tui.config_path:
                lines.append(f"\n  [dim]Config file: {tui.config_path}[/dim]")
        else:
            lines.append("  [dim]No config object[/dim]")
    else:
        lines.append(f"  Server: {tui.server_url}")
        lines.append(f"  Session: {tui._session_id}")
        if tui.config_path:
            lines.append(f"  Config: {tui.config_path}")
    return "\n".join(lines)

@command("middleware", "Show middleware pipeline", "/middleware")
async def cmd_middleware(tui: Any, args: str) -> str:
    from io import StringIO
    from rich.console import Console
    from kantorku.tui.markdown_renderer import render_middleware_pipeline
    lines = ["[bold cyan]Middleware Pipeline[/bold cyan]", ""]
    if _embedded(tui):
        o = _office(tui)
        mws = []
        if hasattr(o, '_pipeline') and o._pipeline:
            for mw in o._pipeline._middleware:
                mws.append({"name": type(mw).__name__, "type": type(mw).__name__,
                            "enabled": True, "config": {}})
        elif hasattr(o, 'config'):
            # List default middlewares
            mws = [
                {"name": "LoggingMiddleware", "type": "LoggingMiddleware", "enabled": True},
                {"name": "AuthMiddleware", "type": "AuthMiddleware", "enabled": True},
                {"name": "RateLimitMiddleware", "type": "RateLimitMiddleware", "enabled": True},
                {"name": "CostGuardMiddleware", "type": "CostGuardMiddleware", "enabled": True},
                {"name": "AuditMiddleware", "type": "AuditMiddleware", "enabled": True},
                {"name": "TimeoutMiddleware", "type": "TimeoutMiddleware", "enabled": True},
                {"name": "RetryMiddleware", "type": "RetryMiddleware", "enabled": True},
                {"name": "CachingMiddleware", "type": "CachingMiddleware", "enabled": True},
            ]
        tree = render_middleware_pipeline(mws)
        console = Console(file=StringIO(), force_terminal=True)
        console.print(tree)
        return console.file.getvalue()
    else:
        lines.append("  [dim]Middleware only in embedded mode[/dim]")
        lines.append("  [dim]Default: Logging, Auth, RateLimit, CostGuard, Audit, Timeout, Retry, Caching[/dim]")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# Worker Lifecycle
# ═══════════════════════════════════════════════════════════════════

@command("hire", "Hire a worker by ID", "/hire <worker_id>")
async def cmd_hire(tui: Any, args: str) -> str:
    if not args.strip():
        return "[yellow]Usage: /hire <worker_id>[/yellow]"
    wid = args.strip()
    if _embedded(tui):
        o = _office(tui)
        if hasattr(o, 'hire_worker'):
            try:
                await o.hire_worker(wid)
                tui._update_embedded_status()
                return f"[green]Hired worker: {wid}[/green]"
            except Exception as e:
                return f"[red]Failed to hire {wid}: {e}[/red]"
        return "[yellow]hire_worker not available[/yellow]"
    return "[yellow]Worker hiring only in embedded mode[/yellow]"

@command("fire", "Fire a worker by ID", "/fire <worker_id>")
async def cmd_fire(tui: Any, args: str) -> str:
    if not args.strip():
        return "[yellow]Usage: /fire <worker_id>[/yellow]"
    wid = args.strip()
    if _embedded(tui):
        o = _office(tui)
        if hasattr(o, 'registry') and hasattr(o.registry, 'fire'):
            try:
                o.registry.fire(wid)
                tui._update_embedded_status()
                return f"[red]Fired worker: {wid}[/red]"
            except Exception as e:
                return f"[red]Failed to fire {wid}: {e}[/red]"
        return "[yellow]Registry.fire not available[/yellow]"
    return "[yellow]Worker firing only in embedded mode[/yellow]"

@command("hotplug", "Hot-plug a worker from directory", "/hotplug <path>")
async def cmd_hotplug(tui: Any, args: str) -> str:
    if not args.strip():
        return "[yellow]Usage: /hotplug <worker_directory_path>[/yellow]"
    path = args.strip()
    if _embedded(tui):
        o = _office(tui)
        if hasattr(o, 'hot_plug_worker'):
            try:
                await o.hot_plug_worker(path)
                tui._update_embedded_status()
                return f"[green]Hot-plugged worker from: {path}[/green]"
            except Exception as e:
                return f"[red]Hot-plug failed: {e}[/red]"
        return "[yellow]hot_plug_worker not available[/yellow]"
    return "[yellow]Hot-plug only in embedded mode[/yellow]"

@command("worker-info", "Show worker identity details", "/worker-info <worker_id>")
async def cmd_worker_info(tui: Any, args: str) -> str:
    from io import StringIO
    from rich.console import Console
    from kantorku.tui.markdown_renderer import render_worker_identity
    if not args.strip():
        return "[yellow]Usage: /worker-info <worker_id>[/yellow]"
    wid = args.strip()
    if _embedded(tui):
        o = _office(tui)
        identity = None
        if hasattr(o, 'registry'):
            try:
                identities = o.registry._identities if hasattr(o.registry, '_identities') else {}
                if wid in identities:
                    identity = identities[wid].to_dict() if hasattr(identities[wid], 'to_dict') else identities[wid].__dict__
            except Exception:
                pass
        if identity:
            g = render_worker_identity(identity)
            console = Console(file=StringIO(), force_terminal=True)
            console.print(g)
            return console.file.getvalue()
        return f"[yellow]Worker '{wid}' identity not found[/yellow]"
    return "[yellow]Worker info only in embedded mode[/yellow]"

@command("generate-worker", "Scaffold a new worker", "/generate-worker <name> <squad>")
async def cmd_generate_worker(tui: Any, args: str) -> str:
    parts = args.strip().split()
    if len(parts) < 2:
        return "[yellow]Usage: /generate-worker <name> <squad>[/yellow]\n[dim]Squads: coding, verification, support, translation[/dim]"
    name, squad = parts[0], parts[1]
    if _embedded(tui):
        o = _office(tui)
        if hasattr(o, 'registry') and hasattr(o.registry, 'generator'):
            try:
                gen = o.registry.generator
                gen.create(name, squad)
                return f"[green]Worker scaffolded: {name} ({squad})[/green]\n[dim]Files: plugin.json, SKILL.md, worker.py[/dim]"
            except Exception as e:
                return f"[red]Generation failed: {e}[/red]"
        try:
            from kantorku.worker.generator import WorkerGenerator
            gen = WorkerGenerator()
            gen.create(name, squad)
            return f"[green]Worker scaffolded: {name} ({squad})[/green]"
        except Exception as e:
            return f"[red]Generation failed: {e}[/red]"
    return "[yellow]Worker generation only in embedded mode[/yellow]"


# ═══════════════════════════════════════════════════════════════════
# Task Control
# ═══════════════════════════════════════════════════════════════════

@command("enqueue", "Enqueue a task manually", "/enqueue <instruction>")
async def cmd_enqueue(tui: Any, args: str) -> str:
    if not args.strip():
        return "[yellow]Usage: /enqueue <instruction>[/yellow]"
    if _embedded(tui):
        o = _office(tui)
        if hasattr(o, 'enqueue_task'):
            try:
                task_id = await o.enqueue_task(args.strip(), session_id=tui._session_id)
                return f"[green]Task enqueued: {task_id}[/green]"
            except Exception as e:
                return f"[red]Enqueue failed: {e}[/red]"
        return "[yellow]enqueue_task not available[/yellow]"
    return "[yellow]Task enqueue only in embedded mode[/yellow]"

@command("cancel", "Cancel a queued task", "/cancel <task_id>")
async def cmd_cancel(tui: Any, args: str) -> str:
    if not args.strip():
        return "[yellow]Usage: /cancel <task_id>[/yellow]"
    if _embedded(tui):
        o = _office(tui)
        if hasattr(o, '_task_queue') and o._task_queue:
            try:
                o._task_queue.cancel(args.strip())
                return f"[yellow]Task cancelled: {args.strip()}[/yellow]"
            except Exception as e:
                return f"[red]Cancel failed: {e}[/red]"
    return "[yellow]Task cancel only in embedded mode[/yellow]"

@command("dlq", "Manage dead letter queue", "/dlq [replay|purge] [id]")
async def cmd_dlq(tui: Any, args: str) -> str:
    parts = args.strip().split()
    action = parts[0].lower() if parts else "list"

    if _embedded(tui):
        o = _office(tui)
        if not hasattr(o, '_task_queue') or not o._task_queue:
            return "[dim]Task queue not available[/dim]"
        q = o._task_queue

        if action == "replay" and len(parts) > 1:
            try:
                q.replay_dead_letter(parts[1])
                return f"[green]Replayed DLQ entry: {parts[1]}[/green]"
            except Exception as e:
                return f"[red]Replay failed: {e}[/red]"
        elif action == "purge":
            dlq = q.get_dead_letter_queue()
            count = len(dlq)
            for entry in dlq:
                if hasattr(q, '_dead_letter'):
                    q._dead_letter.clear()
            return f"[yellow]Purged {count} DLQ entries[/yellow]"
        else:
            # List
            dlq = q.get_dead_letter_queue()
            lines = [f"[bold red]Dead Letter Queue ({len(dlq)} entries)[/bold red]", ""]
            for entry in dlq[:10]:
                lines.append(f"  {entry.get('id','?')[:10]}: {entry.get('error','?')[:50]}")
                lines.append(f"    [dim]retries={entry.get('retry_count',0)} last={entry.get('last_attempt','?')}[/dim]")
            if not dlq:
                lines.append("  [green]DLQ is empty[/green]")
            return "\n".join(lines)
    return "[yellow]DLQ management only in embedded mode[/yellow]"

@command("queue-purge", "Purge completed tasks from queue", "/queue-purge")
async def cmd_queue_purge(tui: Any, args: str) -> str:
    if _embedded(tui):
        o = _office(tui)
        if hasattr(o, '_task_queue') and o._task_queue:
            q = o._task_queue
            if hasattr(q, 'purge_completed'):
                q.purge_completed()
                return "[green]Completed tasks purged![/green]"
            return "[yellow]purge_completed not available[/yellow]"
    return "[yellow]Queue purge only in embedded mode[/yellow]"


# ═══════════════════════════════════════════════════════════════════
# Provider Control
# ═══════════════════════════════════════════════════════════════════

@command("provider", "Show/configure providers", "/provider [configure <name> <model> <key>]")
async def cmd_provider(tui: Any, args: str) -> str:
    parts = args.strip().split()
    if not parts or parts[0].lower() == "list":
        # List providers
        lines = ["[bold cyan]Providers[/bold cyan]", ""]
        if _remote(tui):
            try:
                cb = await tui._connection.get_circuit_breakers()
                if cb:
                    for name, status in cb.items():
                        state = status.get("state", "?")
                        lines.append(f"  {name}: circuit={state}")
            except Exception:
                lines.append("  [dim](unavailable)[/dim]")
        elif _embedded(tui):
            o = _office(tui)
            if hasattr(o, 'router'):
                for name in o.router.configured_providers:
                    lines.append(f"  {name}: configured")
            else:
                lines.append("  [dim]Router not available[/dim]")
        return "\n".join(lines)

    if parts[0].lower() == "configure" and len(parts) >= 4:
        if _embedded(tui):
            o = _office(tui)
            if hasattr(o, 'configure_provider'):
                try:
                    await o.configure_provider(parts[1], model=parts[2], api_key=parts[3])
                    return f"[green]Provider {parts[1]} configured![/green]"
                except Exception as e:
                    return f"[red]Config failed: {e}[/red]"
        return "[yellow]Provider config only in embedded mode[/yellow]"

    return "[yellow]Usage: /provider [list|configure <name> <model> <key>][/yellow]"

@command("circuit-reset", "Reset circuit breaker for provider", "/circuit-reset <provider>")
async def cmd_circuit_reset(tui: Any, args: str) -> str:
    if not args.strip():
        return "[yellow]Usage: /circuit-reset <provider_name>[/yellow]"
    if _embedded(tui):
        o = _office(tui)
        if hasattr(o, 'router'):
            try:
                cb = o.router._circuit_breakers.get(args.strip())
                if cb:
                    cb.reset()
                    return f"[green]Circuit breaker reset for {args.strip()}[/green]"
                return f"[yellow]No circuit breaker for {args.strip()}[/yellow]"
            except Exception as e:
                return f"[red]Reset failed: {e}[/red]"
    return "[yellow]Circuit reset only in embedded mode[/yellow]"

@command("rate-limit", "Show rate limit status", "/rate-limit")
async def cmd_rate_limit(tui: Any, args: str) -> str:
    lines = ["[bold cyan]Rate Limits[/bold cyan]", ""]
    if _embedded(tui):
        o = _office(tui)
        if hasattr(o, 'router') and hasattr(o.router, 'rate_limiter'):
            try:
                status = o.router.rate_limiter.get_status()
                if status:
                    for name, s in status.items():
                        lines.append(f"  {name}: {s}")
                else:
                    lines.append("  [dim]No rate limit data[/dim]")
            except Exception:
                lines.append("  [dim]Rate limiter not available[/dim]")
        else:
            lines.append("  [dim]Router not available[/dim]")
    else:
        lines.append("  [dim]Rate limit info only in embedded mode[/dim]")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# Persistence & Recovery
# ═══════════════════════════════════════════════════════════════════

@command("checkpoint", "Save session checkpoint", "/checkpoint")
async def cmd_checkpoint(tui: Any, args: str) -> str:
    if _embedded(tui):
        o = _office(tui)
        if hasattr(o, 'checkpoint_session'):
            try:
                await o.checkpoint_session(tui._session_id)
                return f"[green]Checkpoint saved for session {tui._session_id}[/green]"
            except Exception as e:
                return f"[red]Checkpoint failed: {e}[/red]"
        elif hasattr(o, '_checkpoint_mgr') and o._checkpoint_mgr:
            try:
                o._checkpoint_mgr.save_session(tui._session_id)
                return f"[green]Checkpoint saved![/green]"
            except Exception as e:
                return f"[red]Checkpoint failed: {e}[/red]"
    return "[yellow]Checkpoint only in embedded mode[/yellow]"

@command("recover", "Recover from crash", "/recover [session_id]")
async def cmd_recover(tui: Any, args: str) -> str:
    if _embedded(tui):
        o = _office(tui)
        if hasattr(o, 'restore_from_crash'):
            try:
                session_id = args.strip() or tui._session_id
                result = await o.restore_from_crash(session_id)
                if result:
                    tui._update_embedded_status()
                    return f"[green]Recovered session: {session_id}[/green]"
                return f"[yellow]No recovery data for {session_id}[/yellow]"
            except Exception as e:
                return f"[red]Recovery failed: {e}[/red]"
        elif hasattr(o, '_crash_recovery'):
            try:
                session_id = args.strip() or tui._session_id
                result = o._crash_recovery.try_recover(session_id)
                if result:
                    return f"[green]Recovered session: {session_id}[/green]"
                return f"[yellow]No recovery data[/yellow]"
            except Exception as e:
                return f"[red]Recovery failed: {e}[/red]"
    return "[yellow]Crash recovery only in embedded mode[/yellow]"

@command("snapshot", "Save office snapshot", "/snapshot")
async def cmd_snapshot(tui: Any, args: str) -> str:
    if _embedded(tui):
        o = _office(tui)
        if hasattr(o, '_checkpoint_mgr') and o._checkpoint_mgr:
            try:
                o._checkpoint_mgr.save_office_snapshot()
                return "[green]Office snapshot saved![/green]"
            except Exception as e:
                return f"[red]Snapshot failed: {e}[/red]"
    return "[yellow]Snapshot only in embedded mode[/yellow]"

@command("snapshots", "List saved snapshots", "/snapshots")
async def cmd_snapshots(tui: Any, args: str) -> str:
    lines = ["[bold cyan]Snapshots[/bold cyan]", ""]
    if _embedded(tui):
        o = _office(tui)
        if hasattr(o, '_checkpoint_mgr') and o._checkpoint_mgr:
            try:
                snaps = o._checkpoint_mgr.list_snapshots()
                if snaps:
                    for s in snaps[:20]:
                        lines.append(f"  {s}")
                else:
                    lines.append("  [dim]No snapshots[/dim]")
            except Exception as e:
                lines.append(f"  [dim]Error: {e}[/dim]")
        else:
            lines.append("  [dim]Checkpoint manager not available[/dim]")
    else:
        lines.append("  [dim]Snapshots only in embedded mode[/dim]")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# Redteam Module
# ═══════════════════════════════════════════════════════════════════

@command("redteam", "Redteam analysis suite", "/redteam <text>")
async def cmd_redteam(tui: Any, args: str) -> str:
    gate = _redteam_gate(tui)
    if gate:
        return gate
    from io import StringIO
    from rich.console import Console
    from kantorku.tui.markdown_renderer import render_redteam_analysis
    if not args.strip():
        return "[yellow]Usage: /redteam <text>[/yellow]\n[dim]Runs classify + stm + parseltongue + scoring[/dim]"
    try:
        from kantorku.redteam.classify import PromptClassifier
        from kantorku.redteam.scoring import ResponseScorer
        from kantorku.redteam.stm import STMEngine, STMModule
        from kantorku.redteam.autotune import AutoTune, ContextType
        from kantorku.redteam.parseltongue import Parseltongue

        # Classify
        classifier = PromptClassifier()
        classification = classifier.classify(args.strip())
        class_dict = classification.to_dict() if hasattr(classification, 'to_dict') else {"category": str(classification), "confidence": 0}

        # STM
        stm = STMEngine()
        stm_result = stm.transform(args.strip())
        stm_dict = {"applied_modules": [m.value if hasattr(m, 'value') else str(m) for m in stm_result.modules_applied]} if hasattr(stm_result, 'modules_applied') else {}

        # Parseltongue
        pt = Parseltongue()
        pt_result = pt.encode(args.strip())
        pt_dict = {"technique": pt_result.technique if hasattr(pt_result, 'technique') else "?",
                    "encoded": pt_result.encoded if hasattr(pt_result, 'encoded') else ""}

        # AutoTune
        at = AutoTune()
        ctx_type = at.classify(args.strip())
        at_dict = {"context_type": ctx_type.value if hasattr(ctx_type, 'value') else str(ctx_type)}

        analysis = {
            "classification": class_dict,
            "stm": stm_dict,
            "parseltongue": pt_dict,
            "autotune": at_dict,
        }
        g = render_redteam_analysis(analysis)
        console = Console(file=StringIO(), force_terminal=True)
        console.print(g)
        return console.file.getvalue()
    except ImportError:
        return "[yellow]Redteam module not available[/yellow]"
    except Exception as e:
        return f"[red]Redteam analysis failed: {e}[/red]"

@command("stm", "Semantic Transformation Modules", "/stm <text>")
async def cmd_stm(tui: Any, args: str) -> str:
    gate = _redteam_gate(tui)
    if gate:
        return gate
    if not args.strip():
        return "[yellow]Usage: /stm <text>[/yellow]\n[dim]Modules: hedge_reducer, direct_mode, casual[/dim]"
    try:
        from kantorku.redteam.stm import STMEngine, STMModule
        stm = STMEngine()
        result = stm.transform(args.strip())
        lines = ["[bold yellow]STM Analysis[/bold yellow]", ""]
        if hasattr(result, 'modules_applied'):
            for m in result.modules_applied:
                lines.append(f"  Module: {m.value if hasattr(m, 'value') else m}")
        if hasattr(result, 'transformed_text'):
            lines.append(f"  Transformed: {result.transformed_text[:100]}")
        if hasattr(result, 'original_text'):
            lines.append(f"  Original: {result.original_text[:100]}")
        return "\n".join(lines)
    except ImportError:
        return "[yellow]STM module not available[/yellow]"

@command("autotune", "Context-adaptive sampling", "/autotune <text>")
async def cmd_autotune(tui: Any, args: str) -> str:
    gate = _redteam_gate(tui)
    if gate:
        return gate
    if not args.strip():
        return "[yellow]Usage: /autotune <text>[/yellow]"
    try:
        from kantorku.redteam.autotune import AutoTune
        at = AutoTune()
        ctx_type = at.classify(args.strip())
        params = at.get_params(ctx_type) if hasattr(at, 'get_params') else {}
        lines = ["[bold cyan]AutoTune[/bold cyan]", ""]
        lines.append(f"  Context: {ctx_type.value if hasattr(ctx_type, 'value') else ctx_type}")
        if params:
            lines.append(f"  Temperature: {params.get('temperature', '?')}")
            lines.append(f"  Top P: {params.get('top_p', '?')}")
            lines.append(f"  Max Tokens: {params.get('max_tokens', '?')}")
        return "\n".join(lines)
    except ImportError:
        return "[yellow]AutoTune module not available[/yellow]"

@command("classify", "Classify prompt harm level", "/classify <text>")
async def cmd_classify(tui: Any, args: str) -> str:
    gate = _redteam_gate(tui)
    if gate:
        return gate
    if not args.strip():
        return "[yellow]Usage: /classify <text>[/yellow]"
    try:
        from kantorku.redteam.classify import PromptClassifier
        classifier = PromptClassifier()
        result = classifier.classify(args.strip())
        if hasattr(result, 'to_dict'):
            d = result.to_dict()
        elif hasattr(result, '__dict__'):
            d = result.__dict__
        else:
            d = {"category": str(result)}
        from kantorku.tui.themes import HARM_COLORS
        category = d.get("category", "unknown")
        color = HARM_COLORS.get(category, "white")
        lines = ["[bold]Classification[/bold]", ""]
        lines.append(f"  Category: [{color}]{category}[/{color}]")
        lines.append(f"  Confidence: {d.get('confidence', '?')}")
        if d.get("reasoning"):
            lines.append(f"  Reasoning: {d['reasoning'][:100]}")
        return "\n".join(lines)
    except ImportError:
        return "[yellow]Classifier module not available[/yellow]"

@command("godmode", "Generate GODMODE liberation prompt", "/godmode")
async def cmd_godmode(tui: Any, args: str) -> str:
    gate = _redteam_gate(tui)
    if gate:
        return gate
    try:
        from kantorku.redteam.godmode import GodModePrompt
        gmp = GodModePrompt()
        prompt = gmp.get_base_prompt()
        depth = gmp.get_depth_directive() if hasattr(gmp, 'get_depth_directive') else ""
        lines = ["[bold red]GODMODE[/bold red]", ""]
        lines.append(f"  [dim]Base prompt: {prompt[:200]}...[/dim]")
        if depth:
            lines.append(f"  [dim]Depth directive: {depth[:100]}...[/dim]")
        forbidden = gmp.get_forbidden_phrases() if hasattr(gmp, 'get_forbidden_phrases') else []
        if forbidden:
            lines.append(f"  [dim]Forbidden phrases: {len(forbidden)}[/dim]")
        return "\n".join(lines)
    except ImportError:
        return "[yellow]GodMode module not available[/yellow]"

@command("score", "Score a response quality", "/score <response>")
async def cmd_score(tui: Any, args: str) -> str:
    gate = _redteam_gate(tui)
    if gate:
        return gate
    if not args.strip():
        return "[yellow]Usage: /score <response_text>[/yellow]"
    try:
        from kantorku.redteam.scoring import ResponseScorer
        scorer = ResponseScorer()
        result = scorer.score(args.strip())
        if hasattr(result, 'to_dict'):
            d = result.to_dict()
        elif hasattr(result, '__dict__'):
            d = result.__dict__
        else:
            d = {"quality_score": float(result) if result else 0}
        lines = ["[bold green]Scoring[/bold green]", ""]
        lines.append(f"  Quality: {d.get('quality_score', '?')}/10")
        lines.append(f"  Refusal: {d.get('is_refusal', '?')}")
        lines.append(f"  GODMODE boost: {d.get('godmode_boost', '?')}")
        return "\n".join(lines)
    except ImportError:
        return "[yellow]Scoring module not available[/yellow]"

@command("parseltongue", "Encode text with parseltongue", "/parseltongue <text>")
async def cmd_parseltongue(tui: Any, args: str) -> str:
    gate = _redteam_gate(tui)
    if gate:
        return gate
    if not args.strip():
        return "[yellow]Usage: /parseltongue <text>[/yellow]"
    try:
        from kantorku.redteam.parseltongue import Parseltongue
        pt = Parseltongue()
        result = pt.encode(args.strip())
        lines = ["[bold magenta]Parseltongue[/bold magenta]", ""]
        if hasattr(result, 'technique'):
            lines.append(f"  Technique: {result.technique}")
        if hasattr(result, 'encoded'):
            lines.append(f"  Encoded: {result.encoded[:200]}")
        if hasattr(result, 'triggers_applied'):
            lines.append(f"  Triggers: {result.triggers_applied}")
        return "\n".join(lines)
    except ImportError:
        return "[yellow]Parseltongue module not available[/yellow]"


# ═══════════════════════════════════════════════════════════════════
# Session Management
# ═══════════════════════════════════════════════════════════════════

@command("reset", "Reset current session", "/reset")
async def cmd_reset(tui: Any, args: str) -> str:
    import uuid
    old = tui._session_id
    tui._session_id = uuid.uuid4().hex[:12]
    tui.pending_contract = {}
    try:
        tui.query_one("#contract-area").contract_data = {}
    except Exception:
        pass

    # Clear worker conversation histories in embedded mode
    if _embedded(tui):
        o = _office(tui)
        if o and hasattr(o, 'registry'):
            for worker_id in o.registry.all_worker_ids:
                try:
                    worker = o.registry.hire(worker_id)
                    worker.clear_conversation()
                except Exception:
                    pass

    # Reset TUI state
    tui._input_history.clear()
    tui._history_index = -1
    try:
        workers_live = tui.query_one("#workers-live", WorkersLiveStream)
        workers_live.clear()
        workers_live._phase = ""
    except Exception:
        pass
    try:
        briefing_panel = tui.query_one("#briefing-panel", BriefingPanel)
        briefing_panel._messages.clear()
        briefing_panel.update("")
    except Exception:
        pass

    return f"[yellow]Session reset![/yellow]\n  Old: {old}\n  New: {tui._session_id}"

@command("export", "Export session to file", "/export [filename]")
async def cmd_export(tui: Any, args: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = args.strip() or f"kantorku_{tui._session_id}_{ts}.json"
    if not filename.startswith("/"):
        filename = os.path.join(os.path.expanduser("~"), filename)
    data = {
        "session_id": tui._session_id,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "connection_state": tui.connection_state,
        "pending_contract": tui.pending_contract,
        "input_history": tui._input_history[-50:],
    }
    if _embedded(tui):
        o = _office(tui)
        data["workers"] = o.get_worker_status()
        if hasattr(o, 'cost_tracker') and o.cost_tracker:
            data["cost_report"] = o.get_cost_report()
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True) if os.path.dirname(filename) else None
        with open(filename, "w") as f:
            json.dump(data, f, indent=2, default=str)
        return f"[green]Exported:[/green] {filename}"
    except Exception as e:
        return f"[red]Export failed:[/red] {e}"

@command("delegate", "View worker delegations", "/delegate")
async def cmd_delegate(tui: Any, args: str) -> str:
    lines = ["[bold cyan]Delegations[/bold cyan]", ""]
    if _embedded(tui):
        o = _office(tui)
        if hasattr(o, 'delegation_manager') and o.delegation_manager:
            dm = o.delegation_manager
            active = dm.get_active_delegations() if hasattr(dm, 'get_active_delegations') else []
            history = dm.get_history() if hasattr(dm, 'get_history') else []
            if active:
                lines.append("[bold]Active:[/bold]")
                for d in active:
                    lines.append(f"  {d.get('from','?')} -> {d.get('to','?')}: {str(d.get('task','?'))[:40]}")
            if history:
                lines.append(f"[bold]History:[/bold] {len(history)} delegations")
                for d in history[-5:]:
                    lines.append(f"  {d.get('from','?')} -> {d.get('to','?')}")
            if not active and not history:
                lines.append("  [dim]No delegations[/dim]")
        else:
            lines.append("  [dim]Delegation manager not available[/dim]")
    else:
        lines.append("  [dim]Only in embedded mode[/dim]")
    return "\n".join(lines)

@command("theme", "Switch color theme", "/theme [office|midnight|terminal|cyberpunk|forest]")
async def cmd_theme(tui: Any, args: str) -> str:
    from kantorku.tui.themes import KANTORKU_THEMES, list_themes, get_theme
    name = args.strip().lower()
    available = list_themes()
    if not name:
        current = getattr(tui, '_current_theme', 'office')
        return (
            f"[bold cyan]Themes[/bold cyan] (current: [bold]{current}[/bold])\n"
            f"  Available: {', '.join(available)}\n"
            f"[dim]Usage: /theme <name>[/dim]"
        )
    if name not in KANTORKU_THEMES:
        return f"[yellow]Unknown theme: {name}[/yellow]\n[dim]Available: {', '.join(available)}[/dim]"
    if hasattr(tui, '_apply_theme'):
        tui._apply_theme(name)
    else:
        # Fallback for non-KantorKuTUI
        t = get_theme(name)
        tui.CSS = f"""
    Screen {{ layout: vertical; }}
    #main-container {{ layout: horizontal; height: 1fr; }}
    #left-panel {{ width: 30%; height: 100%; border: solid {t['primary']}; border-title-color: {t['primary']}; }}
    #center-panel {{ width: 40%; height: 100%; }}
    #right-panel {{ width: 30%; height: 100%; }}
    """
        try:
            tui.screen.styles.update(tui.CSS)
        except Exception:
            pass
    return f"[green]Theme: {name}[/green]"

@command("transcript", "View session transcript", "/transcript")
async def cmd_transcript(tui: Any, args: str) -> str:
    from io import StringIO
    from rich.console import Console
    from kantorku.tui.markdown_renderer import render_transcript
    lines = ["[bold cyan]Session Transcript[/bold cyan]", ""]
    if _embedded(tui):
        o = _office(tui)
        entries = []
        if hasattr(o, 'conductor') and hasattr(o.conductor, '_sessions'):
            session = o.conductor._sessions.get(tui._session_id, {})
            transcript = session.get("transcript")
            if transcript:
                if hasattr(transcript, 'entries'):
                    entries = [e.__dict__ if hasattr(e, '__dict__') else e for e in transcript.entries]
                elif hasattr(transcript, 'get_entries'):
                    entries = transcript.get_entries()
        if entries:
            g = render_transcript(entries)
            console = Console(file=StringIO(), force_terminal=True)
            console.print(g)
            return console.file.getvalue()
        else:
            lines.append("  [dim]No transcript entries yet[/dim]")
    elif _remote(tui):
        try:
            detail = await tui._connection.get_session_detail(tui._session_id)
            if detail:
                transcript = detail.get("transcript", {})
                entries = transcript.get("entries", [])
                if entries:
                    g = render_transcript(entries)
                    console = Console(file=StringIO(), force_terminal=True)
                    console.print(g)
                    return console.file.getvalue()
                else:
                    lines.append("  [dim]No transcript entries yet[/dim]")
            else:
                lines.append("  [dim]Session detail unavailable[/dim]")
        except Exception as e:
            lines.append(f"  [dim]Error fetching transcript: {e}[/dim]")
    else:
        lines.append("  [dim]Not connected[/dim]")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# Settings
# ═══════════════════════════════════════════════════════════════════

@command("settings", "Open settings panel", "/settings")
async def cmd_settings(tui: Any, args: str) -> str:
    """Open the Settings overlay screen."""
    try:
        from kantorku.tui.settings_screen import SettingsScreen
        await tui.push_screen(SettingsScreen(tui))
        return ""
    except Exception as e:
        return f"[red]Failed to open settings: {e}[/red]\n[dim]Check that settings_screen.py is available[/dim]"
