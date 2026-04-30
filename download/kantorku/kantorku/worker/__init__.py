"""Worker package — BaseWorker, Registry, Identity."""

from kantorku.worker.base import BaseWorker, WorkerStatus, Task, TaskResult
from kantorku.worker.registry import WorkerRegistry
from kantorku.worker.identity import WorkerIdentity

__all__ = [
    "BaseWorker",
    "WorkerStatus",
    "Task",
    "TaskResult",
    "WorkerRegistry",
    "WorkerIdentity",
]
