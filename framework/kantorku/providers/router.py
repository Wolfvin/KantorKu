"""
Provider Router — Route LLM calls to the right provider.

Model format: "provider/model-name"
Examples: "anthropic/claude-opus-4-6", "minimax/minimax-m2-7", "deepseek/deepseek-v3-2"

The router parses the provider prefix and dispatches to the appropriate provider.
Integrates:
- Rate limiting (token bucket + semaphore)
- Circuit breaker (protect against cascading failures)
- Retry with exponential backoff
- LLM response caching
- Cost tracking
- Observability (tracing + metrics)
- Provider fallback on failure
"""

from __future__ import annotations

import logging
import time
from typing import Any, AsyncIterator

from kantorku.providers.base import BaseProvider
from kantorku.providers.anthropic_provider import AnthropicProvider
from kantorku.providers.google_provider import GoogleProvider
from kantorku.providers.minimax_provider import MiniMaxProvider
from kantorku.providers.deepseek_provider import DeepSeekProvider
from kantorku.providers.ollama_provider import OllamaProvider
from kantorku.providers.openai_compat import OpenAICompatProvider
from kantorku.providers.rate_limiter import RateLimiter
from kantorku.providers.circuit_breaker import CircuitBreaker
from kantorku.providers.retry import RetryPolicy, retry_with_backoff, DEFAULT_RETRY_POLICY
from kantorku.provider_response import ProviderResponse
from kantorku.cost import CostTracker
from kantorku.cache import LLMCache
from kantorku.observability import get_tracer, get_metrics
from kantorku.errors import (
    ProviderCircuitOpenError,
    AllProvidersFailedError,
    ProviderError,
)

logger = logging.getLogger("kantorku.providers")


class ProviderRouter:
    """
    Route LLM calls to the correct provider based on model prefix.

    Features:
    - Rate limiting per provider (token bucket + semaphore)
    - Circuit breaker per provider (prevent cascading failures)
    - Retry with exponential backoff
    - LLM response caching (in-memory or DuckDB)
    - Cost tracking (per-model pricing)
    - Observability (tracing spans + metrics)
    - Provider fallback on failure

    Usage:
        router = ProviderRouter()
        router.configure("anthropic", api_key="sk-...")
        router.configure("deepseek", api_key="sk-...")

        # Simple call (returns string, backwards compatible)
        response = await router.complete(
            model="anthropic/claude-opus-4-6",
            messages=[{"role": "user", "content": "Hello"}],
        )

        # Full call (returns ProviderResponse with token counts, cost, etc.)
        result = await router.complete_with_usage(
            model="anthropic/claude-opus-4-6",
            messages=[{"role": "user", "content": "Hello"}],
        )
        print(f"Tokens: {result.prompt_tokens}+{result.completion_tokens}")
        print(f"Latency: {result.latency_ms:.0f}ms")
        print(f"Cached: {result.cached}")
    """

    PROVIDER_MAP: dict[str, type[BaseProvider]] = {
        "anthropic": AnthropicProvider,
        "google": GoogleProvider,
        "minimax": MiniMaxProvider,
        "deepseek": DeepSeekProvider,
        "openai": OpenAICompatProvider,
        "xai": OpenAICompatProvider,  # xAI uses OpenAI-compatible API
        "meta": OpenAICompatProvider,  # Meta uses OpenAI-compatible API
        "ollama": OllamaProvider,
    }

    # Default base URLs for providers that need them
    PROVIDER_DEFAULTS: dict[str, dict[str, Any]] = {
        "openai": {"base_url": "https://api.openai.com/v1"},
        "xai": {"base_url": "https://api.x.ai/v1"},
    }

    def __init__(
        self,
        cost_tracker: CostTracker | None = None,
        cache: LLMCache | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self._providers: dict[str, BaseProvider] = {}
        self._rate_limiter = RateLimiter()
        self._fallbacks: dict[str, list[str]] = {}

        # Integrations
        self._cost_tracker = cost_tracker
        self._cache = cache
        self._circuit_breaker = circuit_breaker or CircuitBreaker()
        self._retry_policy = retry_policy or DEFAULT_RETRY_POLICY

        # Observability
        self._tracer = get_tracer()
        self._metrics = get_metrics()

    def set_cost_tracker(self, tracker: CostTracker) -> None:
        """Set or replace the cost tracker."""
        self._cost_tracker = tracker

    def set_cache(self, cache: LLMCache) -> None:
        """Set or replace the LLM cache."""
        self._cache = cache

    def configure(self, provider_name: str, **kwargs: Any) -> None:
        """
        Configure a provider with credentials and settings.

        Args:
            provider_name: One of "anthropic", "google", "minimax", "deepseek", "ollama", "openai", "xai"
            **kwargs: Provider-specific config (api_key, base_url, etc.)
        """
        provider_name = provider_name.lower()
        cls = self.PROVIDER_MAP.get(provider_name)
        if cls is None:
            raise ValueError(
                f"Unknown provider '{provider_name}'. "
                f"Available: {list(self.PROVIDER_MAP.keys())}"
            )

        # Apply provider defaults (e.g. base_url for openai/xai)
        defaults = self.PROVIDER_DEFAULTS.get(provider_name, {})
        merged = {**defaults, **kwargs}

        self._providers[provider_name] = cls(**merged)

    def configure_from_dict(self, providers_config: dict[str, dict[str, Any]]) -> None:
        """
        Configure multiple providers from a dict (e.g. from TOML [providers.*]).

        Handles environment variable expansion for api_key.
        Also reads rate_limit and fallback config if present.
        """
        import os

        for name, config in providers_config.items():
            # Extract non-provider keys
            provider_kwargs = {}
            rate_limit_kwargs = {}
            fallback_list = None

            for k, v in config.items():
                if k == "rate_limit":
                    rate_limit_kwargs = v if isinstance(v, dict) else {}
                elif k == "fallback":
                    fallback_list = v if isinstance(v, list) else None
                elif isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                    env_var = v[2:-1]
                    provider_kwargs[k] = os.environ.get(env_var, "")
                else:
                    provider_kwargs[k] = v

            self.configure(name, **provider_kwargs)

            if rate_limit_kwargs:
                self.configure_rate_limit(name, **rate_limit_kwargs)

            if fallback_list:
                self.configure_fallback(name, fallback_list)

    def configure_rate_limit(
        self,
        provider: str,
        rps: float = 0.0,
        max_concurrent: int = 0,
        burst: int = 5,
    ) -> None:
        """Configure rate limits for a provider."""
        self._rate_limiter.configure(
            provider, rps=rps, max_concurrent=max_concurrent, burst=burst
        )
        logger.info(f"Rate limit configured for {provider}: rps={rps}, max_concurrent={max_concurrent}")

    def configure_fallback(self, provider: str, fallbacks: list[str]) -> None:
        """Configure fallback providers to try if the primary fails."""
        self._fallbacks[provider] = fallbacks
        logger.info(f"Fallback configured for {provider}: {fallbacks}")

    def _parse_model(self, model: str) -> tuple[str, str]:
        """Parse 'provider/model-name' into (provider, model_name)."""
        if "/" not in model:
            raise ValueError(
                f"Model must be in 'provider/model-name' format, got: '{model}'"
            )
        provider, model_name = model.split("/", 1)
        return provider.lower(), model_name

    def _get_provider(self, provider_name: str) -> BaseProvider:
        """Get a configured provider, raising if not configured."""
        if provider_name not in self._providers:
            configured = list(self._providers.keys())
            raise ValueError(
                f"Provider '{provider_name}' not configured. "
                f"Configured: {configured}. "
                f"Call router.configure('{provider_name}', ...) first."
            )
        return self._providers[provider_name]

    async def complete(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> str:
        """
        Send a chat completion request (returns string, backwards compatible).

        Includes: rate limiting, circuit breaker, retry, cache, cost tracking, observability.
        """
        result = await self.complete_with_usage(model=model, messages=messages, **kwargs)
        return result.content

    async def complete_with_usage(
        self,
        model: str,
        messages: list[dict[str, str]],
        session_id: str = "",
        worker_id: str = "",
        **kwargs: Any,
    ) -> ProviderResponse:
        """
        Send a chat completion request with full structured response.

        Pipeline:
        1. Check LLM cache → return cached if hit
        2. Check circuit breaker → skip if open
        3. Apply rate limiting
        4. Call provider with retry + exponential backoff
        5. Record cost + metrics
        6. Store in cache
        7. Return ProviderResponse

        Args:
            model: Full model identifier (e.g. "anthropic/claude-opus-4-6")
            messages: Chat messages in OpenAI format
            session_id: Optional session ID for cost/metrics tracking
            worker_id: Optional worker ID for cost/metrics tracking
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            ProviderResponse with content, token counts, cost, latency
        """
        provider_name, model_name = self._parse_model(model)

        # 1. Check cache
        if self._cache:
            try:
                cached = await self._cache.lookup(model, messages, **kwargs)
                if cached:
                    logger.debug(f"Cache hit for {model}")
                    return ProviderResponse.cached_response(
                        content=cached,
                        model=model_name,
                        provider_name=provider_name,
                    )
            except Exception as e:
                logger.debug(f"Cache lookup failed: {e}")

        # 2. Check circuit breaker
        if self._circuit_breaker.is_open(provider_name):
            # Try fallback instead
            return await self._try_fallbacks_with_usage(
                primary_model=model_name,
                messages=messages,
                failed_provider=provider_name,
                session_id=session_id,
                worker_id=worker_id,
                **kwargs,
            )

        # 3. Execute with rate limiting, retry, and observability
        result = await self._execute_with_observability(
            provider_name=provider_name,
            model_name=model_name,
            full_model=model,
            messages=messages,
            session_id=session_id,
            worker_id=worker_id,
            **kwargs,
        )

        return result

    async def _execute_with_observability(
        self,
        provider_name: str,
        model_name: str,
        full_model: str,
        messages: list[dict[str, str]],
        session_id: str = "",
        worker_id: str = "",
        **kwargs: Any,
    ) -> ProviderResponse:
        """Execute a provider call with full observability pipeline."""

        # Tracing span
        with self._tracer.span(
            f"llm.{provider_name}",
            attributes={
                "provider": provider_name,
                "model": model_name,
                "session_id": session_id,
                "worker_id": worker_id,
            },
        ) as span:
            try:
                # Rate limiting
                async with self._rate_limiter.limit(provider_name):
                    provider = self._get_provider(provider_name)

                    # Retry with backoff
                    result = await retry_with_backoff(
                        policy=self._retry_policy,
                        fn=lambda: provider.complete_with_usage(
                            model=model_name, messages=messages, **kwargs
                        ),
                        provider_name=provider_name,
                        on_retry=lambda attempt, delay, err: span.add_event(
                            "retry", {"attempt": attempt, "delay": delay, "error": str(err)}
                        ),
                    )

                # Ensure provider_name is set
                if not result.provider_name:
                    result.provider_name = provider_name
                if not result.model:
                    result.model = model_name

                # Record success
                self._circuit_breaker.record_success(provider_name)

                # Cost tracking
                if self._cost_tracker and result.total_tokens > 0:
                    self._cost_tracker.record(
                        model=full_model,
                        prompt_tokens=result.prompt_tokens,
                        completion_tokens=result.completion_tokens,
                        session_id=session_id,
                        worker_id=worker_id,
                    )

                # Metrics
                self._metrics.record_tokens(
                    provider=provider_name,
                    model=model_name,
                    prompt_tokens=result.prompt_tokens,
                    completion_tokens=result.completion_tokens,
                    worker_id=worker_id,
                    session_id=session_id,
                )
                if result.latency_ms > 0:
                    self._metrics.record_duration(
                        worker_id=worker_id or provider_name,
                        duration_seconds=result.latency_ms / 1000,
                        session_id=session_id,
                    )

                # Cache the response
                if self._cache and not result.cached:
                    try:
                        await self._cache.store(model, messages, result.content, **kwargs)
                    except Exception as e:
                        logger.debug(f"Cache store failed: {e}")

                # Span attributes
                span.set_attribute("prompt_tokens", result.prompt_tokens)
                span.set_attribute("completion_tokens", result.completion_tokens)
                span.set_attribute("latency_ms", result.latency_ms)
                span.set_attribute("cached", result.cached)

                return result

            except Exception as e:
                # Record failure
                self._circuit_breaker.record_failure(provider_name)
                span.set_status("error")
                span.set_attribute("error.type", type(e).__name__)
                span.set_attribute("error.message", str(e))

                # Try fallbacks
                try:
                    return await self._try_fallbacks_with_usage(
                        primary_model=model_name,
                        messages=messages,
                        failed_provider=provider_name,
                        session_id=session_id,
                        worker_id=worker_id,
                        **kwargs,
                    )
                except Exception:
                    raise

    async def _try_fallbacks_with_usage(
        self,
        primary_model: str,
        messages: list[dict[str, str]],
        failed_provider: str,
        session_id: str = "",
        worker_id: str = "",
        **kwargs: Any,
    ) -> ProviderResponse:
        """Try fallback providers when the primary fails."""
        fallbacks = self._fallbacks.get(failed_provider, [])
        errors: list[str] = []

        for fallback_name in fallbacks:
            if fallback_name not in self._providers:
                logger.debug(f"Fallback {fallback_name} not configured, skipping")
                continue

            if self._circuit_breaker.is_open(fallback_name):
                logger.debug(f"Fallback {fallback_name} circuit breaker open, skipping")
                continue

            try:
                async with self._rate_limiter.limit(fallback_name):
                    provider = self._get_provider(fallback_name)
                    fallback_model = self._guess_fallback_model(fallback_name, primary_model)
                    logger.info(f"Trying fallback: {fallback_name}/{fallback_model}")

                    result = await retry_with_backoff(
                        policy=self._retry_policy,
                        fn=lambda: provider.complete_with_usage(
                            model=fallback_model, messages=messages, **kwargs
                        ),
                        provider_name=fallback_name,
                    )

                    if not result.provider_name:
                        result.provider_name = fallback_name
                    if not result.model:
                        result.model = fallback_model

                    # Record success for fallback
                    self._circuit_breaker.record_success(fallback_name)

                    # Cost + metrics
                    full_model = f"{fallback_name}/{fallback_model}"
                    if self._cost_tracker and result.total_tokens > 0:
                        self._cost_tracker.record(
                            model=full_model,
                            prompt_tokens=result.prompt_tokens,
                            completion_tokens=result.completion_tokens,
                            session_id=session_id,
                            worker_id=worker_id,
                        )

                    self._metrics.record_tokens(
                        provider=fallback_name,
                        model=fallback_model,
                        prompt_tokens=result.prompt_tokens,
                        completion_tokens=result.completion_tokens,
                        worker_id=worker_id,
                        session_id=session_id,
                    )

                    return result

            except Exception as fallback_err:
                self._circuit_breaker.record_failure(fallback_name)
                errors.append(f"{fallback_name}: {fallback_err}")
                logger.warning(f"Fallback {fallback_name} also failed: {fallback_err}")
                continue

        # All fallbacks exhausted
        raise AllProvidersFailedError(
            provider=failed_provider,
            fallbacks=fallbacks,
            errors=errors,
        )

    def _guess_fallback_model(self, fallback_provider: str, original_model: str) -> str:
        """Guess an appropriate model name for a fallback provider."""
        defaults = {
            "anthropic": "claude-sonnet-4-6",
            "google": "gemini-2.5-pro",
            "deepseek": "deepseek-v3-2",
            "minimax": "minimax-m2-7",
            "openai": "gpt-4o",
            "xai": "grok-3",
            "ollama": "llama3",
            "meta": "llama-3.3-70b",
        }
        return defaults.get(fallback_provider, original_model)

    async def complete_stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream a chat completion response."""
        provider_name, model_name = self._parse_model(model)

        # Check circuit breaker
        if self._circuit_breaker.is_open(provider_name):
            # Fall back to non-streaming with fallback provider
            result = await self._try_fallbacks_with_usage(
                primary_model=model_name,
                messages=messages,
                failed_provider=provider_name,
                **kwargs,
            )
            yield result.content
            return

        try:
            async with self._rate_limiter.limit(provider_name):
                provider = self._get_provider(provider_name)
                async for chunk in provider.complete_stream(model=model_name, messages=messages, **kwargs):
                    yield chunk
                self._circuit_breaker.record_success(provider_name)
        except Exception as e:
            self._circuit_breaker.record_failure(provider_name)
            raise

    @property
    def configured_providers(self) -> list[str]:
        return list(self._providers.keys())

    def get_rate_limit_status(self) -> dict[str, Any]:
        """Get rate limit status for all configured providers."""
        return self._rate_limiter.get_status()

    def get_circuit_breaker_status(self) -> dict[str, Any]:
        """Get circuit breaker status for all providers."""
        return self._circuit_breaker.get_status()

    def get_cost_report(self) -> dict[str, Any]:
        """Get cost report if cost tracker is configured."""
        if self._cost_tracker:
            return self._cost_tracker.get_report()
        return {}

    def get_metrics_summary(self) -> dict[str, Any]:
        """Get metrics summary."""
        return self._metrics.get_summary()
