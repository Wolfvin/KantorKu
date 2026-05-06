"""
RsvsClient — wrapper Python ke RSVS engine.

Dua mode koneksi:
  - HTTP (default, sekarang): panggil RSVS FastAPI yang jalan di repo SymbolicPuzzle3D
  - PyO3 bindings (future): import langsung via `from rsvs import RsvsCore`

RSVS tetap repo terpisah — tidak dipindahkan ke KantorKu.
"""
from __future__ import annotations

import logging
from typing import Any

from kantorku.symbolic.client.rsvs_types import (
    AppraiseResult, AppraiseItem, CompositionRef, GraphSnapshot,
    LanguageLink, Node, NodeId, QueryResult, Sense,
)

logger = logging.getLogger(__name__)


class RsvsClient:
    """
    Klien Python ke RSVS engine.

    Usage (HTTP mode):
        client = RsvsClient("http://localhost:8000")
        result = client.query("seekor anjing berlari")

    Usage (PyO3 mode, future):
        from rsvs import RsvsCore
        core = RsvsCore.load("path/to/rsvs.db")
        client = RsvsClient.from_core(core)
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self._http = None       # Lazy init — import httpx hanya jika HTTP mode
        self._core = None       # PyO3 RsvsCore jika pakai bindings

    @classmethod
    def from_core(cls, rsvs_core: Any) -> "RsvsClient":
        """Buat client dari PyO3 RsvsCore (future mode)."""
        client = cls.__new__(cls)
        client.base_url = ""
        client._http = None
        client._core = rsvs_core
        return client

    # ── Public API ────────────────────────────────────────────────────────────

    def query(self, text: str) -> QueryResult:
        """
        Query RSVS — dapat atom yang relevan dengan text.

        Args:
            text: Input teks, bisa satu atau beberapa kalimat.

        Returns:
            QueryResult dengan nodes yang relevan + convergence links.
        """
        if self._core is not None:
            return self._query_via_core(text)
        return self._query_via_http(text)

    def appraise(self, text: str) -> AppraiseResult:
        """
        Appraise structural consistency dari text terhadap graph saat ini.

        Returns:
            AppraiseResult dengan per-node consistency score.
        """
        if self._core is not None:
            return self._appraise_via_core(text)
        return self._appraise_via_http(text)

    def snapshot(self) -> GraphSnapshot:
        """
        Ambil snapshot seluruh graph (untuk spreading activation).

        Catatan: Ini mahal untuk graph besar. Pakai dengan bijak.
        """
        if self._core is not None:
            return self._snapshot_via_core()
        return self._snapshot_via_http()

    # ── HTTP mode ─────────────────────────────────────────────────────────────

    def _get_http(self):
        """Lazy-init httpx client."""
        if self._http is None:
            import httpx
            self._http = httpx.Client(timeout=10.0)
        return self._http

    def _query_via_http(self, text: str) -> QueryResult:
        http = self._get_http()
        try:
            resp = http.post(f"{self.base_url}/query", json={"text": text})
            resp.raise_for_status()
            return self._parse_query_result(resp.json())
        except Exception as e:
            logger.error(f"[RsvsClient] query HTTP error: {e}")
            return QueryResult(query_text=text)

    def _appraise_via_http(self, text: str) -> AppraiseResult:
        http = self._get_http()
        try:
            resp = http.post(f"{self.base_url}/appraise", json={"text": text})
            resp.raise_for_status()
            return self._parse_appraise_result(resp.json())
        except Exception as e:
            logger.error(f"[RsvsClient] appraise HTTP error: {e}")
            return AppraiseResult()

    def _snapshot_via_http(self) -> GraphSnapshot:
        http = self._get_http()
        try:
            resp = http.get(f"{self.base_url}/snapshot")
            resp.raise_for_status()
            return self._parse_snapshot(resp.json())
        except Exception as e:
            logger.error(f"[RsvsClient] snapshot HTTP error: {e}")
            return GraphSnapshot()

    # ── PyO3 mode (future) ────────────────────────────────────────────────────

    def _query_via_core(self, text: str) -> QueryResult:
        result = self._core.query(text)
        return self._parse_query_result(result)

    def _appraise_via_core(self, text: str) -> AppraiseResult:
        result = self._core.appraise(text)
        return self._parse_appraise_result(result)

    def _snapshot_via_core(self) -> GraphSnapshot:
        result = self._core.snapshot()
        return self._parse_snapshot(result)

    # ── Parsers ───────────────────────────────────────────────────────────────

    def _parse_query_result(self, data: dict | Any) -> QueryResult:
        """Parse raw response ke QueryResult. Toleran terhadap format yang berubah."""
        if isinstance(data, dict):
            nodes = [self._parse_node(n) for n in data.get("nodes", [])]
            links = [self._parse_link(l) for l in data.get("language_links", [])]
            return QueryResult(nodes=nodes, language_links=links,
                               query_text=data.get("query_text", ""))
        # PyO3 object — akses attribute
        try:
            nodes = [self._parse_node(n) for n in getattr(data, "nodes", [])]
            links = [self._parse_link(l) for l in getattr(data, "language_links", [])]
            return QueryResult(nodes=nodes, language_links=links)
        except Exception:
            return QueryResult()

    def _parse_appraise_result(self, data: dict | Any) -> AppraiseResult:
        if isinstance(data, dict):
            items = [
                AppraiseItem(
                    node_id=NodeId(i.get("node_id", 0)),
                    agree_pct=i.get("agree_pct", 1.0),
                    sense_matches=i.get("sense_matches", []),
                )
                for i in data.get("items", [])
            ]
            return AppraiseResult(
                items=items,
                overall_consistency=data.get("overall_consistency", 1.0),
                convergence_used=data.get("convergence_used", False),
            )
        return AppraiseResult()

    def _parse_snapshot(self, data: dict | Any) -> GraphSnapshot:
        if isinstance(data, dict):
            nodes = {
                NodeId(int(k)): self._parse_node(v)
                for k, v in data.get("nodes", {}).items()
            }
            return GraphSnapshot(nodes=nodes)
        return GraphSnapshot()

    def _parse_node(self, n: dict | Any) -> Node:
        if isinstance(n, dict):
            senses = [self._parse_sense(s) for s in n.get("senses", [])]
            return Node(
                node_id=NodeId(n.get("node_id", 0)),
                surface_label=n.get("surface_label", ""),
                layer=n.get("layer", 0),
                confidence=n.get("confidence", 0.5),
                senses=senses,
                is_seed=n.get("is_seed", False),
                internal_representation=n.get("internal_representation", False),
            )
        # PyO3 object
        return Node(
            node_id=NodeId(getattr(n, "node_id", 0)),
            surface_label=getattr(n, "surface_label", ""),
            layer=getattr(n, "layer", 0),
            confidence=getattr(n, "confidence", 0.5),
        )

    def _parse_sense(self, s: dict | Any) -> Sense:
        if isinstance(s, dict):
            comps = [
                CompositionRef(target_id=NodeId(c.get("target_id", 0)),
                               weight=c.get("weight", 1.0))
                for c in s.get("compositions", [])
            ]
            return Sense(
                sense_id=s.get("sense_id", 0),
                layer=s.get("layer", 0),
                compositions=comps,
                confidence=s.get("confidence", 0.5),
                description=s.get("description", ""),
            )
        return Sense(sense_id=0, layer=0)

    def _parse_link(self, l: dict | Any) -> LanguageLink:
        if isinstance(l, dict):
            return LanguageLink(
                node_a=NodeId(l.get("node_a", 0)),
                node_b=NodeId(l.get("node_b", 0)),
                link_type=l.get("link_type", "structural_equivalence"),
                score=l.get("score", 0.0),
            )
        return LanguageLink(node_a=NodeId(0), node_b=NodeId(0))
