---
name: vibe-office
description: |
  Desktop app pixel art top-down: kantor virtual di mana AI workers beneran ngoding.
  Fork dari pixel-agents (MIT), host Tauri v2, AI backend Python, output kode nyata.
  Trigger: vibe-office, pixel office, kantor AI, worker visualization, AI game,
  multi-agent game, pixel art office, worker karakter, meeting room TV, CEO office,
  conductor, intake, bridge, narrator, coder_rust, coder_css, coder_js, coder_python,
  tester, auditor, scribe, sentinel, chronicler, scout, curator, trainer, steward,
  job application, GitNexus, cognee, EdgeQuake, GraphRAG, LightRAG, SpacetimeDB,
  learn-claude-code, DeerFlow, OpenSandbox, BitNet, hermes-agent, continual learning,
  LoRA lifecycle, knowledge injection, SKILL.md, brain visualization, FectTral, cyberpunk UI,
  design library, design studio, archivist, stylist, compositor, designer, DNA report,
  design elements, mood system, OpenClaw, nanobot, WhatsApp, Telegram, multi-modal,
  DeepAgents, conductor backbone, Zencoder, multi-model validation, grokking, mech interp,
  training phase, Stripe Minions, tool subset, RLM, markdown fetcher, KARL, RL training.
license: Apache-2.0
metadata:
  author: Wolfvin
  version: "5.6"
  updated: "2026-03-18 (v6.0: NemoClaw + MiniMax M2.5 + Mistral Small 4 + AttnRes)"
  language: Bahasa Indonesia
allowed-tools: Read Write Bash
---

# Vibe-Office — Master Navigator v4.3

> **BACA INI PERTAMA — setiap session baru wajib mulai di sini.**
> Ini peta lengkap vibe-office. File ini dirancang agar session Claude baru
> bisa langsung melanjutkan percakapan seperti sudah tahu semua konteks.

---

## Satu Kalimat

Kamu kirim task via chat → conductor (AI CEO) assign ke workers →
workers ngoding di kantor pixel art → kode nyata keluar ke project kamu.
Workers semakin pintar seiring waktu lewat continual learning.

---

## Apa yang Sudah Diputuskan (Jangan Tanya Ulang)

Ini keputusan yang sudah final dari diskusi sebelumnya:

**Naming workers** — di-revamp total session 2026-03-17. Lihat tabel di bawah.
Alasan: nama lama terlalu generic (`input_translator`, `rust_worker`).

**Coders di-spesialisasi per bahasa** — bukan satu `coder` generik.
`coder_rust`, `coder_css`, `coder_js`, `coder_python` — masing-masing punya
SKILL.md sendiri. Conductor baca field `language` di task untuk assign.

**review_worker + ai_advisor → `auditor`** — merge karena overlap.
auditor punya dua mode: `post_task` (reactive) dan `periodic_audit` (proactive).

**context_worker + ai_fetcher → `scout`** — upgrade, bukan worker baru.
scout punya mode `proactive_research` — research sendiri saat idle.

**3 workers baru di Knowledge Layer:** `curator`, `trainer`, `steward`.

**FectTral = visual identity semua UI vibe-office** — semua overlay, panels,
CEO office, brain visualization, design studio pakai FectTral cyberpunk style.
Pixel art untuk game world, FectTral untuk semua UI di atas canvas.

**Design Library Pipeline (FectTral) → 4 workers baru di design studio:**
`archivist` (fetch+tag), `stylist` (review+select), `compositor` (generate),
`designer` (orchestrator). **Tech stack: Python workers** (diputuskan v4.9 di
`design/design-workers.md`). FectTral MCP TypeScript tetap untuk web-extractor layer.

**Design studio room** = viola room unlock Fase 2. Ada monitor besar.
Klik monitor → pixel art zoom in → seamless transition ke FectTral full UI.
Di dalam: Library, Review Queue, DNA Report, Generate panel.

curator = rawat SKILL.md. trainer = kelola LoRA lifecycle. steward = file org.

**Fase 6 Vision = "Kantor yang Bisa Kamu Telepon"** — sudah diputuskan arahnya.
Workers vibe-office akan exposed sebagai OpenClaw/nanobot skills. Conductor tetap
orchestrator tunggal — semua input (WA, foto, YT, Chrome, robot) masuk ke
conductor via gateway, conductor assign ke worker yang tepat.
Input types yang akan didukung: pesan teks (WA/Telegram), foto (vision workers),
YouTube video (scout via yt-dlp), Chrome browsing (CDP agent), robot/IoT (RPC).
Detail arsitektur: LINKS.md section MULTIMODAL GATEWAY.

**DeepAgents = conductor backbone Fase 4** — upgrade dari LangGraph bookmark.
`uv add deepagents`, terinspirasi Claude Code, batteries included.
EdgeQuake adalah GraphRAG Rust dengan 6 query modes dan <200ms hybrid latency.

**SpacetimeDB** = opsi alternatif state sync (bukan default) — dokumentasi di
`desktop/spacetimedb-option.md`. Arsitektur default tetap Python WebSocket.

---

## Konsep Inti yang Harus Dipahami

**Kantor = visualisasi AI, bukan dekorasi.** Setiap gerakan worker mencerminkan
state AI yang nyata. Worker ke break room = benar-benar idle. Worker ke dormitory
= benar-benar blocked. Bisa kamu klik untuk lihat detail.

**CEO office = satu-satunya tempat kelola workers.** Klik meja conductor →
kertas-kertas muncul → flip next/prev → kertas terakhir = Job Application.
Di sini kamu bisa: hire, fire, deactivate, lihat stats, dan — yang baru —
**lihat "isi otak" worker** (LoRA collection yang aktif).

**3 Translation workers = inovasi arsitektur.** `intake` terima pesanmu →
`bridge` normalize format antar workers → `narrator` "siaran" hasil ke TV dan chat.
Tanpa ini, setiap worker harus tahu format semua worker lain (240 kombinasi).

**Continual Learning = workers makin pintar seiring waktu:**
- Level 1 (Fase 3): Knowledge Injection — curator update SKILL.md dari episodes
- Level 2 (Fase 4): LoRA fine-tuning — trainer otomasi Unsloth dari Ring 2 data

**"Isi otak" bisa divisualisasikan** — setiap worker punya LoRA collection
yang bisa kamu lihat, aktifkan, nonaktifkan, atau minta trainer untuk refactor.
Detail UI: lihat `frontend/brain-visualization.md`.

---

## Workers Registry (25 Total)

### Translation Layer
| Worker | Ganti Dari | Fungsi |
|--------|-----------|--------|
| `intake` | input_translator | Pesan bebasmu → JSON task |
| `bridge` | relay_translator | Normalize format antar workers |
| `narrator` | output_translator | Output teknis → TV + chat |

### Orchestration
| Worker | Ganti Dari | Fungsi |
|--------|-----------|--------|
| `conductor` | orchestrator | CEO — plan, assign, recover |

### Coder Workers (expandable per bahasa)
| Worker | Ganti Dari | Spesialisasi |
|--------|-----------|-------------|
| `coder_rust` | rust_worker | Rust: async, server, unsafe, rayon |
| `coder_css` | — (baru) | CSS: animations, variables, tailwind |
| `coder_js` | — (baru) | JS/TS: canvas, websocket, tauri |
| `coder_python` | — (baru) | Python: AI backend, DuckDB, agent loops |

### Pipeline Workers
| Worker | Ganti Dari | Fungsi |
|--------|-----------|--------|
| `tester` | tester_worker | unit_test, integration_test |
| `auditor` | review_worker + ai_advisor | Code review (2 mode: post_task + periodic) |
| `scribe` | docs_worker | rustdoc, README, comments |
| `sentinel` | security_worker | cargo audit, unsafe scan, secrets scan |
| `chronicler` | git_worker | commit, branch, changelog |
| `scout` | context_worker | GitNexus + Lightpanda + proactive research |

### Knowledge Layer (Workers Baru)
| Worker | Ganti Dari | Fungsi |
|--------|-----------|--------|
| `curator` | ai_teacher | Rawat SKILL.md semua workers, routing data ke trainer |
| `trainer` | ai_scientist | LoRA lifecycle: trigger Unsloth, eval, aktifkan/nonaktifkan |
| `steward` | ai_janitor | File organization, add comments — TIDAK refactor logic |

### Design Workers (dari FectTral Integration)
| Worker | Ganti Dari | Fungsi |
|--------|-----------|--------|
| `archivist` | FectTral curator+tagger | Fetch URL → ekstrak & tag design elements |
| `stylist` | FectTral reviewer+selector | Quality gate + pilih kombinasi terbaik |
| `compositor` | FectTral generator | Rakit library elements → kode frontend |
| `designer` | — (baru, orchestrator) | Routing ke archivist/stylist/compositor |


---

## Post-Coding Pipeline

```
coder_* selesai
  ↓ bridge normalize
scribe ──PARALEL── auditor(post_task) ──PARALEL── sentinel
                          ↓ (semua selesai)
                     chronicler → commit
                          ↓ (background, non-blocking)
                     scout re-index (GitNexus)
                     curator log episode → Ring 2
                     curator check training readiness → trainer? (opsional)
```

---

## Continual Learning Pipeline (Background, Async)

```
Ring 2 Parquet episodes terakumulasi dari semua tasks
  ↓ curator analisis berkala
KNOWLEDGE INJECTION (Fase 3, bisa langsung):
  curator patch SKILL.md workers ← dari: auditor audit, scout research, episodes

LORA TRAINING (Fase 4, butuh data cukup ≥200 episodes per domain):
  curator signal → trainer
  trainer ambil Ring 2 → compress → Unsloth fine-tune
  trainer eval LoRA baru vs baseline
  kalau +5% improvement → aktifkan LoRA
  narrator announce: "🧠 coder_rust upgraded: +23% borrow checker"
```

---

## Tech Stack

| Layer | Tech | Link |
|-------|------|------|
| Canvas / game | React 19 + Canvas 2D (fork pixel-agents) | github.com/pablodelucca/pixel-agents |
| Desktop host | Tauri v2 | tauri.app |
| AI backend | Python — pola dari learn-claude-code | github.com/shareAI-lab/learn-claude-code |
| Codebase intelligence | GitNexus (MCP + CLI) | github.com/abhigyanpatwari/GitNexus |
| Web scraping | Lightpanda (scout) | github.com/lightpanda-io/browser |
| Memory hot | DuckDB Ring 1 | duckdb.org |
| Memory warm | SQLite + Parquet Ring 2 | — |
| Memory cold (Fase 3) | Cognee | github.com/topoteretes/cognee |
| Memory cold (Fase 4+) | EdgeQuake GraphRAG Rust | github.com/raphaelmansuy/edgequake |
| Sandbox isolation | OpenSandbox (Fase 3+) | github.com/alibaba/OpenSandbox |
| Fine-tuning | Unsloth QLoRA | github.com/unslothai/unsloth |
| CPU inference | BitNet (no-GPU fallback) | github.com/microsoft/BitNet |
| SuperAgent reference | DeerFlow | github.com/bytedance/deer-flow |
| State sync alternatif | SpacetimeDB (opsi) | github.com/clockworklabs/SpacetimeDB |
| Long-context inference | alexzhang13/rlm (Fase 3) | github.com/alexzhang13/rlm |
| Scout HTTP layer | Cloudflare Markdown for Agents (Fase 3) | blog.cloudflare.com/markdown-for-agents |
| Trainer loop patterns | karpathy + uditgoenka autoresearch (referensi) | github.com/karpathy/autoresearch |
| Design intentionality | Impeccable (concepts only) | github.com/pbakaus/impeccable |
| Conductor tool management | Anthropic Advanced Tool Use (Fase 3) | anthropic.com/engineering/advanced-tool-use |
| UI generation guardrail | Vercel JSON-Render (pattern only) | github.com/vercel-labs/json-render |
| RL evolution blueprint | KARL / Databricks (Fase 5) | databricks.com/blog/karl-knowledge-agents-via-reinforcement-learning |
| Grokking detection | Mech. Interp. / Nanda et al. (Fase 4) | arxiv.org/abs/2301.05217 |
| Pipeline architecture | Stripe Minions patterns (referensi) | stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents |
| Conductor backbone (Fase 4) | DeepAgents / LangChain (kandidat) | github.com/langchain-ai/deepagents |
| Model kandidat coder_* (Fase 3) | MiniMax M2.5 MIT/Modified-MIT | huggingface.co/MiniMaxAI/MiniMax-M2.5 |
| Model kandidat intake/bridge (Fase 3) | Mistral Small 4 Apache-2.0 | huggingface.co/mistralai/Mistral-Small-4 |
| Transformer arch referensi | AttnRes / Moonshot Kimi (self-study) | github.com/MoonshotAI/Attention-Residuals |
| Multi-modal gateway (Fase 6) | OpenClaw + NemoClaw security | github.com/openclaw/openclaw + github.com/NVIDIA/NemoClaw |
| Visual office reference | openclaw-office / WW-AI-Lab (**BACA Fase 2**) | github.com/WW-AI-Lab/openclaw-office |
| Multi-agent bridge ref | AgentScope / Alibaba (patterns only) | github.com/agentscope-ai/agentscope |
| RL fine-tuning ref | AgentScope Trinity-RFT (referensi) | github.com/agentscope-ai/Trinity-RFT |
| Timeline UI reference | MassGen (patterns only) | github.com/massgen/MassGen |
| Continual learning ref | GMvandeVen/continual-learning (Fase 5) | github.com/GMvandeVen/continual-learning |
| Code review Fase 1-2 | PR-Agent / Codium (self-hosted) | github.com/Codium-ai/pr-agent |
| Code review Fase 3+ | Kodus/Kody (kandidat upgrade) | github.com/kodus-app/kodus-ai |
| Code review patterns | CodeRabbit (patterns only, no install) | github.com/marketplace/coderabbitai |
| Multi-model validation ref | Zencoder (pattern only) | zencoder.ai |

---

## Roadmap

```
Fase 1 (M1)   — Game Shell: fork pixel-agents → Tauri v2, WebSocket dummy backend
Fase 2 (M2)   — Rooms & FSM: 6 ruangan + viola rooms, 7 FSM states, TV screen, CEO office UI
Fase 3 (M3-4) — AI Connect: conductor + workers live, GitNexus, Cognee Ring 3,
                 3 translation workers, curator + Knowledge Injection,
                 Advanced Tool Use beta header, RLM inference, MarkdownFetcher
Fase 4 (M5-8) — Full AI: semua workers, EdgeQuake production, trainer + LoRA lifecycle,
                 OpenSandbox isolation, Unsloth fine-tuning, brain visualization + Tab 4,
                 grokking detection, DeepAgents conductor backbone, KARL iterative loop
Fase 5 (M9+)  — Polish + Expand: sound, steward automation, onboarding,
                 continual learning UI, KARL RL training, dLLM experimental
Fase 6 (M12+) — Multi-Modal Integration: nanobot bridge → trigger workers dari
                 WhatsApp/Telegram/Discord, foto input, YouTube video ingestion,
                 Chrome browsing agent, robot/IoT nodes via RPC,
                 expose workers sebagai OpenClaw skills di ClawHub
```

**Visi Fase 6 — "Kantor yang Bisa Kamu Telepon":**
Bukan hanya kantor visual yang bisa kamu lihat di desktop. Fase 6 adalah kantor
yang bisa kamu hubungi dari mana saja — WA, foto, video, browser, bahkan robot fisik.
Fondasi: OpenClaw/nanobot sebagai messaging gateway. Workers vibe-office
exposed sebagai OpenClaw skills. Conductor tetap sebagai orchestrator tunggal.
Detail arsitektur: lihat `backend/multimodal-integration.md` (dibuat Fase 5).

---

## Navigasi File

### Backend (baca sesuai kebutuhan, tidak perlu semua)

### Master Link Registry
| File | Isi |
|------|-----|
| **`LINKS.md`** | **SEMUA GitHub links, status gap, install order per fase — baca ini sebelum implement** |

| File | Isi | Kapan |
|------|-----|-------|
| **`backend/workers.md`** | **SEMUA workers, naming, kode, pipeline — BACA INI** | Selalu |
| `backend/agent-loop.md` | learn-claude-code s01-s12 mapping ke vibe-office | Fase 3 |
| `backend/worker-identity-card.md` | Format plugin.json + SKILL.md per worker | Fase 1+ |
| `backend/gitnexus-integration.md` | GitNexus 7 MCP tools, scout queries | Fase 3 |
| `backend/memory.md` | DuckDB Ring 1, SQLite Ring 2, Cognee/EdgeQuake Ring 3 | Fase 3 |
| `backend/websocket-events.md` | Event schema + simulated backend Fase 1-2 | Fase 1 |
| `backend/uncertainty-escalation.md` | Knowledge quadrant, scout escalation flow | Fase 3 |
| `backend/sandbox.md` | OpenSandbox Docker isolation per worker | Fase 3+ |
| `backend/deerflow-patterns.md` | DeerFlow: skill loading, LangGraph, context eng | Fase 3 ref |
| `backend/hermes-patterns.md` | hermes-agent: trajectory compression, RL env | Fase 4 ref |
| `backend/concurrent-editing.md` | Git worktree per worker, file locking, merge flow, crash recovery | Fase 3 |
| `backend/vllm-setup.md` | vLLM production inference, swap dari Ollama, LoRA loading | Fase 3+ |
| `backend/edgequake-setup.md` | PostgreSQL + Apache AGE + pgvector + EdgeQuake full setup | Fase 4 |
| **`frontend/brain-visualization.md`** | **LoRA UI full page** — DNA Overview + Training Phase (Grokking), LoRA Manager, Conflict Map, **Tab 4 Loss Curve (Fase 4)**, Backend API | Fase 4 |
| `backend/olora-qwen.md` | O-LoRA adaptasi Qwen2.5 — OrthogonalLoRATrainer, compute_orthogonality_loss | Fase 4 |
| `backend/atropos-setup.md` | Atropos RL training — CoderRustEnv, TesterEnv, reward design | Fase 4+ |
| `backend/workers.md` | +Router Dinamis: intake classify routing_hint, conductor fast-path kalau confidence > 0.8 | Fase 3 |
| `backend/training-landscape.md` | +Evaluation Module (lm-evaluation-harness) + dLLM Penyusun (Fase 5 experimental) + **KARL RL blueprint (Fase 4-5)** | Fase 4/5 |
| `backend/knowledge-approval.md` | Approval pipeline: curator→auditor→trainer/coder, bridge routes, status states, 3x discard | Fase 3 |
| `backend/scout-auto-mode.md` | Scout auto web search — TypeScript MCP tools, research queue, cooldown, send to curator | Fase 3 |
| `frontend/knowledge-browser.md` | Knowledge Browser 3-tab overlay — Domains, All Episodes (Ring 2 raw), SKILL Files | Fase 3 |
| `frontend/task-animations.md` | +Rooftop ceremony: 11-beat LoRA presentation scene, semua workers naik rooftop | Fase 3+ |
| `frontend/nova-notes-integration.md` | NovaNotes embed di server machine — lazy load, disk persist, enkripsi per-note, Send to Curator | Fase 2+ |
| `backend/knowledge-ingestion.md` | Curator knowledge pipeline — classify→SKILL update→Ring 2→threshold check + Knowledge Browser UI | Fase 3 |
| `frontend/task-animations.md` | Walk-to-desk entry sequence + task animations (meeting, argue, hacking, celebrate) | Fase 2+ |
| `frontend/needs-system.md` | Needs system (energy/social/focus/hunger), behavior triggers, social interaction | Fase 2+ |
| `backend/life-manager.md` | life_manager worker — generate daily_rules.json dari room config + personalities | Fase 3 |
| `desktop/room-editor.md` | Room editor Tauri app terpisah — drag & drop, multi-lantai, tema, dekorasi | Fase 2+ |
| `ux/settings-panel.md` | Settings panel FectTral — audio, display, AI models, room editor, workers | Fase 2 |
| `backend/training-landscape.md` | Unsloth vs BitNet decision tree | Fase 4 |

### Frontend
| File | Isi | Kapan |
|------|-----|-------|
| `frontend/canvas-game.md` | Fork pixel-agents, sprite format, dev setup | Fase 1 |
| `frontend/fsm-rooms.md` | FSM 7 states, zone JSON, viola rooms unlock | Fase 1-2 |
| `frontend/ui-overlays.md` | TV screen, status popup, progress bar | Fase 2 |
| `frontend/chat-panel.md` | Command system, /commands, message types | Fase 2 |
| `frontend/ceo-office.md` | Paper stack, flip/tear animasi, hire/fire | Fase 2 |
| `frontend/onboarding.md` | 4-step wizard, tutorial tooltips | Fase 5 |

### Desktop
| File | Isi | Kapan |
|------|-----|-------|
| `desktop/tauri-setup.md` | Fork pixel-agents, Tauri v2 setup, dev workflow | Fase 1 |
| `desktop/session-management.md` | Atomic save, resume, multi-project | Fase 1 |
| `desktop/spacetimedb-option.md` | SpacetimeDB sebagai alternatif state sync | Opsi Fase 3 |

### Assets & UX
| File | Isi | Kapan |
|------|-----|-------|
| `assets/sprite-pipeline.md` | SD generate → Pixelorama, prompt per worker | Fase 2 |
| `assets/worker-customization.md` | Nama, skin, catchphrase, tone | Fase 2 |
| `assets/worker-personality.md` | SOUL.md pattern dari airi, DuckDB WASM proto | Fase 2 |
| `ux/error-recovery.md` | Tier 1-3 UX, crash recovery | Fase 2 |
| `ux/sound-design.md` | jsfxr event map, AudioManager | Fase 5 |

### Design (FectTral Integration)
| File | Isi | Kapan |
|------|-----|-------|
| `design/design-system.md` | FectTral tokens, templates, pixel art → FectTral transisi | Fase 2+ |
| `design/design-workers.md` | archivist/stylist/compositor/designer, MCP tools, DB schema, TS vs Python | Fase 2+ |


---

## Aturan Kritis (Jangan Dilanggar)

1. **Conductor hanya query Ring 1** untuk real-time decisions
2. **Urutan wajib:** `checkpoint(in_progress)` → `send_to_worker` → `checkpoint(done/failed)`
3. **Satu DuckDB per project** — tidak boleh shared
4. **dLLM tidak auto-correct** — hanya deteksi + eskalasi ke conductor
5. **auditor critical/major = block commit** (sama dengan sentinel)
6. **Atomic write** — tulis `.tmp` dulu, lalu rename
7. **CEO office = satu-satunya tempat** hire/fire/deactivate worker
8. **scout WAJIB jalan** sebelum task di-assign ke coder_*
9. **Load SKILL.md on-demand** (s05 pattern) — jangan inject semua ke system prompt
10. **steward TIDAK boleh** ubah logic atau behavior kode — hanya file org + comments
11. **trainer TIDAK aktifkan LoRA** kalau delta < 5% improvement

---

## Status & Gap

**Status:** Design + dokumentasi lengkap v4.3. Belum ada implementasi.
**Next step:** Fase 1 — semua docs sudah lengkap, tinggal buka terminal dan `git clone pixel-agents`.

**Gap yang masih terbuka:**
- ✅ Tech stack: TypeScript MCP untuk scout + design workers (backend/scout-auto-mode.md)
- Concurrent file editing edge cases: lihat backend/concurrent-editing.md

---

## Keputusan Final yang Sudah Dibuat (v6.0 — update 2026-03-18)

> **Koreksi dari sumber video:** "Minimax M2.7" tidak exist (yang ada M2/M2.1/M2.5),
> "Mistral Small 2" nama yang benar Mistral Small 4, "Intention Residual" (Moonshot)
> nama yang benar AttnRes (Attention Residuals), NemoClaw masih alpha bukan production.
> MiniMax lisensi MIT/Modified-MIT — lebih permisif dari dugaan awal (bukan hanya open weights).

- **NemoClaw (NVIDIA, GTC 2026)**: Langsung solve security concern terbesar Fase 6 kita.
  Install di atas OpenClaw dalam satu command — kernel sandbox, privacy router, policy
  guardrails. ⚠️ Status: early-stage alpha per Maret 2026 — "expect rough edges."
  Tunggu stable release sebelum deploy. Pantau: github.com/NVIDIA/NemoClaw
  Security note sebelumnya ("WAJIB security review manual") → NemoClaw adalah solusinya.
- **MiniMax M2.5**: WORTH IT ✅ kandidat serius coder_* workers Fase 3.
  MIT/Modified-MIT (bukan hanya open weights). 10B active params dari 230B MoE.
  80.2% SWE-Bench Verified. Unsloth support sudah ada.
  Links: huggingface.co/MiniMaxAI/MiniMax-M2.5 | github.com/MiniMax-AI/MiniMax-M2.1
  Evaluate parallel vs Qwen2.5-Coder-7B pada 20 coding tasks.
- **Mistral Small 4**: WORTH IT ✅ kandidat intake + bridge. Apache-2.0.
  6B active (MoE 119B total). 3× throughput vs sebelumnya.
  huggingface.co/mistralai/Mistral-Small-4
- **AttnRes (Moonshot/Kimi)**: REFERENSI companion ke mHC.
  Drop-in residual replacement, <2% inference overhead. arXiv:2603.15031.
  github.com/MoonshotAI/Attention-Residuals
  Sama dengan mHC: skip kecuali pre-train dari scratch.
- **Codex Subagents (OpenAI)**: Tidak perlu masuk blueprint — validasi bahwa
  arsitektur conductor + workers paralel kita sudah benar. OpenAI adopt pattern
  yang sama yang sudah kita design.
- **Claude Opus 4.6 1M context**: Active di conductor kita. Planning kompleks
  sekarang bisa handle tanpa context overflow.

## Keputusan Final yang Sudah Dibuat (v5.9 — update 2026-03-18)

- **CodeRabbit**: SKIP install (commercial SaaS). 3 patterns diadopsi ke auditor:
  context engineering (`gather_audit_context()`), learnable preferences
  (`record_audit_feedback()` → curator SKILL.md), tiered pipeline 3-tier
  (Clippy T1 → Kodus T2 → RLM+multi-model T3). Source of truth: workers.md auditor section.
- **Kodus/Kody** (github.com/kodus-app/kodus-ai): kandidat replace PR-Agent Fase 3.
  Open-source, self-host, BYOK. AST pre-analysis sebelum LLM inference.
  Auto-detect SKILL.md sebagai review rules. Evaluate parallel vs PR-Agent di 20 PRs.
- **LoRA Composition**: SELESAI didokumentasikan di `backend/vllm-setup.md`.
  Opsi A (merge offline via PEFT) sebagai default. `merge_active_loras()`,
  `rebuild_merged_lora()`, `reload_lora_in_vllm()` functions lengkap.
  Triggered saat user ubah weight slider atau toggle LoRA di brain viz.
- **TV Screen Timeline Mode**: SELESAI di `frontend/ui-overlays.md`.
  Dua mode: live (current task + workers) dan timeline (full scrollable event history).
  Toggle button ⚡/📋. `TVEvent` interface, `tvEventStore` dengan max 200 events.
  Mode toggle selaras dengan `TVMode` state di workerManager.
- **Fix contradictions**: Tech stack design workers sudah Python (v4.9) — README diupdate.
  Rooftop room sudah punya fungsi jelas — workers.md diupdate.
  "Idea BELUM" lama yang sudah selesai — dipindahkan ke "sudah selesai."

## Keputusan Final yang Sudah Dibuat (v5.8 — update 2026-03-18)

- **openclaw-office (WW-AI-Lab)**: WAJIB baca sebelum implement Fase 2.
  `git clone https://github.com/WW-AI-Lab/openclaw-office /tmp/openclaw-office-ref`
  Focus: event-parser.ts (WebSocket event → visual state mapping), mock-adapter.ts
  (simulate data untuk dev tanpa backend), office-store.ts (Zustand patterns).
  Kita tidak fork — stack berbeda (SVG/R3F vs pixel art canvas). Tapi patterns-nya proven.
- **AgentScope (Alibaba)**: SKIP install. 3 patterns diadopsi ke workers.md:
  WorkerHub class (MsgHub pattern → dynamic worker add/remove untuk hire/fire runtime),
  group-wise tool management (extend TASK_TYPE_TOOL_SUBSETS), Distributed Interrupt
  Service pattern (extend conductor recovery tiers).
  Trinity-RFT: referensi implementasi KARL patterns trainer Fase 4-5.
- **MassGen**: Timeline view pattern untuk TV screen meeting room — history semua
  events sebagai timeline, bukan hanya speech bubble terakhir.
  `enable_tool_search` bm25 sebagai fallback Advanced Tool Use kalau beta belum stabil.
- **GMvandeVen/continual-learning**: EWC referensi untuk trainer Fase 5+.
  Catatan: O-LoRA yang sudah kita punya mungkin cukup — implement EWC hanya kalau
  O-LoRA proven insufficient untuk anti-catastrophic forgetting.
  ICLR 2025 blogpost (Fisher Information) wajib baca sebelum decide.

## Keputusan Final yang Sudah Dibuat (v5.7 — update 2026-03-18)

- **OpenClaw + nanobot (Fase 6 vision)**: OpenClaw adalah proof-of-concept dari
  visi jangka panjang vibe-office — foto, YT, Chrome, WA, robot, dll.
  247k stars, support WhatsApp/Telegram/Discord/iMessage/Signal/iOS/Android/Pi.
  Strategi: Fase 1-4 standalone, Fase 5 integrasi nanobot (lighter alternative),
  Fase 6 expose workers sebagai OpenClaw skills di ClawHub.
  Security note: WAJIB security review sebelum expose ke public gateway.
  Nanobot: github.com/HKUDS/nanobot — 99% fewer lines, multi-modal, Ollama support.
  Full evaluasi dan arsitektur integrasi: LINKS.md section MULTIMODAL GATEWAY.
- **DeepAgents (Fase 4 conductor backbone)**: Upgrade dari LangGraph bookmark.
  DeepAgents terinspirasi Claude Code — `write_todos` planning, filesystem backend
  untuk context offload, subagent spawning per worker, QuickJS REPL.
  install: `uv add deepagents`. Evaluate sebagai conductor backbone saat Fase 4 dimulai.
  LangGraph tetap listed sebagai underlying runtime kalau butuh low-level control.
- **Zencoder patterns (referensi)**: SKIP install (commercial, $19-250/user/month).
  2 patterns diadopsi: multi-model validation untuk auditor periodic_audit
  (model A run, model B verify), daily scheduled GitNexus re-index untuk scout
  (bukan hanya post-commit). Dokumentasi: workers.md auditor + scout sections.

## Keputusan Final yang Sudah Dibuat (v5.6 — update 2026-03-18)

- **Mechanistic Interpretability / Grokking**: LoRAMetadata extended dengan
  `training_phase`, `grokking_confidence`, `loss_curve`, `circuit_count`.
  Trainer WAJIB simpan loss curve snapshots setiap 50 steps ke Ring 2.
  Trainer WAJIB run grokking analysis setelah training — jangan activate
  kalau phase == 'memorizing' atau confidence < 0.4.
  Brain viz Tab 4 Loss Curve: phase banner, chart, grokking event annotations.
  Sources: arxiv.org/abs/2301.05217 (paper) + brain-visualization.md + training-landscape.md
- **Stripe Minions patterns**: 4 patterns diadopsi ke workers.md —
  TASK_TYPE_TOOL_SUBSETS (task-type → curated tool subset per task),
  Deterministic/Agentic labels di post-coding pipeline,
  MAX_RETRY_CAP=2 untuk tester (2 CI rounds then escalate),
  DIRECTORY_SKILL_MAP (scout auto-attach SKILL.md per directory).
  Source: stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents
- **mHC (tokenbender/DeepSeek)**: SKIP. Hanya relevant kalau pre-train dari scratch.
  Bookmark di LINKS.md untuk Fase 5+.
  Konsep geometric structure selaras dengan mech interp — keduanya confirm
  neural networks learn interpretable structured representations.

- **Anthropic Advanced Tool Use**: beta header `advanced-tool-use-2025-11-20` di conductor.
  Tool Search (`defer_loading: true`) → 85% reduction tool definition overhead.
  Programmatic Tool Calling → 37% token reduction, eliminasi 19+ inference passes.
  Tool Use Examples → accuracy 72% → 90%. Implementation: workers.md → conductor.
  Baca dulu: https://www.anthropic.com/engineering/advanced-tool-use
- **Qwen3.5-35B Distilled Claude Opus**: bookmark Fase 4 — evaluate vs Qwen2.5-32B
  untuk conductor. Link: huggingface.co/Jackrong/Qwen3.5-35B-A3B-Claude-4.6-Opus-Reasoning-Distilled
  Koleksi semua size (2B→35B): huggingface.co/collections/Jackrong/...
  Ditraining Unsloth — langsung kompatibel trainer pipeline kita.
- **OmniCoder-9B**: SKIP sekarang. Butuh model card + benchmark spesifik dulu.
- **JSON-Render (Vercel)**: tidak di-install. Guardrailed generation pattern diadopsi:
  compositor generate JSON → map ke FectTral components (catalog-driven, bukan arbitrary HTML).
  FectTral MCP server expose `render-ui` tool constrained ke component catalog.
- **KARL (Databricks)**: blueprint Fase 4-5. Implementation di training-landscape.md.
  Tiga patterns diadopsi: iterative bootstrapping (trainer), search efficiency training
  (scout), hard-to-verify multi-attempt eval (auditor + curator).
  Baca: databricks.com/blog/karl-knowledge-agents-via-reinforcement-learning

- **RLM (alexzhang13/rlm)**: `pip install rlm` — inference wrapper untuk scout + auditor + curator.
  Tidak replace Ollama/vLLM. Aktif kalau estimated_tokens > 6000-8000.
- **MarkdownFetcher**: buat `backend/utils/markdown_fetcher.py` saat implement scout.
  `Accept: text/markdown` header → 80-99% token reduction. Bukan worker baru.
  `x-markdown-tokens` di-pass ke conductor untuk decide RLM atau tidak.
- **Trainer overnight loop**: patterns dari karpathy + uditgoenka autoresearch sudah masuk
  trainer section di workers.md. val_bpb metric, MAX_TRAIN_MINUTES=5, git-as-memory,
  experiments.parquet di Ring 2. Tidak install kedua repo — baca saat implement.
- **Impeccable concepts** (pbakaus/impeccable): tidak di-install. Command vocabulary
  (/audit /polish /distill /bolder /quieter /animate /typeset /colorize /critique
  /delight /overdrive) masuk SKILL.md compositor + stylist. Anti-pattern catalog masuk
  archivist tagging. Aesthetic direction + aesthetic-context.json masuk designer.

- **Tech stack design workers + scout**: TypeScript MCP (`packages/mcp-scout/` + `packages/mcp-design/`)
- **life_manager**: worker baru 🌱, generate daily_rules.json setiap session
- **Needs system**: 4 bars (energy/social/focus/hunger), rule-based, settings toggle
- **Room editor**: Tauri app terpisah, komunikasi file-based (room-config.json)
- **Multi-lantai**: lantai 2 unlock saat workers > 15, viola rooms di lantai 2
- **Walk-to-desk entry**: conductor/scout/trainer/curator/designer punya animasi masuk
- **Rooftop ceremony**: 11-beat scene saat LoRA baru di-approve
- **Knowledge approval**: curator → auditor → trainer/coder, loop sampai approved
- **dLLM**: Fase 5 experimental — tunggu model ≥7B HumanEval >60%. Track: Dream 7B, DiffuLLaMA
- **uncertainty detector**: logic conductor detect UNKNOWN UNKNOWN (bukan dLLM — nama direfactor)
- **Router Dinamis**: intake output tambah routing_hint, conductor fast-path kalau confidence >0.8
- **Eval Module**: lm-evaluation-harness per-benchmark scoring, replace eval sederhana Fase 4

## Konteks Diskusi Terakhir (2026-03-18 — session terbaru)

**Update besar dari session 2026-03-18:**

openclaw-office discovery — WW-AI-Lab sudah build "vibe-office versi lain" dengan
React SVG/R3F. Core metaphor sama: Agent = Employee, Office = Runtime, Desk = Session.
WAJIB baca source code sebelum Fase 2 — terutama event-parser.ts dan mock-adapter.ts.

AgentScope (Alibaba, 18.2k stars) — MsgHub pattern untuk dynamic worker management
diadopsi sebagai WorkerHub class untuk bridge Fase 3. Group-wise tool management
extend TASK_TYPE_TOOL_SUBSETS. Trinity-RFT untuk KARL implementation Fase 4-5.

MassGen — timeline view pattern untuk TV screen meeting room.

GMvandeVen/continual-learning — EWC referensi Fase 5, tapi O-LoRA mungkin cukup.

OpenClaw + nanobot + DeepAgents + Zencoder dari session sebelumnya juga sudah
terdokumentasi di LINKS.md section MULTIMODAL GATEWAY.

**Hal yang BELUM didokumentasikan / perlu session berikutnya:**
- `backend/multimodal-integration.md` → arsitektur Fase 6 (foto/YT/Chrome handlers)
- LoRA composition di inference → SUDAH SELESAI di `backend/vllm-setup.md`
- EWC implementation detail kalau O-LoRA insufficient (Fase 5)
- Security model detail untuk OpenClaw gateway exposure

## Konteks Diskusi Lama (2026-03-17, FectTral integration)

Wolfvin mengusulkan beberapa ide baru yang sudah diputuskan:

**Penamaan workers** — semua direvamp. Lihat tabel Registry di atas.
Wolfvin setuju semua kecuali coders di-spesialisasi (`coder_rust`, `coder_css`, dll).

**Continual Learning** — workers bisa terus belajar dua level:
Knowledge Injection (SKILL.md update) dan LoRA fine-tuning via trainer.

**"Isi otak" workers** — bisa divisualisasikan sebagai LoRA collection.
Kamu bisa lihat tiap LoRA, performancenya, domain-nya. Bisa toggle aktif/nonaktif.
Kalau ada fungsi yang tidak OK → inform trainer untuk disable LoRA tersebut
atau minta trainer refactor (trainer minta bantuan scout untuk research).

**Workers yang merged:**
- review_worker + ai_advisor → `auditor` (2 mode)
- context_worker + ai_fetcher → `scout` (+ proactive research mode)

**Workers baru standalone:** `curator`, `trainer`, `steward`

**Idea yang sudah selesai didokumentasikan (dari diskusi lama):**
- Brain visualization UI detail → `frontend/brain-visualization.md` ✅
- LoRA composition di inference → `backend/vllm-setup.md` ✅
- EWC → referensi di `LINKS.md` + `backend/training-landscape.md` ✅ (Fase 5)
