"""
Markdown Renderer — Renders markdown with syntax-highlighted code blocks.

Extends Rich's Markdown renderer with:
- Syntax highlighting for code blocks (30+ languages)
- Better formatting for contracts and task results
- Code block rendering for /code command output
- Contract summary rendering used by ContractPanel
- Task result rendering for work output display
- DAG visualization helper
- Memory stats formatting
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
    STATUS_ICONS,
    STATUS_COLORS,
    CONTRACT_STATE_COLORS,
    SQUAD_COLORS,
)


# Map common language identifiers to Pygments lexers
LANG_MAP = {
    "python": "python",
    "py": "python",
    "javascript": "javascript",
    "js": "javascript",
    "typescript": "typescript",
    "ts": "typescript",
    "rust": "rust",
    "go": "go",
    "bash": "bash",
    "sh": "bash",
    "shell": "bash",
    "sql": "sql",
    "json": "json",
    "yaml": "yaml",
    "yml": "yaml",
    "toml": "toml",
    "html": "html",
    "css": "css",
    "jsx": "jsx",
    "tsx": "tsx",
    "dockerfile": "docker",
    "docker": "docker",
    "makefile": "makefile",
    "markdown": "markdown",
    "md": "markdown",
    "java": "java",
    "c": "c",
    "cpp": "cpp",
    "csharp": "csharp",
    "cs": "csharp",
    "ruby": "ruby",
    "rb": "ruby",
    "php": "php",
    "swift": "swift",
    "kotlin": "kotlin",
    "kt": "kotlin",
    "scala": "scala",
    "r": "r",
    "lua": "lua",
    "perl": "perl",
    "pl": "perl",
    "elixir": "elixir",
    "ex": "elixir",
    "haskell": "haskell",
    "hs": "haskell",
    "zig": "zig",
    "nix": "nix",
    "protobuf": "protobuf",
    "proto": "protobuf",
    "graphql": "graphql",
    "gql": "graphql",
    "xml": "xml",
    "ini": "ini",
    "cfg": "ini",
    "conf": "nginx",
    "nginx": "nginx",
}


def render_markdown(text: str) -> Markdown:
    """Render markdown text with Rich's Markdown widget."""
    return Markdown(text, code_theme="monokai")


def render_code(code: str, language: str = "") -> Syntax:
    """
    Render a code block with syntax highlighting.

    Used for:
    - Displaying worker output code blocks
    - /code command output
    - Inline code review in chat
    """
    lexer = LANG_MAP.get(language.lower(), language or "text")
    try:
        return Syntax(
            code,
            lexer,
            theme="monokai",
            line_numbers=True,
            word_wrap=False,
        )
    except Exception:
        return Syntax(code, "text", theme="monokai")


def render_contract_summary(contract: dict[str, Any]) -> Text:
    """
    Render a contract summary as a Rich Text object.

    Used by ContractPanel and /status command.
    Displays: title, state, description, and task list with status icons.
    """
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
            lines.append(f"  [{color}]{icon}[/{color}] [{assigned}]{squad_str} {desc[:60]}")

    return Text.from_markup("\n".join(lines))


def render_task_result(result: dict[str, Any] | str) -> Text | Markdown:
    """
    Render a task result as a Rich object.

    Used for:
    - Work completion display in chat
    - /code command output
    - Worker output viewer

    Handles both dict (structured) and str (raw text) results.
    """
    if isinstance(result, str):
        return render_markdown(result)

    lines = []

    worker = result.get("worker_id", "unknown")
    status = result.get("status", "?")
    output = result.get("output", "")

    status_color = "green" if status == "done" else "red"
    lines.append(f"[bold]{worker}[/bold] [{status_color}]{status}[/{status_color}]")

    if output:
        # Truncate very long outputs
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

    return Text.from_markup("\n".join(lines))


def render_dag_tree(
    groups: list[list[dict]],
    todos: list[dict],
) -> Tree:
    """
    Render a DAG as a Rich Tree.

    Used by DAGPanel and /dag command.
    Groups represent parallel execution levels.
    """
    tree = Tree("Task DAG", guide_style="cyan")

    if groups:
        for level, group in enumerate(groups):
            branch = tree.add(f"[bold]Level {level}[/bold] (parallel)")
            for task in group:
                status = task.get("status", "pending")
                icon = STATUS_ICONS.get(status, "?")
                color = STATUS_COLORS.get(status, "dim")
                desc = task.get("description", task.get("id", "?"))[:40]
                assigned = task.get("assigned_to", "unassigned")
                branch.add(f"[{color}]{icon}[/{color}] [{assigned}] {desc}")
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
    """
    Render 3-Ring memory statistics as a Rich Group.

    Used by MemoryPanel and /memory command.
    """
    parts: list[Any] = []

    # Ring 1
    r1_lines = [
        f"[bold cyan]Ring 1 (DuckDB — Hot)[/bold cyan]",
        f"  Contexts: {ring1.get('context_count', '?')}",
        f"  Sessions: {ring1.get('session_count', '?')}",
        f"  Task Results: {ring1.get('task_result_count', '?')}",
        f"  History: {ring1.get('history_count', '?')}",
        f"  DB Size: {ring1.get('db_size_mb', '?')} MB",
    ]
    parts.append(Text.from_markup("\n".join(r1_lines)))

    # Ring 2
    r2_lines = [
        f"\n[bold magenta]Ring 2 (SQLite — Warm)[/bold magenta]",
        f"  Episodes: {ring2.get('episode_count', '?')}",
        f"  Lessons: {ring2.get('lesson_count', '?')}",
        f"  Audit Trails: {ring2.get('audit_trail_count', '?')}",
        f"  DB Size: {ring2.get('db_size_mb', '?')} MB",
    ]
    parts.append(Text.from_markup("\n".join(r2_lines)))

    # Ring 3
    parts.append(Text.from_markup(
        "\n[bold dim]Ring 3 (Cognee GraphRAG — Cold)[/bold dim]\n"
        "  [dim]Not yet connected[/dim]"
    ))

    return Group(*parts)


def render_health_table(providers: dict[str, dict]) -> Table:
    """
    Render provider health as a Rich Table.

    Used by HealthPanel and /health command.
    """
    table = Table(
        title="Provider Health",
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
        expand=True,
    )
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

        table.add_row(
            name,
            circuit_str,
            str(total),
            f"{success_rate:.0%}" if total > 0 else "N/A",
            f"{avg_lat:.0f}ms" if avg_lat > 0 else "N/A",
            health_str,
        )

    return table
