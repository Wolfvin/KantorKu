# Reports Extraction (Consolidated)

- date: 2026-04-21
- scope: `.codex/reports/**`
- extraction_mode: evolve_compact
- objective: extract reusable signals, keep one canonical report, prune noisy historical artifacts.

## Units Extracted

### workflow
- Evolve mode efektif: `incremental`, `risk_budget=low`, `one-skill-per-cycle`.
- Plan/execute split (`plan_first|execute_first`) membantu mencegah mutasi saat context belum stabil.
- Batch pattern yang berhasil dipakai berulang: A (evolve), B (web-search), C (token-optimizer).

### gating
- Guard yang terbukti penting: `context_alignment_guard`, `disagreement_protocol`, `no_blind_yes`.
- Trigger safety: dua context miss berturut memaksa `plan_first` dan menahan patch.
- Stagnation handling: jika `quality_delta` tidak naik berturut, pindah ke mode lebih defensif (`harden|repair-only`).

### verification
- Benchmark-after-patch dipakai konsisten, tapi banyak artifact lama masih `pending_benchmark`.
- Measurement drift pernah terdeteksi saat baseline tidak apple-to-apple.
- Verification matrix yang efektif: `policy`, `loop`, `integrity`.

### tooling
- Wrapper runtime arg0 dan fallback bootstrap menjadi kontrak setup penting.
- Lifecycle health check dibutuhkan untuk mencegah restart tanpa sinyal valid.

### project-storage signals
- `smart_tax_assistance/public` terhubung ke runtime pipeline (publicDir aktif).
- `scan_backend` + `Scan_Rule_based` tercatat sebagai non-main-runtime (terpisah dari app utama).
- Cleanup non-runtime artifact berhasil menurunkan noise root project.

## Canonical Metrics Extracted
- Token profile (2026-04-16): portfolio byte reduction ~89.46% (estimated tokens turun signifikan).
- Last benchmark snapshot (`token-benchmark-latest.md` lama):
  - session_kind: `long`
  - portfolio_est_tokens: `8066`
  - scenario_bugfix_ui_est_tokens: `1601`
  - scenario_mcp_integration_est_tokens: `1594`
  - runtime metrics: `na` (belum terisi)

## High-Signal Retained Behaviors
- Recommendation-first untuk user-requested evolve.
- Low-risk incremental cycles + explicit tradeoff sebelum high-impact edits.
- Context-miss hard signal sebagai stop condition (bukan warning pasif).

## Noise/Redundancy Identified
- Banyak report eksperimen lama masih template `pending` tanpa closure final.
- Banyak benchmark timestamp duplikatif hanya beda run-id.
- Imported reports dari merge sudah diekstrak, tidak perlu dipertahankan sebagai working reports.

## Cleanup Policy Applied
- Keep:
  - `.codex/reports/REPORTS_EXTRACT__2026-04-21.md` (canonical extraction)
  - `.codex/reports/evolve-auto-state.json` (operational state)
- Purge:
  - seluruh benchmark historis, profile lama, report project-storage lama,
  - seluruh report `evolve-experiments/*` lama,
  - seluruh `imported-from-codex-merge/*`,
  - backup state lama (`evolve-auto-state.json.bak.*`).

## Post-Cleanup Result Target
- reports directory menjadi minimal, deterministik, dan siap diisi artifact baru tanpa membawa drift lama.
