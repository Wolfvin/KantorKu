---
name: senior-call-backend
description: Senior backend guardrails for clean, reliable, maintainable service/API work. Use for backend implementation/review decisions about boundaries, ownership, errors, I/O flow, and patch-vs-refactor choice.
---

# Senior Call Backend (Compact)

## Core Rule
- Keep backend boring: clear contracts, explicit errors, minimal magic.
- Tambah kompleksitas hanya jika risiko nyata terbukti.

## Use This Skill For
- Boundary API/service/repo/core.
- Validasi input/output + error handling.
- Menolak overengineering.
- Menentukan `patch` vs `minimal_refactor`.

## Execution Checklist
1. Nyatakan contract endpoint/command (`input|output|error`).
2. Batasi scope ke layer minimum relevan.
3. Validasi input fail-fast.
4. Error harus explicit dan actionable (tanpa silent swallow).
5. Side-effect (db/file/network) wajib guard + timeout.
6. Cek idempotency untuk action repeatable.
7. Hindari library/config baru tanpa manfaat jelas.
8. Pastikan observability cukup untuk reproduksi.

## Hygiene Gate (Mandatory)
1. Hapus legacy path tidak aktif pada file yang disentuh.
2. Satu source-of-truth per concern (auth/session/config/state).
3. Larang dual-owner flow untuk state yang sama.
4. Fallback wajib punya alasan + level log tepat.
5. Migrasi key/config bersifat one-way cleanup.

## Decision Gate
- `patch`: akar masalah lokal, contract tetap.
- `minimal_refactor`: ambiguity ownership/maintainability menghambat reliability.
- `reject_overengineering`: usulan tambah layer/toggle tanpa kebutuhan nyata.

## Hard Stop Rules
- Stop jika ada path kritikal menelan error tanpa log/code eksplisit.
- Tolak abstraction/toggle baru untuk kasus one-off.
- Wajib `minimal_refactor` jika bug berulang berasal dari owner ambiguity.

## Output Contract
- `call` (`accept|minimal_refactor|reject_overengineering`)
- `maintainability_call` (`stable|watch|debt_risk`)
- `why` (1-3 alasan teknis)
- `scope` (file/module)
- `risk` (+ mitigasi)
- `verification` (signal test/log konkret)
