"""
Opinionated Defaults — O19: Enforce opinionated recommendations.

Ensures the Conductor always takes a position rather than being
non-committal. Validates responses for assertiveness and enforces
explicit recommendations.

Like a senior manager who doesn't say "it depends" — they give
you a clear recommendation with reasoning.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Recommendation:
    """A structured recommendation."""
    primary_choice: str = ""
    technical_reasoning: str = ""
    alternatives: list[str] = field(default_factory=list)
    assertiveness_score: float = 0.0


# Non-committal language patterns
_NON_COMMITTAL_PATTERNS: list[str] = [
    r"it\s+depends",
    r"could\s+go\s+either\s+way",
    r"both\s+options\s+are\s+valid",
    r"either\s+approach\s+works",
    r"no\s+clear\s+(?:winner|choice|preference)",
    r"(?:hard|difficult)\s+to\s+say",
    r"there\s+is\s+no\s+(?:right|wrong|best)",
    r"(?:matter|matters)\s+of\s+(?:preference|taste|opinion)",
    r"up\s+to\s+you",
    r"(?:your|you)\s+call",
    r"(?:i\s+)?(?:wouldn't|cannot)\s+(?:recommend|say|choose)",
]

# Assertiveness indicator patterns
_ASSERTIVE_PATTERNS: list[str] = [
    r"i\s+recommend",
    r"the\s+best\s+(?:approach|choice|option)\s+is",
    r"go\s+with",
    r"use\s+",
    r"choose\s+",
    r"prefer\s+",
    r"should\s+",
    r"must\s+",
    r"definitely",
    r"clearly",
    r"without\s+(?:a\s+)?doubt",
]


class OpinionatedDefaults:
    """
    Opinionated Defaults — enforce clear recommendations.

    Ensures the Conductor always provides:
    - A primary choice/recommendation
    - Technical reasoning for the choice
    - Alternatives (but as alternatives, not equals)
    - High assertiveness score

    Usage:
        od = OpinionatedDefaults()
        rec = od.format_recommendation("Use FastAPI", "Better async support", ["Flask", "Django"])
        has_rec, has_reason, is_non_committal = od.validate_response(response_text)
        modified = od.enforce_conductor_position(response_text)
        score = od.score_assertiveness(response_text)
    """

    def format_recommendation(
        self,
        primary: str,
        reasoning: str,
        alternatives: list[str] | None = None,
    ) -> Recommendation:
        """
        Format a structured recommendation.

        Args:
            primary: The primary recommended choice
            reasoning: Technical reasoning for the choice
            alternatives: Optional list of alternatives

        Returns:
            Recommendation with assertiveness score
        """
        alternatives = alternatives or []

        # Calculate assertiveness based on content
        score = 0.5  # Base score for having a recommendation
        if primary:
            score += 0.2
        if reasoning:
            score += 0.2
        if alternatives and len(alternatives) <= 2:
            score += 0.1  # Having 1-2 alternatives is good, more is wishy-washy

        return Recommendation(
            primary_choice=primary,
            technical_reasoning=reasoning,
            alternatives=alternatives,
            assertiveness_score=min(1.0, score),
        )

    def validate_response(
        self, response_text: str
    ) -> tuple[bool, bool, bool]:
        """
        Validate a response for recommendation quality.

        Args:
            response_text: The response text to validate

        Returns:
            Tuple of (has_recommendation, has_reasoning, is_non_committal)
        """
        if not response_text:
            return False, False, True

        text_lower = response_text.lower()

        # Check for recommendation
        has_recommendation = bool(re.search(
            r"(recommend|suggest|go with|use|choose|prefer|should|best approach|best option)",
            text_lower,
        ))

        # Check for reasoning
        has_reasoning = bool(re.search(
            r"(because|since|due to|reason|rationale|advantage|benefit|because of|as it)",
            text_lower,
        ))

        # Check for non-committal language
        is_non_committal = any(
            re.search(pattern, text_lower)
            for pattern in _NON_COMMITTAL_PATTERNS
        )

        return has_recommendation, has_reasoning, is_non_committal

    def enforce_conductor_position(
        self, conductor_response: str
    ) -> str:
        """
        Modify a response to enforce an explicit position.

        If the response is non-committal, adds a clear recommendation
        prefix. If it already has a position, ensures it's prominent.

        Args:
            conductor_response: The original conductor response

        Returns:
            Modified response with explicit position
        """
        if not conductor_response:
            return "RECOMMENDATION: Unable to provide a recommendation — insufficient context. Please provide more details."

        has_rec, has_reason, is_non_committal = self.validate_response(conductor_response)

        if is_non_committal:
            # Extract the most specific option mentioned
            options = re.findall(
                r"(?:option|alternative|approach)\s+\d+[:\s]+([^\n,]+)",
                conductor_response,
                re.IGNORECASE,
            )

            # Try to find the first mentioned technology/tool
            if not options:
                options = re.findall(
                    r"\b([A-Z][a-zA-Z]+(?:\.js|\.py|\.rs)?)\b",
                    conductor_response,
                )

            if options:
                primary = options[0].strip()
                position = (
                    f"RECOMMENDATION: {primary}\n\n"
                    f"Reasoning: Based on the available options, {primary} "
                    f"is the recommended choice for this use case.\n\n"
                )
                return position + conductor_response
            else:
                return (
                    "RECOMMENDATION: A specific approach is needed but none was clearly identified. "
                    "Please clarify the requirements so a definitive recommendation can be made.\n\n"
                    + conductor_response
                )

        if not has_rec:
            # Response has content but no clear recommendation
            return (
                "RECOMMENDATION: Based on the analysis above, proceed with the most direct approach.\n\n"
                + conductor_response
            )

        if not has_reason:
            # Has recommendation but no reasoning
            return conductor_response + "\n\nReasoning: This approach minimizes complexity while meeting the requirements."

        return conductor_response

    def score_assertiveness(self, response_text: str) -> float:
        """
        Score the assertiveness of a response (0.0 - 1.0).

        Higher score = more assertive (clear recommendation with reasoning).
        Lower score = more non-committal (vague, hedging).

        Args:
            response_text: The response text to score

        Returns:
            Assertiveness score (0.0 - 1.0)
        """
        if not response_text:
            return 0.0

        text_lower = response_text.lower()
        score = 0.5  # Neutral starting point

        # Positive: assertive language
        for pattern in _ASSERTIVE_PATTERNS:
            if re.search(pattern, text_lower):
                score += 0.1

        # Negative: non-committal language
        for pattern in _NON_COMMITTAL_PATTERNS:
            if re.search(pattern, text_lower):
                score -= 0.15

        # Positive: structured recommendation
        has_rec, has_reason, _ = self.validate_response(response_text)
        if has_rec:
            score += 0.1
        if has_reason:
            score += 0.1

        return max(0.0, min(1.0, score))
