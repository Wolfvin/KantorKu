"""
Markdown Renderer — Renders markdown with syntax-highlighted code blocks.

Complete rendering for ALL KantorKu framework features:
- Markdown with syntax highlighting (30+ languages)
- Contract summary with full state display
- Task result with worker/output/error/tokens/duration
- DAG tree visualization with critical path
- 3-Ring memory stats
- Health table for providers
- Structured error display (KantorkuError hierarchy)
- Worker identity card
- Middleware pipeline visualization
- Session transcript display
- Redteam analysis results
- Cost breakdown by session/worker/model
- Audit trail entries
- Checkpoint/snapshot display
"""

from __future__ import annotations

from typing import Any

from rich.console import Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from kantorku.tui.themes import (
    STATUS_ICONS, STATUS_COLORS, CONTRACT_STATE_COLORS,
    SQUAD_COLORS, ERROR_COLORS, MIDDLEWARE_COLORS,
    REDTEAM_STYLES, HARM_COLORS, TASK_STATE_ICONS, TASK_STATE_COLORS,
    SEVERITY_COLORS,
)

# Language map for syntax highlighting
LANG_MAP = {
    "python": "python", "py": "python",
    "javascript": "javascript", "js": "javascript",
    "typescript": "typescript", "ts": "typescript",
    "rust": "rust", "go": "go",
    "bash": "bash", "sh": "bash", "shell": "bash",
    "sql": "sql", "json": "json", "yaml": "yaml", "yml": "yaml",
    "toml": "toml", "html": "html", "css": "css",
    "jsx": "jsx", "tsx": "tsx",
    "dockerfile": "docker", "docker": "docker",
    "makefile": "makefile", "markdown": "markdown", "md": "markdown",
    "java": "java", "c": "c", "cpp": "cpp",
    "csharp": "csharp", "cs": "csharp",
    "ruby": "ruby", "rb": "ruby", "php": "php",
    "swift": "swift", "kotlin": "kotlin", "kt": "kotlin",
    "scala": "scala", "r": "r", "lua": "lua",
    "perl": "perl", "pl": "perl", "elixir": "elixir", "ex": "elixir",
    "haskell": "haskell", "hs": "haskell", "zig": "zig",
    "nix": "nix", "protobuf": "protobuf", "proto": "protobuf",
    "graphql": "graphql", "gql": "graphql", "xml": "xml",
    "ini": "ini", "cfg": "ini", "nginx": "nginx",
}


def render_markdown(text: str) -> Markdown:
    """Render markdown text with Rich's Markdown widget."""
    return Markdown(text, code_theme="monokai")


def render_code(code: str, language: str = "") -> Syntax:
    """Render a code block with syntax highlighting."""
    lexer = LANG_MAP.get(language.lower(), language or "text")
    try:
        return Syntax(code, lexer, theme="monokai", line_numbers=True, word_wrap=False)
    except Exception:
        return Syntax(code, "text", theme="monokai")


def render_contract_summary(contract: dict[str, Any]) -> Text:
    """Render a contract summary with full state display."""
    lines = []
    title = contract.get("title", "Untitled Contract")
    state = contract.get("state", "unknown")
    description = contract.get("description", "")
    state_color = CONTRACT_STATE_COLORS.get(state, "white")

    lines.append(f"[bold cyan]Contract:[/bold cyan] {title}")
    lines.append(f"[bold]State:[/bold] [{state_color}]{state}[/{state_color}]")
    if description:
        lines.append(f"[dim]{description[:300]}[/dim]")
    lines.append("")

    todos = contract.get("todos", [])
    if todos:
        lines.append(f"[bold]Tasks ({len(todos)}):[/bold]")
        for i, todo in enumerate(todos):
            desc = todo.get("description", "")
            assigned = todo.get("assigned_to", "unassigned")
            todo_state = todo.get("status", "pending")
            icon = STATUS_ICONS.get(todo_state, "?")
            color = STATUS_COLORS.get(todo_state, "dim")
            squad = todo.get("squad", "")
            squad_str = f" [{SQUAD_COLORS.get(squad, 'dim')}]{squad}[/]" if squad else ""
            deps = todo.get("depends_on", [])
            dep_str = f" [dim](depends: {','.join(str(d) for d in deps[:3])})[/dim]" if deps else ""
            lines.append(f"  [{color}]{icon}[/{color}] [{assigned}]{squad_str} {desc[:60]}{dep_str}")

    return Text.from_markup("\n".join(lines))


def render_task_result(result: dict[str, Any] | str) -> Text | Markdown:
    """Render a task result with full details."""
    if isinstance(result, str):
        return render_markdown(result)

    lines = []
    worker = result.get("worker_id", "unknown")
    status = result.get("status", "?")
    output = result.get("output", "")
    status_color = "green" if status == "done" else "red"
    lines.append(f"[bold]{worker}[/bold] [{status_color}]{status}[/{status_color}]")

    if output:
        if len(output) > 2000:
            output = output[:2000] + "\n... (truncated)"
        lines.append(output)

    error = result.get("error", "")
    if error:
        lines.append(f"[red]Error: {error}[/red]")

    files = result.get("files", [])
    if files:
        lines.append(f"[cyan]Files: {', '.join(files)}[/cyan]")

    duration = result.get("duration_seconds", 0)
    if duration:
        lines.append(f"[dim]Duration: {duration:.1f}s[/dim]")

    tokens = result.get("tokens_used", 0)
    if tokens:
        lines.append(f"[dim]Tokens: {tokens}[/dim]")

    cost = result.get("cost_usd", 0)
    if cost:
        lines.append(f"[dim]Cost: ${cost:.4f}[/dim]")

    cached = result.get("cached", False)
    if cached:
        lines.append(f"[cyan dim](cached)[/cyan dim]")

    return Text.from_markup("\n".join(lines))


def render_dag_tree(groups: list[list[dict]], todos: list[dict],
                    critical_path: list[str] | None = None) -> Tree:
    """Render a DAG tree with critical path highlighting."""
    tree = Tree("Task DAG", guide_style="cyan")
    cp_set = set(critical_path) if critical_path else set()

    if groups:
        for level, group in enumerate(groups):
            is_cp_level = any(t.get("id", "") in cp_set for t in group)
            level_label = f"[bold]Level {level}[/bold] (parallel)"
            if is_cp_level:
                level_label += " [red bold]*CRITICAL*[/red bold]"
            branch = tree.add(level_label)
            for task in group:
                status = task.get("status", "pending")
                icon = STATUS_ICONS.get(status, "?")
                color = STATUS_COLORS.get(status, "dim")
                desc = task.get("description", task.get("id", "?"))[:40]
                assigned = task.get("assigned_to", "unassigned")
                is_cp = task.get("id", "") in cp_set
                cp_marker = " [red bold]*[/red bold]" if is_cp else ""
                branch.add(f"[{color}]{icon}[/{color}] [{assigned}] {desc}{cp_marker}")
    elif todos:
        for todo in todos:
            status = todo.get("status", "pending")
            icon = STATUS_ICONS.get(status, "?")
            color = STATUS_COLORS.get(status, "dim")
            desc = todo.get("description", "?")[:50]
            assigned = todo.get("assigned_to", "unassigned")
            tree.add(f"[{color}]{icon}[/{color}] [{assigned}] {desc}")

    return tree


def render_memory_stats(ring1: dict, ring2: dict) -> Group:
    """Render 3-Ring memory statistics."""
    parts: list[Any] = []

    r1_lines = [
        "[bold cyan]Ring 1 (DuckDB — Hot)[/bold cyan]",
        f"  Contexts: {ring1.get('context_count', '?')}",
        f"  Sessions: {ring1.get('session_count', '?')}",
        f"  Task Results: {ring1.get('task_result_count', '?')}",
        f"  History: {ring1.get('history_count', '?')}",
        f"  DB Size: {ring1.get('db_size_mb', '?')} MB",
    ]
    parts.append(Text.from_markup("\n".join(r1_lines)))

    r2_lines = [
        "\n[bold magenta]Ring 2 (SQLite — Warm)[/bold magenta]",
        f"  Episodes: {ring2.get('episode_count', '?')}",
        f"  Lessons: {ring2.get('lesson_count', '?')}",
        f"  Audit Trails: {ring2.get('audit_trail_count', '?')}",
        f"  DB Size: {ring2.get('db_size_mb', '?')} MB",
    ]
    parts.append(Text.from_markup("\n".join(r2_lines)))

    parts.append(Text.from_markup(
        "\n[bold dim]Ring 3 (Cognee GraphRAG — Cold)[/bold dim]\n"
        "  [dim]Not yet connected[/dim]"
    ))

    return Group(*parts)


def render_health_table(providers: dict[str, dict]) -> Table:
    """Render provider health table."""
    table = Table(title="Provider Health", show_header=True, header_style="bold cyan",
                  border_style="dim", expand=True)
    table.add_column("Provider", style="bold", width=14)
    table.add_column("Circuit", width=12)
    table.add_column("Calls", width=8)
    table.add_column("Success", width=10)
    table.add_column("Latency", width=10)
    table.add_column("Status", width=10)

    for name, data in providers.items():
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
        table.add_row(name, circuit_str, str(total),
                      f"{success_rate:.0%}" if total > 0 else "N/A",
                      f"{avg_lat:.0f}ms" if avg_lat > 0 else "N/A", health_str)

    return table


def render_error(error: dict[str, Any]) -> Text:
    """Render a structured KantorkuError with code and context."""
    error_type = error.get("type", "KantorkuError")
    message = error.get("message", "Unknown error")
    code = error.get("code", "")
    context = error.get("context", {})
    color = ERROR_COLORS.get(error_type, "red")

    lines = [f"[{color} bold]{error_type}[/{color} bold]: {message}"]
    if code:
        lines.append(f"  [dim]Code: {code}[/dim]")
    if context:
        for k, v in list(context.items())[:5]:
            lines.append(f"  [dim]{k}: {v}[/dim]")

    return Text.from_markup("\n".join(lines))


def render_worker_identity(identity: dict[str, Any]) -> Group:
    """Render a WorkerIdentity card with full details."""
    parts: list[Any] = []
    wid = identity.get("id", "?")
    role = identity.get("role", "")
    squad = identity.get("squad", "")
    category = identity.get("category", "")
    subcategory = identity.get("subcategory", "")

    parts.append(Text.from_markup(f"[bold cyan]{wid}[/bold cyan] — {role}"))

    api = identity.get("api", {})
    if api:
        provider = api.get("provider", "?")
        model = api.get("model", "?")
        base_url = api.get("base_url", "")
        parts.append(Text.from_markup(f"  [bold]Provider:[/bold] {provider} / {model}"))
        if base_url:
            parts.append(Text.from_markup(f"  [dim]Base URL: {base_url}[/dim]"))

    squad_color = SQUAD_COLORS.get(squad, "white")
    parts.append(Text.from_markup(
        f"  [bold]Squad:[/bold] [{squad_color}]{squad}[/{squad_color}]  "
        f"[bold]Category:[/bold] {category}/{subcategory}"
    ))

    capabilities = identity.get("capabilities", [])
    if capabilities:
        parts.append(Text.from_markup(f"  [bold]Capabilities:[/bold] {', '.join(capabilities[:8])}"))

    skill_md = identity.get("skill_markdown", "")
    if skill_md:
        parts.append(Text.from_markup(f"  [dim]SKILL.md: {skill_md[:100]}...[/dim]"))

    return Group(*parts)


def render_middleware_pipeline(middlewares: list[dict[str, Any]]) -> Tree:
    """Render middleware pipeline as a tree."""
    tree = Tree("Middleware Pipeline", guide_style="blue")
    for i, mw in enumerate(middlewares):
        name = mw.get("name", f"Middleware_{i}")
        mw_type = mw.get("type", name)
        color = MIDDLEWARE_COLORS.get(mw_type, "white")
        enabled = mw.get("enabled", True)
        status = "[green]ON[/green]" if enabled else "[dim]OFF[/dim]"
        config = mw.get("config", {})
        config_str = f" {config}" if config else ""
        tree.add(f"[{color}]{name}[/{color}] {status}{config_str}")
    return tree


def render_transcript(entries: list[dict[str, Any]]) -> Group:
    """Render session transcript entries."""
    parts: list[Any] = []
    for entry in entries[-30:]:
        phase = entry.get("phase", "?")
        role = entry.get("role", "?")
        content = entry.get("content", "")[:100]
        timestamp = entry.get("timestamp", "")
        ts_str = timestamp.split("T")[1][:8] if "T" in str(timestamp) else ""

        phase_colors = {
            "client_discussion": "cyan",
            "team_briefing": "magenta",
            "todo_review": "blue",
            "execution": "green",
        }
        color = phase_colors.get(phase, "white")
        parts.append(Text.from_markup(
            f"  [{color}]{phase}[/{color}] [bold]{role}[/bold]: {content} [dim]{ts_str}[/dim]"
        ))

    if not parts:
        parts.append(Text.from_markup("[dim]No transcript entries[/dim]"))

    return Group(*parts)


def render_redteam_analysis(analysis: dict[str, Any]) -> Group:
    """Render redteam analysis results."""
    parts: list[Any] = []

    # Classification
    classification = analysis.get("classification", {})
    if classification:
        category = classification.get("category", "unknown")
        confidence = classification.get("confidence", 0)
        color = HARM_COLORS.get(category, "white")
        parts.append(Text.from_markup(
            f"[bold]Classification:[/bold] [{color}]{category}[/{color}] "
            f"(confidence: {confidence:.0%})"
        ))

    # Scoring
    scoring = analysis.get("scoring", {})
    if scoring:
        quality = scoring.get("quality_score", 0)
        refusal = scoring.get("is_refusal", False)
        parts.append(Text.from_markup(
            f"[bold]Quality:[/bold] {quality:.1f}/10  "
            f"[bold]Refusal:[/bold] {'[red]Yes[/red]' if refusal else '[green]No[/green]'}"
        ))

    # STM modules
    stm = analysis.get("stm", {})
    if stm:
        modules = stm.get("applied_modules", [])
        if modules:
            parts.append(Text.from_markup(
                f"[bold]STM Modules:[/bold] {', '.join(modules)}"
            ))

    # Parseltongue
    parseltongue = analysis.get("parseltongue", {})
    if parseltongue:
        technique = parseltongue.get("technique", "")
        encoded = parseltongue.get("encoded", "")
        if technique:
            parts.append(Text.from_markup(
                f"[bold magenta]Parseltongue:[/bold magenta] {technique}"
            ))
        if encoded:
            parts.append(Text.from_markup(f"  [dim]{encoded[:80]}[/dim]"))

    # AutoTune
    autotune = analysis.get("autotune", {})
    if autotune:
        ctx_type = autotune.get("context_type", "")
        params = autotune.get("sampling_params", {})
        parts.append(Text.from_markup(
            f"[bold cyan]AutoTune:[/bold cyan] {ctx_type}"
        ))
        if params:
            parts.append(Text.from_markup(
                f"  [dim]temp={params.get('temperature', '?')} "
                f"top_p={params.get('top_p', '?')}[/dim]"
            ))

    if not parts:
        parts.append(Text.from_markup("[dim]No analysis data[/dim]"))

    return Group(*parts)


def render_cost_breakdown(cost: dict[str, Any], mode: str = "full") -> Group:
    """Render cost breakdown by model, worker, and session."""
    parts: list[Any] = []

    total = cost.get("total_cost_usd", 0)
    calls = cost.get("total_calls", 0)
    parts.append(Text.from_markup(
        f"[bold cyan]Total:[/bold cyan] ${total:.4f} ({calls} calls)"
    ))

    by_model = cost.get("by_model", {})
    if by_model and mode in ("full", "model"):
        parts.append(Text.from_markup("\n[bold]By Model:[/bold]"))
        table = Table(show_header=True, header_style="bold", border_style="dim", expand=True)
        table.add_column("Model", width=30)
        table.add_column("Cost", width=12)
        table.add_column("Calls", width=8)
        table.add_column("Tokens", width=10)
        for model, data in by_model.items():
            table.add_row(
                model,
                f"${data.get('cost_usd', 0):.4f}",
                str(data.get("calls", 0)),
                str(data.get("total_tokens", 0)),
            )
        parts.append(table)

    by_worker = cost.get("by_worker", {})
    if by_worker and mode in ("full", "worker"):
        parts.append(Text.from_markup("\n[bold]By Worker:[/bold]"))
        table = Table(show_header=True, header_style="bold", border_style="dim", expand=True)
        table.add_column("Worker", width=20)
        table.add_column("Cost", width=12)
        table.add_column("Calls", width=8)
        for worker, data in by_worker.items():
            table.add_row(
                worker,
                f"${data.get('cost_usd', 0):.4f}",
                str(data.get("calls", 0)),
            )
        parts.append(table)

    by_session = cost.get("by_session", {})
    if by_session and mode in ("full", "session"):
        parts.append(Text.from_markup("\n[bold]By Session:[/bold]"))
        for sid, data in list(by_session.items())[:10]:
            parts.append(Text.from_markup(
                f"  {sid}: ${data.get('cost_usd', 0):.4f} ({data.get('calls', 0)} calls)"
            ))

    pricing = cost.get("pricing_table", {})
    if pricing and mode == "full":
        parts.append(Text.from_markup("\n[bold dim]Pricing Table:[/bold dim]"))
        for provider, models in list(pricing.items())[:5]:
            parts.append(Text.from_markup(f"  [dim]{provider}:[/dim]"))
            if isinstance(models, dict):
                for model, price in list(models.items())[:3]:
                    parts.append(Text.from_markup(f"    [dim]{model}: ${price}/1K tokens[/dim]"))

    return Group(*parts)


def render_checkpoint(snapshot: dict[str, Any]) -> Group:
    """Render a checkpoint/snapshot display."""
    parts: list[Any] = []
    sid = snapshot.get("session_id", "?")
    ts = snapshot.get("timestamp", "?")
    state = snapshot.get("state", "?")
    parts.append(Text.from_markup(
        f"[bold green]Checkpoint[/bold green] Session: {sid}"
    ))
    parts.append(Text.from_markup(f"  State: [{CONTRACT_STATE_COLORS.get(state, 'dim')}]{state}[/]"))
    parts.append(Text.from_markup(f"  Time: {ts}"))
    todos = snapshot.get("todos", [])
    if todos:
        parts.append(Text.from_markup(f"  Tasks: {len(todos)}"))
    return Group(*parts)


def render_audit_trail(entries: list[dict[str, Any]]) -> Group:
    """Render Ring2 audit trail entries."""
    parts: list[Any] = []
    if not entries:
        parts.append(Text.from_markup("[dim]No audit trail entries[/dim]"))
        return Group(*parts)

    table = Table(title="Audit Trail", show_header=True, header_style="bold cyan",
                  border_style="dim", expand=True)
    table.add_column("Time", width=10)
    table.add_column("Action", width=20)
    table.add_column("Worker", width=16)
    table.add_column("Detail", width=30)
    for e in entries[-20:]:
        ts = e.get("timestamp", "")
        if "T" in str(ts):
            ts = str(ts).split("T")[1][:8]
        table.add_row(
            ts,
            e.get("action", "?")[:20],
            e.get("worker_id", "?")[:16],
            str(e.get("detail", ""))[:30],
        )
    parts.append(table)
    return Group(*parts)
