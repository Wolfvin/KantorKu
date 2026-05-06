"""
CEO Orchestration Mode — O8: Structured failure classification and recovery.

Provides the CEO (Conductor) with a systematic approach to:
- Classifying failures into a taxonomy
- Selecting appropriate recovery strategies
- Formatting structured communication contracts
- Validating quality gates
- Generating phase reports and verification evidence

Like a real CEO: when things go wrong, you don't panic — you classify,
pick the right response, and communicate clearly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FailureType(Enum):
    """Taxonomy of failure types the CEO can encounter."""
    STALE_CHECK = "stale_check"
    IMPLEMENTATION_BUG = "implementation_bug"
    TEST_HARNESS_BUG = "test_harness_bug"
    SPEC_AMBIGUITY = "spec_ambiguity"
    ENVIRONMENT_BLOCKER = "environment_blocker"
    UNKNOWN = "unknown"


class RecoveryStrategy(Enum):
    """Available recovery strategies for the CEO."""
    RETRY = "retry"
    REASSIGN = "reassign"
    SIMPLIFY = "simplify"
    ESCALATE = "escalate"


# Failure keyword patterns for classification
_FAILURE_PATTERNS: dict[FailureType, list[str]] = {
    FailureType.STALE_CHECK: [
        "stale", "outdated", "cache", "expired", "old version",
        "not refreshed", "stale data", "stale state",
    ],
    FailureType.IMPLEMENTATION_BUG: [
        "bug", "error", "exception", "traceback", "null pointer",
        "undefined", "type error", "value error", "index error",
        "attribute error", "key error", "runtime error",
    ],
    FailureType.TEST_HARNESS_BUG: [
        "test fail", "assertion", "mock", "fixture", "test harness",
        "flaky test", "test timeout", "test setup",
    ],
    FailureType.SPEC_AMBIGUITY: [
        "ambiguous", "unclear", "undefined behavior", "not specified",
        "conflicting requirements", "vague", "interpretation",
    ],
    FailureType.ENVIRONMENT_BLOCKER: [
        "permission denied", "network", "timeout", "unreachable",
        "connection refused", "dns", "env var", "missing dependency",
        "out of memory", "disk full", "rate limit",
    ],
}

# Default worker assignments for the stable squad
STABLE_SQUAD: dict[str, str] = {
    "frontend": "coder_frontend",
    "backend": "coder_backend",
    "wiring": "coder_wiring",
    "design_verify": "verifier_designer",
    "engineer_verify": "verifier_engineer",
    "debug": "debugger",
    "research": "scout",
    "review": "auditor",
}

# Recovery strategy mapping by failure type
_RECOVERY_MAP: dict[FailureType, RecoveryStrategy] = {
    FailureType.STALE_CHECK: RecoveryStrategy.RETRY,
    FailureType.IMPLEMENTATION_BUG: RecoveryStrategy.REASSIGN,
    FailureType.TEST_HARNESS_BUG: RecoveryStrategy.SIMPLIFY,
    FailureType.SPEC_AMBIGUITY: RecoveryStrategy.ESCALATE,
    FailureType.ENVIRONMENT_BLOCKER: RecoveryStrategy.ESCALATE,
    FailureType.UNKNOWN: RecoveryStrategy.RETRY,
}

# Quality gate definitions
_QUALITY_GATES: dict[str, dict[str, Any]] = {
    "contract_complete": {
        "description": "Contract has all required fields",
        "required_fields": ["title", "description", "todos"],
    },
    "plan_actionable": {
        "description": "Plan has concrete, executable steps",
        "required_fields": ["execution_order", "relevant_workers"],
    },
    "output_verifiable": {
        "description": "Output can be verified against spec",
        "required_fields": ["spec", "output"],
    },
    "no_dead_code": {
        "description": "No unused imports or unreachable code",
        "required_fields": ["scan_results"],
    },
}


@dataclass
class QualityGateResult:
    """Result of a quality gate validation."""
    gate_name: str
    passed: bool
    evidence: dict[str, Any] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)


class CEOOrchestrationMode:
    """
    CEO Orchestration Mode — structured failure handling and communication.

    Provides systematic approaches to:
    - Classifying failures into a taxonomy
    - Selecting recovery strategies based on failure type
    - Formatting communication contracts
    - Validating quality gates
    - Generating phase reports and verification evidence

    Usage:
        ceo = CEOOrchestrationMode()
        failure = ceo.classify_failure("TypeError: null pointer", {})
        strategy = ceo.select_recovery_strategy(failure)
        report = ceo.generate_phase_report("understanding", "complete", {}, [])
    """

    FAILURE_TAXONOMY: dict[str, FailureType] = {
        "stale_check": FailureType.STALE_CHECK,
        "implementation_bug": FailureType.IMPLEMENTATION_BUG,
        "test_harness_bug": FailureType.TEST_HARNESS_BUG,
        "spec_ambiguity": FailureType.SPEC_AMBIGUITY,
        "environment_blocker": FailureType.ENVIRONMENT_BLOCKER,
    }

    STABLE_SQUAD: dict[str, str] = dict(STABLE_SQUAD)

    def classify_failure(
        self, error_msg: str, context: dict[str, Any] | None = None
    ) -> FailureType:
        """
        Classify a failure message into a failure type from the taxonomy.

        Uses keyword pattern matching against the error message.
        Context can provide additional signals (e.g., 'phase', 'worker_id').

        Args:
            error_msg: The error message or description
            context: Optional additional context for classification

        Returns:
            The classified FailureType
        """
        if not error_msg:
            return FailureType.UNKNOWN

        context = context or {}
        msg_lower = error_msg.lower()

        # Score each failure type by keyword matches
        scores: dict[FailureType, int] = {}
        for ftype, keywords in _FAILURE_PATTERNS.items():
            score = sum(1 for kw in keywords if kw in msg_lower)
            if score > 0:
                scores[ftype] = score

        # Context-based overrides
        phase = context.get("phase", "")
        if phase == "verification" and scores.get(FailureType.TEST_HARNESS_BUG, 0) > 0:
            return FailureType.TEST_HARNESS_BUG
        if phase == "understanding" and scores.get(FailureType.SPEC_AMBIGUITY, 0) > 0:
            return FailureType.SPEC_AMBIGUITY

        if not scores:
            return FailureType.UNKNOWN

        return max(scores, key=lambda ft: scores[ft])

    def select_recovery_strategy(self, failure_type: FailureType) -> RecoveryStrategy:
        """
        Select a recovery strategy based on the failure type.

        Args:
            failure_type: The classified failure type

        Returns:
            The recommended RecoveryStrategy
        """
        return _RECOVERY_MAP.get(failure_type, RecoveryStrategy.RETRY)

    def format_communication_contract(
        self,
        phase: str,
        delegation: dict[str, str],
        artifacts: list[str],
        checks: list[str],
        gate_result: QualityGateResult | None = None,
        confidence: float = 0.0,
        next_action: str = "",
    ) -> dict[str, Any]:
        """
        Format a structured communication contract for handoff between phases.

        Args:
            phase: Current orchestration phase
            delegation: Worker → task assignment mapping
            artifacts: List of produced artifacts
            checks: Quality checks performed
            gate_result: Result of quality gate validation
            confidence: Confidence score (0.0-1.0)
            next_action: Recommended next action

        Returns:
            Structured dict representing the communication contract
        """
        return {
            "phase": phase,
            "delegation": delegation or {},
            "artifacts": artifacts or [],
            "checks": checks or [],
            "gate": {
                "name": gate_result.gate_name if gate_result else "none",
                "passed": gate_result.passed if gate_result else False,
                "missing": gate_result.missing if gate_result else [],
            },
            "confidence": max(0.0, min(1.0, confidence)),
            "next_action": next_action or "proceed",
            "timestamp_hint": phase,
        }

    def validate_quality_gate(
        self, gate_name: str, evidence: dict[str, Any]
    ) -> QualityGateResult:
        """
        Validate a quality gate against provided evidence.

        Args:
            gate_name: Name of the quality gate to validate
            evidence: Evidence dict to check against gate criteria

        Returns:
            QualityGateResult with pass/fail status and details
        """
        gate_def = _QUALITY_GATES.get(gate_name)
        if not gate_def:
            return QualityGateResult(
                gate_name=gate_name,
                passed=False,
                evidence=evidence,
                missing=[f"Unknown gate: {gate_name}"],
            )

        required = gate_def.get("required_fields", [])
        missing = [f for f in required if f not in evidence or not evidence[f]]

        return QualityGateResult(
            gate_name=gate_name,
            passed=len(missing) == 0,
            evidence=evidence,
            missing=missing,
        )

    def generate_phase_report(
        self,
        phase: str,
        status: str,
        delegation_map: dict[str, str],
        decisions: list[str],
    ) -> str:
        """
        Generate a markdown phase report.

        Args:
            phase: Phase name
            status: Phase status (complete, in_progress, failed)
            delegation_map: Worker → task mapping
            decisions: List of decisions made in this phase

        Returns:
            Markdown formatted report string
        """
        delegation_lines = ""
        for worker, task in (delegation_map or {}).items():
            delegation_lines += f"| {worker} | {task} |\n"

        decisions_text = ""
        for i, d in enumerate(decisions or [], 1):
            decisions_text += f"{i}. {d}\n"

        return (
            f"# Phase Report: {phase}\n\n"
            f"**Status:** {status}\n\n"
            f"## Delegation\n\n"
            f"| Worker | Task |\n"
            f"|--------|------|\n"
            f"{delegation_lines if delegation_lines else '| — | — |\n'}\n"
            f"## Decisions\n\n"
            f"{decisions_text if decisions_text else 'No decisions recorded.'}\n"
        )

    def generate_verification_evidence(
        self,
        gate: str,
        checks: list[str],
        proof: str,
    ) -> str:
        """
        Generate markdown verification evidence for a quality gate.

        Args:
            gate: The quality gate name
            checks: List of checks performed
            proof: Evidence/proof text

        Returns:
            Markdown formatted verification evidence
        """
        checks_text = ""
        for c in checks or []:
            checks_text += f"- [x] {c}\n"

        return (
            f"# Verification Evidence: {gate}\n\n"
            f"## Checks\n\n"
            f"{checks_text if checks_text else '- No checks recorded.'}\n\n"
            f"## Proof\n\n"
            f"{proof or 'No proof provided.'}\n"
        )

    def generate_open_gaps(
        self,
        blockers: list[str],
        residuals: list[str],
    ) -> str:
        """
        Generate markdown listing open gaps (blockers + residuals).

        Args:
            blockers: List of blocker descriptions
            residuals: List of residual/open items

        Returns:
            Markdown formatted open gaps report
        """
        blockers_text = ""
        for b in blockers or []:
            blockers_text += f"- [BLOCKER] {b}\n"

        residuals_text = ""
        for r in residuals or []:
            residuals_text += f"- [RESIDUAL] {r}\n"

        return (
            f"# Open Gaps\n\n"
            f"## Blockers\n\n"
            f"{blockers_text if blockers_text else 'No blockers.'}\n\n"
            f"## Residuals\n\n"
            f"{residuals_text if residuals_text else 'No residuals.'}\n"
        )
