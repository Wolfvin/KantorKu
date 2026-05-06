"""
Library data models — all dataclasses and enums for the Library system.

LibraryEntry is the central data structure representing a single piece of
knowledge in the Library. It supports four entry types (KNOWLEDGE, SOLUTION,
QA_PAIR, PROCEDURE), quality scoring, usage tracking, and origin tracing
back to KantorKu workers and sessions.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class EntrySource(str, Enum):
    """Origin of a Library entry."""
    MANUAL = "manual"          # User input langsung
    KANTORKU = "kantorku"      # Dari worker KantorKu
    IMPORT = "import"          # Dari file/URL import
    ARCHIVIST = "archivist"    # Dari interaksi tanya-jawab


class EntryType(str, Enum):
    """Type of content stored in a Library entry."""
    KNOWLEDGE = "knowledge"    # Pengetahuan faktual
    SOLUTION = "solution"      # Solusi dari masalah nyata
    QA_PAIR = "qa_pair"        # Tanya-jawab tersimpan
    PROCEDURE = "procedure"    # Langkah-langkah


class VerificationResult(str, Enum):
    """Verification status for SOLUTION entries."""
    PASS = "pass"
    FAIL = "fail"
    UNTESTED = "untested"


class EvidenceTier(str, Enum):
    """Source quality tier for Library entries.

    Used to factor evidence quality into quality scoring:
    - OFFICIAL: Official documentation (quality bonus +0.1)
    - VENDOR: Vendor blogs/tutorials (neutral)
    - SECONDARY: Stack Overflow, wikis (default, neutral)
    - COMMUNITY: Blog posts, forums (quality penalty -0.05)
    """
    OFFICIAL = "official"
    VENDOR = "vendor"
    SECONDARY = "secondary"
    COMMUNITY = "community"


# Icon mappings for TUI display
ENTRY_TYPE_ICONS: dict[EntryType, str] = {
    EntryType.KNOWLEDGE: "\U0001f4d6",   # 📖
    EntryType.SOLUTION: "\U0001f4a1",    # 💡
    EntryType.QA_PAIR: "\U0001f4ac",     # 💬
    EntryType.PROCEDURE: "\U0001f527",   # 🔧
}

ENTRY_TYPE_COLORS: dict[EntryType, str] = {
    EntryType.KNOWLEDGE: "white",
    EntryType.SOLUTION: "yellow",
    EntryType.QA_PAIR: "cyan",
    EntryType.PROCEDURE: "green",
}


@dataclass
class LibraryEntry:
    """A single knowledge entry in the Library.

    Entries are the atomic unit of the Library. Each entry has content
    (markdown), metadata (type, domain, keywords), a shelf location
    (hierarchical path), quality tracking, and optional KantorKu origin
    information.

    Entry types have additional specialized fields:
    - SOLUTION: problem_description, failed_attempts, solution_code,
      verification_result
    - QA_PAIR: question, answer, source_entry_ids
    - PROCEDURE: steps (ordered list of actions)
    """

    # ── Identity ──────────────────────────────────────────────────────
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    source: EntrySource = EntrySource.MANUAL

    # ── Content ───────────────────────────────────────────────────────
    title: str = ""
    content: str = ""                    # Markdown body
    summary: str = ""                    # 1-3 kalimat
    keywords: list[str] = field(default_factory=list)

    # ── Classification ────────────────────────────────────────────────
    entry_type: EntryType = EntryType.KNOWLEDGE
    domain: str = "web_text"            # Untuk Losion training data
    lang: str = "id"

    # ── Shelf placement ───────────────────────────────────────────────
    shelf_path: list[str] = field(default_factory=list)
    shelf_confidence: float = 0.0

    # ── Relations ─────────────────────────────────────────────────────
    related_ids: list[str] = field(default_factory=list)
    supersedes_id: Optional[str] = None
    solution_for: Optional[str] = None

    # ── Quality & feedback ────────────────────────────────────────────
    quality_score: float = 0.5
    verified: bool = False
    usage_count: int = 0
    was_helpful: int = 0
    was_unhelpful: int = 0

    # ── KantorKu origin ───────────────────────────────────────────────
    origin_session_id: Optional[str] = None
    origin_worker_id: Optional[str] = None
    origin_task_id: Optional[str] = None

    # ── Evidence tier ──────────────────────────────────────────────────
    evidence_tier: EvidenceTier = EvidenceTier.SECONDARY

    # ── SOLUTION specific ─────────────────────────────────────────────
    problem_description: Optional[str] = None
    failed_attempts: list[dict[str, Any]] = field(default_factory=list)
    solution_code: Optional[str] = None
    verification_result: Optional[VerificationResult] = None

    # ── QA_PAIR specific ──────────────────────────────────────────────
    question: Optional[str] = None
    answer: Optional[str] = None
    source_entry_ids: list[str] = field(default_factory=list)

    # ── PROCEDURE specific ────────────────────────────────────────────
    steps: list[dict[str, Any]] = field(default_factory=list)
    # steps format: [{"step": 1, "action": "...", "expected": "..."}]

    def touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(timezone.utc)

    def mark_helpful(self) -> None:
        """Record that this entry was helpful to a user."""
        self.was_helpful += 1
        self._recalculate_quality()
        self.touch()

    def mark_unhelpful(self) -> None:
        """Record that this entry was not helpful."""
        self.was_unhelpful += 1
        self._recalculate_quality()
        self.touch()

    def record_usage(self) -> None:
        """Record that this entry was accessed/used."""
        self.usage_count += 1
        self.touch()

    def _recalculate_quality(self) -> None:
        """Recalculate quality score based on feedback.

        Uses a Bayesian-inspired formula that pulls toward a prior (0.5)
        when there's little feedback, and trusts the feedback ratio more
        as the sample size grows.

        Formula:
            quality = (prior * prior_weight + helpful) /
                      (prior_weight + helpful + unhelpful)

        Where prior = 0.5, prior_weight = 2 (minimum 2 "virtual" votes).

        Evidence tier adjustments are applied after the base calculation:
        - OFFICIAL: +0.1 quality bonus
        - VENDOR: no adjustment
        - SECONDARY: no adjustment (default)
        - COMMUNITY: -0.05 quality penalty
        """
        if self.verified:
            # Verified entries get a quality floor of 0.8
            base = 0.8
        else:
            base = 0.5

        prior_weight = 2.0
        numerator = base * prior_weight + self.was_helpful
        denominator = prior_weight + self.was_helpful + self.was_unhelpful

        raw = numerator / denominator

        # Usage bonus: entries used many times are slightly better
        usage_bonus = min(self.usage_count * 0.005, 0.05)

        # Evidence tier adjustment
        tier_adjustments: dict[EvidenceTier, float] = {
            EvidenceTier.OFFICIAL: 0.1,
            EvidenceTier.VENDOR: 0.0,
            EvidenceTier.SECONDARY: 0.0,
            EvidenceTier.COMMUNITY: -0.05,
        }
        tier_adjustment = tier_adjustments.get(self.evidence_tier, 0.0)

        self.quality_score = min(max(raw + usage_bonus + tier_adjustment, 0.0), 1.0)

    @property
    def shelf_str(self) -> str:
        """Return shelf path as a slash-separated string."""
        return " / ".join(self.shelf_path) if self.shelf_path else "Uncategorized"

    @property
    def icon(self) -> str:
        """Return the icon for this entry type."""
        return ENTRY_TYPE_ICONS.get(self.entry_type, "\U0001f4d6")

    @property
    def color(self) -> str:
        """Return the display color for this entry type."""
        return ENTRY_TYPE_COLORS.get(self.entry_type, "white")

    @property
    def verified_icon(self) -> str:
        """Return verification icon."""
        if self.verified:
            return "\u2713"  # ✓
        return "\u25cb"      # ○

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary for storage/JSON export."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "source": self.source.value,
            "title": self.title,
            "content": self.content,
            "summary": self.summary,
            "keywords": self.keywords,
            "entry_type": self.entry_type.value,
            "domain": self.domain,
            "lang": self.lang,
            "shelf_path": self.shelf_path,
            "shelf_confidence": self.shelf_confidence,
            "related_ids": self.related_ids,
            "supersedes_id": self.supersedes_id,
            "solution_for": self.solution_for,
            "quality_score": self.quality_score,
            "verified": self.verified,
            "usage_count": self.usage_count,
            "was_helpful": self.was_helpful,
            "was_unhelpful": self.was_unhelpful,
            "origin_session_id": self.origin_session_id,
            "origin_worker_id": self.origin_worker_id,
            "origin_task_id": self.origin_task_id,
            "problem_description": self.problem_description,
            "failed_attempts": self.failed_attempts,
            "solution_code": self.solution_code,
            "verification_result": (
                self.verification_result.value
                if self.verification_result
                else None
            ),
            "question": self.question,
            "answer": self.answer,
            "source_entry_ids": self.source_entry_ids,
            "steps": self.steps,
            "evidence_tier": self.evidence_tier.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LibraryEntry:
        """Deserialize from a dictionary (e.g., from SQLite row)."""
        # Parse datetime strings
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now(timezone.utc)

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        elif updated_at is None:
            updated_at = datetime.now(timezone.utc)

        # Parse enums
        source = data.get("source", "manual")
        if isinstance(source, str):
            source = EntrySource(source)

        entry_type = data.get("entry_type", "knowledge")
        if isinstance(entry_type, str):
            entry_type = EntryType(entry_type)

        verification_result = data.get("verification_result")
        if isinstance(verification_result, str):
            verification_result = VerificationResult(verification_result)

        # Parse JSON strings if needed (SQLite stores some as JSON)
        keywords = data.get("keywords", [])
        if isinstance(keywords, str):
            import json
            keywords = json.loads(keywords)

        shelf_path = data.get("shelf_path", [])
        if isinstance(shelf_path, str):
            import json
            shelf_path = json.loads(shelf_path)

        related_ids = data.get("related_ids", [])
        if isinstance(related_ids, str):
            import json
            related_ids = json.loads(related_ids)

        failed_attempts = data.get("failed_attempts", [])
        if isinstance(failed_attempts, str):
            import json
            failed_attempts = json.loads(failed_attempts)

        source_entry_ids = data.get("source_entry_ids", [])
        if isinstance(source_entry_ids, str):
            import json
            source_entry_ids = json.loads(source_entry_ids)

        steps = data.get("steps", [])
        if isinstance(steps, str):
            import json
            steps = json.loads(steps)

        evidence_tier = data.get("evidence_tier", "secondary")
        if isinstance(evidence_tier, str):
            try:
                evidence_tier = EvidenceTier(evidence_tier)
            except ValueError:
                evidence_tier = EvidenceTier.SECONDARY

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            created_at=created_at,
            updated_at=updated_at,
            source=source,
            title=data.get("title", ""),
            content=data.get("content", ""),
            summary=data.get("summary", ""),
            keywords=keywords,
            entry_type=entry_type,
            domain=data.get("domain", "web_text"),
            lang=data.get("lang", "id"),
            shelf_path=shelf_path,
            shelf_confidence=data.get("shelf_confidence", 0.0),
            related_ids=related_ids,
            supersedes_id=data.get("supersedes_id"),
            solution_for=data.get("solution_for"),
            quality_score=data.get("quality_score", 0.5),
            verified=data.get("verified", False),
            usage_count=data.get("usage_count", 0),
            was_helpful=data.get("was_helpful", 0),
            was_unhelpful=data.get("was_unhelpful", 0),
            origin_session_id=data.get("origin_session_id"),
            origin_worker_id=data.get("origin_worker_id"),
            origin_task_id=data.get("origin_task_id"),
            problem_description=data.get("problem_description"),
            failed_attempts=failed_attempts,
            solution_code=data.get("solution_code"),
            verification_result=verification_result,
            question=data.get("question"),
            answer=data.get("answer"),
            source_entry_ids=source_entry_ids,
            steps=steps,
            evidence_tier=evidence_tier,
        )


@dataclass
class ShelfNode:
    """A node in the shelf hierarchy tree.

    Represents a category/section in the Library's organization system.
    Shelves can contain sub-shelves and entries, forming a tree structure
    like: Engineering → Backend → Database → PostgreSQL.
    """

    name: str
    path: list[str]           # Full path from root
    entry_count: int = 0
    quality_avg: float = 0.0
    last_updated: Optional[datetime] = None
    children: list[ShelfNode] = field(default_factory=list)
    is_expanded: bool = False

    @property
    def path_str(self) -> str:
        """Return full path as slash-separated string."""
        return " / ".join(self.path)

    @property
    def icon(self) -> str:
        """Return icon based on state."""
        if self.children:
            return "\U0001f4c2" if self.is_expanded else "\U0001f4c1"  # 📂/📁
        return "\U0001f4c1"  # 📁

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSON export."""
        return {
            "name": self.name,
            "path": self.path,
            "entry_count": self.entry_count,
            "quality_avg": self.quality_avg,
            "last_updated": (
                self.last_updated.isoformat() if self.last_updated else None
            ),
            "children": [c.to_dict() for c in self.children],
        }
