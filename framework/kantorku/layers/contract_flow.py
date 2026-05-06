"""
Contract Flow Manager — O25: Track and enforce contract phase transitions.

Manages the lifecycle of contracts through defined phases with
valid transitions, history tracking, and bottleneck detection.

Like a project management office that tracks which stage each
project is in and flags when things get stuck.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ContractPhase(Enum):
    """Phases of a contract lifecycle."""
    INTAKE = "intake"
    UNDERSTANDING = "understanding"
    PLAN_DRAFTED = "plan_drafted"
    TEAM_REVIEW = "team_review"
    TODO_REVIEW = "todo_review"
    CLIENT_FEEDBACK = "client_feedback"
    ACCEPTED = "accepted"
    WORKING = "working"
    VERIFICATION = "verification"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PhaseTransition:
    """A recorded phase transition."""
    from_phase: str = ""
    to_phase: str = ""
    timestamp: float = field(default_factory=time.time)
    trigger: str = ""
    evidence: str = ""


# Define all valid phase transitions
VALID_TRANSITIONS: dict[ContractPhase, list[ContractPhase]] = {
    ContractPhase.INTAKE: [
        ContractPhase.UNDERSTANDING,
        ContractPhase.CANCELLED,
    ],
    ContractPhase.UNDERSTANDING: [
        ContractPhase.PLAN_DRAFTED,
        ContractPhase.CLIENT_FEEDBACK,
        ContractPhase.CANCELLED,
    ],
    ContractPhase.PLAN_DRAFTED: [
        ContractPhase.TEAM_REVIEW,
        ContractPhase.CLIENT_FEEDBACK,
        ContractPhase.CANCELLED,
    ],
    ContractPhase.TEAM_REVIEW: [
        ContractPhase.TODO_REVIEW,
        ContractPhase.PLAN_DRAFTED,
        ContractPhase.CLIENT_FEEDBACK,
        ContractPhase.CANCELLED,
    ],
    ContractPhase.TODO_REVIEW: [
        ContractPhase.ACCEPTED,
        ContractPhase.PLAN_DRAFTED,
        ContractPhase.CLIENT_FEEDBACK,
        ContractPhase.CANCELLED,
    ],
    ContractPhase.CLIENT_FEEDBACK: [
        ContractPhase.UNDERSTANDING,
        ContractPhase.PLAN_DRAFTED,
        ContractPhase.ACCEPTED,
        ContractPhase.CANCELLED,
    ],
    ContractPhase.ACCEPTED: [
        ContractPhase.WORKING,
        ContractPhase.CANCELLED,
    ],
    ContractPhase.WORKING: [
        ContractPhase.VERIFICATION,
        ContractPhase.FAILED,
        ContractPhase.CANCELLED,
    ],
    ContractPhase.VERIFICATION: [
        ContractPhase.DONE,
        ContractPhase.WORKING,
        ContractPhase.FAILED,
        ContractPhase.CANCELLED,
    ],
    ContractPhase.DONE: [],
    ContractPhase.FAILED: [
        ContractPhase.INTAKE,
    ],
    ContractPhase.CANCELLED: [],
}


class ContractFlowManager:
    """
    Contract Flow Manager — track and enforce contract phase transitions.

    Manages the complete lifecycle of contracts:
    - Validates that phase transitions are legal
    - Records transition history with timestamps and triggers
    - Calculates time-per-phase metrics
    - Identifies bottlenecks (phases taking too long)
    - Provides flow summaries

    Usage:
        manager = ContractFlowManager()
        is_valid = manager.validate_transition(ContractPhase.INTAKE, ContractPhase.UNDERSTANDING)
        manager.record_transition("contract-1", PhaseTransition(
            from_phase="intake", to_phase="understanding", trigger="client_message"
        ))
        history = manager.get_contract_history("contract-1")
        bottleneck = manager.identify_bottleneck("contract-1")
    """

    def __init__(self) -> None:
        self._contracts: dict[str, list[PhaseTransition]] = {}
        self._current_phases: dict[str, ContractPhase] = {}

    def validate_transition(
        self, current_phase: ContractPhase | str, target_phase: ContractPhase | str
    ) -> bool:
        """
        Validate that a phase transition is allowed.

        Args:
            current_phase: Current contract phase
            target_phase: Desired target phase

        Returns:
            True if the transition is valid
        """
        # Handle string inputs
        if isinstance(current_phase, str):
            try:
                current_phase = ContractPhase(current_phase)
            except ValueError:
                return False
        if isinstance(target_phase, str):
            try:
                target_phase = ContractPhase(target_phase)
            except ValueError:
                return False

        allowed = VALID_TRANSITIONS.get(current_phase, [])
        return target_phase in allowed

    def record_transition(
        self,
        contract_id: str,
        transition: PhaseTransition,
    ) -> None:
        """
        Record a phase transition for a contract.

        Args:
            contract_id: Contract identifier
            transition: PhaseTransition to record
        """
        if contract_id not in self._contracts:
            self._contracts[contract_id] = []

        self._contracts[contract_id].append(transition)

        # Update current phase
        try:
            self._current_phases[contract_id] = ContractPhase(transition.to_phase)
        except ValueError:
            pass

    def get_contract_history(
        self, contract_id: str
    ) -> list[PhaseTransition]:
        """
        Get the full transition history for a contract.

        Args:
            contract_id: Contract identifier

        Returns:
            List of PhaseTransition instances in chronological order
        """
        return list(self._contracts.get(contract_id, []))

    def get_phase_metrics(
        self, contract_id: str
    ) -> dict[str, float]:
        """
        Calculate time spent in each phase for a contract.

        Args:
            contract_id: Contract identifier

        Returns:
            Dict of phase_name → duration_in_seconds
        """
        transitions = self._contracts.get(contract_id, [])
        if not transitions:
            return {}

        metrics: dict[str, float] = {}

        for i, transition in enumerate(transitions):
            phase_name = transition.from_phase
            if not phase_name:
                continue

            # Calculate duration until next transition out of this phase
            start_time = transition.timestamp
            end_time = start_time  # Default: same time

            # Find when we left this phase
            for j in range(i + 1, len(transitions)):
                if transitions[j].from_phase == phase_name:
                    end_time = transitions[j].timestamp
                    break
            else:
                # Still in this phase or last transition
                if i < len(transitions) - 1:
                    end_time = transitions[i + 1].timestamp
                else:
                    end_time = time.time()  # Still in phase

            duration = max(0.0, end_time - start_time)

            # Accumulate if phase was visited multiple times
            if phase_name in metrics:
                metrics[phase_name] += duration
            else:
                metrics[phase_name] = duration

        return metrics

    def identify_bottleneck(
        self, contract_id: str
    ) -> dict[str, Any]:
        """
        Identify the bottleneck phase for a contract.

        The bottleneck is the phase that took the longest time.

        Args:
            contract_id: Contract identifier

        Returns:
            Dict with bottleneck phase name and duration
        """
        metrics = self.get_phase_metrics(contract_id)

        if not metrics:
            return {
                "bottleneck_phase": None,
                "duration": 0.0,
                "all_phases": {},
            }

        bottleneck = max(metrics, key=lambda p: metrics[p])

        return {
            "bottleneck_phase": bottleneck,
            "duration": metrics[bottleneck],
            "all_phases": metrics,
        }

    def get_flow_summary(
        self, contract_id: str
    ) -> dict[str, Any]:
        """
        Get a complete flow summary for a contract.

        Args:
            contract_id: Contract identifier

        Returns:
            Summary dict with current phase, history, metrics, and bottleneck
        """
        current = self._current_phases.get(contract_id)
        current_value = current.value if current else "unknown"

        history = self.get_contract_history(contract_id)
        metrics = self.get_phase_metrics(contract_id)
        bottleneck = self.identify_bottleneck(contract_id)

        total_duration = sum(metrics.values())
        transition_count = len(history)

        # Determine flow health
        if transition_count == 0:
            flow_health = "no_activity"
        elif bottleneck.get("duration", 0) > total_duration * 0.6:
            flow_health = "bottleneck_detected"
        else:
            flow_health = "healthy"

        return {
            "contract_id": contract_id,
            "current_phase": current_value,
            "transition_count": transition_count,
            "total_duration": total_duration,
            "phase_metrics": metrics,
            "bottleneck": bottleneck,
            "flow_health": flow_health,
            "phases_visited": [
                {
                    "from": t.from_phase,
                    "to": t.to_phase,
                    "trigger": t.trigger,
                    "timestamp": t.timestamp,
                }
                for t in history
            ],
        }
