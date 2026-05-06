"""
AskPanel — Ask Archivist panel for the Library TUI.

Provides a chat-like interface for asking questions to the Archivist.
The Archivist searches the Library's stored knowledge and synthesizes
responses with source citations.

Layout:
    ┌──────────────────────────────────────────────────────────────┐
    │  🤖 Tanya Archivist                                         │
    │  ─────────────────────────────────────────────────────────── │
    │                                                              │
    │  Kamu: Bagaimana cara fix Python ImportError?               │
    │                                                              │
    │  Archivist:                                                  │
    │  Berdasarkan 3 entri Library:                                │
    │  ...answer with [1], [2], [3] citations...                  │
    │                                                              │
    │  Sumber:                                                     │
    │  [1] Fixing Import Errors (solution) - similar: 0.87        │
    │  [2] Python Package Management (knowledge) - similar: 0.72  │
    │  [3] Virtual Environment Setup (procedure) - similar: 0.65  │
    │                                                              │
    │  ─────────────────────────────────────────────────────────── │
    │  [💾 Save to Library] [📋 Copy] [🔄 Ask again]             │
    └──────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import logging
import os
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button, Static

from rich.console import Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from kantorku.library.core.models import (
    ENTRY_TYPE_COLORS,
    ENTRY_TYPE_ICONS,
    EntrySource,
    EntryType,
    LibraryEntry,
)
from kantorku.library.core.archivist import Archivist
from kantorku.library.storage.archive import Archive

logger = logging.getLogger(__name__)

# ── CSS ────────────────────────────────────────────────────────────────

_CSS = """
AskPanel {
    layout: vertical;
    height: 1fr;
}

#ask-header {
    height: 3;
    padding: 0 1;
    border-bottom: tall $primary 30%;
    background: $primary 8%;
}

#ask-conversation {
    height: 1fr;
    scrollbar-size: 1 1;
    padding: 0 1;
}

#ask-actions {
    dock: bottom;
    height: 3;
    padding: 0 1;
    background: $surface;
    border-top: tall $primary 20%;
    layout: horizontal;
    gap: 1;
}

.ask-action-btn {
    min-width: 12;
    height: 2;
    margin: 1 0;
    background: $primary 12%;
    color: $primary;
    border: tall $primary 30%;
}

.ask-action-btn:hover {
    background: $primary 25%;
    color: $text;
}

#btn-save {
    background: $success 12%;
    color: $success;
    border: tall $success 30%;
}

#btn-save:hover {
    background: $success 25%;
    color: $text;
}

#btn-copy {
    background: $accent 12%;
    color: $accent;
    border: tall $accent 30%;
}

#btn-copy:hover {
    background: $accent 25%;
    color: $text;
}

#btn-ask-again {
    background: $warning 12%;
    color: $warning;
    border: tall $warning 30%;
}

#btn-ask-again:hover {
    background: $warning 25%;
    color: $text;
}
"""


class AskPanel(Static):
    """Ask Archivist panel for the Library TUI.

    Provides a chat-like interface for asking questions. The Archivist
    searches the Library's knowledge base and synthesizes an answer
    with source citations displayed as [N] markers.

    Actions:
    - 💾 Save to Library: Save the Q&A as a QA_PAIR entry
    - 📋 Copy: Copy the answer to clipboard
    - 🔄 Ask again: Re-submit the last question
    """

    CSS = _CSS

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._archivist: Archivist | None = None
        self._archive: Archive | None = None
        self._library_screen: Any = None

        # Conversation state
        self._conversation: list[dict[str, Any]] = []
        self._last_question: str = ""
        self._last_sources: list[dict[str, Any]] = []
        self._last_answer: str = ""
        self._is_thinking: bool = False

    def set_managers(
        self,
        archivist: Archivist,
        archive: Archive | None = None,
        library_screen: Any = None,
    ) -> None:
        """Set manager references for data access.

        Args:
            archivist: The Archivist instance for answering questions.
            archive: The Archive instance for saving interactions.
            library_screen: The parent LibraryScreen.
        """
        self._archivist = archivist
        self._archive = archive
        self._library_screen = library_screen

    # ── Compose ────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Static(
            "\U0001f916 Tanya Archivist  [dim]Ajukan pertanyaan tentang konten Library[/dim]",
            id="ask-header",
        )
        with VerticalScroll(id="ask-conversation"):
            yield Static(id="ask-conversation-content")
        with Horizontal(id="ask-actions"):
            yield Button(
                "\U0001f4be Save to Library", id="btn-save", classes="ask-action-btn"
            )
            yield Button(
                "\U0001f4cb Copy", id="btn-copy", classes="ask-action-btn"
            )
            yield Button(
                "\U0001f504 Ask again", id="btn-ask-again", classes="ask-action-btn"
            )

    # ── Main ask interface ─────────────────────────────────────────────

    async def ask_question(self, question: str) -> None:
        """Send a question to the Archivist and display the response.

        Shows a thinking indicator while the Archivist processes,
        then displays the answer with source citations.

        Args:
            question: The question to ask.
        """
        if self._is_thinking:
            return

        if not question.strip():
            return

        self._last_question = question
        self._is_thinking = True

        # Add user question to conversation
        self._conversation.append({
            "role": "user",
            "content": question,
        })
        self._render_thinking()

        try:
            if self._archivist is None:
                answer = (
                    "Archivist tidak tersedia. "
                    "Pastikan Library sudah diinisialisasi dengan benar."
                )
                sources: list[dict[str, Any]] = []
                confidence = 0.0
            else:
                result = await self._archivist.ask(question, top_k=5)
                answer = result.get("answer", "Tidak ada jawaban.")
                sources = result.get("sources", [])
                confidence = result.get("confidence", 0.0)

            self._last_answer = answer
            self._last_sources = sources

            # Add Archivist response to conversation
            self._conversation.append({
                "role": "archivist",
                "content": answer,
                "sources": sources,
                "confidence": confidence,
            })

        except Exception as exc:
            logger.error("Ask question failed: %s", exc)
            error_msg = f"Gagal mendapatkan jawaban: {exc}"
            self._conversation.append({
                "role": "archivist",
                "content": error_msg,
                "sources": [],
                "confidence": 0.0,
            })
            self._last_answer = error_msg
            self._last_sources = []

        finally:
            self._is_thinking = False
            self._render_conversation()

    async def save_interaction(self) -> None:
        """Save the current Q&A interaction as a QA_PAIR entry.

        Only saves if there is a valid question and answer from the
        Archivist. The entry references the source entries used.
        """
        if not self._last_question or not self._last_answer:
            return

        if self._archivist is None or self._archive is None:
            return

        try:
            # Collect source entry IDs
            source_ids = [
                s.get("entry_id", "")
                for s in self._last_sources
                if s.get("entry_id")
            ]

            qa_entry = await self._archivist.save_interaction(
                question=self._last_question,
                answer=self._last_answer,
                source_entry_ids=source_ids,
            )

            if qa_entry is not None:
                self._show_status(
                    f"[green]\u2713 Disimpan sebagai QA_PAIR: "
                    f"{qa_entry.title[:50]}[/green]"
                )
                # Refresh shelf tree
                if self._library_screen is not None:
                    await self._library_screen.refresh_shelf_tree()
            else:
                self._show_status(
                    "[yellow]Kualitas jawaban terlalu rendah untuk disimpan[/yellow]"
                )

        except Exception as exc:
            logger.error("Failed to save interaction: %s", exc)
            self._show_status(f"[red]Gagal menyimpan: {exc}[/red]")

    # ── Rendering ──────────────────────────────────────────────────────

    def _render_conversation(self) -> None:
        """Render the full conversation history."""
        try:
            conv_content = self.query_one(
                "#ask-conversation-content", Static
            )
        except Exception:
            return

        if not self._conversation:
            conv_content.update(
                Panel(
                    "[dim]Ajukan pertanyaan untuk memulai percakapan "
                    "dengan Archivist.[/dim]\n\n"
                    "[dim]Archivist akan mencari entri Library yang relevan "
                    "dan menyusun jawaban dengan referensi sumber.[/dim]",
                    border_style="dim",
                    padding=(0, 1),
                )
            )
            return

        parts: list[Any] = []

        for msg in self._conversation:
            role = msg.get("role", "")
            content = msg.get("content", "")
            sources = msg.get("sources", [])
            confidence = msg.get("confidence", 0.0)

            if role == "user":
                parts.append(Text.from_markup(
                    f"[bold cyan]Kamu:[/bold cyan] {content}"
                ))
                parts.append(Text.from_markup(""))

            elif role == "archivist":
                parts.append(Text.from_markup(
                    "[bold magenta]Archivist:[/bold magenta]"
                ))

                # Try to render answer as Markdown
                try:
                    md = Markdown(content)
                    parts.append(md)
                except Exception:
                    parts.append(Text(content))

                # Confidence indicator
                if confidence > 0:
                    conf_color = "green" if confidence > 0.7 else (
                        "yellow" if confidence > 0.4 else "red"
                    )
                    parts.append(Text.from_markup(
                        f"[{conf_color}]Kepercayaan: {confidence:.0%}[/{conf_color}]"
                    ))

                # Source citations
                if sources:
                    parts.append(Text.from_markup(""))
                    parts.append(Text.from_markup(
                        "[bold]Sumber:[/bold]"
                    ))
                    for i, src in enumerate(sources, 1):
                        title = src.get("title", "(tanpa judul)")
                        entry_type = src.get("entry_type", "knowledge")
                        similarity = src.get("similarity", 0.0)

                        type_icon = ENTRY_TYPE_ICONS.get(
                            EntryType(entry_type), "\U0001f4d6"
                        )
                        type_color = ENTRY_TYPE_COLORS.get(
                            EntryType(entry_type), "white"
                        )

                        parts.append(Text.from_markup(
                            f"  [{i}] [{type_color}]{type_icon}[/{type_color}] "
                            f"{title} ({entry_type}) - similar: {similarity:.0%}"
                        ))

                parts.append(Text.from_markup(""))
                parts.append(Text.from_markup(
                    "\u2500" * 50
                ))
                parts.append(Text.from_markup(""))

        conv_content.update(Group(*parts))

    def _render_thinking(self) -> None:
        """Show a thinking indicator while the Archivist processes."""
        try:
            conv_content = self.query_one(
                "#ask-conversation-content", Static
            )
        except Exception:
            return

        # Re-render conversation with thinking indicator at the end
        parts: list[Any] = []

        for msg in self._conversation:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "user":
                parts.append(Text.from_markup(
                    f"[bold cyan]Kamu:[/bold cyan] {content}"
                ))
                parts.append(Text.from_markup(""))

        # Add thinking indicator
        parts.append(Text.from_markup(
            "[bold magenta]Archivist:[/bold magenta] "
            "[yellow]\u25d0 Sedang berpikir...[/yellow]"
        ))

        conv_content.update(Group(*parts))

    def _show_status(self, message: str) -> None:
        """Show a status message at the bottom of the conversation.

        Args:
            message: The status message (may contain Rich markup).
        """
        try:
            conv_content = self.query_one(
                "#ask-conversation-content", Static
            )
            # Append status to existing content
            conv_content.update(
                Panel(message, border_style="dim", padding=(0, 1))
            )
        except Exception:
            pass

    # ── Event handlers ─────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle action button clicks."""
        btn_id = event.button.id or ""

        if btn_id == "btn-save":
            async def _save() -> None:
                await self.save_interaction()
            self.app.run_worker(_save())

        elif btn_id == "btn-copy":
            self._copy_answer()

        elif btn_id == "btn-ask-again":
            self._ask_again()

    def _copy_answer(self) -> None:
        """Copy the last answer to clipboard using pyperclip or fallback."""
        if not self._last_answer:
            return

        # Try pyperclip first
        try:
            import pyperclip
            pyperclip.copy(self._last_answer)
            self._show_status("[green]✓ Jawaban disalin ke clipboard[/green]")
            return
        except ImportError:
            logger.debug("pyperclip not installed — trying fallback")
        except Exception as exc:
            logger.debug("pyperclip failed: %s — trying fallback", exc)

        # Fallback: try platform-specific clipboard commands
        import subprocess
        import tempfile

        try:
            if os.name == "posix":
                # Try xclip, xsel, wl-copy
                for cmd_args in [
                    ["xclip", "-selection", "clipboard"],
                    ["xsel", "--clipboard", "--input"],
                    ["wl-copy"],
                ]:
                    try:
                        process = subprocess.Popen(
                            cmd_args,
                            stdin=subprocess.PIPE,
                        )
                        process.communicate(self._last_answer.encode("utf-8"))
                        if process.returncode == 0:
                            self._show_status(
                                "[green]✓ Jawaban disalin ke clipboard[/green]"
                            )
                            return
                    except FileNotFoundError:
                        continue

            elif os.name == "nt":
                process = subprocess.Popen(
                    ["clip"],
                    stdin=subprocess.PIPE,
                )
                process.communicate(self._last_answer.encode("utf-8"))
                self._show_status("[green]✓ Jawaban disalin ke clipboard[/green]")
                return

            elif os.name == "mac":
                process = subprocess.Popen(
                    ["pbcopy"],
                    stdin=subprocess.PIPE,
                )
                process.communicate(self._last_answer.encode("utf-8"))
                self._show_status("[green]✓ Jawaban disalin ke clipboard[/green]")
                return

        except Exception:
            pass

        # Final fallback: write to temp file and show path
        try:
            import os
            tmp_dir = tempfile.gettempdir()
            tmp_path = os.path.join(tmp_dir, "kantorku_answer.txt")
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(self._last_answer)
            self._show_status(
                f"[yellow]Clipboard tidak tersedia. Jawaban disimpan di: {tmp_path}[/yellow]"
            )
        except Exception:
            self._show_status(
                "[yellow]Clipboard tidak tersedia. "
                "Jawaban ditampilkan di atas untuk disalin manual.[/yellow]"
            )

    def _ask_again(self) -> None:
        """Re-submit the last question."""
        if not self._last_question:
            return

        async def _ask() -> None:
            await self.ask_question(self._last_question)

        self.app.run_worker(_ask())
