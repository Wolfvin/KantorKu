"""
WorkerHub — Peer-to-peer communication between workers.

Workers can:
- DM each other (visible in Panel 2)
- Broadcast to all workers
- Escalate blockers to Conductor

This is the "social layer" of kantorku — workers aren't isolated,
they communicate and coordinate like a real team.
"""

from __future__ import annotations

import asyncio
from typing import Any

from kantorku.events.bus import EventBus
from kantorku.events.emitter import EventEmitter
from kantorku.layers.conductor import Conductor
from kantorku.worker.registry import WorkerRegistry


class WorkerHub:
    """
    WorkerHub — DM and broadcast layer between workers.

    Usage:
        hub = WorkerHub(registry=registry, bus=bus, conductor=conductor)

        # Worker A DMs Worker B
        response = await hub.dm("coder_backend", "coder_wiring", "Need WS pattern")

        # Worker broadcasts to all
        await hub.broadcast("coder_backend", "Found issue with auth module")
    """

    def __init__(
        self,
        registry: WorkerRegistry,
        bus: EventBus,
        conductor: Conductor,
    ) -> None:
        self.registry = registry
        self.bus = bus
        self.conductor = conductor

    async def dm(
        self,
        from_id: str,
        to_id: str,
        message: str,
        session_id: str = "",
    ) -> dict[str, Any]:
        """
        Direct message from one worker to another.
        Visible in Panel 2. Blockers are escalated to Conductor.

        Args:
            from_id: Sending worker ID
            to_id: Receiving worker ID
            message: Message content
            session_id: Session identifier

        Returns:
            Response dict from receiving worker
        """
        emitter = EventEmitter(self.bus, session_id)

        # Emit DM event for Panel 2
        await emitter.worker_dm(from_id=from_id, to_id=to_id, content=message)

        # Get the receiving worker and deliver message
        to_worker = self.registry.hire(to_id)
        response = await to_worker.receive_dm(from_id, message)

        # If blocker → escalate to Conductor
        if response.get("is_blocker"):
            await self.conductor.notify_blocker(
                from_id=from_id,
                to_id=to_id,
                details=response,
                session_id=session_id,
            )

        return response

    async def broadcast(
        self,
        from_id: str,
        message: str,
        session_id: str = "",
    ) -> list[dict[str, Any]]:
        """
        Broadcast a message from one worker to all others.
        Useful for sharing discoveries or warnings.

        Args:
            from_id: Sending worker ID
            message: Message content
            session_id: Session identifier

        Returns:
            List of responses from all workers
        """
        emitter = EventEmitter(self.bus, session_id)

        # Emit broadcast event for Panel 2
        await emitter.worker_broadcast(from_id=from_id, content=message)

        # Send to all workers except sender
        responses: list[dict[str, Any]] = []
        for worker_id in self.registry.all_worker_ids:
            if worker_id == from_id:
                continue

            try:
                worker = self.registry.hire(worker_id)
                response = await asyncio.wait_for(
                    worker.receive_broadcast(from_id, message),
                    timeout=10.0,
                )
                responses.append({
                    "from": from_id,
                    "to": worker_id,
                    "response": response,
                })
            except (asyncio.TimeoutError, Exception):
                continue

        return responses

    async def request_help(
        self,
        from_id: str,
        to_id: str,
        question: str,
        session_id: str = "",
    ) -> dict[str, Any]:
        """
        Worker requests help from another worker.
        Like a DM but with explicit help-seeking semantics.
        """
        return await self.dm(
            from_id=from_id,
            to_id=to_id,
            message=f"[HELP REQUEST] {question}",
            session_id=session_id,
        )
