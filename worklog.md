---
Task ID: 1
Agent: Main Agent
Task: Implement plug-and-play worker system for kantorku framework

Work Log:
- Explored entire worker system: base.py, registry.py, identity.py, all 13 workers, CLI, office.py
- Upgraded WorkerIdentity with: class_path field, source_dir field, validate() method, resolve_worker_class() with dynamic import, _load_from_file() and _load_from_dotted_path(), to_plugin_json() serialization
- Upgraded WorkerRegistry with: discover_workers_multi(), discover_from_entry_points(), hot_plug(), hot_plug_class(), validate_worker_dir(), _infer_squad(), backwards-compatible register_from_config alias
- Created WorkerGenerator with: create() scaffolding, plugin.json + SKILL.md + worker.py + __init__.py templates, validation, quickstart guide
- Upgraded CLI with: worker create, worker add, worker validate, worker list (improved), backwards compat with worker-list
- Upgraded Office with: hire_worker(path=...) for directory loading, hot_plug_worker() for runtime addition, multi-path discover in initialize(), entry points discovery
- Added HookType.ON_WORKER_HIRED and ON_WORKER_FIRED
- Created example custom worker (translator) with plugin.json + SKILL.md + worker.py
- Created usage_examples.py showing 4 methods of adding workers
- Updated __init__.py with WorkerGenerator export
- Created 30 comprehensive tests in test_plug_and_play.py
- All 39 tests pass (9 original + 30 new)

Stage Summary:
- Plug-and-play worker system is fully implemented
- Workers can be added by: directory path, custom class, hot-plug at runtime, CLI scaffold, TOML config, pip entry points
- Auto-discovery from: builtin workers/, project workers/, custom dirs, pip packages
- worker.py auto-detection and dynamic class loading works
- Validation and error reporting for worker directories
- Full backwards compatibility maintained
