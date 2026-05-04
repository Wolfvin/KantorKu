"""
KantorkuConfig — TOML configuration parser and settings model.

Reads kantorku.toml and provides structured access to all configuration:
- Office settings (conductor model)
- Worker definitions (model, squad, role)
- Pool settings (model, instances, queue type)
- Provider credentials
- Memory settings
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import toml
except ImportError:
    toml = None  # type: ignore


@dataclass
class WorkerConfig:
    """Configuration for a single worker."""

    id: str = ""
    model: str = ""
    squad: str = ""
    role: str = ""
    capabilities: list[str] = field(default_factory=list)
    skill_md: str = ""

    @classmethod
    def from_dict(cls, worker_id: str, data: dict[str, Any]) -> WorkerConfig:
        return cls(
            id=worker_id,
            model=data.get("model", ""),
            squad=data.get("squad", ""),
            role=data.get("role", ""),
            capabilities=data.get("capabilities", []),
            skill_md=data.get("skill_md", ""),
        )


@dataclass
class PoolConfig:
    """Configuration for the DeepSeek Context Pool."""

    model: str = "deepseek/deepseek-v3-2"
    instances: int = 3
    queue_type: str = "fifo"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PoolConfig:
        return cls(
            model=data.get("model", "deepseek/deepseek-v3-2"),
            instances=data.get("instances", 3),
            queue_type=data.get("queue_type", "fifo"),
        )


@dataclass
class MemoryConfig:
    """Configuration for the Three-Ring Memory system."""

    ring1_path: str = "data/ring1.duckdb"
    ring2_path: str = "data/ring2.db"
    ring3_enabled: bool = False
    ring3_path: str = "data/ring3"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryConfig:
        return cls(
            ring1_path=data.get("ring1_path", "data/ring1.duckdb"),
            ring2_path=data.get("ring2_path", "data/ring2.db"),
            ring3_enabled=data.get("ring3_enabled", False),
            ring3_path=data.get("ring3_path", "data/ring3"),
        )


@dataclass
class ServerConfig:
    """Configuration for the FastAPI server."""

    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = field(default_factory=lambda: ["*"])

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ServerConfig:
        return cls(
            host=data.get("host", "0.0.0.0"),
            port=data.get("port", 8000),
            cors_origins=data.get("cors_origins", ["*"]),
        )


@dataclass
class KantorkuConfig:
    """
    Complete kantorku configuration.

    Loaded from kantorku.toml or created programmatically.
    """

    conductor_model: str = "anthropic/claude-opus-4-6"
    workers: dict[str, WorkerConfig] = field(default_factory=dict)
    pool: PoolConfig = field(default_factory=PoolConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    providers: dict[str, dict[str, str]] = field(default_factory=dict)

    # Security gates
    redteam_enabled: bool = True  # Gate for /godmode, /parseltongue, /classify, /stm commands

    # Personality system
    personality_enabled: bool = True  # Enable proactive worker speaking via consider_speaking()

    # Notebook
    notebook_enabled: bool = True  # Enable ProjectNotebook for shared persistent knowledge

    @classmethod
    def from_toml(cls, path: str | Path) -> KantorkuConfig:
        """Load configuration from a TOML file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        if toml is None:
            raise ImportError("TOML parsing requires 'toml' package. pip install toml")

        with open(path) as f:
            data = toml.load(f)

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KantorkuConfig:
        """Create config from a parsed TOML dict."""
        office = data.get("office", {})
        conductor_model = office.get("conductor_model", "anthropic/claude-opus-4-6")

        # Parse workers
        workers: dict[str, WorkerConfig] = {}
        for key, value in data.items():
            if key.startswith("workers."):
                worker_id = key[len("workers."):]
                if isinstance(value, dict):
                    workers[worker_id] = WorkerConfig.from_dict(worker_id, value)

        # Parse pool
        pool = PoolConfig.from_dict(data.get("pool", {}))

        # Parse memory
        memory = MemoryConfig.from_dict(data.get("memory", {}))

        # Parse server
        server = ServerConfig.from_dict(data.get("server", {}))

        # Parse providers
        providers: dict[str, dict[str, str]] = {}
        for key, value in data.items():
            if key.startswith("providers."):
                provider_name = key[len("providers."):]
                if isinstance(value, dict):
                    providers[provider_name] = value

        # Parse security/personality flags
        redteam_enabled = office.get("redteam_enabled", True)
        personality_enabled = office.get("personality_enabled", True)
        notebook_enabled = office.get("notebook_enabled", True)

        return cls(
            conductor_model=conductor_model,
            workers=workers,
            pool=pool,
            memory=memory,
            server=server,
            providers=providers,
            redteam_enabled=redteam_enabled,
            personality_enabled=personality_enabled,
            notebook_enabled=notebook_enabled,
        )

    def resolve_env_vars(self) -> None:
        """Resolve ${ENV_VAR} patterns in provider configs."""
        for provider_name, config in self.providers.items():
            for k, v in config.items():
                if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                    env_var = v[2:-1]
                    config[k] = os.environ.get(env_var, "")

    def to_dict(self) -> dict[str, Any]:
        """Serialize config back to dict format."""
        result: dict[str, Any] = {
            "office": {"conductor_model": self.conductor_model},
            "pool": {
                "model": self.pool.model,
                "instances": self.pool.instances,
                "queue_type": self.pool.queue_type,
            },
            "memory": {
                "ring1_path": self.memory.ring1_path,
                "ring2_path": self.memory.ring2_path,
                "ring3_enabled": self.memory.ring3_enabled,
            },
            "server": {
                "host": self.server.host,
                "port": self.server.port,
            },
        }
        for wid, wcfg in self.workers.items():
            result[f"workers.{wid}"] = {
                "model": wcfg.model,
                "squad": wcfg.squad,
                "role": wcfg.role,
            }
        for pname, pcfg in self.providers.items():
            result[f"providers.{pname}"] = pcfg
        return result
