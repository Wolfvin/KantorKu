---
name: checkpoint
description: Unified memory checkpoint and rapid codebase onboarding workflow. Use when user asks to save learnings/context, persist session insights, avoid repeating failed approaches, or quickly onboard unfamiliar repositories into an executable engineering map.
---

# Checkpoint (Compact)

## Trigger
- User minta simpan pembelajaran sesi.
- Perlu handoff/context recovery.

## Memory Rule
1. Multi-file staging:
- index: `.codex/memory/memory.md`
- topics: `.codex/memory/<topic>.md`
2. Simpan high-signal reusable lessons.
3. Hindari narasi panjang dan duplikasi.
4. Simpan lesson gagal secara blameless (`symptom`, `root_cause`, `fix_applied`, `reusable_rule`).
5. Jika user minta cleanup/hapus dokumen sesi, WAJIB arsipkan isi penting markdown ke memory staging dulu.

## Markdown Artifact Sweep (Mandatory)
Gunakan saat user meminta checkpoint terhadap plan/report/markdown sesi.

1. Scan markdown artifact relevan (default prioritas):
- root workspace: `SMART_PLAN__*.md`, `DEBUG_REPORT__*.md`, `plan*.md`, `*PLAN*.md`, `*REPORT*.md`
- boleh tambah scope jika user sebut folder/file spesifik.
2. Buat ringkasan artifact di MEMORY:
- `plans_archived_before_delete`
- `reports_archived_before_delete`
- `symptom`, `root_cause`, `fix_applied`, `verification_signal`, `reusable_rule`, `confidence`
3. Jika user minta hapus file:
- hapus hanya setelah ringkasan masuk MEMORY.
- verifikasi post-delete (`Remaining: none` untuk target pattern).
4. Jika user tidak minta hapus:
- simpan hanya indeks artifact + pembelajaran reusable.

## De-dup Rule
- Jangan copy isi markdown mentah ke MEMORY.
- Simpan indeks file + keputusan + pelajaran reusable (delta only).
- Jika artifact sama sudah pernah dicatat, update section existing (append delta), jangan duplikasi penuh.

## MCP Consistency Guard
- Sinkronkan status MCP di memory dengan config aktual.
- Jangan simpan "active" jika runtime sudah default-off.
- Jika ada drift state, tandai `state_drift_detected` + tindakan koreksi minimum.

## Output Wajib
- apa yang ditambah/diubah di MEMORY
- alasan reusable
- confidence lesson (`high|medium|low`)
- daftar markdown artifact yang diarsipkan
- status cleanup artifact (`deleted|kept|not_requested`)
