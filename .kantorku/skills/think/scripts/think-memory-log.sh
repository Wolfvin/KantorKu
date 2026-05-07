#!/usr/bin/env bash
set -euo pipefail

MEMORY_FILE=".codex/memory/MEMORY.md"

pattern=""
gap=""
query=""
evidence=""
decision=""
failure=""
rule=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --pattern) pattern="${2:-}"; shift 2 ;;
    --gap) gap="${2:-}"; shift 2 ;;
    --query) query="${2:-}"; shift 2 ;;
    --evidence) evidence="${2:-}"; shift 2 ;;
    --decision) decision="${2:-}"; shift 2 ;;
    --failure) failure="${2:-}"; shift 2 ;;
    --rule) rule="${2:-}"; shift 2 ;;
    *)
      echo "Unknown arg: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "$pattern" || -z "$evidence" || -z "$decision" || -z "$rule" ]]; then
  echo "Required: --pattern --evidence --decision --rule" >&2
  exit 1
fi

if [[ ! -f "$MEMORY_FILE" ]]; then
  echo "Memory file not found: $MEMORY_FILE" >&2
  exit 1
fi

timestamp="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

if rg -q '^think_lessons:' "$MEMORY_FILE"; then
  cat >> "$MEMORY_FILE" <<EOF
- timestamp: $timestamp
  task_pattern: $pattern
  context_gap_detected: ${gap:-none}
  search_query_used: ${query:-none}
  evidence_level: $evidence
  decision_taken: $decision
  failure_mode: ${failure:-none}
  reusable_rule: $rule
EOF
else
  cat >> "$MEMORY_FILE" <<EOF

think_lessons:
- timestamp: $timestamp
  task_pattern: $pattern
  context_gap_detected: ${gap:-none}
  search_query_used: ${query:-none}
  evidence_level: $evidence
  decision_taken: $decision
  failure_mode: ${failure:-none}
  reusable_rule: $rule
EOF
fi

echo "Appended think lesson to $MEMORY_FILE"
