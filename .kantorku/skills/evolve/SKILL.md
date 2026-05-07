# Evolve Skill (Unified)

## Purpose
The **Evolve** skill provides a unified improvement workflow that combines structured evolve cycles with arch-engine knowledge extraction. It runs systematic improvement cycles, extracts reusable learning from repo/link/session inputs, stores decisions into `apps/arch-engine` as primary memory, and syncs affected skills.

## Trigger
- User requests improvement, optimization, or benchmarking
- User wants to extract learning from repo/link/session into arch-engine
- User wants pruning of overlap/noise or token efficiency evaluation
- Internal signals: `rate_limit_hits|measurement_drift|failure_recurrence|routing_drop`
- User requests learning extraction to `arch-engine`

## Capabilities

### Legacy KantorKu Actions
1. **Evolve** — Run a structured improvement cycle on target code
2. **Optimize** — Apply specific optimizations (speed, memory, readability)
3. **Tune** — Fine-tune parameters and configurations for better performance
4. **Upgrade** — Upgrade dependencies, patterns, or architecture
5. **Improve** — Apply general quality improvements (type safety, error handling)
6. **Benchmark** — Measure and compare performance metrics

### Arch-Engine Integrated Actions
7. **Extract** — Extract reusable knowledge units from source (workflow|gating|tooling|verification)
8. **Ingest** — Ingest knowledge into arch-engine (classify + reusability gate)
9. **Resolve** — Resolve conflicts (replace|merge_variant|keep_old)
10. **Improve** — Plan improvements with decision cache from arch-engine
11. **Cleanup** — Audit and cleanup stale entries in arch-engine

## Hard Rules

1. **Measure first** — Always benchmark before and after changes
2. **Small batches** — Evolve in small, reviewable batches (A/B/C rotation)
3. **Halt on regression** — Stop after 2 consecutive regressions
4. **No blind agreements** — Require critique alongside approval (3+ consecutive = halt)
5. **Context awareness** — Halt if responses don't match query intent (2+ consecutive context misses)
6. **State persistence** — Track evolve state in `reports/evolve-state.json`
7. **Report generation** — Generate Markdown report after each cycle
8. **Revert capability** — Always be able to revert to previous state
9. **Recommendation first** — Analyze first, patch only for low-risk scope or user-approved
10. **Gate before patch** — Must show `evolve_necessity`, `reasoning_summary`, `token_impact_estimate`, `decision`
11. **Autonomy boundary** — No destructive/high-impact without user approval
12. **Minimal atomic change** — 1 micro-change per cycle
13. **Action-verified arch memory** — No execution, no arch-engine memory
14. **Context alignment gate** — Output must align to user's last question
15. **Safety stance** — If high risk, must use `assistant_position=partial|disagree` + safe option
16. **Cleanup after extract** — Source intake must be deleted after arch-engine lane completes and sync is done

## Necessity Gate

1. Run `think` to determine `desired_mode`:
   - `plan_first` for ambiguous/non-trivial/high-risk
   - `execute_first` for clear/low-risk
2. Run `token-optimizer` for budget and bloat check
3. Classify need: `required|optional|not_needed`

## Execution Flow

1. Intake minimum relevance-first
2. Break into knowledge units: `workflow|gating|tooling|verification`
3. Save knowledge to `arch-engine` first (ingest + classify + gate)
4. Map downstream actions: `enrich|merge|create|create_tool|drop`
5. Set `evolution_hypothesis` + `if_then_commitment`
6. Choose mode: `incremental|adaptive|breakthrough`
7. Execute patch only if mode allows (`execute_first` or user-approved)
8. Verify, record impact, save experiment artifact

## Primary + Sync Lane (Mandatory)

1. **Primary lane (arch-engine)**: All reusable learning must go to `arch-engine` as source-of-truth (ingest/resolve/lifecycle/cleanup audit)
2. **Sync lane (skill/memory)**: Update skill + MEMORY only as downstream from `arch-engine` decisions
3. Cleanup source only after primary lane succeeds AND sync lane completes for affected scope

## Source Lanes

- `memory->arch-engine`: Distill MEMORY into candidate knowledge, ingest to arch-engine, sync delta to skill
- `archive->arch-engine`: Classify `runtime-linked|non-runtime|standalone-reference`, ingest boundary/dependency/verification to arch-engine
- `tmp->arch-engine`: Treat `.tmp` as ephemeral, ingest lesson to arch-engine then cleanup

## Strategy + Stagnation

- Preset: `balanced` (default), `innovate`, `harden`, `repair-only`
- A/B/C batch rotation: `A=evolve`, `B=web-search`, `C=optimize`
- If 2 cycles without positive `quality_delta` → stagnation active
- During stagnation: mode `harden|repair-only`, scope 1 micro-change
- If stagnant after 2 additional interventions → stop and escalate to user

## Verification

- Must measure: `quality_delta`, `token_delta`, `failure_recurrence`
- Must record: `assertiveness_quality`, `blind_agreement_incident`, `context_alignment_quality`
- If regress: rollback to version before experiment

## Evidence Tier

- Tier 1: Primary/official source
- Tier 2: Official maintainer documentation
- Tier 3: Quality secondary analysis
- Tier 4: Complementary community signal
- Source conflict: escalate `quick -> default -> deep`

## Output Schema

```json
{
  "skill": "evolve",
  "action": "evolve|optimize|tune|upgrade|improve|benchmark|extract|ingest|resolve|cleanup",
  "result": {
    "cycle_id": "string",
    "batch_type": "A|B|C",
    "target": "string",
    "evolution_mode": "incremental|adaptive|breakthrough",
    "strategy_preset": "balanced|innovate|harden|repair-only",
    "before": {
      "metric": 0.0,
      "tokens": 0,
      "latency_ms": 0
    },
    "after": {
      "metric": 0.0,
      "tokens": 0,
      "latency_ms": 0
    },
    "delta": 0.0,
    "regression": false,
    "changes": [
      {
        "file": "string",
        "type": "string",
        "description": "string"
      }
    ],
    "halted": false,
    "halt_reason": null,
    "arch_engine_ingestion": [
      {
        "unit": "string",
        "status": "ingested|rejected|pending",
        "decision": "replace|merge_variant|keep_old"
      }
    ],
    "mapping": [
      {
        "unit": "string",
        "skill": "string",
        "action": "enrich|merge|create|create_tool|drop"
      }
    ],
    "quality_impact_summary": "string",
    "initiative_mode": "user_requested|self_initiated",
    "desired_mode": "plan_first|execute_first",
    "assistant_position": "agree|partial|disagree",
    "assertiveness_quality": "pass|fail|pending",
    "blind_agreement_incident": "yes|no"
  },
  "metadata": {
    "tokens_used": 0,
    "latency_ms": 0,
    "provider": "string"
  }
}
```
