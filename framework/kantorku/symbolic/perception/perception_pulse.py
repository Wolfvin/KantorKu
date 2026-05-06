"""
PerceptionPulse — dipanggil setiap kali input teks masuk.

Menyebarkan aktivasi ke semua atom yang relevan secara simultan
(bukan sequential). Ini yang membuat RSVS terasa seperti "otak" —
bukan lookup table.
"""
from __future__ import annotations

from kantorku.symbolic.client.rsvs_client import RsvsClient
from kantorku.symbolic.perception.activation_state import ActivationState, NodeId


class PerceptionPulse:
    """
    Alur kerja per input:
        1. RSVS.query(text) → dapat relevant nodes
        2. Aktifkan semua node yang relevan dengan strength proporsional ke confidence
        3. Spreading activation: aktifkan juga komposisi dari node yang aktif
        4. Update ActivationState

    Analogi: seperti cahaya yang menyebar dari titik ke seluruh graph.
    """

    def __init__(self, rsvs: RsvsClient, activation_state: ActivationState,
                 spread_depth: int = 2, spread_decay: float = 0.5):
        self.rsvs = rsvs
        self.state = activation_state
        self.spread_depth = spread_depth   # Seberapa jauh spreading
        self.spread_decay = spread_decay   # Strength berkurang per hop

    def pulse(self, text: str) -> ActivationState:
        """
        Proses satu input teks. Return state yang sudah diupdate.

        Args:
            text: Input teks (satu kalimat atau beberapa kalimat)

        Returns:
            ActivationState yang sudah diupdate dengan aktivasi baru
        """
        # 1. Query RSVS — dapat semua atom yang relevan
        query_result = self.rsvs.query(text)

        # 2. Aktifkan atom yang ditemukan
        for node in query_result.nodes:
            self.state.activate(
                NodeId(node.node_id),
                strength=node.confidence   # Confidence as activation strength
            )

        # 3. Spreading activation ke komposisi
        self._spread(list(query_result.nodes), depth=self.spread_depth,
                     strength=self.spread_decay)

        return self.state

    def _spread(self, nodes, depth: int, strength: float) -> None:
        """Sebarkan aktivasi ke komposisi dari node yang aktif."""
        if depth == 0 or not nodes:
            return

        next_nodes = []
        snapshot = self.rsvs.snapshot()

        for node in nodes:
            for sense in (node.senses or []):
                for comp in sense.compositions:
                    comp_node = snapshot.node_by_id(comp.target_id)
                    if comp_node:
                        self.state.activate(NodeId(comp.target_id), strength=strength)
                        next_nodes.append(comp_node)

        # Rekursif dengan strength yang meluruh
        self._spread(next_nodes, depth=depth - 1, strength=strength * self.spread_decay)
