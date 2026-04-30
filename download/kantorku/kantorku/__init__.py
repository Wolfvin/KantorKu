"""
kantorku — Kantor digital yang sesungguhnya.

AI worker orchestration framework with Conductor, BriefingRoom,
WorkerHub, ContextPool, and Three-Ring Memory.

Usage:
    from kantorku import Office

    office = Office.from_config("kantorku.toml")
    result = await office.run("Buat rate limiter di Rust")
"""

from kantorku.office import Office
from kantorku.worker.base import BaseWorker, WorkerStatus
from kantorku.worker.registry import WorkerRegistry
from kantorku.worker.identity import WorkerIdentity
from kantorku.layers.conductor import Conductor
from kantorku.layers.briefing_room import BriefingRoom
from kantorku.layers.worker_hub import WorkerHub
from kantorku.layers.intake import Intake
from kantorku.pool.context_pool import ContextPool
from kantorku.pool.pool_worker import PoolWorker
from kantorku.memory.ring1 import Ring1Memory
from kantorku.memory.ring2 import Ring2Memory
from kantorku.events.bus import EventBus
from kantorku.events.emitter import EventEmitter
from kantorku.config.settings import KantorkuConfig, WorkerConfig, PoolConfig

__version__ = "0.1.0"
__all__ = [
    "Office",
    "BaseWorker",
    "WorkerStatus",
    "WorkerRegistry",
    "WorkerIdentity",
    "Conductor",
    "BriefingRoom",
    "WorkerHub",
    "Intake",
    "ContextPool",
    "PoolWorker",
    "Ring1Memory",
    "Ring2Memory",
    "EventBus",
    "EventEmitter",
    "KantorkuConfig",
    "WorkerConfig",
    "PoolConfig",
]
