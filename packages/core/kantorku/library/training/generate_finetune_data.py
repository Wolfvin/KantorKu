"""
Generate Librarian fine-tuning data from the Library archive.

CLI script that reads verified, high-quality entries from the Library
archive and generates JSONL training files for fine-tuning the Librarian
model. The output is split into train and validation sets (90/10).

Usage::

    # Default settings
    python -m kantorku.library.training.generate_finetune_data

    # Custom output directory and quality threshold
    python -m kantorku.library.training.generate_finetune_data \\
        --output-dir exports/librarian_finetune \\
        --min-quality 0.8 \\
        --db-path data/library/archive.db

The script generates:
- ``train.jsonl``: 90% of the training records.
- ``val.jsonl``: 10% of the training records.

Each JSONL line is a JSON object with:
- ``prompt``: The full Librarian prompt (system instruction + shelf
  structure + document content).
- ``response``: The expected JSON metadata output.
- ``quality``: The source entry's quality score.
- ``verified``: Whether the source entry is verified.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import os
import sys
from pathlib import Path
from typing import Any

from kantorku.library.storage.archive import Archive
from kantorku.library.training.data_formatter import DataFormatter

logger = logging.getLogger(__name__)


async def generate_training_data(
    archive: Archive,
    output_path: str,
    min_quality: float = 0.8,
) -> dict:
    """Generate and split Librarian fine-tuning training data.

    Reads all verified entries with quality >= min_quality from the
    archive, formats them as Librarian training records using the
    DataFormatter, and splits them 90/10 into train and validation
    JSONL files.

    Args:
        archive: The Archive instance to read entries from. Must be
            initialized before calling this function.
        output_path: The directory to write the ``train.jsonl`` and
            ``val.jsonl`` files.
        min_quality: Minimum quality score threshold for entries
            (default: 0.8).

    Returns:
        A dict with statistics about the generation:
        - ``total_entries``: Number of entries in the archive meeting
          the quality threshold.
        - ``train_count``: Number of training records written.
        - ``val_count``: Number of validation records written.
        - ``total_records``: Total records generated (may be less than
          total_entries if some entries couldn't be formatted).
        - ``skipped``: Number of entries skipped due to formatting
          issues.
    """
    logger.info(
        "Generating training data: output=%s, min_quality=%.2f",
        output_path,
        min_quality,
    )

    # Get verified entries meeting quality threshold
    entries = await archive.get_all(
        min_quality=min_quality,
        verified=True,
        limit=100000,
    )

    if not entries:
        logger.warning(
            "No verified entries with quality >= %.2f found", min_quality
        )
        # Create empty output files
        Path(output_path).mkdir(parents=True, exist_ok=True)
        Path(os.path.join(output_path, "train.jsonl")).write_text(
            "", encoding="utf-8"
        )
        Path(os.path.join(output_path, "val.jsonl")).write_text(
            "", encoding="utf-8"
        )
        return {
            "total_entries": 0,
            "train_count": 0,
            "val_count": 0,
            "total_records": 0,
            "skipped": 0,
        }

    logger.info("Found %d entries meeting quality threshold", len(entries))

    # Get current shelf structure for realistic prompts
    try:
        current_shelves = await archive.get_shelf_structure()
    except Exception as exc:
        logger.warning("Failed to get shelf structure: %s — using empty", exc)
        current_shelves = {}

    # Format entries as training records
    formatter = DataFormatter(archive=archive)
    records: list[dict[str, Any]] = []
    skipped = 0

    for entry in entries:
        if not entry.content or not entry.content.strip():
            skipped += 1
            continue

        try:
            record = await formatter.generate_librarian_training_record(
                entry, current_shelves
            )
            records.append(record)
        except Exception as exc:
            logger.warning(
                "Failed to format entry %s: %s — skipping", entry.id, exc
            )
            skipped += 1

    if not records:
        logger.warning("No valid training records generated")
        Path(output_path).mkdir(parents=True, exist_ok=True)
        Path(os.path.join(output_path, "train.jsonl")).write_text(
            "", encoding="utf-8"
        )
        Path(os.path.join(output_path, "val.jsonl")).write_text(
            "", encoding="utf-8"
        )
        return {
            "total_entries": len(entries),
            "train_count": 0,
            "val_count": 0,
            "total_records": 0,
            "skipped": skipped,
        }

    # 90/10 split
    split_idx = math.ceil(len(records) * 0.9)
    train_records = records[:split_idx]
    val_records = records[split_idx:]

    # Write output files
    Path(output_path).mkdir(parents=True, exist_ok=True)
    train_path = os.path.join(output_path, "train.jsonl")
    val_path = os.path.join(output_path, "val.jsonl")

    _write_jsonl(train_path, train_records)
    _write_jsonl(val_path, val_records)

    stats = {
        "total_entries": len(entries),
        "train_count": len(train_records),
        "val_count": len(val_records),
        "total_records": len(records),
        "skipped": skipped,
    }

    logger.info(
        "Training data generated: %d train, %d val, %d total (%d skipped)",
        stats["train_count"],
        stats["val_count"],
        stats["total_records"],
        stats["skipped"],
    )
    return stats


def _write_jsonl(filepath: str, records: list[dict]) -> None:
    """Write a list of dicts as JSONL (one JSON object per line).

    Args:
        filepath: The output file path.
        records: A list of dicts to write.
    """
    with open(filepath, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    """CLI entry point for generating Librarian fine-tuning data.

    Parses command-line arguments, initializes the Archive, and runs
    the training data generation pipeline.

    Arguments:
        --output-dir: Directory to write train.jsonl and val.jsonl
            (default: ``exports/librarian_finetune``).
        --min-quality: Minimum quality score threshold (default: 0.8).
        --db-path: Path to the Library archive SQLite database
            (default: ``data/library/archive.db``).
    """
    parser = argparse.ArgumentParser(
        description="Generate Librarian fine-tuning data from the Library archive",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Example:\n"
            "  python -m kantorku.library.training.generate_finetune_data \\\n"
            "    --output-dir exports/librarian_finetune \\\n"
            "    --min-quality 0.8 \\\n"
            "    --db-path data/library/archive.db\n"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="exports/librarian_finetune",
        help="Directory to write train.jsonl and val.jsonl (default: exports/librarian_finetune)",
    )
    parser.add_argument(
        "--min-quality",
        type=float,
        default=0.8,
        help="Minimum quality score threshold (default: 0.8)",
    )
    parser.add_argument(
        "--db-path",
        default="data/library/archive.db",
        help="Path to the Library archive SQLite database (default: data/library/archive.db)",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Validate min_quality range
    if not 0.0 <= args.min_quality <= 1.0:
        logger.error("min-quality must be between 0.0 and 1.0, got %.2f", args.min_quality)
        sys.exit(1)

    # Validate db_path exists
    if not os.path.exists(args.db_path):
        logger.error("Database file not found: %s", args.db_path)
        sys.exit(1)

    # Run the async generation pipeline
    async def _run() -> dict:
        archive = Archive(args.db_path)
        await archive.initialize()

        try:
            stats = await generate_training_data(
                archive=archive,
                output_path=args.output_dir,
                min_quality=args.min_quality,
            )
            return stats
        finally:
            await archive.close()

    stats = asyncio.run(_run())

    # Print summary
    print(f"\n{'=' * 60}")
    print("Librarian Fine-tuning Data Generation Complete")
    print(f"{'=' * 60}")
    print(f"  Output directory: {args.output_dir}")
    print(f"  Min quality:      {args.min_quality}")
    print(f"  Total entries:    {stats['total_entries']}")
    print(f"  Train records:    {stats['train_count']}")
    print(f"  Val records:      {stats['val_count']}")
    print(f"  Total records:    {stats['total_records']}")
    print(f"  Skipped:          {stats['skipped']}")
    print(f"{'=' * 60}")

    if stats["total_records"] == 0:
        logger.warning("No training records were generated!")
        sys.exit(1)


if __name__ == "__main__":
    main()
