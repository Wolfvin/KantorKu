# Vibe-Office — Master Link Registry

> **Baca ini kalau mau tahu "dari mana kita ambil bagian ini?"**
> Semua repo sudah dievaluasi. Kolom STATUS menunjukkan apa yang sudah
> diambil, apa yang belum, dan apa yang masih gap.
> Update: 2026-03-17

---

## GAME LAYER

| Repo | Link | License | Stars | Status |
|------|------|---------|-------|--------|
| pixel-agents (base fork) | https://github.com/pablodelucca/pixel-agents | MIT | 3.6k | ✅ Fase 1 — fork ini, cabut VS Code, tambah Tauri |
| Tauri v2 | https://github.com/tauri-apps/tauri | MIT | 89k | ✅ host desktop app |
| Pixelorama (sprite editor) | https://github.com/Orama-Interactive/Pixelorama | MIT | 4k | ✅ edit + export sprite sheets |
| proper-pixel-art (cleanup) | https://github.com/nicholasgasior/proper-pixel-art | MIT | — | ✅ clean up AI-generated sprites |
| pixel-sprite-lab (AI gen) | https://github.com/pixel-sprite-lab/pixel-sprite-lab | — | — | ⬜ generate sprites dari deskripsi |

---

## AI BACKEND CORE

| Repo | Link | License | Stars | Status |
|------|------|---------|-------|--------|
| learn-claude-code | https://github.com/shareAI-lab/learn-claude-code | MIT | 23.1k | ✅ blueprint agent loop s01-s12 |
| learn-claude-code (web) | https://learn-claude-agents.vercel.app/en/s01/ | — | — | ✅ referensi interaktif |
| DeerFlow | https://github.com/bytedance/deer-flow | MIT | 22.7k | ✅ referensi implementasi, skill loading |
| hermes-agent | https://github.com/NousResearch/hermes-agent | MIT | — | ✅ trajectory compression, RL patterns |
| DeepAgents | https://github.com/langchain-ai/deepagents | MIT | — | ⬜ **Fase 4 — conductor backbone, upgrade dari LangGraph** |
| LangGraph | https://github.com/langchain-ai/langgraph | MIT | 13k | ⬜ underlying runtime DeepAgents, low-level control fallback |
| LangChain | https://github.com/langchain-ai/langchain | MIT | 98k | ⬜ diperlukan kalau pakai LangGraph langsung |

---

## LONG-CONTEXT INFERENCE

> **Konteks:** Workers seperti scout, auditor, dan curator sering handle input yang
> jauh melebihi context window model. Section ini mendokumentasikan solusinya.

### Evaluasi: RLM (Recursive Language Models)

**alexzhang13/rlm — WORTH IT ✅ — masuk Fase 3**

| Repo | Link | License | Stars | Status |
|------|------|---------|-------|--------|
| alexzhang13/rlm | https://github.com/alexzhang13/rlm | MIT | — | ⬜ Fase 3 — inference layer scout + auditor + curator |

**Apa ini:**
RLM adalah inference paradigm baru dari MIT — bukan framework, bukan library baru.
Ini adalah cara *berbeda* dalam feed context ke LLM. Alih-alih inject semua token
sekaligus ke prompt (yang overflow kalau dokumen besar), context di-load sebagai
Python variable ke REPL. LLM nulis kode untuk akses, slice, search, dan filter
context tersebut — termasuk bisa recursively call sub-LLM untuk bagian tertentu.

**Kenapa worth it:**
- +28.3% improvement RLM-Qwen3-8B vs vanilla Qwen3-8B — tanpa fine-tuning tambahan
- Process input dua orders of magnitude beyond context window
- Support vLLM via LiteLLM → tinggal ganti `llm.complete()` → `rlm.completion()`
- Install: `pip install rlm` — production-ready, dari MIT
- Sandbox support: local (default), Docker, Modal, e2b — kompatibel dengan OpenSandbox kita

**Worker yang terpengaruh dan prioritasnya:**

| Worker | Use Case | Priority |
|--------|----------|----------|
| `scout` | Research codebase besar + web results panjang tanpa context rot | 🔴 Tinggi |
| `auditor` | Review file 5000+ baris tanpa manual chunking | 🔴 Tinggi |
| `curator` | Classify knowledge dari NovaNotes / dokumen panjang (50K+ tokens) | 🟡 Medium |
| `conductor` | Planning task yang involve banyak file sekaligus | 🟡 Medium |
| `coder_*` | Tidak perlu — task mereka per-file, context masih manageable | 🟢 Skip |

**Integrasi:**
```python
# Sebelum (vanilla):
response = await llm.complete(system=SYSTEM, user=long_codebase_dump)

# Sesudah (RLM):
from rlm import RLM
rlm = RLM(backend="openai", backend_kwargs={
    "model_name": "qwen2.5-coder",
    "api_base": "http://localhost:8000/v1"  # vLLM endpoint
})
response = await rlm.completion(prompt=query, context=long_codebase_dump)
```

**Tidak replace:** Ollama, vLLM, GitNexus, EdgeQuake, Lightpanda — semua tetap.
RLM adalah *inference wrapper* di atas model yang sudah ada, bukan pengganti stack.

---

**zircote/rlm-rs — SKIP sebagai dependency, AMBIL sebagai referensi arsitektur ⚠️**

| Repo | Link | License | Stars | Status |
|------|------|---------|-------|--------|
| zircote/rlm-rs | https://github.com/zircote/rlm-rs | — | 0 | 📚 referensi arsitektur Tauri side — jangan jadikan dependency |

**Apa ini:**
Rust CLI tool untuk process dokumen besar via intelligent chunking, SQLite
persistence untuk intermediate RLM results, dan recursive sub-LLM orchestration.
Dirancang spesifik untuk Claude Code plugin workflow — bukan library embeddable.

**Kenapa di-skip:**
- 0 stars — belum tested oleh siapapun di luar pembuat
- Scope terlalu spesifik ke Claude Code CLI, bukan general inference
- Fungsi utamanya sudah ditangani: GitNexus (codebase) + EdgeQuake (memory) + alexzhang13/rlm (inference)
- Menambahkan ini = duplikasi tanpa value tambah

**Konsep yang diambil meski tool-nya di-skip:**

1. **SQLite persistence untuk intermediate RLM results** — rlm-rs simpan hasil
   chunking/processing ke SQLite sebelum di-feed ke LLM. Pattern ini selaras
   sempurna dengan Ring 2 kita yang juga SQLite. Artinya kalau scout/auditor
   pakai RLM dan butuh persist intermediate results, bisa langsung masuk Ring 2
   tanpa bridging layer tambahan. Catat ini saat implement scout Fase 3.

2. **Rust-side document processing pattern** — kita sudah pakai Rust di Tauri backend.
   Kalau nanti ada kebutuhan process dokumen besar di sisi desktop (misalnya
   room-editor load config besar atau session-management replay session panjang),
   pattern chunking dari rlm-rs bisa di-adapt sebagai Tauri command — tanpa
   dependency ke repo-nya.

**Rekomendasi:**
- Fase 3: pakai `alexzhang13/rlm` untuk scout + auditor + curator
- rlm-rs: bookmark, cek ulang di Fase 4 — kalau sudah ada stars dan community tumbuh,
  pertimbangkan untuk Tauri-side document processing
- SQLite persistence pattern dari rlm-rs: apply ke Ring 2 saat implement scout

---

## WORKERS & ORCHESTRATION

| Repo | Link | License | Stars | Status |
|------|------|---------|-------|--------|
| Qwen2.5-Coder-7B | https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct | Apache-2.0 | — | ✅ base model semua coder_* workers |
| Qwen2.5-32B | https://huggingface.co/Qwen/Qwen2.5-32B-Instruct | Apache-2.0 | — | ✅ conductor model |
| Ollama | https://github.com/ollama/ollama | MIT | 104k | ✅ Fase 1-3 local inference |
| vLLM | https://github.com/vllm-project/vllm | Apache-2.0 | 47k | ✅ setup guide di `backend/vllm-setup.md` |
| PR-Agent (auditor Fase 1-2) | https://github.com/Codium-ai/pr-agent | Apache-2.0 | 7k | ✅ code review, auditor Fase 1-2 |
| Kodus/Kody (auditor Fase 3+) | https://github.com/kodus-app/kodus-ai | Apache-2.0 | — | ⬜ **Fase 3 — upgrade PR-Agent: AST pre-analysis + SKILL.md auto-detect** |
| agentskills.io spec | https://agentskills.io/specification | — | — | ✅ SKILL.md format standard |

### Evaluasi: CodeRabbit + Kodus untuk auditor

**CodeRabbit — SKIP install ❌ — 3 patterns diadopsi ke auditor**

| Resource | Link | Status |
|----------|------|--------|
| CodeRabbit GitHub Marketplace | https://github.com/marketplace/coderabbitai | 📚 patterns diadopsi — tidak di-install |

**Apa ini:** #1 most-installed AI app di GitHub, 13 juta PRs di-review, 2 juta repos.
Commercial SaaS $30/seat/month — data keluar server. SKIP.

**3 patterns yang diadopsi ke auditor (source of truth di workers.md):**
1. **Context Engineering** — gather intelligence dari GitNexus + SKILL.md + audit history
   sebelum review. Bukan hanya diff. `gather_audit_context()` function.
2. **Learnable Preferences** — `record_audit_feedback()` routing ke curator SKILL.md update.
   User resolve = true positive, dismiss = false positive. Auditor belajar dari ini.
3. **Tiered Pipeline** — 3 tier berdasarkan scope: Clippy (Tier 1) → Kodus (Tier 2) →
   RLM+multi-model (Tier 3 critical path). `determine_audit_tier()` function.

---

**Kodus/Kody — WORTH IT ✅ — kandidat replace PR-Agent Fase 3**

| Resource | Link | License | Stars | Status |
|----------|------|---------|-------|--------|
| kodus-app/kodus-ai | https://github.com/kodus-app/kodus-ai | Apache-2.0 | — | ⬜ Fase 3 — evaluate vs PR-Agent |
| Kodus docs | https://docs.kodus.io | — | — | ⬜ baca sebelum evaluate |

**Apa ini:** Open-source AI code review, self-host, BYOK (OpenAI/Anthropic/Google).
AST pre-analysis sebelum LLM inference — drastically reduce noise dan hallucinations.
Auto-detect rule files dari Cursor/Copilot/Claude/Windsurf — **termasuk SKILL.md kita**.
Technical debt tracking via automatic issue conversion. Learnable dari feedback.
30+ bahasa.

**Kenapa lebih baik dari PR-Agent untuk Fase 3:**

| Aspek | PR-Agent | Kodus |
|-------|---------|-------|
| Open source | ✅ | ✅ |
| Self-host + BYOK | ✅ | ✅ |
| AST pre-analysis | ❌ LLM langsung ke diff | ✅ understand structure dulu |
| Auto-read SKILL.md | ❌ | ✅ auto-detect rule files |
| Technical debt tracking | ❌ | ✅ auto-convert ke issues |
| Learnable dari feedback | ❌ | ✅ adaptive |

**Cara evaluate di Fase 3:**
Run parallel: PR-Agent dan Kodus pada 20 PRs yang sama.
Bandingkan: false positive rate, context understanding, alignment dengan SKILL.md rules.
Pilih yang lebih baik — tidak harus ganti kalau PR-Agent cukup.

**Integration dengan SKILL.md:**
```bash
# Kodus auto-detect SKILL.md di project root atau workers/ folder
# Tidak perlu config tambahan — Kodus scan dan pakai sebagai review rules
kodus review --rule-files "workers/*/SKILL.md"
```

---

## CODEBASE INTELLIGENCE (scout)

| Repo | Link | License | Stars | Status |
|------|------|---------|-------|--------|
| GitNexus | https://github.com/abhigyanpatwari/GitNexus | PolyForm Noncommercial | 9.4k | ✅ knowledge graph, 7 MCP tools |
| Lightpanda browser | https://github.com/lightpanda-io/browser | AGPL-3.0 | 11.8k | ✅ web scraping 11x lebih cepat dari Chrome |

### Evaluasi: Cloudflare Markdown for Agents

**Cloudflare Markdown for Agents — WORTH IT ✅ — implement langsung di scout HTTP layer**

| Resource | Link | Status |
|----------|------|--------|
| Cloudflare blog post | https://blog.cloudflare.com/markdown-for-agents | ✅ implement di scout Fase 3 |
| Claude Code docs (best practices) | https://code.claude.com/docs/id/best-practices | ✅ referensi pattern |

**Apa ini:**
HTTP protocol feature dari Cloudflare. Agent kirim header `Accept: text/markdown` →
Cloudflare convert halaman on-the-fly → agent terima markdown bersih tanpa CSS, JS,
nav bar. Hasil: 80-99% token reduction. 16,180 token HTML → 3,150 token markdown.
Claude Code dan OpenCode sudah kirim header ini secara default.

**Kenapa TIDAK perlu worker baru:**
Ini adalah upgrade HTTP layer scout yang sudah ada — satu header tambahan.
Worker baru hanya justified kalau ada domain kerja baru. "Fetch web content" sudah
menjadi responsibility scout. `MarkdownFetcher` adalah thin wrapper (50 baris)
yang scout import dan pakai — bukan worker terpisah.

**Yang sudah di-implement di `workers.md` (tidak duplikasi):**
- `MarkdownFetcher` class lengkap dengan fetch, error handling, dan HEAD estimate
- `x-markdown-tokens` header → scout report ke conductor → conductor decide RLM atau tidak
- Structured error handling (RFC 9457) → scout retry logic deterministic, bukan parse HTML
- Integrasi dengan RLM: kalau `estimated_tokens` dari header terlalu tinggi →
  auto-trigger RLM untuk summarize sebelum pass ke conductor

**Rekomendasi:** Fase 3 bersama scout. Satu file baru: `backend/utils/markdown_fetcher.py`.
Buat file tersebut saat implement scout — jangan sebelumnya.

---

## MEMORY SYSTEM

| Repo | Link | License | Stars | Status |
|------|------|---------|-------|--------|
| DuckDB | https://github.com/duckdb/duckdb | MIT | 26k | ✅ Ring 1 — hot in-process |
| Cognee | https://github.com/topoteretes/cognee | Apache-2.0 | 11k | ✅ Ring 3 Fase 3 prototype |
| EdgeQuake (GraphRAG) | https://github.com/raphaelmansuy/edgequake | Apache-2.0 | 109 | ✅ Ring 3 Fase 4 production |
| LightRAG (EdgeQuake base) | https://github.com/HKUDS/LightRAG | MIT | 16k | ✅ algoritma yang di-implement EdgeQuake |
| Apache AGE (graph DB) | https://github.com/apache/age | Apache-2.0 | 3k | ✅ setup guide di `backend/edgequake-setup.md` |
| pgvector | https://github.com/pgvector/pgvector | PostgreSQL License | 14k | ✅ setup guide di `backend/edgequake-setup.md` |

---

## SANDBOX & ISOLATION

| Repo | Link | License | Stars | Status |
|------|------|---------|-------|--------|
| OpenSandbox | https://github.com/alibaba/OpenSandbox | Apache-2.0 | 4.3k | ✅ Docker/K8s isolation Fase 3+ |

---

## TRAINING & CONTINUAL LEARNING

| Repo | Link | License | Stars | Status |
|------|------|---------|-------|--------|
| Unsloth | https://github.com/unslothai/unsloth | Apache-2.0 | 31k | ✅ fine-tuning utama, lebih efisien dari PEFT |
| BitNet | https://github.com/microsoft/BitNet | MIT | 25.8k | ✅ CPU inference tanpa GPU |
| HuggingFace PEFT | https://github.com/huggingface/peft | Apache-2.0 | 18k | ✅ LoRA base (Unsloth build di atasnya) |
| O-LoRA | https://github.com/cmnfriend/O-LoRA | MIT | — | ✅ adaptasi Qwen2.5 di `backend/olora-qwen.md` |
| O-LoRA paper | https://arxiv.org/abs/2309.01158 | — | — | ✅ baca paper, implement constraint sendiri |
| Atropos (RL training) | https://github.com/NousResearch/atropos | Apache-2.0 | — | ✅ setup guide di `backend/atropos-setup.md` |
| Avalanche (CL research) | https://github.com/ContinualAI/avalanche | MIT | 2k | ⬜ untuk self-study CL saja, tidak dipakai langsung |
| Mammoth (DER replay) | https://github.com/aimagelab/mammoth | MIT | 3k | ⬜ untuk self-study DER saja |

### Evaluasi: Autoresearch Tools (Trainer Loop Pattern)

**karpathy/autoresearch + uditgoenka/autoresearch — WORTH IT ✅ tapi TIDAK di-install — adopt patterns ke `trainer`**

| Repo | Link | License | Stars | Status |
|------|------|---------|-------|--------|
| karpathy/autoresearch | https://github.com/karpathy/autoresearch | MIT | — | 📚 patterns adopted ke trainer — fixed budget, val_bpb, git-as-memory |
| uditgoenka/autoresearch | https://github.com/uditgoenka/autoresearch | MIT | — | 📚 patterns adopted ke trainer — overnight loop, git rollback, binary eval |

**Apa karpathy/autoresearch:**
Single Python file yang loop malam hari: review state + edit `train.py` satu perubahan
→ git commit → run 5 menit → eval val_bpb → keep atau revert. ~12 experiments/jam.
Hasilnya: AI menemukan bug arsitektur atau parameter yang terlewat manusia, bahkan
pada model yang sudah dianggap optimal. Karpathy: constraint + mechanical metric +
autonomous iteration = compounding gains.

**Apa uditgoenka/autoresearch:**
Generalisasi pattern Karpathy ke domain apapun yang punya metric yang bisa diukur.
Tambahan: git rollback otomatis kalau eval turun, SKILL.md-as-program.md (agent
iterate instruksi di markdown), binary verification metric. Langsung selaras dengan
SKILL.md pattern kita yang sudah ada.

**Kenapa tidak di-install:**
Kedua repo ini adalah single-file scripts yang di-run manual di terminal — bukan
library. `trainer` kita sudah autonomous — yang kita butuhkan adalah pattern-nya,
bukan tool-nya. Install keduanya hanya menambah dependency tanpa value.

**Patterns yang diadopsi ke `trainer` (tidak duplikasi — sudah masuk `workers.md`):**
1. **Fixed time budget** `MAX_TRAIN_MINUTES = 5` — prevent overkill satu experiment
2. **Single-file scope** — trainer hanya boleh edit satu LoRA config per experiment
3. **val_bpb metric** `val_loss / ln(2)` — vocab-size-independent, fair untuk arch changes
4. **Git-as-memory** — `git commit` sebelum tiap experiment, `git reset --hard HEAD~1`
   kalau eval turun. State hidup di git, bukan RAM
5. **experiments.parquet** — semua hasil overnight loop di-persist ke Ring 2 Parquet.
   Selaras dengan Ring 2 storage kita yang sudah ada
6. **SKILL.md-as-program.md** — curator update SKILL.md trainer, trainer loop pakai
   SKILL.md sebagai "program" yang di-iterate. Pattern yang sudah ada tinggal disambung

**Rekomendasi:** Fase 4. Trainer overnight loop sudah terdokumentasi di `workers.md`.
Baca kedua repo saat implement untuk validasi implementasi kita.
| karpathy/autoresearch | https://github.com/karpathy/autoresearch | MIT | — | 📚 referensi trainer: fixed budget, val_bpb metric, git-as-memory — pattern diadopsi ke trainer, TIDAK di-install |
| uditgoenka/autoresearch | https://github.com/uditgoenka/autoresearch | — | — | 📚 referensi trainer: generalisasi ke domain non-ML, binary eval, git rollback — pattern diadopsi ke trainer, TIDAK di-install |

---

## DESIGN SYSTEM (FectTral + Impeccable)

| Repo | Link | License | Stars | Status |
|------|------|---------|-------|--------|
| FectTral SKILL-v3 | *dari FectTral.rar (file lokal)* | Apache-2.0 | — | ✅ design system utama |
| FectTral MCP server | *dari FectTral.rar (file lokal)* | Apache-2.0 | — | ✅ TypeScript + SQLite tools |
| Sigma.js (graph viz) | https://github.com/jacomyal/sigma.js | MIT | 11k | ⬜ dibutuhkan EdgeQuake frontend + DNA Report graph |
| airi (VTuber, referensi) | https://github.com/moeru-ai/airi | MIT | 17.5k | ✅ SOUL.md pattern, DuckDB WASM, tauri-plugin-mcp |

### Evaluasi: Impeccable

**pbakaus/impeccable — WORTH IT ✅ tapi TIDAK di-install — adopt concepts saja**

| Repo | Link | License | Stars | Status |
|------|------|---------|-------|--------|
| pbakaus/impeccable | https://github.com/pbakaus/impeccable | MIT | — | 📚 concepts adopted ke design workers SKILL.md |

**Apa ini:**
Open-source plugin Claude Code yang solve "AI slop" — output frontend yang selalu
convergence ke pola median (Space Grotesk, Inter, purple gradient, cards in cards).
1 skill file + 20+ commands yang define cara berpikir sebelum generate design.

**Kenapa tidak di-install:**
Kita sudah punya FectTral sebagai design identity yang lengkap — tokens, warna,
komponen, background layers. Impeccable solve problem yang sama tapi dari arah
berbeda (intentionality vs. pre-built system). Menambah keduanya sebagai dependency
menciptakan conflict. Yang kita butuhkan adalah *cara berpikirnya*, bukan tool-nya.

**Concepts yang diadopsi (tidak duplikasi — masing-masing ke tempat yang tepat):**
1. **Command vocabulary** (`/audit`, `/polish`, `/distill`, `/bolder`, `/quieter`,
   `/animate`, `/typeset`, `/colorize`, `/critique`, `/delight`, `/overdrive`)
   → masuk ke SKILL.md `compositor` dan `stylist` — bukan ditambahkan di file ini lagi
2. **Anti-pattern catalog** (Inter default, purple gradient, glassmorphism, cards-in-cards,
   Heroicons tanpa modifikasi, pill button sebagai default)
   → masuk ke `archivist` tagging system — auto-reject saat ekstrak dari web
3. **Aesthetic direction framework** (Brutal, Maximalist, Retro-futuristic, Luxury Editorial)
   → masuk ke `designer` system prompt + `aesthetic-context.json`
4. **Project aesthetic context** (`teach-impeccable` pattern)
   → selaras `room-config.json` theme system — designer maintain `aesthetic-context.json`

**Rekomendasi:** Cek Impeccable saat implement design workers Fase 2 untuk validate
command vocabulary yang kita adopt sudah cover semua use case-nya.

---

## FRONTEND DESIGN QUALITY

> **Konteks:** FectTral mendefinisikan *tokens + hasil akhir* vibe-office UI.
> Impeccable mendefinisikan *proses berpikir estetika* sebelum generate —
> intentionality, differentiation, "apa yang membuat ini unforgettable."
> Keduanya tidak overlap — saling melengkapi.

### Evaluasi: Impeccable

**pbakaus/impeccable — WORTH IT ✅ — concepts diadopsi ke SKILL.md design workers, tidak di-install**

| Repo | Link | License | Stars | Status |
|------|------|---------|-------|--------|
| pbakaus/impeccable | https://github.com/pbakaus/impeccable | — | — | 📚 vocabulary + anti-patterns diadopsi ke design-workers.md |

**Apa ini:**
Plugin Claude Code untuk mengatasi "AI slop" di frontend — output AI yang selalu
convergence ke Inter font, purple gradient, cards in cards. Impeccable mendorong
pilihan estetika ekstrem dan intentional: Brutalist, Maximalist, Retro-futuristic,
Luxury Editorial. 1 skill file, 20+ slash commands, curated anti-pattern catalog.

**Kenapa tidak di-install sebagai dependency:**
Kita sudah punya FectTral sebagai full design system. Impeccable adalah Claude Code
plugin — bukan library yang bisa di-embed. Menginstall Impeccable di atas FectTral
akan conflict karena keduanya define aesthetic direction.

**Konsep yang diadopsi (tanpa install):**

1. **Command vocabulary → masuk SKILL.md compositor + stylist:**
   `/audit` (cek apakah UI terasa generic), `/polish` (refine detail),
   `/distill` (kurangi noise), `/bolder` (push aesthetic lebih jauh),
   `/quieter` (kurangi visual noise), `/animate` (tambah motion),
   `/typeset` (improve typography hierarchy), `/colorize` (strengthen color),
   `/critique` (honest assessment), `/delight` (add unexpected detail),
   `/overdrive` (push ke ekstrem — pakai dengan hati-hati)

2. **Anti-pattern catalog → masuk archivist reject list:**
   Inter/Plus Jakarta Sans sebagai font default, purple-to-blue gradient hero,
   cards inside cards, frosted glass overuse, "AI blue" (#3B82F6) sebagai accent,
   centered everything layout, ghost buttons dengan border-radius: 9999px

3. **Aesthetic direction system → extend room-config.json:**
   User bisa set project aesthetic context yang di-persist (Brutalist, Maximalist,
   dll) — selaras dengan theme system yang sudah ada di room-config.json kita.
   Designer worker baca ini saat orchestrate.

**Detail implementasi:** lihat `design/design-workers.md` section "Impeccable Adoption"

---

## SCOUT & WEB FETCHING

> **Konteks:** Scout pakai Lightpanda untuk scrape. Tanpa optimasi, Lightpanda
> return HTML mentah → boros token. Cloudflare Markdown for Agents solve ini
> dengan satu header HTTP — 80-99% token reduction.

### Evaluasi: Cloudflare Markdown for Agents

**Cloudflare Markdown for Agents — WORTH IT ✅ — implement di scout HTTP layer Fase 3, bukan worker baru**

| Resource | Link | Status |
|----------|------|--------|
| Cloudflare blog post | https://blog.cloudflare.com/markdown-for-agents/ | ✅ implement Fase 3 |
| Cloudflare docs | https://developers.cloudflare.com/workers/static-assets/markdown-for-agents/ | ✅ referensi |

**Apa ini:**
Cloudflare-powered sites (mayoritas web) bisa return halaman sebagai markdown
bukan HTML — cukup kirim `Accept: text/markdown` header. 16,180 token HTML →
3,150 token markdown. 80% reduction. Response include `x-markdown-tokens` header
dengan estimated token count. Claude Code dan OpenCode sudah kirim header ini
secara default.

**Kenapa bukan worker baru:**
Ini adalah satu header HTTP tambahan di scout's fetch layer — bukan domain kerja
baru. Worker baru hanya justified kalau ada fungsi baru. Ini adalah upgrade
infrastruktur yang invisible ke worker lain.

**Konsep tambahan yang diambil:**
- `x-markdown-tokens` header → scout report token estimate ke conductor sebelum
  pass context. Conductor bisa decide: "terlalu besar, minta scout summarize via RLM."
- Structured error responses (RFC 9457) → saat rate-limited, dapat instruksi jelas
  bukan HTML error page. Scout's retry logic jadi deterministic.
- Fallback: kalau site tidak support markdown (non-Cloudflare), tetap return HTML
  → arsitek `MarkdownFetcher` wrapper handle ini transparently

**Detail implementasi:** lihat `backend/scout-auto-mode.md` section "MarkdownFetcher"

---

## MULTIMODAL GATEWAY (Fase 4-6)

> **Visi:** Vibe-office bukan hanya kantor yang bisa dilihat di desktop.
> Fase 6 = kantor yang bisa kamu telepon dari mana saja — WA, foto, YouTube,
> Chrome, robot fisik. Fondasi: OpenClaw/nanobot sebagai messaging gateway.
> Workers vibe-office exposed sebagai skills. Conductor tetap orchestrator tunggal.

### Evaluasi: OpenClaw + NemoClaw — WORTH IT ✅ Fase 6 vision

| Resource | Link | License | Stars | Status |
|----------|------|---------|-------|--------|
| openclaw/openclaw | https://github.com/openclaw/openclaw | MIT | 247k | ⬜ Fase 6 — expose workers sebagai OpenClaw skills |
| ClawHub skill registry | https://clawstore.openclaw.ai | — | 5.4k skills | ⬜ publish workers ke ClawHub Fase 6 |
| agent-team-orchestration skill | https://clawstore.openclaw.ai/skills/agent-team-orchestration | — | — | ⬜ referensi orchestration pattern multi-agent |
| **NVIDIA/NemoClaw** | **https://github.com/NVIDIA/NemoClaw** | Apache-2.0 | — | **⬜ Fase 6 — security layer wajib sebelum expose ke public gateway** |
| NemoClaw official | https://www.nvidia.com/en-us/ai/nemoclaw/ | — | — | ⬜ dokumentasi resmi NVIDIA |
| NemoClaw press release | https://nvidianews.nvidia.com/news/nvidia-announces-nemoclaw | — | — | ⬜ context GTC 2026 announcement |

**Apa OpenClaw:**
Free open-source autonomous AI agent yang pakai messaging platforms sebagai main UI.
247k stars, 47.7k forks. Support: WhatsApp, Telegram, Slack, Discord, Signal,
iMessage, iOS/Android nodes, Pi agent via RPC. Browser control via CDP.
ClawHub: skill registry dengan 5,400+ skills — community-built, composable.

**Apa NemoClaw (NVIDIA GTC 2026, 16 Maret 2026):**
NemoClaw adalah security + privacy stack yang di-install di atas OpenClaw dalam
satu command. Diumumkan di GTC 2026 oleh NVIDIA. Langsung solve security concern
terbesar kita untuk Fase 6 — sebelumnya kita catat "WAJIB security review" tapi
belum ada solusi konkret. NemoClaw adalah solusinya.

```bash
# Install NemoClaw di atas OpenClaw — satu command
nemoclaw install --with-openstack --model nemotron-local
```

**Fitur NemoClaw yang relevan untuk vibe-office Fase 6:**
- **OpenShell runtime**: kernel-level sandboxing, setiap network request + file access
  diatur oleh declarative policy. Ini adalah sandbox isolation yang kita butuhkan.
- **Privacy router**: monitor behavior dan komunikasi OpenClaw dengan sistem lain.
  Logs semua requests — audit trail yang kita butuhkan.
- **Policy-based guardrails**: define apa yang boleh dan tidak boleh dilakukan agent
  secara declarative. Ini adalah input sanitization layer kita.
- **Nemotron models lokal**: NVIDIA open models yang bisa run lokal tanpa API call.
  Alternatif untuk workers kita yang butuh local inference.
- **Model-agnostic**: bisa run dengan OpenAI, Anthropic, atau Nemotron family.
  Tidak perlu ganti model stack kita.

⚠️ **Status:** Early-stage alpha release per Maret 2026 — "expect rough edges,
building toward production-ready sandbox orchestration." Jangan pakai di Fase 5
sebelum ada stable release. Pantau repo untuk update.

**Update arsitektur integrasi vibe-office ↔ OpenClaw + NemoClaw:**

```
USER (WA/Telegram/Discord)
  ↓
NemoClaw Gateway (OpenClaw + security layer)
  ↓ [kernel sandbox + privacy router + policy guardrails]
vibe-office Skill Set (exposed via OpenClaw)
  ↓
conductor (tetap orchestrator tunggal — TIDAK berubah)
  ↓
workers (sama persis dengan standalone mode)
  ↓
output → narrator → NemoClaw → reply ke user
```

**Update strategi rollout (dengan NemoClaw):**
```
Fase 4: Vibe-office standalone
Fase 5: nanobot local-only — test multi-modal di desktop
Fase 6: NemoClaw gateway — tunggu stable release dulu
         pantau: github.com/NVIDIA/NemoClaw
         deploy saat: bukan lagi alpha, kernel sandbox proven
Fase 6+: Publish selected workers ke ClawHub
```

**Input types yang akan bisa diterima vibe-office di Fase 6:**

| Input Type | Gateway | Handler di vibe-office |
|------------|---------|------------------------|
| Pesan teks | WhatsApp/Telegram/Discord via NemoClaw | intake worker (sudah ada) |
| Foto/gambar | iOS/Android node → NemoClaw | worker vision baru (Fase 6) |
| YouTube video | scout via yt-dlp + RLM summarize | scout proactive_research |
| Chrome browsing | CDP via NemoClaw browser control | scout on_demand |
| File/dokumen | iCloud/Google Drive node | curator knowledge injection |
| Robot/IoT | Pi agent via RPC | worker IoT baru (Fase 6+) |
| Voice | Audio node → transcribe → intake | intake (pre-processing step) |

**Cara expose workers sebagai OpenClaw skills:**
```python
# Setiap worker jadi satu OpenClaw skill
# plugin.json worker sudah compatible — tinggal extend dengan OpenClaw schema

# workers/coder_rust/openclaw_skill.json
{
  "name": "vibe-office:coder_rust",
  "description": "Rust coding specialist — write, debug, refactor Rust code",
  "trigger_phrases": ["write rust", "fix rust", "rust code", "cargo"],
  "input_schema": {
    "instruction": "string",
    "files": "optional array"
  },
  "endpoint": "ws://localhost:8765/skill/coder_rust",
  "auth": "tauri_local_only"  # atau NemoClaw policy token kalau public
}
```

---

### Evaluasi: nanobot (HKUDS) — WORTH IT ✅ Fase 4-5 lighter alternative

| Resource | Link | License | Stars | Status |
|----------|------|---------|-------|--------|
| HKUDS/nanobot | https://github.com/HKUDS/nanobot | MIT | — | ⬜ Fase 4-5 — lighter alternative untuk early multi-modal testing |

**Apa ini:**
Ultra-lightweight OpenClaw alternative. 99% fewer lines of code.
Multi-modal: image, voice, video input native. Long-term memory built-in.
Multi-step planning. Support Ollama, Claude, semua major providers.
Sudah proven dengan Qwen2.5-VL dan LLaMA-3.2-Vision untuk image tasks.

**Kenapa nanobot lebih cocok untuk Fase 4-5 daripada full OpenClaw:**
- OpenClaw = production system dengan ratusan dependencies → heavy untuk embed di Tauri
- nanobot = ringan, bisa embed langsung sebagai Python subprocess dari Tauri backend
- nanobot multi-modal native → foto input langsung dari Fase 4 tanpa build custom handler
- Kalau nanobot sukses di Fase 5, upgrade ke OpenClaw di Fase 6 lebih mudah
  karena skill format compatible

**Use case pertama di Fase 4 (sebelum full multi-modal):**
Photo input untuk room-config — user foto ruangan nyata, nanobot convert ke
room-config.json draft untuk room editor. `life_manager` lalu generate
daily_rules.json berdasarkan dekorasi yang terdeteksi dari foto.

```python
# backend/multimodal/photo_handler.py — Fase 4
# Dibuat saat implement nanobot integration

import subprocess
import base64
from pathlib import Path

async def photo_to_room_config(image_path: str) -> dict:
    """
    User foto ruangan → nanobot analyze → draft room-config.json.
    Pakai vision model (Qwen2.5-VL atau LLaMA-3.2-Vision via Ollama).
    """
    # Encode image
    image_data = base64.b64encode(Path(image_path).read_bytes()).decode()

    # nanobot call dengan vision model
    result = await nanobot_call(
        model="qwen2.5-vl:7b",  # atau llava, llama-3.2-vision via Ollama
        prompt=(
            "Analyze this room photo. List all furniture and decorations you see. "
            "Output JSON: {rooms: [{id, decorations: [{type, position}]}]}"
        ),
        image=image_data,
    )

    # Draft room-config.json
    room_config = parse_nanobot_result(result)

    # life_manager akan generate daily_rules.json dari ini
    return room_config
```

---

### Evaluasi: DeepAgents (LangChain) — WORTH IT ✅ Fase 4 conductor backbone

| Resource | Link | License | Stars | Status |
|----------|------|---------|-------|--------|
| langchain-ai/deepagents | https://github.com/langchain-ai/deepagents | MIT | — | ⬜ Fase 4 — evaluate sebagai conductor backbone |
| LangGraph (underlying) | https://github.com/langchain-ai/langgraph | MIT | 13k | ⬜ underlying runtime, low-level fallback |

**Apa ini:**
Agent harness terinspirasi langsung dari Claude Code. `uv add deepagents` dan
kamu punya working agent. Features yang langsung relevan untuk conductor:
- `write_todos` planning tool — conductor planning yang explicit dan traceable
- FilesystemBackend — conductor offload planning artifacts ke disk, bukan RAM
- Subagent spawning — conductor spawn `scout`, `coder_*`, dll sebagai isolated subagents
- Multiple backends: StateBackend, FilesystemBackend, LocalShellBackend, StoreBackend, CompositeBackend
- QuickJS REPL support — selaras dengan Advanced Tool Use Programmatic Tool Calling
- Batteries included vs LangGraph yang butuh extensive setup

**Kenapa upgrade dari LangGraph bookmark:**
DeepAgents lebih opinionated tapi lebih langsung applicable untuk conductor use case.
LangGraph butuh lebih banyak boilerplate untuk hal-hal yang DeepAgents sudah provide
out-of-the-box. Conductor kita butuh planning, context management, dan subagent
spawning — semua ada di DeepAgents tanpa setup tambahan.

**Cara evaluate Fase 4:**
```python
# Test DeepAgents sebagai conductor backbone
# Bandingkan dengan custom conductor yang sudah kita design

from deepagents import Agent, FilesystemBackend, write_todos

async def conductor_deepagents(task: dict) -> dict:
    """
    Prototype conductor menggunakan DeepAgents.
    Evaluate vs custom conductor — mana yang lebih reliable?
    """
    backend = FilesystemBackend(base_dir="~/.vibe-office/conductor_state/")

    agent = Agent(
        model="qwen2.5:32b",  # atau claude-opus-4-6
        tools=[
            write_todos,  # planning tool
            # + semua worker tools dengan defer_loading=True (Advanced Tool Use)
        ],
        backend=backend,
    )

    # Conductor planning via DeepAgents
    result = await agent.run(
        f"Plan and execute: {task['instruction']}. "
        f"Available workers: {list_workers()}. "
        f"Use write_todos first to plan steps."
    )

    return extract_conductor_result(result)
```

**Keputusan final:** Evaluate di Fase 4 — jika DeepAgents > custom conductor dalam
planning accuracy + reliability, adopt sebagai backbone. Kalau custom conductor
sudah mature, DeepAgents menjadi optional enhancement bukan replacement.

---

### Evaluasi: Zencoder — SKIP install, AMBIL 2 patterns

| Resource | Link | Status |
|----------|------|--------|
| zencoder.ai | https://zencoder.ai/ | 📚 commercial — 2 patterns diadopsi |

**Apa ini:** Commercial AI coding agent. $19-250/user/month.
Multi-model validation (Claude review kode yang ditulis GPT), Repo Grokking™,
cross-repo dependency mapping dengan daily updates.

**Kenapa tidak install:** Commercial pricing, bukan open-source.
Fungsi utamanya sudah ditangani lebih baik oleh kombinasi yang kita punya:
GitNexus + PR-Agent + Advanced Tool Use + RLM.

**2 Patterns yang diadopsi (source of truth di workers.md):**

**Pattern 1 — Multi-model validation untuk auditor:**
Zencoder: Claude review kode yang ditulis GPT — model diversity eliminate blind spots.
Untuk kita: auditor `periodic_audit` mode run dengan model A, verifikasi dengan model B.
Implemented di workers.md → auditor section sebagai `periodic_audit_multi_model()`.

**Pattern 2 — Daily scheduled GitNexus re-index untuk scout:**
Zencoder: daily cross-repo dependency updates, bukan hanya post-commit.
Untuk kita: scout punya scheduled daily re-index via GitNexus, selain post-commit trigger.
Implemented di workers.md → scout section sebagai `daily_reindex_schedule`.

---

## REFERENSI ARSITEKTUR (self-study only, tidak diintegrasikan langsung)

| Repo / Resource | Link | License | Stars | Catatan |
|----------------|------|---------|-------|---------|
| SpacetimeDB | https://github.com/clockworklabs/SpacetimeDB | BSL 1.1 | 22.6k | Alternatif state sync — PoC di Fase 3 |
| InsForge | https://github.com/InsForge/InsForge | Apache-2.0 | 1.3k | Konsep plugin.json worker identity |
| claude-plugins-official | https://github.com/anthropics/claude-plugins-official | MIT | 9.4k | Format SKILL.md standard |
| Say-I-Dont-Know (paper) | https://github.com/OpenMOSS/Say-I-Dont-Know | — | 85 | Knowledge quadrant, uncertainty detection |
| L2P (vision, skip) | https://github.com/google-research/l2p | Apache-2.0 | — | Vision only, tidak relevan untuk NLP workers |
| KARL (Databricks paper) | https://www.databricks.com/blog/karl-knowledge-agents-via-reinforcement-learning | — | — | Fase 4-5 — RL internalize SKILL.md ke weights |
| JSON-Render (Vercel) | https://github.com/vercel-labs/json-render | MIT | 10.5k | Pattern diadopsi ke compositor + FectTral MCP |
| mHC (tokenbender/DeepSeek) | https://github.com/tokenbender/mHC-manifold-constrained-hyper-connections | MIT | — | Arsitektur training — hanya relevan kalau pre-train dari scratch |
| AttnRes (Moonshot/Kimi) | https://github.com/MoonshotAI/Attention-Residuals | — | — | Companion mHC, arXiv:2603.15031 — drop-in residual replacement, <2% inference overhead |
| NemoClaw (NVIDIA) | https://github.com/NVIDIA/NemoClaw | Apache-2.0 | — | Fase 6 security layer untuk OpenClaw — alpha, pantau untuk stable release |
| Mechanistic Interpretability (Nanda) | https://www.neelnanda.io/mechanistic-interpretability/200-concrete-problems | — | — | Grokking phases → brain viz Tab 4 Loss Curve |
| Stripe Minions | https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents | — | — | 4 patterns diadopsi: tool subsets, det/agentic labels, retry cap, dir-scoped rules |
| **WW-AI-Lab/openclaw-office** | https://github.com/WW-AI-Lab/openclaw-office | MIT | — | **BACA SEBELUM FASE 2** — isometric office, WebSocket schema, avatar, speech bubble patterns |
| AgentScope (Alibaba) | https://github.com/agentscope-ai/agentscope | Apache-2.0 | 18.2k | MsgHub pattern → referensi bridge worker, group-wise tool management |
| AgentScope Runtime | https://github.com/agentscope-ai/agentscope-runtime | Apache-2.0 | — | Sandbox types, interrupt service → referensi conductor recovery |
| AgentScope Trinity-RFT | https://github.com/agentscope-ai/Trinity-RFT | Apache-2.0 | — | RL fine-tuning framework dari Alibaba → referensi trainer Fase 4-5 |
| MassGen | https://github.com/massgen/MassGen | MIT | — | React+WebSocket real-time visualization, timeline views → referensi UI Fase 2 |
| GMvandeVen/continual-learning | https://github.com/GMvandeVen/continual-learning | MIT | — | EWC/SI/LwF/ER PyTorch — referensi trainer, tapi O-LoRA mungkin cukup |
| ICLR 2025 blog (Fisher Info) | https://github.com/GMvandeVen/continual-learning/tree/master/ICLR-blogpost | — | — | Fisher Information in continual learning — selaras dengan grokking detection |

---

## VISUAL OFFICE REFERENCE (Fase 2 — BACA SEBELUM IMPLEMENT)

> **Ini adalah section terpenting untuk Fase 2.** openclaw-office sudah implement
> hampir semua yang kita mau build. WAJIB baca source code-nya sebelum mulai
> Fase 2 — jangan reinvent wheel, ambil patterns yang sudah proven.

### WW-AI-Lab/openclaw-office — KRITIKAL ✅ referensi Fase 2

| Resource | Link | Status |
|----------|------|--------|
| openclaw-office (main) | https://github.com/WW-AI-Lab/openclaw-office | 📚 **BACA SEBELUM FASE 2** |
| NPM package | https://www.npmjs.com/package/@ww-ai-lab/openclaw-office | 📚 bisa run langsung: `npx @ww-ai-lab/openclaw-office` |

**Apa ini:**
Visual monitoring dan management frontend untuk OpenClaw Multi-Agent system.
React + WebSocket, isometric SVG 2D floor plan + React Three Fiber 3D scene,
agent avatars dengan status animations, collaboration lines antar agents,
speech bubbles, side panels dengan charts, dan full console management.

**Core metaphor yang sama persis dengan vibe-office:**
Agent = Digital Employee | Office = Agent Runtime | Desk = Session | Meeting Pod = Collaboration Context

**Fitur yang sudah proven dan bisa kita jadikan referensi langsung:**

```
FITUR openclaw-office → RELEVANSI untuk vibe-office
─────────────────────────────────────────────────────
2D Floor Plan (SVG isometric)     → referensi zone layout + furniture tiles
3D Scene (React Three Fiber)      → opsional Fase 5+ upgrade dari pixel art
Agent Avatars (deterministic SVG) → referensi avatar generation dari worker ID
  idle/working/speaking/tool_calling/error states
Collaboration Lines               → visualisasi bridge routing antar workers
Speech Bubbles (live Markdown)    → kita sudah punya, tapi punya live streaming
Side Panels                       → Token charts, cost pie, activity heatmap,
                                    SubAgent graph, event timeline → referensi
                                    untuk status popup + stats di CEO office
Chat Dock                         → referensi chat-panel.md kita
WebSocket Schema                  → event-parser.ts mapping lifecycle events
                                    ke visual states — BACA sebelum implement
                                    backend/websocket-events.md Fase 1
```

**WebSocket event schema (dari AGENTS.md openclaw-office):**
```typescript
// Event schema yang sudah proven — adapt untuk vibe-office
type AgentEventPayload = {
  runId: string
  seq: number
  stream: "lifecycle" | "tool" | "assistant" | "error"
  ts: number
  data: Record<string, unknown>
  sessionKey?: string
}

// RPC methods yang exposed: agents.list, sessions.list, usage.status,
// tools.catalog, chat.send, chat.abort, chat.history
// → Kita bisa adapt ini untuk vibe-office WebSocket API
```

**Folder structure yang relevan untuk dipelajari:**
```
openclaw-office/src/
├── gateway/
│   ├── ws-client.ts      ← WebSocket + auth + reconnect pattern
│   ├── rpc-client.ts     ← RPC wrapper — referensi untuk conductor API
│   ├── event-parser.ts   ← mapping lifecycle events → visual states
│   └── mock-adapter.ts   ← SANGAT BERGUNA: simulate data untuk dev Fase 1
├── store/
│   └── office-store.ts   ← Zustand state management — referensi untuk
│                            workerManager.ts kita
├── components/
│   ├── office-2d/        ← SVG floor plan + furniture
│   ├── overlays/         ← speech bubbles HTML overlay
│   └── panels/           ← detail/metrics/chart panels
```

**Yang BERBEDA dari vibe-office (jangan ikuti ini):**
- Stack: React SVG/R3F (mereka) vs React Canvas pixel art (kita) — beda fundamental
- Mereka tidak punya pixel art game feel — itu yang membuat vibe-office unik
- Mereka connect ke OpenClaw Gateway yang sudah running — kita build backend sendiri

**Cara baca sebelum Fase 2:**
```bash
git clone https://github.com/WW-AI-Lab/openclaw-office /tmp/openclaw-office-ref
# Baca secara urutan:
# 1. src/gateway/event-parser.ts  → mapping states
# 2. src/gateway/mock-adapter.ts  → cara simulate data (langsung pakai untuk Fase 1)
# 3. src/store/office-store.ts    → state management pattern
# 4. src/components/office-2d/   → SVG floor plan untuk inspirasi zone layout
```

---

## MULTI-AGENT FRAMEWORK REFERENCE

> **Frameworks yang sudah battle-tested — bukan untuk di-install, tapi
> source code-nya adalah referensi implementasi konkret untuk bridge dan conductor.**

### AgentScope (Alibaba DAMO) — WORTH IT ✅ referensi bridge + conductor

| Resource | Link | License | Stars | Status |
|----------|------|---------|-------|--------|
| agentscope-ai/agentscope | https://github.com/agentscope-ai/agentscope | Apache-2.0 | 18.2k | 📚 MsgHub → referensi bridge worker |
| agentscope-ai/agentscope-runtime | https://github.com/agentscope-ai/agentscope-runtime | Apache-2.0 | — | 📚 sandbox + interrupt → referensi conductor recovery |
| agentscope-ai/Trinity-RFT | https://github.com/agentscope-ai/Trinity-RFT | Apache-2.0 | — | 📚 RL fine-tuning → referensi trainer Fase 4-5 |

**Kenapa tidak di-install:** Framework opinionated yang akan conflict dengan arsitektur
custom kita. Kita sudah punya struktur workers yang spesifik — import AgentScope
akan bawa banyak abstraksi yang tidak kita butuhkan.

**Patterns konkret yang diadopsi:**

**1. MsgHub → referensi bridge worker:**
AgentScope MsgHub: `async with MsgHub(participants=[agent1, agent2, agent3]) as hub: hub.add(agent4); hub.delete(agent3); await hub.broadcast(msg)`

Bridge kita saat ini pakai static `TRANSFORM_RULES` dict. MsgHub pattern dari
AgentScope menunjukkan cara yang lebih elegant: dynamic participant management,
broadcast ke semua atau subset, dan add/remove participants saat runtime.
Ini berguna untuk Fase 3 saat workers bisa hire/fire dinamis.

```python
# Pattern yang bisa kita adapt untuk bridge Fase 3
# Bukan import AgentScope — adapt logic-nya saja

class WorkerHub:
    """
    Inspired by AgentScope MsgHub — dynamic participant management.
    Bridge kita jadi lebih flexible untuk hire/fire workers runtime.
    """
    def __init__(self):
        self._participants: dict[str, Worker] = {}
        self._message_log: list[dict] = []

    def add(self, worker: Worker):
        self._participants[worker.id] = worker
        # Auto-update TRANSFORM_RULES untuk worker baru

    def remove(self, worker_id: str):
        self._participants.pop(worker_id, None)

    async def broadcast(self, msg: dict, to: list[str] | None = None):
        """Broadcast ke semua atau subset workers."""
        targets = to or list(self._participants.keys())
        for wid in targets:
            if wid in self._participants:
                await self._participants[wid].receive(msg)

    async def relay(self, from_id: str, to_id: str, msg: dict) -> dict:
        """Point-to-point relay dengan transform (existing bridge logic)."""
        return await self._transform_and_send(from_id, to_id, msg)
```

**2. Group-wise tool management → extend conductor tool subsets:**
AgentScope: tools yang saling berkaitan di-group, bukan isolated options. Web automation task = navigate URL + click elements + enter text — disajikan sebagai group, bukan individual tools.

Ini extend `TASK_TYPE_TOOL_SUBSETS` kita — bukan hanya per task_type, tapi
juga grouping semantic berdasarkan workflow natural. Relevant untuk Fase 3.

**3. Distributed Interrupt Service (agentscope-runtime) → conductor recovery:**
AgentScope Runtime v1.1: Distributed Interrupt Service — manual task preemption saat agent execution, customize state persistence dan recovery logic.

Ini adalah pattern yang lebih sophisticated dari Tier 1-2-3 recovery kita.
Baca `agentscope-runtime` source sebelum implement conductor recovery Fase 3.

**4. Trinity-RFT → referensi trainer RL Fase 4-5:**
AgentScope Trinity-RFT adalah general-purpose framework untuk RL fine-tuning LLMs
dari Alibaba. Ini bisa jadi referensi implementasi konkret untuk KARL patterns
yang sudah kita dokumentasikan di training-landscape.md.

---

### MassGen — WORTH IT ✅ referensi real-time visualization UI

| Resource | Link | License | Stars | Status |
|----------|------|---------|-------|--------|
| massgen/MassGen | https://github.com/massgen/MassGen | MIT | — | 📚 React+WebSocket timeline view → referensi UI Fase 2 |

**Apa ini:**
MassGen Web UI: React frontend, WebSocket streaming, timeline views, workspace browsing. Claude Advanced Tooling: programmatic tool calling via `enable_programmatic_flow`, server-side tool discovery via `enable_tool_search` dengan regex atau bm25.

**Patterns relevan untuk vibe-office:**
- **Timeline view** — visualisasi urutan events per worker secara chronological.
  Ini adalah apa yang kita butuhkan di TV screen meeting room — bukan hanya
  speech bubble terakhir, tapi history semua events sebagai timeline.
- **WebSocket streaming** — cara mereka stream agent output ke React frontend
  bisa jadi referensi untuk `narrator` → TV screen rendering.
- `enable_tool_search` dengan bm25 — ini adalah alternatif dari `tool_search_tool_regex`
  yang sudah kita adopt. Bisa jadi fallback kalau Advanced Tool Use beta belum stabil.

---

### GMvandeVen/continual-learning — REFERENSI ✅ EWC untuk trainer

| Resource | Link | License | Stars | Status |
|----------|------|---------|-------|--------|
| GMvandeVen/continual-learning | https://github.com/GMvandeVen/continual-learning | MIT | — | 📚 EWC/SI/LwF/ER PyTorch implementation |
| ICLR 2025 Fisher Info blogpost | https://github.com/GMvandeVen/continual-learning/tree/master/ICLR-blogpost | — | — | 📚 Fisher Information computation |

**Apa ini:**
PyTorch implementation EWC, SI, LwF, FROMP, DGR, BI-R, ER, A-GEM, iCaRL, Generative Classifier. Dipakai untuk NeurIPS 2022 tutorial dan ICLR 2025 blogpost tentang Fisher Information.

**Catatan penting sebelum implement:**
Temuan terbaru dari komunitas: untuk large pre-trained models seperti Qwen2.5-Coder-7B,
naive rehearsal (mixing old training data) sering beats semua CL techniques termasuk EWC.
O-LoRA yang sudah kita punya (orthogonal constraint) memberikan anti-forgetting yang
comparable tanpa overhead Fisher Information computation.

**Kapan EWC berguna untuk kita:**
Hanya kalau di Fase 5 workers kita mulai show catastrophic forgetting yang
O-LoRA tidak bisa handle — terutama untuk domains yang overlap secara
semantic (misalnya coder_rust `async` domain vs coder_python `async` domain).
Baca ICLR 2025 blogpost untuk understand Fisher Information computation sebelum decide.

**Rekomendasi:** Fase 5, setelah O-LoRA proven insufficent. Baca repo ini untuk
understand trade-offs antara EWC, SI, dan ER sebelum implement apapun.

---

> **Reading list untuk implementasi brain visualization Fase 4.
> Concepts sudah masuk brain-visualization.md dan training-landscape.md.
> Tidak ada yang di-install — ini research framework berpikir.**

| Resource | Link | Dipakai untuk |
|----------|------|---------------|
| Grokking paper (Nanda et al., ICLR 2023) | https://arxiv.org/abs/2301.05217 | training_phase detection: memorizing → circuit_forming → grokked |
| Alignment Forum deep analysis | https://www.alignmentforum.org/posts/N6WM6hs7RQMKDhYjB/a-mechanistic-interpretability-analysis-of-grokking | 3 fase detail, cleanup phase, weight decay role |
| 200 open problems (Neel Nanda) | https://www.neelnanda.io/mechanistic-interpretability/200-concrete-problems | long-term research direction trainer Fase 5 |

**Key insight untuk implementasi:**
Training bagi tiga fase yang continuous: memorization → circuit formation → cleanup.
"Grokking tiba-tiba" sebenarnya adalah fase cleanup yang buang memorization circuits
dan tinggalkan generalizing circuits. Trainer detect ini dari loss curve shape.

**Concepts yang sudah diadopsi (source of truth di file berikut):**
- `frontend/brain-visualization.md`:
  - `LoRAMetadata` fields: `training_phase`, `grokking_confidence`, `loss_curve`, `circuit_count`
  - `WorkerBrainState` fields: `grokked_count`, `memorizing_count`, `overall_health`
  - Component `TrainingPhaseOverview` — Tab 1 DNA Overview
  - Component `GrokEventAnnotations` — Tab 4 Loss Curve
  - Tab 4 Loss Curve selengkapnya — pilih LoRA, lihat phase banner, loss chart, events
  - Backend API: `GET /brain/{worker_id}/loss-curve/{lora_name}`
  - Backend API: `GET /brain/{worker_id}/grokking-phase/{lora_name}`
  - `detect_grokking_events()` function — threshold 15%, window 10 steps
- `backend/training-landscape.md`:
  - Trainer simpan loss curve snapshots ke Ring 2 experiments.parquet
  - Auto-run grokking analysis setelah setiap training run
  - Jangan activate LoRA kalau `grokking_confidence < 0.4`

---

## AGENTIC ARCHITECTURE PATTERNS

> **Patterns dari production systems — concepts diadopsi, tidak di-install.**

### Stripe Minions Patterns

| Resource | Link | Status |
|----------|------|--------|
| Blog post | https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents | 📚 4 patterns diadopsi ke workers.md |

**Apa ini:** Stripe's internal agentic coding system — ~500 MCP tools via Toolshed,
hybrid deterministic+agentic blueprints, directory-scoped rule files, 2 CI round cap.

**Kenapa tidak install Toolshed:**
Advanced Tool Use kita sudah lebih sophisticated. Yang diambil adalah patterns
di sekitar tool management dan pipeline design.

**4 Patterns yang diadopsi (source of truth di workers.md):**

| Pattern | Implementasi | Location |
|---------|--------------|----------|
| Task-type → tool subset | `TASK_TYPE_TOOL_SUBSETS` dict | workers.md → Post-Coding Pipeline |
| Deterministic vs Agentic labels | Pipeline annotation setiap step | workers.md → Post-Coding Pipeline |
| MAX_RETRY_CAP = 2 | `run_tester()` function | workers.md → tester section |
| Directory-scoped SKILL loading | `DIRECTORY_SKILL_MAP` dict | workers.md → Post-Coding Pipeline |

### mHC (Manifold-Constrained Hyper-Connections)

| Resource | Link | Status |
|----------|------|--------|
| tokenbender/mHC | https://github.com/tokenbender/mHC-manifold-constrained-hyper-connections | 📚 self-study only |
| DeepSeek evaluation | (dari paper yang diimplementasi di repo atas) | 📚 27B transformer benchmark |

**Apa ini:** Arsitektur pengganti skip connections di transformer. 4 parallel residual
paths + Sinkhorn-Knopp algorithm untuk constrain ke Birkhoff polytope (doubly stochastic).
Solve gradient explosion 3000× yang terjadi di unconstrained version.
Custom GPU kernels: 3× less memory traffic, 6.7% compute overhead.

**Kenapa di-skip:**
mHC adalah arsitektur modification yang hanya berlaku kalau pre-train dari scratch.
Kita adalah users dan fine-tuners — Unsloth LoRA tidak menyentuh residual connections.
Tidak relevant untuk vibe-office use case.

**Satu-satunya koneksi dengan vibe-office:**
Konsep bahwa ada geometric structure (manifold) di weights selaras dengan
Mechanistic Interpretability findings (Claude 3.5 Haiku 6D manifold untuk character counting,
grokking trigonometric circuits). Ini adalah bukti bahwa neural networks learn
interpretable geometric structures — yang justifies kenapa brain viz kita bermakna.

**Kapan mHC relevant:** Hanya kalau Fase 5+ kita putuskan pre-train custom base model.
Extremely unlikely. Bookmark saja.

---

### AttnRes (Attention Residuals) — Moonshot/Kimi

> **Companion ke mHC** — dua approach berbeda untuk solve masalah yang sama.
> tokenbender (author mHC) sendiri compare keduanya: "AttnRes is still more
> retrieval-like than mHC, but less exact than full AttnRes."
>
> **Koreksi nama dari video:** Video menyebut "Intention Residual" — nama yang benar
> adalah **Attention Residuals (AttnRes)** dari Kimi Team, Moonshot AI.

| Resource | Link | Status |
|----------|------|--------|
| MoonshotAI/Attention-Residuals | https://github.com/MoonshotAI/Attention-Residuals | 📚 self-study only |
| arXiv paper | https://arxiv.org/abs/2603.15031 | 📚 published 16 Maret 2026 |

**Apa ini:**
AttnRes adalah drop-in replacement untuk standard residual connections di Transformer.
Setiap layer secara selektif aggregate representasi dari layers sebelumnya via
learned, input-dependent attention over depth — bukan hanya dari layer sebelumnya saja.

**Benchmark terverifikasi:**
- Matching ~1.25× more baseline compute (sama dengan mHC)
- Training overhead <4%, inference latency overhead <2%
- Tested pada language modeling dan code generation tasks

**Perbedaan dengan mHC:**
| Aspek | mHC | AttnRes |
|-------|-----|---------|
| Mechanism | 4 parallel residual paths + Sinkhorn-Knopp | Attention over depth |
| Focus | Gradient stability (prevent 3000× explosion) | Selective depth aggregation |
| Overhead | 6.7% compute | <4% training, <2% inference |
| Implementation | Custom GPU kernels | Drop-in replacement, no custom kernels |
| Author | tokenbender (community) | Kimi Team / Moonshot AI |

**Kenapa di-skip (sama dengan mHC):**
Hanya relevant kalau pre-train dari scratch. Kita fine-tune dengan Unsloth LoRA
yang tidak menyentuh residual connections. Bookmark untuk Fase 5+ kalau ada
rencana pre-train custom base model.

**Koneksi dengan vibe-office (sama dengan mHC):**
Bukti tambahan bahwa transformer architecture masih punya ruang improvement.
Selaras dengan Mechanistic Interpretability — networks learn structured representations.
Justifies kenapa brain viz training phase detection (grokking) bermakna secara arsitektural.

> **Resources resmi Anthropic — sudah dievaluasi dan diadopsi ke conductor:**

### Advanced Tool Use — KRITIKAL ✅ implement conductor Fase 3

| Resource | Link | Status |
|----------|------|--------|
| Blog post (wajib baca sebelum implement conductor) | https://www.anthropic.com/engineering/advanced-tool-use | ✅ conductor Fase 3 |
| Claude Code best practices | https://code.claude.com/docs/id/best-practices | ✅ referensi pattern |

**Tiga fitur dalam satu beta header `advanced-tool-use-2025-11-20`:**

**1. Tool Search Tool (`tool_search_tool_regex_20251119`)** — solve context bloat
Setup kita Fase 3+: GitNexus 7 tools + OpenSandbox + FectTral MCP + semua SKILL.md
workers = 55K-134K token hanya dari definitions. `defer_loading: true` → tools
discoverable, tidak load ke context sampai conductor butuh.
Hasil: **85% reduction** token overhead definitions.

**2. Programmatic Tool Calling (`code_execution_20260120`)** — solve multi-inference waste
Conductor nulis Python script untuk orchestrate scout → coder → auditor → chronicler
dalam satu sandbox. Script pause saat butuh tool result. Model lihat output final saja.
Hasil: **37% token reduction**, eliminasi **19+ inference passes** per workflow kompleks.

**3. Tool Use Examples** — solve tool selection accuracy
Tambah (input, output) examples ke tool definitions yang sering salah dipilih.
Accuracy: **72% → 90%**. Anthropic internal: Opus 4 dari 49% → 74%.

**Implementation source of truth:** `backend/workers.md` section ORCHESTRATION → conductor.
Full `conduct()` function + `build_all_worker_skill_tools()` + Tool Use Examples format
sudah ada di sana. Tidak ada duplikasi di sini.

**Pattern conductor tools setup (quick reference):**
```
always-loaded  : bridge_tool, narrator_tool
deferred       : semua worker SKILL tools (defer_loading: True)
special        : tool_search_tool_regex, code_execution
beta header    : "advanced-tool-use-2025-11-20"
```

---

## MODEL CATALOG

> **Semua model yang sudah dievaluasi dan diputuskan per worker:**
> Update terakhir: 2026-03-18. Verifikasi versi terbaru sebelum implement.
> Koreksi video: "Minimax M2.7" tidak exist, versi yang ada M2/M2.1/M2.5.
>   "Mistral Small 2" nama yang benar Mistral Small 4.
>   MiniMax lisensi MIT/Modified-MIT — lebih permisif dari dugaan (bukan hanya open weights).

| Model | Link | License | Dipakai untuk | Fase |
|-------|------|---------|---------------|------|
| Qwen2.5-32B-Instruct | https://huggingface.co/Qwen/Qwen2.5-32B-Instruct | Apache-2.0 | conductor (default) | 1+ |
| Qwen2.5-Coder-7B-Instruct | https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct | Apache-2.0 | semua coder_*, tester, auditor | 1+ |
| Llama-3.2-3B-Instruct | https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct | Llama 3.2 | intake, bridge | 1+ |
| Qwen2.5-1.5B | https://huggingface.co/Qwen/Qwen2.5-1.5B | Apache-2.0 | life_manager | 3+ |

---

### Evaluasi: MiniMax M2.5 — WORTH IT ✅ kandidat coder_* workers Fase 3+

| Resource | Link | License | Status |
|----------|------|---------|--------|
| MiniMax-M2 | https://huggingface.co/MiniMaxAI/MiniMax-M2 | MIT | ⬜ base version |
| MiniMax-M2 GitHub | https://github.com/MiniMax-AI/MiniMax-M2 | MIT | ⬜ architecture docs |
| MiniMax-M2.1 | https://huggingface.co/MiniMaxAI/MiniMax-M2.1 | Modified-MIT | ⬜ agentic optimization |
| MiniMax-M2.1 GitHub | https://github.com/MiniMax-AI/MiniMax-M2.1 | Modified-MIT | ⬜ |
| **MiniMax-M2.5** | **https://huggingface.co/MiniMaxAI/MiniMax-M2.5** | **Modified-MIT** | **⬜ Fase 3 — evaluate vs Qwen2.5-Coder-7B** |

**Apa ini:** MoE model — 230B total parameters, hanya **10B active** saat inference.
MIT/Modified-MIT license — open weights yang bisa dipakai commercially.
Unsloth sudah support MiniMax M2.5 GGUF — langsung compatible trainer pipeline kita.

**Benchmark M2.5 terverifikasi:**
- 80.2% SWE-Bench Verified (SOTA untuk 10B active params)
- 51.3% Multi-SWE-Bench
- 37% lebih cepat dari M2.1, matching speed Claude Opus 4.6
- Multi-language: Rust, TypeScript, Python, Go, C++

**Kenapa menarik:** Qwen2.5-Coder-7B kita 7B full. M2.5 punya 10B active dari 230B
total MoE — "pengetahuan" jauh lebih luas dengan inference cost hampir sama.
SWE-Bench score jauh di atas Qwen2.5-Coder-7B.

**Catatan Modified-MIT:** Baca license file sebelum deploy ke production — kemungkinan
ada restriction attribution atau anti-training. Link: github.com/MiniMax-AI/MiniMax-M2.5/blob/main/LICENSE

**Rekomendasi:** Fase 3 — benchmark parallel vs Qwen2.5-Coder-7B pada 20 coding tasks
real. Kalau M2.5 >10% better → pertimbangkan replace. Trainer tidak perlu diubah.

---

### Evaluasi: Mistral Small 4 — WORTH IT ✅ kandidat intake + bridge

| Resource | Link | License | Status |
|----------|------|---------|--------|
| Mistral Small 4 (HuggingFace) | https://huggingface.co/mistralai/Mistral-Small-4 | Apache-2.0 | ⬜ evaluate sebagai intake/bridge |
| Mistral blog | https://mistral.ai/news/mistral-small-4 | — | ⬜ benchmark detail |

**Apa ini:** 119B total params, 6B active (MoE). Apache-2.0 fully open.
40% lebih cepat, 3× throughput vs Mistral sebelumnya. Context 256k.
Untuk: general chat, coding, agentic tasks. Tersedia di DGX Spark + RTX PRO.

**Kenapa menarik untuk intake + bridge:** Fast inference, 6B active vs Llama-3.2-3B
tapi 3× faster throughput mengkompensasi. Apache-2.0 = tidak ada licensing concern.

**Rekomendasi:** Fase 3 — evaluate vs Llama-3.2-3B untuk intake dan bridge.

---

### Evaluasi: Qwen3.5 Distilled Claude 4.6 Opus Reasoning

**WORTH IT ✅ — bookmark Fase 4, evaluate vs Qwen2.5-32B untuk conductor**

| Resource | Link | Status |
|----------|------|--------|
| Model card 35B | https://huggingface.co/Jackrong/Qwen3.5-35B-A3B-Claude-4.6-Opus-Reasoning-Distilled | ⬜ evaluate Fase 4 |
| Koleksi semua size | https://huggingface.co/collections/Jackrong/qwen35-claude-46-opus-reasoning-distilled | ⬜ 2B/4B/5B/9B/27B/28B/35B |
| MLX 4-bit Mac | https://huggingface.co/Jackrong/Qwen3.5-35B-A3B-Claude-4.6-Opus-Reasoning-Distilled-MLX-4bit | ⬜ 14GB footprint |

**Apa ini:** Qwen3.5 di-SFT dengan CoT distillation dari Claude-4.6 Opus.
`<think>` block sebelum output. Ditraining Unsloth — compatible trainer kita.
Community test: autonomous 9+ menit, self-correct errors, auto-generate README.

**Size recommendation per worker:**
| Size | Kandidat | Reasoning |
|------|----------|-----------|
| 35B / 27B | conductor upgrade Fase 4 | Planning kompleks |
| 9B | auditor, curator | Multi-step judgment |
| 4B / 5B | scout | Quick context assessment |
| 2B | intake, bridge | Fast inference |

**Kenapa belum di-adopt:** Qwen2.5-32B sudah proven. Benchmark dulu Fase 4.
Perhatikan `<think>` token overhead vs quality improvement.

---

### Evaluasi: OmniCoder-9B (Teslate)

**SKIP ❌ — butuh model card + benchmark spesifik dulu**

| Resource | Link | Status |
|----------|------|--------|
| HuggingFace models (terlalu general) | https://huggingface.co/models?library=transformers | ❌ butuh link spesifik |

Tidak cukup data. Kalau dapat link spesifik → evaluate ulang vs Qwen2.5-Coder-7B.
## DESIGN PATTERN LIBRARY

### Evaluasi: JSON-Render (Vercel)

**WORTH IT ✅ tapi TIDAK di-install — adopt guardrailed generation pattern**

| Repo | Link | License | Stars | Status |
|------|------|---------|-------|--------|
| vercel-labs/json-render | https://github.com/vercel-labs/json-render | MIT | 10.5k | 📚 pattern diadopsi ke compositor + FectTral MCP |

**Apa ini:** Generative UI framework — AI generate JSON, render dengan components
yang user define sendiri. Guardrailed: AI hanya bisa pakai components dalam catalog.
Predictable: JSON output match schema setiap kali. Ada MCP server example.

**Kenapa tidak di-install:** Kita pakai React + Canvas (pixel-agents fork) + FectTral
overlays — JSON-Render adalah full rendering framework yang akan conflict dengan
arsitektur canvas kita. Kita tidak build "generative dashboard."

**Patterns yang diadopsi ke compositor + FectTral MCP (tidak duplikasi — source of truth di workers.md):**
1. **Guardrailed generation** — compositor tidak generate HTML arbitrary, hanya JSON
   yang map ke FectTral components yang sudah terdefinisi
2. **Catalog-driven** — compositor hanya reference elements dari archivist SQLite
   library, bukan generate dari nol. Archivist library = "catalog" kita
3. **MCP render tool** — FectTral MCP server bisa expose `render-ui` tool yang
   constrained ke FectTral component catalog, LLM call tool → constrained JSON output

---

## GAP MAP — Yang Belum Ada Tapi Dibutuhkan

```
FASE 1 (perlu sebelum mulai):
  ✅ pixel-agents    → sudah ada link
  ✅ Tauri v2        → sudah ada link
  ✅ Ollama          → sudah ada link

FASE 2 (perlu untuk rooms + design studio):
  ✅ Impeccable concepts → adopted ke design workers SKILL.md
  ⬜ Sigma.js        → untuk DNA Report graph visualization
  ⬜ proper-pixel-art install → perlu cek apakah masih maintained
  ✅ BACA openclaw-office SEBELUM mulai Fase 2:
     git clone https://github.com/WW-AI-Lab/openclaw-office /tmp/openclaw-office-ref
     focus: event-parser.ts, mock-adapter.ts, office-store.ts, office-2d/
     ambil: WebSocket schema, mock data pattern, state management, zone layout ideas
     JANGAN ikuti: React SVG/R3F stack — kita tetap pixel art canvas

FASE 3 (perlu untuk AI live):
  ✅ GitNexus        → sudah ada link + 7 MCP tools documented
  ✅ Lightpanda      → sudah ada link
  ✅ Cognee          → sudah ada link
  ✅ OpenSandbox     → sudah ada link
  ✅ concurrent editing → backend/concurrent-editing.md
  ✅ Apache AGE      → setup di backend/edgequake-setup.md
  ✅ pgvector        → setup di backend/edgequake-setup.md
  ✅ alexzhang13/rlm → RLM inference layer: scout + auditor + curator
     install: pip install rlm
  ✅ MarkdownFetcher → scout HTTP layer (Cloudflare Markdown for Agents)
     buat: backend/utils/markdown_fetcher.py saat implement scout
  ✅ Advanced Tool Use → conductor beta header
     baca: https://www.anthropic.com/engineering/advanced-tool-use
     beta: "advanced-tool-use-2025-11-20"
  ✅ auditor tiered pipeline → workers.md — Clippy T1 + Kodus T2 + RLM T3
     gather_audit_context(), record_audit_feedback(), determine_audit_tier()
  ⬜ Kodus → evaluate vs PR-Agent untuk auditor Fase 3
     github.com/kodus-app/kodus-ai | AST pre-analysis + SKILL.md auto-detect

FASE 4 (perlu untuk full AI + training):
  ✅ Unsloth         → sudah ada link
  ✅ vLLM            → setup di backend/vllm-setup.md
  ✅ O-LoRA          → adaptasi Qwen2.5 di backend/olora-qwen.md
  ✅ Atropos         → setup guide di backend/atropos-setup.md
  ✅ trainer overnight loop → patterns karpathy + uditgoenka autoresearch
  ✅ Grokking detection → brain-visualization.md Tab 4 + training-landscape.md
  ✅ Stripe Minions patterns → workers.md
  ⬜ DeepAgents → conductor backbone candidate
     uv add deepagents | github.com/langchain-ai/deepagents
     evaluate vs custom conductor: planning accuracy + reliability
  ⬜ nanobot → early multi-modal (foto → room-config)
     github.com/HKUDS/nanobot | use case: photo_to_room_config()
  ⬜ Qwen3.5 35B Distilled → evaluate vs Qwen2.5-32B untuk conductor
     https://huggingface.co/Jackrong/Qwen3.5-35B-A3B-Claude-4.6-Opus-Reasoning-Distilled
  ⬜ LangGraph → underlying runtime DeepAgents, tidak blocking

FASE 5 (polish + expand):
  ✅ KARL (Databricks) → trainer + curator RL — training-landscape.md
  ⬜ nanobot local gateway — test multi-modal sebelum expose ke messaging
  ⬜ Buat backend/multimodal-integration.md → arsitektur Fase 6

FASE 6 (multi-modal integration):
  ⬜ NemoClaw + OpenClaw gateway → expose workers sebagai skills
     github.com/NVIDIA/NemoClaw (security layer — tunggu stable release dulu)
     github.com/openclaw/openclaw | clawstore.openclaw.ai
     NemoClaw: kernel sandbox + privacy router + policy guardrails
     Status NemoClaw: alpha per Maret 2026 — pantau sebelum deploy
  ⬜ Input handlers: foto (nanobot vision), YT (yt-dlp+RLM), Chrome (CDP)
  ⬜ ClawHub publish → selected workers jadi public skills
  ⬜ mHC / AttnRes → hanya kalau pre-train dari scratch (unlikely)

BELUM DIDOKUMENTASIKAN SAMA SEKALI:
  ✅ brain visualization + Tab 4 → frontend/brain-visualization.md
  ✅ Tech stack TypeScript MCP → backend/scout-auto-mode.md
  ✅ Settings panel → ux/settings-panel.md
  ✅ JSON-Render pattern → workers.md compositor section
  ✅ Mech Interp + Grokking → brain-visualization.md + training-landscape.md
  ✅ Stripe Minions → workers.md post-coding pipeline
  ✅ OpenClaw + nanobot + DeepAgents + Zencoder → LINKS.md MULTIMODAL GATEWAY
  ⬜ backend/multimodal-integration.md (Fase 5)
     photo_handler.py, yt_handler.py, chrome_handler.py, security_model
  ⬜ LoRA composition di inference (multiple LoRA aktif bersamaan)
  ⬜ EWC (Elastic Weight Consolidation) anti-catastrophic forgetting
```

---

## Quick Reference: Install Urutan Fase

```bash
# FASE 1 — Game Shell
git clone https://github.com/pablodelucca/pixel-agents vibe-office
cargo install tauri-cli
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull qwen2.5-coder:7b
ollama pull qwen2.5:32b      # conductor
ollama pull qwen2.5:1.5b     # life_manager

# FASE 2 — Design Studio
npm install -g sigma          # untuk graph visualization
# Setup FectTral MCP server (dari FectTral.rar):
cd frontend/fectral/design-tools && npm install
# aesthetic-context.json dibuat oleh designer worker saat pertama run

# FASE 3 — AI Connect
npm install -g gitnexus
./lightpanda serve --port 9222   # dari github.com/lightpanda-io/browser
pip install cognee
pip install opensandbox-server opensandbox-code-interpreter
pip install rlm                  # long-context inference: scout + auditor + curator
# MarkdownFetcher: buat backend/utils/markdown_fetcher.py (sudah documented di workers.md)
# Advanced Tool Use: TIDAK perlu install — beta header di conductor API call
#   beta: "advanced-tool-use-2025-11-20"
#   baca: https://www.anthropic.com/engineering/advanced-tool-use

# FASE 4 — Training
pip install unsloth
pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
# Untuk EdgeQuake (PostgreSQL + AGE + pgvector):
# psql -c "CREATE EXTENSION age;"
# psql -c "CREATE EXTENSION vector;"
git clone https://github.com/raphaelmansuy/edgequake && cd edgequake && make install
# Evaluate Qwen3.5-35B vs Qwen2.5-32B untuk conductor:
# https://huggingface.co/Jackrong/Qwen3.5-35B-A3B-Claude-4.6-Opus-Reasoning-Distilled
# MLX 4-bit (Mac): huggingface.co/Jackrong/...-MLX-4bit (14GB footprint)

# FASE 5 — KARL RL Evolution
# Tidak ada install baru — KARL patterns pakai Unsloth yang sudah ada.
# Baca training-landscape.md section KARL sebelum mulai.
# Minimal: 2000 episodes per domain di Ring 2, base LoRA sudah proven.
```

*(last updated: 2026-03-17, v4.4)*
