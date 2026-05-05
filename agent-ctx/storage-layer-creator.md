# Task: Create KantorKu Library Storage Layer

## Summary
Created all four storage layer files for the KantorKu Library system with full async support, error handling, and docstrings.

## Files Created

### 1. `__init__.py`
- Simple module init importing `Archive`, `HotIndex`, `VectorStore`
- Re-exports via `__all__`

### 2. `archive.py` — SQLite Persistent Storage
- `Archive` class using `aiosqlite` for all async operations
- Full CRUD: `store()`, `get()`, `update()`, `delete()`
- FTS5 full-text search with triggers for auto-sync
- `search()` with filters (entry_type, shelf_path, min_quality, verified_only)
- `get_by_shelf()`, `get_all()` with pagination
- `get_shelf_structure()` returns nested dict with counts
- `record_usage()` with helpful/unhelpful feedback
- `get_stats()` returns aggregate statistics
- `get_related()` fetches entries from related_ids
- Embeddings cache table (`embeddings_cache`) with `get_cached_embedding()` / `set_cached_embedding()`
- JSON-encodes list fields before storage, uses `LibraryEntry.from_dict()` / `to_dict()`
- WAL mode, proper directory creation, graceful error handling

### 3. `hot_index.py` — DuckDB Hot Index
- `HotIndex` class using DuckDB with `asyncio.to_thread()` for async compat
- `upsert()`, `remove()` for write operations
- `get_trending()` — highest usage_count
- `get_recent()` — most recently updated
- `get_top_quality()` — highest quality_score
- `search()` — ILIKE-based text search on title, summary, keywords
- `get_shelf_stats()` — aggregate stats per shelf path

### 4. `vectors.py` — Vector Store
- `VectorStore` class with ChromaDB → FAISS → in-memory fallback
- `_embed()` uses sentence-transformers, falls back to hash-based embedding
- `add()` with Archive embedding cache integration
- `search()` returns `{entry_id, similarity, metadata}`
- `remove()` and `get_embedding()` supported across all backends
- CPU-bound operations run in thread pool via `asyncio.to_thread()`
- FAISS index auto-saves to disk; ChromaDB uses PersistentClient

## Design Decisions
- FTS5 virtual table with automatic sync triggers for fast text search in Archive
- DuckDB's columnar format ideal for analytical queries (trending, stats)
- VectorStore gracefully degrades: ChromaDB → FAISS → memory
- Hash-based embedding fallback ensures the system works even without ML models
- All list fields JSON-encoded for SQLite compatibility
- Consistent async patterns with `asyncio.to_thread()` for blocking operations
