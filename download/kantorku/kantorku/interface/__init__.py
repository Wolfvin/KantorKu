"""
kantorku.interface — WebSocket/FastAPI interface for external clients.

Provides the HTTP/WebSocket/SSE interface for connecting to the
KantorKu Office from browsers, mobile apps, or any HTTP client.

Components:
    server      — FastAPI app with 2 WebSocket channels + SSE + Health
    protocol    — Pydantic models for WebSocket message protocol
    middleware  — Middleware pipeline (auth, logging, rate-limit, cost guard)
    health      — Health monitoring (liveness, readiness, dashboard)

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

# Protocol, middleware, and health are safe to import eagerly
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
]
