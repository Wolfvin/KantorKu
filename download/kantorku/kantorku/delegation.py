"""
Delegation — Sub-task delegation between workers.

Allows workers to break their tasks into sub-tasks and delegate
them to other workers. This enables collaborative problem-solving
where a worker can request help from a specialist.

Usage:
    from kantorku.delegation import DelegationManager, DelegationRequest

    # Inside a worker's handle() method:
    delegation = DelegationManager(registry, bus, ring1)

    # Delegate a sub-task to another worker
    result = await delegation.delegate(
        from_worker="coder_backend",
        to_worker="debugger",
        instruction="Debug the database connection issue",
        session_id="session-1",
        parent_task_id="task-123",
    )
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from kantorku.events.bus import EventBus
from kantorku.events.emitter import EventEmitter
from kantorku.worker.base import BaseWorker, Task, TaskResult
from kantorku.worker.registry import WorkerRegistry
from kantorku.memory.ring1 import Ring1Memory


@dataclass
class DelegationRequest:
    """A request to delegate a sub-task to another worker."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    from_worker: str = ""
    to_worker: str = ""
    instruction: str = ""
    session_id: str = ""
    parent_task_id: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 120

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "from_worker": self.from_worker,
            "to_worker": self.to_worker,
            "instruction": self.instruction,
            "session_id": self.session_id,
            "parent_task_id": self.parent_task_id,
            "context": self.context,
        }


@dataclass
class DelegationResult:
    """The result of a delegated sub-task."""
    delegation_id: str = ""
    from_worker: str = ""
    to_worker: str = ""
    status: str = "done"  # done | failed | timeout
    output: str = ""
    error: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "delegation_id": self.delegation_id,
            "from_worker": self.from_worker,
            "to_worker": self.to_worker,
            "status": self.status,
            "output": self.output,
            "error": self.error,
            "data": self.data,
        }


class DelegationManager:
    """
    Manages sub-task delegation between workers.

    When a worker encounters a problem outside its expertise,
    it can delegate a sub-task to a more specialized worker.
    The delegating worker waits for the result before continuing.

    Delegation is different from WorkerHub DM:
    - DM is for questions/discussion
    - Delegation is for actual work execution
    - The delegated worker runs the task and returns a result

    Usage:
        delegation = DelegationManager(registry, bus, ring1)

        # In a worker's handle() method:
        result = await delegation.delegate(
            from_worker="coder_backend",
            to_worker="debugger",
            instruction="Find the root cause of this TypeError",
            session_id="sess-1",
            parent_task_id=task.id,
        )

        if result.status == "done":
            # Use the debugger's output
            analysis = result.output
    """

    def __init__(
        self,
        registry: WorkerRegistry,
        bus: EventBus,
        ring1: Ring1Memory | None = None,
    ) -> None:
        self.registry = registry
        self.bus = bus
        self.ring1 = ring1
        self._history: list[dict[str, Any]] = []

    async def delegate(
        self,
        from_worker: str,
        to_worker: str,
        instruction: str,
        session_id: str,
        parent_task_id: str = "",
        context: dict[str, Any] | None = None,
        timeout_seconds: int = 120,
    ) -> DelegationResult:
        """
        Delegate a sub-task to another worker.

        Args:
            from_worker: ID of the delegating worker
            to_worker: ID of the worker to delegate to
            instruction: What the delegated worker should do
            session_id: Current session ID
            parent_task_id: ID of the parent task
            context: Additional context for the delegated worker
            timeout_seconds: Maximum time to wait for the result

        Returns:
            DelegationResult with the delegated worker's output
        """
        request = DelegationRequest(
            from_worker=from_worker,
            to_worker=to_worker,
            instruction=instruction,
            session_id=session_id,
            parent_task_id=parent_task_id,
            context=context or {},
            timeout_seconds=timeout_seconds,
        )

        emitter = EventEmitter(self.bus, session_id)

        # Emit delegation event
        await emitter.worker_dm(
            from_id=from_worker,
            to_id=to_worker,
            content=f"[DELEGATION] {instruction}",
        )

        # Check if target worker exists
        if to_worker not in self.registry.all_worker_ids:
            return DelegationResult(
                delegation_id=request.id,
                from_worker=from_worker,
                to_worker=to_worker,
                status="failed",
                error=f"Worker '{to_worker}' not found in registry",
            )

        # Create sub-task
        sub_task = Task(
            instruction=instruction,
            session_id=session_id,
            context={
                "delegated_by": from_worker,
                "parent_task_id": parent_task_id,
                **(context or {}),
            },
            parent_task_id=parent_task_id,
        )

        # Get worker and execute
        try:
            worker = self.registry.hire(to_worker)
            result = await worker.execute(sub_task, timeout=timeout_seconds)

            delegation_result = DelegationResult(
                delegation_id=request.id,
                from_worker=from_worker,
                to_worker=to_worker,
                status=result.status,
                output=result.output,
                error=result.error,
                data=result.data,
            )

            # Store delegation in Ring1
            if self.ring1:
                await self.ring1.store_task_result(
                    task_id=request.id,
                    worker_id=to_worker,
                    session_id=session_id,
                    result=delegation_result.to_dict(),
                )

            # Record in history
            self._history.append({
                "request": request.to_dict(),
                "result": delegation_result.to_dict(),
            })

            return delegation_result

        except Exception as e:
            return DelegationResult(
                delegation_id=request.id,
                from_worker=from_worker,
                to_worker=to_worker,
                status="failed",
                error=str(e),
            )

    async def broadcast_request(
        self,
        from_worker: str,
        instruction: str,
        squad: str = "",
        session_id: str = "",
        parent_task_id: str = "",
    ) -> list[DelegationResult]:
        """
        Broadcast a request to all workers in a squad.
        Useful for gathering multiple perspectives.

        Args:
            from_worker: Delegating worker ID
            instruction: What to ask
            squad: Target squad (empty = all workers)
            session_id: Session ID
            parent_task_id: Parent task ID

        Returns:
            List of DelegationResults from responding workers
        """
        emitter = EventEmitter(self.bus, session_id)
        await emitter.worker_broadcast(
            from_id=from_worker,
            content=f"[BROADCAST REQUEST] {instruction}",
        )

        # Get workers by squad
        if squad:
            workers = [w for w in self.registry.list_workers() if w.get("squad") == squad]
        else:
            workers = self.registry.list_workers()

        results = []
        for w in workers:
            worker_id = w["id"]
            if worker_id == from_worker:
                continue  # Don't delegate to self

            result = await self.delegate(
                from_worker=from_worker,
                to_worker=worker_id,
                instruction=instruction,
                session_id=session_id,
                parent_task_id=parent_task_id,
                timeout_seconds=60,
            )
            results.append(result)

        return results

    def get_history(self, session_id: str = "") -> list[dict[str, Any]]:
        """Get delegation history, optionally filtered by session."""
        if not session_id:
            return self._history
        return [
            h for h in self._history
            if h.get("request", {}).get("session_id") == session_id
        ]

    def get_delegation_count(self, from_worker: str = "", to_worker: str = "") -> int:
        """Count delegations, optionally filtered by worker."""
        count = 0
        for h in self._history:
            req = h.get("request", {})
            if from_worker and req.get("from_worker") != from_worker:
                continue
            if to_worker and req.get("to_worker") != to_worker:
                continue
            count += 1
        return count
