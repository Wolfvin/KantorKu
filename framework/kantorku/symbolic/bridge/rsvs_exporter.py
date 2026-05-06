"""
RSVSLosionExporter — Export dari RSVS knowledge graph ke format training Losion.

Export 4 format:
1. pretraining  — plain text dari atom descriptions + compositions
2. reasoning    — pasangan (query → reasoning_trace) dari RSVS appraise
3. crosslingual — pasangan ekuivalen struktural antar bahasa (convergence pairs)
4. appraise     — structural consistency judgment pairs

Import:
    from kantorku.losion.bridge.rsvs_exporter import RSVSLosionExporter, ExportConfig

Usage:
    from rsvs import RsvsCore

    rsvs = RsvsCore.load("path/to/rsvs.db")
    exporter = RSVSLosionExporter(rsvs, ExportConfig(
        min_confidence=0.6,
        min_convergence_score=0.75,
        output_dir="exports/rsvs_losion",
    ))
    counts = exporter.export_all()
    # counts = {"pretraining": 12450, "reasoning": 3210, "crosslingual": 890, "appraise": 2100}
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

logger = logging.getLogger(__name__)


@dataclass
class ExportConfig:
    """Konfigurasi untuk RSVSLosionExporter."""

    # Filter threshold
    min_confidence: float = 0.6
    """Hanya export atom dengan confidence >= nilai ini."""

    min_convergence_score: float = 0.75
    """Hanya export convergence pair dengan score >= nilai ini."""

    # Output
    output_dir: str = "exports/rsvs_losion"
    """Direktori output. Akan dibuat jika belum ada."""

    val_ratio: float = 0.05
    """Fraksi data untuk validation split."""

    # Pretraining
    max_pretraining_tokens: int = 512
    """Maksimum token per pretraining sample."""

    # Reasoning
    min_reasoning_steps: int = 2
    """Minimum jumlah langkah reasoning untuk dimasukkan."""

    # Batch
    batch_size: int = 1000
    """Ukuran batch untuk iterasi dari RSVS."""


class RSVSLosionExporter:
    """
    Mengekspor data dari RSVS knowledge graph ke format training Losion.

    RSVS adalah symbolic AI engine — datanya berupa atom (node) dengan
    confidence, layer, compositions, dan convergence links. Exporter ini
    mengubah struktur tersebut ke jsonl yang bisa dikonsumsi LosionRecipe.

    Catatan penting:
        - RSVS tetap repo terpisah (Rust) — tidak dipindahkan ke KantorKu
        - Import via: `from rsvs import RsvsCore`
        - RSVS adalah language-agnostic — JANGAN tambahkan language detection
    """

    def __init__(self, rsvs_core: Any, config: ExportConfig | None = None):
        """
        Args:
            rsvs_core: Instance dari RsvsCore (dari repo RSVS/SymbolicPuzzle3D).
            config: ExportConfig. None = pakai default.
        """
        self.rsvs = rsvs_core
        self.config = config or ExportConfig()
        self._out = Path(self.config.output_dir)

    # ── Public API ────────────────────────────────────────────────────────────

    def export_all(self) -> dict[str, int]:
        """
        Export semua 4 format. Return dict jumlah records per format.

        Returns:
            {"pretraining": N, "reasoning": N, "crosslingual": N, "appraise": N}
        """
        self._out.mkdir(parents=True, exist_ok=True)

        counts = {}
        counts["pretraining"] = self._export_pretraining()
        counts["reasoning"] = self._export_reasoning()
        counts["crosslingual"] = self._export_crosslingual()
        counts["appraise"] = self._export_appraise()

        total = sum(counts.values())
        logger.info(f"[RSVSExport] Selesai. Total records: {total:,} — {counts}")
        return counts

    # ── Private: Per-format export ────────────────────────────────────────────

    def _export_pretraining(self) -> int:
        """
        Export atom descriptions + compositions sebagai pretraining text.

        Format jsonl per record:
            {"text": "...", "source": "rsvs_atom", "atom_id": N, "layer": N,
             "confidence": 0.xx, "token_count": N}
        """
        subset_dir = self._out / "pretraining"
        subset_dir.mkdir(exist_ok=True)

        records = []
        for atom in self._iter_atoms(min_confidence=self.config.min_confidence):
            text = self._atom_to_pretraining_text(atom)
            if not text:
                continue

            records.append({
                "text": text,
                "source": "rsvs_atom",
                "atom_id": atom.get("id"),
                "layer": atom.get("layer", 0),
                "confidence": atom.get("confidence", 0.0),
                "token_count": len(text.split()),
            })

        return self._write_split(records, subset_dir)

    def _export_reasoning(self) -> int:
        """
        Export reasoning traces dari RSVS appraise sessions.

        Format jsonl per record:
            {"prompt": "...", "response": "...", "steps": [...],
             "source": "rsvs_appraise", "convergence_used": bool}
        """
        subset_dir = self._out / "reasoning"
        subset_dir.mkdir(exist_ok=True)

        records = []
        for session in self._iter_appraise_sessions():
            if len(session.get("steps", [])) < self.config.min_reasoning_steps:
                continue

            records.append({
                "prompt": session.get("query", ""),
                "response": session.get("conclusion", ""),
                "steps": session.get("steps", []),
                "source": "rsvs_appraise",
                "convergence_used": session.get("convergence_used", False),
            })

        return self._write_split(records, subset_dir)

    def _export_crosslingual(self) -> int:
        """
        Export convergence pairs — atom yang strukturally ekuivalen.

        Catatan: RSVS tidak tahu ini adalah "bahasa berbeda" — convergence
        terjadi karena overlap struktural, bukan karena mapping bahasa.

        Format jsonl per record:
            {"atom_a": {...}, "atom_b": {...}, "convergence_score": 0.xx,
             "shared_compositions": [...], "source": "rsvs_convergence"}
        """
        subset_dir = self._out / "crosslingual"
        subset_dir.mkdir(exist_ok=True)

        records = []
        for pair in self._iter_convergence_pairs(
            min_score=self.config.min_convergence_score
        ):
            records.append({
                "atom_a": pair.get("node_a"),
                "atom_b": pair.get("node_b"),
                "convergence_score": pair.get("score", 0.0),
                "shared_compositions": pair.get("shared_compositions", []),
                "source": "rsvs_convergence",
            })

        return self._write_split(records, subset_dir)

    def _export_appraise(self) -> int:
        """
        Export structural consistency judgments.

        Format jsonl per record:
            {"statement": "...", "judgment": "consistent|inconsistent|uncertain",
             "reason": "...", "atoms_involved": [...], "source": "rsvs_judgment"}
        """
        subset_dir = self._out / "appraise"
        subset_dir.mkdir(exist_ok=True)

        records = []
        for judgment in self._iter_judgments():
            records.append({
                "statement": judgment.get("statement", ""),
                "judgment": judgment.get("verdict", "uncertain"),
                "reason": judgment.get("reason", ""),
                "atoms_involved": judgment.get("atom_ids", []),
                "source": "rsvs_judgment",
            })

        return self._write_split(records, subset_dir)

    # ── RSVS iterators ────────────────────────────────────────────────────────

    def _iter_atoms(self, min_confidence: float = 0.0) -> Iterator[dict]:
        """Iterate semua atom dari RSVS dengan filter confidence."""
        try:
            for atom in self.rsvs.iter_atoms(
                min_confidence=min_confidence,
                batch_size=self.config.batch_size,
            ):
                yield atom
        except AttributeError:
            # Fallback jika RSVS belum implement iter_atoms
            logger.warning("rsvs.iter_atoms tidak tersedia — skip pretraining export")

    def _iter_appraise_sessions(self) -> Iterator[dict]:
        """Iterate appraise sessions dari RSVS."""
        try:
            yield from self.rsvs.iter_appraise_sessions(
                batch_size=self.config.batch_size
            )
        except AttributeError:
            logger.warning("rsvs.iter_appraise_sessions tidak tersedia")

    def _iter_convergence_pairs(self, min_score: float = 0.0) -> Iterator[dict]:
        """Iterate convergence pairs dari RSVS."""
        try:
            yield from self.rsvs.iter_convergence_pairs(
                min_score=min_score,
                batch_size=self.config.batch_size,
            )
        except AttributeError:
            logger.warning("rsvs.iter_convergence_pairs tidak tersedia")

    def _iter_judgments(self) -> Iterator[dict]:
        """Iterate structural judgments dari RSVS."""
        try:
            yield from self.rsvs.iter_judgments(
                batch_size=self.config.batch_size
            )
        except AttributeError:
            logger.warning("rsvs.iter_judgments tidak tersedia")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _atom_to_pretraining_text(self, atom: dict) -> str:
        """
        Ubah atom menjadi teks pretraining yang bermakna.
        Gunakan surface_label (display-only) + komposisi.
        """
        label = atom.get("surface_label", "")
        layer = atom.get("layer", 0)
        compositions = atom.get("compositions", [])
        senses = atom.get("active_senses", [])

        if not label:
            return ""

        parts = [label]

        if compositions:
            comp_labels = [c.get("surface_label", "") for c in compositions if c.get("surface_label")]
            if comp_labels:
                parts.append(f"composed of: {', '.join(comp_labels)}")

        if senses:
            sense_descs = [s.get("description", "") for s in senses if s.get("description")]
            if sense_descs:
                parts.append(f"senses: {'; '.join(sense_descs[:3])}")

        text = ". ".join(filter(None, parts)) + "."

        # Trim ke max_pretraining_tokens (rough estimate via split)
        tokens = text.split()
        if len(tokens) > self.config.max_pretraining_tokens:
            text = " ".join(tokens[: self.config.max_pretraining_tokens]) + "..."

        return text

    def _write_split(self, records: list[dict], dest: Path) -> int:
        """
        Tulis records ke train.jsonl dan val.jsonl.
        Return total jumlah records.
        """
        if not records:
            (dest / "train.jsonl").write_text("", encoding="utf-8")
            (dest / "val.jsonl").write_text("", encoding="utf-8")
            return 0

        # Shuffle deterministik
        import random
        rng = random.Random(42)
        rng.shuffle(records)

        n_val = max(1, int(len(records) * self.config.val_ratio))
        val_records = records[:n_val]
        train_records = records[n_val:]

        def write_jsonl(path: Path, data: list[dict]) -> None:
            path.write_text(
                "\n".join(json.dumps(r, ensure_ascii=False) for r in data),
                encoding="utf-8",
            )

        write_jsonl(dest / "train.jsonl", train_records)
        write_jsonl(dest / "val.jsonl", val_records)

        logger.info(f"[RSVSExport] {dest.name}: {len(train_records)} train, {len(val_records)} val")
        return len(records)
