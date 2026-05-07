---
name: smart-plan
description: Unified planning, delivery, intake, routing, and verification workflow for complex execution. Use when user asks for roadmap/planning/spec/RPI/delivery gates, tagged or ambiguous intake, or high-accuracy verification before final delivery.
---

# Smart Plan (Compact)

## Trigger
- Task non-trivial, multi-fase, atau high-risk.
- User minta plan/roadmap/spec sebelum eksekusi.

## Default Lane
1. Define objective + constraints + done criteria.
2. Break jadi fase kecil yang executable.
3. Eksekusi fase aktif, verify, lalu lanjut fase berikutnya.
4. Simpan handoff ringkas saat phase switch.

## Plan Schema (Ringkas)
- `goal`
- `scope_in`
- `scope_out`
- `phases[]`
- `risks[]`
- `verification[]`
- `next_step`

## Delivery Gates
- Gate 1: context cukup.
- Gate 2: plan realistis dan teruji.
- Gate 3: hasil verified.
- Gate 4: ringkasan + next actions.

## Token Policy
- `tight_plan_mode` default.
- Hindari narasi panjang; fokus checklist/action.

## Output Wajib
- plan ringkas per fase
- status fase (`pending|in_progress|done|blocked`)
- evidence verifikasi
- blocker + minimal next step
