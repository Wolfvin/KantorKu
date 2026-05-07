---
name: repo-intake
description: Intake workflow for external repositories or local source paths into reusable skill knowledge. Use when user provides repo URLs and asks to extract high-signal practices into `.codex`.
---

# Repo Intake (Compact)

## Trigger
- User kasih repo URL/path untuk diambil ilmunya.

## Flow
1. Clone ke `.tmp/repo-intake/`.
2. Ekstrak high-signal practices.
3. Map ke skill owner relevan.
4. Hapus clone setelah selesai.

## Intake Guard
- `signal over noise`: ambil hanya pola yang menaikkan kualitas agentic coding.
- `surgical changes`: patch seperlunya, hindari rewrite besar tanpa alasan kuat.
- `source hygiene`: jangan adopsi kode dari sumber leak/proprietary yang meragukan.
- `idempotent`: intake source yang sama tidak boleh menghasilkan duplikasi liar.
- `traceable`: setiap insight harus punya sumber yang jelas.

## Intake Fallback
- Jika `.codex` tidak writable saat intake, simpan report sementara ke `.tmp/repo-intake/reports` lalu sync via tooling (`agentic-cli`/hub) setelah writable.

## Archive Intake Rule
- Jika source berasal dari `.codex/archive/*`, wajib klasifikasikan:
  - `runtime-linked`: terhubung ke runtime aktif.
  - `non-runtime`: arsip referensi, tidak dipakai runtime aktif.
  - `standalone-reference`: modul terpisah yang bisa build sendiri tapi belum integrated.
- Ekstrak hanya kontrak reusable (boundary modul, dependency minimum, verification note).
- Hindari menganggap folder `minimal/standalone` sebagai runtime aktif tanpa bukti wiring.

## Output Wajib
- source analyzed
- extracted insights
- target skills updated
- cleanup status (`deleted|kept`)
