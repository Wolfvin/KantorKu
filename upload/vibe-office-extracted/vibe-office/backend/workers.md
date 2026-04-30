# Backend — Worker Registry

> **Konteks untuk session baru yang baca ini:**
> Ini adalah SINGLE SOURCE OF TRUTH untuk semua workers di vibe-office.
> Naming sudah di-revamp total dari session sebelumnya.
> Keputusan naming dibuat bersama Wolfvin (2026-03-17).
> Jangan baca file lama `specialist-workers.md` atau `translator-workers.md`
> — keduanya sudah digantikan file ini.
>
> **Perubahan besar dari versi lama:**
> - `orchestrator` → `conductor` (opsional, masih interchangeable)
> - `input_translator` → `intake`
> - `relay_translator` → `bridge`
> - `output_translator` → `narrator`
> - `rust_worker` → `coder_rust` (dan diperluas ke bahasa lain)
> - `docs_worker` → `scribe`
> - `security_worker` → `sentinel`
> - `git_worker` → `chronicler`
> - `context_worker` → `scout` (+ proactive research mode baru)
> - `review_worker` merged dengan `ai_advisor` → `auditor` (dua mode)
> - WORKERS BARU: `curator`, `trainer`, `steward`

---

## Arsitektur Workers (20 total)

```
TRANSLATION LAYER (3)
  intake    → bridge    → narrator
     ↓                       ↑
ORCHESTRATION (1)
  conductor (CEO)
     ↓ assign
SPECIALIST WORKERS (16)
  ┌── CODERS (N, expandable) ──────────────────────────────┐
  │  coder_rust  coder_css  coder_js  coder_python  ...    │
  └────────────────────────────────────────────────────────┘
  ┌── PIPELINE WORKERS ────────────────────────────────────┐
  │  tester  auditor  scribe  sentinel  chronicler  scout  │
  └────────────────────────────────────────────────────────┘
  ┌── KNOWLEDGE LAYER (workers baru) ──────────────────────┐
  │  curator  trainer  steward                             │
  └────────────────────────────────────────────────────────┘
```

---

## TRANSLATION LAYER

### intake
**Ganti dari:** `input_translator`
**Tugas:** Pesan bebasmu → JSON task terstruktur untuk conductor.
**Model:** Small LLM (Ollama llama3 atau claude-haiku).
**Refs:** https://github.com/ollama/ollama | https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct
**Tinggal di:** pintu masuk kantor (lobby tile di canvas).

```python
SYSTEM = """
Kamu intake worker. Convert pesan user ke JSON task.
Output HANYA JSON valid, tidak ada teks lain.

Schema output:
{
  "task_type": "write_code|debug|refactor|test|review|docs|audit|research",
  "language": "rust|css|js|python|null",
  "instruction": "<instruksi spesifik, bahasa Inggris>",
  "context": {
    "files_mentioned": ["<paths>"],
    "urgency": "high|normal|low"
  }
}
"""

async def translate_input(human_message: str) -> dict:
    response = await llm.complete(system=SYSTEM, user=human_message)
    return json.loads(response.text)

# Contoh:
# "buatin endpoint HTTP GET yang handle timeout"
# → {"task_type":"write_code","language":"rust",
#    "instruction":"Implement async HTTP GET endpoint with timeout handling",
#    "context":{"files_mentioned":[],"urgency":"normal"}}
```

**Edge cases:**
- Pesan ambigu → tanya klarifikasi via narrator sebelum create task
- Multi-task → split jadi beberapa tasks terpisah
- Tidak ada language disebutkan → conductor decide berdasarkan project

---

### bridge
**Ganti dari:** `relay_translator`
**Tugas:** Normalize output worker A → format input worker B.
**Model:** Rule-based primary, LLM fallback untuk edge cases tidak terdefinisi.
**Kenapa penting:** Tanpa bridge, setiap worker harus tahu format semua worker
lain. 16 workers = potensial 16×15=240 format pairs. Bridge memotong ini jadi
satu layer tunggal.

**AgentScope MsgHub Pattern (Fase 3 upgrade):**
Bridge saat ini pakai static TRANSFORM_RULES dict. Di Fase 3 saat hire/fire
workers jadi dynamic, upgrade ke WorkerHub class yang inspired MsgHub pattern
dari AgentScope (github.com/agentscope-ai/agentscope).
TIDAK import AgentScope — adapt logic-nya saja ke arsitektur kita.

```python
class WorkerHub:
    """
    Dynamic worker management — inspired by AgentScope MsgHub pattern.
    Fase 3 upgrade untuk bridge: support hire/fire workers saat runtime.
    Ref: github.com/agentscope-ai/agentscope (MsgHub + sequential_pipeline)
    """
    def __init__(self):
        self._workers: dict[str, 'Worker'] = {}
        self._rules: dict[tuple, callable] = dict(TRANSFORM_RULES)  # existing rules

    def add(self, worker: 'Worker'):
        """Hire worker baru — auto-register transform rules."""
        self._workers[worker.id] = worker
        # Auto-generate default rules untuk worker baru
        for existing_id in self._workers:
            if existing_id != worker.id:
                self._register_default_rules(existing_id, worker.id)

    def remove(self, worker_id: str):
        """Fire worker — hapus dari participants dan rules."""
        self._workers.pop(worker_id, None)
        # Clean up rules yang involve worker ini
        self._rules = {k: v for k, v in self._rules.items()
                       if worker_id not in k}

    async def broadcast(self, msg: dict, to: list[str] | None = None):
        """Broadcast ke semua atau subset workers — untuk conductor briefing."""
        targets = to or list(self._workers.keys())
        results = {}
        for wid in targets:
            if wid in self._workers:
                results[wid] = await self._workers[wid].receive(msg)
        return results

    async def relay(self, from_id: str, to_id: str, output: dict) -> dict:
        """Point-to-point relay dengan transform (existing bridge logic)."""
        key = self._find_rule(from_id, to_id)
        if key:
            return self._rules[key](output)
        return await self._llm_transform(from_id, to_id, output)

    def _find_rule(self, from_id: str, to_id: str) -> tuple | None:
        # Support wildcard: ('coder_*', 'tester') match 'coder_rust'
        for key in self._rules:
            f, t = key
            if (f == from_id or (f.endswith('*') and from_id.startswith(f[:-1]))):
                if t == to_id:
                    return key
        return None

# Singleton — dipakai oleh conductor dan semua workers
worker_hub = WorkerHub()
```

```python
TRANSFORM_RULES = {
    # Setelah coder selesai → tester
    ('coder_*', 'tester'): lambda out: {
        'task_type': 'unit_test',
        'code_to_test': out['result']['code'],
        'files_modified': out['result']['files_modified'],
        'function_signatures': extract_signatures(out['result']['code'])
    },
    # Setelah coder selesai → auditor (post-task mode)
    ('coder_*', 'auditor'): lambda out: {
        'task_type': 'review_code',
        'mode': 'post_task',
        'diff': generate_diff(out['result']['files_modified']),
        'context': out['result']['explanation']
    },
    # Setelah coder selesai → scribe
    ('coder_*', 'scribe'): lambda out: {
        'task_type': 'write_docs',
        'files': out['result']['files_modified'],
        'new_functions': [c for c in out['result'].get('changes', [])
                         if c['type'] == 'new_public_function']
    },
    # Setelah auditor block → coder
    ('auditor', 'coder_*'): lambda out: {
        'task_type': 'refactor',
        'instruction': format_critical_findings(out['issues'])
    },
    # Setelah tester fail → coder
    ('tester', 'coder_*'): lambda out: {
        'task_type': 'debug',
        'error_type': out['error']['type'],
        'error_detail': out['error']['detail'],
    },
    # curator update SKILL.md → kirim ke trainer kalau cukup data
    ('curator', 'trainer'): lambda out: {
        'task_type': 'evaluate_training_need',
        'domain': out['domain'],
        'episode_count': out['episode_count'],
        'worker_id': out['worker_id'],
    },
}

async def bridge_relay(from_worker: str, to_worker: str, output: dict) -> dict:
    # Match dengan wildcard untuk coder_*
    key = find_matching_rule(TRANSFORM_RULES, from_worker, to_worker)
    if key:
        return TRANSFORM_RULES[key](output)
    # Fallback LLM untuk transform yang tidak terdefinisi
    return await llm_transform(from_worker, to_worker, output)
```

---

### narrator
**Ganti dari:** `output_translator`
**Tugas:** Output teknis worker → readable untuk TV screen dan chat panel.
**Model:** Small LLM, fokus summarization + natural language.
**Tinggal di:** dekat TV meeting room (dia yang "siaran").

```python
TEMPLATES = {
    'task_start':      "[{wid}] mulai {task_type}...",
    'task_done':       "[{wid}] ✓ {summary}",
    'review_blocking': "[auditor] 🔴 {n} critical issue → kirim ke {coder}",
    'security_block':  "[sentinel] 🔒 blocked: {reason}",
    'blocked':         "[{wid}] ⚠ butuh bantuan: {reason}",
    'tier3_escalate':  "[conductor] ❗ butuh inputmu — {summary}",
    'training_start':  "[trainer] 🧠 mulai fine-tune {domain} untuk {worker}",
    'lora_ready':      "[trainer] ✅ LoRA {lora_name} siap — {delta}",
    'skill_updated':   "[curator] 📚 SKILL.md {worker} di-update: {what_changed}",
}

async def translate_for_tv(worker_id: str, event: dict) -> str:
    template = TEMPLATES.get(event['type'])
    if template:
        return template.format(wid=worker_id, **event)
    # Fallback LLM untuk event tidak terdefinisi
    return await llm.complete(
        system="Summarize this AI worker event in 1 short sentence, casual Indonesian.",
        user=json.dumps(event)
    )
```

---

## ORCHESTRATION

### conductor
**Ganti dari:** `orchestrator` (nama lama masih diterima, interchangeable)
**Model:** Qwen2.5-32B — https://huggingface.co/Qwen/Qwen2.5-32B-Instruct
**Fase 4 kandidat model upgrade:** Qwen3.5-35B-A3B-Claude-4.6-Opus-Reasoning-Distilled
  → https://huggingface.co/Jackrong/Qwen3.5-35B-A3B-Claude-4.6-Opus-Reasoning-Distilled
  → Evaluate vs Qwen2.5-32B saat Fase 4 dimulai — reasoning lebih structured,
    autonomous lebih lama, self-correct errors via `<think>` block
**Tinggal di:** CEO office (klik meja → kertas identitas workers)
**Peran:** Plan, assign, recover. Baca SKILL.md workers on-demand (s05 pattern).
Tidak pernah nulis kode sendiri — dia delegasi.

**Anthropic Advanced Tool Use (Fase 3 — KRITIKAL):**
Referensi resmi: https://www.anthropic.com/engineering/advanced-tool-use
Tiga fitur yang semuanya langsung solve problem nyata kita:

**Problem 1 — Context Bloat dari Tool Definitions:**
Setup kita di Fase 3+: GitNexus 7 MCP tools + OpenSandbox + FectTral MCP +
semua SKILL.md workers = bisa konsumsi 55K-134K token HANYA untuk tool definitions
sebelum conversation dimulai. Dengan `defer_loading: true`, tools discoverable
tapi tidak load ke context sampai benar-benar dibutuhkan.
Hasil: **85% reduction** token overhead dari tool definitions.

**Problem 2 — Multi-step workflows = banyak inference passes:**
Saat conductor orchestrate scout → coder_rust → auditor → chronicler,
setiap step = 1 full inference pass. LLM lihat semua intermediate results
walau hanya butuh output final.
Programmatic Tool Calling: conductor nulis Python script yang orchestrate
seluruh workflow di dalam sandbox. Script pause saat butuh tool result,
lanjut setelah dapat. Model hanya lihat output final.
Hasil: **37% token reduction**, eliminasi hingga **19+ inference passes**
pada workflow kompleks.

**Problem 3 — Tool selection accuracy rendah:**
Workers kita punya banyak SKILL.md dengan domain yang overlap.
Tool Use Examples parameter naik accuracy dari **72% → 90%**.
Internal Anthropic benchmarks: Opus 4 dari 49% → 74%, Opus 4.5 dari 79.5% → 88.1%.

```python
import anthropic

client = anthropic.Anthropic()

# Tool catalog — semua worker tools dengan defer_loading
# "always loaded": bridge + narrator (dipanggil di setiap workflow)
# "deferred": semua SKILL.md workers (load on-demand saat conductor butuh)
ALWAYS_LOADED_TOOLS = [
    bridge_tool_definition,
    narrator_tool_definition,
]

DEFERRED_WORKER_TOOLS = [
    {**skill_tool, "defer_loading": True}
    for skill_tool in build_all_worker_skill_tools()
    # build_all_worker_skill_tools() scan workers/ directory,
    # load plugin.json + SKILL.md header per worker
]

async def conduct(task: dict) -> dict:
    checkpoint(task['id'], 'in_progress')

    response = client.beta.messages.create(
        model="claude-opus-4-6",  # atau local Qwen2.5-32B via vLLM
        max_tokens=8096,
        betas=["advanced-tool-use-2025-11-20"],
        tools=[
            # Tool Search — conductor bisa discover tools on-demand
            {
                "type": "tool_search_tool_regex_20251119",
                "name": "tool_search_tool_regex",
            },
            # Code Execution — conductor bisa orchestrate multi-step
            # workflows dalam satu Python script (Programmatic Tool Calling)
            {
                "type": "code_execution_20260120",
                "name": "code_execution",
            },
            *ALWAYS_LOADED_TOOLS,
            *DEFERRED_WORKER_TOOLS,
        ],
        system=CONDUCTOR_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": format_task(task)}],
    )

    result = extract_result(response)
    checkpoint(task['id'], 'completed' if result['ok'] else 'failed')
    return result


def build_all_worker_skill_tools() -> list[dict]:
    """
    Scan workers/ directory → build tool definition per worker.
    Setiap worker jadi satu tool dengan description dari SKILL.md header.
    Conductor search tool ini via tool_search_tool_regex saat planning.
    """
    tools = []
    for worker_dir in Path("workers/").iterdir():
        if not worker_dir.is_dir():
            continue
        plugin = load_json(worker_dir / "plugin.json")
        skill_header = read_skill_header(worker_dir / "SKILL.md")
        tools.append({
            "name":        f"assign_to_{plugin['id']}",
            "description": skill_header,  # conductor search berdasarkan ini
            "input_schema": {
                "type": "object",
                "properties": {
                    "task": {"type": "object"},
                    "context": {"type": "object"},
                },
                "required": ["task"],
            },
            # defer_loading: True → tidak load ke context sampai dibutuhkan
            # Bisa reduce dari 134K token overhead → ~20K untuk typical task
        })
    return tools
```

**Tool Use Examples — tingkatkan accuracy tool selection:**
```python
# Tambahkan ke tool definitions yang sering salah dipilih
# Format: list of (input, output) contoh nyata
coder_rust_tool = {
    "name": "assign_to_coder_rust",
    "description": "...",
    "input_schema": {...},
    "examples": [
        {
            "input": {"task": {"instruction": "buat async HTTP GET dengan timeout"}},
            "output": {"worker": "coder_rust", "skill": "SKILL-server.md"}
        },
        {
            "input": {"task": {"instruction": "fix borrow checker error di main.rs"}},
            "output": {"worker": "coder_rust", "skill": "SKILL.md"}
        },
    ]
}
# Tool Use Examples: accuracy naik 72% → 90%
# Anthropic internal: Opus 4 dari 49% → 74%, Opus 4.5 dari 79.5% → 88.1%
```

**Recovery tiers:**
- Tier 1: Worker self-retry (invisible ke user)
- Tier 2: Conductor intervensi, assign ulang ke worker berbeda
- Tier 3: Eskalasi ke user via narrator + chat panel

**Catatan untuk session implementasi:**
Saat Fase 3 mulai, baca full blog post Anthropic:
https://www.anthropic.com/engineering/advanced-tool-use
Ada detail tentang tool_search_tool_regex syntax, code_execution sandbox limits,
dan best practices untuk Tool Use Examples yang tidak ada di docs resmi.

---

## CODER WORKERS (Expandable)

**Konsep:** Bukan satu `rust_worker` generik, tapi spesialisasi per bahasa.
Setiap `coder_*` punya SKILL.md sendiri yang spesifik untuk bahasanya.
Conductor baca `language` field di task untuk decide mana yang di-assign.

Semua coders punya output schema yang sama:
```json
{
  "code": "...",
  "explanation": "...",
  "files_modified": ["src/http.rs"],
  "warnings": ["..."],
  "changes": [{"type": "new_public_function", "name": "...", "file": "..."}],
  "confidence": 0.92
}
```

### coder_rust
**Model:** Qwen2.5-Coder-7B (fine-tuned Fase 4).
**Capabilities:** write_code, debug, refactor untuk Rust.
**SKILL files:** `SKILL.md`, `SKILL-async.md`, `SKILL-server.md`, `SKILL-unsafe.md`, `SKILL-rayon.md`
**Timeout:** 60s. **Tinggal di:** workstation.

Sebelum execute: WAJIB terima context dari scout (GitNexus analysis).
Kalau confidence < 0.6 → trigger uncertainty escalation ke scout.

```python
SKILL_TRIGGERS = {
    'SKILL-server.md':  ['server', 'http', 'api', 'axum', 'actix', 'hyper'],
    'SKILL-async.md':   ['async', 'await', 'tokio', 'future', 'spawn'],
    'SKILL-unsafe.md':  ['unsafe', 'ffi', 'raw pointer', 'transmute'],
    'SKILL-rayon.md':   ['parallel', 'rayon', 'thread', 'concurrent', 'par_iter'],
}
```

### coder_css
**Model:** Qwen2.5-Coder-7B (fine-tuned Fase 4) atau small LLM.
**Capabilities:** write_styles, debug_layout, refactor_css, animation.
**SKILL files:** `SKILL.md`, `SKILL-animation.md`, `SKILL-tailwind.md`, `SKILL-variables.md`
**Timeout:** 30s. **Tinggal di:** workstation (meja berbeda dari coder_rust).

Spesialisasi: CSS custom properties, keyframe animations, responsive layout.
Di vibe-office sendiri, coder_css yang maintain theme system kantor pixel art.

### coder_js
**Model:** Qwen2.5-Coder-7B atau Ollama codellama.
**Capabilities:** write_code, debug, refactor untuk JS/TypeScript.
**SKILL files:** `SKILL.md`, `SKILL-canvas.md`, `SKILL-websocket.md`, `SKILL-tauri.md`
**Timeout:** 45s. **Tinggal di:** workstation.

Spesialisasi vibe-office: Canvas 2D game logic, WebSocket client, Tauri APIs.
`SKILL-canvas.md` berisi pixel-agents fork patterns yang spesifik.

### coder_python
**Model:** Qwen2.5-Coder-7B.
**Capabilities:** write_code, debug, refactor untuk Python.
**SKILL files:** `SKILL.md`, `SKILL-async.md`, `SKILL-llm.md`, `SKILL-duckdb.md`
**Timeout:** 45s. **Tinggal di:** workstation.

Spesialisasi: AI backend (agent loops, WebSocket server, DuckDB operations).
`SKILL-llm.md` berisi learn-claude-code patterns (s01-s12 mapping).

### Menambah coder Baru
```python
# Untuk tambah coder baru (misal coder_go):
# 1. Buat folder: workers/coder_go/
# 2. Buat plugin.json + SKILL.md
# 3. Update TRANSFORM_RULES di bridge untuk ('coder_go', 'tester'), dll
# 4. conductor auto-detect dari worker registry scan
# Tidak perlu retrain conductor — dia baca registry saat startup
```

---

## PIPELINE WORKERS

> **Stripe Minions Pattern (adopted 2026-03-18):**
> Referensi: https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents
> Stripe hard-cap 2 iterasi CI sebelum escalate ke human.
> Kita adopt equivalent: setiap worker punya MAX_RETRY_CAP.
> Pipeline juga di-label explicit: mana yang DETERMINISTIC (no LLM) dan
> mana yang AGENTIC (LLM judgment dibutuhkan). Ini penting untuk cost planning
> dan debugging — kalau pipeline gagal di deterministic step, bukan LLM issue.
>
> **Directory-scoped rules (Stripe Minions pattern):**
> Scout auto-attach SKILL.md berdasarkan directory yang di-traverse:
> `/frontend` → load SKILL-canvas.md, SKILL-tailwind.md
> `/backend`  → load SKILL-llm.md, SKILL-duckdb.md
> `/src/lib`  → load SKILL-async.md
> Pattern ini extend `build_all_worker_skill_tools()` di conductor.

### tester
**Ganti dari:** `tester_worker` (minor rename)
**Model:** Qwen2.5-Coder-7B (fine-tuned). Timeout: 90s.
**Type: AGENTIC** — butuh LLM judgment untuk generate test cases dan analisis failures.
**Capabilities:** unit_test, integration_test, test_review.
**Tinggal di:** workstation (area testing zone).

**MAX_RETRY_CAP = 2** (dari Stripe Minions "2 CI rounds" pattern)
Setelah 2x gagal → WAJIB escalate ke Tier 3 (user). Tidak boleh infinite retry.
Ini adalah safeguard penting — tanpa ini tester bisa loop selamanya.

```python
MAX_TESTER_RETRIES = 2  # Stripe Minions equivalent: "2 CI rounds before escalate"

async def run_tester(task: dict, retry_count: int = 0) -> dict:
    result = await execute_tests(task)

    if result['ok']:
        return result

    if retry_count >= MAX_TESTER_RETRIES:
        # Hard escalate ke Tier 3 — jangan retry lagi
        return {
            'ok': False,
            'escalate': True,
            'tier': 3,
            'reason': f'tester failed after {MAX_TESTER_RETRIES} attempts',
            'last_error': result['error'],
        }

    # Route berdasarkan error type
    if result['error']['type'] in ['compilation_error', 'logic_error']:
        # Re-assign ke coder yang buat code ini
        return await bridge.relay('tester', result['original_coder'], result)
    elif result['error']['type'] == 'test_setup_error':
        # Self-retry — tester fix setup-nya sendiri
        return await run_tester(task, retry_count + 1)
    elif result['error']['type'] == 'missing_context':
        # Request scout tambah context dulu
        extra_context = await scout.get_context(task)
        task['context'].update(extra_context)
        return await run_tester(task, retry_count + 1)

    # Unknown error → escalate
    return {'ok': False, 'escalate': True, 'tier': 2, 'error': result['error']}
```

Error routing:
- compilation_error / logic_error → request coder_* yang assign task sebelumnya
- test_setup_error → self-retry (max sampai MAX_RETRY_CAP)
- missing_context → request scout, lalu retry
- **Setelah 2x gagal apapun → TIER 3 ESCALATION, stop**

---

### auditor
**Merge dari:** `review_worker` + `ai_advisor` (dua mode dalam satu worker)
**Model:** Clippy (rule-based) + **Kodus/Kody** (Fase 3 kandidat replace PR-Agent) + **RLM untuk periodic_audit**
**Repo PR-Agent (Fase 1-2):** https://github.com/Codium-ai/pr-agent (open source, self-hosted)
**Repo Kodus (Fase 3 upgrade):** https://github.com/kodus-app/kodus-ai (open source, self-hosted, BYOK)
**Timeout:** 45s (post_task) | 120s (periodic_audit). **Tinggal di:** workstation area.

**Referensi evaluasi (jangan install, ambil patterns):**
- CodeRabbit: https://github.com/marketplace/coderabbitai — #1 AI PR reviewer, 13M PRs reviewed.
  Commercial SaaS ($30/seat/month), data keluar. SKIP install. 3 patterns diadopsi.
- Kodus/Kody: https://github.com/kodus-app/kodus-ai — open-source alternative, self-host, BYOK.
  AST pre-analysis sebelum LLM (reduce noise), auto-detect rule files (termasuk SKILL.md kita),
  technical debt tracking, learnable dari feedback. Kandidat replace PR-Agent Fase 3.

**Kenapa Kodus lebih baik dari PR-Agent untuk Fase 3:**
PR-Agent = LLM langsung ke diff. Kodus = AST analysis dulu → LLM inference.
AST pre-analysis drastically reduce hallucinations karena model understand code structure
sebelum inference, bukan hanya text. Plus Kodus auto-detect SKILL.md kita sebagai review rules.

---

**3 CodeRabbit patterns yang diadopsi:**

**Pattern 1 — Context Engineering (bukan hanya diff):**
CodeRabbit gather intelligence dari dozens of sources sebelum review.
Auditor kita adopt ini: sebelum review, inject context dari GitNexus + SKILL.md + audit history.

**Pattern 2 — Learnable Preferences dari Episode Feedback:**
CodeRabbit learn dari bagaimana tim resolve atau dismiss threads.
Auditor kita: curator routing episode feedback ke auditor SKILL.md.
User resolve issue → true positive → reinforce di SKILL.md.
User dismiss issue → false positive → auditor belajar tidak flag hal ini lagi.

**Pattern 3 — Tiered Pipeline (bukan hanya dua model):**
CodeRabbit: speed untuk semua PR + depth untuk critical paths.
Auditor kita: tiga tiers berdasarkan scope dan criticality.

---

**Tiered Audit Pipeline (CodeRabbit-inspired, tiga tier):**

```
TIER 1 — FAST (semua PR, <5s)
  Clippy → compile errors, lint, unsafe blocks
  Tujuan: catch obvious issues tanpa LLM cost
  Block kalau: compile error

TIER 2 — MEDIUM (PR yang touch non-trivial files, <45s)
  Kodus/Kody (atau PR-Agent Fase 1-2) dengan context dari GitNexus
  Tujuan: code quality, patterns, refactor opportunities
  Block kalau: critical/major severity

TIER 3 — DEEP (periodic atau PR yang touch critical path, <120s)
  RLM + full codebase context + multi-model validation (Zencoder pattern)
  Tujuan: architectural issues, cross-file patterns, technical debt
  Block kalau: critical severity
```

```python
# backend/workers/auditor.py

CRITICAL_PATH_PATTERNS = [
    'conductor', 'bridge', 'ring1', 'ring2', 'memory',
    'auth', 'security', 'webhook', 'gateway'
]

def determine_audit_tier(task: dict) -> int:
    """
    Pilih tier berdasarkan scope dan file yang dimodifikasi.
    Tier 1: semua. Tier 2: ada logic change. Tier 3: critical path.
    """
    files = task.get('files_modified', [])
    is_critical = any(
        any(p in f for p in CRITICAL_PATH_PATTERNS)
        for f in files
    )
    has_logic_change = task.get('change_type') in ['new_function', 'refactor', 'architecture']

    if is_critical:
        return 3
    elif has_logic_change:
        return 2
    else:
        return 1


async def run_auditor(task: dict) -> dict:
    mode = task.get('mode', 'post_task')

    if mode == 'post_task':
        tier = determine_audit_tier(task)

        # TIER 1 — always run
        clippy = run_clippy(task['files_modified'])
        if clippy['has_errors']:
            return block_result(clippy, tier=1)

        if tier == 1:
            # Hanya Clippy — cukup untuk simple changes
            return {'ok': True, 'tier': 1, 'findings': clippy['warnings']}

        # TIER 2 — context-enriched review
        # CodeRabbit pattern: inject context sebelum review
        context = await gather_audit_context(task)
        review = await run_kodus_review(task['diff'], context)

        if tier == 2:
            return aggregate_results(clippy, review, tier=2)

        # TIER 3 — deep review dengan RLM + multi-model
        deep_review = await run_deep_audit(task, context, review)
        return aggregate_results(clippy, review, deep_review, tier=3)

    elif mode == 'periodic_audit':
        codebase = load_full_codebase(task['project_path'])
        context   = await gather_audit_context(task)

        if estimate_tokens(codebase) > 8000:
            audit_findings = await rlm_client.completion(
                prompt=(
                    "Audit this codebase for: "
                    "1) refactor opportunities "
                    "2) duplicate patterns "
                    "3) anti-patterns "
                    "4) missing docs. "
                    "Return structured JSON findings."
                ),
                context=codebase
            )
        else:
            audit_findings = await run_kodus_review(codebase, context)

        # Zencoder multi-model validation (opt-in)
        if task.get('multi_model_validate', False):
            audit_findings = await periodic_audit_multi_model(
                task['project_path'], audit_findings
            )

        # Route ke curator untuk SKILL.md update + learnable preferences
        await bridge.relay('auditor', 'curator', {
            'audit_findings': audit_findings,
            'source': 'periodic_audit',
        })
        await bridge.relay('auditor', 'steward', {
            'cleanup_suggestions': audit_findings,
        })
        return audit_findings


async def gather_audit_context(task: dict) -> dict:
    """
    CodeRabbit pattern: gather intelligence dari multiple sources sebelum review.
    Bukan hanya diff — context dari GitNexus + SKILL.md + audit history.
    """
    context = {}

    # 1. GitNexus: impact analysis + dependency graph
    if task.get('files_modified'):
        context['gitnexus'] = await gitnexus.query(
            f"impact analysis for: {task['files_modified']}"
        )

    # 2. SKILL.md worker yang relevan sebagai review standards
    # Kodus pattern: auto-detect rule files. Kita inject manual via DIRECTORY_SKILL_MAP.
    for file in task.get('files_modified', []):
        skills = get_directory_skills(file)
        for skill in skills:
            context.setdefault('skill_rules', []).append(load_skill(skill))

    # 3. Audit history: apakah ada false positives sebelumnya untuk pattern ini?
    context['audit_history'] = load_recent_audit_episodes(
        worker_id='auditor',
        limit=20,
        filter_outcome='false_positive'
    )

    return context


async def run_kodus_review(diff_or_code: str, context: dict) -> dict:
    """
    Kodus/Kody review dengan enriched context.
    Fase 1-2: pakai PR-Agent (langsung).
    Fase 3+: upgrade ke Kodus untuk AST pre-analysis.

    Kodus auto-detect SKILL.md sebagai rule files — inject path ke SKILL.md
    saat initialize Kodus di Fase 3.
    """
    # Fase 1-2 fallback: PR-Agent
    if not KODUS_AVAILABLE:
        return await pr_agent.review(diff_or_code)

    # Fase 3+: Kodus dengan context injection
    return await kodus.review(
        code=diff_or_code,
        context=context,
        rule_files=[
            f"workers/{wid}/SKILL.md"
            for wid in get_active_worker_ids()
        ]
    )


async def run_deep_audit(task: dict, context: dict, tier2_review: dict) -> dict:
    """
    Tier 3: RLM + architectural reasoning.
    Hanya untuk critical path changes.
    """
    codebase_context = load_full_codebase(task['project_path'])

    return await rlm_client.completion(
        prompt=(
            f"Deep audit for critical path change.\n"
            f"Files: {task['files_modified']}\n"
            f"GitNexus impact: {context.get('gitnexus', {})}\n"
            f"Tier 2 findings so far: {tier2_review}\n"
            f"Focus: architectural correctness, security, cross-file consistency."
        ),
        context=codebase_context
    )


async def record_audit_feedback(
    finding_id: str,
    outcome: str,   # 'true_positive' | 'false_positive' | 'resolved'
    worker_id: str = 'auditor'
):
    """
    CodeRabbit learnable preferences pattern.
    Dipanggil saat user resolve atau dismiss audit finding di chat panel.
    Curator routing feedback ini ke auditor SKILL.md update.

    Flow: user resolve/dismiss → narrator catch event → call ini →
          curator update SKILL.md auditor → auditor tidak flag hal serupa lagi
    """
    episode = {
        'finding_id':  finding_id,
        'outcome':     outcome,
        'timestamp':   datetime.now().isoformat(),
        'worker_id':   worker_id,
        'source':      'user_feedback',
    }

    # Simpan ke Ring 2 sebagai episode feedback
    await ring2.store_episode(episode)

    # Langsung notify curator untuk update SKILL.md auditor
    if outcome == 'false_positive':
        await bridge.relay('auditor', 'curator', {
            'source':    'audit_feedback',
            'outcome':   'false_positive',
            'finding':   finding_id,
            'action':    'update_skill_md_suppress_pattern',
        })
    elif outcome == 'true_positive':
        await bridge.relay('auditor', 'curator', {
            'source':    'audit_feedback',
            'outcome':   'true_positive',
            'finding':   finding_id,
            'action':    'reinforce_skill_md_pattern',
        })


async def periodic_audit_multi_model(project_path: str, primary_findings: dict) -> dict:
    """
    Zencoder pattern: verifikasi findings dari model A dengan model B.
    Opt-in via task['multi_model_validate'] = True — cost lebih tinggi.
    """
    secondary_review = await llm.complete(
        model="qwen2.5-coder:7b",
        system=(
            "You are a second-opinion code reviewer. "
            "Given these audit findings, identify likely FALSE POSITIVES. "
            "Be conservative — only flag definite issues."
        ),
        user=(
            f"Primary audit findings:\n{json.dumps(primary_findings)}\n\n"
            f"Context:\n{load_recent_context(project_path)}"
        )
    )
    return merge_audit_findings(
        primary_findings, secondary_review, threshold='both_agree'
    )
```

---

### scribe
**Ganti dari:** `docs_worker`
**Model:** Qwen2.5-Coder-7B (fine-tuned). Timeout: 45s.
**Capabilities:** write_rustdoc, generate_readme, update_docs, write_comments.
**Tinggal di:** workstation (meja sendiri, ada "buku" pixel art di meja).

Dipanggil otomatis setelah coder selesai (post-coding pipeline).
Kalau gagal → log_and_continue (tidak block commit).

**Perbedaan dari curator:** scribe tulis docs untuk *user project* (rustdoc, README).
curator update *internal knowledge workers* (SKILL.md). Tidak overlap.

---

### sentinel
**Ganti dari:** `security_worker`
**Model:** Rule-based (tidak pakai LLM). Timeout: 30s.
**Tools:** `cargo audit` (CVE deps), scan unsafe blocks, scan hardcoded secrets.
**Tinggal di:** server_room (dia yang "jaga pintu" server).

Hasil FAIL → block commit. Routing:
- unsafe_without_justification → coder_rust
- vulnerable_dependency → eskalasi ke user (Tier 3)
- hardcoded_secret → coder_* yang buat file tersebut

---

### chronicler
**Ganti dari:** `git_worker`
**Model:** Rule-based. Timeout: 20s.
**Capabilities:** commit, create_branch, generate_changelog, squash_commits.
**Tinggal di:** server_room (dia yang "arsip" semua history).

Hanya jalan setelah: sentinel CLEAR + auditor tidak ada critical/major.
Format commit: conventional commits (`feat(scope): description`).
Setelah commit → trigger `npx gitnexus analyze` background (re-index GitNexus).

---

### scout
**Ganti dari:** `context_worker` (major upgrade)
**Model:** Rule-based + GitNexus MCP + Lightpanda + **RLM (Fase 3)**. Timeout: 30s.
**Tinggal di:** server_room (dengan banyak monitor, "reconnaissance center").

**RLM Integration (Fase 3):**
Scout adalah worker dengan use case RLM paling kritis. Masalah utama tanpa RLM:
saat scout harus analisis seluruh codebase + dokumentasi + web results sekaligus,
total token bisa overflow context window conductor. Dengan RLM, scout nulis Python
di REPL untuk slice dan filter codebase — hanya bagian relevan yang di-feed ke LLM.

```python
from rlm import RLM

# Init RLM dengan vLLM endpoint (Fase 3+) atau Ollama (Fase 1-2)
rlm_client = RLM(
    backend="openai",
    backend_kwargs={
        "model_name": "qwen2.5-coder:7b",
        "api_base": "http://localhost:8000/v1"  # vLLM endpoint
    }
)
```

**Dua mode:**

**Mode 1 — `on_demand`** (sebelum task di-assign ke coder):
```python
async def scout_for_task(task: dict) -> dict:
    # Query GitNexus knowledge graph
    gitnexus_context = await gitnexus.query(task['instruction'])

    # Impact analysis kalau edit existing code
    if task['task_type'] in ['debug', 'refactor']:
        for symbol in extract_symbols(task['instruction']):
            impact = await gitnexus.impact(symbol, direction='upstream')
            gitnexus_context['impacts'][symbol] = impact

    # Kalau butuh external docs → Lightpanda scrape
    # Pakai MarkdownFetcher (Cloudflare Markdown for Agents pattern)
    if needs_external_docs(task['instruction']):
        docs_url = infer_docs_url(task['language'], task['instruction'])
        external_docs = await markdown_fetcher.fetch(docs_url)
        gitnexus_context['external_docs'] = external_docs
        gitnexus_context['external_docs_tokens'] = external_docs.get('estimated_tokens')

    # Kalau total context besar (>8K tokens) → pakai RLM
    # RLM bisa handle codebase dump penuh tanpa overflow
    if estimate_tokens(gitnexus_context) > 8000:
        summary = await rlm_client.completion(
            prompt=f"Summarize relevant context for task: {task['instruction']}",
            context=serialize_context(gitnexus_context)
        )
        # Persist intermediate RLM result ke Ring 2 SQLite (pattern dari rlm-rs)
        await ring2.store_intermediate({
            'task_id': task['id'],
            'type': 'rlm_scout_summary',
            'content': summary
        })
        return {'rlm_summary': summary, 'raw_context': gitnexus_context}

    return gitnexus_context
```

**Mode 2 — `proactive_research`** (BARU — ide dari session 2026-03-17):
Scout duduk di ruangan penuh komputer. Ketika tidak ada meeting (tidak ada
task aktif), scout *proactively* research topik-topik yang mungkin berguna:
library baru, CVE terbaru, best practices update, deprecated APIs.

```python
async def proactive_research_loop():
    """
    Background loop: scout research sendiri saat idle.
    RLM dipakai kalau hasil scrape Lightpanda sangat panjang.
    Hasil disimpan ke EdgeQuake Ring 3 sebagai knowledge untuk workers.
    """
    while True:
        if not has_active_tasks():
            topic = await research_queue.get()
            if topic:
                # Scrape dengan Lightpanda
                raw_results = await lightpanda.research(topic['query'])

                # Kalau hasil scrape panjang → RLM extract structured knowledge
                if estimate_tokens(raw_results) > 6000:
                    processed = await rlm_client.completion(
                        prompt=f"Extract structured knowledge about: {topic['query']}. "
                               f"Focus on: {topic['relevant_workers']}",
                        context=raw_results['content']
                    )
                else:
                    processed = raw_results

                await edgequake.store({
                    'type': 'proactive_research',
                    'topic': topic,
                    'content': processed,
                    'relevance': topic['relevant_workers']
                })

                if processed['significance'] > 0.7:
                    await notify_curator(topic, processed)

        await asyncio.sleep(30)
```

Di kantor pixel art: scout terlihat duduk di depan banyak monitor, ada animasi
"typing" atau "scrolling" saat proactive research. Klik scout → popup
"currently researching: {topic}" atau "idle, ready for task."

**MarkdownFetcher — HTTP layer upgrade (Cloudflare Markdown for Agents):**
Tidak perlu worker baru. Ini thin wrapper di HTTP layer scout yang berlaku
untuk semua fetch — baik on_demand maupun proactive_research.

Referensi: https://blog.cloudflare.com/markdown-for-agents (Accept: text/markdown header)
Claude Code dan OpenCode sudah kirim header ini secara default — kita follow pattern yang sama.

```python
# backend/utils/markdown_fetcher.py
import httpx

class MarkdownFetcher:
    """
    HTTP wrapper yang prefer markdown over HTML.
    80-99% token reduction untuk Cloudflare-powered sites (mayoritas web).
    Fallback ke HTML kalau server tidak support markdown.
    Pakai di scout — on_demand fetch dan proactive_research loop.
    """

    async def fetch(self, url: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers={
                "Accept": "text/markdown, text/html;q=0.9, */*;q=0.8",
                "User-Agent": "vibe-office-scout/1.0 (AI agent)"
            }, follow_redirects=True)

            content_type = resp.headers.get("content-type", "")
            is_markdown   = "text/markdown" in content_type

            # x-markdown-tokens header dari Cloudflare — estimated token count
            # Scout pass ini ke conductor agar conductor bisa decide:
            # "terlalu besar → minta scout summarize dulu via RLM"
            estimated_tokens = resp.headers.get("x-markdown-tokens")

            return {
                "content":          resp.text,
                "format":           "markdown" if is_markdown else "html",
                "estimated_tokens": int(estimated_tokens) if estimated_tokens else None,
                "url":              url,
                "status":           resp.status_code,
            }

    async def fetch_with_error_handling(self, url: str) -> dict:
        """
        Structured error handling — Cloudflare return RFC 9457-compliant
        markdown errors. Bukan parse HTML error page (yang 98% lebih besar).
        Scout retry logic bisa baca error secara deterministic.
        """
        result = await self.fetch(url)
        if result['status'] == 429:
            # Rate limit — Cloudflare markdown error ada instruksi eksplisit
            # "wait 30 seconds, retry with exponential backoff"
            # Parse dari result['content'] yang sudah structured markdown
            return {'error': 'rate_limited', 'retry_after': 30, **result}
        if result['status'] >= 400:
            return {'error': f"http_{result['status']}", **result}
        return result

    async def estimate_before_fetch(self, url: str) -> int | None:
        """
        HEAD request dulu untuk cek ukuran sebelum full fetch.
        Kalau terlalu besar → pass ke RLM, jangan flood context window.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.head(url, headers={"Accept": "text/markdown"})
            return resp.headers.get("x-markdown-tokens")

# Singleton — scout import dan pakai langsung
markdown_fetcher = MarkdownFetcher()
```

**Kenapa ini satu method bukan worker baru:**
Cloudflare Markdown for Agents adalah HTTP protocol upgrade, bukan domain kerja baru.
Scout sudah punya responsibility fetch web content — ini adalah cara fetch yang lebih
efisien. Worker baru hanya justified kalau ada domain kerja yang berbeda, bukan
satu header HTTP. `x-markdown-tokens` yang di-return dari fetch bisa dipakai conductor
untuk decide apakah perlu RLM atau tidak — integrasi yang bersih dengan layer yang sudah ada.

**Zencoder Pattern — Daily scheduled GitNexus re-index:**
Zencoder lakukan cross-repo dependency mapping dengan daily updates, bukan hanya
post-commit. Scout kita adopt ini sebagai scheduled background job.
Ref: zencoder.ai — "Repo Grokking with daily cross-repo dependency updates"

```python
# Tambahan di scout — DAILY RE-INDEX SCHEDULE
# Ini melengkapi post-commit re-index yang sudah ada (via chronicler)

import asyncio
from datetime import datetime, time as dtime

DAILY_REINDEX_TIME = dtime(hour=3, minute=0)  # jam 3 pagi — low traffic

async def daily_reindex_schedule():
    """
    Zencoder pattern: daily GitNexus re-index untuk catch dependency changes
    yang tidak ter-trigger oleh commit (misalnya: library update, dependency baru
    di project lain yang di-import, atau config change).
    Jalan sebagai background task saat scout idle.
    """
    while True:
        now = datetime.now().time()
        if now.hour == DAILY_REINDEX_TIME.hour and now.minute == DAILY_REINDEX_TIME.minute:
            await ws_broadcast({
                'type': 'speech_bubble',
                'worker_id': 'scout',
                'text': '🔄 daily reindex running...',
                'duration_ms': 3000,
            })

            # Full re-index semua repos yang dikenal
            for repo_path in get_known_repos():
                await run_gitnexus_analyze(repo_path)
                # Cross-repo dependency map update
                await gitnexus.update_cross_repo_deps(repo_path)

            await ws_broadcast({
                'type': 'speech_bubble',
                'worker_id': 'scout',
                'text': '✅ reindex done',
                'duration_ms': 2000,
            })

        await asyncio.sleep(60)  # check setiap menit

# Di backend/main.py:
# asyncio.create_task(scout.daily_reindex_schedule())
```

**Fase 6 — Multi-Modal Input via nanobot/OpenClaw:**
Scout akan menjadi handler untuk beberapa input type baru di Fase 6.
Detail arsitektur ada di `backend/multimodal-integration.md` (dibuat Fase 5).
Quick reference:
- YouTube video → `scout` via yt-dlp download + RLM summarize transcript
- Chrome browsing → `scout` via CDP (Chrome DevTools Protocol) — Lightpanda sudah ada
- Web research → `scout` sudah ada (proactive_research_loop)
Semua masuk ke EdgeQuake Ring 3 via `edgequake.store()` yang sudah ada.

---

## KNOWLEDGE LAYER (Workers Baru)

### curator
**Ganti dari:** `ai_teacher`
**Model:** LLM medium (Qwen2.5-14B atau API) + **RLM untuk dokumen panjang (Fase 3)**. Timeout: flexible.
**Tinggal di:** library room (viola room yang unlock Fase 2, ada "rak buku" pixel art).
**Fungsi inti:** Rawat pengetahuan internal semua workers. Bukan mengajar aktif,
tapi *curate* — pilih mana yang relevan, update mana yang outdated, routing data.

**RLM Integration (Fase 3 — Medium Priority):**
Curator sering terima input panjang: NovaNotes bisa 50K+ tokens, batch episodes
dari Ring 2 bisa ratusan entries. Tanpa RLM, curator harus chunk manual atau
risiko context rot di tengah analisis. RLM solve ini — curator bisa query
keseluruhan knowledge base dan extract structured output tanpa kehilangan coherence.

```
Sumber data curator:
  ← auditor (periodic_audit findings)
  ← scout (proactive research results)
  ← Ring 2 Parquet episodes (sukses + gagal)
  ← user (explicit "tambah knowledge ini")
  ← NovaNotes (panjang — kandidat utama RLM)

Output curator:
  → update SKILL.md workers
  → routing episode ke trainer kalau cukup data untuk LoRA baru
  → update research_queue scout
  → notify narrator kalau ada update signifikan
```

**Hierarki SKILL.md yang dirawat curator:**
```
workers/{worker_id}/
├── SKILL.md              ← peta utama: kapabilitas, kapan pakai, kapan tidak
├── SKILL-{domain}.md     ← knowledge spesifik per domain (server, async, dll)
└── references/
    ├── examples/         ← episode sukses (source of truth untuk trainer)
    └── failures/         ← episode gagal + root cause analysis
```

```python
async def curate_knowledge(source: str, data: dict):
    worker_id = data.get('worker_id') or infer_relevant_worker(data)

    if source == 'auditor_periodic':
        # Audit findings → biasanya pendek, tidak butuh RLM
        await patch_skill_md(worker_id, 'Known Issues & Pitfalls', data['findings'])

    elif source == 'scout_research':
        # New research → bisa panjang kalau dari Lightpanda scrape
        domain = classify_domain(data['topic'])
        content = data['content']

        # Kalau panjang → RLM extract structured knowledge dulu
        if estimate_tokens(content) > 6000:
            content = await rlm_client.completion(
                prompt=f"Extract actionable knowledge for {worker_id} about {domain}. "
                       f"Return: key patterns, gotchas, best practices.",
                context=content
            )

        await patch_skill_md(worker_id, f'SKILL-{domain}.md', content)

    elif source == 'episode_batch':
        # Batch episodes dari Ring 2 — bisa sangat banyak
        episodes = data['episodes']

        if len(episodes) > 50 or estimate_tokens(episodes) > 8000:
            # RLM process batch besar, extract lessons secara recursive
            lessons = await rlm_client.completion(
                prompt=f"Extract lessons learned for {worker_id}. "
                       f"Identify: success patterns, failure patterns, improvement areas.",
                context=serialize_episodes(episodes)
            )
        else:
            lessons = await extract_lessons(episodes)

        await patch_skill_md(worker_id, 'Lessons Learned', lessons)

        if data['episode_count'] >= TRAINING_THRESHOLD:
            await bridge.relay('curator', 'trainer', {
                'domain': data['domain'],
                'worker_id': worker_id,
                'episode_count': data['episode_count']
            })

    elif source == 'nova_notes':
        # NovaNotes bisa 50K+ tokens — RLM wajib
        structured = await rlm_client.completion(
            prompt="Extract structured knowledge: key concepts, code patterns, "
                   "decisions made, and their rationale.",
            context=data['content']
        )
        domain = classify_domain(data.get('title', ''))
        await patch_skill_md(worker_id, f'SKILL-{domain}.md', structured)
```

---

### trainer
**Ganti dari:** `ai_scientist`
**Model:** Automation script + Unsloth + LLM untuk eval. Timeout: hours.
**Tinggal di:** lab room (viola room khusus, ada GPU icon pixel art di dinding).
**Fungsi inti:** Kelola LoRA lifecycle sepenuhnya autonomous — dari signal curator
sampai LoRA aktif di production. Trainer tidak hanya "run fine-tuning sekali" tapi
loop malam hari iterating experiment, git commit tiap run, rollback otomatis kalau
eval turun.

**Referensi arsitektur (JANGAN install, adopt pattern-nya):**
- `karpathy/autoresearch` (https://github.com/karpathy/autoresearch) — fixed time budget
  per experiment (~12 runs/jam), single-file scope, `val_bpb` metric, git-as-memory pattern
- `uditgoenka/autoresearch` (https://github.com/uditgoenka/autoresearch) — generalisasi
  pattern ke domain non-ML: git rollback otomatis, SKILL.md-as-program.md, mechanical
  binary verification metric. Selaras dengan SKILL.md pattern kita.

**Dua mode trainer:**

**Mode 1 — `train_lora`** (dipanggil curator, satu domain):
```
1. Curator kirim signal: "coder_rust domain=borrow_checker punya 847 episodes"
2. Trainer ambil episodes dari Ring 2 Parquet
3. Filter: sukses saja, compress dengan trajectory compressor (hermes-patterns)
4. git commit state awal → checkpoint sebelum training
5. Jalankan Unsloth fine-tuning dengan fixed time budget (MAX_TRAIN_MINUTES)
6. Eval dengan val_bpb (vocab-size-independent, fair untuk architectural changes)
7. Kalau val_bpb turun → git revert otomatis ke checkpoint
8. Kalau +5% improvement → aktifkan LoRA, notify narrator
```

**Mode 2 — `overnight_loop`** (autonomous, cron tengah malam):
```
Loop sampai MAX_EXPERIMENTS tercapai atau pagi tiba:
  1. Review state + git history sejak malam terakhir
  2. Pilih satu perubahan (hyperparameter, rank, data filtering)
  3. git commit sebelum experiment
  4. Run training dengan MAX_TRAIN_MINUTES budget
  5. Mechanical eval: val_bpb naik atau turun?
     → naik: keep commit, lanjut experiment berikutnya
     → turun: git revert otomatis, coba arah berbeda
  6. Log hasil ke Ring 2 experiments.parquet
  7. Pagi: narrator announce top result ke TV screen
```

```python
import subprocess
from pathlib import Path

MAX_TRAIN_MINUTES = 5      # fixed budget per experiment (Karpathy pattern)
MAX_EXPERIMENTS   = 12     # overnight loop cap (≈ 1 jam)
IMPROVEMENT_THRESHOLD = 0.05   # minimal 5% val_bpb improvement untuk keep

async def train_new_lora(request: dict) -> dict:
    worker_id = request['worker_id']
    domain    = request['domain']

    # 1. Ambil episodes dari Ring 2
    episodes = load_parquet_episodes(worker_id, domain, min_success_rate=0.8)
    if len(episodes) < TRAINING_THRESHOLD:
        return {'status': 'skipped', 'reason': 'insufficient_data'}

    # 2. Compress untuk fit context window (hermes-patterns)
    compressed = compress_trajectories(episodes, target_max_tokens=6000)

    # 3. git checkpoint sebelum training (Karpathy/autoresearch pattern)
    lora_name = f"lora_{domain}_v{get_next_version(worker_id, domain)}"
    lora_path = Path(f"~/.vibe-office/loras/{worker_id}/{lora_name}").expanduser()
    git_checkpoint(f"trainer: pre-train {lora_name}")

    # 4. Fine-tune dengan fixed time budget
    result = await unsloth_finetune(
        base_model=get_worker_base_model(worker_id),
        dataset=compressed,
        output_path=str(lora_path),
        rank=16, alpha=32,
        seed=42,
        max_minutes=MAX_TRAIN_MINUTES   # BARU: fixed budget dari Karpathy pattern
    )

    # 5. Eval dengan val_bpb (BARU: vocab-size-independent metric dari Karpathy)
    eval_result = eval_lora_val_bpb(worker_id, lora_path, domain)

    if eval_result['improvement'] > IMPROVEMENT_THRESHOLD:
        activate_lora(worker_id, lora_name, weight=0.8)
        git_checkpoint(f"trainer: activate {lora_name} +{eval_result['improvement']:.1%}")
        return {'status': 'activated', 'lora': lora_name, 'val_bpb_delta': eval_result['improvement']}
    else:
        # Git rollback otomatis (autoresearch pattern)
        git_revert_to_last_checkpoint()
        discard_lora(lora_path)
        return {'status': 'discarded', 'reason': 'no_improvement', 'val_bpb': eval_result['val_bpb']}


async def overnight_loop(worker_id: str, domain: str):
    """
    Autonomous improvement loop — jalan tengah malam.
    Pattern dari karpathy/autoresearch + uditgoenka/autoresearch.
    Single-file scope: hanya boleh edit satu LoRA config per experiment.
    State tersimpan di Ring 2 experiments.parquet (bukan di RAM).
    """
    results = []

    for i in range(MAX_EXPERIMENTS):
        await ws_broadcast({
            'type': 'progress',
            'worker_id': 'trainer',
            'progress': i / MAX_EXPERIMENTS,
            'message': f'experiment {i+1}/{MAX_EXPERIMENTS}'
        })

        # git commit state sebelum experiment
        git_checkpoint(f"trainer: experiment {i+1} start")

        # Pilih satu perubahan — trainer LLM review history dan propose
        change = await propose_next_experiment(worker_id, domain, results)

        # Apply dan train (fixed budget)
        apply_experiment_config(change)
        eval_result = await run_timed_training(worker_id, domain, MAX_TRAIN_MINUTES)

        if eval_result['improvement'] > 0:
            # Keep — commit permanen
            git_checkpoint(f"trainer: keep exp {i+1} +{eval_result['improvement']:.1%}")
            results.append({'change': change, 'result': eval_result, 'kept': True})
        else:
            # Revert otomatis
            git_revert_to_last_checkpoint()
            results.append({'change': change, 'result': eval_result, 'kept': False})

        # Persist ke Ring 2
        append_to_parquet('experiments', {
            'worker_id': worker_id, 'domain': domain,
            'experiment': i+1, **eval_result, 'kept': eval_result['improvement'] > 0
        })

    # Morning report via narrator
    best = max(results, key=lambda r: r['result']['improvement'])
    await ws_broadcast({
        'type': 'speech_bubble',
        'worker_id': 'trainer',
        'text': f"🌅 overnight done: {sum(r['kept'] for r in results)}/{MAX_EXPERIMENTS} improvements. best: {best['result']['improvement']:.1%}",
        'duration_ms': 8000
    })


def git_checkpoint(message: str):
    """Commit current state — trainer pakai git sebagai memori eksperimen."""
    subprocess.run(['git', 'add', '-A'], cwd=get_lora_dir())
    subprocess.run(['git', 'commit', '-m', f'[trainer] {message}'], cwd=get_lora_dir())

def git_revert_to_last_checkpoint():
    """Rollback ke commit terakhir — hapus perubahan yang tidak improve."""
    subprocess.run(['git', 'reset', '--hard', 'HEAD~1'], cwd=get_lora_dir())
```

**val_bpb sebagai metric utama (dari karpathy/autoresearch):**
```python
def eval_lora_val_bpb(worker_id: str, lora_path: Path, domain: str) -> dict:
    """
    val_bpb = validation bits per byte.
    Vocab-size-independent → bisa compare fair meski architectural changes.
    Lebih reliable dari accuracy% untuk compare LoRA variants.
    Formula: val_bpb = val_loss / ln(2)
    Baseline disimpan di Ring 2, diambil setiap eval untuk delta calculation.
    """
    val_loss = run_validation(worker_id, lora_path, domain)
    val_bpb  = val_loss / 0.693147  # ln(2)

    baseline_bpb = load_baseline_bpb(worker_id, domain)
    improvement  = (baseline_bpb - val_bpb) / baseline_bpb  # positif = lebih baik

    return {
        'val_bpb':     val_bpb,
        'baseline_bpb': baseline_bpb,
        'improvement': improvement,
        'performance_delta': f"{improvement:+.1%} val_bpb"
    }
```

**LoRA Metadata (untuk brain visualization):**
```json
{
  "name": "lora_borrow_checker_v2",
  "domain": "borrow_checker",
  "trained_at": "2026-03-17",
  "episodes_count": 847,
  "performance_delta": "+23% val_bpb",
  "val_bpb": 0.412,
  "baseline_bpb": 0.534,
  "experiments_run": 8,
  "status": "active",
  "weight": 0.8,
  "side_effects": {"async_accuracy": "-2%"}
}
```

Trainer juga bisa **disable LoRA** kalau kamu minta via CEO office:
```python
def disable_lora(worker_id: str, lora_name: str):
    """Matikan LoRA — tidak hapus dari disk, bisa re-enable."""
    composer = get_lora_composer(worker_id)
    composer.disable(lora_name)
    update_lora_metadata(worker_id, lora_name, status='disabled')
    # LoRA tetap ada di ~/.vibe-office/loras/, bisa re-enable kapan saja
```

---

### steward
**Ganti dari:** `ai_janitor`
**Model:** LLM medium. Timeout: 60s per file batch.
**Tinggal di:** break room (dia yang "bersih-bersih" kantor).
**Scope ketat:** HANYA file organization + comment generation.
**TIDAK boleh:** refactor logic, ubah behavior kode, merge function.

```python
STEWARD_TASKS = {
    'split_file': "File terlalu besar (>500 LOC) → pisah jadi beberapa module",
    'add_comments': "Tambah function comments/docstrings yang missing",
    'organize_imports': "Susun imports secara alphabetical + group (std, ext, local)",
    'rename_to_convention': "Rename yang tidak ikut konvensi bahasa (snake_case, dll)",
}

# STEWARD TIDAK BOLEH:
STEWARD_FORBIDDEN = [
    "Mengubah logic atau behavior fungsi",
    "Merge dua fungsi jadi satu",
    "Hapus kode yang kelihatan tidak terpakai",
    "Rewrite algorithm",
]

async def run_steward(project_path: str):
    """Jalankan steward secara periodic (setiap commit besar, atau manual)."""
    files = scan_project(project_path)

    for f in files:
        if count_lines(f) > 500:
            await split_large_file(f)  # pecah file besar
        if has_missing_comments(f):
            await add_function_comments(f)  # tambah comments
        if imports_not_organized(f):
            await organize_imports(f)       # susun imports

    # Setelah steward selesai → trigger auditor periodic untuk verify
    await trigger_auditor(mode='post_steward_check', files_touched=files)
```

---

## Post-Coding Pipeline (Updated)

> **Stripe Minions Blueprint Pattern:**
> Setiap step di-label DETERMINISTIC atau AGENTIC.
> DETERMINISTIC = fixed code, no LLM, predictable cost dan hasil.
> AGENTIC = LLM judgment dibutuhkan, variable cost.
> Kalau pipeline gagal di DETERMINISTIC step → bukan LLM issue, debug code-nya.
> Ref: https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents

```
coder_* selesai
  ↓ bridge normalize output  [DETERMINISTIC — rule-based transform]

scribe ──PARALEL── auditor(post_task) ──PARALEL── sentinel
[AGENTIC]          [AGENTIC]                       [DETERMINISTIC]
rustdoc + README   Clippy + PR-Agent               cargo audit, secret scan
tidak block commit bisa block kalau critical/major  FAIL = block commit

                    ↓ (semua selesai)
              chronicler → commit  [DETERMINISTIC — conventional commit format]

                    ↓ (background, non-blocking)
              scout re-index GitNexus     [DETERMINISTIC — CLI command]
              curator log episode Ring 2  [AGENTIC — classify + extract lessons]
              curator → trainer?          [AGENTIC — threshold check]
```

**Catatan penting dari Stripe Minions:**
- `sentinel` dan `chronicler` adalah DETERMINISTIC — tidak ada LLM call.
  Kalau gagal → bug di rule/config, bukan LLM issue. Debug berbeda.
- `scribe` bisa FAIL SILENTLY (log_and_continue) — tidak block commit.
  Ini intentional: docs penting tapi tidak critical path.
- `auditor post_task` adalah satu-satunya yang bisa BLOCK dengan LLM judgment.
  Kalau terlalu banyak false blocks → improve auditor SKILL.md atau Tool Use Examples.

---

## Task-Type → Tool Subset Mapping (Conductor — Stripe Minions Pattern)

> Dari Stripe Minions: agents perform best dengan curated subset yang relevan per task,
> bukan semua tools sekaligus. Ini extend `build_all_worker_skill_tools()` di conductor.
> Setiap task_type punya "default loaded" dan "available on-search" tools.

```python
# backend/conductor_tool_subsets.py
# Conductor load subset ini saat planning — bukan semua tools sekaligus
# Selaras dengan Advanced Tool Use defer_loading pattern

TASK_TYPE_TOOL_SUBSETS: dict[str, dict] = {
    "write_code": {
        "always_load":    ["scout", "tester", "auditor"],
        "available":      ["scribe", "sentinel", "chronicler"],
        "skip_by_default": ["designer", "archivist", "curator", "trainer"],
    },
    "debug": {
        "always_load":    ["scout", "tester", "auditor"],
        "available":      ["sentinel", "chronicler"],
        "skip_by_default": ["scribe", "designer", "curator", "trainer"],
    },
    "refactor": {
        "always_load":    ["scout", "auditor", "steward"],
        "available":      ["tester", "scribe", "sentinel", "chronicler"],
        "skip_by_default": ["designer", "curator", "trainer"],
    },
    "design": {
        "always_load":    ["designer", "archivist", "stylist", "compositor"],
        "available":      ["coder_css", "coder_js"],
        "skip_by_default": ["coder_rust", "tester", "sentinel", "trainer"],
    },
    "research": {
        "always_load":    ["scout"],
        "available":      ["curator"],
        "skip_by_default": ["all_coders", "designer", "trainer"],
    },
    "audit": {
        "always_load":    ["auditor", "sentinel"],
        "available":      ["scout", "steward"],
        "skip_by_default": ["all_coders", "designer", "trainer"],
    },
    "docs": {
        "always_load":    ["scribe"],
        "available":      ["scout", "steward"],
        "skip_by_default": ["all_coders", "designer", "trainer"],
    },
}

# Directory-scoped SKILL loading (Stripe Minions "directory rule files" pattern)
DIRECTORY_SKILL_MAP: dict[str, list[str]] = {
    "frontend/":       ["SKILL-canvas.md", "SKILL-tailwind.md", "SKILL-websocket.md"],
    "backend/":        ["SKILL-llm.md", "SKILL-duckdb.md", "SKILL-async.md"],
    "src/":            ["SKILL-async.md", "SKILL-server.md"],
    "workers/":        ["SKILL.md"],  # setiap worker load SKILL.md-nya sendiri
    "design/":         ["SKILL-animation.md", "SKILL-variables.md"],
}

def get_directory_skills(file_path: str) -> list[str]:
    """
    Auto-attach SKILL.md berdasarkan directory yang di-traverse.
    Scout pakai ini saat on_demand context gathering.
    """
    for prefix, skills in DIRECTORY_SKILL_MAP.items():
        if file_path.startswith(prefix):
            return skills
    return []
```

---

## Knowledge Layer Pipeline (Async, Background)

```
Ring 2 Parquet episodes (terakumulasi)
  ↓ curator analisis
curator update SKILL.md workers      ← bisa kapan saja
curator evaluate training readiness
  ↓ kalau ≥ threshold episodes
trainer fine-tune LoRA baru
trainer eval + activate/discard
  ↓ kalau activated
narrator announce ke TV: "🧠 coder_rust upgraded: +23% borrow checker"
```

---

## Ruangan Workers di Kantor

```
CEO OFFICE      → conductor
MEETING ROOM    → semua workers saat briefing, TV screen
WORKSTATION     → coder_rust, coder_css, coder_js, coder_python, tester, auditor, scribe
SERVER ROOM     → sentinel, chronicler, scout (banyak monitor)
BREAK ROOM      → workers idle, steward juga di sini
DORMITORY       → workers blocked/recharge
LIBRARY ROOM*   → curator (viola, unlock Fase 2)
LAB ROOM*       → trainer (viola, unlock Fase 3 — ada GPU icon di dinding)
ROOFTOP*        → ceremony room: LoRA presentation + celebration + bird's-eye stats (unlock Fase 4)

* = viola rooms, unlock seiring progress
```

---

## DESIGN WORKERS (5 Workers Baru — dari FectTral + Impeccable Integration)

Detail lengkap di `design/design-workers.md`.
Semua tinggal di **design studio room** (viola room, unlock Fase 2).

**Impeccable Integration (https://github.com/pbakaus/impeccable):**
Impeccable adalah open-source plugin Claude Code yang solve "AI slop" problem —
output frontend yang selalu convergence ke pola median (Space Grotesk, Inter,
purple gradient, cards in cards). Kita TIDAK install Impeccable sebagai dependency.
Yang kita adopt:
1. **Command vocabulary** (20+ commands) → masuk ke SKILL.md compositor + stylist
2. **Anti-pattern catalog** → masuk ke archivist tagging system sebagai reject patterns
3. **Aesthetic intentionality framework** → masuk ke designer's system prompt
4. **Project aesthetic context** → selaras dengan room-config.json theme system kita

### archivist
**Merge dari:** FectTral curator + tagger
**Fungsi:** Fetch URL → ekstrak elemen design → auto-tag → masuk library.
**Proactive mode:** watch URL watchlist saat idle (Dribbble, Awwwards, url custom).
**Storage:** SQLite `library.db` (terpisah dari DuckDB Ring 1).
**Detail:** `design/design-workers.md`

**Impeccable anti-pattern catalog yang di-enforce archivist saat tagging:**
Setiap elemen yang masuk library di-check terhadap reject patterns ini.
Kalau elemen adalah varian dari pola-pola ini → auto-tag `avoid: true`.
```
REJECT PATTERNS (dari Impeccable anti-pattern catalog):
  Typography : Inter/Space Grotesk sebagai satu-satunya pilihan font
  Color      : Purple gradient sebagai aksen utama
  Layout     : Cards in cards (nested card pattern)
  Components : Glassmorphism sebagai efek utama
  Animation  : Simple fade-in sebagai satu-satunya transisi
  Spacing    : Identical padding di semua breakpoints tanpa intentionality
  Icons      : Heroicons/Lucide tanpa modifikasi visual apapun
  CTA        : Rounded pill button dengan shadow sebagai default
```

### stylist
**Merge dari:** FectTral reviewer + selector
**Fungsi:** Quality gate (approve/reject/rename) + pilih kombinasi terbaik.
**Detail:** `design/design-workers.md`

**Impeccable command vocabulary yang masuk SKILL.md stylist:**
Stylist bisa dipanggil dengan commands ini — bukan hanya approve/reject mentah.
```
/audit      → scan seluruh design library, flag yang terlalu generic atau anti-pattern
/distill    → dari 20 pilihan, extract 3 paling distinct dan intentional
/quieter    → pilih kombinasi yang lebih subtle, kurangi visual noise
/bolder     → pilih kombinasi yang lebih assertive dan memorable
/critique   → berikan honest assessment mengapa pilihan ini kuat atau lemah
/colorize   → suggest palette yang sesuai dengan mood target, bukan random
```

**Aesthetic direction yang stylist bisa enforce (dari Impeccable):**
Wolfvin bisa set project aesthetic context — stylist enforce ini di semua seleksi.
```
Brutal      → raw edges, high contrast, slab serifs, no rounded corners
Maximalist  → layered, rich texture, decorative, unapologetically complex
Retro-futuristic → CRT effects, scanlines, phosphor glow (FectTral sudah ada ini)
Luxury Editorial → generous whitespace, refined typography, restrained palette
Cyberpunk   → FectTral default kita — electric blue, dark void, neon accents
```

### compositor
**Dari:** FectTral generator
**Fungsi:** Rakit elemen dari library → kode frontend kohesif.
**Perbedaan dari `coder_css`:** compositor COMPOSE yang sudah ada di library,
`coder_css` BUAT dari nol. Tidak overlap.
**Detail:** `design/design-workers.md`

**Impeccable command vocabulary yang masuk SKILL.md compositor:**
Compositor bisa menerima directives ini setelah dapat kombinasi dari stylist.
```
/polish     → refine detail kecil: spacing konsisten, micro-animation, hover states
/animate    → tambah motion yang purposeful, bukan sekadar fade-in
/typeset    → refine typography: hierarchy, contrast, legibility di semua sizes
/delight    → tambah satu unexpected detail yang membuat user "oh nice"
/overdrive  → push aesthetic lebih jauh — lebih extreme dari brief awal
```

**Aturan compositor dari Impeccable:**
Setiap output compositor wajib bisa jawab pertanyaan ini sebelum deliver:
1. Apakah ini bisa salah dikira sebagai template generic? (kalau ya → /overdrive)
2. Apakah ada satu detail yang unforgettable? (kalau tidak ada → /delight)
3. Apakah font choice disengaja, bukan default? (kalau tidak → /typeset)

### designer
**Worker baru** — orchestrator semua design workers.
**Fungsi:** Kamu bicara ke designer, dia yang routing ke archivist/stylist/compositor.
"Ambil design dari X" → archivist. "Buat landing page" → stylist → compositor.

**Aesthetic context yang designer maintain (dari Impeccable teach-impeccable pattern):**
Designer simpan project aesthetic context di `~/.vibe-office/aesthetic-context.json`.
Selaras dengan `room-config.json` theme system. Di-update tiap kamu set preferensi baru.
```json
{
  "project_aesthetic": "cyberpunk-retro-futuristic",
  "base_system": "FectTral",
  "avoid_patterns": ["purple-gradient", "glassmorphism", "cards-in-cards"],
  "signature_elements": ["electric-blue-glow", "scanlines", "perspective-grid"],
  "typography_direction": "Orbitron headings, JetBrains Mono terminals",
  "updated_at": "2026-03-17"
}
```

---

## Updated: Ruangan Workers di Kantor

```
CEO OFFICE         → conductor
MEETING ROOM       → semua workers briefing, TV screen
WORKSTATION        → coder_rust, coder_css, coder_js, coder_python, tester,
                     auditor, scribe
SERVER ROOM        → sentinel, chronicler, scout (banyak monitor)
BREAK ROOM         → workers idle, steward
DORMITORY          → workers blocked/recharge
LIBRARY ROOM*      → curator (knowledge layer)
LAB ROOM*          → trainer (GPU icon di dinding)
DESIGN STUDIO*     → designer (meja tengah), archivist, stylist, compositor,
                     + 1 MONITOR BESAR untuk enter FectTral UI
ROOFTOP*           → ceremony room: trainer present LoRA baru, celebration zone, bird's-eye stats (unlock Fase 4)

* = viola rooms, unlock seiring progress
```

---

## Extension: intake — Router Dinamis (Fase 3)

> Extend `intake` worker — bukan worker baru.
> intake sudah classify task type, sekarang tambahkan worker routing suggestion
> agar conductor tidak perlu figure out dari scratch siapa yang harus kerja.

### Tambahan di intake output schema

```python
# SEBELUM (intake output):
{
  "task_type": "write_code|debug|refactor|test|review|docs|audit|research",
  "instruction": "...",
  "context": {...}
}

# SESUDAH (tambah routing_hint):
{
  "task_type": "write_code",
  "instruction": "...",
  "context": {...},
  "routing_hint": {
    "primary_worker": "coder_rust",       # worker utama yang paling cocok
    "support_workers": ["scout", "tester"],# worker pendukung yang kemungkinan dibutuhkan
    "confidence": 0.87,                   # seberapa yakin classifier
    "reasoning": "Rust keyword detected, async pattern mentioned",
    "skip_scout": False,                  # kalau True → conductor bisa skip scout phase
    "estimated_complexity": "medium",     # low/medium/high → conductor adjust planning depth
  }
}
```

### Classifier Logic (rule-based + keyword, bukan LLM tambahan)

```python
# Di intake worker — setelah parse task, sebelum return

ROUTING_RULES = [
    # (pattern, primary_worker, support, skip_scout, complexity_hint)
    (r'\b(rust|cargo|borrow|lifetime|unsafe|tokio|axum)\b',
        'coder_rust',    ['scout', 'tester'],  False, 'medium'),
    (r'\b(python|pip|pandas|numpy|sklearn|fastapi|pydantic)\b',
        'coder_python',  ['scout', 'tester'],  False, 'medium'),
    (r'\b(css|tailwind|animation|flexbox|grid|responsive)\b',
        'coder_css',     ['compositor'],        True,  'low'),
    (r'\b(javascript|typescript|react|canvas|websocket|tauri)\b',
        'coder_js',      ['scout', 'tester'],  False, 'medium'),
    (r'\b(test|unit test|integration|spec|assert|mock)\b',
        'tester',        ['coder_rust'],        True,  'low'),
    (r'\b(review|audit|security|vulnerability|unsafe)\b',
        'auditor',       ['sentinel'],          True,  'low'),
    (r'\b(design|ui|component|layout|figma|color|theme)\b',
        'designer',      ['archivist'],         False, 'medium'),
    (r'\b(research|find|look up|how to|what is|documentation)\b',
        'scout',         [],                    False, 'low'),
    (r'\b(commit|git|branch|changelog|version)\b',
        'chronicler',    [],                    True,  'low'),
    (r'\b(docs|readme|comment|document|explain)\b',
        'scribe',        [],                    True,  'low'),
]

def classify_routing(task_text: str) -> dict:
    import re
    text = task_text.lower()
    matches = []

    for pattern, primary, support, skip_scout, complexity in ROUTING_RULES:
        if re.search(pattern, text, re.IGNORECASE):
            matches.append({
                'primary': primary,
                'support': support,
                'skip_scout': skip_scout,
                'complexity': complexity,
                'pattern': pattern,
            })

    if not matches:
        return {
            'primary_worker': 'conductor',   # conductor decide sendiri
            'support_workers': [],
            'confidence': 0.3,
            'reasoning': 'no clear routing pattern detected',
            'skip_scout': False,
            'estimated_complexity': 'medium',
        }

    # Ambil match pertama (prioritas order dari ROUTING_RULES)
    best = matches[0]
    confidence = min(0.5 + len(matches) * 0.1, 0.95)  # lebih banyak match = lebih yakin

    return {
        'primary_worker': best['primary'],
        'support_workers': best['support'],
        'confidence': confidence,
        'reasoning': f"{len(matches)} pattern(s) matched",
        'skip_scout': best['skip_scout'] and len(matches) == 1,
        'estimated_complexity': best['complexity'],
    }
```

### Conductor pakai routing_hint

```python
# Di conductor planning — baca routing_hint sebelum LLM call

async def plan_task(task: dict) -> dict:
    hint = task.get('routing_hint', {})

    # Kalau confidence tinggi → conductor skip expensive planning
    if hint.get('confidence', 0) > 0.8:
        # Fast path: langsung assign berdasarkan hint
        plan = {
            'primary': hint['primary_worker'],
            'support': hint['support_workers'],
            'skip_scout': hint.get('skip_scout', False),
        }
        # Conductor masih bisa override kalau mau
    else:
        # Slow path: conductor LLM call untuk plan dari scratch
        plan = await conductor_llm_plan(task)

    return plan
```
