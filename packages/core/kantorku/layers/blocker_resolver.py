"""
Blocker Resolver — O15: Automated blocker classification and resolution.

Classifies blockers by type, selects resolution strategies, delegates
to debug workers, and tracks resolution history.

Like a project manager who doesn't just say "it's blocked" but
figures out WHY and WHAT to do about it.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class BlockerType(Enum):
    """Types of blockers that can occur."""
    TRANSIENT = "transient"
    SYSTEMATIC = "systematic"
    RESOURCE = "resource"
    SPEC_AMBIGUITY = "spec_ambiguity"


class ResolutionStrategy(Enum):
    """Available resolution strategies."""
    RETRY_SAME = "retry_same"
    REASSIGN_WORKER = "reassign_worker"
    SIMPLIFY_TASK = "simplify_task"
    ESCALATE_TO_MANAGER = "escalate_to_manager"


@dataclass
class Blocker:
    """A classified blocker."""
    error: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    worker_id: str = ""
    blocker_type: BlockerType = BlockerType.TRANSIENT
    attempt_count: int = 0


@dataclass
class Resolution:
    """A resolution for a blocker."""
    strategy: ResolutionStrategy = ResolutionStrategy.RETRY_SAME
    outcome: str = "pending"
    new_worker_id: str = ""
    simplified_task: str = ""


# Keyword patterns for blocker classification
_BLOCKER_PATTERNS: dict[BlockerType, list[str]] = {
    BlockerType.TRANSIENT: [
        "timeout", "temporarily", "retry", "rate limit", "503",
        "connection reset", "network error", "temporary failure",
    ],
    BlockerType.SYSTEMATIC: [
        "always fails", "consistently", "every time", "persistent",
        "recurring", "systematic", "reproducible", "deterministic",
    ],
    BlockerType.RESOURCE: [
        "out of memory", "disk full", "quota exceeded", "limit reached",
        "insufficient", "not available", "unavailable", "resource",
    ],
    BlockerType.SPEC_AMBIGUITY: [
        "ambiguous", "unclear", "not specified", "undefined",
        "conflicting", "contradictory", "interpretation",
    ],
}

# Max retries before escalating
_MAX_RETRY_ATTEMPTS = 2


class BlockerResolver:
    """
    Blocker Resolver — automated blocker classification and resolution.

    Classifies blockers by type, selects appropriate resolution
    strategies, can delegate to debug workers, and maintains
    a history of resolutions.

    Usage:
        resolver = BlockerResolver()
        blocker = resolver.analyze_blocker("Connection timeout", {}, "worker_1")
        strategy = resolver.select_strategy(blocker)
        if resolver.should_escalate(3, "persistent"):
            # Escalate to manager
    """

    def __init__(self) -> None:
        self._history: list[dict[str, Any]] = []

    def analyze_blocker(
        self,
        error: str,
        context: dict[str, Any] | None = None,
        worker_id: str = "",
    ) -> Blocker:
        """
        Analyze and classify a blocker from an error message.

        Args:
            error: The error message or description
            context: Additional context about the blocker
            worker_id: The worker that encountered the blocker

        Returns:
            Classified Blocker with type and attempt count
        """
        if not error:
            return Blocker(
                error=error or "",
                context=context or {},
                worker_id=worker_id,
                blocker_type=BlockerType.TRANSIENT,
                attempt_count=0,
            )

        context = context or {}
        error_lower = error.lower()

        # Score each blocker type by keyword matches
        scores: dict[BlockerType, int] = {}
        for btype, keywords in _BLOCKER_PATTERNS.items():
            score = sum(1 for kw in keywords if kw in error_lower)
            if score > 0:
                scores[btype] = score

        # Determine blocker type
        if scores:
            blocker_type = max(scores, key=lambda bt: scores[bt])
        else:
            # Default classification based on context
            attempt_count = context.get("attempt_count", 0)
            if attempt_count >= 3:
                blocker_type = BlockerType.SYSTEMATIC
            else:
                blocker_type = BlockerType.TRANSIENT

        # Get attempt count from context or history
        attempt_count = context.get("attempt_count", 0)
        # Also check history for same worker + similar error
        for entry in self._history:
            if entry.get("worker_id") == worker_id and entry.get("error") == error:
                attempt_count = max(attempt_count, entry.get("attempt_count", 0))

        return Blocker(
            error=error,
            context=context,
            worker_id=worker_id,
            blocker_type=blocker_type,
            attempt_count=attempt_count,
        )

    def select_strategy(
        self,
        blocker: Blocker | None = None,
        attempt_count: int | None = None,
        blocker_type: BlockerType | None = None,
    ) -> ResolutionStrategy:
        """
        Select a resolution strategy based on blocker classification.

        Rules:
        - TRANSIENT + attempts ≤ 2 → RETRY_SAME
        - TRANSIENT + attempts > 2 → REASSIGN_WORKER
        - SYSTEMATIC → REASSIGN_WORKER
        - RESOURCE → SIMPLIFY_TASK
        - SPEC_AMBIGUITY → ESCALATE_TO_MANAGER

        Args:
            blocker: The Blocker to resolve (alternative to individual args)
            attempt_count: Override attempt count
            blocker_type: Override blocker type

        Returns:
            ResolutionStrategy to apply
        """
        # Extract values from blocker or use overrides
        if blocker:
            btype = blocker_type or blocker.blocker_type
            attempts = attempt_count if attempt_count is not None else blocker.attempt_count
        else:
            btype = blocker_type or BlockerType.TRANSIENT
            attempts = attempt_count or 0

        if btype == BlockerType.TRANSIENT:
            if attempts <= _MAX_RETRY_ATTEMPTS:
                return ResolutionStrategy.RETRY_SAME
            else:
                return ResolutionStrategy.REASSIGN_WORKER
        elif btype == BlockerType.SYSTEMATIC:
            return ResolutionStrategy.REASSIGN_WORKER
        elif btype == BlockerType.RESOURCE:
            return ResolutionStrategy.SIMPLIFY_TASK
        elif btype == BlockerType.SPEC_AMBIGUITY:
            return ResolutionStrategy.ESCALATE_TO_MANAGER
        else:
            return ResolutionStrategy.RETRY_SAME

    def delegate_to_debugger(
        self,
        blocker: Blocker,
        session_id: str = "",
    ) -> dict[str, Any]:
        """
        Delegate a blocker to the debug worker.

        Creates a structured debug task from the blocker information.

        Args:
            blocker: The Blocker to debug
            session_id: Session identifier

        Returns:
            Dict with debug task details
        """
        return {
            "task_type": "debug",
            "session_id": session_id,
            "worker_id": "debugger",
            "error": blocker.error,
            "context": blocker.context,
            "original_worker": blocker.worker_id,
            "blocker_type": blocker.blocker_type.value,
            "attempt_count": blocker.attempt_count,
            "instructions": (
                f"Debug the following {blocker.blocker_type.value} blocker "
                f"encountered by {blocker.worker_id}:\n"
                f"Error: {blocker.error}\n"
                f"Context: {blocker.context}"
            ),
        }

    def record_resolution(
        self,
        blocker: str | Blocker,
        strategy: str | ResolutionStrategy,
        outcome: str = "pending",
        worker_id: str = "",
    ) -> None:
        """
        Record a blocker resolution in history.

        Args:
            blocker: The blocker (string error or Blocker object)
            strategy: The strategy applied
            outcome: The outcome of the resolution
            worker_id: The worker that was involved
        """
        if isinstance(blocker, Blocker):
            error_str = blocker.error
            w_id = blocker.worker_id or worker_id
            attempts = blocker.attempt_count
        else:
            error_str = str(blocker)
            w_id = worker_id
            attempts = 0

        strategy_val = strategy.value if isinstance(strategy, ResolutionStrategy) else str(strategy)

        self._history.append({
            "error": error_str,
            "strategy": strategy_val,
            "outcome": outcome,
            "worker_id": w_id,
            "attempt_count": attempts,
            "timestamp": time.time(),
        })

    def should_escalate(
        self, attempt_count: int, error_pattern: str = ""
    ) -> bool:
        """
        Determine if a blocker should be escalated to the manager.

        Escalate when:
        - Attempt count exceeds max retries
        - Error pattern matches systematic failure indicators

        Args:
            attempt_count: Number of attempts made
            error_pattern: Error message or pattern to check

        Returns:
            True if the blocker should be escalated
        """
        if attempt_count > _MAX_RETRY_ATTEMPTS:
            return True

        if error_pattern:
            systematic_keywords = [
                "always", "consistent", "every time", "persistent",
                "recurring", "systematic",
            ]
            error_lower = error_pattern.lower()
            if any(kw in error_lower for kw in systematic_keywords):
                return True

        return False

    def get_history(self) -> list[dict[str, Any]]:
        """Get the resolution history."""
        return list(self._history)

    def clear_history(self) -> None:
        """Clear the resolution history."""
        self._history.clear()
