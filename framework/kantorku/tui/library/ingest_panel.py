"""
IngestPanel — Ingest new material panel for the Library TUI.

Provides an interface for adding new knowledge to the Library.
The user pastes content, the Librarian classifies it, and then
the user can review and save the classified entry.

Workflow:
    1. Paste content into the text area
    2. Click "Analisa Materi →" to trigger Librarian classification
    3. Review the analysis:
       - Suggested title (editable)
       - Suggested categories with "Gunakan" buttons
       - Custom category input
       - Tags display
       - Entry type dropdown
    4. Click "💾 Simpan ke Library" to save

Layout (before analysis):
    ┌──────────────────────────────────────────────────────────────┐
    │  📥 Ingest Materi Baru                                      │
    │  ─────────────────────────────────────────────────────────── │
    │                                                              │
    │  [TextArea for pasting content]                              │
    │                                                              │
    │  [Analisa Materi →]                                         │
    └──────────────────────────────────────────────────────────────┘

Layout (after analysis):
    ┌──────────────────────────────────────────────────────────────┐
    │  📥 Ingest Materi Baru                                      │
    │  ─────────────────────────────────────────────────────────── │
    │  Judul: [________________________]                           │
    │                                                              │
    │  Kategori yang Disarankan:                                   │
    │  📂 Engineering / Backend / Python   [Gunakan]              │
    │  📂 Engineering / DevOps             [Gunakan]              │
    │  📂 Uncategorized                    [Gunakan]              │
    │                                                              │
    │  Kategori Kustom: [___________________] [Gunakan]           │
    │                                                              │
    │  Tipe: [KNOWLEDGE ▾]                                        │
    │  Tag: python, async, concurrency                            │
    │                                                              │
    │  [💾 Simpan ke Library]                                     │
    └──────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import logging
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button, Input, Select, Static, TextArea

from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from kantorku.library.core.models import (
    ENTRY_TYPE_ICONS,
    EntrySource,
    EntryType,
    LibraryEntry,
)
from kantorku.library.core.librarian import Librarian
from kantorku.library.core.indexer import Indexer
from kantorku.library.storage.archive import Archive
from kantorku.library.storage.vectors import VectorStore

logger = logging.getLogger(__name__)

# ── Entry type choices for the dropdown ────────────────────────────────

_ENTRY_TYPE_OPTIONS = [
    ("\U0001f4d6 KNOWLEDGE — Pengetahuan faktual", "knowledge"),
    ("\U0001f4a1 SOLUTION — Solusi dari masalah", "solution"),
    ("\U0001f4ac QA_PAIR — Tanya-jawab", "qa_pair"),
    ("\U0001f527 PROCEDURE — Langkah-langkah", "procedure"),
]


# ── CSS ────────────────────────────────────────────────────────────────

_CSS = """
IngestPanel {
    layout: vertical;
    height: 1fr;
}

#ingest-header {
    height: 3;
    padding: 0 1;
    border-bottom: tall $primary 30%;
    background: $primary 8%;
}

#ingest-content {
    height: 1fr;
    scrollbar-size: 1 1;
    padding: 0 1;
}

#ingest-text-area {
    height: 1fr;
    min-height: 8;
    scrollbar-size: 1 1;
}

#ingest-bottom {
    dock: bottom;
    height: auto;
    padding: 0 1;
    background: $surface;
    border-top: tall $primary 20%;
    layout: vertical;
    gap: 1;
}

#ingest-input-area {
    height: auto;
    padding: 0;
}

.ingest-field-row {
    layout: horizontal;
    height: 3;
    padding: 0 1;
    align: left middle;
}

.ingest-field-label {
    width: 14;
    color: $text;
    text-style: bold;
}

.ingest-field-row Input {
    width: 1fr;
}

#btn-analyze {
    width: 100%;
    background: $primary 15%;
    color: $primary;
    text-style: bold;
    border: tall $primary 40%;
}

#btn-analyze:hover {
    background: $primary 30%;
    color: $text;
}

#btn-save {
    width: 100%;
    background: $success 15%;
    color: $success;
    text-style: bold;
    border: tall $success 40%;
}

#btn-save:hover {
    background: $success 30%;
    color: $text;
}

.category-btn {
    min-width: 8;
    height: 2;
    background: $accent 12%;
    color: $accent;
    border: tall $accent 30%;
    margin-left: 1;
}

.category-btn:hover {
    background: $accent 25%;
    color: $text;
}
"""


class IngestPanel(Static):
    """Ingest new material panel for the Library TUI.

    Provides a two-phase workflow:
    1. **Input phase**: Paste content and trigger analysis
    2. **Review phase**: Review Librarian classification and save

    The Librarian classifies the content, determining entry type,
    keywords, shelf placement, and quality estimate. The user can
    then adjust the classification before saving.
    """

    CSS = _CSS

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._librarian: Librarian | None = None
        self._archive: Archive | None = None
        self._vector_store: VectorStore | None = None
        self._indexer: Indexer | None = None
        self._library_screen: Any = None

        # Analysis state
        self._classification: dict[str, Any] = {}
        self._selected_shelf_path: list[str] = []
        self._selected_entry_type: EntryType = EntryType.KNOWLEDGE
        self._is_analyzing: bool = False
        self._analysis_done: bool = False

    def set_managers(
        self,
        librarian: Librarian,
        archive: Archive,
        vector_store: VectorStore,
        indexer: Indexer | None = None,
        library_screen: Any = None,
    ) -> None:
        """Set manager references for data access.

        Args:
            librarian: The Librarian instance for classification.
            archive: The Archive instance for persistent storage.
            vector_store: The VectorStore for semantic search.
            indexer: The Indexer instance (optional).
            library_screen: The parent LibraryScreen.
        """
        self._librarian = librarian
        self._archive = archive
        self._vector_store = vector_store
        self._indexer = indexer
        self._library_screen = library_screen

    # ── Compose ────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Static(
            "\U0001f4e5 Ingest Materi Baru  [dim]Tambah pengetahuan ke Library[/dim]",
            id="ingest-header",
        )
        with VerticalScroll(id="ingest-content"):
            yield Static(id="ingest-status")
            yield TextArea(
                id="ingest-text-area",
                language="markdown",
            )
        with Vertical(id="ingest-bottom"):
            yield Button(
                "Analisa Materi \u2192", id="btn-analyze"
            )

    # ── Analysis ───────────────────────────────────────────────────────

    async def analyze_content(self, content: str) -> None:
        """Trigger Librarian classification of the provided content.

        Sends the content to the Librarian for classification, then
        renders the analysis results in the panel for user review.

        Args:
            content: The text content to classify.
        """
        if self._is_analyzing:
            return

        if not content.strip():
            self._show_status("[yellow]Konten kosong. Tulis sesuatu dulu.[/yellow]")
            return

        self._is_analyzing = True
        self._show_status("[yellow]\u25d0 Menganalisis materi...[/yellow]")

        try:
            if self._librarian is None:
                self._show_status(
                    "[red]Librarian tidak tersedia. "
                    "Pastikan Library sudah diinisialisasi.[/red]"
                )
                return

            classification = await self._librarian.classify(
                content=content,
                title="",
                user_hint="",
            )

            self._classification = classification
            self._selected_shelf_path = classification.get("shelf_path", [])
            self._selected_entry_type = EntryType(
                classification.get("entry_type", "knowledge")
            )
            self._analysis_done = True

            # Render analysis results
            self._render_analysis(content)

        except Exception as exc:
            logger.error("Content analysis failed: %s", exc)
            self._show_status(
                f"[red]Analisis gagal: {exc}[/red]"
            )

        finally:
            self._is_analyzing = False

    async def save_to_library(self) -> None:
        """Save the classified entry to the Library.

        Uses the Librarian's full ingest pipeline to create, store,
        and index the entry. After saving, refreshes the shelf tree
        and switches to read mode.
        """
        if not self._analysis_done or self._librarian is None:
            self._show_status("[yellow]Analisis belum selesai.[/yellow]")
            return

        try:
            # Get content from text area
            text_area = self.query_one("#ingest-text-area", TextArea)
            content = text_area.text.strip()
            if not content:
                self._show_status("[yellow]Konten kosong.[/yellow]")
                return

            # Get title from input
            title = ""
            try:
                title_input = self.query_one("#input-title", Input)
                title = title_input.value.strip()
            except Exception:
                pass

            # Perform full ingest
            self._show_status("[yellow]\u25d0 Menyimpan ke Library...[/yellow]")

            entry = await self._librarian.ingest(
                content=content,
                title=title,
                source=EntrySource.MANUAL,
                user_hint="",
            )

            # Override classification with user selections if different
            if self._selected_shelf_path != entry.shelf_path:
                entry.shelf_path = self._selected_shelf_path
                entry.touch()

            if self._selected_entry_type != entry.entry_type:
                entry.entry_type = self._selected_entry_type
                entry.touch()

            # Re-persist with user modifications
            if self._archive:
                await self._archive.update(entry)

            # Index the entry
            if self._indexer:
                await self._indexer.index_entry(entry)

            self._show_status(
                f"[green]\u2713 Tersimpan! ID: {entry.id[:8]}... "
                f"Tipe: {entry.entry_type.value} | "
                f"Rak: {entry.shelf_str}[/green]"
            )

            # Reset state
            self._analysis_done = False
            self._classification = {}

            # Refresh shelf tree
            if self._library_screen is not None:
                await self._library_screen.refresh_shelf_tree()
                # Display the saved entry
                await self._library_screen.display_entry(entry)

        except Exception as exc:
            logger.error("Save to library failed: %s", exc)
            self._show_status(f"[red]Gagal menyimpan: {exc}[/red]")

    # ── Rendering ──────────────────────────────────────────────────────

    def _render_analysis(self, original_content: str) -> None:
        """Render the analysis results in the content area.

        Shows suggested title, categories, tags, and entry type
        with controls for the user to review and adjust.

        Args:
            original_content: The original content that was analyzed.
        """
        try:
            content_area = self.query_one("#ingest-content", VerticalScroll)
        except Exception:
            return

        # Remove old widgets and add analysis form
        # We'll add the analysis fields to the bottom area instead
        try:
            bottom_area = self.query_one("#ingest-bottom", Vertical)
            # Remove existing children
            bottom_area.remove_children()

            # Title input
            suggested_title = self._classification.get("summary", "")[:80]
            with Horizontal(classes="ingest-field-row"):
                bottom_area.mount(Static("Judul:", classes="ingest-field-label"))
                title_input = Input(
                    value=suggested_title,
                    placeholder="Judul entri...",
                    id="input-title",
                )
                bottom_area.mount(title_input)

            # Suggested categories
            shelf_path = self._classification.get("shelf_path", [])
            summary_text = self._classification.get("summary", "")

            # Build analysis summary
            parts: list[Any] = []

            # Category display
            if shelf_path:
                shelf_str = " / ".join(shelf_path)
                parts.append(Text.from_markup(
                    f"[bold]Kategori Disarankan:[/bold] \U0001f4c2 {shelf_str}"
                ))
            else:
                parts.append(Text.from_markup(
                    "[bold]Kategori Disarankan:[/bold] [dim]Uncategorized[/dim]"
                ))

            # Tags
            keywords = self._classification.get("keywords", [])
            if keywords:
                tag_str = " ".join(f"#{kw}" for kw in keywords)
                parts.append(Text.from_markup(
                    f"[bold]Tag:[/bold] {tag_str}"
                ))

            # Quality estimate
            quality = self._classification.get("quality_initial", 0.5)
            q_color = "green" if quality > 0.7 else (
                "yellow" if quality > 0.5 else "red"
            )
            parts.append(Text.from_markup(
                f"[bold]Estimasi Kualitas:[/bold] [{q_color}]{quality:.0%}[/{q_color}]"
            ))

            # Confidence
            confidence = self._classification.get("shelf_confidence", 0.0)
            c_color = "green" if confidence > 0.7 else (
                "yellow" if confidence > 0.5 else "red"
            )
            parts.append(Text.from_markup(
                f"[bold]Kepercayaan Rak:[/bold] [{c_color}]{confidence:.0%}[/{c_color}]"
            ))

            # Domain
            domain = self._classification.get("domain", "web_text")
            parts.append(Text.from_markup(
                f"[bold]Domain:[/bold] {domain}"
            ))

            # Summary
            if summary_text:
                parts.append(Text.from_markup(""))
                parts.append(Text.from_markup("[bold]Ringkasan:[/bold]"))
                parts.append(Text.from_markup(f"[dim]{summary_text}[/dim]"))

            # Custom category input
            parts.append(Text.from_markup(""))
            parts.append(Text.from_markup("[bold]Kategori Kustom:[/bold]"))

            # Entry type selection
            type_str = self._selected_entry_type.value
            type_icon = ENTRY_TYPE_ICONS.get(
                self._selected_entry_type, "\U0001f4d6"
            )
            parts.append(Text.from_markup(
                f"[bold]Tipe Entri:[/bold] {type_icon} {type_str}"
            ))

            # Update status
            try:
                status = self.query_one("#ingest-status", Static)
                status.update(
                    Panel(
                        Group(*parts),
                        title="\U0001f4cb Hasil Analisis",
                        border_style="cyan",
                        padding=(0, 1),
                    )
                )
            except Exception:
                pass

            # Add custom category row
            with Horizontal(classes="ingest-field-row"):
                bottom_area.mount(
                    Static("Kategori:", classes="ingest-field-label")
                )
                bottom_area.mount(
                    Input(
                        placeholder="Misalnya: Engineering / Backend / Python",
                        id="input-custom-category",
                    )
                )
                btn_use = Button(
                    "Gunakan", id="btn-use-category", classes="category-btn"
                )
                bottom_area.mount(btn_use)

            # Entry type dropdown
            with Horizontal(classes="ingest-field-row"):
                bottom_area.mount(
                    Static("Tipe:", classes="ingest-field-label")
                )
                bottom_area.mount(
                    Select(
                        _ENTRY_TYPE_OPTIONS,
                        value=self._selected_entry_type.value,
                        id="select-entry-type",
                        allow_blank=False,
                    )
                )

            # Save button
            bottom_area.mount(
                Button(
                    "\U0001f4be Simpan ke Library",
                    id="btn-save",
                )
            )

            # New analysis button
            bottom_area.mount(
                Button(
                    "\U0001f504 Analisa Ulang",
                    id="btn-reanalyze",
                )
            )

        except Exception as exc:
            logger.error("Failed to render analysis: %s", exc)

    def _show_status(self, message: str) -> None:
        """Show a status message in the ingest panel.

        Args:
            message: The status message (may contain Rich markup).
        """
        try:
            status = self.query_one("#ingest-status", Static)
            status.update(message)
        except Exception:
            pass

    # ── Event handlers ─────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        btn_id = event.button.id or ""

        if btn_id == "btn-analyze":
            self._trigger_analysis()
        elif btn_id == "btn-save":
            async def _save() -> None:
                await self.save_to_library()
            self.app.run_worker(_save())
        elif btn_id == "btn-reanalyze":
            self._reset_for_reanalysis()
        elif btn_id == "btn-use-category":
            self._apply_custom_category()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle entry type selection change."""
        if event.select.id == "select-entry-type":
            value = event.value
            if isinstance(value, str) and value in (
                "knowledge", "solution", "qa_pair", "procedure"
            ):
                self._selected_entry_type = EntryType(value)

    def _trigger_analysis(self) -> None:
        """Trigger content analysis from the text area."""
        try:
            text_area = self.query_one("#ingest-text-area", TextArea)
            content = text_area.text.strip()
        except Exception:
            self._show_status("[red]Gagal membaca konten[/red]")
            return

        async def _analyze() -> None:
            await self.analyze_content(content)

        self.app.run_worker(_analyze())

    def _apply_custom_category(self) -> None:
        """Apply the custom category from the input field."""
        try:
            category_input = self.query_one(
                "#input-custom-category", Input
            )
            raw = category_input.value.strip()
            if not raw:
                return

            # Parse category path (supports "/" or " > " separators)
            parts = [p.strip() for p in raw.replace(">", "/").split("/") if p.strip()]
            if parts:
                self._selected_shelf_path = parts
                self._show_status(
                    f"[green]\u2713 Kategori diterapkan: "
                    f"{' / '.join(parts)}[/green]"
                )
        except Exception as exc:
            logger.error("Apply category failed: %s", exc)

    def _reset_for_reanalysis(self) -> None:
        """Reset the panel for a new analysis."""
        self._analysis_done = False
        self._classification = {}

        try:
            # Reset bottom area
            bottom_area = self.query_one("#ingest-bottom", Vertical)
            bottom_area.remove_children()
            bottom_area.mount(
                Button("Analisa Materi \u2192", id="btn-analyze")
            )

            # Clear status
            self._show_status("")
        except Exception:
            pass
