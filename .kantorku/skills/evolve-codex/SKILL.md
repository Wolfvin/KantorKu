---
name: evolve
description: Unified evolution workflow for extracting reusable learning from repo/link/session inputs and storing it into `.codex/apps/arch-engine` as the primary decision memory, then syncing affected skills.
---

# Evolve (Compact)

## Trigger
- User minta upgrade lintas skill dari repo/link/pembelajaran sesi.
- User minta pruning overlap/noise atau evaluasi token efficiency.
- Sinyal internal berulang: `rate_limit_hits|measurement_drift|failure_recurrence|routing_drop`.
- User minta pembelajaran diekstrak ke `arch-engine`.

## Hard Rules
1. `recommendation_first`: analisis dulu, patch hanya untuk scope low-risk atau user-approved.
2. `gate_before_patch`: wajib tampilkan `evolve_necessity`, `reasoning_summary`, `token_impact_estimate`, `decision`.
3. `autonomy_boundary`: tidak boleh destructive/high-impact tanpa approval user.
4. `minimal_atomic_change`: 1 micro-change terukur per cycle.
5. `action_verified_arch_memory_only`: no execution, no arch-engine memory.
6. `context_alignment_gate`: output wajib align ke pertanyaan user terakhir.
7. `safety_stance`: jika risiko tinggi, wajib `assistant_position=partial|disagree` + opsi aman.
8. `cleanup_after_extract`: source intake sementara wajib dihapus setelah `arch-engine lane` selesai dan sinkronisasi turunan selesai.

## Necessity Gate
1. Jalankan `think` untuk tentukan `desired_mode`:
- `plan_first` untuk ambigu/non-trivial/high-risk.
- `execute_first` untuk jelas/low-risk.
2. Jalankan `token-optimizer` untuk budget dan bloat check.
3. Klasifikasi kebutuhan: `required|optional|not_needed`.

## Execution Flow
1. Intake minimum relevance-first.
2. Pecah jadi unit ilmu: `workflow|gating|tooling|verification`.
3. Simpan unit ilmu ke `arch-engine` dulu (ingest + classify + gate).
4. Map action turunan: `enrich|merge|create|create_tool|drop`.
5. Tetapkan `evolution_hypothesis` + `if_then_commitment`.
6. Pilih mode: `incremental|adaptive|breakthrough`.
7. Eksekusi patch hanya jika mode mengizinkan (`execute_first` atau user-approved).
8. Verifikasi, catat dampak, dan simpan artifact eksperimen.

## Primary + Sync Lane (Mandatory)
1. `primary lane (arch-engine)`: semua pembelajaran reusable wajib masuk ke `arch-engine` sebagai source-of-truth (ingest/resolve/lifecycle/cleanup audit).
2. `sync lane (skill/memory)`: update skill + MEMORY hanya sebagai turunan dari keputusan `arch-engine`.
3. Cleanup source hanya setelah lane primary `berhasil` dan lane sync selesai untuk scope terdampak.

## Source Lanes
- `memory->arch-engine`: distill MEMORY jadi candidate knowledge, ingest ke arch-engine, lalu sync delta ke skill.
- `archive->arch-engine`: klasifikasi `runtime-linked|non-runtime|standalone-reference`, ingest boundary/dependency/verification ke arch-engine.
- `tmp->arch-engine`: perlakukan `.tmp` sebagai ephemeral, ingest lesson ke arch-engine lalu cleanup.

## Strategy + Stagnation
- Preset: `balanced` (default), `innovate`, `harden`, `repair-only`.
- Jika 2 cycle tanpa `quality_delta` positif -> stagnation aktif.
- Saat stagnation: mode `harden|repair-only`, scope 1 micro-change.
- Jika stagnan setelah 2 intervensi tambahan -> stop dan eskalasi user.

## Verification
- Wajib ukur: `quality_delta`, `token_delta`, `failure_recurrence`.
- Wajib catat: `assertiveness_quality`, `blind_agreement_incident`, `context_alignment_quality`.
- Jika regress: rollback ke versi sebelum eksperimen.

## Evidence Tier
- Tier 1: sumber primer/resmi.
- Tier 2: dokumentasi resmi maintainer.
- Tier 3: analisis sekunder berkualitas.
- Tier 4: community signal pelengkap.
- Konflik sumber: escalate `quick -> default -> deep`.

## Output Wajib
- `units_of_knowledge`
- `arch_engine_ingestion` (unit -> status -> decision)
- `mapping` (unit -> skill -> action, turunan dari arch-engine)
- `kept_vs_dropped` (+ alasan)
- `files_changed`
- `quality_impact_summary`
- `source_quality_score`
- `evolution_mode`
- `risk_budget`
- `initiative_mode` (`user_requested|self_initiated`)
- `desired_mode` (`plan_first|execute_first`)
- `mode_source` (`think|token_optimizer_guard|web_search_guard|default`)
- `mode_effect` (`planned_only|executed`)
- `assistant_position` (`agree|partial|disagree`)
- `assertiveness_quality` (`pass|fail|pending`)
- `blind_agreement_incident` (`yes|no`)
