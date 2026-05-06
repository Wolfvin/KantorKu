"""
DeadEntryDetector — Detect and classify dead/orphaned Library entries.

The DeadEntryDetector scans the Library for entries that are no longer
useful: zero usage with low quality, no references, empty shelves,
or stale embeddings. It classifies each finding and generates a
report with recommended actions.

Verdicts:
    wire:   Reconnect — update embedding, add to shelf, boost quality
    delete: Remove — the entry is beyond recovery
    legacy: Keep temporarily — may still have archival value
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from kantorku.library.core.models import EntryType, LibraryEntry
from kantorku.library.storage.archive import Archive

logger = logging.getLogger(__name__)


@dataclass
class DeadEntryFinding:
    """A finding from dead entry detection."""

    entry_id: str
    title: str
    issues: list[str]
    verdict: str = "wire"  # wire, delete, legacy
    quality_score: float = 0.0
    usage_count: int = 0
    age_days: int = 0


class DeadEntryDetector:
    """Detect and classify dead/orphaned Library entries.

    Scans the Archive for entries that may no longer be useful
    and classifies them for cleanup actions.

    Example::

        detector = DeadEntryDetector()
        findings = detector.detect(archive)
        report = detector.generate_report(findings)
    """

    # Thresholds
    ZERO_USAGE_QUALITY_THRESHOLD: float = 0.3
    STALE_EMBEDDING_AGE_DAYS: int = 90

    async def detect(self, archive: Archive) -> list[DeadEntryFinding]:
        """Find dead/orphaned entries in the Archive.

        Detection criteria:
        - Entries with 0 usage + quality < 0.3
        - Entries with no references (not referenced by any other entry)
        - Shelves with 0 entries
        - Entries with potentially stale embeddings

        Args:
            archive: The Archive to scan.

        Returns:
            A list of DeadEntryFinding objects.
        """
        findings: list[DeadEntryFinding] = []

        try:
            entries = await archive.get_all(limit=100000)
        except Exception as exc:
            logger.error("Failed to scan archive: %s", exc)
            return findings

        if not entries:
            return findings

        # Build a set of all entry IDs that are referenced by other entries
        referenced_ids: set[str] = set()
        for entry in entries:
            if entry.related_ids:
                referenced_ids.update(entry.related_ids)
            if entry.source_entry_ids:
                referenced_ids.update(entry.source_entry_ids)
            if entry.supersedes_id:
                referenced_ids.add(entry.supersedes_id)
            if entry.solution_for:
                referenced_ids.add(entry.solution_for)

        now = datetime.now(timezone.utc)

        for entry in entries:
            issues: list[str] = []

            # Check: 0 usage + low quality
            if entry.usage_count == 0 and entry.quality_score < self.ZERO_USAGE_QUALITY_THRESHOLD:
                issues.append(f"Zero usage with quality {entry.quality_score:.2f}")

            # Check: no references from other entries
            if entry.id not in referenced_ids:
                # Only flag if also has low usage
                if entry.usage_count == 0:
                    issues.append("Not referenced by any other entry")

            # Check: potentially stale (old + unused)
            age_days = (now - entry.updated_at).days
            if age_days > self.STALE_EMBEDDING_AGE_DAYS and entry.usage_count == 0:
                issues.append(f"Stale entry: {age_days} days old, no usage")

            # Check: empty content
            if not entry.content or not entry.content.strip():
                issues.append("Empty content")

            # Check: no shelf path
            if not entry.shelf_path:
                issues.append("No shelf assignment")

            if issues:
                finding = DeadEntryFinding(
                    entry_id=entry.id,
                    title=entry.title or "(untitled)",
                    issues=issues,
                    quality_score=entry.quality_score,
                    usage_count=entry.usage_count,
                    age_days=age_days,
                )
                finding.verdict = self.classify(entry, issues[0])
                findings.append(finding)

        # Check for empty shelves
        try:
            structure = await archive.get_shelf_structure()
            empty_shelves = self._find_empty_shelves(structure)
            for shelf_path_str in empty_shelves:
                findings.append(DeadEntryFinding(
                    entry_id="",
                    title=f"Empty shelf: {shelf_path_str}",
                    issues=["Shelf has 0 entries"],
                    verdict="legacy",
                ))
        except Exception:
            pass

        logger.info(
            "Dead entry detection: %d findings from %d entries",
            len(findings),
            len(entries),
        )

        return findings

    def classify(self, entry: LibraryEntry, issue: str) -> str:
        """Classify a dead entry with a recommended action.

        Verdicts:
        - wire: Reconnect (update embedding, reassign shelf, boost)
        - delete: Remove (beyond recovery)
        - legacy: Keep temporarily (may have archival value)

        Args:
            entry: The LibraryEntry to classify.
            issue: The primary issue detected.

        Returns:
            One of "wire", "delete", "legacy".
        """
        # Delete: empty content or very low quality
        if not entry.content or not entry.content.strip():
            return "delete"

        if entry.quality_score < 0.1:
            return "delete"

        # Legacy: old but verified or from archivist source
        if entry.verified:
            return "legacy"

        if entry.source.value == "archivist" and entry.quality_score >= 0.3:
            return "legacy"

        if entry.age_days if hasattr(entry, 'age_days') else 0 > 180 and entry.quality_score >= 0.4:
            return "legacy"

        # Wire: can be reconnected
        return "wire"

    def generate_report(self, findings: list[DeadEntryFinding]) -> str:
        """Generate a Markdown report of dead entry findings.

        Args:
            findings: The list of findings.

        Returns:
            A Markdown report string.
        """
        if not findings:
            return "# Dead Entry Report\n\nNo dead entries detected. Library is healthy."

        lines: list[str] = [
            "# Dead Entry Report",
            "",
            f"**Total findings**: {len(findings)}",
            "",
        ]

        # Summary by verdict
        verdicts: dict[str, int] = {}
        for f in findings:
            verdicts[f.verdict] = verdicts.get(f.verdict, 0) + 1

        lines.append("## Summary")
        lines.append("")
        for verdict, count in sorted(verdicts.items()):
            lines.append(f"- **{verdict}**: {count} entries")
        lines.append("")

        # Per-entry details
        lines.append("## Findings")
        lines.append("")

        for i, finding in enumerate(findings, 1):
            if finding.entry_id:
                lines.append(f"### {i}. {finding.title}")
                lines.append(f"- **ID**: {finding.entry_id[:12]}...")
                lines.append(f"- **Verdict**: {finding.verdict}")
                lines.append(f"- **Quality**: {finding.quality_score:.2f}")
                lines.append(f"- **Usage**: {finding.usage_count}")
                lines.append(f"- **Age**: {finding.age_days} days")
                lines.append(f"- **Issues**: {'; '.join(finding.issues)}")
            else:
                lines.append(f"### {i}. {finding.title}")
                lines.append(f"- **Verdict**: {finding.verdict}")
                lines.append(f"- **Issues**: {'; '.join(finding.issues)}")
            lines.append("")

        return "\n".join(lines)

    async def cleanup(
        self,
        findings: list[DeadEntryFinding],
        auto_delete: bool = False,
    ) -> dict[str, Any]:
        """Apply cleanup actions based on findings.

        Args:
            findings: The findings to act on.
            auto_delete: If True, automatically delete entries marked
                for deletion. If False, only wire and legacy actions
                are applied.

        Returns:
            A dict with cleanup statistics.
        """
        stats: dict[str, int] = {
            "wired": 0,
            "deleted": 0,
            "legacied": 0,
            "skipped": 0,
        }

        for finding in findings:
            if not finding.entry_id:
                stats["skipped"] += 1
                continue

            if finding.verdict == "wire":
                # Wire: mark for re-indexing (don't delete)
                stats["wired"] += 1

            elif finding.verdict == "delete" and auto_delete:
                # Delete: remove from archive
                try:
                    await self._archive.delete(finding.entry_id)
                    stats["deleted"] += 1
                except Exception:
                    stats["skipped"] += 1

            elif finding.verdict == "delete" and not auto_delete:
                # Skip deletion without confirmation
                stats["skipped"] += 1

            elif finding.verdict == "legacy":
                # Legacy: no action, just track
                stats["legacied"] += 1

        logger.info("Cleanup: %s", stats)
        return stats

    # ── Helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _find_empty_shelves(
        structure: dict,
        path: list[str] | None = None,
    ) -> list[str]:
        """Find shelves with 0 entries in the structure dict."""
        if path is None:
            path = []

        empty: list[str] = []

        for key, value in structure.items():
            if key == "_count":
                continue

            current_path = path + [key]

            if isinstance(value, dict):
                count = value.get("_count", 0)
                if count == 0 and len(current_path) > 0:
                    empty.append(" / ".join(current_path))
                empty.extend(
                    DeadEntryDetector._find_empty_shelves(value, current_path)
                )

        return empty
