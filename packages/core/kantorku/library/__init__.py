"""
KantorKu Library — Knowledge management system.

A persistent, searchable knowledge base that integrates with the KantorKu
office workflow. Library entries are organized into a hierarchical shelf
system (like a real library) and can be searched via vector similarity.

Components:
    core/      — Librarian (AI categorization), Archivist (AI answering),
                 Shelf system, Indexer (vector embedding), Exporter,
                 ThinkGate, SkillRouter, EvolveEngine, Checkpoint,
                 TokenOptimizer, SeniorCall, WebSearch, DeadDetector,
                 RepoIntake, FailureRecorder, MultiFormatIngest
    storage/   — Archive (SQLite), HotIndex (DuckDB), Vectors (ChromaDB/FAISS)
    bridge/    — KantorKu integration, Losion export
    training/  — Fine-tune recipe and data formatting for Librarian model
"""

from kantorku.library.core.models import LibraryEntry, EntryType, EntrySource, EvidenceTier
from kantorku.library.core.think_gate import ThinkGate, ThinkAction
from kantorku.library.core.skill_router import LibrarySkillRouter
from kantorku.library.core.evolve_engine import LibraryEvolveEngine
from kantorku.library.core.checkpoint import LibraryCheckpoint
from kantorku.library.core.token_optimizer import TokenOptimizer
from kantorku.library.core.senior_call import LibrarySeniorCall
from kantorku.library.core.web_search import LibraryWebSearch
from kantorku.library.core.dead_detector import DeadEntryDetector
from kantorku.library.core.repo_intake import RepoIntake
from kantorku.library.core.failure_recorder import BlamelessFailureRecorder
from kantorku.library.core.multi_ingest import MultiFormatIngest

__all__ = [
    "LibraryEntry",
    "EntryType",
    "EntrySource",
    "EvidenceTier",
    "ThinkGate",
    "ThinkAction",
    "LibrarySkillRouter",
    "LibraryEvolveEngine",
    "LibraryCheckpoint",
    "TokenOptimizer",
    "LibrarySeniorCall",
    "LibraryWebSearch",
    "DeadEntryDetector",
    "RepoIntake",
    "BlamelessFailureRecorder",
    "MultiFormatIngest",
]
