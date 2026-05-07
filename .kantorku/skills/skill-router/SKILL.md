---
name: skill-router
description: Unified routing and skill discovery workflow. Use when user prompt is ambiguous/non-specific, when multiple skills may apply, or when user needs to find/install/manage skills. This router can select one or many skills depending on complexity (especially when smart-plan indicates multi-phase work).
---

# Skill Router (Compact)

## Trigger
- Prompt ambigu atau multi-domain.

## Routing Rule
1. Simple task -> 1 skill owner.
2. Complex task -> `think` + `smart-plan` + domain skill.
3. External context gap -> `web-search`.
4. MCP/tool integration -> `mcp-builder`.
5. Context injection (general/frontend/tauri/typescript) -> `inject`.
6. Evolve lintas banyak skill -> `evolve` sebagai owner; learning masuk `arch-engine` dulu, lalu sync ke skill target minimal.

## Canonical Owner Map
- context/frontend/tauri/typescript injection -> `inject`
- mcp integration/build -> `mcp-builder`
- multi-skill evolution + reusable learning ingestion -> `evolve` (primary lane: `arch-engine`)

## Anti-Noise
- Pilih skill minimum yang cukup.
- Hindari activate banyak skill tanpa kebutuhan nyata.
- Jika evolve multi-skill, urutkan patch berdasar dampak tertinggi dulu.

## Output Wajib
- chosen skill(s)
- alasan singkat
- urutan eksekusi
