"""
kantorku.tui.office — TUI panels for the KantorKu Office interface.

Provides a 3-panel chat-driven office interface:
- Left:   Manager Chat (conversation with Conductor)
- Center: Tabbed views (Workers Live, Briefing, DAG, Events)
- Right:  Contract Display (13-state progress, TODO list, Accept/Revise)

All panels are reactive (update on data change) and support
both embedded and remote modes via the OfficeConnection.
"""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Footer, Header, Input, Static, TabbedContent, TabPane
from textual.reactive import reactive

from kantorku.tui.office.manager_chat import ManagerChatPanel
from kantorku.tui.office.briefing_room import BriefingRoomPanel
from kantorku.tui.office.dag_panel import DAGPanel
from kantorku.tui.office.workers_live import WorkersLivePanel
from kantorku.tui.office.contract_panel import ContractPanel

from rich.text import Text

__all__ = [
    "ManagerChatPanel",
    "BriefingRoomPanel",
    "DAGPanel",
    "WorkersLivePanel",
    "ContractPanel",
    "OfficePanels",
]


# ── CSS ────────────────────────────────────────────────────────────────

_OFFICE_CSS = """
OfficePanels {
    layout: horizontal;
    height: 1fr;
}

#office-left {
    width: 30%;
    height: 100%;
    border: tall $primary;
    background: $background;
}

#office-center {
    width: 40%;
    height: 100%;
    border: tall $secondary;
    background: $background;
}

#office-right {
    width: 30%;
    height: 100%;
    border: tall $accent;
    background: $background;
}

#office-center-tabs {
    height: 1fr;
}

#office-center-tabs > TabPane {
    padding: 0 1;
}
"""


class OfficePanels(Horizontal):
    """Composite widget arranging all 5 office panels.

    Layout:
        ┌──────────┬──────────────────────┬──────────┐
        │ Manager  │  Workers | Briefing  │ Contract │
        │ Chat     │  DAG | Events       │ Display  │
        │          │                      │          │
        └──────────┴──────────────────────┴──────────┘

    The left panel is the ManagerChatPanel for conversation.
    The center panel has tabbed views for Workers Live,
    Briefing Room, DAG, and an event log.
    The right panel is the ContractPanel for contract review.

    All panels are accessible as attributes for direct data updates.
    """

    CSS = _OFFICE_CSS

    # ── Reactives ──────────────────────────────────────────────────

    contract_state: reactive[str] = reactive("idle")

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    # ── Compose ────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        # Left panel: Manager Chat
        with Vertical(id="office-left"):
            yield ManagerChatPanel()

        # Center panel: Tabbed views
        with Vertical(id="office-center"):
            with TabbedContent(id="office-center-tabs"):
                with TabPane("Workers", id="tab-workers"):
                    yield WorkersLivePanel()
                with TabPane("Briefing", id="tab-briefing"):
                    yield BriefingRoomPanel()
                with TabPane("DAG", id="tab-dag"):
                    yield DAGPanel()
                with TabPane("Events", id="tab-events"):
                    from textual.widgets import RichLog
                    yield RichLog(
                        highlight=True,
                        markup=True,
                        auto_scroll=True,
                        id="office-event-log",
                    )

        # Right panel: Contract Display
        with Vertical(id="office-right"):
            yield ContractPanel()

    # ── Lifecycle ──────────────────────────────────────────────────

    def on_mount(self) -> None:
        """Initialize panel references."""
        pass

    # ── Reactive Watchers ──────────────────────────────────────────

    def watch_contract_state(self, state: str) -> None:
        """Propagate contract state to sub-panels."""
        # Update Manager Chat panel
        try:
            chat = self.query_one(ManagerChatPanel)
            chat.contract_state = state
        except Exception:
            pass

        # Update Workers Live phase
        phase_map = {
            "idle": "idle",
            "manager_thinking": "idle",
            "clarifying": "idle",
            "contract_presented": "idle",
            "awaiting_revision": "idle",
            "team_review": "briefing",
            "todo_review": "briefing",
            "client_feedback": "idle",
            "working": "execution",
            "verifying": "verification",
            "accepted": "execution",
            "done": "done",
            "failed": "failed",
        }
        phase = phase_map.get(state, "idle")
        try:
            workers = self.query_one(WorkersLivePanel)
            workers.phase = phase
        except Exception:
            pass

    # ── Convenience Accessors ──────────────────────────────────────

    @property
    def manager_chat(self) -> ManagerChatPanel | None:
        """Get the Manager Chat panel."""
        try:
            return self.query_one(ManagerChatPanel)
        except Exception:
            return None

    @property
    def workers_live(self) -> WorkersLivePanel | None:
        """Get the Workers Live panel."""
        try:
            return self.query_one(WorkersLivePanel)
        except Exception:
            return None

    @property
    def briefing_room(self) -> BriefingRoomPanel | None:
        """Get the Briefing Room panel."""
        try:
            return self.query_one(BriefingRoomPanel)
        except Exception:
            return None

    @property
    def dag_panel(self) -> DAGPanel | None:
        """Get the DAG panel."""
        try:
            return self.query_one(DAGPanel)
        except Exception:
            return None

    @property
    def contract_panel(self) -> ContractPanel | None:
        """Get the Contract panel."""
        try:
            return self.query_one(ContractPanel)
        except Exception:
            return None
