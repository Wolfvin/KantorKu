"""
CheckpointContract — ABC yang harus diimplementasikan semua training scripts.
Ini adalah kontrak resmi antara free_gpu-kekek (sekarang kantorku.gpu) dan trainer.
"""
from abc import ABC, abstractmethod


class CheckpointContract(ABC):
    """Semua training jobs harus mewarisi kelas ini."""

    @abstractmethod
    def save_checkpoint(self, path: str) -> None:
        """Simpan model + optimizer + metadata ke path."""
        ...

    @abstractmethod
    def load_checkpoint(self, path: str) -> dict:
        """Load checkpoint, return dict {step, epoch, loss}. {} jika tidak ada."""
        ...

    @abstractmethod
    def train(self, resume_from: str | None = None) -> None:
        """Training loop utama. Handle SIGTERM di sini."""
        ...
