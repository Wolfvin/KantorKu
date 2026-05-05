"""
LibraryScreen — Main Library TUI screen for KantorKu.

Composes the full Library interface with a left shelf panel,
right content area, and bottom ask bar. Supports four modes:
Browse, Read, Ask, and Ingest.

Layout:
    ┌─────────────────────────────────────────────────────────────────┐
    │ 📚 PERPUSTAKAAN           [Tab: Kantor] [Ctrl+F: Cari]  [ESC]  │
    ├──────────────────┬──────────────────────────────────────────────┤
    │  RAK BUKU        │                                              │
    │  ─────────────   │           [PANEL KANAN]                      │
    │                  │                                              │
    │  [ShelfPanel]    │     Browse / Baca / Tanya / Ingest           │
    │                  │                                              │
    ├──────────────────┴──────────────────────────────────────────────┤
    │ 🔍 Tanya: [___________________________________________] [Kirim]  │
    └─────────────────────────────────────────────────────────────────┘

Usage:
    # Push from any KantorKu TUI app
    app.push_screen(LibraryScreen())
"""

from __future__ import annotations

import logging
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Static

from kantorku.library.core.models import EntryType, LibraryEntry
from kantorku.library.storage.archive import Archive
from kantorku.library.storage.hot_index import HotIndex
from kantorku.library.storage.vectors import VectorStore
from kantorku.library.core.librarian import Librarian
from kantorku.library.core.archivist import Archivist
from kantorku.library.core.shelf import ShelfManager
from kantorku.library.core.indexer import Indexer

from kantorku.tui.library.shelf_panel import ShelfPanel
from kantorku.tui.library.reader_panel import ReaderPanel
from kantorku.tui.library.ask_panel import AskPanel
from kantorku.tui.library.ingest_panel import IngestPanel

logger = logging.getLogger(__name__)

# ── Default paths ──────────────────────────────────────────────────────

_DEFAULT_ARCHIVE_PATH = "data/library/archive.db"
_DEFAULT_VECTOR_DIR = "data/library/vectors"
_DEFAULT_HOT_INDEX_PATH = "data/library/hot_index.duckdb"

# ── CSS ────────────────────────────────────────────────────────────────

_CSS = """
LibraryScreen {
    layout: vertical;
    background: $surface;
}

/* ── Top bar ── */
#library-topbar {
    height: 3;
    dock: top;
    background: $primary 15%;
    border-bottom: tall $primary;
    padding: 0 2;
    layout: horizontal;
}

#library-topbar-title {
    width: 1fr;
    color: $text;
    text-style: bold;
    padding: 1 0;
}

#library-topbar-actions {
    width: auto;
    padding: 0 1;
    layout: horizontal;
    gap: 1;
}

.topbar-btn {
    min-width: 10;
    height: 2;
    margin: 1 0;
    background: $primary 15%;
    color: $primary;
    border: tall $primary 40%;
}

.topbar-btn:hover {
    background: $primary 30%;
    color: $text;
}

/* ── Main area ── */
#library-main {
    height: 1fr;
    layout: horizontal;
}

/* ── Left shelf panel ── */
#shelf-panel {
    width: 25%;
    min-width: 24;
    max-width: 40;
    height: 1fr;
    border-right: tall $primary 30%;
    background: $surface;
}

/* ── Right content area ── */
#content-area {
    width: 75%;
    height: 1fr;
    layout: vertical;
    background: $surface;
}

#content-display {
    height: 1fr;
    scrollbar-size: 1 1;
}

/* ── Bottom ask bar ── */
#library-bottombar {
    height: 3;
    dock: bottom;
    background: $primary 10%;
    border-top: tall $primary 30%;
    padding: 0 1;
    layout: horizontal;
}

#ask-label {
    width: auto;
    color: $primary;
    padding: 1 1 0 0;
    text-style: bold;
}

#ask-input {
    width: 1fr;
}

#ask-submit-btn {
    width: 10;
    margin-left: 1;
    background: $primary 15%;
    color: $primary;
    text-style: bold;
    border: tall $primary 40%;
}

#ask-submit-btn:hover {
    background: $primary 30%;
    color: $text;
}
"""


class LibraryScreen(Screen):
    """Main Library screen that composes all sub-panels.

    Provides four interaction modes:
    - **browse**: Browse shelf tree and entry list (default)
    - **read**: Read a full entry with actions (helpful, edit, etc.)
    - **ask**: Ask the Archivist a question
    - **ingest**: Ingest new material into the Library

    The left panel always shows the shelf tree. The right panel
    switches content based on the current mode.

    State:
        _current_mode: One of "browse", "read", "ask", "ingest"
        _selected_entry: The currently selected LibraryEntry (or None)
        _current_shelf_path: The current shelf path being browsed
    """

    CSS = _CSS

    BINDINGS = [
        Binding("escape", "close_library", "Close", show=True),
        Binding("ctrl+f", "focus_search", "Cari", show=True),
        Binding("tab", "switch_to_office", "Kantor", show=True),
        Binding("1", "mode_browse", "Browse", show=False),
        Binding("2", "mode_read", "Baca", show=False),
        Binding("3", "mode_ask", "Tanya", show=False),
        Binding("4", "mode_ingest", "Ingest", show=False),
    ]

    def __init__(
        self,
        archive_path: str = _DEFAULT_ARCHIVE_PATH,
        vector_dir: str = _DEFAULT_VECTOR_DIR,
        hot_index_path: str = _DEFAULT_HOT_INDEX_PATH,
        provider_router: Any | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._archive_path = archive_path
        self._vector_dir = vector_dir
        self._hot_index_path = hot_index_path
        self._provider_router = provider_router

        # Library components (initialized in on_mount)
        self._archive: Archive | None = None
        self._hot_index: HotIndex | None = None
        self._vector_store: VectorStore | None = None
        self._librarian: Librarian | None = None
        self._archivist: Archivist | None = None
        self._shelf_manager: ShelfManager | None = None
        self._indexer: Indexer | None = None

        # UI state
        self._current_mode: str = "browse"
        self._selected_entry: LibraryEntry | None = None
        self._current_shelf_path: list[str] = []

    # ── Compose ────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        # Top bar
        with Horizontal(id="library-topbar"):
            yield Static(
                "\U0001f4da PERPUSTAKAAN",
                id="library-topbar-title",
            )
            with Horizontal(id="library-topbar-actions"):
                yield Button(
                    "Tab: Kantor", id="btn-office", classes="topbar-btn"
                )
                yield Button(
                    "Ctrl+F: Cari", id="btn-search", classes="topbar-btn"
                )

        # Main area: left shelf + right content
        with Horizontal(id="library-main"):
            yield ShelfPanel(id="shelf-panel")
            with Vertical(id="content-area"):
                yield ReaderPanel(id="content-display")

        # Bottom ask bar
        with Horizontal(id="library-bottombar"):
            yield Static("\U0001f50d Tanya:", id="ask-label")
            yield Input(
                placeholder="Tulis pertanyaan untuk Archivist...",
                id="ask-input",
            )
            yield Button("Kirim", id="ask-submit-btn")

        yield Footer()

    # ── Lifecycle ──────────────────────────────────────────────────────

    async def on_mount(self) -> None:
        """Initialize storage backends and load shelf tree."""
        try:
            # Initialize storage
            self._archive = Archive(self._archive_path)
            await self._archive.initialize()

            self._vector_store = VectorStore(self._vector_dir)
            await self._vector_store.initialize()
            self._vector_store.set_archive(self._archive)

            self._hot_index = HotIndex(self._hot_index_path)
            await self._hot_index.initialize()

            # Initialize Library components
            self._shelf_manager = ShelfManager(archive=self._archive)
            self._librarian = Librarian(
                archive=self._archive,
                vector_store=self._vector_store,
                provider_router=self._provider_router,
            )
            self._archivist = Archivist(
                archive=self._archive,
                vector_store=self._vector_store,
                provider_router=self._provider_router,
            )
            self._indexer = Indexer(
                archive=self._archive,
                vector_store=self._vector_store,
                hot_index=self._hot_index,
            )

            # Pass references to sub-panels
            shelf_panel = self.query_one("#shelf-panel", ShelfPanel)
            shelf_panel.set_managers(
                shelf_manager=self._shelf_manager,
                archive=self._archive,
                library_screen=self,
            )

            content_area = self.query_one("#content-display", ReaderPanel)
            content_area.set_managers(
                archive=self._archive,
                archivist=self._archivist,
                library_screen=self,
            )

            # Load shelf tree
            await shelf_panel.load_tree()

        except Exception as exc:
            logger.error("Failed to initialize Library: %s", exc)
            # Show error in content area
            try:
                content_area = self.query_one("#content-display", ReaderPanel)
                content_area.show_error(
                    f"Gagal menginisialisasi Library:\n{exc}"
                )
            except Exception:
                pass

    # ── Actions ────────────────────────────────────────────────────────

    def action_close_library(self) -> None:
        """Close the Library screen and return to the previous screen."""
        self.app.pop_screen()

    def action_focus_search(self) -> None:
        """Focus the ask input bar."""
        try:
            ask_input = self.query_one("#ask-input", Input)
            ask_input.focus()
        except Exception:
            pass

    def action_switch_to_office(self) -> None:
        """Switch back to the office screen."""
        self.action_close_library()

    def action_mode_browse(self) -> None:
        """Switch to browse mode."""
        self._switch_mode("browse")

    def action_mode_read(self) -> None:
        """Switch to read mode."""
        self._switch_mode("read")

    def action_mode_ask(self) -> None:
        """Switch to ask mode."""
        self._switch_mode("ask")

    def action_mode_ingest(self) -> None:
        """Switch to ingest mode."""
        self._switch_mode("ingest")

    # ── Mode switching ─────────────────────────────────────────────────

    def _switch_mode(self, mode: str) -> None:
        """Switch the right panel to display a different mode.

        Args:
            mode: One of "browse", "read", "ask", "ingest".
        """
        if mode == self._current_mode:
            return

        old_mode = self._current_mode
        self._current_mode = mode
        logger.debug("Switching mode: %s → %s", old_mode, mode)

        try:
            content_area = self.query_one("#content-area", Vertical)

            # Remove existing content widget
            existing = content_area.query_one("#content-display")
            existing.remove()

            # Mount the appropriate panel
            if mode == "browse":
                content_area.mount(ReaderPanel(id="content-display"))
            elif mode == "read":
                content_area.mount(ReaderPanel(id="content-display"))
            elif mode == "ask":
                ask_panel = AskPanel(id="content-display")
                if self._archivist:
                    ask_panel.set_managers(
                        archivist=self._archivist,
                        archive=self._archive,
                        library_screen=self,
                    )
                content_area.mount(ask_panel)
            elif mode == "ingest":
                ingest_panel = IngestPanel(id="content-display")
                if self._librarian and self._archive and self._vector_store:
                    ingest_panel.set_managers(
                        librarian=self._librarian,
                        archive=self._archive,
                        vector_store=self._vector_store,
                        indexer=self._indexer,
                        library_screen=self,
                    )
                content_area.mount(ingest_panel)

            # Set up managers for newly mounted panels
            new_panel = content_area.query_one("#content-display")
            if isinstance(new_panel, ReaderPanel) and self._archive:
                new_panel.set_managers(
                    archive=self._archive,
                    archivist=self._archivist,
                    library_screen=self,
                )

        except Exception as exc:
            logger.error("Failed to switch mode to %s: %s", mode, exc)

    # ── Panel update methods ───────────────────────────────────────────

    async def display_entry(self, entry: LibraryEntry) -> None:
        """Display a LibraryEntry in the reader panel.

        Args:
            entry: The LibraryEntry to display.
        """
        self._selected_entry = entry
        self._current_mode = "read"

        try:
            content_area = self.query_one("#content-area", Vertical)

            # Remove existing content widget
            try:
                existing = content_area.query_one("#content-display")
                existing.remove()
            except Exception:
                pass

            # Mount a fresh ReaderPanel
            reader = ReaderPanel(id="content-display")
            content_area.mount(reader)

            if self._archive and self._archivist:
                reader.set_managers(
                    archive=self._archive,
                    archivist=self._archivist,
                    library_screen=self,
                )

            await reader.display_entry(entry)

            # Record usage
            if self._archive:
                try:
                    await self._archive.record_usage(entry.id)
                except Exception:
                    pass

        except Exception as exc:
            logger.error("Failed to display entry %s: %s", entry.id, exc)

    async def open_ask_panel(self) -> None:
        """Switch to the Ask panel for interacting with the Archivist."""
        self._switch_mode("ask")

    async def open_ingest_panel(self) -> None:
        """Switch to the Ingest panel for adding new material."""
        self._switch_mode("ingest")

    async def refresh_shelf_tree(self) -> None:
        """Refresh the shelf tree after changes (ingest, move, delete)."""
        try:
            shelf_panel = self.query_one("#shelf-panel", ShelfPanel)
            await shelf_panel.load_tree()
        except Exception as exc:
            logger.error("Failed to refresh shelf tree: %s", exc)

    # ── Event handlers ─────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks in the top bar and bottom bar."""
        btn_id = event.button.id or ""

        if btn_id == "btn-office":
            self.action_switch_to_office()
        elif btn_id == "btn-search":
            self.action_focus_search()
        elif btn_id == "ask-submit-btn":
            self._handle_ask_submit()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in the ask input bar."""
        if event.input.id == "ask-input":
            self._handle_ask_submit()

    def _handle_ask_submit(self) -> None:
        """Process a question from the bottom ask bar."""
        try:
            ask_input = self.query_one("#ask-input", Input)
            question = ask_input.value.strip()
            if not question:
                return

            ask_input.value = ""

            # Switch to ask mode and send the question
            self._switch_mode("ask")

            # After switching, get the ask panel and submit
            try:
                from textual.worker import get_current_worker

                async def _submit() -> None:
                    try:
                        ask_panel = self.query_one(
                            "#content-display", AskPanel
                        )
                        await ask_panel.ask_question(question)
                    except Exception as exc:
                        logger.error("Ask submit failed: %s", exc)

                self.app.run_worker(_submit())
            except Exception:
                pass

        except Exception as exc:
            logger.error("Handle ask submit failed: %s", exc)

    # ── Properties ─────────────────────────────────────────────────────

    @property
    def current_mode(self) -> str:
        """Current interaction mode."""
        return self._current_mode

    @property
    def selected_entry(self) -> LibraryEntry | None:
        """Currently selected entry."""
        return self._selected_entry

    @property
    def current_shelf_path(self) -> list[str]:
        """Current shelf path being browsed."""
        return self._current_shelf_path

    @property
    def archive(self) -> Archive | None:
        """The Archive instance."""
        return self._archive

    @property
    def shelf_manager(self) -> ShelfManager | None:
        """The ShelfManager instance."""
        return self._shelf_manager
