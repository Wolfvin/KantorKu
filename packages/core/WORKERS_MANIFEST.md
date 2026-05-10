# kantorku Workers Manifest

> File ini adalah index lengkap semua worker kantorku, dikelompokkan per squad/kategori.
> AI agents: Baca file ini untuk memahami struktur worker dan cara menyusun mereka.

---

## Daftar Worker per Squad

### 🟦 CODING — Yang Nulis Kode

Worker yang bertugas menulis kode. Masing-masing punya spesialisasi berbeda dan API sendiri.

| ID | Display Name | API Provider | Model | Spesialisasi |
|----|-------------|-------------|-------|-------------|
| `coder_frontend` | Frontend Coder | Anthropic | Claude Sonnet 4.6 | React, Next.js, CSS, Tailwind, UI/Visual, Accessibility |
| `coder_backend` | Backend Coder | MiniMax | M2.7 | Python, Rust, Database, API Design, Systems |
| `coder_wiring` | Wiring Coder | Google | Gemini 3.1 Pro | API Integration, WebSocket, MCP, Glue Code, SDK |

**Cara membedakan:**
- `coder_frontend` → Yang bikin UI, komponen React, styling
- `coder_backend` → Yang bikin server, database, API handler
- `coder_wiring` → Yang nyambungin semuanya — integrasi, WebSocket, middleware

---

### 🟩 VERIFICATION — Yang Cek & Verifikasi

Worker yang bertugas mereview dan memverifikasi output. Punya API sendiri yang cocok untuk review.

| ID | Display Name | API Provider | Model | Spesialisasi |
|----|-------------|-------------|-------|-------------|
| `verifier_designer` | Design Verifier | Google | Gemini 3.1 Pro | Visual review, UX evaluation, Accessibility audit |
| `verifier_engineer` | Engineering Verifier | MiniMax | M2.5 | Logic review, Test coverage, Security audit, Performance |

**Cara membedakan:**
- `verifier_designer` → Cek dari sisi visual/UX — tampilan, warna, layout, responsif
- `verifier_engineer` → Cek dari sisi engineering — logic, security, test, performance

---

### 🟧 SUPPORT — Yang Bantuan & Analisis

Worker yang bertugas membantu kerja utama — debug, riset, review, dokumentasi, kompresi, monitoring.

| ID | Display Name | API Provider | Model | Subkategori | Spesialisasi |
|----|-------------|-------------|-------|------------|-------------|
| `debugger` | Root Cause Analyst | DeepSeek | V3.2 | debugging | Root cause analysis, stack trace, bug triage |
| `scout` | Research Agent | Google | Gemini 2.5 Pro | research | Web search, documentation, API research |
| `auditor` | Code Auditor | Anthropic | Claude Sonnet 4.6 | review | Architecture review, anti-patterns, best practices |
| `scribe` | Documentation Writer | DeepSeek | V4 Flash | documentation | API docs, README, changelog, guides |
| `summarizer` | Context Compressor | DeepSeek | V4 Flash | compression | Summarization, context compression, key points |
| `sentinel` | Error Watchdog | Ollama | Llama3 | monitoring | Error logging, lesson extraction, incident tracking |

**Cara membedakan:**
- `debugger` → Cari akar masalah bug/error — pakai DeepSeek V3.2 (murah, banyak iterasi)
- `scout` → Cari informasi dari web/dokumentasi — pakai Gemini
- `auditor` → Review arsitektur & kualitas kode — pakai Claude Sonnet
- `scribe` → Tulis dokumentasi — pakai DeepSeek (murah, long context)
- `summarizer` → Ringkas konteks panjang — pakai DeepSeek (1M context)
- `sentinel` → Log error & catat pelajaran — pakai Ollama (lokal, gratis)

---

### 🟪 TRANSLATION — Yang Parse & Format

Worker yang bertugas menerjemahkan antara client dan office — parsing input, formatting output.

| ID | Display Name | API Provider | Model | Subkategori | Spesialisasi |
|----|-------------|-------------|-------|------------|-------------|
| `intake` | Message Gatekeeper | Ollama | Llama3 | input | Message parsing, intent extraction, urgency classification |
| `narrator` | Output Storyteller | Ollama | Llama3 | output | Output formatting, client communication, presentation |

**Cara membedakan:**
- `intake` → Terima pesan dari client → parse & klasifikasi (INPUT)
- `narrator` → Format output buat client → presentasi & packaging (OUTPUT)

---

## Hubungan Antar Worker

```
CLIENT
  │
  ▼
[intake] ──parse──→ [conductor] ──orchestrate──→ [briefing_room]
                                                    │
                      ┌─────────────────────────────┤
                      │                             │
                ┌─────▼─────┐              ┌───────▼───────┐
                │  CODING   │              │  CONTEXT POOL  │
                │ frontend  │              │ (DeepSeek V3.2)│
                │ backend   │              │  x3 instances   │
                │ wiring    │              └───────┬───────┘
                └─────┬─────┘                      │
                      │                    prefetch context
                      │                      to Ring 1
                ┌─────▼──────┐
                │VERIFICATION│
                │design_judge│
                │logic_judge │
                └─────┬──────┘
                      │
          ┌───────────┼───────────┐
          │           │           │
    ┌─────▼──┐  ┌─────▼──┐  ┌────▼────┐
    │debugger│  │auditor │  │sentinel │
    │scout   │  │scribe  │  │summariz │
    └────────┘  └────────┘  └─────────┘
                      │
                      ▼
                [narrator] ──format──→ CLIENT
```

---

## API Assignment Rangkuman

| Provider | Dipakai Oleh |
|----------|-------------|
| Anthropic (Claude Sonnet 4.6) | `coder_frontend`, `auditor` |
| MiniMax (M2.7 / M2.5) | `coder_backend`, `verifier_engineer` |
| Google (Gemini 3.1 Pro) | `coder_wiring`, `verifier_designer` |
| Google (Gemini 2.5 Pro) | `scout` |
| DeepSeek (V3.2) | `debugger`, Context Pool (x3) |
| DeepSeek (V4 Flash) | `scribe`, `summarizer` |
| Ollama (Llama3, lokal) | `intake`, `narrator`, `sentinel` |
| Anthropic (Claude Opus 4.6) | Conductor (CEO) |

---

## Cara Tambah Worker Baru

Lihat [ADDING_WORKERS.md](./ADDING_WORKERS.md) untuk panduan lengkap.

Ringkasan cepat:
1. Buat folder `workers/nama_worker/` dengan `plugin.json` + `SKILL.md`
2. Set `category`, `subcategory`, `squad`, `tags` di `plugin.json`
3. Tulis SKILL.md yang detail — ini jadi system prompt
4. (Opsional) Tambah `worker.py` untuk custom logic
5. Restart → auto-discovered!
