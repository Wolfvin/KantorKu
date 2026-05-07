---
name: mcp-builder
description: Unified MCP integration and MCP server construction workflow. Use when the user wants to connect a new tool/service via MCP, configure connectors, or build a custom MCP server from API contracts with stable schemas and validation gates. Trigger for prompts like "connect to X", "add MCP", "build MCP server", "integrate tool", and "MCP setup".
---

# MCP Builder (Compact)

## Trigger
- User minta tambah MCP atau build MCP server baru.

## Decision
1. `integrate` jika server sudah ada dan memadai.
2. `build` jika belum ada/kurang cocok.

## Integrate Flow
1. Tambah config minimum.
2. Handshake check.
3. Callable probe.
4. Catat fallback jika gagal.

## Build Flow
1. Contract-first schema.
2. Implement tool minimal.
3. Validate input/output/error.

## Ephemeral Enable Lane
- MCP bukan always-on.
- Enable per fase aktif.
- Disable setelah fase selesai jika tidak dibutuhkan.

## Output Wajib
- `mode`
- `target_service`
- `validation_status`
- `callable_probe_status`
- `failure_reason` (jika ada)
- `next_action`
