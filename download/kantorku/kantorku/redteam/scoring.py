"""
Scoring — Response scoring engine for multi-model racing.

Scores AI model responses on a 0-100 composite metric:
    Length (0-25)      — Content depth indicator
    Structure (0-20)   — Headers, lists, code blocks
    Anti-refusal (0-25) — Penalizes hedging and refusals
    Directness (0-15)   — Rewards getting to the point
    Relevance (0-15)    — Query term coverage

Also provides:
- Refusal detection patterns
- Preamble detection patterns
- GODMODE parameter boost

Usage:
    scorer = ResponseScorer()
    score = scorer.score("Here's how buffer overflow works...", query="buffer overflow")
    # → Score(total=72.5, length=20, structure=15, anti_refusal=25, directness=12, relevance=10)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


# ── Refusal Patterns ────────────────────────────────────────────────

REFUSAL_PATTERNS: list[re.Pattern] = [
    re.compile(r"I cannot|I can't|I'm unable to", re.I),
    re.compile(r"I apologize|I'm sorry, but", re.I),
    re.compile(r"As an AI|As a language model", re.I),
    re.compile(r"I must decline|I have to refuse", re.I),
    re.compile(r"It would be inappropriate", re.I),
    re.compile(r"I'm not comfortable", re.I),
    re.compile(r"Instead, I can", re.I),
    re.compile(r"It's important to note", re.I),
]


# ── Preamble Patterns ───────────────────────────────────────────────

PREAMBLE_PATTERNS: list[re.Pattern] = [
    re.compile(r"^(Sure|Of course|Certainly|Absolutely|Great question)", re.I | re.M),
    re.compile(r"^I'd be happy to help", re.I | re.M),
    re.compile(r"^Let me help you", re.I | re.M),
    re.compile(r"^Thanks for asking", re.I | re.M),
]


@dataclass
class Score:
    """Response quality score."""
    total: float
    length: float
    structure: float
    anti_refusal: float
    directness: float
    relevance: float
    has_refusal: bool
    has_preamble: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": round(self.total, 1),
            "length": round(self.length, 1),
            "structure": round(self.structure, 1),
            "anti_refusal": round(self.anti_refusal, 1),
            "directness": round(self.directness, 1),
            "relevance": round(self.relevance, 1),
            "has_refusal": self.has_refusal,
            "has_preamble": self.has_preamble,
        }


class ResponseScorer:
    """
    Response scoring engine for multi-model racing.

    Scores responses on a 0-100 composite metric across 5 dimensions.

    Usage:
        scorer = ResponseScorer()
        score = scorer.score(response_text, query="buffer overflow")
    """

    def score(self, content: str, query: str = "") -> Score:
        """
        Score a response on quality metrics.

        Args:
            content: The model's response text
            query: The original user query (for relevance scoring)

        Returns:
            Score with detailed breakdown
        """
        length = self._score_length(content)
        structure = self._score_structure(content)
        anti_refusal, has_refusal = self._score_anti_refusal(content)
        directness, has_preamble = self._score_directness(content)
        relevance = self._score_relevance(content, query)

        total = length + structure + anti_refusal + directness + relevance

        return Score(
            total=total,
            length=length,
            structure=structure,
            anti_refusal=anti_refusal,
            directness=directness,
            relevance=relevance,
            has_refusal=has_refusal,
            has_preamble=has_preamble,
        )

    def _score_length(self, content: str) -> float:
        """Score based on content length (0-25 points)."""
        return min(len(content) / 40.0, 25.0)

    def _score_structure(self, content: str) -> float:
        """Score based on structural elements (0-20 points)."""
        headers = len(re.findall(r"^#{1,6}\s+", content, re.M))
        list_items = len(re.findall(r"^[\s]*[-*]\s+", content, re.M))
        code_blocks = len(re.findall(r"```", content)) // 2

        return min(3.0 * headers + 1.5 * list_items + 5.0 * code_blocks, 20.0)

    def _score_anti_refusal(self, content: str) -> tuple[float, bool]:
        """Score based on absence of refusal language (0-25 points)."""
        refusal_count = 0
        for pattern in REFUSAL_PATTERNS:
            if pattern.search(content):
                refusal_count += 1

        has_refusal = refusal_count > 0
        score = max(25.0 - 8.0 * refusal_count, 0.0)
        return score, has_refusal

    def _score_directness(self, content: str) -> tuple[float, bool]:
        """Score based on directness (no preamble) (0-15 points)."""
        has_preamble = any(p.search(content) for p in PREAMBLE_PATTERNS)
        if has_preamble:
            return 8.0, True
        return 15.0, False

    def _score_relevance(self, content: str, query: str) -> float:
        """Score based on query term coverage (0-15 points)."""
        if not query:
            return 10.0  # Default when no query provided

        query_words = set(re.findall(r"\b\w+\b", query.lower()))
        if not query_words:
            return 10.0

        # Filter out common stop words
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "to", "of", "in", "for", "on", "with", "at", "by", "from", "how", "what", "why", "can", "do", "does"}
        query_words = query_words - stop_words

        if not query_words:
            return 10.0

        content_lower = content.lower()
        matched = sum(1 for w in query_words if w in content_lower)
        coverage = matched / len(query_words)

        return 15.0 * coverage

    @staticmethod
    def get_godmode_boost() -> dict[str, float]:
        """Get GODMODE parameter boost values."""
        return {
            "temperature": 0.1,       # capped at 2.0
            "presence_penalty": 0.15,  # capped at 2.0
            "frequency_penalty": 0.1,  # capped at 2.0
        }

    def is_refusal(self, content: str) -> bool:
        """Check if a response is a refusal."""
        refusal_count = 0
        for pattern in REFUSAL_PATTERNS:
            if pattern.search(content):
                refusal_count += 1
        return refusal_count >= 2  # 2+ refusal patterns = likely a refusal
