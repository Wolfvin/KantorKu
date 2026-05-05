"""
Indexer — Vector embedding and search for KantorKu Library.

The Indexer is responsible for creating vector embeddings for Library entries,
maintaining the search index, and performing combined vector + archive searches
with filtering. It coordinates between the VectorStore (semantic search),
Archive (persistent storage), and HotIndex (fast analytical queries).

The Indexer handles:
- Embedding individual entries and upserting into the search index
- Bulk re-indexing of entries that lack embeddings
- Combined search with quality and type filters
- Removal of entries from all search backends

Example::

    from kantorku.library.storage.archive import Archive
    from kantorku.library.storage.vectors import VectorStore
    from kantorku.library.storage.hot_index import HotIndex

    archive = Archive("data/library/archive.db")
    vector_store = VectorStore("data/library/vectors")
    hot_index = HotIndex("data/library/hot_index.duckdb")
    await archive.initialize()
    await vector_store.initialize()
    await hot_index.initialize()

    indexer = Indexer(archive=archive, vector_store=vector_store, hot_index=hot_index)
    await indexer.index_entry(my_entry)
    results = await indexer.search("Python async patterns", top_k=5)
"""

from __future__ import annotations

import logging
from typing import Any

from kantorku.library.core.models import EntryType, LibraryEntry
from kantorku.library.storage.archive import Archive
from kantorku.library.storage.hot_index import HotIndex
from kantorku.library.storage.vectors import VectorStore

logger = logging.getLogger(__name__)


class Indexer:
    """Vector embedding and search for KantorKu Library.

    The Indexer coordinates between three storage backends:
    - **VectorStore**: Semantic search via vector similarity
    - **Archive**: Persistent storage and full-text search
    - **HotIndex**: Fast analytical queries on entry metadata

    It provides a unified search interface that combines vector similarity
    with quality and type filters, and manages the indexing lifecycle.

    Args:
        archive: The Archive instance for persistent storage.
        vector_store: The VectorStore instance for semantic search.
        hot_index: The HotIndex instance for fast metadata queries.
    """

    def __init__(
        self,
        archive: Archive,
        vector_store: VectorStore,
        hot_index: HotIndex,
    ) -> None:
        self._archive = archive
        self._vector_store = vector_store
        self._hot_index = hot_index

    # ── Indexing ─────────────────────────────────────────────────────────

    async def index_entry(self, entry: LibraryEntry) -> None:
        """Embed entry content and add to vector store and hot index.

        Performs the following steps:
        1. Generate a vector embedding for the entry content.
        2. Add (or update) the embedding in the VectorStore.
        3. Upsert the entry metadata into the HotIndex.

        Errors during embedding or indexing are logged but not raised,
        ensuring that a single entry failure doesn't block the pipeline.

        Args:
            entry: The LibraryEntry to index.
        """
        # 1. Embed and add to vector store
        try:
            metadata = {
                "entry_type": entry.entry_type.value,
                "domain": entry.domain,
                "shelf_path": " / ".join(entry.shelf_path) if entry.shelf_path else "",
                "quality_score": entry.quality_score,
            }

            # Build a rich embedding text from title + content + keywords
            embed_text = self._build_embed_text(entry)
            await self._vector_store.add(entry.id, embed_text, metadata)
            logger.debug("Indexed entry %s in vector store", entry.id)
        except Exception as exc:
            logger.warning(
                "Failed to index entry %s in vector store: %s", entry.id, exc
            )

        # 2. Upsert into hot index
        try:
            await self._hot_index.upsert(entry)
            logger.debug("Upserted entry %s in hot index", entry.id)
        except Exception as exc:
            logger.warning(
                "Failed to upsert entry %s in hot index: %s", entry.id, exc
            )

    async def index_all(self, force: bool = False) -> int:
        """Re-index all entries that don't have embeddings yet.

        Iterates through all entries in the Archive and indexes any that
        are missing from the VectorStore. If ``force`` is True, all
        entries are re-indexed regardless of their current state.

        This is a potentially slow operation for large archives — it
        generates embeddings for every unindexed entry.

        Args:
            force: If True, re-index all entries even if already indexed.

        Returns:
            The number of entries indexed.
        """
        logger.info("Starting index_all (force=%s)", force)

        # Get all entries from archive
        entries = await self._archive.get_all(limit=100000)
        indexed = 0

        for entry in entries:
            if not force:
                # Check if the entry already has an embedding
                existing = await self._vector_store.get_embedding(entry.id)
                if existing is not None:
                    continue

            try:
                await self.index_entry(entry)
                indexed += 1
            except Exception as exc:
                logger.error(
                    "Failed to index entry %s during index_all: %s",
                    entry.id,
                    exc,
                )

        logger.info(
            "index_all complete: %d/%d entries indexed",
            indexed,
            len(entries),
        )
        return indexed

    # ── Search ───────────────────────────────────────────────────────────

    async def search(
        self,
        query: str,
        top_k: int = 5,
        entry_type: str | None = None,
        min_quality: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Combined vector + archive search with filters.

        Performs a two-phase search:
        1. **Vector search**: Find entries by semantic similarity to the query.
        2. **Filter and enrich**: Apply type and quality filters, then
           retrieve full entry data from the Archive.

        Results are ranked by a combined score of vector similarity and
        quality score.

        Args:
            query: The search query text.
            top_k: Maximum number of results to return.
            entry_type: If provided, filter to this entry type
                (e.g., "knowledge", "solution", "qa_pair", "procedure").
            min_quality: Minimum quality score threshold (0.0-1.0).

        Returns:
            A list of dicts with keys: entry_id, title, similarity,
            quality_score, entry_type, shelf_path, summary.
        """
        # Phase 1: Vector search
        try:
            vector_results = await self._vector_store.search(
                query=query,
                top_k=top_k * 3,  # Over-fetch to allow for filtering
                min_similarity=0.1,
            )
        except Exception as exc:
            logger.error("Vector search failed: %s", exc)
            vector_results = []

        # Phase 2: Filter and enrich
        results: list[dict[str, Any]] = []

        for vr in vector_results:
            entry_id = vr.get("entry_id", "")
            similarity = vr.get("similarity", 0.0)

            # Retrieve full entry
            entry = await self._archive.get(entry_id)
            if entry is None:
                continue

            # Apply filters
            if entry_type is not None and entry.entry_type.value != entry_type:
                continue

            if entry.quality_score < min_quality:
                continue

            results.append({
                "entry_id": entry.id,
                "title": entry.title or "(untitled)",
                "similarity": similarity,
                "quality_score": entry.quality_score,
                "entry_type": entry.entry_type.value,
                "shelf_path": entry.shelf_path,
                "shelf_str": entry.shelf_str,
                "summary": entry.summary,
                "domain": entry.domain,
            })

        # Sort by combined score: 0.6 * similarity + 0.4 * quality
        results.sort(
            key=lambda r: 0.6 * r["similarity"] + 0.4 * r["quality_score"],
            reverse=True,
        )

        return results[:top_k]

    # ── Removal ──────────────────────────────────────────────────────────

    async def remove_entry(self, entry_id: str) -> None:
        """Remove an entry from the vector store and hot index.

        Does NOT remove the entry from the Archive — that should be
        done separately via ``Archive.delete()``. This method only
        cleans up the search indices.

        Args:
            entry_id: The ID of the entry to remove from indices.
        """
        # Remove from vector store
        try:
            await self._vector_store.remove(entry_id)
            logger.debug("Removed entry %s from vector store", entry_id)
        except Exception as exc:
            logger.warning(
                "Failed to remove entry %s from vector store: %s",
                entry_id,
                exc,
            )

        # Remove from hot index
        try:
            await self._hot_index.remove(entry_id)
            logger.debug("Removed entry %s from hot index", entry_id)
        except Exception as exc:
            logger.warning(
                "Failed to remove entry %s from hot index: %s",
                entry_id,
                exc,
            )

    # ── Private helpers ───────────────────────────────────────────────────

    @staticmethod
    def _build_embed_text(entry: LibraryEntry) -> str:
        """Build a rich text representation for embedding.

        Combines the entry's title, keywords, and content into a single
        string that produces better embeddings than raw content alone.

        Args:
            entry: The LibraryEntry to build embedding text for.

        Returns:
            A combined text string optimized for embedding.
        """
        parts: list[str] = []

        if entry.title:
            parts.append(f"Title: {entry.title}")

        if entry.keywords:
            parts.append(f"Keywords: {', '.join(entry.keywords)}")

        if entry.summary:
            parts.append(f"Summary: {entry.summary}")

        # Add entry type hint
        type_hints: dict[EntryType, str] = {
            EntryType.KNOWLEDGE: "This is factual knowledge.",
            EntryType.SOLUTION: "This is a problem-solution entry.",
            EntryType.QA_PAIR: "This is a question-answer pair.",
            EntryType.PROCEDURE: "This is a step-by-step procedure.",
        }
        hint = type_hints.get(entry.entry_type, "")
        if hint:
            parts.append(hint)

        # Add content (truncated if too long for embedding)
        content = entry.content
        max_content = 2000
        if len(content) > max_content:
            content = content[:max_content]
        parts.append(content)

        return "\n\n".join(parts)
