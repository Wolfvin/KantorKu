"""
Senior Call — O13: Code review with opinionated frontend/backend checklists.

Provides structured code review with specific checklists for frontend
and backend code, change classification, and hygiene checks.

Like a senior engineer who reviews your code with clear standards,
not just "looks good to me."
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ReviewVerdict(Enum):
    """Possible review verdicts."""
    APPROVE = "approve"
    WARN = "warn"
    REJECT = "reject"


@dataclass
class ReviewIssue:
    """A single issue found during review."""
    severity: str = "info"
    category: str = ""
    description: str = ""
    suggestion: str = ""


@dataclass
class ReviewResult:
    """Result of a code review."""
    verdict: ReviewVerdict = ReviewVerdict.WARN
    issues: list[ReviewIssue] = field(default_factory=list)
    score: int = 100


# Frontend review checklist categories
_FRONTEND_CATEGORIES = [
    "component_scope",
    "state_ownership",
    "data_flow_direction",
    "css_specificity",
    "accessibility",
    "naming",
]

# Backend review checklist categories
_BACKEND_CATEGORIES = [
    "explicit_contracts",
    "fail_fast",
    "error_handling",
    "idempotency",
    "dependencies",
    "observability",
]

# Change classification thresholds
_CHANGE_THRESHOLDS = {
    "patch": 3,
    "minimal_refactor": 7,
    "reject_overengineering": 10,
}

# Hygiene patterns for different languages
_HYGIENE_PATTERNS: dict[str, dict[str, list[str]]] = {
    "python": {
        "legacy_traces": [
            r"#\s*TODO", r"#\s*FIXME", r"#\s*HACK", r"#\s*XXX",
            r"pass\s*#", r"deprecated",
        ],
        "dual_owner_state": [
            r"self\.\w+\s*=\s*.*\n.*self\.\w+\s*=\s*",
        ],
        "missing_fallbacks": [
            r"except\s*:", r"except\s+Exception\s*:",
        ],
    },
    "typescript": {
        "legacy_traces": [
            r"//\s*TODO", r"//\s*FIXME", r"//\s*HACK", r"//\s*XXX",
            r"@deprecated",
        ],
        "dual_owner_state": [
            r"this\.\w+\s*=\s*.*\n.*this\.\w+\s*=\s*",
        ],
        "missing_fallbacks": [
            r"catch\s*\(\s*\w+\s*\)\s*\{\s*\}",
        ],
    },
}


class SeniorCall:
    """
    Senior Call — opinionated code review with frontend/backend checklists.

    Reviews code against specific quality criteria:
    - Frontend: component scope, state ownership, data flow,
      CSS specificity, accessibility, naming
    - Backend: explicit contracts, fail-fast, error handling,
      idempotency, dependencies, observability

    Also classifies changes and performs hygiene checks.

    Usage:
        reviewer = SeniorCall()
        result = reviewer.review_frontend(output, spec)
        result = reviewer.review_backend(output, spec)
        classification = reviewer.classify_change(impact_score)
        issues = reviewer.hygiene_check(code, "python")
    """

    def review_frontend(
        self, output: str, spec: dict[str, Any] | str | None = None
    ) -> ReviewResult:
        """
        Review frontend code output against a spec.

        Checks: component scope, state ownership, data flow direction,
        CSS specificity, accessibility, naming.

        Args:
            output: The frontend code to review
            spec: Specification to review against (dict or string)

        Returns:
            ReviewResult with verdict, issues, and score
        """
        issues: list[ReviewIssue] = []
        score = 100

        if not output:
            return ReviewResult(
                verdict=ReviewVerdict.REJECT,
                issues=[ReviewIssue("critical", "empty_output", "Output is empty", "Provide frontend code")],
                score=0,
            )

        spec_str = str(spec) if spec else ""

        # Component scope check
        component_count = len(re.findall(r"(function|const|class)\s+\w+", output))
        if component_count > 5:
            issues.append(ReviewIssue(
                "warn", "component_scope",
                f"Too many components in single file ({component_count})",
                "Split into smaller, focused components",
            ))
            score -= 10

        # State ownership check
        state_count = len(re.findall(r"(useState|useReducer|this\.state)", output))
        if state_count > 3:
            issues.append(ReviewIssue(
                "warn", "state_ownership",
                f"Too many state variables ({state_count}) — potential dual ownership",
                "Consolidate state or lift to parent component",
            ))
            score -= 10

        # Data flow direction check
        prop_drilling = len(re.findall(r"props\.\w+\.\w+\.\w+", output))
        if prop_drilling > 2:
            issues.append(ReviewIssue(
                "warn", "data_flow_direction",
                "Deep prop drilling detected — consider context or state management",
                "Use Context API or state management library",
            ))
            score -= 10

        # CSS specificity check
        important_count = len(re.findall(r"!important", output))
        if important_count > 0:
            issues.append(ReviewIssue(
                "warn", "css_specificity",
                f"Found {important_count} !important declaration(s)",
                "Restructure CSS to avoid !important",
            ))
            score -= 5 * important_count

        # Accessibility check
        aria_count = len(re.findall(r"aria-", output))
        img_no_alt = len(re.findall(r"<img[^>]*(?!alt=)", output))
        if img_no_alt > 0:
            issues.append(ReviewIssue(
                "warn", "accessibility",
                f"Found {img_no_alt} <img> tag(s) without alt attribute",
                "Add alt attributes to all images",
            ))
            score -= 10
        if aria_count == 0 and len(output) > 200:
            issues.append(ReviewIssue(
                "info", "accessibility",
                "No ARIA attributes found in substantial output",
                "Consider adding ARIA attributes for accessibility",
            ))
            score -= 5

        # Naming check
        single_char_vars = re.findall(r"(?:const|let|var)\s+([a-z])\s*=", output)
        if len(single_char_vars) > 2:
            issues.append(ReviewIssue(
                "info", "naming",
                f"Found {len(single_char_vars)} single-character variable(s)",
                "Use descriptive variable names",
            ))
            score -= 5

        # Determine verdict
        score = max(0, score)
        if score >= 80:
            verdict = ReviewVerdict.APPROVE
        elif score >= 50:
            verdict = ReviewVerdict.WARN
        else:
            verdict = ReviewVerdict.REJECT

        return ReviewResult(verdict=verdict, issues=issues, score=score)

    def review_backend(
        self, output: str, spec: dict[str, Any] | str | None = None
    ) -> ReviewResult:
        """
        Review backend code output against a spec.

        Checks: explicit contracts, fail-fast, error handling,
        idempotency, dependencies, observability.

        Args:
            output: The backend code to review
            spec: Specification to review against (dict or string)

        Returns:
            ReviewResult with verdict, issues, and score
        """
        issues: list[ReviewIssue] = []
        score = 100

        if not output:
            return ReviewResult(
                verdict=ReviewVerdict.REJECT,
                issues=[ReviewIssue("critical", "empty_output", "Output is empty", "Provide backend code")],
                score=0,
            )

        # Explicit contracts check
        type_hints = len(re.findall(r":\s*(str|int|float|bool|list|dict|Any|Optional)", output))
        if type_hints < 3 and len(output) > 100:
            issues.append(ReviewIssue(
                "warn", "explicit_contracts",
                "Few type hints found — contracts may be implicit",
                "Add type hints to function signatures",
            ))
            score -= 15

        # Fail-fast check
        early_returns = len(re.findall(r"(if\s+not\s+|if\s+\w+\s+is\s+None|raise\s+ValueError|raise\s+TypeError)", output))
        if early_returns == 0 and len(output) > 100:
            issues.append(ReviewIssue(
                "warn", "fail_fast",
                "No guard clauses or early validation found",
                "Add input validation and fail-fast checks",
            ))
            score -= 15

        # Error handling check
        try_blocks = len(re.findall(r"try\s*:", output))
        except_blocks = len(re.findall(r"except\s+", output))
        if try_blocks == 0 and len(output) > 200:
            issues.append(ReviewIssue(
                "info", "error_handling",
                "No try/except blocks found",
                "Consider adding error handling for external calls",
            ))
            score -= 5
        if try_blocks > 0 and except_blocks > try_blocks * 2:
            issues.append(ReviewIssue(
                "info", "error_handling",
                "More except blocks than try blocks — check for overly broad catching",
                "Use specific exception types",
            ))

        # Idempotency check
        random_calls = len(re.findall(r"(random\.|uuid\.|time\.time|datetime\.now)", output))
        if random_calls > 2:
            issues.append(ReviewIssue(
                "info", "idempotency",
                f"Found {random_calls} non-deterministic call(s) — may affect idempotency",
                "Consider making operations idempotent where possible",
            ))
            score -= 5

        # Dependencies check
        import_count = len(re.findall(r"(?:from\s+\w+|import\s+\w+)", output))
        if import_count > 10:
            issues.append(ReviewIssue(
                "warn", "dependencies",
                f"High number of imports ({import_count}) — check dependency necessity",
                "Review and remove unnecessary imports",
            ))
            score -= 10

        # Observability check
        has_logging = bool(re.search(r"(logging|logger|log\.|print\()", output))
        if not has_logging and len(output) > 200:
            issues.append(ReviewIssue(
                "info", "observability",
                "No logging statements found",
                "Add logging for observability",
            ))
            score -= 5

        # Determine verdict
        score = max(0, score)
        if score >= 80:
            verdict = ReviewVerdict.APPROVE
        elif score >= 50:
            verdict = ReviewVerdict.WARN
        else:
            verdict = ReviewVerdict.REJECT

        return ReviewResult(verdict=verdict, issues=issues, score=score)

    def classify_change(self, impact_score: int | float) -> str:
        """
        Classify a change by its impact score.

        Args:
            impact_score: Numerical impact score (files changed, lines affected, etc.)

        Returns:
            Classification: "patch", "minimal_refactor", or "reject_overengineering"
        """
        impact_score = abs(impact_score)

        if impact_score <= _CHANGE_THRESHOLDS["patch"]:
            return "patch"
        elif impact_score <= _CHANGE_THRESHOLDS["minimal_refactor"]:
            return "minimal_refactor"
        else:
            return "reject_overengineering"

    def hygiene_check(
        self, code: str, language: str = "python"
    ) -> list[ReviewIssue]:
        """
        Perform hygiene checks on code for common issues.

        Checks for:
        - Legacy traces (TODO, FIXME, HACK, deprecated markers)
        - Dual-owner state (multiple assignments to same attribute)
        - Missing fallbacks (bare except, empty catch blocks)

        Args:
            code: The code to check
            language: Programming language ("python" or "typescript")

        Returns:
            List of ReviewIssue instances
        """
        if not code:
            return []

        issues: list[ReviewIssue] = []
        patterns = _HYGIENE_PATTERNS.get(language, _HYGIENE_PATTERNS["python"])

        # Check legacy traces
        for pattern in patterns.get("legacy_traces", []):
            matches = re.findall(pattern, code, re.IGNORECASE)
            if matches:
                issues.append(ReviewIssue(
                    "info", "legacy_traces",
                    f"Found {len(matches)} legacy trace(s): {pattern}",
                    "Remove or resolve legacy markers before merging",
                ))

        # Check dual-owner state
        for pattern in patterns.get("dual_owner_state", []):
            matches = re.findall(pattern, code, re.MULTILINE)
            if matches:
                issues.append(ReviewIssue(
                    "warn", "dual_owner_state",
                    "Potential dual-owner state detected",
                    "Ensure single ownership of state mutations",
                ))

        # Check missing fallbacks
        for pattern in patterns.get("missing_fallbacks", []):
            matches = re.findall(pattern, code)
            if matches:
                issues.append(ReviewIssue(
                    "warn", "missing_fallbacks",
                    f"Found {len(matches)} catch without specific handling",
                    "Add specific error handling instead of bare catch",
                ))

        return issues
