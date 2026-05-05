"""
VectorStore — Vector storage wrapper supporting ChromaDB, FAISS, or in-memory.

The VectorStore provides semantic search over LibraryEntry content using
vector embeddings. It tries backends in order of preference:

1. **ChromaDB** — persistent, feature-rich vector database
2. **FAISS** — Facebook's high-performance similarity search
3. **In-memory dict** — minimal fallback for environments without
   either library

Embeddings are produced by ``sentence-transformers`` when available. If the
model is not installed, a deterministic hash-based embedding is used as a
fallback (suitable for testing but not for production semantic search).

All CPU-bound operations (embedding, similarity search) are dispatched to
a thread pool via ``asyncio.to_thread()`` to keep the event loop responsive.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import struct
from pathlib import Path
from typing import Any

from kantorku.library.core.models import LibraryEntry

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────

_EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 output dimension


class VectorStore:
    """Vector storage with automatic backend selection.

    Tries ChromaDB → FAISS → in-memory dict. Embeddings are generated
    with sentence-transformers if available, otherwise a hash-based
    fallback is used.

    The store can optionally reference an :class:`Archive` instance to
    persist cached embeddings in SQLite's ``embeddings_cache`` table.

    Example::

        store = VectorStore("data/library/vectors", "all-MiniLM-L6-v2")
        await store.initialize()

        await store.add("entry-123", "Some text content", {"type": "knowledge"})
        results = await store.search("query text", top_k=5)
    """

    def __init__(
        self,
        persist_dir: str = "data/library/vectors",
        embedding_model: str = "all-MiniLM-L6-v2",
    ) -> None:
        self._persist_dir = persist_dir
        self._embedding_model = embedding_model
        self._backend: str = ""  # "chromadb" | "faiss" | "memory"
        self._archive: Any = None  # Optional[Archive] for cache

        # Backend-specific handles
        self._chroma_client: Any = None
        self._chroma_collection: Any = None
        self._faiss_index: Any = None  # faiss.IndexFlatIP
        self._faiss_ids: list[str] = []  # Parallel id list for FAISS
        self._faiss_metadata: dict[str, dict] = {}  # id → metadata

        # In-memory fallback
        self._memory_vectors: dict[str, list[float]] = {}
        self._memory_metadata: dict[str, dict] = {}

        # Sentence-transformers model (lazy-loaded)
        self._st_model: Any = None
        self._st_loaded: bool = False

    # ── Lifecycle ──────────────────────────────────────────────────────

    async def initialize(self) -> None:
        """Initialize the vector store, selecting the best available backend.

        Backends are tried in order: ChromaDB → FAISS → in-memory.
        The active backend name is stored in ``self._backend``.
        """
        Path(self._persist_dir).mkdir(parents=True, exist_ok=True)

        # Try ChromaDB first
        try:
            import chromadb  # noqa: F401

            await self._init_chromadb()
            self._backend = "chromadb"
            logger.info("VectorStore using ChromaDB backend")
            return
        except Exception as exc:
            logger.debug("ChromaDB not available: %s", exc)

        # Try FAISS
        try:
            import faiss  # noqa: F401

            await self._init_faiss()
            self._backend = "faiss"
            logger.info("VectorStore using FAISS backend")
            return
        except Exception as exc:
            logger.debug("FAISS not available: %s", exc)

        # In-memory fallback
        self._backend = "memory"
        logger.warning(
            "VectorStore using in-memory fallback — "
            "vectors will not persist across restarts"
        )

    def set_archive(self, archive: Any) -> None:
        """Set a reference to the Archive for embedding cache storage.

        Args:
            archive: An Archive instance with get_cached_embedding /
                     set_cached_embedding methods.
        """
        self._archive = archive

    async def close(self) -> None:
        """Persist data and release resources."""
        if self._backend == "chromadb" and self._chroma_client is not None:
            # ChromaDB PersistentClient auto-persists
            pass

        if self._backend == "faiss" and self._faiss_index is not None:
            await self._save_faiss()

        logger.debug("VectorStore closed (backend=%s)", self._backend)

    # ── Backend initializers ───────────────────────────────────────────

    async def _init_chromadb(self) -> None:
        """Initialize ChromaDB persistent client and collection."""
        import chromadb

        def _setup() -> None:
            self._chroma_client = chromadb.PersistentClient(path=self._persist_dir)
            self._chroma_collection = self._chroma_client.get_or_create_collection(
                name="library_entries",
                metadata={"hnsw:space": "cosine"},
            )

        await asyncio.to_thread(_setup)

    async def _init_faiss(self) -> None:
        """Initialize FAISS index, loading from disk if available."""
        import faiss
        import numpy as np

        def _setup() -> None:
            index_path = os.path.join(self._persist_dir, "faiss.index")
            ids_path = os.path.join(self._persist_dir, "faiss_ids.json")
            meta_path = os.path.join(self._persist_dir, "faiss_meta.json")

            if os.path.exists(index_path):
                self._faiss_index = faiss.read_index(index_path)
                import json

                with open(ids_path, "r") as f:
                    self._faiss_ids = json.load(f)
                with open(meta_path, "r") as f:
                    self._faiss_metadata = json.load(f)
                logger.info(
                    "Loaded FAISS index with %d vectors",
                    self._faiss_index.ntotal,
                )
            else:
                self._faiss_index = faiss.IndexFlatIP(_EMBEDDING_DIM)
                self._faiss_ids = []
                self._faiss_metadata = {}

        await asyncio.to_thread(_setup)

    async def _save_faiss(self) -> None:
        """Persist FAISS index and metadata to disk."""
        import json

        def _save() -> None:
            import faiss

            index_path = os.path.join(self._persist_dir, "faiss.index")
            ids_path = os.path.join(self._persist_dir, "faiss_ids.json")
            meta_path = os.path.join(self._persist_dir, "faiss_meta.json")

            faiss.write_index(self._faiss_index, index_path)
            with open(ids_path, "w") as f:
                json.dump(self._faiss_ids, f)
            with open(meta_path, "w") as f:
                json.dump(self._faiss_metadata, f)
            logger.debug("Saved FAISS index with %d vectors", self._faiss_index.ntotal)

        await asyncio.to_thread(_save)

    # ── Embedding ──────────────────────────────────────────────────────

    def _embed(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text.

        Tries sentence-transformers first; falls back to a deterministic
        hash-based embedding if the model is not available.

        Args:
            text: The text to embed.

        Returns:
            A list of floats representing the embedding vector.
        """
        # Lazy-load sentence-transformers
        if not self._st_loaded:
            try:
                from sentence_transformers import SentenceTransformer

                self._st_model = SentenceTransformer(self._embedding_model)
                logger.info("Loaded sentence-transformers model: %s", self._embedding_model)
            except Exception as exc:
                logger.warning(
                    "sentence-transformers not available (%s) — "
                    "using hash-based fallback embedding",
                    exc,
                )
                self._st_model = None
            self._st_loaded = True

        if self._st_model is not None:
            embedding = self._st_model.encode(text, normalize_embeddings=True)
            return embedding.tolist()

        # Hash-based fallback: deterministic but not semantically meaningful
        return self._hash_embed(text)

    @staticmethod
    def _hash_embed(text: str) -> list[float]:
        """Generate a deterministic hash-based embedding.

        Uses multiple hash rounds with different seeds to produce a
        fixed-length float vector. Useful as a fallback when no ML
        model is available.

        Args:
            text: The text to embed.

        Returns:
            A list of ``_EMBEDDING_DIM`` floats in the range [-1, 1].
        """
        vector = []
        for i in range(_EMBEDDING_DIM):
            seed = f"{text}||{i}".encode("utf-8")
            digest = hashlib.sha256(seed).digest()
            # Use first 4 bytes as a float
            value = struct.unpack("<f", digest[:4])[0]
            # Normalize to [-1, 1]
            normalized = (value % 2.0) - 1.0
            vector.append(normalized)

        # Normalize to unit length
        magnitude = sum(x * x for x in vector) ** 0.5
        if magnitude > 0:
            vector = [x / magnitude for x in vector]

        return vector

    # ── Public API ─────────────────────────────────────────────────────

    async def add(
        self,
        entry_id: str,
        content: str,
        metadata: dict | None = None,
    ) -> None:
        """Embed content and store the vector.

        Also caches the embedding in the Archive's embeddings_cache
        table if an Archive reference has been set.

        Args:
            entry_id: Unique identifier for the entry.
            content: The text content to embed and store.
            metadata: Optional metadata dict to associate with the vector.
        """
        meta = metadata or {}

        # Check cache first
        cached: list[float] | None = None
        if self._archive is not None:
            try:
                cached = await self._archive.get_cached_embedding(
                    entry_id, self._embedding_model
                )
            except Exception:
                cached = None

        if cached is not None:
            embedding = cached
            logger.debug("Using cached embedding for %s", entry_id)
        else:
            embedding = await asyncio.to_thread(self._embed, content)
            # Store in cache
            if self._archive is not None:
                try:
                    await self._archive.set_cached_embedding(
                        entry_id, self._embedding_model, embedding
                    )
                except Exception as exc:
                    logger.warning("Failed to cache embedding for %s: %s", entry_id, exc)

        # Store in the active backend
        if self._backend == "chromadb":
            await self._add_chromadb(entry_id, embedding, meta)
        elif self._backend == "faiss":
            await self._add_faiss(entry_id, embedding, meta)
        elif self._backend == "memory":
            self._memory_vectors[entry_id] = embedding
            self._memory_metadata[entry_id] = meta
        else:
            logger.error("No vector backend initialized")

    async def search(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.3,
    ) -> list[dict[str, Any]]:
        """Search for entries similar to the query text.

        Args:
            query: The search query text.
            top_k: Maximum number of results to return.
            min_similarity: Minimum cosine similarity threshold.

        Returns:
            A list of dicts with keys: ``entry_id``, ``similarity``, ``metadata``.
        """
        query_embedding = await asyncio.to_thread(self._embed, query)

        if self._backend == "chromadb":
            return await self._search_chromadb(query_embedding, top_k, min_similarity)
        elif self._backend == "faiss":
            return await self._search_faiss(query_embedding, top_k, min_similarity)
        elif self._backend == "memory":
            return self._search_memory(query_embedding, top_k, min_similarity)
        else:
            logger.error("No vector backend initialized")
            return []

    async def remove(self, entry_id: str) -> None:
        """Remove a vector from the store.

        Args:
            entry_id: The id of the entry to remove.
        """
        if self._backend == "chromadb":
            await self._remove_chromadb(entry_id)
        elif self._backend == "faiss":
            await self._remove_faiss(entry_id)
        elif self._backend == "memory":
            self._memory_vectors.pop(entry_id, None)
            self._memory_metadata.pop(entry_id, None)
        else:
            logger.error("No vector backend initialized")

    async def get_embedding(self, entry_id: str) -> list[float] | None:
        """Retrieve the cached embedding for an entry.

        Checks the Archive cache first, then falls back to the active
        vector backend's stored data.

        Args:
            entry_id: The id of the entry.

        Returns:
            The embedding as a list of floats, or ``None`` if not found.
        """
        # Try Archive cache first
        if self._archive is not None:
            try:
                cached = await self._archive.get_cached_embedding(
                    entry_id, self._embedding_model
                )
                if cached is not None:
                    return cached
            except Exception:
                pass

        # Fall back to in-memory store
        if self._backend == "memory":
            return self._memory_vectors.get(entry_id)

        # For ChromaDB and FAISS, the cache above should have it
        # but as a last resort try to retrieve from the backend
        if self._backend == "chromadb" and self._chroma_collection is not None:
            try:
                result = await asyncio.to_thread(
                    self._chroma_collection.get,
                    ids=[entry_id],
                    include=["embeddings"],
                )
                if result["embeddings"] and len(result["embeddings"]) > 0:
                    return result["embeddings"][0].tolist()
            except Exception:
                pass

        return None

    # ── ChromaDB backend methods ───────────────────────────────────────

    async def _add_chromadb(
        self, entry_id: str, embedding: list[float], metadata: dict
    ) -> None:
        """Add or update a vector in ChromaDB."""
        def _add() -> None:
            self._chroma_collection.upsert(
                ids=[entry_id],
                embeddings=[embedding],
                metadatas=[metadata],
            )

        await asyncio.to_thread(_add)

    async def _search_chromadb(
        self,
        query_embedding: list[float],
        top_k: int,
        min_similarity: float,
    ) -> list[dict[str, Any]]:
        """Search ChromaDB for similar vectors."""
        def _query() -> list[dict[str, Any]]:
            results = self._chroma_collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["metadatas", "distances"],
            )

            entries: list[dict[str, Any]] = []
            ids = results["ids"][0] if results["ids"] else []
            distances = results["distances"][0] if results["distances"] else []
            metadatas = results["metadatas"][0] if results["metadatas"] else []

            for eid, dist, meta in zip(ids, distances, metadatas):
                # ChromaDB cosine distance: 0 = identical, 2 = opposite
                # Convert to similarity: similarity = 1 - distance/2
                similarity = max(0.0, 1.0 - dist / 2.0)
                if similarity >= min_similarity:
                    entries.append({
                        "entry_id": eid,
                        "similarity": round(similarity, 4),
                        "metadata": meta or {},
                    })

            return entries

        return await asyncio.to_thread(_query)

    async def _remove_chromadb(self, entry_id: str) -> None:
        """Remove a vector from ChromaDB."""
        def _remove() -> None:
            self._chroma_collection.delete(ids=[entry_id])

        await asyncio.to_thread(_remove)

    # ── FAISS backend methods ──────────────────────────────────────────

    async def _add_faiss(
        self, entry_id: str, embedding: list[float], metadata: dict
    ) -> None:
        """Add or update a vector in the FAISS index."""
        import numpy as np

        def _add() -> None:
            # If entry already exists, remove it first
            if entry_id in self._faiss_ids:
                self._faiss_remove_internal(entry_id)

            vec = np.array([embedding], dtype=np.float32)
            self._faiss_index.add(vec)
            self._faiss_ids.append(entry_id)
            self._faiss_metadata[entry_id] = metadata

        await asyncio.to_thread(_add)
        # Auto-save after modifications
        await self._save_faiss()

    def _faiss_remove_internal(self, entry_id: str) -> None:
        """Internal synchronous removal from FAISS index.

        FAISS does not support direct removal from IndexFlatIP, so we
        rebuild the index without the target entry.
        """
        import faiss
        import numpy as np

        if entry_id not in self._faiss_ids:
            return

        idx = self._faiss_ids.index(entry_id)
        # Reconstruct all vectors except the one to remove
        new_vectors = []
        new_ids = []
        for i, eid in enumerate(self._faiss_ids):
            if eid == entry_id:
                continue
            vec = self._faiss_index.reconstruct(i)
            new_vectors.append(vec)
            new_ids.append(eid)

        # Rebuild index
        self._faiss_index = faiss.IndexFlatIP(_EMBEDDING_DIM)
        if new_vectors:
            self._faiss_index.add(np.array(new_vectors, dtype=np.float32))
        self._faiss_ids = new_ids
        self._faiss_metadata.pop(entry_id, None)

    async def _remove_faiss(self, entry_id: str) -> None:
        """Remove a vector from the FAISS index."""
        def _remove() -> None:
            self._faiss_remove_internal(entry_id)

        await asyncio.to_thread(_remove)
        await self._save_faiss()

    async def _search_faiss(
        self,
        query_embedding: list[float],
        top_k: int,
        min_similarity: float,
    ) -> list[dict[str, Any]]:
        """Search the FAISS index for similar vectors."""
        import numpy as np

        def _query() -> list[dict[str, Any]]:
            if self._faiss_index.ntotal == 0:
                return []

            k = min(top_k, self._faiss_index.ntotal)
            vec = np.array([query_embedding], dtype=np.float32)
            distances, indices = self._faiss_index.search(vec, k)

            entries: list[dict[str, Any]] = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx < 0 or idx >= len(self._faiss_ids):
                    continue
                # IndexFlatIP uses inner product; with normalized vectors
                # this equals cosine similarity
                similarity = float(dist)
                if similarity >= min_similarity:
                    eid = self._faiss_ids[idx]
                    meta = self._faiss_metadata.get(eid, {})
                    entries.append({
                        "entry_id": eid,
                        "similarity": round(similarity, 4),
                        "metadata": meta,
                    })

            return entries

        return await asyncio.to_thread(_query)

    # ── In-memory backend methods ──────────────────────────────────────

    def _search_memory(
        self,
        query_embedding: list[float],
        top_k: int,
        min_similarity: float,
    ) -> list[dict[str, Any]]:
        """Search the in-memory vector store using cosine similarity.

        This is a simple brute-force search — suitable for small datasets
        or testing but not for production at scale.
        """
        import math

        def _cosine_sim(a: list[float], b: list[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            mag_a = sum(x * x for x in a) ** 0.5
            mag_b = sum(x * x for x in b) ** 0.5
            if mag_a == 0 or mag_b == 0:
                return 0.0
            return dot / (mag_a * mag_b)

        scored: list[tuple[float, str]] = []
        for eid, vec in self._memory_vectors.items():
            sim = _cosine_sim(query_embedding, vec)
            if sim >= min_similarity:
                scored.append((sim, eid))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:top_k]

        return [
            {
                "entry_id": eid,
                "similarity": round(sim, 4),
                "metadata": self._memory_metadata.get(eid, {}),
            }
            for sim, eid in top
        ]
