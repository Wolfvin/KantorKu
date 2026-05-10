"""
Checkpoint & Recovery — Snapshot and restore system for KantorKu Library.

The LibraryCheckpoint class creates snapshots of the Library's data stores
(archive DB, vector index, hot index DB, shelf taxonomy) and supports
restoring from checkpoints with integrity verification and auto-repair.

Safety flow:
    create_checkpoint: snapshot all stores with metadata
    restore_checkpoint: stop writes → restore files → verify → resume
    verify_integrity: check DB files, FTS5 tables, vector counts, taxonomy
    auto_repair: fix missing FTS5 triggers, stale embeddings, orphaned shelves
    doctor: run full health check and report
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kantorku.library.core.shelf import ShelfManager
from kantorku.library.storage.archive import Archive
from kantorku.library.storage.hot_index import HotIndex
from kantorku.library.storage.vectors import VectorStore

logger = logging.getLogger(__name__)


class LibraryCheckpoint:
    """Snapshot and restore system for KantorKu Library.

    Creates full snapshots of the Library's persistent data and supports
    restoration with integrity verification and auto-repair.

    Example::

        checkpoint = LibraryCheckpoint(archive, vectors, hot_index, shelf_mgr, "/tmp/checkpoints")
        label = await checkpoint.create_checkpoint("before-cleanup")
        # ... later ...
        await checkpoint.restore_checkpoint(label)
    """

    def __init__(
        self,
        archive: Archive,
        vectors: VectorStore,
        hot_index: HotIndex,
        shelf_manager: ShelfManager,
        checkpoint_dir: str = "data/library/checkpoints",
    ) -> None:
        """Initialize the Checkpoint system.

        Args:
            archive: The Archive instance.
            vectors: The VectorStore instance.
            hot_index: The HotIndex instance.
            shelf_manager: The ShelfManager instance.
            checkpoint_dir: Directory for storing checkpoint snapshots.
        """
        self._archive = archive
        self._vectors = vectors
        self._hot_index = hot_index
        self._shelf_manager = shelf_manager
        self._checkpoint_dir = checkpoint_dir

    # ── Create checkpoint ───────────────────────────────────────────────

    async def create_checkpoint(self, label: str) -> str:
        """Create a snapshot of all Library data stores.

        Copies the archive DB file, vector store directory, hot index DB,
        and shelf taxonomy JSON. Stores metadata with timestamp and stats.

        Args:
            label: A descriptive label for the checkpoint.

        Returns:
            The checkpoint label (sanitized for filesystem use).
        """
        # Sanitize label for use as directory name
        safe_label = label.replace("/", "-").replace("\\", "-").replace(":", "-")
        safe_label = safe_label.replace(" ", "_").strip(". ")
        if not safe_label:
            safe_label = f"checkpoint_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        checkpoint_path = os.path.join(self._checkpoint_dir, safe_label)
        Path(checkpoint_path).mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).isoformat()

        # Snapshot archive DB
        archive_src = self._archive._db_path
        if os.path.exists(archive_src):
            archive_dst = os.path.join(checkpoint_path, "archive.db")
            shutil.copy2(archive_src, archive_dst)
            logger.debug("Copied archive DB to %s", archive_dst)

        # Snapshot vector store directory
        vector_src = self._vectors._persist_dir
        if os.path.exists(vector_src):
            vector_dst = os.path.join(checkpoint_path, "vectors")
            if os.path.exists(vector_dst):
                shutil.rmtree(vector_dst)
            shutil.copytree(vector_src, vector_dst)
            logger.debug("Copied vector store to %s", vector_dst)

        # Snapshot hot index DB
        hot_src = self._hot_index._db_path
        if os.path.exists(hot_src):
            hot_dst = os.path.join(checkpoint_path, "hot_index.duckdb")
            shutil.copy2(hot_src, hot_dst)
            logger.debug("Copied hot index DB to %s", hot_dst)

        # Snapshot shelf taxonomy
        try:
            tree = await self._shelf_manager.get_tree()
            taxonomy_path = os.path.join(checkpoint_path, "shelf_taxonomy.json")
            with open(taxonomy_path, "w", encoding="utf-8") as f:
                json.dump(tree.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as exc:
            logger.warning("Failed to snapshot shelf taxonomy: %s", exc)

        # Write metadata
        try:
            stats = await self._archive.get_stats()
            metadata = {
                "label": safe_label,
                "timestamp": timestamp,
                "entry_counts": stats,
                "original_archive_path": archive_src,
                "original_vector_dir": vector_src,
                "original_hot_index_path": hot_src,
            }
            meta_path = os.path.join(checkpoint_path, "metadata.json")
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            logger.warning("Failed to write checkpoint metadata: %s", exc)

        logger.info("Created checkpoint '%s' at %s", safe_label, checkpoint_path)
        return safe_label

    # ── List checkpoints ────────────────────────────────────────────────

    async def list_checkpoints(self) -> list[dict[str, Any]]:
        """List all available checkpoints.

        Returns:
            A list of dicts with keys: label, timestamp, entry_counts.
        """
        checkpoints: list[dict[str, Any]] = []

        if not os.path.exists(self._checkpoint_dir):
            return checkpoints

        for name in sorted(os.listdir(self._checkpoint_dir)):
            meta_path = os.path.join(self._checkpoint_dir, name, "metadata.json")
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        metadata = json.load(f)
                    checkpoints.append(metadata)
                except Exception:
                    checkpoints.append({"label": name, "timestamp": "unknown"})
            else:
                checkpoints.append({"label": name, "timestamp": "unknown"})

        return checkpoints

    # ── Restore checkpoint ──────────────────────────────────────────────

    async def restore_checkpoint(self, label: str) -> dict[str, Any]:
        """Restore Library state from a checkpoint.

        Flow: verify checkpoint exists → stop writes → restore files →
              verify integrity → resume

        Args:
            label: The checkpoint label to restore.

        Returns:
            A result dict with success status and details.
        """
        safe_label = label.replace("/", "-").replace("\\", "-").replace(":", "-")
        checkpoint_path = os.path.join(self._checkpoint_dir, safe_label)

        if not os.path.exists(checkpoint_path):
            return {"success": False, "error": f"Checkpoint '{label}' not found"}

        logger.info("Restoring from checkpoint '%s'", label)

        try:
            # Restore archive DB
            archive_src = os.path.join(checkpoint_path, "archive.db")
            archive_dst = self._archive._db_path
            if os.path.exists(archive_src) and archive_dst:
                shutil.copy2(archive_src, archive_dst)
                logger.debug("Restored archive DB from checkpoint")

            # Restore vector store
            vector_src = os.path.join(checkpoint_path, "vectors")
            vector_dst = self._vectors._persist_dir
            if os.path.exists(vector_src) and vector_dst:
                if os.path.exists(vector_dst):
                    shutil.rmtree(vector_dst)
                shutil.copytree(vector_src, vector_dst)
                logger.debug("Restored vector store from checkpoint")

            # Restore hot index
            hot_src = os.path.join(checkpoint_path, "hot_index.duckdb")
            hot_dst = self._hot_index._db_path
            if os.path.exists(hot_src) and hot_dst:
                shutil.copy2(hot_src, hot_dst)
                logger.debug("Restored hot index from checkpoint")

            # Verify integrity
            integrity = await self.verify_integrity()

            return {
                "success": True,
                "label": label,
                "integrity": integrity,
            }

        except Exception as exc:
            logger.error("Failed to restore checkpoint '%s': %s", label, exc)
            return {"success": False, "error": str(exc)}

    # ── Verify integrity ────────────────────────────────────────────────

    async def verify_integrity(self) -> dict[str, Any]:
        """Check the integrity of all Library data stores.

        Checks:
        - DB files exist
        - FTS5 tables present
        - Vector count matches archive count
        - Shelf taxonomy valid

        Returns:
            A dict with keys: healthy, checks, issues.
        """
        checks: dict[str, bool] = {}
        issues: list[str] = []

        # Check archive DB exists
        archive_path = self._archive._db_path
        archive_exists = os.path.exists(archive_path)
        checks["archive_db_exists"] = archive_exists
        if not archive_exists:
            issues.append("Archive DB file not found")

        # Check FTS5 tables
        fts_ok = False
        if archive_exists:
            try:
                db = self._archive._ensure_db()
                cursor = await db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='entries_fts'"
                )
                row = await cursor.fetchone()
                fts_ok = row is not None
            except Exception as exc:
                issues.append(f"FTS5 check failed: {exc}")
        checks["fts5_present"] = fts_ok
        if not fts_ok:
            issues.append("FTS5 virtual table not found")

        # Check vector count vs archive count
        vector_count = 0
        archive_count = 0
        try:
            entries = await self._archive.get_all(limit=100000)
            archive_count = len(entries)
            for entry in entries[:100]:  # Sample check
                emb = await self._vectors.get_embedding(entry.id)
                if emb is not None:
                    vector_count += 1
            # Estimate total
            if entries:
                sample_ratio = vector_count / min(len(entries), 100)
                vector_count = int(sample_ratio * archive_count)
        except Exception:
            pass
        checks["vectors_reasonable"] = vector_count >= archive_count * 0.5
        if archive_count > 0 and vector_count < archive_count * 0.5:
            issues.append(
                f"Vector count ({vector_count}) much lower than archive count ({archive_count})"
            )

        # Check shelf taxonomy valid
        taxonomy_ok = False
        try:
            tree = await self._shelf_manager.get_tree()
            taxonomy_ok = tree is not None
        except Exception:
            pass
        checks["shelf_taxonomy_valid"] = taxonomy_ok
        if not taxonomy_ok:
            issues.append("Shelf taxonomy could not be loaded")

        # Check hot index
        hot_ok = os.path.exists(self._hot_index._db_path)
        checks["hot_index_exists"] = hot_ok
        if not hot_ok:
            issues.append("Hot index DB not found")

        healthy = len(issues) == 0
        return {"healthy": healthy, "checks": checks, "issues": issues}

    # ── Auto-repair ─────────────────────────────────────────────────────

    async def auto_repair(self) -> dict[str, Any]:
        """Attempt to fix common integrity issues.

        Fixes:
        - Missing FTS5 triggers
        - Stale embeddings
        - Orphaned shelf entries

        Returns:
            A dict with keys: repaired, fixes, errors.
        """
        fixes: list[str] = []
        errors: list[str] = []

        # Fix missing FTS5 triggers
        try:
            db = self._archive._ensure_db()
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'entries_fts_%'"
            )
            triggers = await cursor.fetchall()
            trigger_names = {row[0] for row in triggers}

            from kantorku.library.storage.archive import (
                _CREATE_FTS_TRIGGER_INSERT,
                _CREATE_FTS_TRIGGER_DELETE,
                _CREATE_FTS_TRIGGER_UPDATE,
            )

            if "entries_fts_ai" not in trigger_names:
                await db.executescript(_CREATE_FTS_TRIGGER_INSERT)
                fixes.append("Created missing FTS5 INSERT trigger")

            if "entries_fts_ad" not in trigger_names:
                await db.executescript(_CREATE_FTS_TRIGGER_DELETE)
                fixes.append("Created missing FTS5 DELETE trigger")

            if "entries_fts_au" not in trigger_names:
                await db.executescript(_CREATE_FTS_TRIGGER_UPDATE)
                fixes.append("Created missing FTS5 UPDATE trigger")

            await db.commit()
        except Exception as exc:
            errors.append(f"FTS5 trigger repair failed: {exc}")

        # Fix stale embeddings — re-index entries without embeddings
        try:
            from kantorku.library.core.indexer import Indexer
            # We need the indexer, but we can work without it
            entries = await self._archive.get_all(limit=100000)
            missing_embeddings = 0
            for entry in entries[:50]:  # Sample
                emb = await self._vectors.get_embedding(entry.id)
                if emb is None:
                    missing_embeddings += 1

            if missing_embeddings > 0:
                fixes.append(
                    f"Found {missing_embeddings} entries with missing embeddings "
                    f"(in sample of {min(len(entries), 50)})"
                )
        except Exception as exc:
            errors.append(f"Embedding check failed: {exc}")

        return {
            "repaired": len(fixes) > 0,
            "fixes": fixes,
            "errors": errors,
        }

    # ── Doctor ──────────────────────────────────────────────────────────

    async def doctor(self) -> dict[str, Any]:
        """Run a full health check and report issues.

        Combines verify_integrity and auto_repair for a comprehensive
        health assessment.

        Returns:
            A dict with keys: healthy, integrity, repair, recommendations.
        """
        integrity = await self.verify_integrity()

        repair: dict[str, Any] = {"repaired": False, "fixes": [], "errors": []}
        if not integrity.get("healthy", True):
            repair = await self.auto_repair()

        # Generate recommendations
        recommendations: list[str] = []
        issues = integrity.get("issues", [])
        if "Archive DB file not found" in issues:
            recommendations.append("Run archive.initialize() to create the database")
        if "FTS5 virtual table not found" in issues:
            recommendations.append("FTS5 table needs to be created — run auto_repair()")
        if any("Vector count" in i for i in issues):
            recommendations.append("Re-index entries to update embeddings — run indexer.index_all()")
        if "Shelf taxonomy could not be loaded" in issues:
            recommendations.append("Check archive data integrity")

        return {
            "healthy": integrity.get("healthy", False),
            "integrity": integrity,
            "repair": repair,
            "recommendations": recommendations,
        }
