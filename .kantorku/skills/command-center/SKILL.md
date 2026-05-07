---
name: command-center
description: Unified command-center workflow for bootstrap, repo intake, MCP connector operations, and plugin notes via .codex/tools/agentic-hub.sh. Use when the user wants one CLI entrypoint for day-to-day agent operations. Trigger for prompts like "single command center", "agentic cli", "agentic hub", "bootstrap + intake", and "manage connectors/plugins".
---

# Command Center (Compact)

## Trigger
- User minta satu entrypoint operasional harian.

## Core Ops
- `doctor`
- `bootstrap`
- `intake`
- `mcp list/add`
- `lifecycle check` (status + stagnation signal)

## Platform Hook Contract
- `bootstrap` harus mempertahankan kompatibilitas wrapper/hook lintas runtime (Codex/Cursor/Claude/OpenClaw) tanpa hard-lock vendor.
- Untuk runtime arg0, gunakan prioritas:
1. `.codex/skills/setup/scripts/codex-arg0-ensure.sh`
2. fallback `.codex/tools/codex-arg0-bootstrap.sh`
- Laporkan jalur yang dipakai (`primary|fallback`) pada output operasional.

## Token Rule
- Gunakan output ringkas, bukan dump penuh.

## Output Wajib
- command yang dijalankan
- status (`pass|fail|blocked`)
- lifecycle_state (`healthy|warning|error|unknown`)
- next step
