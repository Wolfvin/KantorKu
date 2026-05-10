"""
ActivationState — "working memory" simbolik dari RSVS.

Hidup selama sesi percakapan. Setiap atom yang relevan mendapat
activation_level yang meluruh jika tidak diaktifkan ulang.

Blueprint: LongTermMemory di Losion DualMemorySystem (EMA compressed).
Di sini: lebih simpel — hanya decay linier, bukan EMA.
"""
from dataclasses import dataclass, field
from typing import NewType

NodeId = NewType("NodeId", int)


@dataclass
class ActivationState:
    """
    HashMap<NodeId, f32> yang hidup selama satu sesi.

    Blueprint: LongTermMemory di Losion DualMemorySystem (EMA compressed).
    Di sini: lebih simpel — hanya decay linier, bukan EMA.
    """
    activations: dict[NodeId, float] = field(default_factory=dict)
    decay_rate: float = 0.05           # Per-tick decay (dikurangi tiap DecayLoop.tick())
    min_threshold: float = 0.01        # Pruned jika di bawah ini

    def activate(self, node_id: NodeId, strength: float = 1.0) -> None:
        """Aktifkan atau perkuat node."""
        current = self.activations.get(node_id, 0.0)
        # Additive dengan cap di 1.0
        self.activations[node_id] = min(1.0, current + strength)

    def decay(self) -> None:
        """Kurangi semua activation. Hapus yang di bawah threshold."""
        to_remove = []
        for node_id, level in self.activations.items():
            new_level = level - self.decay_rate
            if new_level < self.min_threshold:
                to_remove.append(node_id)
            else:
                self.activations[node_id] = new_level
        for node_id in to_remove:
            del self.activations[node_id]

    def top_k(self, k: int = 20) -> list[tuple[NodeId, float]]:
        """Return k node dengan activation tertinggi."""
        return sorted(
            self.activations.items(),
            key=lambda x: x[1],
            reverse=True
        )[:k]

    def to_context_vector(self) -> dict[NodeId, float]:
        """Format untuk dikirim ke Losion sebagai symbolic context."""
        return dict(self.top_k(50))
