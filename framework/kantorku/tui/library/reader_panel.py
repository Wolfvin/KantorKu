"""
ReaderPanel — Entry reading panel (right side) for the Library TUI.

Displays the full content of a LibraryEntry rendered as Markdown,
with a header showing metadata and action buttons for feedback,
editing, related entries, and export.

Layout:
    ┌──────────────────────────────────────────────────────────────┐
    │  📖 Entry Title          Q:75%  👁 12  👍 5  ✓ verified    │
    │  📂 Engineering / Backend / Python                          │
    │  ─────────────────────────────────────────────────────────── │
    │                                                              │
    │  [Full Markdown content here...]                             │
    │                                                              │
    │  ─────────────────────────────────────────────────────────── │
    │  Source: https://...  (SOLUTION entries only)               │
    │  Steps: (PROCEDURE entries only)                             │
    │                                                              │
    │  [👍 Helpful] [👎 Not helpful] [✏️ Edit] [🔗 Related] [📤]  │
    └──────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import logging
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button, Static

from rich.console import Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from kantorku.library.core.models import (
    ENTRY_TYPE_COLORS,
    ENTRY_TYPE_ICONS,
    EntryType,
    LibraryEntry,
)
from kantorku.library.core.archivist import Archivist
from kantorku.library.storage.archive import Archive

logger = logging.getLogger(__name__)

# ── CSS ────────────────────────────────────────────────────────────────

_CSS = """
ReaderPanel {
    layout: vertical;
    height: 1fr;
}

#reader-header {
    height: auto;
    max-height: 6;
    padding: 0 1;
    border-bottom: tall $primary 30%;
    background: $primary 8%;
}

#reader-content {
    height: 1fr;
    scrollbar-size: 1 1;
    padding: 0 1;
}

#reader-actions {
    dock: bottom;
    height: 3;
    padding: 0 1;
    background: $surface;
    border-top: tall $primary 20%;
    layout: horizontal;
    gap: 1;
}

.reader-action-btn {
    min-width: 10;
    height: 2;
    margin: 1 0;
    background: $primary 12%;
    color: $primary;
    border: tall $primary 30%;
}

.reader-action-btn:hover {
    background: $primary 25%;
    color: $text;
}

#btn-helpful {
    background: $success 12%;
    color: $success;
    border: tall $success 30%;
}

#btn-helpful:hover {
    background: $success 25%;
    color: $text;
}

#btn-unhelpful {
    background: $error 12%;
    color: $error;
    border: tall $error 30%;
}

#btn-unhelpful:hover {
    background: $error 25%;
    color: $text;
}

#btn-related {
    background: $accent 12%;
    color: $accent;
    border: tall $accent 30%;
}

#btn-related:hover {
    background: $accent 25%;
    color: $text;
}
"""


class ReaderPanel(Static):
    """Entry reading panel for the Library TUI.

    Displays the full content of a LibraryEntry with metadata,
    actions, and type-specific sections (source links for SOLUTION,
    steps for PROCEDURE).

    Args:
        archive: The Archive instance for data access.
        archivist: The Archivist instance for related entry queries.
        library_screen: Reference to the parent LibraryScreen.
    """

    CSS = _CSS

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._archive: Archive | None = None
        self._archivist: Archivist | None = None
        self._library_screen: Any = None
        self._current_entry: LibraryEntry | None = None

    def set_managers(
        self,
        archive: Archive,
        archivist: Archivist | None = None,
        library_screen: Any = None,
    ) -> None:
        """Set manager references for data access.

        Args:
            archive: The Archive instance.
            archivist: The Archivist instance (optional).
            library_screen: The parent LibraryScreen (optional).
        """
        self._archive = archive
        self._archivist = archivist
        self._library_screen = library_screen

    # ── Compose ────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Static(id="reader-header")
        with VerticalScroll(id="reader-content"):
            yield Static(id="reader-body")
        with Horizontal(id="reader-actions"):
            yield Button(
                "\U0001f44d Helpful", id="btn-helpful", classes="reader-action-btn"
            )
            yield Button(
                "\U0001f44e Not helpful", id="btn-unhelpful", classes="reader-action-btn"
            )
            yield Button(
                "\u270f\ufe0f Edit", id="btn-edit", classes="reader-action-btn"
            )
            yield Button(
                "\U0001f517 Related", id="btn-related", classes="reader-action-btn"
            )
            yield Button(
                "\U0001f4e4 Export", id="btn-export", classes="reader-action-btn"
            )

    # ── Display methods ────────────────────────────────────────────────

    async def display_entry(self, entry: LibraryEntry) -> None:
        """Render a LibraryEntry in the reader panel.

        Displays the entry's full content as Markdown, along with
        a metadata header and type-specific sections.

        Args:
            entry: The LibraryEntry to display.
        """
        self._current_entry = entry
        self._render_header(entry)
        self._render_body(entry)

    async def show_related(self, entry_id: str) -> None:
        """Show entries related to the given entry.

        Retrieves related entries from the Archive and displays
        them as a list with type icons and quality scores.

        Args:
            entry_id: The ID of the entry to find relations for.
        """
        if self._archive is None:
            return

        try:
            related = await self._archive.get_related(entry_id, limit=10)

            try:
                body = self.query_one("#reader-body", Static)
            except Exception:
                return

            if not related:
                body.update(
                    Panel(
                        "[dim]Tidak ada entri terkait[/dim]",
                        title="Entri Terkait",
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
            table.add_column("", width=2)
            table.add_column("Judul", ratio=1)
            table.add_column("Tipe", width=10)
            table.add_column("Q", width=4)

            for rel_entry in related:
                icon = ENTRY_TYPE_ICONS.get(
                    rel_entry.entry_type, "\U0001f4d6"
                )
                color = ENTRY_TYPE_COLORS.get(
                    rel_entry.entry_type, "white"
                )
                title = rel_entry.title or "(tanpa judul)"
                if len(title) > 50:
                    title = title[:47] + "..."

                table.add_row(
                    f"[{color}]{icon}[/{color}]",
                    f"[{color}]{title}[/{color}]",
                    rel_entry.entry_type.value,
                    f"{rel_entry.quality_score:.0%}",
                )

            body.update(
                Panel(
                    table,
                    title=f"Entri Terkait ({len(related)})",
                    border_style="cyan",
                    padding=(0, 1),
                )
            )

        except Exception as exc:
            logger.error("Failed to show related for %s: %s", entry_id, exc)

    def show_error(self, message: str) -> None:
        """Show an error message in the reader panel.

        Args:
            message: The error message to display.
        """
        try:
            header = self.query_one("#reader-header", Static)
            header.update("")

            body = self.query_one("#reader-body", Static)
            body.update(
                Panel(
                    f"[red]{message}[/red]",
                    title="Error",
                    border_style="red",
                    padding=(0, 1),
                )
            )
        except Exception:
            pass

    # ── Rendering helpers ──────────────────────────────────────────────

    def _render_header(self, entry: LibraryEntry) -> None:
        """Render the metadata header for an entry.

        Args:
            entry: The LibraryEntry whose header to render.
        """
        try:
            header = self.query_one("#reader-header", Static)
        except Exception:
            return

        parts: list[Any] = []

        # Title line
        type_icon = ENTRY_TYPE_ICONS.get(entry.entry_type, "\U0001f4d6")
        color = ENTRY_TYPE_COLORS.get(entry.entry_type, "white")

        title = entry.title or "(tanpa judul)"
        verified_str = (
            "[green]\u2713 verified[/green]"
            if entry.verified
            else "[dim]\u25cb unverified[/dim]"
        )

        parts.append(Text.from_markup(
            f"{type_icon} [{color} bold]{title}[/{color} bold]  "
            f"Q:{entry.quality_score:.0%}  "
            f"\U0001f441 {entry.usage_count}  "
            f"\U0001f44d {entry.was_helpful}  "
            f"{verified_str}"
        ))

        # Shelf breadcrumb
        if entry.shelf_path:
            shelf_str = " \u203a ".join(entry.shelf_path)
            parts.append(Text.from_markup(
                f"\U0001f4c2 {shelf_str}"
            ))

        # Entry type label
        parts.append(Text.from_markup(
            f"[dim]{entry.entry_type.value} | {entry.source.value} | "
            f"{entry.domain}[/dim]"
        ))

        # Keywords
        if entry.keywords:
            kw_str = " ".join(f"#{kw}" for kw in entry.keywords[:8])
            parts.append(Text.from_markup(
                f"[dim]{kw_str}[/dim]"
            ))

        header.update(Group(*parts))

    def _render_body(self, entry: LibraryEntry) -> None:
        """Render the entry body content.

        Renders Markdown content with type-specific additions:
        - SOLUTION: problem description and source links
        - PROCEDURE: step-by-step list
        - QA_PAIR: question and answer sections

        Args:
            entry: The LibraryEntry whose body to render.
        """
        try:
            body = self.query_one("#reader-body", Static)
        except Exception:
            return

        parts: list[Any] = []

        # ── Type-specific prelude ──────────────────────────────────────

        if entry.entry_type == EntryType.SOLUTION:
            if entry.problem_description:
                parts.append(Text.from_markup(
                    "[bold red]\u26a0 Masalah:[/bold red]"
                ))
                parts.append(Text(entry.problem_description))
                parts.append(Text.from_markup(""))

            if entry.failed_attempts:
                parts.append(Text.from_markup(
                    f"[dim]{len(entry.failed_attempts)} percobaan gagal[/dim]"
                ))
                parts.append(Text.from_markup(""))

        elif entry.entry_type == EntryType.QA_PAIR:
            if entry.question:
                parts.append(Text.from_markup(
                    "[bold cyan]\u2753 Pertanyaan:[/bold cyan]"
                ))
                parts.append(Text(entry.question))
                parts.append(Text.from_markup(""))

        elif entry.entry_type == EntryType.PROCEDURE:
            if entry.steps:
                parts.append(Text.from_markup(
                    f"[bold green]\U0001f527 Langkah-langkah ({len(entry.steps)}):[/bold green]"
                ))
                for step_data in entry.steps:
                    step_num = step_data.get("step", "?")
                    action = step_data.get("action", "")
                    expected = step_data.get("expected", "")
                    parts.append(Text.from_markup(
                        f"  [bold]{step_num}.[/bold] {action}"
                    ))
                    if expected:
                        parts.append(Text.from_markup(
                            f"     [dim]\u2192 {expected}[/dim]"
                        ))
                parts.append(Text.from_markup(""))

        # ── Main content (Markdown) ────────────────────────────────────

        if entry.content:
            try:
                md = Markdown(entry.content)
                parts.append(md)
            except Exception:
                # Fallback: plain text
                parts.append(Text(entry.content))
            parts.append(Text.from_markup(""))

        # ── Type-specific postlude ─────────────────────────────────────

        if entry.entry_type == EntryType.SOLUTION:
            if entry.solution_code:
                parts.append(Text.from_markup(
                    "[bold green]\u2713 Solusi:[/bold green]"
                ))
                # Show code block
                code = entry.solution_code
                if len(code) > 2000:
                    code = code[:2000] + "\n...[truncated]"
                parts.append(Text(code))
                parts.append(Text.from_markup(""))

            if entry.verification_result:
                vr = entry.verification_result.value
                v_color = "green" if vr == "pass" else "red"
                parts.append(Text.from_markup(
                    f"[{v_color}]Verifikasi: {vr}[/{v_color}]"
                ))

        elif entry.entry_type == EntryType.QA_PAIR:
            if entry.answer:
                parts.append(Text.from_markup(
                    "[bold green]\u2713 Jawaban:[/bold green]"
                ))
                try:
                    md = Markdown(entry.answer)
                    parts.append(md)
                except Exception:
                    parts.append(Text(entry.answer))

            if entry.source_entry_ids:
                parts.append(Text.from_markup(
                    f"[dim]Sumber: {len(entry.source_entry_ids)} entri[/dim]"
                ))

        # ── Summary ────────────────────────────────────────────────────

        if entry.summary:
            parts.append(Text.from_markup(""))
            parts.append(Text.from_markup("[bold]Ringkasan:[/bold]"))
            parts.append(Text.from_markup(f"[dim]{entry.summary}[/dim]"))

        # ── Footer metadata ────────────────────────────────────────────

        parts.append(Text.from_markup(""))
        parts.append(Text.from_markup(
            f"[dim]ID: {entry.id[:8]}... | "
            f"Dibuat: {entry.created_at.strftime('%Y-%m-%d %H:%M')} | "
            f"Diperbarui: {entry.updated_at.strftime('%Y-%m-%d %H:%M')}[/dim]"
        ))

        if entry.origin_worker_id:
            parts.append(Text.from_markup(
                f"[dim]Worker: {entry.origin_worker_id}[/dim]"
            ))

        body.update(Group(*parts))

    # ── Event handlers ─────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle action button clicks."""
        btn_id = event.button.id or ""

        if btn_id == "btn-helpful":
            self._mark_helpful()
        elif btn_id == "btn-unhelpful":
            self._mark_unhelpful()
        elif btn_id == "btn-edit":
            self._edit_entry()
        elif btn_id == "btn-related":
            self._show_related()
        elif btn_id == "btn-export":
            self._export_entry()

    def _mark_helpful(self) -> None:
        """Mark the current entry as helpful."""
        if self._current_entry is None or self._archive is None:
            return

        entry = self._current_entry
        entry.mark_helpful()

        async def _persist() -> None:
            try:
                await self._archive.record_usage(entry.id, helpful=True)
                self._render_header(entry)
            except Exception as exc:
                logger.error("Failed to mark helpful: %s", exc)

        self.app.run_worker(_persist())

    def _mark_unhelpful(self) -> None:
        """Mark the current entry as not helpful."""
        if self._current_entry is None or self._archive is None:
            return

        entry = self._current_entry
        entry.mark_unhelpful()

        async def _persist() -> None:
            try:
                await self._archive.record_usage(entry.id, helpful=False)
                self._render_header(entry)
            except Exception as exc:
                logger.error("Failed to mark unhelpful: %s", exc)

        self.app.run_worker(_persist())

    def _edit_entry(self) -> None:
        """Open the entry for inline editing."""
        if self._current_entry is None:
            return

        entry = self._current_entry

        try:
            body = self.query_one("#reader-body", Static)
            from textual.widgets import Input, Select as TSelect

            # Build edit form
            parts: list[Any] = []
            parts.append(Text.from_markup("[bold yellow]✏️ Mode Edit[/bold yellow]"))
            parts.append(Text.from_markup(""))

            # Title
            parts.append(Text.from_markup("[bold]Judul:[/bold]"))
            parts.append(Text(entry.title or ""))
            parts.append(Text.from_markup(""))

            # Content
            parts.append(Text.from_markup("[bold]Konten:[/bold]"))
            content_preview = entry.content[:500] if entry.content else ""
            if len(entry.content or "") > 500:
                content_preview += "..."
            parts.append(Text(content_preview))
            parts.append(Text.from_markup(""))

            # Keywords
            parts.append(Text.from_markup(
                f"[bold]Keywords:[/bold] {', '.join(entry.keywords) if entry.keywords else '(none)'}"
            ))

            # Shelf path
            parts.append(Text.from_markup(
                f"[bold]Shelf:[/bold] {entry.shelf_str}"
            ))

            # Entry type
            parts.append(Text.from_markup(
                f"[bold]Type:[/bold] {entry.entry_type.value}"
            ))

            parts.append(Text.from_markup(""))
            parts.append(Text.from_markup(
                "[dim]Edit fields above. Use Ingest panel for full content editing.[/dim]"
            ))
            parts.append(Text.from_markup(
                "[dim]Press the ✏️ Edit button again or use Ingest to save changes.[/dim]"
            ))

            body.update(
                Panel(
                    Group(*parts),
                    title=f"Edit: {entry.title[:40] if entry.title else 'Untitled'}",
                    border_style="yellow",
                    padding=(0, 1),
                )
            )

            # Store previous version in metadata for version tracking
            if not hasattr(entry, '_edit_history'):
                entry._edit_history = []

            entry._edit_history.append({
                "title": entry.title,
                "content": entry.content[:200] if entry.content else "",
                "keywords": list(entry.keywords),
                "shelf_path": list(entry.shelf_path),
                "entry_type": entry.entry_type.value,
                "timestamp": entry.updated_at.isoformat(),
            })

        except Exception as exc:
            logger.error("Failed to open edit mode: %s", exc)

    def _show_related(self) -> None:
        """Show related entries for the current entry."""
        if self._current_entry is None:
            return

        async def _load() -> None:
            await self.show_related(self._current_entry.id)

        self.app.run_worker(_load())

    def _export_entry(self) -> None:
        """Export the current entry with format picker and file save dialog."""
        if self._current_entry is None:
            return

        entry = self._current_entry

        try:
            body = self.query_one("#reader-body", Static)

            # Export format options
            import json

            # JSON export
            json_data = json.dumps(entry.to_dict(), indent=2, ensure_ascii=False)

            # Markdown export
            md_lines: list[str] = []
            md_lines.append(f"# {entry.title or 'Untitled'}")
            md_lines.append("")
            md_lines.append(f"**Type**: {entry.entry_type.value}")
            md_lines.append(f"**Quality**: {entry.quality_score:.2f}")
            md_lines.append(f"**Shelf**: {entry.shelf_str}")
            md_lines.append(f"**Keywords**: {', '.join(entry.keywords) if entry.keywords else 'None'}")
            md_lines.append("")
            md_lines.append(entry.content)
            md_data = "\n".join(md_lines)

            # Build format picker display
            parts: list[Any] = []
            parts.append(Text.from_markup("[bold green]📤 Export Entry[/bold green]"))
            parts.append(Text.from_markup(""))
            parts.append(Text.from_markup("[bold]JSON Format:[/bold]"))
            parts.append(Text(json_data[:600] + ("..." if len(json_data) > 600 else "")))
            parts.append(Text.from_markup(""))
            parts.append(Text.from_markup("[bold]Markdown Format:[/bold]"))
            parts.append(Text(md_data[:600] + ("..." if len(md_data) > 600 else "")))
            parts.append(Text.from_markup(""))
            parts.append(Text.from_markup(
                "[dim]Select format above. Content can be copied to clipboard.[/dim]"
            ))
            parts.append(Text.from_markup(
                "[dim]For batch export, use the Exporter module directly.[/dim]"
            ))

            body.update(
                Panel(
                    Group(*parts),
                    title=f"Export: {entry.title[:40] if entry.title else 'Untitled'}",
                    border_style="green",
                    padding=(0, 1),
                )
            )

        except Exception as exc:
            logger.error("Failed to export entry: %s", exc)
