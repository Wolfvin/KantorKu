<p align="center">
  <h1 align="center">🏢 kantorku</h1>
  <p align="center">
    <em>Kantor digital yang sesungguhnya — AI worker orchestration framework</em>
  </p>
  <p align="center">
    <a href="#quick-start">Quick Start</a> •
    <a href="#architecture">Architecture</a> •
    <a href="#workers">Workers</a> •
    <a href="#api-keys">API Keys</a> •
    <a href="#cli">CLI</a> •
    <a href="#credits">Credits</a>
  </p>
</p>

---

## Apa itu kantorku?

kantorku adalah framework orchestrasi multi-agent LLM yang memodelkan kantor digital sesungguhnya. Daripada satu AI monolitik, kantorku menggunakan **14 specialized workers** yang berkoordinasi melalui **Conductor (CEO)** — masing-masing dengan model LLM, spesialisasi, dan peran yang berbeda.

**Konsep utama**: Bayangkan kantor developer sungguhan — ada CEO yang mengatur, programmer frontend/backend, QA, auditor, researcher, dan documentation writer. Mereka rapat, diskusi, dan kerja sesuai tugas masing-masing.

### Fitur Utama

- 🧠 **14 Specialized Workers** — masing-masing dengan model & spesialisasi berbeda
- 📋 **Contract-Based Workflow** — kontrak formal sebelum eksekusi, dengan approval gates
- 💬 **Interactive Questions** — AI Manager bisa bertanya dengan pilihan A/B/C/Other (seperti Claude)
- 🏢 **BriefingRoom** — tim diskusi sebelum eksekusi dimulai
- 💾 **3-Ring Memory** — DuckDB (hot) → SQLite (warm) → Vector DB (cold)
- 🔄 **DAG Execution** — parallel task execution dengan dependency resolution
- 🛡️ **Circuit Breakers** — auto-recovery saat provider down
- 💰 **Cost Guard** — budget enforcement & real-time cost tracking
- 📊 **Full Observability** — distributed tracing, spans, metrics
- 🔌 **7 LLM Providers** — Anthropic, Google, MiniMax, DeepSeek, OpenAI, xAI, Ollama
- 🖥️ **3-Zone UI** — Lobby (Chat), Ruang Kerja (Workers), Dashboard (Monitoring)
- 🤖 **CLI Tool** — interactive setup, chat, worker management

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      kantorku                           │
├────────────────┬──────────────────┬─────────────────────┤
│   interface/   │   framework/     │      cli/           │
│   (Next.js)    │   (Python)       │   (Node.js)         │
│                │                  │                     │
│  🖥️ Web UI     │  🐍 Backend      │  ⌨️ Terminal tool   │
│  Dashboard     │  Workers engine  │  Setup wizard       │
│  Chat panel    │  Memory rings    │  Interactive chat   │
│  Monitoring    │  Provider router │  Worker management  │
│  Settings      │  Event bus       │  Status check       │
└────────────────┴──────────────────┴─────────────────────┘
```

### Framework Layers (20+)

```
                    ┌─────────────────┐
                    │   Conductor     │  ← CEO — understands, drafts, orchestrates
                    │   (CEO/Manager) │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                     │
  ┌─────▼──────┐   ┌────────▼────────┐   ┌───────▼───────┐
  │ Intake     │   │ BriefingRoom     │   │ GroupChannel  │
  │ (Parse)    │   │ (Team Discuss)   │   │ (Discussion)  │
  └─────┬──────┘   └────────┬────────┘   └───────┬───────┘
        │                    │                     │
        └────────────────────┼────────────────────┘
                             │
                    ┌────────▼────────┐
                    │ TodoReview      │  ← Team reviews TODOs
                    │ Phase           │
                    └────────┬────────┘
                             │
        ┌────────────────────┼─────────────────────┐
        │                    │                      │
  ┌─────▼──────┐   ┌────────▼────────┐   ┌────────▼───────┐
  │ DAG        │   │ Context Pool     │   │ Worker Hub     │
  │ Resolver   │   │ (DeepSeek V3.2)  │   │ (P2P DM)       │
  └─────┬──────┘   └────────┬────────┘   └────────┬───────┘
        │                    │                      │
        └────────────────────┼──────────────────────┘
                             │
                    ┌────────▼────────┐
                    │ 14 Workers      │  ← Execute tasks
                    │ (Coding/Verify/ │
                    │  Support/Trans) │
                    └────────┬────────┘
                             │
        ┌────────────────────┼─────────────────────┐
        │                    │                      │
  ┌─────▼──────┐   ┌────────▼────────┐   ┌────────▼───────┐
  │ Debrief    │   │ 3-Ring Memory    │   │ EventBus       │
  │ (Lessons)  │   │ (Duck/SQLite/Vec)│   │ (Real-time)    │
  └────────────┘   └─────────────────┘   └────────────────┘
```

---

## Workers

### Coding Squad 🟦
| Worker | Emoji | Model | Role |
|--------|-------|-------|------|
| `coder_frontend` | 🎨 | Claude Sonnet 4.6 | React/CSS/UI specialist |
| `coder_backend` | ⚙️ | MiniMax M2.7 | Python/Rust/Systems |
| `coder_wiring` | 🔌 | Gemini 3.1 Pro | API/WS/MCP/Glue |

### Verification Squad 🟩
| Worker | Emoji | Model | Role |
|--------|-------|-------|------|
| `verifier_designer` | 👁️ | Gemini 3.1 Pro | Visual/UX judge |
| `verifier_engineer` | ✅ | MiniMax M2.5 | Logic/test/security |

### Support Squad 🟧
| Worker | Emoji | Model | Role |
|--------|-------|-------|------|
| `debugger` | 🐛 | DeepSeek V3.2 | Root cause analysis |
| `scout` | 🔍 | Gemini 2.5 Pro | Research & documentation |
| `auditor` | 🔒 | Claude Sonnet 4.6 | Architecture review |
| `scribe` | 📝 | DeepSeek V4 Flash | Documentation writing |
| `summarizer` | 📊 | DeepSeek V4 Flash | Context compression |
| `sentinel` | 🛡️ | Ollama Llama3 | Error monitoring |

### Translation Squad 🟪
| Worker | Emoji | Model | Role |
|--------|-------|-------|------|
| `intake` | 📋 | Ollama Llama3 | Message parsing |
| `narrator` | 📖 | Ollama Llama3 | Output formatting |

### Special
| Component | Model | Role |
|-----------|-------|------|
| Conductor | Claude Opus 4.6 | CEO — orchestration |
| Context Pool (x3) | DeepSeek V3.2 | Proactive prefetch |

---

## Quick Start

### Prerequisites

- **Python 3.11+** (untuk framework)
- **Node.js 18+** (untuk interface & CLI)
- **Bun** (recommended, untuk interface)

### 1. Clone Repository
```bash
git clone https://github.com/your-org/kantorku.git
cd kantorku
```

### 2. Setup API Keys

**Via CLI (Recommended)**:
```bash
cd cli
npm install
npm link
kantorku setup
```

**Via Environment Variables**:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="AIza..."
export MINIMAX_API_KEY="..."
export DEEPSEEK_API_KEY="sk-..."
export OPENAI_API_KEY="sk-..."
export XAI_API_KEY="xai-..."
```

### 3a. Run Interface (Standalone Mode)
```bash
cd interface
npm install
npm run dev
# Open http://localhost:3000
```

### 3b. Run Full Stack (Python + Next.js)
```bash
# Terminal 1: Python backend
cd framework
pip install -e ".[all]"
kantorku serve --config kantorku.toml

# Terminal 2: Next.js interface
cd interface
npm install
npm run dev
```

### 3c. Run CLI Only
```bash
cd cli
npm install
npm link
kantorku chat
```

---

## API Keys

kantorku mendukung 8 LLM providers. Anda tidak perlu semua — cukup yang Anda gunakan.

| Provider | Env Variable | Workers | Required? |
|----------|-------------|---------|-----------|
| Anthropic | `ANTHROPIC_API_KEY` | Conductor, coder_frontend, auditor | ✅ Recommended |
| Google | `GOOGLE_API_KEY` | coder_wiring, verifier_designer, scout | ✅ Recommended |
| MiniMax | `MINIMAX_API_KEY` | coder_backend, verifier_engineer | Optional |
| DeepSeek | `DEEPSEEK_API_KEY` | debugger, scribe, summarizer, Pool | ✅ Recommended |
| OpenAI | `OPENAI_API_KEY` | coder_wiring (Codex) | Optional |
| xAI | `XAI_API_KEY` | debugger (Grok) | Optional |
| Ollama | (local) | intake, narrator, sentinel | Optional (free, local) |
| Z-AI SDK | (built-in) | Standalone mode | ✅ For interface |

### Minimal Setup (Cheapest)

Untuk menjalankan kantorku dengan biaya minimal:
1. **Z-AI SDK** — gratis untuk standalone mode
2. **Ollama** — gratis, jalankan lokal (intake, narrator, sentinel)
3. **DeepSeek** — murah ($0.28/M) untuk support workers

---

## CLI

```bash
kantorku              # Show banner & quick start
kantorku init         # Scaffold new project
kantorku setup        # Interactive API key wizard
kantorku chat         # Chat with Conductor
kantorku serve        # Start Python backend
kantorku dev          # Start Next.js interface
kantorku worker list  # List all workers
kantorku worker show  # Show worker details
kantorku status       # System health check
kantorku version      # Show version
```

---

## Contract Lifecycle

```
IDLE → MANAGER_THINKING → TEAM_CONSULT → CLARIFYING →
CONTRACT_PRESENTED → TEAM_REVIEW → TODO_REVIEW →
CLIENT_FEEDBACK → WORKING → DONE
```

Setiap permintaan client melalui alur formal ini — memastikan transparansi, persetujuan, dan kualitas.

---

## 3-Zone Interface

| Zone | Panel | Fungsi |
|------|-------|--------|
| 🏛️ **Lobby** | Panel 1 | Client ↔ Manager chat, Interactive Questions |
| 🏗️ **Ruang Kerja** | Panel 2 | Worker grid, Contract, BriefingRoom, DAG |
| 📊 **Dashboard** | Panel 3 | Cost, Health, Metrics, Memory, Traces |

---

## Project Structure

```
kantorku/
├── framework/              # Python backend
│   ├── kantorku/           # Main package
│   │   ├── office.py       # Office class (entry point)
│   │   ├── server.py       # FastAPI + WebSocket + SSE
│   │   ├── layers/         # Conductor, BriefingRoom, GroupChannel...
│   │   ├── workers/        # 14 built-in workers
│   │   ├── providers/      # 7 LLM providers + router
│   │   ├── memory/         # 3-Ring memory system
│   │   ├── pool/           # Context pool
│   │   ├── events/         # EventBus + EventEmitter
│   │   └── ...             # DAG, hooks, cost, cache, etc.
│   ├── workers/            # Worker plugins (SKILL.md + plugin.json)
│   ├── examples/           # Usage examples
│   ├── tests/              # Test suite
│   ├── kantorku.toml       # Configuration
│   └── pyproject.toml      # Python package
│
├── interface/              # Next.js frontend
│   ├── src/
│   │   ├── app/            # Next.js App Router + API routes
│   │   ├── components/     # UI components (kantorku/ + shadcn/ui)
│   │   └── lib/kantorku/   # Types, store, workers data
│   ├── package.json
│   └── ...
│
├── cli/                    # Node.js CLI tool
│   ├── src/
│   │   ├── index.ts        # Main entry + commands
│   │   ├── commands/       # setup, chat, serve, dev, workers, status
│   │   └── lib/            # config, api client
│   ├── package.json
│   └── ...
│
├── docs/                   # Documentation
│   └── pemakaian-khusus-agents.md
├── CREDITS.md              # Credits & acknowledgments
├── README.md               # This file
├── LICENSE                 # MIT
└── .gitignore
```

---

## Configuration

### kantorku.toml
```toml
[office]
conductor_model = "anthropic/claude-opus-4-6"

[workers.coder_frontend]
model = "anthropic/claude-sonnet-4-6"
squad = "coding"
role = "React/CSS/UI specialist"

[providers.anthropic]
api_key = "${ANTHROPIC_API_KEY}"

[providers.ollama]
base_url = "http://localhost:11434/v1"

[memory]
ring1_path = "data/ring1.duckdb"
ring2_path = "data/ring2.db"

[server]
host = "0.0.0.0"
port = 8000
```

---

## Adding Custom Workers

### Via CLI
```bash
kantorku worker create my_worker --model "ollama/llama3" --squad "support"
```

### Via Manual
Buat `workers/my_worker/` dengan `plugin.json` + `SKILL.md`. Auto-discovered at startup!

Lihat [docs/pemakaian-khusus-agents.md](docs/pemakaian-khusus-agents.md) untuk panduan lengkap.

---

## Cost Optimization

| Strategy | Implementation |
|----------|---------------|
| Model routing | Cheap workers (Ollama) for simple tasks, expensive (Claude) for reasoning |
| Circuit breaker | Auto-switch provider when one is down |
| Cost guard | Middleware blocks requests when budget exceeded |
| LLM cache | Avoid redundant API calls |
| Context pool | Prefetch once, reuse many times |

Estimated costs per task (with full team):
- Simple task: ~$0.01-0.05
- Moderate task: ~$0.05-0.20
- Complex task: ~$0.20-1.00

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Credits

See [CREDITS.md](CREDITS.md) for full acknowledgments and source repositories.

---

> *"Kantor yang sesungguhnya bukan soal gedung — tapi soal orang-orang yang bekerja bersama."*
