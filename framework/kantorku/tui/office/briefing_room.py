"""
BriefingRoomPanel — Center panel showing multi-round worker discussion.

Displays the briefing room conversation where workers discuss the plan
before execution. Shows concerns (🔴), suggestions (🟡), and
agreements (🟢) with collapsible round sections.

Layout:
    ┌──────────────────────────────────────────────────────┐
    │  BRIEFING ROOM — Round 2/3                           │
    │  Workers: architect, coder, verifier                 │
    │  ─────────────────────────────────────────────────── │
    │                                                      │
    │  ▼ Round 1 ─────────────────────────────────────     │
    │  📢 conductor: Briefing for: Build rate limiter      │
    │  🟡 architect: Suggest using token bucket            │
    │  🔴 verifier: Need more test coverage                │
    │  🟢 coder: Agree with token bucket approach          │
    │  📋 Manager Summary: Team prefers token bucket...    │
    │                                                      │
    │  ▼ Round 2 ─────────────────────────────────────     │
    │  🟢 architect: Updated plan looks good               │
    │  🟢 verifier: Test plan is comprehensive             │
    │  📋 Manager Summary: Consensus reached.              │
    │                                                      │
    └──────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Collapsible, Static

from rich.console import Group
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree

from kantorku.tui.themes import (
    KANTORKU_THEME,
    SQUAD_COLORS,
)

# ── CSS ────────────────────────────────────────────────────────────────

_CSS = """
BriefingRoomPanel {
    layout: vertical;
    height: 1fr;
}

#briefing-header {
    height: 2;
    padding: 0 1;
    border-bottom: tall $secondary 30%;
    background: $secondary 8%;
}

#briefing-rounds {
    height: 1fr;
    scrollbar-size: 1 1;
    padding: 0 1;
}
"""


class BriefingRoomPanel(Static):
    """Briefing room panel — shows multi-round worker discussion.

    Displays:
    - Round counter header with participating workers
    - Worker messages with concern (🔴), suggestion (🟡), agreement (🟢) tags
    - Manager summary at end of each round
    - Collapsible discussion rounds

    Messages are organized by rounds, each round being a separate
    collapsible section showing the full discussion thread.
    """

    CSS = _CSS

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._messages: list[dict[str, Any]] = []
        self._current_round: int = 0
        self._max_rounds: int = 3
        self._workers: list[str] = []
        self._is_active: bool = False

    # ── Compose ────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Static(self._render_header(), id="briefing-header")
        with VerticalScroll(id="briefing-rounds"):
            yield Static(id="briefing-rounds-content")

    # ── Public API ─────────────────────────────────────────────────

    def add_event(self, event: dict[str, Any]) -> None:
        """Add a briefing-relevant event."""
        event_type = event.get("type", "")

        briefing_types = {
            "briefing_opened", "worker_speak_up", "manager_brainstorming",
            "plan_drafted", "plan_revised",
        }
        if event_type not in briefing_types:
            return

        self._messages.append(event)
        self._render_rounds()

    def set_round_info(self, current: int, max_rounds: int = 3) -> None:
        """Set the current round counter."""
        self._current_round = current
        self._max_rounds = max_rounds
        self._update_header()

    def set_workers(self, workers: list[str]) -> None:
        """Set the participating workers list."""
        self._workers = list(workers)
        self._update_header()

    def set_active(self, active: bool) -> None:
        """Set whether briefing is currently active."""
        self._is_active = active
        self._update_header()

    def clear(self) -> None:
        """Clear all briefing messages."""
        self._messages.clear()
        self._current_round = 0
        self._is_active = False
        self._render_rounds()

    # ── Rendering ──────────────────────────────────────────────────

    def _render_header(self) -> str:
        """Render the briefing header."""
        if not self._is_active and not self._messages:
            return "[bold magenta]BRIEFING ROOM[/bold magenta]  [dim]No active briefing[/dim]"

        round_str = f"Round {self._current_round}/{self._max_rounds}" if self._current_round > 0 else "Starting..."
        workers_str = ", ".join(self._workers[:5]) if self._workers else ""
        workers_display = f"  [dim]Workers: {workers_str}[/dim]" if workers_str else ""

        return f"[bold magenta]BRIEFING ROOM[/bold magenta]  [cyan]{round_str}[/cyan]{workers_display}"

    def _update_header(self) -> None:
        """Update the header widget."""
        try:
            header = self.query_one("#briefing-header", Static)
            header.update(self._render_header())
        except Exception:
            pass

    def _render_rounds(self) -> None:
        """Render all briefing rounds as collapsible sections."""
        try:
            content = self.query_one("#briefing-rounds-content", Static)
        except Exception:
            return

        if not self._messages:
            content.update(
                Panel(
                    "[dim]Briefing room messages will appear here\n"
                    "when a contract is accepted.[/dim]\n\n"
                    "[dim]Workers discuss the plan before\n"
                    "execution begins. Concerns,\n"
                    "suggestions, and agreements\n"
                    "are all tracked here.[/dim]",
                    border_style="dim",
                    padding=(0, 1),
                )
            )
            return

        # Group messages by round
        rounds: dict[int, list[dict[str, Any]]] = {}
        round_num = 1
        for msg in self._messages:
            event_type = msg.get("type", "")
            # New round starts with briefing_opened from conductor
            if event_type == "briefing_opened" and msg.get("from") == "conductor":
                if rounds:  # Don't increment on the very first one
                    round_num += 1
            if round_num not in rounds:
                rounds[round_num] = []
            rounds[round_num].append(msg)

        # Build rich display
        parts: list[Any] = []

        for r_num, messages in rounds.items():
            # Round header
            parts.append(Text.from_markup(
                f"[bold magenta]\u25bc Round {r_num}[/bold magenta] "
                f"[dim]{'─' * 40}[/dim]"
            ))

            for msg in messages:
                event_type = msg.get("type", "")
                from_id = msg.get("from", "?")
                content_text = msg.get("content", "")

                if event_type == "briefing_opened":
                    icon = "\U0001f4e2"  # 📢
                    parts.append(Text.from_markup(
                        f"  [bold magenta]{icon} {from_id}:[/bold magenta] {content_text[:120]}"
                    ))

                elif event_type == "worker_speak_up":
                    # Determine tag: concern, suggestion, or agreement
                    tag = msg.get("tag", "")
                    concern = msg.get("concern", "")
                    suggestion = msg.get("suggestion", "")
                    agreement = msg.get("agreement", "")

                    if concern:
                        tag_icon = "\U0001f534"  # 🔴 concern
                        display_text = concern
                    elif suggestion:
                        tag_icon = "\U0001f7e1"  # 🟡 suggestion
                        display_text = suggestion
                    elif agreement:
                        tag_icon = "\U0001f7e2"  # 🟢 agreement
                        display_text = agreement
                    else:
                        tag_icon = "\U0001f4ac"  # 💬 general
                        display_text = content_text

                    squad_color = SQUAD_COLORS.get(from_id, "white")
                    parts.append(Text.from_markup(
                        f"  {tag_icon} [{squad_color}]{from_id}:[/{squad_color}] {display_text[:120]}"
                    ))

                elif event_type == "manager_brainstorming":
                    parts.append(Text.from_markup(
                        "  [bold cyan]\U0001f4ad Manager brainstorming with workers...[/bold cyan]"
                    ))

                elif event_type == "plan_drafted":
                    parts.append(Text.from_markup(
                        "  [bold blue]\U0001f4cb Plan drafted for team review[/bold blue]"
                    ))

                elif event_type == "plan_revised":
                    reason = msg.get("reason", "")
                    parts.append(Text.from_markup(
                        f"  [yellow]\U0001f4cb Plan revised: {reason[:80]}[/yellow]"
                    ))

            # Manager summary placeholder at end of round
            parts.append(Text.from_markup(
                f"  [bold cyan]\U0001f4cb Manager Summary:[/bold cyan] [dim]Round {r_num} complete[/dim]"
            ))
            parts.append(Text.from_markup(""))  # Spacing

        content.update(Group(*parts))

        # Auto-scroll
        try:
            scroll = self.query_one("#briefing-rounds", VerticalScroll)
            scroll.scroll_end(animate=False)
        except Exception:
            pass
