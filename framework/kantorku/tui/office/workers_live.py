"""
WorkersLivePanel — Real-time worker event log with filtering and roster.

Displays a live stream of worker activity with:
- Real-time event log with 500-entry buffer
- Filter buttons: All, Tasks, Briefing, Errors, LLM
- Worker roster sidebar: name, status badge, current task
- Thinking spinner per active worker
- 20fps render throttle
- Color-coded event types

Layout:
    ┌────────────────────────────────────────────────────────────┐
    │  ⚡ EXECUTING                                              │
    │  [All] [Tasks] [Briefing] [Errors] [LLM]                  │
    │  ───────────────────────────────────────────────────────── │
    │  ┌─ Roster ──────────┐  ┌─ Event Stream ────────────────┐│
    │  │ ● architect  idle │  │ 📢 conductor: Briefing...     ││
    │  │ ◐ coder    work ⣾│  │ 🟡 architect: Suggest token.. ││
    │  │ ○ verifier  idle  │  │ ✓ coder done                  ││
    │  │ ○ qa        idle  │  │ ⚡ Circuit OPEN: openai       ││
    │  └──────────────────┘  └────────────────────────────────┘│
    └────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import time
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widgets import Button, Static

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from kantorku.tui.themes import (
    BRAILLE_SPINNER,
    KANTORKU_THEME,
    SQUAD_COLORS,
    STATUS_ICONS,
    STATUS_COLORS,
    WORKERS_PHASE_STYLES,
)

# ── Filter category mappings ──────────────────────────────────────────

FILTER_CATEGORIES: dict[str, set[str]] = {
    "tasks": {
        "task_assigned", "task_started", "task_done",
        "task_failed", "task_recovered", "task_timeout",
    },
    "briefing": {
        "briefing_opened", "plan_drafted", "plan_revised",
        "worker_speak_up", "worker_dm", "worker_broadcast",
    },
    "errors": {
        "error_logged", "circuit_open", "rate_limit_hit", "cost_warning",
    },
    "llm": {
        "llm_stream_start", "llm_stream_chunk", "llm_stream_done",
    },
}

# ── Event color mapping ───────────────────────────────────────────────

EVENT_TYPE_COLORS: dict[str, str] = {
    "task_assigned": "cyan",
    "task_started": "yellow",
    "task_done": "green",
    "task_failed": "red bold",
    "task_recovered": "green",
    "task_timeout": "red",
    "briefing_opened": "magenta",
    "plan_drafted": "blue",
    "plan_revised": "yellow",
    "worker_speak_up": "magenta",
    "worker_dm": "dim",
    "worker_broadcast": "cyan",
    "error_logged": "red",
    "circuit_open": "red bold",
    "circuit_closed": "green",
    "rate_limit_hit": "yellow",
    "cost_warning": "yellow bold",
    "llm_stream_start": "dim",
    "llm_stream_chunk": "dim",
    "llm_stream_done": "dim",
    "contract_accepted": "green bold",
    "worker_hired": "green bold",
    "worker_fired": "red bold",
    "delegation_request": "cyan",
    "delegation_result": "cyan",
    "checkpoint_saved": "green",
    "crash_recovered": "yellow bold",
    "skill_updated": "cyan",
    "manager_brainstorming": "cyan bold",
    "revision_requested": "yellow bold",
    "verify_design_start": "magenta",
    "verify_design_done": "magenta",
    "verify_engineer_start": "magenta",
    "verify_engineer_done": "magenta",
    "context_fetch_start": "dim",
    "context_fetch_done": "dim",
    "middleware_before": "dim blue",
    "middleware_after": "dim blue",
    "work_done": "green bold",
}

# ── Event icon mapping ────────────────────────────────────────────────

EVENT_TYPE_ICONS: dict[str, str] = {
    "task_assigned": "\u27a1",       # →
    "task_started": "\u25cf",        # ●
    "task_done": "\u2713",           # ✓
    "task_failed": "\u2717",         # ✗
    "task_recovered": "\u21bb",      # ↻
    "task_timeout": "\u23f1",        # ⏱
    "briefing_opened": "\U0001f4e2", # 📢
    "plan_drafted": "\U0001f4cb",    # 📋
    "plan_revised": "\U0001f4cb",    # 📋
    "worker_speak_up": "\U0001f4ac", # 💬
    "worker_dm": "\u2709",           # ✉
    "worker_broadcast": "\U0001f4e2",# 📢
    "error_logged": "\u26a0",        # ⚠
    "circuit_open": "\u26a1",        # ⚡
    "circuit_closed": "\u2713",      # ✓
    "rate_limit_hit": "\u23f0",      # ⏰
    "cost_warning": "\U0001f4b8",    # 💸
    "llm_stream_start": "\u25b6",    # ▶
    "llm_stream_chunk": "\u2500",    # ─
    "llm_stream_done": "\u25a0",     # ■
    "contract_accepted": "\u2713",   # ✓
    "worker_hired": "\U0001f91d",    # 🤝
    "worker_fired": "\U0001f6ae",    # 🚮
    "delegation_request": "\u2197",  # ↗
    "delegation_result": "\u2199",   # ↙
    "checkpoint_saved": "\U0001f4be",# 💾
    "crash_recovered": "\U0001f504", # 🔄
}

# ── CSS ────────────────────────────────────────────────────────────────

_CSS = """
WorkersLivePanel {
    layout: vertical;
    height: 1fr;
}

#workers-phase {
    height: 1;
    padding: 0 1;
}

#workers-filter-bar {
    height: 1;
    dock: top;
    padding: 0;
    background: $surface;
    border-bottom: tall $primary 15%;
    layout: horizontal;
}

.workers-filter-btn {
    margin: 0 1;
    height: 1;
    min-width: 0;
    background: transparent;
    color: $muted;
    border: none;
}

.workers-filter-btn.active {
    text-style: bold;
    color: $primary;
    background: $primary 10%;
}

.workers-filter-btn:hover {
    color: $text;
    background: $primary 15%;
}

#workers-main {
    height: 1fr;
    layout: horizontal;
}

#workers-roster {
    width: 22;
    height: 1fr;
    border-right: tall $primary 20%;
    background: $surface;
    padding: 0 1;
    scrollbar-size: 0 0;
}

#workers-stream {
    width: 1fr;
    height: 1fr;
    scrollbar-size: 1 1;
    padding: 0 1;
}
"""


class WorkersLivePanel(Static):
    """Center panel — real-time worker event log with filtering and roster.

    Features:
    - Real-time worker event log with 500-entry buffer
    - Filter buttons: All, Tasks, Briefing, Errors, LLM
    - Worker roster sidebar: name, status badge, current task
    - Thinking spinner per active worker
    - 20fps render throttle
    - Color-coded event types
    """

    CSS = _CSS

    phase: reactive[str] = reactive("idle")

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._entries: list[dict[str, Any]] = []
        self._max_entries: int = 500
        self._active_filters: set[str] = set(FILTER_CATEGORIES.keys())
        self._workers: dict[str, dict[str, Any]] = {}  # worker_id -> status info
        self._streaming_workers: set[str] = set()

        # Render throttle (20fps max)
        self._last_render_time: float = 0.0
        self._dirty: bool = False
        self._pending_render: Any = None
        self._render_cooldown: float = 0.05

        # Spinner state
        self._spinner_index: int = 0
        self._spinner_timer: Any = None

    # ── Compose ────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Static(self._render_phase(), id="workers-phase")
        with Horizontal(id="workers-filter-bar"):
            yield Button("All", id="wfilter-all", classes="workers-filter-btn active")
            yield Button("Tasks", id="wfilter-tasks", classes="workers-filter-btn")
            yield Button("Briefing", id="wfilter-briefing", classes="workers-filter-btn")
            yield Button("Errors", id="wfilter-errors", classes="workers-filter-btn")
            yield Button("LLM", id="wfilter-llm", classes="workers-filter-btn")
        with Horizontal(id="workers-main"):
            with VerticalScroll(id="workers-roster"):
                yield Static(id="workers-roster-content")
            with VerticalScroll(id="workers-stream"):
                yield Static(id="workers-stream-content")

    # ── Lifecycle ──────────────────────────────────────────────────

    def on_mount(self) -> None:
        """Initialize display and start spinner timer."""
        self._render_stream()
        self._render_roster()
        # Spinner timer for streaming workers
        self._spinner_timer = self.set_interval(0.25, self._tick_spinner)

    def on_unmount(self) -> None:
        """Clean up timer."""
        if self._spinner_timer is not None:
            self._spinner_timer.stop()

    # ── Reactive Watchers ──────────────────────────────────────────

    def watch_phase(self, new_phase: str) -> None:
        """Update phase indicator when phase changes."""
        try:
            phase_widget = self.query_one("#workers-phase", Static)
            phase_widget.update(self._render_phase())
        except Exception:
            pass

    # ── Public API ─────────────────────────────────────────────────

    def add_event(self, event: dict[str, Any]) -> None:
        """Add an office event to the live stream."""
        event_type = event.get("type", "")

        relevant_types = {
            "briefing_opened", "plan_drafted", "plan_revised",
            "worker_speak_up", "worker_dm", "worker_broadcast",
            "task_assigned", "task_started", "task_done", "task_failed",
            "task_recovered", "task_timeout",
            "context_fetch_start", "context_fetch_done",
            "verify_design_start", "verify_design_done",
            "verify_engineer_start", "verify_engineer_done",
            "error_logged", "skill_updated",
            "llm_stream_start", "llm_stream_chunk", "llm_stream_done",
            "contract_accepted",
            "delegation_request", "delegation_result",
            "checkpoint_saved", "crash_recovered",
            "circuit_open", "circuit_closed",
            "rate_limit_hit", "cost_warning",
            "worker_hired", "worker_fired",
            "revision_requested", "manager_brainstorming",
            "work_done",
            "middleware_before", "middleware_after",
        }

        if event_type not in relevant_types:
            return

        self._entries.append(event)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]

        # Update worker roster based on event
        self._update_worker_from_event(event)

        self._schedule_render()

    def add_system_message(self, message: str, style: str = "dim") -> None:
        """Add a system/phase message to the stream."""
        self._entries.append({
            "type": "system",
            "content": message,
            "style": style,
        })
        self._schedule_render()

    def update_worker_status(self, worker_id: str, status: str = "idle",
                             current_task: str = "") -> None:
        """Update a worker's status in the roster."""
        self._workers[worker_id] = {
            "status": status,
            "current_task": current_task,
        }
        if status == "thinking" or status == "in_progress":
            self._streaming_workers.add(worker_id)
        else:
            self._streaming_workers.discard(worker_id)
        self._render_roster()

    def clear(self) -> None:
        """Clear all events and worker states."""
        self._entries.clear()
        self._workers.clear()
        self._streaming_workers.clear()
        self._render_stream()
        self._render_roster()

    # ── Filter ─────────────────────────────────────────────────────

    def _event_matches_filter(self, event_type: str) -> bool:
        """Check if an event type passes the active filters."""
        if event_type == "system":
            return True

        for category, types in FILTER_CATEGORIES.items():
            if event_type in types:
                return category in self._active_filters

        return True  # Events not in any category always shown

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle filter button clicks."""
        btn_id = event.button.id or ""

        if not btn_id.startswith("wfilter-"):
            return

        if btn_id == "wfilter-all":
            self._active_filters = set(FILTER_CATEGORIES.keys())
        else:
            category = btn_id.replace("wfilter-", "")
            if category in self._active_filters:
                self._active_filters.discard(category)
            else:
                self._active_filters.add(category)

        self._update_filter_button_states()
        self._render_stream()

    def _update_filter_button_states(self) -> None:
        """Update filter button CSS classes."""
        all_active = self._active_filters == set(FILTER_CATEGORIES.keys())
        try:
            btn_all = self.query_one("#wfilter-all", Button)
            if all_active:
                btn_all.add_class("active")
            else:
                btn_all.remove_class("active")
        except NoMatches:
            pass

        for category in FILTER_CATEGORIES:
            try:
                btn = self.query_one(f"#wfilter-{category}", Button)
                if category in self._active_filters:
                    btn.add_class("active")
                else:
                    btn.remove_class("active")
            except NoMatches:
                pass

    # ── Render Throttle ────────────────────────────────────────────

    def _schedule_render(self) -> None:
        """Throttled render — max 20fps."""
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
        self._pending_render = None
        if self._dirty:
            self._dirty = False
            self._render_stream()
            self._last_render_time = time.monotonic()

    # ── Spinner ────────────────────────────────────────────────────

    def _tick_spinner(self) -> None:
        """Advance the spinner for streaming workers."""
        self._spinner_index = (self._spinner_index + 1) % len(BRAILLE_SPINNER)
        if self._streaming_workers:
            self._render_roster()

    # ── Worker Roster ──────────────────────────────────────────────

    def _update_worker_from_event(self, event: dict[str, Any]) -> None:
        """Update worker roster based on an event."""
        event_type = event.get("type", "")

        if event_type == "task_assigned":
            worker_id = event.get("to", "")
            content = event.get("content", "")
            if worker_id:
                self._workers[worker_id] = {
                    "status": "assigned",
                    "current_task": content[:30],
                }

        elif event_type == "task_started":
            worker_id = event.get("from", "")
            if worker_id:
                self._workers[worker_id] = {
                    "status": "in_progress",
                    "current_task": self._workers.get(worker_id, {}).get("current_task", ""),
                }
                self._streaming_workers.add(worker_id)

        elif event_type in ("task_done", "task_failed", "task_recovered", "task_timeout"):
            worker_id = event.get("from", "")
            if worker_id:
                status = "done" if event_type == "task_done" else (
                    "failed" if event_type == "task_failed" else "idle"
                )
                self._workers[worker_id] = {
                    "status": status,
                    "current_task": "",
                }
                self._streaming_workers.discard(worker_id)

        elif event_type == "llm_stream_start":
            worker_id = event.get("from", "")
            if worker_id:
                self._streaming_workers.add(worker_id)
                if worker_id in self._workers:
                    self._workers[worker_id]["status"] = "thinking"

        elif event_type == "llm_stream_done":
            worker_id = event.get("from", "")
            if worker_id:
                self._streaming_workers.discard(worker_id)
                if worker_id in self._workers:
                    self._workers[worker_id]["status"] = "idle"

        elif event_type == "worker_hired":
            worker_id = event.get("worker_id", "")
            if worker_id:
                self._workers[worker_id] = {"status": "idle", "current_task": ""}

        elif event_type == "worker_fired":
            worker_id = event.get("worker_id", "")
            if worker_id:
                self._workers.pop(worker_id, None)
                self._streaming_workers.discard(worker_id)

        self._render_roster()

    def _render_roster(self) -> None:
        """Render the worker roster sidebar."""
        try:
            roster_content = self.query_one("#workers-roster-content", Static)
        except Exception:
            return

        if not self._workers:
            roster_content.update(
                "[dim]No workers[/dim]"
            )
            return

        lines: list[str] = []
        lines.append("[bold]Roster[/bold]")
        lines.append("")

        spinner_char = BRAILLE_SPINNER[self._spinner_index]

        for worker_id, info in self._workers.items():
            status = info.get("status", "idle")
            current_task = info.get("current_task", "")

            icon = STATUS_ICONS.get(status, "\u25cb")
            color = STATUS_COLORS.get(status, "dim")
            squad_color = SQUAD_COLORS.get(worker_id, "white")

            # Spinner for active workers
            if status in ("thinking", "in_progress"):
                spinner = spinner_char
            else:
                spinner = ""

            # Truncate worker_id for display
            display_id = worker_id[:14] if len(worker_id) > 14 else worker_id
            task_str = f" {current_task[:12]}" if current_task else ""

            lines.append(
                f"[{color}]{icon}[/{color}] [{squad_color}]{display_id:14s}[/{squad_color}] {spinner}{task_str}"
            )

        roster_content.update(Text.from_markup("\n".join(lines)))

    # ── Phase ──────────────────────────────────────────────────────

    def _render_phase(self) -> str:
        """Render the phase indicator."""
        phase_style = WORKERS_PHASE_STYLES.get(self.phase, ("dim", self.phase.upper()))
        pc, pi = phase_style
        return f"[{pc}]{pi}[/{pc}]"

    # ── Event Stream ───────────────────────────────────────────────

    def _render_stream(self) -> None:
        """Render the event stream."""
        try:
            stream_content = self.query_one("#workers-stream-content", Static)
        except Exception:
            return

        if not self._entries:
            stream_content.update(Panel(
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

        # Filter indicator
        if self._active_filters != set(FILTER_CATEGORIES.keys()):
            active_names = sorted(self._active_filters)
            parts.append(Text.from_markup(
                f"[dim]Filter: {', '.join(active_names)}[/dim]\n"
            ))

        visible = self._entries[-50:]

        for e in visible:
            event_type = e.get("type", "")

            if not self._event_matches_filter(event_type):
                continue

            # System messages
            if event_type == "system":
                style = e.get("style", "dim")
                parts.append(Text.from_markup(f"[{style}]{e.get('content', '')}[/{style}]"))
                continue

            # Color-coded event rendering
            color = EVENT_TYPE_COLORS.get(event_type, "dim")
            icon = EVENT_TYPE_ICONS.get(event_type, "\u00b7")  # ·

            # Build event text
            from_id = e.get("from", e.get("worker_id", ""))
            to_id = e.get("to", "")
            content = e.get("content", e.get("error", e.get("message", e.get("reason", ""))))

            squad_color = SQUAD_COLORS.get(from_id, "white") if from_id else "dim"

            if to_id:
                event_text = f"{from_id} \u2192 {to_id}: {str(content)[:70]}"
            elif from_id:
                event_text = f"{from_id}: {str(content)[:70]}"
            elif content:
                event_text = str(content)[:80]
            else:
                event_text = event_type

            parts.append(Text.from_markup(
                f"  [{color}]{icon}[/{color}] [{squad_color}]{from_id[:12]}[/{squad_color}] {event_text}"
            ))

        stream_content.update(Panel(
            Group(*parts),
            title="Workers Live",
            border_style=KANTORKU_THEME["secondary"],
            padding=(0, 1),
        ))

        # Auto-scroll
        try:
            scroll = self.query_one("#workers-stream", VerticalScroll)
            scroll.scroll_end(animate=False)
        except Exception:
            pass
