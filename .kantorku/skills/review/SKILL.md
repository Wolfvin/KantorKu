---
name: review
description: Structured code and change review workflow focused on defects, regressions, risk, and test coverage gaps before delivery.
---

# Review (Compact)

## Trigger
- User minta review PR/patch/perubahan.

## Plan Mode Audit Gate
- Jika user memanggil kombinasi `[$debug-n-check] [$review] mode plan`, WAJIB buat file markdown audit sebelum kerja review/debug dimulai.
- Lokasi file audit: root workspace (cwd saat eksekusi).
- Nama file: `AUDIT_PLAN__YYYY-MM-DD__<topic-slug>.md`
- Minimal isi audit:
  - context & tujuan
  - scope in/out
  - asumsi
  - rencana verifikasi
  - risiko awal
  - timestamp mulai
- Review tidak boleh berjalan sebelum file audit tersedia.

## Default Format
1. Findings dulu (severity tertinggi ke rendah).
2. Open questions/assumptions.
3. Ringkasan perubahan (singkat).

## Checklist
- bug/regression risk
- edge cases
- security/perf concern
- testing gaps

## Verification Matrix (Mini)
- `policy`: aturan/gate baru punya kondisi aktif dan kondisi fail yang jelas.
- `loop`: alur utama jalan minimal 1 path end-to-end.
- `integrity`: tidak ada kontradiksi antar skill/rule yang disentuh.
- Gunakan matrix ini sebagai baseline saat review perubahan skill/workflow.

## Execution Guard (Anti-Ribet)
- Prinsip utama review: untuk hasil yang sama, WAJIB pilih pendekatan paling sederhana dan paling mudah dipahami.
- Jika user memberi permintaan spesifik, implementasi WAJIB mengikuti spesifikasi user tersebut (tanpa improvisasi di luar scope).
- Jika user minta aksi langsung (`direct mode`, `langsung edit`, `hardcode`, `sementara`) utamakan solusi paling sederhana yang memenuhi permintaan sekarang.
- Dilarang menambah fleksibilitas/arsitektur tambahan (toggle, config layer, refactor) kecuali user meminta eksplisit.
- Sebelum patch, WAJIB re-read file target terbaru agar patch sesuai state aktual.
- Jika ada tradeoff, jalankan versi minimal dulu; opsi yang lebih rapi disampaikan setelah perubahan utama selesai.
- Untuk mode diagnosis sementara, prioritaskan perubahan yang mudah dibalik (1 file, 1 flag, 1 titik kontrol).
- Jika ada risiko blocker/high-impact, reviewer wajib keluarkan `blocker-level disagreement` (tidak boleh hanya kompromi).

## Output Wajib
- daftar findings + lokasi file
- status overall (`pass|needs_fix`)
- residual risk
- `assistant_position` (`agree|partial|disagree`)
