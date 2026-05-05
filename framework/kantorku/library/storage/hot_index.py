"""
HotIndex — DuckDB-based index for fast queries on recent and frequent entries.

The HotIndex mirrors a subset of each LibraryEntry (metadata and counters)
into a columnar DuckDB table optimized for analytical queries such as
trending entries, recent updates, top-quality lookups, and shelf aggregation.

Because DuckDB's Python API is synchronous, all operations are wrapped in
``asyncio.to_thread()`` to avoid blocking the event loop.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kantorku.library.core.models import LibraryEntry

logger = logging.getLogger(__name__)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS hot_entries (
    entry_id      TEXT    PRIMARY KEY,
    title         TEXT    NOT NULL DEFAULT '',
    shelf_path    TEXT    NOT NULL DEFAULT '[]',
    entry_type    TEXT    NOT NULL DEFAULT 'knowledge',
    quality_score DOUBLE  NOT NULL DEFAULT 0.5,
    usage_count   BIGINT  NOT NULL DEFAULT 0,
    was_helpful   BIGINT  NOT NULL DEFAULT 0,
    was_unhelpful BIGINT  NOT NULL DEFAULT 0,
    updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    summary       TEXT    NOT NULL DEFAULT '',
    keywords      TEXT    NOT NULL DEFAULT '[]'
);
"""


class HotIndex:
    """DuckDB-based index for fast queries on recent and frequent entries.

    The HotIndex keeps a lightweight copy of entry metadata in DuckDB for
    analytical queries that would be expensive on SQLite's row-based storage.

    Example::

        index = HotIndex("data/library/hot_index.duckdb")
        await index.initialize()

        await index.upsert(my_entry)
        trending = await index.get_trending(limit=5)
    """

    def __init__(self, db_path: str = "data/library/hot_index.duckdb") -> None:
        self._db_path = db_path
        self._con: Any = None  # duckdb.DuckDBPyConnection

    # ── Lifecycle ──────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Create the database directory, open the connection, and create the table.

        Safe to call multiple times — uses IF NOT EXISTS.
        """
        db_dir = os.path.dirname(self._db_path)
        if db_dir:
            Path(db_dir).mkdir(parents=True, exist_ok=True)

        def _init() -> None:
            import duckdb

            self._con = duckdb.connect(self._db_path)
            self._con.execute(_CREATE_TABLE_SQL)
            logger.info("HotIndex initialized at %s", self._db_path)

        await asyncio.to_thread(_init)

    async def close(self) -> None:
        """Close the DuckDB connection gracefully."""
        if self._con:
            await asyncio.to_thread(self._con.close)
            self._con = None
            logger.debug("HotIndex connection closed")

    # ── Internal helpers ───────────────────────────────────────────────

    def _ensure_con(self) -> Any:
        """Return the active connection or raise if not initialized."""
        if self._con is None:
            raise RuntimeError("HotIndex not initialized — call initialize() first")
        return self._con

    @staticmethod
    def _entry_to_row(entry: LibraryEntry) -> dict[str, Any]:
        """Convert a LibraryEntry to a row dict for DuckDB insertion."""
        updated = entry.updated_at
        if isinstance(updated, datetime):
            ts = updated.isoformat()
        else:
            ts = str(updated)

        return {
            "entry_id": entry.id,
            "title": entry.title,
            "shelf_path": json.dumps(entry.shelf_path, ensure_ascii=False),
            "entry_type": entry.entry_type.value,
            "quality_score": entry.quality_score,
            "usage_count": entry.usage_count,
            "was_helpful": entry.was_helpful,
            "was_unhelpful": entry.was_unhelpful,
            "updated_at": ts,
            "summary": entry.summary,
            "keywords": json.dumps(entry.keywords, ensure_ascii=False),
        }

    # ── Write operations ───────────────────────────────────────────────

    async def upsert(self, entry: LibraryEntry) -> None:
        """Insert or update an entry in the hot index.

        Args:
            entry: The LibraryEntry to upsert.
        """
        row = self._entry_to_row(entry)

        def _upsert() -> None:
            con = self._ensure_con()
            con.execute(
                """
                INSERT OR REPLACE INTO hot_entries
                    (entry_id, title, shelf_path, entry_type, quality_score,
                     usage_count, was_helpful, was_unhelpful, updated_at,
                     summary, keywords)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    row["entry_id"], row["title"], row["shelf_path"],
                    row["entry_type"], row["quality_score"], row["usage_count"],
                    row["was_helpful"], row["was_unhelpful"], row["updated_at"],
                    row["summary"], row["keywords"],
                ],
            )
            logger.debug("HotIndex upserted %s", entry.id)

        await asyncio.to_thread(_upsert)

    async def remove(self, entry_id: str) -> None:
        """Remove an entry from the hot index.

        Args:
            entry_id: The id of the entry to remove.
        """
        def _remove() -> None:
            con = self._ensure_con()
            con.execute(
                "DELETE FROM hot_entries WHERE entry_id = ?", [entry_id]
            )
            logger.debug("HotIndex removed %s", entry_id)

        await asyncio.to_thread(_remove)

    # ── Read queries ───────────────────────────────────────────────────

    async def get_trending(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get entries with the highest usage count recently.

        Results are ordered by ``usage_count`` descending, then by
        ``updated_at`` descending as a tiebreaker.

        Args:
            limit: Maximum number of entries to return.

        Returns:
            A list of dicts with entry metadata.
        """
        def _query() -> list[dict[str, Any]]:
            con = self._ensure_con()
            result = con.execute(
                """
                SELECT entry_id, title, shelf_path, entry_type,
                       quality_score, usage_count, was_helpful, was_unhelpful,
                       updated_at, summary, keywords
                FROM hot_entries
                ORDER BY usage_count DESC, updated_at DESC
                LIMIT ?
                """,
                [limit],
            )
            columns = [desc[0] for desc in result.description]
            return [dict(zip(columns, row)) for row in result.fetchall()]

        return await asyncio.to_thread(_query)

    async def get_recent(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get the most recently updated entries.

        Args:
            limit: Maximum number of entries to return.

        Returns:
            A list of dicts with entry metadata, ordered by ``updated_at`` DESC.
        """
        def _query() -> list[dict[str, Any]]:
            con = self._ensure_con()
            result = con.execute(
                """
                SELECT entry_id, title, shelf_path, entry_type,
                       quality_score, usage_count, was_helpful, was_unhelpful,
                       updated_at, summary, keywords
                FROM hot_entries
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                [limit],
            )
            columns = [desc[0] for desc in result.description]
            return [dict(zip(columns, row)) for row in result.fetchall()]

        return await asyncio.to_thread(_query)

    async def get_top_quality(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get entries with the highest quality scores.

        Args:
            limit: Maximum number of entries to return.

        Returns:
            A list of dicts with entry metadata, ordered by ``quality_score`` DESC.
        """
        def _query() -> list[dict[str, Any]]:
            con = self._ensure_con()
            result = con.execute(
                """
                SELECT entry_id, title, shelf_path, entry_type,
                       quality_score, usage_count, was_helpful, was_unhelpful,
                       updated_at, summary, keywords
                FROM hot_entries
                ORDER BY quality_score DESC, usage_count DESC
                LIMIT ?
                """,
                [limit],
            )
            columns = [desc[0] for desc in result.description]
            return [dict(zip(columns, row)) for row in result.fetchall()]

        return await asyncio.to_thread(_query)

    async def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Fast full-text search on title, summary, and keywords.

        Uses DuckDB's string matching (LIKE/ILIKE) for broad text search
        across the indexed fields.

        Args:
            query: The search string (case-insensitive).
            limit: Maximum number of results.

        Returns:
            A list of dicts with entry metadata.
        """
        def _query() -> list[dict[str, Any]]:
            con = self._ensure_con()
            pattern = f"%{query}%"
            result = con.execute(
                """
                SELECT entry_id, title, shelf_path, entry_type,
                       quality_score, usage_count, was_helpful, was_unhelpful,
                       updated_at, summary, keywords
                FROM hot_entries
                WHERE title ILIKE ?
                   OR summary ILIKE ?
                   OR keywords ILIKE ?
                ORDER BY quality_score DESC, usage_count DESC
                LIMIT ?
                """,
                [pattern, pattern, pattern, limit],
            )
            columns = [desc[0] for desc in result.description]
            return [dict(zip(columns, row)) for row in result.fetchall()]

        return await asyncio.to_thread(_query)

    async def get_shelf_stats(self) -> list[dict[str, Any]]:
        """Aggregate statistics per shelf path.

        Returns:
            A list of dicts, each with keys: ``shelf_path``, ``entry_count``,
            ``avg_quality``, ``total_usage``.
        """
        def _query() -> list[dict[str, Any]]:
            con = self._ensure_con()
            result = con.execute(
                """
                SELECT shelf_path,
                       COUNT(*)          AS entry_count,
                       AVG(quality_score) AS avg_quality,
                       SUM(usage_count)  AS total_usage
                FROM hot_entries
                GROUP BY shelf_path
                ORDER BY entry_count DESC
                """
            )
            columns = [desc[0] for desc in result.description]
            rows = [dict(zip(columns, row)) for row in result.fetchall()]
            # Round avg_quality for readability
            for row in rows:
                row["avg_quality"] = round(float(row["avg_quality"]), 4)
            return rows

        return await asyncio.to_thread(_query)
