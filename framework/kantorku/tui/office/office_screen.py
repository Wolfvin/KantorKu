"""
OfficeScreen — Main Office TUI screen for KantorKu.

Composes the full Office interface with a 3-panel layout:
- Left: Manager Chat
- Center: Tabbed views (Workers Live, Briefing, DAG, Events)
- Right: Contract Display

Supports both embedded and remote modes.

Layout:
    ┌─────────────────────────────────────────────────────────────────┐
    │ ⚡ KANTORKU           [Tab: Library] [Ctrl+K: Kantor]  [ESC]   │
    ├──────────────┬──────────────────────────┬──────────────────────┤
    │  MANAGER     │  Workers | Briefing |    │  CONTRACT            │
    │  CHAT        │  DAG | Events             │  DISPLAY             │
    │              │                          │                      │
    │              │                          │                      │
    ├──────────────┴──────────────────────────┴──────────────────────┤
    │ ⚡ Disrupt  │ Session: abc123 │ $0.0042 │ 3 workers │ IDLE     │
    └─────────────────────────────────────────────────────────────────┘

Usage:
    # Push from any KantorKu TUI app
    app.push_screen(OfficeScreen())
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Static

from kantorku.tui.office import OfficePanels
from kantorku.tui.office.manager_chat import ManagerChatPanel
from kantorku.tui.office.briefing_room import BriefingRoomPanel
from kantorku.tui.office.dag_panel import DAGPanel
from kantorku.tui.office.workers_live import WorkersLivePanel
from kantorku.tui.office.contract_panel import ContractPanel

from rich.text import Text

logger = logging.getLogger(__name__)

# ── CSS ────────────────────────────────────────────────────────────────

_CSS = """
OfficeScreen {
    layout: vertical;
    background: $surface;
}

/* ── Top bar ── */
#office-topbar {
    height: 3;
    dock: top;
    background: $primary 15%;
    border-bottom: tall $primary;
    padding: 0 2;
    layout: horizontal;
}

#office-topbar-title {
    width: 1fr;
    color: $text;
    text-style: bold;
    padding: 1 0;
}

#office-topbar-actions {
    width: auto;
    padding: 0 1;
    layout: horizontal;
    gap: 1;
}

.office-topbar-btn {
    min-width: 10;
    height: 2;
    margin: 1 0;
    background: $primary 15%;
    color: $primary;
    border: tall $primary 40%;
}

.office-topbar-btn:hover {
    background: $primary 30%;
    color: $text;
}

/* ── Main area (3-panel) ── */
#office-main {
    height: 1fr;
}

/* ── Bottom status bar ── */
#office-statusbar {
    height: 1;
    dock: bottom;
    background: $surface;
    color: $muted;
    padding: 0 1;
    border-top: tall $primary 20%;
}
"""


class OfficeScreen(Screen):
    """Main Office screen that composes all sub-panels.

    Provides the 3-panel office interface:
    - Left: Manager Chat (conversation with Conductor)
    - Center: Tabbed views — Workers Live, Briefing, DAG, Events
    - Right: Contract Display (13-state progress, Accept/Revise)

    Keyboard bindings:
    - Escape: Return to previous screen
    - Tab: Switch to Library
    - Ctrl+K: Stay in Kantor (Office) mode
    - 1-4: Switch center panel tabs
    - Ctrl+A: Accept contract
    - Ctrl+R: Revise contract
    - Ctrl+I: Disrupt/interrupt work

    Supports both embedded (in-process) and remote (WebSocket)
    modes via OfficeConnection.
    """

    CSS = _CSS

    BINDINGS = [
        Binding("escape", "close_office", "Back", show=True),
        Binding("tab", "switch_to_library", "Library", show=True),
        Binding("ctrl+k", "kantor_mode", "Kantor", show=True),
        Binding("1", "tab_workers", "Workers", show=False),
        Binding("2", "tab_briefing", "Briefing", show=False),
        Binding("3", "tab_dag", "DAG", show=False),
        Binding("4", "tab_events", "Events", show=False),
        Binding("ctrl+a", "accept_contract", "Accept", show=True),
        Binding("ctrl+r", "revise_contract", "Revise", show=True),
        Binding("ctrl+i", "disrupt", "Disrupt", show=True),
    ]

    def __init__(
        self,
        connection: Any | None = None,
        office: Any | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._connection = connection
        self._office = office

        # Session state
        self._session_id: str = ""
        self._contract_state: str = "idle"
        self._pending_contract: dict[str, Any] = {}

    # ── Compose ────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        # Top bar
        with Horizontal(id="office-topbar"):
            yield Static(
                "\u26a1 KANTORKU",
                id="office-topbar-title",
            )
            with Horizontal(id="office-topbar-actions"):
                yield Button(
                    "Tab: Library", id="btn-library", classes="office-topbar-btn"
                )

        # Main 3-panel area
        with Vertical(id="office-main"):
            yield OfficePanels()

        # Bottom status bar
        yield Static(
            "\u26a1 kantorku | Session: -- | Not connected | [dim]1-4: Switch tabs[/dim]",
            id="office-statusbar",
        )

        yield Footer()

    # ── Lifecycle ──────────────────────────────────────────────────

    async def on_mount(self) -> None:
        """Initialize office panels and connections."""
        # Set up event routing from panels
        panels = self.query_one(OfficePanels)

        # Initialize connection if in remote mode
        if self._connection:
            self._setup_remote_mode()
        elif self._office:
            self._setup_embedded_mode()

        self._update_status_bar()

    # ── Actions ────────────────────────────────────────────────────

    def action_close_office(self) -> None:
        """Close the Office screen and return to the previous screen."""
        self.app.pop_screen()

    def action_switch_to_library(self) -> None:
        """Switch to the Library screen."""
        try:
            from kantorku.tui.library.library_screen import LibraryScreen
            self.app.push_screen(LibraryScreen())
        except Exception:
            # Library not available
            pass

    def action_kantor_mode(self) -> None:
        """Stay in Kantor (Office) mode — no-op."""
        pass

    def action_tab_workers(self) -> None:
        """Switch center tab to Workers."""
        self._switch_tab(0)

    def action_tab_briefing(self) -> None:
        """Switch center tab to Briefing."""
        self._switch_tab(1)

    def action_tab_dag(self) -> None:
        """Switch center tab to DAG."""
        self._switch_tab(2)

    def action_tab_events(self) -> None:
        """Switch center tab to Events."""
        self._switch_tab(3)

    async def action_accept_contract(self) -> None:
        """Accept the current contract."""
        panels = self.query_one(OfficePanels)
        chat = panels.manager_chat
        if chat:
            chat.add_system_message("[green]Contract accepted![/green]")
            chat.contract_state = "accepted"

    async def action_revise_contract(self) -> None:
        """Revise the current contract."""
        panels = self.query_one(OfficePanels)
        chat = panels.manager_chat
        if chat:
            chat.add_system_message("[yellow]Revision requested.[/yellow]")
            chat.contract_state = "awaiting_revision"

    async def action_disrupt(self) -> None:
        """Interrupt current work."""
        panels = self.query_one(OfficePanels)
        chat = panels.manager_chat
        if chat:
            chat.add_system_message("[yellow]\u26a1 Work interrupted.[/yellow]")

    # ── Tab Switching ──────────────────────────────────────────────

    def _switch_tab(self, index: int) -> None:
        """Switch the center panel tab by index."""
        try:
            from textual.widgets import TabbedContent
            tabs = self.query_one("#office-center-tabs", TabbedContent)
            # Tab indices: 0=Workers, 1=Briefing, 2=DAG, 3=Events
            tab_ids = ["tab-workers", "tab-briefing", "tab-dag", "tab-events"]
            if 0 <= index < len(tab_ids):
                tabs.active = tab_ids[index]
        except Exception:
            pass

    # ── Event Handlers ─────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks in the top bar."""
        btn_id = event.button.id or ""

        if btn_id == "btn-library":
            self.action_switch_to_library()

    def on_manager_chat_panel_user_message(
        self, event: ManagerChatPanel.UserMessage
    ) -> None:
        """Handle user message from the Manager Chat panel."""
        text = event.text
        self._handle_user_message(text)

    def on_manager_chat_panel_action_requested(
        self, event: ManagerChatPanel.ActionRequested
    ) -> None:
        """Handle action request from the Manager Chat panel."""
        action = event.action
        feedback = event.feedback

        if action == "accept":
            self._do_accept()
        elif action == "revise":
            self._do_revise(feedback)
        elif action == "interrupt":
            self._do_disrupt()

    def on_contract_panel_accept_requested(
        self, event: ContractPanel.AcceptRequested
    ) -> None:
        """Handle Accept button from Contract panel."""
        self._do_accept()

    def on_contract_panel_revise_requested(
        self, event: ContractPanel.ReviseRequested
    ) -> None:
        """Handle Revise button from Contract panel."""
        self._do_revise("")

    # ── Internal ───────────────────────────────────────────────────

    def _handle_user_message(self, text: str) -> None:
        """Process a user message — dispatch to connection or embedded office."""
        panels = self.query_one(OfficePanels)
        chat = panels.manager_chat

        # Handle slash commands
        if text.startswith("/"):
            self._handle_slash_command(text)
            return

        # Show thinking indicator
        if chat:
            chat.start_thinking()

        # Remote mode
        if self._connection:
            self._send_remote_message(text)
        # Embedded mode
        elif self._office:
            self._send_embedded_message(text)
        else:
            # No connection — echo back
            if chat:
                chat.stop_thinking()
                chat.add_manager_message(
                    "I'm not connected yet. Start a server with `/serve` "
                    "or configure a connection."
                )

    def _handle_slash_command(self, text: str) -> None:
        """Handle slash commands via the parent app."""
        try:
            from kantorku.tui.commands import handle_slash_command
            app = self.app
            # Run the command in the app context
            async def _run_cmd():
                result = await handle_slash_command(text, app)
                if result:
                    panels = self.query_one(OfficePanels)
                    chat = panels.manager_chat
                    if chat:
                        chat.add_manager_message(result)
            self.app.run_worker(_run_cmd())
        except Exception as e:
            logger.error("Slash command failed: %s", e)

    def _do_accept(self) -> None:
        """Accept the current contract."""
        panels = self.query_one(OfficePanels)
        chat = panels.manager_chat
        contract = panels.contract_panel

        if chat:
            chat.add_system_message("[green]\u2713 Contract accepted![/green]", "green")
            chat.contract_state = "accepted"
            chat.stop_thinking()

        if contract:
            contract.contract_state = "accepted"

        self._contract_state = "accepted"
        panels.contract_state = "accepted"
        self._update_status_bar()

        # Update workers phase
        workers = panels.workers_live
        if workers:
            workers.phase = "execution"
            workers.add_system_message("[green bold]\u2713 Contract accepted \u2014 work begins![/green bold]")

        # Send to connection/office
        if self._connection:
            self._send_remote_accept()
        elif self._office:
            self._send_embedded_accept()

    def _do_revise(self, feedback: str) -> None:
        """Request a contract revision."""
        panels = self.query_one(OfficePanels)
        chat = panels.manager_chat
        contract = panels.contract_panel

        if chat:
            chat.add_system_message("[yellow]\u270f Revision requested.[/yellow]", "yellow")
            chat.contract_state = "awaiting_revision"
            chat.start_thinking("Manager brainstorming")

        if contract:
            contract.contract_state = "awaiting_revision"
            contract.revision_count = contract.revision_count + 1

        self._contract_state = "awaiting_revision"
        panels.contract_state = "awaiting_revision"
        self._update_status_bar()

        # Update workers
        workers = panels.workers_live
        if workers:
            workers.add_system_message(
                "[yellow bold]\u270f Revision requested: Manager brainstorming with workers...[/yellow bold]"
            )

        # Send to connection/office
        if self._connection:
            self._send_remote_revise(feedback)
        elif self._office:
            self._send_embedded_revise(feedback)

    def _do_disrupt(self) -> None:
        """Interrupt current work."""
        panels = self.query_one(OfficePanels)
        chat = panels.manager_chat

        if chat:
            chat.add_system_message("[yellow]\u26a1 Work interrupted.[/yellow]", "yellow")
            chat.contract_state = "clarifying"
            chat.stop_thinking()

        self._contract_state = "clarifying"
        panels.contract_state = "clarifying"
        self._update_status_bar()

        # Send interrupt
        if self._connection:
            self._send_remote_interrupt()
        elif self._office:
            self._send_embedded_interrupt()

    # ── Remote Mode ────────────────────────────────────────────────

    def _setup_remote_mode(self) -> None:
        """Set up remote mode with OfficeConnection."""
        if not self._connection:
            return

        self._session_id = getattr(self._connection, 'session_id', '')

        # Start event listener
        self._start_remote_event_listener()

    def _start_remote_event_listener(self) -> None:
        """Start listening for remote events."""
        from textual import work

        @work(exclusive=True)
        async def _listen():
            if not self._connection:
                return
            try:
                async for event in self._connection.listen_events():
                    self._process_remote_event(event)
            except Exception as e:
                logger.error("Remote event listener error: %s", e)
                panels = self.query_one(OfficePanels)
                chat = panels.manager_chat
                if chat:
                    chat.add_system_message(f"[red]Connection lost: {e}[/red]")

        _listen()

    def _process_remote_event(self, event: dict[str, Any]) -> None:
        """Process an event received from the remote server."""
        event_type = event.get("type", "")
        panels = self.query_one(OfficePanels)

        # Route events to appropriate panels
        if event_type == "manager_message":
            content = event.get("content", "")
            chat = panels.manager_chat
            if chat:
                chat.stop_thinking()
                chat.add_manager_message(content)
                chat.contract_state = event.get("state", "clarifying")

        elif event_type == "contract_ready":
            contract = event.get("contract", {})
            chat = panels.manager_chat
            contract_panel = panels.contract_panel

            if chat:
                chat.stop_thinking()
                chat.contract_state = "contract_presented"

            if contract_panel:
                contract_panel.contract_data = contract
                contract_panel.contract_state = "contract_presented"

            self._pending_contract = contract
            self._contract_state = "contract_presented"
            panels.contract_state = "contract_presented"

        elif event_type == "work_started":
            self._contract_state = "working"
            panels.contract_state = "working"
            chat = panels.manager_chat
            if chat:
                chat.contract_state = "working"

        elif event_type == "work_done":
            result = event.get("result", {})
            self._contract_state = "done"
            panels.contract_state = "done"
            contract_panel = panels.contract_panel
            if contract_panel:
                contract_panel.work_result = result
                contract_panel.contract_state = "done"
            chat = panels.manager_chat
            if chat:
                chat.contract_state = "done"

        else:
            # Route to sub-panels
            workers = panels.workers_live
            briefing = panels.briefing_room
            dag = panels.dag_panel

            if workers:
                workers.add_event(event)
            if briefing:
                briefing.add_event(event)
            if dag:
                dag.add_event(event)

        self._update_status_bar()

    def _send_remote_message(self, text: str) -> None:
        """Send a message via remote connection."""
        from textual import work

        @work(exclusive=False)
        async def _send():
            if not self._connection:
                return
            try:
                async for event in self._connection.send_message(text):
                    self._process_remote_event(event)
            except Exception as e:
                logger.error("Remote send failed: %s", e)
                panels = self.query_one(OfficePanels)
                chat = panels.manager_chat
                if chat:
                    chat.stop_thinking()
                    chat.add_system_message(f"[red]Send failed: {e}[/red]")

        _send()

    def _send_remote_accept(self) -> None:
        """Send accept via remote connection."""
        from textual import work

        @work(exclusive=False)
        async def _accept():
            if not self._connection:
                return
            try:
                result = await self._connection.accept_contract()
                if result:
                    self._process_remote_event(result)
            except Exception as e:
                logger.error("Remote accept failed: %s", e)

        _accept()

    def _send_remote_revise(self, feedback: str) -> None:
        """Send revision via remote connection."""
        from textual import work

        @work(exclusive=False)
        async def _revise():
            if not self._connection:
                return
            try:
                async for event in self._connection.revise_contract(feedback):
                    self._process_remote_event(event)
            except Exception as e:
                logger.error("Remote revise failed: %s", e)

        _revise()

    def _send_remote_interrupt(self) -> None:
        """Send interrupt via remote connection."""
        from textual import work

        @work(exclusive=False)
        async def _interrupt():
            if not self._connection:
                return
            try:
                await self._connection.send_interrupt()
            except Exception as e:
                logger.error("Remote interrupt failed: %s", e)

        _interrupt()

    # ── Embedded Mode ──────────────────────────────────────────────

    def _setup_embedded_mode(self) -> None:
        """Set up embedded mode with in-process Office."""
        if not self._office:
            return

        # Get session info
        if hasattr(self._office, 'session_id'):
            self._session_id = self._office.session_id

        # Subscribe to events
        if hasattr(self._office, 'bus'):
            self._subscribe_embedded_events()

    def _subscribe_embedded_events(self) -> None:
        """Subscribe to embedded office events."""
        try:
            bus = self._office.bus
            # Subscribe to all events and route to panels
            async def _on_event(event_data: dict[str, Any]) -> None:
                self.call_from_thread(self._process_embedded_event, event_data)

            # Register subscriber if bus supports it
            if hasattr(bus, 'subscribe'):
                bus.subscribe("**", _on_event)
        except Exception as e:
            logger.error("Failed to subscribe to embedded events: %s", e)

    def _process_embedded_event(self, event: dict[str, Any]) -> None:
        """Process an event from the embedded office."""
        # Same processing as remote events
        self._process_remote_event(event)

    def _send_embedded_message(self, text: str) -> None:
        """Send a message to the embedded office."""
        from textual import work

        @work(exclusive=False)
        async def _send():
            if not self._office:
                return
            try:
                if hasattr(self._office, 'conductor'):
                    async for event in self._office.conductor.understand_client(
                        self._session_id, text
                    ):
                        self._process_embedded_event(event)
                else:
                    panels = self.query_one(OfficePanels)
                    chat = panels.manager_chat
                    if chat:
                        chat.stop_thinking()
                        chat.add_manager_message(
                            "Office is running but no conductor is available."
                        )
            except Exception as e:
                logger.error("Embedded send failed: %s", e)
                panels = self.query_one(OfficePanels)
                chat = panels.manager_chat
                if chat:
                    chat.stop_thinking()
                    chat.add_system_message(f"[red]Error: {e}[/red]")

        _send()

    def _send_embedded_accept(self) -> None:
        """Send accept to the embedded office."""
        if self._office and hasattr(self._office, 'conductor'):
            try:
                import asyncio
                asyncio.create_task(
                    self._office.conductor.mark_working(self._session_id)
                )
            except Exception as e:
                logger.error("Embedded accept failed: %s", e)

    def _send_embedded_revise(self, feedback: str) -> None:
        """Send revision to the embedded office."""
        from textual import work

        @work(exclusive=False)
        async def _revise():
            if not self._office:
                return
            try:
                if hasattr(self._office, 'conductor'):
                    async for event in self._office.conductor.revise_contract(
                        self._session_id, feedback
                    ):
                        self._process_embedded_event(event)
            except Exception as e:
                logger.error("Embedded revise failed: %s", e)

        _revise()

    def _send_embedded_interrupt(self) -> None:
        """Send interrupt to the embedded office."""
        # In embedded mode, interrupt just pauses the conductor
        if self._office and hasattr(self._office, 'conductor'):
            logger.info("Interrupt requested in embedded mode")

    # ── Status Bar ─────────────────────────────────────────────────

    def _update_status_bar(self) -> None:
        """Update the bottom status bar with current state."""
        try:
            statusbar = self.query_one("#office-statusbar", Static)
        except Exception:
            return

        conn_status = "Not connected"
        if self._connection:
            from kantorku.tui.connection import ConnectionState
            conn_status = self._connection.state.value

        session_str = self._session_id[:8] if self._session_id else "--"
        state_str = self._contract_state.upper()

        statusbar.update(
            f"\u26a1 kantorku | Session: {session_str} | {conn_status} | "
            f"[cyan]{state_str}[/cyan] | [dim]1-4: Switch tabs | Ctrl+A: Accept | Ctrl+R: Revise | Ctrl+I: Disrupt[/dim]"
        )
