# Pemakaian Khusus AI Agents

> Panduan lengkap untuk menggunakan kantorku sebagai AI agent orchestration framework.
> Ditujukan untuk developer dan AI agents yang ingin membangun sistem multi-agent.

---

## Apa itu kantorku?

kantorku adalah framework orchestrasi AI worker yang memodelkan kantor digital sesungguhnya. Setiap worker punya peran, spesialisasi, dan model LLM yang berbeda. Semua berkoordinasi melalui Conductor (CEO) yang mengatur alur kerja berdasarkan kontrak (contract).

**Analogi**: Bayangkan sebuah kantor developer sungguhan — ada CEO (Conductor), programmer frontend/backend, QA, auditor, dan sebagainya. Mereka rapat (BriefingRoom), diskusi (GroupChannel), dan kerja sesuai tugas masing-masing.

---

## Arsitektur 3 Komponen

```
┌─────────────────────────────────────────────────────┐
│                    kantorku                          │
├──────────────┬──────────────────┬───────────────────┤
│  web-ui/     │   framework/     │     cli/          │
│  (Next.js)   │   (Python)       │   (Node.js)       │
│              │                  │                   │
│  Web UI      │  Backend engine  │  Terminal tool    │
│  Dashboard   │  Workers         │  Setup wizard     │
│  Chat panel  │  Memory          │  Chat mode        │
│  Monitoring  │  Providers       │  Worker mgmt      │
│  Settings    │  Events          │  Status check     │
└──────────────┴──────────────────┴───────────────────┘
```

---

## Quick Start untuk Agents

### 1. Setup API Keys (WAJIB)

Sebelum menjalankan kantorku, Anda perlu mengatur API keys untuk LLM providers.

**Via CLI (Recommended)**:
```bash
cd cli && npm install && npm link
kantorku setup
```

Wizard akan menanyakan:
- Anthropic API Key (untuk Conductor, coder_frontend, auditor)
- Google API Key (untuk verifier_designer, scout)
- MiniMax API Key (untuk coder_backend, verifier_engineer)
- DeepSeek API Key (untuk debugger, scribe, summarizer, Context Pool)
- OpenAI API Key (untuk coder_wiring)
- xAI API Key (untuk debugger alternatif)
- Ollama Base URL (untuk intake, narrator, sentinel — default: localhost:11434)
- Z-AI SDK Key (untuk standalone mode tanpa Python backend)

**Via Environment Variables**:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="AIza..."
export MINIMAX_API_KEY="..."
export DEEPSEEK_API_KEY="sk-..."
export OPENAI_API_KEY="sk-..."
export XAI_API_KEY="xai-..."
```

**Via Interface Settings**:
Buka kantorku UI → klik Settings (gear icon) → masukkan API keys per provider.

### 2. Pilih Mode Operasi

#### Mode A: Standalone (Tanpa Python Backend)
```bash
cd web-ui && npm install && npm run dev
```
Cukup gunakan Next.js web-ui. LLM calls langsung via z-ai-web-dev-sdk. Tidak perlu Python.

#### Mode B: Full Stack (Python Backend + Next.js Web UI)
```bash
# Terminal 1: Start Python backend
cd framework && pip install -e . && kantorku serve

# Terminal 2: Start Next.js web-ui
cd web-ui && npm install && npm run dev
```

#### Mode C: CLI Only
```bash
cd cli && npm install && npm link
kantorku chat  # Interactive chat with Conductor
```

### 3. Gunakan!

- **Chat dengan Manager**: Kirim pesan di Lobby Zone → Conductor akan merespons
- **Ajukan pertanyaan**: Manager bisa mengajukan pertanyaan dengan pilihan A/B/C/Other (seperti Claude)
- **Monitor workers**: Lihat status workers di Ruang Kerja
- **Cek biaya**: Dashboard menampilkan cost, latency, health metrics

---

## Contract Lifecycle

Setiap permintaan client melalui alur ini:

```
IDLE → MANAGER_THINKING → TEAM_CONSULT → CLARIFYING →
CONTRACT_PRESENTED → TEAM_REVIEW → TODO_REVIEW →
CLIENT_FEEDBACK → WORKING → DONE
```

### Penjelasan Setiap State:

| State | Deskripsi | Yang Terjadi |
|-------|-----------|-------------|
| `IDLE` | Menunggu input | Tidak ada kontrak aktif |
| `MANAGER_THINKING` | Conductor menganalisis | Intake + Conductor memahami kebutuhan client |
| `TEAM_CONSULT` | Tim diskusi | BriefingRoom — workers diskusi rencana |
| `CLARIFYING` | Manager bertanya | Interactive Question — pilihan A/B/C/Other |
| `CONTRACT_PRESENTED` | Kontrak ditampilkan | Client bisa approve/reject |
| `TEAM_REVIEW` | Review tim | GroupChannel — workers review kontrak |
| `TODO_REVIEW` | Review TODO | TodoReviewPhase — tim cek daftar tugas |
| `CLIENT_FEEDBACK` | Feedback client | Client memberi masukan |
| `WORKING` | Eksekusi | DAG-resolved parallel execution |
| `DONE` | Selesai | Debrief + lessons learned |

---

## Workers & Assignments

### Worker Categories

#### Coding Squad (Yang Nulis Kode)
| Worker | Model | Spesialisasi |
|--------|-------|-------------|
| `coder_frontend` | Claude Sonnet 4.6 | React, CSS, Tailwind, UI/Visual |
| `coder_backend` | MiniMax M2.7 | Python, Rust, API, Database |
| `coder_wiring` | Gemini 3.1 Pro | Integration, WebSocket, MCP |

#### Verification Squad (Yang Cek & Verifikasi)
| Worker | Model | Spesialisasi |
|--------|-------|-------------|
| `verifier_designer` | Gemini 3.1 Pro | Visual review, UX evaluation |
| `verifier_engineer` | MiniMax M2.5 | Logic, security, performance |

#### Support Squad (Yang Bantuan & Analisis)
| Worker | Model | Spesialisasi |
|--------|-------|-------------|
| `debugger` | DeepSeek V3.2 | Root cause analysis |
| `scout` | Gemini 2.5 Pro | Research, documentation |
| `auditor` | Claude Sonnet 4.6 | Architecture review |
| `scribe` | DeepSeek V4 Flash | Documentation writing |
| `summarizer` | DeepSeek V4 Flash | Context compression |
| `sentinel` | Ollama Llama3 | Error monitoring |

#### Translation Squad (Yang Parse & Format)
| Worker | Model | Spesialisasi |
|--------|-------|-------------|
| `intake` | Ollama Llama3 | Message parsing |
| `narrator` | Ollama Llama3 | Output formatting |

### Context Pool
| Komponen | Model | Fungsi |
|----------|-------|--------|
| Context Pool (x3) | DeepSeek V3.2 | Proactive context prefetch |

---

## Cara Tambah Worker Baru

### Metode 1: CLI
```bash
kantorku worker create my_worker --model "ollama/llama3" --squad "support"
```

### Metode 2: Manual
Buat folder `workers/my_worker/` dengan file:

**plugin.json**:
```json
{
  "id": "my_worker",
  "model": "ollama/llama3",
  "squad": "support",
  "role": "My custom worker",
  "capabilities": ["custom_task"],
  "category": "support",
  "subcategory": "custom"
}
```

**SKILL.md**:
```markdown
# My Worker

You are a specialist in custom_task.

## Responsibilities
- Handle custom requests
- Provide expert analysis

## Output Format
Always respond in JSON with keys: result, confidence, notes
```

Worker akan auto-discovered saat startup!

---

## 3-Ring Memory System

| Ring | Engine | Kegunaan | Persistence |
|------|--------|----------|-------------|
| Ring 1 | DuckDB | Hot/session memory — konteks percakapan aktif | Session |
| Ring 2 | SQLite | Warm/episodes — pelajaran dari sesi sebelumnya | Persistent |
| Ring 3 | Vector DB | Cold/knowledge — pengetahuan jangka panjang | Optional |

### Menggunakan Memory:
```python
from kantorku import Office

office = Office.from_config("kantorku.toml")
await office.initialize()

# Store ke Ring 1
await office.memory.ring1.store("key", {"data": "value"})

# Query dari Ring 2
results = await office.memory.ring2.query("similar to this")

# Prefetch via Context Pool
await office.pool.prefetch("topic for context")
```

---

## Event System & Real-time

### Event Types
kantorku mengirim event real-time melalui WebSocket dan SSE:

| Channel | Endpoint | Kegunaan |
|---------|----------|----------|
| Client WS | `/ws/client` | Client ↔ Manager messages |
| Workers WS | `/ws/workers` | Worker activity & status |
| Office WS | `/ws/office` | Full office events |
| SSE Stream | `/events/stream/{session_id}` | Server-Sent Events fallback |

### Event Flow:
```javascript
// Frontend (Next.js)
const ws = new WebSocket('ws://localhost:8000/ws/client');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // data.type: 'worker_status' | 'contract_update' | 'chat_message' | etc.
};
```

---

## Provider Configuration

### kantorku.toml
```toml
[office]
conductor_model = "anthropic/claude-opus-4-6"

[providers.anthropic]
api_key = "${ANTHROPIC_API_KEY}"

[providers.google]
api_key = "${GOOGLE_API_KEY}"

[providers.minimax]
api_key = "${MINIMAX_API_KEY}"

[providers.deepseek]
api_key = "${DEEPSEEK_API_KEY}"

[providers.ollama]
base_url = "http://localhost:11434/v1"

[workers.coder_frontend]
model = "anthropic/claude-sonnet-4-6"
squad = "coding"
role = "React/CSS/UI specialist"
```

### Cost Optimization
kantorku dirancang untuk optimasi biaya:

| Strategi | Implementasi |
|----------|-------------|
| **Model routing** | Worker murah untuk tugas sederhana (Ollama), model mahal untuk reasoning (Claude Opus) |
| **Circuit breaker** | Auto-switch provider kalau satu down |
| **Cost guard** | Middleware yang blokir request kalau budget habis |
| **LLM cache** | Hindari repeated API calls untuk prompt yang sama |
| **Context pool** | Prefetch konteks sekali, pakai berkali-kali |

---

## Interactive Question Feature

Manager (Conductor) bisa mengajukan pertanyaan kepada client dengan pilihan:

```
Manager: "Framework apa yang ingin digunakan?"
  [A] React
  [B] Vue
  [C] Svelte
  [Other] Ketik jawaban custom...
```

Client tinggal klik pilihan — tidak perlu mengetik. Fitur ini mirip dengan Claude's interactive questions.

### Implementasi:
```
[ASK]
question: Framework apa yang ingin digunakan?
A: React
B: Vue
C: Svelte
[/ASK]
```

---

## API Reference

### Chat Endpoint
```http
POST /api/chat
Content-Type: application/json

{
  "message": "Buatkan REST API untuk e-commerce",
  "session_id": "optional-session-id"
}
```

Response:
```json
{
  "type": "manager_message",
  "content": "Baik, saya akan menyusun kontrak..."
}
```

### Execute Endpoint
```http
POST /api/execute
Content-Type: application/json

{
  "contract_id": "contract-123",
  "session_id": "session-456"
}
```

### Briefing Endpoint
```http
POST /api/briefing
Content-Type: application/json

{
  "session_id": "session-456",
  "topic": "E-commerce REST API"
}
```

### Health Endpoint
```http
GET /api/health
```

---

## Tips untuk AI Agents

### 1. Pahami Worker Spesialisasi
Jangan assign tugas frontend ke `coder_backend` — setiap worker punya spesialisasi yang jelas.

### 2. Gunakan Interactive Questions
Kalau kebutuhan client tidak jelas, gunakan format `[ASK]...[/ASK]` untuk bertanya dengan pilihan.

### 3. Manfaatkan Context Pool
Sebelum task dimulai, Context Pool sudah prefetch konteks relevan ke Ring 1 memory.

### 4. Check Trust Scores
Workers dengan trust score tinggi lebih reliable. Check di Dashboard sebelum delegasi tugas penting.

### 5. Monitor Circuit Breakers
Kalau provider down, circuit breaker otomatis switch ke provider cadangan.

### 6. Budget Management
Set `budget_limit` di kontrak untuk mencegah cost overrun. Cost guard middleware akan blokir request kalau budget habis.

### 7. DAG Execution
Tasks yang tidak bergantung satu sama lain akan dijalankan secara parallel oleh DAG resolver.

---

## Troubleshooting

### "No API key configured"
Jalankan `kantorku setup` atau atur API keys di Settings.

### "Circuit breaker open"
Provider sedang down. Tunggu recovery timeout atau reset manual via Dashboard.

### "Worker not ready"
Worker belum selesai initialize. Tunggu beberapa detik atau restart.

### "Budget exceeded"
Cost guard memblokir request. Naikkan budget limit atau check cost report.

---

> *"Di kantorku, setiap worker punya peran, setiap peran punya tujuan, dan setiap tujuan tercapai melalui kolaborasi."*
