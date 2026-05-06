"""
DAGPanel — ASCII tree rendering of task dependency graph.

Shows the DAG (Directed Acyclic Graph) of task dependencies with
status icons, critical path highlighting, and parallel group display.

Layout:
    ┌────────────────────────────────────────────────────────────┐
    │  DAG — Task Dependency Tree                                │
    │  ───────────────────────────────────────────────────────── │
    │                                                            │
    │  🗂 Task Dependency Tree                                   │
    │  ██ coding                                                 │
    │  ├─ ⏳ Implement rate limiter          [coder]            │
    │  └─ ⏳ Add token bucket                [architect]        │
    │  ██ verification                                           │
    │  ├─ 🔄 Verify rate limiter             [verifier]         │
    │  └─ ✅ Check test coverage             [qa]               │
    │                                                            │
    │  ⚡ Critical Path: setup → impl → verify                   │
    │                                                            │
    │  Tasks: 4 total, 1 done, 0 failed                         │
    │  Legend: ⏳ pending  🔄 running  ✅ done  ❌ failed        │
    └────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static

from rich.console import Group
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree

from kantorku.tui.themes import (
    KANTORKU_THEME,
    SQUAD_COLORS,
    STATUS_ICONS,
    STATUS_COLORS,
)

# ── DAG Status Icons ──────────────────────────────────────────────────

DAG_STATUS_ICONS = {
    "pending": "\u23f3",       # ⏳
    "assigned": "\u23f3",      # ⏳
    "running": "\U0001f504",   # 🔄
    "in_progress": "\U0001f504",  # 🔄
    "done": "\u2705",          # ✅
    "completed": "\u2705",     # ✅
    "failed": "\u274c",        # ❌
}

DAG_STATUS_COLORS = {
    "pending": "dim",
    "assigned": "dim",
    "running": "yellow",
    "in_progress": "yellow",
    "done": "green",
    "completed": "green",
    "failed": "red bold",
}

# ── CSS ────────────────────────────────────────────────────────────────

_CSS = """
DAGPanel {
    layout: vertical;
    height: 1fr;
}

#dag-content {
    height: 1fr;
    scrollbar-size: 1 1;
    padding: 0 1;
}
"""


class DAGPanel(Static):
    """DAG / Task dependency tree panel.

    Features:
    - ASCII tree rendering of task dependency graph
    - Status icons: ⏳ pending, 🔄 running, ✅ done, ❌ failed
    - Critical path highlighted in bold
    - Parallel group display with indentation
    - Legend at bottom

    Receives task events and builds a visual task tree.
    Integrates with kantorku.dag.DAGResolver for critical path.
    """

    CSS = _CSS

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._tasks: dict[str, dict[str, Any]] = {}
        self._groups: dict[str, list[str]] = {}  # squad -> [task_ids]
        self._todos: list[dict[str, Any]] = []
        self._critical_path: list[str] = []
        self._parallel_groups: list[list[str]] = []  # From DAGResolver

    # ── Compose ────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="dag-content"):
            yield Static(id="dag-tree")

    # ── Public API ─────────────────────────────────────────────────

    def update_dag(
        self,
        groups: dict[str, list[str]] | None = None,
        todos: list[dict[str, Any]] | None = None,
        critical_path: list[str] | None = None,
        parallel_groups: list[list[str]] | None = None,
    ) -> None:
        """Update the DAG with new task information.

        Args:
            groups: Squad-based grouping of task IDs
            todos: List of task dictionaries with status info
            critical_path: List of task IDs forming the critical path
            parallel_groups: Parallel execution groups from DAGResolver
        """
        if groups is not None:
            self._groups = groups
        if todos is not None:
            self._todos = todos
            for todo in todos:
                tid = todo.get("id", todo.get("description", "?"))
                self._tasks[tid] = todo
        if critical_path is not None:
            self._critical_path = critical_path
        if parallel_groups is not None:
            self._parallel_groups = parallel_groups
        self._render_dag()

    def add_event(self, event: dict[str, Any]) -> None:
        """Update task status from events."""
        event_type = event.get("type", "")

        if event_type == "task_assigned":
            to_id = event.get("to", "?")
            content = event.get("content", "")
            squad = event.get("squad", "")
            tid = event.get("task_id", content[:30])
            depends_on = event.get("depends_on", [])
            self._tasks[tid] = {
                "id": tid,
                "description": content,
                "assigned_to": to_id,
                "status": "assigned",
                "squad": squad,
                "depends_on": depends_on,
            }
            if squad:
                if squad not in self._groups:
                    self._groups[squad] = []
                if tid not in self._groups[squad]:
                    self._groups[squad].append(tid)

        elif event_type == "task_started":
            from_id = event.get("from", "?")
            for tid, task in self._tasks.items():
                if task.get("assigned_to") == from_id and task.get("status") not in ("done", "failed"):
                    task["status"] = "in_progress"
                    break

        elif event_type == "task_done":
            from_id = event.get("from", "?")
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

        elif event_type == "task_recovered":
            from_id = event.get("from", "?")
            for tid, task in self._tasks.items():
                if task.get("assigned_to") == from_id:
                    task["status"] = "in_progress"
                    break

        self._render_dag()

    def compute_critical_path(self) -> None:
        """Compute the critical path using DAGResolver."""
        try:
            from kantorku.dag import DAGResolver, TaskNode

            nodes = []
            for tid, task in self._tasks.items():
                depends_on = task.get("depends_on", [])
                if isinstance(depends_on, str):
                    depends_on = [depends_on]
                nodes.append(TaskNode(id=tid, depends_on=depends_on, data=task))

            if nodes:
                resolver = DAGResolver(nodes)
                self._critical_path = resolver.get_critical_path()
                self._parallel_groups = [
                    [n.id for n in group]
                    for group in resolver.resolve()
                ]
        except Exception:
            pass

        self._render_dag()

    def clear(self) -> None:
        """Clear the DAG."""
        self._tasks.clear()
        self._groups.clear()
        self._todos.clear()
        self._critical_path.clear()
        self._parallel_groups.clear()
        self._render_dag()

    # ── Rendering ──────────────────────────────────────────────────

    def _render_dag(self) -> None:
        """Render the task dependency tree with ASCII art."""
        try:
            tree_widget = self.query_one("#dag-tree", Static)
        except Exception:
            return

        if not self._tasks:
            tree_widget.update(
                Panel(
                    "[dim]Task dependency tree will appear here\n"
                    "once tasks are assigned.[/dim]\n\n"
                    "[dim]The DAG shows task dependencies\n"
                    "and parallel execution groups.[/dim]",
                    title="DAG \u2014 Task Dependency Tree",
                    border_style="dim",
                    padding=(0, 1),
                )
            )
            return

        cp_set = set(self._critical_path) if self._critical_path else set()
        tree = Tree("\U0001f5c2 Task Dependency Tree")

        # If we have parallel groups from DAGResolver, show them
        if self._parallel_groups:
            for level, group_ids in enumerate(self._parallel_groups):
                is_cp_level = any(tid in cp_set for tid in group_ids)
                level_label = f"[bold]Level {level}[/bold] (parallel)"
                if is_cp_level:
                    level_label += " [red bold]*CRITICAL*[/red bold]"
                branch = tree.add(level_label)

                for tid in group_ids:
                    task = self._tasks.get(tid, {})
                    status = task.get("status", "pending")
                    desc = task.get("description", tid)[:50]
                    assigned = task.get("assigned_to", "?")
                    is_cp = tid in cp_set

                    icon = DAG_STATUS_ICONS.get(status, "\u25cb")
                    color = DAG_STATUS_COLORS.get(status, "dim")
                    cp_marker = " [red bold]*[/red bold]" if is_cp else ""

                    branch.add(
                        f"[{color}]{icon}[/{color}] [{assigned}] {desc}{cp_marker}"
                    )

        # Squad-based grouping
        elif self._groups:
            for squad, task_ids in self._groups.items():
                squad_color = SQUAD_COLORS.get(squad, "dim")
                branch = tree.add(f"[{squad_color} bold]\u2588 {squad}[/{squad_color} bold]")

                for i, tid in enumerate(task_ids):
                    task = self._tasks.get(tid, {})
                    desc = task.get("description", tid)[:50]
                    status = task.get("status", "pending")
                    assigned = task.get("assigned_to", "?")
                    is_cp = tid in cp_set

                    icon = DAG_STATUS_ICONS.get(status, "\u25cb")
                    color = DAG_STATUS_COLORS.get(status, "dim")
                    cp_marker = " [red bold]*[/red bold]" if is_cp else ""

                    # Box-drawing chars for hierarchy
                    is_last = (i == len(task_ids) - 1)
                    prefix = "\u2514\u2500" if is_last else "\u251c\u2500"

                    branch.add(
                        f"[dim]{prefix}[/dim] [{color}]{icon}[/{color}] "
                        f"{desc} [dim][{assigned}][/dim]{cp_marker}"
                    )
        else:
            # No grouping — flat list with box-drawing
            for i, (tid, task) in enumerate(self._tasks.items()):
                desc = task.get("description", tid)[:50]
                status = task.get("status", "pending")
                assigned = task.get("assigned_to", "?")
                is_cp = tid in cp_set

                icon = DAG_STATUS_ICONS.get(status, "\u25cb")
                color = DAG_STATUS_COLORS.get(status, "dim")
                cp_marker = " [red bold]*[/red bold]" if is_cp else ""

                is_last = (i == len(self._tasks) - 1)
                prefix = "\u2514\u2500" if is_last else "\u251c\u2500"

                tree.add(
                    f"[dim]{prefix}[/dim] [{color}]{icon}[/{color}] "
                    f"{desc} [dim][{assigned}][/dim]{cp_marker}"
                )

        # Build final display
        parts: list[Any] = [tree]

        # Critical path
        if self._critical_path:
            cp_labels = []
            for tid in self._critical_path[:8]:
                task = self._tasks.get(tid, {})
                label = task.get("description", tid)[:20]
                cp_labels.append(label)
            cp_str = " \u2192 ".join(cp_labels)
            parts.append(Text.from_markup(
                f"\n[bold red]\u26a1 Critical Path:[/bold red] {cp_str}"
            ))

        # Summary
        total = len(self._tasks)
        done = sum(1 for t in self._tasks.values() if t.get("status") in ("done", "completed"))
        failed = sum(1 for t in self._tasks.values() if t.get("status") == "failed")
        in_progress = sum(1 for t in self._tasks.values() if t.get("status") in ("in_progress", "running"))
        parts.append(Text.from_markup(
            f"\n[dim]Tasks: {total} total, {in_progress} running, {done} done, {failed} failed[/dim]"
        ))

        # Legend
        parts.append(Text.from_markup(
            "\n[dim]Legend: \u23f3 pending  \U0001f504 running  \u2705 done  \u274c failed  "
            "[red bold]*[/red bold] critical[/dim]"
        ))

        tree_widget.update(Panel(
            Group(*parts),
            title="DAG \u2014 Task Dependency Tree",
            border_style=KANTORKU_THEME["secondary"],
            padding=(0, 1),
        ))
