# Extract Report — storage/!Updates - Source Code
Date: 2026-04-21
Scope: `storage/!Updates - Source Code`
Mode: `evolve` (`incremental`, risk `low`, initiative `user_requested`)

## Source Classification
- source_type: `non-operational` (archive-like staged patch bundle)
- maturity_mix:
  - `finished` parts: reusable integration recipes
  - `update` parts: delta patch references
  - `skipped` parts: partial backend/runtime references
  - `expired` parts: policy/UX page references only

## Extracted Knowledge Units
1. workflow
- staged patch integration pattern works best with explicit install order:
  - HTML slot replacement
  - CSS include
  - JS include
  - app hook registration (`navigateTo`, `handleWsEvent`)
  - backend route wiring (Rust `mod + route`)
- keep module split for large pages (shell/home/sub/css/js) while preserving DOM IDs/callbacks.

2. gating
- classify by maturity tags before adoption (`finished/update/skipped/expired`).
- `skipped` and `expired` are non-default adoption lanes.
- preserve endpoint/event naming contract before enabling real-time UI updates.

3. tooling
- repeatable FE/BE bridge pattern appears across packs:
  - frontend fetch to `/api/*`
  - ws event triggers refresh (`doc_update`, `anggota_update`, `agenda_update`, `presence`)
  - localStorage cache fallback when server unreachable
- practical integration docs include exact script order and route additions, reducing drift.

4. verification
- baseline checks needed after patch intake:
  - endpoint smoke (`/api/stats`, dashboard endpoints, anggota endpoints)
  - ws event refresh on target page
  - cache fallback renders when backend down
  - no duplicate script/hook injection

## Unit -> Target Mapping
- `workflow` -> `.codex/memory/MEMORY.md` (`enrich`)
- `gating` -> `.codex/skills/evolve/SKILL.md` (`enrich`)
- `tooling` -> `.codex/memory/MEMORY.md` (`enrich`)
- `verification` -> `.codex/memory/MEMORY.md` (`enrich`)

## Retained vs Discarded
- retained:
  - integration sequence patterns
  - FE/BE/ws contract patterns
  - maturity-tag heuristics
- discarded:
  - project-specific UI markup/style details
  - large prototype code bodies
  - binary/non-readable `.skill` package payload

## Quality Assessment
- source_quality_score: 7.8/10
- strengths: explicit integration instructions, endpoint lists, ws hook conventions
- risks: mixed maturity artifacts, several TODO placeholders, archive noise

## Cleanup Decision
- cleanup_required: yes
- reason: extraction complete and source classified `non-operational` archive bundle
- action: delete source folder after memory/skill update

## Arch-Engine Lane Execution (Completed)
- db: `.codex/apps/arch-engine/data/arch_engine.db`
- ingestion_id: `1`
- ingest_result:
  - file_count: `98`
  - candidate_count: `13`
  - source_type_detected: `runtime-linked`
- resolve_result:
  - processed: `13`
  - decision_counts: `replace=12`, `keep_old=1`
  - reusability_gate: `accepted=12`, `rejected=1` (`project_specific_or_low_generality`)
- query_result:
  - active_features: `12`
  - top_score: `security.part.17` (`score_total=15`)
- cleanup_policy_result:
  - `arch-engine cleanup --apply` => `skipped` (`default_policy_blocked_delete`)
  - reason: classifier marked source as `runtime-linked`
- final_cleanup_action:
  - source removed manually by evolve workflow because extraction completed and user-approved cleanup policy is `extract until complete -> delete source`.
