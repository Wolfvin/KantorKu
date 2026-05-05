"""
ShelfPanel — Never-ending shelf panel (left sidebar) for the Library TUI.

Displays a hierarchical shelf tree with icons and an entry list for
the selected shelf. Supports breadcrumb navigation and infinite
drill-down into sub-shelves.

Layout:
    ┌──────────────────┐
    │  RAK BUKU        │
    │  ─────────────   │
    │  📂 Engineering  │
    │  📂 Mathematics  │
    │  📂 Science      │
    │                  │
    │  ── Engineering ─│
    │  📖 Entry 1  ✓  │
    │  💡 Entry 2  ○  │
    │  💬 Entry 3  ✓  │
    │  🔧 Entry 4  ○  │
    │                  │
    │  [↑ Naik]        │
    │  [+ Sarangkan]   │
    └──────────────────┘

Entry type icons:
    KNOWLEDGE = 📖  (white)
    SOLUTION  = 💡  (yellow)
    QA_PAIR   = 💬  (cyan)
    PROCEDURE = 🔧  (green)

Verified icon:
    ✓ (green) or ○ (gray)
"""

from __future__ import annotations

import logging
from typing import Any

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Button, Static

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from kantorku.library.core.models import (
    ENTRY_TYPE_COLORS,
    ENTRY_TYPE_ICONS,
    EntryType,
    LibraryEntry,
    ShelfNode,
)
from kantorku.library.core.shelf import ShelfManager
from kantorku.library.storage.archive import Archive

logger = logging.getLogger(__name__)

# ── CSS ────────────────────────────────────────────────────────────────

_CSS = """
ShelfPanel {
    layout: vertical;
    height: 1fr;
}

#shelf-header {
    height: 2;
    color: $primary;
    text-style: bold;
    padding: 0 1;
    border-bottom: tall $primary 30%;
}

#shelf-breadcrumb {
    height: 1;
    color: $text-muted;
    padding: 0 1;
    background: $primary 8%;
}

#shelf-tree-area {
    height: 1fr;
    scrollbar-size: 1 1;
    padding: 0;
}

#shelf-entry-area {
    height: auto;
    max-height: 16;
    scrollbar-size: 1 1;
    padding: 0;
    border-top: tall $primary 20%;
}

#shelf-bottom-btns {
    dock: bottom;
    height: auto;
    padding: 0 1;
    gap: 1;
    layout: vertical;
}

#btn-navigate-up {
    width: 100%;
    background: $primary 12%;
    color: $primary;
    border: tall $primary 30%;
}

#btn-navigate-up:hover {
    background: $primary 25%;
    color: $text;
}

#btn-add-shelf {
    width: 100%;
    background: $accent 12%;
    color: $accent;
    border: tall $accent 30%;
}

#btn-add-shelf:hover {
    background: $accent 25%;
    color: $text;
}
"""


class ShelfPanel(Static):
    """Never-ending shelf panel (left sidebar) for the Library TUI.

    Displays two sections:
    1. **Shelf Tree**: Hierarchical navigation with expand/collapse
    2. **Entry List**: Entries within the currently selected shelf

    Supports breadcrumb navigation showing the current path,
    and buttons to navigate up or add a new shelf.

    Messages:
        ShelfSelected: Emitted when a shelf is clicked
        EntrySelected: Emitted when an entry is clicked
    """

    CSS = _CSS

    # ── Messages ───────────────────────────────────────────────────────

    class ShelfSelected(Message):
        """Posted when a shelf node is selected."""

        def __init__(self, path: list[str]) -> None:
            super().__init__()
            self.path: list[str] = path

    class EntrySelected(Message):
        """Posted when a library entry is selected."""

        def __init__(self, entry_id: str) -> None:
            super().__init__()
            self.entry_id: str = entry_id

    # ── Init ───────────────────────────────────────────────────────────

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._shelf_manager: ShelfManager | None = None
        self._archive: Archive | None = None
        self._library_screen: Any = None

        # State
        self._shelf_tree: ShelfNode | None = None
        self._current_shelf_path: list[str] = []
        self._current_entries: list[LibraryEntry] = []
        self._expanded_nodes: set[str] = set()  # path_str → expanded?

    def set_managers(
        self,
        shelf_manager: ShelfManager,
        archive: Archive,
        library_screen: Any = None,
    ) -> None:
        """Set the manager references for data access.

        Args:
            shelf_manager: The ShelfManager for tree operations.
            archive: The Archive for entry retrieval.
            library_screen: Reference to the parent LibraryScreen.
        """
        self._shelf_manager = shelf_manager
        self._archive = archive
        self._library_screen = library_screen

    # ── Compose ────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Static("RAK BUKU", id="shelf-header")
        yield Static("", id="shelf-breadcrumb")
        with VerticalScroll(id="shelf-tree-area"):
            yield Static(id="shelf-tree-content")
        with VerticalScroll(id="shelf-entry-area"):
            yield Static(id="shelf-entry-content")
        with Vertical(id="shelf-bottom-btns"):
            yield Button("\u2191 Naik", id="btn-navigate-up")
            yield Button("+ Sarangkan Rak", id="btn-add-shelf")

    # ── Data loading ───────────────────────────────────────────────────

    async def load_tree(self) -> None:
        """Load the shelf tree from ShelfManager and render it."""
        if self._shelf_manager is None:
            self._render_tree_error("ShelfManager tidak tersedia")
            return

        try:
            self._shelf_tree = await self._shelf_manager.get_tree()
            self._render_tree()
        except Exception as exc:
            logger.error("Failed to load shelf tree: %s", exc)
            self._render_tree_error(f"Gagal memuat rak: {exc}")

    async def navigate_to_shelf(self, path: list[str]) -> None:
        """Navigate into a specific shelf and display its entries.

        Args:
            path: The shelf path segments to navigate to.
        """
        self._current_shelf_path = list(path)
        await self._load_entries()

        # Update breadcrumb
        self._update_breadcrumb()

        # Notify parent
        self.post_message(self.ShelfSelected(path))

    async def navigate_up(self) -> None:
        """Go up one level in the shelf hierarchy."""
        if self._current_shelf_path:
            self._current_shelf_path = self._current_shelf_path[:-1]
            await self._load_entries()
            self._update_breadcrumb()

    async def select_entry(self, entry_id: str) -> None:
        """Select an entry to read.

        Args:
            entry_id: The ID of the entry to select.
        """
        if self._archive is None:
            return

        try:
            entry = await self._archive.get(entry_id)
            if entry is not None and self._library_screen is not None:
                await self._library_screen.display_entry(entry)
                self.post_message(self.EntrySelected(entry_id))
        except Exception as exc:
            logger.error("Failed to select entry %s: %s", entry_id, exc)

    # ── Rendering ──────────────────────────────────────────────────────

    def _render_tree(self) -> None:
        """Render the shelf tree using Rich Tree."""
        if self._shelf_tree is None:
            return

        try:
            tree_content = self.query_one("#shelf-tree-content", Static)
        except Exception:
            return

        tree = Tree("\U0001f3db Perpustakaan", guide_style="dim")
        tree.expanded = True

        if self._shelf_tree.children:
            for child in self._shelf_tree.children:
                self._add_tree_node(tree, child)
        else:
            tree.add("[dim]Belum ada rak[/dim]")

        tree_content.update(tree)

    def _add_tree_node(self, parent: Any, node: ShelfNode) -> None:
        """Recursively add shelf nodes to the Rich Tree.

        Args:
            parent: The Rich Tree parent node.
            node: The ShelfNode to render.
        """
        # Determine icon
        if node.children:
            icon = "\U0001f4c2"  # 📂 (has children / expanded)
        else:
            icon = "\U0001f4c1"  # 📁 (leaf shelf)

        # Entry count badge
        count_str = f" ({node.entry_count})" if node.entry_count > 0 else ""

        # Quality indicator
        quality_str = ""
        if node.quality_avg > 0.7:
            quality_str = " \u2605"  # ★
        elif node.quality_avg > 0.5:
            quality_str = " \u25cb"  # ○

        path_key = " / ".join(node.path)
        is_expanded = path_key in self._expanded_nodes

        label = f"{icon} {node.name}{count_str}{quality_str}"
        branch = parent.add(label, style="white")

        if is_expanded and node.children:
            for child in node.children:
                self._add_tree_node(branch, child)

    def _render_entry_list(self) -> None:
        """Render the list of entries in the current shelf."""
        try:
            entry_content = self.query_one("#shelf-entry-content", Static)
        except Exception:
            return

        if not self._current_entries:
            entry_content.update(
                Panel(
                    "[dim]Pilih rak untuk melihat entri[/dim]",
                    border_style="dim",
                    padding=(0, 1),
                )
            )
            return

        table = Table(
            show_header=True,
            header_style="bold",
            show_lines=False,
            box=None,
            padding=(0, 1),
        )
        table.add_column("", width=2)  # Type icon
        table.add_column("Judul", ratio=1)
        table.add_column("Q", width=3)  # Quality
        table.add_column("", width=1)  # Verified

        for entry in self._current_entries[:50]:
            type_icon = ENTRY_TYPE_ICONS.get(entry.entry_type, "\U0001f4d6")
            color = ENTRY_TYPE_COLORS.get(entry.entry_type, "white")

            # Title (truncated)
            title = entry.title or "(tanpa judul)"
            if len(title) > 35:
                title = title[:32] + "..."

            # Quality score
            quality = f"{entry.quality_score:.0%}"

            # Verified icon
            verified = "\u2713" if entry.verified else "\u25cb"
            v_color = "green" if entry.verified else "dim"

            table.add_row(
                f"[{color}]{type_icon}[/{color}]",
                f"[{color}]{title}[/{color}]",
                quality,
                f"[{v_color}]{verified}[/{v_color}]",
            )

        entry_content.update(table)

    def _render_tree_error(self, message: str) -> None:
        """Show an error message in the tree area."""
        try:
            tree_content = self.query_one("#shelf-tree-content", Static)
            tree_content.update(
                Panel(
                    f"[red]{message}[/red]",
                    border_style="red",
                    padding=(0, 1),
                )
            )
        except Exception:
            pass

    def _update_breadcrumb(self) -> None:
        """Update the breadcrumb navigation display."""
        try:
            breadcrumb = self.query_one("#shelf-breadcrumb", Static)
        except Exception:
            return

        if not self._current_shelf_path:
            breadcrumb.update("[dim]Perpustakaan[/dim]")
        else:
            parts = ["Perpustakaan"] + self._current_shelf_path
            breadcrumb.update(" \u203a ".join(parts))

    async def _load_entries(self) -> None:
        """Load entries for the current shelf path."""
        if self._shelf_manager is None:
            return

        try:
            if self._current_shelf_path:
                self._current_entries = await self._shelf_manager.get_shelf_entries(
                    self._current_shelf_path, limit=50
                )
            else:
                # Root level: show recent entries
                if self._archive:
                    self._current_entries = await self._archive.get_all(
                        limit=20
                    )
                else:
                    self._current_entries = []

            self._render_entry_list()

            # Also re-render tree to reflect navigation state
            self._render_tree()

        except Exception as exc:
            logger.error("Failed to load entries: %s", exc)
            self._current_entries = []
            self._render_entry_list()

    # ── Event handlers ─────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        btn_id = event.button.id or ""

        if btn_id == "btn-navigate-up":
            async def _nav_up() -> None:
                await self.navigate_up()
            self.app.run_worker(_nav_up())

        elif btn_id == "btn-add-shelf":
            self._prompt_add_shelf()

    def _prompt_add_shelf(self) -> None:
        """Show a prompt for creating a new shelf.

        For now, we use a simple inline approach. In the future,
        this could be a modal dialog.
        """
        # TODO: Implement modal dialog for shelf creation
        try:
            entry_content = self.query_one("#shelf-entry-content", Static)
            entry_content.update(
                Panel(
                    "[yellow]Fitur sarangkan rak segera hadir![/yellow]\n"
                    "[dim]Gunakan Ingest panel untuk menambah konten baru[/dim]",
                    border_style="yellow",
                    padding=(0, 1),
                )
            )
        except Exception:
            pass
