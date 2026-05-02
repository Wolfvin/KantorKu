"""
Tests for the P0 backend maturation features:
- ProviderResponse
- Structured Errors
- Circuit Breaker
- Retry Policy
- Cost Tracker Integration
- LLM Cache Integration
- Observability Integration
- Office async context manager
- Router complete_with_usage
"""

import asyncio
import time

import pytest

from kantorku import (
    Office,
    BaseWorker,
    WorkerStatus,
    Task,
    TaskResult,
    ProviderResponse,
    KantorkuError,
    ProviderError,
    ProviderTimeoutError,
    ProviderRateLimitError,
    ProviderAuthError,
    ProviderCircuitOpenError,
    AllProvidersFailedError,
    WorkerError,
    WorkerTimeoutError,
    OfficeNotInitializedError,
    NoContractError,
    CircuitBreaker,
    CircuitState,
    RetryPolicy,
    DEFAULT_RETRY_POLICY,
    CostTracker,
    LLMCache,
    EventBus,
    WorkerIdentity,
    WorkerRegistry,
)
from kantorku.providers.router import ProviderRouter
from kantorku.providers.circuit_breaker import CircuitBreaker as CB
from kantorku.providers.retry import retry_with_backoff


# ── ProviderResponse Tests ──────────────────────────────────────────


class TestProviderResponse:
    def test_basic_creation(self):
        r = ProviderResponse(
            content="Hello!",
            model="claude-opus-4-6",
            provider_name="anthropic",
            prompt_tokens=10,
            completion_tokens=5,
            latency_ms=150.0,
        )
        assert r.content == "Hello!"
        assert r.total_tokens == 15
        assert not r.cached
        assert not r.is_empty
        assert r.provider_name == "anthropic"

    def test_auto_total_tokens(self):
        r = ProviderResponse(prompt_tokens=100, completion_tokens=50)
        assert r.total_tokens == 150

    def test_cached_response(self):
        r = ProviderResponse.cached_response("Cached!", model="test")
        assert r.cached is True
        assert r.latency_ms == 0.0
        assert r.content == "Cached!"
        assert r.provider_name == "cache"

    def test_empty_response(self):
        r = ProviderResponse()
        assert r.is_empty
        assert r.content == ""

    def test_non_empty_response(self):
        r = ProviderResponse(content="Hi")
        assert not r.is_empty

    def test_to_dict(self):
        r = ProviderResponse(
            content="Test",
            model="gpt-4o",
            provider_name="openai",
            prompt_tokens=5,
            completion_tokens=3,
            latency_ms=100.0,
        )
        d = r.to_dict()
        assert d["content"] == "Test"
        assert d["model"] == "gpt-4o"
        assert d["provider_name"] == "openai"
        assert d["prompt_tokens"] == 5
        assert d["completion_tokens"] == 3
        assert d["total_tokens"] == 8
        assert d["latency_ms"] == 100.0
        assert d["cached"] is False


# ── Structured Error Tests ──────────────────────────────────────────


class TestStructuredErrors:
    def test_base_error(self):
        e = KantorkuError("TEST_CODE", "Test message", {"key": "value"})
        assert e.code == "TEST_CODE"
        assert e.message == "Test message"
        assert e.context["key"] == "value"
        d = e.to_dict()
        assert d["code"] == "TEST_CODE"

    def test_provider_error(self):
        e = ProviderError("anthropic", "API failed", model="claude-opus-4-6", status_code=500)
        assert e.provider == "anthropic"
        assert e.model == "claude-opus-4-6"
        assert e.status_code == 500
        assert e.context["provider"] == "anthropic"
        assert isinstance(e, KantorkuError)

    def test_provider_timeout(self):
        e = ProviderTimeoutError("openai", timeout_seconds=30.0)
        assert e.code == "PROVIDER_TIMEOUT"
        assert e.context["timeout_seconds"] == 30.0

    def test_provider_rate_limit(self):
        e = ProviderRateLimitError("anthropic", retry_after=5.0)
        assert e.code == "PROVIDER_RATE_LIMIT"
        assert e.context["retry_after"] == 5.0

    def test_provider_auth(self):
        e = ProviderAuthError("openai")
        assert e.code == "PROVIDER_AUTH"

    def test_circuit_open(self):
        e = ProviderCircuitOpenError("anthropic", reset_at=time.time() + 60)
        assert e.code == "PROVIDER_CIRCUIT_OPEN"

    def test_all_providers_failed(self):
        e = AllProvidersFailedError("anthropic", fallbacks=["deepseek", "ollama"])
        assert e.code == "ALL_PROVIDERS_FAILED"
        assert "anthropic" in str(e)

    def test_worker_error(self):
        e = WorkerError("coder_backend", "Task failed")
        assert e.worker_id == "coder_backend"
        assert isinstance(e, KantorkuError)

    def test_worker_timeout(self):
        e = WorkerTimeoutError("coder_backend", timeout_seconds=300)
        assert e.code == "WORKER_TIMEOUT"

    def test_office_not_initialized(self):
        e = OfficeNotInitializedError()
        assert e.code == "OFFICE_NOT_INITIALIZED"
        assert "initialize" in str(e).lower()

    def test_no_contract(self):
        e = NoContractError("session-123")
        assert e.code == "NO_CONTRACT"


# ── Circuit Breaker Tests ───────────────────────────────────────────


class TestCircuitBreaker:
    def test_initially_closed(self):
        cb = CB(failure_threshold=3)
        assert not cb.is_open("test")
        circuit = cb._get_circuit("test")
        assert circuit.state == CircuitState.CLOSED

    def test_opens_after_threshold(self):
        cb = CB(failure_threshold=3)
        cb.record_failure("test")
        cb.record_failure("test")
        assert not cb.is_open("test")  # Not yet
        cb.record_failure("test")
        assert cb.is_open("test")  # Now open

    def test_success_resets_failures(self):
        cb = CB(failure_threshold=3)
        cb.record_failure("test")
        cb.record_failure("test")
        cb.record_success("test")
        # Failure count should be reset
        circuit = cb._get_circuit("test")
        assert circuit.failure_count == 0
        assert circuit.state == CircuitState.CLOSED

    def test_half_open_to_closed(self):
        cb = CB(failure_threshold=1, reset_timeout_seconds=0.05)
        cb.record_failure("test")
        assert cb.is_open("test")
        time.sleep(0.1)  # Wait for reset timeout
        assert not cb.is_open("test")  # Now half-open
        cb.record_success("test")
        circuit = cb._get_circuit("test")
        assert circuit.state == CircuitState.CLOSED

    def test_half_open_to_open(self):
        cb = CB(failure_threshold=1, reset_timeout_seconds=0.05)
        cb.record_failure("test")
        time.sleep(0.1)  # Wait for reset timeout
        assert not cb.is_open("test")  # Half-open
        cb.record_failure("test")  # Test request failed
        circuit = cb._get_circuit("test")
        assert circuit.state == CircuitState.OPEN

    def test_reset(self):
        cb = CB(failure_threshold=1)
        cb.record_failure("test")
        assert cb.is_open("test")
        cb.reset("test")
        assert not cb.is_open("test")

    def test_status(self):
        cb = CB(failure_threshold=1)
        cb.record_failure("test")
        status = cb.get_status()
        assert "test" in status
        assert status["test"]["state"] in ("open", "closed", "half_open")


# ── Retry Policy Tests ──────────────────────────────────────────────


class TestRetryPolicy:
    def test_delay_computation(self):
        policy = RetryPolicy(base_delay=0.1, max_delay=10.0, exponential_base=2.0, jitter=False)
        assert abs(policy.compute_delay(0) - 0.1) < 0.01
        assert abs(policy.compute_delay(1) - 0.2) < 0.01
        assert abs(policy.compute_delay(2) - 0.4) < 0.01

    def test_max_delay_cap(self):
        policy = RetryPolicy(base_delay=1.0, max_delay=2.0, exponential_base=10.0, jitter=False)
        assert policy.compute_delay(5) <= 2.0

    def test_retryable_classification(self):
        policy = RetryPolicy()
        # Non-retryable
        assert not policy.is_retryable(ProviderAuthError("openai"))
        # Retryable
        assert policy.is_retryable(ProviderTimeoutError("openai", timeout_seconds=10))
        assert policy.is_retryable(ProviderRateLimitError("openai", retry_after=5))
        assert policy.is_retryable(ConnectionError("Connection refused"))
        assert policy.is_retryable(asyncio.TimeoutError())

    @pytest.mark.asyncio
    async def test_retry_with_backoff_success_first_try(self):
        call_count = 0

        async def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"

        policy = RetryPolicy(max_retries=3, base_delay=0.01)
        result = await retry_with_backoff(policy, succeed, provider_name="test")
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_with_backoff_eventual_success(self):
        call_count = 0

        async def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection refused")
            return "ok"

        policy = RetryPolicy(max_retries=3, base_delay=0.01)
        result = await retry_with_backoff(policy, fail_then_succeed, provider_name="test")
        assert result == "ok"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        async def always_fail():
            raise ConnectionError("Down")

        policy = RetryPolicy(max_retries=2, base_delay=0.01)
        with pytest.raises(ConnectionError):
            await retry_with_backoff(policy, always_fail, provider_name="test")

    @pytest.mark.asyncio
    async def test_retry_non_retryable_not_retried(self):
        call_count = 0

        async def auth_fail():
            nonlocal call_count
            call_count += 1
            raise ProviderAuthError("openai")

        policy = RetryPolicy(max_retries=3, base_delay=0.01)
        with pytest.raises(ProviderAuthError):
            await retry_with_backoff(policy, auth_fail, provider_name="openai")
        assert call_count == 1  # Not retried


# ── Cost Tracker Integration Tests ──────────────────────────────────


class TestCostTrackerIntegration:
    def test_office_has_cost_tracker(self):
        office = Office(enable_cost_tracking=True)
        assert office.cost_tracker is not None
        assert office.router._cost_tracker is office.cost_tracker

    def test_office_without_cost_tracking(self):
        office = Office(enable_cost_tracking=False)
        assert office.cost_tracker is None

    def test_cost_report_empty(self):
        office = Office(enable_cost_tracking=True)
        report = office.get_cost_report()
        assert report["total_cost_usd"] == 0.0
        assert report["total_calls"] == 0

    def test_cost_tracker_manual_recording(self):
        tracker = CostTracker()
        cost = tracker.record(
            model="anthropic/claude-opus-4-6",
            prompt_tokens=1000,
            completion_tokens=500,
            session_id="sess-1",
            worker_id="coder_backend",
        )
        assert cost > 0
        report = tracker.get_report()
        assert report["total_cost_usd"] > 0
        assert report["total_calls"] == 1
        assert "anthropic/claude-opus-4-6" in report["by_model"]


# ── LLM Cache Integration Tests ─────────────────────────────────────


class TestLLMCacheIntegration:
    def test_office_has_cache(self):
        office = Office(enable_cache=True)
        assert office.cache is not None
        assert office.router._cache is office.cache

    def test_office_without_cache(self):
        office = Office(enable_cache=False)
        assert office.cache is None

    @pytest.mark.asyncio
    async def test_cache_lookup_and_store(self):
        cache = LLMCache(backend="memory", ttl_seconds=3600)
        await cache.initialize()

        # Store
        await cache.store(
            model="anthropic/claude-opus-4-6",
            messages=[{"role": "user", "content": "Hello"}],
            response="Hi there!",
        )

        # Lookup
        result = await cache.lookup(
            model="anthropic/claude-opus-4-6",
            messages=[{"role": "user", "content": "Hello"}],
        )
        assert result == "Hi there!"

        # Different messages → miss
        miss = await cache.lookup(
            model="anthropic/claude-opus-4-6",
            messages=[{"role": "user", "content": "Goodbye"}],
        )
        assert miss is None

        await cache.close()


# ── Router Integration Tests ────────────────────────────────────────


class TestRouterIntegration:
    def test_router_has_cost_tracker(self):
        tracker = CostTracker()
        router = ProviderRouter(cost_tracker=tracker)
        assert router._cost_tracker is tracker

    def test_router_has_cache(self):
        cache = LLMCache(backend="memory")
        router = ProviderRouter(cache=cache)
        assert router._cache is cache

    def test_router_has_circuit_breaker(self):
        cb = CircuitBreaker()
        router = ProviderRouter(circuit_breaker=cb)
        assert router._circuit_breaker is cb

    def test_router_has_retry_policy(self):
        policy = RetryPolicy(max_retries=5)
        router = ProviderRouter(retry_policy=policy)
        assert router._retry_policy is policy

    def test_router_default_retry(self):
        router = ProviderRouter()
        assert router._retry_policy.max_retries == DEFAULT_RETRY_POLICY.max_retries

    def test_router_has_complete_with_usage(self):
        router = ProviderRouter()
        assert hasattr(router, "complete_with_usage")

    def test_router_circuit_breaker_status(self):
        router = ProviderRouter()
        status = router.get_circuit_breaker_status()
        assert isinstance(status, dict)

    def test_router_cost_report(self):
        router = ProviderRouter(cost_tracker=CostTracker())
        report = router.get_cost_report()
        assert isinstance(report, dict)

    def test_router_metrics_summary(self):
        router = ProviderRouter()
        summary = router.get_metrics_summary()
        assert isinstance(summary, dict)

    def test_openai_xai_provider_registered(self):
        router = ProviderRouter()
        assert "openai" in router.PROVIDER_MAP
        assert "xai" in router.PROVIDER_MAP


# ── Office Integration Tests ────────────────────────────────────────


class TestOfficeIntegration:
    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        office = Office()
        # Mock initialize to avoid needing real providers
        office._initialized = True
        # The context manager should work
        # (We can't fully test without real providers, but we can verify the protocol)
        assert hasattr(office, "__aenter__")
        assert hasattr(office, "__aexit__")

    def test_office_new_methods(self):
        office = Office()
        assert hasattr(office, "get_cost_report")
        assert hasattr(office, "get_circuit_breaker_status")
        assert hasattr(office, "get_metrics_summary")
        assert hasattr(office, "get_observability_spans")

    def test_office_default_config(self):
        office = Office()
        assert office.cost_tracker is not None
        assert office.cache is not None
        assert office.router is not None

    def test_office_custom_cache_ttl(self):
        office = Office(cache_ttl=7200)
        assert office.cache is not None

    @pytest.mark.asyncio
    async def test_observability_spans_empty(self):
        office = Office()
        spans = office.get_observability_spans()
        assert isinstance(spans, list)


# ── BaseWorker with structured errors ────────────────────────────────


class TestWorkerStructuredErrors:
    @pytest.mark.asyncio
    async def test_worker_timeout_returns_structured_result(self):
        class SlowWorker(BaseWorker):
            async def handle(self, task):
                await asyncio.sleep(10)
                return TaskResult(task_id=task.id, status="done", output="Never")

        bus = EventBus()
        router = ProviderRouter()
        identity = WorkerIdentity.from_dict({
            "id": "slow_worker",
            "model": "ollama/llama3",
        })
        worker = SlowWorker(identity=identity, router=router, bus=bus)
        worker.DEFAULT_TASK_TIMEOUT = 0.1  # Very short timeout for testing

        task = Task(instruction="Do something slow", session_id="test")
        result = await worker.execute(task)

        assert result.status == "failed"
        assert "timed out" in result.error.lower()

    @pytest.mark.asyncio
    async def test_worker_success(self):
        class FastWorker(BaseWorker):
            async def handle(self, task):
                return TaskResult(task_id=task.id, status="done", output="Done!")

        bus = EventBus()
        router = ProviderRouter()
        identity = WorkerIdentity.from_dict({
            "id": "fast_worker",
            "model": "ollama/llama3",
        })
        worker = FastWorker(identity=identity, router=router, bus=bus)

        task = Task(instruction="Do something", session_id="test")
        result = await worker.execute(task)

        assert result.status == "done"
        assert result.output == "Done!"
        assert worker.status == WorkerStatus.DONE
