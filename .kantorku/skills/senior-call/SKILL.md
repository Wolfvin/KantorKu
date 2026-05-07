---
name: senior-call
description: "Router skill untuk memilih jalur senior frontend atau senior backend. Use ketika user meminta perspektif senior engineer terkait kerapian, kesederhanaan, maintainability, lalu arahkan ke skill domain senior-call-frontend atau senior-call-backend."
---

# Senior Call (Router)

## Purpose
Skill ini hanya berfungsi sebagai router agar trigger `senior-call` tetap kompatibel.
Skill ini wajib dipakai untuk task implementasi/review/refactor yang menulis kode atau mengambil keputusan arsitektur.

## Routing Priority (Risk First)
1. Jika ada risiko `data loss`, `security`, atau `silent failure` di backend:
- Route wajib: `senior-call-backend`.

2. Jika risiko dominan runtime/API/I/O/error handling/persistence:
- Route: `senior-call-backend`.

3. Jika risiko dominan UI/UX, komponen, state frontend, styling, halaman webview:
- Route: `senior-call-frontend`.

4. Jika konteks campuran:
- Route: `split`, mulai dari sisi risiko tertinggi (backend risk > frontend risk).

## Routing Rule
- Konteks backend dominan -> `senior-call-backend`.
- Konteks frontend dominan -> `senior-call-frontend`.
- Jika ambigu, pilih backend dulu jika ada potensi dampak data/runtime.
- Jika task menyentuh backend+frontend: route `split`, jalankan backend dulu lalu frontend.

## Mandatory Gate
- Untuk task write-code/decision:
1. Jalankan `senior-call` dulu.
2. Route ke skill domain (`backend|frontend|split`).
3. Output keputusan domain wajib dipakai sebelum patch final.

## Output Contract
- `route`: `frontend|backend|split`
- `reason`: alasan singkat pemilihan route
- `next`: skill target yang harus dijalankan

## Note
- Jangan duplikasi checklist detail di skill ini.
- Checklist detail ada di skill domain masing-masing.
