#!/usr/bin/env bash
# =====================================================
# KantorKu Bootstrap Script (Linux/macOS)
# Initializes the .kantorku/ workspace for development
# =====================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
KANTORKU_DIR="${WORKSPACE_ROOT}/.kantorku"
FRAMEWORK_DIR="${WORKSPACE_ROOT}/framework"
HOME_KANTORKU="${HOME}/.kantorku"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ─────────────────────────────────────
# Step 1: Install Python dependencies
# ─────────────────────────────────────
step_install_deps() {
    log_info "Step 1/5: Installing Python dependencies..."

    if [[ ! -d "${FRAMEWORK_DIR}" ]]; then
        log_error "Framework directory not found: ${FRAMEWORK_DIR}"
        exit 1
    fi

    cd "${FRAMEWORK_DIR}"

    if command -v pip &>/dev/null; then
        pip install -e ".[all]" 2>&1 | tail -5
        log_ok "Python dependencies installed via pip"
    elif command -v pip3 &>/dev/null; then
        pip3 install -e ".[all]" 2>&1 | tail -5
        log_ok "Python dependencies installed via pip3"
    else
        log_error "pip/pip3 not found. Install Python 3.11+ first."
        exit 1
    fi
}

# ─────────────────────────────────────
# Step 2: Verify Python 3.11+
# ─────────────────────────────────────
step_verify_python() {
    log_info "Step 2/5: Verifying Python version..."

    if ! command -v python3 &>/dev/null; then
        log_error "python3 not found in PATH"
        exit 1
    fi

    local py_version
    py_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    local major minor
    major=$(echo "${py_version}" | cut -d. -f1)
    minor=$(echo "${py_version}" | cut -d. -f2)

    if [[ "${major}" -lt 3 ]] || [[ "${major}" -eq 3 && "${minor}" -lt 11 ]]; then
        log_error "Python 3.11+ required, found ${py_version}"
        exit 1
    fi

    log_ok "Python ${py_version} detected (>= 3.11)"
}

# ─────────────────────────────────────
# Step 3: Link skills to ~/.kantorku/skills/
# ─────────────────────────────────────
step_link_skills() {
    log_info "Step 3/5: Linking skills to ${HOME_KANTORKU}/skills/..."

    mkdir -p "${HOME_KANTORKU}"

    # Remove existing symlink or directory if present
    if [[ -L "${HOME_KANTORKU}/skills" ]]; then
        rm "${HOME_KANTORKU}/skills"
        log_info "Removed existing skills symlink"
    elif [[ -d "${HOME_KANTORKU}/skills" ]]; then
        log_warn "Existing skills directory found at ${HOME_KANTORKU}/skills/ — backing up"
        mv "${HOME_KANTORKU}/skills" "${HOME_KANTORKU}/skills.bak.$(date +%Y%m%d%H%M%S)"
    fi

    ln -s "${KANTORKU_DIR}/skills" "${HOME_KANTORKU}/skills"
    log_ok "Skills linked: ${HOME_KANTORKU}/skills → ${KANTORKU_DIR}/skills"

    # Link config.toml if not already present
    if [[ ! -f "${HOME_KANTORKU}/config.toml" ]]; then
        cp "${KANTORKU_DIR}/config.toml" "${HOME_KANTORKU}/config.toml"
        log_ok "Default config copied to ${HOME_KANTORKU}/config.toml"
    else
        log_info "Existing config.toml found at ${HOME_KANTORKU}/ — keeping"
    fi
}

# ─────────────────────────────────────
# Step 4: Initialize MEMORY.md
# ─────────────────────────────────────
step_init_memory() {
    log_info "Step 4/5: Initializing MEMORY.md..."

    local memory_file="${KANTORKU_DIR}/memory/MEMORY.md"

    if [[ -f "${memory_file}" ]] && grep -q "## Key Decisions" "${memory_file}" 2>/dev/null; then
        log_info "MEMORY.md already initialized — updating project info"
    fi

    # Auto-detect project info
    local project_name="KantorKu"
    local project_version="0.5.0"
    local python_version
    python_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "unknown")

    if [[ -f "${FRAMEWORK_DIR}/pyproject.toml" ]]; then
        project_version=$(python3 -c "
import re
with open('${FRAMEWORK_DIR}/pyproject.toml') as f:
    content = f.read()
m = re.search(r'version\s*=\s*\"([^\"]+)\"', content)
print(m.group(1) if m else 'unknown')
" 2>/dev/null || echo "0.5.0")
    fi

    # Write updated memory if template is empty
    if ! grep -q "KantorKu" "${memory_file}" 2>/dev/null || ! grep -q "AI worker" "${memory_file}" 2>/dev/null; then
        cat > "${memory_file}" <<EOF
# Project Memory

## Context
KantorKu — AI worker orchestration framework modeling a real digital office.
14 specialized workers coordinated by a Conductor (CEO) with contract-based workflows.

**Auto-detected info:**
- Project: ${project_name} v${project_version}
- Python: ${python_version}
- Framework dir: ${FRAMEWORK_DIR}
- Bootstrapped: $(date -Iseconds 2>/dev/null || date)

## Key Decisions
- [$(date +%Y-%m-%d)] Workspace bootstrapped via bootstrap.sh

## Active Tasks
- [ ] Verify all workers respond to health check

## Completed Tasks
- [x] Workspace bootstrap ($(date +%Y-%m-%d))

## Learnings
EOF
        log_ok "MEMORY.md initialized with project info"
    else
        log_ok "MEMORY.md already contains project context"
    fi
}

# ─────────────────────────────────────
# Step 5: Configure MCP servers
# ─────────────────────────────────────
step_configure_mcp() {
    log_info "Step 5/5: Configuring MCP servers..."

    local config_file="${FRAMEWORK_DIR}/kantorku.toml"

    if [[ -f "${config_file}" ]]; then
        log_ok "kantorku.toml found at ${config_file}"

        # Verify the config is valid TOML
        if python3 -c "import toml; toml.load('${config_file}')" 2>/dev/null; then
            log_ok "kantorku.toml is valid TOML"
        else
            log_warn "kantorku.toml may have syntax errors — verify manually"
        fi
    else
        log_warn "kantorku.toml not found — copying from example"
        local example_file="${FRAMEWORK_DIR}/kantorku.toml.example"
        if [[ -f "${example_file}" ]]; then
            cp "${example_file}" "${config_file}"
            log_ok "Copied kantorku.toml.example → kantorku.toml"
            log_info "Edit ${config_file} to add your API keys"
        else
            log_warn "kantorku.toml.example not found either — skip MCP config"
        fi
    fi

    # Check for kantorku CLI
    if command -v kantorku &>/dev/null; then
        log_ok "kantorku CLI available"
    else
        log_info "kantorku CLI not in PATH — ensure framework is installed: pip install -e '.[all]'"
    fi
}

# ─────────────────────────────────────
# Main
# ─────────────────────────────────────
main() {
    echo ""
    echo "╔══════════════════════════════════════╗"
    echo "║   KantorKu Workspace Bootstrap       ║"
    echo "╚══════════════════════════════════════╝"
    echo ""

    step_install_deps
    step_verify_python
    step_link_skills
    step_init_memory
    step_configure_mcp

    echo ""
    log_ok "Bootstrap complete! Your workspace is ready."
    echo ""
    echo "Next steps:"
    echo "  1. Edit framework/kantorku.toml with your API keys"
    echo "  2. Run: kantorku setup          (interactive key wizard)"
    echo "  3. Run: kantorku serve           (start backend)"
    echo "  4. Run: bash .kantorku/tools/guard.sh doctor  (verify health)"
    echo ""
}

main "$@"
