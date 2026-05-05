"""
DataFormatter — Format Library entries for Losion training data.

Transforms LibraryEntry objects into various training data representations
used for Losion model training:

- **Pretraining format**: Plain text with domain/quality metadata for
  continued pretraining.
- **RLHF QA format**: Question-answer pairs for RLHF training.
- **RLHF Solution format**: Problem-solution pairs for RLHF training.
- **Preference pairs**: Chosen vs rejected comparisons for preference
  learning.
- **Librarian training records**: Prompt-response pairs for fine-tuning
  the Librarian classification model.

The formatter uses the Archive to look up shelf structures for building
realistic Librarian prompts that include the current Library taxonomy.

Example::

    from kantorku.library.storage.archive import Archive

    archive = Archive("data/library/archive.db")
    await archive.initialize()

    formatter = DataFormatter(archive=archive)

    # Format a single entry
    pretraining = await formatter.format_pretraining_entry(my_entry)

    # Generate a Librarian training record
    shelves = await archive.get_shelf_structure()
    record = await formatter.generate_librarian_training_record(my_entry, shelves)
"""

from __future__ import annotations

import json
import logging
from typing import Any

from kantorku.library.core.models import EntryType, LibraryEntry
from kantorku.library.storage.archive import Archive

logger = logging.getLogger(__name__)

# System prompt for Librarian fine-tuning
_LIBRARIAN_SYSTEM_PROMPT: str = (
    "You are Librarian, the categorization and indexing AI for KantorKu Library.\n"
    "Analyze the provided document and return a JSON object with:\n"
    "- entry_type: one of knowledge, solution, qa_pair, procedure\n"
    "- keywords: list of 3-8 significant keywords\n"
    "- shelf_path: list of category strings (e.g., [\"Engineering\", \"Backend\", \"Python\"])\n"
    "- quality_initial: float 0.0-1.0\n"
    "- domain: knowledge domain string\n"
    "- shelf_confidence: float 0.0-1.0\n"
    "- summary: 1-3 sentence summary\n\n"
    "Respond with ONLY the JSON object, no markdown fences."
)


class DataFormatter:
    """Format Library entries for Losion training data.

    Provides methods to transform LibraryEntry objects into various
    training data formats used by the Losion training pipeline. The
    formatter uses the Archive to look up shelf structures and related
    entries for building realistic training contexts.

    Args:
        archive: The Archive instance for data lookups.
    """

    def __init__(self, archive: Archive) -> None:
        self._archive = archive

    # ── Librarian Prompt ──────────────────────────────────────────────────

    async def format_librarian_prompt(
        self,
        content: str,
        current_shelves: dict,
    ) -> str:
        """Build the full prompt for Librarian training.

        Constructs a complete prompt that includes the system instruction,
        the current Library shelf structure (as context for shelf placement
        decisions), and the document content to be classified.

        The shelf structure helps the Librarian model learn to place
        documents on existing shelves rather than inventing new ones.

        Args:
            content: The document content to include in the prompt.
            current_shelves: A dict representing the current Library shelf
                hierarchy (as returned by ``Archive.get_shelf_structure()``).

        Returns:
            The full prompt string for Librarian training.
        """
        # Build a compact representation of available shelves
        shelf_listing = self._format_shelf_listing(current_shelves)

        prompt_parts: list[str] = [
            _LIBRARIAN_SYSTEM_PROMPT,
            "",
            "## Current Library Shelves",
            "",
        ]

        if shelf_listing:
            prompt_parts.append(shelf_listing)
        else:
            prompt_parts.append("(No shelves defined yet)")

        prompt_parts.extend([
            "",
            "## Document to Classify",
            "",
            content,
        ])

        return "\n".join(prompt_parts)

    # ── Pretraining Entry ─────────────────────────────────────────────────

    async def format_pretraining_entry(self, entry: LibraryEntry) -> dict:
        """Format a LibraryEntry as a Losion pretraining data record.

        Pretraining data includes the full text content along with
        metadata fields (domain, quality, source, shelf) that help
        the model learn document quality and domain associations.

        Args:
            entry: The LibraryEntry to format.

        Returns:
            A dict with keys:
            - ``text``: The entry's content.
            - ``domain``: The knowledge domain.
            - ``quality``: The quality score (rounded to 4 decimals).
            - ``source``: The entry source as a string.
            - ``shelf``: The shelf path as a slash-separated string.
        """
        # Build the text representation with title and content
        text_parts: list[str] = []
        if entry.title:
            text_parts.append(f"# {entry.title}")
            text_parts.append("")
        if entry.summary:
            text_parts.append(entry.summary)
            text_parts.append("")
        text_parts.append(entry.content)

        return {
            "text": "\n".join(text_parts),
            "domain": entry.domain,
            "quality": round(entry.quality_score, 4),
            "source": entry.source.value,
            "shelf": " / ".join(entry.shelf_path) if entry.shelf_path else "",
        }

    # ── RLHF QA Entry ─────────────────────────────────────────────────────

    async def format_rlhf_qa_entry(self, entry: LibraryEntry) -> dict:
        """Format a QA_PAIR entry as RLHF training data.

        Creates a prompt-chosen-rejected triple for RLHF training.
        The chosen response is the entry's answer (or content), while
        the rejected response is a synthetic low-quality alternative
        generated from the question context.

        Args:
            entry: The QA_PAIR LibraryEntry to format.

        Returns:
            A dict with keys:
            - ``prompt``: The question text.
            - ``chosen``: The high-quality answer.
            - ``rejected``: A synthetic rejected (low-quality) answer.
            - ``quality``: The entry's quality score.
        """
        question = entry.question or entry.title or ""
        answer = entry.answer or entry.content

        # Generate a synthetic rejected answer
        rejected = self._generate_rejected_qa(question, answer)

        return {
            "prompt": question,
            "chosen": answer,
            "rejected": rejected,
            "quality": round(entry.quality_score, 4),
        }

    # ── RLHF Solution Entry ───────────────────────────────────────────────

    async def format_rlhf_solution_entry(self, entry: LibraryEntry) -> dict:
        """Format a SOLUTION entry as RLHF training data.

        Creates a prompt-chosen-rejected triple where the prompt is the
        problem description, the chosen response is the solution, and
        the rejected response is built from the entry's failed attempts
        (or a synthetic fallback).

        Args:
            entry: The SOLUTION LibraryEntry to format.

        Returns:
            A dict with keys:
            - ``prompt``: The problem description.
            - ``chosen``: The solution content.
            - ``rejected``: A rejected response (from failed attempts or
              synthetic).
            - ``quality``: The entry's quality score.
            - ``verification``: The verification result string.
        """
        problem = entry.problem_description or entry.title or ""
        solution = entry.content

        # Build rejected from failed attempts
        rejected = self._build_rejected_from_attempts(entry)

        return {
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

    # ── Preference Pair ───────────────────────────────────────────────────

    async def format_preference_pair(
        self,
        good_entry: LibraryEntry,
        bad_entry: LibraryEntry,
    ) -> dict:
        """Format a pair of entries as a preference learning data point.

        Creates a preference pair where the ``chosen`` entry is clearly
        better than the ``rejected`` entry based on their quality scores.
        The prompt is a shared context derived from the entries' domain
        and shelf.

        Args:
            good_entry: The higher-quality (chosen) LibraryEntry.
            bad_entry: The lower-quality (rejected) LibraryEntry.

        Returns:
            A dict with keys:
            - ``prompt``: Shared context (domain + shelf).
            - ``chosen``: The good entry's content (truncated to 2000 chars).
            - ``rejected``: The bad entry's content (truncated to 2000 chars).
            - ``chosen_quality``: The chosen entry's quality score.
            - ``rejected_quality``: The rejected entry's quality score.
        """
        # Build shared context
        domain = good_entry.domain
        shelf = " / ".join(good_entry.shelf_path) if good_entry.shelf_path else "Uncategorized"
        prompt = f"Domain: {domain}\nShelf: {shelf}"

        return {
            "prompt": prompt,
            "chosen": good_entry.content[:2000],
            "rejected": bad_entry.content[:2000],
            "chosen_quality": round(good_entry.quality_score, 4),
            "rejected_quality": round(bad_entry.quality_score, 4),
        }

    # ── Librarian Training Record ─────────────────────────────────────────

    async def generate_librarian_training_record(
        self,
        entry: LibraryEntry,
        current_shelves: dict,
    ) -> dict:
        """Generate one training record for Librarian fine-tuning.

        Creates a prompt-response pair where the prompt includes the
        system instruction, current shelf structure, and document content,
        and the response is the expected JSON metadata that the Librarian
        should produce.

        This is the primary method used by the LosionExporter when
        generating fine-tuning data for the Librarian model.

        Args:
            entry: The LibraryEntry to convert to a training record.
            current_shelves: The current Library shelf hierarchy dict
                (as returned by ``Archive.get_shelf_structure()``).

        Returns:
            A dict with keys:
            - ``prompt``: The full Librarian prompt.
            - ``response``: The expected JSON metadata response.
            - ``quality``: The source entry's quality score.
            - ``verified``: Whether the source entry is verified.
        """
        # Build the full prompt
        prompt = await self.format_librarian_prompt(
            content=entry.content,
            current_shelves=current_shelves,
        )

        # Build the expected response
        response_data = {
            "entry_type": entry.entry_type.value,
            "keywords": entry.keywords,
            "shelf_path": entry.shelf_path,
            "quality_initial": round(entry.quality_score, 4),
            "domain": entry.domain,
            "shelf_confidence": round(entry.shelf_confidence, 4),
            "summary": entry.summary or "",
        }

        response = json.dumps(response_data, ensure_ascii=False)

        return {
            "prompt": prompt,
            "response": response,
            "quality": entry.quality_score,
            "verified": entry.verified,
        }

    # ── Private helpers ───────────────────────────────────────────────────

    @staticmethod
    def _format_shelf_listing(shelves: dict, indent: int = 0) -> str:
        """Format a shelf hierarchy dict as a readable listing.

        Produces an indented, human-readable representation of the
        Library's shelf structure suitable for inclusion in a training
        prompt.

        Args:
            shelves: The shelf hierarchy dict.
            indent: Current indentation level.

        Returns:
            A formatted string listing all shelves.
        """
        lines: list[str] = []
        prefix = "  " * indent

        for key, value in shelves.items():
            if key == "_count":
                continue  # Skip internal count keys

            if isinstance(value, dict):
                count = value.get("_count", 0)
                lines.append(f"{prefix}- {key} ({count} entries)")
                # Recurse into children
                child_lines = DataFormatter._format_shelf_listing(value, indent + 1)
                if child_lines:
                    lines.append(child_lines)

        return "\n".join(lines)

    @staticmethod
    def _generate_rejected_qa(question: str, answer: str) -> str:
        """Generate a synthetic rejected answer for RLHF QA training.

        Creates a plausible but low-quality answer that serves as the
        "rejected" response in preference training.

        Args:
            question: The question text.
            answer: The chosen (correct) answer.

        Returns:
            A synthetic rejected answer string.
        """
        # Create a vague, unhelpful response
        short_question = question[:50] if len(question) > 50 else question
        return (
            f"I'm not entirely sure about {short_question}. "
            "You might want to check the documentation or search online for more information. "
            "There could be several approaches to this."
        )

    @staticmethod
    def _build_rejected_from_attempts(entry: LibraryEntry) -> str:
        """Build a rejected response from a SOLUTION entry's failed attempts.

        Uses the recorded failed attempts as the rejected response,
        providing realistic contrast for RLHF training. If no failed
        attempts are recorded, generates a synthetic fallback.

        Args:
            entry: The SOLUTION LibraryEntry.

        Returns:
            A rejected response string.
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
