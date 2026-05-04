"""
TaskQueue — Persistent, prioritized task queue with retry and dead letter handling.

Provides:
- PriorityQueue: Priority-based task ordering (higher priority = executed first)
- PersistentStorage: Ring2-backed task persistence (survives restarts)
- RetryLogic: Configurable retry with exponential backoff per task
- DeadLetterQueue: Tasks that exceeded max retries are moved here
- Cancellation: Cancel pending or in-progress tasks
- Metrics: Queue depth, processing time, success/failure rates

The TaskQueue is used by the Office to manage task execution order,
ensure reliable delivery, and handle failures gracefully. Unlike the
in-memory DAGResolver which handles dependency ordering, the TaskQueue
handles execution scheduling, persistence, and reliability.

Usage:
    from kantorku.interface.task_queue import TaskQueue, QueuedTask

    queue = TaskQueue(ring2=ring2, bus=bus)

    # Enqueue a task
    task_id = await queue.enqueue(
        instruction="Implement authentication",
        session_id="sess-1",
        assigned_to="coder_backend",
        priority=5,
    )

    # Dequeue the next task
    task = await queue.dequeue()

    # Mark as done
    await queue.mark_done(task.id, result={"output": "done"})

    # If failed, it auto-retries or goes to DLQ
    await queue.mark_failed(task.id, error="timeout")
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from kantorku.events.bus import EventBus
from kantorku.events.emitter import EventEmitter
from kantorku.observability import get_tracer, get_metrics

logger = logging.getLogger("kantorku.task_queue")


# ── Task Queue States ─────────────────────────────────────────────────


class TaskState(str, Enum):
    """States a queued task can be in."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    DEAD_LETTER = "dead_letter"


# ── Queued Task ───────────────────────────────────────────────────────


@dataclass
class QueuedTask:
    """
    A task in the persistent queue.

    Extends the base Task with queue-specific metadata:
    - Priority (higher = executed first)
    - Retry count and max retries
    - State machine (pending → in_progress → done/failed)
    - Timing (enqueued_at, started_at, completed_at)
    - Dead letter tracking
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    instruction: str = ""
    session_id: str = ""
    assigned_to: str = ""
    priority: int = 0  # Higher = more important, processed first
    state: TaskState = TaskState.PENDING

    # Context
    context: dict[str, Any] = field(default_factory=dict)
    parent_task_id: str = ""
    contract_id: str = ""

    # Retry
    retry_count: int = 0
    max_retries: int = 2
    last_error: str = ""

    # Timing
    enqueued_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    started_at: str = ""
    completed_at: str = ""

    # Result
    result: dict[str, Any] = field(default_factory=dict)

    @property
    def is_retryable(self) -> bool:
        """Check if this task can be retried."""
        return self.retry_count < self.max_retries

    @property
    def processing_time_seconds(self) -> float:
        """Time spent processing (if started)."""
        if not self.started_at:
            return 0.0
        end = self.completed_at or datetime.now(timezone.utc).isoformat()
        try:
            start_dt = datetime.fromisoformat(self.started_at)
            end_dt = datetime.fromisoformat(end)
            return (end_dt - start_dt).total_seconds()
        except (ValueError, TypeError):
            return 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "instruction": self.instruction,
            "session_id": self.session_id,
            "assigned_to": self.assigned_to,
            "priority": self.priority,
            "state": self.state.value,
            "context": self.context,
            "parent_task_id": self.parent_task_id,
            "contract_id": self.contract_id,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "last_error": self.last_error,
            "enqueued_at": self.enqueued_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result": self.result,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QueuedTask:
        state_val = data.get("state", "pending")
        try:
            state = TaskState(state_val)
        except ValueError:
            state = TaskState.PENDING

        return cls(
            id=data.get("id", ""),
            instruction=data.get("instruction", ""),
            session_id=data.get("session_id", ""),
            assigned_to=data.get("assigned_to", ""),
            priority=data.get("priority", 0),
            state=state,
            context=data.get("context", {}),
            parent_task_id=data.get("parent_task_id", ""),
            contract_id=data.get("contract_id", ""),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 2),
            last_error=data.get("last_error", ""),
            enqueued_at=data.get("enqueued_at", ""),
            started_at=data.get("started_at", ""),
            completed_at=data.get("completed_at", ""),
            result=data.get("result", {}),
        )


# ── Dead Letter Queue ─────────────────────────────────────────────────


@dataclass
class DeadLetterEntry:
    """An entry in the dead letter queue — a task that failed permanently."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    original_task_id: str = ""
    instruction: str = ""
    session_id: str = ""
    assigned_to: str = ""
    retry_count: int = 0
    max_retries: int = 0
    last_error: str = ""
    all_errors: list[str] = field(default_factory=list)
    original_enqueued_at: str = ""
    dead_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    original_context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "original_task_id": self.original_task_id,
            "instruction": self.instruction,
            "session_id": self.session_id,
            "assigned_to": self.assigned_to,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "last_error": self.last_error,
            "all_errors": self.all_errors,
            "original_enqueued_at": self.original_enqueued_at,
            "dead_at": self.dead_at,
            "original_context": self.original_context,
        }


# ── Task Queue ────────────────────────────────────────────────────────


class TaskQueue:
    """
    Persistent, prioritized task queue with retry and dead letter handling.

    The queue uses a combination of:
    - In-memory priority queue for fast dequeue (asyncio.PriorityQueue)
    - Ring2 (SQLite) for persistence and crash recovery
    - EventBus for real-time notifications

    Features:
    - Priority ordering: Higher priority tasks are processed first
    - Persistence: All state changes are written to Ring2
    - Retry: Failed tasks can be automatically retried (configurable)
    - Dead Letter Queue: Tasks that exceed retries go to DLQ
    - Cancellation: Cancel pending or in-progress tasks
    - Metrics: Queue depth, wait time, processing time

    Usage:
        queue = TaskQueue(ring2=ring2, bus=bus)

        # Start the queue processor
        await queue.start()

        # Enqueue tasks
        await queue.enqueue("Build feature X", session_id="s1", priority=5)

        # Dequeue and process
        task = await queue.dequeue()
        try:
            result = await process(task)
            await queue.mark_done(task.id, result)
        except Exception as e:
            await queue.mark_failed(task.id, str(e))

        # Get DLQ items
        dlq = queue.get_dead_letter_queue()

        # Stop
        await queue.stop()
    """

    def __init__(
        self,
        ring2: Any = None,
        bus: EventBus | None = None,
        default_max_retries: int = 2,
        retry_delay_seconds: float = 5.0,
        max_queue_size: int = 1000,
    ) -> None:
        self.ring2 = ring2
        self.bus = bus
        self.default_max_retries = default_max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.max_queue_size = max_queue_size

        # In-memory queue: (neg_priority, enqueue_order, task_id)
        self._queue: asyncio.PriorityQueue[tuple[int, int, str]] = asyncio.PriorityQueue(
            maxsize=max_queue_size
        )
        self._tasks: dict[str, QueuedTask] = {}  # task_id -> QueuedTask
        self._dead_letter: list[DeadLetterEntry] = []
        self._enqueue_counter: int = 0  # For FIFO within same priority
        self._running: bool = False
        self._cancelled: set[str] = set()  # Cancelled task IDs
        self._in_progress: set[str] = set()  # Currently processing

        # Metrics
        self._metrics = get_metrics()
        self._tracer = get_tracer()
        self._total_enqueued: int = 0
        self._total_completed: int = 0
        self._total_failed: int = 0
        self._total_dead: int = 0
        self._total_retried: int = 0

    async def start(self) -> None:
        """Start the queue and recover persisted tasks."""
        self._running = True
        await self._recover_from_ring2()
        logger.info(
            f"TaskQueue started: {len(self._tasks)} tasks recovered, "
            f"{self._queue.qsize()} pending"
        )

    async def stop(self) -> None:
        """Stop the queue and persist state."""
        self._running = False
        # Persist all in-progress tasks back to pending
        for task_id in list(self._in_progress):
            task = self._tasks.get(task_id)
            if task and task.state == TaskState.IN_PROGRESS:
                task.state = TaskState.PENDING
                task.started_at = ""
                await self._persist_task(task)
        logger.info("TaskQueue stopped")

    async def enqueue(
        self,
        instruction: str,
        session_id: str = "",
        assigned_to: str = "",
        priority: int = 0,
        context: dict[str, Any] | None = None,
        parent_task_id: str = "",
        contract_id: str = "",
        max_retries: int | None = None,
    ) -> str:
        """
        Enqueue a new task.

        Args:
            instruction: What the task should do
            session_id: Session this task belongs to
            assigned_to: Worker ID to assign to
            priority: Higher = processed first (default 0)
            context: Additional context for the worker
            parent_task_id: Parent task if this is a subtask
            contract_id: Contract this task is part of
            max_retries: Override default max retries

        Returns:
            The task ID
        """
        task = QueuedTask(
            instruction=instruction,
            session_id=session_id,
            assigned_to=assigned_to,
            priority=priority,
            context=context or {},
            parent_task_id=parent_task_id,
            contract_id=contract_id,
            max_retries=max_retries if max_retries is not None else self.default_max_retries,
        )

        with self._tracer.span(
            "task_queue.enqueue",
            attributes={"task_id": task.id, "session_id": session_id, "priority": priority},
        ):
            self._tasks[task.id] = task
            self._enqueue_counter += 1
            # Negate priority so higher priority = lower number = dequeued first
            await self._queue.put((-priority, self._enqueue_counter, task.id))
            self._total_enqueued += 1

            # Persist
            await self._persist_task(task)

            # Emit event
            if self.bus:
                emitter = EventEmitter(self.bus, session_id)
                await emitter._emit(
                    type="task_enqueued",
                    **{"from": "task_queue"},
                    task_id=task.id,
                    instruction=instruction,
                    assigned_to=assigned_to,
                    priority=priority,
                )

        return task.id

    async def dequeue(self, timeout: float | None = None) -> QueuedTask | None:
        """
        Dequeue the next highest-priority task.

        Args:
            timeout: Maximum time to wait (None = wait forever, 0 = non-blocking)

        Returns:
            The next QueuedTask, or None if timeout/empty
        """
        try:
            if timeout == 0:
                # Non-blocking
                neg_priority, order, task_id = self._queue.get_nowait()
            elif timeout is not None:
                neg_priority, order, task_id = await asyncio.wait_for(
                    self._queue.get(), timeout=timeout
                )
            else:
                neg_priority, order, task_id = await self._queue.get()
        except (asyncio.QueueEmpty, asyncio.TimeoutError):
            return None

        task = self._tasks.get(task_id)
        if not task:
            return None

        # Skip cancelled tasks
        if task_id in self._cancelled:
            task.state = TaskState.CANCELLED
            self._cancelled.discard(task_id)
            return await self.dequeue(timeout=0)

        # Skip already-processed tasks (can happen after recovery)
        if task.state in (TaskState.DONE, TaskState.CANCELLED, TaskState.DEAD_LETTER):
            return await self.dequeue(timeout=0)

        # Mark as in-progress
        task.state = TaskState.IN_PROGRESS
        task.started_at = datetime.now(timezone.utc).isoformat()
        self._in_progress.add(task_id)

        await self._persist_task(task)
        return task

    async def mark_done(
        self,
        task_id: str,
        result: dict[str, Any] | None = None,
    ) -> None:
        """Mark a task as completed successfully."""
        task = self._tasks.get(task_id)
        if not task:
            logger.warning(f"mark_done: task {task_id} not found")
            return

        task.state = TaskState.DONE
        task.completed_at = datetime.now(timezone.utc).isoformat()
        task.result = result or {}
        self._in_progress.discard(task_id)
        self._total_completed += 1

        await self._persist_task(task)

        # Metrics
        self._metrics.record_duration(
            worker_id=task.assigned_to or "unknown",
            duration_seconds=task.processing_time_seconds,
            session_id=task.session_id,
            status="ok",
        )

        # Emit event
        if self.bus:
            emitter = EventEmitter(self.bus, task.session_id)
            await emitter._emit(
                type="task_completed",
                **{"from": "task_queue"},
                task_id=task_id,
                worker_id=task.assigned_to,
            )

    async def mark_failed(
        self,
        task_id: str,
        error: str = "",
    ) -> None:
        """
        Mark a task as failed.

        If the task has retries remaining, it's re-enqueued with retry_count incremented.
        If not, it's moved to the dead letter queue.
        """
        task = self._tasks.get(task_id)
        if not task:
            logger.warning(f"mark_failed: task {task_id} not found")
            return

        task.last_error = error
        task.retry_count += 1
        self._in_progress.discard(task_id)

        if task.is_retryable:
            # Re-enqueue for retry
            task.state = TaskState.RETRYING
            self._total_retried += 1

            # Delay before retry (exponential backoff)
            delay = self.retry_delay_seconds * (2 ** (task.retry_count - 1))

            await self._persist_task(task)

            # Schedule re-enqueue after delay
            asyncio.create_task(self._schedule_retry(task_id, delay))

            logger.info(
                f"Task {task_id} retry {task.retry_count}/{task.max_retries} "
                f"after {delay:.1f}s: {error[:100]}"
            )
        else:
            # Move to dead letter queue
            self._move_to_dead_letter(task, error)

    async def _schedule_retry(self, task_id: str, delay: float) -> None:
        """Re-enqueue a task after a delay."""
        await asyncio.sleep(delay)

        task = self._tasks.get(task_id)
        if not task or task.state != TaskState.RETRYING:
            return

        # Reset state to pending and re-enqueue
        task.state = TaskState.PENDING
        task.started_at = ""
        self._enqueue_counter += 1
        await self._queue.put((-task.priority, self._enqueue_counter, task_id))
        await self._persist_task(task)

    def _move_to_dead_letter(self, task: QueuedTask, error: str) -> None:
        """Move a task to the dead letter queue."""
        task.state = TaskState.DEAD_LETTER
        task.completed_at = datetime.now(timezone.utc).isoformat()

        entry = DeadLetterEntry(
            original_task_id=task.id,
            instruction=task.instruction,
            session_id=task.session_id,
            assigned_to=task.assigned_to,
            retry_count=task.retry_count,
            max_retries=task.max_retries,
            last_error=error,
            all_errors=[task.last_error],
            original_enqueued_at=task.enqueued_at,
            original_context=task.context,
        )

        self._dead_letter.append(entry)
        self._total_dead += 1

        logger.warning(
            f"Task {task.id} moved to DLQ after {task.retry_count} retries: {error[:100]}"
        )

        # Persist to Ring2
        if self.ring2:
            try:
                asyncio.get_event_loop().create_task(
                    self.ring2.log_audit(
                        session_id=task.session_id,
                        worker_id="task_queue",
                        action="dead_letter",
                        details=entry.to_dict(),
                    )
                )
            except Exception:
                pass

    async def cancel(self, task_id: str) -> bool:
        """
        Cancel a pending or in-progress task.

        Returns True if cancellation was successful.
        """
        task = self._tasks.get(task_id)
        if not task:
            return False

        if task.state in (TaskState.DONE, TaskState.DEAD_LETTER, TaskState.CANCELLED):
            return False

        task.state = TaskState.CANCELLED
        task.completed_at = datetime.now(timezone.utc).isoformat()
        self._cancelled.add(task_id)
        self._in_progress.discard(task_id)

        await self._persist_task(task)
        return True

    async def _persist_task(self, task: QueuedTask) -> None:
        """Persist task state to Ring2."""
        if not self.ring2:
            return

        try:
            await self.ring2.log_audit(
                session_id=task.session_id,
                worker_id="task_queue",
                action="task_state_change",
                details={
                    "task_id": task.id,
                    "state": task.state.value,
                    "priority": task.priority,
                    "retry_count": task.retry_count,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to persist task {task.id}: {e}")

    async def _recover_from_ring2(self) -> None:
        """Recover pending and retrying tasks from Ring2 on startup."""
        if not self.ring2:
            return

        try:
            # Get recent audit entries for task state changes
            cursor = await self.ring2._db.execute(
                "SELECT details FROM audit_trail "
                "WHERE worker_id = 'task_queue' AND action = 'task_state_change' "
                "ORDER BY id DESC LIMIT 500"
            )
            rows = await cursor.fetchall()

            # Rebuild task state from audit trail
            seen_tasks: dict[str, QueuedTask] = {}
            for row in reversed(rows):
                try:
                    details = json.loads(row[0])
                    task_id = details.get("task_id", "")
                    if not task_id:
                        continue

                    if task_id not in seen_tasks:
                        seen_tasks[task_id] = QueuedTask(
                            id=task_id,
                            state=TaskState(details.get("state", "pending")),
                            priority=details.get("priority", 0),
                            retry_count=details.get("retry_count", 0),
                        )
                except (json.JSONDecodeError, ValueError):
                    continue

            # Re-enqueue pending tasks
            for task_id, task in seen_tasks.items():
                if task.state in (TaskState.PENDING, TaskState.RETRYING):
                    self._tasks[task_id] = task
                    self._enqueue_counter += 1
                    task.state = TaskState.PENDING
                    await self._queue.put((-task.priority, self._enqueue_counter, task_id))

        except Exception as e:
            logger.warning(f"Task recovery from Ring2 failed: {e}")

    # ── Query Methods ──────────────────────────────────────────────

    def get_queue_depth(self) -> int:
        """Get the number of tasks waiting in the queue."""
        return self._queue.qsize()

    def get_task(self, task_id: str) -> QueuedTask | None:
        """Get a specific task by ID."""
        return self._tasks.get(task_id)

    def get_tasks_by_session(self, session_id: str) -> list[QueuedTask]:
        """Get all tasks for a session."""
        return [t for t in self._tasks.values() if t.session_id == session_id]

    def get_tasks_by_worker(self, worker_id: str) -> list[QueuedTask]:
        """Get all tasks assigned to a worker."""
        return [t for t in self._tasks.values() if t.assigned_to == worker_id]

    def get_in_progress(self) -> list[QueuedTask]:
        """Get all currently in-progress tasks."""
        return [t for t in self._tasks.values() if t.state == TaskState.IN_PROGRESS]

    def get_dead_letter_queue(self) -> list[DeadLetterEntry]:
        """Get all dead letter entries."""
        return list(self._dead_letter)

    def get_stats(self) -> dict[str, Any]:
        """Get queue statistics."""
        by_state: dict[str, int] = {}
        for task in self._tasks.values():
            state = task.state.value
            by_state[state] = by_state.get(state, 0) + 1

        return {
            "queue_depth": self.get_queue_depth(),
            "total_enqueued": self._total_enqueued,
            "total_completed": self._total_completed,
            "total_failed": self._total_failed,
            "total_retried": self._total_retried,
            "total_dead_letter": self._total_dead,
            "in_progress": len(self._in_progress),
            "by_state": by_state,
            "dead_letter_count": len(self._dead_letter),
        }

    async def replay_dead_letter(self, entry_id: str, priority: int = 0) -> str | None:
        """
        Replay a dead letter entry as a new task.

        Useful for manual retry after fixing the underlying issue.
        """
        for entry in self._dead_letter:
            if entry.id == entry_id:
                new_task_id = await self.enqueue(
                    instruction=entry.instruction,
                    session_id=entry.session_id,
                    assigned_to=entry.assigned_to,
                    priority=priority,
                    context=entry.original_context,
                    parent_task_id=entry.original_task_id,
                )
                self._dead_letter.remove(entry)
                logger.info(
                    f"Replayed DLQ entry {entry_id} as new task {new_task_id}"
                )
                return new_task_id

        return None

    async def purge_completed(self, max_age_hours: int = 24) -> int:
        """
        Remove completed/failed tasks older than max_age_hours.

        Returns the number of purged tasks.
        """
        now = datetime.now(timezone.utc)
        purged = 0

        for task_id in list(self._tasks.keys()):
            task = self._tasks[task_id]
            if task.state in (TaskState.DONE, TaskState.FAILED, TaskState.CANCELLED):
                if task.completed_at:
                    try:
                        completed = datetime.fromisoformat(task.completed_at)
                        age_hours = (now - completed).total_seconds() / 3600
                        if age_hours > max_age_hours:
                            del self._tasks[task_id]
                            purged += 1
                    except (ValueError, TypeError):
                        pass

        logger.info(f"Purged {purged} completed tasks older than {max_age_hours}h")
        return purged
