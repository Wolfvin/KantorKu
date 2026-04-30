"""
kantorku — Kantor digital yang sesungguhnya.

AI worker orchestration framework with Conductor, BriefingRoom,
WorkerHub, ContextPool, and Three-Ring Memory.

Now includes (v0.3.0):
- Session persistence & crash recovery
- Persistent task queue with retry & DLQ
- Middleware pipeline (auth, logging, rate-limit, cost guard)
- Health monitoring (liveness, readiness, dashboard)
- SSE streaming for non-WebSocket clients
- Full observability (tracing + metrics)

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
from kantorku.providers.circuit_breaker import CircuitBreaker, CircuitState
from kantorku.providers.retry import RetryPolicy, DEFAULT_RETRY_POLICY
from kantorku.observability import get_tracer, get_metrics, Tracer, Metrics
from kantorku.cost import CostTracker
from kantorku.protocol import OfficeEvent, EventType, parse_client_message
from kantorku.dag import DAGResolver, TaskNode, DAGCycleError
from kantorku.cache import LLMCache
from kantorku.delegation import DelegationManager, DelegationRequest, DelegationResult
from kantorku.provider_response import ProviderResponse
from kantorku.errors import (
    KantorkuError,
    ProviderError,
    ProviderTimeoutError,
    ProviderRateLimitError,
    ProviderAuthError,
    ProviderCircuitOpenError,
    AllProvidersFailedError,
    WorkerError,
    WorkerTimeoutError,
    WorkerNotReadyError,
    OfficeError,
    OfficeNotInitializedError,
    ContractError,
    NoContractError,
    ConfigError,
    WorkerNotFoundError,
)

# P3: Persistence & Crash Recovery
from kantorku.persistence import (
    CheckpointManager,
    CrashRecovery,
    SessionSnapshot,
    OfficeSnapshot,
    atomic_write,
    atomic_write_json,
    atomic_read_json,
)

# P3: Task Queue
from kantorku.task_queue import (
    TaskQueue,
    QueuedTask,
    TaskState as QueueTaskState,
    DeadLetterEntry,
)

# P3: Middleware Pipeline
from kantorku.middleware import (
    Middleware,
    MiddlewarePipeline,
    MiddlewareContext,
    LoggingMiddleware,
    AuthMiddleware,
    RateLimitMiddleware as RateLimitMiddleware,
    CostGuardMiddleware,
    AuditMiddleware,
    TimeoutMiddleware,
    RetryMiddleware,
    CachingMiddleware,
)

# P3: Health Monitoring
from kantorku.health import (
    HealthChecker,
    HealthStatus,
    HealthCheckResult,
    AggregatedHealth,
    WorkerHealthStatus,
    ProviderHealthStatus,
    Alert,
    AlertSystem,
)

__version__ = "0.3.0"
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
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitState",
    # Retry
    "RetryPolicy",
    "DEFAULT_RETRY_POLICY",
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
    # Provider Response
    "ProviderResponse",
    # Errors
    "KantorkuError",
    "ProviderError",
    "ProviderTimeoutError",
    "ProviderRateLimitError",
    "ProviderAuthError",
    "ProviderCircuitOpenError",
    "AllProvidersFailedError",
    "WorkerError",
    "WorkerTimeoutError",
    "WorkerNotReadyError",
    "OfficeError",
    "OfficeNotInitializedError",
    "ContractError",
    "NoContractError",
    "ConfigError",
    "WorkerNotFoundError",

    # P3: Persistence
    "CheckpointManager",
    "CrashRecovery",
    "SessionSnapshot",
    "OfficeSnapshot",
    "atomic_write",
    "atomic_write_json",
    "atomic_read_json",

    # P3: Task Queue
    "TaskQueue",
    "QueuedTask",
    "QueueTaskState",
    "DeadLetterEntry",

    # P3: Middleware
    "Middleware",
    "MiddlewarePipeline",
    "MiddlewareContext",
    "LoggingMiddleware",
    "AuthMiddleware",
    "RateLimitMiddleware",
    "CostGuardMiddleware",
    "AuditMiddleware",
    "TimeoutMiddleware",
    "RetryMiddleware",
    "CachingMiddleware",

    # P3: Health
    "HealthChecker",
    "HealthStatus",
    "HealthCheckResult",
    "AggregatedHealth",
    "WorkerHealthStatus",
    "ProviderHealthStatus",
    "Alert",
    "AlertSystem",
]
