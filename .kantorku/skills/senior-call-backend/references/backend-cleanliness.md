# Backend Cleanliness Heuristics

## Practical Rules
- Pisahkan orchestrator logic dari pure business rule bila mulai bercampur.
- Pastikan setiap integration point punya timeout, retry policy sadar risiko, atau fail-fast.
- Error taxonomy sederhana lebih baik daripada enum berlapis yang tidak dipakai.

## Review Prompts
- Kalau request gagal, apakah penyebab utama bisa ditemukan dari satu trace/log path?
- Apakah endpoint/command ini punya perilaku deterministik untuk input sama?
- Apakah perubahan ini mengunci tim ke dependency/architecture yang sulit diputar balik?

## Release Hygiene
- Prefer small deployable changes.
- Tulis migration/risk note jika ada perubahan schema atau format data.
- Pisahkan commit refactor dan commit behavioral change bila memungkinkan.

## Maintainability Scorecard
Gunakan skor cepat 0/1 per item, lalu jumlahkan.

1. Domain ownership jelas (tidak ada owner ganda untuk flow inti).
2. Naming folder/file/function intention-revealing.
3. Dependency direction bersih (tidak ada layer inversion).
4. Duplikasi logic kritikal tidak bertambah.
5. Error handling tetap eksplisit dan actionable.
6. Perubahan tetap small-batch (blast radius terkendali).
7. Verification path jelas (test/log/manual signal ada).

Interpretasi:
- `6-7`: `stable`
- `4-5`: `watch`
- `0-3`: `debt_risk`

## Red Flags (Immediate Watch)
- Satu bug fix menyentuh banyak domain yang tidak berkaitan.
- Nama function terlalu umum sehingga intent tidak terbaca.
- Repo/integration mulai berisi policy bisnis.
- Banyak fallback diam-diam tanpa log/code error eksplisit.

## Ready-to-Use Review Template
Gunakan template ini untuk hasil review cepat:

```text
BACKEND MAINTAINABILITY REVIEW
call: <accept|minimal_refactor|reject_overengineering>
maintainability_call: <stable|watch|debt_risk>

why:
1) <alasan-1>
2) <alasan-2>

scope:
- <file/module-1>
- <file/module-2>

risk:
- <risiko-utama> -> <mitigasi>

verification:
- <test/log/manual signal>

scorecard:
- ownership: <0|1>
- naming: <0|1>
- dependency_direction: <0|1>
- duplication: <0|1>
- explicit_errors: <0|1>
- blast_radius: <0|1>
- verification_path: <0|1>
- total: <0..7>
```
