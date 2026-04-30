# Backend — Hermes Agent Patterns

> **Konteks untuk session baru yang baca file ini:**
> File ini adalah "pelajaran" dari hermes-agent (github.com/NousResearch/hermes-agent,
> MIT license, by Nous Research). Hermes bukan untuk di-integrate ke vibe-office —
> ini adalah production-grade AI agent yang worth dipelajari karena arsitekturnya
> sangat mirip dengan apa yang sedang kita bangun.
> Tiga hal utama yang kita pinjam: trajectory compression, RL environments, skills system.
> Dievaluasi dan didokumentasikan session 2026-03-16.

---

## Overview Hermes

Hermes adalah fully open-source AI agent yang "grows with you":
- Persistent memory across sessions
- Spawn subagents untuk parallel workstreams  
- Built-in cron scheduler
- Skills system yang kompatibel dengan agentskills.io
- Batch runner + RL training environments (ini yang paling menarik)

Relevansi ke vibe-office: Hermes adalah implementasi nyata dari konsep-konsep
yang ada di arsitektur vibe-office. Lihat ini sebagai "production reference."

```bash
# Install untuk self-study:
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
hermes  # langsung bisa chat
```

---

## Pelajaran 1 — Trajectory Compression

**File di hermes:** `trajectory_compressor.py`
**Relevansi:** Fase 4 training pipeline — compress Ring 2 episodes agar fit ke token budget.

**Masalah:** Episode dari Ring 2 bisa sangat panjang (tool calls + outputs + context).
Kalau langsung pakai untuk fine-tuning, banyak yang melebihi context window model.

**Solusi hermes — 3-step compression:**
```python
# Dipelajari dari trajectory_compressor.py hermes-agent

def compress_trajectory(messages: list, target_max_tokens: int = 16000) -> list:
    """
    Compress trajectory ke dalam token budget untuk fine-tuning.
    
    Strategy:
    1. Protect first 2 turns (task setup) — jangan dicompress
    2. Protect last 2 turns (final result) — jangan dicompress  
    3. Summarize middle turns via LLM — ini yang dicompress
    """
    if count_tokens(messages) <= target_max_tokens:
        return messages  # sudah cukup kecil, tidak perlu compress
    
    first = messages[:2]   # protected: task + initial response
    last = messages[-2:]   # protected: final result
    middle = messages[2:-2]  # yang akan dicompress
    
    # Summarize middle dengan LLM
    summary = llm.complete(
        system="Summarize these agent steps concisely. Keep tool names and key decisions.",
        user=format_as_text(middle)
    )
    
    synthetic_message = {
        "role": "user",
        "content": f"[COMPRESSED STEPS SUMMARY]\n{summary}\n[END SUMMARY]"
    }
    
    return first + [synthetic_message] + last
```

**Untuk vibe-office:**
```python
# Compress sebelum masuk ke Unsloth training pipeline
def prepare_training_batch(episodes: list) -> list:
    compressed = []
    for ep in episodes:
        if ep['token_count'] > 8000:  # terlalu panjang untuk 7B model
            ep['messages'] = compress_trajectory(ep['messages'], target_max_tokens=6000)
        compressed.append(ep)
    return compressed
```

**Command hermes (untuk referensi):**
```bash
python trajectory_compressor.py --input=data/my_run
python trajectory_compressor.py --input=data/my_run --sample_percent=15
python trajectory_compressor.py --input=data/my_run --target_max_tokens=16000
```

---

## Pelajaran 2 — RL Environments (Atropos)

**Files di hermes:** `environments/hermes_base_env.py`
**Atropos repo:** https://github.com/NousResearch/atropos, `environments/agent_loop.py`
**Relevansi:** Fase 4+ — train workers pakai reinforcement learning, bukan hanya SFT.

**Mengapa RL lebih baik dari pure SFT untuk workers:**
- SFT: worker belajar "tiru contoh sukses"
- RL: worker belajar "apa yang benar-benar works dalam environment nyata"
  → rust_worker dapat reward +1 kalau kode compile, -1 kalau gagal
  → lebih robust, lebih generalize

**Arsitektur Atropos (dari hermes):**
```
VLLM server (model yang di-train)
  ↓ token IDs + logprobs
Atropos API server (RL orchestrator)
  ↓ distribusi task
HermesAgentBaseEnv (satu environment per task type)
  ↓ rollout agent
ToolContext (reward function punya akses ke real tools)
  ↓ compute_reward(item, result, ctx)
Training signal balik ke VLLM
```

**Cara buat custom RL environment untuk rust_worker:**
```python
# Pola dari hermes environments/hermes_base_env.py

from environments.hermes_base_env import HermesAgentBaseEnv

class RustWorkerEnv(HermesAgentBaseEnv):
    name = "rust_coding"

    async def setup(self):
        """Load dataset coding tasks."""
        self.tasks = load_rust_coding_tasks()  # dari Ring 2

    async def get_next_item(self):
        """Return next coding task."""
        return random.choice(self.tasks)

    def format_prompt(self, item) -> str:
        """Task dict → prompt string untuk model."""
        return f"Write Rust code: {item['instruction']}\nContext: {item['context']}"

    async def compute_reward(self, item, result, ctx) -> float:
        """
        Reward function — punya akses ke real terminal via ctx.
        Ini yang membuat RL environment hermes powerful.
        """
        # Tulis kode ke file temp
        ctx.terminal(f"cat > /tmp/test.rs << 'EOF'\n{result['code']}\nEOF")
        
        # Coba compile
        compile_result = ctx.terminal("rustc /tmp/test.rs -o /tmp/test 2>&1")
        if compile_result['exit_code'] != 0:
            return 0.0  # tidak compile = reward 0
        
        # Jalankan test (kalau ada)
        if item.get('expected_output'):
            run_result = ctx.terminal("/tmp/test")
            if item['expected_output'] in run_result['stdout']:
                return 1.0  # compile + output benar = reward penuh
            return 0.5  # compile tapi output salah = reward setengah
        
        return 0.8  # compile tapi tidak ada test = mostly good

    async def evaluate(self, *args, **kwargs):
        """Periodic evaluation — jalankan benchmark."""
        pass

if __name__ == "__main__":
    RustWorkerEnv.cli()
```

**Jalankan:**
```bash
# Start VLLM dengan tool parser
vllm serve Qwen/Qwen2.5-Coder-7B --tool-parser hermes

# Start Atropos API
run-api

# Start environment
python environments/rust_worker_env.py serve \
    --openai.base_url http://localhost:8000/v1 \
    --openai.model_name Qwen/Qwen2.5-Coder-7B \
    --openai.server_type openai
```

**Catatan:** RL training ini adalah Fase 4+, bukan prioritas sekarang.
Dokumentasikan sekarang agar tidak perlu research ulang nanti.

---

## Pelajaran 3 — Skills System & agentskills.io

**Files di hermes:** `~/.hermes/skills/`, `tools/skill_manage.py`
**Relevansi:** Format SKILL.md kita kompatibel dengan hermes + agentskills.io standar.

**Yang menarik dari hermes skills system:**

```
~/.hermes/skills/
├── axolotl/
│   ├── SKILL.md          ← instruksi utama
│   ├── references/       ← docs tambahan
│   ├── templates/        ← format output
│   └── assets/           ← file pendukung
└── .hub/
    ├── lock.json          ← provenance setiap installed skill
    └── audit.log          ← security scan history
```

Ini adalah standar yang sama dengan `worker-identity-card.md` kita.
Dengan kata lain: **format SKILL.md workers vibe-office sudah compatible
dengan agentskills.io standard dari hari pertama.**

**patch action — cara update SKILL.md yang efisien:**
```python
# Hermes: patch lebih efisien dari full rewrite untuk update kecil
skill_manage(
    action="patch",
    name="rust_worker",
    old_string="Known Issues & Pitfalls\n- Kalau task terlalu besar",
    new_string="Known Issues & Pitfalls\n- Kalau task > 150 LOC (bukan 200)"
)
# Hanya kirim diff, bukan seluruh file → jauh lebih hemat token
```

Adaptasi untuk vibe-office:
```python
async def patch_worker_skill(worker_id: str, old: str, new: str):
    """Update SKILL.md worker dengan surgical patch."""
    path = f"~/.vibe-office/workers/{worker_id}/SKILL.md"
    content = open(path).read()
    if old not in content:
        raise ValueError(f"String not found: {old}")
    updated = content.replace(old, new, 1)  # replace hanya sekali
    open(path, 'w').write(updated)
    
    # Juga update Cognee Ring 3 agar tahu SKILL.md berubah
    await cognee.add(f"Updated skill for {worker_id}: {new}")
    await cognee.cognify()
```

---

## Pelajaran 4 — Context Compression pada Long Sessions

**Relevansi:** s06 dari learn-claude-code + hermes context compressor = sama conceptually.
Di vibe-office, sessions bisa sangat panjang (seharian kerja).

**Hermes config:**
```yaml
# ~/.hermes/config.yaml
compression:
  enabled: true
  threshold: 0.85    # compress saat 85% context limit tercapai
```

**Implementasi untuk vibe-office:**
```python
# Di setiap worker agent loop
MAX_TOKENS = 32000  # context limit model

async def worker_loop_with_compression(messages: list, tools: list):
    while True:
        # Cek context size sebelum setiap call
        if count_tokens(messages) > MAX_TOKENS * 0.85:
            messages = compress_trajectory(messages, target_max_tokens=MAX_TOKENS * 0.5)
            # Inject compression notice
            messages.append({
                "role": "user",
                "content": "[Context compressed. Previous steps summarized above. Continue task.]"
            })
        
        response = await llm.complete(messages=messages, tools=tools)
        messages.append({"role": "assistant", "content": response.content})
        
        if response.stop_reason != "tool_use":
            return response
        
        # ... handle tool calls ...
```

---

## Pelajaran 5 — Subagents dengan Isolated Context

**Relevansi:** Sama persis dengan worker spawning di vibe-office.

Hermes punya `delegate_task` tool yang spawn child AIAgent dengan:
- Fresh `messages[]` sendiri (tidak mewarisi parent context)
- Restricted toolsets
- Depth limit 2 (tidak ada grandchildren)
- Parallel batch hingga 3 concurrent

```python
# Pola yang sama dengan s04 learn-claude-code
delegate_task(tasks=[
    {"goal": "Write HTTP client", "toolsets": ["terminal", "file"]},
    {"goal": "Write unit tests", "toolsets": ["terminal", "file"]},
    {"goal": "Write docs",       "toolsets": ["file"]},
])
# Tiga subagents jalan paralel, results dikumpulkan
```

Ini adalah exact pattern yang dipakai di post-coding pipeline vibe-office:
`docs_worker PARALEL review_worker PARALEL security_worker`.

---

## Summary: Apa yang Dipinjam dari Hermes

| Konsep | File hermes | Dipakai di vibe-office |
|--------|-------------|------------------------|
| Trajectory compression | `trajectory_compressor.py` | Fase 4 training pipeline |
| RL environments | `environments/hermes_base_env.py` | Fase 4+ worker training |
| SKILL.md format | `~/.hermes/skills/*/SKILL.md` | `backend/worker-identity-card.md` |
| patch action | `tools/skill_manage.py` | Update SKILL.md workers |
| Context compression | `agent/context_compressor.py` | Long session handling |
| Subagents parallel | `tools/delegation.py` | Post-coding pipeline |

**Hermes tidak diintegrasikan sebagai dependency** — terlalu besar dan punya
gateway/messaging/cron yang tidak dibutuhkan. Tapi pola implementasinya
adalah referensi solid untuk Fase 3-4.
