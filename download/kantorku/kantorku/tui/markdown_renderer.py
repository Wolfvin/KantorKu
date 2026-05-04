"""
Markdown Renderer — Renders markdown with syntax-highlighted code blocks.

Extends Rich's Markdown renderer with:
- Syntax highlighting for code blocks
- Better formatting for contracts and task results
- Code block copy indicators
"""

from __future__ import annotations

from typing import Any

from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.text import Text


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
}


def render_markdown(text: str) -> Markdown:
    """Render markdown text with Rich's Markdown widget."""
    return Markdown(text, code_theme="monokai")


def render_code(code: str, language: str = "") -> Syntax:
    """Render a code block with syntax highlighting."""
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
    """Render a contract summary as a Rich Text object."""
    lines = []

    title = contract.get("title", "Untitled Contract")
    state = contract.get("state", "unknown")
    description = contract.get("description", "")

    state_styles = {
        "drafting": "yellow",
        "proposed": "cyan",
        "negotiating": "yellow",
        "accepted": "green",
        "working": "blue",
        "verifying": "magenta",
        "done": "green bold",
        "failed": "red",
    }
    state_style = state_styles.get(state, "white")

    lines.append(f"[bold cyan]Contract:[/bold cyan] {title}")
    lines.append(f"[bold]State:[/bold] [{state_style}]{state}[/{state_style}]")
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
            icon = {
                "pending": "[dim]○[/dim]",
                "in_progress": "[yellow]◑[/yellow]",
                "done": "[green]●[/green]",
                "failed": "[red]●[/red]",
            }.get(todo_state, "○")
            lines.append(f"  {icon} [{assigned}] {desc[:60]}")

    return Text.from_markup("\n".join(lines))


def render_task_result(result: dict[str, Any]) -> Text:
    """Render a task result as a Rich Text object."""
    lines = []

    worker = result.get("worker_id", "unknown")
    status = result.get("status", "?")
    output = result.get("output", "")

    status_style = "green" if status == "done" else "red"
    lines.append(f"[bold]{worker}[/bold] [{status_style}]{status}[/{status_style}]")

    if output:
        # Truncate very long outputs
        if len(output) > 2000:
            output = output[:2000] + "\n... (truncated)"
        lines.append(output)

    error = result.get("error", "")
    if error:
        lines.append(f"[red]Error: {error}[/red]")

    return Text.from_markup("\n".join(lines))
