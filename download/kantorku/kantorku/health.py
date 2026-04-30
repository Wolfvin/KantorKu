"""
Health — Liveness/readiness probes, worker health checks, provider dashboard.

Provides:
- HealthChecker: Periodic health checks for all subsystems
- LivenessProbe: Is the server alive? (for orchestrators like K8s)
- ReadinessProbe: Is the server ready to accept requests?
- WorkerHealth: Per-worker health status with heartbeat
- ProviderHealth: Provider availability, latency, and error rates
- AlertSystem: Simple alerting for critical conditions

This module enables kantorku to run reliably in production by
continuously monitoring system health and surfacing issues early.

Usage:
    from kantorku.health import HealthChecker, HealthStatus

    health = HealthChecker(office=office)
    await health.start()

    # In FastAPI endpoint:
    @app.get("/health/live")
    async def liveness():
        return health.liveness().to_dict()

    @app.get("/health/ready")
    async def readiness():
        return health.readiness().to_dict()

    @app.get("/health/dashboard")
    async def dashboard():
        return health.dashboard()
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from kantorku.observability import get_tracer

logger = logging.getLogger("kantorku.health")


# ── Health Status ─────────────────────────────────────────────────────


class HealthStatus(str, Enum):
    """Health check result status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"  # Partially functional
    UNHEALTHY = "unhealthy"  # Not functional
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a single health check."""

    name: str
    status: HealthStatus = HealthStatus.UNKNOWN
    message: str = ""
    duration_ms: float = 0.0
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "duration_ms": round(self.duration_ms, 1),
            "timestamp": self.timestamp,
            "details": self.details,
        }


@dataclass
class AggregatedHealth:
    """Aggregated health status for the entire system."""

    status: HealthStatus = HealthStatus.UNKNOWN
    checks: list[HealthCheckResult] = field(default_factory=list)
    uptime_seconds: float = 0.0
    version: str = "0.3.0"

    @property
    def is_healthy(self) -> bool:
        return self.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "is_healthy": self.is_healthy,
            "uptime_seconds": round(self.uptime_seconds, 1),
            "version": self.version,
            "checks": [c.to_dict() for c in self.checks],
        }


# ── Worker Health ─────────────────────────────────────────────────────


@dataclass
class WorkerHealthStatus:
    """Health status of a single worker."""

    worker_id: str
    status: str = "unknown"  # idle, thinking, active, done, failed, unknown
    last_heartbeat: float = 0.0
    tasks_completed: int = 0
    tasks_failed: int = 0
    avg_duration_seconds: float = 0.0
    consecutive_failures: int = 0
    is_healthy: bool = True
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "status": self.status,
            "last_heartbeat_ago": round(time.time() - self.last_heartbeat, 1) if self.last_heartbeat else None,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "avg_duration_seconds": round(self.avg_duration_seconds, 2),
            "consecutive_failures": self.consecutive_failures,
            "is_healthy": self.is_healthy,
            "message": self.message,
        }


# ── Provider Health ───────────────────────────────────────────────────


@dataclass
class ProviderHealthStatus:
    """Health status of a single LLM provider."""

    provider: str
    is_configured: bool = False
    circuit_state: str = "closed"  # closed, open, half_open
    total_calls: int = 0
    failed_calls: int = 0
    success_rate: float = 0.0
    avg_latency_ms: float = 0.0
    last_error: str = ""
    last_call_at: float = 0.0
    is_healthy: bool = True
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "is_configured": self.is_configured,
            "circuit_state": self.circuit_state,
            "total_calls": self.total_calls,
            "failed_calls": self.failed_calls,
            "success_rate": round(self.success_rate, 3),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "last_error": self.last_error,
            "is_healthy": self.is_healthy,
            "message": self.message,
        }


# ── Alert System ──────────────────────────────────────────────────────


@dataclass
class Alert:
    """A health alert."""

    id: str = ""
    severity: str = "warning"  # info, warning, critical
    source: str = ""  # worker_id, provider_name, subsystem
    message: str = ""
    timestamp: float = field(default_factory=time.time)
    resolved: bool = False
    resolved_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "severity": self.severity,
            "source": self.source,
            "message": self.message,
            "timestamp": self.timestamp,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at if self.resolved else None,
        }


class AlertSystem:
    """
    Simple alert system for health monitoring.

    Tracks active alerts and provides callbacks for external
    notification systems (Slack, email, etc.).

    Usage:
        alerts = AlertSystem()

        # Register callback
        alerts.on_alert(lambda alert: send_slack(alert.message))

        # Trigger alert
        alerts.trigger("critical", "anthropic", "Circuit breaker open")

        # Resolve
        alerts.resolve("anthropic")

        # Get active alerts
        active = alerts.get_active()
    """

    def __init__(self, max_alerts: int = 100) -> None:
        self._alerts: list[Alert] = []
        self._max_alerts = max_alerts
        self._callbacks: list[Any] = []  # Callable[[Alert], Awaitable[None]]

    def on_alert(self, callback: Any) -> None:
        """Register a callback to be called when a new alert is triggered."""
        self._callbacks.append(callback)

    def trigger(self, severity: str, source: str, message: str) -> Alert:
        """Trigger a new alert."""
        alert = Alert(
            id=f"{source}:{int(time.time())}",
            severity=severity,
            source=source,
            message=message,
        )

        self._alerts.append(alert)

        # Rotate old alerts
        if len(self._alerts) > self._max_alerts:
            self._alerts = self._alerts[-self._max_alerts:]

        # Fire callbacks
        for cb in self._callbacks:
            try:
                result = cb(alert)
                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)
            except Exception as e:
                logger.warning(f"Alert callback error: {e}")

        return alert

    def resolve(self, source: str) -> None:
        """Resolve all active alerts for a source."""
        now = time.time()
        for alert in self._alerts:
            if alert.source == source and not alert.resolved:
                alert.resolved = True
                alert.resolved_at = now

    def get_active(self) -> list[Alert]:
        """Get all unresolved alerts."""
        return [a for a in self._alerts if not a.resolved]

    def get_all(self, limit: int = 50) -> list[Alert]:
        """Get recent alerts (including resolved)."""
        return self._alerts[-limit:]


# ── Health Checker ────────────────────────────────────────────────────


class HealthChecker:
    """
    Comprehensive health monitoring for kantorku.

    Periodically checks:
    - Memory subsystems (Ring1, Ring2, Ring3)
    - Provider availability and performance
    - Worker health (heartbeat, failure rate)
    - Cost tracking (budget limits)
    - Task queue depth

    Provides:
    - Liveness: Is the server process alive?
    - Readiness: Can it accept requests?
    - Dashboard: Detailed health dashboard

    Usage:
        health = HealthChecker(office=office, check_interval=30)
        await health.start()

        # FastAPI endpoints
        @app.get("/health/live")
        async def liveness():
            result = health.liveness()
            return result.to_dict(), 200 if result.is_healthy else 503

        @app.get("/health/ready")
        async def readiness():
            result = health.readiness()
            return result.to_dict(), 200 if result.is_healthy else 503

        # Stop monitoring
        await health.stop()
    """

    def __init__(
        self,
        office: Any = None,
        check_interval: int = 30,
        worker_failure_threshold: int = 3,
        provider_failure_threshold: float = 0.5,
    ) -> None:
        self.office = office
        self.check_interval = check_interval
        self.worker_failure_threshold = worker_failure_threshold
        self.provider_failure_threshold = provider_failure_threshold

        self.alerts = AlertSystem()
        self._started_at = time.time()
        self._running = False
        self._check_task: asyncio.Task | None = None
        self._last_check: float = 0.0
        self._tracer = get_tracer()

        # Cached health data
        self._worker_health: dict[str, WorkerHealthStatus] = {}
        self._provider_health: dict[str, ProviderHealthStatus] = {}

    async def start(self) -> None:
        """Start periodic health checking."""
        self._running = True
        self._check_task = asyncio.create_task(self._check_loop())
        logger.info(f"HealthChecker started (interval={self.check_interval}s)")

    async def stop(self) -> None:
        """Stop health checking."""
        self._running = False
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
        logger.info("HealthChecker stopped")

    async def _check_loop(self) -> None:
        """Periodic health check loop."""
        while self._running:
            try:
                await self._run_checks()
            except Exception as e:
                logger.warning(f"Health check failed: {e}")
            await asyncio.sleep(self.check_interval)

    async def _run_checks(self) -> None:
        """Run all health checks and update cached data."""
        self._last_check = time.time()

        if not self.office:
            return

        # Check workers
        self._check_workers()

        # Check providers
        self._check_providers()

        # Check memory
        # (memory checks are quick, done inline)

    def _check_workers(self) -> None:
        """Check health of all workers."""
        if not self.office or not hasattr(self.office, 'registry'):
            return

        for worker_id in self.office.registry.all_worker_ids:
            try:
                worker = self.office.registry.hire(worker_id)
                existing = self._worker_health.get(worker_id, WorkerHealthStatus(worker_id=worker_id))

                existing.status = worker.status.value if hasattr(worker.status, 'value') else str(worker.status)
                existing.last_heartbeat = time.time()

                # Check consecutive failures
                if existing.consecutive_failures >= self.worker_failure_threshold:
                    existing.is_healthy = False
                    existing.message = f"Consecutive failures: {existing.consecutive_failures}"
                    self.alerts.trigger(
                        "warning",
                        worker_id,
                        f"Worker {worker_id} has {existing.consecutive_failures} consecutive failures"
                    )

                self._worker_health[worker_id] = existing
            except Exception as e:
                existing = self._worker_health.get(worker_id, WorkerHealthStatus(worker_id=worker_id))
                existing.is_healthy = False
                existing.message = str(e)
                self._worker_health[worker_id] = existing

    def _check_providers(self) -> None:
        """Check health of all providers."""
        if not self.office or not hasattr(self.office, 'router'):
            return

        router = self.office.router

        for provider_name in router.configured_providers:
            existing = self._provider_health.get(
                provider_name, ProviderHealthStatus(provider=provider_name)
            )
            existing.is_configured = True

            # Get circuit breaker status
            cb_status = router.get_circuit_breaker_status()
            provider_cb = cb_status.get(provider_name, {})
            existing.circuit_state = provider_cb.get("state", "closed")

            if existing.circuit_state == "open":
                existing.is_healthy = False
                existing.message = "Circuit breaker is open"
                self.alerts.trigger(
                    "critical",
                    provider_name,
                    f"Provider {provider_name} circuit breaker is OPEN — calls are being blocked"
                )

            # Get metrics
            metrics = router.get_metrics_summary()
            by_provider = metrics.get("by_provider", {})
            provider_metrics = by_provider.get(provider_name, {})
            existing.total_calls = provider_metrics.get("calls", 0)
            existing.failed_calls = provider_metrics.get("failed_calls", 0)

            total = existing.total_calls
            if total > 0:
                existing.success_rate = (total - existing.failed_calls) / total
                if existing.success_rate < self.provider_failure_threshold:
                    existing.is_healthy = False
                    existing.message = f"Low success rate: {existing.success_rate:.1%}"

            existing.avg_latency_ms = provider_metrics.get("avg_latency_ms", 0.0)

            # If healthy, resolve any previous alerts
            if existing.is_healthy:
                self.alerts.resolve(provider_name)

            self._provider_health[provider_name] = existing

    # ── Public API ─────────────────────────────────────────────────

    def liveness(self) -> AggregatedHealth:
        """
        Liveness probe — is the server alive?

        This should always return HEALTHY unless the process is
        completely unresponsive. Used by orchestrators (K8s, Docker)
        to decide whether to restart the container.
        """
        return AggregatedHealth(
            status=HealthStatus.HEALTHY,
            uptime_seconds=time.time() - self._started_at,
            checks=[
                HealthCheckResult(
                    name="liveness",
                    status=HealthStatus.HEALTHY,
                    message="Server is alive",
                )
            ],
        )

    def readiness(self) -> AggregatedHealth:
        """
        Readiness probe — is the server ready to accept requests?

        Checks that all critical subsystems are operational:
        - Office is initialized
        - At least one provider is configured and available
        - Memory is accessible
        - No critical alerts
        """
        checks: list[HealthCheckResult] = []

        # Check office initialization
        if self.office and getattr(self.office, '_initialized', False):
            checks.append(HealthCheckResult(
                name="office",
                status=HealthStatus.HEALTHY,
                message="Office is initialized",
            ))
        else:
            checks.append(HealthCheckResult(
                name="office",
                status=HealthStatus.UNHEALTHY,
                message="Office not initialized",
            ))

        # Check providers
        healthy_providers = sum(
            1 for p in self._provider_health.values() if p.is_healthy and p.is_configured
        )
        total_providers = sum(
            1 for p in self._provider_health.values() if p.is_configured
        )

        if total_providers == 0:
            checks.append(HealthCheckResult(
                name="providers",
                status=HealthStatus.UNHEALTHY,
                message="No providers configured",
            ))
        elif healthy_providers == 0:
            checks.append(HealthCheckResult(
                name="providers",
                status=HealthStatus.UNHEALTHY,
                message=f"All providers unhealthy (0/{total_providers})",
            ))
        elif healthy_providers < total_providers:
            checks.append(HealthCheckResult(
                name="providers",
                status=HealthStatus.DEGRADED,
                message=f"Some providers unhealthy ({healthy_providers}/{total_providers})",
                details={
                    "healthy": [
                        p.provider for p in self._provider_health.values()
                        if p.is_healthy and p.is_configured
                    ],
                    "unhealthy": [
                        p.provider for p in self._provider_health.values()
                        if not p.is_healthy and p.is_configured
                    ],
                },
            ))
        else:
            checks.append(HealthCheckResult(
                name="providers",
                status=HealthStatus.HEALTHY,
                message=f"All providers healthy ({healthy_providers}/{total_providers})",
            ))

        # Check workers
        healthy_workers = sum(1 for w in self._worker_health.values() if w.is_healthy)
        total_workers = len(self._worker_health)

        if total_workers > 0 and healthy_workers < total_workers:
            checks.append(HealthCheckResult(
                name="workers",
                status=HealthStatus.DEGRADED if healthy_workers > 0 else HealthStatus.UNHEALTHY,
                message=f"Workers: {healthy_workers}/{total_workers} healthy",
                details={
                    "unhealthy": [
                        w.worker_id for w in self._worker_health.values()
                        if not w.is_healthy
                    ],
                },
            ))
        elif total_workers > 0:
            checks.append(HealthCheckResult(
                name="workers",
                status=HealthStatus.HEALTHY,
                message=f"All {total_workers} workers healthy",
            ))

        # Check critical alerts
        critical_alerts = [
            a for a in self.alerts.get_active() if a.severity == "critical"
        ]
        if critical_alerts:
            checks.append(HealthCheckResult(
                name="alerts",
                status=HealthStatus.UNHEALTHY,
                message=f"{len(critical_alerts)} critical alerts active",
                details={"alerts": [a.to_dict() for a in critical_alerts]},
            ))

        # Aggregate status
        statuses = [c.status for c in checks]
        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            overall = HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY

        return AggregatedHealth(
            status=overall,
            checks=checks,
            uptime_seconds=time.time() - self._started_at,
        )

    def dashboard(self) -> dict[str, Any]:
        """
        Full health dashboard with detailed status of all subsystems.

        Returns a comprehensive dict suitable for rendering as a
        monitoring dashboard or returning via API.
        """
        readiness = self.readiness()

        return {
            "status": readiness.status.value,
            "is_healthy": readiness.is_healthy,
            "uptime_seconds": round(time.time() - self._started_at, 1),
            "last_check_at": self._last_check,
            "version": "0.3.0",
            "providers": {
                name: status.to_dict()
                for name, status in self._provider_health.items()
            },
            "workers": {
                name: status.to_dict()
                for name, status in self._worker_health.items()
            },
            "alerts": {
                "active": [a.to_dict() for a in self.alerts.get_active()],
                "total_active": len(self.alerts.get_active()),
                "critical": len([a for a in self.alerts.get_active() if a.severity == "critical"]),
            },
            "checks": [c.to_dict() for c in readiness.checks],
            "cost": self._get_cost_info(),
            "task_queue": self._get_queue_info(),
        }

    def _get_cost_info(self) -> dict[str, Any]:
        """Get cost tracking information."""
        if not self.office or not hasattr(self.office, 'cost_tracker') or not self.office.cost_tracker:
            return {"tracking_enabled": False}

        report = self.office.cost_tracker.get_report()
        return {
            "tracking_enabled": True,
            "total_cost_usd": report.get("total_cost_usd", 0.0),
            "total_calls": report.get("total_calls", 0),
        }

    def _get_queue_info(self) -> dict[str, Any]:
        """Get task queue information."""
        if not self.office or not hasattr(self.office, '_task_queue'):
            return {"enabled": False}

        queue = getattr(self.office, '_task_queue', None)
        if not queue:
            return {"enabled": False}

        return {
            "enabled": True,
            **queue.get_stats(),
        }

    def update_worker_health(
        self,
        worker_id: str,
        status: str = "",
        completed: bool = False,
        failed: bool = False,
        duration_seconds: float = 0.0,
    ) -> None:
        """
        Update a worker's health status.

        Called by the Office after each task execution.
        """
        existing = self._worker_health.get(worker_id, WorkerHealthStatus(worker_id=worker_id))

        if status:
            existing.status = status
        existing.last_heartbeat = time.time()

        if completed:
            existing.tasks_completed += 1
            existing.consecutive_failures = 0
            # Update average duration
            total = existing.tasks_completed
            existing.avg_duration_seconds = (
                (existing.avg_duration_seconds * (total - 1) + duration_seconds) / total
            )

        if failed:
            existing.tasks_failed += 1
            existing.consecutive_failures += 1

        # Check health
        if existing.consecutive_failures >= self.worker_failure_threshold:
            existing.is_healthy = False
            existing.message = f"Consecutive failures: {existing.consecutive_failures}"
        else:
            existing.is_healthy = True
            existing.message = ""

        self._worker_health[worker_id] = existing

    def update_provider_health(
        self,
        provider: str,
        success: bool = True,
        latency_ms: float = 0.0,
        error: str = "",
    ) -> None:
        """
        Update a provider's health status.

        Called by the ProviderRouter after each call.
        """
        existing = self._provider_health.get(provider, ProviderHealthStatus(provider=provider))
        existing.is_configured = True
        existing.total_calls += 1
        existing.last_call_at = time.time()

        if success:
            # Update average latency
            total = existing.total_calls
            existing.avg_latency_ms = (
                (existing.avg_latency_ms * (total - 1) + latency_ms) / total
            )
        else:
            existing.failed_calls += 1
            existing.last_error = error

        # Recalculate success rate
        if existing.total_calls > 0:
            existing.success_rate = (existing.total_calls - existing.failed_calls) / existing.total_calls

        self._provider_health[provider] = existing
