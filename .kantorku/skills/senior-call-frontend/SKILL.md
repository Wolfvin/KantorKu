---
name: senior-call-frontend
description: Senior frontend guardrails for clean, simple, maintainable UI work. Use for frontend implementation/review decisions on component structure, state flow, styling hygiene, and patch-vs-refactor choice.
---

# Senior Call Frontend (Compact)

## Core Rule
- Prefer simple, consistent UI architecture.
- Hindari state/abstraction tambahan tanpa kebutuhan nyata.

## Use This Skill For
- Struktur pages/components/features/shared.
- State ownership dan alur data.
- CSS hygiene dan anti-sprawl.
- Menentukan `patch` vs `minimal_refactor`.

## Execution Checklist
1. Definisikan target UI/UX dalam 1 kalimat.
2. Batasi scope komponen (hindari edit lintas halaman jika tidak perlu).
3. State ownership: local dulu, global hanya jika benar-benar shared.
4. Data flow one-directional dan mudah ditelusuri.
5. CSS spesifik secukupnya; hindari `!important`/duplikasi.
6. Cek aksesibilitas minimum (focus, keyboard, label/role).
7. Naming komponen/class/handler harus intention-revealing.
8. Evaluasi blast radius visual + interaction regression.

## Hygiene Gate (Mandatory)
1. Hapus legacy flag/key/fallback/handler yang tidak aktif.
2. Satu source-of-truth untuk auth/session/config/state frontend.
3. Larang dual owner state lintas core/feature/wrapper.
4. Fallback UI/network harus eksplisit alasan degrade + log level tepat.
5. Migrasi key/config one-way cleanup.

## Decision Gate
- `patch`: perubahan terbatas 1-3 komponen, flow utama tetap.
- `minimal_refactor`: duplikasi logic/style menghambat perubahan saat ini.
- `reject_overengineering`: usulan tambah layer/state/tool tanpa urgency.

## Output Contract
- `call` (`accept|minimal_refactor|reject_overengineering`)
- `why` (1-3 alasan teknis)
- `scope` (file frontend)
- `risk` (+ mitigasi)
- `verification` (cek UI konkret)
