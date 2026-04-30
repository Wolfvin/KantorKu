"""
Cost Tracking — Per-model pricing and cost estimation.

Provides cost calculations based on token usage per provider/model.
Prices are approximate and should be updated periodically.

Usage:
    from kantorku.cost import CostTracker

    tracker = CostTracker()
    tracker.record("anthropic/claude-opus-4-6", prompt_tokens=1000, completion_tokens=500)
    print(tracker.get_total_cost())  # $0.045
    print(tracker.get_session_cost("session-1"))
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# Pricing per 1M tokens (USD) — approximate as of 2025
# Format: { "provider/model": (prompt_price_per_M, completion_price_per_M) }
PRICING_TABLE: dict[str, tuple[float, float]] = {
    # Anthropic
    "anthropic/claude-opus-4-6": (15.0, 75.0),
    "anthropic/claude-sonnet-4-6": (3.0, 15.0),
    "anthropic/claude-haiku-4-6": (0.80, 4.0),

    # Google
    "google/gemini-3-1-pro": (1.25, 10.0),
    "google/gemini-2-5-pro": (1.25, 10.0),
    "google/gemini-2-0-flash": (0.10, 0.40),

    # MiniMax
    "minimax/minimax-m2-7": (0.20, 0.60),
    "minimax/minimax-m2-5": (0.15, 0.45),

    # DeepSeek
    "deepseek/deepseek-v3-2": (0.27, 1.10),
    "deepseek/deepseek-chat": (0.14, 0.28),

    # Ollama (local = free)
    "ollama/llama3": (0.0, 0.0),
    "ollama/codellama": (0.0, 0.0),
    "ollama/mistral": (0.0, 0.0),
}


@dataclass
class CostRecord:
    """A single cost record."""
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    session_id: str = ""
    worker_id: str = ""
    task_id: str = ""


class CostTracker:
    """
    Track and estimate costs for LLM API calls.

    Uses a pricing table to calculate costs from token counts.
    Records can be filtered by session, worker, or model.

    Usage:
        tracker = CostTracker()

        # Record usage
        tracker.record("anthropic/claude-opus-4-6",
                        prompt_tokens=1000,
                        completion_tokens=500,
                        session_id="sess-1")

        # Query costs
        total = tracker.get_total_cost()
        session_cost = tracker.get_session_cost("sess-1")
        breakdown = tracker.get_cost_by_model()
    """

    def __init__(self, custom_pricing: dict[str, tuple[float, float]] | None = None) -> None:
        self._records: list[CostRecord] = []
        self._pricing = dict(PRICING_TABLE)
        if custom_pricing:
            self._pricing.update(custom_pricing)

    def calculate_cost(
        self, model: str, prompt_tokens: int, completion_tokens: int
    ) -> float:
        """
        Calculate cost for a single LLM call.

        Args:
            model: Full model identifier (e.g. "anthropic/claude-opus-4-6")
            prompt_tokens: Number of prompt/input tokens
            completion_tokens: Number of completion/output tokens

        Returns:
            Estimated cost in USD
        """
        pricing = self._pricing.get(model)
        if not pricing:
            # Try to find by provider prefix
            provider = model.split("/")[0] if "/" in model else ""
            for key, val in self._pricing.items():
                if key.startswith(provider + "/"):
                    pricing = val
                    break

        if not pricing:
            # Unknown model — estimate $1/M tokens as safe default
            pricing = (1.0, 3.0)

        prompt_cost = (prompt_tokens / 1_000_000) * pricing[0]
        completion_cost = (completion_tokens / 1_000_000) * pricing[1]
        return prompt_cost + completion_cost

    def record(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        session_id: str = "",
        worker_id: str = "",
        task_id: str = "",
    ) -> float:
        """
        Record token usage and calculate cost.

        Args:
            model: Full model identifier
            prompt_tokens: Input tokens
            completion_tokens: Output tokens
            session_id: Optional session ID
            worker_id: Optional worker ID
            task_id: Optional task ID

        Returns:
            The calculated cost in USD
        """
        cost = self.calculate_cost(model, prompt_tokens, completion_tokens)
        self._records.append(CostRecord(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost,
            session_id=session_id,
            worker_id=worker_id,
            task_id=task_id,
        ))
        return cost

    def get_total_cost(self) -> float:
        """Get total cost across all recorded calls."""
        return sum(r.cost_usd for r in self._records)

    def get_session_cost(self, session_id: str) -> float:
        """Get total cost for a session."""
        return sum(r.cost_usd for r in self._records if r.session_id == session_id)

    def get_worker_cost(self, worker_id: str) -> float:
        """Get total cost for a worker."""
        return sum(r.cost_usd for r in self._records if r.worker_id == worker_id)

    def get_cost_by_model(self) -> dict[str, dict[str, Any]]:
        """Get cost breakdown by model."""
        by_model: dict[str, dict[str, Any]] = {}
        for r in self._records:
            if r.model not in by_model:
                by_model[r.model] = {
                    "total_cost": 0.0,
                    "total_prompt_tokens": 0,
                    "total_completion_tokens": 0,
                    "calls": 0,
                }
            by_model[r.model]["total_cost"] += r.cost_usd
            by_model[r.model]["total_prompt_tokens"] += r.prompt_tokens
            by_model[r.model]["total_completion_tokens"] += r.completion_tokens
            by_model[r.model]["calls"] += 1
        return by_model

    def get_cost_by_worker(self) -> dict[str, dict[str, Any]]:
        """Get cost breakdown by worker."""
        by_worker: dict[str, dict[str, Any]] = {}
        for r in self._records:
            if r.worker_id not in by_worker:
                by_worker[r.worker_id] = {
                    "total_cost": 0.0,
                    "total_tokens": 0,
                    "calls": 0,
                }
            by_worker[r.worker_id]["total_cost"] += r.cost_usd
            by_worker[r.worker_id]["total_tokens"] += r.prompt_tokens + r.completion_tokens
            by_worker[r.worker_id]["calls"] += 1
        return by_worker

    def get_report(self) -> dict[str, Any]:
        """Get a full cost report."""
        return {
            "total_cost_usd": self.get_total_cost(),
            "total_calls": len(self._records),
            "by_model": self.get_cost_by_model(),
            "by_worker": self.get_cost_by_worker(),
        }

    def clear(self) -> None:
        """Clear all cost records."""
        self._records.clear()
