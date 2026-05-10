"""
Worker Evolve Engine — O11: Continuous worker performance improvement.

Monitors worker health metrics, detects signals of degradation or
improvement opportunity, proposes and executes evolve actions,
and maintains a state machine with halt conditions.

Like a team lead who keeps an eye on team performance and suggests
training, tools, or role changes when needed.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class EvolveActionType(Enum):
    """Types of actions the evolve engine can propose."""
    RETUNE_PROMPT = "retune_prompt"
    UPGRADE_MODEL = "upgrade_model"
    FLAG_FOR_REVIEW = "flag_for_review"
    SUGGEST_REPLACEMENT = "suggest_replacement"


@dataclass
class WorkerHealth:
    """Health metrics for a worker."""
    success_rate: float = 1.0
    avg_duration: float = 0.0
    token_efficiency: float = 1.0
    failure_rate: float = 0.0
    last_updated: float = field(default_factory=time.time)


@dataclass
class EvolveSignal:
    """A signal detected from worker health metrics."""
    worker_id: str = ""
    signal_type: str = ""
    severity: str = "low"
    description: str = ""


@dataclass
class EvolveAction:
    """A proposed or executed evolve action."""
    worker_id: str = ""
    action_type: EvolveActionType = EvolveActionType.FLAG_FOR_REVIEW
    rationale: str = ""
    risk_level: str = "low"


# Signal detection thresholds
_FAILURE_RATE_THRESHOLD = 0.3
_SUCCESS_RATE_THRESHOLD = 0.7
_TOKEN_EFFICIENCY_THRESHOLD = 0.5
_AVG_DURATION_THRESHOLD = 60.0  # seconds

# State file path
_DEFAULT_STATE_PATH = "evolve_state.json"


class WorkerEvolveEngine:
    """
    Worker Evolve Engine — continuous worker performance improvement.

    Monitors worker health, detects signals, proposes actions, and
    executes them safely with backup, apply, verify steps.

    Includes a state machine with halt conditions (2 consecutive
    regressions stop auto-evolution for that worker).

    Usage:
        engine = WorkerEvolveEngine()
        health = engine.measure_worker_health("coder_backend", metrics_data)
        signals = engine.detect_signals("coder_backend", health)
        action = engine.propose_action("coder_backend", signals)
        result = engine.execute_action("coder_backend", action)
    """

    def __init__(self, state_path: str | Path | None = None) -> None:
        self._state_path = Path(state_path or _DEFAULT_STATE_PATH)
        self._state: dict[str, Any] = self._load_state()
        self._regression_count: dict[str, int] = {}

    def _load_state(self) -> dict[str, Any]:
        """Load evolve state from disk."""
        try:
            if self._state_path.exists():
                with open(self._state_path, "r") as f:
                    return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
        return {"workers": {}, "history": []}

    def _save_state(self) -> None:
        """Persist evolve state to disk."""
        try:
            with open(self._state_path, "w") as f:
                json.dump(self._state, f, indent=2, default=str)
        except OSError:
            pass

    def measure_worker_health(
        self, worker_id: str, metrics_data: dict[str, Any]
    ) -> WorkerHealth:
        """
        Calculate health metrics for a worker from raw metrics data.

        Args:
            worker_id: The worker to measure
            metrics_data: Raw metrics dict with keys like
                'total_tasks', 'successful_tasks', 'failed_tasks',
                'total_duration', 'total_tokens', 'total_output_tokens'

        Returns:
            WorkerHealth with calculated metrics
        """
        if not metrics_data:
            return WorkerHealth(last_updated=time.time())

        total = metrics_data.get("total_tasks", 0)
        successful = metrics_data.get("successful_tasks", 0)
        failed = metrics_data.get("failed_tasks", 0)
        total_duration = metrics_data.get("total_duration", 0.0)
        total_tokens = metrics_data.get("total_tokens", 0)
        output_tokens = metrics_data.get("total_output_tokens", 0)

        success_rate = (successful / total) if total > 0 else 1.0
        failure_rate = (failed / total) if total > 0 else 0.0
        avg_duration = (total_duration / total) if total > 0 else 0.0
        token_efficiency = (output_tokens / total_tokens) if total_tokens > 0 else 1.0

        health = WorkerHealth(
            success_rate=success_rate,
            avg_duration=avg_duration,
            token_efficiency=token_efficiency,
            failure_rate=failure_rate,
            last_updated=time.time(),
        )

        # Store in state
        if "workers" not in self._state:
            self._state["workers"] = {}
        self._state["workers"][worker_id] = {
            "health": {
                "success_rate": success_rate,
                "avg_duration": avg_duration,
                "token_efficiency": token_efficiency,
                "failure_rate": failure_rate,
            },
            "last_updated": health.last_updated,
        }
        self._save_state()

        return health

    def detect_signals(
        self, worker_id: str, health: WorkerHealth
    ) -> list[EvolveSignal]:
        """
        Detect evolve signals from worker health metrics.

        Looks for degradation patterns that warrant action.

        Args:
            worker_id: The worker to analyze
            health: Current health metrics

        Returns:
            List of EvolveSignal instances
        """
        signals: list[EvolveSignal] = []

        # High failure rate
        if health.failure_rate >= _FAILURE_RATE_THRESHOLD:
            signals.append(EvolveSignal(
                worker_id=worker_id,
                signal_type="high_failure_rate",
                severity="high",
                description=f"Failure rate {health.failure_rate:.1%} meets/exceeds threshold {_FAILURE_RATE_THRESHOLD:.1%}",
            ))

        # Low success rate
        if health.success_rate <= _SUCCESS_RATE_THRESHOLD:
            signals.append(EvolveSignal(
                worker_id=worker_id,
                signal_type="low_success_rate",
                severity="high",
                description=f"Success rate {health.success_rate:.1%} at/below threshold {_SUCCESS_RATE_THRESHOLD:.1%}",
            ))

        # Poor token efficiency
        if health.token_efficiency <= _TOKEN_EFFICIENCY_THRESHOLD:
            signals.append(EvolveSignal(
                worker_id=worker_id,
                signal_type="poor_token_efficiency",
                severity="medium",
                description=f"Token efficiency {health.token_efficiency:.2f} at/below threshold {_TOKEN_EFFICIENCY_THRESHOLD:.2f}",
            ))

        # Slow execution
        if health.avg_duration >= _AVG_DURATION_THRESHOLD:
            signals.append(EvolveSignal(
                worker_id=worker_id,
                signal_type="slow_execution",
                severity="low",
                description=f"Average duration {health.avg_duration:.1f}s exceeds threshold {_AVG_DURATION_THRESHOLD:.1f}s",
            ))

        # Perfect health signal
        if not signals and health.success_rate >= 0.9 and health.failure_rate <= 0.1:
            signals.append(EvolveSignal(
                worker_id=worker_id,
                signal_type="healthy",
                severity="info",
                description="Worker performing well — no action needed",
            ))

        return signals

    def propose_action(
        self, worker_id: str, signals: list[EvolveSignal]
    ) -> EvolveAction:
        """
        Propose an evolve action based on detected signals.

        Prioritizes actions by signal severity and type.

        Args:
            worker_id: The worker to propose action for
            signals: Detected signals

        Returns:
            EvolveAction with proposed action

        Raises:
            None — returns FLAG_FOR_REVIEW if uncertain
        """
        if not signals:
            return EvolveAction(
                worker_id=worker_id,
                action_type=EvolveActionType.FLAG_FOR_REVIEW,
                rationale="No signals detected — flag for periodic review",
                risk_level="low",
            )

        # Check halt condition: 2 consecutive regressions
        if self._regression_count.get(worker_id, 0) >= 2:
            return EvolveAction(
                worker_id=worker_id,
                action_type=EvolveActionType.FLAG_FOR_REVIEW,
                rationale="Halted: 2 consecutive regressions detected — manual review required",
                risk_level="high",
            )

        # Find highest severity signal
        high_signals = [s for s in signals if s.severity == "high"]
        medium_signals = [s for s in signals if s.severity == "medium"]

        if high_signals:
            signal_types = {s.signal_type for s in high_signals}
            if "high_failure_rate" in signal_types or "low_success_rate" in signal_types:
                return EvolveAction(
                    worker_id=worker_id,
                    action_type=EvolveActionType.RETUNE_PROMPT,
                    rationale=f"High severity signals: {', '.join(s.signal_type for s in high_signals)} — retune prompt",
                    risk_level="medium",
                )

        if medium_signals:
            signal_types = {s.signal_type for s in medium_signals}
            if "poor_token_efficiency" in signal_types:
                return EvolveAction(
                    worker_id=worker_id,
                    action_type=EvolveActionType.UPGRADE_MODEL,
                    rationale="Poor token efficiency — consider upgrading model",
                    risk_level="medium",
                )
            return EvolveAction(
                worker_id=worker_id,
                action_type=EvolveActionType.RETUNE_PROMPT,
                rationale=f"Medium severity signals: {', '.join(s.signal_type for s in medium_signals)} — retune prompt",
                risk_level="low",
            )

        # Only low/info signals
        return EvolveAction(
            worker_id=worker_id,
            action_type=EvolveActionType.FLAG_FOR_REVIEW,
            rationale="Only low-severity signals — periodic review sufficient",
            risk_level="low",
        )

    def execute_action(
        self, worker_id: str, action: EvolveAction
    ) -> dict[str, Any]:
        """
        Execute an evolve action safely with backup, apply, verify.

        Steps:
        1. Backup current state
        2. Apply action
        3. Verify (check if action caused regression)
        4. Rollback if regression detected

        Args:
            worker_id: The worker to evolve
            action: The EvolveAction to execute

        Returns:
            Result dict with success status and details
        """
        result: dict[str, Any] = {
            "worker_id": worker_id,
            "action_type": action.action_type.value,
            "status": "pending",
            "backup_created": False,
            "applied": False,
            "verified": False,
            "rolled_back": False,
        }

        # Step 1: Backup current state
        current_state = self._state.get("workers", {}).get(worker_id, {})
        backup = dict(current_state)
        result["backup_created"] = True
        result["backup"] = backup

        # Step 2: Apply action
        applied = self._apply_action(worker_id, action)
        result["applied"] = applied

        if not applied:
            result["status"] = "apply_failed"
            return result

        # Step 3: Verify — check if the action would cause regression
        # In a real system, this would wait for actual results
        # Here we simulate by checking if health improved
        new_health_data = self._state.get("workers", {}).get(worker_id, {}).get("health", {})
        old_health_data = backup.get("health", {})

        verified = True
        if old_health_data:
            old_success = old_health_data.get("success_rate", 1.0)
            new_success = new_health_data.get("success_rate", 1.0)
            if new_success < old_success:
                verified = False
                self._regression_count[worker_id] = self._regression_count.get(worker_id, 0) + 1

        result["verified"] = verified

        # Step 4: Rollback if regression
        if not verified and self._regression_count.get(worker_id, 0) >= 2:
            # Rollback
            self._state.setdefault("workers", {})[worker_id] = backup
            self._save_state()
            result["rolled_back"] = True
            result["status"] = "rolled_back"
        else:
            result["status"] = "success"

        # Record in history
        self._state.setdefault("history", []).append({
            "worker_id": worker_id,
            "action": action.action_type.value,
            "rationale": action.rationale,
            "result": result["status"],
            "timestamp": time.time(),
        })
        self._save_state()

        return result

    def run_evolution_cycle(
        self, all_worker_metrics: dict[str, dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Run a full evolution cycle across all workers.

        For each worker: measure health → detect signals → propose action → execute.

        Args:
            all_worker_metrics: Dict of worker_id → metrics_data

        Returns:
            Cycle report dict with results per worker
        """
        report: dict[str, Any] = {
            "workers_processed": 0,
            "actions_taken": 0,
            "regressions_detected": 0,
            "results": {},
        }

        for worker_id, metrics in (all_worker_metrics or {}).items():
            health = self.measure_worker_health(worker_id, metrics)
            signals = self.detect_signals(worker_id, health)
            action = self.propose_action(worker_id, signals)
            result = self.execute_action(worker_id, action)

            report["results"][worker_id] = {
                "health": {
                    "success_rate": health.success_rate,
                    "failure_rate": health.failure_rate,
                    "avg_duration": health.avg_duration,
                    "token_efficiency": health.token_efficiency,
                },
                "signals": [
                    {"type": s.signal_type, "severity": s.severity}
                    for s in signals
                ],
                "action": action.action_type.value,
                "result": result["status"],
            }

            report["workers_processed"] += 1
            if result["applied"]:
                report["actions_taken"] += 1
            if result.get("rolled_back"):
                report["regressions_detected"] += 1

        return report

    def _apply_action(self, worker_id: str, action: EvolveAction) -> bool:
        """Apply an evolve action to a worker's configuration."""
        workers = self._state.setdefault("workers", {})
        if worker_id not in workers:
            workers[worker_id] = {}

        if action.action_type == EvolveActionType.RETUNE_PROMPT:
            workers[worker_id]["prompt_retuned"] = True
            workers[worker_id]["last_retune"] = time.time()
        elif action.action_type == EvolveActionType.UPGRADE_MODEL:
            workers[worker_id]["model_upgrade_pending"] = True
        elif action.action_type == EvolveActionType.FLAG_FOR_REVIEW:
            workers[worker_id]["flagged_for_review"] = True
        elif action.action_type == EvolveActionType.SUGGEST_REPLACEMENT:
            workers[worker_id]["replacement_suggested"] = True

        self._save_state()
        return True
