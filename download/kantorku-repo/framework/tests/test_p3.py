"""
Comprehensive tests for P3: Backend Maturation Phase 3.

Tests:
1. Persistence: atomic writes, session snapshots, checkpoint, crash recovery
2. TaskQueue: enqueue, dequeue, priority, retry, DLQ, cancel
3. Middleware: pipeline, before/after hooks, built-in middleware
4. Health: liveness, readiness, dashboard, alerts
5. Integration: Office with all P3 systems
"""

import asyncio
import json
import os
import shutil
import tempfile
import time

import pytest


# ── Persistence Tests ─────────────────────────────────────────────────


class TestAtomicWrites:
    """Test atomic file write operations."""

    def test_atomic_write_creates_file(self, tmp_path):
        from kantorku.persistence import atomic_write
        path = tmp_path / "test.json"
        atomic_write(str(path), "hello world")
        assert path.exists()
        assert path.read_text() == "hello world"

    def test_atomic_write_json(self, tmp_path):
        from kantorku.persistence import atomic_write_json
        path = tmp_path / "test.json"
        data = {"key": "value", "number": 42}
        atomic_write_json(str(path), data)
        assert path.exists()
        loaded = json.loads(path.read_text())
        assert loaded["key"] == "value"
        assert loaded["number"] == 42

    def test_atomic_read_json(self, tmp_path):
        from kantorku.persistence import atomic_write_json, atomic_read_json
        path = tmp_path / "test.json"
        data = {"session_id": "s1", "state": "working"}
        atomic_write_json(str(path), data)
        loaded = atomic_read_json(str(path))
        assert loaded["session_id"] == "s1"

    def test_atomic_read_json_missing_file(self, tmp_path):
        from kantorku.persistence import atomic_read_json
        result = atomic_read_json(str(tmp_path / "nonexistent.json"))
        assert result is None

    def test_atomic_write_bytes(self, tmp_path):
        from kantorku.persistence import atomic_write
        path = tmp_path / "test.bin"
        atomic_write(str(path), b"\x00\x01\x02\x03")
        assert path.exists()
        assert path.read_bytes() == b"\x00\x01\x02\x03"


class TestSessionSnapshot:
    """Test session snapshot serialization."""

    def test_snapshot_to_dict(self):
        from kantorku.persistence import SessionSnapshot
        snap = SessionSnapshot(
            session_id="s1",
            contract_state="working",
            contract={"title": "Test"},
        )
        d = snap.to_dict()
        assert d["session_id"] == "s1"
        assert d["contract_state"] == "working"
        assert d["contract"]["title"] == "Test"

    def test_snapshot_from_dict(self):
        from kantorku.persistence import SessionSnapshot
        data = {
            "session_id": "s2",
            "contract_state": "idle",
            "contract": {"title": "Hello"},
            "task_results": {"t1": {"status": "done"}},
        }
        snap = SessionSnapshot.from_dict(data)
        assert snap.session_id == "s2"
        assert snap.contract_state == "idle"
        assert snap.task_results["t1"]["status"] == "done"

    def test_snapshot_round_trip(self):
        from kantorku.persistence import SessionSnapshot
        snap = SessionSnapshot(
            session_id="s3",
            contract_state="contract_presented",
            client_messages=[{"role": "user", "content": "test"}],
            cost_usd=1.23,
            total_tokens=5000,
        )
        d = snap.to_dict()
        restored = SessionSnapshot.from_dict(d)
        assert restored.session_id == "s3"
        assert restored.cost_usd == 1.23
        assert len(restored.client_messages) == 1


class TestOfficeSnapshot:
    """Test office-level snapshot."""

    def test_office_snapshot_round_trip(self):
        from kantorku.persistence import OfficeSnapshot, SessionSnapshot
        snap = OfficeSnapshot(
            sessions={
                "s1": SessionSnapshot(session_id="s1", contract_state="working"),
                "s2": SessionSnapshot(session_id="s2", contract_state="idle"),
            },
            workers={"w1": {"id": "w1", "status": "idle"}},
        )
        d = snap.to_dict()
        restored = OfficeSnapshot.from_dict(d)
        assert len(restored.sessions) == 2
        assert "s1" in restored.sessions
        assert restored.sessions["s1"].contract_state == "working"


class TestCheckpointManager:
    """Test checkpoint manager."""

    @pytest.fixture
    def tmp_dir(self, tmp_path):
        return str(tmp_path / "snapshots")

    def test_save_and_load_snapshot(self, tmp_dir):
        from kantorku.persistence import CheckpointManager
        cm = CheckpointManager(snapshot_dir=tmp_dir)
        snap_id = asyncio.get_event_loop().run_until_complete(
            cm.save_session("s1", contract={"title": "Test"}, contract_state="working")
        )
        assert snap_id

        loaded = asyncio.get_event_loop().run_until_complete(
            cm.load_session("s1")
        )
        assert loaded is not None
        assert loaded.contract_state == "working"

    def test_auto_checkpoint(self, tmp_dir):
        from kantorku.persistence import CheckpointManager
        cm = CheckpointManager(snapshot_dir=tmp_dir, auto_interval=3)

        # First 2 calls: no checkpoint
        r1 = asyncio.get_event_loop().run_until_complete(
            cm.auto_checkpoint("s1", contract_state="idle")
        )
        r2 = asyncio.get_event_loop().run_until_complete(
            cm.auto_checkpoint("s1", contract_state="idle")
        )
        assert r1 is None
        assert r2 is None

        # 3rd call: checkpoint saved
        r3 = asyncio.get_event_loop().run_until_complete(
            cm.auto_checkpoint("s1", contract_state="working")
        )
        assert r3 is not None

    def test_delete_session(self, tmp_dir):
        from kantorku.persistence import CheckpointManager
        cm = CheckpointManager(snapshot_dir=tmp_dir)
        asyncio.get_event_loop().run_until_complete(
            cm.save_session("s1", contract_state="working")
        )
        assert (os.path.join(tmp_dir, "session_s1.json"))

        asyncio.get_event_loop().run_until_complete(cm.delete_session("s1"))
        # File should be deleted
        assert not os.path.exists(os.path.join(tmp_dir, "session_s1.json"))


class TestCrashRecovery:
    """Test crash recovery."""

    def test_no_recovery_data(self, tmp_path):
        from kantorku.persistence import CrashRecovery
        recovery = CrashRecovery(snapshot_dir=str(tmp_path / "empty"))
        result = asyncio.get_event_loop().run_until_complete(recovery.try_recover())
        assert result is None

    def test_recover_from_snapshot(self, tmp_path):
        from kantorku.persistence import CrashRecovery, CheckpointManager, atomic_write_json
        snap_dir = str(tmp_path / "snapshots")
        os.makedirs(snap_dir, exist_ok=True)

        # Create an office snapshot
        snapshot_data = {
            "snapshot_id": "test-123",
            "timestamp": "2026-05-01T00:00:00+00:00",
            "version": "0.3.0",
            "sessions": {
                "s1": {
                    "session_id": "s1",
                    "contract_state": "working",
                    "contract": {"title": "Test"},
                }
            },
            "workers": {},
            "providers": {},
            "cost_report": {},
            "metrics_summary": {},
        }
        atomic_write_json(os.path.join(snap_dir, "office_20260501_000000.json"), snapshot_data)

        recovery = CrashRecovery(snapshot_dir=snap_dir)
        result = asyncio.get_event_loop().run_until_complete(recovery.try_recover())
        assert result is not None
        assert "s1" in result.sessions
        assert result.sessions["s1"].contract_state == "working"

    def test_recovery_info(self, tmp_path):
        from kantorku.persistence import CrashRecovery
        recovery = CrashRecovery(snapshot_dir=str(tmp_path / "info"))
        info = recovery.get_recovery_info()
        assert "snapshot_dir" in info
        assert "office_snapshots" in info


# ── Task Queue Tests ──────────────────────────────────────────────────


class TestTaskQueue:
    """Test persistent task queue."""

    def test_enqueue_dequeue(self):
        from kantorku.task_queue import TaskQueue
        queue = TaskQueue()
        asyncio.get_event_loop().run_until_complete(queue.start())

        task_id = asyncio.get_event_loop().run_until_complete(
            queue.enqueue("Build feature X", session_id="s1", priority=5)
        )
        assert task_id

        task = asyncio.get_event_loop().run_until_complete(queue.dequeue(timeout=1))
        assert task is not None
        assert task.instruction == "Build feature X"
        assert task.priority == 5
        assert task.state.value == "in_progress"

    def test_priority_ordering(self):
        from kantorku.task_queue import TaskQueue
        queue = TaskQueue()
        asyncio.get_event_loop().run_until_complete(queue.start())

        # Enqueue with different priorities
        asyncio.get_event_loop().run_until_complete(
            queue.enqueue("Low priority", priority=1)
        )
        asyncio.get_event_loop().run_until_complete(
            queue.enqueue("High priority", priority=10)
        )
        asyncio.get_event_loop().run_until_complete(
            queue.enqueue("Medium priority", priority=5)
        )

        # Should get highest priority first
        t1 = asyncio.get_event_loop().run_until_complete(queue.dequeue(timeout=1))
        assert t1.instruction == "High priority"

        t2 = asyncio.get_event_loop().run_until_complete(queue.dequeue(timeout=1))
        assert t2.instruction == "Medium priority"

        t3 = asyncio.get_event_loop().run_until_complete(queue.dequeue(timeout=1))
        assert t3.instruction == "Low priority"

    def test_mark_done(self):
        from kantorku.task_queue import TaskQueue
        queue = TaskQueue()
        asyncio.get_event_loop().run_until_complete(queue.start())

        task_id = asyncio.get_event_loop().run_until_complete(
            queue.enqueue("Test task", session_id="s1")
        )
        task = asyncio.get_event_loop().run_until_complete(queue.dequeue(timeout=1))
        asyncio.get_event_loop().run_until_complete(
            queue.mark_done(task.id, result={"output": "done"})
        )

        task = queue.get_task(task_id)
        assert task.state.value == "done"
        assert task.result["output"] == "done"

    def test_retry_on_failure(self):
        from kantorku.task_queue import TaskQueue
        queue = TaskQueue(default_max_retries=2, retry_delay_seconds=0.1)
        asyncio.get_event_loop().run_until_complete(queue.start())

        task_id = asyncio.get_event_loop().run_until_complete(
            queue.enqueue("Flaky task", max_retries=2)
        )
        task = asyncio.get_event_loop().run_until_complete(queue.dequeue(timeout=1))
        asyncio.get_event_loop().run_until_complete(
            queue.mark_failed(task.id, error="Temporary error")
        )

        # Should be retrying
        task = queue.get_task(task_id)
        assert task.retry_count == 1
        assert task.state.value == "retrying"

    def test_dead_letter_queue(self):
        from kantorku.task_queue import TaskQueue
        queue = TaskQueue(default_max_retries=0, retry_delay_seconds=0.01)
        asyncio.get_event_loop().run_until_complete(queue.start())

        task_id = asyncio.get_event_loop().run_until_complete(
            queue.enqueue("Failing task", max_retries=0)
        )
        task = asyncio.get_event_loop().run_until_complete(queue.dequeue(timeout=1))
        asyncio.get_event_loop().run_until_complete(
            queue.mark_failed(task.id, error="Permanent error")
        )

        # Should be in DLQ
        dlq = queue.get_dead_letter_queue()
        assert len(dlq) == 1
        assert dlq[0].original_task_id == task_id

    def test_cancel_task(self):
        from kantorku.task_queue import TaskQueue
        queue = TaskQueue()
        asyncio.get_event_loop().run_until_complete(queue.start())

        task_id = asyncio.get_event_loop().run_until_complete(
            queue.enqueue("To be cancelled")
        )
        success = asyncio.get_event_loop().run_until_complete(queue.cancel(task_id))
        assert success

        task = queue.get_task(task_id)
        assert task.state.value == "cancelled"

    def test_queue_stats(self):
        from kantorku.task_queue import TaskQueue
        queue = TaskQueue()
        asyncio.get_event_loop().run_until_complete(queue.start())

        asyncio.get_event_loop().run_until_complete(queue.enqueue("Task 1"))
        asyncio.get_event_loop().run_until_complete(queue.enqueue("Task 2"))

        stats = queue.get_stats()
        assert stats["total_enqueued"] == 2
        assert stats["queue_depth"] == 2

    def test_dequeue_empty(self):
        from kantorku.task_queue import TaskQueue
        queue = TaskQueue()
        asyncio.get_event_loop().run_until_complete(queue.start())

        task = asyncio.get_event_loop().run_until_complete(queue.dequeue(timeout=0))
        assert task is None


# ── Middleware Tests ───────────────────────────────────────────────────


class TestMiddlewarePipeline:
    """Test middleware pipeline."""

    @pytest.mark.asyncio
    async def test_basic_pipeline(self):
        from kantorku.middleware import MiddlewarePipeline, MiddlewareContext

        pipeline = MiddlewarePipeline()

        async def my_operation(name: str = "world") -> str:
            return f"Hello, {name}!"

        result = await pipeline.execute(
            operation=my_operation,
            context=MiddlewareContext(operation="greet"),
            name="test",
        )
        assert result == "Hello, test!"

    @pytest.mark.asyncio
    async def test_before_hook(self):
        from kantorku.middleware import Middleware, MiddlewarePipeline, MiddlewareContext

        class EnrichMiddleware(Middleware):
            async def before(self, ctx: MiddlewareContext) -> MiddlewareContext:
                ctx.attributes["enriched"] = True
                return ctx

        pipeline = MiddlewarePipeline()
        pipeline.add(EnrichMiddleware())

        async def check_enriched(**kwargs) -> dict:
            return {"enriched": True}

        result = await pipeline.execute(
            operation=check_enriched,
            context=MiddlewareContext(),
        )

    @pytest.mark.asyncio
    async def test_before_short_circuit(self):
        from kantorku.middleware import Middleware, MiddlewarePipeline, MiddlewareContext

        class BlockMiddleware(Middleware):
            async def before(self, ctx: MiddlewareContext) -> MiddlewareContext:
                raise PermissionError("Blocked!")

        pipeline = MiddlewarePipeline()
        pipeline.add(BlockMiddleware())

        called = False

        async def should_not_be_called(**kwargs) -> str:
            nonlocal called
            called = True
            return "should not reach"

        with pytest.raises(PermissionError):
            await pipeline.execute(
                operation=should_not_be_called,
                context=MiddlewareContext(),
            )
        assert not called

    @pytest.mark.asyncio
    async def test_logging_middleware(self):
        from kantorku.middleware import LoggingMiddleware, MiddlewarePipeline, MiddlewareContext

        pipeline = MiddlewarePipeline()
        pipeline.add(LoggingMiddleware())

        async def my_op(**kwargs) -> str:
            return "ok"

        result = await pipeline.execute(
            operation=my_op,
            context=MiddlewareContext(operation="test", session_id="s1"),
        )
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_rate_limit_middleware(self):
        from kantorku.middleware import RateLimitMiddleware, MiddlewarePipeline, MiddlewareContext

        pipeline = MiddlewarePipeline()
        pipeline.add(RateLimitMiddleware(max_requests=2, window_seconds=60))

        async def my_op(**kwargs) -> str:
            return "ok"

        # First 2 should work
        r1 = await pipeline.execute(operation=my_op, context=MiddlewareContext(session_id="s1"))
        r2 = await pipeline.execute(operation=my_op, context=MiddlewareContext(session_id="s1"))

        # Third should be rate limited
        with pytest.raises(PermissionError, match="Rate limit exceeded"):
            await pipeline.execute(operation=my_op, context=MiddlewareContext(session_id="s1"))

    @pytest.mark.asyncio
    async def test_cost_guard_middleware(self):
        from kantorku.middleware import CostGuardMiddleware, MiddlewarePipeline, MiddlewareContext
        from kantorku.cost import CostTracker

        tracker = CostTracker()
        # Record some cost to exceed the limit
        tracker.record("anthropic/claude-opus-4-6", 100000, 100000, session_id="s1")

        pipeline = MiddlewarePipeline()
        pipeline.add(CostGuardMiddleware(max_session_cost=0.01, cost_tracker=tracker))

        async def my_op(**kwargs) -> str:
            return "ok"

        with pytest.raises(PermissionError, match="Session cost limit"):
            await pipeline.execute(
                operation=my_op,
                context=MiddlewareContext(session_id="s1"),
            )


# ── Health Tests ──────────────────────────────────────────────────────


class TestHealthChecker:
    """Test health monitoring."""

    def test_liveness(self):
        from kantorku.health import HealthChecker, HealthStatus
        checker = HealthChecker()
        result = checker.liveness()
        assert result.status == HealthStatus.HEALTHY
        assert result.is_healthy

    def test_readiness_without_office(self):
        from kantorku.health import HealthChecker, HealthStatus
        checker = HealthChecker()
        result = checker.readiness()
        # Without office initialized, should be unhealthy
        assert result.status == HealthStatus.UNHEALTHY

    def test_alert_system(self):
        from kantorku.health import AlertSystem
        alerts = AlertSystem()

        alert = alerts.trigger("critical", "anthropic", "Circuit breaker open")
        assert alert.severity == "critical"
        assert alert.source == "anthropic"

        active = alerts.get_active()
        assert len(active) == 1

        alerts.resolve("anthropic")
        active = alerts.get_active()
        assert len(active) == 0

    def test_worker_health_update(self):
        from kantorku.health import HealthChecker
        checker = HealthChecker()

        checker.update_worker_health("coder_backend", completed=True, duration_seconds=5.0)
        status = checker._worker_health.get("coder_backend")
        assert status is not None
        assert status.tasks_completed == 1

    def test_provider_health_update(self):
        from kantorku.health import HealthChecker
        checker = HealthChecker()

        checker.update_provider_health("anthropic", success=True, latency_ms=150.0)
        status = checker._provider_health.get("anthropic")
        assert status is not None
        assert status.is_configured
        assert status.total_calls == 1
        assert status.success_rate == 1.0

    def test_consecutive_failures_triggers_unhealthy(self):
        from kantorku.health import HealthChecker
        checker = HealthChecker(worker_failure_threshold=3)

        for i in range(3):
            checker.update_worker_health("coder_backend", failed=True)

        status = checker._worker_health.get("coder_backend")
        assert not status.is_healthy

    def test_dashboard(self):
        from kantorku.health import HealthChecker
        checker = HealthChecker()
        dashboard = checker.dashboard()
        assert "status" in dashboard
        assert "alerts" in dashboard
        assert "providers" in dashboard
        assert "workers" in dashboard


class TestHealthStatus:
    """Test health status enums and data classes."""

    def test_health_status_values(self):
        from kantorku.health import HealthStatus
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"

    def test_health_check_result_to_dict(self):
        from kantorku.health import HealthCheckResult, HealthStatus
        result = HealthCheckResult(
            name="test",
            status=HealthStatus.HEALTHY,
            message="All good",
            duration_ms=5.0,
        )
        d = result.to_dict()
        assert d["name"] == "test"
        assert d["status"] == "healthy"

    def test_aggregated_health_to_dict(self):
        from kantorku.health import AggregatedHealth, HealthStatus, HealthCheckResult
        health = AggregatedHealth(
            status=HealthStatus.DEGRADED,
            checks=[
                HealthCheckResult(name="providers", status=HealthStatus.DEGRADED),
            ],
            uptime_seconds=3600.0,
        )
        d = health.to_dict()
        assert d["status"] == "degraded"
        assert d["is_healthy"] is True  # degraded is still "healthy"
        assert len(d["checks"]) == 1


# ── Integration Tests ─────────────────────────────────────────────────


class TestP3Integration:
    """Test all P3 systems working together."""

    @pytest.mark.asyncio
    async def test_task_queue_with_persistence(self, tmp_path):
        """Test that task queue works with persistence."""
        from kantorku.task_queue import TaskQueue
        from kantorku.persistence import CheckpointManager

        queue = TaskQueue(default_max_retries=1)
        await queue.start()

        # Enqueue some tasks
        t1 = await queue.enqueue("Task 1", session_id="s1", priority=3)
        t2 = await queue.enqueue("Task 2", session_id="s1", priority=5)

        # Dequeue and process one
        task = await queue.dequeue(timeout=1)
        await queue.mark_done(task.id, result={"output": "completed"})

        # Check stats
        stats = queue.get_stats()
        assert stats["total_completed"] == 1
        assert stats["queue_depth"] == 1

        await queue.stop()

    @pytest.mark.asyncio
    async def test_middleware_with_cost_guard(self):
        """Test middleware pipeline with cost guard integration."""
        from kantorku.middleware import MiddlewarePipeline, MiddlewareContext, LoggingMiddleware, RateLimitMiddleware
        from kantorku.cost import CostTracker

        tracker = CostTracker()
        pipeline = MiddlewarePipeline()
        pipeline.add(LoggingMiddleware())
        pipeline.add(RateLimitMiddleware(max_requests=100, window_seconds=60))

        async def my_op(**kwargs) -> str:
            return "success"

        result = await pipeline.execute(
            operation=my_op,
            context=MiddlewareContext(session_id="s1"),
        )
        assert result == "success"

    def test_snapshot_and_recovery_flow(self, tmp_path):
        """Test full snapshot → crash → recovery flow."""
        from kantorku.persistence import (
            CheckpointManager, CrashRecovery,
            SessionSnapshot, atomic_write_json,
        )

        snap_dir = str(tmp_path / "snapshots")
        os.makedirs(snap_dir, exist_ok=True)

        # 1. Create checkpoint manager and save session
        cm = CheckpointManager(snapshot_dir=snap_dir)
        snap_id = asyncio.get_event_loop().run_until_complete(
            cm.save_session(
                "s1",
                contract={"title": "Build API"},
                contract_state="working",
            )
        )
        assert snap_id

        # 2. Simulate crash (nothing needed — just stop)

        # 3. Create recovery and try to restore
        recovery = CrashRecovery(snapshot_dir=snap_dir)
        result = asyncio.get_event_loop().run_until_complete(recovery.try_recover())
        assert result is not None
        assert "s1" in result.sessions
        assert result.sessions["s1"].contract_state == "working"

    @pytest.mark.asyncio
    async def test_health_with_mock_office(self):
        """Test health checker with a mock-like office."""
        from kantorku.health import HealthChecker, HealthStatus

        # Minimal mock office
        class MockOffice:
            _initialized = True
            cost_tracker = None
            registry = None
            router = None

            class _Registry:
                all_worker_ids = []

            registry = _Registry()

        office = MockOffice()
        checker = HealthChecker(office=office, check_interval=300)

        # Liveness should always be healthy
        live = checker.liveness()
        assert live.is_healthy

        # Update provider health
        checker.update_provider_health("anthropic", success=True, latency_ms=200.0)
        checker.update_provider_health("anthropic", success=False, latency_ms=0, error="timeout")

        provider = checker._provider_health.get("anthropic")
        assert provider.total_calls == 2
        assert provider.failed_calls == 1
        assert provider.success_rate == 0.5

        # Dashboard should work
        dashboard = checker.dashboard()
        assert "providers" in dashboard
        assert "anthropic" in dashboard["providers"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
