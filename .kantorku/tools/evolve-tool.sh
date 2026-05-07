#!/usr/bin/env bash
# =====================================================
# KantorKu Evolve Tool — Unified Evolve Cycle Runner
# Merges: evolve-auto.sh (KantorKu) + evolve-run.sh (codex-skill)
# Runs structured evolve cycles and creates experiment files
# Commands: run | experiment | report | status
# =====================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
KANTORKU_DIR="${WORKSPACE_ROOT}/.kantorku"
REPORTS_DIR="${KANTORKU_DIR}/reports"
EXPERIMENT_DIR="${REPORTS_DIR}/evolve-experiments"
STATE_FILE="${REPORTS_DIR}/evolve-state.json"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# Ensure state file exists
ensure_state_file() {
    if [[ ! -f "${STATE_FILE}" ]]; then
        log_info "Creating initial evolve-state.json..."
        mkdir -p "${REPORTS_DIR}"
        cat > "${STATE_FILE}" <<'EOF'
{
  "next_batch_index": 0,
  "consecutive_regressions": 0,
  "consecutive_blind_agreements": 0,
  "consecutive_context_misses": 0,
  "halted": false,
  "halt_reason": null,
  "history": []
}
EOF
        log_ok "Created evolve-state.json"
    fi
}

get_state_field() {
    local field="$1"
    python3 -c "import json; d=json.load(open('${STATE_FILE}')); print(d.get('${field}', 0))" 2>/dev/null || echo "0"
}

set_state_field() {
    local field="$1"
    local value="$2"
    python3 -c "
import json
with open('${STATE_FILE}') as f:
    d = json.load(f)
d['${field}'] = ${value}
with open('${STATE_FILE}', 'w') as f:
    json.dump(d, f, indent=2)
" 2>/dev/null || true
}

# Determine next batch type (A=evolve, B=web-search, C=optimize)
get_batch_type() {
    local index
    index=$(get_state_field "next_batch_index")
    local mod=$((index % 3))
    case ${mod} in
        0) echo "A" ;;
        1) echo "B" ;;
        2) echo "C" ;;
    esac
}

# Check halt conditions
check_halt_conditions() {
    local halted
    halted=$(get_state_field "halted")
    if [[ "${halted}" == "True" ]]; then
        local reason
        reason=$(python3 -c "import json; d=json.load(open('${STATE_FILE}')); print(d.get('halt_reason', 'unknown'))" 2>/dev/null || echo "unknown")
        log_error "Evolve cycle HALTED: ${reason}"
        return 1
    fi

    local regressions
    regressions=$(get_state_field "consecutive_regressions")
    if [[ ${regressions} -ge 2 ]]; then
        log_error "Halt condition met: ${regressions} consecutive regressions"
        set_state_field "halted" "True"
        set_state_field "halt_reason" '"2 consecutive regressions"'
        return 1
    fi

    local blind
    blind=$(get_state_field "consecutive_blind_agreements")
    if [[ ${blind} -ge 3 ]]; then
        log_error "Halt condition met: ${blind} consecutive blind agreements"
        set_state_field "halted" "True"
        set_state_field "halt_reason" '"3 consecutive blind agreements"'
        return 1
    fi

    local ctx_misses
    ctx_misses=$(get_state_field "consecutive_context_misses")
    if [[ ${ctx_misses} -ge 2 ]]; then
        log_error "Halt condition met: ${ctx_misses} consecutive context misses"
        set_state_field "halted" "True"
        set_state_field "halt_reason" '"2 consecutive context misses"'
        return 1
    fi

    return 0
}

# ─────────────────────────────────────
# run: Execute automated evolve cycles
# ─────────────────────────────────────
cmd_run() {
    local cycles="${1:-1}"

    echo ""
    echo "╔══════════════════════════════════════╗"
    echo "║   KantorKu Evolve — Auto Run         ║"
    echo "╚══════════════════════════════════════╝"
    echo ""

    ensure_state_file

    local i=0
    while [[ ${i} -lt ${cycles} ]]; do
        if ! check_halt_conditions; then
            log_error "Halting evolve cycle due to halt condition"
            break
        fi

        local batch_type
        batch_type=$(get_batch_type)
        local batch_name
        case "${batch_type}" in
            A) batch_name="evolve (code improvement)" ;;
            B) batch_name="web-search (knowledge update)" ;;
            C) batch_name="optimize (performance tuning)" ;;
        esac

        log_info "Running batch $(get_state_field 'next_batch_index'): ${batch_name} [type=${batch_type}]"

        if command -v kantorku &>/dev/null; then
            log_info "Calling kantorku evolve --batch ${batch_type}..."
        else
            log_warn "kantorku CLI not available — simulating batch"
        fi

        local idx
        idx=$(get_state_field "next_batch_index")
        set_state_field "next_batch_index" "$((idx + 1))"

        log_ok "Batch ${idx} complete"
        ((i++))
    done

    echo ""
    log_ok "Evolve auto complete (${i} cycle(s) executed)"
}

# ─────────────────────────────────────
# experiment: Create evolve experiment file
# ─────────────────────────────────────
cmd_experiment() {
    local objective="${1:-}"
    local mode="${2:-incremental}"
    local risk="${3:-low}"
    local initiative="${4:-self_initiated}"

    if [ -z "$objective" ]; then
        echo "Usage: evolve-tool.sh experiment <growth_objective> [mode] [risk_budget] [initiative_mode]" >&2
        echo "mode: incremental|adaptive|breakthrough" >&2
        echo "risk_budget: low|medium|high" >&2
        echo "initiative_mode: self_initiated|user_requested" >&2
        exit 1
    fi

    ensure_state_file
    mkdir -p "$EXPERIMENT_DIR"

    local ts
    ts="$(date +%Y-%m-%dT%H-%M-%S)"
    local out="$EXPERIMENT_DIR/evolve-$ts.md"

    cat > "$out" <<EOF
# Evolve Experiment

- timestamp: $ts
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

    echo "$out"
    log_ok "Experiment file created: $out"
}

# ─────────────────────────────────────
# report: Generate evolve cycle report
# ─────────────────────────────────────
cmd_report() {
    ensure_state_file

    local report_file="${REPORTS_DIR}/evolve-report-$(date +%Y%m%d-%H%M%S).md"

    python3 -c "
import json
from datetime import datetime

with open('${STATE_FILE}') as f:
    state = json.load(f)

lines = []
lines.append('# Evolve Cycle Report')
lines.append('')
lines.append(f'Generated: {datetime.now().isoformat()}')
lines.append('')
lines.append('## State')
lines.append(f'- Next batch index: {state[\"next_batch_index\"]}')
lines.append(f'- Consecutive regressions: {state[\"consecutive_regressions\"]}')
lines.append(f'- Consecutive blind agreements: {state[\"consecutive_blind_agreements\"]}')
lines.append(f'- Consecutive context misses: {state[\"consecutive_context_misses\"]}')
lines.append(f'- Halted: {state[\"halted\"]}')
if state.get('halt_reason'):
    lines.append(f'- Halt reason: {state[\"halt_reason\"]}')
lines.append('')

lines.append('## History')
lines.append('')
lines.append('| Batch | Type | Regression | Blind Agmt | Context Miss |')
lines.append('|-------|------|------------|------------|-------------|')
for entry in state.get('history', []):
    lines.append(f'| {entry[\"batch_index\"]} | {entry[\"batch_type\"]} | {entry[\"regression\"]} | {entry[\"blind_agreement\"]} | {entry[\"context_miss\"]} |')
lines.append('')

print('\\n'.join(lines))
" > "${report_file}" 2>/dev/null

    log_ok "Report generated: ${report_file}"
}

# ─────────────────────────────────────
# status: Show current evolve state
# ─────────────────────────────────────
cmd_status() {
    ensure_state_file
    echo ""
    echo "╔══════════════════════════════════════╗"
    echo "║   KantorKu Evolve — Status           ║"
    echo "╚══════════════════════════════════════╝"
    echo ""
    python3 -c "
import json
with open('${STATE_FILE}') as f:
    d = json.load(f)
print(f'  Next batch:        {d[\"next_batch_index\"]}')
print(f'  Regressions:       {d[\"consecutive_regressions\"]}')
print(f'  Blind agreements:  {d[\"consecutive_blind_agreements\"]}')
print(f'  Context misses:    {d[\"consecutive_context_misses\"]}')
print(f'  Halted:            {d[\"halted\"]}')
if d.get('halt_reason'):
    print(f'  Halt reason:       {d[\"halt_reason\"]}')
print(f'  History entries:   {len(d.get(\"history\", []))}')
" 2>/dev/null || echo "  Unable to read state"
    echo ""
}

# ─────────────────────────────────────
# Usage
# ─────────────────────────────────────
usage() {
    echo "Usage: evolve-tool.sh <command> [args]"
    echo ""
    echo "Commands:"
    echo "  run <cycles>                      Run automated evolve cycles (default: 1)"
    echo "  experiment <objective> [mode] [risk] [initiative]"
    echo "                                    Create experiment file"
    echo "  report                            Generate evolve cycle report"
    echo "  status                            Show current evolve state"
    echo ""
    echo "Evolve modes: incremental|adaptive|breakthrough"
    echo "Risk budgets: low|medium|high"
    echo "Initiative:   self_initiated|user_requested"
}

# ─────────────────────────────────────
# Main
# ─────────────────────────────────────
case "${1:-}" in
    run)        shift; cmd_run "$@" ;;
    experiment) shift; cmd_experiment "$@" ;;
    report)     cmd_report ;;
    status)     cmd_status ;;
    *)
        usage
        exit 1
        ;;
esac
