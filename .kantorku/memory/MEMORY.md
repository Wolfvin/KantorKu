# Project Memory (unified)

## Project
- name: `KantorKu` (merged with `codex-skill`)
- purpose: AI worker orchestration framework + enriched agentic skill ecosystem with knowledge library
- memory_policy: multi-file staging (`memory/MEMORY.md` index + `memory/<topic>.md` topic files)

## Context
KantorKu — AI worker orchestration framework modeling a real digital office.
14 specialized workers coordinated by a Conductor (CEO) with contract-based workflows.
Merged with codex-skill (skills_and_mcp) for enriched skill portfolio (21+ skills) and knowledge library.

## Stable Directives
- Operate autonomously, implementation-first.
- Keep signal high: no speculative additions, no bulk import without request.
- Local skills are primary owner (`.kantorku/skills/*`).
- Default non-trivial gate: `think` first; route with `skill-router` when ambiguous.
- MCP posture: default off, enable on-demand per phase.
- Action-verified memory only: No Execution, No Memory.

## Runtime Guardrails
- Start session with home guard:
  - Linux/macOS: `bash .kantorku/tools/home-codex-guard.sh enforce`
  - Windows: `powershell -ExecutionPolicy Bypass -File .kantorku/tools/home-codex-guard.ps1 enforce`
- Ensure arg0 wrapper:
  - primary: `bash .kantorku/tools/codex-arg0-bootstrap.sh`
- Web research escalation: `quick/native_search -> default/metasearch_backend -> deep/deep_research_orchestrator`

## Key Decisions
- [2026-05-07] Merged codex-skill repo into KantorKu -> enrich office+library with 21+ skills, arch-engine, knowledge corpus
- [2026-05-07] Codex skills transferred to `.kantorku/skills/` (20 new + 5 existing = 25 total)
- [2026-05-07] Knowledge corpus placed at `data/library-sources/` (50 MD files, 12 categories)
- [2026-05-07] arch-engine placed at `.kantorku/apps/arch-engine/` for dual-lane evolve

## Active Tasks
- [ ] Library ingestion of `data/library-sources/` knowledge corpus (pending runtime activation)
- [ ] Mini-service interface-drop setup (pending)
- [ ] Evolve skills merge: align `evolve-codex` with KantorKu `evolve` skill

## Completed Tasks
- [x] Transfer all codex-skill skills to KantorKu (2026-05-07)
- [x] Transfer all codex-skill tools to KantorKu (2026-05-07)
- [x] Transfer codex memory to KantorKu memory (2026-05-07)
- [x] Transfer arch-engine app to KantorKu (2026-05-07)
- [x] Transfer New Information/ knowledge corpus to library-sources (2026-05-07)
- [x] Transfer HP-NI-1.txt, KDS_PLAN.md, KAW81/, asus/ to library (2026-05-07)
- [x] Transfer interface-drop mini-service (2026-05-07)
- [x] Merge .vscode configs (2026-05-07)
- [x] Enrich AGENTS.md with codex knowledge (2026-05-07)
- [x] Update skill-map.tsv with all skills (2026-05-07)

## Learnings
- `.tmp` = ephemeral intake cache; not source-of-truth long-term (from codex evolve sessions)
- Compact skill format materially reduces context cost (~89% byte reduction observed)
- Dual-lane evolve: arch-engine (structural) + skill/memory (operational); cleanup only after both lanes complete
- Repeated context miss must be hard safety signal: if `consecutive_context_misses >= 2`, force `plan_first`
- Archive classification before adoption: `runtime-linked | non-runtime | standalone-reference`
- Action-verified memory wajib; inference-only memory is anti-pattern
- Layer index harus pointer-only; detail di layer/artifact bawah
- Context compression sebaiknya cadence-based (milestone), bukan reaktif saat limit token

## Reusable Lessons (from codex-skill evolve sessions)

### Evolution / Governance
- Keep evolve cycles incremental, low-risk, one micro-change + verify.
- Use strategy preset intentionally: `balanced|innovate|harden|repair-only`.
- For user-requested high-impact changes: recommendation-first + explicit tradeoff.

### Token / Context
- Large skill corpus causes rate-limit pressure quickly.
- Keep outputs short by default; details go to artifacts only when needed.

### Setup / Drift
- Home-level Codex drift is a recurring risk; enforce baseline at session start.
- Keep wrappers and model defaults reproducible via deterministic scripts, not manual fixes.

### Verification Discipline
- Do not trust "looks successful" signals when backend/runtime can fallback silently.
- Separate lanes for verification when chaos behavior and deterministic hooks differ.
- Use minimal verification matrix on critical changes: `policy`, `loop`, `integrity`.

### Hybrid App Runtime (Tauri + local backend)
- Treat `connection refused` as backend lifecycle issue first.
- Frontend must be shape-safe (array/number guards) and auth-gated without fake success fallback.

### Cross-OS / Toolchain
- For cross-OS issues, validate invariant app behavior first, then confirm on target OS.
- Feature-gate toolchain-sensitive capabilities (e.g., `libclang`-dependent OCR modes).

## Anti-Drift Rules
- Use `memory/MEMORY.md` as index and `memory/<topic>.md` as staging topics.
- Before deleting temporary/session docs: extract reusable lessons into this file first.
- Prefer updating existing sections over appending duplicate narratives.

## Library Knowledge Corpus Index
- `data/library-sources/knowledge/` — 50 curated MD files across 12 domains
  - 01_Rust-Tauri (5 files)
  - 02_AI-Model-Arsitektur (5 files)
  - 03_Cybersecurity-EDR (9 files)
  - 04_Spreadsheet-Excel (6 files)
  - 05_AI-Agent-Orchestration (4 files)
  - 06_AI-Image-Video (5 files)
  - 07_Game-Development (1 file)
  - 08_Jaringan-Kriptografi (1 file)
  - 09_AI-Career-Trends (4 files)
  - 10_Self-Hosting-AI (3 files)
  - 11_Multi-Domain (3 files)
  - 12_Project-Docs (3 files)
- `data/library-sources/references/HP-NI-1.txt` — Networking/Crypto/Security/Dev deep reference
- `data/library-sources/projects/KDS_PLAN.md` — Kitchen Display System plan
- `data/library-sources/projects/KAW81/` — Restaurant web app + SOP
- `data/library-sources/scripts/asus/` — Python automation (tax, PDF, Excel)

## Latest Consolidation Checkpoints
- 2026-05-07: codex-skill repo merged into KantorKu; all skills, tools, memory, apps, knowledge transferred.
- 2026-04-21: (from codex) `.codex-merge` consolidated into `.codex`, unique artifacts imported.
- 2026-04-21: (from codex) evolve gates hardened (strategy preset, stagnation gate, safety boundary).
