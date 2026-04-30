"""
Ring2 — SQLite + Parquet warm memory.

Stores:
- Episode logs (what happened, what worked, what didn't)
- Audit trails
- Training data for future fine-tuning
- Sentinel error logs and lessons

SQLite for structured queries, Parquet for bulk analytics.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import aiosqlite
except ImportError:
    aiosqlite = None  # type: ignore


class Ring2Memory:
    """
    Ring 2 — SQLite + Parquet warm memory.

    Usage:
        ring2 = Ring2Memory("data/ring2.db")
        await ring2.initialize()

        # Log an episode
        await ring2.log_episode("session-1", "task_assigned", {...})

        # Log a lesson
        await ring2.log_lesson("sentinel", "Always check timeout handling", "debugging")

        # Query lessons
        lessons = await ring2.get_lessons(category="debugging")
    """

    def __init__(self, path: str = "data/ring2.db") -> None:
        self.path = path
        self._db: Any = None

    async def initialize(self) -> None:
        """Initialize SQLite database and create tables."""
        if aiosqlite is None:
            raise ImportError(
                "Ring2 requires 'aiosqlite' package. pip install aiosqlite"
            )

        Path(self.path).parent.mkdir(parents=True, exist_ok=True)

        self._db = await aiosqlite.connect(self.path)
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                event_type TEXT,
                data JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                lesson TEXT,
                category TEXT,
                context JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS audit_trail (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                worker_id TEXT,
                action TEXT,
                details JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_episodes_session ON episodes(session_id);
            CREATE INDEX IF NOT EXISTS idx_lessons_category ON lessons(category);
            CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_trail(session_id);
        """)
        await self._db.commit()

    async def log_episode(
        self,
        session_id: str,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        """Log an episode (any significant event)."""
        await self._db.execute(
            "INSERT INTO episodes (session_id, event_type, data) VALUES (?, ?, ?)",
            [session_id, event_type, json.dumps(data)],
        )
        await self._db.commit()

    async def get_episodes(
        self,
        session_id: str,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query episodes for a session."""
        if event_type:
            cursor = await self._db.execute(
                "SELECT event_type, data, created_at FROM episodes "
                "WHERE session_id = ? AND event_type = ? ORDER BY id DESC LIMIT ?",
                [session_id, event_type, limit],
            )
        else:
            cursor = await self._db.execute(
                "SELECT event_type, data, created_at FROM episodes "
                "WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                [session_id, limit],
            )

        rows = await cursor.fetchall()
        return [
            {"event_type": r[0], "data": json.loads(r[1]), "created_at": r[2]}
            for r in reversed(rows)
        ]

    async def log_lesson(
        self,
        source: str,
        lesson: str,
        category: str = "general",
        context: dict[str, Any] | None = None,
    ) -> None:
        """Log a lesson learned (from Sentinel or other sources)."""
        await self._db.execute(
            "INSERT INTO lessons (source, lesson, category, context) VALUES (?, ?, ?, ?)",
            [source, lesson, category, json.dumps(context or {})],
        )
        await self._db.commit()

    async def get_lessons(
        self,
        category: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get lessons, optionally filtered by category."""
        if category:
            cursor = await self._db.execute(
                "SELECT source, lesson, category, created_at FROM lessons "
                "WHERE category = ? ORDER BY id DESC LIMIT ?",
                [category, limit],
            )
        else:
            cursor = await self._db.execute(
                "SELECT source, lesson, category, created_at FROM lessons "
                "ORDER BY id DESC LIMIT ?",
                [limit],
            )

        rows = await cursor.fetchall()
        return [
            {"source": r[0], "lesson": r[1], "category": r[2], "created_at": r[3]}
            for r in reversed(rows)
        ]

    async def log_audit(
        self,
        session_id: str,
        worker_id: str,
        action: str,
        details: dict[str, Any],
    ) -> None:
        """Log an audit trail entry."""
        await self._db.execute(
            "INSERT INTO audit_trail (session_id, worker_id, action, details) VALUES (?, ?, ?, ?)",
            [session_id, worker_id, action, json.dumps(details)],
        )
        await self._db.commit()

    async def close(self) -> None:
        """Close the SQLite connection."""
        if self._db:
            await self._db.close()
            self._db = None
