---
name: compact
description: Smart compact pre-layer for context preservation before native compact. Use to extract latest-relevant state, write reusable lessons into topic memory files, and emit compact handoff.
---

# Compact (Smart v1)

## Trigger
- User asks for compact with context-preservation intent.
- Phase transition before high-risk or high-context work.

## Contract
1. Collect active context snapshot from latest session evidence.
2. Distill reusable lessons in blameless format.
3. Update memory index + topic files under `.codex/memory/`.
4. Emit compact handoff summary for next phase.

## Output Schema
- `task_state`
- `open_loops`
- `decisions`
- `next_actions`
- `lessons_written`
- `handoff_summary`

## Memory Staging Layout
- `.codex/memory/memory.md` (index)
- `.codex/memory/backend.md` (backend seed topic)
- `.codex/memory/<topic>.md` (lazy-created topic files)

## Lesson Format
- `symptom`
- `root_cause`
- `fix_applied`
- `reusable_rule`
- `confidence`
