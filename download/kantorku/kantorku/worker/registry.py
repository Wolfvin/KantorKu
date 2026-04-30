"""
WorkerRegistry — Hire, fire, and discover workers.

Manages the lifecycle of all workers in the office.
Workers can be registered from:
1. Worker directories (plugin.json + SKILL.md)
2. Programmatic registration
3. TOML configuration
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Type

from kantorku.worker.base import BaseWorker
from kantorku.worker.identity import WorkerIdentity
from kantorku.events.bus import EventBus
from kantorku.providers.router import ProviderRouter


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

    Usage:
        registry = WorkerRegistry(router=router, bus=bus)
        registry.discover_workers(Path("workers/"))
        registry.register_from_config(config)

        worker = registry.hire("coder_backend")
        result = await worker.execute(task)
    """

    def __init__(self, router: ProviderRouter, bus: EventBus) -> None:
        self.router = router
        self.bus = bus
        self._identities: dict[str, WorkerIdentity] = {}
        self._instances: dict[str, BaseWorker] = {}
        self._worker_classes: dict[str, Type[BaseWorker]] = {}

    def register_identity(self, identity: WorkerIdentity) -> None:
        """Register a worker identity (without instantiating)."""
        self._identities[identity.id] = identity

    def register_worker_class(self, worker_id: str, cls: Type[BaseWorker]) -> None:
        """Register a custom worker class for a worker ID."""
        self._worker_classes[worker_id] = cls

    def discover_workers(self, workers_dir: Path) -> list[str]:
        """
        Discover workers from a directory structure.
        Each subdirectory should contain plugin.json and optionally SKILL.md.
        """
        discovered = []
        if not workers_dir.exists():
            return discovered

        for subdir in sorted(workers_dir.iterdir()):
            if subdir.is_dir() and (subdir / "plugin.json").exists():
                identity = WorkerIdentity.from_directory(subdir)
                self.register_identity(identity)
                discovered.append(identity.id)

        return discovered

    def register_from_config(self, workers_config: dict[str, Any]) -> list[str]:
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
            })
            self.register_identity(identity)
            registered.append(worker_id)

        return registered

    def _infer_squad(self, worker_id: str) -> str:
        """Infer squad from worker ID naming convention."""
        if any(x in worker_id for x in ["coder"]):
            return "coding"
        if any(x in worker_id for x in ["verifier"]):
            return "verification"
        return "support"

    def hire(self, worker_id: str) -> BaseWorker:
        """
        Instantiate and return a worker by ID.
        Caches instances — hiring the same worker returns the same object.
        """
        if worker_id in self._instances:
            return self._instances[worker_id]

        identity = self._identities.get(worker_id)
        if not identity:
            raise ValueError(
                f"Worker '{worker_id}' not found. "
                f"Available: {list(self._identities.keys())}"
            )

        # Try custom class first, then built-in, then BaseWorker
        cls = self._worker_classes.get(worker_id)
        if cls is None:
            cls = self._try_load_builtin(worker_id)
        if cls is None:
            cls = BaseWorker

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
                "squad": identity.squad,
                "role": identity.role,
                "status": instance.status.value if instance else "unhired",
            })
        return result

    def list_by_squad(self, squad: str) -> list[str]:
        """List worker IDs belonging to a specific squad."""
        return [
            wid for wid, identity in self._identities.items()
            if identity.squad == squad
        ]

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
