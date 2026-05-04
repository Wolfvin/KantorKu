"""
Slash Commands — Quick commands for the TUI.

Provides a /commands system for coders to quickly interact with
the KantorKu office without full typing.

Usage in TUI:
    /status        — Show office status
    /accept        — Accept current contract
    /revise ...    — Revise contract with feedback
    /workers       — Show worker grid
    /health        — Show provider health
    /cost          — Show cost report
    /sessions      — List active sessions
    /reset         — Reset current session
    /help          — Show available commands
    /code ...      — Quick code task (auto-accept)
"""

from __future__ import annotations

from dataclasses import dataclass
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
    lines = ["[bold cyan]Slash Commands:[/bold cyan]", ""]
    max_name = max(len(name) for name in COMMANDS) if COMMANDS else 0

    for name in sorted(COMMANDS.keys()):
        cmd = COMMANDS[name]
        lines.append(
            f"  [bold green]/{name:<{max_name}}[/bold green]  {cmd.description}"
        )
        if cmd.usage and cmd.usage != f"/{name}":
            lines.append(f"  {'':>{max_name + 2}}  [dim]{cmd.usage}[/dim]")

    lines.append("")
    lines.append("[dim]Type a message without / to chat with the Conductor[/dim]")
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


# ── Command Handlers ───────────────────────────────────────────────


@command("status", "Show office status", "/status")
async def cmd_status(tui: Any, args: str) -> str:
    """Show current office status."""
    lines = [
        "[bold]Office Status[/bold]",
        f"  Session:    {tui._session_id}",
        f"  Connection: {tui.connection_state}",
    ]

    if hasattr(tui, '_connection') and tui._connection._http_client:
        try:
            status = await tui._connection.get_status()
            if status:
                workers = status.get("workers", [])
                lines.append(f"  Workers:    {len(workers)}")

                cost = status.get("cost", {})
                if cost:
                    total = cost.get("total_cost_usd", 0)
                    calls = cost.get("total_calls", 0)
                    lines.append(f"  Cost:       ${total:.4f} ({calls} calls)")
        except Exception:
            lines.append("  [dim](status unavailable)[/dim]")
    elif hasattr(tui, '_office') and tui._office:
        workers = tui._office.get_worker_status()
        lines.append(f"  Workers:    {len(workers)}")
        lines.append(f"  Mode:       Embedded")

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

    table = Table(title="Workers", show_header=True)
    table.add_column("ID", style="bold")
    table.add_column("Status")
    table.add_column("Model")
    table.add_column("Squad")
    table.add_column("Role")

    if hasattr(tui, '_connection') and tui._connection._http_client:
        try:
            status = await tui._connection.get_status()
            workers = status.get("workers", []) if status else []
        except Exception:
            workers = []
    elif hasattr(tui, '_office') and tui._office:
        workers = tui._office.get_worker_status()
    else:
        workers = []

    if not workers:
        return "[dim]No workers available[/dim]"

    for w in workers:
        status = w.get("status", "?")
        s = {"idle": "[dim]idle[/dim]", "active": "[green]active[/green]", "failed": "[red]failed[/red]"}.get(status, status)
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

    if hasattr(tui, '_connection') and tui._connection._http_client:
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
                active = alerts.get("total_active", 0)
                critical = alerts.get("critical", 0)
                if active > 0:
                    lines.append(f"\n  [red]{active} active alerts ({critical} critical)[/red]")
        except Exception:
            lines.append("  [dim](health unavailable)[/dim]")
    else:
        lines.append("  [dim]Not connected[/dim]")

    return "\n".join(lines)


@command("cost", "Show cost tracking report", "/cost")
async def cmd_cost(tui: Any, args: str) -> str:
    """Show LLM cost report."""
    lines = ["[bold]Cost Report[/bold]", ""]

    if hasattr(tui, '_connection') and tui._connection._http_client:
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
    else:
        lines.append("  [dim]Not connected[/dim]")

    return "\n".join(lines)


@command("sessions", "List active sessions", "/sessions")
async def cmd_sessions(tui: Any, args: str) -> str:
    """List active sessions."""
    lines = ["[bold]Active Sessions[/bold]", ""]

    if hasattr(tui, '_connection') and tui._connection._http_client:
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

    # Send the message
    await tui._send_message(args)

    # Auto-accept if contract is ready
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
