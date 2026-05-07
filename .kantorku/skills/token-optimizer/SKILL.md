---
name: token-optimizer
description: Optimize context usage and compaction resilience for long Codex CLI sessions. Use when context is bloated, compaction quality drops, or token costs must be reduced without sacrificing answer quality.
---

# Token Optimizer (Compact)

## Trigger
- Rate limit cepat habis.
- Context bloat / quality drop.

## Session Audit
1. ukur token pressure (prompt, memory, tools, skill overlap)
2. tetapkan budget (`tight|balanced|expanded`)
3. ambil intervensi minimum

## MCP Footprint
1. default `zero-enabled baseline`
2. enable MCP on-demand saja
3. verify callable minimal
4. disable lagi setelah fase selesai

## Compaction Safety
- simpan snapshot sebelum compact
- audit drift sesudah compact
- recovery via checkpoint jika drift tinggi
- jika `measurement_drift` belum terselesaikan, force `desired_mode=plan_first` untuk cycle berikutnya

## Output Wajib
- `selected_mode`
- `baseline_summary`
- `intervention_plan`
- `compaction_quality`
- `benchmark_status`
- `next_step`

<!-- EVOLVE_AUTO_BATCH_C_BEGIN -->
## Auto Batch C Signal (Conservative)
- workflow: Reusable workflow patterns extracted from https://github.com/AI-App/PromptFoo, https://github.com/EleutherAI/lm-evaluation-harness, https://github.com/continuedev/continue, https://github.com/anthropics/claude-plugins-official
- gating: Decision/failure gates extracted from CI + instruction manifests in intake reports
- verification: Per-batch benchmark-immediately rule + repository verification signals (workflows/tests/manifests)
<!-- EVOLVE_AUTO_BATCH_C_END -->
