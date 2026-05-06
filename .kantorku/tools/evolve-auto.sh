#!/usr/bin/env bash
# =====================================================
# KantorKu Evolve Auto — Automated Evolve Cycle Runner
# Runs structured evolve cycles with halt conditions
# =====================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
KANTORKU_DIR="${WORKSPACE_ROOT}/.kantorku"
REPORTS_DIR="${KANTORKU_DIR}/reports"
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

# ─────────────────────────────────────
# Read current state
# ─────────────────────────────────────
read_state() {
    if command -v python3 &>/dev/null; then
        python3 -c "import json; d=json.load(open('${STATE_FILE}')); print(json.dumps(d))"
    else
        cat "${STATE_FILE}"
    fi
}

get_state_field() {
    local field="$1"
    python3 -c "import json; d=json.load(open('${STATE_FILE}')); print(d.get('${field}', 0))"
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
"
}

# ─────────────────────────────────────
# Determine next batch type
# ─────────────────────────────────────
# A = evolve, B = web-search, C = optimize
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

# ─────────────────────────────────────
# Check halt conditions
# ─────────────────────────────────────
check_halt_conditions() {
    local halted
    halted=$(get_state_field "halted")
    if [[ "${halted}" == "True" ]]; then
        local reason
        reason=$(python3 -c "import json; d=json.load(open('${STATE_FILE}')); print(d.get('halt_reason', 'unknown'))")
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
# Run a single evolve batch
# ─────────────────────────────────────
run_batch() {
    local batch_type="$1"
    local batch_name

    case "${batch_type}" in
        A) batch_name="evolve (code improvement)" ;;
        B) batch_name="web-search (knowledge update)" ;;
        C) batch_name="optimize (performance tuning)" ;;
    esac

    log_info "Running batch $(get_state_field 'next_batch_index'): ${batch_name} [type=${batch_type}]"

    # Collect metrics (placeholder — integrate with actual evolve logic)
    local start_time
    start_time=$(date +%s)
    local tokens_used=0
    local delta=0.0
    local is_regression=false
    local is_blind_agreement=false
    local is_context_miss=false

    # Simulate evolve cycle (in production, this calls kantorku evolve)
    if command -v kantorku &>/dev/null; then
        log_info "Calling kantorku evolve --batch ${batch_type}..."
        # kantorku evolve --batch "${batch_type}" --report json 2>/dev/null || true
        log_info "Evolve command would be executed here"
    else
        log_warn "kantorku CLI not available — simulating batch"
    fi

    local end_time
    end_time=$(date +%s)
    local duration=$((end_time - start_time))

    # Update state based on results
    if [[ "${is_regression}" == "true" ]]; then
        local reg
        reg=$(get_state_field "consecutive_regressions")
        set_state_field "consecutive_regressions" "$((reg + 1))"
    else
        set_state_field "consecutive_regressions" "0"
    fi

    if [[ "${is_blind_agreement}" == "true" ]]; then
        local blind
        blind=$(get_state_field "consecutive_blind_agreements")
        set_state_field "consecutive_blind_agreements" "$((blind + 1))"
    else
        set_state_field "consecutive_blind_agreements" "0"
    fi

    if [[ "${is_context_miss}" == "true" ]]; then
        local ctx
        ctx=$(get_state_field "consecutive_context_misses")
        set_state_field "consecutive_context_misses" "$((ctx + 1))"
    else
        set_state_field "consecutive_context_misses" "0"
    fi

    # Increment batch index
    local idx
    idx=$(get_state_field "next_batch_index")
    set_state_field "next_batch_index" "$((idx + 1))"

    # Add to history
    python3 -c "
import json
from datetime import datetime
with open('${STATE_FILE}') as f:
    d = json.load(f)
d['history'].append({
    'batch_index': ${idx},
    'batch_type': '${batch_type}',
    'timestamp': datetime.now().isoformat(),
    'duration_seconds': ${duration},
    'regression': ${is_regression},
    'blind_agreement': ${is_blind_agreement},
    'context_miss': ${is_context_miss}
})
with open('${STATE_FILE}', 'w') as f:
    json.dump(d, f, indent=2)
"

    log_ok "Batch ${idx} complete (${duration}s)"
}

# ─────────────────────────────────────
# Generate report
# ─────────────────────────────────────
generate_report() {
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
lines.append('| Batch | Type | Duration | Regression | Blind Agmt | Context Miss |')
lines.append('|-------|------|----------|------------|------------|-------------|')
for entry in state.get('history', []):
    lines.append(f'| {entry[\"batch_index\"]} | {entry[\"batch_type\"]} | {entry[\"duration_seconds\"]}s | {entry[\"regression\"]} | {entry[\"blind_agreement\"]} | {entry[\"context_miss\"]} |')
lines.append('')

print('\n'.join(lines))
" > "${report_file}"

    log_ok "Report generated: ${report_file}"
}

# ─────────────────────────────────────
# Main
# ─────────────────────────────────────
main() {
    local cycles="${1:-1}"

    echo ""
    echo "╔══════════════════════════════════════╗"
    echo "║   KantorKu Evolve Auto               ║"
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
        run_batch "${batch_type}"

        ((i++))
    done

    generate_report

    echo ""
    log_ok "Evolve auto complete (${i} cycle(s) executed)"
}

main "$@"
