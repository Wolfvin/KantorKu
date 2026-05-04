# Changelog

All notable changes to KantorKu will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.4.0] - 2025-04-30

### P4: Communication Maturation

#### Framework
- **Added**: `GroupChannel` — Multi-worker broadcast channels for coordinated work sessions
- **Added**: `TodoReview` — Structured review workflow for task verification and sign-off
- **Added**: `SessionTranscript` — Full conversation logging with searchable archives
- **Added**: `BriefingRoom` enhancements — Priority-based briefing queue and async briefing delivery
- **Changed**: Worker communication now supports structured message types (question, status, escalation)
- **Changed**: Conductor routing improved with context-aware worker selection
- **Fixed**: Race condition in parallel worker execution
- **Fixed**: Memory context overflow when processing large codebases

#### Interface
- **Added**: Real-time collaboration view for GroupChannel conversations
- **Added**: TodoReview panel with approve/reject/request-changes actions
- **Added**: Session transcript viewer with search and filtering
- **Changed**: 3-Zone UI refined with improved responsive breakpoints
- **Fixed**: WebSocket reconnection handling on network interruption

---

## [0.3.0] - 2025-04-20

### P3: Production Hardening

#### Framework
- **Added**: Persistence layer — DuckDB-based task and conversation storage
- **Added**: Task queue with priority scheduling and retry logic
- **Added**: Middleware system for request/response pipeline
- **Added**: Health check endpoints (`/health`, `/ready`)
- **Added**: Observability — structured logging, metrics, and tracing
- **Added**: Server-Sent Events (SSE) for real-time streaming
- **Changed**: Server migrated to production-grade ASGI with proper lifecycle management
- **Changed**: Error handling now uses structured error codes
- **Fixed**: Memory leak in long-running sessions
- **Fixed**: SSE connection cleanup on client disconnect

#### Interface
- **Added**: Streaming response display with real-time token output
- **Added**: WebSocket connection for bidirectional communication
- **Added**: Task status indicators and progress tracking
- **Changed**: API client refactored for SSE/WebSocket support
- **Fixed**: UI flickering during state transitions

---

## [0.2.0] - 2025-04-10

### P2: Worker Identity & Provider Router

#### Framework
- **Added**: Worker identity system — Each worker has a distinct personality, role, and communication style
- **Added**: Provider router — Intelligent routing of tasks to optimal AI providers based on worker needs
- **Added**: Worker configuration via TOML files (`worker.toml`)
- **Added**: Multi-provider support — Anthropic, Google, MiniMax, DeepSeek, OpenAI, xAI, Ollama
- **Added**: Fallback provider chain for resilience
- **Changed**: Worker dispatch now considers provider availability and rate limits
- **Changed**: Configuration centralized in `kantorku.toml`
- **Fixed**: Provider API error handling and retry logic
- **Fixed**: Worker timeout handling for slow providers

#### Interface
- **Added**: Provider status display in settings panel
- **Changed**: Configuration UI for provider API keys
- **Fixed**: Form validation for API key inputs

---

## [0.1.0] - 2025-04-01

### Initial Release

#### Framework
- **Added**: `Office` — Central orchestrator managing worker lifecycle and task routing
- **Added**: `Conductor` — CEO agent that coordinates the office, triages tasks, and dispatches work
- **Added**: Core workers:
  - `intake` — Task intake and initial analysis
  - `coder_backend` — Backend code generation
  - `coder_frontend` — Frontend code generation
  - `coder_wiring` — Integration and wiring code
  - `debugger` — Bug detection and fixing
  - `auditor` — Code quality and security auditing
  - `scribe` — Documentation generation
  - `scout` — Research and information gathering
  - `verifier_designer` — Design verification
  - `verifier_engineer` — Engineering verification
  - `narrator` — Progress narration and reporting
  - `summarizer` — Content summarization
  - `sentinel` — Watchdog and monitoring
- **Added**: `Memory` — Context pool with conversation history and knowledge management
- **Added**: `Server` — FastAPI-based HTTP/WebSocket server
- **Added**: CLI with `kantorku serve`, `kantorku version`, and `kantorku config` commands
- **Added**: TOML-based configuration system

#### Interface
- **Added**: Next.js 14 frontend with 3-Zone UI layout
- **Added**: Chat interface with streaming support
- **Added**: Worker status dashboard
- **Added**: Configuration management UI
- **Added**: Dark/light theme support

#### CLI
- **Added**: Node.js CLI tool for kantorku management
- **Added**: Project scaffolding commands

---

## [0.2.0-interface] - 2025-04-10

### Interface Release

- **Added**: 3-Zone UI — Navigation | Chat | Context layout
- **Added**: Streaming response display
- **Added**: WebSocket connection for real-time updates
- **Added**: Worker activity feed
- **Added**: Session management
- **Changed**: Migrated to Next.js App Router
- **Changed**: Tailwind CSS 4 integration

---

[0.4.0]: https://github.com/kantorku/kantorku/releases/tag/v0.4.0
[0.3.0]: https://github.com/kantorku/kantorku/releases/tag/v0.3.0
[0.2.0]: https://github.com/kantorku/kantorku/releases/tag/v0.2.0
[0.1.0]: https://github.com/kantorku/kantorku/releases/tag/v0.1.0
