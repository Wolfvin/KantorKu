# Changelog

All notable changes to KantorKu will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2025-05-04

### Added

- **Core Framework**
  - Office entry point with `from_config()` and programmatic API
  - Conductor (CEO) — intelligent orchestration with contract negotiation
  - BriefingRoom — pre-execution worker discussion
  - WorkerHub — peer-to-peer DM and broadcast between workers
  - ContextPool — proactive context prefetch during briefing (FIFO queue)
  - ExecutionChannel — structured worker output channel
  - GroupChannel — squad-level communication
  - ProjectNotebook — structured proposal system with channel injection
  - DAG — task dependency graph with ASCII tree rendering
  - Delegation patterns for task assignment

- **Workers (13 built-in)**
  - Coding: `coder_frontend`, `coder_backend`, `coder_wiring`
  - Verification: `verifier_designer`, `verifier_engineer`
  - Support: `debugger`, `scout`, `auditor`, `scribe`, `summarizer`, `sentinel`
  - Translation: `intake`, `narrator`
  - Each worker has `plugin.json` + `SKILL.md` + optional `worker.py`

- **Memory System (3-Ring)**
  - Ring 1 — DuckDB hot memory (microsecond latency)
  - Ring 2 — SQLite + Parquet warm memory (millisecond latency)
  - Ring 3 — GraphRAG cold memory (stub for future)

- **LLM Providers (7 supported)**
  - Anthropic (Claude Sonnet/Opus)
  - Google (Gemini)
  - OpenAI (GPT/Codex)
  - xAI (Grok)
  - DeepSeek
  - MiniMax
  - Ollama (local, free)
  - ProviderRouter with `provider/model` dispatch
  - Circuit breaker and retry with exponential backoff
  - Token-bucket rate limiter

- **Personality System**
  - Per-worker personality profiles
  - `consider_speaking()` wired into Office runtime loop
  - Personality-aware BriefingRoom participation

- **TUI (Terminal UI)**
  - 3-panel layout: Manager Chat, Workers Live Stream, Contract Display
  - 10 built-in themes: Synthwave, Neon Nights, Hackerman, Void, Tokyo Night, Dracula, Monokai, Nord, Gruvbox, Default
  - Hot theme switching with `/theme` command
  - Command palette with 38 event renderers and slash commands
  - Settings screen with full worker CRUD, live preview, backup/restore
  - Real-time WebSocket connection with exponential backoff reconnect
  - Rich Markdown rendering in panels
  - Braille spinner animations (⣾⣽⣻⢿⡿⣟⣯⣷)
  - Keyboard shortcuts: Ctrl+Enter send, Ctrl+M multi-line, / commands
  - DAG panel with ASCII tree rendering
  - Filter bar for worker event streams
  - Thinking indicators with worker-specific status

- **Server Mode**
  - FastAPI server with dual WebSocket channels
  - `/ws/client` — Client ↔ Manager interaction (Panel 1)
  - `/ws/office` — Live worker event stream (Panel 2)
  - REST endpoints: health check, status, event replay
  - Session persistence and middleware

- **Red Team Module**
  - STM (Short-Term Memory) exploit testing
  - AutoTune scoring with EMA and bias correction
  - Godmode bypass testing
  - Parseltongue encoding
  - Prompt classification
  - Safety scoring with confidence levels

- **Event System**
  - EventBus — pub/sub per session
  - EventEmitter — typed convenience layer
  - 38 event types covering full lifecycle

- **Configuration**
  - `kantorku.toml` — single config file for everything
  - Environment variable interpolation (`${API_KEY}`)
  - Worker, provider, pool, memory, server sections

- **CLI**
  - `kantorku` — launch TUI
  - `kantorku worker create` — create new worker
  - `kantorku worker validate` — validate worker directory
  - `kantorku worker list` — list all workers by category
  - `kantorku --config` — custom config path
  - `kantorku --port` — server mode port

- **Testing**
  - Integration test suite (`test_office.py`, `test_components.py`)
  - Plug-and-play tests (`test_plug_and_play.py`)
  - Maturation tests (`test_maturation.py`)
  - Core logic tests (`test_p3.py`)

- **Documentation**
  - README.md — project overview with quick start
  - ADDING_WORKERS.md — complete worker creation guide
  - WORKERS_MANIFEST.md — full worker index by squad
  - PANDUAN_PEMASANGAN.md — installation guide (Bahasa Indonesia)
  - CONTRIBUTING.md — contribution guidelines
  - SECURITY.md — security policy
  - CHANGELOG.md — release history

[0.1.0]: https://github.com/Wolfvin/KantorKu/releases/tag/v0.1.0
