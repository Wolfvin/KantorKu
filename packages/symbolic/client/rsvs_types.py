"""
RSVS Types — dataclass representasi untuk Node, Sense, CompositionRef, LanguageLink.

Dipakai oleh RsvsClient untuk mewrap response dari RSVS HTTP API atau PyO3 bindings.
Semua types ini language-agnostic — tidak ada field bahasa, hanya structure.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import NewType, Optional

NodeId = NewType("NodeId", int)


@dataclass
class CompositionRef:
    """Referensi ke node lain yang membentuk sense ini."""
    target_id: NodeId
    weight: float = 1.0


@dataclass
class Sense:
    """Satu sense dari sebuah node — terbentuk dari komposisi atom-atom lain."""
    sense_id: int
    layer: int
    compositions: list[CompositionRef] = field(default_factory=list)
    confidence: float = 0.5
    description: str = ""


@dataclass
class Node:
    """Atom dalam RSVS knowledge graph."""
    node_id: NodeId
    surface_label: str          # Display-only — bukan semantic anchor
    layer: int = 0
    confidence: float = 0.5
    senses: list[Sense] = field(default_factory=list)
    is_seed: bool = False       # True jika ini salah satu dari 24 primitif
    internal_representation: bool = False  # True jika layer 1 internal


@dataclass
class LanguageLink:
    """Link konvergensi antara dua node yang strukturally ekuivalen."""
    node_a: NodeId
    node_b: NodeId
    link_type: str = "structural_equivalence"
    score: float = 0.0
    shared_compositions: list[CompositionRef] = field(default_factory=list)


@dataclass
class QueryResult:
    """Hasil dari RSVS.query()."""
    nodes: list[Node] = field(default_factory=list)
    language_links: list[LanguageLink] = field(default_factory=list)
    query_text: str = ""


@dataclass
class AppraiseItem:
    """Satu item dalam hasil appraise."""
    node_id: NodeId
    agree_pct: float = 1.0      # 1.0 = fully consistent, 0.0 = contradiction
    sense_matches: list[int] = field(default_factory=list)


@dataclass
class AppraiseResult:
    """Hasil dari RSVS.appraise()."""
    items: list[AppraiseItem] = field(default_factory=list)
    overall_consistency: float = 1.0
    convergence_used: bool = False


@dataclass
class GraphSnapshot:
    """Snapshot dari seluruh graph — dipakai untuk spreading activation."""
    nodes: dict[NodeId, Node] = field(default_factory=dict)

    def node_by_id(self, node_id: NodeId) -> Optional[Node]:
        return self.nodes.get(node_id)
