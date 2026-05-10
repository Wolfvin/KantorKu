"""
Retry — Exponential backoff retry for LLM provider calls.

Retries transient failures (timeouts, 5xx errors, rate limits)
with exponential backoff and jitter. Non-retryable errors
(auth failures, 4xx client errors) are not retried.

Usage:
    from kantorku.providers.retry import RetryPolicy, retry_with_backoff

    policy = RetryPolicy(max_retries=3, base_delay=1.0, max_delay=30.0)

    response = await retry_with_backoff(
        policy,
        lambda: provider.complete(model, messages),
        provider_name="anthropic",
    )
"""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Type

from kantorku.errors import (
    ProviderAuthError,
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)

logger = logging.getLogger("kantorku.retry")


@dataclass
class RetryPolicy:
    """
    Configuration for retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts (0 = no retries)
        base_delay: Initial delay in seconds before first retry
        max_delay: Maximum delay between retries in seconds
        exponential_base: Multiplier for exponential backoff
        jitter: Whether to add random jitter to delays
        retryable_errors: Exception types that should trigger a retry
    """

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_errors: tuple[Type[Exception], ...] = (
        ProviderTimeoutError,
        ProviderRateLimitError,
        ProviderError,
        ConnectionError,
        TimeoutError,
        asyncio.TimeoutError,
    )

    def compute_delay(self, attempt: int) -> float:
        """
        Compute delay for the given retry attempt (0-indexed).

        Uses exponential backoff: base_delay * exponential_base^attempt
        With optional jitter: ±25% of the computed delay
        Capped at max_delay.
        """
        delay = self.base_delay * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay)

        if self.jitter:
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)

        return max(0, delay)

    def is_retryable(self, error: Exception) -> bool:
        """
        Determine if an error should be retried.

        Auth errors and 4xx client errors are NOT retryable.
        Timeouts, rate limits, and connection errors ARE retryable.
        """
        # Auth errors: never retry
        if isinstance(error, ProviderAuthError):
            return False

        # Rate limit: retry (with backoff)
        if isinstance(error, ProviderRateLimitError):
            return True

        # Check if it's one of the retryable types
        for err_type in self.retryable_errors:
            if isinstance(error, err_type):
                return True

        # Generic exceptions: retry on connection/timeout
        if isinstance(error, (ConnectionError, TimeoutError, asyncio.TimeoutError)):
            return True

        return False


# Default retry policy
DEFAULT_RETRY_POLICY = RetryPolicy()


async def retry_with_backoff(
    policy: RetryPolicy,
    fn: Callable[[], Awaitable[Any]],
    provider_name: str = "",
    on_retry: Callable[[int, float, Exception], Awaitable[None]] | None = None,
) -> Any:
    """
    Execute an async function with retry and exponential backoff.

    Args:
        policy: Retry configuration
        fn: Async function to execute
        provider_name: Provider name for logging
        on_retry: Optional callback called before each retry

    Returns:
        The result of fn() on success

    Raises:
        The last exception if all retries are exhausted
    """
    last_error: Exception | None = None

    for attempt in range(policy.max_retries + 1):
        try:
            return await fn()
        except Exception as e:
            last_error = e

            # Don't retry if this is the last attempt
            if attempt >= policy.max_retries:
                break

            # Don't retry non-retryable errors
            if not policy.is_retryable(e):
                logger.debug(
                    f"Non-retryable error from {provider_name}: "
                    f"{type(e).__name__}: {e}"
                )
                raise

            # Compute backoff delay
            delay = policy.compute_delay(attempt)

            logger.info(
                f"Retry {attempt + 1}/{policy.max_retries} for {provider_name} "
                f"after {delay:.1f}s due to: {type(e).__name__}: {e}"
            )

            # Call retry callback if provided
            if on_retry:
                try:
                    await on_retry(attempt, delay, e)
                except Exception:
                    pass  # Callback errors don't affect retry

            # Wait before retrying
            await asyncio.sleep(delay)

    # All retries exhausted
    if last_error is not None:
        raise last_error

    # Shouldn't reach here, but just in case
    raise RuntimeError("retry_with_backoff: unexpected state")
