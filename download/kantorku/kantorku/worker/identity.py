"""
WorkerIdentity — Worker plugin system.

Each worker is defined by a directory containing:
- plugin.json: Machine-readable metadata (id, model, squad, capabilities, class)
- SKILL.md: Human-readable skill description (injected into LLM prompt)
- worker.py: Optional Python module with custom BaseWorker subclass

Workers are discovered from:
1. kantorku/workers/ (built-in)
2. workers/ in project root (project-level)
3. Any custom directory passed to discover_workers()
4. Entry points from pip-installed packages

Plug-and-play: Drop a folder with plugin.json + SKILL.md and it just works.
              Add worker.py for custom logic. No registration needed.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Type


# Name used for the Python module file inside a worker directory
WORKER_MODULE_FILENAME = "worker.py"

# Name of the class that will be auto-detected inside worker.py
# If not found, falls back to the first BaseWorker subclass
DEFAULT_WORKER_CLASS_NAME = "Worker"


@dataclass
class WorkerIdentity:
    """
    A worker's identity — loaded from plugin.json + SKILL.md + optional worker.py.

    Attributes:
        id: Unique worker identifier (e.g. "coder_backend")
        model: LLM model assignment (e.g. "minimax/minimax-m2-7")
        squad: Squad membership (coding, verification, support, translation)
        role: Human-readable role description
        capabilities: What this worker can do
        skill_md: Contents of SKILL.md (injected into system prompt)
        class_path: Dotted path to worker class (e.g. "my_package.MyWorker")
        source_dir: Directory this identity was loaded from (for auto-discovery)
        plugin_data: Raw plugin.json data
    """

    id: str = ""
    model: str = ""
    squad: str = ""
    role: str = ""
    capabilities: list[str] = field(default_factory=list)
    skill_md: str = ""
    class_path: str = ""
    source_dir: str = ""
    plugin_data: dict[str, Any] = field(default_factory=dict)

    # ---- Transient (not serialized) ----
    _resolved_class: Type | None = field(default=None, repr=False, compare=False)

    @classmethod
    def from_directory(cls, path: Path) -> WorkerIdentity:
        """
        Load worker identity from a directory.

        Expected structure:
            my_worker/
            ├── plugin.json    (required)
            ├── SKILL.md       (optional, injected as system prompt)
            └── worker.py      (optional, custom BaseWorker subclass)

        The plugin.json "class" field can specify:
        - A dotted path: "my_package.my_module.MyClass"
        - A local module: "worker.py:MyWorker" or just "worker.MyWorker"
        - Empty string: auto-detect worker.py in same directory
        """
        path = Path(path).resolve()
        plugin_path = path / "plugin.json"
        skill_path = path / "SKILL.md"
        worker_py_path = path / WORKER_MODULE_FILENAME

        # Load plugin.json
        plugin_data: dict[str, Any] = {}
        if plugin_path.exists():
            with open(plugin_path, encoding="utf-8") as f:
                plugin_data = json.load(f)

        # Load SKILL.md
        skill_md = ""
        if skill_path.exists():
            skill_md = skill_path.read_text(encoding="utf-8")

        # Determine class_path
        class_path = plugin_data.get("class", "")

        # Auto-detect: if no class_path and worker.py exists, mark for auto-load
        if not class_path and worker_py_path.exists():
            class_path = f"_auto:{worker_py_path}"

        return cls(
            id=plugin_data.get("id", path.name),
            model=plugin_data.get("model", ""),
            squad=plugin_data.get("squad", ""),
            role=plugin_data.get("role", ""),
            capabilities=plugin_data.get("capabilities", []),
            skill_md=skill_md,
            class_path=class_path,
            source_dir=str(path),
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
            class_path=data.get("class_path", ""),
            source_dir=data.get("source_dir", ""),
            plugin_data=data,
        )

    def validate(self) -> list[str]:
        """
        Validate this identity. Returns list of error messages (empty = valid).

        Checks:
        - id is present and valid format
        - model has provider/model format (if set)
        - squad is a known squad or custom
        - class_path is resolvable (if set)
        - source_dir exists (if set)
        """
        errors: list[str] = []

        if not self.id:
            errors.append("Worker id is required")
        elif not self.id.replace("_", "").isalnum():
            errors.append(
                f"Worker id '{self.id}' must be alphanumeric + underscores only"
            )

        if self.model and "/" not in self.model:
            errors.append(
                f"Model must be 'provider/model' format, got: {self.model}"
            )

        if self.class_path and self.class_path.startswith("_auto:"):
            # Check the worker.py file exists
            py_path = Path(self.class_path[6:])
            if not py_path.exists():
                errors.append(f"Auto-detected worker.py not found: {py_path}")
        elif self.class_path and "." not in self.class_path:
            errors.append(
                f"class_path must be dotted (e.g. 'pkg.module.Class'), got: {self.class_path}"
            )

        if self.source_dir and not Path(self.source_dir).exists():
            errors.append(f"Source directory does not exist: {self.source_dir}")

        return errors

    def resolve_worker_class(self) -> Type | None:
        """
        Resolve and return the worker class for this identity.

        Resolution order:
        1. Already resolved (cached in _resolved_class)
        2. Auto-detected worker.py in source_dir
        3. Dotted class_path import (e.g. "my_package.MyWorker")

        Returns None if no custom class can be found.
        """
        if self._resolved_class is not None:
            return self._resolved_class

        from kantorku.worker.base import BaseWorker

        # Case 1: Auto-detected worker.py
        if self.class_path.startswith("_auto:"):
            py_path = Path(self.class_path[6:])
            return self._load_from_file(py_path, BaseWorker)

        # Case 2: Dotted class path
        if self.class_path and "." in self.class_path:
            return self._load_from_dotted_path(self.class_path, BaseWorker)

        # Case 3: source_dir has worker.py but class_path wasn't set
        if self.source_dir:
            py_path = Path(self.source_dir) / WORKER_MODULE_FILENAME
            if py_path.exists():
                return self._load_from_file(py_path, BaseWorker)

        return None

    def _load_from_file(
        self, py_path: Path, base_class: Type
    ) -> Type | None:
        """
        Dynamically load a Python module from file path and find
        the first subclass of base_class.
        """
        if not py_path.exists():
            return None

        try:
            module_name = f"kantorku_worker_{self.id}"
            spec = importlib.util.spec_from_file_location(module_name, py_path)
            if spec is None or spec.loader is None:
                return None

            module = importlib.util.module_from_spec(spec)
            # Add to sys.modules so relative imports work
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Strategy 1: Look for class named DEFAULT_WORKER_CLASS_NAME
            candidate = getattr(module, DEFAULT_WORKER_CLASS_NAME, None)
            if candidate and isinstance(candidate, type) and issubclass(candidate, base_class):
                self._resolved_class = candidate
                return candidate

            # Strategy 2: Find first BaseWorker subclass in the module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, base_class)
                    and attr is not base_class
                ):
                    self._resolved_class = attr
                    return attr

        except Exception:
            pass

        return None

    def _load_from_dotted_path(
        self, class_path: str, base_class: Type
    ) -> Type | None:
        """Load a class from a dotted module path (e.g. 'pkg.module.Class')."""
        try:
            module_path, class_name = class_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name, None)
            if cls and isinstance(cls, type) and issubclass(cls, base_class):
                self._resolved_class = cls
                return cls
        except (ImportError, AttributeError, ValueError):
            pass
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "model": self.model,
            "squad": self.squad,
            "role": self.role,
            "capabilities": self.capabilities,
            "class_path": self.class_path,
            "source_dir": self.source_dir,
        }

    def to_plugin_json(self) -> dict[str, Any]:
        """Serialize back to plugin.json format."""
        result = dict(self.plugin_data) if self.plugin_data else {}
        result.update({
            "id": self.id,
            "model": self.model,
            "squad": self.squad,
            "role": self.role,
            "capabilities": self.capabilities,
        })
        if self.class_path and not self.class_path.startswith("_auto:"):
            result["class"] = self.class_path
        return result
