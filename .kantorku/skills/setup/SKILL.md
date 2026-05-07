---
name: setup
description: Unified setup and operational SOP workflow. Use when initializing project environment, preparing runtime/tooling, or building operational PowerShell SOP runbooks for run/stop/check/debug in a context-aware way.
---

# Setup (Compact)

## Trigger
- Setup environment baru / bootstrap.
- User minta SOP run/stop/check/debug.
- User invoke `$setup` untuk menyederhanakan command panjang menjadi interaktif CLI menu (contoh: `cargo run --...` jadi pilih nomor/menu prompt).

## Bootstrap Flow
1. Cek runtime/deps/env var.
2. Cek entrypoint run/test.
3. Cek tools penting (yang dipakai fase aktif).
4. Jalankan `scripts/codex-arg0-ensure.sh` untuk re-apply wrapper defaults (`gpt-5.3-codex` + `medium`) di runtime arg0.
5. Laporkan status siap jalan.

## Hook/Wrapper Contract
- Wajib cek ketersediaan script utama: `.codex/skills/setup/scripts/codex-arg0-ensure.sh`.
- Jika script utama tidak ada, jalankan fallback: `.codex/tools/codex-arg0-bootstrap.sh`.
- Tujuan contract: satu command bootstrap tetap valid walau path runtime wrapper berubah.

## Interactive CLI Builder Mode
1. Identifikasi command panjang yang sering dipakai berulang.
2. Rancang menu interaktif CLI (nomor/prompt) agar user cukup menjalankan satu command utama.
3. Map setiap opsi menu ke command asli + parameter penting (dengan default aman).
4. Tambahkan loop kembali ke menu + exit path yang jelas.
5. Pastikan `cargo run`/entrypoint utama bisa langsung membuka menu saat diminta user.
6. Verifikasi cepat minimal satu jalur menu berjalan end-to-end.

## Local Tooling Pattern
- Untuk tooling folder aktif (mis. `my_tools`), pertahankan pattern:
  - pre-build cleanup script (hapus generated output lama),
  - typed build/check (`tsc`),
  - helper launcher script untuk debug runtime (contoh Chrome remote debugging).
- Saat evolve dari tooling aktif, ekstrak lesson reusable ke MEMORY/skill dan jangan hapus root tooling kecuali diminta user.

## MCP Manual Mode (Default)
1. `MCP off by default`.
2. Enable hanya saat dibutuhkan.
3. Verify callable tool minimal 1.
4. Disable lagi setelah fase selesai.

## Output Schema
- `environment_status`
- `preflight_checks`
- `runtime_state`
- `arg0_wrapper_state`
- `mcp_mode` (`manual_on_demand`)
- `mcp_active_set`
- `interactive_cli_state` (`created|updated|not_requested`)
- `status` (`pass|fail|blocked`)
- `next_step`
