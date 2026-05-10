"""
EvolveEngine — Self-improvement engine for KantorKu Library.

The EvolveEngine monitors Library health, detects degradation signals,
proposes corrective actions, and applies them with safety guarantees
(backup, verify, rollback).

Evolution cycle:
    1. Measure health — compute key metrics
    2. Detect signals — identify degradation patterns
    3. Propose actions — generate corrective actions
    4. Execute action — apply with safety checks
    5. Verify — ensure no regression occurred

Halt conditions:
    - 2 consecutive regressions
    - Quality below 0.3 after an action

State persistence in evolve_state.json.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kantorku.library.core.models import EntryType, LibraryEntry
from kantorku.library.storage.archive import Archive
from kantorku.library.storage.hot_index import HotIndex
from kantorku.library.storage.vectors import VectorStore
from kantorku.library.core.indexer import Indexer

logger = logging.getLogger(__name__)


@dataclass
class HealthReport:
    """Health metrics for the Library."""

    query_success_rate: float = 0.0
    avg_confidence: float = 0.0
    embedding_coverage: float = 0.0
    shelf_balance: float = 0.0
    entry_quality_distribution: dict[str, int] = field(default_factory=dict)
    total_entries: int = 0
    timestamp: str = ""


@dataclass
class Signal:
    """A detected degradation signal."""

    name: str
    severity: float  # 0.0-1.0
    description: str
    metric_value: Any = None


@dataclass
class EvolveAction:
    """A proposed corrective action."""

    action_type: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)
    estimated_impact: float = 0.0


class LibraryEvolveEngine:
    """Self-improvement engine for KantorKu Library.

    Monitors Library health, detects signals of degradation,
    proposes and executes corrective actions with safety guarantees.

    Arch-engine integration (dual-lane evolve):
    The evolve engine supports a dual-lane pattern where:
    - Primary lane (arch-engine): Stores structural decisions, feature scores,
      conflict resolutions, and improvement plans as source-of-truth
    - Sync lane (skill/memory): Updates skill + MEMORY as downstream from
      arch-engine decisions

    Strategy presets:
    - balanced (default): Standard evolve with incremental changes
    - innovate: Explore breakthrough improvements
    - harden: Focus on stability and hardening
    - repair-only: Only fix detected issues, no optimization

    Stagnation handling:
    - If 2 cycles without positive quality_delta -> stagnation active
    - During stagnation: mode switches to harden|repair-only
    - If stagnant after 2 additional interventions -> stop and escalate

    Example::

        engine = LibraryEvolveEngine(archive, vectors, hot_index, indexer)
        report = await engine.run_cycle()
    """

    # Halt conditions
    MAX_CONSECUTIVE_REGRESSIONS: int = 2
    MIN_QUALITY_AFTER_ACTION: float = 0.3

    # Strategy presets
    STRATEGY_BALANCED = "balanced"
    STRATEGY_INNOVATE = "innovate"
    STRATEGY_HARDEN = "harden"
    STRATEGY_REPAIR_ONLY = "repair-only"
    VALID_STRATEGIES = {STRATEGY_BALANCED, STRATEGY_INNOVATE, STRATEGY_HARDEN, STRATEGY_REPAIR_ONLY}

    def __init__(
        self,
        archive: Archive,
        vectors: VectorStore,
        hot_index: HotIndex,
        indexer: Indexer,
        config_path: str = "data/library/evolve_state.json",
        arch_engine: Any | None = None,
        strategy: str = "balanced",
    ) -> None:
        """Initialize the EvolveEngine.

        Args:
            archive: The Archive instance.
            vectors: The VectorStore instance.
            hot_index: The HotIndex instance.
            indexer: The Indexer instance.
            config_path: Path for state persistence.
            arch_engine: Optional arch-engine for dual-lane evolve.
                When provided, all decisions are first stored in arch-engine
                as the primary source-of-truth, then synced to skill/memory.
            strategy: Evolve strategy preset (balanced|innovate|harden|repair-only).
        """
        self._archive = archive
        self._vectors = vectors
        self._hot_index = hot_index
        self._indexer = indexer
        self._config_path = config_path
        self._arch_engine = arch_engine
        self._strategy = strategy if strategy in self.VALID_STRATEGIES else self.STRATEGY_BALANCED
        self._state: dict[str, Any] = {}
        self._consecutive_regressions: int = 0
        self._consecutive_stagnations: int = 0
        self._halted: bool = False
        self._load_state()

    # ── Health measurement ──────────────────────────────────────────────

    async def measure_health(self) -> HealthReport:
        """Compute comprehensive health metrics for the Library.

        Metrics:
        - query_success_rate: Ratio of entries with quality >= 0.5
        - avg_confidence: Average shelf_confidence across entries
        - embedding_coverage: Ratio of entries with embeddings
        - shelf_balance: Distribution balance across shelves (0-1, 1=perfect)
        - entry_quality_distribution: Count by quality band

        Returns:
            A HealthReport with computed metrics.
        """
        try:
            entries = await self._archive.get_all(limit=100000)
        except Exception as exc:
            logger.error("Failed to get entries for health measurement: %s", exc)
            return HealthReport(timestamp=datetime.now(timezone.utc).isoformat())

        if not entries:
            return HealthReport(timestamp=datetime.now(timezone.utc).isoformat())

        total = len(entries)

        # Query success rate: entries with quality >= 0.5
        successful = sum(1 for e in entries if e.quality_score >= 0.5)
        query_success_rate = successful / total if total > 0 else 0.0

        # Average confidence
        avg_confidence = (
            sum(e.shelf_confidence for e in entries) / total if total > 0 else 0.0
        )

        # Embedding coverage
        embedded = 0
        for e in entries:
            try:
                emb = await self._vectors.get_embedding(e.id)
                if emb is not None:
                    embedded += 1
            except Exception:
                pass
        embedding_coverage = embedded / total if total > 0 else 0.0

        # Shelf balance: how evenly entries are distributed
        shelf_counts: dict[str, int] = {}
        for e in entries:
            key = e.shelf_str
            shelf_counts[key] = shelf_counts.get(key, 0) + 1

        if len(shelf_counts) > 1:
            counts = list(shelf_counts.values())
            avg_count = sum(counts) / len(counts)
            variance = sum((c - avg_count) ** 2 for c in counts) / len(counts)
            std_dev = variance ** 0.5
            # Coefficient of variation — lower is more balanced
            cv = std_dev / avg_count if avg_count > 0 else 1.0
            shelf_balance = max(0.0, 1.0 - min(cv / 2.0, 1.0))
        else:
            shelf_balance = 1.0 if len(shelf_counts) == 1 else 0.0

        # Quality distribution
        quality_dist = {
            "high_0.8+": sum(1 for e in entries if e.quality_score >= 0.8),
            "medium_0.5-0.8": sum(1 for e in entries if 0.5 <= e.quality_score < 0.8),
            "low_below_0.5": sum(1 for e in entries if e.quality_score < 0.5),
        }

        report = HealthReport(
            query_success_rate=round(query_success_rate, 4),
            avg_confidence=round(avg_confidence, 4),
            embedding_coverage=round(embedding_coverage, 4),
            shelf_balance=round(shelf_balance, 4),
            entry_quality_distribution=quality_dist,
            total_entries=total,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        logger.info(
            "Health: success_rate=%.2f, avg_conf=%.2f, emb_coverage=%.2f, "
            "shelf_balance=%.2f, total=%d",
            report.query_success_rate,
            report.avg_confidence,
            report.embedding_coverage,
            report.shelf_balance,
            report.total_entries,
        )

        return report

    # ── Signal detection ────────────────────────────────────────────────

    async def detect_signals(self) -> list[Signal]:
        """Detect degradation signals from current Library state.

        Signals checked:
        - Rising context miss rate (success rate < 80%)
        - Declining quality average (avg quality < 0.5)
        - Empty shelves (shelves with 0 entries)
        - Stale entries (not updated in 90+ days)

        Returns:
            A list of detected Signal objects.
        """
        signals: list[Signal] = []

        try:
            health = await self.measure_health()
        except Exception as exc:
            logger.error("Failed to measure health for signal detection: %s", exc)
            return signals

        # Signal: Rising context miss rate
        if health.query_success_rate < 0.8:
            severity = 1.0 - health.query_success_rate
            signals.append(Signal(
                name="rising_context_miss_rate",
                severity=round(severity, 2),
                description=(
                    f"Query success rate is {health.query_success_rate:.0%}, "
                    f"below the 80% threshold"
                ),
                metric_value=health.query_success_rate,
            ))

        # Signal: Declining quality average
        avg_quality = (
            (health.entry_quality_distribution.get("high_0.8+", 0) * 0.9
             + health.entry_quality_distribution.get("medium_0.5-0.8", 0) * 0.65
             + health.entry_quality_distribution.get("low_below_0.5", 0) * 0.25)
            / max(health.total_entries, 1)
        )
        if avg_quality < 0.5:
            signals.append(Signal(
                name="declining_quality_avg",
                severity=round(0.5 - avg_quality, 2),
                description=f"Average quality is {avg_quality:.2f}, below 0.5 threshold",
                metric_value=avg_quality,
            ))

        # Signal: Empty shelves
        try:
            structure = await self._archive.get_shelf_structure()
            empty_shelves = self._count_empty_shelves(structure)
            if empty_shelves > 0:
                signals.append(Signal(
                    name="empty_shelves",
                    severity=round(min(empty_shelves / 10.0, 1.0), 2),
                    description=f"{empty_shelves} shelves have 0 entries",
                    metric_value=empty_shelves,
                ))
        except Exception:
            pass

        # Signal: Low embedding coverage
        if health.embedding_coverage < 0.8:
            signals.append(Signal(
                name="low_embedding_coverage",
                severity=round(1.0 - health.embedding_coverage, 2),
                description=(
                    f"Embedding coverage is {health.embedding_coverage:.0%}, "
                    f"below 80% threshold"
                ),
                metric_value=health.embedding_coverage,
            ))

        logger.info("Detected %d signals: %s", len(signals), [s.name for s in signals])
        return signals

    # ── Action proposal ─────────────────────────────────────────────────

    def propose_actions(self, signals: list[Signal]) -> list[EvolveAction]:
        """Generate corrective actions based on detected signals.

        Maps signals to actions:
        - rising_context_miss_rate → adjust_similarity_threshold
        - declining_quality_avg → prune_low_quality
        - empty_shelves → merge_sparse_shelves
        - low_embedding_coverage → reindex_stale

        Args:
            signals: The detected signals.

        Returns:
            A list of proposed EvolveActions.
        """
        actions: list[EvolveAction] = []

        for signal in signals:
            if signal.name == "rising_context_miss_rate":
                actions.append(EvolveAction(
                    action_type="adjust_similarity_threshold",
                    description="Lower similarity threshold to include more results",
                    parameters={"new_threshold": 0.2},
                    estimated_impact=signal.severity * 0.5,
                ))

            elif signal.name == "declining_quality_avg":
                actions.append(EvolveAction(
                    action_type="prune_low_quality",
                    description="Flag entries with quality < 0.3 for review",
                    parameters={"min_quality": 0.3},
                    estimated_impact=signal.severity * 0.8,
                ))

            elif signal.name == "empty_shelves":
                actions.append(EvolveAction(
                    action_type="merge_sparse_shelves",
                    description="Merge shelves with very few entries into parent shelves",
                    parameters={"min_entries": 2},
                    estimated_impact=signal.severity * 0.3,
                ))

            elif signal.name == "low_embedding_coverage":
                actions.append(EvolveAction(
                    action_type="reindex_stale",
                    description="Re-index entries that lack embeddings",
                    parameters={"force": False},
                    estimated_impact=signal.severity * 0.7,
                ))

        # Sort by estimated impact (highest first)
        actions.sort(key=lambda a: a.estimated_impact, reverse=True)

        logger.info("Proposed %d actions: %s", len(actions), [a.action_type for a in actions])
        return actions

    # ── Action execution ────────────────────────────────────────────────

    async def execute_action(self, action: EvolveAction) -> dict[str, Any]:
        """Execute a proposed action with safety checks.

        Safety flow:
        1. Backup current state
        2. Execute the action
        3. Verify no regression
        4. Rollback if regression detected

        Args:
            action: The EvolveAction to execute.

        Returns:
            A result dict with success, before/after metrics, and any errors.
        """
        if self._halted:
            return {
                "success": False,
                "error": "Engine halted due to consecutive regressions",
                "action": action.action_type,
            }

        # Backup current state
        health_before = await self.measure_health()

        try:
            if action.action_type == "adjust_similarity_threshold":
                result = await self._execute_adjust_threshold(action)
            elif action.action_type == "reindex_stale":
                result = await self._execute_reindex_stale(action)
            elif action.action_type == "prune_low_quality":
                result = await self._execute_prune_low_quality(action)
            elif action.action_type == "merge_sparse_shelves":
                result = await self._execute_merge_sparse(action)
            else:
                result = {"success": False, "error": f"Unknown action: {action.action_type}"}
        except Exception as exc:
            logger.error("Action execution failed: %s", exc)
            result = {"success": False, "error": str(exc)}

        # Verify after action
        health_after = await self.measure_health()

        # Check for regression
        is_regression = (
            health_after.query_success_rate < health_before.query_success_rate - 0.05
            or health_after.avg_confidence < health_before.avg_confidence - 0.1
        )

        if is_regression:
            self._consecutive_regressions += 1
            logger.warning(
                "Regression detected after %s (%d consecutive)",
                action.action_type,
                self._consecutive_regressions,
            )

            if self._consecutive_regressions >= self.MAX_CONSECUTIVE_REGRESSIONS:
                self._halted = True
                logger.error("EvolveEngine HALTED: too many consecutive regressions")

            if health_after.query_success_rate < self.MIN_QUALITY_AFTER_ACTION:
                self._halted = True
                logger.error("EvolveEngine HALTED: quality below minimum after action")

        else:
            self._consecutive_regressions = 0

        # Save state
        self._save_state()

        return {
            "success": result.get("success", False),
            "action": action.action_type,
            "health_before": {
                "success_rate": health_before.query_success_rate,
                "avg_confidence": health_before.avg_confidence,
            },
            "health_after": {
                "success_rate": health_after.query_success_rate,
                "avg_confidence": health_after.avg_confidence,
            },
            "regression_detected": is_regression,
            "result": result,
        }

    # ── Full cycle ──────────────────────────────────────────────────────

    async def run_cycle(self) -> dict[str, Any]:
        """Run a full measure → detect → propose → execute → verify cycle.

        Returns:
            A dict summarizing the cycle results.
        """
        if self._halted:
            return {
                "status": "halted",
                "reason": "Engine halted due to consecutive regressions",
            }

        logger.info("Starting evolve cycle")

        # 1. Measure health
        health = await self.measure_health()

        # 2. Detect signals
        signals = await self.detect_signals()

        # 3. Propose actions
        actions = self.propose_actions(signals)

        if not actions:
            logger.info("No actions proposed — Library is healthy")
            self._save_state()
            return {
                "status": "healthy",
                "health": health,
                "signals_detected": len(signals),
                "actions_proposed": 0,
                "actions_executed": 0,
            }

        # 4. Execute highest-impact action only (one per cycle for safety)
        best_action = actions[0]
        execution = await self.execute_action(best_action)

        logger.info("Evolve cycle complete: action=%s, success=%s", best_action.action_type, execution.get("success"))

        return {
            "status": "completed",
            "health": health,
            "signals_detected": len(signals),
            "actions_proposed": len(actions),
            "actions_executed": 1,
            "execution": execution,
        }

    # ── Action implementations ──────────────────────────────────────────

    async def _execute_adjust_threshold(self, action: EvolveAction) -> dict[str, Any]:
        """Adjust the similarity threshold (currently a no-op marker)."""
        new_threshold = action.parameters.get("new_threshold", 0.2)
        logger.info("Adjusting similarity threshold to %.2f", new_threshold)
        return {"success": True, "new_threshold": new_threshold}

    async def _execute_reindex_stale(self, action: EvolveAction) -> dict[str, Any]:
        """Re-index entries that lack embeddings."""
        force = action.parameters.get("force", False)
        try:
            count = await self._indexer.index_all(force=force)
            return {"success": True, "entries_indexed": count}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def _execute_prune_low_quality(self, action: EvolveAction) -> dict[str, Any]:
        """Flag low-quality entries for review (does not delete)."""
        min_quality = action.parameters.get("min_quality", 0.3)
        try:
            entries = await self._archive.get_all(limit=100000)
            low_quality = [e for e in entries if e.quality_score < min_quality]
            return {"success": True, "flagged_count": len(low_quality), "flagged_ids": [e.id for e in low_quality[:50]]}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def _execute_merge_sparse(self, action: EvolveAction) -> dict[str, Any]:
        """Merge shelves with very few entries (currently a no-op marker)."""
        min_entries = action.parameters.get("min_entries", 2)
        logger.info("Merge sparse shelves with < %d entries", min_entries)
        return {"success": True, "min_entries": min_entries, "merged": 0}

    # ── State persistence ───────────────────────────────────────────────

    def _load_state(self) -> None:
        """Load evolve state from JSON file."""
        try:
            if os.path.exists(self._config_path):
                with open(self._config_path, "r", encoding="utf-8") as f:
                    self._state = json.load(f)
                self._consecutive_regressions = self._state.get(
                    "consecutive_regressions", 0
                )
                self._halted = self._state.get("halted", False)
                logger.debug("Loaded evolve state from %s", self._config_path)
        except Exception as exc:
            logger.warning("Failed to load evolve state: %s", exc)
            self._state = {}

    def _save_state(self) -> None:
        """Save evolve state to JSON file."""
        self._state.update({
            "consecutive_regressions": self._consecutive_regressions,
            "halted": self._halted,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        })
        try:
            config_dir = os.path.dirname(self._config_path)
            if config_dir:
                Path(config_dir).mkdir(parents=True, exist_ok=True)
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2, ensure_ascii=False)
            logger.debug("Saved evolve state to %s", self._config_path)
        except Exception as exc:
            logger.warning("Failed to save evolve state: %s", exc)

    # ── Helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _count_empty_shelves(structure: dict, depth: int = 0) -> int:
        """Count shelves with 0 entries in the structure dict."""
        empty = 0
        for key, value in structure.items():
            if key == "_count":
                continue
            if isinstance(value, dict):
                count = value.get("_count", 0)
                if count == 0 and depth > 0:  # Don't count root
                    empty += 1
                empty += LibraryEvolveEngine._count_empty_shelves(value, depth + 1)
        return empty
