"""
SkillRouter — Deterministic query-to-action router for KantorKu Library.

The SkillRouter classifies incoming queries into actions (ask, search,
ingest, browse, export) using keyword scoring patterns. This enables
the Library system to route user input to the appropriate worker
without requiring LLM calls for simple routing decisions.

Routing strategy:
    1. Deterministic keyword scoring against query patterns
    2. If confidence >= 0.6, return the scored action
    3. If confidence < 0.6, fall back to LLM classification (optional)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RouteResult:
    """Result of a routing decision."""

    action: str = "ask"
    worker: str = "archivist"
    confidence: float = 0.0
    reason: str = ""


# ── Routing patterns ──────────────────────────────────────────────────────
# Each pattern maps a list of keyword patterns to a score.
# The action with the highest total score wins.

_ROUTE_PATTERNS: dict[str, list[tuple[list[str], float]]] = {
    "ask": [
        (["how", "what", "why", "when", "where", "who", "which"], 1.0),
        (["explain", "describe", "tell me", "show me"], 1.5),
        (["bagaimana", "apa", "mengapa", "kapan", "dimana", "siapa"], 1.0),
        (["jelaskan", "terangkan", "ceritakan"], 1.5),
        (["?"], 0.5),
        (["does", "is it", "can i", "should i", "will it"], 1.0),
    ],
    "search": [
        (["search", "find", "look for", "lookup", "locate"], 2.0),
        (["cari", "temukan", "cari tahu"], 2.0),
        (["filter", "query", "list all", "show all"], 1.5),
    ],
    "ingest": [
        (["add", "import", "ingest", "save", "store", "record"], 2.0),
        (["tambah", "impor", "simpan", "catat"], 2.0),
        (["http://", "https://", "www.", ".com", ".org", ".io"], 2.5),
        (["github.com", "gitlab.com", "bitbucket"], 2.5),
        (["paste", "upload", "load from"], 1.5),
    ],
    "browse": [
        (["browse", "explore", "navigate", "list shelves", "tree"], 2.0),
        (["jelajahi", "navigasi", "lihat rak"], 2.0),
        (["show shelf", "open shelf", "go to shelf"], 1.5),
        (["what shelves", "categories", "taxonomy"], 1.0),
    ],
    "export": [
        (["export", "download", "save as", "convert to"], 2.0),
        (["ekspor", "unduh", "simpan sebagai"], 2.0),
        (["json", "markdown", "csv"], 1.0),
        (["backup", "archive"], 1.5),
    ],
}

# Worker mapping — each action maps to a Library worker class
WORKER_MAP: dict[str, str] = {
    "ask": "archivist",
    "search": "indexer",
    "ingest": "librarian",
    "browse": "shelf_manager",
    "export": "exporter",
}


class LibrarySkillRouter:
    """Deterministic query-to-action router for the Library.

    Routes user queries to appropriate Library workers based on
    keyword scoring. Falls back to LLM classification when
    deterministic confidence is too low.

    Example::

        router = LibrarySkillRouter()
        result = router.route("How do I fix a Python ImportError?")
        # result.action == "ask", result.worker == "archivist"

        result = router.route("https://github.com/example/repo")
        # result.action == "ingest", result.worker == "librarian"
    """

    def __init__(self, provider_router: Any | None = None) -> None:
        """Initialize the SkillRouter.

        Args:
            provider_router: Optional provider router for LLM fallback
                classification when deterministic confidence is too low.
        """
        self._provider_router = provider_router

    def route(self, query: str) -> RouteResult:
        """Route a query to the appropriate Library action.

        Uses deterministic keyword scoring to classify the query.
        Falls back to LLM classification if confidence < 0.6
        and a provider router is available.

        Args:
            query: The user's input query string.

        Returns:
            A RouteResult with action, worker, confidence, and reason.
        """
        if not query or not query.strip():
            return RouteResult(
                action="ask",
                worker=WORKER_MAP["ask"],
                confidence=0.0,
                reason="Empty query — defaulting to ask",
            )

        query_lower = query.lower().strip()

        # Score each action based on keyword matching
        scores: dict[str, float] = {}
        matched_keywords: dict[str, list[str]] = {}

        for action, patterns in _ROUTE_PATTERNS.items():
            total_score = 0.0
            matched: list[str] = []

            for keywords, score in patterns:
                for kw in keywords:
                    if kw in query_lower:
                        total_score += score
                        matched.append(kw)

            scores[action] = total_score
            matched_keywords[action] = matched

        # Find the best scoring action
        if not scores or max(scores.values()) == 0:
            # No keywords matched — default to ask
            return RouteResult(
                action="ask",
                worker=WORKER_MAP["ask"],
                confidence=0.3,
                reason="No keyword patterns matched — defaulting to ask",
            )

        best_action = max(scores, key=lambda a: scores[a])
        best_score = scores[best_action]
        second_score = sorted(scores.values(), reverse=True)[1] if len(scores) > 1 else 0.0

        # Compute confidence: ratio of best to total, with gap bonus
        total_score = sum(scores.values())
        if total_score > 0:
            ratio = best_score / total_score
            gap = (best_score - second_score) / max(total_score, 1.0)
            confidence = min(ratio + gap * 0.5, 1.0)
        else:
            confidence = 0.0

        reason = (
            f"Matched keywords: {', '.join(matched_keywords[best_action])} "
            f"(score={best_score:.1f})"
        )

        # If confidence is too low and LLM fallback is available
        if confidence < 0.6 and self._provider_router is not None:
            llm_result = self._route_with_llm(query)
            if llm_result is not None:
                return llm_result

        return RouteResult(
            action=best_action,
            worker=WORKER_MAP.get(best_action, "archivist"),
            confidence=round(confidence, 2),
            reason=reason,
        )

    def _route_with_llm(self, query: str) -> RouteResult | None:
        """Use LLM for classification when deterministic confidence is low.

        Args:
            query: The user's input query.

        Returns:
            A RouteResult from LLM classification, or None if LLM fails.
        """
        if self._provider_router is None:
            return None

        try:
            # This is a synchronous stub — in production, this would be async
            # For now, we just return None to indicate LLM routing is not
            # available in this context
            logger.debug("LLM fallback routing not yet available for query: %s", query[:50])
            return None
        except Exception as exc:
            logger.warning("LLM routing failed: %s", exc)
            return None
