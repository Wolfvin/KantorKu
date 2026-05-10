"""
CircuitBreaker — Protect against cascading provider failures.

When a provider starts failing repeatedly, the circuit breaker "opens"
and stops sending requests to it for a cooldown period. After the
cooldown, it enters "half-open" state and allows one test request.
If that succeeds, the circuit closes. If it fails, the cooldown restarts.

States:
- CLOSED: Normal operation. Requests go through. Failures are counted.
- OPEN: Provider is disabled. All requests fail immediately.
- HALF_OPEN: One test request is allowed. If it succeeds, circuit closes.

Usage:
    cb = CircuitBreaker(failure_threshold=3, reset_timeout_seconds=60)

    if cb.is_open("anthropic"):
        raise ProviderCircuitOpenError("anthropic")

    try:
        result = await provider.complete(...)
        cb.record_success("anthropic")
    except Exception:
        cb.record_failure("anthropic")
"""

from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field
from typing import Any


class CircuitState(enum.Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitStatus:
    """Status of a single provider's circuit breaker."""
    provider: str
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_at: float = 0.0
    last_success_at: float = 0.0
    opened_at: float = 0.0


class CircuitBreaker:
    """
    Circuit breaker for LLM providers.

    Configurable per-provider thresholds for failures before opening,
    and cooldown duration before trying again.

    Usage:
        cb = CircuitBreaker(failure_threshold=3, reset_timeout_seconds=60)

        # Check before calling
        if cb.is_open("anthropic"):
            # Skip this provider, try fallback
            ...

        # After call
        cb.record_success("anthropic")  # or
        cb.record_failure("anthropic")
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        reset_timeout_seconds: float = 60.0,
        half_open_max_calls: int = 1,
    ) -> None:
        """
        Args:
            failure_threshold: Number of consecutive failures before opening circuit
            reset_timeout_seconds: Seconds to wait before allowing a test request
            half_open_max_calls: Number of test requests allowed in half-open state
        """
        self.failure_threshold = failure_threshold
        self.reset_timeout_seconds = reset_timeout_seconds
        self.half_open_max_calls = half_open_max_calls
        self._circuits: dict[str, CircuitStatus] = {}
        self._half_open_calls: dict[str, int] = {}

    def _get_circuit(self, provider: str) -> CircuitStatus:
        if provider not in self._circuits:
            self._circuits[provider] = CircuitStatus(provider=provider)
        return self._circuits[provider]

    def is_open(self, provider: str) -> bool:
        """
        Check if the circuit breaker is open for a provider.

        Returns True if requests should be rejected (circuit is OPEN).
        Also handles state transitions: OPEN → HALF_OPEN after timeout.
        """
        circuit = self._get_circuit(provider)

        if circuit.state == CircuitState.CLOSED:
            return False

        if circuit.state == CircuitState.OPEN:
            # Check if cooldown has elapsed
            elapsed = time.monotonic() - circuit.opened_at
            if elapsed >= self.reset_timeout_seconds:
                # Transition to half-open
                circuit.state = CircuitState.HALF_OPEN
                self._half_open_calls[provider] = 0
                return False
            return True

        if circuit.state == CircuitState.HALF_OPEN:
            # Allow limited test requests
            current_calls = self._half_open_calls.get(provider, 0)
            if current_calls < self.half_open_max_calls:
                return False
            return True

        return False

    def record_success(self, provider: str) -> None:
        """
        Record a successful call. Closes the circuit if it was half-open.
        Resets failure count.
        """
        circuit = self._get_circuit(provider)
        circuit.success_count += 1
        circuit.last_success_at = time.monotonic()
        circuit.failure_count = 0  # Reset on success

        if circuit.state == CircuitState.HALF_OPEN:
            # Test request succeeded → close circuit
            circuit.state = CircuitState.CLOSED

    def record_failure(self, provider: str) -> None:
        """
        Record a failed call. Opens the circuit if failure threshold is reached.
        """
        circuit = self._get_circuit(provider)
        circuit.failure_count += 1
        circuit.last_failure_at = time.monotonic()

        if circuit.state == CircuitState.HALF_OPEN:
            # Test request failed → re-open circuit
            circuit.state = CircuitState.OPEN
            circuit.opened_at = time.monotonic()

        elif circuit.state == CircuitState.CLOSED:
            if circuit.failure_count >= self.failure_threshold:
                # Threshold reached → open circuit
                circuit.state = CircuitState.OPEN
                circuit.opened_at = time.monotonic()

    def get_status(self) -> dict[str, Any]:
        """Get status of all circuit breakers."""
        result = {}
        for provider, circuit in self._circuits.items():
            result[provider] = {
                "state": circuit.state.value,
                "failure_count": circuit.failure_count,
                "success_count": circuit.success_count,
                "last_failure_at": circuit.last_failure_at,
                "last_success_at": circuit.last_success_at,
            }
            if circuit.state == CircuitState.OPEN:
                elapsed = time.monotonic() - circuit.opened_at
                result[provider]["resets_in_seconds"] = max(
                    0, self.reset_timeout_seconds - elapsed
                )
        return result

    def reset(self, provider: str) -> None:
        """Manually reset a circuit breaker for a provider."""
        if provider in self._circuits:
            self._circuits[provider].state = CircuitState.CLOSED
            self._circuits[provider].failure_count = 0

    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for provider in self._circuits:
            self.reset(provider)
