"""
WorkerIdentity — Worker plugin system with API support.

Each worker is defined by a directory containing:
- plugin.json: Machine-readable metadata (id, api, squad, capabilities, class)
- SKILL.md: Human-readable skill description (injected into LLM prompt)
- worker.py: Optional Python module with custom BaseWorker subclass

Workers are discovered from:
1. kantorku/workers/ (built-in)
2. workers/ in project root (project-level)
3. Any custom directory passed to discover_workers()
4. Entry points from pip-installed packages

Each worker has its OWN API configuration — not just a model string.
Example:
    verifier_designer uses Gemini API (google/gemini-2.5-pro)
    debugger uses Grok API (xai/grok-3)
    coder_wiring uses Codex API (openai/codex-5.3)

Plug-and-play: Drop a folder with plugin.json + SKILL.md and it just works.
              Add worker.py for custom logic. No registration needed.
"""

from __future__ import annotations

import importlib.util
import json
import os
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
class WorkerAPI:
    """
    API configuration for a worker.

    Each worker has its OWN API — separate from the global provider config.
    This is what makes kantorku workers truly independent agents:
    they can call different AI providers, different models, with different keys.

    Example:
        # Design worker uses Gemini
        api = WorkerAPI(provider="google", model="gemini-2.5-pro",
                        api_key="${GOOGLE_API_KEY}")

        # Debug worker uses Grok
        api = WorkerAPI(provider="xai", model="grok-3",
                        api_key="${XAI_API_KEY}",
                        base_url="https://api.x.ai/v1")

        # Wiring worker uses OpenAI Codex
        api = WorkerAPI(provider="openai", model="codex-5.3",
                        api_key="${OPENAI_API_KEY}")

    Attributes:
        provider: AI provider name (anthropic, google, openai, xai, deepseek, minimax, ollama, etc.)
        model: Model name WITHOUT provider prefix (e.g. "gemini-2.5-pro", not "google/gemini-2.5-pro")
        api_key: API key (supports ${ENV_VAR} pattern for env var resolution)
        base_url: Optional custom base URL (for self-hosted or proxy APIs)
        extra: Additional provider-specific config (temperature, max_tokens, etc.)
    """
    provider: str = ""
    model: str = ""
    api_key: str = ""
    base_url: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkerAPI:
        """Create WorkerAPI from a dictionary (e.g. plugin.json "api" section)."""
        return cls(
            provider=data.get("provider", ""),
            model=data.get("model", ""),
            api_key=data.get("api_key", ""),
            base_url=data.get("base_url", ""),
            extra=data.get("extra", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "provider": self.provider,
            "model": self.model,
        }
        if self.api_key:
            result["api_key"] = self.api_key
        if self.base_url:
            result["base_url"] = self.base_url
        if self.extra:
            result["extra"] = self.extra
        return result

    def resolve_env_vars(self) -> WorkerAPI:
        """
        Resolve ${ENV_VAR} patterns in api_key and base_url.
        Returns a new WorkerAPI with resolved values.
        """
        resolved_key = self._resolve_env(self.api_key)
        resolved_url = self._resolve_env(self.base_url)

        # Also resolve in extra
        resolved_extra = {}
        for k, v in self.extra.items():
            if isinstance(v, str):
                resolved_extra[k] = self._resolve_env(v)
            else:
                resolved_extra[k] = v

        return WorkerAPI(
            provider=self.provider,
            model=self.model,
            api_key=resolved_key,
            base_url=resolved_url,
            extra=resolved_extra,
        )

    def _resolve_env(self, value: str) -> str:
        """Resolve ${ENV_VAR} patterns in a string."""
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            return os.environ.get(env_var, "")
        return value

    @property
    def full_model(self) -> str:
        """Get the full 'provider/model' string."""
        if self.provider and self.model:
            return f"{self.provider}/{self.model}"
        return self.model or ""

    def validate(self) -> list[str]:
        """Validate API config. Returns list of error messages."""
        errors: list[str] = []
        if not self.provider:
            errors.append("API provider is required")
        if not self.model:
            errors.append("API model is required")
        if self.api_key and self.api_key.startswith("${") and self.api_key.endswith("}"):
            env_var = self.api_key[2:-1]
            if not os.environ.get(env_var):
                errors.append(f"API key env var ${env_var} is not set")
        return errors


@dataclass
class WorkerIdentity:
    """
    A worker's identity — loaded from plugin.json + SKILL.md + optional worker.py.

    Each worker is a FULLY INDEPENDENT AGENT with its own:
    - API configuration (provider, model, api_key, base_url)
    - Skill description (SKILL.md → injected into system prompt)
    - Custom logic (worker.py → BaseWorker subclass)
    - Squad membership and role

    Attributes:
        id: Unique worker identifier (e.g. "verifier_designer")
        api: Worker's OWN API configuration (separate from global providers)
        squad: Squad membership (coding, verification, support, translation)
        role: Human-readable role description
        capabilities: What this worker can do
        skill_md: Contents of SKILL.md (injected into system prompt)
        class_path: Dotted path to worker class (e.g. "my_package.MyWorker")
        source_dir: Directory this identity was loaded from
        plugin_data: Raw plugin.json data
    """

    id: str = ""
    api: WorkerAPI = field(default_factory=WorkerAPI)
    squad: str = ""
    role: str = ""
    capabilities: list[str] = field(default_factory=list)
    skill_md: str = ""
    class_path: str = ""
    source_dir: str = ""
    plugin_data: dict[str, Any] = field(default_factory=dict)

    # ---- Transient (not serialized) ----
    _resolved_class: Type | None = field(default=None, repr=False, compare=False)

    def __init__(self, model: str = "", **kwargs: Any) -> None:
        """
        Create a WorkerIdentity.

        Supports backwards compatibility with 'model' kwarg:
            WorkerIdentity(id="x", model="anthropic/claude-opus-4-6")
        which gets parsed into self.api automatically.
        """
        # Extract api from kwargs if present
        api = kwargs.pop("api", WorkerAPI())

        # If model is provided and api is empty, parse model into api
        if model and not api.provider and not api.model:
            if "/" in model:
                api.provider, api.model = model.split("/", 1)
            else:
                api.model = model

        # Set all fields
        self.id = kwargs.get("id", "")
        self.api = api
        self.squad = kwargs.get("squad", "")
        self.role = kwargs.get("role", "")
        self.capabilities = kwargs.get("capabilities", [])
        self.skill_md = kwargs.get("skill_md", "")
        self.class_path = kwargs.get("class_path", "")
        self.source_dir = kwargs.get("source_dir", "")
        self.plugin_data = kwargs.get("plugin_data", {})
        self._resolved_class = None

    @property
    def model(self) -> str:
        """Full model string (provider/model). Backwards compatible."""
        return self.api.full_model

    @model.setter
    def model(self, value: str) -> None:
        """Set model from 'provider/model' string."""
        if "/" in value:
            self.api.provider, self.api.model = value.split("/", 1)
        else:
            self.api.model = value

    @classmethod
    def from_directory(cls, path: Path) -> WorkerIdentity:
        """
        Load worker identity from a directory.

        Expected structure:
            my_worker/
            ├── plugin.json    (required)
            ├── SKILL.md       (optional, injected as system prompt)
            └── worker.py      (optional, custom BaseWorker subclass)

        plugin.json "api" section (recommended):
            {
              "id": "verifier_designer",
              "api": {
                "provider": "google",
                "model": "gemini-2.5-pro",
                "api_key": "${GOOGLE_API_KEY}"
              },
              "squad": "verification",
              "role": "Visual/UX judge"
            }

        Legacy plugin.json (still supported):
            {
              "id": "verifier_designer",
              "model": "google/gemini-2.5-pro",
              "squad": "verification"
            }
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

        # Build API config — prefer "api" section, fallback to "model" string
        api_data = plugin_data.get("api", {})
        if api_data:
            api = WorkerAPI.from_dict(api_data)
        elif "model" in plugin_data:
            # Legacy: parse "provider/model" string
            model_str = plugin_data.get("model", "")
            if "/" in model_str:
                provider, model = model_str.split("/", 1)
                api = WorkerAPI(provider=provider, model=model)
            else:
                api = WorkerAPI(model=model_str)
        else:
            api = WorkerAPI()

        # Also check for api_key at top level (shorthand)
        if not api.api_key and "api_key" in plugin_data:
            api.api_key = plugin_data["api_key"]

        # Also check for base_url at top level (shorthand)
        if not api.base_url and "base_url" in plugin_data:
            api.base_url = plugin_data["base_url"]

        return cls(
            id=plugin_data.get("id", path.name),
            api=api,
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
        # Build API from dict
        api_data = data.get("api", {})
        if api_data:
            api = WorkerAPI.from_dict(api_data)
        elif "model" in data:
            model_str = data.get("model", "")
            if "/" in model_str:
                provider, model = model_str.split("/", 1)
                api = WorkerAPI(provider=provider, model=model)
            else:
                api = WorkerAPI(model=model_str)
        else:
            api = WorkerAPI()

        if not api.api_key and "api_key" in data:
            api.api_key = data["api_key"]
        if not api.base_url and "base_url" in data:
            api.base_url = data["base_url"]

        return cls(
            id=data.get("id", ""),
            api=api,
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

        NOTE: API key env vars are NOT checked during discovery.
        They are only resolved at runtime when the worker is actually hired.
        """
        errors: list[str] = []

        if not self.id:
            errors.append("Worker id is required")
        elif not self.id.replace("_", "").isalnum():
            errors.append(
                f"Worker id '{self.id}' must be alphanumeric + underscores only"
            )

        # Only validate API structure, NOT env var presence
        # (env vars are checked at runtime, not discovery time)

        if self.class_path and self.class_path.startswith("_auto:"):
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
        """Dynamically load a Python module from file path and find a BaseWorker subclass."""
        if not py_path.exists():
            return None

        try:
            module_name = f"kantorku_worker_{self.id}"
            spec = importlib.util.spec_from_file_location(module_name, py_path)
            if spec is None or spec.loader is None:
                return None

            module = importlib.util.module_from_spec(spec)
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
            "api": self.api.to_dict(),
            "model": self.api.full_model,  # Backwards compat
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
            "api": self.api.to_dict(),
            "squad": self.squad,
            "role": self.role,
            "capabilities": self.capabilities,
        })
        if self.class_path and not self.class_path.startswith("_auto:"):
            result["class"] = self.class_path
        return result
