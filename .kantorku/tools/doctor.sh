#!/usr/bin/env bash
# =====================================================
# KantorKu Doctor — Health Check Script
# Verifies workspace integrity, config, and skill links
# =====================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
KANTORKU_DIR="${WORKSPACE_ROOT}/.kantorku"
FRAMEWORK_DIR="${WORKSPACE_ROOT}/framework"
HOME_KANTORKU="${HOME}/.kantorku"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0

check_pass() { ((PASS++)); echo -e "  ${GREEN}✓${NC} $*"; }
check_fail() { ((FAIL++)); echo -e "  ${RED}✗${NC} $*"; }
check_warn() { ((WARN++)); echo -e "  ${YELLOW}!${NC} $*"; }

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   KantorKu Doctor — Health Check     ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── Check 1: ~/.kantorku/ exists ──
echo "Checking home directory..."
if [[ -d "${HOME_KANTORKU}" ]]; then
    check_pass "~/.kantorku/ exists"
else
    check_fail "~/.kantorku/ not found — run bootstrap.sh first"
fi

# ── Check 2: config.toml matches baseline ──
echo "Checking configuration..."
HOME_CONFIG="${HOME_KANTORKU}/config.toml"
BASELINE_CONFIG="${KANTORKU_DIR}/home-sync/home-config.toml"

if [[ -f "${HOME_CONFIG}" ]] && [[ -f "${BASELINE_CONFIG}" ]]; then
    if diff -q "${HOME_CONFIG}" "${BASELINE_CONFIG}" &>/dev/null; then
        check_pass "config.toml matches baseline"
    else
        check_warn "config.toml has drifted from baseline"
        diff "${BASELINE_CONFIG}" "${HOME_CONFIG}" 2>/dev/null | head -10
    fi
elif [[ -f "${HOME_CONFIG}" ]]; then
    check_warn "config.toml exists but no baseline to compare"
else
    check_fail "config.toml not found at ${HOME_CONFIG}"
fi

# ── Check 3: Skills are linked ──
echo "Checking skill links..."
HOME_SKILLS="${HOME_KANTORKU}/skills"
if [[ -L "${HOME_SKILLS}" ]]; then
    local_target="$(readlink "${HOME_SKILLS}")"
    if [[ -d "${local_target}" ]]; then
        check_pass "Skills symlink is valid → ${local_target}"
    else
        check_fail "Skills symlink is broken → ${local_target}"
    fi
elif [[ -d "${HOME_SKILLS}" ]]; then
    check_warn "Skills directory exists but is not a symlink"
else
    check_fail "Skills not linked — run bootstrap.sh step 3"
fi

# ── Check 4: Required skills exist ──
echo "Checking required skills..."
for skill in library office debug evolve deploy; do
    SKILL_DIR="${KANTORKU_DIR}/skills/${skill}"
    if [[ -d "${SKILL_DIR}" ]]; then
        if [[ -f "${SKILL_DIR}/SKILL.md" ]]; then
            check_pass "Skill '${skill}' — SKILL.md present"
        else
            check_fail "Skill '${skill}' — missing SKILL.md"
        fi
        if [[ -f "${SKILL_DIR}/agents/openai.yaml" ]]; then
            check_pass "Skill '${skill}' — openai.yaml present"
        else
            check_fail "Skill '${skill}' — missing openai.yaml"
        fi
    else
        check_fail "Skill '${skill}' — directory missing"
    fi
done

# ── Check 5: Framework is installed ──
echo "Checking framework..."
if command -v kantorku &>/dev/null; then
    check_pass "kantorku CLI is available"
else
    check_warn "kantorku CLI not in PATH — framework may not be installed"
fi

if [[ -f "${FRAMEWORK_DIR}/kantorku.toml" ]]; then
    check_pass "kantorku.toml exists in framework/"
else
    check_warn "kantorku.toml not found in framework/ — run 'kantorku setup'"
fi

# ── Check 6: Memory file ──
echo "Checking project memory..."
MEMORY_FILE="${KANTORKU_DIR}/memory/MEMORY.md"
if [[ -f "${MEMORY_FILE}" ]]; then
    if grep -q "KantorKu" "${MEMORY_FILE}" 2>/dev/null; then
        check_pass "MEMORY.md is initialized"
    else
        check_warn "MEMORY.md exists but may not be initialized"
    fi
else
    check_fail "MEMORY.md not found"
fi

# ── Check 7: Python version ──
echo "Checking Python..."
if command -v python3 &>/dev/null; then
    py_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    major=$(echo "${py_version}" | cut -d. -f1)
    minor=$(echo "${py_version}" | cut -d. -f2)
    if [[ "${major}" -lt 3 ]] || [[ "${major}" -eq 3 && "${minor}" -lt 11 ]]; then
        check_fail "Python ${py_version} — 3.11+ required"
    else
        check_pass "Python ${py_version} — meets requirement"
    fi
else
    check_fail "python3 not found"
fi

# ── Summary ──
echo ""
echo "─────────────────────────────────────"
echo -e "  ${GREEN}PASS${NC}: ${PASS}  ${YELLOW}WARN${NC}: ${WARN}  ${RED}FAIL${NC}: ${FAIL}"
echo "─────────────────────────────────────"

if [[ ${FAIL} -gt 0 ]]; then
    echo -e "  ${RED}Action required: Fix failures above or run 'guard.sh repair'${NC}"
    exit 1
elif [[ ${WARN} -gt 0 ]]; then
    echo -e "  ${YELLOW}Warnings detected — review above${NC}"
    exit 0
else
    echo -e "  ${GREEN}All checks passed!${NC}"
    exit 0
fi
