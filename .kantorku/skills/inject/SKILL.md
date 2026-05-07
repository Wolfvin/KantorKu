---
name: inject
description: Unified context injection router/adaptor for general, frontend, tauri, and typescript tasks. Use when agents need context assembly before implementation, while verification gate and fail-condition decisions are owned by `.codex/apps/arch-engine`.
---

# Inject (Compact)

## Trigger
- Perlu context injection cepat sebelum implementasi.
- Task frontend/UI, Tauri, TypeScript/JavaScript refactor safety, atau context orchestration lintas domain.

## Domain Route
1. `general` untuk context orchestration umum.
2. `frontend` untuk UI/design system constraints.
3. `tauri` untuk desktop/mobile Tauri constraints.
4. `typescript` untuk TS/JS diagnostics dan impact check.

## Flow
1. Klasifikasikan domain (`general|frontend|tauri|typescript`).
2. Kumpulkan context minimum sesuai domain.
3. Kirim context ke `arch-engine` sebagai decision owner.
4. Terapkan `verification_gate` dan `fail_condition` dari `arch-engine`.
5. Jika evidence kurang, fallback `web-search` lalu re-evaluate via `arch-engine`.

## Domain Context Pack
- `general`: tujuan, scope, dependency context, known gap.
- `frontend`: design language, visual direction, responsive constraints, DESIGN.md fit.
- `tauri`: bridge/plugin readiness, IPC contract, window/webview constraints.
- `typescript`: diagnostics/error state, symbol/reference impact, type-safety path, regression hotspot.

## Rule
- Skill ini hanya router/adaptor.
- Keputusan final pass/fail wajib dari `arch-engine`.
- Dilarang menentukan gate final secara lokal tanpa hasil `arch-engine`.
- Jika saat inject ditemukan pembelajaran reusable lintas sesi, wajib handoff ke `evolve` untuk ingest ke `arch-engine` sebagai source-of-truth.

## Output Wajib
- `domain`
- `context_packet`
- `arch_engine_decision`
- `verification_gate`
- `fail_condition`
- `fallback_applied` (`yes|no`)
- `gap_remaining` (jika ada)
- `evolve_handoff` (`required|not_required`)
