"""
WorkerRegistry — Hire, fire, discover, and hot-plug workers.

Manages the lifecycle of all workers in the office.
Workers can be registered from:
1. Worker directories (plugin.json + SKILL.md + optional worker.py)
2. Programmatic registration
3. TOML configuration
4. Entry points from pip-installed packages
5. Runtime hot-plug (add workers after initialization)

Plug-and-play: Drop a folder → it's discovered → it works.
"""

from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Any, Type

from kantorku.worker.base import BaseWorker
from kantorku.worker.identity import WorkerIdentity
from kantorku.events.bus import EventBus
from kantorku.providers.router import ProviderRouter

logger = logging.getLogger(__name__)

# Built-in worker class mapping
BUILTIN_WORKERS: dict[str, str] = {
    "coder_frontend": "kantorku.workers.coder_frontend.CoderFrontend",
    "coder_backend": "kantorku.workers.coder_backend.CoderBackend",
    "coder_wiring": "kantorku.workers.coder_wiring.CoderWiring",
    "verifier_designer": "kantorku.workers.verifier_designer.VerifierDesigner",
    "verifier_engineer": "kantorku.workers.verifier_engineer.VerifierEngineer",
    "debugger": "kantorku.workers.debugger.Debugger",
    "scout": "kantorku.workers.scout.Scout",
    "auditor": "kantorku.workers.auditor.Auditor",
    "scribe": "kantorku.workers.scribe.Scribe",
    "summarizer": "kantorku.workers.summarizer.Summarizer",
    "sentinel": "kantorku.workers.sentinel.Sentinel",
    "intake": "kantorku.workers.intake_worker.IntakeWorker",
    "narrator": "kantorku.workers.narrator.Narrator",
}


class WorkerRegistry:
    """
    Registry of all workers in the kantorku office.

    Supports plug-and-play worker discovery and registration:

    Usage:
        registry = WorkerRegistry(router=router, bus=bus)

        # Auto-discover from directories
        registry.discover_workers(Path("workers/"))
        registry.discover_workers_multi([
            Path("kantorku/workers/"),   # built-in
            Path("workers/"),            # project-level
            Path("/custom/workers/"),    # custom
        ])

        # Hot-plug at runtime
        registry.hot_plug(Path("workers/my_new_worker/"))

        # Programmatic
        registry.register_worker_class("my_worker", MyWorkerClass)

        # Hire and use
        worker = registry.hire("coder_backend")
        result = await worker.execute(task)
    """

    def __init__(self, router: ProviderRouter, bus: EventBus) -> None:
        self.router = router
        self.bus = bus
        self._identities: dict[str, WorkerIdentity] = {}
        self._instances: dict[str, BaseWorker] = {}
        self._worker_classes: dict[str, Type[BaseWorker]] = {}
        self._discovered_dirs: list[Path] = []  # Track scanned directories

    # ─────────────────────────────────────────────────
    #  Registration
    # ─────────────────────────────────────────────────

    def register_identity(self, identity: WorkerIdentity) -> None:
        """Register a worker identity (without instantiating)."""
        # Validate first
        errors = identity.validate()
        if errors:
            raise ValueError(
                f"Invalid worker identity '{identity.id}': {'; '.join(errors)}"
            )

        # Check for duplicate
        if identity.id in self._identities:
            existing = self._identities[identity.id]
            logger.info(
                f"Worker '{identity.id}' already registered from "
                f"'{existing.source_dir}', replacing with '{identity.source_dir}'"
            )

        self._identities[identity.id] = identity

        # Try to auto-resolve the worker class from the identity
        cls = identity.resolve_worker_class()
        if cls is not None:
            self._worker_classes[identity.id] = cls
            logger.debug(f"Auto-resolved class for '{identity.id}': {cls}")

    def register_worker_class(self, worker_id: str, cls: Type[BaseWorker]) -> None:
        """Register a custom worker class for a worker ID."""
        if not issubclass(cls, BaseWorker):
            raise TypeError(
                f"Worker class must be a subclass of BaseWorker, got {cls}"
            )
        self._worker_classes[worker_id] = cls

    # ─────────────────────────────────────────────────
    #  Discovery
    # ─────────────────────────────────────────────────

    def discover_workers(self, workers_dir: Path) -> list[str]:
        """
        Discover workers from a directory structure.
        Each subdirectory should contain plugin.json and optionally SKILL.md.

        Directory structure:
            workers/
            ├── coder_frontend/
            │   ├── plugin.json   (required)
            │   ├── SKILL.md      (optional)
            │   └── worker.py     (optional, custom BaseWorker subclass)
            ├── my_custom_worker/
            │   ├── plugin.json
            │   ├── SKILL.md
            │   └── worker.py
            └── simple_worker/
                ├── plugin.json   (uses BaseWorker with SKILL.md prompt)
                └── SKILL.md
        """
        discovered = []
        workers_dir = Path(workers_dir).resolve()

        if not workers_dir.exists():
            logger.debug(f"Workers directory does not exist: {workers_dir}")
            return discovered

        if workers_dir in self._discovered_dirs:
            logger.debug(f"Already scanned: {workers_dir}")
            return discovered

        for subdir in sorted(workers_dir.iterdir()):
            if not subdir.is_dir():
                continue
            if subdir.name.startswith("_") or subdir.name.startswith("."):
                continue  # Skip __pycache__, .git, etc.
            if not (subdir / "plugin.json").exists():
                continue  # No plugin.json = not a worker directory

            try:
                identity = WorkerIdentity.from_directory(subdir)
                self.register_identity(identity)
                discovered.append(identity.id)
                logger.info(f"Discovered worker: {identity.id} from {subdir}")
            except Exception as e:
                logger.warning(f"Failed to load worker from {subdir}: {e}")

        self._discovered_dirs.append(workers_dir)
        return discovered

    def discover_workers_multi(self, directories: list[Path]) -> list[str]:
        """
        Discover workers from multiple directories.

        Later directories override earlier ones if there are ID conflicts.
        This allows project-level workers to override built-in workers.

        Args:
            directories: List of directory paths to scan

        Returns:
            List of all discovered worker IDs
        """
        all_discovered = []
        for d in directories:
            found = self.discover_workers(d)
            all_discovered.extend(found)
        return all_discovered

    def discover_from_entry_points(self) -> list[str]:
        """
        Discover workers from pip-installed packages via entry points.

        Packages can register workers by adding to their pyproject.toml:
            [project.entry-points."kantorku.workers"]
            my_worker = "my_package.workers:MyWorker"

        Returns:
            List of discovered worker IDs
        """
        discovered = []
        try:
            # Python 3.12+ uses importlib.metadata
            from importlib.metadata import entry_points

            eps = entry_points()
            # Python 3.12+ returns a SelectableGroups, 3.9 returns dict
            if hasattr(eps, "select"):
                worker_eps = eps.select(group="kantorku.workers")
            else:
                worker_eps = eps.get("kantorku.workers", [])

            for ep in worker_eps:
                try:
                    cls = ep.load()
                    if issubclass(cls, BaseWorker):
                        worker_id = ep.name
                        identity = WorkerIdentity.from_dict({
                            "id": worker_id,
                            "class_path": f"{ep.value}",
                        })
                        self.register_identity(identity)
                        self.register_worker_class(worker_id, cls)
                        discovered.append(worker_id)
                        logger.info(
                            f"Discovered worker from entry point: {worker_id} "
                            f"({ep.value})"
                        )
                except Exception as e:
                    logger.warning(
                        f"Failed to load entry point worker '{ep.name}': {e}"
                    )
        except ImportError:
            logger.debug("importlib.metadata not available, skipping entry points")

        return discovered

    def discover_from_config(self, workers_config: dict[str, Any]) -> list[str]:
        """
        Register workers from TOML config sections.

        Args:
            workers_config: Dict of worker configs keyed by worker ID
                           e.g. {"coder_frontend": {"model": "..."}, ...}

        Returns:
            List of registered worker IDs
        """
        registered = []
        for worker_id, config in workers_config.items():
            identity = WorkerIdentity.from_dict({
                "id": worker_id,
                "model": config.get("model", ""),
                "squad": config.get("squad", self._infer_squad(worker_id)),
                "role": config.get("role", worker_id.replace("_", " ").title()),
                "capabilities": config.get("capabilities", []),
                "skill_md": config.get("skill_md", ""),
                "class_path": config.get("class_path", ""),
            })
            self.register_identity(identity)
            registered.append(worker_id)

        return registered

    # Alias for backwards compatibility
    register_from_config = discover_from_config

    def _infer_squad(self, worker_id: str) -> str:
        """Infer squad from worker ID naming convention."""
        if any(x in worker_id for x in ["coder", "frontend", "backend", "wiring"]):
            return "coding"
        if any(x in worker_id for x in ["verifier", "judge"]):
            return "verification"
        if any(x in worker_id for x in ["intake", "narrator", "translat", "gatekeeper", "storyteller"]):
            return "translation"
        return "support"

    # ─────────────────────────────────────────────────
    #  Hot-Plug (Runtime Worker Addition)
    # ─────────────────────────────────────────────────

    def hot_plug(
        self,
        path: Path,
        model: str = "",
        squad: str = "",
        role: str = "",
    ) -> BaseWorker:
        """
        Hot-plug a worker at runtime from a directory.

        This is the core plug-and-play method. Drop a folder with
        plugin.json (and optionally SKILL.md + worker.py), call this,
        and the worker is immediately available.

        Args:
            path: Path to the worker directory
            model: Override model (if not set in plugin.json)
            squad: Override squad (if not set in plugin.json)
            role: Override role (if not set in plugin.json)

        Returns:
            The instantiated worker, ready to use

        Raises:
            FileNotFoundError: If path or plugin.json doesn't exist
            ValueError: If the worker identity is invalid
        """
        path = Path(path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Worker directory not found: {path}")
        if not (path / "plugin.json").exists():
            raise FileNotFoundError(
                f"No plugin.json found in {path}. "
                f"A worker directory must contain plugin.json."
            )

        identity = WorkerIdentity.from_directory(path)

        # Apply overrides
        if model:
            identity.model = model
        if squad:
            identity.squad = squad
        if role:
            identity.role = role

        self.register_identity(identity)
        logger.info(
            f"Hot-plugged worker: {identity.id} "
            f"(model={identity.model}, squad={identity.squad})"
        )

        # Fire existing instance if any
        if identity.id in self._instances:
            del self._instances[identity.id]

        return self.hire(identity.id)

    def hot_plug_class(
        self,
        worker_id: str,
        cls: Type[BaseWorker],
        model: str = "",
        squad: str = "",
        role: str = "",
        skill_md: str = "",
    ) -> BaseWorker:
        """
        Hot-plug a worker from a class at runtime.

        Args:
            worker_id: Unique worker identifier
            cls: BaseWorker subclass
            model: LLM model assignment
            squad: Squad membership
            role: Role description
            skill_md: Skill description (injected into system prompt)

        Returns:
            The instantiated worker, ready to use
        """
        identity = WorkerIdentity.from_dict({
            "id": worker_id,
            "model": model,
            "squad": squad,
            "role": role,
            "skill_md": skill_md,
        })
        self.register_identity(identity)
        self.register_worker_class(worker_id, cls)

        # Fire existing instance if any
        if worker_id in self._instances:
            del self._instances[worker_id]

        return self.hire(worker_id)

    # ─────────────────────────────────────────────────
    #  Hire / Fire
    # ─────────────────────────────────────────────────

    def hire(self, worker_id: str) -> BaseWorker:
        """
        Instantiate and return a worker by ID.
        Caches instances — hiring the same worker returns the same object.

        Resolution chain:
        1. Return cached instance if exists
        2. Look up identity → fail if not found
        3. Try _worker_classes[worker_id] (explicit registration)
        4. Try identity.resolve_worker_class() (auto-detect from directory)
        5. Try _try_load_builtin() (built-in Python classes)
        6. Fallback to BaseWorker (with handle() raising NotImplementedError)
        """
        if worker_id in self._instances:
            return self._instances[worker_id]

        identity = self._identities.get(worker_id)
        if not identity:
            raise ValueError(
                f"Worker '{worker_id}' not found. "
                f"Available: {list(self._identities.keys())}"
            )

        # Try custom class first
        cls = self._worker_classes.get(worker_id)

        # Then try auto-resolving from identity
        if cls is None:
            cls = identity.resolve_worker_class()

        # Then try built-in
        if cls is None:
            cls = self._try_load_builtin(worker_id)

        # Fallback to BaseWorker
        if cls is None:
            cls = BaseWorker
            logger.warning(
                f"No custom class found for worker '{worker_id}', "
                f"using BaseWorker (handle() will raise NotImplementedError "
                f"unless SKILL.md provides enough prompt guidance). "
                f"Add a worker.py file to define custom behavior."
            )

        worker = cls(identity=identity, router=self.router, bus=self.bus)
        self._instances[worker_id] = worker
        return worker

    def _try_load_builtin(self, worker_id: str) -> Type[BaseWorker] | None:
        """Try to load a built-in worker class by its module path."""
        path = BUILTIN_WORKERS.get(worker_id)
        if path is None:
            return None

        try:
            module_path, class_name = path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            return getattr(module, class_name)
        except (ImportError, AttributeError):
            return None

    def fire(self, worker_id: str) -> None:
        """Remove a worker from the registry."""
        self._instances.pop(worker_id, None)
        self._identities.pop(worker_id, None)
        self._worker_classes.pop(worker_id, None)

    # ─────────────────────────────────────────────────
    #  Query
    # ─────────────────────────────────────────────────

    def get(self, worker_id: str) -> BaseWorker | None:
        """Get an existing worker instance (or None)."""
        return self._instances.get(worker_id)

    def get_identity(self, worker_id: str) -> WorkerIdentity | None:
        """Get a worker's identity."""
        return self._identities.get(worker_id)

    def list_workers(self) -> list[dict[str, Any]]:
        """List all registered workers with their status."""
        result = []
        for wid, identity in self._identities.items():
            instance = self._instances.get(wid)
            result.append({
                "id": wid,
                "model": identity.model,
                "category": identity.category,
                "subcategory": identity.subcategory,
                "display_name": identity.display_name,
                "squad": identity.squad,
                "role": identity.role,
                "capabilities": identity.capabilities,
                "tags": identity.tags,
                "status": instance.status.value if instance else "unhired",
                "has_custom_class": wid in self._worker_classes or bool(identity.class_path),
                "source_dir": identity.source_dir,
            })
        return result

    def list_by_squad(self, squad: str) -> list[str]:
        """List worker IDs belonging to a specific squad."""
        return [
            wid for wid, identity in self._identities.items()
            if identity.squad == squad
        ]

    def list_by_category(self, category: str) -> list[str]:
        """List worker IDs belonging to a specific category."""
        return [
            wid for wid, identity in self._identities.items()
            if identity.category == category
        ]

    def list_by_subcategory(self, subcategory: str) -> list[str]:
        """List worker IDs belonging to a specific subcategory."""
        return [
            wid for wid, identity in self._identities.items()
            if identity.subcategory == subcategory
        ]

    def validate_worker_dir(self, path: Path) -> list[str]:
        """
        Validate a worker directory structure.
        Returns list of error/warning messages (empty = valid).

        Checks:
        - plugin.json exists and is valid JSON
        - SKILL.md exists (warning if missing)
        - worker.py exists and contains a BaseWorker subclass (warning if not)
        - plugin.json has required fields
        """
        path = Path(path).resolve()
        messages: list[str] = []

        if not path.exists():
            return [f"Directory does not exist: {path}"]
        if not path.is_dir():
            return [f"Not a directory: {path}"]

        # Check plugin.json
        plugin_path = path / "plugin.json"
        if not plugin_path.exists():
            return [f"Missing plugin.json in {path}"]

        try:
            identity = WorkerIdentity.from_directory(path)
            errors = identity.validate()
            messages.extend(errors)
        except Exception as e:
            messages.append(f"Failed to load plugin.json: {e}")
            return messages

        # Check SKILL.md
        skill_path = path / "SKILL.md"
        if not skill_path.exists():
            messages.append(
                f"[WARNING] No SKILL.md found — worker will have no "
                f"system prompt unless provided via code"
            )

        # Check worker.py
        worker_py = path / "worker.py"
        if worker_py.exists():
            try:
                cls = identity.resolve_worker_class()
                if cls is None:
                    messages.append(
                        f"[WARNING] worker.py exists but no BaseWorker "
                        f"subclass found. Define a class inheriting "
                        f"from BaseWorker."
                    )
            except Exception as e:
                messages.append(
                    f"[WARNING] worker.py has errors: {e}"
                )
        else:
            messages.append(
                f"[INFO] No worker.py — will use BaseWorker with SKILL.md prompt. "
                f"Add worker.py for custom behavior."
            )

        return messages

    @property
    def all_worker_ids(self) -> list[str]:
        return list(self._identities.keys())

    @property
    def coding_squad(self) -> list[str]:
        return self.list_by_squad("coding")

    @property
    def verification_squad(self) -> list[str]:
        return self.list_by_squad("verification")

    @property
    def support_squad(self) -> list[str]:
        return self.list_by_squad("support")

    @property
    def translation_squad(self) -> list[str]:
        return self.list_by_squad("translation")

    @property
    def categories(self) -> dict[str, list[str]]:
        """All workers grouped by category."""
        cats: dict[str, list[str]] = {}
        for wid, identity in self._identities.items():
            cat = identity.category or identity.squad or "uncategorized"
            if cat not in cats:
                cats[cat] = []
            cats[cat].append(wid)
        return cats
