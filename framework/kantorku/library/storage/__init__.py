"""
Library storage layer — persistent and indexed storage backends.

Components:
    Archive    — SQLite-based persistent storage for all LibraryEntry records
    HotIndex   — DuckDB-based index for fast queries on recent/frequent entries
    Vectors    — Vector storage wrapper (ChromaDB / FAISS / in-memory fallback)
"""

from kantorku.library.storage.archive import Archive
from kantorku.library.storage.hot_index import HotIndex
from kantorku.library.storage.vectors import VectorStore

__all__ = ["Archive", "HotIndex", "VectorStore"]
