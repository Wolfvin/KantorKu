"""
ContextPool — DeepSeek pool manager with FIFO queue.

The pool manages multiple DeepSeek instances that:
- Prefetch context during briefing (proactive)
- Fetch context on demand for workers (reactive)
- Store results in Ring 1 for instant access

Queue is FIFO — no priority system. Simple by design.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from kantorku.events.bus import EventBus
from kantorku.events.emitter import EventEmitter
from kantorku.pool.pool_worker import PoolWorker
from kantorku.memory.ring1 import Ring1Memory


@dataclass
class ContextResult:
    """Result from a context fetch operation."""

    task_id: str = ""
    query: str = ""
    files: list[str] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    summary: str = ""
    raw_response: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "query": self.query,
            "files": self.files,
            "patterns": self.patterns,
            "references": self.references,
            "summary": self.summary,
        }


class ContextPool:
    """
    DeepSeek Context Pool with FIFO queue.

    Pool instances standby and listen to the queue.
    Proactive: prefetch during briefing breakdown.
    Reactive: fetch when a worker requests context.
    No priority system — FIFO, simple by design.

    Usage:
        pool = ContextPool(
            model="deepseek/deepseek-v3-2",
            size=3,
            bus=bus,
            ring1=ring1,
        )
        await pool.start()

        # Proactive (during briefing)
        await pool.prefetch("todo-1", "rate limiter patterns Rust", "session-1")

        # Reactive (worker request)
        await pool.request("coder_backend", "WebSocket reconnect pattern", "todo-2", "session-1")
    """

    def __init__(
        self,
        model: str = "deepseek/deepseek-v3-2",
        size: int = 3,
        bus: EventBus | None = None,
        ring1: Ring1Memory | None = None,
    ) -> None:
        self.model = model
        self.size = size
        self.bus = bus or EventBus()
        self.ring1 = ring1

        self.queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.instances: list[PoolWorker] = [
            PoolWorker(instance_id=i, model=model)
            for i in range(size)
        ]
        self._running = False
        self._tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        """Start all pool instances — they begin listening to the queue."""
        if self._running:
            return

        self._running = True
        self._tasks = [
            asyncio.create_task(
                inst.listen(self.queue, self.bus, self.ring1)
            )
            for inst in self.instances
        ]

    async def stop(self) -> None:
        """Stop all pool instances."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def prefetch(
        self,
        task_id: str,
        query: str,
        session_id: str,
    ) -> None:
        """
        Proactive prefetch — called during briefing when todos are broken down.
        Enters the FIFO queue like any other job.
        """
        emitter = EventEmitter(self.bus, session_id)

        await self.queue.put({
            "type": "prefetch",
            "task_id": task_id,
            "query": self._build_query(query),
            "raw_query": query,
            "session_id": session_id,
        })

        await emitter.context_fetch_start(
            instance=-1,  # Not yet assigned
            query=query,
            for_task=task_id,
        )

    async def request(
        self,
        worker_id: str,
        query: str,
        task_id: str,
        session_id: str,
    ) -> None:
        """
        Reactive request — called when a worker needs additional context.
        Enters the FIFO queue like any other job.
        """
        emitter = EventEmitter(self.bus, session_id)

        await self.queue.put({
            "type": "reactive",
            "worker_id": worker_id,
            "task_id": task_id,
            "query": query,
            "session_id": session_id,
        })

        await emitter.context_requested(
            from_id=worker_id,
            query=query,
        )

    def _build_query(self, todo_item: str) -> str:
        """Build a detailed context-fetch query from a todo item."""
        return f"""For task: "{todo_item}"

Find:
1. Files/functions/classes relevant to this task in the codebase
2. Existing patterns or examples that can be reused
3. Documentation or external references that would help
4. Dependencies that might be needed

Format: file location + brief snippet + reason for relevance."""

    def get_status(self) -> dict[str, Any]:
        """Get current pool status for monitoring."""
        return {
            "running": self._running,
            "queue_size": self.queue.qsize(),
            "instances": [
                {
                    "id": inst.id,
                    "status": inst.status,
                }
                for inst in self.instances
            ],
        }
