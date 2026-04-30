"""
Cache — LLM response caching for kantorku.

Caches LLM responses to avoid redundant API calls for identical prompts.
Supports in-memory and DuckDB-backed persistent caching.

Usage:
    from kantorku.cache import LLMCache

    cache = LLMCache(backend="memory", ttl_seconds=3600)

    # Check cache before calling LLM
    cached = await cache.get(model, messages_hash)
    if cached:
        return cached

    # Store result after LLM call
    await cache.put(model, messages_hash, response)
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CacheEntry:
    """A cached LLM response."""
    key: str
    model: str
    response: str
    created_at: float = field(default_factory=time.time)
    ttl_seconds: float = 3600.0
    hit_count: int = 0

    @property
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        if self.ttl_seconds <= 0:
            return False  # No expiration
        return (time.time() - self.created_at) > self.ttl_seconds


def compute_cache_key(model: str, messages: list[dict[str, str]], **kwargs: Any) -> str:
    """
    Compute a deterministic cache key from model, messages, and params.

    Args:
        model: Model identifier
        messages: Chat messages
        **kwargs: Additional parameters (temperature, etc.)

    Returns:
        SHA-256 hash string
    """
    # Normalize messages for consistent hashing
    normalized = json.dumps(
        {"model": model, "messages": messages, "params": {k: v for k, v in sorted(kwargs.items())}},
        sort_keys=True,
        ensure_ascii=True,
    )
    return hashlib.sha256(normalized.encode()).hexdigest()[:32]


class MemoryCacheBackend:
    """In-memory cache backend — fast but not persistent."""

    def __init__(self, max_size: int = 1000) -> None:
        self._entries: dict[str, CacheEntry] = {}
        self._max_size = max_size

    async def get(self, key: str) -> CacheEntry | None:
        entry = self._entries.get(key)
        if entry and not entry.is_expired:
            entry.hit_count += 1
            return entry
        if entry and entry.is_expired:
            del self._entries[key]
        return None

    async def put(self, entry: CacheEntry) -> None:
        # Evict if at capacity
        if len(self._entries) >= self._max_size and entry.key not in self._entries:
            self._evict()
        self._entries[entry.key] = entry

    async def delete(self, key: str) -> None:
        self._entries.pop(key, None)

    async def clear(self) -> None:
        self._entries.clear()

    async def size(self) -> int:
        return len(self._entries)

    def _evict(self) -> None:
        """Evict the least recently used entry."""
        if not self._entries:
            return
        # Simple LRU: evict the entry with the lowest hit count
        lru_key = min(self._entries, key=lambda k: self._entries[k].hit_count)
        del self._entries[lru_key]


class DuckDBCacheBackend:
    """
    DuckDB-backed persistent cache — survives server restarts.

    Stores cache entries in a DuckDB table for persistence.
    """

    def __init__(self, db_path: str = "data/cache.duckdb") -> None:
        self._db_path = db_path
        self._conn: Any = None

    async def initialize(self) -> None:
        """Initialize the DuckDB connection and create table."""
        try:
            import duckdb
        except ImportError:
            raise ImportError("DuckDB cache requires 'duckdb' package")

        from pathlib import Path
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

        self._conn = duckdb.connect(self._db_path)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS llm_cache (
                key VARCHAR PRIMARY KEY,
                model VARCHAR,
                response TEXT,
                created_at DOUBLE,
                ttl_seconds DOUBLE,
                hit_count INTEGER DEFAULT 0
            )
        """)

    async def get(self, key: str) -> CacheEntry | None:
        if not self._conn:
            return None

        result = self._conn.execute(
            "SELECT key, model, response, created_at, ttl_seconds, hit_count FROM llm_cache WHERE key = ?",
            [key],
        ).fetchone()

        if not result:
            return None

        entry = CacheEntry(
            key=result[0],
            model=result[1],
            response=result[2],
            created_at=result[3],
            ttl_seconds=result[4],
            hit_count=result[5],
        )

        if entry.is_expired:
            await self.delete(key)
            return None

        # Increment hit count
        self._conn.execute(
            "UPDATE llm_cache SET hit_count = hit_count + 1 WHERE key = ?",
            [key],
        )
        entry.hit_count += 1
        return entry

    async def put(self, entry: CacheEntry) -> None:
        if not self._conn:
            return

        self._conn.execute(
            """INSERT OR REPLACE INTO llm_cache (key, model, response, created_at, ttl_seconds, hit_count)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [entry.key, entry.model, entry.response, entry.created_at, entry.ttl_seconds, 0],
        )

    async def delete(self, key: str) -> None:
        if self._conn:
            self._conn.execute("DELETE FROM llm_cache WHERE key = ?", [key])

    async def clear(self) -> None:
        if self._conn:
            self._conn.execute("DELETE FROM llm_cache")

    async def size(self) -> int:
        if not self._conn:
            return 0
        result = self._conn.execute("SELECT COUNT(*) FROM llm_cache").fetchone()
        return result[0] if result else 0

    async def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None


class LLMCache:
    """
    LLM response cache for kantorku.

    Wraps a cache backend with a high-level API. Computes cache keys
    automatically from model, messages, and parameters.

    Usage:
        cache = LLMCache(backend="memory", ttl_seconds=3600)

        # Check before LLM call
        cached_response = await cache.lookup("anthropic/claude-opus-4-6", messages)
        if cached_response:
            return cached_response

        # Store after LLM call
        await cache.store("anthropic/claude-opus-4-6", messages, response)
    """

    def __init__(
        self,
        backend: str = "memory",
        ttl_seconds: float = 3600.0,
        max_size: int = 1000,
        db_path: str = "data/cache.duckdb",
    ) -> None:
        """
        Args:
            backend: "memory" or "duckdb"
            ttl_seconds: Time-to-live for cache entries (0 = no expiration)
            max_size: Maximum entries (memory backend only)
            db_path: Database path (duckdb backend only)
        """
        self.ttl_seconds = ttl_seconds

        if backend == "duckdb":
            self._backend = DuckDBCacheBackend(db_path)
        else:
            self._backend = MemoryCacheBackend(max_size)

        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the cache backend (required for DuckDB)."""
        if self._initialized:
            return
        if isinstance(self._backend, DuckDBCacheBackend):
            await self._backend.initialize()
        self._initialized = True

    async def lookup(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> str | None:
        """
        Look up a cached response.

        Args:
            model: Full model identifier
            messages: Chat messages
            **kwargs: Additional LLM parameters

        Returns:
            Cached response text, or None if not found/expired
        """
        if not self._initialized:
            await self.initialize()

        key = compute_cache_key(model, messages, **kwargs)
        entry = await self._backend.get(key)
        return entry.response if entry else None

    async def store(
        self,
        model: str,
        messages: list[dict[str, str]],
        response: str,
        **kwargs: Any,
    ) -> None:
        """
        Store an LLM response in the cache.

        Args:
            model: Full model identifier
            messages: Chat messages
            response: The LLM response text
            **kwargs: Additional LLM parameters
        """
        if not self._initialized:
            await self.initialize()

        key = compute_cache_key(model, messages, **kwargs)
        entry = CacheEntry(
            key=key,
            model=model,
            response=response,
            ttl_seconds=self.ttl_seconds,
        )
        await self._backend.put(entry)

    async def invalidate(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> None:
        """Remove a specific cached response."""
        key = compute_cache_key(model, messages, **kwargs)
        await self._backend.delete(key)

    async def clear(self) -> None:
        """Clear all cached responses."""
        await self._backend.clear()

    async def size(self) -> int:
        """Get the number of cached entries."""
        return await self._backend.size()

    async def close(self) -> None:
        """Close the cache backend."""
        if isinstance(self._backend, DuckDBCacheBackend):
            await self._backend.close()
