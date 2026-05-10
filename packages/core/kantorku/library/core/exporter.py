"""
Exporter — Export Library entries in various formats for training and backup.

The Exporter supports multiple output formats:

- **JSONL**: One JSON object per line, suitable for backup and data exchange.
- **Markdown**: Organized by shelf hierarchy, readable by humans.
- **Losion Pretraining**: JSONL with text, domain, quality, source, and shelf
  fields for LLM pretraining data.
- **Losion RLHF QA**: Question-answer pairs in RLHF (Reinforcement Learning
  from Human Feedback) format.
- **Losion RLHF Solutions**: Problem-solution pairs in RLHF format.
- **Losion Preference Pairs**: Contrasting helpful vs unhelpful entries for
  preference learning.

All export methods return the count of entries exported and write files
to the specified output paths.

Example::

    from kantorku.library.storage.archive import Archive

    archive = Archive("data/library/archive.db")
    await archive.initialize()

    exporter = Exporter(archive=archive)
    count = await exporter.export_json("exports/library.jsonl")
    print(f"Exported {count} entries")

    # Losion training formats
    pretrain_count = await exporter.export_losion_pretraining(
        "exports/losion_pretraining/", min_quality=0.7
    )
    rlhf_qa_count = await exporter.export_losion_rlhf_qa(
        "exports/losion_rlhf_qa/", min_quality=0.8
    )
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kantorku.library.core.models import EntryType, LibraryEntry
from kantorku.library.storage.archive import Archive

logger = logging.getLogger(__name__)


class Exporter:
    """Export Library entries in various formats for training and backup.

    Supports JSONL backup, Markdown documentation, and multiple Losion
    training data formats (pretraining, RLHF QA, RLHF solutions,
    preference pairs).

    Args:
        archive: The Archive instance to export entries from.
    """

    def __init__(self, archive: Archive) -> None:
        self._archive = archive

    # ── JSON Export ──────────────────────────────────────────────────────

    async def export_json(
        self,
        output_path: str,
        min_quality: float = 0.0,
        entry_type: EntryType | None = None,
    ) -> int:
        """Export all matching entries as JSONL (one JSON object per line).

        Each line is a complete JSON object representing one LibraryEntry,
        as produced by ``LibraryEntry.to_dict()``.

        Args:
            output_path: Path to the output JSONL file.
            min_quality: Minimum quality score threshold.
            entry_type: If provided, filter to this entry type.

        Returns:
            The number of entries exported.
        """
        entries = await self._get_filtered_entries(
            min_quality=min_quality,
            entry_type=entry_type,
        )

        self._ensure_directory(output_path)

        with open(output_path, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")

        logger.info(
            "Exported %d entries to JSONL: %s", len(entries), output_path
        )
        return len(entries)

    # ── Markdown Export ──────────────────────────────────────────────────

    async def export_markdown(
        self,
        output_path: str,
        shelf_path: list[str] | None = None,
    ) -> int:
        """Export entries as markdown files organized by shelf.

        Creates a directory structure at ``output_path`` that mirrors
        the shelf hierarchy, with each entry as a separate markdown file.
        If ``shelf_path`` is provided, only entries from that shelf
        are exported.

        Args:
            output_path: Path to the output directory.
            shelf_path: If provided, only export entries from this shelf.

        Returns:
            The number of entries exported.
        """
        if shelf_path is not None:
            entries = await self._archive.get_by_shelf(shelf_path, limit=100000)
        else:
            entries = await self._archive.get_all(limit=100000)

        if not entries:
            logger.info("No entries to export as markdown")
            return 0

        base_dir = Path(output_path)
        base_dir.mkdir(parents=True, exist_ok=True)

        exported = 0
        for entry in entries:
            # Build the directory path from shelf_path
            if entry.shelf_path:
                entry_dir = base_dir / Path(*entry.shelf_path)
            else:
                entry_dir = base_dir / "Uncategorized"

            entry_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename from title or ID
            filename = self._sanitize_filename(
                entry.title or entry.id
            )
            filepath = entry_dir / f"{filename}.md"

            # Write markdown content
            md_content = self._entry_to_markdown(entry)
            filepath.write_text(md_content, encoding="utf-8")
            exported += 1

        logger.info(
            "Exported %d entries as markdown to: %s", exported, output_path
        )
        return exported

    # ── Losion Pretraining Format ────────────────────────────────────────

    async def export_losion_pretraining(
        self,
        output_dir: str,
        min_quality: float = 0.7,
    ) -> int:
        """Export entries in Losion pretraining format.

        Each entry is exported as a JSONL line with the following fields:
        - ``text``: The full content of the entry.
        - ``domain``: The knowledge domain (e.g., "code", "mathematics").
        - ``quality``: The quality score of the entry.
        - ``source``: The entry source (e.g., "manual", "kantorku").
        - ``shelf``: The shelf path as a slash-separated string.

        Only entries with quality >= min_quality are included.

        Args:
            output_dir: Path to the output directory.
            min_quality: Minimum quality score threshold (default: 0.7).

        Returns:
            The number of entries exported.
        """
        entries = await self._get_filtered_entries(min_quality=min_quality)

        if not entries:
            logger.info("No entries meet quality threshold for pretraining export")
            return 0

        self._ensure_directory_for_dir(output_dir)
        output_path = os.path.join(output_dir, "pretraining.jsonl")

        with open(output_path, "w", encoding="utf-8") as f:
            for entry in entries:
                record = {
                    "text": entry.content,
                    "domain": entry.domain,
                    "quality": round(entry.quality_score, 4),
                    "source": entry.source.value,
                    "shelf": " / ".join(entry.shelf_path) if entry.shelf_path else "",
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        logger.info(
            "Exported %d entries in Losion pretraining format to: %s",
            len(entries),
            output_path,
        )
        return len(entries)

    # ── Losion RLHF QA Format ────────────────────────────────────────────

    async def export_losion_rlhf_qa(
        self,
        output_dir: str,
        min_quality: float = 0.8,
    ) -> int:
        """Export QA_PAIR entries in RLHF format.

        Each QA pair is exported as a JSONL line with:
        - ``prompt``: The question text.
        - ``chosen``: The answer (high-quality response).
        - ``rejected``: An empty or low-quality alternative (if available).
        - ``quality``: The quality score.

        Only QA_PAIR entries with quality >= min_quality are included.

        Args:
            output_dir: Path to the output directory.
            min_quality: Minimum quality score threshold (default: 0.8).

        Returns:
            The number of entries exported.
        """
        entries = await self._get_filtered_entries(
            min_quality=min_quality,
            entry_type=EntryType.QA_PAIR,
        )

        if not entries:
            logger.info("No QA_PAIR entries meet quality threshold for RLHF export")
            return 0

        self._ensure_directory_for_dir(output_dir)
        output_path = os.path.join(output_dir, "rlhf_qa.jsonl")

        # Also try to find rejected answers from low-quality QA pairs
        low_quality_entries = await self._get_filtered_entries(
            min_quality=0.0,
            max_quality=min_quality,
            entry_type=EntryType.QA_PAIR,
        )

        with open(output_path, "w", encoding="utf-8") as f:
            for entry in entries:
                question = entry.question or entry.title or ""
                answer = entry.answer or entry.content

                if not question or not answer:
                    continue

                # Try to find a rejected answer (low quality, similar question)
                rejected = self._find_rejected_answer(
                    question, answer, low_quality_entries
                )

                record = {
                    "prompt": question,
                    "chosen": answer,
                    "rejected": rejected,
                    "quality": round(entry.quality_score, 4),
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        logger.info(
            "Exported %d QA_PAIR entries in RLHF format to: %s",
            len(entries),
            output_path,
        )
        return len(entries)

    # ── Losion RLHF Solutions Format ─────────────────────────────────────

    async def export_losion_rlhf_solutions(
        self,
        output_dir: str,
        min_quality: float = 0.8,
    ) -> int:
        """Export SOLUTION entries in RLHF format.

        Each solution is exported as a JSONL line with:
        - ``prompt``: The problem description.
        - ``chosen``: The solution content.
        - ``rejected``: A failed attempt or low-quality alternative.
        - ``quality``: The quality score.
        - ``verification``: The verification result.

        Only SOLUTION entries with quality >= min_quality are included.

        Args:
            output_dir: Path to the output directory.
            min_quality: Minimum quality score threshold (default: 0.8).

        Returns:
            The number of entries exported.
        """
        entries = await self._get_filtered_entries(
            min_quality=min_quality,
            entry_type=EntryType.SOLUTION,
        )

        if not entries:
            logger.info("No SOLUTION entries meet quality threshold for RLHF export")
            return 0

        self._ensure_directory_for_dir(output_dir)
        output_path = os.path.join(output_dir, "rlhf_solutions.jsonl")

        with open(output_path, "w", encoding="utf-8") as f:
            for entry in entries:
                problem = entry.problem_description or ""
                solution = entry.content

                if not problem:
                    # Try to extract problem from content
                    problem = self._extract_problem_from_content(entry.content)

                # Build rejected from failed attempts
                rejected = self._build_rejected_from_failed_attempts(entry)

                record = {
                    "prompt": problem,
                    "chosen": solution,
                    "rejected": rejected,
                    "quality": round(entry.quality_score, 4),
                    "verification": (
                        entry.verification_result.value
                        if entry.verification_result
                        else "untested"
                    ),
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        logger.info(
            "Exported %d SOLUTION entries in RLHF format to: %s",
            len(entries),
            output_path,
        )
        return len(entries)

    # ── Losion Preference Pairs ──────────────────────────────────────────

    async def export_losion_preference_pairs(
        self,
        output_dir: str,
        min_contrast: float = 0.2,
    ) -> int:
        """Export preference pairs (helpful vs unhelpful) for preference learning.

        Creates pairs of entries where one is clearly better than the other
        based on quality score, feedback, or verification status. The
        ``min_contrast`` parameter ensures that only pairs with a significant
        quality difference are included.

        Each pair is exported as a JSONL line with:
        - ``prompt``: A shared context (domain + shelf).
        - ``chosen``: The higher-quality entry content.
        - ``rejected``: The lower-quality entry content.
        - ``quality_diff``: The quality score difference.

        Args:
            output_dir: Path to the output directory.
            min_contrast: Minimum quality difference between pairs (default: 0.2).

        Returns:
            The number of preference pairs exported.
        """
        all_entries = await self._archive.get_all(limit=100000)

        if len(all_entries) < 2:
            logger.info("Not enough entries to create preference pairs")
            return 0

        # Group entries by shelf_path for meaningful comparisons
        shelf_groups: dict[str, list[LibraryEntry]] = {}
        for entry in all_entries:
            key = " / ".join(entry.shelf_path) if entry.shelf_path else "Uncategorized"
            shelf_groups.setdefault(key, []).append(entry)

        self._ensure_directory_for_dir(output_dir)
        output_path = os.path.join(output_dir, "preference_pairs.jsonl")

        pairs_exported = 0

        with open(output_path, "w", encoding="utf-8") as f:
            for shelf_key, group in shelf_groups.items():
                if len(group) < 2:
                    continue

                # Sort by quality score
                sorted_group = sorted(
                    group, key=lambda e: e.quality_score, reverse=True
                )

                # Create pairs: highest quality vs lowest quality
                for i, high_entry in enumerate(sorted_group):
                    for low_entry in reversed(sorted_group):
                        quality_diff = (
                            high_entry.quality_score - low_entry.quality_score
                        )
                        if quality_diff >= min_contrast:
                            prompt = f"Domain: {high_entry.domain}\nShelf: {shelf_key}"
                            record = {
                                "prompt": prompt,
                                "chosen": high_entry.content[:2000],
                                "rejected": low_entry.content[:2000],
                                "quality_diff": round(quality_diff, 4),
                            }
                            f.write(json.dumps(record, ensure_ascii=False) + "\n")
                            pairs_exported += 1
                            break  # One pair per high-quality entry

        logger.info(
            "Exported %d preference pairs to: %s",
            pairs_exported,
            output_path,
        )
        return pairs_exported

    # ── Export Stats ─────────────────────────────────────────────────────

    async def get_export_stats(self) -> dict[str, Any]:
        """Return counts of entries available for each export format.

        Useful for previewing how many entries will be exported before
        actually running the export.

        Returns:
            A dict with keys for each export format and their available
            entry counts: total, json_exportable, pretraining_exportable,
            rlhf_qa_exportable, rlhf_solutions_exportable,
            preference_pairs_possible.
        """
        all_entries = await self._archive.get_all(limit=100000)
        total = len(all_entries)

        # Count by quality threshold
        high_quality = [e for e in all_entries if e.quality_score >= 0.7]
        very_high_quality = [e for e in all_entries if e.quality_score >= 0.8]

        # Count by type
        qa_pairs = [e for e in all_entries if e.entry_type == EntryType.QA_PAIR]
        solutions = [e for e in all_entries if e.entry_type == EntryType.SOLUTION]
        high_qa = [e for e in qa_pairs if e.quality_score >= 0.8]
        high_solutions = [e for e in solutions if e.quality_score >= 0.8]

        # Count preference pairs (same shelf, quality diff >= 0.2)
        shelf_groups: dict[str, list[LibraryEntry]] = {}
        for entry in all_entries:
            key = " / ".join(entry.shelf_path) if entry.shelf_path else "Uncategorized"
            shelf_groups.setdefault(key, []).append(entry)

        pref_pairs = 0
        for group in shelf_groups.values():
            if len(group) >= 2:
                sorted_g = sorted(group, key=lambda e: e.quality_score, reverse=True)
                highest = sorted_g[0].quality_score
                lowest = sorted_g[-1].quality_score
                if highest - lowest >= 0.2:
                    pref_pairs += len(sorted_g) // 2

        return {
            "total": total,
            "json_exportable": total,
            "pretraining_exportable": len(high_quality),
            "rlhf_qa_exportable": len(high_qa),
            "rlhf_solutions_exportable": len(high_solutions),
            "preference_pairs_possible": pref_pairs,
            "by_type": {
                "knowledge": len([e for e in all_entries if e.entry_type == EntryType.KNOWLEDGE]),
                "solution": len(solutions),
                "qa_pair": len(qa_pairs),
                "procedure": len([e for e in all_entries if e.entry_type == EntryType.PROCEDURE]),
            },
            "by_quality": {
                "high_0.8+": len(very_high_quality),
                "medium_0.5-0.8": len([e for e in all_entries if 0.5 <= e.quality_score < 0.8]),
                "low_below_0.5": len([e for e in all_entries if e.quality_score < 0.5]),
            },
        }

    # ── Private helpers ───────────────────────────────────────────────────

    async def _get_filtered_entries(
        self,
        min_quality: float = 0.0,
        max_quality: float = 1.0,
        entry_type: EntryType | None = None,
    ) -> list[LibraryEntry]:
        """Get entries matching quality and type filters.

        Args:
            min_quality: Minimum quality score (inclusive).
            max_quality: Maximum quality score (exclusive).
            entry_type: Optional entry type filter.

        Returns:
            A list of matching LibraryEntry objects.
        """
        entries = await self._archive.get_all(limit=100000)

        filtered = [
            e for e in entries
            if min_quality <= e.quality_score < max_quality
        ]

        if entry_type is not None:
            filtered = [e for e in filtered if e.entry_type == entry_type]

        return filtered

    @staticmethod
    def _ensure_directory(filepath: str) -> None:
        """Ensure the parent directory of a file path exists.

        Args:
            filepath: The file path to create a parent directory for.
        """
        parent = os.path.dirname(filepath)
        if parent:
            Path(parent).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _ensure_directory_for_dir(dirpath: str) -> None:
        """Ensure a directory exists.

        Args:
            dirpath: The directory path to create.
        """
        Path(dirpath).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Sanitize a string for use as a filename.

        Removes or replaces characters that are invalid in filenames.

        Args:
            name: The raw name string.

        Returns:
            A sanitized filename string.
        """
        # Remove/replace invalid characters
        sanitized = name.replace("/", "-").replace("\\", "-")
        sanitized = sanitized.replace(":", "-").replace("*", "")
        sanitized = sanitized.replace("?", "").replace('"', "")
        sanitized = sanitized.replace("<", "").replace(">", "")
        sanitized = sanitized.replace("|", "-").replace("\n", " ")
        sanitized = sanitized.strip(". ")

        # Truncate to reasonable length
        if len(sanitized) > 80:
            sanitized = sanitized[:80]

        # Ensure non-empty
        if not sanitized:
            sanitized = "untitled"

        return sanitized

    @staticmethod
    def _entry_to_markdown(entry: LibraryEntry) -> str:
        """Convert a LibraryEntry to a markdown document.

        Args:
            entry: The LibraryEntry to convert.

        Returns:
            A markdown string representing the entry.
        """
        lines: list[str] = []

        # Title
        title = entry.title or "Untitled"
        lines.append(f"# {title}")
        lines.append("")

        # Metadata
        lines.append("## Metadata")
        lines.append("")
        lines.append(f"- **Type**: {entry.entry_type.value}")
        lines.append(f"- **Domain**: {entry.domain}")
        lines.append(f"- **Quality**: {entry.quality_score:.2f}")
        lines.append(f"- **Source**: {entry.source.value}")
        lines.append(f"- **Shelf**: {entry.shelf_str}")
        lines.append(f"- **Keywords**: {', '.join(entry.keywords) if entry.keywords else 'None'}")
        lines.append(f"- **Created**: {entry.created_at.isoformat()}")
        lines.append(f"- **Updated**: {entry.updated_at.isoformat()}")
        lines.append(f"- **Usage**: {entry.usage_count} (helpful: {entry.was_helpful}, unhelpful: {entry.was_unhelpful})")
        lines.append("")

        # Summary
        if entry.summary:
            lines.append("## Summary")
            lines.append("")
            lines.append(entry.summary)
            lines.append("")

        # Content
        lines.append("## Content")
        lines.append("")
        lines.append(entry.content)
        lines.append("")

        # Type-specific sections
        if entry.entry_type == EntryType.SOLUTION:
            if entry.problem_description:
                lines.append("## Problem")
                lines.append("")
                lines.append(entry.problem_description)
                lines.append("")

            if entry.solution_code:
                lines.append("## Solution Code")
                lines.append("")
                lines.append(f"```")
                lines.append(entry.solution_code)
                lines.append("```")
                lines.append("")

            if entry.failed_attempts:
                lines.append("## Failed Attempts")
                lines.append("")
                for i, attempt in enumerate(entry.failed_attempts, 1):
                    lines.append(f"### Attempt {i}")
                    for key, value in attempt.items():
                        lines.append(f"- **{key}**: {value}")
                    lines.append("")

        elif entry.entry_type == EntryType.QA_PAIR:
            if entry.question:
                lines.append("## Question")
                lines.append("")
                lines.append(entry.question)
                lines.append("")

            if entry.answer:
                lines.append("## Answer")
                lines.append("")
                lines.append(entry.answer)
                lines.append("")

            if entry.source_entry_ids:
                lines.append("## Source Entries")
                lines.append("")
                for eid in entry.source_entry_ids:
                    lines.append(f"- {eid}")
                lines.append("")

        elif entry.entry_type == EntryType.PROCEDURE:
            if entry.steps:
                lines.append("## Steps")
                lines.append("")
                for step in entry.steps:
                    step_num = step.get("step", "?")
                    action = step.get("action", "")
                    expected = step.get("expected", "")
                    lines.append(f"**Step {step_num}**: {action}")
                    if expected:
                        lines.append(f"  - Expected: {expected}")
                    lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _find_rejected_answer(
        question: str,
        chosen_answer: str,
        low_quality_entries: list[LibraryEntry],
    ) -> str:
        """Find a rejected (low-quality) answer for RLHF training.

        Tries to find a low-quality QA_PAIR entry with a similar question
        to serve as the rejected response. If none is found, generates
        a synthetic rejected answer.

        Args:
            question: The question text.
            chosen_answer: The high-quality (chosen) answer.
            low_quality_entries: List of low-quality entries to search.

        Returns:
            A rejected answer string.
        """
        # Try to find a similar low-quality answer
        question_lower = question.lower()
        for entry in low_quality_entries:
            entry_question = (entry.question or entry.title or "").lower()
            # Simple similarity: shared significant words
            q_words = set(question_lower.split())
            eq_words = set(entry_question.split())
            overlap = len(q_words & eq_words)
            if overlap >= 2:
                return entry.answer or entry.content

        # Generate a synthetic rejected answer
        return (
            f"I'm not sure about {question[:50]}. "
            "You might want to look it up or try a different approach."
        )

    @staticmethod
    def _extract_problem_from_content(content: str) -> str:
        """Extract problem description from SOLUTION content.

        Args:
            content: The full entry content.

        Returns:
            Extracted problem description.
        """
        import re

        # Try to find "Problem:" or "Error:" sections
        for pattern in [
            r"(?:problem|error|issue)\s*:\s*\n?([\s\S]*?)(?=\n(?:solution|fix)\s*:|\Z)",
        ]:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()[:500]

        # Fallback: first paragraph
        lines = content.split("\n")
        problem_lines: list[str] = []
        for line in lines:
            if line.strip().startswith("```") or re.match(
                r"(?:solution|fix)\s*:", line, re.IGNORECASE
            ):
                break
            if line.strip():
                problem_lines.append(line.strip())

        return " ".join(problem_lines)[:500]

    @staticmethod
    def _build_rejected_from_failed_attempts(entry: LibraryEntry) -> str:
        """Build a rejected answer from a SOLUTION entry's failed attempts.

        Args:
            entry: The SOLUTION LibraryEntry.

        Returns:
            A rejected answer string based on failed attempts.
        """
        if not entry.failed_attempts:
            return (
                "I tried a basic approach but it didn't work. "
                "I'm not sure what else to try."
            )

        parts: list[str] = []
        for attempt in entry.failed_attempts[:3]:
            desc = attempt.get("description", attempt.get("approach", "an approach"))
            reason = attempt.get("reason", attempt.get("error", "it failed"))
            parts.append(f"Tried {desc}, but {reason}.")

        return " ".join(parts)
