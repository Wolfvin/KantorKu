#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="$ROOT/reports"
mkdir -p "$REPORT_DIR"

SESSION_KIND="${1:-portfolio}"
REQUEST_COUNT="${2:-}"
AVG_LATENCY_MS="${3:-}"
RATE_LIMIT_HITS="${4:-}"

TS="$(date +%Y-%m-%dT%H-%M-%S-%3N)"
JSON_OUT="$REPORT_DIR/token-benchmark-${TS}.json"
MD_OUT="$REPORT_DIR/token-benchmark-${TS}.md"
CSV_OUT="$REPORT_DIR/token-benchmark-trend.csv"

LINE_TOTAL=$(find "$ROOT/skills" -mindepth 2 -maxdepth 2 -name SKILL.md -print0 | xargs -0 wc -l | awk 'END{print $1}')
BYTE_TOTAL=$(find "$ROOT/skills" -mindepth 2 -maxdepth 2 -name SKILL.md -print0 | xargs -0 wc -c | awk 'END{print $1}')
TOKEN_EST=$(( BYTE_TOTAL / 4 ))

s1_skills=(skill-router think smart-plan debug-n-check setup checkpoint)
s2_skills=(skill-router think setup mcp-builder token-optimizer checkpoint)

sum_bytes_for() {
  local total=0
  for skill in "$@"; do
    local p="$ROOT/skills/$skill/SKILL.md"
    if [[ -f "$p" ]]; then
      local b
      b=$(wc -c < "$p")
      total=$((total + b))
    fi
  done
  echo "$total"
}

S1_BYTES=$(sum_bytes_for "${s1_skills[@]}")
S2_BYTES=$(sum_bytes_for "${s2_skills[@]}")
S1_TOKENS=$(( S1_BYTES / 4 ))
S2_TOKENS=$(( S2_BYTES / 4 ))

cat > "$JSON_OUT" <<JSON
{
  "timestamp": "$TS",
  "session_kind": "$SESSION_KIND",
  "portfolio": {
    "skill_count": 18,
    "lines": $LINE_TOTAL,
    "bytes": $BYTE_TOTAL,
    "est_tokens": $TOKEN_EST
  },
  "scenario_bugfix_ui": {
    "bytes": $S1_BYTES,
    "est_tokens": $S1_TOKENS
  },
  "scenario_mcp_integration": {
    "bytes": $S2_BYTES,
    "est_tokens": $S2_TOKENS
  },
  "runtime_metrics": {
    "request_count": "${REQUEST_COUNT:-na}",
    "avg_latency_ms": "${AVG_LATENCY_MS:-na}",
    "rate_limit_hits": "${RATE_LIMIT_HITS:-na}"
  }
}
JSON

cat > "$MD_OUT" <<MD
# Token Benchmark - $TS

- session_kind: $SESSION_KIND
- portfolio_lines: $LINE_TOTAL
- portfolio_bytes: $BYTE_TOTAL
- portfolio_est_tokens: $TOKEN_EST
- scenario_bugfix_ui_est_tokens: $S1_TOKENS
- scenario_mcp_integration_est_tokens: $S2_TOKENS
- request_count: ${REQUEST_COUNT:-na}
- avg_latency_ms: ${AVG_LATENCY_MS:-na}
- rate_limit_hits: ${RATE_LIMIT_HITS:-na}

## Notes
- Token estimate uses \

tokens ~= bytes / 4\
.
- Fill runtime metrics when running after real sessions.
MD

if [[ ! -f "$CSV_OUT" ]]; then
  echo "timestamp,session_kind,portfolio_lines,portfolio_bytes,portfolio_est_tokens,bugfix_ui_est_tokens,mcp_integration_est_tokens,request_count,avg_latency_ms,rate_limit_hits" > "$CSV_OUT"
fi

echo "$TS,$SESSION_KIND,$LINE_TOTAL,$BYTE_TOTAL,$TOKEN_EST,$S1_TOKENS,$S2_TOKENS,${REQUEST_COUNT:-na},${AVG_LATENCY_MS:-na},${RATE_LIMIT_HITS:-na}" >> "$CSV_OUT"

cp -f "$JSON_OUT" "$REPORT_DIR/token-benchmark-latest.json"
cp -f "$MD_OUT" "$REPORT_DIR/token-benchmark-latest.md"

echo "[token-benchmark] wrote: $JSON_OUT"
echo "[token-benchmark] wrote: $MD_OUT"
echo "[token-benchmark] updated: $CSV_OUT"
