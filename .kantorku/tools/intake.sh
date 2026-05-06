#!/usr/bin/env bash
# =====================================================
# KantorKu Intake Pipeline — Repository Analysis
# Commands: intake <repo-url...> | sync <source-dir>
# Options: --keep  --name <slug>
# =====================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
KANTORKU_DIR="${WORKSPACE_ROOT}/.kantorku"
REPORTS_DIR="${KANTORKU_DIR}/reports"
INTAKE_DIR="${REPORTS_DIR}/intake"
TEMP_DIR="/tmp/kantorku-intake"

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

# ─────────────────────────────────────
# Parse options
# ─────────────────────────────────────
KEEP_REPOS=false
PROJECT_NAME=""

parse_opts() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --keep)   KEEP_REPOS=true; shift ;;
            --name)   PROJECT_NAME="$2"; shift 2 ;;
            *)        break ;;
        esac
    done
    REPO_URLS=("$@")
}

# ─────────────────────────────────────
# Clone a repository
# ─────────────────────────────────────
clone_repo() {
    local url="$1"
    local target="$2"

    log_info "Cloning ${url}..."

    if command -v git &>/dev/null; then
        git clone --depth 1 "${url}" "${target}" 2>/dev/null
        if [[ $? -eq 0 ]]; then
            log_ok "Cloned to ${target}"
        else
            log_error "Failed to clone ${url}"
            return 1
        fi
    else
        log_error "git not found — cannot clone repositories"
        return 1
    fi
}

# ─────────────────────────────────────
# Scan a repository
# ─────────────────────────────────────
scan_repo() {
    local repo_dir="$1"
    local repo_name
    repo_name="$(basename "${repo_dir}")"

    log_info "Scanning ${repo_name}..."

    local scan_result="${INTAKE_DIR}/${repo_name}-scan.json"

    # Collect repository statistics
    local total_files=0
    local total_lines=0
    local total_bytes=0
    local languages=""

    if [[ -d "${repo_dir}" ]]; then
        total_files=$(find "${repo_dir}" -type f \
            ! -path "*/.git/*" ! -path "*/node_modules/*" ! -path "*/__pycache__/*" \
            ! -path "*/.venv/*" ! -path "*/venv/*" ! -path "*/dist/*" ! -path "*/build/*" \
            2>/dev/null | wc -l || echo 0)
        total_lines=$(find "${repo_dir}" -type f \
            ! -path "*/.git/*" ! -path "*/node_modules/*" ! -path "*/__pycache__/*" \
            ! -path "*/.venv/*" ! -path "*/venv/*" ! -path "*/dist/*" ! -path "*/build/*" \
            -exec cat {} + 2>/dev/null | wc -l || echo 0)
        total_bytes=$(find "${repo_dir}" -type f \
            ! -path "*/.git/*" ! -path "*/node_modules/*" ! -path "*/__pycache__/*" \
            ! -path "*/.venv/*" ! -path "*/venv/*" ! -path "*/dist/*" ! -path "*/build/*" \
            -exec cat {} + 2>/dev/null | wc -c || echo 0)

        # Detect languages
        languages=$(find "${repo_dir}" -type f \
            ! -path "*/.git/*" ! -path "*/node_modules/*" ! -path "*/__pycache__/*" \
            2>/dev/null | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -5 | tr '\n' ',' | sed 's/,$//')
    fi

    # Generate scan report
    python3 -c "
import json
report = {
    'repository': '${repo_name}',
    'path': '${repo_dir}',
    'statistics': {
        'total_files': ${total_files},
        'total_lines': ${total_lines},
        'total_bytes': ${total_bytes},
        'estimated_tokens': ${total_bytes} // 4
    },
    'languages': '${languages}',
    'insights': []
}
with open('${scan_result}', 'w') as f:
    json.dump(report, f, indent=2)
print(json.dumps(report, indent=2))
" 2>/dev/null || {
        # Fallback without python
        echo "{\"repository\":\"${repo_name}\",\"total_files\":${total_files},\"total_lines\":${total_lines}}" > "${scan_result}"
    }

    log_ok "Scan complete: ${total_files} files, ${total_lines} lines"
}

# ─────────────────────────────────────
# Extract insights from a scanned repo
# ─────────────────────────────────────
extract_insights() {
    local repo_dir="$1"
    local repo_name
    repo_name="$(basename "${repo_dir}")"

    log_info "Extracting insights from ${repo_name}..."

    local insights_file="${INTAKE_DIR}/${repo_name}-insights.md"

    cat > "${insights_file}" <<EOF
# Intake Insights: ${repo_name}

Generated: $(date -Iseconds 2>/dev/null || date)

## Repository Overview

EOF

    # Check for common project files
    [[ -f "${repo_dir}/README.md" ]] && echo "- Has README.md" >> "${insights_file}"
    [[ -f "${repo_dir}/pyproject.toml" ]] && echo "- Python project (pyproject.toml)" >> "${insights_file}"
    [[ -f "${repo_dir}/package.json" ]] && echo "- Node.js project (package.json)" >> "${insights_file}"
    [[ -f "${repo_dir}/Cargo.toml" ]] && echo "- Rust project (Cargo.toml)" >> "${insights_file}"
    [[ -f "${repo_dir}/Dockerfile" ]] && echo "- Has Dockerfile" >> "${insights_file}"
    [[ -f "${repo_dir}/docker-compose.yml" ]] && echo "- Has docker-compose.yml" >> "${insights_file}"
    [[ -f "${repo_dir}/.github/workflows" ]] && echo "- Has CI/CD (.github/workflows)" >> "${insights_file}"

    # Extract dependency info
    echo "" >> "${insights_file}"
    echo "## Dependencies" >> "${insights_file}"
    echo "" >> "${insights_file}"

    if [[ -f "${repo_dir}/pyproject.toml" ]]; then
        echo "### Python (pyproject.toml)" >> "${insights_file}"
        echo '```toml' >> "${insights_file}"
        grep -A 50 "dependencies" "${repo_dir}/pyproject.toml" 2>/dev/null | head -30 >> "${insights_file}"
        echo '```' >> "${insights_file}"
    fi

    if [[ -f "${repo_dir}/package.json" ]]; then
        echo "### Node.js (package.json)" >> "${insights_file}"
        echo '```json' >> "${insights_file}"
        python3 -c "
import json
with open('${repo_dir}/package.json') as f:
    pkg = json.load(f)
deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
for k, v in deps.items():
    print(f'  {k}: {v}')
" 2>/dev/null >> "${insights_file}"
        echo '```' >> "${insights_file}"
    fi

    # Architecture notes
    echo "" >> "${insights_file}"
    echo "## Architecture Notes" >> "${insights_file}"
    echo "" >> "${insights_file}"

    # Top-level directories
    echo "### Directory Structure" >> "${insights_file}"
    echo '```' >> "${insights_file}"
    ls -1 "${repo_dir}" 2>/dev/null | head -20 >> "${insights_file}"
    echo '```' >> "${insights_file}"

    log_ok "Insights extracted: ${insights_file}"
}

# ─────────────────────────────────────
# Generate combined report
# ─────────────────────────────────────
generate_report() {
    local report_name="${PROJECT_NAME:-intake-$(date +%Y%m%d-%H%M%S)}"
    local report_file="${INTAKE_DIR}/${report_name}-report.md"

    cat > "${report_file}" <<EOF
# Intake Report: ${report_name}

Generated: $(date -Iseconds 2>/dev/null || date)
Sources: ${#REPO_URLS[@]} repositories

## Summary

EOF

    # Aggregate scan results
    for scan_file in "${INTAKE_DIR}"/*-scan.json; do
        if [[ -f "${scan_file}" ]]; then
            local repo_name
            repo_name=$(python3 -c "import json; print(json.load(open('${scan_file}'))['repository'])" 2>/dev/null || echo "unknown")
            local total_files total_lines
            total_files=$(python3 -c "import json; print(json.load(open('${scan_file}'))['statistics']['total_files'])" 2>/dev/null || echo "?")
            total_lines=$(python3 -c "import json; print(json.load(open('${scan_file}'))['statistics']['total_lines'])" 2>/dev/null || echo "?")
            echo "- **${repo_name}**: ${total_files} files, ${total_lines} lines" >> "${report_file}"
        fi
    done

    # Append individual insights
    for insights_file in "${INTAKE_DIR}"/*-insights.md; do
        if [[ -f "${insights_file}" ]]; then
            echo "" >> "${report_file}"
            cat "${insights_file}" >> "${report_file}"
        fi
    done

    log_ok "Combined report: ${report_file}"

    # Print summary
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════${NC}"
    echo -e "${CYAN}  Intake Complete${NC}"
    echo -e "${CYAN}═══════════════════════════════════════${NC}"
    echo -e "  Sources:  ${GREEN}${#REPO_URLS[@]}${NC}"
    echo -e "  Report:   ${GREEN}${report_file}${NC}"
    echo -e "${CYAN}═══════════════════════════════════════${NC}"
    echo ""
}

# ─────────────────────────────────────
# intake: Clone → scan → extract → report
# ─────────────────────────────────────
cmd_intake() {
    parse_opts "$@"

    if [[ ${#REPO_URLS[@]} -eq 0 ]]; then
        log_error "No repository URLs provided"
        echo "Usage: intake.sh intake [--keep] [--name <slug>] <repo-url...>"
        exit 1
    fi

    echo ""
    echo "╔══════════════════════════════════════╗"
    echo "║   KantorKu Intake Pipeline           ║"
    echo "╚══════════════════════════════════════╝"
    echo ""

    # Prepare directories
    mkdir -p "${INTAKE_DIR}"
    mkdir -p "${TEMP_DIR}"

    # Process each repository
    for url in "${REPO_URLS[@]}"; do
        local repo_slug
        repo_slug="$(basename "${url%.git}")"
        local clone_dir="${TEMP_DIR}/${repo_slug}"

        # Clone
        if clone_repo "${url}" "${clone_dir}"; then
            # Scan
            scan_repo "${clone_dir}"

            # Extract insights
            extract_insights "${clone_dir}"

            # Clean up unless --keep
            if [[ "${KEEP_REPOS}" == "false" ]]; then
                rm -rf "${clone_dir}"
                log_info "Cleaned up cloned repo: ${repo_slug}"
            else
                log_info "Keeping cloned repo: ${clone_dir}"
            fi
        fi
    done

    # Generate combined report
    generate_report

    # Clean up temp dir
    if [[ "${KEEP_REPOS}" == "false" ]]; then
        rmdir "${TEMP_DIR}" 2>/dev/null || true
    fi
}

# ─────────────────────────────────────
# sync: Copy reports into intake reports directory
# ─────────────────────────────────────
cmd_sync() {
    local source_dir="${1:-}"

    if [[ -z "${source_dir}" ]]; then
        log_error "Source directory required"
        echo "Usage: intake.sh sync <source-dir>"
        exit 1
    fi

    if [[ ! -d "${source_dir}" ]]; then
        log_error "Source directory not found: ${source_dir}"
        exit 1
    fi

    mkdir -p "${INTAKE_DIR}"

    log_info "Syncing reports from ${source_dir}..."

    local count=0
    for file in "${source_dir}"/*.{md,json,tsv,csv}; do
        if [[ -f "${file}" ]]; then
            cp "${file}" "${INTAKE_DIR}/"
            ((count++))
            log_ok "Synced: $(basename "${file}")"
        fi
    done

    if [[ ${count} -eq 0 ]]; then
        log_warn "No report files found in ${source_dir}"
    else
        log_ok "Synced ${count} report(s) to ${INTAKE_DIR}"
    fi
}

# ─────────────────────────────────────
# Usage
# ─────────────────────────────────────
usage() {
    echo "Usage: intake.sh <command> [options]"
    echo ""
    echo "Commands:"
    echo "  intake [--keep] [--name <slug>] <repo-url...>"
    echo "      Clone repos → scan → extract insights → generate report"
    echo "      --keep    Keep cloned repositories after analysis"
    echo "      --name    Override project name for the report"
    echo ""
    echo "  sync <source-dir>"
    echo "      Copy reports from source directory into intake reports"
    echo ""
}

# ─────────────────────────────────────
# Main
# ─────────────────────────────────────
case "${1:-}" in
    intake) shift; cmd_intake "$@" ;;
    sync)   cmd_sync "${2:-}" ;;
    *)
        usage
        exit 1
        ;;
esac
