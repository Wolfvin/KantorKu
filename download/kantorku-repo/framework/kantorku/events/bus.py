"""
EventBus — Internal pub/sub for all kantorku activity.

Every worker action, pool fetch, memory access → event → subscribers.

Supports:
- Per-session channels (each user session gets its own stream)
- Global subscriptions (for logging, sentinel)
- Async iteration (WebSocket friendly)
"""

from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Callable, Awaitable


@dataclass
class Event:
    """A single event in the kantorku event stream."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    type: str = ""
    from_id: str = ""
    to_id: str = ""
    content: str = ""
    session_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = {
            "id": self.id,
            "type": self.type,
            "from": self.from_id,
            "to": self.to_id,
            "content": self.content,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
        }
        if self.data:
            d.update(self.data)
        return d


class _SessionChannel:
    """One session's event stream. AsyncIterator friendly."""

    def __init__(self, session_id: str, bus: EventBus):
        self.session_id = session_id
        self._bus = bus
        self._queue: asyncio.Queue[Event] = asyncio.Queue()
        self._subscribers: list[Callable[[Event], Awaitable[None]]] = []

    async def put(self, event: Event) -> None:
        await self._queue.put(event)
        for sub in self._subscribers:
            await sub(event)

    async def get(self) -> Event:
        return await self._queue.get()

    def subscribe(self, callback: Callable[[Event], Awaitable[None]]) -> None:
        self._subscribers.append(callback)

    def __aiter__(self) -> AsyncIterator[Event]:
        return self

    async def __anext__(self) -> Event:
        return await self._queue.get()


class EventBus:
    """
    Internal pub/sub — the nervous system of kantorku.

    Usage:
        bus = EventBus()
        await bus.emit("session-1", {"type": "task_assigned", ...})
        async with bus.subscribe("session-1") as events:
            async for event in events:
                print(event.to_dict())
    """

    def __init__(self) -> None:
        self._channels: dict[str, _SessionChannel] = {}
        self._global_subscribers: list[Callable[[Event], Awaitable[None]]] = []
        self._history: dict[str, list[Event]] = defaultdict(list)
        self._max_history = 500

    def _get_channel(self, session_id: str) -> _SessionChannel:
        if session_id not in self._channels:
            self._channels[session_id] = _SessionChannel(session_id, self)
        return self._channels[session_id]

    async def emit(self, session_id: str, data: dict[str, Any]) -> Event:
        """
        Emit an event to a session channel.
        Also notifies global subscribers.
        """
        event = Event(
            type=data.get("type", "unknown"),
            from_id=data.get("from", ""),
            to_id=data.get("to", ""),
            content=data.get("content", ""),
            session_id=session_id,
            data=data,
        )

        channel = self._get_channel(session_id)
        await channel.put(event)

        # History
        self._history[session_id].append(event)
        if len(self._history[session_id]) > self._max_history:
            self._history[session_id] = self._history[session_id][-self._max_history:]

        # Global subscribers
        for sub in self._global_subscribers:
            await sub(event)

        return event

    @asynccontextmanager
    async def subscribe(self, session_id: str) -> AsyncIterator[_SessionChannel]:
        """
        Subscribe to a session's event stream.
        Returns an async iterable of Events.
        """
        channel = self._get_channel(session_id)
        try:
            yield channel
        finally:
            pass  # Channel persists for history

    def subscribe_global(self, callback: Callable[[Event], Awaitable[None]]) -> None:
        """Subscribe to ALL events across all sessions."""
        self._global_subscribers.append(callback)

    def get_history(self, session_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent events for a session (for reconnection/replay)."""
        events = self._history.get(session_id, [])
        return [e.to_dict() for e in events[-limit:]]

    async def cleanup_session(self, session_id: str) -> None:
        """Clean up session resources."""
        if session_id in self._channels:
            del self._channels[session_id]
