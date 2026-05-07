#!/usr/bin/env bash
set -euo pipefail

cat <<'TXT'
Session Hygiene Checklist (Codex CLI)

1) Before starting a new major phase:
   - Run /status to check context pressure.
   - Confirm only relevant MCP tools are active (/mcp).

2) During execution:
   - Keep tasks in small slices (single clear output per step).
   - Use concise shell output patterns:
     * git status --short
     * ls
     * command | head -n N / tail -n N

3) At phase boundaries:
   - Save a short handoff summary to .codex/memory/MEMORY.md.
   - Run /compact proactively.

4) When changing topic/domain:
   - Use /new for a fresh conversation.
   - Use /fork for alternate approaches.

5) Recovery:
   - Use /resume to continue a previous session intentionally.
TXT
