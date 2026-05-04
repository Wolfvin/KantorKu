# kantorku — Panduan Pemasangan & Konfigurasi Lengkap

> **Kantor digital yang sesungguhnya** — Manager terima brief dari client, diskusi dengan tim, tim riset sudah mulai kerja sebelum disuruh, dan para coder tinggal verifikasi + edit konteks yang sudah disiapkan.

---

## Daftar Isi

1. [Persyaratan Sistem](#1-persyaratan-sistem)
2. [Pemasangan](#2-pemasangan)
3. [Konfigurasi](#3-konfigurasi)
4. [Setting API Keys & Ollama](#4-setting-api-keys--ollama)
5. [Quick Start](#5-quick-start)
6. [Membuat Custom Worker](#6-membuat-custom-worker)
7. [Tabel Worker & Model Assignment](#7-tabel-worker--model-assignment)
8. [Three-Ring Memory](#8-three-ring-memory)
9. [Server Mode (WebSocket)](#9-server-mode-websocket)
10. [Troubleshooting](#10-troubleshooting)
11. [Arsitektur Overview](#11-arsitektur-overview)
12. [Struktur Package](#12-struktur-package)

---

## 1. Persyaratan Sistem

### 1.1 Prasyarat Perangkat Lunak

| Komponen | Versi Minimum | Catatan |
|----------|---------------|---------|
| Python | 3.11+ | Wajib. Gunakan `python3 --version` untuk cek |
| pip | 24.0+ | Manajer paket Python |
| Git | 2.30+ | Opsional, untuk clone repository |
| Ollama | Terbaru | Opsional, untuk LLM lokal (gratis) |

### 1.2 Provider LLM yang Didukung

| Provider | Env Variable | Install Command | Harga |
|----------|-------------|-----------------|-------|
| **Ollama** | — | `pip install kantorku[ollama]` | **Gratis (lokal)** |
| Anthropic | `ANTHROPIC_API_KEY` | `pip install kantorku[anthropic]` | $3-15/1M token |
| Google | `GOOGLE_API_KEY` | `pip install kantorku[google]` | $1.25-10/1M token |
| MiniMax | `MINIMAX_API_KEY` | `pip install kantorku[minimax]` | $0.12-0.30/1M token |
| DeepSeek | `DEEPSEEK_API_KEY` | `pip install kantorku[deepseek]` | $0.27-0.28/1M token |

> **Untuk memulai tanpa biaya**, cukup gunakan Ollama. Semua worker bisa diarahkan ke model lokal — tidak ada yang mewajibkan API key berbayar.

---

## 2. Pemasangan

### 2.1 Metode A: Instal dari PyPI (Direkomendasikan)

```bash
# Instal dengan semua provider
pip install kantorku[all]

# Instal hanya provider tertentu
pip install kantorku[anthropic,deepseek]

# Instal minimal (core saja, tanpa provider cloud)
pip install kantorku

# Instal dengan Ollama (gratis, lokal)
pip install kantorku[ollama]
```

### 2.2 Metode B: Instal dari Source

```bash
git clone https://github.com/your-org/kantorku.git
cd kantorku
pip install -e ".[dev]"
python tests/test_office.py  # verifikasi
```

### 2.3 Metode C: Virtual Environment (Best Practice)

```bash
python3 -m venv kantorku-env
source kantorku-env/bin/activate    # Linux/macOS
# atau:
kantorku-env\Scripts\activate       # Windows

pip install kantorku[all]
```

### 2.4 Verifikasi Instalasi

```bash
python3 -c "from kantorku import Office; print('kantorku OK!')"
# Output: kantorku OK!

# Jalankan test suite lengkap
python3 -m pytest tests/ -v
```

---

## 3. Konfigurasi

Kantorku dikonfigurasi melalui file `kantorku.toml`. File ini adalah pusat kendali seluruh operasi — setiap worker, pool instance, dan memory tier bisa dikustomisasi dari sini.

### 3.1 Buat File Konfigurasi

```bash
cp kantorku.toml.example kantorku.toml
# atau buat manual (lihat template lengkap di bawah)
```

### 3.2 Template kantorku.toml — Lengkap

```toml
# =====================================================
# KANTORKU.TOML — KONFIGURASI LENGKAP
# =====================================================

[office]
conductor_model = "anthropic/claude-opus-4-6"
# Model untuk Conductor (CEO).
# Hanya untuk decision-making + orchestration.
# Mahal ($5/M) tapi frekuensi pakai rendah.

# ─────────────────────────────────────
# TRANSLATION LAYER — murah & cepat
# ─────────────────────────────────────

[workers.intake]
model = "ollama/llama3"
# Parsing saja — tidak butuh frontier

[workers.narrator]
model = "ollama/llama3"
# Format output saja — tidak butuh frontier

# ─────────────────────────────────────
# CODING — 3 SPESIALISASI
# ─────────────────────────────────────

[workers.coder_frontend]
model = "anthropic/claude-sonnet-4-6"
squad = "coding"
role = "React/CSS/UI/Visual specialist"
# WebDev Arena Elo: top 3
# $1.50/M — reasonable untuk frontend quality

[workers.coder_backend]
model = "minimax/minimax-m2-7"
squad = "coding"
role = "Python/Rust/Systems specialist"
# SWE-bench Pro 56.2% — #1 open-weight
# $0.30/M — 16x lebih murah dari Claude Opus

[workers.coder_wiring]
model = "google/gemini-3-1-pro"
squad = "coding"
role = "API/WS/MCP/Glue specialist"
# BFCL tool calling: 99.3 score (#1 tie)
# 1M context — lihat seluruh codebase saat wire

# ─────────────────────────────────────
# VERIFICATION — 2 SPESIALISASI
# ─────────────────────────────────────

[workers.verifier_designer]
model = "google/gemini-3-1-pro"
squad = "verification"
role = "Visual/UX judge"
# Multimodal: screenshot → judge visual quality

[workers.verifier_engineer]
model = "minimax/minimax-m2-5"
squad = "verification"
role = "Logic/test/security reviewer"
# SWE-bench Verified 80.2% | $0.12/M

# ─────────────────────────────────────
# DEEPSEEK CONTEXT POOL
# ─────────────────────────────────────

[pool]
model = "deepseek/deepseek-v3-2"
instances = 3
queue_type = "fifo"
# LiveCodeBench 83.3% | $0.28/M
# Context caching $0.028/M repeated prefixes

# ─────────────────────────────────────
# SUPPORT WORKERS
# ─────────────────────────────────────

[workers.debugger]
model = "deepseek/deepseek-v3-2"
squad = "support"
role = "Root cause analysis"
# Debugging = banyak iterasi → butuh murah

[workers.scout]
model = "google/gemini-2-5-pro"
squad = "support"
role = "Research, real-time search"
# Real-time search | 1M+ context

[workers.auditor]
model = "anthropic/claude-sonnet-4-6"
squad = "support"
role = "Code review, nuance"
# Architectural reasoning

[workers.scribe]
model = "deepseek/deepseek-v4-flash"
squad = "support"
role = "Documentation"
# Long context | murah | docs don't need frontier

[workers.summarizer]
model = "deepseek/deepseek-v4-flash"
squad = "support"
role = "Long context compression"
# 1M context | compress long histories

[workers.sentinel]
model = "ollama/llama3"
squad = "support"
role = "Error logging"
# Logging only — lokal/gratis

# ─────────────────────────────────────
# PROVIDERS — kredensial dari env vars
# ─────────────────────────────────────

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

# ─────────────────────────────────────
# MEMORY — Three-Ring System
# ─────────────────────────────────────

[memory]
ring1_path = "data/ring1.duckdb"   # Hot: DuckDB (μs latency)
ring2_path = "data/ring2.db"         # Warm: SQLite + Parquet
ring3_enabled = false                 # Cold: Cognee (Fase 3)
ring3_path = "data/ring3"

# ─────────────────────────────────────
# SERVER
# ─────────────────────────────────────

[server]
host = "0.0.0.0"
port = 8000
```

### 3.3 Konfigurasi untuk Lokal Saja (Gratis, Tanpa API Key)

Jika Anda hanya ingin menggunakan Ollama tanpa biaya, ubah semua model ke Ollama:

```toml
[office]
conductor_model = "ollama/llama3"

[workers.coder_frontend]
model = "ollama/llama3"
squad = "coding"
role = "Frontend coder"

[workers.coder_backend]
model = "ollama/deepseek-coder-v2"
squad = "coding"
role = "Backend coder"

[workers.coder_wiring]
model = "ollama/llama3"
squad = "coding"
role = "Wiring coder"

[workers.verifier_designer]
model = "ollama/llama3"
squad = "verification"

[workers.verifier_engineer]
model = "ollama/deepseek-coder-v2"
squad = "verification"

[pool]
model = "ollama/llama3"
instances = 2
queue_type = "fifo"

# Semua support workers
[workers.debugger]
model = "ollama/llama3"
squad = "support"

[workers.scout]
model = "ollama/llama3"
squad = "support"

[workers.auditor]
model = "ollama/llama3"
squad = "support"

[workers.scribe]
model = "ollama/llama3"
squad = "support"

[workers.summarizer]
model = "ollama/llama3"
squad = "support"

[workers.sentinel]
model = "ollama/llama3"
squad = "support"

[workers.intake]
model = "ollama/llama3"

[workers.narrator]
model = "ollama/llama3"

[providers.ollama]
base_url = "http://localhost:11434/v1"
```

> **Tip:** Model yang lebih besar seperti `deepseek-coder-v2` atau `codellama` memberikan hasil coding lebih baik. Gunakan `ollama list` untuk melihat model yang tersedia.

---

## 4. Setting API Keys & Ollama

### 4.1 Setup Ollama (Gratis, Direkomendasikan untuk Awal)

```bash
# Instal Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull model yang dibutuhkan
ollama pull llama3
ollama pull deepseek-coder-v2

# Verifikasi Ollama berjalan
ollama list
curl http://localhost:11434/api/tags
```

Ollama berjalan di `http://localhost:11434` secara default. Kantorku sudah dikonfigurasi untuk menggunakan endpoint ini secara otomatis.

### 4.2 Environment Variable (untuk Provider Cloud)

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="AIza..."
export MINIMAX_API_KEY="mmx-..."
export DEEPSEEK_API_KEY="sk-..."
```

### 4.3 Menggunakan .env File

```bash
# Buat .env (JANGAN commit ke Git!)
cat > .env << 'EOF'
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...
MINIMAX_API_KEY=mmx-...
DEEPSEEK_API_KEY=sk-...
EOF

# Tambahkan ke .gitignore
echo ".env" >> .gitignore

# Muat sebelum menjalankan kantorku
set -a && source .env && set +a
```

---

## 5. Quick Start

### 5.1 Programmatic API — One-Shot Run

```python
import asyncio
from kantorku import Office

async def main():
    # 1. Buat office dari config
    office = Office.from_config("kantorku.toml")
    await office.initialize()

    # 2. One-shot run (paling simpel)
    result = await office.run("Buat rate limiter di Rust")
    print(result)

    # 3. Shutdown
    await office.shutdown()

asyncio.run(main())
```

### 5.2 Step-by-Step — Panel 1 (Negosiasi) + Panel 2 (Eksekusi)

```python
office = Office.from_config("kantorku.toml")
await office.initialize()

# ── Panel 1: Chat dengan Manager ──
async for event in office.chat("session-1", "Buat rate limiter di Rust"):
    if event["type"] == "manager_message":
        print(f"Manager: {event['content']}")
    elif event["type"] == "contract_ready":
        print(f"Kontrak siap: {event['contract']}")

# Client setuju → mulai kerja
result = await office.accept_and_run("session-1")
print(result)
```

### 5.3 Programmatic API — Tanpa Config File

```python
from kantorku import Office

office = Office(conductor_model="ollama/llama3")

# Configure provider
office.configure_provider("ollama", base_url="http://localhost:11434/v1")

# Hire workers
office.hire_worker("coder_backend", model="ollama/deepseek-coder-v2", squad="coding", role="Backend")
office.hire_worker("coder_frontend", model="ollama/llama3", squad="coding", role="Frontend")
office.hire_worker("debugger", model="ollama/llama3", squad="support", role="Debugger")

await office.initialize()

# Run
result = await office.run("Implementasi autentikasi JWT di Python")
```

### 5.4 Revisi Kontrak

```python
# Jika client minta revisi
async for event in office.revise("session-1", "Tambahkan refresh token mechanism"):
    print(event)
```

---

## 6. Membuat Custom Worker

### 6.1 Worker Sederhana

```python
from kantorku import BaseWorker, Office
from kantorku.worker.base import Task, TaskResult


class SecurityAuditor(BaseWorker):
    """Custom worker untuk security audit."""

    async def handle(self, task: Task) -> TaskResult:
        # Ambil konteks yang sudah di-prefetch oleh Context Pool
        context = await self.get_context(task.id)

        prompt = f"""
        Audit keamanan untuk: {task.instruction}

        Konteks: {context or 'Tidak ada konteks prefetch'}

        Periksa:
        1. SQL injection, XSS, CSRF
        2. Authentication/Authorization
        3. Input validation
        4. Sensitive data exposure
        """

        response = await self.llm_call(prompt)
        return TaskResult(
            task_id=task.id,
            status="done",
            output=response,
        )


# Daftarkan ke Office
office = Office()
office.hire_worker(
    "security_auditor",
    model="anthropic/claude-sonnet-4-6",
    squad="verification",
    role="Security audit specialist",
    worker_class=SecurityAuditor,
)
```

### 6.2 Worker dengan Konteks Prefetch + Reactive Request

```python
class SmartCoder(BaseWorker):
    """Coder yang memanfaatkan Context Pool secara penuh."""

    async def handle(self, task: Task) -> TaskResult:
        # 1. Ambil konteks proaktif (sudah di-prefetch saat briefing)
        context = await self.get_context(task.id)

        if context:
            prompt = f"""
            Task: {task.instruction}

            Konteks yang sudah disiapkan:
            {context.get('summary', '')}
            Files: {context.get('files', [])}
            Patterns: {context.get('patterns', [])}

            Verifikasi konteks ini masih relevan, lalu implement.
            """
        else:
            # Fallback: tidak ada konteks prefetch (rare case)
            prompt = f"Task: {task.instruction}"

        result = await self.llm_call_structured(prompt)

        # 2. Jika butuh konteks tambahan mid-task (reactive)
        if result.get("needs_more_context"):
            await self.pool.request(
                worker_id=self.id,
                query=result["context_query"],
                task_id=task.id,
                session_id=task.session_id,
            )
            # Tunggu konteks baru, lalu lanjut...

        return TaskResult(
            task_id=task.id,
            status="done",
            output=str(result),
        )
```

### 6.3 Worker dengan BriefingRoom Participation

```python
class ProactiveCoder(BaseWorker):
    """Coder yang aktif berpartisipasi saat briefing."""

    async def speak_up(self, task, plan):
        """Dipanggil saat BriefingRoom — share concerns sebelum eksekusi."""
        prompt = f"""
        Task: {task.instruction}
        Plan: {plan}

        Kamu adalah {self.id} ({self.role}).
        Ada concern atau sifikasi sebelum mulai?

        Respond with JSON:
        {{
            "has_input": true/false,
            "concern": "your concern",
            "suggestion": "what you'd suggest"
        }}
        """
        return await self.llm_call_structured(prompt)

    async def receive_dm(self, from_id, message):
        """Terima pesan langsung dari worker lain."""
        prompt = f"""
        Worker {from_id} mengirim DM: "{message}"
        Kamu {self.id}. Tanggapi. Jika blocker, tandai.

        JSON: {{"response": "...", "is_blocker": true/false}}
        """
        return await self.llm_call_structured(prompt)

    async def handle(self, task):
        # ... implementasi handle ...
        pass
```

---

## 7. Tabel Worker & Model Assignment

### 7.1 Worker Utama — Dikelompokkan per Category

#### 🟦 CODING — Yang Nulis Kode

| Worker | Subcategory | Display Name | Model | Harga/1M | Benchmark |
|--------|------------|-------------|-------|----------|-----------|
| **coder_frontend** | frontend | Frontend Coder | Claude Sonnet 4.6 | $1.50 | WebDev Arena top 3 |
| **coder_backend** | backend | Backend Coder | MiniMax M2.7 | $0.30 | SWE-Pro #1 open-weight |
| **coder_wiring** | integration | Wiring Coder | Gemini 3.1 Pro | $2.00 | BFCL 99.3, 1M context |

#### 🟩 VERIFICATION — Yang Cek & Verifikasi

| Worker | Subcategory | Display Name | Model | Harga/1M | Benchmark |
|--------|------------|-------------|-------|----------|-----------|
| **verifier_designer** | visual | Design Verifier | Gemini 3.1 Pro | $2.00 | Multimodal visual judge |
| **verifier_engineer** | engineering | Engineering Verifier | MiniMax M2.5 | $0.12 | SWE 80.2%, $0.12/M |

#### 🟧 SUPPORT — Yang Bantuan & Analisis

| Worker | Subcategory | Display Name | Model | Harga/1M | Benchmark |
|--------|------------|-------------|-------|----------|-----------|
| **debugger** | debugging | Root Cause Analyst | DeepSeek V3.2 | $0.28 | Iterasi banyak → murah |
| **scout** | research | Research Agent | Gemini 2.5 Pro | $1.25 | Real-time search |
| **auditor** | review | Code Auditor | Claude Sonnet 4.6 | $1.50 | Architectural reasoning |
| **scribe** | documentation | Documentation Writer | DeepSeek V4 Flash | $0.27 | Long context, murah |
| **summarizer** | compression | Context Compressor | DeepSeek V4 Flash | $0.27 | 1M context compress |
| **sentinel** | monitoring | Error Watchdog | Llama 3 (Ollama) | gratis | Logging saja |

#### 🟪 TRANSLATION — Yang Parse & Format

| Worker | Subcategory | Display Name | Model | Harga/1M | Benchmark |
|--------|------------|-------------|-------|----------|-----------|
| **intake** | input | Message Gatekeeper | Llama 3 (Ollama) | gratis | 2600 tok/s lokal |
| **narrator** | output | Output Storyteller | Llama 3 (Ollama) | gratis | Format output saja |

#### 🎯 ORCHESTRATION — Yang Mengatur

| Worker | Model | Harga/1M | Benchmark |
|--------|-------|----------|-----------|
| **conductor** | Claude Opus 4.6 | $5.00 | SWE-bench 80.8% |

#### 🔄 CONTEXT POOL

| Worker | Model | Instances | Harga/1M | Benchmark |
|--------|-------|-----------|----------|-----------|
| **pool** | DeepSeek V3.2 | 3 | $0.28 | LiveCodeBench 83.3% |

### 7.2 Model Ollama untuk Lokal

| Model | Pull Command | Best For | RAM |
|-------|-------------|----------|-----|
| `llama3` | `ollama pull llama3` | General purpose, Conductor | 4.7GB |
| `deepseek-coder-v2` | `ollama pull deepseek-coder-v2` | Coding, Backend | 5.9GB |
| `codellama` | `ollama pull codellama` | Coding, all languages | 3.8GB |
| `mistral` | `ollama pull mistral` | Fast, general purpose | 4.1GB |
| `qwen2.5-coder` | `ollama pull qwen2.5-coder` | Coding, multilingual | 4.4GB |

---

## 8. Three-Ring Memory

### 8.1 Ring 1 — DuckDB Hot Memory

```
Latensi:    mikrodetik (in-process)
Konten:     prefetched context, session state, task results, history
Kapasitas:  sesuai RAM tersedia
Persistensi: file .duckdb di disk
```

```python
from kantorku import Ring1Memory

ring1 = Ring1Memory("data/ring1.duckdb")
await ring1.initialize()

# Store context (biasanya oleh Context Pool)
await ring1.store_context("todo-1", {
    "files": ["src/middleware/rate_limit.rs"],
    "patterns": ["token bucket"],
    "summary": "Found existing rate limiter pattern",
})

# Get context (oleh worker saat mulai kerja)
context = await ring1.get_context("todo-1")

# Session state
await ring1.store_session("session-1", {"user": "client", "status": "active"})
session = await ring1.get_session("session-1")

# History
await ring1.add_history("session-1", "user", "Buat rate limiter")
await ring1.add_history("session-1", "assistant", "Production atau internal?")
history = await ring1.get_history("session-1")
```

### 8.2 Ring 2 — SQLite Warm Memory

```
Latensi:    milidetik
Konten:     episode logs, lessons learned, audit trail
Format:     SQLite + Parquet (untuk bulk analytics)
Use case:   training data, post-mortem analysis
```

```python
from kantorku import Ring2Memory

ring2 = Ring2Memory("data/ring2.db")
await ring2.initialize()

# Log episode
await ring2.log_episode("session-1", "task_completed", {
    "todo_id": "todo-1",
    "worker_id": "coder_backend",
    "status": "done",
})

# Log lesson (oleh Sentinel)
await ring2.log_lesson("sentinel", "Always check timeout handling", "debugging")

# Query lessons
lessons = await ring2.get_lessons(category="debugging")
```

### 8.3 Ring 3 — Cognee GraphRAG Cold Memory (Fase 3)

```
Latensi:    ratusan milidetik
Konten:     knowledge graph, semantic search index
Use case:   cross-session learning, pattern discovery
Status:     Stub — akan diimplementasikan di Fase 3
```

---

## 9. Server Mode (WebSocket)

### 9.1 Menjalankan Server

```bash
# CLI
kantorku --config kantorku.toml --port 8000

# Atau dengan uvicorn langsung
uvicorn kantorku.interface.server:app --host 0.0.0.0 --port 8000
```

### 9.2 REST Endpoints

| Endpoint | Method | Deskripsi |
|----------|--------|-----------|
| `GET /` | — | Health check |
| `GET /status` | — | Worker status + pool status |
| `GET /events/{session_id}` | — | Recent events (replay/reconnect) |

### 9.3 WebSocket Channel 1: `/ws/client` (Panel 1)

Interaksi user ↔ Manager. Client mengirim pesan, menerima respons dari Conductor.

```javascript
// Connect
const ws = new WebSocket("ws://localhost:8000/ws/client");

// Kirim pesan
ws.send(JSON.stringify({
    type: "user_message",
    content: "Buat rate limiter di Rust"
}));

// Terima respons
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    // data.type: "manager_message" | "contract_ready" | "work_started" | "work_done"
    console.log(data);
};

// Setuju kontrak
ws.send(JSON.stringify({
    type: "contract_accepted",
    contract: contractData
}));

// Minta revisi
ws.send(JSON.stringify({
    type: "contract_revision",
    feedback: "Tambahkan refresh token mechanism"
}));
```

### 9.4 WebSocket Channel 2: `/ws/office` (Panel 2)

Live event stream — semua aktivitas worker, context fetch, verification.

```javascript
// Connect (butuh session_id)
const ws = new WebSocket("ws://localhost:8000/ws/office?session_id=session-1");

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    // Event types:
    // briefing_opened, plan_drafted, plan_revised
    // task_assigned, task_started, task_done, task_failed
    // worker_dm, worker_broadcast
    // context_fetch_start, context_fetch_done, context_requested, context_delivered
    // verify_design_start/done, verify_engineer_start/done
    // error_logged, skill_updated
    console.log(data);
};
```

---

## 10. Troubleshooting

### 10.1 `ModuleNotFoundError: No module named 'anthropic'`

Provider-specific package belum diinstal. Kantorku menggunakan optional dependencies.

```bash
# Solusi: instal provider yang dibutuhkan
pip install kantorku[anthropic]    # untuk Anthropic
pip install kantorku[google]       # untuk Google
pip install kantorku[minimax]      # untuk MiniMax
pip install kantorku[deepseek]     # untuk DeepSeek
pip install kantorku[ollama]       # untuk Ollama
pip install kantorku[all]          # semua sekaligus
```

### 10.2 `Provider 'anthropic' not configured`

API key belum diset atau section `[providers.*]` belum ada di kantorku.toml.

```bash
# Set API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Verifikasi
python3 -c "import os; print(os.environ.get('ANTHROPIC_API_KEY', 'NOT SET'))"
```

### 10.3 Ollama Connection Refused

```bash
# Cek apakah Ollama berjalan
curl http://localhost:11434/api/tags

# Jalankan Ollama
ollama serve

# Pull model yang dibutuhkan
ollama pull llama3
```

### 10.4 DuckDB Ring1 Error

```bash
# Error: Unable to open database file
# Solusi: buat directory
mkdir -p data
chmod 755 data
```

### 10.5 `Worker 'xxx' not found`

Worker belum diregistrasi. Tambahkan ke kantorku.toml atau hire secara programmatic.

```python
# Programmatic
office.hire_worker("my_worker", model="ollama/llama3", squad="coding", role="My worker")
```

---

## 11. Arsitektur Overview

### 11.1 Flow Lengkap

```
USER              PANEL 1           BACKEND              PANEL 2
────              ───────           ───────              ───────
"Buat rate
 limiter Rust"
    │
    ▼──────────→ ws/client
                     │
                     ▼
                Conductor.understand_client()
                "Production atau internal?"
                     │◄── manager_message
                     ▼

"Production,
 distributed"
    │
    ▼──────────→ ws/client
                     │
                     ▼
                Conductor draft contract
                     │◄── contract_ready
                     ▼

[Klik Setuju]
    │
    ▼──────────→ ws/client (contract_accepted)
                     │
                     ▼
                office.start_work()
                     │
                     ▼
                Conductor.conduct()
                     │
                     ├── briefing_opened ──────────────────→ Panel 2
                     │
                     ├── breakdown todos → prefetch paralel
                     │     ├── pool.prefetch(todo-1) ────────→ Panel 2
                     │     ├── pool.prefetch(todo-2) ────────→ Panel 2
                     │     └── pool.prefetch(todo-3) ────────→ Panel 2
                     │
                     ├── workers speak_up() paralel
                     │     ├── worker_speak_up (coder_backend) → Panel 2
                     │     └── worker_speak_up (coder_wiring)  → Panel 2
                     │
                     ├── plan_revised ───────────────────────→ Panel 2
                     │
                     ├── task_assigned → coder_backend ───────→ Panel 2
                     ├── task_assigned → coder_wiring ─────────→ Panel 2
                     │     (paralel, konteks sudah di Ring 1)
                     │
                     ├── coder_backend ←DM→ coder_wiring
                     │     worker_dm ──────────────────────────→ Panel 2
                     │
                     ├── task_done: coder_backend ────────────→ Panel 2
                     ├── task_done: coder_wiring ─────────────→ Panel 2
                     │
                     ├── verify_design_start ────────────────→ Panel 2
                     ├── verify_engineer_start ──────────────→ Panel 2
                     │
                     ├── verify_design_done ─────────────────→ Panel 2
                     ├── verify_engineer_done ───────────────→ Panel 2
                     │
                     └── error_logged (sentinel) ────────────→ Panel 2
```

### 11.2 Perbandingan Framework

| Fitur | LangGraph | CrewAI | **kantorku** |
|-------|-----------|--------|-------------|
| Orkestrasi | Manual routing | Process.sequential | **Conductor (CEO)** |
| Pre-execution | Tidak | Tidak | **BriefingRoom** |
| Worker communication | Tidak | Terbatas | **WorkerHub DM** |
| Proactive prefetch | Tidak | Tidak | **ContextPool FIFO** |
| Memory | External | Basic | **3-Ring (hot/warm/cold)** |
| Contract negotiation | Tidak | Tidak | **Client ↔ Manager** |
| Real-time UI | Tidak | Tidak | **Dual WebSocket** |
| Worker plugin system | Tidak | Terbatas | **plugin.json + SKILL.md** |

### 11.3 Konsep Unik kantorku

- **Conductor** bukan router — ia *berpikir* dan membuat keputusan cerdas berdasarkan konteks
- **BriefingRoom** — workers diskusi *sebelum* eksekusi, bukan setelah error
- **ContextPool** — konteks di-prefetch *saat briefing*, bukan saat worker mulai kerja
- **Contract flow** — client negosiasi dulu, setuju baru kerja dimulai
- **WorkerHub DM** — workers bisa ngobrol sesama, bukan hanya terima perintah
- **Three-Ring Memory** — hot/warm/cold tiers seperti CPU cache

---

## 12. Struktur Package

```
kantorku/
├── pyproject.toml              # pip installable
├── kantorku.toml               # Config template
├── kantorku/
│   ├── __init__.py             # Public API exports
│   ├── office.py               # Office — main entry point
│   ├── server.py               # FastAPI + 2 WebSocket channels
│   ├── cli.py                  # CLI entry point
│   ├── worker/
│   │   ├── base.py             # BaseWorker, Task, TaskResult, WorkerStatus
│   │   ├── registry.py         # WorkerRegistry — hire/fire/discover
│   │   └── identity.py         # WorkerIdentity — plugin.json + SKILL.md
│   ├── layers/
│   │   ├── conductor.py        # Conductor — CEO, contract, orchestration
│   │   ├── briefing_room.py    # BriefingRoom — workers discuss + prefetch
│   │   ├── worker_hub.py       # WorkerHub — DM peer-to-peer + broadcast
│   │   └── intake.py           # Intake — parse freeform → structured
│   ├── pool/
│   │   ├── context_pool.py     # ContextPool — FIFO queue, prefetch/reactive
│   │   ├── pool_worker.py      # PoolWorker — single DeepSeek instance
│   │   └── context_store.py    # Store results to Ring 1
│   ├── memory/
│   │   ├── ring1.py            # Ring1 — DuckDB hot memory
│   │   ├── ring2.py            # Ring2 — SQLite warm memory
│   │   └── ring3.py            # Ring3 — Cognee stub (Fase 3)
│   ├── events/
│   │   ├── bus.py              # EventBus — pub/sub per session
│   │   └── emitter.py          # EventEmitter — typed convenience
│   ├── providers/
│   │   ├── router.py           # ProviderRouter — "provider/model" dispatch
│   │   ├── base.py             # BaseProvider abstract
│   │   ├── anthropic_provider.py
│   │   ├── google_provider.py
│   │   ├── openai_compat.py    # MiniMax + DeepSeek
│   │   └── ollama_provider.py
│   ├── config/
│   │   └── settings.py         # KantorkuConfig, WorkerConfig, PoolConfig
│   └── workers/                # 12 built-in worker implementations
│       ├── coder_frontend.py
│       ├── coder_backend.py
│       ├── coder_wiring.py
│       ├── verifier_designer.py
│       ├── verifier_engineer.py
│       ├── debugger.py
│       ├── scout.py
│       ├── auditor.py
│       ├── scribe.py
│       ├── summarizer.py
│       ├── sentinel.py
│       ├── intake_worker.py
│       └── narrator.py
├── workers/                    # Worker plugin directories
│   ├── coder_frontend/plugin.json
│   ├── coder_backend/plugin.json
│   └── ...
└── tests/
    └── test_office.py          # 9 integration tests — ALL PASS ✓
```

---

## Dependency Graph

```
kantorku core (always installed):
  fastapi, uvicorn, websockets, httpx,
  pydantic, pydantic-settings, toml,
  duckdb, aiosqlite, pyarrow, anyio

Optional (per provider):
  [anthropic] → anthropic
  [google]    → google-genai
  [minimax]   → openai
  [deepseek]  → openai
  [ollama]    → openai

Dev:
  [dev] → pytest, pytest-asyncio, ruff
```

---

*kantorku — karena kantor yang baik bukan yang paling canggih, tapi yang paling tahu siapa harus mengerjakan apa.*
