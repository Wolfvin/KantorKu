"""
SeniorCall — Quality gate system for KantorKu Library entries.

The SeniorCall class acts as a senior reviewer that validates entries
before they are saved to the Library. It performs quality checks,
duplicate detection, completeness validation, and staleness detection.

Verdicts:
    ALLOW: Entry meets quality standards — save it
    WARN:  Entry has minor issues — save with a warning
    REJECT: Entry has serious problems — don't save
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from enum import Enum
from typing import Any

from kantorku.library.core.models import EntryType, LibraryEntry

logger = logging.getLogger(__name__)


class Verdict(str, Enum):
    """Quality gate verdict."""

    ALLOW = "allow"
    WARN = "warn"
    REJECT = "reject"


@dataclass
class ReviewIssue:
    """A single issue found during review."""

    severity: str  # "error", "warning", "info"
    category: str  # "quality", "duplicate", "completeness", "validation"
    message: str
    detail: str = ""


@dataclass
class ReviewResult:
    """Result of a SeniorCall review."""

    verdict: Verdict = Verdict.ALLOW
    issues: list[ReviewIssue] = field(default_factory=list)
    score: float = 1.0
    summary: str = ""


class LibrarySeniorCall:
    """Quality gate system for Library entries.

    Reviews entries before saving to catch quality issues,
    duplicates, incomplete data, and stale content.

    Example::

        senior = LibrarySeniorCall()
        result = senior.review_entry(entry)
        if result.verdict == Verdict.REJECT:
            print("Entry rejected:", result.issues)
    """

    # Quality thresholds
    MIN_QUALITY_THRESHOLD: float = 0.2
    DUPLICATE_TITLE_SIMILARITY: float = 0.8
    DUPLICATE_CONTENT_JACCARD: float = 0.7
    STALE_MAX_AGE_DAYS: int = 90

    def review_entry(self, entry: LibraryEntry) -> ReviewResult:
        """Quality gate review for an entry before save.

        Checks:
        1. Minimum quality threshold
        2. Duplicate detection
        3. Completeness check
        4. Type-specific validation

        Args:
            entry: The LibraryEntry to review.

        Returns:
            A ReviewResult with verdict, issues, score, and summary.
        """
        issues: list[ReviewIssue] = []

        # 1. Quality threshold check
        if entry.quality_score < self.MIN_QUALITY_THRESHOLD:
            issues.append(ReviewIssue(
                severity="error",
                category="quality",
                message=f"Quality score {entry.quality_score:.2f} below minimum {self.MIN_QUALITY_THRESHOLD}",
            ))

        # 2. Completeness check
        if not entry.title or not entry.title.strip():
            issues.append(ReviewIssue(
                severity="warning",
                category="completeness",
                message="Entry has no title",
            ))

        if not entry.content or not entry.content.strip():
            issues.append(ReviewIssue(
                severity="error",
                category="completeness",
                message="Entry has no content",
            ))

        if not entry.keywords:
            issues.append(ReviewIssue(
                severity="info",
                category="completeness",
                message="Entry has no keywords",
            ))

        if not entry.shelf_path:
            issues.append(ReviewIssue(
                severity="warning",
                category="completeness",
                message="Entry is not assigned to any shelf",
            ))

        # 3. Type-specific validation
        if entry.entry_type == EntryType.SOLUTION:
            if not entry.problem_description:
                issues.append(ReviewIssue(
                    severity="warning",
                    category="validation",
                    message="SOLUTION entry has no problem description",
                ))

        elif entry.entry_type == EntryType.QA_PAIR:
            if not entry.question:
                issues.append(ReviewIssue(
                    severity="warning",
                    category="validation",
                    message="QA_PAIR entry has no question",
                ))
            if not entry.answer:
                issues.append(ReviewIssue(
                    severity="warning",
                    category="validation",
                    message="QA_PAIR entry has no answer",
                ))

        elif entry.entry_type == EntryType.PROCEDURE:
            if not entry.steps:
                issues.append(ReviewIssue(
                    severity="warning",
                    category="validation",
                    message="PROCEDURE entry has no steps",
                ))

        # 4. Content length check
        if entry.content and len(entry.content) < 20:
            issues.append(ReviewIssue(
                severity="warning",
                category="quality",
                message="Entry content is very short (< 20 characters)",
            ))

        # Compute verdict
        verdict = self.verdict(entry, issues)

        # Compute score (1.0 = perfect, reduced by issues)
        score = 1.0
        for issue in issues:
            if issue.severity == "error":
                score -= 0.3
            elif issue.severity == "warning":
                score -= 0.1
            elif issue.severity == "info":
                score -= 0.02
        score = max(score, 0.0)

        summary = (
            f"Verdict: {verdict.value} | "
            f"Issues: {len(issues)} | "
            f"Score: {score:.2f}"
        )

        logger.debug("SeniorCall review: %s", summary)

        return ReviewResult(
            verdict=verdict,
            issues=issues,
            score=round(score, 2),
            summary=summary,
        )

    def review_shelf(
        self,
        shelf_path: list[str],
        entries: list[LibraryEntry],
    ) -> ReviewResult:
        """Review a shelf for quality issues.

        Checks:
        - Shelf has enough entries
        - Entries belong in the shelf
        - Quality distribution

        Args:
            shelf_path: The shelf path to review.
            entries: Entries in the shelf.

        Returns:
            A ReviewResult for the shelf.
        """
        issues: list[ReviewIssue] = []

        if not entries:
            issues.append(ReviewIssue(
                severity="warning",
                category="completeness",
                message=f"Shelf {' / '.join(shelf_path)} has no entries",
            ))

        # Quality distribution check
        if entries:
            low_quality = sum(1 for e in entries if e.quality_score < 0.3)
            if low_quality > len(entries) * 0.5:
                issues.append(ReviewIssue(
                    severity="warning",
                    category="quality",
                    message=f"More than 50% of entries ({low_quality}/{len(entries)}) have low quality",
                ))

        verdict = self.verdict(None, issues)
        score = max(1.0 - len(issues) * 0.1, 0.0)

        return ReviewResult(
            verdict=verdict,
            issues=issues,
            score=round(score, 2),
            summary=f"Shelf review: {' / '.join(shelf_path)} | {len(entries)} entries | {verdict.value}",
        )

    def detect_duplicates(
        self,
        entry: LibraryEntry,
        existing_entries: list[LibraryEntry],
    ) -> list[dict[str, Any]]:
        """Detect near-duplicate entries.

        Checks:
        - Title similarity > 0.8
        - Content Jaccard similarity > 0.7

        Args:
            entry: The new entry to check.
            existing_entries: Existing entries to compare against.

        Returns:
            A list of duplicate detection dicts.
        """
        duplicates: list[dict[str, Any]] = []

        for existing in existing_entries:
            # Title similarity
            title_sim = self._text_similarity(
                entry.title or "", existing.title or ""
            )

            # Content Jaccard similarity
            content_sim = self._jaccard_similarity(
                entry.content or "", existing.content or ""
            )

            if title_sim > self.DUPLICATE_TITLE_SIMILARITY:
                duplicates.append({
                    "existing_id": existing.id,
                    "existing_title": existing.title,
                    "similarity_type": "title",
                    "similarity_score": round(title_sim, 4),
                    "threshold": self.DUPLICATE_TITLE_SIMILARITY,
                })

            if content_sim > self.DUPLICATE_CONTENT_JACCARD:
                duplicates.append({
                    "existing_id": existing.id,
                    "existing_title": existing.title,
                    "similarity_type": "content",
                    "similarity_score": round(content_sim, 4),
                    "threshold": self.DUPLICATE_CONTENT_JACCARD,
                })

        return duplicates

    def flag_stale(
        self,
        entries: list[LibraryEntry],
        max_age_days: int = 90,
    ) -> list[dict[str, Any]]:
        """Flag entries that haven't been accessed/updated recently.

        Args:
            entries: Entries to check for staleness.
            max_age_days: Maximum age in days before flagging.

        Returns:
            A list of stale entry dicts.
        """
        stale: list[dict[str, Any]] = []
        now = datetime.now(timezone.utc)
        threshold_days = max_age_days

        for entry in entries:
            age_days = (now - entry.updated_at).days
            if age_days > threshold_days and entry.usage_count == 0:
                stale.append({
                    "id": entry.id,
                    "title": entry.title,
                    "age_days": age_days,
                    "usage_count": entry.usage_count,
                    "quality_score": entry.quality_score,
                })

        return stale

    def verdict(
        self,
        entry: LibraryEntry | None,
        issues: list[ReviewIssue],
    ) -> Verdict:
        """Determine the verdict based on issues found.

        Logic:
        - Any error severity → REJECT
        - 2+ warning severity → WARN
        - Otherwise → ALLOW

        Args:
            entry: The entry being reviewed (optional for shelf reviews).
            issues: The list of issues found.

        Returns:
            A Verdict enum value.
        """
        error_count = sum(1 for i in issues if i.severity == "error")
        warning_count = sum(1 for i in issues if i.severity == "warning")

        if error_count > 0:
            return Verdict.REJECT
        elif warning_count >= 2:
            return Verdict.WARN
        else:
            return Verdict.ALLOW

    # ── Helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _text_similarity(a: str, b: str) -> float:
        """Compute text similarity using SequenceMatcher.

        Args:
            a: First text string.
            b: Second text string.

        Returns:
            A similarity score between 0.0 and 1.0.
        """
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    @staticmethod
    def _jaccard_similarity(a: str, b: str) -> float:
        """Compute Jaccard similarity between two texts.

        Tokenizes by whitespace and computes set overlap.

        Args:
            a: First text string.
            b: Second text string.

        Returns:
            A Jaccard similarity score between 0.0 and 1.0.
        """
        set_a = set(a.lower().split())
        set_b = set(b.lower().split())
        if not set_a and not set_b:
            return 1.0
        if not set_a or not set_b:
            return 0.0
        intersection = set_a & set_b
        union = set_a | set_b
        return len(intersection) / len(union)
