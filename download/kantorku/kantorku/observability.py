"""
Observability — Structured logging, tracing, and metrics for kantorku.

Provides:
- Structured JSON logging with context
- Span-based tracing (OpenTelemetry-compatible format)
- Per-session metrics collection
- Optional OpenTelemetry export

Usage:
    from kantorku.observability import get_tracer, Metrics

    tracer = get_tracer()

    with tracer.span("conduct", attributes={"session_id": "abc"}) as span:
        # ... do work ...
        span.set_attribute("workers_used", 3)
        span.add_event("task_completed", {"worker": "coder_backend"})

    metrics = Metrics()
    metrics.record_tokens("anthropic", 1500, 800)
    metrics.record_duration("coder_backend", 2.5)
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator


# ── Structured Logging ──────────────────────────────────────────────


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields
        for key in ("session_id", "worker_id", "task_id", "span_id", "trace_id"):
            value = getattr(record, key, None)
            if value:
                log_entry[key] = value

        # Add exception info
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def setup_logging(level: int = logging.INFO, json_format: bool = False) -> None:
    """
    Configure kantorku logging.

    Args:
        level: Logging level
        json_format: If True, use JSON structured logging
    """
    logger = logging.getLogger("kantorku")
    logger.setLevel(level)

    handler = logging.StreamHandler()
    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )

    logger.addHandler(handler)


# ── Tracing ──────────────────────────────────────────────────────────


@dataclass
class SpanEvent:
    """An event within a span."""
    name: str
    timestamp: float
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class Span:
    """
    A tracing span — represents a unit of work.

    Compatible with OpenTelemetry span format for future export.
    """
    name: str
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:32])
    parent_id: str = ""
    start_time: float = field(default_factory=time.monotonic)
    end_time: float = 0.0
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[SpanEvent] = field(default_factory=list)
    status: str = "ok"  # ok | error

    def set_attribute(self, key: str, value: Any) -> None:
        """Set a span attribute."""
        self.attributes[key] = value

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        """Add an event to the span."""
        self.events.append(SpanEvent(
            name=name,
            timestamp=time.monotonic(),
            attributes=attributes or {},
        ))

    def set_status(self, status: str) -> None:
        """Set span status (ok or error)."""
        self.status = status

    @property
    def duration_ms(self) -> float:
        """Span duration in milliseconds."""
        end = self.end_time or time.monotonic()
        return (end - self.start_time) * 1000

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for serialization."""
        return {
            "name": self.name,
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_id": self.parent_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "attributes": self.attributes,
            "events": [
                {"name": e.name, "timestamp": e.timestamp, "attributes": e.attributes}
                for e in self.events
            ],
        }


class Tracer:
    """
    Simple tracer for kantorku — creates and manages spans.

    Not full OpenTelemetry SDK, but compatible format for future
    migration. Spans are stored in-memory and can be exported.

    Usage:
        tracer = get_tracer()

        with tracer.span("conduct", attributes={"session_id": "abc"}) as span:
            span.add_event("task_started", {"worker": "coder_backend"})
            # ... do work ...
    """

    def __init__(self) -> None:
        self._spans: list[Span] = []
        self._active_spans: list[Span] = []
        self._logger = logging.getLogger("kantorku.tracer")

    @contextmanager
    def span(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
    ) -> Generator[Span, None, None]:
        """
        Create a new span as a context manager.

        Args:
            name: Span name (e.g. "conduct", "worker.execute")
            attributes: Optional initial attributes

        Yields:
            The Span object
        """
        parent_id = self._active_spans[-1].span_id if self._active_spans else ""
        trace_id = self._active_spans[-1].trace_id if self._active_spans else uuid.uuid4().hex[:32]

        s = Span(name=name, parent_id=parent_id, trace_id=trace_id)
        if attributes:
            s.attributes.update(attributes)

        self._spans.append(s)
        self._active_spans.append(s)

        self._logger.debug(f"Span started: {name} ({s.span_id})")

        try:
            yield s
            s.status = "ok"
        except Exception as e:
            s.status = "error"
            s.set_attribute("error.type", type(e).__name__)
            s.set_attribute("error.message", str(e))
            raise
        finally:
            s.end_time = time.monotonic()
            self._active_spans.pop()
            self._logger.debug(
                f"Span ended: {name} ({s.span_id}) duration={s.duration_ms:.1f}ms"
            )

    def get_spans(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent spans as dicts."""
        return [s.to_dict() for s in self._spans[-limit:]]

    def get_trace(self, trace_id: str) -> list[dict[str, Any]]:
        """Get all spans for a trace."""
        return [s.to_dict() for s in self._spans if s.trace_id == trace_id]

    def clear(self) -> None:
        """Clear all stored spans."""
        self._spans.clear()


# Global tracer singleton
_tracer: Tracer | None = None


def get_tracer() -> Tracer:
    """Get the global tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = Tracer()
    return _tracer


# ── Metrics ──────────────────────────────────────────────────────────


@dataclass
class MetricsRecord:
    """A single metrics record."""
    timestamp: float = field(default_factory=time.time)
    provider: str = ""
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    duration_seconds: float = 0.0
    worker_id: str = ""
    session_id: str = ""
    status: str = "ok"


class Metrics:
    """
    Collect and query usage metrics.

    Tracks token usage, costs, durations, and success rates
    per provider, model, worker, and session.

    Usage:
        metrics = get_metrics()

        # Record a call
        metrics.record_tokens("anthropic", "claude-opus-4-6", 1500, 800)
        metrics.record_duration("coder_backend", 2.5)

        # Query
        summary = metrics.get_summary()
    """

    def __init__(self) -> None:
        self._records: list[MetricsRecord] = []

    def record_tokens(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        worker_id: str = "",
        session_id: str = "",
    ) -> None:
        """Record token usage for an LLM call."""
        self._records.append(MetricsRecord(
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            worker_id=worker_id,
            session_id=session_id,
        ))

    def record_duration(
        self,
        worker_id: str,
        duration_seconds: float,
        session_id: str = "",
        status: str = "ok",
    ) -> None:
        """Record task execution duration."""
        self._records.append(MetricsRecord(
            worker_id=worker_id,
            duration_seconds=duration_seconds,
            session_id=session_id,
            status=status,
        ))

    def get_summary(self) -> dict[str, Any]:
        """Get aggregate metrics summary."""
        total_prompt = sum(r.prompt_tokens for r in self._records)
        total_completion = sum(r.completion_tokens for r in self._records)
        total_tokens = sum(r.total_tokens for r in self._records)

        by_provider: dict[str, dict[str, int]] = {}
        for r in self._records:
            if r.provider not in by_provider:
                by_provider[r.provider] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "calls": 0}
            by_provider[r.provider]["prompt_tokens"] += r.prompt_tokens
            by_provider[r.provider]["completion_tokens"] += r.completion_tokens
            by_provider[r.provider]["total_tokens"] += r.total_tokens
            by_provider[r.provider]["calls"] += 1

        by_worker: dict[str, dict[str, Any]] = {}
        for r in self._records:
            if r.worker_id not in by_worker:
                by_worker[r.worker_id] = {"calls": 0, "total_duration": 0.0, "total_tokens": 0}
            by_worker[r.worker_id]["calls"] += 1
            by_worker[r.worker_id]["total_duration"] += r.duration_seconds
            by_worker[r.worker_id]["total_tokens"] += r.total_tokens

        success_count = sum(1 for r in self._records if r.status == "ok")
        failure_count = sum(1 for r in self._records if r.status == "error")

        return {
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "total_tokens": total_tokens,
            "total_calls": len(self._records),
            "success_rate": success_count / max(1, len(self._records)),
            "by_provider": by_provider,
            "by_worker": by_worker,
        }

    def get_session_metrics(self, session_id: str) -> dict[str, Any]:
        """Get metrics for a specific session."""
        session_records = [r for r in self._records if r.session_id == session_id]
        return {
            "session_id": session_id,
            "total_tokens": sum(r.total_tokens for r in session_records),
            "total_calls": len(session_records),
            "total_duration": sum(r.duration_seconds for r in session_records),
        }

    def clear(self) -> None:
        """Clear all metrics records."""
        self._records.clear()


# Global metrics singleton
_metrics: Metrics | None = None


def get_metrics() -> Metrics:
    """Get the global metrics instance."""
    global _metrics
    if _metrics is None:
        _metrics = Metrics()
    return _metrics
