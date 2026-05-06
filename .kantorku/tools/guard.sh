#!/usr/bin/env bash
# =====================================================
# KantorKu Home Guard — Config Drift Protection
# Commands: doctor | repair | enforce | snapshot
# =====================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
KANTORKU_DIR="${WORKSPACE_ROOT}/.kantorku"
FRAMEWORK_DIR="${WORKSPACE_ROOT}/framework"
HOME_KANTORKU="${HOME}/.kantorku"
BASELINE_DIR="${KANTORKU_DIR}/home-sync"

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

# ─────────────────────────────────────
# doctor: Check workspace integrity
# ─────────────────────────────────────
cmd_doctor() {
    local drift_found=0

    echo ""
    echo "╔══════════════════════════════════════╗"
    echo "║   KantorKu Guard — Doctor Check      ║"
    echo "╚══════════════════════════════════════╝"
    echo ""

    # Check 1: ~/.kantorku/ exists
    if [[ -d "${HOME_KANTORKU}" ]]; then
        log_ok "~/.kantorku/ exists"
    else
        log_error "~/.kantorku/ not found"
        drift_found=1
    fi

    # Check 2: config.toml matches baseline
    local home_config="${HOME_KANTORKU}/config.toml"
    local baseline_config="${BASELINE_DIR}/home-config.toml"

    if [[ -f "${home_config}" ]] && [[ -f "${baseline_config}" ]]; then
        if diff -q "${home_config}" "${baseline_config}" &>/dev/null; then
            log_ok "config.toml matches baseline"
        else
            log_warn "config.toml has drifted from baseline"
            drift_found=1
        fi
    elif [[ ! -f "${home_config}" ]]; then
        log_error "config.toml missing at ${home_config}"
        drift_found=1
    fi

    # Check 3: Skills are linked
    local home_skills="${HOME_KANTORKU}/skills"
    if [[ -L "${home_skills}" ]]; then
        local target
        target="$(readlink "${home_skills}")"
        if [[ -d "${target}" ]]; then
            log_ok "Skills symlink valid → ${target}"
        else
            log_error "Skills symlink broken → ${target}"
            drift_found=1
        fi
    elif [[ -d "${home_skills}" ]]; then
        log_warn "Skills directory exists but not a symlink"
        drift_found=1
    else
        log_error "Skills not linked"
        drift_found=1
    fi

    # Check 4: Approval rules exist
    if [[ -f "${BASELINE_DIR}/home-default.rules" ]]; then
        log_ok "Approval rules present"
    else
        log_warn "Approval rules not found"
    fi

    # Check 5: MEMORY.md exists
    if [[ -f "${KANTORKU_DIR}/memory/MEMORY.md" ]]; then
        log_ok "MEMORY.md exists"
    else
        log_error "MEMORY.md not found"
        drift_found=1
    fi

    # Check 6: Required skill directories
    for skill in library office debug evolve deploy; do
        if [[ -d "${KANTORKU_DIR}/skills/${skill}" ]]; then
            log_ok "Skill '${skill}' directory present"
        else
            log_error "Skill '${skill}' directory missing"
            drift_found=1
        fi
    done

    echo ""
    if [[ ${drift_found} -eq 0 ]]; then
        log_ok "No drift detected — workspace is healthy"
        return 0
    else
        log_warn "Drift detected — run 'guard.sh repair' or 'guard.sh enforce' to fix"
        return 1
    fi
}

# ─────────────────────────────────────
# repair: Restore from templates, re-link
# ─────────────────────────────────────
cmd_repair() {
    echo ""
    echo "╔══════════════════════════════════════╗"
    echo "║   KantorKu Guard — Repair            ║"
    echo "╚══════════════════════════════════════╝"
    echo ""

    # Repair 1: Create ~/.kantorku/ if missing
    if [[ ! -d "${HOME_KANTORKU}" ]]; then
        log_info "Creating ~/.kantorku/..."
        mkdir -p "${HOME_KANTORKU}"
        log_ok "Created ~/.kantorku/"
    fi

    # Repair 2: Restore config.toml from baseline
    local home_config="${HOME_KANTORKU}/config.toml"
    local baseline_config="${BASELINE_DIR}/home-config.toml"

    if [[ ! -f "${home_config}" ]] && [[ -f "${baseline_config}" ]]; then
        log_info "Restoring config.toml from baseline..."
        cp "${baseline_config}" "${home_config}"
        log_ok "Restored config.toml"
    elif [[ -f "${home_config}" ]] && [[ -f "${baseline_config}" ]]; then
        if ! diff -q "${home_config}" "${baseline_config}" &>/dev/null; then
            log_warn "config.toml has drifted — backing up and restoring baseline"
            cp "${home_config}" "${home_config}.drifted.$(date +%Y%m%d%H%M%S)"
            cp "${baseline_config}" "${home_config}"
            log_ok "Restored config.toml (drifted version backed up)"
        fi
    fi

    # Repair 3: Re-link skills
    local home_skills="${HOME_KANTORKU}/skills"
    if [[ -L "${home_skills}" ]]; then
        local target
        target="$(readlink "${home_skills}")"
        if [[ ! -d "${target}" ]]; then
            log_info "Fixing broken skills symlink..."
            rm "${home_skills}"
            ln -s "${KANTORKU_DIR}/skills" "${home_skills}"
            log_ok "Skills symlink repaired"
        fi
    elif [[ -d "${home_skills}" ]]; then
        log_info "Replacing skills directory with symlink..."
        mv "${home_skills}" "${home_skills}.bak.$(date +%Y%m%d%H%M%S)"
        ln -s "${KANTORKU_DIR}/skills" "${home_skills}"
        log_ok "Skills symlink created (directory backed up)"
    else
        log_info "Creating skills symlink..."
        ln -s "${KANTORKU_DIR}/skills" "${home_skills}"
        log_ok "Skills symlink created"
    fi

    # Repair 4: Restore MEMORY.md if missing
    local memory_file="${KANTORKU_DIR}/memory/MEMORY.md"
    if [[ ! -f "${memory_file}" ]]; then
        log_info "Creating MEMORY.md template..."
        cat > "${memory_file}" <<'EOF'
# Project Memory

## Context
KantorKu — AI worker orchestration framework modeling a real digital office.
14 specialized workers coordinated by a Conductor (CEO) with contract-based workflows.

## Key Decisions
<!-- Add decisions here as the project evolves -->

## Active Tasks
<!-- Add active tasks here -->

## Completed Tasks
<!-- Add completed tasks here -->

## Learnings
<!-- Add learnings here -->
EOF
        log_ok "MEMORY.md template created"
    fi

    # Repair 5: Ensure skill directories exist
    for skill in library office debug evolve deploy; do
        local skill_dir="${KANTORKU_DIR}/skills/${skill}"
        if [[ ! -d "${skill_dir}" ]]; then
            log_info "Creating missing skill directory: ${skill}..."
            mkdir -p "${skill_dir}/agents"
            log_ok "Created ${skill} skill directory"
        fi
    done

    echo ""
    log_ok "Repair complete! Run 'guard.sh doctor' to verify."
}

# ─────────────────────────────────────
# enforce: doctor → auto-repair if drift
# ─────────────────────────────────────
cmd_enforce() {
    echo ""
    echo "╔══════════════════════════════════════╗"
    echo "║   KantorKu Guard — Enforce           ║"
    echo "╚══════════════════════════════════════╝"
    echo ""

    log_info "Running doctor check..."
    if cmd_doctor; then
        log_ok "Workspace is healthy — no enforcement needed"
    else
        log_warn "Drift detected — running auto-repair..."
        cmd_repair
        log_info "Re-running doctor check after repair..."
        if cmd_doctor; then
            log_ok "Enforcement successful — workspace is now healthy"
        else
            log_error "Enforcement failed — manual intervention required"
            exit 1
        fi
    fi
}

# ─────────────────────────────────────
# snapshot: Capture current state as baseline
# ─────────────────────────────────────
cmd_snapshot() {
    echo ""
    echo "╔══════════════════════════════════════╗"
    echo "║   KantorKu Guard — Snapshot          ║"
    echo "╚══════════════════════════════════════╝"
    echo ""

    local home_config="${HOME_KANTORKU}/config.toml"
    local baseline_config="${BASELINE_DIR}/home-config.toml"

    if [[ -f "${home_config}" ]]; then
        log_info "Capturing current config.toml as new baseline..."
        cp "${home_config}" "${baseline_config}"
        log_ok "Baseline updated from ${home_config}"
    else
        log_error "No config.toml found at ${home_config} — nothing to snapshot"
        exit 1
    fi

    # Also snapshot current skill state
    local skill_map="${KANTORKU_DIR}/skills/skill-map.tsv"
    if [[ -f "${skill_map}" ]]; then
        cp "${skill_map}" "${BASELINE_DIR}/skill-map.baseline.tsv"
        log_ok "Skill map snapshot saved"
    fi

    # Record snapshot timestamp
    echo "$(date -Iseconds 2>/dev/null || date)" > "${BASELINE_DIR}/.last-snapshot"
    log_ok "Snapshot timestamp recorded"

    echo ""
    log_ok "Snapshot complete! Current state is now the baseline."
}

# ─────────────────────────────────────
# Usage
# ─────────────────────────────────────
usage() {
    echo "Usage: guard.sh <command>"
    echo ""
    echo "Commands:"
    echo "  doctor    Check workspace integrity and detect drift"
    echo "  repair    Restore from templates and re-link skills"
    echo "  enforce   Doctor → auto-repair if drift detected"
    echo "  snapshot  Capture current state as new baseline"
    echo ""
}

# ─────────────────────────────────────
# Main
# ─────────────────────────────────────
case "${1:-}" in
    doctor)    cmd_doctor ;;
    repair)    cmd_repair ;;
    enforce)   cmd_enforce ;;
    snapshot)  cmd_snapshot ;;
    *)
        usage
        exit 1
        ;;
esac
