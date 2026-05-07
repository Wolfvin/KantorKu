---
name: command-creator
description: Create or update workspace command entrypoints in `.codex/tools/agentic-hub.sh` and `.codex/tools/agentic-hub.ps1` with cross-platform parity, usage docs, and verification checks. Use when user asks to add a new command, alias, or command workflow in Codex hub.
---

# Command Creator

## Trigger
- User asks to add a new command in the Codex hub.
- User asks to expose an existing script via `agentic-hub`.
- User asks for command parity between bash and PowerShell.

## Contract
1. Define command name, purpose, and input arguments.
2. Wire command in bash hub (`.codex/tools/agentic-hub.sh`) with:
- `usage` entry
- command function (if needed)
- `case` route
3. Wire same command in PowerShell hub (`.codex/tools/agentic-hub.ps1`) with:
- `Show-Usage` entry
- function/handler
- `switch` route
4. Update operational docs that mention command workflow (for example `.codex/README.md`, `.codex/AGENTS.md`, `.codex/chat.md`) only when behavior changes.
5. Run verification:
- syntax checks for edited shell scripts
- command help/usage visibility check
- smoke-run command if non-destructive

## Design Rules
- Keep behavior deterministic and side-effect boundaries explicit.
- Preserve backward compatibility unless user asks for breaking change.
- Never remove existing commands without explicit request.
- For destructive or high-impact commands, require explicit guard/warning output.
- Prefer shared script execution (`.codex/tools/*.sh/.ps1`) over duplicated logic in hub router.

## Output Wajib
- `command_name`
- `purpose`
- `entrypoints_updated` (bash|powershell|docs)
- `verification_evidence`
- `risk_notes`
