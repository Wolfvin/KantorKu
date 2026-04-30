"""
RateLimiter — Token-bucket rate limiter for LLM API calls.

Prevents hitting provider API rate limits by controlling the
rate of outgoing requests. Configurable per-provider.

Supports:
- Requests per second (RPS)
- Concurrent request limits
- Per-provider independent limits
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RateLimitConfig:
    """Rate limit configuration for a single provider."""

    # Maximum requests per second (0 = unlimited)
    rps: float = 0.0
    # Maximum concurrent requests (0 = unlimited)
    max_concurrent: int = 0
    # Burst size — how many requests can fire at once
    burst: int = 5


class TokenBucket:
    """
    Token bucket algorithm for rate limiting.

    Tokens are added at a fixed rate. Each request consumes one token.
    If no tokens are available, the request waits until one is added.
    """

    def __init__(self, rate: float, burst: int = 5) -> None:
        """
        Args:
            rate: Tokens added per second (0 = unlimited)
            burst: Maximum tokens that can accumulate
        """
        self.rate = rate
        self.burst = burst
        self._tokens: float = float(burst)
        self._last_refill: float = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Acquire a token, waiting if necessary."""
        if self.rate <= 0:
            return  # Unlimited

        async with self._lock:
            self._refill()

            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return

        # Not enough tokens — wait for refill
        wait_time = (1.0 - self._tokens) / self.rate
        await asyncio.sleep(wait_time)

        async with self._lock:
            self._refill()
            self._tokens -= 1.0

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.burst, self._tokens + elapsed * self.rate)
        self._last_refill = now


class RateLimiter:
    """
    Per-provider rate limiter for LLM API calls.

    Usage:
        limiter = RateLimiter()
        limiter.configure("anthropic", rps=5.0, max_concurrent=3)
        limiter.configure("deepseek", rps=2.0, max_concurrent=2)

        # Before each API call:
        async with limiter.limit("anthropic"):
            response = await provider.complete(...)
    """

    def __init__(self) -> None:
        self._configs: dict[str, RateLimitConfig] = {}
        self._buckets: dict[str, TokenBucket] = {}
        self._semaphores: dict[str, asyncio.Semaphore] = {}

    def configure(
        self,
        provider: str,
        rps: float = 0.0,
        max_concurrent: int = 0,
        burst: int = 5,
    ) -> None:
        """
        Configure rate limits for a provider.

        Args:
            provider: Provider name (e.g. "anthropic", "deepseek")
            rps: Maximum requests per second (0 = unlimited)
            max_concurrent: Maximum concurrent requests (0 = unlimited)
            burst: Token bucket burst size
        """
        config = RateLimitConfig(rps=rps, max_concurrent=max_concurrent, burst=burst)
        self._configs[provider] = config
        self._buckets[provider] = TokenBucket(rate=rps, burst=burst)
        if max_concurrent > 0:
            self._semaphores[provider] = asyncio.Semaphore(max_concurrent)

    def _get_or_create(self, provider: str) -> None:
        """Ensure provider has rate limit structures (defaults to unlimited)."""
        if provider not in self._configs:
            self.configure(provider)

    def limit(self, provider: str) -> _RateLimitContext:
        """
        Get an async context manager that enforces rate limits.

        Usage:
            async with limiter.limit("anthropic"):
                response = await provider.complete(...)
        """
        self._get_or_create(provider)
        return _RateLimitContext(self, provider)

    def get_status(self) -> dict[str, Any]:
        """Get rate limiter status for all providers."""
        status = {}
        for provider, config in self._configs.items():
            bucket = self._buckets.get(provider)
            sem = self._semaphores.get(provider)
            status[provider] = {
                "rps": config.rps,
                "max_concurrent": config.max_concurrent,
                "available_tokens": bucket._tokens if bucket else 0,
                "semaphore_available": sem._value if sem else -1,
            }
        return status


class _RateLimitContext:
    """Async context manager for rate limiting a single request."""

    def __init__(self, limiter: RateLimiter, provider: str) -> None:
        self.limiter = limiter
        self.provider = provider

    async def __aenter__(self) -> None:
        # Acquire token bucket token (waits if rate exceeded)
        bucket = self.limiter._buckets.get(self.provider)
        if bucket:
            await bucket.acquire()

        # Acquire semaphore (waits if concurrency exceeded)
        sem = self.limiter._semaphores.get(self.provider)
        if sem:
            await sem.acquire()

    async def __aexit__(self, *args: Any) -> None:
        # Release semaphore
        sem = self.limiter._semaphores.get(self.provider)
        if sem:
            sem.release()
