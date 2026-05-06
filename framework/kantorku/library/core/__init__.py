"""Library core modules — models, AI components, shelf system, indexing, and export."""

from kantorku.library.core.models import (
    LibraryEntry,
    EntryType,
    EntrySource,
    ShelfNode,
    EvidenceTier,
    VerificationResult,
)
from kantorku.library.core.librarian import Librarian
from kantorku.library.core.archivist import Archivist
from kantorku.library.core.shelf import ShelfManager
from kantorku.library.core.indexer import Indexer
from kantorku.library.core.exporter import Exporter
from kantorku.library.core.think_gate import ThinkGate, ThinkAction, ThinkResult
from kantorku.library.core.skill_router import LibrarySkillRouter, RouteResult, WORKER_MAP
from kantorku.library.core.evolve_engine import LibraryEvolveEngine, HealthReport, Signal, EvolveAction
from kantorku.library.core.checkpoint import LibraryCheckpoint
from kantorku.library.core.token_optimizer import TokenOptimizer, BudgetMode
from kantorku.library.core.senior_call import LibrarySeniorCall, Verdict, ReviewResult, ReviewIssue
from kantorku.library.core.web_search import LibraryWebSearch, SourceTier, EscalationLevel, WebSearchResult
from kantorku.library.core.dead_detector import DeadEntryDetector, DeadEntryFinding
from kantorku.library.core.repo_intake import RepoIntake
from kantorku.library.core.failure_recorder import BlamelessFailureRecorder, FailureRecord
from kantorku.library.core.multi_ingest import MultiFormatIngest

__all__ = [
    # Models
    "LibraryEntry",
    "EntryType",
    "EntrySource",
    "ShelfNode",
    "EvidenceTier",
    "VerificationResult",
    # Core components
    "Librarian",
    "Archivist",
    "ShelfManager",
    "Indexer",
    "Exporter",
    # L9: Think Gate
    "ThinkGate",
    "ThinkAction",
    "ThinkResult",
    # L10: Skill Router
    "LibrarySkillRouter",
    "RouteResult",
    "WORKER_MAP",
    # L11: Evolve Engine
    "LibraryEvolveEngine",
    "HealthReport",
    "Signal",
    "EvolveAction",
    # L12: Checkpoint & Recovery
    "LibraryCheckpoint",
    # L13: Token Optimization
    "TokenOptimizer",
    "BudgetMode",
    # L14: Senior Call
    "LibrarySeniorCall",
    "Verdict",
    "ReviewResult",
    "ReviewIssue",
    # L15: Web Search
    "LibraryWebSearch",
    "SourceTier",
    "EscalationLevel",
    "WebSearchResult",
    # L16: Dead Entry Detection
    "DeadEntryDetector",
    "DeadEntryFinding",
    # L17: Repo Intake
    "RepoIntake",
    # L24: Failure Recorder
    "BlamelessFailureRecorder",
    "FailureRecord",
    # L26: Multi-Format Ingest
    "MultiFormatIngest",
]
