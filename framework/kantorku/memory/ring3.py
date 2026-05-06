"""
Ring3 — GraphRAG cold memory.

Knowledge-graph-backed long-term memory that provides:
- Semantic search across all historical sessions
- Knowledge graph of project entities, concepts, and patterns
- Structured lessons learned (symptom → root cause → fix)
- Cross-session learning and recommendations

Storage: SQLite via aiosqlite (same as Ring2), with FTS5 for text search
and BLOB-stored embeddings for vector similarity.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import struct
import uuid
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    import aiosqlite
except ImportError:
    aiosqlite = None  # type: ignore

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────

_EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 output dimension

_VALID_NODE_TYPES = frozenset({
    "entity", "concept", "lesson", "pattern", "procedure",
})

_VALID_RELATIONS = frozenset({
    "depends_on", "related_to", "derived_from",
    "supersedes", "contradicts", "extends", "example_of",
})


# ── Dataclasses ────────────────────────────────────────────────────────────

@dataclass
class KnowledgeNode:
    """A node in the knowledge graph.

    Represents an entity, concept, lesson, pattern, or procedure
    extracted from session content.
    """

    node_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    node_type: str = "concept"
    name: str = ""
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: Optional[list[float]] = None

    def __post_init__(self) -> None:
        if self.node_type not in _VALID_NODE_TYPES:
            logger.warning(
                "Unknown node_type %r — defaulting to 'concept'", self.node_type
            )
            self.node_type = "concept"
        # Ensure metadata has expected keys
        self.metadata.setdefault("source_session", "")
        self.metadata.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        self.metadata.setdefault("access_count", 0)
        self.metadata.setdefault("quality_score", 0.5)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary for storage / JSON export."""
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "name": self.name,
            "content": self.content,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KnowledgeNode:
        """Deserialize from a dictionary (e.g., from SQLite row)."""
        metadata = data.get("metadata", {})
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        return cls(
            node_id=data.get("node_id", str(uuid.uuid4())),
            node_type=data.get("node_type", "concept"),
            name=data.get("name", ""),
            content=data.get("content", ""),
            metadata=metadata,
            embedding=data.get("embedding"),
        )


@dataclass
class KnowledgeEdge:
    """A directed edge in the knowledge graph.

    Represents a relationship between two knowledge nodes.
    """

    edge_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str = ""
    target_id: str = ""
    relation: str = "related_to"
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.relation not in _VALID_RELATIONS:
            logger.warning(
                "Unknown relation %r — defaulting to 'related_to'", self.relation
            )
            self.relation = "related_to"
        self.weight = max(0.0, min(self.weight, 1.0))

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary for storage / JSON export."""
        return {
            "edge_id": self.edge_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation": self.relation,
            "weight": self.weight,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KnowledgeEdge:
        """Deserialize from a dictionary."""
        metadata = data.get("metadata", {})
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        return cls(
            edge_id=data.get("edge_id", str(uuid.uuid4())),
            source_id=data.get("source_id", ""),
            target_id=data.get("target_id", ""),
            relation=data.get("relation", "related_to"),
            weight=data.get("weight", 1.0),
            metadata=metadata,
        )


@dataclass
class Lesson:
    """A structured lesson learned from a past incident.

    Captures the full diagnostic arc: what went wrong, why, what was
    done to fix it, how the fix was verified, and a generalized rule.
    """

    lesson_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symptom: str = ""
    root_cause: str = ""
    fix_applied: str = ""
    verification: str = ""
    reusable_rule: str = ""
    context: str = ""
    confidence: float = 0.5
    source_session: str = ""
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary for storage / JSON export."""
        return {
            "lesson_id": self.lesson_id,
            "symptom": self.symptom,
            "root_cause": self.root_cause,
            "fix_applied": self.fix_applied,
            "verification": self.verification,
            "reusable_rule": self.reusable_rule,
            "context": self.context,
            "confidence": self.confidence,
            "source_session": self.source_session,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Lesson:
        """Deserialize from a dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now(timezone.utc)
        return cls(
            lesson_id=data.get("lesson_id", str(uuid.uuid4())),
            symptom=data.get("symptom", ""),
            root_cause=data.get("root_cause", ""),
            fix_applied=data.get("fix_applied", ""),
            verification=data.get("verification", ""),
            reusable_rule=data.get("reusable_rule", ""),
            context=data.get("context", ""),
            confidence=data.get("confidence", 0.5),
            source_session=data.get("source_session", ""),
            created_at=created_at,
        )


# ── Ring3Store — SQLite-backed storage ────────────────────────────────────

class Ring3Store:
    """Low-level SQLite storage for knowledge nodes, edges, and lessons.

    Uses aiosqlite for non-blocking I/O, FTS5 for full-text search,
    and BLOB columns for embedding vectors.
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._db: Any = None

    async def initialize(self) -> None:
        """Create the database directory, open the connection, and create tables."""
        if aiosqlite is None:
            raise ImportError(
                "Ring3 requires 'aiosqlite' package. pip install aiosqlite"
            )

        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self._db_path)
        self._db.row_factory = aiosqlite.Row

        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA foreign_keys=ON")

        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS knowledge_nodes (
                node_id     TEXT PRIMARY KEY,
                node_type   TEXT    NOT NULL DEFAULT 'concept',
                name        TEXT    NOT NULL DEFAULT '',
                content     TEXT    NOT NULL DEFAULT '',
                metadata    TEXT    NOT NULL DEFAULT '{}',
                embedding   BLOB,
                created_at  TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS knowledge_edges (
                edge_id     TEXT PRIMARY KEY,
                source_id   TEXT    NOT NULL,
                target_id   TEXT    NOT NULL,
                relation    TEXT    NOT NULL DEFAULT 'related_to',
                weight      REAL    NOT NULL DEFAULT 1.0,
                metadata    TEXT    NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS lessons (
                lesson_id       TEXT PRIMARY KEY,
                symptom         TEXT    NOT NULL DEFAULT '',
                root_cause      TEXT    NOT NULL DEFAULT '',
                fix_applied     TEXT    NOT NULL DEFAULT '',
                verification    TEXT    NOT NULL DEFAULT '',
                reusable_rule   TEXT    NOT NULL DEFAULT '',
                context         TEXT    NOT NULL DEFAULT '',
                confidence      REAL    NOT NULL DEFAULT 0.5,
                source_session  TEXT    NOT NULL DEFAULT '',
                created_at      TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS lesson_embeddings (
                lesson_id   TEXT PRIMARY KEY,
                embedding   BLOB    NOT NULL,
                model_name  TEXT    NOT NULL DEFAULT 'all-MiniLM-L6-v2'
            );

            CREATE INDEX IF NOT EXISTS idx_nodes_type
                ON knowledge_nodes(node_type);
            CREATE INDEX IF NOT EXISTS idx_nodes_name
                ON knowledge_nodes(name);
            CREATE INDEX IF NOT EXISTS idx_edges_source
                ON knowledge_edges(source_id);
            CREATE INDEX IF NOT EXISTS idx_edges_target
                ON knowledge_edges(target_id);
            CREATE INDEX IF NOT EXISTS idx_edges_relation
                ON knowledge_edges(relation);
            CREATE INDEX IF NOT EXISTS idx_lessons_session
                ON lessons(source_session);
        """)

        # Standalone FTS5 virtual table for knowledge nodes.
        # Using content-less sync (no content=) to avoid rowid mismatch issues
        # with INSERT OR REPLACE on TEXT PRIMARY KEY tables.
        try:
            await self._db.executescript("""
                CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_nodes_fts USING fts5(
                    node_id,
                    name,
                    content
                );
            """)
        except Exception as exc:
            logger.warning("FTS5 setup for knowledge_nodes skipped: %s", exc)

        # Standalone FTS5 for lessons
        try:
            await self._db.executescript("""
                CREATE VIRTUAL TABLE IF NOT EXISTS lessons_fts USING fts5(
                    lesson_id,
                    symptom,
                    root_cause,
                    context,
                    reusable_rule
                );
            """)
        except Exception as exc:
            logger.warning("FTS5 setup for lessons skipped: %s", exc)

        await self._db.commit()
        logger.info("Ring3Store initialized at %s", self._db_path)

    # ── Node operations ────────────────────────────────────────────────

    async def store_node(self, node: KnowledgeNode) -> str:
        """Insert or replace a knowledge node. Returns the node_id.

        Also maintains the standalone FTS5 index for text search.
        """
        db = self._db
        metadata_json = json.dumps(node.metadata, ensure_ascii=False)
        embedding_blob: Optional[bytes] = None
        if node.embedding is not None:
            embedding_blob = json.dumps(node.embedding).encode("utf-8")
        created_at = node.metadata.get(
            "created_at", datetime.now(timezone.utc).isoformat()
        )

        await db.execute(
            """INSERT OR REPLACE INTO knowledge_nodes
               (node_id, node_type, name, content, metadata, embedding, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (node.node_id, node.node_type, node.name, node.content,
             metadata_json, embedding_blob, created_at),
        )

        # Maintain standalone FTS5 index: delete old entry, insert new
        try:
            await db.execute(
                "DELETE FROM knowledge_nodes_fts WHERE node_id = ?",
                (node.node_id,),
            )
            await db.execute(
                "INSERT INTO knowledge_nodes_fts(node_id, name, content) VALUES (?, ?, ?)",
                (node.node_id, node.name, node.content),
            )
        except Exception as exc:
            logger.debug("FTS5 index update for node %s skipped: %s", node.node_id, exc)

        await db.commit()
        return node.node_id

    async def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        """Fetch a knowledge node by ID."""
        cursor = await self._db.execute(
            "SELECT node_id, node_type, name, content, metadata, embedding FROM knowledge_nodes WHERE node_id = ?",
            (node_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return self._row_to_node(row)

    async def search_nodes(
        self,
        query: str,
        top_k: int = 10,
        node_type: Optional[str] = None,
    ) -> list[KnowledgeNode]:
        """Search knowledge nodes using FTS5 + optional node_type filter."""
        if not query.strip():
            return await self._list_nodes(top_k, node_type)

        params: list[Any] = [query]
        type_filter = ""
        if node_type is not None:
            type_filter = " AND n.node_type = ?"
            params.append(node_type)

        sql = f"""
            SELECT n.node_id, n.node_type, n.name, n.content, n.metadata, n.embedding
            FROM knowledge_nodes_fts fts
            INNER JOIN knowledge_nodes n ON n.node_id = fts.node_id
            WHERE knowledge_nodes_fts MATCH ?
            {type_filter}
            LIMIT ?
        """
        params.append(top_k)

        try:
            cursor = await self._db.execute(sql, params)
            rows = await cursor.fetchall()
            return [self._row_to_node(row) for row in rows]
        except Exception as exc:
            logger.warning("FTS5 search failed, falling back to LIKE: %s", exc)
            return await self._search_nodes_like(query, top_k, node_type)

    async def _search_nodes_like(
        self,
        query: str,
        top_k: int,
        node_type: Optional[str] = None,
    ) -> list[KnowledgeNode]:
        """Fallback text search using LIKE when FTS5 is unavailable."""
        like_pattern = f"%{query}%"
        conditions = "(n.name LIKE ? OR n.content LIKE ?)"
        params: list[Any] = [like_pattern, like_pattern]

        if node_type is not None:
            conditions += " AND n.node_type = ?"
            params.append(node_type)

        sql = f"""
            SELECT n.node_id, n.node_type, n.name, n.content, n.metadata, n.embedding
            FROM knowledge_nodes n
            WHERE {conditions}
            LIMIT ?
        """
        params.append(top_k)

        cursor = await self._db.execute(sql, params)
        rows = await cursor.fetchall()
        return [self._row_to_node(row) for row in rows]

    async def _list_nodes(
        self,
        limit: int,
        node_type: Optional[str] = None,
    ) -> list[KnowledgeNode]:
        """List nodes when no query is provided."""
        if node_type is not None:
            cursor = await self._db.execute(
                "SELECT node_id, node_type, name, content, metadata, embedding FROM knowledge_nodes WHERE node_type = ? LIMIT ?",
                (node_type, limit),
            )
        else:
            cursor = await self._db.execute(
                "SELECT node_id, node_type, name, content, metadata, embedding FROM knowledge_nodes LIMIT ?",
                (limit,),
            )
        rows = await cursor.fetchall()
        return [self._row_to_node(row) for row in rows]

    async def search_nodes_by_embedding(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        node_type: Optional[str] = None,
        min_similarity: float = 0.3,
    ) -> list[tuple[KnowledgeNode, float]]:
        """Search knowledge nodes by embedding similarity.

        Returns list of (node, similarity) tuples sorted by similarity descending.
        """
        type_filter = ""
        params: list[Any] = []
        if node_type is not None:
            type_filter = "WHERE node_type = ?"
            params.append(node_type)

        sql = f"SELECT node_id, node_type, name, content, metadata, embedding FROM knowledge_nodes {type_filter}"
        cursor = await self._db.execute(sql, params)
        rows = await cursor.fetchall()

        scored: list[tuple[KnowledgeNode, float]] = []
        for row in rows:
            node = self._row_to_node(row)
            if node.embedding is None:
                continue
            sim = _cosine_similarity(query_embedding, node.embedding)
            if sim >= min_similarity:
                scored.append((node, sim))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    async def delete_node(self, node_id: str) -> bool:
        """Delete a node, cascade-delete its edges, and clean FTS5 index."""
        # Delete edges first
        await self._db.execute(
            "DELETE FROM knowledge_edges WHERE source_id = ? OR target_id = ?",
            (node_id, node_id),
        )
        cursor = await self._db.execute(
            "DELETE FROM knowledge_nodes WHERE node_id = ?",
            (node_id,),
        )
        # Clean FTS5 index
        try:
            await self._db.execute(
                "DELETE FROM knowledge_nodes_fts WHERE node_id = ?",
                (node_id,),
            )
        except Exception:
            pass
        await self._db.commit()
        return cursor.rowcount > 0

    # ── Edge operations ────────────────────────────────────────────────

    async def store_edge(self, edge: KnowledgeEdge) -> str:
        """Insert a knowledge edge. Returns the edge_id."""
        metadata_json = json.dumps(edge.metadata, ensure_ascii=False)
        await self._db.execute(
            """INSERT OR REPLACE INTO knowledge_edges
               (edge_id, source_id, target_id, relation, weight, metadata)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (edge.edge_id, edge.source_id, edge.target_id,
             edge.relation, edge.weight, metadata_json),
        )
        await self._db.commit()
        return edge.edge_id

    async def get_edges(
        self,
        node_id: str,
        direction: str = "both",
    ) -> list[KnowledgeEdge]:
        """Get edges connected to a node.

        Args:
            node_id: The node to query.
            direction: "outgoing", "incoming", or "both".
        """
        if direction == "outgoing":
            cursor = await self._db.execute(
                "SELECT edge_id, source_id, target_id, relation, weight, metadata FROM knowledge_edges WHERE source_id = ?",
                (node_id,),
            )
        elif direction == "incoming":
            cursor = await self._db.execute(
                "SELECT edge_id, source_id, target_id, relation, weight, metadata FROM knowledge_edges WHERE target_id = ?",
                (node_id,),
            )
        else:
            cursor = await self._db.execute(
                "SELECT edge_id, source_id, target_id, relation, weight, metadata FROM knowledge_edges WHERE source_id = ? OR target_id = ?",
                (node_id, node_id),
            )
        rows = await cursor.fetchall()
        return [self._row_to_edge(row) for row in rows]

    async def get_neighbors(
        self,
        node_id: str,
        max_depth: int = 2,
    ) -> list[KnowledgeNode]:
        """BFS graph traversal from a node, returning all reachable neighbors."""
        visited: set[str] = {node_id}
        result_nodes: list[KnowledgeNode] = []
        queue: deque[tuple[str, int]] = deque([(node_id, 0)])

        while queue:
            current_id, depth = queue.popleft()
            if depth >= max_depth:
                continue

            edges = await self.get_edges(current_id, direction="both")
            neighbor_ids: set[str] = set()
            for edge in edges:
                if edge.source_id == current_id:
                    neighbor_ids.add(edge.target_id)
                else:
                    neighbor_ids.add(edge.source_id)

            for nid in neighbor_ids:
                if nid in visited:
                    continue
                visited.add(nid)
                node = await self.get_node(nid)
                if node is not None:
                    result_nodes.append(node)
                    queue.append((nid, depth + 1))

        return result_nodes

    async def get_path(
        self,
        source_id: str,
        target_id: str,
    ) -> list[str]:
        """Shortest path via BFS between two nodes.

        Returns a list of node_id strings forming the path,
        or an empty list if no path exists.
        """
        if source_id == target_id:
            return [source_id]

        visited: set[str] = {source_id}
        parent: dict[str, Optional[str]] = {source_id: None}
        queue: deque[str] = deque([source_id])

        while queue:
            current = queue.popleft()
            edges = await self.get_edges(current, direction="both")
            neighbor_ids: set[str] = set()
            for edge in edges:
                if edge.source_id == current:
                    neighbor_ids.add(edge.target_id)
                else:
                    neighbor_ids.add(edge.source_id)

            for nid in neighbor_ids:
                if nid in visited:
                    continue
                visited.add(nid)
                parent[nid] = current
                if nid == target_id:
                    # Reconstruct path
                    path: list[str] = []
                    step: Optional[str] = target_id
                    while step is not None:
                        path.append(step)
                        step = parent[step]
                    path.reverse()
                    return path
                queue.append(nid)

        return []

    # ── Lesson operations ──────────────────────────────────────────────

    async def store_lesson(self, lesson: Lesson) -> str:
        """Insert or replace a lesson. Returns the lesson_id.

        Also maintains the standalone FTS5 index for text search.
        """
        await self._db.execute(
            """INSERT OR REPLACE INTO lessons
               (lesson_id, symptom, root_cause, fix_applied, verification,
                reusable_rule, context, confidence, source_session, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (lesson.lesson_id, lesson.symptom, lesson.root_cause,
             lesson.fix_applied, lesson.verification, lesson.reusable_rule,
             lesson.context, lesson.confidence, lesson.source_session,
             lesson.created_at.isoformat()),
        )

        # Maintain standalone FTS5 index
        try:
            await self._db.execute(
                "DELETE FROM lessons_fts WHERE lesson_id = ?",
                (lesson.lesson_id,),
            )
            await self._db.execute(
                """INSERT INTO lessons_fts(lesson_id, symptom, root_cause, context, reusable_rule)
                   VALUES (?, ?, ?, ?, ?)""",
                (lesson.lesson_id, lesson.symptom, lesson.root_cause,
                 lesson.context, lesson.reusable_rule),
            )
        except Exception as exc:
            logger.debug("FTS5 index update for lesson %s skipped: %s", lesson.lesson_id, exc)

        await self._db.commit()
        return lesson.lesson_id

    async def get_lesson(self, lesson_id: str) -> Optional[Lesson]:
        """Fetch a lesson by ID."""
        cursor = await self._db.execute(
            """SELECT lesson_id, symptom, root_cause, fix_applied, verification,
                      reusable_rule, context, confidence, source_session, created_at
               FROM lessons WHERE lesson_id = ?""",
            (lesson_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return self._row_to_lesson(row)

    async def search_lessons_fts(
        self,
        query: str,
        limit: int = 10,
    ) -> list[Lesson]:
        """Search lessons using FTS5."""
        if not query.strip():
            return []

        try:
            cursor = await self._db.execute(
                """SELECT l.lesson_id, l.symptom, l.root_cause, l.fix_applied,
                          l.verification, l.reusable_rule, l.context,
                          l.confidence, l.source_session, l.created_at
                   FROM lessons_fts fts
                   INNER JOIN lessons l ON l.lesson_id = fts.lesson_id
                   WHERE lessons_fts MATCH ?
                   LIMIT ?""",
                (query, limit),
            )
            rows = await cursor.fetchall()
            return [self._row_to_lesson(row) for row in rows]
        except Exception as exc:
            logger.warning("Lesson FTS5 search failed: %s", exc)
            return []

    async def store_lesson_embedding(
        self,
        lesson_id: str,
        embedding: list[float],
        model_name: str = "all-MiniLM-L6-v2",
    ) -> None:
        """Store a lesson's embedding vector as a BLOB."""
        blob = json.dumps(embedding).encode("utf-8")
        await self._db.execute(
            """INSERT OR REPLACE INTO lesson_embeddings (lesson_id, embedding, model_name)
               VALUES (?, ?, ?)""",
            (lesson_id, blob, model_name),
        )
        await self._db.commit()

    async def search_lessons_by_embedding(
        self,
        query_embedding: list[float],
        top_k: int = 3,
        min_similarity: float = 0.3,
    ) -> list[tuple[Lesson, float]]:
        """Search lessons by embedding similarity.

        Returns list of (lesson, similarity) tuples.
        """
        cursor = await self._db.execute(
            "SELECT lesson_id, embedding FROM lesson_embeddings"
        )
        rows = await cursor.fetchall()

        scored: list[tuple[str, float]] = []
        for row in rows:
            lid = row["lesson_id"]
            blob = row["embedding"]
            try:
                embedding = json.loads(blob.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            sim = _cosine_similarity(query_embedding, embedding)
            if sim >= min_similarity:
                scored.append((lid, sim))

        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:top_k]

        result: list[tuple[Lesson, float]] = []
        for lid, sim in top:
            lesson = await self.get_lesson(lid)
            if lesson is not None:
                result.append((lesson, sim))
        return result

    async def get_all_lesson_embeddings(
        self,
    ) -> list[tuple[str, list[float]]]:
        """Retrieve all lesson embeddings for batch similarity search."""
        cursor = await self._db.execute(
            "SELECT lesson_id, embedding FROM lesson_embeddings"
        )
        rows = await cursor.fetchall()
        result: list[tuple[str, list[float]]] = []
        for row in rows:
            try:
                embedding = json.loads(row["embedding"].decode("utf-8"))
                result.append((row["lesson_id"], embedding))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
        return result

    # ── Statistics ─────────────────────────────────────────────────────

    async def get_node_count_by_type(self) -> dict[str, int]:
        """Count nodes grouped by type."""
        cursor = await self._db.execute(
            "SELECT node_type, COUNT(*) as cnt FROM knowledge_nodes GROUP BY node_type"
        )
        rows = await cursor.fetchall()
        return {row["node_type"]: row["cnt"] for row in rows}

    async def get_edge_count_by_relation(self) -> dict[str, int]:
        """Count edges grouped by relation type."""
        cursor = await self._db.execute(
            "SELECT relation, COUNT(*) as cnt FROM knowledge_edges GROUP BY relation"
        )
        rows = await cursor.fetchall()
        return {row["relation"]: row["cnt"] for row in rows}

    async def get_lesson_count(self) -> int:
        """Count total lessons."""
        cursor = await self._db.execute("SELECT COUNT(*) FROM lessons")
        row = await cursor.fetchone()
        return row[0] if row else 0

    async def get_all_nodes(self) -> list[KnowledgeNode]:
        """Retrieve all knowledge nodes (for export)."""
        cursor = await self._db.execute(
            "SELECT node_id, node_type, name, content, metadata, embedding FROM knowledge_nodes"
        )
        rows = await cursor.fetchall()
        return [self._row_to_node(row) for row in rows]

    async def get_all_edges(self) -> list[KnowledgeEdge]:
        """Retrieve all knowledge edges (for export)."""
        cursor = await self._db.execute(
            "SELECT edge_id, source_id, target_id, relation, weight, metadata FROM knowledge_edges"
        )
        rows = await cursor.fetchall()
        return [self._row_to_edge(row) for row in rows]

    async def get_all_lessons(self) -> list[Lesson]:
        """Retrieve all lessons (for export)."""
        cursor = await self._db.execute(
            """SELECT lesson_id, symptom, root_cause, fix_applied, verification,
                      reusable_rule, context, confidence, source_session, created_at
               FROM lessons"""
        )
        rows = await cursor.fetchall()
        return [self._row_to_lesson(row) for row in rows]

    # ── Lifecycle ──────────────────────────────────────────────────────

    async def close(self) -> None:
        """Close the database connection."""
        if self._db:
            await self._db.close()
            self._db = None

    # ── Internal helpers ───────────────────────────────────────────────

    @staticmethod
    def _row_to_node(row: Any) -> KnowledgeNode:
        """Convert a database row to a KnowledgeNode."""
        metadata = row["metadata"]
        if isinstance(metadata, str):
            metadata = json.loads(metadata)

        embedding = None
        embedding_blob = row["embedding"]
        if embedding_blob is not None:
            try:
                embedding = json.loads(embedding_blob.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                pass

        return KnowledgeNode(
            node_id=row["node_id"],
            node_type=row["node_type"],
            name=row["name"],
            content=row["content"],
            metadata=metadata,
            embedding=embedding,
        )

    @staticmethod
    def _row_to_edge(row: Any) -> KnowledgeEdge:
        """Convert a database row to a KnowledgeEdge."""
        metadata = row["metadata"]
        if isinstance(metadata, str):
            metadata = json.loads(metadata)

        return KnowledgeEdge(
            edge_id=row["edge_id"],
            source_id=row["source_id"],
            target_id=row["target_id"],
            relation=row["relation"],
            weight=row["weight"],
            metadata=metadata,
        )

    @staticmethod
    def _row_to_lesson(row: Any) -> Lesson:
        """Convert a database row to a Lesson."""
        created_at = row["created_at"]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now(timezone.utc)

        return Lesson(
            lesson_id=row["lesson_id"],
            symptom=row["symptom"],
            root_cause=row["root_cause"],
            fix_applied=row["fix_applied"],
            verification=row["verification"],
            reusable_rule=row["reusable_rule"],
            context=row["context"],
            confidence=row["confidence"],
            source_session=row["source_session"],
            created_at=created_at,
        )


# ── Utility functions ──────────────────────────────────────────────────────

def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x * x for x in a) ** 0.5
    mag_b = sum(x * x for x in b) ** 0.5
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return dot / (mag_a * mag_b)


def _hash_embed(text: str) -> list[float]:
    """Generate a deterministic hash-based embedding (fallback).

    Uses multiple hash rounds with different seeds to produce a
    fixed-length float vector. Similar approach to VectorStore._hash_embed
    but with NaN-safety to ensure deterministic output.
    """
    import math

    vector: list[float] = []
    for i in range(_EMBEDDING_DIM):
        seed = f"{text}||{i}".encode("utf-8")
        digest = hashlib.sha256(seed).digest()
        # Use integer interpretation for deterministic results (avoids NaN)
        int_val = int.from_bytes(digest[:4], byteorder="little", signed=False)
        # Map [0, 2^32) to [-1, 1]
        normalized = (int_val / 2**32) * 2.0 - 1.0
        vector.append(normalized)

    # Normalize to unit length
    magnitude = math.sqrt(sum(x * x for x in vector))
    if magnitude > 0:
        vector = [x / magnitude for x in vector]
    return vector


# ── Node extraction (rule-based) ──────────────────────────────────────────

import re as _re

# Common technical terms pattern
_TECH_PATTERN = _re.compile(
    r"[a-z][A-Z][a-zA-Z]+"       # camelCase
    r"|[a-z]+_[a-z_]+"           # snake_case
    r"|[A-Z][a-z]+(?:[A-Z][a-z]+)+"  # PascalCase
    r"|\b[A-Z]{2,}\b"            # Acronyms (API, SQL, etc.)
)

# Capitalized phrase pattern (potential entity names)
_ENTITY_PATTERN = _re.compile(
    r"(?<![a-z])"                # Not preceded by lowercase
    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)"  # Title Case phrases
)

# Quoted phrase pattern
_QUOTED_PATTERN = _re.compile(r'"([^"]+)"' + r"|'([^']+)'")


def _extract_entities_from_content(content: str) -> list[dict[str, str]]:
    """Extract potential entities from content using rule-based patterns.

    Returns a list of dicts with keys: name, node_type.
    """
    entities: list[dict[str, str]] = []
    seen: set[str] = set()

    # 1. Technical identifiers (camelCase, snake_case, PascalCase, acronyms)
    for match in _TECH_PATTERN.finditer(content):
        name = match.group(0)
        lower = name.lower()
        if lower not in seen and len(name) > 1:
            entities.append({"name": name, "node_type": "entity"})
            seen.add(lower)

    # 2. Title-case phrases (potential concept/entity names)
    for match in _ENTITY_PATTERN.finditer(content):
        name = match.group(1)
        lower = name.lower()
        # Filter out common non-entity title-case phrases
        if lower not in seen and len(name) > 3 and not _is_common_phrase(lower):
            entities.append({"name": name, "node_type": "concept"})
            seen.add(lower)

    # 3. Quoted phrases (explicitly named things)
    for match in _QUOTED_PATTERN.finditer(content):
        name = match.group(1) or match.group(2) or ""
        lower = name.lower().strip()
        if lower not in seen and 2 < len(name) < 100:
            entities.append({"name": name.strip(), "node_type": "entity"})
            seen.add(lower)

    return entities


_COMMON_PHRASES: frozenset[str] = frozenset({
    "the", "this", "that", "then", "there", "they", "their",
    "step", "first", "second", "third", "next", "last", "final",
    "make", "sure", "need", "will", "must", "should", "could",
    "also", "just", "like", "using", "based", "going",
})


def _is_common_phrase(lower: str) -> bool:
    """Check if a phrase is too common to be an entity."""
    words = lower.split()
    if len(words) == 1 and lower in _COMMON_PHRASES:
        return True
    return False


def _infer_edges(
    nodes: list[KnowledgeNode],
    session_id: str,
) -> list[KnowledgeEdge]:
    """Infer edges between nodes based on content overlap and patterns.

    Rules:
    - Keyword overlap between node contents → related_to
    - Temporal sequence in same session → derived_from
    - Fix/pattern patterns → example_of
    """
    edges: list[KnowledgeEdge] = []

    for i, node_a in enumerate(nodes):
        for j in range(i + 1, len(nodes)):
            node_b = nodes[j]

            # Compute content word overlap
            words_a = set(node_a.content.lower().split())
            words_b = set(node_b.content.lower().split())
            overlap = words_a & words_b

            if len(overlap) >= 2:
                # Determine relation type based on content patterns
                relation = _determine_relation(node_a, node_b)
                weight = min(len(overlap) / 10.0, 1.0)

                edges.append(KnowledgeEdge(
                    source_id=node_a.node_id,
                    target_id=node_b.node_id,
                    relation=relation,
                    weight=weight,
                    metadata={"source_session": session_id, "overlap_count": len(overlap)},
                ))

    return edges


def _determine_relation(node_a: KnowledgeNode, node_b: KnowledgeNode) -> str:
    """Determine the relation type between two nodes based on content patterns."""
    a_lower = node_a.content.lower()
    b_lower = node_b.content.lower()

    # Fix pattern: if one describes a problem and another a fix
    problem_words = {"error", "bug", "fail", "issue", "problem", "broken"}
    fix_words = {"fix", "resolve", "solution", "patch", "repair", "solved"}

    a_has_problem = any(w in a_lower for w in problem_words)
    b_has_fix = any(w in b_lower for w in fix_words)
    a_has_fix = any(w in a_lower for w in fix_words)
    b_has_problem = any(w in b_lower for w in problem_words)

    if a_has_problem and b_has_fix:
        return "example_of"
    if a_has_fix and b_has_problem:
        return "example_of"

    # Dependency pattern
    dep_words = {"depends", "requires", "needs", "uses", "imports"}
    if any(w in a_lower for w in dep_words):
        return "depends_on"

    # Extension pattern
    ext_words = {"extends", "builds", "enhances", "improves", "adds"}
    if any(w in a_lower for w in ext_words):
        return "extends"

    # Supersede pattern
    sup_words = {"replaces", "supersedes", "deprecates", "instead of"}
    if any(w in a_lower for w in sup_words):
        return "supersedes"

    # Contradiction pattern
    contra_words = {"however", "but", "contrary", "opposite", "not the case"}
    if any(w in a_lower for w in contra_words):
        return "contradicts"

    # Default to related_to
    return "related_to"


# ── Ring3Memory — Main public class ───────────────────────────────────────

class Ring3Memory:
    """
    Ring 3 — GraphRAG cold memory.

    Provides knowledge graph storage, semantic search, and structured
    lessons learned. Uses SQLite (aiosqlite) for persistence, FTS5 for
    text search, and sentence-transformers for embeddings (with hash-based
    fallback).

    Usage:
        ring3 = Ring3Memory("data/ring3.db")
        await ring3.initialize()

        # Store an episode
        await ring3.store_episode("session-1", "Fixed auth bug...", {...})

        # Retrieve context
        context = await ring3.retrieve_context("authentication error", top_k=5)

        # Store a lesson
        await ring3.store_lesson(Lesson(
            symptom="500 on login",
            root_cause="Missing CSRF token",
            fix_applied="Added CSRF middleware",
            verification="All login tests pass",
            reusable_rule="Always check middleware chain",
            context="Express.js auth setup",
        ))

        # Find similar lessons
        lessons = await ring3.find_similar_lessons("500 error on login")
    """

    def __init__(
        self,
        db_path: str = "data/ring3.db",
        vector_dim: int = 384,
    ) -> None:
        self._db_path = db_path
        self._vector_dim = vector_dim
        self._store: Ring3Store | None = None
        self._st_model: Any = None
        self._st_loaded: bool = False
        self._embedding_model_name: str = "all-MiniLM-L6-v2"

    async def initialize(self) -> None:
        """Initialize the Ring3 store and embedding support."""
        self._store = Ring3Store(self._db_path)
        await self._store.initialize()
        logger.info("Ring3Memory initialized at %s", self._db_path)

    # ── Embedding ──────────────────────────────────────────────────────

    def _embed(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text.

        Uses sentence-transformers if available, otherwise falls back
        to a deterministic hash-based embedding.
        """
        if not self._st_loaded:
            try:
                from sentence_transformers import SentenceTransformer
                self._st_model = SentenceTransformer(self._embedding_model_name)
                logger.info(
                    "Ring3: Loaded sentence-transformers model: %s",
                    self._embedding_model_name,
                )
            except Exception as exc:
                logger.warning(
                    "Ring3: sentence-transformers not available (%s) — "
                    "using hash-based fallback embedding",
                    exc,
                )
                self._st_model = None
            self._st_loaded = True

        if self._st_model is not None:
            embedding = self._st_model.encode(text, normalize_embeddings=True)
            return embedding.tolist()

        return _hash_embed(text)

    async def _embed_async(self, text: str) -> list[float]:
        """Generate embedding in a thread to avoid blocking the event loop."""
        return await asyncio.to_thread(self._embed, text)

    # ── Episode storage ────────────────────────────────────────────────

    async def store_episode(
        self,
        session_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[str]:
        """Store an episode: extract entities, create nodes, infer edges.

        Args:
            session_id: The session this episode belongs to.
            content: The episode content text.
            metadata: Optional metadata dict.

        Returns:
            A list of created node IDs.
        """
        if self._store is None:
            raise RuntimeError("Ring3 not initialized — call initialize() first")

        meta = metadata or {}
        now = datetime.now(timezone.utc).isoformat()

        # 1. Extract entities from content
        extracted = _extract_entities_from_content(content)
        if not extracted:
            # Create a single concept node for the whole content
            extracted = [{"name": f"episode-{session_id[:8]}", "node_type": "concept"}]

        # 2. Create KnowledgeNode objects
        created_nodes: list[KnowledgeNode] = []
        for entity_info in extracted:
            name = entity_info["name"]
            node_type = entity_info["node_type"]

            # Generate embedding
            embedding = await self._embed_async(f"{name}: {content[:500]}")

            node = KnowledgeNode(
                node_type=node_type,
                name=name,
                content=content[:2000],  # Truncate for storage
                metadata={
                    "source_session": session_id,
                    "created_at": now,
                    "access_count": 0,
                    "quality_score": meta.get("quality_score", 0.5),
                },
                embedding=embedding,
            )
            await self._store.store_node(node)
            created_nodes.append(node)

        # 3. Infer and create edges between extracted nodes
        edges = _infer_edges(created_nodes, session_id)
        for edge in edges:
            await self._store.store_edge(edge)

        # 4. Also link to existing nodes from the same session if any
        await self._link_to_existing_session_nodes(created_nodes, session_id)

        logger.info(
            "Ring3: Stored episode for session %s — %d nodes, %d edges",
            session_id, len(created_nodes), len(edges),
        )
        return [n.node_id for n in created_nodes]

    async def _link_to_existing_session_nodes(
        self,
        new_nodes: list[KnowledgeNode],
        session_id: str,
    ) -> None:
        """Create edges between new nodes and existing nodes from the same session."""
        if self._store is None:
            return

        # Find existing nodes from the same session
        existing_nodes = await self._store.search_nodes(
            query=session_id,
            top_k=20,
        )

        for new_node in new_nodes:
            for existing in existing_nodes:
                if existing.node_id == new_node.node_id:
                    continue
                # Check if they share content words
                new_words = set(new_node.content.lower().split()[:50])
                existing_words = set(existing.content.lower().split()[:50])
                overlap = new_words & existing_words
                if len(overlap) >= 3:
                    edge = KnowledgeEdge(
                        source_id=existing.node_id,
                        target_id=new_node.node_id,
                        relation="related_to",
                        weight=min(len(overlap) / 10.0, 1.0),
                        metadata={"source_session": session_id, "auto_linked": True},
                    )
                    await self._store.store_edge(edge)

    # ── Context retrieval ──────────────────────────────────────────────

    async def retrieve_context(
        self,
        query: str,
        top_k: int = 5,
        max_depth: int = 2,
    ) -> dict[str, Any]:
        """Find relevant nodes and expand via edges to build context.

        Performs the following steps:
        1. Generate query embedding
        2. Search nodes by text (FTS5) and by embedding similarity
        3. Merge and deduplicate results
        4. Expand context by traversing edges up to max_depth
        5. Build a structured context dict

        Args:
            query: The search query.
            top_k: Number of top nodes to retrieve initially.
            max_depth: Max BFS depth for graph expansion.

        Returns:
            A dict with keys: nodes, edges, context_text.
        """
        if self._store is None:
            raise RuntimeError("Ring3 not initialized — call initialize() first")

        # 1. Generate query embedding
        query_embedding = await self._embed_async(query)

        # 2. Search by FTS5 text search
        text_nodes = await self._store.search_nodes(query, top_k=top_k)

        # 3. Search by embedding similarity
        embedding_results = await self._store.search_nodes_by_embedding(
            query_embedding, top_k=top_k, min_similarity=0.3,
        )
        embedding_nodes = [node for node, _sim in embedding_results]

        # 4. Merge and deduplicate
        seen_ids: set[str] = set()
        seed_nodes: list[KnowledgeNode] = []
        for node in text_nodes + embedding_nodes:
            if node.node_id not in seen_ids:
                seed_nodes.append(node)
                seen_ids.add(node.node_id)

        seed_nodes = seed_nodes[:top_k]

        if not seed_nodes:
            return {"nodes": [], "edges": [], "context_text": ""}

        # 5. Expand via graph traversal
        all_nodes: list[KnowledgeNode] = list(seed_nodes)
        all_edges: list[KnowledgeEdge] = []

        for seed in seed_nodes:
            # Get direct edges
            edges = await self._store.get_edges(seed.node_id, direction="both")
            all_edges.extend(edges)

            # Get neighbors up to max_depth
            if max_depth > 1:
                neighbors = await self._store.get_neighbors(
                    seed.node_id, max_depth=max_depth,
                )
                for neighbor in neighbors:
                    if neighbor.node_id not in seen_ids:
                        all_nodes.append(neighbor)
                        seen_ids.add(neighbor.node_id)

        # Deduplicate edges
        seen_edge_ids: set[str] = set()
        unique_edges: list[KnowledgeEdge] = []
        for edge in all_edges:
            if edge.edge_id not in seen_edge_ids:
                unique_edges.append(edge)
                seen_edge_ids.add(edge.edge_id)

        # 6. Increment access counts for seed nodes
        for node in seed_nodes:
            try:
                node.metadata["access_count"] = node.metadata.get("access_count", 0) + 1
                await self._store.store_node(node)
            except Exception:
                pass

        # 7. Build context text
        context_text = self._build_context_text(seed_nodes, all_nodes, unique_edges)

        return {
            "nodes": [n.to_dict() for n in all_nodes],
            "edges": [e.to_dict() for e in unique_edges],
            "context_text": context_text,
        }

    @staticmethod
    def _build_context_text(
        seed_nodes: list[KnowledgeNode],
        all_nodes: list[KnowledgeNode],
        edges: list[KnowledgeEdge],
    ) -> str:
        """Build a human-readable context string from retrieved nodes and edges."""
        parts: list[str] = []

        # Seed nodes (most relevant)
        if seed_nodes:
            parts.append("=== Most Relevant Knowledge ===")
            for i, node in enumerate(seed_nodes, 1):
                parts.append(
                    f"[{i}] {node.name} ({node.node_type}): "
                    f"{node.content[:300]}{'...' if len(node.content) > 300 else ''}"
                )

        # Expanded context nodes
        expanded = [n for n in all_nodes if n not in seed_nodes]
        if expanded:
            parts.append("\n=== Related Knowledge ===")
            for node in expanded[:10]:  # Limit expanded nodes
                parts.append(
                    f"- {node.name} ({node.node_type}): "
                    f"{node.content[:200]}{'...' if len(node.content) > 200 else ''}"
                )

        # Relationship summary
        if edges:
            parts.append("\n=== Relationships ===")
            for edge in edges[:15]:  # Limit edges shown
                parts.append(
                    f"- {edge.source_id[:8]}... --[{edge.relation}]--> {edge.target_id[:8]}... "
                    f"(weight={edge.weight:.2f})"
                )

        return "\n".join(parts)

    # ── Lesson operations ──────────────────────────────────────────────

    async def store_lesson(self, lesson: Lesson) -> str:
        """Store a structured lesson with embedding.

        Creates a lesson node in the knowledge graph and stores the
        symptom embedding for similarity search.

        Args:
            lesson: The Lesson object to store.

        Returns:
            The lesson_id.
        """
        if self._store is None:
            raise RuntimeError("Ring3 not initialized — call initialize() first")

        # 1. Store the lesson
        lesson_id = await self._store.store_lesson(lesson)

        # 2. Generate and store symptom embedding
        symptom_text = f"{lesson.symptom} {lesson.context} {lesson.root_cause}"
        embedding = await self._embed_async(symptom_text)
        await self._store.store_lesson_embedding(
            lesson_id, embedding, self._embedding_model_name,
        )

        # 3. Create a knowledge node for the lesson
        lesson_node = KnowledgeNode(
            node_type="lesson",
            name=f"Lesson: {lesson.symptom[:80]}",
            content=(
                f"Symptom: {lesson.symptom}\n"
                f"Root cause: {lesson.root_cause}\n"
                f"Fix: {lesson.fix_applied}\n"
                f"Rule: {lesson.reusable_rule}"
            ),
            metadata={
                "source_session": lesson.source_session,
                "created_at": lesson.created_at.isoformat(),
                "access_count": 0,
                "quality_score": lesson.confidence,
                "lesson_id": lesson_id,
            },
            embedding=embedding,
        )
        await self._store.store_node(lesson_node)

        logger.info(
            "Ring3: Stored lesson %s — symptom=%r, confidence=%.2f",
            lesson_id, lesson.symptom[:50], lesson.confidence,
        )
        return lesson_id

    async def find_similar_lessons(
        self,
        symptom: str,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """Find lessons with similar symptoms using vector search.

        Args:
            symptom: The symptom text to search for.
            top_k: Maximum number of results.

        Returns:
            A list of dicts with keys: lesson, similarity.
        """
        if self._store is None:
            raise RuntimeError("Ring3 not initialized — call initialize() first")

        # 1. Embed the symptom
        query_embedding = await self._embed_async(symptom)

        # 2. Search by embedding similarity
        embedding_results = await self._store.search_lessons_by_embedding(
            query_embedding, top_k=top_k, min_similarity=0.2,
        )

        # 3. Also search by FTS5 for text matches
        fts_results = await self._store.search_lessons_fts(symptom, limit=top_k)

        # 4. Merge results, deduplicate
        seen_ids: set[str] = set()
        results: list[dict[str, Any]] = []

        for lesson, similarity in embedding_results:
            if lesson.lesson_id not in seen_ids:
                seen_ids.add(lesson.lesson_id)
                results.append({
                    "lesson": lesson.to_dict(),
                    "similarity": round(similarity, 4),
                })

        for lesson in fts_results:
            if lesson.lesson_id not in seen_ids:
                seen_ids.add(lesson.lesson_id)
                results.append({
                    "lesson": lesson.to_dict(),
                    "similarity": 0.5,  # FTS matches get a default similarity
                })

        # Sort by similarity descending
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    async def get_lessons_for_context(
        self,
        context: str,
        top_k: int = 3,
    ) -> list[dict[str, Any]]:
        """Find lessons applicable to the current context/situation.

        Searches both by symptom similarity and by context text match.

        Args:
            context: Description of the current situation/context.
            top_k: Maximum number of results.

        Returns:
            A list of dicts with keys: lesson, similarity, relevance_reason.
        """
        if self._store is None:
            raise RuntimeError("Ring3 not initialized — call initialize() first")

        # Embed the context description
        query_embedding = await self._embed_async(context)

        # Search lessons by embedding
        embedding_results = await self._store.search_lessons_by_embedding(
            query_embedding, top_k=top_k, min_similarity=0.2,
        )

        # Search by FTS5 on context field
        fts_results = await self._store.search_lessons_fts(context, limit=top_k)

        # Merge
        seen_ids: set[str] = set()
        results: list[dict[str, Any]] = []

        for lesson, similarity in embedding_results:
            if lesson.lesson_id not in seen_ids:
                seen_ids.add(lesson.lesson_id)
                reason = "Similar symptoms" if similarity > 0.7 else "Partially similar symptoms"
                if lesson.context and lesson.context.lower() in context.lower():
                    reason = "Same context/situation"
                results.append({
                    "lesson": lesson.to_dict(),
                    "similarity": round(similarity, 4),
                    "relevance_reason": reason,
                })

        for lesson in fts_results:
            if lesson.lesson_id not in seen_ids:
                seen_ids.add(lesson.lesson_id)
                results.append({
                    "lesson": lesson.to_dict(),
                    "similarity": 0.5,
                    "relevance_reason": "Text match in lesson content",
                })

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    # ── Graph summary and export ───────────────────────────────────────

    async def get_graph_summary(self) -> dict[str, Any]:
        """Get statistics about the knowledge graph.

        Returns:
            A dict with node counts by type, edge counts by relation,
            lesson count, and total counts.
        """
        if self._store is None:
            return {}

        node_counts = await self._store.get_node_count_by_type()
        edge_counts = await self._store.get_edge_count_by_relation()
        lesson_count = await self._store.get_lesson_count()

        # DB file size
        db_size_mb = 0.0
        try:
            db_path = Path(self._db_path)
            if db_path.exists():
                db_size_mb = round(db_path.stat().st_size / (1024 * 1024), 2)
        except Exception:
            pass

        return {
            "node_count_by_type": node_counts,
            "total_nodes": sum(node_counts.values()),
            "edge_count_by_relation": edge_counts,
            "total_edges": sum(edge_counts.values()),
            "lesson_count": lesson_count,
            "db_size_mb": db_size_mb,
        }

    async def export_graph(self, format: str = "json") -> str:
        """Export the full knowledge graph for visualization.

        Args:
            format: Export format. Currently only "json" is supported.

        Returns:
            A JSON string representing the full graph.
        """
        if self._store is None:
            return "{}"

        if format != "json":
            logger.warning("Unsupported export format %r — defaulting to json", format)

        nodes = await self._store.get_all_nodes()
        edges = await self._store.get_all_edges()
        lessons = await self._store.get_all_lessons()

        graph_data = {
            "nodes": [n.to_dict() for n in nodes],
            "edges": [e.to_dict() for e in edges],
            "lessons": [l.to_dict() for l in lessons],
            "metadata": {
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "total_lessons": len(lessons),
            },
        }

        return json.dumps(graph_data, ensure_ascii=False, indent=2)

    # ── Compatibility: search/store/get_related/close ──────────────────
    # These maintain backward compatibility with the old stub interface.

    async def search(
        self,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Semantic search across historical knowledge.

        Compatibility method matching the old Ring3 stub interface.
        """
        context = await self.retrieve_context(query, top_k=limit)
        return context.get("nodes", [])

    async def store(
        self,
        key: str,
        value: dict[str, Any],
    ) -> None:
        """Store knowledge in the graph.

        Compatibility method matching the old Ring3 stub interface.
        """
        content = value.get("content", str(value))
        metadata = value.get("metadata", {})
        metadata["key"] = key
        session_id = metadata.get("session_id", "unknown")
        await self.store_episode(session_id, content, metadata)

    async def get_related(
        self,
        key: str,
    ) -> list[dict[str, Any]]:
        """Get related knowledge graph nodes.

        Compatibility method matching the old Ring3 stub interface.
        """
        if self._store is None:
            return []

        # Search by key/name
        nodes = await self._store.search_nodes(key, top_k=10)
        results: list[dict[str, Any]] = []
        for node in nodes:
            # Get neighbors
            neighbors = await self._store.get_neighbors(node.node_id, max_depth=1)
            results.append(node.to_dict())
            for neighbor in neighbors:
                if neighbor.node_id != node.node_id:
                    results.append(neighbor.to_dict())
        return results

    # ── Statistics (sync, same pattern as Ring1/Ring2) ─────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about Ring3 memory contents (synchronous).

        Uses a synchronous SQLite connection, same pattern as Ring2.
        """
        stats: dict[str, Any] = {}
        try:
            import sqlite3
            sync_conn = sqlite3.connect(self._db_path)
            try:
                cursor = sync_conn.execute("SELECT COUNT(*) FROM knowledge_nodes")
                stats["node_count"] = cursor.fetchone()[0]

                cursor = sync_conn.execute("SELECT COUNT(*) FROM knowledge_edges")
                stats["edge_count"] = cursor.fetchone()[0]

                cursor = sync_conn.execute("SELECT COUNT(*) FROM lessons")
                stats["lesson_count"] = cursor.fetchone()[0]
            finally:
                sync_conn.close()
        except Exception:
            stats["node_count"] = stats.get("node_count", 0)
            stats["edge_count"] = stats.get("edge_count", 0)
            stats["lesson_count"] = stats.get("lesson_count", 0)

        try:
            db_path = Path(self._db_path)
            if db_path.exists():
                stats["db_size_mb"] = round(db_path.stat().st_size / (1024 * 1024), 2)
            else:
                stats["db_size_mb"] = 0
        except Exception:
            stats["db_size_mb"] = 0

        return stats

    # ── Lifecycle ──────────────────────────────────────────────────────

    async def close(self) -> None:
        """Graceful shutdown — close the store."""
        if self._store is not None:
            await self._store.close()
            self._store = None
        logger.info("Ring3Memory closed")
