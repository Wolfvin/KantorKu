"""
DataMerger — Menggabungkan output dari RSVSLosionExporter dan LosionExporter
ke satu direktori exports/losion/ yang siap dikonsumsi LosionRecipe.

Struktur input:
    exports/rsvs_losion/
        pretraining/{train,val}.jsonl
        reasoning/{train,val}.jsonl
        crosslingual/{train,val}.jsonl
        appraise/{train,val}.jsonl

    exports/kantorku_losion/
        pretraining/{train,val}.jsonl
        rlhf_qa/{train,val}.jsonl
        preference/{train,val}.jsonl

Struktur output:
    exports/losion/
        pretraining/{train,val}.jsonl   ← gabungan dari dua sumber
        reasoning/{train,val}.jsonl     ← hanya dari RSVS
        crosslingual/{train,val}.jsonl  ← hanya dari RSVS
        appraise/{train,val}.jsonl      ← hanya dari RSVS
        rlhf_qa/{train,val}.jsonl       ← hanya dari KantorKu
        preference/{train,val}.jsonl    ← hanya dari KantorKu
"""
import shutil
from pathlib import Path
from dataclasses import dataclass


@dataclass
class MergeConfig:
    rsvs_export_dir: str = "exports/rsvs_losion"
    kantorku_export_dir: str = "exports/kantorku_losion"
    output_dir: str = "exports/losion"


class DataMerger:
    """
    Menggabungkan dua sumber export ke satu direktori.
    """

    def __init__(self, config: MergeConfig = None):
        self.config = config or MergeConfig()

    def merge(self) -> dict[str, int]:
        """Jalankan merge. Return dict jumlah records per subset."""
        out = Path(self.config.output_dir)
        out.mkdir(parents=True, exist_ok=True)

        rsvs = Path(self.config.rsvs_export_dir)
        kantorku = Path(self.config.kantorku_export_dir)

        counts = {}

        # Pretraining: gabungkan dari dua sumber
        counts["pretraining"] = self._merge_subset(
            sources=[rsvs / "pretraining", kantorku / "pretraining"],
            dest=out / "pretraining",
        )

        # Subset yang hanya dari RSVS
        for subset in ["reasoning", "crosslingual", "appraise"]:
            counts[subset] = self._copy_subset(rsvs / subset, out / subset)

        # Subset yang hanya dari KantorKu
        for subset in ["rlhf_qa", "preference"]:
            counts[subset] = self._copy_subset(kantorku / subset, out / subset)

        return counts

    def _merge_subset(self, sources: list[Path], dest: Path) -> int:
        """Gabungkan beberapa sumber ke satu subset."""
        dest.mkdir(parents=True, exist_ok=True)
        total = 0
        for split in ["train.jsonl", "val.jsonl"]:
            lines = []
            for src in sources:
                f = src / split
                if f.exists():
                    lines.extend(f.read_text(encoding="utf-8").splitlines())
            (dest / split).write_text("\n".join(lines), encoding="utf-8")
            total += len(lines)
        return total

    def _copy_subset(self, src: Path, dest: Path) -> int:
        """Copy subset dari satu sumber ke dest."""
        if not src.exists():
            return 0
        shutil.copytree(src, dest, dirs_exist_ok=True)
        total = 0
        for f in dest.glob("*.jsonl"):
            total += len(f.read_text().splitlines())
        return total
