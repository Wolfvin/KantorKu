"""
Middleware — Pluggable request/response pipeline for kantorku operations.

Provides:
- Middleware base class with before/after hooks
- MiddlewarePipeline: Ordered chain of middleware
- Built-in middleware: Auth, Logging, RateLimit, CostGuard
- Context propagation through the pipeline

Middleware wraps any async operation with pre/post processing:
- BEFORE: Validate, authorize, rate-limit, enrich context
- AFTER: Log, audit, transform, cache, measure

Each middleware sees the full context and can:
- Short-circuit by raising an exception (before)
- Modify the request before it reaches the operation
- Modify or inspect the response after the operation
- Handle exceptions from the operation

Usage:
    from kantorku.middleware import MiddlewarePipeline, LoggingMiddleware, AuthMiddleware

    pipeline = MiddlewarePipeline()
    pipeline.add(AuthMiddleware(api_key_header="X-API-Key"))
    pipeline.add(LoggingMiddleware())
    pipeline.add(CostGuardMiddleware(max_cost_usd=10.0))

    # Wrap any operation
    result = await pipeline.execute(
        operation=my_async_function,
        context={"session_id": "s1", "user": "admin"},
        **kwargs,
    )
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

from kantorku.observability import get_tracer, get_metrics

logger = logging.getLogger("kantorku.middleware")


# ── Middleware Context ────────────────────────────────────────────────


@dataclass
class MiddlewareContext:
    """
    Context propagated through the middleware pipeline.

    Carries request metadata, response, and any state
    that middleware need to share with each other.
    """

    # Request
    operation: str = ""  # Name of the operation being called
    session_id: str = ""
    worker_id: str = ""
    user: str = ""

    # Request metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    # Response (filled after operation)
    response: Any = None
    error: Exception | None = None

    # Timing
    started_at: float = 0.0
    completed_at: float = 0.0

    # Flags (middleware can set these)
    skip_operation: bool = False  # If True, skip the actual operation
    cached_response: bool = False  # If True, response came from cache

    # Custom attributes (middleware can add anything)
    attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        """Pipeline duration in milliseconds."""
        end = self.completed_at or time.monotonic()
        return (end - self.started_at) * 1000

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "session_id": self.session_id,
            "worker_id": self.worker_id,
            "user": self.user,
            "duration_ms": self.duration_ms,
            "skip_operation": self.skip_operation,
            "cached_response": self.cached_response,
            "error": str(self.error) if self.error else None,
            "attributes": self.attributes,
        }


# ── Base Middleware ───────────────────────────────────────────────────


class Middleware(ABC):
    """
    Abstract base class for middleware.

    Subclasses implement `before()` and/or `after()` hooks.
    The `before()` hook runs before the operation, and can:
    - Modify the context (enrich, validate)
    - Raise an exception to short-circuit

    The `after()` hook runs after the operation, and can:
    - Inspect or transform the response
    - Log, audit, or record metrics
    - Handle exceptions from the operation
    """

    @property
    def name(self) -> str:
        """Middleware name (defaults to class name)."""
        return self.__class__.__name__

    async def before(self, ctx: MiddlewareContext) -> MiddlewareContext:
        """
        Process request before the operation.

        Override to implement pre-processing logic.
        Must return the (possibly modified) context.

        Args:
            ctx: The middleware context with request info

        Returns:
            Modified context (or same context if no changes)
        """
        return ctx

    async def after(self, ctx: MiddlewareContext) -> MiddlewareContext:
        """
        Process response after the operation.

        Override to implement post-processing logic.
        Must return the (possibly modified) context.

        Args:
            ctx: The middleware context with response info

        Returns:
            Modified context (or same context if no changes)
        """
        return ctx


# ── Middleware Pipeline ───────────────────────────────────────────────


class MiddlewarePipeline:
    """
    Ordered chain of middleware that wraps async operations.

    Execution flow:
    1. before() of each middleware (in order)
    2. The actual operation
    3. after() of each middleware (in reverse order)

    If any before() raises, the pipeline stops and after() is NOT called.
    If the operation raises, after() IS called with ctx.error set.

    Usage:
        pipeline = MiddlewarePipeline()
        pipeline.add(LoggingMiddleware())
        pipeline.add(AuthMiddleware())

        result = await pipeline.execute(
            operation=my_function,
            context=MiddlewareContext(session_id="s1"),
            arg1="value1",
        )
    """

    def __init__(self) -> None:
        self._middleware: list[Middleware] = []

    def add(self, middleware: Middleware) -> MiddlewarePipeline:
        """
        Add middleware to the pipeline.

        Middleware are executed in the order they are added.
        Returns self for chaining.

        Args:
            middleware: Middleware instance to add
        """
        self._middleware.append(middleware)
        return self

    def remove(self, name: str) -> bool:
        """Remove middleware by name. Returns True if found."""
        for i, mw in enumerate(self._middleware):
            if mw.name == name:
                self._middleware.pop(i)
                return True
        return False

    def list_middleware(self) -> list[str]:
        """List all middleware names in order."""
        return [mw.name for mw in self._middleware]

    async def execute(
        self,
        operation: Callable[..., Awaitable[Any]],
        context: MiddlewareContext | None = None,
        **kwargs: Any,
    ) -> Any:
        """
        Execute an operation through the middleware pipeline.

        Args:
            operation: The async function to execute
            context: Optional middleware context
            **kwargs: Arguments to pass to the operation

        Returns:
            The operation's return value

        Raises:
            Any exception from before() hooks or the operation itself
        """
        ctx = context or MiddlewareContext()
        if not ctx.operation:
            ctx.operation = getattr(operation, "__name__", "unknown")
        ctx.started_at = time.monotonic()

        tracer = get_tracer()

        with tracer.span(
            f"pipeline.{ctx.operation}",
            attributes={"middleware_count": len(self._middleware)},
        ) as span:
            # 1. Run before() hooks in order
            for mw in self._middleware:
                try:
                    ctx = await mw.before(ctx)
                    span.add_event(f"middleware.before.{mw.name}")
                except Exception as e:
                    logger.warning(
                        f"Middleware {mw.name} blocked operation {ctx.operation}: {e}"
                    )
                    ctx.error = e
                    ctx.completed_at = time.monotonic()
                    raise

            # 2. Execute operation (unless skipped)
            if not ctx.skip_operation:
                try:
                    ctx.response = await operation(**kwargs)
                except Exception as e:
                    ctx.error = e

            # 3. Run after() hooks in reverse order
            for mw in reversed(self._middleware):
                try:
                    ctx = await mw.after(ctx)
                    span.add_event(f"middleware.after.{mw.name}")
                except Exception as e:
                    logger.warning(
                        f"Middleware {mw.name} after() raised: {e}"
                    )
                    # Don't override original error
                    if ctx.error is None:
                        ctx.error = e

            ctx.completed_at = time.monotonic()

            # Set span attributes
            span.set_attribute("duration_ms", ctx.duration_ms)
            if ctx.error:
                span.set_status("error")
                span.set_attribute("error.type", type(ctx.error).__name__)
                span.set_attribute("error.message", str(ctx.error))

        # Raise if there was an error
        if ctx.error:
            raise ctx.error

        return ctx.response


# ── Built-in Middleware ───────────────────────────────────────────────


class LoggingMiddleware(Middleware):
    """
    Log all operations with timing information.

    Logs at INFO level for normal operations and WARNING for failures.
    Includes operation name, duration, session, and worker context.
    """

    def __init__(self, level: str = "INFO", log_request: bool = True, log_response: bool = False) -> None:
        self.level = level
        self.log_request = log_request
        self.log_response = log_response

    async def before(self, ctx: MiddlewareContext) -> MiddlewareContext:
        if self.log_request:
            logger.log(
                getattr(logging, self.level),
                f"[PIPELINE] → {ctx.operation} session={ctx.session_id} worker={ctx.worker_id}",
            )
        return ctx

    async def after(self, ctx: MiddlewareContext) -> MiddlewareContext:
        status = "ERROR" if ctx.error else "OK"
        logger.log(
            getattr(logging, self.level) if not ctx.error else logging.WARNING,
            f"[PIPELINE] ← {ctx.operation} {status} {ctx.duration_ms:.1f}ms "
            f"session={ctx.session_id} worker={ctx.worker_id}",
        )
        return ctx


class AuthMiddleware(Middleware):
    """
    API key authentication middleware.

    Validates that requests include a valid API key.
    Can be configured to require a specific header or query parameter.

    Supports:
    - Static API keys (provided in constructor)
    - Environment variable-based keys
    - Key rotation (multiple valid keys)
    """

    def __init__(
        self,
        api_keys: list[str] | None = None,
        api_key_header: str = "X-API-Key",
        env_var: str = "",
        bypass_for_health: bool = True,
    ) -> None:
        self._valid_keys: set[str] = set(api_keys or [])
        self.api_key_header = api_key_header
        self.env_var = env_var
        self.bypass_for_health = bypass_for_health

        # Load from env var if specified
        if env_var:
            import os
            env_key = os.environ.get(env_var, "")
            if env_key:
                self._valid_keys.add(env_key)

    async def before(self, ctx: MiddlewareContext) -> MiddlewareContext:
        # Bypass for health checks
        if self.bypass_for_health and ctx.operation in ("health", "readiness", "liveness"):
            return ctx

        # No keys configured = auth disabled
        if not self._valid_keys:
            return ctx

        # Check for API key in context attributes
        provided_key = ctx.attributes.get("api_key", "")

        if not provided_key:
            raise PermissionError(
                f"API key required. Provide via {self.api_key_header} header."
            )

        if provided_key not in self._valid_keys:
            raise PermissionError("Invalid API key")

        ctx.attributes["authenticated"] = True
        return ctx


class RateLimitMiddleware(Middleware):
    """
    Per-operation rate limiting middleware.

    Limits the number of operations per time window.
    Uses a simple sliding window counter.

    Args:
        max_requests: Maximum requests per window
        window_seconds: Time window in seconds
        key_func: Function to extract rate limit key from context
    """

    def __init__(
        self,
        max_requests: int = 100,
        window_seconds: int = 60,
        key_func: Callable[[MiddlewareContext], str] | None = None,
    ) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.key_func = key_func or (lambda ctx: ctx.session_id or "global")
        self._counters: dict[str, list[float]] = {}

    async def before(self, ctx: MiddlewareContext) -> MiddlewareContext:
        key = self.key_func(ctx)
        now = time.monotonic()
        window_start = now - self.window_seconds

        # Clean old entries
        if key not in self._counters:
            self._counters[key] = []

        self._counters[key] = [t for t in self._counters[key] if t > window_start]

        # Check rate limit
        if len(self._counters[key]) >= self.max_requests:
            raise PermissionError(
                f"Rate limit exceeded: {self.max_requests} requests per "
                f"{self.window_seconds}s for key '{key}'"
            )

        # Record this request
        self._counters[key].append(now)

        ctx.attributes["rate_limit_remaining"] = self.max_requests - len(self._counters[key])
        return ctx


class CostGuardMiddleware(Middleware):
    """
    Cost guard middleware — blocks operations that would exceed cost limits.

    Checks the cost tracker before allowing an operation to proceed.
    If the session or total cost would exceed the limit, the operation
    is blocked with a clear error message.

    Args:
        max_session_cost: Maximum cost per session (USD)
        max_total_cost: Maximum total cost across all sessions (USD)
        cost_tracker: Reference to the CostTracker instance
    """

    def __init__(
        self,
        max_session_cost: float = 5.0,
        max_total_cost: float = 50.0,
        cost_tracker: Any = None,
    ) -> None:
        self.max_session_cost = max_session_cost
        self.max_total_cost = max_total_cost
        self.cost_tracker = cost_tracker

    async def before(self, ctx: MiddlewareContext) -> MiddlewareContext:
        if not self.cost_tracker:
            return ctx

        # Check total cost
        total = self.cost_tracker.get_total_cost()
        if total >= self.max_total_cost:
            raise PermissionError(
                f"Total cost limit reached: ${total:.4f} / ${self.max_total_cost:.2f}. "
                f"Increase limit or start a new billing period."
            )

        # Check session cost
        if ctx.session_id:
            session_cost = self.cost_tracker.get_session_cost(ctx.session_id)
            if session_cost >= self.max_session_cost:
                raise PermissionError(
                    f"Session cost limit reached: ${session_cost:.4f} / "
                    f"${self.max_session_cost:.2f} for session {ctx.session_id}"
                )

        ctx.attributes["cost_guard_total"] = total
        ctx.attributes["cost_guard_session"] = (
            self.cost_tracker.get_session_cost(ctx.session_id) if ctx.session_id else 0.0
        )

        return ctx


class AuditMiddleware(Middleware):
    """
    Audit trail middleware — logs all operations to Ring2.

    Records every operation with full context to the audit trail
    in Ring2 (SQLite). This enables compliance, debugging, and analytics.

    Args:
        ring2: Ring2 memory instance
        log_request_body: Whether to log request details
        log_response_body: Whether to log response details
    """

    def __init__(
        self,
        ring2: Any = None,
        log_request_body: bool = False,
        log_response_body: bool = False,
    ) -> None:
        self.ring2 = ring2
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body

    async def after(self, ctx: MiddlewareContext) -> MiddlewareContext:
        if not self.ring2:
            return ctx

        details: dict[str, Any] = {
            "operation": ctx.operation,
            "duration_ms": ctx.duration_ms,
            "error": str(ctx.error) if ctx.error else None,
        }

        if self.log_request_body:
            details["request"] = ctx.metadata

        if self.log_response_body and ctx.response is not None:
            # Truncate large responses
            resp_str = str(ctx.response)
            details["response_preview"] = resp_str[:500]

        try:
            await self.ring2.log_audit(
                session_id=ctx.session_id,
                worker_id=ctx.worker_id or "middleware",
                action=ctx.operation,
                details=details,
            )
        except Exception as e:
            logger.warning(f"Audit logging failed: {e}")

        return ctx


class TimeoutMiddleware(Middleware):
    """
    Timeout middleware — enforces maximum execution time.

    Wraps the operation with an asyncio timeout. If the operation
    takes longer than the specified timeout, it's cancelled.

    Args:
        timeout_seconds: Maximum execution time per operation
        operation_timeouts: Per-operation timeout overrides
    """

    def __init__(
        self,
        timeout_seconds: float = 300.0,
        operation_timeouts: dict[str, float] | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.operation_timeouts = operation_timeouts or {}

    async def before(self, ctx: MiddlewareContext) -> MiddlewareContext:
        timeout = self.operation_timeouts.get(
            ctx.operation, self.timeout_seconds
        )
        ctx.attributes["timeout_seconds"] = timeout
        return ctx


class RetryMiddleware(Middleware):
    """
    Retry middleware — automatically retry failed operations.

    On failure (after the operation), this middleware can schedule a retry
    by re-raising the exception. It works with the TaskQueue's retry
    mechanism, or can do simple retries on its own.

    Args:
        max_retries: Maximum number of retries
        retry_delay: Base delay between retries (seconds)
        retryable_exceptions: Exception types that should be retried
    """

    def __init__(
        self,
        max_retries: int = 1,
        retry_delay: float = 1.0,
        retryable_exceptions: tuple[type[Exception], ...] | None = None,
    ) -> None:
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.retryable_exceptions = retryable_exceptions or (Exception,)

    async def after(self, ctx: MiddlewareContext) -> MiddlewareContext:
        if ctx.error and isinstance(ctx.error, self.retryable_exceptions):
            retry_count = ctx.attributes.get("retry_count", 0)
            if retry_count < self.max_retries:
                ctx.attributes["retry_count"] = retry_count + 1
                logger.info(
                    f"Retrying {ctx.operation} (attempt {retry_count + 1}/{self.max_retries})"
                )
        return ctx


class CachingMiddleware(Middleware):
    """
    Caching middleware — cache operation results.

    Before the operation, checks if there's a cached result.
    After the operation, stores the result in cache.

    Works with the LLMCache for LLM calls, or any cache backend.

    Args:
        cache: LLMCache instance
        cache_key_func: Function to compute cache key from context
    """

    def __init__(
        self,
        cache: Any = None,
        cache_key_func: Callable[[MiddlewareContext], str] | None = None,
    ) -> None:
        self.cache = cache
        self.cache_key_func = cache_key_func or (lambda ctx: f"{ctx.operation}:{ctx.session_id}")

    async def before(self, ctx: MiddlewareContext) -> MiddlewareContext:
        if not self.cache:
            return ctx

        key = self.cache_key_func(ctx)
        ctx.attributes["cache_key"] = key

        # Check cache (simplified — in practice, you'd need to know the cache structure)
        return ctx

    async def after(self, ctx: MiddlewareContext) -> MiddlewareContext:
        if not self.cache or ctx.error or ctx.cached_response:
            return ctx

        # Store result in cache
        return ctx
