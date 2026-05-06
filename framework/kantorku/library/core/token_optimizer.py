"""
TokenOptimizer — Context window management for KantorKu Library.

The TokenOptimizer manages the size of context windows sent to LLMs
by truncating, compacting, and prioritizing Library entries to fit
within token budgets. This ensures efficient use of context windows
while preserving the most relevant information.

Modes:
    tight:    Max 1000 chars per entry context (~250 tokens)
    balanced: Max 2000 chars per entry context (~500 tokens)
    expanded: Max 4000 chars per entry context (~1000 tokens)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

from kantorku.library.core.models import LibraryEntry

logger = logging.getLogger(__name__)


class BudgetMode(str, Enum):
    """Token budget modes for context optimization."""

    TIGHT = "tight"
    BALANCED = "balanced"
    EXPANDED = "expanded"


# Budget limits (approximate character counts, ~4 chars per token)
_BUDGET_LIMITS: dict[BudgetMode, int] = {
    BudgetMode.TIGHT: 1000,
    BudgetMode.BALANCED: 2000,
    BudgetMode.EXPANDED: 4000,
}

# Detail level character limits
_DETAIL_LIMITS: dict[str, int] = {
    "full": 2000,
    "summary": 500,
    "minimal": 100,
}


class TokenOptimizer:
    """Context window management for Library entries.

    Optimizes the context sent to LLMs by truncating entries to fit
    within token budgets, prioritizing by relevance and quality.

    Example::

        optimizer = TokenOptimizer(mode="balanced")
        context = optimizer.build_optimal_context(
            query="Python ImportError",
            entries=retrieved_entries,
            budget_mode=BudgetMode.BALANCED,
        )
    """

    def __init__(self, mode: str = "balanced") -> None:
        """Initialize the TokenOptimizer.

        Args:
            mode: The default budget mode — "tight", "balanced", or "expanded".
        """
        try:
            self._mode = BudgetMode(mode)
        except ValueError:
            logger.warning("Invalid mode %r — defaulting to 'balanced'", mode)
            self._mode = BudgetMode.BALANCED

    # ── Public API ──────────────────────────────────────────────────────

    def optimize_context(
        self,
        entries: list[LibraryEntry],
        max_tokens: int | None = None,
    ) -> list[dict[str, Any]]:
        """Truncate entries to fit within a token budget.

        Prioritizes entries by relevance (quality score) and truncates
        each to fit the budget. Returns compacted entry representations.

        Args:
            entries: The Library entries to optimize.
            max_tokens: Maximum token budget. If None, uses the default
                mode budget.

        Returns:
            A list of compacted entry dicts with content truncated to fit.
        """
        if not entries:
            return []

        budget = max_tokens if max_tokens is not None else self.get_budget(self._mode)
        budget_chars = budget * 4  # Approximate chars per token

        # Sort entries by quality (highest first) for prioritization
        sorted_entries = sorted(entries, key=lambda e: e.quality_score, reverse=True)

        result: list[dict[str, Any]] = []
        used_chars = 0

        for entry in sorted_entries:
            # Calculate remaining budget
            remaining = budget_chars - used_chars
            if remaining <= 0:
                break

            # Compact the entry to fit remaining budget
            compacted = self.compact_entry(entry, detail_level="summary")

            # Truncate content if still too long
            content = compacted.get("content", "")
            if len(content) > remaining:
                content = content[:remaining - 3] + "..."
                compacted["content"] = content
                compacted["truncated"] = True

            used_chars += len(content)
            result.append(compacted)

        logger.debug(
            "Optimized context: %d entries → %d chars (~%d tokens)",
            len(result),
            used_chars,
            used_chars // 4,
        )

        return result

    def compact_entry(
        self,
        entry: LibraryEntry,
        detail_level: str = "summary",
    ) -> dict[str, Any]:
        """Compact a single entry to a specified detail level.

        Detail levels:
        - full: Full content (up to 2000 chars)
        - summary: Summary + title + keywords (up to 500 chars)
        - minimal: Just title + keywords (up to 100 chars)

        Args:
            entry: The LibraryEntry to compact.
            detail_level: One of "full", "summary", "minimal".

        Returns:
            A compacted dict representation of the entry.
        """
        max_chars = _DETAIL_LIMITS.get(detail_level, 500)

        result: dict[str, Any] = {
            "id": entry.id,
            "title": entry.title,
            "entry_type": entry.entry_type.value,
            "quality_score": entry.quality_score,
            "shelf_path": entry.shelf_path,
            "keywords": entry.keywords[:5],
            "detail_level": detail_level,
            "truncated": False,
        }

        if detail_level == "full":
            content = entry.content
            if len(content) > max_chars:
                content = content[:max_chars - 3] + "..."
                result["truncated"] = True
            result["content"] = content

        elif detail_level == "summary":
            parts: list[str] = []
            if entry.summary:
                parts.append(entry.summary)
            else:
                # Use first part of content as summary
                content_preview = entry.content[:300]
                if len(entry.content) > 300:
                    content_preview += "..."
                parts.append(content_preview)

            content = "\n".join(parts)
            if len(content) > max_chars:
                content = content[:max_chars - 3] + "..."
                result["truncated"] = True
            result["content"] = content

        elif detail_level == "minimal":
            parts = [entry.title or "(untitled)"]
            if entry.keywords:
                parts.append(" ".join(f"#{kw}" for kw in entry.keywords[:3]))
            content = " | ".join(parts)
            if len(content) > max_chars:
                content = content[:max_chars - 3] + "..."
                result["truncated"] = True
            result["content"] = content

        else:
            result["content"] = entry.summary or entry.content[:200]

        return result

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate the number of tokens in a text string.

        Uses a simple heuristic: 1 token ≈ 4 characters.

        Args:
            text: The text to estimate tokens for.

        Returns:
            An estimated token count.
        """
        return len(text) // 4 if text else 0

    def build_optimal_context(
        self,
        query: str,
        entries: list[LibraryEntry],
        budget_mode: BudgetMode | None = None,
    ) -> str:
        """Build an optimal context string within a token budget.

        Constructs a context string from entries, prioritizing by
        relevance to the query and quality scores, then truncating
        to fit the budget.

        Args:
            query: The user's query (for relevance scoring).
            entries: The retrieved Library entries.
            budget_mode: Override the default budget mode.

        Returns:
            A context string optimized for the token budget.
        """
        mode = budget_mode or self._mode
        budget = self.get_budget(mode)
        budget_chars = budget * 4

        # Deduct query tokens from budget
        query_chars = len(query)
        available_chars = max(budget_chars - query_chars - 200, 500)  # 200 for formatting

        # Score entries by relevance + quality
        scored_entries: list[tuple[float, LibraryEntry]] = []
        query_lower = query.lower()
        for entry in entries:
            # Keyword overlap score
            keyword_score = sum(
                1 for kw in entry.keywords if kw.lower() in query_lower
            )
            # Quality score
            quality_score = entry.quality_score
            # Combined score
            combined = keyword_score * 0.3 + quality_score * 0.7
            scored_entries.append((combined, entry))

        # Sort by combined score (highest first)
        scored_entries.sort(key=lambda x: x[0], reverse=True)

        # Build context
        parts: list[str] = []
        used_chars = 0

        for score, entry in scored_entries:
            remaining = available_chars - used_chars
            if remaining <= 100:  # Need at least 100 chars per entry
                break

            compacted = self.compact_entry(entry, detail_level="summary")
            entry_text = (
                f"[{entry.id[:8]}] {compacted['title']}\n"
                f"  Type: {compacted['entry_type']} | Q: {compacted['quality_score']:.2f}\n"
                f"  {compacted['content']}"
            )

            if len(entry_text) > remaining:
                entry_text = entry_text[:remaining - 3] + "..."

            parts.append(entry_text)
            used_chars += len(entry_text)

        context = "\n\n".join(parts)

        logger.debug(
            "Built context: %d entries, %d chars (~%d tokens), mode=%s",
            len(parts),
            len(context),
            self.estimate_tokens(context),
            mode.value,
        )

        return context

    @staticmethod
    def get_budget(mode: BudgetMode | str | None = None) -> int:
        """Get the token budget for a mode.

        Args:
            mode: The budget mode. Defaults to "balanced".

        Returns:
            The token limit for the mode.
        """
        if mode is None:
            mode = BudgetMode.BALANCED
        if isinstance(mode, str):
            try:
                mode = BudgetMode(mode)
            except ValueError:
                mode = BudgetMode.BALANCED
        return _BUDGET_LIMITS.get(mode, 2000)
