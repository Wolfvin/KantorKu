# Evolve Skill

## Purpose
The **Evolve** skill provides improvement, optimization, and benchmarking capabilities. It runs structured evolve cycles to systematically improve code quality, performance, and architecture over time.

## Capabilities

1. **Evolve** — Run a structured improvement cycle on target code
2. **Optimize** — Apply specific optimizations (speed, memory, readability)
3. **Tune** — Fine-tune parameters and configurations for better performance
4. **Upgrade** — Upgrade dependencies, patterns, or architecture
5. **Improve** — Apply general quality improvements (type safety, error handling)
6. **Benchmark** — Measure and compare performance metrics

## Output Schema

```json
{
  "skill": "evolve",
  "action": "evolve|optimize|tune|upgrade|improve|benchmark",
  "result": {
    "cycle_id": "string",
    "batch_type": "A|B|C",
    "target": "string",
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
    "halt_reason": null
  },
  "metadata": {
    "tokens_used": 0,
    "latency_ms": 0,
    "provider": "string"
  }
}
```

## Key Rules

1. **Measure first** — Always benchmark before and after changes
2. **Small batches** — Evolve in small, reviewable batches (A/B/C rotation)
3. **Halt on regression** — Stop after 2 consecutive regressions
4. **No blind agreements** — Require critique alongside approval
5. **Context awareness** — Halt if responses don't match query intent
6. **State persistence** — Track evolve state in `reports/evolve-state.json`
7. **Report generation** — Generate Markdown report after each cycle
8. **Revert capability** — Always be able to revert to previous state
