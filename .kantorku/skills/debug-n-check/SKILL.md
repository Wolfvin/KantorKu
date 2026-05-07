---
name: debug-n-check
description: Unified debug and verification workflow for frontend and backend issues. Use after plan completion for validation, or immediately when user reports a bug. Combines console loop (frontend/js/ui) and terminal loop (backend/api/runtime) with evidence-first iteration.
---

# Debug N Check (Compact)

## Trigger
- User lapor bug/error/regresi.
- Perlu validasi hasil patch secara evidence-first.

## Plan Mode Audit Gate
- Jika user memanggil kombinasi `[$debug-n-check] [$review] mode plan`, WAJIB buat file markdown audit sebelum kerja teknis.
- Kerja teknis = sebelum reproduce, edit file, run test/build, atau eksekusi command debug.
- Lokasi file audit: root workspace (cwd saat eksekusi).
- Nama file: `AUDIT_PLAN__YYYY-MM-DD__<topic-slug>.md`
- Minimal isi audit:
  - context & tujuan
  - scope in/out
  - asumsi
  - rencana langkah verifikasi
  - risiko awal
  - timestamp mulai
- Jika file audit belum ada, proses harus berhenti di langkah persiapan (jangan lanjut debug loop).

## Loop
1. Reproduce minimal.
2. Isolate suspect layer (UI/API/runtime/config/state).
3. Apply smallest fix.
4. Verify with concrete signal.
5. Repeat sampai pass.

## Stagnation Gate
- Jika dua iterasi loop tidak mengubah symptom, tandai `stagnation=active`.
- Saat `stagnation=active`, ganti hanya satu variabel per iterasi berikutnya.
- Restart proses hanya jika health check gagal dan tidak ada output berarti melewati silence window.
- Jika tetap stagnan setelah dua iterasi tambahan, stop dan eskalasi dengan evidence.

## Evidence Minimum
- symptom awal
- root cause singkat
- fix applied
- verification signal (log/test/UI behavior)

## Token Policy
- Ambil log secukupnya, potong noisy output.
- Jangan dump full console jika tidak perlu.

## Output Wajib
- findings (severity-first)
- patch summary
- verification result
- residual risk/testing gap
