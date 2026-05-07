#!/usr/bin/env bash
# =====================================================
# KantorKu Guard — Unified Config Drift Protection
# Merges: guard.sh (KantorKu) + home-codex-guard.sh (codex-skill)
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
pass()      { printf "[PASS] %s\n" "$1"; }
warn()      { printf "[WARN] %s\n" "$1"; }
fail()      { printf "[FAIL] %s\n" "$1"; }

sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

check_file_equal() {
  local current="$1"
  local template="$2"
  local label="$3"

  if [ ! -f "$template" ]; then
    fail "$label template missing: $template"
    return 1
  fi
  if [ ! -f "$current" ]; then
    fail "$label missing: $current"
    return 1
  fi

  local a b
  a="$(sha256_of "$current")"
  b="$(sha256_of "$template")"
  if [ "$a" = "$b" ]; then
    pass "$label matches baseline"
    return 0
  fi

  fail "$label drift detected"
  return 1
}

check_models_cache_policy() {
  local cache="$HOME_KANTORKU/models_cache.json"
  local policy_file="$BASELINE_DIR/home-model-policy.json"

  if [ ! -f "$policy_file" ]; then
    log_info "Model policy file not found, skipping model cache check"
    return 0
  fi

  if [ ! -f "$cache" ]; then
    warn "models cache missing: $cache"
    return 1
  fi

  local result
  result="$(python3 - <<'PY' "$cache" "$policy_file"
import json, sys
cache_path=sys.argv[1]
policy_path=sys.argv[2]
policy=json.load(open(policy_path, encoding='utf-8'))
cache=json.load(open(cache_path, encoding='utf-8'))
models=cache.get('models') or []
slug=policy.get('required_slug')
default_effort=policy.get('required_default_reasoning_level')
required_supported=set(policy.get('required_supported_efforts') or [])

m=next((x for x in models if x.get('slug')==slug), None)
if not m:
    print('fail:missing_slug')
    raise SystemExit(0)

if default_effort and m.get('default_reasoning_level')!=default_effort:
    print('fail:default_reasoning_mismatch')
    raise SystemExit(0)

supported=m.get('supported_reasoning_levels') or []
supported_efforts={x.get('effort') for x in supported if isinstance(x, dict) and x.get('effort')}
if required_supported and supported_efforts!=required_supported:
    print('fail:supported_reasoning_mismatch')
    raise SystemExit(0)

print('pass')
PY
)"

  if [ "$result" = "pass" ]; then
    pass "models_cache policy matches baseline"
    return 0
  fi

  fail "models_cache policy check failed ($result)"
  return 1
}

sanitize_models_cache() {
  local cache="$HOME_KANTORKU/models_cache.json"
  local policy_file="$BASELINE_DIR/home-model-policy.json"
  [ -f "$cache" ] || return 0
  [ -f "$policy_file" ] || return 0

  node -e '
const fs=require("fs");
const cachePath=process.argv[1];
const policyPath=process.argv[2];
const policy=JSON.parse(fs.readFileSync(policyPath,"utf8"));
const requiredSlug=policy.required_slug;
const requiredEffort=policy.required_default_reasoning_level;
const requiredSupported=(policy.required_supported_efforts||[]).map(e=>({effort:e,description:"Balances speed and reasoning depth for everyday tasks"}));
const clearPayload=Boolean(policy.clear_instruction_payload);
const d=JSON.parse(fs.readFileSync(cachePath,"utf8"));
if(!Array.isArray(d.models)) d.models=[];
for(const m of d.models){
  if(clearPayload){
    if(typeof m.base_instructions==="string") m.base_instructions="";
    if(!m.model_messages || typeof m.model_messages!=="object") m.model_messages={};
    if(typeof m.model_messages.instructions_template==="string") m.model_messages.instructions_template="";
    if(m.model_messages.instructions_variables && typeof m.model_messages.instructions_variables==="object"){
      m.model_messages.instructions_variables={};
    }
  }
  if(m.slug===requiredSlug){
    m.default_reasoning_level=requiredEffort;
    m.supported_reasoning_levels=requiredSupported;
  }
}
fs.writeFileSync(cachePath, JSON.stringify(d));
' "$cache" "$policy_file"
}

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

    # Check 2: config.toml matches baseline (sha256)
    local home_config="${HOME_KANTORKU}/config.toml"
    local baseline_config="${BASELINE_DIR}/home-config.toml"

    if [[ -f "${home_config}" ]] && [[ -f "${baseline_config}" ]]; then
        check_file_equal "${home_config}" "${baseline_config}" "home config.toml" || drift_found=1
    elif [[ ! -f "${home_config}" ]]; then
        log_error "config.toml missing at ${home_config}"
        drift_found=1
    fi

    # Check 3: default.rules matches baseline (sha256)
    local home_rules="${HOME_KANTORKU}/rules/default.rules"
    local baseline_rules="${BASELINE_DIR}/home-default.rules"

    if [[ -f "${home_rules}" ]] && [[ -f "${baseline_rules}" ]]; then
        check_file_equal "${home_rules}" "${baseline_rules}" "home default.rules" || drift_found=1
    fi

    # Check 4: Models cache policy (codex-skill integration)
    check_models_cache_policy || drift_found=1

    # Check 5: Skills are linked
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

    # Check 6: Approval rules exist
    if [[ -f "${BASELINE_DIR}/home-default.rules" ]]; then
        log_ok "Approval rules present"
    else
        log_warn "Approval rules not found"
    fi

    # Check 7: MEMORY.md exists
    if [[ -f "${KANTORKU_DIR}/memory/MEMORY.md" ]]; then
        log_ok "MEMORY.md exists"
    else
        log_error "MEMORY.md not found"
        drift_found=1
    fi

    # Check 8: Required skill directories
    for skill in library office debug evolve deploy; do
        if [[ -d "${KANTORKU_DIR}/skills/${skill}" ]]; then
            log_ok "Skill '${skill}' directory present"
        else
            log_error "Skill '${skill}' directory missing"
            drift_found=1
        fi
    done

    # Check 9: arg0 wrapper (codex-skill integration)
    local arg0_dir="${HOME_KANTORKU}/tmp/arg0/codex-arg0GInYml"
    local wrapper="${arg0_dir}/codex-wrapper"
    if [ -x "$wrapper" ]; then
        pass "arg0 wrapper exists"
    else
        warn "arg0 wrapper missing or not executable: $wrapper"
    fi

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

    # Repair 3: Restore default.rules from baseline
    local home_rules="${HOME_KANTORKU}/rules/default.rules"
    local baseline_rules="${BASELINE_DIR}/home-default.rules"

    if [[ -f "${baseline_rules}" ]]; then
        mkdir -p "$(dirname "${home_rules}")"
        cp "${baseline_rules}" "${home_rules}"
        pass "restored home default.rules"
    fi

    # Repair 4: Re-link skills
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

    # Repair 5: Restore MEMORY.md if missing
    local memory_file="${KANTORKU_DIR}/memory/MEMORY.md"
    if [[ ! -f "${memory_file}" ]]; then
        log_info "Creating MEMORY.md template..."
        cat > "${memory_file}" <<'EOF'
# Project Memory

## Context
KantorKu — AI worker orchestration framework modeling a real digital office.

## Key Decisions

## Active Tasks

## Completed Tasks

## Learnings
EOF
        log_ok "MEMORY.md template created"
    fi

    # Repair 6: Ensure skill directories exist
    for skill in library office debug evolve deploy; do
        local skill_dir="${KANTORKU_DIR}/skills/${skill}"
        if [[ ! -d "${skill_dir}" ]]; then
            log_info "Creating missing skill directory: ${skill}..."
            mkdir -p "${skill_dir}/agents"
            log_ok "Created ${skill} skill directory"
        fi
    done

    # Repair 7: Refresh arg0 wrapper (codex-skill integration)
    local setup_script="${KANTORKU_DIR}/skills/setup/scripts/codex-arg0-ensure.sh"
    if [ -x "$setup_script" ]; then
        bash "$setup_script"
        pass "arg0 wrapper refreshed"
    fi

    # Repair 8: Sanitize models cache (codex-skill integration)
    sanitize_models_cache
    pass "models cache sanitized"

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
        mkdir -p "${BASELINE_DIR}"
        cp "${home_config}" "${baseline_config}"
        log_ok "Baseline updated from ${home_config}"
    else
        log_error "No config.toml found at ${home_config} — nothing to snapshot"
        exit 1
    fi

    # Snapshot default.rules
    local home_rules="${HOME_KANTORKU}/rules/default.rules"
    local baseline_rules="${BASELINE_DIR}/home-default.rules"
    if [[ -f "${home_rules}" ]]; then
        cp "${home_rules}" "${baseline_rules}"
        pass "baseline default.rules refreshed"
    fi

    # Snapshot current skill state
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
