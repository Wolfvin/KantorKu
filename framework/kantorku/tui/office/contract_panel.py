"""
ContractPanel — Right panel showing 13-state contract progress display.

Displays the full contract lifecycle with:
- 13-state contract progress display with visual indicator
- Team feedback tree showing worker concerns/suggestions
- TODO list with assignee and status
- Accept/Revise buttons
- Revision counter
- Quality score display

Layout:
    ┌──────────────────────────────────────────────────────┐
    │  CONTRACT [◈ CONTRACT PRESENTED]                     │
    │  ─────────────────────────────────────────────────── │
    │                                                      │
    │  Build Rate Limiter                                  │
    │  Implement a token bucket rate limiter...            │
    │                                                      │
    │  📋 Contract                                         │
    │  📝 Tasks (3)                                        │
    │  ├─ ○ [coder] Implement rate limiter core            │
    │  ├─ ○ [architect] Design token bucket                │
    │  └─ ○ [verifier] Write tests                         │
    │  Progress: [████████░░░░░░░░░░░░] 40% (1/3)         │
    │                                                      │
    │  💬 Team Feedback (1 round)                          │
    │  ├─ Round 1: 2 concern(s)                            │
    │  └─ ✓ architect: Use token bucket                   │
    │                                                      │
    │  Quality: ████████░░ 78%                             │
    │  Revision: #2                                        │
    │                                                      │
    │  ▸ Click [ACCEPT] or type 'yes'/'ok'                 │
    │  ▸ Click [REVISE] or type your feedback              │
    │                                                      │
    │  [✓ ACCEPT]  [✏ REVISE]                              │
    └──────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, Static

from rich.console import Group
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree

from kantorku.tui.themes import (
    CONTRACT_STATE_COLORS,
    KANTORKU_THEME,
    SQUAD_COLORS,
    STATUS_ICONS,
    STATUS_COLORS,
)

# ── 13-State Contract States ──────────────────────────────────────────

CONTRACT_STATES = [
    "idle",
    "manager_thinking",
    "clarifying",
    "contract_presented",
    "awaiting_revision",
    "team_review",
    "todo_review",
    "client_feedback",
    "working",
    "verifying",
    "accepted",
    "done",
    "failed",
]

# ── State icons (coder-style, no emoji) ───────────────────────────────

STATE_ICONS = {
    "idle": "\u25cb",              # ○
    "manager_thinking": "\u25d0",  # ◐
    "clarifying": "\u25c7",        # ◇
    "contract_presented": "\u25c8",# ◈
    "awaiting_revision": "\u270f", # ✏
    "team_review": "\u253c",       # ┼
    "todo_review": "\u253c",       # ┼
    "client_feedback": "\u21bb",   # ↻
    "working": "\u26a1",           # ⚡
    "verifying": "\u25c7",         # ◇
    "accepted": "\u2713",          # ✓
    "done": "\u2713",              # ✓
    "failed": "\u2717",            # ✗
}

STATE_LABELS = {
    "contract_presented": "CONTRACT PRESENTED",
    "awaiting_revision": "AWAITING YOUR REVISION",
    "accepted": "CONTRACT ACCEPTED",
    "team_review": "TEAM REVIEW",
    "todo_review": "TODO REVIEW",
    "client_feedback": "CLIENT FEEDBACK",
}

# ── CSS ────────────────────────────────────────────────────────────────

_CSS = """
ContractPanel {
    layout: vertical;
    height: 1fr;
}

#contract-scroll {
    height: 1fr;
    scrollbar-size: 1 1;
    padding: 0 1;
}

#contract-actions {
    dock: bottom;
    height: auto;
    padding: 0 1;
    background: $surface;
    border-top: tall $accent 20%;
    layout: horizontal;
    gap: 1;
}

#contract-accept-btn {
    background: $success 15%;
    color: $success;
    text-style: bold;
    border: tall $success;
}

#contract-accept-btn:hover {
    background: $success 30%;
}

#contract-accept-btn:disabled {
    background: $surface;
    color: $muted;
    text-style: not bold;
    border: tall $surface;
}

#contract-revise-btn {
    background: $warning 15%;
    color: $warning;
    text-style: bold;
    border: tall $warning;
}

#contract-revise-btn:hover {
    background: $warning 30%;
}

#contract-revise-btn:disabled {
    background: $surface;
    color: $muted;
    text-style: not bold;
    border: tall $surface;
}
"""


class ContractPanel(Static):
    """Right panel — shows current contract with 13-state progress display.

    Features:
    - 13-state contract progress display with visual indicator
    - Team feedback tree showing worker concerns/suggestions
    - TODO list with assignee and status
    - Accept/Revise buttons
    - Revision counter
    - Quality score display

    Messages:
        AcceptRequested: Emitted when Accept button is clicked
        ReviseRequested: Emitted when Revise button is clicked
    """

    CSS = _CSS

    # ── Messages ───────────────────────────────────────────────────

    class AcceptRequested(Message):
        """Posted when the Accept button is clicked."""
        pass

    class ReviseRequested(Message):
        """Posted when the Revise button is clicked."""
        pass

    # ── Reactives ──────────────────────────────────────────────────

    contract_data: reactive[dict[str, Any]] = reactive({})
    contract_state: reactive[str] = reactive("idle")
    work_result: reactive[dict[str, Any]] = reactive({})
    revision_count: reactive[int] = reactive(0)
    quality_score: reactive[float] = reactive(0.0)

    # ── Init ───────────────────────────────────────────────────────

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    # ── Compose ────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="contract-scroll"):
            yield Static(id="contract-content")
        with Horizontal(id="contract-actions"):
            yield Button("\u2713 Accept", id="contract-accept-btn")
            yield Button("\u270f Revise", id="contract-revise-btn")

    # ── Lifecycle ──────────────────────────────────────────────────

    def on_mount(self) -> None:
        """Initialize display."""
        self._refresh_display()

    # ── Reactive Watchers ──────────────────────────────────────────

    def watch_contract_data(self, data: dict[str, Any]) -> None:
        self._refresh_display()

    def watch_contract_state(self, state: str) -> None:
        self._refresh_display()
        self._update_action_buttons()

    def watch_work_result(self, data: dict[str, Any]) -> None:
        self._refresh_display()

    def watch_revision_count(self, count: int) -> None:
        self._refresh_display()

    def watch_quality_score(self, score: float) -> None:
        self._refresh_display()

    # ── Event Handlers ─────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle Accept/Revise button clicks."""
        btn_id = event.button.id or ""
        if btn_id == "contract-accept-btn":
            self.post_message(self.AcceptRequested())
        elif btn_id == "contract-revise-btn":
            self.post_message(self.ReviseRequested())

    # ── Internal ───────────────────────────────────────────────────

    def _update_action_buttons(self) -> None:
        """Enable/disable action buttons based on contract state."""
        state = self.contract_state
        try:
            accept_btn = self.query_one("#contract-accept-btn", Button)
            revise_btn = self.query_one("#contract-revise-btn", Button)

            can_accept = state in ("contract_presented", "awaiting_revision")
            can_revise = state in ("contract_presented", "awaiting_revision")

            accept_btn.disabled = not can_accept
            revise_btn.disabled = not can_revise
        except Exception:
            pass

    def _refresh_display(self) -> None:
        """Refresh the entire contract display."""
        try:
            content = self.query_one("#contract-content", Static)
        except Exception:
            return

        parts: list[Any] = []

        # ── Header with state ──
        state = self.contract_state
        state_color = CONTRACT_STATE_COLORS.get(state, "dim")
        state_icon = STATE_ICONS.get(state, "\u2753")
        state_label = STATE_LABELS.get(state, state.upper())

        parts.append(Text.from_markup(
            f"[{state_color} bold]{state_icon} {state_label}[/{state_color} bold]"
        ))

        # ── Progress indicator ──
        if state != "idle":
            # Show progress through the 13 states
            try:
                current_idx = CONTRACT_STATES.index(state)
            except ValueError:
                current_idx = 0

            total_states = len(CONTRACT_STATES)
            bar_len = 20
            filled = int(bar_len * current_idx / total_states) if total_states > 0 else 0
            filled = max(0, min(filled, bar_len))
            bar = "\u2588" * filled + "\u2591" * (bar_len - filled)
            pct = int(100 * current_idx / total_states) if total_states > 0 else 0
            parts.append(Text.from_markup(
                f"[dim]Progress: [{bar}] {pct}% ({current_idx}/{total_states})[/dim]"
            ))

        # ── Revision count badge ──
        if self.revision_count > 0 and state in (
            "contract_presented", "awaiting_revision", "accepted", "working"
        ):
            parts.append(Text.from_markup(
                f"[dim]Revision #{self.revision_count}[/dim]"
            ))

        # ── Contract details ──
        data = self.contract_data
        if data:
            parts.append(Text.from_markup(""))
            title = data.get("title", "Untitled")
            description = data.get("description", "")
            parts.append(Text.from_markup(f"[bold cyan]{title}[/bold cyan]"))
            if description:
                parts.append(Text.from_markup(f"[dim]{description[:200]}[/dim]"))

            # Rich Tree for collapsible sections
            tree = Tree("\U0001f4cb Contract", guide_style="dim")
            tree.expanded = True

            # ── Tasks Branch ──
            todos = data.get("todos", [])
            if todos:
                tasks_branch = tree.add(
                    f"\U0001f4dd Tasks ({len(todos)})", style="bold cyan"
                )
                for todo in todos:
                    desc = todo.get("description", "")
                    assigned = todo.get("assigned_to", "unassigned")
                    status = todo.get("status", "pending")
                    icon = STATUS_ICONS.get(status, "\u25cb")
                    color = STATUS_COLORS.get(status, "dim")
                    squad = todo.get("squad", "")
                    squad_str = (
                        f" [{SQUAD_COLORS.get(squad, 'dim')}]{squad}[/]"
                        if squad else ""
                    )
                    depends = todo.get("depends_on", [])
                    dep_str = (
                        f" [dim](depends: {','.join(str(d) for d in depends[:3])})[/dim]"
                        if depends else ""
                    )
                    tasks_branch.add(
                        f"[{color}]{icon}[/{color}] [{assigned}]{squad_str} "
                        f"{desc[:50]}{dep_str}"
                    )

                # Progress bar
                done_count = sum(1 for t in todos if t.get("status") == "done")
                total = len(todos)
                pct = int((done_count / total) * 100) if total > 0 else 0
                bar_len = 20
                filled = (
                    min(int(bar_len * done_count / total), bar_len)
                    if total > 0 else 0
                )
                filled = max(filled, 0)
                bar = "\u2588" * filled + "\u2591" * (bar_len - filled)
                tasks_branch.add(
                    f"[bold]Progress:[/bold] [{bar}] {pct}% ({done_count}/{total})"
                )

            # ── Team Feedback Branch ──
            team_feedback = data.get("team_feedback_rounds", [])
            if team_feedback:
                feedback_branch = tree.add(
                    f"\U0001f4ac Team Feedback ({len(team_feedback)} round(s))",
                    style="bold magenta",
                )
                for i, round_data in enumerate(team_feedback[-3:]):
                    concerns = round_data.get("concerns", [])
                    decisions = round_data.get("decisions", [])
                    round_branch = feedback_branch.add(
                        f"Round {i+1}: "
                        f"[yellow]{len(concerns)} concern(s)[/yellow]"
                    )
                    if concerns:
                        for c in concerns[:3]:
                            worker_id = c.get("worker_id", "?")
                            concern_text = c.get("concern", c.get("response", ""))
                            squad_color = SQUAD_COLORS.get(worker_id, "white")
                            round_branch.add(
                                f"\U0001f534 [{squad_color}]{worker_id}[/{squad_color}]: "
                                f"{concern_text[:50]}"
                            )
                    if decisions:
                        for d in decisions[:2]:
                            round_branch.add(f"\U0001f7e2 {d[:40]}")

            # ── Result Branch ──
            result = self.work_result
            if result:
                result_branch = tree.add(
                    "\U0001f4ca Result", style="bold green"
                )
                results_data = result.get("results", {})
                if results_data:
                    for tid, r in list(results_data.items())[:5]:
                        rstatus = r.get("status", "?")
                        output = r.get("output", "")[:100]
                        sc = "green" if rstatus == "done" else "red"
                        result_branch.add(f"[{sc}]{rstatus}[/{sc}] {output}")

            parts.append(tree)

            # ── Quality Score ──
            if self.quality_score > 0:
                qs = self.quality_score
                qs_color = "green" if qs > 0.7 else ("yellow" if qs > 0.4 else "red")
                bar_len = 10
                filled = int(bar_len * qs)
                bar = "\u2588" * filled + "\u2591" * (bar_len - filled)
                parts.append(Text.from_markup(
                    f"\n[bold]Quality:[/bold] [{qs_color}]{bar}[/{qs_color}] {qs:.0%}"
                ))

        else:
            parts.append(Text.from_markup(
                "\n[dim]No active contract yet.[/dim]\n\n"
                "[dim]Chat with the Manager in\n"
                "the left panel to start.[/dim]\n\n"
                "[dim]Just type what you need\n"
                "and press Enter.[/dim]"
            ))

        # ── Work result (top level if no tree) ──
        result = self.work_result
        if result and not data:
            parts.append(Text.from_markup(
                "\n[bold green]\u2501\u2501\u2501 Result \u2501\u2501\u2501[/bold green]"
            ))
            results_data = result.get("results", {})
            if results_data:
                for tid, r in list(results_data.items())[:5]:
                    status = r.get("status", "?")
                    output = r.get("output", "")[:100]
                    sc = "green" if status == "done" else "red"
                    parts.append(Text.from_markup(
                        f"  [{sc}]{status}[/{sc}] {output}"
                    ))

        # ── State-specific action instructions ──
        parts.append(Text.from_markup(""))
        if state == "contract_presented":
            parts.append(Text.from_markup(
                "[bold green]\u25b8 Click [ACCEPT] below or type 'yes'/'ok'[/bold green]\n"
                "[bold yellow]\u25b8 Click [REVISE] below or type your feedback[/bold yellow]"
            ))
        elif state == "awaiting_revision":
            parts.append(Text.from_markup(
                "[bold yellow]\u25b8 Write your revision feedback below...[/bold yellow]\n"
                "[dim]The Manager will brainstorm with workers and present a new contract[/dim]"
            ))
        elif state == "accepted":
            parts.append(Text.from_markup(
                "[bold green]\u2501\u2501\u2501 CONTRACT ACCEPTED \u2501\u2501\u2501[/bold green]\n"
                "[dim]Workers are now executing the tasks...[/dim]"
            ))
        elif state == "working":
            parts.append(Text.from_markup(
                "[bold green]\u25b8 Workers are executing...[/bold green]\n"
                "[bold yellow]\u25b8 Click [DISRUPT] or type 'stop' to pause[/bold yellow]"
            ))
        elif state in ("team_review", "todo_review"):
            parts.append(Text.from_markup(
                "[bold magenta]\u25b8 Team is reviewing the plan...[/bold magenta]"
            ))
        elif state == "done":
            parts.append(Text.from_markup(
                "[bold green]\u25b8 Work complete! Type a new task to start.[/bold green]"
            ))

        border_color = {
            "idle": "dim",
            "contract_presented": "cyan",
            "awaiting_revision": "yellow",
            "working": "green",
            "accepted": "green",
            "done": "green",
            "failed": "red",
        }.get(state, "yellow")

        content.update(Panel(
            Group(*parts),
            title="Contract",
            border_style=border_color,
            padding=(0, 1),
        ))
