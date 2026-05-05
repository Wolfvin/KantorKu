"""
kantorku.tui.library — TUI screens for the KantorKu Library.

Provides a Textual-based interface for browsing, reading, asking,
and ingesting knowledge entries in the Library system.
"""

try:
    from kantorku.tui.library.library_screen import LibraryScreen
except ImportError:
    LibraryScreen = None  # type: ignore[assignment,misc]

__all__ = ["LibraryScreen"]
