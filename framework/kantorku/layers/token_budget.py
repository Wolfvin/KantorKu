"""
Token Budget Manager — O12: Token budget allocation and tracking.

Manages token budgets per session and per worker, with modes
for tight/balanced/expanded spending and auto-switching based
on usage patterns.

Like a finance manager who ensures the team doesn't overspend
on API tokens.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class BudgetMode(Enum):
    """Token budget modes."""
    TIGHT = "tight"
    BALANCED = "balanced"
    EXPANDED = "expanded"


@dataclass
class BudgetAllocation:
    """Token budget allocation for a session."""
    session_id: str = ""
    mode: BudgetMode = BudgetMode.BALANCED
    total_budget: int = 0
    used: int = 0
    per_worker: dict[str, int] = field(default_factory=dict)


# Budget multipliers by mode
BUDGET_MODES: dict[BudgetMode, float] = {
    BudgetMode.TIGHT: 0.5,
    BudgetMode.BALANCED: 1.0,
    BudgetMode.EXPANDED: 2.0,
}

# Default budget per session (tokens)
DEFAULT_BUDGET: int = 100_000


class TokenBudgetManager:
    """
    Token Budget Manager — allocation and tracking for API tokens.

    Manages token budgets at session and worker level with:
    - Three budget modes: TIGHT (0.5x), BALANCED (1.0x), EXPANDED (2.0x)
    - Per-worker budget allocation with share percentages
    - Usage tracking and reporting
    - Auto-switching between modes based on usage patterns
    - Mode suggestion based on task complexity

    Usage:
        manager = TokenBudgetManager()
        alloc = manager.allocate_session("sess-1", BudgetMode.BALANCED)
        worker_budget = manager.allocate_worker("sess-1", "coder_backend", 0.4)
        can_proceed, remaining = manager.check_budget("sess-1", "coder_backend")
        manager.record_usage("sess-1", "coder_backend", 5000)
    """

    def __init__(
        self,
        default_budget: int = DEFAULT_BUDGET,
    ) -> None:
        self._default_budget = default_budget
        self._sessions: dict[str, BudgetAllocation] = {}
        self._usage_log: dict[str, list[dict[str, Any]]] = {}

    def allocate_session(
        self, session_id: str, mode: BudgetMode = BudgetMode.BALANCED
    ) -> BudgetAllocation:
        """
        Allocate a token budget for a session.

        Args:
            session_id: Session identifier
            mode: Budget mode (TIGHT/BALANCED/EXPANDED)

        Returns:
            BudgetAllocation for the session
        """
        multiplier = BUDGET_MODES.get(mode, 1.0)
        total_budget = int(self._default_budget * multiplier)

        allocation = BudgetAllocation(
            session_id=session_id,
            mode=mode,
            total_budget=total_budget,
            used=0,
            per_worker={},
        )

        self._sessions[session_id] = allocation
        self._usage_log.setdefault(session_id, [])

        return allocation

    def allocate_worker(
        self, session_id: str, worker_id: str, share_pct: float = 0.25
    ) -> int:
        """
        Allocate a portion of the session budget to a specific worker.

        Args:
            session_id: Session identifier
            worker_id: Worker identifier
            share_pct: Percentage of total budget (0.0-1.0)

        Returns:
            Allocated token count for the worker
        """
        allocation = self._sessions.get(session_id)
        if not allocation:
            allocation = self.allocate_session(session_id)

        share_pct = max(0.0, min(1.0, share_pct))
        worker_budget = int(allocation.total_budget * share_pct)
        allocation.per_worker[worker_id] = worker_budget

        return worker_budget

    def check_budget(
        self, session_id: str, worker_id: str
    ) -> tuple[bool, int]:
        """
        Check if a worker can proceed within budget.

        Args:
            session_id: Session identifier
            worker_id: Worker identifier

        Returns:
            Tuple of (can_proceed, remaining_tokens)
        """
        allocation = self._sessions.get(session_id)
        if not allocation:
            return True, self._default_budget

        # Check session-level budget
        session_remaining = allocation.total_budget - allocation.used
        if session_remaining <= 0:
            return False, 0

        # Check worker-level budget
        worker_budget = allocation.per_worker.get(worker_id)
        if worker_budget is not None:
            # Calculate worker usage from logs
            worker_used = sum(
                entry.get("tokens", 0)
                for entry in self._usage_log.get(session_id, [])
                if entry.get("worker_id") == worker_id
            )
            worker_remaining = worker_budget - worker_used
            if worker_remaining <= 0:
                return False, 0
            return True, min(worker_remaining, session_remaining)

        # No specific worker budget — check session level only
        return True, session_remaining

    def record_usage(
        self, session_id: str, worker_id: str, tokens: int
    ) -> BudgetAllocation:
        """
        Record token usage for a worker in a session.

        Args:
            session_id: Session identifier
            worker_id: Worker identifier
            tokens: Number of tokens consumed

        Returns:
            Updated BudgetAllocation
        """
        allocation = self._sessions.get(session_id)
        if not allocation:
            allocation = self.allocate_session(session_id)

        allocation.used += tokens

        # Log the usage
        self._usage_log.setdefault(session_id, []).append({
            "worker_id": worker_id,
            "tokens": tokens,
            "timestamp": time.time(),
        })

        return allocation

    def get_report(self, session_id: str) -> dict[str, Any]:
        """
        Get a budget vs actual report for a session.

        Args:
            session_id: Session identifier

        Returns:
            Dict with budget summary, worker breakdown, and usage log
        """
        allocation = self._sessions.get(session_id)
        if not allocation:
            return {
                "session_id": session_id,
                "error": "No allocation found",
                "budget": 0,
                "used": 0,
                "remaining": 0,
                "utilization": 0.0,
            }

        remaining = allocation.total_budget - allocation.used
        utilization = (
            allocation.used / allocation.total_budget
            if allocation.total_budget > 0
            else 0.0
        )

        # Worker breakdown
        worker_breakdown: dict[str, dict[str, Any]] = {}
        usage_entries = self._usage_log.get(session_id, [])
        for wid, budget in allocation.per_worker.items():
            worker_used = sum(
                e.get("tokens", 0) for e in usage_entries if e.get("worker_id") == wid
            )
            worker_breakdown[wid] = {
                "budget": budget,
                "used": worker_used,
                "remaining": budget - worker_used,
                "utilization": (worker_used / budget) if budget > 0 else 0.0,
            }

        return {
            "session_id": session_id,
            "mode": allocation.mode.value,
            "budget": allocation.total_budget,
            "used": allocation.used,
            "remaining": remaining,
            "utilization": utilization,
            "workers": worker_breakdown,
        }

    def suggest_mode(self, complexity: str) -> BudgetMode:
        """
        Suggest a budget mode based on task complexity.

        Args:
            complexity: "simple", "medium", or "complex"

        Returns:
            Suggested BudgetMode
        """
        mapping = {
            "simple": BudgetMode.TIGHT,
            "medium": BudgetMode.BALANCED,
            "complex": BudgetMode.EXPANDED,
        }
        return mapping.get(complexity, BudgetMode.BALANCED)

    def auto_switch(self, session_id: str) -> BudgetMode | None:
        """
        Auto-adjust budget mode based on usage pattern.

        Switches to EXPANDED if utilization > 80% early,
        or to TIGHT if utilization < 20% at midpoint.

        Args:
            session_id: Session identifier

        Returns:
            New BudgetMode if switched, None otherwise
        """
        allocation = self._sessions.get(session_id)
        if not allocation:
            return None

        utilization = (
            allocation.used / allocation.total_budget
            if allocation.total_budget > 0
            else 0.0
        )

        current_mode = allocation.mode
        new_mode: BudgetMode | None = None

        # High utilization — expand budget
        if utilization > 0.8 and current_mode != BudgetMode.EXPANDED:
            if current_mode == BudgetMode.TIGHT:
                new_mode = BudgetMode.BALANCED
            else:
                new_mode = BudgetMode.EXPANDED

        # Low utilization — tighten budget
        elif utilization < 0.2 and current_mode != BudgetMode.TIGHT:
            if current_mode == BudgetMode.EXPANDED:
                new_mode = BudgetMode.BALANCED
            else:
                new_mode = BudgetMode.TIGHT

        if new_mode:
            # Re-allocate with new mode
            multiplier = BUDGET_MODES.get(new_mode, 1.0)
            old_used = allocation.used
            allocation.mode = new_mode
            allocation.total_budget = int(self._default_budget * multiplier)
            allocation.used = old_used  # Preserve usage

        return new_mode
