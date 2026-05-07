#!/usr/bin/env bash
# =====================================================
# KantorKu Doctor — Unified Health Check
# Merges: doctor.sh (KantorKu) + body-doctor.sh (codex-skill)
# Verifies workspace integrity, config, skill links, memory, and skill map
# =====================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
KANTORKU_DIR="${WORKSPACE_ROOT}/.kantorku"
FRAMEWORK_DIR="${WORKSPACE_ROOT}/framework"
HOME_KANTORKU="${HOME}/.kantorku"
SKILLS_DIR="${KANTORKU_DIR}/skills"
MEMORY_DIR="${KANTORKU_DIR}/memory"
MAP_FILE="${SKILLS_DIR}/skill-map.tsv"

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

list_skills() {
  find "$SKILLS_DIR" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort
}

create_default_openai_yaml() {
  local skill_dir="$1"
  local skill
  skill="$(basename "$skill_dir")"
  local display
  display="$(echo "$skill" | tr '-' ' ' | sed -E 's/\b(.)/\U\1/g')"
  cat > "$skill_dir/agents/openai.yaml" <<YAML
---
interface:
  display_name: "$display"
  short_description: "Workflow for $skill"
  default_prompt: "Use $skill for this request."
YAML
}

rebuild_skill_map() {
  mkdir -p "$(dirname "$MAP_FILE")"
  declare -A old_cat=()
  declare -A old_kw=()
  if [ -f "$MAP_FILE" ]; then
    while IFS=$'\t' read -r skill category keywords; do
      [ -n "${skill:-}" ] || continue
      [ "$skill" = "skill_name" ] && continue
      [ "$skill" = "skill" ] && continue
      old_cat["$skill"]="${category:-general}"
      old_kw["$skill"]="${keywords:-}"
    done < "$MAP_FILE"
  fi

  {
    echo -e "skill_name\tcategory\tkeywords"
    while read -r skill; do
      [ -n "$skill" ] || continue
      local desc=""
      local category="general"
      local keywords=""
      if [ -n "${old_cat[$skill]:-}" ]; then
        category="${old_cat[$skill]}"
      fi
      if [ -n "${old_kw[$skill]:-}" ]; then
        keywords="${old_kw[$skill]}"
      fi
      if [ -f "$SKILLS_DIR/$skill/SKILL.md" ]; then
        desc="$(sed -n 's/^description:[[:space:]]*//p' "$SKILLS_DIR/$skill/SKILL.md" | head -n 1 | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9 ]+/ /g')"
      fi
      if [ -z "$keywords" ]; then
        keywords="$(echo "$skill" | tr '-' ' ') $desc"
      fi
      printf "%s\t%s\t%s\n" "$skill" "$category" "$keywords"
    done < <(list_skills)
  } > "$MAP_FILE"
}

ensure_memory_staging_layout() {
  mkdir -p "$MEMORY_DIR"
  [ -f "$MEMORY_DIR/MEMORY.md" ] || printf "# Project Memory\n\n## Context\n\n## Key Decisions\n\n## Active Tasks\n\n## Completed Tasks\n\n## Learnings\n" > "$MEMORY_DIR/MEMORY.md"
  [ -f "$MEMORY_DIR/backend.md" ] || printf "# Topic: backend\n\n" > "$MEMORY_DIR/backend.md"
  check_pass "memory staging layout ready (MEMORY.md + topic files)"
}

# ─────────────────────────────────────
# doctor: Full health check
# ─────────────────────────────────────
run_doctor() {
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

    # ── Check 4: All skills have SKILL.md and openai.yaml ──
    echo "Checking skills completeness..."
    local missing=0
    while IFS= read -r skill; do
        [ -n "$skill" ] || continue
        local sdir="$SKILLS_DIR/$skill"
        if [ ! -f "$sdir/SKILL.md" ]; then
            check_fail "missing $sdir/SKILL.md"
            missing=$((missing + 1))
        else
            check_pass "Skill '${skill}' — SKILL.md present"
        fi
        if [ ! -f "$sdir/agents/openai.yaml" ]; then
            check_warn "missing $sdir/agents/openai.yaml"
            missing=$((missing + 1))
        fi
    done < <(list_skills)
    if [ "$missing" -eq 0 ]; then
        check_pass "all skills have SKILL.md and agents/openai.yaml"
    fi

    # ── Check 5: Skill map exists ──
    echo "Checking skill map..."
    if [[ -f "${MAP_FILE}" ]]; then
        check_pass "skill-map.tsv exists"
    else
        check_fail "skill-map.tsv not found"
    fi

    # ── Check 6: Memory files ──
    echo "Checking project memory..."
    MEMORY_FILE="${MEMORY_DIR}/MEMORY.md"
    if [[ -f "${MEMORY_FILE}" ]]; then
        if grep -q "KantorKu" "${MEMORY_FILE}" 2>/dev/null; then
            check_pass "MEMORY.md is initialized"
        else
            check_warn "MEMORY.md exists but may not be initialized"
        fi
    else
        check_fail "MEMORY.md not found"
    fi

    # Multi-file memory staging check
    local topics
    topics="$(find "$MEMORY_DIR" -maxdepth 1 -type f -name '*.md' ! -name 'MEMORY.md' | wc -l | tr -d ' ')"
    if [ "$topics" -ge 1 ]; then
        check_pass "multi-file memory staging clean (topic files=$topics)"
    else
        check_warn "no topic memory files detected"
    fi

    # ── Check 7: Framework is installed ──
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

    # ── Check 8: Python version ──
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
        return 1
    elif [[ ${WARN} -gt 0 ]]; then
        echo -e "  ${YELLOW}Warnings detected — review above${NC}"
        return 0
    else
        echo -e "  ${GREEN}All checks passed!${NC}"
        return 0
    fi
}

# ─────────────────────────────────────
# repair: Fix issues and rebuild
# ─────────────────────────────────────
run_repair() {
    echo ""
    echo "╔══════════════════════════════════════╗"
    echo "║   KantorKu Doctor — Repair           ║"
    echo "╚══════════════════════════════════════╝"
    echo ""

    mkdir -p "$SKILLS_DIR" "$MEMORY_DIR"

    # Fix missing openai.yaml
    while IFS= read -r skill; do
        [ -n "$skill" ] || continue
        local sdir="$SKILLS_DIR/$skill"
        if [ ! -f "$sdir/SKILL.md" ]; then
            check_warn "skip $skill (missing SKILL.md)"
            continue
        fi
        if [ ! -f "$sdir/agents/openai.yaml" ]; then
            mkdir -p "$sdir/agents"
            create_default_openai_yaml "$sdir"
            check_pass "created $sdir/agents/openai.yaml"
        fi
    done < <(list_skills)

    # Rebuild skill map
    rebuild_skill_map
    check_pass "rebuilt skill-map.tsv"

    # Ensure memory staging layout
    ensure_memory_staging_layout

    # Run doctor to verify
    run_doctor
}

# ─────────────────────────────────────
# Main
# ─────────────────────────────────────
cmd="${1:-}"
case "$cmd" in
    doctor) run_doctor ;;
    repair) run_repair ;;
    -h|--help|help|"")
        echo "Usage: doctor.sh <command>"
        echo ""
        echo "Commands:"
        echo "  doctor    Check workspace integrity"
        echo "  repair    Fix missing files and rebuild skill map"
        ;;
    *)
        echo "Unknown command: $cmd"
        echo "Usage: doctor.sh [doctor|repair]"
        exit 1
        ;;
esac
