"""
Archive — SQLite-based persistent storage for all LibraryEntry records.

The Archive is the authoritative store for every LibraryEntry. It uses
aiosqlite for non-blocking I/O and persists data to a single SQLite file.
List fields (keywords, shelf_path, related_ids, etc.) are JSON-encoded
before storage and decoded on read via LibraryEntry.from_dict().
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import aiosqlite

from kantorku.library.core.models import LibraryEntry

logger = logging.getLogger(__name__)

# ── SQL DDL ───────────────────────────────────────────────────────────────

_CREATE_ENTRIES_TABLE = """
CREATE TABLE IF NOT EXISTS entries (
    id                  TEXT PRIMARY KEY,
    created_at          TEXT    NOT NULL,
    updated_at          TEXT    NOT NULL,
    source              TEXT    NOT NULL DEFAULT 'manual',
    title               TEXT    NOT NULL DEFAULT '',
    content             TEXT    NOT NULL DEFAULT '',
    summary             TEXT    NOT NULL DEFAULT '',
    keywords            TEXT    NOT NULL DEFAULT '[]',
    entry_type          TEXT    NOT NULL DEFAULT 'knowledge',
    domain              TEXT    NOT NULL DEFAULT 'web_text',
    lang                TEXT    NOT NULL DEFAULT 'id',
    shelf_path          TEXT    NOT NULL DEFAULT '[]',
    shelf_confidence    REAL    NOT NULL DEFAULT 0.0,
    related_ids         TEXT    NOT NULL DEFAULT '[]',
    supersedes_id       TEXT,
    solution_for        TEXT,
    quality_score       REAL    NOT NULL DEFAULT 0.5,
    verified            INTEGER NOT NULL DEFAULT 0,
    usage_count         INTEGER NOT NULL DEFAULT 0,
    was_helpful         INTEGER NOT NULL DEFAULT 0,
    was_unhelpful       INTEGER NOT NULL DEFAULT 0,
    origin_session_id   TEXT,
    origin_worker_id    TEXT,
    origin_task_id      TEXT,
    problem_description TEXT,
    failed_attempts     TEXT    NOT NULL DEFAULT '[]',
    solution_code       TEXT,
    verification_result TEXT,
    question            TEXT,
    answer              TEXT,
    source_entry_ids    TEXT    NOT NULL DEFAULT '[]',
    steps               TEXT    NOT NULL DEFAULT '[]'
);
"""

_CREATE_EMBEDDINGS_CACHE_TABLE = """
CREATE TABLE IF NOT EXISTS embeddings_cache (
    entry_id    TEXT    NOT NULL,
    model_name  TEXT    NOT NULL,
    embedding   BLOB    NOT NULL,
    created_at  TEXT    NOT NULL,
    PRIMARY KEY (entry_id, model_name)
);
"""

# Full-text search virtual table
_CREATE_FTS_TABLE = """
CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
    entry_id,
    title,
    content,
    summary,
    keywords,
    content='entries',
    content_rowid='rowid'
);
"""

_CREATE_FTS_TRIGGER_INSERT = """
CREATE TRIGGER IF NOT EXISTS entries_fts_ai AFTER INSERT ON entries BEGIN
    INSERT INTO entries_fts(rowid, entry_id, title, content, summary, keywords)
    VALUES (new.rowid, new.id, new.title, new.content, new.summary, new.keywords);
END;
"""

_CREATE_FTS_TRIGGER_DELETE = """
CREATE TRIGGER IF NOT EXISTS entries_fts_ad AFTER DELETE ON entries BEGIN
    INSERT INTO entries_fts(entries_fts, rowid, entry_id, title, content, summary, keywords)
    VALUES ('delete', old.rowid, old.id, old.title, old.content, old.summary, old.keywords);
END;
"""

_CREATE_FTS_TRIGGER_UPDATE = """
CREATE TRIGGER IF NOT EXISTS entries_fts_au AFTER UPDATE ON entries BEGIN
    INSERT INTO entries_fts(entries_fts, rowid, entry_id, title, content, summary, keywords)
    VALUES ('delete', old.rowid, old.id, old.title, old.content, old.summary, old.keywords);
    INSERT INTO entries_fts(rowid, entry_id, title, content, summary, keywords)
    VALUES (new.rowid, new.id, new.title, new.content, new.summary, new.keywords);
END;
"""

# List fields that need JSON encoding/decoding
_JSON_FIELDS: frozenset[str] = frozenset({
    "keywords", "shelf_path", "related_ids", "failed_attempts",
    "source_entry_ids", "steps",
})

# Column order used for INSERT/REPLACE
_ENTRY_COLUMNS: tuple[str, ...] = (
    "id", "created_at", "updated_at", "source", "title", "content",
    "summary", "keywords", "entry_type", "domain", "lang", "shelf_path",
    "shelf_confidence", "related_ids", "supersedes_id", "solution_for",
    "quality_score", "verified", "usage_count", "was_helpful", "was_unhelpful",
    "origin_session_id", "origin_worker_id", "origin_task_id",
    "problem_description", "failed_attempts", "solution_code",
    "verification_result", "question", "answer", "source_entry_ids", "steps",
)


class Archive:
    """SQLite-based persistent storage for LibraryEntry records.

    All write operations use INSERT OR REPLACE semantics so that calling
    ``store()`` on an entry whose id already exists will silently update it.

    Example::

        archive = Archive("data/library/archive.db")
        await archive.initialize()

        entry_id = await archive.store(my_entry)
        retrieved = await archive.get(entry_id)
    """

    def __init__(self, db_path: str = "data/library/archive.db") -> None:
        self._db_path = db_path
        self._db: aiosqlite.Connection | None = None

    # ── Lifecycle ──────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Create the database directory, open the connection, and create tables.

        Safe to call multiple times — uses IF NOT EXISTS for all DDL.
        """
        db_dir = os.path.dirname(self._db_path)
        if db_dir:
            Path(db_dir).mkdir(parents=True, exist_ok=True)

        self._db = await aiosqlite.connect(self._db_path)
        self._db.row_factory = aiosqlite.Row

        # Enable WAL for better concurrent read performance
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA foreign_keys=ON")

        await self._db.executescript(_CREATE_ENTRIES_TABLE)
        await self._db.executescript(_CREATE_EMBEDDINGS_CACHE_TABLE)

        # Create FTS virtual table and triggers
        await self._db.executescript(_CREATE_FTS_TABLE)
        await self._db.executescript(_CREATE_FTS_TRIGGER_INSERT)
        await self._db.executescript(_CREATE_FTS_TRIGGER_DELETE)
        await self._db.executescript(_CREATE_FTS_TRIGGER_UPDATE)

        await self._db.commit()
        logger.info("Archive initialized at %s", self._db_path)

    async def close(self) -> None:
        """Close the database connection gracefully."""
        if self._db:
            await self._db.close()
            self._db = None
            logger.debug("Archive connection closed")

    # ── Internal helpers ───────────────────────────────────────────────

    def _ensure_db(self) -> aiosqlite.Connection:
        """Return the active connection or raise if not initialized."""
        if self._db is None:
            raise RuntimeError("Archive not initialized — call initialize() first")
        return self._db

    @staticmethod
    def _serialize_entry(entry: LibraryEntry) -> dict[str, Any]:
        """Convert a LibraryEntry to a row dict, JSON-encoding list fields."""
        data = entry.to_dict()
        for field_name in _JSON_FIELDS:
            value = data.get(field_name)
            if value is not None:
                data[field_name] = json.dumps(value, ensure_ascii=False)
        # Booleans → int for SQLite
        data["verified"] = int(data.get("verified", False))
        return data

    @staticmethod
    def _row_to_dict(row: aiosqlite.Row) -> dict[str, Any]:
        """Convert a database row to a plain dict for from_dict()."""
        d = dict(row)
        # Convert integer booleans back
        if "verified" in d:
            d["verified"] = bool(d["verified"])
        return d

    # ── CRUD ───────────────────────────────────────────────────────────

    async def store(self, entry: LibraryEntry) -> str:
        """Insert or replace a LibraryEntry, returning its id.

        Args:
            entry: The LibraryEntry to persist.

        Returns:
            The id of the stored entry.
        """
        db = self._ensure_db()
        data = self._serialize_entry(entry)
        placeholders = ", ".join("?" for _ in _ENTRY_COLUMNS)
        columns = ", ".join(_ENTRY_COLUMNS)
        values = tuple(data[col] for col in _ENTRY_COLUMNS)

        await db.execute(
            f"INSERT OR REPLACE INTO entries ({columns}) VALUES ({placeholders})",
            values,
        )
        await db.commit()
        logger.debug("Stored entry %s", entry.id)
        return entry.id

    async def get(self, entry_id: str) -> LibraryEntry | None:
        """Retrieve a LibraryEntry by its id.

        Args:
            entry_id: The unique identifier of the entry.

        Returns:
            The LibraryEntry if found, or ``None``.
        """
        db = self._ensure_db()
        cursor = await db.execute(
            "SELECT * FROM entries WHERE id = ?", (entry_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return LibraryEntry.from_dict(self._row_to_dict(row))

    async def update(self, entry: LibraryEntry) -> None:
        """Update an existing LibraryEntry in-place.

        Raises:
            ValueError: If the entry does not exist in the archive.
        """
        db = self._ensure_db()
        # Verify the entry exists first
        cursor = await db.execute(
            "SELECT 1 FROM entries WHERE id = ?", (entry.id,)
        )
        if await cursor.fetchone() is None:
            raise ValueError(f"Entry {entry.id!r} not found in archive")

        # Use store (INSERT OR REPLACE) for simplicity
        data = self._serialize_entry(entry)
        placeholders = ", ".join("?" for _ in _ENTRY_COLUMNS)
        columns = ", ".join(_ENTRY_COLUMNS)
        values = tuple(data[col] for col in _ENTRY_COLUMNS)

        await db.execute(
            f"INSERT OR REPLACE INTO entries ({columns}) VALUES ({placeholders})",
            values,
        )
        await db.commit()
        logger.debug("Updated entry %s", entry.id)

    async def delete(self, entry_id: str) -> bool:
        """Delete an entry by id.

        Args:
            entry_id: The unique identifier of the entry to delete.

        Returns:
            ``True`` if a row was deleted, ``False`` otherwise.
        """
        db = self._ensure_db()
        cursor = await db.execute(
            "DELETE FROM entries WHERE id = ?", (entry_id,)
        )
        await db.commit()
        deleted = cursor.rowcount > 0
        if deleted:
            logger.debug("Deleted entry %s", entry_id)
        else:
            logger.debug("Delete entry %s — not found", entry_id)
        return deleted

    # ── Search ─────────────────────────────────────────────────────────

    async def search(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        entry_type: str | None = None,
        shelf_path: list[str] | None = None,
        min_quality: float = 0.0,
        verified_only: bool = False,
    ) -> list[LibraryEntry]:
        """Full-text search on title, content, keywords, and summary.

        Uses SQLite FTS5 for fast text matching. Results can be filtered
        by entry type, shelf path, quality score, and verification status.

        Args:
            query: The search string.
            limit: Maximum number of results to return.
            offset: Number of results to skip (for pagination).
            entry_type: If provided, filter to this entry type.
            shelf_path: If provided, filter to entries in this shelf.
            min_quality: Minimum quality score threshold.
            verified_only: If ``True``, only return verified entries.

        Returns:
            A list of matching LibraryEntry objects.
        """
        db = self._ensure_db()

        if not query.strip():
            # Fall back to filtered list when query is empty
            return await self.get_all(
                min_quality=min_quality,
                verified=verified_only,
                limit=limit,
                offset=offset,
            )

        # Build the base query joining FTS results with the entries table
        sql = """
            SELECT e.* FROM entries e
            INNER JOIN entries_fts fts ON e.id = fts.entry_id
            WHERE entries_fts MATCH ?
        """
        params: list[Any] = [query]

        if entry_type is not None:
            sql += " AND e.entry_type = ?"
            params.append(entry_type)

        if shelf_path is not None:
            # Match shelf_path as a JSON-encoded list
            shelf_json = json.dumps(shelf_path, ensure_ascii=False)
            sql += " AND e.shelf_path = ?"
            params.append(shelf_json)

        if min_quality > 0.0:
            sql += " AND e.quality_score >= ?"
            params.append(min_quality)

        if verified_only:
            sql += " AND e.verified = 1"

        sql += " ORDER BY e.quality_score DESC, e.updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = await db.execute(sql, params)
        rows = await cursor.fetchall()
        return [LibraryEntry.from_dict(self._row_to_dict(row)) for row in rows]

    async def get_by_shelf(
        self,
        shelf_path: list[str],
        limit: int = 50,
        offset: int = 0,
    ) -> list[LibraryEntry]:
        """Get all entries belonging to a specific shelf.

        Args:
            shelf_path: The hierarchical path identifying the shelf.
            limit: Maximum number of entries to return.
            offset: Number of entries to skip.

        Returns:
            A list of LibraryEntry objects in the specified shelf.
        """
        db = self._ensure_db()
        shelf_json = json.dumps(shelf_path, ensure_ascii=False)

        cursor = await db.execute(
            """
            SELECT * FROM entries
            WHERE shelf_path = ?
            ORDER BY quality_score DESC, updated_at DESC
            LIMIT ? OFFSET ?
            """,
            (shelf_json, limit, offset),
        )
        rows = await cursor.fetchall()
        return [LibraryEntry.from_dict(self._row_to_dict(row)) for row in rows]

    async def get_all(
        self,
        min_quality: float = 0.0,
        verified: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[LibraryEntry]:
        """List all entries with optional filters.

        Args:
            min_quality: Minimum quality score threshold.
            verified: If ``True``, only return verified entries.
            limit: Maximum number of entries to return.
            offset: Number of entries to skip.

        Returns:
            A list of LibraryEntry objects matching the filters.
        """
        db = self._ensure_db()
        conditions: list[str] = []
        params: list[Any] = []

        if min_quality > 0.0:
            conditions.append("quality_score >= ?")
            params.append(min_quality)

        if verified:
            conditions.append("verified = 1")

        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)

        sql = f"""
            SELECT * FROM entries
            {where}
            ORDER BY quality_score DESC, updated_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        cursor = await db.execute(sql, params)
        rows = await cursor.fetchall()
        return [LibraryEntry.from_dict(self._row_to_dict(row)) for row in rows]

    # ── Shelf structure ────────────────────────────────────────────────

    async def get_shelf_structure(self) -> dict:
        """Return a nested dict representing the shelf hierarchy with counts.

        Each leaf and intermediate node includes an ``_count`` key with the
        number of entries at that exact shelf path.

        Returns:
            A nested dictionary like ``{"Engineering": {"_count": 0, "Backend": {"_count": 5}}}``.
        """
        db = self._ensure_db()
        cursor = await db.execute(
            "SELECT shelf_path, COUNT(*) as cnt FROM entries GROUP BY shelf_path"
        )
        rows = await cursor.fetchall()

        structure: dict[str, Any] = {}
        for row in rows:
            path_raw = row["shelf_path"]
            count = row["cnt"]
            try:
                path: list[str] = json.loads(path_raw) if isinstance(path_raw, str) else path_raw
            except (json.JSONDecodeError, TypeError):
                continue

            if not path:
                structure.setdefault("_count", 0)
                structure["_count"] = structure.get("_count", 0) + count
                continue

            node = structure
            for segment in path:
                if segment not in node:
                    node[segment] = {"_count": 0}
                node[segment]["_count"] = node[segment].get("_count", 0) + count
                node = node[segment]

        return structure

    # ── Usage & feedback ───────────────────────────────────────────────

    async def record_usage(
        self,
        entry_id: str,
        helpful: bool | None = None,
    ) -> None:
        """Increment usage count and optionally record helpful/unhelpful feedback.

        Args:
            entry_id: The entry to update.
            helpful: ``True`` = helpful, ``False`` = unhelpful, ``None`` = no feedback.
        """
        db = self._ensure_db()

        # Fetch current values so we can recalculate quality
        entry = await self.get(entry_id)
        if entry is None:
            logger.warning("record_usage: entry %s not found", entry_id)
            return

        entry.usage_count += 1
        if helpful is True:
            entry.was_helpful += 1
        elif helpful is False:
            entry.was_unhelpful += 1

        entry._recalculate_quality()
        entry.touch()

        # Persist the updated entry
        data = self._serialize_entry(entry)
        placeholders = ", ".join("?" for _ in _ENTRY_COLUMNS)
        columns = ", ".join(_ENTRY_COLUMNS)
        values = tuple(data[col] for col in _ENTRY_COLUMNS)

        await db.execute(
            f"INSERT OR REPLACE INTO entries ({columns}) VALUES ({placeholders})",
            values,
        )
        await db.commit()
        logger.debug("Recorded usage for %s (helpful=%s)", entry_id, helpful)

    # ── Statistics ─────────────────────────────────────────────────────

    async def get_stats(self) -> dict[str, Any]:
        """Return aggregate statistics about the archive.

        Returns:
            A dict with keys: ``total_entries``, ``verified_entries``,
            ``avg_quality``, ``shelves_count``, ``entries_by_type``.
        """
        db = self._ensure_db()

        # Total entries
        cursor = await db.execute("SELECT COUNT(*) FROM entries")
        total = (await cursor.fetchone())[0]

        # Verified entries
        cursor = await db.execute("SELECT COUNT(*) FROM entries WHERE verified = 1")
        verified = (await cursor.fetchone())[0]

        # Average quality
        cursor = await db.execute(
            "SELECT COALESCE(AVG(quality_score), 0.0) FROM entries"
        )
        avg_quality = (await cursor.fetchone())[0]

        # Distinct shelves
        cursor = await db.execute(
            "SELECT COUNT(DISTINCT shelf_path) FROM entries"
        )
        shelves_count = (await cursor.fetchone())[0]

        # Entries by type
        cursor = await db.execute(
            "SELECT entry_type, COUNT(*) as cnt FROM entries GROUP BY entry_type"
        )
        type_rows = await cursor.fetchall()
        entries_by_type = {row["entry_type"]: row["cnt"] for row in type_rows}

        return {
            "total_entries": total,
            "verified_entries": verified,
            "avg_quality": round(avg_quality, 4),
            "shelves_count": shelves_count,
            "entries_by_type": entries_by_type,
        }

    # ── Relations ──────────────────────────────────────────────────────

    async def get_related(
        self,
        entry_id: str,
        limit: int = 5,
    ) -> list[LibraryEntry]:
        """Get entries listed in an entry's ``related_ids`` field.

        Args:
            entry_id: The entry whose relations to look up.
            limit: Maximum number of related entries to return.

        Returns:
            A list of related LibraryEntry objects.
        """
        entry = await self.get(entry_id)
        if entry is None or not entry.related_ids:
            return []

        db = self._ensure_db()
        related = entry.related_ids[:limit]
        placeholders = ", ".join("?" for _ in related)

        cursor = await db.execute(
            f"SELECT * FROM entries WHERE id IN ({placeholders})",
            tuple(related),
        )
        rows = await cursor.fetchall()
        return [LibraryEntry.from_dict(self._row_to_dict(row)) for row in rows]

    # ── Embeddings cache ───────────────────────────────────────────────

    async def get_cached_embedding(
        self,
        entry_id: str,
        model_name: str,
    ) -> list[float] | None:
        """Retrieve a cached embedding from the embeddings_cache table.

        Args:
            entry_id: The entry id.
            model_name: The name of the embedding model.

        Returns:
            The embedding as a list of floats, or ``None`` if not cached.
        """
        db = self._ensure_db()
        cursor = await db.execute(
            "SELECT embedding FROM embeddings_cache WHERE entry_id = ? AND model_name = ?",
            (entry_id, model_name),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        blob = row["embedding"]
        return json.loads(blob.decode("utf-8"))

    async def set_cached_embedding(
        self,
        entry_id: str,
        model_name: str,
        embedding: list[float],
    ) -> None:
        """Store an embedding in the cache table.

        Args:
            entry_id: The entry id.
            model_name: The name of the embedding model.
            embedding: The embedding vector.
        """
        db = self._ensure_db()
        from datetime import datetime, timezone

        blob = json.dumps(embedding).encode("utf-8")
        created_at = datetime.now(timezone.utc).isoformat()

        await db.execute(
            """
            INSERT OR REPLACE INTO embeddings_cache (entry_id, model_name, embedding, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (entry_id, model_name, blob, created_at),
        )
        await db.commit()
