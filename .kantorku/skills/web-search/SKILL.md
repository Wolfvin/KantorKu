---
name: web-search
description: Web context acquisition skill for ambiguous or low-context tasks. Use when agents need fresh external context, source links, or quick market/library discovery before planning or implementation.
---

# Web Search (Compact)

## Trigger
- Butuh info eksternal terbaru/terverifikasi.

## Escalation
1. `quick` dulu.
2. naik ke `default` kalau evidence kurang.
3. `deep` hanya untuk high-risk/konflik sumber.

## Source Rule
- Prioritaskan sumber primer/resmi.
- Gunakan jumlah sumber adaptif berbasis risiko (`low|medium|high`).
- Jika sumber konflik, escalate `quick -> default -> deep` sampai cukup konsisten.
- Jika konflik sumber tetap unresolved setelah escalation, force `desired_mode=plan_first` untuk langkah berikutnya.

## Output Wajib
- answer singkat
- evidence relevan (jumlah adaptif, bukan fixed cap)
- link sumber
- uncertainty note jika ada



<!-- EVOLVE_AUTO_BATCH_B_BEGIN -->
## Auto Batch B Signal (Conservative)
- workflow: Reusable workflow patterns extracted from https://github.com/openai/openai-agents-python, https://github.com/langchain-ai/langgraph, https://github.com/Aider-AI/aider
- gating: Decision/failure gates extracted from CI + instruction manifests in intake reports
- verification: Per-batch benchmark-immediately rule + repository verification signals (workflows/tests/manifests)
<!-- EVOLVE_AUTO_BATCH_B_END -->
