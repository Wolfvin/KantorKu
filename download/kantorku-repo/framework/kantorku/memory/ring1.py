"""
Ring1 — DuckDB hot memory.

Ultra-fast in-process analytical database for:
- Session state and history
- Prefetched context (from ContextPool)
- Task results and artifacts
- Active worker status

μs latency, in-process, no network overhead.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

try:
    import duckdb
except ImportError:
    duckdb = None  # type: ignore


class Ring1Memory:
    """
    Ring 1 — DuckDB hot memory.

    Stores session data, prefetched context, and task results
    with microsecond latency. In-process, no network.

    Usage:
        ring1 = Ring1Memory("data/ring1.duckdb")
        await ring1.initialize()

        # Store context
        await ring1.store_context("todo-1", {"files": [...], "patterns": [...]})

        # Get context
        context = await ring1.get_context("todo-1")

        # Store session
        await ring1.store_session("session-1", {"user": "client", ...})
    """

    def __init__(self, path: str = "data/ring1.duckdb") -> None:
        self.path = path
        self._conn: Any = None

    async def initialize(self) -> None:
        """Initialize DuckDB and create tables."""
        if duckdb is None:
            raise ImportError(
                "Ring1 requires 'duckdb' package. pip install duckdb"
            )

        # Ensure directory exists
        from pathlib import Path
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)

        self._conn = duckdb.connect(self.path)

        # Create tables
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS contexts (
                task_id VARCHAR PRIMARY KEY,
                session_id VARCHAR,
                context JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id VARCHAR PRIMARY KEY,
                state JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS task_results (
                task_id VARCHAR,
                worker_id VARCHAR,
                session_id VARCHAR,
                result JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create sequence before table that references it
        try:
            self._conn.execute("CREATE SEQUENCE IF NOT EXISTS history_id_seq START 1")
        except Exception:
            pass  # Sequence might already exist

        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY DEFAULT nextval('history_id_seq'),
                session_id VARCHAR,
                role VARCHAR,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    async def store_context(self, task_id: str, context: dict[str, Any]) -> None:
        """Store prefetched context for a task."""
        self._conn.execute(
            "INSERT OR REPLACE INTO contexts (task_id, session_id, context) VALUES (?, ?, ?)",
            [task_id, context.get("session_id", ""), json.dumps(context)],
        )

    async def get_context(self, task_id: str) -> dict[str, Any] | None:
        """Get prefetched context for a task."""
        result = self._conn.execute(
            "SELECT context FROM contexts WHERE task_id = ?",
            [task_id],
        ).fetchone()

        if result:
            return json.loads(result[0])
        return None

    async def store_session(self, session_id: str, state: dict[str, Any]) -> None:
        """Store session state."""
        self._conn.execute(
            """INSERT OR REPLACE INTO sessions (session_id, state, updated_at)
               VALUES (?, ?, CURRENT_TIMESTAMP)""",
            [session_id, json.dumps(state)],
        )

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get session state."""
        result = self._conn.execute(
            "SELECT state FROM sessions WHERE session_id = ?",
            [session_id],
        ).fetchone()

        if result:
            return json.loads(result[0])
        return None

    async def store_task_result(
        self, task_id: str, worker_id: str, session_id: str, result: dict[str, Any]
    ) -> None:
        """Store a task result."""
        self._conn.execute(
            "INSERT INTO task_results (task_id, worker_id, session_id, result) VALUES (?, ?, ?, ?)",
            [task_id, worker_id, session_id, json.dumps(result)],
        )

    async def get_task_results(self, session_id: str) -> list[dict[str, Any]]:
        """Get all task results for a session."""
        results = self._conn.execute(
            "SELECT task_id, worker_id, result FROM task_results WHERE session_id = ?",
            [session_id],
        ).fetchall()

        return [
            {"task_id": r[0], "worker_id": r[1], **json.loads(r[2])}
            for r in results
        ]

    async def add_history(
        self, session_id: str, role: str, content: str
    ) -> None:
        """Add a message to session history."""
        self._conn.execute(
            "INSERT INTO history (session_id, role, content) VALUES (?, ?, ?)",
            [session_id, role, content],
        )

    async def get_history(
        self, session_id: str, limit: int = 50
    ) -> list[dict[str, str]]:
        """Get session history."""
        results = self._conn.execute(
            "SELECT role, content FROM history WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            [session_id, limit],
        ).fetchall()

        return [{"role": r[0], "content": r[1]} for r in reversed(results)]

    async def cleanup_session(self, session_id: str) -> None:
        """Clean up session data."""
        self._conn.execute("DELETE FROM sessions WHERE session_id = ?", [session_id])
        self._conn.execute("DELETE FROM history WHERE session_id = ?", [session_id])

    async def close(self) -> None:
        """Close the DuckDB connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
