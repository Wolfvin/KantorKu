"""
errors — Structured error hierarchy for kantorku.

All kantorku-specific exceptions inherit from KantorkuError.
This enables:
- Programmatic error handling (catch specific types)
- Structured error reporting (error code + context)
- Consistent error propagation across the framework

Usage:
    from kantorku.errors import KantorkuError, ProviderError, WorkerError

    try:
        result = await office.run("Build X")
    except ProviderError as e:
        print(f"Provider {e.provider} failed: {e}")
    except KantorkuError as e:
        print(f"Kantorku error: {e.code} — {e}")
"""

from __future__ import annotations

from typing import Any


class KantorkuError(Exception):
    """
    Base exception for all kantorku errors.

    Every kantorku error has:
    - code: Machine-readable error code (e.g. "PROVIDER_TIMEOUT")
    - message: Human-readable description
    - context: Optional dict with additional details

    Usage:
        raise KantorkuError("OFFICE_NOT_INITIALIZED", "Office must be initialized first")
    """

    def __init__(
        self,
        code: str,
        message: str = "",
        context: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message or code
        self.context = context or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "context": self.context,
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self.code!r}, message={self.message!r})"


# ── Provider Errors ────────────────────────────────────────────────


class ProviderError(KantorkuError):
    """Error from an LLM provider (API call failed)."""

    def __init__(
        self,
        provider: str,
        message: str = "",
        model: str = "",
        status_code: int | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        ctx = context or {}
        ctx["provider"] = provider
        if model:
            ctx["model"] = model
        if status_code:
            ctx["status_code"] = status_code
        super().__init__(
            code="PROVIDER_ERROR",
            message=message or f"Provider {provider} failed",
            context=ctx,
        )
        self.provider = provider
        self.model = model
        self.status_code = status_code


class ProviderTimeoutError(ProviderError):
    """Provider call timed out."""

    def __init__(self, provider: str, timeout_seconds: float = 0, **kwargs: Any) -> None:
        ctx = kwargs.pop("context", {})
        ctx["timeout_seconds"] = timeout_seconds
        super().__init__(
            provider=provider,
            message=f"Provider {provider} timed out after {timeout_seconds}s",
            context=ctx,
            **kwargs,
        )
        self.code = "PROVIDER_TIMEOUT"


class ProviderRateLimitError(ProviderError):
    """Provider rate limit exceeded."""

    def __init__(self, provider: str, retry_after: float = 0, **kwargs: Any) -> None:
        ctx = kwargs.pop("context", {})
        ctx["retry_after"] = retry_after
        super().__init__(
            provider=provider,
            message=f"Provider {provider} rate limit exceeded, retry after {retry_after}s",
            context=ctx,
            **kwargs,
        )
        self.code = "PROVIDER_RATE_LIMIT"


class ProviderAuthError(ProviderError):
    """Provider authentication failed (bad API key)."""

    def __init__(self, provider: str, **kwargs: Any) -> None:
        super().__init__(
            provider=provider,
            message=f"Provider {provider} authentication failed — check API key",
            **kwargs,
        )
        self.code = "PROVIDER_AUTH"


class ProviderCircuitOpenError(ProviderError):
    """Circuit breaker is open — provider is temporarily disabled."""

    def __init__(self, provider: str, reset_at: float = 0, **kwargs: Any) -> None:
        ctx = kwargs.pop("context", {})
        ctx["reset_at"] = reset_at
        super().__init__(
            provider=provider,
            message=f"Circuit breaker open for {provider}, retry after reset",
            context=ctx,
            **kwargs,
        )
        self.code = "PROVIDER_CIRCUIT_OPEN"


class AllProvidersFailedError(KantorkuError):
    """Primary provider and all fallbacks failed."""

    def __init__(
        self,
        provider: str,
        fallbacks: list[str] | None = None,
        errors: list[str] | None = None,
    ) -> None:
        super().__init__(
            code="ALL_PROVIDERS_FAILED",
            message=f"Provider {provider} and all fallbacks failed",
            context={
                "provider": provider,
                "fallbacks": fallbacks or [],
                "errors": errors or [],
            },
        )


# ── Worker Errors ──────────────────────────────────────────────────


class WorkerError(KantorkuError):
    """Error from a worker."""

    def __init__(
        self,
        worker_id: str,
        message: str = "",
        context: dict[str, Any] | None = None,
    ) -> None:
        ctx = context or {}
        ctx["worker_id"] = worker_id
        super().__init__(
            code="WORKER_ERROR",
            message=message or f"Worker {worker_id} failed",
            context=ctx,
        )
        self.worker_id = worker_id


class WorkerTimeoutError(WorkerError):
    """Worker task execution timed out."""

    def __init__(self, worker_id: str, timeout_seconds: float = 0) -> None:
        super().__init__(
            worker_id=worker_id,
            message=f"Worker {worker_id} timed out after {timeout_seconds}s",
            context={"timeout_seconds": timeout_seconds},
        )
        self.code = "WORKER_TIMEOUT"


class WorkerNotReadyError(WorkerError):
    """Worker is not in a ready state to accept tasks."""

    def __init__(self, worker_id: str, current_status: str = "") -> None:
        super().__init__(
            worker_id=worker_id,
            message=f"Worker {worker_id} not ready (status: {current_status})",
            context={"current_status": current_status},
        )
        self.code = "WORKER_NOT_READY"


# ── Office Errors ──────────────────────────────────────────────────


class OfficeError(KantorkuError):
    """Error from the Office orchestrator."""

    def __init__(self, message: str = "", context: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="OFFICE_ERROR",
            message=message,
            context=context,
        )


class OfficeNotInitializedError(OfficeError):
    """Office was used before initialize() was called."""

    def __init__(self) -> None:
        super().__init__(
            message="Office must be initialized first — call await office.initialize()",
        )
        self.code = "OFFICE_NOT_INITIALIZED"


class ContractError(OfficeError):
    """Contract-related error."""

    def __init__(self, message: str, session_id: str = "") -> None:
        super().__init__(
            message=message,
            context={"session_id": session_id},
        )
        self.code = "CONTRACT_ERROR"


class NoContractError(ContractError):
    """No contract found for a session."""

    def __init__(self, session_id: str) -> None:
        super().__init__(
            message=f"No contract found for session {session_id}",
            session_id=session_id,
        )
        self.code = "NO_CONTRACT"


# ── Config Errors ──────────────────────────────────────────────────


class ConfigError(KantorkuError):
    """Configuration error."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="CONFIG_ERROR",
            message=message,
            context=context,
        )


class WorkerNotFoundError(KantorkuError):
    """Requested worker not found in registry."""

    def __init__(self, worker_id: str, available: list[str] | None = None) -> None:
        super().__init__(
            code="WORKER_NOT_FOUND",
            message=f"Worker '{worker_id}' not found",
            context={"worker_id": worker_id, "available": available or []},
        )
