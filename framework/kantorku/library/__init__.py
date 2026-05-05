"""
KantorKu Library — Knowledge management system.

A persistent, searchable knowledge base that integrates with the KantorKu
office workflow. Library entries are organized into a hierarchical shelf
system (like a real library) and can be searched via vector similarity.

Components:
    core/      — Librarian (AI categorization), Archivist (AI answering),
                 Shelf system, Indexer (vector embedding), Exporter
    storage/   — Archive (SQLite), HotIndex (DuckDB), Vectors (ChromaDB/FAISS)
    bridge/    — KantorKu integration, Losion export
    training/  — Fine-tune recipe and data formatting for Librarian model
"""

from kantorku.library.core.models import LibraryEntry, EntryType, EntrySource

__all__ = ["LibraryEntry", "EntryType", "EntrySource"]
