"""
kantorku.interface — Server-side interface infrastructure for KantorKu.

Provides the HTTP/WebSocket/SSE interface, middleware pipeline,
health monitoring, persistence, and task queue for the KantorKu Office.

Components:
    server      — FastAPI app with 2 WebSocket channels + SSE + Health
    protocol    — Pydantic models for WebSocket message protocol
    middleware  — Middleware pipeline (auth, logging, rate-limit, cost guard)
    health      — Health monitoring (liveness, readiness, dashboard)
    persistence — Session checkpoint, crash recovery, atomic writes
    task_queue  — Persistent task queue with retry & dead letter handling

Usage:
    # Start the server
    uvicorn kantorku.interface.server:app --host 0.0.0.0 --port 8000

    # Or via CLI
    kantorku serve --config kantorku.toml

Note:
    The server module is NOT eagerly imported here to avoid circular imports
    (server → office → interface.middleware). Import it directly when needed:

        from kantorku.interface.server import app, create_office
"""

# Protocol, middleware, health, persistence, and task_queue are safe to import eagerly
# (no circular dependency — they don't import office)
from kantorku.interface.protocol import (
    OfficeEvent,
    EventType,
    parse_client_message,
    UserMessage,
    ContractAccepted,
    ContractRevision,
    ManagerMessage,
    ContractReady,
    WorkStarted,
    WorkDone,
    ErrorMessage,
)
from kantorku.interface.middleware import (
    Middleware,
    MiddlewarePipeline,
    MiddlewareContext,
    LoggingMiddleware,
    AuthMiddleware,
    RateLimitMiddleware,
    CostGuardMiddleware,
    AuditMiddleware,
    TimeoutMiddleware,
    RetryMiddleware,
    CachingMiddleware,
)
from kantorku.interface.health import (
    HealthChecker,
    HealthStatus,
    HealthCheckResult,
    AggregatedHealth,
    WorkerHealthStatus,
    ProviderHealthStatus,
    Alert,
    AlertSystem,
)
from kantorku.interface.persistence import (
    CheckpointManager,
    CrashRecovery,
    SessionSnapshot,
    OfficeSnapshot,
    atomic_write,
    atomic_write_json,
    atomic_read_json,
)
from kantorku.interface.task_queue import (
    TaskQueue,
    QueuedTask,
    TaskState,
    DeadLetterEntry,
)

__all__ = [
    # Protocol
    "OfficeEvent",
    "EventType",
    "parse_client_message",
    "UserMessage",
    "ContractAccepted",
    "ContractRevision",
    "ManagerMessage",
    "ContractReady",
    "WorkStarted",
    "WorkDone",
    "ErrorMessage",
    # Middleware
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
    # Health
    "HealthChecker",
    "HealthStatus",
    "HealthCheckResult",
    "AggregatedHealth",
    "WorkerHealthStatus",
    "ProviderHealthStatus",
    "Alert",
    "AlertSystem",
    # Persistence
    "CheckpointManager",
    "CrashRecovery",
    "SessionSnapshot",
    "OfficeSnapshot",
    "atomic_write",
    "atomic_write_json",
    "atomic_read_json",
    # Task Queue
    "TaskQueue",
    "QueuedTask",
    "TaskState",
    "DeadLetterEntry",
]
