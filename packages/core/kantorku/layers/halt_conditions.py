"""
Halt Conditions — O18: Monitor and enforce halt/pause conditions.

Tracks session metrics (consecutive failures, cost overruns,
quality regressions) and determines when to halt, pause, or
continue execution.

Like a safety officer who pulls the emergency stop when things
go wrong too many times.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class HaltStatus(Enum):
    """Possible halt statuses for a session."""
    CONTINUE = "continue"
    PAUSE_NOTIFY = "pause_notify"
    HALT_REPLAN = "halt_replan"


@dataclass
class HaltConfig:
    """Configuration for halt condition thresholds."""
    max_consecutive_failures: int = 2
    max_cost_overrun_pct: float = 50.0
    max_quality_regressions: int = 2


@dataclass
class SessionCounters:
    """Counters tracked per session for halt detection."""
    consecutive_failures: int = 0
    cost_overruns: int = 0
    quality_regressions: int = 0
    last_failure_time: float = 0.0
    last_overrun_time: float = 0.0
    last_regression_time: float = 0.0


class HaltMonitor:
    """
    Halt Monitor — track and enforce halt conditions.

    Thread-safe monitor that tracks per-session metrics and
    determines when execution should halt, pause, or continue.

    Conditions:
    - Consecutive failures → HALT_REPLAN when threshold exceeded
    - Cost overruns → PAUSE_NOTIFY when over budget
    - Quality regressions → HALT_REPLAN when too many regressions

    Usage:
        monitor = HaltMonitor()
        monitor.record_failure("sess-1", "worker_1", "TypeError")
        monitor.record_cost_overrun("sess-1", 100, 200)
        status = monitor.check_execution("sess-1")
        if status == HaltStatus.HALT_REPLAN:
            report = monitor.generate_halt_report("failures", evidence)
    """

    def __init__(self, config: HaltConfig | None = None) -> None:
        self._config = config or HaltConfig()
        self._sessions: dict[str, SessionCounters] = {}
        self._lock = threading.Lock()

    def _get_or_create_counters(self, session_id: str) -> SessionCounters:
        """Get or create session counters (thread-safe)."""
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionCounters()
        return self._sessions[session_id]

    def check_execution(
        self, session_id: str, session_metrics: dict[str, Any] | None = None
    ) -> HaltStatus:
        """
        Check if execution should continue, pause, or halt.

        Args:
            session_id: Session identifier
            session_metrics: Optional additional metrics to consider

        Returns:
            HaltStatus indicating the recommended action
        """
        with self._lock:
            counters = self._get_or_create_counters(session_id)

        # Check consecutive failures
        if counters.consecutive_failures >= self._config.max_consecutive_failures:
            return HaltStatus.HALT_REPLAN

        # Check quality regressions
        if counters.quality_regressions >= self._config.max_quality_regressions:
            return HaltStatus.HALT_REPLAN

        # Check cost overruns
        if counters.cost_overruns > 0:
            return HaltStatus.PAUSE_NOTIFY

        # Check additional metrics if provided
        if session_metrics:
            failure_count = session_metrics.get("failure_count", 0)
            if failure_count >= self._config.max_consecutive_failures:
                return HaltStatus.HALT_REPLAN

            cost_pct = session_metrics.get("cost_overrun_pct", 0.0)
            if cost_pct > self._config.max_cost_overrun_pct:
                return HaltStatus.PAUSE_NOTIFY

        return HaltStatus.CONTINUE

    def record_failure(
        self, session_id: str, worker_id: str, error: str
    ) -> SessionCounters:
        """
        Record a task failure for a session.

        Args:
            session_id: Session identifier
            worker_id: Worker that failed
            error: Error description

        Returns:
            Updated SessionCounters
        """
        with self._lock:
            counters = self._get_or_create_counters(session_id)
            counters.consecutive_failures += 1
            counters.last_failure_time = time.time()

        return counters

    def record_cost_overrun(
        self, session_id: str, budget: float, actual: float
    ) -> SessionCounters:
        """
        Record a cost overrun for a session.

        Args:
            session_id: Session identifier
            budget: Budgeted cost
            actual: Actual cost

        Returns:
            Updated SessionCounters
        """
        with self._lock:
            counters = self._get_or_create_counters(session_id)
            if budget > 0:
                overrun_pct = ((actual - budget) / budget) * 100
                if overrun_pct > self._config.max_cost_overrun_pct:
                    counters.cost_overruns += 1
                    counters.last_overrun_time = time.time()

        return counters

    def record_quality_regression(
        self, session_id: str, before_score: float, after_score: float
    ) -> SessionCounters:
        """
        Record a quality regression for a session.

        Args:
            session_id: Session identifier
            before_score: Quality score before change
            after_score: Quality score after change

        Returns:
            Updated SessionCounters
        """
        with self._lock:
            counters = self._get_or_create_counters(session_id)
            if after_score < before_score:
                counters.quality_regressions += 1
                counters.last_regression_time = time.time()

        return counters

    def reset(self, session_id: str) -> None:
        """
        Clear all counters for a session.

        Args:
            session_id: Session identifier
        """
        with self._lock:
            self._sessions.pop(session_id, None)

    def generate_halt_report(
        self, reason: str, evidence: dict[str, Any]
    ) -> str:
        """
        Generate a markdown halt report.

        Args:
            reason: The reason for halting
            evidence: Evidence supporting the halt decision

        Returns:
            Markdown formatted halt report
        """
        evidence_lines = ""
        for key, value in (evidence or {}).items():
            evidence_lines += f"| {key} | {value} |\n"

        session_id = evidence.get("session_id", "unknown")
        counters = self._sessions.get(str(session_id))

        counters_section = ""
        if counters:
            counters_section = (
                f"## Session Counters\n\n"
                f"- Consecutive failures: {counters.consecutive_failures}\n"
                f"- Cost overruns: {counters.cost_overruns}\n"
                f"- Quality regressions: {counters.quality_regressions}\n"
            )

        return (
            f"# HALT Report\n\n"
            f"**Reason:** {reason}\n\n"
            f"**Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"## Evidence\n\n"
            f"| Key | Value |\n"
            f"|-----|-------|\n"
            f"{evidence_lines if evidence_lines else '| — | — |\n'}\n"
            f"{counters_section}\n"
            f"## Recommended Action\n\n"
            f"Stop execution and replan. Review the failures and adjust the approach "
            f"before resuming.\n"
        )

    def get_session_status(self, session_id: str) -> dict[str, Any] | None:
        """
        Get the current counter status for a session.

        Args:
            session_id: Session identifier

        Returns:
            Dict with counter values, or None if session not tracked
        """
        counters = self._sessions.get(session_id)
        if not counters:
            return None
        return {
            "session_id": session_id,
            "consecutive_failures": counters.consecutive_failures,
            "cost_overruns": counters.cost_overruns,
            "quality_regressions": counters.quality_regressions,
            "halt_status": self.check_execution(session_id).value,
        }
