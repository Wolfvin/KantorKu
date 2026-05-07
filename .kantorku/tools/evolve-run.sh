#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODEX_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPORT_DIR="$CODEX_DIR/reports/evolve-experiments"
TS="$(date +%Y-%m-%dT%H-%M-%S)"
OUT="$REPORT_DIR/evolve-$TS.md"

objective="${1:-}"
mode="${2:-incremental}"
risk="${3:-low}"
initiative="${4:-self_initiated}"

if [ -z "$objective" ]; then
  echo "Usage: bash .codex/tools/evolve-run.sh <growth_objective> [mode] [risk_budget]" >&2
  echo "mode: incremental|adaptive|breakthrough" >&2
  echo "risk_budget: low|medium|high" >&2
  echo "initiative_mode: self_initiated|user_requested" >&2
  exit 1
fi

mkdir -p "$REPORT_DIR"

cat > "$OUT" <<EOF
# Evolve Experiment

- timestamp: $TS
- growth_objective: $objective
- evolution_mode: $mode
- risk_budget: $risk
- initiative_mode: $initiative
- status: pending

## Gate
- evolve_necessity: pending
- reasoning_summary: pending
- token_impact_estimate: pending
- decision: pending

## Hypothesis
- <isi hipotesis evolusi>

## If-Then Commitment
- if <kondisi>, then <aksi operasional>

## Experiment Scope
- <ruang lingkup kecil dan aman>

## Metrics (Eval-First)
- quality_delta: pending
- token_delta: pending
- failure_recurrence: pending

## Result
- experiment_result: pending
- retained_behavior: pending
- discarded_behavior: pending
- next_evolution_trigger: pending
- source_quality_score: pending
- benchmark_status: pending_benchmark
EOF

echo "$OUT"
