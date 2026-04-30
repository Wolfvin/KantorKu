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
from kantorku.worker.base import BaseWorker, WorkerStatus, Task, TaskResult
from kantorku.worker.registry import WorkerRegistry
from kantorku.worker.identity import WorkerIdentity, WorkerAPI
from kantorku.worker.generator import WorkerGenerator
from kantorku.layers.conductor import Conductor, Contract, ContractState, TodoItem
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
from kantorku.hooks import Hooks, HookType
from kantorku.providers.rate_limiter import RateLimiter
from kantorku.observability import get_tracer, get_metrics, Tracer, Metrics
from kantorku.cost import CostTracker
from kantorku.protocol import OfficeEvent, EventType, parse_client_message
from kantorku.dag import DAGResolver, TaskNode, DAGCycleError
from kantorku.cache import LLMCache
from kantorku.delegation import DelegationManager, DelegationRequest, DelegationResult

__version__ = "0.1.0"
__all__ = [
    # Core
    "Office",
    "BaseWorker",
    "WorkerStatus",
    "Task",
    "TaskResult",
    "WorkerRegistry",
    "WorkerIdentity",
    "WorkerAPI",
    "WorkerGenerator",
    # Layers
    "Conductor",
    "Contract",
    "ContractState",
    "TodoItem",
    "BriefingRoom",
    "WorkerHub",
    "Intake",
    # Pool
    "ContextPool",
    "PoolWorker",
    # Memory
    "Ring1Memory",
    "Ring2Memory",
    # Events
    "EventBus",
    "EventEmitter",
    # Config
    "KantorkuConfig",
    "WorkerConfig",
    "PoolConfig",
    # Hooks
    "Hooks",
    "HookType",
    # Rate Limiting
    "RateLimiter",
    # Observability
    "Tracer",
    "Metrics",
    "get_tracer",
    "get_metrics",
    # Cost Tracking
    "CostTracker",
    # Protocol
    "OfficeEvent",
    "EventType",
    "parse_client_message",
    # DAG
    "DAGResolver",
    "TaskNode",
    "DAGCycleError",
    # Cache
    "LLMCache",
    # Delegation
    "DelegationManager",
    "DelegationRequest",
    "DelegationResult",
]
