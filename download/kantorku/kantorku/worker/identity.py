"""
WorkerIdentity — Worker plugin system.

Each worker is defined by:
- plugin.json: machine-readable metadata (id, model, squad, capabilities)
- SKILL.md: human-readable skill description (injected into LLM prompt)

Workers are discovered from the `workers/` directory at startup.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class WorkerIdentity:
    """
    A worker's identity — loaded from plugin.json + SKILL.md.

    Attributes:
        id: Unique worker identifier (e.g. "coder_backend")
        model: LLM model assignment (e.g. "minimax/minimax-m2-7")
        squad: Squad membership (coding, verification, support)
        role: Human-readable role description
        capabilities: What this worker can do
        skill_md: Contents of SKILL.md (injected into system prompt)
        plugin_data: Raw plugin.json data
    """

    id: str = ""
    model: str = ""
    squad: str = ""
    role: str = ""
    capabilities: list[str] = field(default_factory=list)
    skill_md: str = ""
    plugin_data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_directory(cls, path: Path) -> WorkerIdentity:
        """Load worker identity from a directory containing plugin.json + SKILL.md."""
        plugin_path = path / "plugin.json"
        skill_path = path / "SKILL.md"

        plugin_data: dict[str, Any] = {}
        if plugin_path.exists():
            with open(plugin_path) as f:
                plugin_data = json.load(f)

        skill_md = ""
        if skill_path.exists():
            skill_md = skill_path.read_text()

        return cls(
            id=plugin_data.get("id", path.name),
            model=plugin_data.get("model", ""),
            squad=plugin_data.get("squad", ""),
            role=plugin_data.get("role", ""),
            capabilities=plugin_data.get("capabilities", []),
            skill_md=skill_md,
            plugin_data=plugin_data,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkerIdentity:
        """Create identity from a dictionary (useful for programmatic creation)."""
        return cls(
            id=data.get("id", ""),
            model=data.get("model", ""),
            squad=data.get("squad", ""),
            role=data.get("role", ""),
            capabilities=data.get("capabilities", []),
            skill_md=data.get("skill_md", ""),
            plugin_data=data,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "model": self.model,
            "squad": self.squad,
            "role": self.role,
            "capabilities": self.capabilities,
        }
