<p align="center">
  <img src="https://img.shields.io/badge/kantorku-v0.1.0-ff79c6?style=for-the-badge&labelColor=0d0d1a" alt="version" />
  <img src="https://img.shields.io/badge/python-3.11+-8be9fd?style=for-the-badge&labelColor=0d0d1a" alt="python" />
  <img src="https://img.shields.io/badge/license-MIT-50fa7b?style=for-the-badge&labelColor=0d0d1a" alt="license" />
  <img src="https://img.shields.io/badge/status-alpha-ffb86c?style=for-the-badge&labelColor=0d0d1a" alt="status" />
</p>

<h1 align="center">KantorKu</h1>

<p align="center">
  <strong>The digital office that actually works</strong><br/>
  Multi-agent LLM orchestration framework — where AI workers collaborate like a real team.
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> ·
  <a href="#-architecture">Architecture</a> ·
  <a href="#-workers">Workers</a> ·
  <a href="#-tui">TUI</a> ·
  <a href="#-api">API</a> ·
  <a href="#-documentation">Docs</a> ·
  <a href="./CONTRIBUTING.md">Contributing</a>
</p>

---

## Why KantorKu?

Other multi-agent frameworks give you a router and wish you luck. KantorKu gives you an **actual office**:

| Problem | Others | KantorKu |
|---------|--------|----------|
| Who decides what? | You wire the graph manually | **Conductor (CEO) thinks and decides** |
| Workers just execute blindly | Yes | **BriefingRoom — workers discuss before executing** |
| No pre-work context | Fetch on demand | **ContextPool — proactive prefetch during briefing** |
| Workers can't talk to each other | Limited or none | **WorkerHub DM — peer-to-peer worker communication** |
| Client sends task, prays | Fire and forget | **Contract negotiation — agree before work starts** |
| Memory = chat history | External bolt-on | **3-Ring Memory — hot/warm/cold like CPU caches** |
| Terminal UI | None or basic | **Full TUI — 3-panel, 10 themes, command palette** |

KantorKu is not another agent wrapper. It is an **office metaphor** brought to life: the Manager receives the brief, the team discusses in the BriefingRoom, the Scout starts researching before being asked, and the Coders verify and refine context that has already been prepared.

---

## Quick Start

### Install

#### From PyPI (recommended)

```bash
# Core only (use Ollama — free, local)
pip install kantorku

# With specific providers
pip install kantorku[anthropic,google]

# Everything (all providers + TUI)
pip install kantorku[all]
```

#### Arch Linux / Manjaro

Arch-based distros enforce [PEP 668](https://peps.python.org/pep-0668/) — you **must** use a virtual environment:

```bash
# Create and activate a venv
python -m venv ~/.venv/kantorku
source ~/.venv/kantorku/bin/activate

# Install
pip install kantorku[all]

# Add to your shell for easy access
echo 'source ~/.venv/kantorku/bin/activate' >> ~/.bashrc
```

Or use `pipx` for a global CLI without venv hassle:

```bash
# Install pipx (if not already)
sudo pacman -S python-pipx

# Install kantorku
pipx install kantorku[all]

# Now kantorku command is available globally
kantorku --help
```

#### Ubuntu / Debian

```bash
# Install Python venv support
sudo apt install python3-venv python3-pip

# Create and activate a venv
python3 -m venv ~/.venv/kantorku
source ~/.venv/kantorku/bin/activate

# Install
pip install kantorku[all]
```

#### Fedora

```bash
# Create and activate a venv
python3 -m venv ~/.venv/kantorku
source ~/.venv/kantorku/bin/activate

# Install
pip install kantorku[all]
```

#### macOS

```bash
# Install Python with Homebrew (if not already)
brew install python

# Create and activate a venv
python3 -m venv ~/.venv/kantorku
source ~/.venv/kantorku/bin/activate

# Install
pip install kantorku[all]
```

#### Windows

```powershell
# Create and activate a venv
python -m venv .venv\kantorku
.venv\kantorku\Scripts\activate

# Install
pip install kantorku[all]
```

#### From Source (any OS)

```bash
git clone https://github.com/Wolfvin/KantorKu.git
cd KantorKu/framework

# Create and activate a venv (recommended)
python -m venv .venv
source .venv/bin/activate    # Linux/macOS
# .venv\Scripts\activate     # Windows

# Install in editable mode
pip install -e ".[all]"

# Verify
kantorku version
python -m pytest tests/ -v
```

> **Why a venv?** Modern Linux distros (Arch, Ubuntu 23.04+, Fedora 38+) enforce [PEP 668](https://peps.python.org/pep-0668/) which prevents installing packages system-wide. A virtual environment is the cleanest solution and works everywhere.

### Run

```python
import asyncio
from kantorku import Office

async def main():
    office = Office.from_config("kantorku.toml")
    await office.initialize()
    result = await office.run("Build a rate limiter in Rust")
    print(result)

asyncio.run(main())
```

### Or use the TUI

```bash
pip install kantorku[tui]
kantorku
```

<p align="center">
  <img src="https://img.shields.io/badge/3_panel_layout-manager_·_workers_·_contract-8be9fd?style=flat-square&labelColor=0d0d1a" alt="layout" />
  <img src="https://img.shields.io/badge/10_themes-synthwave_·_void_·_tokyo_night-bd93f9?style=flat-square&labelColor=0d0d1a" alt="themes" />
  <img src="https://img.shields.io/badge/command_palette-38_renderers-ff79c6?style=flat-square&labelColor=0d0d1a" alt="commands" />
</p>

---

## Architecture

```
CLIENT                PANEL 1              BACKEND                 PANEL 2
──────                ───────              ───────                 ───────
"Build a rate
 limiter in Rust"
    │
    ▼────────────→  ws/client
                       │
                       ▼
                  Conductor.understand_client()
                  "Production or internal?"
                       │◄── manager_message
                       ▼

"Production,
 distributed"
    │
    ▼────────────→  ws/client
                       │
                       ▼
                  Conductor draft contract
                       │◄── contract_ready
                       ▼

[Accept contract]
    │
    ▼────────────→  ws/client (contract_accepted)
                       │
                       ▼
                  Office.start_work()
                       │
                       ▼
                  Conductor.conduct()
                       ├── briefing_opened ───────────────────→ Panel 2
                       ├── breakdown todos → parallel prefetch
                       │     ├── pool.prefetch(todo-1) ────────→ Panel 2
                       │     ├── pool.prefetch(todo-2) ────────→ Panel 2
                       │     └── pool.prefetch(todo-3) ────────→ Panel 2
                       ├── workers speak_up() in parallel
                       ├── task_assigned → workers execute (context ready in Ring 1)
                       ├── WorkerHub DMs between workers
                       ├── Verification passes
                       └── Final output → narrator → CLIENT
```

### Core Concepts

- **Conductor** — The CEO. Not a router — it *thinks*, makes decisions, drafts contracts, and orchestrates workers based on context.
- **BriefingRoom** — Workers discuss *before* execution. Catches misunderstandings early, not after errors.
- **ContextPool** — Proactive prefetch during briefing. When a coder starts working, the context is already in Ring 1.
- **WorkerHub** — Peer-to-peer DM between workers. Workers can negotiate, share concerns, and coordinate without going through the Conductor.
- **Contract Flow** — Client negotiates with the Conductor, agrees on scope, then work begins. No surprises.
- **3-Ring Memory** — DuckDB (hot, microseconds) → SQLite + Parquet (warm, milliseconds) → GraphRAG (cold, future). Like CPU cache tiers for AI context.

---

## Workers

KantorKu ships with 13 built-in workers across 4 squads:

### Coding — The Code Writers

| Worker | Model | Specialty |
|--------|-------|-----------|
| `coder_frontend` | Claude Sonnet 4.6 | React, CSS, UI/Visual, Accessibility |
| `coder_backend` | MiniMax M2.7 | Python, Rust, Database, Systems |
| `coder_wiring` | Gemini 3.1 Pro | API, WebSocket, MCP, Integration |

### Verification — The Quality Gate

| Worker | Model | Specialty |
|--------|-------|-----------|
| `verifier_designer` | Gemini 3.1 Pro | Visual/UX review |
| `verifier_engineer` | MiniMax M2.5 | Logic, security, performance review |

### Support — The Specialists

| Worker | Model | Specialty |
|--------|-------|-----------|
| `debugger` | DeepSeek V3.2 | Root cause analysis |
| `scout` | Gemini 2.5 Pro | Research, web search |
| `auditor` | Claude Sonnet 4.6 | Architecture review |
| `scribe` | DeepSeek V4 Flash | Documentation |
| `summarizer` | DeepSeek V4 Flash | Context compression |
| `sentinel` | Ollama Llama3 | Error logging, lessons learned |

### Translation — The Interface Layer

| Worker | Model | Specialty |
|--------|-------|-----------|
| `intake` | Ollama Llama3 | Parse & classify client messages |
| `narrator` | Ollama Llama3 | Format output for the client |

> **Every worker is pluggable.** Swap models, add custom logic, or create entirely new workers. See [ADDING_WORKERS.md](./ADDING_WORKERS.md).

### Supported Providers

| Provider | Required | Class |
|----------|----------|-------|
| Anthropic | `api_key` | `AnthropicProvider` |
| Google | `api_key` | `GoogleProvider` |
| OpenAI | `api_key` | OpenAI-compatible |
| xAI | `api_key`, `base_url` | OpenAI-compatible |
| DeepSeek | `api_key` | `DeepSeekProvider` |
| MiniMax | `api_key` | `MiniMaxProvider` |
| Ollama | `base_url` | `OllamaProvider` (free, local) |

---

## TUI

KantorKu includes a full terminal UI built with [Textual](https://github.com/Textualize/textual) and [Rich](https://github.com/Textualize/rich):

- **3-panel layout** — Manager chat (left), Workers live stream (center), Contract display (right)
- **10 built-in themes** — Synthwave, Void, Tokyo Night, Hackerman, Neon Nights, and more
- **Command palette** — 38 event renderers, slash commands, filterable
- **Real-time** — WebSocket-connected, live worker activity, thinking indicators
- **Settings screen** — Full worker CRUD, live preview, backup/restore
- **Keyboard-first** — Ctrl+Enter to send, Ctrl+M for multi-line, / for commands

```bash
kantorku                    # Launch TUI
kantorku --config my.toml   # Custom config
```

---

## API

### Programmatic

```python
from kantorku import Office

# From config file
office = Office.from_config("kantorku.toml")
await office.initialize()

# One-shot
result = await office.run("Implement JWT auth in Python")

# Step-by-step with negotiation
async for event in office.chat("session-1", "Build a rate limiter"):
    if event["type"] == "contract_ready":
        result = await office.accept_and_run("session-1")

# Without config file
office = Office(conductor_model="ollama/llama3")
office.configure_provider("ollama", base_url="http://localhost:11434/v1")
office.hire_worker("coder_backend", model="ollama/deepseek-coder-v2", squad="coding")
await office.initialize()
```

### Server Mode (WebSocket)

```bash
kantorku --config kantorku.toml --port 8000
```

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /` | — | Health check |
| `GET /status` | — | Worker + pool status |
| `GET /events/{session_id}` | — | Recent events (replay) |
| `WS /ws/client` | — | Client ↔ Manager (Panel 1) |
| `WS /ws/office` | — | Live worker events (Panel 2) |

### Adding Custom Workers

```bash
# CLI
kantorku worker create image_gen --squad support --model "openai/dall-e-3"

# Or drop a folder
workers/
└── my_worker/
    ├── plugin.json    # Required — metadata + API config
    ├── SKILL.md       # Recommended — system prompt
    └── worker.py      # Optional — custom BaseWorker subclass
```

See [ADDING_WORKERS.md](./ADDING_WORKERS.md) for the complete guide.

---

## Memory

The 3-Ring Memory system provides tiered context storage:

| Ring | Storage | Latency | Content |
|------|---------|---------|---------|
| **Ring 1** | DuckDB | Microseconds | Prefetched context, session state, task results |
| **Ring 2** | SQLite + Parquet | Milliseconds | Episode logs, lessons learned, audit trail |
| **Ring 3** | GraphRAG (planned) | Hundreds of ms | Knowledge graph, cross-session learning |

```python
from kantorku import Ring1Memory, Ring2Memory

ring1 = Ring1Memory("data/ring1.duckdb")
await ring1.initialize()

# Store context (typically by ContextPool)
await ring1.store_context("todo-1", {
    "files": ["src/middleware/rate_limit.rs"],
    "patterns": ["token bucket"],
    "summary": "Found existing rate limiter pattern",
})

# Worker retrieves context when starting a task
context = await ring1.get_context("todo-1")
```

---

## Comparison

| Feature | LangGraph | CrewAI | AutoGen | **KantorKu** |
|---------|-----------|--------|---------|-------------|
| Orchestration | Manual routing | Process.sequential | Conversation | **Conductor (CEO)** |
| Pre-execution discussion | No | No | No | **BriefingRoom** |
| Worker communication | No | Limited | Yes | **WorkerHub DM** |
| Proactive prefetch | No | No | No | **ContextPool FIFO** |
| Memory tiers | External | Basic | Basic | **3-Ring (hot/warm/cold)** |
| Contract negotiation | No | No | No | **Client ↔ Manager** |
| Terminal UI | No | No | No | **Full TUI, 10 themes** |
| Plugin system | No | Limited | No | **plugin.json + SKILL.md** |
| Real-time streaming | No | Limited | Limited | **Dual WebSocket channels** |

---

## Documentation

| Document | Description |
|----------|-------------|
| [ADDING_WORKERS.md](./ADDING_WORKERS.md) | Complete guide to adding custom workers |
| [WORKERS_MANIFEST.md](./WORKERS_MANIFEST.md) | Full index of all built-in workers |
| [PANDUAN_PEMASANGAN.md](./PANDUAN_PEMASANGAN.md) | Installation & configuration guide (Bahasa Indonesia) |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | How to contribute |
| [CHANGELOG.md](./CHANGELOG.md) | Release history |
| [SECURITY.md](./SECURITY.md) | Security policy |

---

## Project Structure

```
kantorku/
├── pyproject.toml
├── kantorku.toml
├── kantorku/
│   ├── __init__.py
│   ├── office.py               # Office — main entry point
│   ├── dag.py                   # DAG — task dependency graph
│   ├── delegation.py            # Delegation patterns
│   ├── hooks.py                 # Lifecycle hooks
│   ├── errors.py                # Custom exceptions
│   ├── worker/
│   │   ├── base.py              # BaseWorker, Task, TaskResult
│   │   ├── registry.py          # WorkerRegistry — hire/fire/discover
│   │   ├── identity.py          # WorkerIdentity — plugin.json + SKILL.md
│   │   ├── personality.py       # Personality system
│   │   └── generator.py         # Worker code generation
│   ├── layers/
│   │   ├── conductor.py         # Conductor — CEO, contract, orchestration
│   │   ├── briefing_room.py     # BriefingRoom — workers discuss + prefetch
│   │   ├── worker_hub.py        # WorkerHub — DM peer-to-peer + broadcast
│   │   ├── execution_channel.py # ExecutionChannel — structured worker output
│   │   ├── group_channel.py     # GroupChannel — squad-level communication
│   │   ├── intake.py            # Intake — parse freeform → structured
│   │   ├── session_transcript.py
│   │   └── todo_review.py
│   ├── pool/
│   │   ├── context_pool.py      # ContextPool — FIFO queue, prefetch/reactive
│   │   └── pool_worker.py       # PoolWorker — single instance
│   ├── memory/
│   │   ├── ring1.py             # Ring1 — DuckDB hot memory
│   │   ├── ring2.py             # Ring2 — SQLite warm memory
│   │   ├── ring3.py             # Ring3 — Cognee stub (Phase 3)
│   │   └── notebook.py          # ProjectNotebook — structured proposals
│   ├── events/
│   │   ├── bus.py               # EventBus — pub/sub per session
│   │   └── emitter.py           # EventEmitter — typed convenience
│   ├── providers/
│   │   ├── router.py            # ProviderRouter — "provider/model" dispatch
│   │   ├── base.py              # BaseProvider abstract
│   │   ├── anthropic_provider.py
│   │   ├── google_provider.py
│   │   ├── openai_compat.py     # OpenAI-compatible (xAI, etc.)
│   │   ├── deepseek_provider.py
│   │   ├── minimax_provider.py
│   │   ├── ollama_provider.py
│   │   ├── retry.py             # Retry with exponential backoff
│   │   ├── rate_limiter.py      # Token-bucket rate limiter
│   │   └── circuit_breaker.py   # Circuit breaker pattern
│   ├── redteam/
│   │   ├── stm.py               # Short-Term Memory exploit
│   │   ├── autotune.py          # AutoTune scoring
│   │   ├── godmode.py           # Godmode bypass
│   │   ├── parselongue.py       # Parseltongue encoding
│   │   ├── classify.py          # Prompt classification
│   │   └── scoring.py           # Safety scoring
│   ├── config/
│   │   └── settings.py          # KantorkuConfig, WorkerConfig, PoolConfig
│   ├── tui/
│   │   ├── app.py               # Main TUI application (3-panel layout)
│   │   ├── cli.py               # CLI entry point
│   │   ├── commands.py          # Command palette (38 renderers)
│   │   ├── themes.py            # 10 named themes with hot-switch
│   │   ├── settings_screen.py   # Worker CRUD, live preview
│   │   ├── connection.py        # WebSocket connection manager
│   │   └── markdown_renderer.py # Rich Markdown rendering
│   ├── interface/
│   │   ├── server.py            # FastAPI + 2 WebSocket channels
│   │   ├── health.py            # Health check endpoints
│   │   ├── persistence.py       # Session persistence
│   │   ├── protocol.py          # WebSocket protocol
│   │   ├── middleware.py        # Auth & logging middleware
│   │   └── task_queue.py        # Task queue for server mode
│   ├── workers/                 # 13 built-in worker implementations
│   └── cache.py                 # Response caching
├── workers/                     # Worker plugin directories
│   ├── coder_frontend/plugin.json + SKILL.md
│   ├── coder_backend/plugin.json + SKILL.md
│   └── ...
├── examples/
│   ├── 01_basic_usage.py
│   ├── 02_custom_worker.py
│   ├── 03_hooks_and_streaming.py
│   └── 04_from_config.py
└── tests/
    ├── test_office.py
    ├── test_components.py
    ├── test_plug_and_play.py
    ├── test_maturation.py
    └── test_p3.py
```

---

## Development

```bash
# Clone
git clone https://github.com/Wolfvin/KantorKu.git
cd KantorKu/framework

# Create venv (required on Arch/Fedora/Ubuntu 23.04+)
python -m venv .venv
source .venv/bin/activate    # Linux/macOS
# .venv\Scripts\activate     # Windows

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -v

# Lint
ruff check kantorku/
```

See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

---

## License

MIT License — see [LICENSE](./LICENSE).

---

<p align="center">
  <em>kantorku — because a good office isn't the one with the fanciest tools,<br/>it's the one that knows who should do what.</em>
</p>
