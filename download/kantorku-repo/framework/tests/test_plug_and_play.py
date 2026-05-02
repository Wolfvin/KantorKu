"""
Tests for the plug-and-play worker system.

Covers: WorkerIdentity, WorkerRegistry, WorkerGenerator, Office.hot_plug_worker
"""

import asyncio
import json
import tempfile
from pathlib import Path

import pytest

from kantorku import Office, BaseWorker, WorkerIdentity, WorkerRegistry, WorkerGenerator, WorkerAPI
from kantorku.worker.base import Task, TaskResult, WorkerStatus
from kantorku.worker.identity import WORKER_MODULE_FILENAME
from kantorku.events.bus import EventBus
from kantorku.providers.router import ProviderRouter
from kantorku.hooks import HookType, Hooks


# ─────────────────────────────────────────────────
#  WorkerIdentity tests
# ─────────────────────────────────────────────────

class TestWorkerIdentity:
    """Test the upgraded WorkerIdentity with auto-discovery."""

    def test_from_directory_with_skill_md(self, tmp_path):
        """WorkerIdentity loads plugin.json + SKILL.md."""
        worker_dir = tmp_path / "my_worker"
        worker_dir.mkdir()

        plugin = {"id": "my_worker", "model": "ollama/llama3", "squad": "support", "role": "Helper"}
        (worker_dir / "plugin.json").write_text(json.dumps(plugin))
        (worker_dir / "SKILL.md").write_text("# My Worker\nYou are a helpful assistant.")

        identity = WorkerIdentity.from_directory(worker_dir)

        assert identity.id == "my_worker"
        assert identity.model == "ollama/llama3"
        assert identity.squad == "support"
        assert identity.role == "Helper"
        assert "helpful assistant" in identity.skill_md
        assert identity.source_dir == str(worker_dir.resolve())

    def test_from_directory_with_worker_py(self, tmp_path):
        """WorkerIdentity auto-detects worker.py and resolves class."""
        worker_dir = tmp_path / "smart_bot"
        worker_dir.mkdir()

        plugin = {"id": "smart_bot", "model": "ollama/llama3"}
        (worker_dir / "plugin.json").write_text(json.dumps(plugin))
        (worker_dir / "SKILL.md").write_text("You are smart.")
        (worker_dir / "worker.py").write_text('''
from kantorku.worker.base import BaseWorker, Task, TaskResult

class Worker(BaseWorker):
    async def handle(self, task):
        return TaskResult(task_id=task.id, status="done", output="smart!")
''')

        identity = WorkerIdentity.from_directory(worker_dir)

        assert identity.id == "smart_bot"
        assert identity.class_path.startswith("_auto:")
        assert "worker.py" in identity.class_path

        # Resolve the class
        cls = identity.resolve_worker_class()
        assert cls is not None
        assert issubclass(cls, BaseWorker)
        assert cls.__name__ == "Worker"

    def test_from_directory_without_plugin_json(self, tmp_path):
        """WorkerIdentity uses directory name as ID when no plugin.json."""
        worker_dir = tmp_path / "fallback_bot"
        worker_dir.mkdir()
        (worker_dir / "SKILL.md").write_text("Fallback worker")

        identity = WorkerIdentity.from_directory(worker_dir)
        assert identity.id == "fallback_bot"  # Uses directory name
        assert identity.model == ""
        assert identity.skill_md == "Fallback worker"

    def test_validate_valid_identity(self):
        """validate() returns empty list for valid identity."""
        identity = WorkerIdentity(id="my_bot", model="ollama/llama3")
        errors = identity.validate()
        assert errors == []

    def test_validate_invalid_id(self):
        """validate() catches invalid ID format."""
        identity = WorkerIdentity(id="bad bot!", model="ollama/llama3")
        errors = identity.validate()
        assert len(errors) > 0
        assert "alphanumeric" in errors[0]

    def test_validate_invalid_model(self):
        """validate() no longer checks model format at discovery time (env vars may not be set)."""
        identity = WorkerIdentity(id="my_bot", model="just-a-model")
        errors = identity.validate()
        # Model validation is deferred to runtime, so no errors at discovery
        assert len(errors) == 0

    def test_validate_api_structure(self):
        """WorkerAPI.validate() catches missing provider/model."""
        api = WorkerAPI(provider="google", model="", api_key="${GOOGLE_API_KEY}")
        errors = api.validate()
        assert any("model" in e.lower() for e in errors)

    def test_validate_empty_model_ok(self):
        """validate() allows empty model (can be set later via config)."""
        identity = WorkerIdentity(id="my_bot", model="")
        errors = identity.validate()
        assert errors == []

    def test_to_plugin_json(self, tmp_path):
        """to_plugin_json() serializes back to plugin.json format."""
        worker_dir = tmp_path / "json_bot"
        worker_dir.mkdir()
        plugin = {"id": "json_bot", "model": "ollama/llama3", "squad": "support"}
        (worker_dir / "plugin.json").write_text(json.dumps(plugin))
        (worker_dir / "SKILL.md").write_text("JSON worker")

        identity = WorkerIdentity.from_directory(worker_dir)
        result = identity.to_plugin_json()

        assert result["id"] == "json_bot"
        assert result["model"] == "ollama/llama3"
        assert result["squad"] == "support"

    def test_from_dict_with_class_path(self):
        """WorkerIdentity.from_dict supports class_path."""
        identity = WorkerIdentity.from_dict({
            "id": "remote_bot",
            "model": "anthropic/claude-sonnet-4-6",
            "class_path": "my_package.workers.RemoteBot",
        })
        assert identity.class_path == "my_package.workers.RemoteBot"


# ─────────────────────────────────────────────────
#  WorkerRegistry tests
# ─────────────────────────────────────────────────

class TestWorkerRegistry:
    """Test the upgraded WorkerRegistry with plug-and-play."""

    def _make_registry(self):
        return WorkerRegistry(router=ProviderRouter(), bus=EventBus())

    def test_discover_workers(self, tmp_path):
        """discover_workers finds workers in directory."""
        for name in ["bot_a", "bot_b"]:
            d = tmp_path / name
            d.mkdir()
            (d / "plugin.json").write_text(json.dumps({
                "id": name, "model": "ollama/llama3", "squad": "support"
            }))

        registry = self._make_registry()
        found = registry.discover_workers(tmp_path)

        assert "bot_a" in found
        assert "bot_b" in found

    def test_discover_workers_skips_invalid(self, tmp_path):
        """discover_workers skips directories without plugin.json."""
        (tmp_path / "valid").mkdir()
        (tmp_path / "valid" / "plugin.json").write_text('{"id": "valid"}')
        (tmp_path / "invalid").mkdir()  # No plugin.json
        (tmp_path / ".hidden").mkdir()  # Hidden dir
        (tmp_path / "__pycache__").mkdir()  # Python cache

        registry = self._make_registry()
        found = registry.discover_workers(tmp_path)

        assert found == ["valid"]

    def test_discover_workers_multi(self, tmp_path):
        """discover_workers_multi scans multiple directories."""
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        dir_a.mkdir()
        dir_b.mkdir()

        (dir_a / "bot_x").mkdir()
        (dir_a / "bot_x" / "plugin.json").write_text('{"id": "bot_x"}')
        (dir_b / "bot_y").mkdir()
        (dir_b / "bot_y" / "plugin.json").write_text('{"id": "bot_y"}')

        registry = self._make_registry()
        found = registry.discover_workers_multi([dir_a, dir_b])

        assert "bot_x" in found
        assert "bot_y" in found

    def test_hot_plug(self, tmp_path):
        """hot_plug creates a worker from directory at runtime."""
        worker_dir = tmp_path / "hot_bot"
        worker_dir.mkdir()
        (worker_dir / "plugin.json").write_text(json.dumps({
            "id": "hot_bot", "model": "ollama/llama3", "squad": "support"
        }))
        (worker_dir / "SKILL.md").write_text("You are hot.")
        (worker_dir / "worker.py").write_text('''
from kantorku.worker.base import BaseWorker, Task, TaskResult

class Worker(BaseWorker):
    async def handle(self, task):
        return TaskResult(task_id=task.id, status="done", output="hot!")
''')

        registry = self._make_registry()
        worker = registry.hot_plug(worker_dir)

        assert worker.id == "hot_bot"
        assert isinstance(worker, BaseWorker)
        assert worker.__class__.__name__ == "Worker"

    def test_hot_plug_with_overrides(self, tmp_path):
        """hot_plug applies model/squad/role overrides."""
        worker_dir = tmp_path / "override_bot"
        worker_dir.mkdir()
        (worker_dir / "plugin.json").write_text('{"id": "override_bot"}')

        registry = self._make_registry()
        worker = registry.hot_plug(
            worker_dir,
            model="anthropic/claude-sonnet-4-6",
            squad="coding",
            role="Override Specialist",
        )

        assert worker.model == "anthropic/claude-sonnet-4-6"
        assert worker.squad == "coding"
        assert worker.role == "Override Specialist"

    def test_hot_plug_class(self):
        """hot_plug_class registers worker from class."""
        class FastBot(BaseWorker):
            async def handle(self, task):
                return TaskResult(task_id=task.id, status="done", output="fast!")

        registry = self._make_registry()
        worker = registry.hot_plug_class(
            "fast_bot",
            FastBot,
            model="ollama/llama3",
            squad="support",
        )

        assert worker.id == "fast_bot"
        assert isinstance(worker, FastBot)

    def test_validate_worker_dir(self, tmp_path):
        """validate_worker_dir checks worker directory structure."""
        # Invalid: no plugin.json
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        registry = self._make_registry()
        messages = registry.validate_worker_dir(empty_dir)
        assert any("plugin.json" in m for m in messages)

        # Valid: with plugin.json + SKILL.md
        good_dir = tmp_path / "good"
        good_dir.mkdir()
        (good_dir / "plugin.json").write_text('{"id": "good", "model": "ollama/llama3"}')
        (good_dir / "SKILL.md").write_text("Good worker")

        messages = registry.validate_worker_dir(good_dir)
        errors = [m for m in messages if not m.startswith("[")]
        assert errors == []

    def test_discover_from_config(self):
        """discover_from_config registers workers from TOML-like config."""
        registry = self._make_registry()
        registered = registry.discover_from_config({
            "my_coder": {"model": "ollama/llama3", "squad": "coding", "role": "Coder"},
        })

        assert "my_coder" in registered
        identity = registry.get_identity("my_coder")
        assert identity.model == "ollama/llama3"
        assert identity.squad == "coding"

    def test_register_from_config_alias(self):
        """register_from_config is an alias for discover_from_config."""
        registry = self._make_registry()
        result = registry.register_from_config({
            "alias_test": {"model": "ollama/llama3"},
        })
        assert "alias_test" in result

    def test_hire_with_auto_resolved_class(self, tmp_path):
        """hire() auto-resolves worker.py class from directory."""
        worker_dir = tmp_path / "auto_bot"
        worker_dir.mkdir()
        (worker_dir / "plugin.json").write_text('{"id": "auto_bot", "model": "ollama/llama3"}')
        (worker_dir / "worker.py").write_text('''
from kantorku.worker.base import BaseWorker, Task, TaskResult

class Worker(BaseWorker):
    async def handle(self, task):
        return TaskResult(task_id=task.id, status="done", output="auto!")
''')

        registry = self._make_registry()
        registry.discover_workers(tmp_path)
        worker = registry.hire("auto_bot")

        assert worker.__class__.__name__ == "Worker"
        assert isinstance(worker, BaseWorker)

    def test_list_workers_with_source_info(self, tmp_path):
        """list_workers includes source_dir and custom class info."""
        worker_dir = tmp_path / "info_bot"
        worker_dir.mkdir()
        (worker_dir / "plugin.json").write_text('{"id": "info_bot", "model": "ollama/llama3"}')

        registry = self._make_registry()
        registry.discover_workers(tmp_path)

        workers = registry.list_workers()
        info_bot = next(w for w in workers if w["id"] == "info_bot")
        assert "source_dir" in info_bot
        assert "has_custom_class" in info_bot


# ─────────────────────────────────────────────────
#  WorkerGenerator tests
# ─────────────────────────────────────────────────

class TestWorkerGenerator:
    """Test the WorkerGenerator scaffolding system."""

    def test_create_basic(self, tmp_path):
        """Generator creates all required files."""
        gen = WorkerGenerator()
        worker_dir = gen.create(
            "basic_bot",
            base_dir=tmp_path,
            model="ollama/llama3",
            squad="support",
        )

        assert (worker_dir / "plugin.json").exists()
        assert (worker_dir / "SKILL.md").exists()
        assert (worker_dir / "worker.py").exists()
        assert (worker_dir / "__init__.py").exists()

    def test_create_with_custom_content(self, tmp_path):
        """Generator uses custom SKILL.md and worker.py content."""
        gen = WorkerGenerator()
        worker_dir = gen.create(
            "custom_bot",
            base_dir=tmp_path,
            model="ollama/llama3",
            skill_md_content="# Custom\nYou are custom.",
            worker_py_content="from kantorku.worker.base import BaseWorker\n\nclass Worker(BaseWorker): pass\n",
        )

        skill = (worker_dir / "SKILL.md").read_text()
        assert "Custom" in skill

        py = (worker_dir / "worker.py").read_text()
        assert "custom" not in py.lower() or "Custom" in py

    def test_create_validates_name(self, tmp_path):
        """Generator rejects invalid worker names."""
        gen = WorkerGenerator()
        with pytest.raises(ValueError, match="alphanumeric"):
            gen.create("bad name!", base_dir=tmp_path)

    def test_create_validates_model(self, tmp_path):
        """Generator rejects model without provider/ prefix."""
        gen = WorkerGenerator()
        with pytest.raises(ValueError, match="provider/model"):
            gen.create("my_bot", base_dir=tmp_path, model="just-llama3")

    def test_create_no_overwrite(self, tmp_path):
        """Generator won't overwrite existing worker without flag."""
        gen = WorkerGenerator()
        gen.create("existing", base_dir=tmp_path, model="ollama/llama3")

        with pytest.raises(FileExistsError):
            gen.create("existing", base_dir=tmp_path, model="ollama/llama3")

    def test_create_with_overwrite(self, tmp_path):
        """Generator overwrites with --overwrite flag."""
        gen = WorkerGenerator()
        gen.create("overwrite_me", base_dir=tmp_path, model="ollama/llama3")
        gen.create("overwrite_me", base_dir=tmp_path, model="anthropic/claude-sonnet-4-6", overwrite=True)

        plugin = json.loads((tmp_path / "overwrite_me" / "plugin.json").read_text())
        assert plugin["model"] == "anthropic/claude-sonnet-4-6"

    def test_create_with_capabilities(self, tmp_path):
        """Generator includes capabilities in plugin.json."""
        gen = WorkerGenerator()
        gen.create(
            "cap_bot",
            base_dir=tmp_path,
            model="ollama/llama3",
            capabilities=["translate", "summarize"],
        )

        plugin = json.loads((tmp_path / "cap_bot" / "plugin.json").read_text())
        assert "translate" in plugin["capabilities"]
        assert "summarize" in plugin["capabilities"]

    def test_generated_worker_is_loadable(self, tmp_path):
        """Generated worker can be loaded back by WorkerIdentity."""
        gen = WorkerGenerator()
        worker_dir = gen.create("loadable", base_dir=tmp_path, model="ollama/llama3")

        identity = WorkerIdentity.from_directory(worker_dir)
        assert identity.id == "loadable"
        assert identity.model == "ollama/llama3"

        # Should resolve the generated Worker class
        cls = identity.resolve_worker_class()
        assert cls is not None
        assert issubclass(cls, BaseWorker)


# ─────────────────────────────────────────────────
#  Office hot-plug tests
# ─────────────────────────────────────────────────

class TestOfficePlugAndPlay:
    """Test Office.hire_worker and hot_plug_worker."""

    def test_hire_worker_with_path(self, tmp_path):
        """hire_worker can load from a directory path."""
        worker_dir = tmp_path / "path_bot"
        worker_dir.mkdir()
        (worker_dir / "plugin.json").write_text(json.dumps({
            "id": "path_bot", "model": "ollama/llama3", "squad": "support"
        }))
        (worker_dir / "SKILL.md").write_text("Path worker")

        office = Office.__new__(Office)
        office.config = office.config if hasattr(office, 'config') else None
        # Use the simple approach
        from kantorku.config.settings import KantorkuConfig
        office.config = KantorkuConfig()
        office.bus = EventBus()
        office.router = ProviderRouter()
        office.registry = WorkerRegistry(router=office.router, bus=office.bus)
        office._initialized = False

        office.hire_worker("path_bot", path=str(worker_dir))

        identity = office.registry.get_identity("path_bot")
        assert identity is not None
        assert identity.id == "path_bot"

    def test_hire_worker_programmatic(self):
        """hire_worker with custom class works."""
        class TestBot(BaseWorker):
            async def handle(self, task):
                return TaskResult(task_id=task.id, status="done")

        from kantorku.config.settings import KantorkuConfig
        office = Office.__new__(Office)
        office.config = KantorkuConfig()
        office.bus = EventBus()
        office.router = ProviderRouter()
        office.registry = WorkerRegistry(router=office.router, bus=office.bus)
        office._initialized = False

        office.hire_worker(
            "test_bot",
            model="ollama/llama3",
            squad="support",
            worker_class=TestBot,
        )

        # Should be able to hire it
        worker = office.registry.hire("test_bot")
        assert isinstance(worker, TestBot)
