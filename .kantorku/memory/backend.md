# Topic: backend

## Seed
- symptom: Context transitions can drop backend implementation intent.
- root_cause: Native compact optimizes context fit, not domain memory staging.
- fix_applied: Smart compact pre-layer persists latest-relevant backend state before native compact.
- reusable_rule: Before high-context phase switch, run `bash .codex/tools/agentic-hub.sh compact`.
- confidence: high

## Lesson backend-0b033d1a0e1f
- timestamp: 2026-04-22T07:33:43Z
- lesson_id: backend-0b033d1a0e1f
- symptom: # Context from my IDE setup: ## Open tabs: - openai.yaml: .codex/skills/compact/agents/openai.yaml - POLICY_ENGINE_DETAIL.md: RSVS/docs/audit/root/POLICY_ENGINE_DETAIL.md - README.md: RSVS/README.md - README.md: web_e...
- root_cause: Long thread context can lose critical state during native compaction.
- fix_applied: Smart compact pre-layer writes latest-relevant state and lessons to topic memory files.
- reusable_rule: Before compacting, persist active decisions/open-loops into memory staging files.
- confidence: medium

