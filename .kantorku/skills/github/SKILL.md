---
name: github
description: Safe GitHub commit and push workflow with strict no-merge policy. Use when user asks to commit and push current project to GitHub, wants remote to match local project exactly, needs conventional commit messages, and requires explicit checks for nested git repositories that may be left out.
---

# GitHub (Compact)

## Trigger
- Commit/push/PR workflow.

## Flow
1. Scope check (`git status --short`).
2. Commit message jelas.
3. Push branch target.
4. Verifikasi remote state.

## Guardrails
- No destructive git ops tanpa instruksi.
- No merge otomatis.

## Output Wajib
- files changed
- commit hash
- push result
- follow-up (PR/link)
