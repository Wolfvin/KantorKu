"""
losion_train.py — Training script Losion untuk kantorku.gpu scheduler.

Menggantikan train.py dummy di free_gpu-kekek. Implement CheckpointContract
penuh agar AutoLoop bisa melakukan failover + resume yang seamless.

Usage:
    python -m kantorku.gpu.jobs.losion_train \\
        --model-size 1b \\
        --checkpoint-dir /workspace/ckpt/losion-1b-run-001 \\
        --data-dir exports/losion \\
        --max-steps 100000

Import:
    from kantorku.gpu.jobs.losion_train import LosionTrainJob
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import time
from pathlib import Path

logger = logging.getLogger(__name__)


# ── Import Losion (dari kantorku.losion setelah Agent 2 selesai) ────────────
# Jika kantorku.losion belum ada, fallback ke repo Losion langsung.
def _import_losion():
    """Coba import dari kantorku.losion dulu, fallback ke losion langsung."""
    try:
        from kantorku.losion.models.losion_model_v2 import LosionForCausalLMV2
        from kantorku.losion.training.trainer import LosionTrainer
        from kantorku.losion.training.losion_recipe import ScalingRecipe
        return LosionForCausalLMV2, LosionTrainer, ScalingRecipe
    except ImportError:
        pass

    try:
        from losion.models.losion_model_v2 import LosionForCausalLMV2
        from losion.training.trainer import LosionTrainer
        from losion.training.losion_recipe import ScalingRecipe
        return LosionForCausalLMV2, LosionTrainer, ScalingRecipe
    except ImportError as e:
        raise ImportError(
            "Tidak bisa import Losion. Pastikan kantorku.losion sudah dipasang "
            "(Agent 2) atau repo Losion ada di PYTHONPATH.\n"
            f"Original error: {e}"
        )


# ── Import GPU scheduler ─────────────────────────────────────────────────────
from kantorku.gpu.api.server import GPUSchedulerAPI
from kantorku.gpu.jobs.base_job import CheckpointContract
from kantorku.gpu.jobs.job_request import JobRequest


# ─────────────────────────────────────────────────────────────────────────────


MODEL_SIZE_MAP = {
    "1b": "losion_1b",
    "7b": "losion_7b",
    "48b": "losion_48b",
}

SAVE_EVERY_STEPS = 250  # Lebih sering dari interval SIGTERM (10 menit sebelum expiry)


class LosionTrainJob(CheckpointContract):
    """
    Training job Losion yang mengimplementasikan CheckpointContract.

    Dipanggil oleh free_gpu-kekek / kantorku.gpu AutoLoop via:
        job.train(resume_from=checkpoint_uri)

    SIGTERM handler memastikan checkpoint tersimpan sebelum lease expiry.
    """

    def __init__(
        self,
        model_size: str = "1b",
        checkpoint_dir: str = "./checkpoints",
        data_dir: str = "exports/losion",
        max_steps: int = 0,  # 0 = tidak ada limit
    ):
        scale_key = MODEL_SIZE_MAP.get(model_size)
        if scale_key is None:
            raise ValueError(f"model_size harus salah satu dari: {list(MODEL_SIZE_MAP.keys())}")

        self.checkpoint_dir = Path(checkpoint_dir)
        self.data_dir = Path(data_dir)
        self.max_steps = max_steps
        self.scale_key = scale_key

        # State yang dibaca SIGTERM handler
        self.global_step: int = 0
        self.current_epoch: int = 0
        self.last_loss: float = float("inf")

        self._trainer = None
        self._sigterm_received = False

        # Pasang SIGTERM handler
        signal.signal(signal.SIGTERM, self._handle_sigterm)

    # ── CheckpointContract ───────────────────────────────────────────────────

    def save_checkpoint(self, path: str) -> None:
        """
        Simpan model + optimizer + metadata ke path.
        Dipanggil oleh AutoLoop sebelum lease expiry.
        """
        if self._trainer is None:
            logger.warning("save_checkpoint dipanggil sebelum trainer diinisialisasi")
            return

        save_path = Path(path)
        save_path.mkdir(parents=True, exist_ok=True)

        # LosionTrainer sudah punya _save_checkpoint internal —
        # kita panggil via trainer langsung
        self._trainer._save_checkpoint(f"sigterm-step-{self.global_step}")
        logger.info(f"[Checkpoint] Saved step {self.global_step} → {save_path}")

    def load_checkpoint(self, path: str) -> dict:
        """
        Load checkpoint dari path.
        Return dict {step, epoch, loss}. {} jika tidak ada checkpoint.
        """
        ckpt_path = Path(path)
        if not ckpt_path.exists():
            return {}

        # Cari checkpoint terbaru
        ckpt_files = sorted(ckpt_path.glob("**/*.pt"), key=lambda p: p.stat().st_mtime)
        if not ckpt_files:
            return {}

        latest = ckpt_files[-1]
        logger.info(f"[Checkpoint] Akan resume dari: {latest}")

        return {
            "step": self.global_step,
            "epoch": self.current_epoch,
            "loss": self.last_loss,
            "path": str(latest),
        }

    def train(self, resume_from: str | None = None) -> None:
        """
        Training loop utama. Handle SIGTERM dengan graceful checkpoint.

        Args:
            resume_from: Path ke checkpoint directory untuk resume.
                         None = mulai dari awal.
        """
        LosionForCausalLMV2, LosionTrainer, ScalingRecipe = _import_losion()

        logger.info(f"[LosionTrain] Inisialisasi scale={self.scale_key}")

        # Load config + recipe
        config, recipe = ScalingRecipe.get(self.scale_key)

        # Override max_steps jika di-set
        if self.max_steps > 0:
            recipe.max_steps = self.max_steps

        # Buat model
        model = LosionForCausalLMV2(config)
        param_count = sum(p.numel() for p in model.parameters()) / 1e9
        logger.info(f"[LosionTrain] Model: {param_count:.2f}B parameters")

        # Inisialisasi trainer
        self._trainer = LosionTrainer(
            model=model,
            recipe=recipe,
            checkpoint_dir=str(self.checkpoint_dir),
            data_dir=str(self.data_dir),
        )

        # Resume jika ada checkpoint
        if resume_from:
            ckpt_info = self.load_checkpoint(resume_from)
            if ckpt_info.get("path"):
                self._trainer._load_checkpoint(ckpt_info["path"])
                self.global_step = self._trainer.global_step
                self.current_epoch = self._trainer.current_epoch
                logger.info(f"[LosionTrain] Resumed dari step {self.global_step}")

        logger.info(f"[LosionTrain] Mulai training dari step {self.global_step}")

        # Training loop — periodic checkpoint + SIGTERM check
        try:
            self._training_loop()
        except SystemExit:
            logger.info("[LosionTrain] SystemExit — checkpoint sudah disimpan oleh SIGTERM handler")
            raise

        logger.info(f"[LosionTrain] Training selesai. Total steps: {self.global_step}")

    # ── Internal ─────────────────────────────────────────────────────────────

    def _training_loop(self):
        """
        Wrapper training loop yang:
        1. Memanggil LosionTrainer.train()
        2. Sync state (global_step, current_epoch, last_loss) setiap SAVE_EVERY_STEPS
        3. Cek SIGTERM flag secara periodik
        """
        # LosionTrainer sudah handle checkpoint internal (save_steps),
        # kita hanya perlu sync state agar SIGTERM handler bisa membacanya.

        # Hook: pasang callback ke trainer jika ada, atau override save_steps
        original_save_steps = self._trainer.trainer_config.save_steps
        self._trainer.trainer_config.save_steps = SAVE_EVERY_STEPS

        try:
            self._trainer.train()
        finally:
            # Sync state setelah training selesai atau interrupted
            self.global_step = self._trainer.global_step
            self.current_epoch = self._trainer.current_epoch
            # last_loss: ambil dari trainer jika ada, otherwise keep existing
            if hasattr(self._trainer, "last_loss"):
                self.last_loss = self._trainer.last_loss

    def _handle_sigterm(self, signum, frame):
        """
        SIGTERM handler — dipanggil 10 menit sebelum lease expiry oleh AutoLoop.
        Simpan checkpoint lalu exit gracefully.
        """
        logger.warning(f"[SIGTERM] Diterima! Step={self.global_step}, Loss={self.last_loss:.4f}")
        self._sigterm_received = True

        # Simpan checkpoint segera
        try:
            self.save_checkpoint(str(self.checkpoint_dir))
            logger.info(f"[SIGTERM] Checkpoint tersimpan. Ready for failover.")
        except Exception as e:
            logger.error(f"[SIGTERM] Gagal simpan checkpoint: {e}")

        sys.exit(0)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Losion training job untuk kantorku.gpu scheduler"
    )
    parser.add_argument(
        "--model-size", choices=["1b", "7b", "48b"], default="1b",
        help="Ukuran model Losion (default: 1b)"
    )
    parser.add_argument(
        "--checkpoint-dir", default="./checkpoints/losion",
        help="Direktori untuk menyimpan checkpoint"
    )
    parser.add_argument(
        "--resume-from", default=None,
        help="Path ke checkpoint directory untuk resume"
    )
    parser.add_argument(
        "--data-dir", default="exports/losion",
        help="Direktori data training (output dari DataMerger)"
    )
    parser.add_argument(
        "--max-steps", type=int, default=0,
        help="Maksimum training steps. 0 = tidak ada limit"
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    job = LosionTrainJob(
        model_size=args.model_size,
        checkpoint_dir=args.checkpoint_dir,
        data_dir=args.data_dir,
        max_steps=args.max_steps,
    )

    job.train(resume_from=args.resume_from)


if __name__ == "__main__":
    main()
