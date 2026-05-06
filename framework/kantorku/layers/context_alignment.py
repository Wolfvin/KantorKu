"""
Context Alignment Gate — O20: Ensure output stays aligned with the original request.

Checks that what's being produced actually matches what was asked for.
Detects off-topic drift and can force rewrites when alignment is lost.

Like a proofreader who catches when the writer has wandered off-topic
from the original assignment.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AlignmentResult:
    """Result of a context alignment check."""
    score: float = 1.0
    is_aligned: bool = True
    misalignment_points: list[str] = field(default_factory=list)
    should_rewrite: bool = False


# Common stopwords for keyword extraction
_STOPWORDS: set[str] = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "into", "through",
    "during", "before", "after", "above", "below", "between", "out",
    "off", "over", "under", "again", "further", "then", "once", "here",
    "there", "when", "where", "why", "how", "all", "each", "every",
    "both", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "just",
    "because", "but", "and", "or", "if", "while", "about", "up", "it",
    "its", "i", "me", "my", "we", "our", "you", "your", "he", "him",
    "his", "she", "her", "they", "them", "their", "this", "that",
    "these", "those", "what", "which", "who", "whom", "whose",
}

# Consecutive miss threshold for halting
_HALT_MISS_THRESHOLD = 2


class ContextAlignmentGate:
    """
    Context Alignment Gate — ensure output stays on-topic.

    Checks alignment between original requests and current output
    using keyword overlap and Jaccard similarity. Tracks per-worker
    context misses and can recommend halting when alignment is
    consistently lost.

    Usage:
        gate = ContextAlignmentGate()
        result = gate.check_alignment("Build a REST API", "Here's a GraphQL schema...")
        score = gate.compute_alignment_score(request_keywords, output_keywords)
        is_off = gate.detect_off_topic(request, output)
    """

    def __init__(self) -> None:
        self._miss_tracker: dict[str, dict[str, int]] = {}  # worker_id → {session_id → count}

    def _extract_keywords(self, text: str) -> set[str]:
        """
        Extract keywords from text: tokenize, remove stopwords, get unique tokens.

        Args:
            text: Input text

        Returns:
            Set of unique keyword tokens (lowercase)
        """
        if not text:
            return set()
        tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text.lower())
        return {t for t in tokens if t not in _STOPWORDS and len(t) > 1}

    def compute_alignment_score(
        self, request_keywords: set[str], output_keywords: set[str]
    ) -> float:
        """
        Compute alignment score between request and output keywords.

        Uses a combination of Jaccard similarity and direct overlap
        ratio for a robust alignment measure.

        Args:
            request_keywords: Keywords from the original request
            output_keywords: Keywords from the current output

        Returns:
            Alignment score (0.0 - 1.0)
        """
        if not request_keywords and not output_keywords:
            return 1.0
        if not request_keywords or not output_keywords:
            return 0.0

        # Jaccard similarity
        intersection = request_keywords & output_keywords
        union = request_keywords | output_keywords
        jaccard = len(intersection) / len(union) if union else 0.0

        # Overlap ratio (what fraction of request keywords are covered)
        overlap = len(intersection) / len(request_keywords) if request_keywords else 0.0

        # Weighted combination: overlap is more important than Jaccard
        # because we care more about request coverage than output breadth
        return 0.4 * jaccard + 0.6 * overlap

    def check_alignment(
        self,
        original_request: str,
        current_output: str,
    ) -> AlignmentResult:
        """
        Check if current output is aligned with the original request.

        Args:
            original_request: The original client request
            current_output: The current output being produced

        Returns:
            AlignmentResult with score, alignment status, and misalignment points
        """
        if not original_request:
            return AlignmentResult(
                score=1.0,
                is_aligned=True,
                misalignment_points=[],
                should_rewrite=False,
            )

        if not current_output:
            return AlignmentResult(
                score=0.0,
                is_aligned=False,
                misalignment_points=["No output produced"],
                should_rewrite=True,
            )

        req_keywords = self._extract_keywords(original_request)
        out_keywords = self._extract_keywords(current_output)

        score = self.compute_alignment_score(req_keywords, out_keywords)

        # Find misalignment points
        misalignment_points: list[str] = []

        # Keywords in output not related to request (potential drift)
        extra_keywords = out_keywords - req_keywords
        if len(extra_keywords) > len(req_keywords) * 1.5:
            misalignment_points.append(
                f"Output has significantly more unique concepts ({len(extra_keywords)}) "
                f"than the request ({len(req_keywords)}) — possible scope expansion"
            )

        # Critical request keywords missing from output
        missing_critical = req_keywords - out_keywords
        if missing_critical:
            # Filter to likely important keywords (longer, more specific)
            important_missing = {kw for kw in missing_critical if len(kw) >= 5}
            if important_missing:
                misalignment_points.append(
                    f"Missing important concepts from request: {', '.join(sorted(important_missing)[:5])}"
                )

        # Determine alignment
        is_aligned = score >= 0.3
        should_rewrite = score < 0.2 and len(misalignment_points) >= 2

        return AlignmentResult(
            score=score,
            is_aligned=is_aligned,
            misalignment_points=misalignment_points,
            should_rewrite=should_rewrite,
        )

    def detect_off_topic(
        self,
        request: str,
        output: str,
        threshold: float = 0.3,
    ) -> bool:
        """
        Detect if output is off-topic relative to the request.

        Args:
            request: The original request
            output: The current output
            threshold: Alignment score threshold (below = off-topic)

        Returns:
            True if the output appears off-topic
        """
        if not request:
            return False

        req_keywords = self._extract_keywords(request)
        out_keywords = self._extract_keywords(output)
        score = self.compute_alignment_score(req_keywords, out_keywords)

        return score < threshold

    def force_rewrite(
        self,
        request: str,
        output: str,
        misalignment_points: list[str] | None = None,
    ) -> str:
        """
        Generate a rewrite instruction string.

        Args:
            request: The original request
            output: The current (misaligned) output
            misalignment_points: Specific points of misalignment

        Returns:
            Rewrite instruction string
        """
        points_text = ""
        for point in (misalignment_points or []):
            points_text += f"- {point}\n"

        req_keywords = self._extract_keywords(request)
        keywords_str = ", ".join(sorted(req_keywords)[:10])

        return (
            f"REWRITE REQUIRED: Output has drifted from the original request.\n\n"
            f"Original request: {request}\n\n"
            f"Key concepts to cover: {keywords_str}\n\n"
            f"Misalignment issues:\n"
            f"{points_text if points_text else '- Output does not align with request scope'}\n"
            f"Please rewrite the output to directly address the original request, "
            f"focusing on the key concepts listed above."
        )

    def track_context_miss(
        self, worker_id: str, session_id: str
    ) -> int:
        """
        Track a context miss for a worker in a session.

        Args:
            worker_id: Worker that missed context
            session_id: Session where miss occurred

        Returns:
            Updated miss count for this worker+session
        """
        if worker_id not in self._miss_tracker:
            self._miss_tracker[worker_id] = {}
        if session_id not in self._miss_tracker[worker_id]:
            self._miss_tracker[worker_id][session_id] = 0

        self._miss_tracker[worker_id][session_id] += 1
        return self._miss_tracker[worker_id][session_id]

    def should_halt(self, miss_count: int) -> bool:
        """
        Determine if execution should halt based on miss count.

        Halt at 2 consecutive misses.

        Args:
            miss_count: Number of consecutive context misses

        Returns:
            True if execution should halt
        """
        return miss_count >= _HALT_MISS_THRESHOLD

    def get_miss_count(self, worker_id: str, session_id: str) -> int:
        """
        Get the context miss count for a worker+session.

        Args:
            worker_id: Worker identifier
            session_id: Session identifier

        Returns:
            Current miss count
        """
        return self._miss_tracker.get(worker_id, {}).get(session_id, 0)

    def reset_miss_count(self, worker_id: str, session_id: str) -> None:
        """
        Reset the context miss count for a worker+session.

        Args:
            worker_id: Worker identifier
            session_id: Session identifier
        """
        if worker_id in self._miss_tracker:
            self._miss_tracker[worker_id].pop(session_id, None)
