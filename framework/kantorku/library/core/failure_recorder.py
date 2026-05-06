"""
BlamelessFailureRecorder — Structured failure recording for KantorKu Library.

Records failures in a blameless, structured format to enable learning
from errors without assigning blame. Supports querying past failures,
auto-correlating similar failures, and suggesting root causes.

Failures are stored as structured JSON entries with:
    - phase: The pipeline phase where the failure occurred
    - symptom: Observable behavior
    - context: Environmental details
    - root_cause: Identified or hypothesized root cause
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class FailureRecord:
    """A structured failure record."""

    id: str = ""
    phase: str = ""
    symptom: str = ""
    context: str = ""
    root_cause: str = ""
    timestamp: str = ""
    resolved: bool = False
    fix: str = ""


class BlamelessFailureRecorder:
    """Structured failure recording for KantorKu Library.

    Records failures in a blameless, structured format, supports
    querying past failures, and auto-correlates similar failures
    to suggest root causes.

    Example::

        recorder = BlamelessFailureRecorder()
        recorder.record_failure(
            phase="embedding",
            symptom="Embedding generation timeout",
            context="Large document with 50k characters",
            root_cause="Document exceeds model max input length",
        )
    """

    def __init__(
        self,
        storage_path: str = "data/library/failures.json",
    ) -> None:
        """Initialize the BlamelessFailureRecorder.

        Args:
            storage_path: Path to the JSON file for persistent storage.
        """
        self._storage_path = storage_path
        self._failures: list[dict[str, Any]] = []
        self._load()

    def record_failure(
        self,
        phase: str,
        symptom: str,
        context: str,
        root_cause: str | None = None,
    ) -> str:
        """Record a structured failure.

        Args:
            phase: The pipeline phase where the failure occurred
                (e.g., "ingest", "embed", "search", "classify").
            symptom: The observable behavior (what went wrong).
            context: Environmental details (input, config, state).
            root_cause: Identified or hypothesized root cause.

        Returns:
            The failure record ID.
        """
        import uuid

        failure_id = str(uuid.uuid4())[:12]
        timestamp = datetime.now(timezone.utc).isoformat()

        record = {
            "id": failure_id,
            "phase": phase,
            "symptom": symptom,
            "context": context,
            "root_cause": root_cause or "unknown",
            "timestamp": timestamp,
            "resolved": False,
            "fix": "",
        }

        self._failures.append(record)
        self._save()

        logger.info(
            "Recorded failure %s: phase=%s, symptom=%s",
            failure_id,
            phase,
            symptom[:80],
        )

        return failure_id

    def query_failures(
        self,
        symptom: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Find similar past failures by symptom.

        Uses text similarity matching to find failures with
        similar symptoms to the given query.

        Args:
            symptom: The symptom to search for.
            top_k: Maximum number of results to return.

        Returns:
            A list of failure record dicts, sorted by similarity.
        """
        if not self._failures:
            return []

        scored: list[tuple[float, dict[str, Any]]] = []
        for failure in self._failures:
            similarity = SequenceMatcher(
                None,
                symptom.lower(),
                failure.get("symptom", "").lower(),
            ).ratio()

            # Also check phase match
            if failure.get("phase", "").lower() in symptom.lower():
                similarity += 0.1

            scored.append((similarity, failure))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [f for _, f in scored[:top_k]]

    def get_lessons(self) -> list[dict[str, Any]]:
        """Get all recorded failures with root causes and fixes.

        Returns only failures that have been resolved or have
        identified root causes, providing actionable lessons.

        Returns:
            A list of lesson dicts with root_cause, fix, and symptom.
        """
        lessons: list[dict[str, Any]] = []

        for failure in self._failures:
            if failure.get("root_cause", "unknown") != "unknown" or failure.get("resolved"):
                lessons.append({
                    "id": failure["id"],
                    "phase": failure.get("phase", ""),
                    "symptom": failure.get("symptom", ""),
                    "root_cause": failure.get("root_cause", ""),
                    "fix": failure.get("fix", ""),
                    "resolved": failure.get("resolved", False),
                })

        return lessons

    def auto_correlate(
        self,
        failure: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Find similar failures and suggest root cause.

        Compares the given failure against all recorded failures
        and suggests root causes based on similar past incidents.

        Args:
            failure: A failure dict with at least 'symptom' and 'phase'.

        Returns:
            A list of similar failure dicts with suggested root causes.
        """
        symptom = failure.get("symptom", "")
        phase = failure.get("phase", "")

        similar = self.query_failures(symptom, top_k=5)

        # Filter to same phase if possible
        same_phase = [f for f in similar if f.get("phase") == phase]
        if same_phase:
            similar = same_phase

        # Add suggestions
        for f in similar:
            if f.get("root_cause") and f["root_cause"] != "unknown":
                f["suggested_root_cause"] = f["root_cause"]
            if f.get("fix"):
                f["suggested_fix"] = f["fix"]

        return similar

    # ── Persistence ─────────────────────────────────────────────────────

    def _load(self) -> None:
        """Load failure records from JSON file."""
        try:
            if os.path.exists(self._storage_path):
                with open(self._storage_path, "r", encoding="utf-8") as f:
                    self._failures = json.load(f)
                logger.debug("Loaded %d failure records", len(self._failures))
        except Exception as exc:
            logger.warning("Failed to load failure records: %s", exc)
            self._failures = []

    def _save(self) -> None:
        """Save failure records to JSON file."""
        try:
            save_dir = os.path.dirname(self._storage_path)
            if save_dir:
                Path(save_dir).mkdir(parents=True, exist_ok=True)
            with open(self._storage_path, "w", encoding="utf-8") as f:
                json.dump(self._failures, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            logger.warning("Failed to save failure records: %s", exc)
