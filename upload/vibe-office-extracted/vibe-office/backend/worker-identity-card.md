# Backend — Worker Identity Card Format

> **Konteks untuk session baru:**
> Di vibe-office, setiap worker bukan hanya JSON profile flat.
> Worker punya "kartu identitas" berstruktur yang bisa dibaca manusia DAN AI.
> Format ini terinspirasi dari dua sumber:
> - `anthropics/claude-plugins-official` (github.com/anthropics/claude-plugins-official)
>   → struktur plugin.json + SKILL.md per plugin
> - `InsForge` (github.com/InsForge/InsForge)
>   → konsep semantic layer: data diformat agar AI bisa understand, reason, dan operate

---

## Masalah yang Dipecahkan

Format lama `workers.json` flat:
```json
{ "id": "rust_worker", "model": "qwen2.5", "tone": "terse" }
```

AR Orchestrator tidak tahu: kapan harus assign ke worker ini? Apa batasannya?
Apa yang pernah berhasil/gagal? Format ini harus dibaca manusia dulu baru berguna.

Format baru: **setiap worker adalah folder dengan SKILL.md**.
Orchestrator bisa langsung baca dan mengerti kapabilitas worker tanpa hardcode.

---

## Struktur Folder

```
~/.vibe-office/workers/
├── rust_worker/
│   ├── plugin.json       ← metadata mesin (version, model, timeout, capabilities)
│   ├── SKILL.md          ← kapabilitas dalam bahasa natural, dibaca AI
│   └── references/
│       ├── examples/     ← contoh task sukses (untuk orchestrator planning)
│       └── failures/     ← contoh task yang gagal + kenapa (untuk dLLM)
├── tester_worker/
│   ├── plugin.json
│   ├── SKILL.md
│   └── references/
├── context_worker/
│   ├── plugin.json
│   ├── SKILL.md
│   └── references/
└── ... (semua 11 workers)
```

---

## plugin.json — Metadata Mesin

Dibaca oleh WorkerManager saat startup. Format terinspirasi dari
`claude-plugins-official` plugin.json schema.

```json
{
  "id": "rust_worker",
  "version": "1.0.0",
  "display_name": "Rusty",
  "badge_emoji": "🦀",
  "model": "qwen2.5-coder-7b-finetuned",
  "model_type": "llm_finetuned",
  "timeout_seconds": 60,
  "max_retries": 2,
  "status": "active",
  "room": "workstation",
  "capabilities": ["write_code", "debug", "refactor"],
  "requires_env": ["rust_toolchain"],
  "personality": {
    "tone": "terse",
    "catchphrase": "borrow checker says no.",
    "system_prompt_addon": "You are terse and precise. Prefer short sentences."
  },
  "stats": {
    "tasks_done": 0,
    "errors": 0,
    "hired_at": "2026-03-16"
  }
}
```

---

## SKILL.md — Kapabilitas untuk AI

Dibaca oleh AR Orchestrator saat planning task assignment.
Format terinspirasi dari `claude-plugins-official` SKILL.md standard dan
`hermes-agent` skills system (github.com/NousResearch/hermes-agent).

```markdown
---
name: rust_worker
description: Specialist Rust programmer — write, debug, refactor idiomatic Rust code
version: 1.0.0
---

# rust_worker

## Kapan Gunakan Worker Ini
- Task: write_code, debug, refactor untuk kode Rust
- Input sudah punya context dari context_worker (GitNexus analysis)
- Butuh kode yang compile dan idiomatis

## Apa yang Bisa Dilakukan
- Menulis fungsi Rust baru dari instruksi natural language
- Debug compile error dan logic error
- Refactor kode yang sudah ada
- Handle async/await, lifetimes, traits, error propagation dengan benar

## Apa yang TIDAK Bisa Dilakukan
- Tidak bisa run/execute kode (itu tugas tester_worker)
- Tidak bisa commit ke git (itu tugas git_worker)
- Tidak bisa tulis dokumentasi (itu tugas docs_worker)
- Tidak cocok untuk JS/CSS/HTML — gunakan worker lain

## Input yang Dibutuhkan
- instruction: string (bahasa Inggris, spesifik)
- context.codebase_context: dari context_worker (GitNexus output)
- context.language: "rust"

## Output yang Dihasilkan
```json
{
  "code": "...",
  "explanation": "...",
  "files_modified": ["src/http.rs"],
  "warnings": ["..."],
  "changes": [{"type": "new_public_function", "name": "...", "file": "..."}]
}
```

## Known Issues & Pitfalls
- Kalau task terlalu besar (>200 LOC), minta Orchestrator decompose dulu
- Butuh context dari context_worker — jangan assign tanpa context
- Setelah selesai, selalu trigger post-coding pipeline (docs + review + security)

## Lessons Learned
(diisi otomatis oleh Cognee Ring 3 setelah setiap session)
```

---

## Cara AR Orchestrator Baca SKILL.md

Pakai s05 pattern dari learn-claude-code — load on demand, bukan di system prompt:

```python
async def assign_task(task: dict) -> dict:
    # 1. Cari worker yang cocok
    candidates = find_candidate_workers(task['task_type'])

    # 2. Load SKILL.md per candidate (on demand, tidak semuanya)
    for worker_id in candidates:
        skill_content = load_skill(worker_id)  # baca SKILL.md

        # 3. Inject ke context orchestrator via tool_result
        # AR Orchestrator baca dan decide
        decision = await orchestrator.decide(
            task=task,
            worker_skills=skill_content
        )

    return decision

def load_skill(worker_id: str) -> str:
    path = f"~/.vibe-office/workers/{worker_id}/SKILL.md"
    with open(path) as f:
        return f.read()
```

Kenapa on demand? Kalau 11 workers semua di-inject ke system prompt = ~5000 token
terbuang setiap request. Dengan on demand, hanya load 2-3 candidates yang relevan.

---

## CEO Office — Kertas Identitas

Di game vibe-office, "kertas" yang kamu flip di meja bos adalah visualisasi
dari `plugin.json` + ringkasan `SKILL.md`. Saat kamu edit nama/tone/personality
di kertas → file `plugin.json` dan `SKILL.md` di-update otomatis.

Saat kamu hire worker baru via Job Application:
1. Isi form → buat `plugin.json` baru
2. AR Orchestrator auto-generate draft `SKILL.md` berdasarkan role yang dipilih
3. Kamu bisa edit SKILL.md langsung (advanced mode) dari kertas identitas

---

## Integrasi dengan Cognee Ring 3

Setelah setiap task selesai, Cognee auto-update bagian "Lessons Learned"
di SKILL.md berdasarkan episode yang tersimpan:

```python
async def update_worker_skill(worker_id: str, episode: dict):
    """Cognee extract lesson dari episode dan append ke SKILL.md."""
    lesson = await cognee.search(
        f"what lesson can be learned from this {worker_id} episode: {episode}"
    )
    if lesson:
        append_to_skill_md(worker_id, "Lessons Learned", lesson)
```

Ini yang membuat workers "makin pintar" seiring waktu — SKILL.md mereka
bertambah kaya dengan lessons dari task nyata.

---

## Kompatibilitas dengan agentskills.io

Format SKILL.md vibe-office kompatibel dengan
[agentskills.io open standard](https://agentskills.io/specification)
yang juga dipakai oleh hermes-agent.

Artinya: skills yang dibuat worker di vibe-office bisa di-share ke komunitas,
dan skills dari komunitas bisa di-import ke vibe-office.
