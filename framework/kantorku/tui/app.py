"""
KantorKu TUI App — 3-Panel Chat-Driven Office Interface.

The central TUI for coders, providing a natural office workflow:
- Left Panel:   Chat with the Manager (Conductor) + Disrupt button
- Center Panel: Workers brainstorming & executing live
- Right Panel:  Contract display + Accept/Revise BUTTONS

Primary interaction is CHAT — type naturally, Manager handles the rest.
Slash commands still work as secondary tools — type /help for list.

Contract Flow:
    When a contract is presented in the RIGHT panel:
      - Click ACCEPT → Contract is finalized and displayed as ACCEPTED
      - Click REVISE → Enter revision mode: write feedback →
        Manager brainstorms with workers → new contract presented
      - Or type naturally: "yes"/"ok"/"accept" → Accept
                           "revise"/"change X" → Revise with feedback

Supports two modes:
1. Remote: Connect to a running kantorku server via WebSocket
2. Embedded: Run the Office directly in-process (no server needed)
"""

from __future__ import annotations

import asyncio
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    RichLog,
    Static,
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
    CONTRACT_STATE_COLORS,
    PANEL_STATE_ICONS,
    WORKERS_PHASE_STYLES,
)
from kantorku.tui.markdown_renderer import (
    render_markdown,
    render_code,
    render_contract_summary,
    render_task_result,
)
from kantorku.tui.commands import handle_slash_command


# ── Natural Language Action Parser ──────────────────────────────────

# Patterns that map to contract actions
ACCEPT_PATTERNS = re.compile(
    r"^(yes|yeah|yep|ok|okay|accept|approve|go ahead|go for it|do it|"
    r"let'?s go|sure|sounds good|perfect|lg|lfg|ship it|"
    r"looks good|agree|confirmed|confirm|proceed|execute)\s*[!.!]*$",
    re.IGNORECASE,
)

REVISE_PATTERNS = re.compile(
    r"^(no|nope|nah|revise|change|modify|update|alter|redo|reject|deny|"
    r"not quite|not really|i want|i need|i prefer|instead|"
    r"could you|can you|please change|please update|but)\b",
    re.IGNORECASE,
)

INTERRUPT_PATTERNS = re.compile(
    r"^(stop|halt|pause|wait|hold on|hold up|interrupt|disrupt|break|cancel)\b",
    re.IGNORECASE,
)


def parse_nl_action(text: str, contract_state: str) -> str | None:
    """
    Parse natural language input to detect contract actions.

    Returns:
        "accept" if user wants to accept the contract
        "revise" if user wants to revise the contract (remaining text = feedback)
        "interrupt" if user wants to interrupt work
        None if no action detected (regular chat message)
    """
    stripped = text.strip()
    if not stripped:
        return None

    # Only parse actions when relevant
    if contract_state in ("contract_presented", "awaiting_revision"):
        if ACCEPT_PATTERNS.match(stripped):
            return "accept"
        if REVISE_PATTERNS.match(stripped):
            return "revise"

    if contract_state == "working":
        if INTERRUPT_PATTERNS.match(stripped):
            return "interrupt"

    return None


# ── Widget Classes ──────────────────────────────────────────────────


class ContractDisplay(Static):
    """Right panel — shows current contract with Accept/Revise BUTTONS.

    States:
        idle               — No contract yet
        manager_thinking   — Manager is processing
        clarifying         — Manager asking questions
        contract_presented — Contract shown, Accept/Revise visible
        awaiting_revision  — User clicked Revise, writing feedback
        team_review        — Team reviewing the plan
        todo_review        — Team reviewing tasks
        client_feedback    — Client (user) giving feedback
        working            — Contract accepted, workers executing
        verifying          — Workers verifying results
        accepted           — Contract finalized (accepted by user)
        done               — Work complete
        failed             — Work failed
    """

    contract_data: reactive[dict[str, Any]] = reactive({})
    contract_state: reactive[str] = reactive("idle")
    work_result: reactive[dict[str, Any]] = reactive({})
    revision_count: reactive[int] = reactive(0)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    def watch_contract_data(self, data: dict[str, Any]) -> None:
        self._render()

    def watch_contract_state(self, state: str) -> None:
        self._render()

    def watch_work_result(self, data: dict[str, Any]) -> None:
        self._render()

    def watch_revision_count(self, count: int) -> None:
        self._render()

    def _render(self) -> None:
        parts: list[Any] = []

        # Header with state
        state = self.contract_state
        state_color = CONTRACT_STATE_COLORS.get(state, "dim")
        state_icon = {
            "idle": "\U0001f4a4",
            "manager_thinking": "\U0001f914",
            "clarifying": "\U0001f4ac",
            "contract_presented": "\U0001f4cb",
            "awaiting_revision": "\u270f\ufe0f",
            "team_review": "\U0001f465",
            "todo_review": "\U0001f4dd",
            "client_feedback": "\U0001f504",
            "working": "\u26a1",
            "verifying": "\U0001f50d",
            "accepted": "\u2705",
            "done": "\u2705",
            "failed": "\u274c",
        }.get(state, "\u2753")

        state_labels = {
            "contract_presented": "CONTRACT PRESENTED",
            "awaiting_revision": "AWAITING YOUR REVISION",
            "accepted": "CONTRACT ACCEPTED",
        }
        state_label = state_labels.get(state, state.upper())

        parts.append(Text.from_markup(
            f"[{state_color} bold]{state_icon} {state_label}[/{state_color} bold]"
        ))

        # Revision count badge
        if self.revision_count > 0 and state in ("contract_presented", "awaiting_revision", "accepted", "working"):
            parts.append(Text.from_markup(
                f"[dim]Revision #{self.revision_count}[/dim]"
            ))

        # Contract details
        data = self.contract_data
        if data:
            parts.append(Text.from_markup(""))
            title = data.get("title", "Untitled")
            description = data.get("description", "")
            parts.append(Text.from_markup(f"[bold cyan]{title}[/bold cyan]"))
            if description:
                parts.append(Text.from_markup(f"[dim]{description[:200]}[/dim]"))

            # Todos
            todos = data.get("todos", [])
            if todos:
                parts.append(Text.from_markup(f"\n[bold]Tasks ({len(todos)}):[/bold]"))
                for todo in todos:
                    desc = todo.get("description", "")
                    assigned = todo.get("assigned_to", "unassigned")
                    status = todo.get("status", "pending")
                    icon = STATUS_ICONS.get(status, "\u25cb")
                    color = STATUS_COLORS.get(status, "dim")
                    squad = todo.get("squad", "")
                    squad_str = f" [{SQUAD_COLORS.get(squad, 'dim')}]{squad}[/]" if squad else ""
                    parts.append(Text.from_markup(
                        f"  [{color}]{icon}[/{color}] [{assigned}]{squad_str} {desc[:50]}"
                    ))

                # Progress bar
                done = sum(1 for t in todos if t.get("status") == "done")
                total = len(todos)
                pct = int((done / total) * 100) if total > 0 else 0
                bar_len = 20
                filled = min(int(bar_len * done / total), bar_len) if total > 0 else 0
                filled = max(filled, 0)  # Guard against negative
                bar = "\u2588" * filled + "\u2591" * (bar_len - filled)
                parts.append(Text.from_markup(
                    f"\n[bold]Progress:[/bold] [{bar}] {pct}% ({done}/{total})"
                ))

            # Team feedback
            team_feedback = data.get("team_feedback_rounds", [])
            if team_feedback:
                parts.append(Text.from_markup(
                    f"\n[bold magenta]Team Feedback:[/bold magenta] {len(team_feedback)} round(s)"
                ))
                for i, round_data in enumerate(team_feedback[-2:]):
                    concerns = round_data.get("concerns", [])
                    decisions = round_data.get("decisions", [])
                    if concerns:
                        parts.append(Text.from_markup(
                            f"  Round {i+1}: [yellow]{len(concerns)} concern(s)[/yellow]"
                        ))
                    if decisions:
                        for d in decisions[:2]:
                            parts.append(Text.from_markup(f"  [green]\u2713 {d[:40]}[/green]"))

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
                    f"[bold magenta]\u25b8 Team is reviewing the plan...[/bold magenta]"
                ))
            elif state == "done":
                parts.append(Text.from_markup(
                    "[bold green]\u25b8 Work complete! Type a new task to start.[/bold green]"
                ))
        else:
            parts.append(Text.from_markup(
                "\n[dim]No active contract yet.[/dim]\n\n"
                "[dim]Chat with the Manager in\n"
                "the left panel to start.[/dim]\n\n"
                "[dim]Just type what you need\n"
                "and press Enter.[/dim]"
            ))

        # Work result
        result = self.work_result
        if result:
            parts.append(Text.from_markup("\n[bold green]\u2501\u2501\u2501 Result \u2501\u2501\u2501[/bold green]"))
            results_data = result.get("results", {})
            if results_data:
                for tid, r in list(results_data.items())[:5]:
                    status = r.get("status", "?")
                    output = r.get("output", "")[:100]
                    sc = "green" if status == "done" else "red"
                    parts.append(Text.from_markup(
                        f"  [{sc}]{status}[/{sc}] {output}"
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

        self.update(Panel(
            Group(*parts),
            title="Contract",
            border_style=border_color,
            padding=(0, 1),
        ))


class WorkersLiveStream(Static):
    """Center panel — live stream of worker activity.

    Shows:
    - Briefing room discussions
    - Worker speak_up / concerns / suggestions
    - Task assignment & execution
    - Worker DMs and broadcasts
    - LLM streaming chunks
    - Context prefetch status
    - Verification progress
    - Checkpoint / recovery events
    - Circuit breaker events
    - Worker lifecycle (hire/fire)
    - Cost warnings
    - Delegation
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._entries: list[dict[str, Any]] = []
        self._max_entries = 500  # Memory buffer; visible display shows last 50
        self._round: int = 0
        self._phase: str = ""  # idle, briefing, execution, verification, done

        # Render throttle (20fps max)
        self._last_render_time: float = 0.0
        self._dirty: bool = False
        self._pending_render: Any = None
        self._render_cooldown: float = 0.05

    def add_event(self, event: dict[str, Any]) -> None:
        """Add an office event to the live stream."""
        event_type = event.get("type", "")

        # Show ALL relevant worker events in center panel
        relevant_types = {
            "briefing_opened", "plan_drafted", "plan_revised",
            "worker_speak_up", "worker_dm", "worker_broadcast",
            "task_assigned", "task_started", "task_done", "task_failed",
            "context_fetch_start", "context_fetch_done",
            "verify_design_start", "verify_design_done",
            "verify_engineer_start", "verify_engineer_done",
            "error_logged", "skill_updated",
            "llm_stream_start", "llm_stream_chunk", "llm_stream_done",
            "contract_accepted",
            "delegation_request", "delegation_result",
            # v0.6.0 additions
            "checkpoint_saved", "crash_recovered",
            "circuit_open", "circuit_closed",
            "rate_limit_hit", "cost_warning",
            "worker_hired", "worker_fired",
            "task_recovered", "task_timeout",
            "middleware_before", "middleware_after",
            # v0.7.0 — revision brainstorming
            "revision_requested", "manager_brainstorming",
            # v0.8.0 — work completion
            "work_done",
        }

        if event_type not in relevant_types:
            return

        self._entries.append(event)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]
        self._schedule_render()

    def add_system_message(self, message: str, style: str = "dim") -> None:
        """Add a system/phase message to the stream."""
        self._entries.append({
            "type": "system",
            "content": message,
            "style": style,
        })
        self._schedule_render()

    def clear(self) -> None:
        self._entries.clear()
        self._render_stream()

    def _schedule_render(self) -> None:
        """Throttled render — max 20fps."""
        import time
        now = time.monotonic()
        if now - self._last_render_time >= self._render_cooldown:
            self._render_stream()
            self._last_render_time = now
        else:
            self._dirty = True
            if self._pending_render is None:
                self._pending_render = self.set_timer(
                    self._render_cooldown, self._flush_pending_render
                )

    def _flush_pending_render(self) -> None:
        """Flush a dirty render after the cooldown."""
        import time
        self._pending_render = None
        if self._dirty:
            self._dirty = False
            self._render_stream()
            self._last_render_time = time.monotonic()

    def _render_stream(self) -> None:
        if not self._entries:
            self.update(Panel(
                "[dim]Workers will appear here once a contract is accepted.[/dim]\n\n"
                "[dim]You'll see:\n"
                "  \u2022 Briefing room discussion\n"
                "  \u2022 Task assignments & execution\n"
                "  \u2022 Worker DMs and concerns\n"
                "  \u2022 LLM streaming output\n"
                "  \u2022 Verification results[/dim]",
                title="Workers Live",
                border_style="dim",
                padding=(0, 1),
            ))
            return

        parts: list[Any] = []

        # Phase indicator
        if self._phase:
            phase_style = WORKERS_PHASE_STYLES.get(
                self._phase, ("dim", self._phase.upper())
            )
            pc, pi = phase_style
            parts.append(Text.from_markup(f"[{pc}]{pi}[/{pc}]\n"))

        visible = self._entries[-50:]  # Show last 50 entries

        for e in visible:
            event_type = e.get("type", "")

            if event_type == "system":
                style = e.get("style", "dim")
                parts.append(Text.from_markup(f"[{style}]{e.get('content', '')}[/{style}]"))
                continue

            if event_type == "briefing_opened":
                from_id = e.get("from", "conductor")
                content = e.get("content", "")
                parts.append(Text.from_markup(
                    f"  [bold magenta]\U0001f4e2 {from_id}:[/bold magenta] {content[:80]}"
                ))

            elif event_type == "plan_drafted":
                parts.append(Text.from_markup(
                    "  [bold blue]\U0001f4cb Plan drafted for team review[/bold blue]"
                ))

            elif event_type == "plan_revised":
                reason = e.get("reason", "")
                parts.append(Text.from_markup(
                    f"  [yellow]\U0001f4cb Plan revised: {reason[:60]}[/yellow]"
                ))

            elif event_type == "revision_requested":
                feedback = e.get("feedback", "")
                parts.append(Text.from_markup(
                    f"  [yellow bold]\u270f\ufe0f Revision requested: {feedback[:60]}[/yellow bold]"
                ))

            elif event_type == "manager_brainstorming":
                parts.append(Text.from_markup(
                    "  [bold cyan]\U0001f4ad Manager brainstorming with workers...[/bold cyan]"
                ))

            elif event_type == "worker_speak_up":
                from_id = e.get("from", "?")
                content = e.get("content", "")
                parts.append(Text.from_markup(
                    f"  [magenta]\U0001f4ac {from_id}:[/magenta] {content[:100]}"
                ))

            elif event_type == "worker_dm":
                from_id = e.get("from", "?")
                to_id = e.get("to", "?")
                content = e.get("content", "")
                parts.append(Text.from_markup(
                    f"  [dim]\u2709 {from_id} \u2192 {to_id}: {content[:80]}[/dim]"
                ))

            elif event_type == "worker_broadcast":
                from_id = e.get("from", "?")
                content = e.get("content", "")
                parts.append(Text.from_markup(
                    f"  [cyan]\U0001f4e2 {from_id}: {content[:80]}[/cyan]"
                ))

            elif event_type == "task_assigned":
                to_id = e.get("to", "?")
                content = e.get("content", "")
                parts.append(Text.from_markup(
                    f"  [cyan]\u27a1 {to_id}: {content[:70]}[/cyan]"
                ))

            elif event_type == "task_started":
                from_id = e.get("from", "?")
                parts.append(Text.from_markup(
                    f"  [yellow]\u25d0 {from_id} started working...[/yellow]"
                ))

            elif event_type == "task_done":
                from_id = e.get("from", "?")
                files = e.get("files", [])
                files_str = f" \u2192 {', '.join(files[:3])}" if files else ""
                parts.append(Text.from_markup(
                    f"  [green]\u2713 {from_id} done{files_str}[/green]"
                ))

            elif event_type == "task_failed":
                from_id = e.get("from", "?")
                error = e.get("error", "")
                parts.append(Text.from_markup(
                    f"  [red bold]\u2717 {from_id} failed: {error[:60]}[/red bold]"
                ))

            elif event_type == "task_recovered":
                from_id = e.get("from", "?")
                parts.append(Text.from_markup(
                    f"  [green]\u21bb {from_id} recovered[/green]"
                ))

            elif event_type == "task_timeout":
                from_id = e.get("from", "?")
                parts.append(Text.from_markup(
                    f"  [red]\u23f1 {from_id} timed out[/red]"
                ))

            elif event_type in ("context_fetch_start", "context_fetch_done"):
                instance = e.get("instance", "?")
                query = e.get("query", "")[:40]
                if event_type == "context_fetch_start":
                    parts.append(Text.from_markup(
                        f"  [dim]\U0001f50d Pool-{instance}: fetching \"{query}\"[/dim]"
                    ))
                else:
                    parts.append(Text.from_markup(
                        f"  [dim]\u2713 Pool-{instance}: fetched[/dim]"
                    ))

            elif event_type == "verify_design_start":
                parts.append(Text.from_markup(
                    "  [magenta]\U0001f50d Design verification starting...[/magenta]"
                ))

            elif event_type == "verify_design_done":
                approved = e.get("approved", True)
                issues = e.get("issues", [])
                icon = "\u2713" if approved else "\u2717"
                color = "green" if approved else "red"
                parts.append(Text.from_markup(
                    f"  [{color}]{icon} Design review: {len(issues)} issue(s)[/{color}]"
                ))

            elif event_type == "verify_engineer_start":
                parts.append(Text.from_markup(
                    "  [magenta]\U0001f50d Engineering verification starting...[/magenta]"
                ))

            elif event_type == "verify_engineer_done":
                approved = e.get("approved", True)
                issues = e.get("issues", [])
                icon = "\u2713" if approved else "\u2717"
                color = "green" if approved else "red"
                parts.append(Text.from_markup(
                    f"  [{color}]{icon} Engineering review: {len(issues)} issue(s)[/{color}]"
                ))

            elif event_type == "error_logged":
                lesson = e.get("lesson", "")
                parts.append(Text.from_markup(
                    f"  [red]\u26a0 Error: {lesson[:80]}[/red]"
                ))

            elif event_type == "skill_updated":
                worker = e.get("worker", "?")
                lesson = e.get("lesson", "")
                parts.append(Text.from_markup(
                    f"  [cyan]\U0001f4da {worker} learned: {lesson[:60]}[/cyan]"
                ))

            elif event_type == "llm_stream_start":
                from_id = e.get("from", "?")
                model = e.get("model", "")
                parts.append(Text.from_markup(
                    f"  [dim]\u25d0 {from_id} thinking ({model})...[/dim]"
                ))

            elif event_type == "llm_stream_chunk":
                chunk = e.get("chunk", "")
                if chunk:
                    parts.append(Text.from_markup(f"  [dim]{chunk}[/dim]"))

            elif event_type == "llm_stream_done":
                from_id = e.get("from", "?")
                parts.append(Text.from_markup(
                    f"  [dim]\u2713 {from_id} stream complete[/dim]"
                ))

            elif event_type == "contract_accepted":
                parts.append(Text.from_markup(
                    "  [bold green]\u2713 Contract accepted \u2014 work begins![/bold green]"
                ))

            elif event_type == "delegation_request":
                parts.append(Text.from_markup(
                    f"  [cyan]\u2197 Delegation: {e.get('content', '')[:60]}[/cyan]"
                ))

            elif event_type == "delegation_result":
                parts.append(Text.from_markup(
                    f"  [cyan]\u2199 Delegation result: {e.get('content', '')[:60]}[/cyan]"
                ))

            elif event_type == "checkpoint_saved":
                parts.append(Text.from_markup(
                    f"  [green]\U0001f4be Checkpoint saved[/green]"
                ))

            elif event_type == "crash_recovered":
                parts.append(Text.from_markup(
                    f"  [yellow bold]\U0001f504 Crash recovered[/yellow bold]"
                ))

            elif event_type == "circuit_open":
                provider = e.get("provider", "?")
                parts.append(Text.from_markup(
                    f"  [red bold]\u26a1 Circuit OPEN: {provider}[/red bold]"
                ))

            elif event_type == "circuit_closed":
                provider = e.get("provider", "?")
                parts.append(Text.from_markup(
                    f"  [green]\u2713 Circuit closed: {provider}[/green]"
                ))

            elif event_type == "rate_limit_hit":
                provider = e.get("provider", "?")
                parts.append(Text.from_markup(
                    f"  [yellow]\u23f0 Rate limit: {provider}[/yellow]"
                ))

            elif event_type == "cost_warning":
                msg = e.get("message", "Cost threshold approached")
                parts.append(Text.from_markup(
                    f"  [yellow bold]\U0001f4b8 {msg[:60]}[/yellow bold]"
                ))

            elif event_type == "worker_hired":
                worker_id = e.get("worker_id", "?")
                parts.append(Text.from_markup(
                    f"  [green bold]\U0001f91d Hired: {worker_id}[/green bold]"
                ))

            elif event_type == "worker_fired":
                worker_id = e.get("worker_id", "?")
                parts.append(Text.from_markup(
                    f"  [red bold]\U0001f6ae Fired: {worker_id}[/red bold]"
                ))

            elif event_type in ("middleware_before", "middleware_after"):
                name = e.get("middleware", "?")
                direction = "\u2192" if event_type == "middleware_before" else "\u2190"
                parts.append(Text.from_markup(
                    f"  [dim blue]{direction} {name}[/dim blue]"
                ))

        self.update(Panel(
            Group(*parts),
            title="Workers Live",
            border_style=KANTORKU_THEME["secondary"],
            padding=(0, 1),
        ))


# ── Main TUI Application ────────────────────────────────────────────


class KantorKuTUI(App):
    """
    KantorKu — 3-Panel Chat-Driven Office Interface for Coders.

    Natural office workflow — chat is PRIMARY:
    1. Chat with Manager in LEFT panel (just type naturally)
    2. Watch workers brainstorm/execute in CENTER panel
    3. Review & accept contracts in RIGHT panel (click buttons or type)
    4. Hit DISRUPT to pause and talk to Manager again

    Contract Accept/Revise Flow:
      - Contract presented → Click ACCEPT or type "yes" → Contract finalized
      - Contract presented → Click REVISE or type feedback →
        Manager brainstorms with workers → New contract presented with Accept/Revise

    Natural Language Actions:
      Contract presented? Type "yes", "ok", "accept" to approve.
      Want changes? Type "revise", "change X", "I want Y" to revise.
      Working? Type "stop", "wait", "pause" to disrupt.

    Slash commands still work as secondary tools — /help for list.
    """

    TITLE = "kantorku"
    SUB_TITLE = "Chat-Driven Office"

    CSS = f"""
    Screen {{
        layout: vertical;
    }}

    #main-container {{
        layout: horizontal;
        height: 1fr;
    }}

    #left-panel {{
        width: 30%;
        height: 100%;
        border: solid {KANTORKU_THEME['primary']};
        border-title-color: {KANTORKU_THEME['primary']};
    }}

    #center-panel {{
        width: 40%;
        height: 100%;
        border: solid {KANTORKU_THEME['secondary']};
        border-title-color: {KANTORKU_THEME['secondary']};
    }}

    #right-panel {{
        width: 30%;
        height: 100%;
        border: solid {KANTORKU_THEME['accent']};
        border-title-color: {KANTORKU_THEME['accent']};
    }}

    #manager-log {{
        height: 1fr;
        border: none;
        padding: 0 1;
    }}

    #contract-scroll {{
        height: 1fr;
    }}

    #input-bar {{
        height: auto;
        dock: bottom;
        padding: 0 1;
    }}

    #chat-input {{
        dock: bottom;
    }}

    #disrupt-btn {{
        dock: bottom;
        margin: 0 1;
        background: {KANTORKU_THEME['warning']};
        color: $text;
        text-style: bold;
    }}

    #disrupt-btn:hover {{
        background: {KANTORKU_THEME['error']};
    }}

    #action-bar {{
        dock: bottom;
        height: auto;
        padding: 0 1;
    }}

    #accept-btn {{
        background: {KANTORKU_THEME['success']};
        color: $text;
        text-style: bold;
        margin-right: 1;
    }}

    #accept-btn:hover {{
        background: #059669;
    }}

    #accept-btn:disabled {{
        background: $surface;
        color: $text-disabled;
        text-style: not bold;
    }}

    #revise-btn {{
        background: {KANTORKU_THEME['accent']};
        color: $text;
        text-style: bold;
    }}

    #revise-btn:hover {{
        background: #d97706;
    }}

    #revise-btn:disabled {{
        background: $surface;
        color: $text-disabled;
        text-style: not bold;
    }}

    #status-bar {{
        dock: bottom;
        height: 1;
        background: {KANTORKU_THEME['surface']};
        color: {KANTORKU_THEME['muted']};
        padding: 0 1;
    }}
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("escape", "cancel_input", "Cancel", show=True),
        Binding("ctrl+a", "accept_contract", "Accept", show=False),
        Binding("ctrl+r", "revise_contract", "Revise", show=False),
        Binding("ctrl+i", "disrupt", "Disrupt", show=False),
        Binding("tab", "focus_next_panel", "Next Panel", show=False),
        Binding("up", "history_up", "History \u2191", show=False),
        Binding("down", "history_down", "History \u2193", show=False),
    ]

    # Reactive state
    session_id: reactive[str] = reactive("")
    connection_state: reactive[str] = reactive("disconnected")
    pending_contract: reactive[dict] = reactive({})
    contract_state: reactive[str] = reactive("idle")

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
        self._reconnect_delay = 2.0

        # Worker event listener
        self._event_listener_running = False

        # Cost tracking for status
        self._total_cost: float = 0.0
        self._total_calls: int = 0

        # Revision tracking
        self._revision_count: int = 0
        self._revision_feedback: str = ""

        # Auto-accept flag for /code and /run
        self._auto_accept_pending: bool = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Container(id="main-container"):
            # ── Left Panel: Manager Chat ──
            with Vertical(id="left-panel"):
                yield RichLog(
                    id="manager-log",
                    highlight=True,
                    markup=True,
                    auto_scroll=True,
                )
                yield Button(
                    "\u26a1 DISRUPT \u2014 Talk to Manager",
                    id="disrupt-btn",
                    variant="warning",
                )
                with Horizontal(id="input-bar"):
                    yield Input(
                        placeholder="Talk to Manager...",
                        id="chat-input",
                    )

            # ── Center Panel: Workers Live ──
            with Vertical(id="center-panel"):
                yield WorkersLiveStream(id="workers-live")

            # ── Right Panel: Contract + Buttons ──
            with Vertical(id="right-panel"):
                with VerticalScroll(id="contract-scroll"):
                    yield ContractDisplay(id="contract-display")
                with Horizontal(id="action-bar"):
                    yield Button(
                        "\u2713 ACCEPT",
                        id="accept-btn",
                        variant="success",
                    )
                    yield Button(
                        "\u270f REVISE",
                        id="revise-btn",
                        variant="warning",
                    )

        yield Footer()

    def on_mount(self) -> None:
        """Initialize connection and start background workers."""
        self.title = f"kantorku \u2014 session {self._session_id}"
        self._add_manager_message(
            f"[bold cyan]KantorKu TUI v0.7.0 \u2014 Chat-Driven Office[/bold cyan]\n"
            f"Session: {self._session_id}\n"
            f"Server: {self.server_url}\n\n"
            f"[bold]How it works:[/bold]\n"
            f"  [bold cyan]Left[/bold cyan]   \u2192 Chat with Manager (just type!)\n"
            f"  [bold magenta]Center[/bold magenta] \u2192 Watch workers brainstorm & execute\n"
            f"  [bold yellow]Right[/bold yellow]  \u2192 Review contracts & click Accept/Revise\n\n"
            f"[bold green]Contract flow:[/bold green]\n"
            f"  Contract shown \u2192 Click [bold green]ACCEPT[/bold green] to finalize\n"
            f"  Want changes? Click [bold yellow]REVISE[/bold yellow] \u2192 write feedback\n"
            f"  \u2192 Manager brainstorms with workers \u2192 new contract!\n\n"
            f"[dim]Or type naturally: 'yes'/'ok' to accept, 'revise' to change\n"
            f"Slash commands: /help for full list\n"
            f"Shortcuts: Ctrl+A=Accept  Ctrl+R=Revise  Ctrl+I=Disrupt  Esc=Cancel[/dim]"
        )

        # Hide action buttons initially (no contract)
        self._update_action_buttons()

        # Connect to server
        self._connect_and_listen()

    # ── State Machine ────────────────────────────────────────────────

    def _set_contract_state(self, new_state: str) -> None:
        """Centralize ALL contract state transitions.

        Sets self.contract_state, updates ContractDisplay,
        and refreshes UI (action buttons, placeholder, subtitle).
        """
        self.contract_state = new_state
        try:
            cd = self.query_one("#contract-display", ContractDisplay)
            cd.contract_state = new_state
        except NoMatches:
            pass
        self._update_action_buttons()
        self._update_input_placeholder()
        self._update_subtitle()

    # ── Action Button Management ─────────────────────────────────────

    def _update_action_buttons(self) -> None:
        """Show/hide Accept/Revise buttons based on contract state."""
        try:
            accept_btn = self.query_one("#accept-btn", Button)
            revise_btn = self.query_one("#revise-btn", Button)
        except NoMatches:
            return

        if self.contract_state == "contract_presented":
            accept_btn.display = True
            revise_btn.display = True
            accept_btn.disabled = False
            revise_btn.disabled = False
        elif self.contract_state == "awaiting_revision":
            # Hide both during revision — user types feedback instead
            accept_btn.display = False
            revise_btn.display = False
        elif self.contract_state == "working":
            accept_btn.display = False
            revise_btn.display = False
        elif self.contract_state == "accepted":
            accept_btn.display = False
            revise_btn.display = False
        else:
            accept_btn.display = False
            revise_btn.display = False

    def _update_input_placeholder(self) -> None:
        """Change input placeholder based on current state."""
        try:
            inp = self.query_one("#chat-input", Input)
        except NoMatches:
            return

        placeholders = {
            "idle": "Talk to Manager...",
            "manager_thinking": "Manager is thinking...",
            "clarifying": "Answer the Manager...",
            "contract_presented": "Type 'yes' to accept / type feedback to revise...",
            "awaiting_revision": "Write your revision feedback here...",
            "team_review": "Team is reviewing...",
            "todo_review": "Team is reviewing tasks...",
            "client_feedback": "Give feedback to Manager...",
            "working": "Type 'stop' to disrupt / or chat with Manager...",
            "verifying": "Workers are verifying...",
            "accepted": "Contract accepted! Workers starting...",
            "done": "Start a new task...",
            "failed": "Try again or ask Manager...",
        }
        inp.placeholder = placeholders.get(self.contract_state, "Talk to Manager...")

    def _update_subtitle(self) -> None:
        """Update the app subtitle with current state info."""
        state_icons = {
            "idle": "\U0001f4a4",
            "manager_thinking": "\U0001f914",
            "clarifying": "\U0001f4ac",
            "contract_presented": "\U0001f4cb",
            "awaiting_revision": "\u270f\ufe0f",
            "working": "\u26a1",
            "accepted": "\u2705",
            "done": "\u2705",
            "failed": "\u274c",
        }
        icon = state_icons.get(self.contract_state, "\u25cb")
        conn = "\u2713" if self.connection_state == "connected" else "\u2717"
        cost_str = f"${self._total_cost:.4f}" if self._total_cost > 0 else ""
        rev_str = f" rev:{self._revision_count}" if self._revision_count > 0 else ""
        self.sub_title = f"{icon} {self.contract_state} | conn:{conn}{rev_str} | {cost_str}"

    # ── Connection & Background Workers ─────────────────────────────

    @work(exclusive=True, name="connect_and_listen")
    async def _connect_and_listen(self) -> None:
        """Connect to server and start listening for events."""
        try:
            await self._connection.connect()
            self.connection_state = "connected"
            self._add_manager_message("[green]\u2713 Connected to server[/green]")
            self._update_subtitle()

            # Start event listener
            self._event_listener_running = True
            await self._listen_office_events()

        except ConnectionError as e:
            self.connection_state = "error"
            self._add_manager_message(
                f"[red]\u2717 Connection failed: {e}[/red]\n"
                f"[dim]Retrying in {self._reconnect_delay}s...[/dim]"
            )
            self._update_subtitle()
            await self._auto_reconnect()
        except Exception as e:
            self.connection_state = "error"
            self._add_manager_message(f"[red]Error: {e}[/red]")
            self._update_subtitle()

    async def _listen_office_events(self) -> None:
        """Listen to the office event stream and route to center panel."""
        try:
            async for event in self._connection.listen_events():
                if not self._event_listener_running:
                    break
                self._route_office_event(event)
        except Exception as e:
            if self._event_listener_running:
                self._add_manager_message(f"[yellow]Event stream ended: {e}[/yellow]")

    def _route_office_event(self, event: dict[str, Any]) -> None:
        """Route an office event to the appropriate panel."""
        event_type = event.get("type", "")

        # Center panel: all worker activity
        try:
            workers_live = self.query_one("#workers-live", WorkersLiveStream)
            workers_live.add_event(event)
        except NoMatches:
            pass

        # Update phase based on event type
        phase_map = {
            "briefing_opened": "briefing",
            "plan_drafted": "briefing",
            "worker_speak_up": "briefing",
            "contract_accepted": "execution",
            "task_assigned": "execution",
            "task_started": "execution",
            "task_done": "execution",
            "task_failed": "execution",
            "verify_design_start": "verification",
            "verify_engineer_start": "verification",
            "revision_requested": "briefing",
            "manager_brainstorming": "briefing",
        }
        new_phase = phase_map.get(event_type)
        if new_phase:
            try:
                workers_live = self.query_one("#workers-live", WorkersLiveStream)
                workers_live._phase = new_phase
            except NoMatches:
                pass

        # Right panel: contract state updates
        contract_events = {
            "contract_ready", "contract_accepted", "work_started",
            "work_done", "plan_drafted", "plan_revised",
        }
        if event_type in contract_events:
            self._handle_contract_event(event)

        # Manager messages go to left panel
        if event_type == "manager_message":
            content = event.get("content", "")
            self._add_manager_message(f"[bold green]Manager:[/bold green] {content}")

        elif event_type == "manager_question":
            content = event.get("content", "")
            self._add_manager_message(f"[bold yellow]Manager asks:[/bold yellow] {content}")

        elif event_type == "work_done":
            result = event.get("result", {})
            self._set_contract_state("done")
            try:
                cd = self.query_one("#contract-display", ContractDisplay)
                cd.work_result = result
                workers_live = self.query_one("#workers-live", WorkersLiveStream)
                workers_live._phase = "done"
                workers_live.add_system_message("\u2705 All work complete!", "green bold")
            except NoMatches:
                pass
            self._add_manager_message("[bold green]\u2713 Work complete![/bold green]")

        elif event_type == "error":
            msg = event.get("message", "Unknown error")
            self._add_manager_message(f"[red bold]\u2717 Error: {msg}[/red bold]")

        # Track cost updates from events
        elif event_type == "cost_warning":
            cost = event.get("cost_usd", 0)
            if cost:
                self._total_cost = cost
            self._update_subtitle()

    def _handle_contract_event(self, event: dict[str, Any]) -> None:
        """Handle contract-related events — update right panel."""
        event_type = event.get("type", "")

        if event_type == "contract_ready":
            contract = event.get("contract", {})
            try:
                cd = self.query_one("#contract-display", ContractDisplay)
                cd.contract_data = contract
                cd.revision_count = self._revision_count
            except NoMatches:
                pass
            self.pending_contract = contract
            self._set_contract_state("contract_presented")

            if self._revision_count > 0:
                self._add_manager_message(
                    f"[bold cyan]\U0001f4cb Revised contract ready! (Rev #{self._revision_count})[/bold cyan]\n"
                    f"Review it in the right panel.\n"
                    f"[bold green]Click \u2713 ACCEPT[/bold green] to finalize  |  "
                    f"[bold yellow]Click \u270f REVISE[/bold yellow] to request more changes\n"
                    f"[dim]Or type 'yes'/'ok' to accept, or type feedback to revise[/dim]"
                )
            else:
                self._add_manager_message(
                    f"[bold cyan]\U0001f4cb Contract ready![/bold cyan] "
                    f"Review it in the right panel.\n"
                    f"[bold green]Click \u2713 ACCEPT[/bold green] to finalize  |  "
                    f"[bold yellow]Click \u270f REVISE[/bold yellow] to request changes\n"
                    f"[dim]Or type 'yes'/'ok' to accept, or type feedback to revise[/dim]"
                )

        elif event_type == "contract_accepted":
            self._set_contract_state("accepted")

        elif event_type == "work_started":
            self._set_contract_state("working")

        elif event_type == "work_done":
            result = event.get("result", {})
            self._set_contract_state("done")
            try:
                cd = self.query_one("#contract-display", ContractDisplay)
                cd.work_result = result
                workers_live = self.query_one("#workers-live", WorkersLiveStream)
                workers_live._phase = "done"
                workers_live.add_system_message("\u2705 All work complete!", "green bold")
            except NoMatches:
                pass
            self._add_manager_message("[bold green]\u2713 Work complete![/bold green]")

    # ── Input Handling ──────────────────────────────────────────────

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input — parse NL actions, slash commands, or chat."""
        if event.input.id != "chat-input":
            return

        text = event.value.strip()
        if not text:
            return

        # Clear input
        event.input.value = ""

        # Add to history
        self._input_history.append(text)
        self._history_index = -1

        # Check for slash commands first
        if text.startswith("/"):
            result = await handle_slash_command(text, self)
            if result:
                self._add_manager_message(result)
            return

        # ── Check for natural language actions ──

        # If in awaiting_revision state, ANY input is revision feedback
        if self.contract_state == "awaiting_revision":
            self._add_manager_message(f"[bold]You (revision):[/bold] {text}")
            await self._send_revise(text)
            return

        nl_action = parse_nl_action(text, self.contract_state)

        if nl_action == "accept":
            self._add_manager_message(f"[bold]You:[/bold] {text}  \u2192 [green]Accepting contract[/green]")
            await self._send_accept()
            return

        if nl_action == "revise":
            # Extract feedback: strip the action word, keep the rest
            feedback = text
            for prefix in ("revise", "change", "modify", "update", "alter", "redo",
                          "no", "nope", "nah", "reject", "deny", "not quite", "not really"):
                if feedback.lower().startswith(prefix):
                    remainder = feedback[len(prefix):].strip()
                    if remainder:
                        feedback = remainder
                    break
            self._add_manager_message(f"[bold]You:[/bold] {text}  \u2192 [yellow]Requesting revision[/yellow]")
            await self._send_revise(feedback if feedback != text else text)
            return

        if nl_action == "interrupt":
            self._add_manager_message(f"[bold]You:[/bold] {text}  \u2192 [yellow]Disrupting work[/yellow]")
            self._do_disrupt()
            return

        # Send as regular message to Manager
        self._add_manager_message(f"[bold]You:[/bold] {text}")
        await self._send_message(text)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "disrupt-btn":
            self._do_disrupt()
        elif event.button.id == "accept-btn":
            self._add_manager_message("[bold green]\u2713 Accepting contract...[/bold green]")
            asyncio.create_task(self._send_accept())
        elif event.button.id == "revise-btn":
            # Enter revision mode — user will type feedback in the chat input
            self._enter_revision_mode()

    # ── Revision Mode ───────────────────────────────────────────────

    def _enter_revision_mode(self) -> None:
        """Enter revision mode — prompt user for feedback.

        When REVISE is clicked:
        1. Contract state → awaiting_revision
        2. Hide Accept/Revise buttons
        3. Change input placeholder to "Write your revision feedback..."
        4. Focus the input field
        5. User types feedback → _send_revise() → Manager brainstorms → new contract
        """
        if not self.pending_contract:
            self._add_manager_message("[yellow]No contract to revise yet. Chat with the Manager first![/yellow]")
            return

        self._set_contract_state("awaiting_revision")

        self._add_manager_message(
            "[bold yellow]\u270f\ufe0f REVISE MODE[/bold yellow]\n"
            "[yellow]Write your revision feedback below and press Enter.[/yellow]\n"
            "[dim]The Manager will brainstorm with the workers and present a new contract.[/dim]"
        )

        # Focus the input
        try:
            inp = self.query_one("#chat-input", Input)
            inp.focus()
        except NoMatches:
            pass

    # ── Key Bindings ────────────────────────────────────────────────

    def action_accept_contract(self) -> None:
        """Ctrl+A — Accept current contract."""
        if self.contract_state in ("contract_presented", "awaiting_revision"):
            asyncio.create_task(self._send_accept())
        else:
            self._add_manager_message("[yellow]No contract to accept yet. Chat with the Manager first![/yellow]")

    def action_revise_contract(self) -> None:
        """Ctrl+R — Enter revision mode."""
        if self.contract_state == "contract_presented":
            self._enter_revision_mode()
        else:
            self._add_manager_message("[yellow]No contract to revise yet.[/yellow]")

    def action_disrupt(self) -> None:
        """Ctrl+I — Disrupt current work and talk to Manager."""
        self._do_disrupt()

    def _do_disrupt(self) -> None:
        """Disrupt current work — pause and talk to Manager."""
        if self.contract_state in ("working", "team_review", "todo_review", "verifying", "accepted"):
            self._add_manager_message(
                "[bold yellow]\u26a1 DISRUPT \u2014 Pausing work to talk to Manager[/bold yellow]"
            )
            self._set_contract_state("client_feedback")
            try:
                workers_live = self.query_one("#workers-live", WorkersLiveStream)
                workers_live.add_system_message(
                    "\u26a1 DISRUPT \u2014 Client paused work for discussion", "yellow bold"
                )
            except NoMatches:
                pass
        else:
            self._add_manager_message(
                "[dim]No active work to disrupt. Just type your message![/dim]"
            )

    def action_focus_next_panel(self) -> None:
        """Tab — Cycle focus between panels."""
        focused = self.focused
        if focused and focused.id == "chat-input":
            self.query_one("#workers-live").focus()
        elif focused and hasattr(focused, 'id') and 'workers' in str(focused.id):
            self.query_one("#contract-scroll").focus()
        else:
            self.query_one("#chat-input").focus()

    def action_history_up(self) -> None:
        """Up arrow — Navigate input history."""
        if not self._input_history:
            return
        if self._history_index < len(self._input_history) - 1:
            self._history_index += 1
            idx = len(self._input_history) - 1 - self._history_index
            try:
                inp = self.query_one("#chat-input", Input)
                inp.value = self._input_history[idx]
            except NoMatches:
                pass

    def action_history_down(self) -> None:
        """Down arrow — Navigate input history."""
        if self._history_index > 0:
            self._history_index -= 1
            idx = len(self._input_history) - 1 - self._history_index
            try:
                inp = self.query_one("#chat-input", Input)
                inp.value = self._input_history[idx]
            except NoMatches:
                pass
        elif self._history_index == 0:
            self._history_index = -1
            try:
                inp = self.query_one("#chat-input", Input)
                inp.value = ""
            except NoMatches:
                pass

    def action_cancel_input(self) -> None:
        """Ctrl+C — Cancel current input or streaming."""
        try:
            inp = self.query_one("#chat-input", Input)
            inp.value = ""
        except NoMatches:
            pass

        # If in revision mode, cancel back to contract_presented
        if self.contract_state == "awaiting_revision":
            self._set_contract_state("contract_presented")
            self._add_manager_message("[dim]Revision cancelled. Accept/Revise buttons are back.[/dim]")

    # ── Message Sending ─────────────────────────────────────────────

    async def _send_message(self, message: str) -> None:
        """Send a message to the Manager via WebSocket."""
        self._set_contract_state("manager_thinking")

        try:
            async for event in self._connection.send_message(message):
                event_type = event.get("type", "")

                if event_type == "manager_message":
                    content = event.get("content", "")
                    self._add_manager_message(
                        f"[bold green]Manager:[/bold green] {content}"
                    )
                    self._set_contract_state("clarifying")

                elif event_type == "manager_question":
                    content = event.get("content", "")
                    self._add_manager_message(
                        f"[bold yellow]Manager asks:[/bold yellow] {content}"
                    )

                elif event_type == "contract_ready":
                    contract = event.get("contract", {})
                    self.pending_contract = contract
                    try:
                        cd = self.query_one("#contract-display", ContractDisplay)
                        cd.contract_data = contract
                        cd.revision_count = self._revision_count
                    except NoMatches:
                        pass
                    self._set_contract_state("contract_presented")
                    self._add_manager_message(
                        f"[bold cyan]\U0001f4cb Contract ready![/bold cyan] "
                        f"Review in right panel.\n"
                        f"[bold green]Click \u2713 ACCEPT[/bold green] to finalize  |  "
                        f"[bold yellow]Click \u270f REVISE[/bold yellow] to request changes"
                    )
                    # Auto-accept if /code or /run requested it
                    if getattr(self, '_auto_accept_pending', False):
                        self._auto_accept_pending = False
                        asyncio.create_task(self._send_accept())

                elif event_type == "error":
                    msg = event.get("message", "Unknown error")
                    self._add_manager_message(f"[red bold]\u2717 {msg}[/red bold]")

        except ConnectionError as e:
            self._add_manager_message(
                f"[red]Connection lost: {e}[/red]\n"
                f"[dim]Will try to reconnect...[/dim]"
            )
            self.connection_state = "disconnected"
            self._update_subtitle()
            await self._auto_reconnect()

    async def _send_accept(self) -> None:
        """Accept the current contract — finalize and display in right panel.

        When Accept is clicked:
        1. Contract state → accepted
        2. Right panel shows the contract with "CONTRACT ACCEPTED" status
        3. Accept/Revise buttons hidden
        4. Workers begin execution (state → working)
        """
        if not self.pending_contract:
            self._add_manager_message("[yellow]No contract to accept.[/yellow]")
            return

        # Reset revision count for next contract cycle
        self._revision_count = 0

        self._add_manager_message(
            "[bold green]\u2713 Contract accepted! Workers are starting...[/bold green]"
        )

        # Show ACCEPTED state in right panel
        try:
            cd = self.query_one("#contract-display", ContractDisplay)
            cd.revision_count = 0
        except NoMatches:
            pass
        self._set_contract_state("accepted")

        try:
            workers_live = self.query_one("#workers-live", WorkersLiveStream)
            workers_live.add_system_message(
                "\u2713 Contract accepted \u2014 Briefing room opening...", "green bold"
            )
            workers_live._phase = "briefing"
        except NoMatches:
            pass

        # Send accept to server
        result = await self._connection.accept_contract()

        if result and result.get("type") == "error":
            self._add_manager_message(f"[red]Accept failed: {result.get('message', '')}[/red]")
            self._set_contract_state("contract_presented")
        elif result:
            # Transition to working state — do NOT set "done" immediately;
            # the work_done event will handle that transition.
            self._set_contract_state("working")

    async def _send_revise(self, feedback: str) -> None:
        """Request a contract revision.

        When Revise is triggered:
        1. Increment revision counter
        2. Send revision feedback to Manager
        3. Manager brainstorms with workers (shown in center panel)
        4. Manager asks clarifying questions if needed
        5. New contract presented with Accept/Revise buttons again
        """
        if not self.pending_contract:
            self._add_manager_message("[yellow]No contract to revise.[/yellow]")
            return

        self._revision_count += 1
        self._revision_feedback = feedback

        self._add_manager_message(
            f"[bold yellow]\u21bb Requesting revision (#{self._revision_count}):[/bold yellow] {feedback}"
        )

        # Show brainstorming in center panel
        try:
            workers_live = self.query_one("#workers-live", WorkersLiveStream)
            workers_live.add_system_message(
                f"\u270f\ufe0f Revision #{self._revision_count}: {feedback[:60]}", "yellow bold"
            )
            workers_live.add_event({
                "type": "revision_requested",
                "feedback": feedback,
            })
            workers_live.add_event({
                "type": "manager_brainstorming",
            })
            workers_live._phase = "briefing"
        except NoMatches:
            pass

        # Set state to clarifying (Manager is thinking about revision)
        try:
            cd = self.query_one("#contract-display", ContractDisplay)
            cd.revision_count = self._revision_count
        except NoMatches:
            pass
        self._set_contract_state("manager_thinking")

        # Send revision request to server
        async for event in self._connection.revise_contract(feedback):
            event_type = event.get("type", "")

            if event_type == "manager_message":
                content = event.get("content", "")
                self._add_manager_message(
                    f"[bold green]Manager:[/bold green] {content}"
                )

            elif event_type == "manager_question":
                content = event.get("content", "")
                self._add_manager_message(
                    f"[bold yellow]Manager asks:[/bold yellow] {content}"
                )
                # Manager is asking a question — set to clarifying
                self._set_contract_state("clarifying")

            elif event_type == "contract_ready":
                contract = event.get("contract", {})
                self.pending_contract = contract
                try:
                    cd = self.query_one("#contract-display", ContractDisplay)
                    cd.contract_data = contract
                    cd.revision_count = self._revision_count
                except NoMatches:
                    pass
                self._set_contract_state("contract_presented")
                self._add_manager_message(
                    f"[bold cyan]\U0001f4cb Revised contract ready! (Rev #{self._revision_count})[/bold cyan]\n"
                    f"Review it in the right panel.\n"
                    f"[bold green]Click \u2713 ACCEPT[/bold green] to finalize  |  "
                    f"[bold yellow]Click \u270f REVISE[/bold yellow] for more changes"
                )

            elif event_type == "error":
                msg = event.get("message", "Unknown error")
                self._add_manager_message(f"[red]\u2717 {msg}[/red]")

    # ── Helpers ─────────────────────────────────────────────────────

    def _add_manager_message(self, content: str) -> None:
        """Add a message to the Manager chat log (left panel)."""
        try:
            log = self.query_one("#manager-log", RichLog)
            log.write(Text.from_markup(content))
        except NoMatches:
            pass

    async def _auto_reconnect(self) -> None:
        """Attempt to reconnect with exponential backoff."""
        while self._reconnect_attempts < self._max_reconnect_attempts:
            self._reconnect_attempts += 1
            delay = self._reconnect_delay * (2 ** (self._reconnect_attempts - 1))
            self._add_manager_message(
                f"[dim]Reconnecting ({self._reconnect_attempts}/{self._max_reconnect_attempts}) "
                f"in {delay:.0f}s...[/dim]"
            )
            await asyncio.sleep(delay)

            try:
                await self._connection.connect()
                self.connection_state = "connected"
                self._reconnect_attempts = 0
                self._update_subtitle()  # Set connection_state BEFORE subtitle
                self._add_manager_message("[green]\u2713 Reconnected![/green]")
                # Restart event listener
                self._event_listener_running = True
                await self._listen_office_events()
                return
            except ConnectionError:
                continue
            except Exception:
                continue

        self._add_manager_message(
            f"[red bold]\u2717 Could not reconnect after {self._max_reconnect_attempts} attempts.[/red bold]\n"
            f"[dim]Check your server and restart the TUI.[/dim]"
        )

    # ── Embedded Mode Support ──────────────────────────────────────

    def _update_embedded_status(self) -> None:
        """Update panels with embedded office data."""
        office = getattr(self, '_office', None)
        if not office:
            return

        try:
            cd = self.query_one("#contract-display", ContractDisplay)

            # Update worker status
            if hasattr(office, 'get_worker_status'):
                workers = office.get_worker_status()

            # Update pool status
            if hasattr(office, 'get_pool_status'):
                pool = office.get_pool_status()

            # Update cost
            if hasattr(office, 'cost_tracker') and office.cost_tracker:
                cost = office.cost_tracker.get_report()
                if cost:
                    self._total_cost = cost.get("total_cost_usd", 0)
                    self._total_calls = cost.get("total_calls", 0)
                    self._update_subtitle()

        except NoMatches:
            pass


class EmbeddedKantorKuTUI(KantorKuTUI):
    """
    KantorKu TUI in embedded mode — runs Office in-process.

    No server needed. Everything runs locally.
    Same chat-driven UX as remote mode.
    """

    def __init__(self, config_path: str | None = None, **kwargs: Any) -> None:
        super().__init__(server_url="embedded", config_path=config_path, **kwargs)
        self._office: Any = None

    @work(exclusive=True, name="embedded_init")
    async def _connect_and_listen(self) -> None:
        """Initialize embedded Office instead of connecting to server."""
        try:
            from kantorku.office import Office

            self._add_manager_message("[bold cyan]Starting embedded Office...[/bold cyan]")

            if self.config_path:
                self._office = Office.from_config(self.config_path)
            else:
                self._office = Office()

            await self._office.initialize()
            self.connection_state = "connected"
            self._add_manager_message(
                "[green]\u2713 Embedded Office initialized![/green]\n"
                f"[dim]Workers: {len(self._office.registry.all_worker_ids)}[/dim]"
            )
            self._update_subtitle()

            # Subscribe to event bus
            self._event_listener_running = True
            await self._listen_embedded_events()

        except Exception as e:
            self.connection_state = "error"
            self._add_manager_message(f"[red bold]\u2717 Failed to start: {e}[/red bold]")
            self._update_subtitle()
            # Auto-reconnect for embedded mode
            await self._embedded_reconnect()

    async def _embedded_reconnect(self) -> None:
        """Attempt to reinitialize the embedded Office on failure."""
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            delay = 5.0 * attempt
            self._add_manager_message(
                f"[dim]Retrying embedded init ({attempt}/{max_attempts}) in {delay:.0f}s...[/dim]"
            )
            await asyncio.sleep(delay)
            try:
                from kantorku.office import Office
                if self.config_path:
                    self._office = Office.from_config(self.config_path)
                else:
                    self._office = Office()
                await self._office.initialize()
                self.connection_state = "connected"
                self._add_manager_message("[green]\u2713 Embedded Office reconnected![/green]")
                self._update_subtitle()
                self._event_listener_running = True
                await self._listen_embedded_events()
                return
            except Exception as e:
                self._add_manager_message(f"[red]Retry {attempt} failed: {e}[/red]")
        self._add_manager_message(
            "[red bold]\u2717 Could not initialize embedded Office after retries.[/red bold]\n"
            "[dim]Check your config and restart.[/dim]"
        )

    async def _listen_embedded_events(self) -> None:
        """Listen to embedded office events."""
        if not self._office:
            return

        bus = self._office.bus
        session_id = self._session_id

        try:
            async with bus.subscribe(session_id) as events:
                async for event in events:
                    if not self._event_listener_running:
                        break
                    self._route_office_event(event.to_dict())
        except Exception as e:
            if self._event_listener_running:
                self._add_manager_message(f"[yellow]Event stream ended: {e}[/yellow]")
                # Attempt reconnect if stream ended unexpectedly
                await self._embedded_reconnect()

    async def _send_message(self, message: str) -> None:
        """Send message using embedded Office."""
        if not self._office:
            self._add_manager_message("[red]Office not initialized[/red]")
            return

        self._set_contract_state("manager_thinking")

        try:
            async for event in self._office.chat(self._session_id, message):
                event_type = event.get("type", "")

                if event_type == "manager_message":
                    content = event.get("content", "")
                    self._add_manager_message(
                        f"[bold green]Manager:[/bold green] {content}"
                    )
                    self._set_contract_state("clarifying")

                elif event_type == "manager_question":
                    content = event.get("content", "")
                    self._add_manager_message(
                        f"[bold yellow]Manager asks:[/bold yellow] {content}"
                    )

                elif event_type == "contract_ready":
                    contract = event.get("contract", {})
                    self.pending_contract = contract
                    try:
                        cd = self.query_one("#contract-display", ContractDisplay)
                        cd.contract_data = contract
                        cd.revision_count = self._revision_count
                    except NoMatches:
                        pass
                    self._set_contract_state("contract_presented")
                    self._add_manager_message(
                        f"[bold cyan]\U0001f4cb Contract ready![/bold cyan] "
                        f"Review in right panel.\n"
                        f"[bold green]Click \u2713 ACCEPT[/bold green] to finalize  |  "
                        f"[bold yellow]Click \u270f REVISE[/bold yellow] for changes"
                    )
                    # Auto-accept if /code or /run requested it
                    if getattr(self, '_auto_accept_pending', False):
                        self._auto_accept_pending = False
                        asyncio.create_task(self._send_accept())

                elif event_type == "error":
                    msg = event.get("message", "Unknown error")
                    self._add_manager_message(f"[red bold]\u2717 {msg}[/red bold]")

        except Exception as e:
            self._add_manager_message(f"[red]Error: {e}[/red]")

    async def _send_accept(self) -> None:
        """Accept contract using embedded Office."""
        if not self._office:
            self._add_manager_message("[red]Office not initialized[/red]")
            return

        if not self.pending_contract:
            self._add_manager_message("[yellow]No contract to accept.[/yellow]")
            return

        self._revision_count = 0

        self._add_manager_message(
            "[bold green]\u2713 Contract accepted! Workers are starting...[/bold green]"
        )

        # Show ACCEPTED state
        try:
            cd = self.query_one("#contract-display", ContractDisplay)
            cd.revision_count = 0
        except NoMatches:
            pass
        self._set_contract_state("accepted")

        try:
            workers_live = self.query_one("#workers-live", WorkersLiveStream)
            workers_live.add_system_message(
                "\u2713 Contract accepted \u2014 Briefing room opening...", "green bold"
            )
            workers_live._phase = "briefing"
        except NoMatches:
            pass

        try:
            result = await self._office.accept_contract(self._session_id)

            if result and result.get("type") == "error":
                self._add_manager_message(f"[red]Accept failed: {result.get('message', '')}[/red]")
                self._set_contract_state("contract_presented")
            elif result:
                # Transition to working — do NOT set "done" immediately;
                # the work_done event will handle that transition.
                self._set_contract_state("working")

        except Exception as e:
            self._add_manager_message(f"[red]Accept error: {e}[/red]")

    async def _send_revise(self, feedback: str) -> None:
        """Request contract revision using embedded Office."""
        if not self._office:
            self._add_manager_message("[red]Office not initialized[/red]")
            return

        if not self.pending_contract:
            self._add_manager_message("[yellow]No contract to revise.[/yellow]")
            return

        self._revision_count += 1

        self._add_manager_message(
            f"[bold yellow]\u21bb Requesting revision (#{self._revision_count}):[/bold yellow] {feedback}"
        )

        # Show brainstorming in center panel
        try:
            workers_live = self.query_one("#workers-live", WorkersLiveStream)
            workers_live.add_system_message(
                f"\u270f\ufe0f Revision #{self._revision_count}: {feedback[:60]}", "yellow bold"
            )
            workers_live.add_event({
                "type": "revision_requested",
                "feedback": feedback,
            })
            workers_live.add_event({
                "type": "manager_brainstorming",
            })
            workers_live._phase = "briefing"
        except NoMatches:
            pass

        try:
            cd = self.query_one("#contract-display", ContractDisplay)
            cd.revision_count = self._revision_count
        except NoMatches:
            pass
        self._set_contract_state("manager_thinking")

        try:
            async for event in self._office.revise_contract(self._session_id, feedback):
                event_type = event.get("type", "")

                if event_type == "manager_message":
                    content = event.get("content", "")
                    self._add_manager_message(
                        f"[bold green]Manager:[/bold green] {content}"
                    )

                elif event_type == "manager_question":
                    content = event.get("content", "")
                    self._add_manager_message(
                        f"[bold yellow]Manager asks:[/bold yellow] {content}"
                    )
                    self._set_contract_state("clarifying")

                elif event_type == "contract_ready":
                    contract = event.get("contract", {})
                    self.pending_contract = contract
                    try:
                        cd = self.query_one("#contract-display", ContractDisplay)
                        cd.contract_data = contract
                        cd.revision_count = self._revision_count
                    except NoMatches:
                        pass
                    self._set_contract_state("contract_presented")
                    self._add_manager_message(
                        f"[bold cyan]\U0001f4cb Revised contract ready! (Rev #{self._revision_count})[/bold cyan]\n"
                        f"Review it in the right panel.\n"
                        f"[bold green]Click \u2713 ACCEPT[/bold green] to finalize  |  "
                        f"[bold yellow]Click \u270f REVISE[/bold yellow] for more changes"
                    )

                elif event_type == "error":
                    msg = event.get("message", "Unknown error")
                    self._add_manager_message(f"[red]\u2717 {msg}[/red]")

        except Exception as e:
            self._add_manager_message(f"[red]Revision error: {e}[/red]")
