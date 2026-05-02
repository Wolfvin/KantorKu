# Cara Menambah Worker di Kantorku

Panduan lengkap untuk menambah worker baru ke framework kantorku.

---

## Apa Itu Worker?

Worker di kantorku **BUKAN cuma LLM wrapper**. Setiap worker adalah **agent independen** yang punya:

- **API sendiri** — Bisa beda provider, beda API key, beda model
- **Category & Subcategory** — Kategorisasi jelas supaya AI agents bisa susun
- **Tags** — Tag searchable untuk discovery dan organisasi
- **SKILL.md** — Deskripsi skill yang jadi system prompt
- **worker.py** — Custom logic (opsional, kalau mau behavior yang lebih kompleks)
- **plugin.json** — Konfigurasi mesin (metadata + API config + categorization)

**Contoh nyata:**

| Worker | Category | Subcategory | API | Alasan |
|--------|----------|-------------|-----|--------|
| `coder_frontend` | coding | frontend | Anthropic Claude Sonnet | Bagus untuk UI/visual |
| `coder_wiring` | coding | integration | OpenAI Codex 5.3 | Bagus untuk API/glue code |
| `verifier_designer` | verification | visual | Google Gemini 2.5 Pro | Bagus untuk visual review |
| `debugger` | support | debugging | xAI Grok 3 | Bagus untuk root cause analysis |
| `scribe` | support | documentation | DeepSeek V4 Flash | Murah untuk dokumentasi |
| `sentinel` | support | monitoring | Ollama Llama3 (local) | Gak perlu API key |

---

## Kategorisasi Worker

Kantorku mengelompokkan worker berdasarkan **category** (utama) dan **subcategory** (detail):

### 🟦 CODING — Yang Nulis Kode

| ID | Subcategory | Display Name | API | Spesialisasi |
|----|------------|-------------|-----|-------------|
| `coder_frontend` | frontend | Frontend Coder | Anthropic Claude Sonnet | React, CSS, UI/Visual |
| `coder_backend` | backend | Backend Coder | MiniMax M2.7 | Python, Rust, Systems |
| `coder_wiring` | integration | Wiring Coder | OpenAI Codex 5.3 | API, WebSocket, MCP, Glue |

### 🟩 VERIFICATION — Yang Cek & Verifikasi

| ID | Subcategory | Display Name | API | Spesialisasi |
|----|------------|-------------|-----|-------------|
| `verifier_designer` | visual | Design Verifier | Google Gemini 2.5 Pro | Visual/UX review |
| `verifier_engineer` | engineering | Engineering Verifier | MiniMax M2.5 | Logic/security review |

### 🟧 SUPPORT — Yang Bantuan & Analisis

| ID | Subcategory | Display Name | API | Spesialisasi |
|----|------------|-------------|-----|-------------|
| `debugger` | debugging | Root Cause Analyst | xAI Grok 3 | Root cause analysis |
| `scout` | research | Research Agent | Google Gemini 2.5 Pro | Web search, documentation |
| `auditor` | review | Code Auditor | Anthropic Claude Sonnet | Architecture review |
| `scribe` | documentation | Documentation Writer | DeepSeek V4 Flash | API docs, README |
| `summarizer` | compression | Context Compressor | DeepSeek V4 Flash | Summarization |
| `sentinel` | monitoring | Error Watchdog | Ollama Llama3 | Error logging, lessons |

### 🟪 TRANSLATION — Yang Parse & Format

| ID | Subcategory | Display Name | API | Spesialisasi |
|----|------------|-------------|-----|-------------|
| `intake` | input | Message Gatekeeper | Ollama Llama3 | Parse pesan client |
| `narrator` | output | Output Storyteller | Ollama Llama3 | Format output buat client |

---

## Struktur Direktori Worker

```
workers/
└── nama_worker/
    ├── plugin.json    ← WAJIB — metadata + API config + categorization
    ├── SKILL.md       ← REKOMENDED — system prompt
    ├── worker.py      ← OPSIONAL — custom BaseWorker subclass
    └── __init__.py    ← OPSIONAL — Python package exports
```

---

## plugin.json — Konfigurasi Mesin

### Format Lengkap (Rekomended)

```json
{
  "id": "coder_frontend",
  "category": "coding",
  "subcategory": "frontend",
  "display_name": "Frontend Coder",
  "api": {
    "provider": "anthropic",
    "model": "claude-sonnet-4-20250514",
    "api_key": "${ANTHROPIC_API_KEY}"
  },
  "squad": "coding",
  "role": "React/CSS/UI/Visual Specialist",
  "description": "Writes frontend code — React, Next.js, CSS, Tailwind, component architecture, visual quality, accessibility",
  "tags": ["react", "nextjs", "css", "tailwind", "component-architecture", "accessibility", "ui", "visual"],
  "capabilities": ["react", "nextjs", "css", "tailwind", "component-architecture", "accessibility"],
  "interacts_with": ["coder_wiring", "verifier_designer", "auditor"]
}
```

### Field — Detail

| Field | Wajib | Contoh | Penjelasan |
|-------|-------|--------|------------|
| `id` | YA | `"coder_frontend"` | Identifier unik |
| `category` | YA | `"coding"`, `"verification"`, `"support"`, `"translation"` | Kategori utama — supaya AI agents bisa kelompokkan |
| `subcategory` | TIDAK | `"frontend"`, `"backend"`, `"debugging"` | Sub-kategori — detail spesialisasi |
| `display_name` | TIDAK | `"Frontend Coder"` | Nama yang manusiawi — untuk display & AI agents |
| `api.provider` | YA | `"google"`, `"anthropic"`, `"openai"`, `"xai"`, `"deepseek"`, `"minimax"`, `"ollama"` | Provider AI yang dipakai worker ini |
| `api.model` | YA | `"gemini-2.5-pro"`, `"codex-5.3"`, `"grok-3"` | Model TANPA prefix provider |
| `api.api_key` | TIDAK | `"${GOOGLE_API_KEY}"`, `"sk-..."` | API key. Pakai `${ENV_VAR}` untuk env var |
| `api.base_url` | TIDAK | `"https://api.x.ai/v1"`, `"http://localhost:11434"` | Custom base URL |
| `api.extra` | TIDAK | `{"temperature": 0.7}` | Parameter tambahan |
| `squad` | YA | `"coding"`, `"verification"`, `"support"`, `"translation"` | Squad membership (sama seperti category) |
| `role` | YA | `"React/CSS/UI/Visual Specialist"` | Deskripsi peran |
| `description` | TIDAK | `"Writes frontend code..."` | Deskripsi detail — untuk AI agents |
| `tags` | TIDAK | `["react", "css", "ui"]` | Tag searchable — supaya AI agents bisa cari |
| `capabilities` | TIDAK | `["react", "nextjs"]` | Daftar kapabilitas |
| `interacts_with` | TIDAK | `["coder_wiring", "auditor"]` | Worker mana yang sering berinteraksi |

### Provider yang Didukung

| Provider | Class | Keperluan |
|----------|-------|-----------|
| `anthropic` | AnthropicProvider | `api_key` |
| `google` | GoogleProvider | `api_key` |
| `openai` | (OpenAI-compatible) | `api_key` |
| `xai` | (OpenAI-compatible) | `api_key`, `base_url` |
| `deepseek` | DeepSeekProvider | `api_key` |
| `minimax` | MiniMaxProvider | `api_key` |
| `ollama` | OllamaProvider | `base_url` (default localhost:11434) |

---

## Cara Menambah Worker

### Metode 1: CLI (Paling Gampang)

```bash
# Create worker dengan kategorisasi lengkap
kantorku worker create image_gen \
  --squad support \
  --category support \
  --subcategory "image-generation" \
  --display-name "Image Generator" \
  --model "openai/dall-e-3" \
  --tags "image,dalle,visual,generation" \
  --capabilities "image-generation,visual"

# Validate
kantorku worker validate workers/image_gen/

# Lihat semua worker (dikelompokkan per category)
kantorku worker list
```

### Metode 2: Drop Folder (Plug-and-Play)

1. Buat folder `workers/nama_worker/`
2. Buat `plugin.json` dengan **category, subcategory, tags** yang jelas
3. Buat `SKILL.md` dengan deskripsi skill
4. (Opsional) Buat `worker.py` dengan custom logic
5. Restart kantorku → auto-discovered!

### Metode 3: Programmatic

```python
from kantorku import Office, WorkerAPI, BaseWorker, Task, TaskResult

office = Office()

# Cara A: Dari directory (auto-discovers category dari plugin.json)
office.hire_worker("image_gen", path="workers/image_gen/")

# Cara B: Dengan custom class + category info
class ImageGen(BaseWorker):
    async def handle(self, task):
        result = await self.api_call("POST", "https://api.openai.com/v1/images/generations",
                                     json={"model": "dall-e-3", "prompt": task.instruction})
        return TaskResult(task_id=task.id, status="done", output=str(result))

office.hire_worker(
    "image_gen",
    model="openai/dall-e-3",
    squad="support",
    worker_class=ImageGen,
)

# Cara C: Hot-plug saat runtime
worker = await office.hot_plug_worker("workers/image_gen/")
result = await worker.execute(task)
```

### Metode 4: Query by Category

```python
# Setelah initialize
await office.initialize()

# Lihat semua worker dikelompokkan per category
categories = office.registry.categories
# {"coding": ["coder_frontend", "coder_backend", "coder_wiring"],
#  "verification": ["verifier_designer", "verifier_engineer"],
#  "support": ["debugger", "scout", "auditor", "scribe", "summarizer", "sentinel"],
#  "translation": ["intake", "narrator"]}

# Query by category
coding_workers = office.registry.list_by_category("coding")
debugging_workers = office.registry.list_by_subcategory("debugging")

# Lihat detail worker
for w in office.registry.list_workers():
    print(f"{w['id']:25s} [{w['category']}/{w['subcategory']}] {w['display_name']}")
```

### Metode 5: TOML Config

```toml
# kantorku.toml

[workers.image_gen]
category = "support"
subcategory = "image-generation"
model = "openai/dall-e-3"
squad = "support"
role = "Image generation specialist"
```

### Metode 6: Pip Package (Advanced)

Buat package Python yang expose worker via entry point:

```toml
# pyproject.toml di package kamu
[project.entry-points."kantorku.workers"]
image_gen = "my_package.workers:ImageGenWorker"
```

---

## SKILL.md — System Prompt

SKILL.md adalah **system prompt** yang otomatis diinject ke LLM saat worker berjalan. Semakin detail, semakin bagus hasilnya.

**TIPS**: Tulis SKILL.md yang menjelaskan:
1. Role jelas — apa worker ini kerjakan
2. Expertise — skill spesifik
3. Interaction — worker mana yang sering diajak kerja sama
4. Output — apa yang dihasilkan
5. Methodology — langkah-langkah kerja

---

## worker.py — Custom Logic

Kalau worker cuma butuh LLM call, **tidak perlu worker.py**. SKILL.md saja cukup.

Kalau butuh logic khusus, buat `worker.py`:

```python
from kantorku.worker.base import BaseWorker, Task, TaskResult


class Worker(BaseWorker):
    """Custom worker dengan logic sendiri."""

    async def handle(self, task: Task) -> TaskResult:
        # self.llm_call() otomatis pakai API milik worker ini
        response = await self.llm_call(
            f"Task: {task.instruction}\n\nContext: {task.context}"
        )

        return TaskResult(
            task_id=task.id,
            status="done",
            output=response,
        )
```

### API yang Tersedia di worker.py

| Method | Penjelasan |
|--------|------------|
| `self.llm_call(prompt)` | LLM call pakai API worker ini (otomatis) |
| `self.llm_call_structured(prompt)` | LLM call → parse JSON |
| `self.llm_call_stream(prompt)` | LLM call → stream tokens |
| `self.api_call(method, url)` | HTTP call pakai API key worker ini |
| `self.get_context(task.id)` | Ambil context dari Ring1 |
| `self.identity.api` | Akses WorkerAPI config langsung |
| `self.identity.category` | Category worker ini |
| `self.identity.tags` | Tags worker ini |

---

## FAQ

### Q: Kenapa perlu category dan subcategory?
Supaya AI agents bisa **otomatis kelompokkan** worker. Tanpa kategorisasi yang jelas, AI agents gak bisa bedain `coder_frontend` dengan `coder_backend` dengan `coder_wiring`. Dengan category + subcategory + tags, AI agents bisa langsung paham: "frontend itu yang bikin UI, backend itu yang bikin server, wiring itu yang nyambungin."

### Q: Apakah setiap worker HARUS punya API sendiri?
Tidak. Kalau worker pakai API global (yang di-config di `[providers.*]`), cukup set `api.provider` dan `api.model` tanpa `api_key`. Worker akan reuse provider yang sudah di-config.

### Q: Bisa pakai provider yang belum di-support?
Ya! Set `api.base_url` ke endpoint custom, dan worker akan call ke sana. Provider apapun yang OpenAI-compatible bisa dipakai.

### Q: Tags vs Capabilities — apa bedanya?
- `capabilities` = apa yang worker BISA lakukan (fungsi teknis)
- `tags` = keyword searchable untuk AI agents (bisa lebih luas, termasuk konteks bisnis)

Contoh: `capabilities: ["api-design"]`, `tags: ["api-design", "integration", "middleware", "sdk"]`

### Q: Bisa worker call API lain (bukan LLM)?
Ya! Pakai `self.api_call(method, url)` di worker.py. API key dari plugin.json otomatis diinject sebagai Bearer token.

### Q: Bagaimana kalau mau bikin squad/category custom?
Bebas! Category cuma string. Tambahin aja `"category": "security"` atau `"category": "data"`. Yang penting konsisten.
