#!/usr/bin/env bash
# =====================================================
# KantorKu Benchmark — Portfolio Metrics & Scenarios
# Commands: portfolio | scenario <name> | trend
# =====================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
KANTORKU_DIR="${WORKSPACE_ROOT}/.kantorku"
FRAMEWORK_DIR="${WORKSPACE_ROOT}/framework"
REPORTS_DIR="${KANTORKU_DIR}/reports"
CSV_FILE="${REPORTS_DIR}/benchmark-trend.csv"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# Ensure reports directory exists
mkdir -p "${REPORTS_DIR}"

# ─────────────────────────────────────
# portfolio: Count lines/bytes, estimate tokens
# ─────────────────────────────────────
cmd_portfolio() {
    local target_dir="${1:-${FRAMEWORK_DIR}/kantorku}"

    if [[ ! -d "${target_dir}" ]]; then
        log_error "Target directory not found: ${target_dir}"
        exit 1
    fi

    log_info "Analyzing portfolio: ${target_dir}"

    # Count files by type
    local py_files=0
    local py_lines=0
    local py_bytes=0
    local ts_files=0
    local ts_lines=0
    local ts_bytes=0
    local other_files=0
    local other_lines=0
    local other_bytes=0
    local total_files=0
    local total_lines=0
    local total_bytes=0

    # Python files
    while IFS= read -r -d '' f; do
        ((py_files++))
        local lines bytes
        lines=$(wc -l < "${f}")
        bytes=$(wc -c < "${f}")
        ((py_lines += lines))
        ((py_bytes += bytes))
    done < <(find "${target_dir}" -name "*.py" -print0 2>/dev/null)

    # TypeScript/JavaScript files
    while IFS= read -r -d '' f; do
        ((ts_files++))
        local lines bytes
        lines=$(wc -l < "${f}")
        bytes=$(wc -c < "${f}")
        ((ts_lines += lines))
        ((ts_bytes += bytes))
    done < <(find "${target_dir}" \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" \) -print0 2>/dev/null)

    # Other files
    while IFS= read -r -d '' f; do
        ((other_files++))
        local lines bytes
        lines=$(wc -l < "${f}")
        bytes=$(wc -c < "${f}")
        ((other_lines += lines))
        ((other_bytes += bytes))
    done < <(find "${target_dir}" -type f \
        ! -name "*.py" ! -name "*.ts" ! -name "*.tsx" ! -name "*.js" ! -name "*.jsx" \
        ! -name "*.pyc" ! -name "__pycache__" ! -name ".git" \
        -print0 2>/dev/null)

    total_files=$((py_files + ts_files + other_files))
    total_lines=$((py_lines + ts_lines + other_lines))
    total_bytes=$((py_bytes + ts_bytes + other_bytes))

    # Estimate tokens (~4 chars per token for code)
    local estimated_tokens=$((total_bytes / 4))

    # Generate JSON report
    local json_report="${REPORTS_DIR}/portfolio-$(date +%Y%m%d-%H%M%S).json"
    python3 -c "
import json
report = {
    'timestamp': '$(date -Iseconds 2>/dev/null || date)',
    'target': '${target_dir}',
    'summary': {
        'total_files': ${total_files},
        'total_lines': ${total_lines},
        'total_bytes': ${total_bytes},
        'estimated_tokens': ${estimated_tokens}
    },
    'python': {
        'files': ${py_files},
        'lines': ${py_lines},
        'bytes': ${py_bytes}
    },
    'typescript': {
        'files': ${ts_files},
        'lines': ${ts_lines},
        'bytes': ${ts_bytes}
    },
    'other': {
        'files': ${other_files},
        'lines': ${other_lines},
        'bytes': ${other_bytes}
    }
}
with open('${json_report}', 'w') as f:
    json.dump(report, f, indent=2)
print(json.dumps(report, indent=2))
"
    log_ok "JSON report: ${json_report}"

    # Generate Markdown report
    local md_report="${REPORTS_DIR}/portfolio-$(date +%Y%m%d-%H%M%S).md"
    cat > "${md_report}" <<EOF
# Portfolio Benchmark Report

Generated: $(date -Iseconds 2>/dev/null || date)
Target: ${target_dir}

## Summary

| Metric | Value |
|--------|-------|
| Total Files | ${total_files} |
| Total Lines | ${total_lines} |
| Total Bytes | ${total_bytes} |
| Estimated Tokens | ~${estimated_tokens} |

## By Language

| Language | Files | Lines | Bytes |
|----------|-------|-------|-------|
| Python | ${py_files} | ${py_lines} | ${py_bytes} |
| TypeScript/JS | ${ts_files} | ${ts_lines} | ${ts_bytes} |
| Other | ${other_files} | ${other_lines} | ${other_bytes} |

## Token Estimate

Based on ~4 chars/token for code:
- **Estimated tokens**: ~${estimated_tokens}
- **At 128K context**: ~$(( estimated_tokens / 128000 )) full contexts
- **At GPT-4o pricing ($2.50/1M input)**: ~$(echo "scale=2; ${estimated_tokens} * 2.50 / 1000000" | bc 2>/dev/null || echo "N/A") USD per full read
EOF

    log_ok "Markdown report: ${md_report}"

    # Append to CSV trend file
    if [[ ! -f "${CSV_FILE}" ]]; then
        echo "timestamp,total_files,total_lines,total_bytes,estimated_tokens" > "${CSV_FILE}"
    fi
    echo "$(date +%Y-%m-%dT%H:%M:%S),${total_files},${total_lines},${total_bytes},${estimated_tokens}" >> "${CSV_FILE}"
    log_ok "Trend data appended to ${CSV_FILE}"

    # Print summary
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════${NC}"
    echo -e "${CYAN}  Portfolio Summary${NC}"
    echo -e "${CYAN}═══════════════════════════════════════${NC}"
    echo -e "  Files:   ${GREEN}${total_files}${NC}"
    echo -e "  Lines:   ${GREEN}${total_lines}${NC}"
    echo -e "  Bytes:   ${GREEN}${total_bytes}${NC}"
    echo -e "  Tokens:  ${GREEN}~${estimated_tokens}${NC}"
    echo -e "${CYAN}═══════════════════════════════════════${NC}"
    echo ""
}

# ─────────────────────────────────────
# scenario: Measure token usage for specific scenarios
# ─────────────────────────────────────
cmd_scenario() {
    local scenario_name="${1:-}"
    if [[ -z "${scenario_name}" ]]; then
        echo "Usage: benchmark.sh scenario <name>"
        echo ""
        echo "Available scenarios:"
        echo "  simple-task    — Simple single-worker task"
        echo "  moderate-task  — Multi-worker coordinated task"
        echo "  complex-task   — Full team briefing + execution"
        echo "  evolve-cycle   — One evolve cycle (A/B/C)"
        echo "  library-search — Semantic search across library"
        echo ""
        exit 1
    fi

    log_info "Running scenario: ${scenario_name}"

    # Define scenario parameters
    local estimated_input_tokens=0
    local estimated_output_tokens=0
    local workers_involved=""
    local description=""

    case "${scenario_name}" in
        simple-task)
            estimated_input_tokens=500
            estimated_output_tokens=1000
            workers_involved="intake,coder_backend,narrator"
            description="Simple single-worker task (intake → code → narrate)"
            ;;
        moderate-task)
            estimated_input_tokens=2000
            estimated_output_tokens=3000
            workers_involved="intake,coder_frontend,coder_backend,verifier_engineer,narrator"
            description="Multi-worker coordinated task (5 workers)"
            ;;
        complex-task)
            estimated_input_tokens=5000
            estimated_output_tokens=8000
            workers_involved="intake,briefing_room,coder_frontend,coder_backend,coder_wiring,verifier_designer,verifier_engineer,narrator"
            description="Full team briefing + execution (8 workers)"
            ;;
        evolve-cycle)
            estimated_input_tokens=3000
            estimated_output_tokens=2000
            workers_involved="auditor,debugger,coder_backend"
            description="One evolve cycle (audit → improve → verify)"
            ;;
        library-search)
            estimated_input_tokens=1000
            estimated_output_tokens=500
            workers_involved="scout,summarizer"
            description="Semantic search across library"
            ;;
        *)
            log_error "Unknown scenario: ${scenario_name}"
            exit 1
            ;;
    esac

    local total_tokens=$((estimated_input_tokens + estimated_output_tokens))

    # Cost estimates (approximate, based on model mix)
    local cost_low cost_high
    cost_low=$(echo "scale=4; ${total_tokens} * 0.15 / 1000000" | bc 2>/dev/null || echo "N/A")
    cost_high=$(echo "scale=4; ${total_tokens} * 3.0 / 1000000" | bc 2>/dev/null || echo "N/A")

    # Generate JSON report
    local json_report="${REPORTS_DIR}/scenario-${scenario_name}-$(date +%Y%m%d-%H%M%S).json"
    python3 -c "
import json
report = {
    'timestamp': '$(date -Iseconds 2>/dev/null || date)',
    'scenario': '${scenario_name}',
    'description': '''${description}''',
    'workers_involved': '${workers_involved}'.split(','),
    'estimated_input_tokens': ${estimated_input_tokens},
    'estimated_output_tokens': ${estimated_output_tokens},
    'total_tokens': ${total_tokens},
    'cost_estimate': {
        'low_usd': '${cost_low}',
        'high_usd': '${cost_high}'
    }
}
with open('${json_report}', 'w') as f:
    json.dump(report, f, indent=2)
print(json.dumps(report, indent=2))
"
    log_ok "Scenario report: ${json_report}"

    # Print summary
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════${NC}"
    echo -e "${CYAN}  Scenario: ${scenario_name}${NC}"
    echo -e "${CYAN}═══════════════════════════════════════${NC}"
    echo -e "  ${description}"
    echo -e "  Workers:  ${GREEN}${workers_involved}${NC}"
    echo -e "  Input:    ${GREEN}~${estimated_input_tokens} tokens${NC}"
    echo -e "  Output:   ${GREEN}~${estimated_output_tokens} tokens${NC}"
    echo -e "  Total:    ${GREEN}~${total_tokens} tokens${NC}"
    echo -e "  Cost:     ${GREEN}\$${cost_low} — \$${cost_high}${NC}"
    echo -e "${CYAN}═══════════════════════════════════════${NC}"
    echo ""
}

# ─────────────────────────────────────
# trend: Show historical benchmark data
# ─────────────────────────────────────
cmd_trend() {
    if [[ ! -f "${CSV_FILE}" ]]; then
        log_warn "No trend data found. Run 'benchmark.sh portfolio' first."
        exit 0
    fi

    echo ""
    echo -e "${CYAN}═══════════════════════════════════════${NC}"
    echo -e "${CYAN}  Benchmark Trend Data${NC}"
    echo -e "${CYAN}═══════════════════════════════════════${NC}"
    echo ""
    cat "${CSV_FILE}"
    echo ""
}

# ─────────────────────────────────────
# Usage
# ─────────────────────────────────────
usage() {
    echo "Usage: benchmark.sh <command> [args]"
    echo ""
    echo "Commands:"
    echo "  portfolio [dir]       Count lines/bytes, estimate tokens"
    echo "  scenario <name>       Measure token usage for a scenario"
    echo "  trend                 Show historical benchmark data"
    echo ""
    echo "Scenarios: simple-task, moderate-task, complex-task, evolve-cycle, library-search"
    echo ""
}

# ─────────────────────────────────────
# Main
# ─────────────────────────────────────
case "${1:-}" in
    portfolio) cmd_portfolio "${2:-}" ;;
    scenario)  cmd_scenario "${2:-}" ;;
    trend)     cmd_trend ;;
    *)
        usage
        exit 1
        ;;
esac
