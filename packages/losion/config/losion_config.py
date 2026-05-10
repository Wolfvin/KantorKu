"""LosionConfig — konfigurasi model yang di-load dari YAML."""
from dataclasses import dataclass, field
from pathlib import Path
import yaml


@dataclass
class LosionConfig:
    # Model architecture
    vocab_size: int = 32_000
    hidden_size: int = 2048
    num_layers: int = 24
    num_heads: int = 16
    max_seq_len: int = 4096

    # Training
    learning_rate: float = 3e-4
    warmup_steps: int = 500
    weight_decay: float = 0.1

    # Memory
    working_memory_size: int = 512   # Ring buffer
    ltm_compression_ratio: float = 0.1

    @classmethod
    def from_yaml(cls, path: str) -> "LosionConfig":
        data = yaml.safe_load(Path(path).read_text())
        return cls(**data)
