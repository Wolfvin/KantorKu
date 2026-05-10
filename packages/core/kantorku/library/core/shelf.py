"""
Shelf — Hierarchical shelf management for KantorKu Library.

The ShelfManager maintains the Library's organizational hierarchy,
analogous to a real library's shelving system. Shelves are implicit —
they exist by virtue of having entries placed on them via their
``shelf_path`` field.

Shelves form a tree structure like::

    Engineering
    ├── Backend
    │   ├── Python
    │   └── Database
    ├── Frontend
    │   └── React
    └── DevOps
        └── Docker
    Mathematics
    ├── Statistics
    └── Logic

The ShelfManager provides operations for browsing the tree, suggesting
shelf placements, moving entries between shelves, and merging shelves.

Example::

    from kantorku.library.storage.archive import Archive

    archive = Archive("data/library/archive.db")
    await archive.initialize()

    shelf_mgr = ShelfManager(archive=archive)
    tree = await shelf_mgr.get_tree()
    suggestions = await shelf_mgr.suggest_shelf(
        "Python async patterns", ["python", "async", "concurrency"]
    )
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from kantorku.library.core.models import LibraryEntry, ShelfNode
from kantorku.library.storage.archive import Archive

logger = logging.getLogger(__name__)

# ── Default Shelf Taxonomy ──────────────────────────────────────────────────
# Built-in taxonomy used for shelf suggestions when no existing shelves match.

DEFAULT_TAXONOMY: dict[str, dict[str, Any]] = {
    "Engineering": {
        "Backend": {
            "Python": {},
            "JavaScript": {},
            "Go": {},
            "Rust": {},
            "Database": {
                "SQL": {},
                "NoSQL": {},
            },
            "API": {},
        },
        "Frontend": {
            "React": {},
            "Vue": {},
            "Angular": {},
            "CSS": {},
            "TypeScript": {},
        },
        "DevOps": {
            "Docker": {},
            "Kubernetes": {},
            "CI/CD": {},
            "Terraform": {},
            "Monitoring": {},
        },
        "Architecture": {
            "Design Patterns": {},
            "Microservices": {},
            "Event-Driven": {},
            "Clean Architecture": {},
        },
        "Security": {
            "Authentication": {},
            "Encryption": {},
            "OWASP": {},
            "Penetration Testing": {},
        },
    },
    "Mathematics": {
        "Algebra": {
            "Linear Algebra": {},
            "Abstract Algebra": {},
        },
        "Calculus": {
            "Differential": {},
            "Integral": {},
        },
        "Statistics": {
            "Bayesian": {},
            "Frequentist": {},
            "Regression": {},
        },
        "Logic": {
            "Propositional": {},
            "Predicate": {},
            "Modal": {},
        },
    },
    "Science": {
        "Physics": {
            "Quantum": {},
            "Classical": {},
            "Relativity": {},
        },
        "Chemistry": {
            "Organic": {},
            "Inorganic": {},
        },
        "Biology": {
            "Genetics": {},
            "Ecology": {},
            "Microbiology": {},
        },
    },
    "Philosophy": {
        "Ethics": {},
        "Metaphysics": {},
        "Epistemology": {},
        "Aesthetics": {},
    },
    "Business": {
        "Strategy": {},
        "Marketing": {},
        "Finance": {},
        "Management": {},
    },
    "Language": {
        "Linguistics": {},
        "NLP": {},
        "Translation": {},
    },
    "Arts": {
        "Design": {},
        "Music": {},
        "Literature": {},
    },
}

# ── Topic indicators for shelf suggestion ───────────────────────────────────
# Maps keyword patterns to suggested shelf paths.

_TOPIC_SHELF_MAP: list[tuple[list[str], list[str]]] = [
    # Engineering / Backend
    (["python", "django", "flask", "fastapi"], ["Engineering", "Backend", "Python"]),
    (["javascript", "typescript", "node", "express"], ["Engineering", "Backend", "JavaScript"]),
    (["go", "golang"], ["Engineering", "Backend", "Go"]),
    (["rust"], ["Engineering", "Backend", "Rust"]),
    (["sql", "postgres", "mysql", "sqlite"], ["Engineering", "Backend", "Database", "SQL"]),
    (["mongodb", "redis", "dynamodb", "nosql"], ["Engineering", "Backend", "Database", "NoSQL"]),
    (["api", "rest", "graphql", "grpc"], ["Engineering", "Backend", "API"]),
    # Engineering / Frontend
    (["react", "nextjs", "next.js"], ["Engineering", "Frontend", "React"]),
    (["vue", "nuxt"], ["Engineering", "Frontend", "Vue"]),
    (["angular"], ["Engineering", "Frontend", "Angular"]),
    (["css", "tailwind", "sass", "scss"], ["Engineering", "Frontend", "CSS"]),
    # Engineering / DevOps
    (["docker", "container", "dockerfile"], ["Engineering", "DevOps", "Docker"]),
    (["kubernetes", "k8s", "helm"], ["Engineering", "DevOps", "Kubernetes"]),
    (["ci/cd", "jenkins", "github actions", "gitlab ci"], ["Engineering", "DevOps", "CI/CD"]),
    (["terraform", "iac", "infrastructure as code"], ["Engineering", "DevOps", "Terraform"]),
    # Engineering / Architecture
    (["design pattern", "factory", "singleton", "observer"], ["Engineering", "Architecture", "Design Patterns"]),
    (["microservice", "microservices"], ["Engineering", "Architecture", "Microservices"]),
    # Engineering / Security
    (["auth", "oauth", "jwt", "authentication"], ["Engineering", "Security", "Authentication"]),
    (["encryption", "ssl", "tls", "crypto"], ["Engineering", "Security", "Encryption"]),
    # Mathematics
    (["algebra", "matrix", "vector space"], ["Mathematics", "Algebra"]),
    (["calculus", "derivative", "integral"], ["Mathematics", "Calculus"]),
    (["statistics", "probability", "regression", "bayesian"], ["Mathematics", "Statistics"]),
    (["logic", "proposition", "inference", "proof"], ["Mathematics", "Logic"]),
    # Science
    (["physics", "quantum", "mechanics", "relativity"], ["Science", "Physics"]),
    (["chemistry", "molecule", "reaction"], ["Science", "Chemistry"]),
    (["biology", "cell", "dna", "genetics"], ["Science", "Biology"]),
    # Philosophy
    (["philosophy", "ethics", "metaphysics"], ["Philosophy"]),
    # Business
    (["business", "startup", "marketing", "strategy"], ["Business"]),
    # Language
    (["language", "linguistics", "nlp", "translation"], ["Language"]),
    # Arts
    (["arts", "design", "music", "creative"], ["Arts"]),
]


class ShelfManager:
    """Hierarchical shelf management for KantorKu Library.

    Provides operations for browsing the shelf tree, suggesting shelf
    placements, moving entries between shelves, and merging shelves.

    Shelves are implicit — they exist when entries have a given ``shelf_path``.
    The ShelfManager reads shelf structure from the Archive and can suggest
    paths using the built-in taxonomy.

    Args:
        archive: The Archive instance for persistent storage.
    """

    def __init__(self, archive: Archive) -> None:
        self._archive = archive

    # ── Tree operations ──────────────────────────────────────────────────

    async def get_tree(self) -> ShelfNode:
        """Build the full shelf tree from archive data.

        Queries the Archive for all distinct shelf paths and their
        entry counts, then constructs a ShelfNode tree with aggregated
        statistics (entry count, average quality, last updated).

        Returns:
            The root ShelfNode containing the full shelf hierarchy.
        """
        structure = await self._archive.get_shelf_structure()
        root = ShelfNode(name="Library", path=[])

        # Get stats per shelf for quality and dates
        shelf_stats = await self._get_shelf_stats_map()

        # Build tree recursively from the structure dict
        self._build_tree_from_structure(
            node=root,
            structure=structure,
            stats=shelf_stats,
        )

        # Also add default taxonomy branches that have no entries yet
        self._merge_taxonomy(root, DEFAULT_TAXONOMY)

        return root

    async def suggest_shelf(
        self,
        content: str,
        keywords: list[str],
    ) -> list[str]:
        """Suggest a shelf path based on content and keywords.

        Uses keyword matching against the topic-shelf map to find
        the best matching shelf. Falls back to checking the existing
        shelf tree for partial matches.

        Args:
            content: The document content.
            keywords: Extracted keywords from the content.

        Returns:
            A list of shelf path segments (e.g., ["Engineering", "Backend", "Python"]).
        """
        combined = f"{content} {' '.join(keywords)}".lower()

        # Score each topic pattern
        best_path: list[str] = []
        best_score = 0

        for patterns, shelf_path in _TOPIC_SHELF_MAP:
            score = sum(1 for p in patterns if p in combined)
            if score > best_score:
                best_score = score
                best_path = shelf_path

        if best_score > 0:
            logger.debug(
                "Suggested shelf %s (score=%d)",
                " / ".join(best_path),
                best_score,
            )
            return best_path

        # Fallback: check existing shelf tree for keyword matches
        tree = await self.get_tree()
        for keyword in keywords:
            kw_lower = keyword.lower()
            match = self._find_shelf_by_name(tree, kw_lower)
            if match:
                return match

        # Last resort: return empty (uncategorized)
        logger.debug("No shelf suggestion found for content")
        return []

    async def create_shelf(self, path: list[str]) -> bool:
        """Create a new shelf.

        Since shelves are implicit (defined by entry paths), this method
        validates the path format but doesn't create any persistent
        structure. The shelf will appear in the tree once an entry is
        placed on it.

        Args:
            path: The shelf path segments to create.

        Returns:
            True if the path is valid (always True for valid paths).
        """
        if not path:
            return False

        # Validate: each segment must be non-empty and properly formatted
        for segment in path:
            if not segment or not segment.strip():
                logger.warning("Empty shelf segment in path: %s", path)
                return False
            if len(segment) > 50:
                logger.warning("Shelf segment too long: %s", segment)
                return False

        logger.info("Shelf path validated: %s", " / ".join(path))
        return True

    async def get_shelf_entries(
        self,
        path: list[str],
        limit: int = 50,
        offset: int = 0,
    ) -> list[LibraryEntry]:
        """Get entries belonging to a specific shelf.

        Args:
            path: The shelf path to query.
            limit: Maximum number of entries to return.
            offset: Number of entries to skip (pagination).

        Returns:
            A list of LibraryEntry objects on the specified shelf.
        """
        return await self._archive.get_by_shelf(path, limit=limit, offset=offset)

    async def get_shelf_info(self, path: list[str]) -> dict[str, Any]:
        """Get information about a specific shelf.

        Returns aggregate statistics about the shelf including entry
        count, average quality, collected tags/keywords, and the
        most recent update timestamp.

        Args:
            path: The shelf path to query.

        Returns:
            A dict with keys: path, entry_count, quality_avg, tags, last_updated.
        """
        entries = await self._archive.get_by_shelf(path, limit=1000)

        if not entries:
            return {
                "path": path,
                "entry_count": 0,
                "quality_avg": 0.0,
                "tags": [],
                "last_updated": None,
            }

        entry_count = len(entries)
        quality_avg = sum(e.quality_score for e in entries) / entry_count

        # Collect unique keywords as tags
        all_keywords: list[str] = []
        seen: set[str] = set()
        for entry in entries:
            for kw in entry.keywords:
                if kw.lower() not in seen:
                    all_keywords.append(kw)
                    seen.add(kw.lower())

        # Last updated
        last_updated = max(entries, key=lambda e: e.updated_at).updated_at

        return {
            "path": path,
            "entry_count": entry_count,
            "quality_avg": round(quality_avg, 4),
            "tags": all_keywords[:20],
            "last_updated": last_updated.isoformat() if last_updated else None,
        }

    async def move_entry(
        self,
        entry_id: str,
        new_shelf_path: list[str],
    ) -> bool:
        """Move an entry to a different shelf.

        Updates the entry's shelf_path and persists the change
        to the Archive.

        Args:
            entry_id: The ID of the entry to move.
            new_shelf_path: The new shelf path.

        Returns:
            True if the entry was moved successfully, False if not found.
        """
        entry = await self._archive.get(entry_id)
        if entry is None:
            logger.warning("move_entry: entry %s not found", entry_id)
            return False

        old_path = entry.shelf_path
        entry.shelf_path = new_shelf_path
        entry.touch()

        try:
            await self._archive.update(entry)
            logger.info(
                "Moved entry %s from %s to %s",
                entry_id,
                " / ".join(old_path) if old_path else "(none)",
                " / ".join(new_shelf_path),
            )
            return True
        except Exception as exc:
            logger.error("Failed to move entry %s: %s", entry_id, exc)
            return False

    async def merge_shelves(
        self,
        source_path: list[str],
        target_path: list[str],
    ) -> int:
        """Move all entries from source shelf to target shelf.

        All entries on the source shelf have their shelf_path updated
        to the target path. The source shelf becomes empty after the
        merge.

        Args:
            source_path: The shelf path to merge from.
            target_path: The shelf path to merge into.

        Returns:
            The number of entries moved.
        """
        entries = await self._archive.get_by_shelf(source_path, limit=10000)
        moved = 0

        for entry in entries:
            entry.shelf_path = target_path
            entry.touch()
            try:
                await self._archive.update(entry)
                moved += 1
            except Exception as exc:
                logger.error(
                    "Failed to move entry %s during merge: %s", entry.id, exc
                )

        logger.info(
            "Merged shelf %s → %s (%d entries moved)",
            " / ".join(source_path),
            " / ".join(target_path),
            moved,
        )
        return moved

    # ── Private helpers ───────────────────────────────────────────────────

    async def _get_shelf_stats_map(self) -> dict[str, dict[str, Any]]:
        """Build a map of shelf_path → {entry_count, quality_avg, last_updated}.

        Queries the archive for per-shelf statistics.

        Returns:
            A dict keyed by JSON-serialized shelf_path.
        """
        stats: dict[str, dict[str, Any]] = {}

        try:
            structure = await self._archive.get_shelf_structure()
            # The structure dict has _count at each level.
            # For more detailed stats, we need to query entries directly.
            # For simplicity, we iterate known shelf paths.
            all_entries = await self._archive.get_all(limit=100000)
        except Exception:
            return stats

        # Group entries by shelf path
        shelf_entries: dict[str, list[LibraryEntry]] = {}
        for entry in all_entries:
            key = json.dumps(entry.shelf_path, ensure_ascii=False)
            shelf_entries.setdefault(key, []).append(entry)

        for key, entries in shelf_entries.items():
            count = len(entries)
            quality_avg = sum(e.quality_score for e in entries) / count if count > 0 else 0.0
            last_updated = max(e.updated_at for e in entries) if entries else None

            stats[key] = {
                "entry_count": count,
                "quality_avg": round(quality_avg, 4),
                "last_updated": last_updated,
            }

        return stats

    def _build_tree_from_structure(
        self,
        node: ShelfNode,
        structure: dict[str, Any],
        stats: dict[str, dict[str, Any]],
    ) -> None:
        """Recursively build a ShelfNode tree from the archive structure dict.

        Args:
            node: The current tree node to populate.
            structure: The archive's shelf structure dict.
            stats: Per-shelf statistics map.
        """
        for name, sub in structure.items():
            if name == "_count":
                continue

            child_path = node.path + [name]
            path_key = json.dumps(child_path, ensure_ascii=False)
            path_stats = stats.get(path_key, {})

            child = ShelfNode(
                name=name,
                path=child_path,
                entry_count=path_stats.get("entry_count", sub.get("_count", 0)),
                quality_avg=path_stats.get("quality_avg", 0.0),
                last_updated=path_stats.get("last_updated"),
            )

            # Recurse into children
            self._build_tree_from_structure(child, sub, stats)

            node.children.append(child)

    @staticmethod
    def _merge_taxonomy(node: ShelfNode, taxonomy: dict[str, Any]) -> None:
        """Merge default taxonomy branches into the tree if not already present.

        Only adds branches that don't already exist in the tree, ensuring
        that user-created shelves are preserved and default suggestions
        are available for empty areas of the taxonomy.

        Args:
            node: The current tree node.
            taxonomy: The default taxonomy dict.
        """
        existing_names = {child.name for child in node.children}

        for name, sub_taxonomy in taxonomy.items():
            if name in existing_names:
                # Merge into existing child
                existing_child = next(
                    c for c in node.children if c.name == name
                )
                ShelfManager._merge_taxonomy(existing_child, sub_taxonomy)
            else:
                # Add new branch from taxonomy
                new_child = ShelfNode(
                    name=name,
                    path=node.path + [name],
                )
                ShelfManager._merge_taxonomy(new_child, sub_taxonomy)
                node.children.append(new_child)

    @staticmethod
    def _find_shelf_by_name(
        node: ShelfNode,
        name_lower: str,
    ) -> list[str] | None:
        """Find a shelf path whose name matches the given string.

        Performs a breadth-first search of the tree to find a node
        whose name (case-insensitive) matches the search term.

        Args:
            node: The tree root to search from.
            name_lower: The lowercase name to search for.

        Returns:
            The matching shelf path, or None if not found.
        """
        # Check current node's children
        for child in node.children:
            if child.name.lower() == name_lower:
                return child.path

        # Recurse into children
        for child in node.children:
            result = ShelfManager._find_shelf_by_name(child, name_lower)
            if result is not None:
                return result

        return None
