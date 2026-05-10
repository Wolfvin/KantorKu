"""
Office Think Gate — O9: Pre-execution thinking and context sufficiency check.

The Think Gate ensures the office doesn't jump into action without
sufficient context. It answers: "Should we proceed, or do we need more info?"

Like a wise manager: "Hold on, do we actually understand what we're doing
before we start doing it?"

5-step evaluation:
1. Clarify the objective
2. Check context sufficiency
3. Assess uncertainty
4. Choose action (GO / NO_GO / NEEDS_MORE_CONTEXT)
5. Generate structured output
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ThinkAction(Enum):
    """Possible outcomes of a think gate evaluation."""
    GO = "go"
    NO_GO = "no_go"
    NEEDS_MORE_CONTEXT = "needs_more_context"


@dataclass
class ThinkResult:
    """Result of a think gate evaluation."""
    action: ThinkAction = ThinkAction.NEEDS_MORE_CONTEXT
    judgment_summary: str = ""
    confidence: float = 0.0
    context_gaps: list[str] = field(default_factory=list)
    recommended_stance: str = ""


# Common stopwords for keyword extraction
_STOPWORDS: set[str] = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "each",
    "every", "both", "few", "more", "most", "other", "some", "such", "no",
    "nor", "not", "only", "own", "same", "so", "than", "too", "very",
    "just", "because", "but", "and", "or", "if", "while", "about", "up",
    "it", "its", "i", "me", "my", "we", "our", "you", "your", "he", "him",
    "his", "she", "her", "they", "them", "their", "this", "that", "these",
    "those", "what", "which", "who", "whom", "whose",
}

# Sufficiency threshold for keyword overlap
_OVERLAP_THRESHOLD: float = 0.3

# Phases where different evaluation criteria apply
_PHASE_WEIGHTS: dict[str, dict[str, float]] = {
    "understanding": {"context_sufficiency": 0.5, "uncertainty": 0.3, "clarity": 0.2},
    "planning": {"context_sufficiency": 0.3, "uncertainty": 0.4, "clarity": 0.3},
    "execution": {"context_sufficiency": 0.2, "uncertainty": 0.5, "clarity": 0.3},
}


class OfficeThinkGate:
    """
    Office Think Gate — pre-execution thinking and context sufficiency check.

    Ensures the office doesn't jump into action without sufficient context.
    Evaluates objectives at multiple points: before planning, before briefing,
    and before execution.

    Usage:
        gate = OfficeThinkGate()
        result = gate.evaluate("Build a rate limiter", {"language": "rust"}, "planning")
        if result.action == ThinkAction.NEEDS_MORE_CONTEXT:
            print(f"Gaps: {result.context_gaps}")
    """

    def _extract_keywords(self, text: str) -> set[str]:
        """
        Extract meaningful keywords from text by tokenizing and removing stopwords.

        Args:
            text: Input text

        Returns:
            Set of unique keyword tokens (lowercase)
        """
        if not text:
            return set()
        # Tokenize: split on non-alphanumeric, lowercase
        tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text.lower())
        return {t for t in tokens if t not in _STOPWORDS and len(t) > 1}

    def _compute_overlap(self, set_a: set[str], set_b: set[str]) -> float:
        """
        Compute keyword overlap ratio between two sets.

        Uses Jaccard-like overlap: |intersection| / |union|.

        Args:
            set_a: First keyword set
            set_b: Second keyword set

        Returns:
            Overlap ratio (0.0 - 1.0)
        """
        if not set_a or not set_b:
            return 0.0
        intersection = set_a & set_b
        union = set_a | set_b
        return len(intersection) / len(union) if union else 0.0

    def _check_sufficiency(
        self, objective: str, context: dict[str, Any]
    ) -> tuple[float, list[str]]:
        """
        Check if context is sufficient for the objective.

        Looks at keyword overlap between objective and context values.
        Returns a sufficiency score and list of gaps.

        Args:
            objective: The objective text
            context: Available context dict

        Returns:
            Tuple of (sufficiency_score, list of gaps)
        """
        obj_keywords = self._extract_keywords(objective)
        if not obj_keywords:
            return 0.0, ["Objective is empty or has no meaningful keywords"]

        # Combine all context values into a single text
        context_text = " ".join(str(v) for v in context.values() if v)
        ctx_keywords = self._extract_keywords(context_text)

        overlap = self._compute_overlap(obj_keywords, ctx_keywords)

        # Find gaps: objective keywords not covered by context
        gaps = []
        uncovered = obj_keywords - ctx_keywords
        if uncovered:
            gaps.append(f"Missing context for: {', '.join(sorted(uncovered)[:10])}")

        # Check for missing key categories in context
        expected_keys = {"language", "framework", "requirements", "spec"}
        missing_keys = expected_keys - set(context.keys())
        if missing_keys:
            gaps.append(f"Missing context keys: {', '.join(sorted(missing_keys))}")

        return overlap, gaps

    def _assess_uncertainty(
        self, objective: str, context: dict[str, Any]
    ) -> tuple[float, list[str]]:
        """
        Assess uncertainty level based on conflicting signals and missing info.

        Args:
            objective: The objective text
            context: Available context dict

        Returns:
            Tuple of (uncertainty_score 0.0-1.0, list of uncertainty signals)
        """
        signals: list[str] = []
        uncertainty = 0.0

        # Check for conflicting signals in context
        context_str = str(context).lower()
        obj_lower = objective.lower()

        # Ambiguous goal indicators
        ambiguous_words = ["maybe", "perhaps", "might", "could be", "not sure", "or", "either"]
        amb_count = sum(1 for w in ambiguous_words if w in obj_lower)
        if amb_count > 0:
            uncertainty += 0.2 * min(amb_count, 3)
            signals.append("Ambiguous goal language detected")

        # Missing requirements
        if "requirement" not in context_str and "spec" not in context_str:
            uncertainty += 0.15
            signals.append("No requirements or spec provided")

        # Conflicting signals
        if "frontend" in context_str and "backend" in context_str:
            if "fullstack" not in context_str and "both" not in obj_lower:
                uncertainty += 0.1
                signals.append("Potentially conflicting frontend/backend signals")

        # Empty or minimal context
        if not context or all(not v for v in context.values()):
            uncertainty += 0.3
            signals.append("Context is empty or minimal")

        return min(1.0, uncertainty), signals

    def evaluate(
        self,
        objective: str,
        context: dict[str, Any] | None = None,
        phase: str = "understanding",
    ) -> ThinkResult:
        """
        Evaluate an objective with the 5-step think process.

        Steps:
        1. Clarify the objective
        2. Check context sufficiency
        3. Assess uncertainty
        4. Choose action (GO / NO_GO / NEEDS_MORE_CONTEXT)
        5. Generate structured output

        Args:
            objective: The objective or task description
            context: Available context information
            phase: Current phase (understanding, planning, execution)

        Returns:
            ThinkResult with action, confidence, and gaps
        """
        context = context or {}

        # Step 1: Clarify
        if not objective or not objective.strip():
            return ThinkResult(
                action=ThinkAction.NO_GO,
                judgment_summary="Objective is empty — cannot proceed",
                confidence=0.0,
                context_gaps=["No objective provided"],
                recommended_stance="Request clarification from client",
            )

        # Step 2: Check sufficiency
        sufficiency, gaps = self._check_sufficiency(objective, context)

        # Step 3: Assess uncertainty
        uncertainty, uncertainty_signals = self._assess_uncertainty(objective, context)

        all_gaps = gaps + uncertainty_signals

        # Step 4: Choose action
        weights = _PHASE_WEIGHTS.get(phase, _PHASE_WEIGHTS["understanding"])

        confidence = (
            sufficiency * weights.get("context_sufficiency", 0.3)
            + (1.0 - uncertainty) * weights.get("uncertainty", 0.4)
            + (1.0 if gaps else 0.5) * weights.get("clarity", 0.3)
        )
        confidence = max(0.0, min(1.0, confidence))

        if confidence >= 0.7 and not all_gaps:
            action = ThinkAction.GO
            stance = "Proceed with current context"
        elif confidence >= 0.4 or (sufficiency >= _OVERLAP_THRESHOLD and uncertainty < 0.5):
            action = ThinkAction.NEEDS_MORE_CONTEXT
            stance = "Gather more context before proceeding"
        else:
            action = ThinkAction.NO_GO
            stance = "Insufficient context — do not proceed without clarification"

        # Step 5: Generate output
        summary = (
            f"Phase: {phase} | Sufficiency: {sufficiency:.2f} | "
            f"Uncertainty: {uncertainty:.2f} | Confidence: {confidence:.2f}"
        )

        return ThinkResult(
            action=action,
            judgment_summary=summary,
            confidence=confidence,
            context_gaps=all_gaps,
            recommended_stance=stance,
        )

    def evaluate_before_plan(self, client_message: str) -> ThinkResult:
        """
        Evaluate before drafting a plan.

        Convenience method that checks if we have enough context
        to create a meaningful plan.

        Args:
            client_message: The client's message/request

        Returns:
            ThinkResult with evaluation
        """
        return self.evaluate(
            objective=client_message,
            context={"client_message": client_message},
            phase="planning",
        )

    def evaluate_before_briefing(self, plan: dict[str, Any] | str) -> ThinkResult:
        """
        Evaluate before opening a briefing session.

        Checks if the plan has enough detail for a productive briefing.

        Args:
            plan: The execution plan (dict or string)

        Returns:
            ThinkResult with evaluation
        """
        if isinstance(plan, dict):
            plan_text = " ".join(str(v) for v in plan.values() if v)
            context = plan
        else:
            plan_text = str(plan)
            context = {"plan": plan_text}

        return self.evaluate(
            objective=plan_text,
            context=context,
            phase="planning",
        )

    def evaluate_before_execute(
        self, task_description: str, worker_context: dict[str, Any] | None = None
    ) -> ThinkResult:
        """
        Evaluate before executing a task.

        Checks if the worker has enough context to execute the task.

        Args:
            task_description: Description of the task to execute
            worker_context: Context available to the worker

        Returns:
            ThinkResult with evaluation
        """
        return self.evaluate(
            objective=task_description,
            context=worker_context or {},
            phase="execution",
        )


# Alias for backward compatibility with conductor.py import
Judgment = ThinkResult
