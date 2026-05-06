"""
Review Anti-Ribet — O17: Anti-over-engineering review and spec alignment.

Enforces the principle that the simplest approach should always be
tried first. Validates output against specs and flags over-engineering.

"Ribet" is Indonesian for "complicated/fussy" — this module
keeps things simple.

Like a senior dev who says: "Why are you adding a message queue
for a CRUD app with 10 users?"
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# Core anti-ribet principles
PRINCIPLES: dict[str, str] = {
    "simplest_approach_first": "Always try the simplest approach before considering alternatives",
    "follow_spec_exactly": "Implement exactly what the spec says — nothing more",
    "no_extra_architecture": "Don't add architectural patterns not required by the spec",
    "re_read_before_patch": "Re-read the spec/issue before making changes",
    "blocker_disagreement_for_high_impact": "Block changes that disagree with spec for high-impact areas",
}


@dataclass
class ApproachScore:
    """Score for an approach evaluation."""
    simplicity: float = 1.0
    spec_alignment: float = 1.0
    blast_radius: float = 1.0
    total: float = 1.0


# Over-engineering indicator keywords
_OVER_ENGINEERING_INDICATORS: list[str] = [
    "design pattern", "factory", "abstract", "strategy pattern",
    "observer pattern", "visitor pattern", "decorator pattern",
    "enterprise", "microservice", "event-driven", "message queue",
    "cqrs", "event sourcing", "dependency injection container",
    "service locator", "plugin architecture", "middleware pipeline",
    "custom framework", "generic solution", "extensible",
    "future-proof", "scalable architecture",
]

# Simplicity indicators
_SIMPLICITY_INDICATORS: list[str] = [
    "direct", "simple", "straightforward", "minimal",
    "basic", "standard", "built-in", "native",
]


class ReviewAntiRibet:
    """
    Review Anti-Ribet — anti-over-engineering review and spec alignment.

    Enforces simplicity through:
    - Approach evaluation with simplicity/spec/blast-radius scoring
    - Spec alignment validation (matches, extra features, missing features)
    - Over-engineering detection
    - Alternative suggestion (simpler approach)

    Usage:
        reviewer = ReviewAntiRibet()
        score = reviewer.evaluate_approach("Add message queue", "Build todo app")
        is_over = reviewer.is_over_engineered("microservice architecture", "simple CRUD")
        matches, extra, missing = reviewer.validate_against_spec(output, spec)
    """

    def evaluate_approach(
        self,
        approach_description: str,
        task_spec: str | dict[str, Any] | None = None,
    ) -> ApproachScore:
        """
        Evaluate an approach on simplicity, spec alignment, and blast radius.

        Args:
            approach_description: Description of the proposed approach
            task_spec: The task specification to align against

        Returns:
            ApproachScore with individual and total scores (0.0-1.0, higher is better)
        """
        desc_lower = (approach_description or "").lower()
        spec_str = str(task_spec or "").lower()

        # Simplicity score: penalize over-engineering indicators
        simplicity = 1.0
        for indicator in _OVER_ENGINEERING_INDICATORS:
            if indicator in desc_lower:
                simplicity -= 0.15
        for indicator in _SIMPLICITY_INDICATORS:
            if indicator in desc_lower:
                simplicity += 0.1
        simplicity = max(0.0, min(1.0, simplicity))

        # Spec alignment: how much does the approach match the spec
        spec_alignment = 1.0
        if spec_str:
            spec_keywords = set(re.findall(r"\b\w{4,}\b", spec_str))
            approach_keywords = set(re.findall(r"\b\w{4,}\b", desc_lower))
            if spec_keywords:
                overlap = len(spec_keywords & approach_keywords) / len(spec_keywords)
                spec_alignment = 0.3 + 0.7 * overlap  # Floor at 0.3

            # Penalize extra concepts not in spec
            extra = approach_keywords - spec_keywords
            over_concepts = sum(1 for kw in extra if kw in " ".join(_OVER_ENGINEERING_INDICATORS))
            spec_alignment -= over_concepts * 0.1
            spec_alignment = max(0.0, min(1.0, spec_alignment))

        # Blast radius: lower is better (fewer files/components affected)
        blast_radius = 1.0
        file_count = len(re.findall(r"(file|module|component|service|class)", desc_lower))
        if file_count > 3:
            blast_radius -= (file_count - 3) * 0.1
        blast_radius = max(0.0, min(1.0, blast_radius))

        # Total: weighted combination
        total = simplicity * 0.4 + spec_alignment * 0.4 + blast_radius * 0.2

        return ApproachScore(
            simplicity=simplicity,
            spec_alignment=spec_alignment,
            blast_radius=blast_radius,
            total=total,
        )

    def suggest_alternative(
        self,
        current_approach: str,
        task_spec: str | dict[str, Any] | None = None,
    ) -> str:
        """
        Suggest a simpler alternative to the current approach.

        Args:
            current_approach: The current (possibly over-engineered) approach
            task_spec: The task specification

        Returns:
            Simpler alternative description
        """
        if not current_approach:
            return "Use the simplest possible approach"

        desc_lower = current_approach.lower()
        spec_str = str(task_spec or "").lower()

        alternatives: list[str] = []

        # Suggest simpler alternatives for common over-engineering patterns
        if "message queue" in desc_lower or "event-driven" in desc_lower:
            alternatives.append("Use direct function calls instead of message queue")
        if "microservice" in desc_lower:
            alternatives.append("Use a monolithic approach — split only when needed")
        if "factory pattern" in desc_lower:
            alternatives.append("Use direct instantiation — add factory only when needed")
        if "abstract" in desc_lower and "class" in desc_lower:
            alternatives.append("Use concrete classes — add abstraction only when needed")
        if "dependency injection" in desc_lower:
            alternatives.append("Use direct imports — add DI framework only if necessary")
        if "plugin architecture" in desc_lower:
            alternatives.append("Use simple module structure — add plugins when extensibility is needed")
        if "cqrs" in desc_lower:
            alternatives.append("Use standard CRUD — add CQRS only at scale")
        if "event sourcing" in desc_lower:
            alternatives.append("Use standard database — add event sourcing only if audit trail is required")

        if alternatives:
            return "; ".join(alternatives)

        # Generic fallback
        if task_spec:
            return f"Follow the spec directly: {task_spec[:100]}"
        return "Simplify: use the most direct approach that satisfies the requirements"

    def validate_against_spec(
        self,
        output: str | dict[str, Any] | None = None,
        spec: str | dict[str, Any] | None = None,
    ) -> tuple[bool, list[str], list[str]]:
        """
        Validate output against specification.

        Args:
            output: The output to validate (string or dict)
            spec: The specification to validate against

        Returns:
            Tuple of (matches_spec, extra_features, missing_features)
            where extra_features are things in output not in spec,
            and missing_features are things in spec not in output.
        """
        output_str = str(output or "").lower()
        spec_str = str(spec or "").lower()

        if not spec_str:
            return True, [], []

        # Extract keywords from spec and output
        spec_keywords = set(re.findall(r"\b\w{4,}\b", spec_str))
        output_keywords = set(re.findall(r"\b\w{4,}\b", output_str))

        # Remove common stopwords
        common_words = {
            "that", "this", "with", "from", "have", "been", "were",
            "will", "would", "could", "should", "about", "which",
            "their", "there", "other", "than", "then", "into",
        }
        spec_keywords -= common_words
        output_keywords -= common_words

        # Find extra features (in output but not in spec)
        extra = sorted(output_keywords - spec_keywords)
        # Filter to meaningful extras (over-engineering indicators)
        extra_features = [
            kw for kw in extra
            if any(ind in kw for ind in ["pattern", "abstract", "factory", "queue",
                                          "microservice", "plugin", "middleware",
                                          "enterprise", "framework"])
        ]

        # Find missing features (in spec but not in output)
        missing_keywords = spec_keywords - output_keywords
        missing_features = sorted(missing_keywords)

        # Determine if output matches spec
        matches_spec = len(missing_features) <= len(spec_keywords) * 0.2  # Allow 20% missing

        return matches_spec, extra_features, missing_features

    def is_over_engineered(
        self,
        approach: str,
        task: str | dict[str, Any] | None = None,
    ) -> bool:
        """
        Check if an approach is over-engineered for the given task.

        Args:
            approach: The proposed approach description
            task: The task description or spec

        Returns:
            True if the approach appears over-engineered
        """
        if not approach:
            return False

        score = self.evaluate_approach(approach, task)

        # If total score is below 0.5, it's likely over-engineered
        if score.total < 0.5:
            return True

        # If simplicity score is particularly low
        if score.simplicity < 0.4:
            return True

        # Check specific indicators
        desc_lower = approach.lower()
        indicator_count = sum(1 for ind in _OVER_ENGINEERING_INDICATORS if ind in desc_lower)
        if indicator_count >= 3:
            return True

        # Compare complexity of approach vs task
        task_str = str(task or "").lower()
        approach_keywords = set(re.findall(r"\b\w{4,}\b", desc_lower))
        task_keywords = set(re.findall(r"\b\w{4,}\b", task_str))

        if task_keywords:
            extra_complexity = len(approach_keywords - task_keywords) / len(task_keywords)
            if extra_complexity > 2.0:
                return True

        return False
