"""
LosionExporter — Export Library data in Losion training formats.

Wraps the core :class:`Exporter` with additional Losion-specific logic,
including Librarian fine-tuning data generation and export validation.

The exporter supports the following Losion training data formats:

- **Pretraining**: All entries as plain text with domain/quality metadata.
- **RLHF QA**: Question-answer pairs for RLHF training.
- **RLHF Solutions**: Problem-solution pairs for RLHF training.
- **Preference Pairs**: Contrasting helpful vs unhelpful entries for
  preference learning.
- **Librarian Fine-tune**: Specialized training data for fine-tuning the
  Librarian model to classify and index documents.

Example::

    from kantorku.library.storage.archive import Archive

    archive = Archive("data/library/archive.db")
    await archive.initialize()

    exporter = LosionExporter(archive=archive)

    # Export all formats
    counts = await exporter.export_all("exports/losion/", min_quality=0.7)
    print(f"Exported: {counts}")

    # Generate Librarian fine-tuning data
    ft_stats = await exporter.generate_librarian_finetune(
        "exports/librarian_finetune/", min_quality=0.8
    )
    print(f"Fine-tune data: {ft_stats}")
"""

from __future__ import annotations

import json
import logging
import math
import os
from pathlib import Path
from typing import Any

from kantorku.library.core.exporter import Exporter
from kantorku.library.core.models import EntryType, LibraryEntry
from kantorku.library.storage.archive import Archive

logger = logging.getLogger(__name__)

# System prompt used for Librarian fine-tuning data generation
_LIBRARIAN_SYSTEM_PROMPT: str = (
    "You are Librarian, the categorization and indexing AI for KantorKu Library. "
    "Analyze the provided document and return a JSON object with: "
    "entry_type (knowledge|solution|qa_pair|procedure), keywords (list of 3-8), "
    "shelf_path (list of category strings), quality_initial (0.0-1.0), "
    "domain (string), shelf_confidence (0.0-1.0), summary (1-3 sentences)."
)


class LosionExporter:
    """Export Library data in Losion training formats.

    Wraps the core :class:`Exporter` with additional Losion-specific
    export capabilities including Librarian fine-tuning data generation
    and export file validation.

    Args:
        archive: The Archive instance to export entries from.
    """

    def __init__(self, archive: Archive) -> None:
        self._archive = archive
        self._core_exporter = Exporter(archive=archive)

    # ── Export All Formats ────────────────────────────────────────────────

    async def export_all(
        self,
        output_dir: str,
        min_quality: float = 0.7,
    ) -> dict:
        """Export all Losion training formats.

        Runs the four core export operations in sequence:

        1. **Pretraining** — all entries as plain text with metadata.
        2. **RLHF QA** — question-answer pairs for RLHF.
        3. **RLHF Solutions** — problem-solution pairs for RLHF.
        4. **Preference Pairs** — helpful vs unhelpful contrasts.

        Each format is exported to its own subdirectory under
        ``output_dir``.

        Args:
            output_dir: The root directory for all exports. Subdirectories
                will be created for each format.
            min_quality: Minimum quality score threshold for included
                entries (default: 0.7).

        Returns:
            A dict with keys ``pretraining``, ``rlhf_qa``,
            ``rlhf_solutions``, ``preference``, each containing the
            count of entries exported.
        """
        logger.info(
            "Starting full Losion export to %s (min_quality=%.2f)",
            output_dir,
            min_quality,
        )

        # Create root output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # 1. Pretraining
        pretraining_dir = os.path.join(output_dir, "pretraining")
        pretraining_count = await self._core_exporter.export_losion_pretraining(
            pretraining_dir, min_quality=min_quality
        )

        # 2. RLHF QA
        rlhf_qa_dir = os.path.join(output_dir, "rlhf_qa")
        rlhf_qa_count = await self._core_exporter.export_losion_rlhf_qa(
            rlhf_qa_dir, min_quality=max(min_quality, 0.8)
        )

        # 3. RLHF Solutions
        rlhf_solutions_dir = os.path.join(output_dir, "rlhf_solutions")
        rlhf_solutions_count = await self._core_exporter.export_losion_rlhf_solutions(
            rlhf_solutions_dir, min_quality=max(min_quality, 0.8)
        )

        # 4. Preference Pairs
        preference_dir = os.path.join(output_dir, "preference")
        preference_count = await self._core_exporter.export_losion_preference_pairs(
            preference_dir, min_contrast=0.2
        )

        counts = {
            "pretraining": pretraining_count,
            "rlhf_qa": rlhf_qa_count,
            "rlhf_solutions": rlhf_solutions_count,
            "preference": preference_count,
        }

        logger.info("Full Losion export complete: %s", counts)
        return counts

    # ── Librarian Fine-tune ───────────────────────────────────────────────

    async def generate_librarian_finetune(
        self,
        output_dir: str,
        min_quality: float = 0.8,
    ) -> dict:
        """Generate training data for fine-tuning the Librarian model.

        Creates JSONL training records from verified Library entries with
        quality >= min_quality. Each record contains:

        - ``prompt``: The Librarian system prompt followed by the document
          content, simulating the input the Librarian would receive during
          inference.
        - ``response``: The expected JSON metadata output (entry_type,
          keywords, shelf_path, etc.), simulating what the fine-tuned model
          should produce.
        - ``quality``: The quality score of the source entry.
        - ``verified``: Whether the source entry has been verified.

        The records are split 90/10 into ``train.jsonl`` and ``val.jsonl``
        files in the output directory.

        Args:
            output_dir: The directory to write the train and val JSONL files.
            min_quality: Minimum quality score threshold (default: 0.8).
                Only verified entries with quality >= min_quality are included.

        Returns:
            A dict with keys ``train_count``, ``val_count``, ``total_count``.
        """
        logger.info(
            "Generating Librarian fine-tune data to %s (min_quality=%.2f)",
            output_dir,
            min_quality,
        )

        # Get all verified entries meeting quality threshold
        entries = await self._archive.get_all(
            min_quality=min_quality,
            verified=True,
            limit=100000,
        )

        if not entries:
            logger.warning(
                "No verified entries with quality >= %.2f found for fine-tuning",
                min_quality,
            )
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            # Write empty files
            train_path = os.path.join(output_dir, "train.jsonl")
            val_path = os.path.join(output_dir, "val.jsonl")
            Path(train_path).write_text("", encoding="utf-8")
            Path(val_path).write_text("", encoding="utf-8")
            return {"train_count": 0, "val_count": 0, "total_count": 0}

        # Generate training records
        records: list[dict[str, Any]] = []
        for entry in entries:
            record = self._build_librarian_training_record(entry)
            if record is not None:
                records.append(record)

        if not records:
            logger.warning("No valid training records generated")
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            train_path = os.path.join(output_dir, "train.jsonl")
            val_path = os.path.join(output_dir, "val.jsonl")
            Path(train_path).write_text("", encoding="utf-8")
            Path(val_path).write_text("", encoding="utf-8")
            return {"train_count": 0, "val_count": 0, "total_count": 0}

        # 90/10 split
        split_idx = math.ceil(len(records) * 0.9)
        train_records = records[:split_idx]
        val_records = records[split_idx:]

        # Write output files
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        train_path = os.path.join(output_dir, "train.jsonl")
        val_path = os.path.join(output_dir, "val.jsonl")

        self._write_jsonl(train_path, train_records)
        self._write_jsonl(val_path, val_records)

        result = {
            "train_count": len(train_records),
            "val_count": len(val_records),
            "total_count": len(records),
        }

        logger.info(
            "Generated Librarian fine-tune data: %d train, %d val, %d total",
            result["train_count"],
            result["val_count"],
            result["total_count"],
        )
        return result

    # ── Validate Export ───────────────────────────────────────────────────

    async def validate_export(self, output_dir: str) -> dict:
        """Validate all exported files exist and are valid JSONL.

        Checks that each expected export file exists in the output
        directory, is readable, and contains valid JSON Lines (one
        JSON object per line).

        Args:
            output_dir: The root directory of the exports to validate.

        Returns:
            A dict with keys:
            - ``valid`` (bool): Whether all files are valid.
            - ``files`` (dict): Mapping of filename to a dict with
              ``valid`` (bool) and ``lines`` (int) keys.
        """
        logger.info("Validating export at %s", output_dir)

        # Expected file paths based on export_all output structure
        expected_files: list[str] = [
            os.path.join("pretraining", "pretraining.jsonl"),
            os.path.join("rlhf_qa", "rlhf_qa.jsonl"),
            os.path.join("rlhf_solutions", "rlhf_solutions.jsonl"),
            os.path.join("preference", "preference_pairs.jsonl"),
        ]

        files_status: dict[str, dict] = {}
        all_valid = True

        for rel_path in expected_files:
            full_path = os.path.join(output_dir, rel_path)
            status = self._validate_jsonl_file(full_path)
            files_status[rel_path] = status
            if not status["valid"]:
                all_valid = False

        # Also check for fine-tune files if they exist
        finetune_files: list[str] = [
            os.path.join("train.jsonl"),
            os.path.join("val.jsonl"),
        ]
        for rel_path in finetune_files:
            full_path = os.path.join(output_dir, rel_path)
            if os.path.exists(full_path):
                status = self._validate_jsonl_file(full_path)
                files_status[rel_path] = status
                if not status["valid"]:
                    all_valid = False

        result = {
            "valid": all_valid,
            "files": files_status,
        }

        logger.info(
            "Export validation %s: %d files checked",
            "PASSED" if all_valid else "FAILED",
            len(files_status),
        )
        return result

    # ── Private helpers ───────────────────────────────────────────────────

    @staticmethod
    def _build_librarian_training_record(entry: LibraryEntry) -> dict | None:
        """Build a single training record for Librarian fine-tuning.

        Creates a prompt-response pair where the prompt is the system
        instruction + document content, and the response is the expected
        JSON metadata output.

        Args:
            entry: The LibraryEntry to convert to a training record.

        Returns:
            A dict with keys ``prompt``, ``response``, ``quality``,
            ``verified``, or ``None`` if the entry cannot be converted.
        """
        if not entry.content or not entry.content.strip():
            return None

        # Build the prompt: system instruction + document
        prompt = (
            f"{_LIBRARIAN_SYSTEM_PROMPT}\n\n"
            f"## Document\n\n"
            f"Title: {entry.title or '(untitled)'}\n\n"
            f"{entry.content}"
        )

        # Build the expected response as JSON metadata
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

    @staticmethod
    def _write_jsonl(filepath: str, records: list[dict]) -> None:
        """Write a list of dicts as JSONL (one JSON object per line).

        Args:
            filepath: The output file path.
            records: A list of dicts to write.
        """
        with open(filepath, "w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

    @staticmethod
    def _validate_jsonl_file(filepath: str) -> dict:
        """Validate a single JSONL file.

        Checks that the file exists, is readable, and contains valid
        JSON on each line. Blank lines are allowed and skipped.

        Args:
            filepath: The path to the JSONL file.

        Returns:
            A dict with keys ``valid`` (bool) and ``lines`` (int).
        """
        if not os.path.exists(filepath):
            return {"valid": False, "lines": 0}

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = 0
                for line_num, line in enumerate(f, 1):
                    stripped = line.strip()
                    if not stripped:
                        continue  # Skip blank lines
                    try:
                        json.loads(stripped)
                        lines += 1
                    except json.JSONDecodeError as exc:
                        logger.warning(
                            "Invalid JSON at %s:%d: %s", filepath, line_num, exc
                        )
                        return {"valid": False, "lines": lines}

                return {"valid": True, "lines": lines}

        except Exception as exc:
            logger.error("Failed to read %s: %s", filepath, exc)
            return {"valid": False, "lines": 0}
