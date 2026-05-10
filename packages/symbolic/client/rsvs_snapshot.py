"""
GraphSnapshot helper — utility untuk bekerja dengan snapshot RSVS graph.
"""
from __future__ import annotations

from kantorku.symbolic.client.rsvs_types import GraphSnapshot, Node, NodeId


class GraphSnapshotHelper:
    """Utility wrapper di atas GraphSnapshot untuk query yang lebih mudah."""

    def __init__(self, snapshot: GraphSnapshot):
        self.snapshot = snapshot

    def get_compositions_of(self, node_id: NodeId) -> list[Node]:
        """Dapat semua node yang menjadi komposisi dari node ini."""
        node = self.snapshot.node_by_id(node_id)
        if not node:
            return []

        comp_ids = set()
        for sense in node.senses:
            for comp in sense.compositions:
                comp_ids.add(comp.target_id)

        return [n for nid in comp_ids if (n := self.snapshot.node_by_id(nid))]

    def get_composites_of(self, node_id: NodeId) -> list[Node]:
        """Dapat semua node yang menggunakan node ini sebagai komposisi (reverse)."""
        result = []
        for node in self.snapshot.nodes.values():
            for sense in node.senses:
                for comp in sense.compositions:
                    if comp.target_id == node_id:
                        result.append(node)
                        break
        return result

    def seeds(self) -> list[Node]:
        """Dapat semua seed atoms (layer 0)."""
        return [n for n in self.snapshot.nodes.values() if n.is_seed]

    def by_layer(self, layer: int) -> list[Node]:
        """Dapat semua node di layer tertentu."""
        return [n for n in self.snapshot.nodes.values() if n.layer == layer]
