"""
ThinkGate — Pre-answer judgment system for KantorKu Library Archivist.

The ThinkGate evaluates whether the Archivist should answer a question
directly, ask for clarification, escalate to a broader search, or defer.
It acts as a reasoning checkpoint before the Archivist synthesizes a response.

Decision flow:
    1. Clarify objective — extract core question from query
    2. Check context sufficiency — are entries relevant enough?
    3. Assess uncertainty — conflicting entries, low similarity, sparse results
    4. Choose action — answer_direct, ask_clarification, escalate_search, defer
    5. Generate output — judgment summary, decision, confidence, recommended stance
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from kantorku.library.core.models import LibraryEntry

logger = logging.getLogger(__name__)


class ThinkAction(str, Enum):
    """Possible actions the ThinkGate can recommend."""

    ANSWER_DIRECT = "answer_direct"
    ASK_CLARIFICATION = "ask_clarification"
    ESCALATE_SEARCH = "escalate_search"
    DEFER = "defer"


@dataclass
class ThinkResult:
    """Result of a ThinkGate evaluation."""

    judgment_summary: str = ""
    decision: ThinkAction = ThinkAction.ANSWER_DIRECT
    confidence: float = 0.0
    recommended_stance: str = ""
    core_question: str = ""
    context_sufficiency: float = 0.0
    uncertainty_score: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)


class ThinkGate:
    """Pre-answer judgment system for the Archivist.

    Evaluates whether the Archivist has enough context to answer
    confidently, and recommends the best course of action.

    Example::

        gate = ThinkGate()
        result = gate.evaluate(
            query="How do I fix a Python ImportError?",
            context_entries=retrieved_entries,
            confidence=0.75,
        )
        if result.decision == ThinkAction.ANSWER_DIRECT:
            # Proceed with answering
            ...
        elif result.decision == ThinkAction.ESCALATE_SEARCH:
            # Broaden the search
            ...
    """

    # Minimum similarity for an entry to be considered relevant
    SIMILARITY_THRESHOLD: float = 0.5

    # Minimum number of relevant entries for confident answering
    MIN_RELEVANT_ENTRIES: int = 1

    def evaluate(
        self,
        query: str,
        context_entries: list[LibraryEntry],
        confidence: float,
    ) -> ThinkResult:
        """Evaluate whether to answer, clarify, escalate, or defer.

        Performs a 5-step evaluation:
        1. Clarify objective — extract the core question
        2. Check context sufficiency — are entries relevant enough?
        3. Assess uncertainty — compute uncertainty from multiple signals
        4. Choose action — select the best course of action
        5. Generate output — produce the ThinkResult

        Args:
            query: The user's original question.
            context_entries: Retrieved Library entries with similarity info.
            confidence: The initial confidence score from the search.

        Returns:
            A ThinkResult with the judgment and recommended action.
        """
        # Step 1: Clarify objective
        core_question = self._extract_core_question(query)

        # Step 2: Check context sufficiency
        relevant_count = sum(
            1 for e in context_entries
            if getattr(e, "_similarity", 0.0) > self.SIMILARITY_THRESHOLD
        )
        context_sufficiency = self._compute_context_sufficiency(
            context_entries, relevant_count
        )

        # Step 3: Assess uncertainty
        uncertainty = self._compute_uncertainty(
            context_entries, confidence, relevant_count
        )

        # Step 4: Choose action
        decision = self._choose_action(
            context_sufficiency, uncertainty, confidence, relevant_count
        )

        # Step 5: Generate output
        recommended_stance = self._get_recommended_stance(decision, confidence)
        judgment_summary = self._build_judgment_summary(
            core_question, decision, context_sufficiency, uncertainty, relevant_count
        )

        result = ThinkResult(
            judgment_summary=judgment_summary,
            decision=decision,
            confidence=confidence,
            recommended_stance=recommended_stance,
            core_question=core_question,
            context_sufficiency=context_sufficiency,
            uncertainty_score=uncertainty,
            details={
                "relevant_entries": relevant_count,
                "total_entries": len(context_entries),
                "avg_quality": (
                    sum(e.quality_score for e in context_entries) / len(context_entries)
                    if context_entries else 0.0
                ),
            },
        )

        logger.debug(
            "ThinkGate: decision=%s, confidence=%.2f, sufficiency=%.2f, "
            "uncertainty=%.2f, relevant=%d",
            decision.value,
            confidence,
            context_sufficiency,
            uncertainty,
            relevant_count,
        )

        return result

    def _extract_core_question(self, query: str) -> str:
        """Extract the core question from a query string.

        Removes filler words and extracts the essential question.

        Args:
            query: The original query text.

        Returns:
            A simplified core question string.
        """
        # Remove common prefixes
        core = query.strip()
        prefixes = [
            r"^(can you |could you |please |i want to know |i need to know |"
            r"tell me |show me |explain |help me understand )",
            r"^(how do i |how to |what is |what are |why does |why do |"
            r"where can i |when should )",
        ]
        for prefix in prefixes:
            core = re.sub(prefix, "", core, flags=re.IGNORECASE).strip()

        # Remove trailing question marks
        core = core.rstrip("?").strip()

        # Take the first sentence if there are multiple
        if "." in core:
            core = core.split(".")[0].strip()

        # Truncate if too long
        if len(core) > 200:
            core = core[:197] + "..."

        return core if core else query.strip()

    def _compute_context_sufficiency(
        self,
        entries: list[LibraryEntry],
        relevant_count: int,
    ) -> float:
        """Compute how sufficient the context is for answering.

        Args:
            entries: The retrieved entries.
            relevant_count: Number of entries above the similarity threshold.

        Returns:
            A sufficiency score between 0.0 and 1.0.
        """
        if not entries:
            return 0.0

        # Factor 1: Relevant entry ratio
        relevant_ratio = relevant_count / max(len(entries), 1)

        # Factor 2: Average quality of entries
        avg_quality = sum(e.quality_score for e in entries) / len(entries)

        # Factor 3: Entry count adequacy
        count_factor = min(len(entries) / 5.0, 1.0)

        # Weighted combination
        sufficiency = (
            0.4 * relevant_ratio
            + 0.35 * avg_quality
            + 0.25 * count_factor
        )

        return min(max(sufficiency, 0.0), 1.0)

    def _compute_uncertainty(
        self,
        entries: list[LibraryEntry],
        confidence: float,
        relevant_count: int,
    ) -> float:
        """Compute an uncertainty score from multiple signals.

        Signals:
        - Conflicting entries (different types for the same query)
        - Low similarity (few relevant entries)
        - Sparse results (very few entries retrieved)
        - Low confidence from search

        Args:
            entries: The retrieved entries.
            confidence: The initial confidence score.
            relevant_count: Number of relevant entries.

        Returns:
            An uncertainty score between 0.0 (certain) and 1.0 (very uncertain).
        """
        uncertainty = 0.0

        # Signal 1: Conflicting entry types
        if entries:
            types = set(e.entry_type for e in entries)
            if len(types) > 2:
                uncertainty += 0.2

        # Signal 2: Low similarity — few relevant entries
        if relevant_count == 0:
            uncertainty += 0.4
        elif relevant_count == 1:
            uncertainty += 0.15

        # Signal 3: Sparse results
        if len(entries) == 0:
            uncertainty += 0.4
        elif len(entries) < 3:
            uncertainty += 0.15

        # Signal 4: Low confidence from search
        if confidence < 0.3:
            uncertainty += 0.3
        elif confidence < 0.5:
            uncertainty += 0.15

        # Signal 5: Low average quality
        if entries:
            avg_quality = sum(e.quality_score for e in entries) / len(entries)
            if avg_quality < 0.3:
                uncertainty += 0.15
            elif avg_quality < 0.5:
                uncertainty += 0.05

        return min(uncertainty, 1.0)

    def _choose_action(
        self,
        context_sufficiency: float,
        uncertainty: float,
        confidence: float,
        relevant_count: int,
    ) -> ThinkAction:
        """Choose the best action based on evaluation signals.

        Decision logic:
        - answer_direct: High confidence, sufficient context, low uncertainty
        - ask_clarification: Ambiguous query, conflicting signals
        - escalate_search: Insufficient context, need more information
        - defer: High uncertainty, cannot reliably answer

        Args:
            context_sufficiency: How sufficient the context is.
            uncertainty: The computed uncertainty score.
            confidence: The initial confidence score.
            relevant_count: Number of relevant entries.

        Returns:
            The recommended ThinkAction.
        """
        # High confidence path
        if confidence >= 0.7 and context_sufficiency >= 0.6 and uncertainty <= 0.3:
            return ThinkAction.ANSWER_DIRECT

        # Moderate confidence — can still answer if context is adequate
        if confidence >= 0.5 and relevant_count >= self.MIN_RELEVANT_ENTRIES:
            if uncertainty <= 0.4:
                return ThinkAction.ANSWER_DIRECT

        # Ambiguous — need clarification
        if uncertainty > 0.5 and confidence >= 0.3:
            return ThinkAction.ASK_CLARIFICATION

        # Insufficient context — escalate to broader search
        if context_sufficiency < 0.3 or relevant_count == 0:
            if confidence >= 0.2:
                return ThinkAction.ESCALATE_SEARCH

        # Very uncertain — defer
        return ThinkAction.DEFER

    @staticmethod
    def _get_recommended_stance(decision: ThinkAction, confidence: float) -> str:
        """Get a human-readable recommended stance for the Archivist.

        Args:
            decision: The chosen action.
            confidence: The confidence score.

        Returns:
            A stance description string.
        """
        stances: dict[ThinkAction, str] = {
            ThinkAction.ANSWER_DIRECT: (
                "Answer confidently with citations from the Library. "
                "Present information as verified knowledge."
            ),
            ThinkAction.ASK_CLARIFICATION: (
                "Answer tentatively and ask the user to clarify their "
                "question for a more precise response."
            ),
            ThinkAction.ESCALATE_SEARCH: (
                "Inform the user that the Library lacks sufficient "
                "information and suggest broadening the search or "
                "adding more knowledge."
            ),
            ThinkAction.DEFER: (
                "Decline to answer due to high uncertainty. Suggest "
                "the user consult additional sources or rephrase."
            ),
        }
        return stances.get(decision, "Answer with appropriate caution.")

    @staticmethod
    def _build_judgment_summary(
        core_question: str,
        decision: ThinkAction,
        context_sufficiency: float,
        uncertainty: float,
        relevant_count: int,
    ) -> str:
        """Build a human-readable judgment summary.

        Args:
            core_question: The extracted core question.
            decision: The chosen action.
            context_sufficiency: Context sufficiency score.
            uncertainty: Uncertainty score.
            relevant_count: Number of relevant entries.

        Returns:
            A judgment summary string.
        """
        return (
            f"Core question: '{core_question}' | "
            f"Decision: {decision.value} | "
            f"Sufficiency: {context_sufficiency:.0%} | "
            f"Uncertainty: {uncertainty:.0%} | "
            f"Relevant entries: {relevant_count}"
        )
