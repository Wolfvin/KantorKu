#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOME_CODEX="${CODEX_HOME:-$HOME/.codex}"
SYNC_DIR="$ROOT/.codex/home-sync"
TEMPLATE_CONFIG="$SYNC_DIR/home-config.toml"
TEMPLATE_RULES="$SYNC_DIR/home-default.rules"
POLICY_FILE="$SYNC_DIR/home-model-policy.json"
SETUP_SCRIPT="$ROOT/.codex/skills/setup/scripts/codex-arg0-ensure.sh"

usage() {
  cat <<'USAGE'
Usage:
  bash .codex/tools/home-codex-guard.sh doctor
  bash .codex/tools/home-codex-guard.sh repair
  bash .codex/tools/home-codex-guard.sh enforce
  bash .codex/tools/home-codex-guard.sh snapshot
USAGE
}

pass() { printf "[PASS] %s\n" "$1"; }
warn() { printf "[WARN] %s\n" "$1"; }
fail() { printf "[FAIL] %s\n" "$1"; }

ensure_parent() {
  mkdir -p "$(dirname "$1")"
}

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
  local cache="$HOME_CODEX/models_cache.json"
  if [ ! -f "$cache" ]; then
    warn "models cache missing: $cache"
    return 1
  fi

  local result
  result="$(python3 - <<'PY' "$cache" "$POLICY_FILE"
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

run_doctor() {
  local rc=0

  [ -d "$HOME_CODEX" ] && pass "home codex dir exists: $HOME_CODEX" || { fail "home codex dir missing: $HOME_CODEX"; rc=1; }

  check_file_equal "$HOME_CODEX/config.toml" "$TEMPLATE_CONFIG" "home config.toml" || rc=1
  check_file_equal "$HOME_CODEX/rules/default.rules" "$TEMPLATE_RULES" "home default.rules" || rc=1
  check_models_cache_policy || rc=1

  local arg0_dir="$HOME_CODEX/tmp/arg0/codex-arg0GInYml"
  local wrapper="$arg0_dir/codex-wrapper"
  if [ -x "$wrapper" ]; then
    pass "arg0 wrapper exists"
  else
    fail "arg0 wrapper missing or not executable: $wrapper"
    rc=1
  fi

  return "$rc"
}

sanitize_models_cache() {
  local cache="$HOME_CODEX/models_cache.json"
  [ -f "$cache" ] || return 0

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
' "$cache" "$POLICY_FILE"
}

run_repair() {
  mkdir -p "$HOME_CODEX" "$HOME_CODEX/rules"

  ensure_parent "$HOME_CODEX/config.toml"
  cp "$TEMPLATE_CONFIG" "$HOME_CODEX/config.toml"
  pass "restored home config.toml"

  ensure_parent "$HOME_CODEX/rules/default.rules"
  cp "$TEMPLATE_RULES" "$HOME_CODEX/rules/default.rules"
  pass "restored home default.rules"

  if [ -x "$SETUP_SCRIPT" ] || [ -f "$SETUP_SCRIPT" ]; then
    chmod +x "$SETUP_SCRIPT"
    bash "$SETUP_SCRIPT"
    pass "arg0 wrapper refreshed"
  else
    warn "setup script missing: $SETUP_SCRIPT"
  fi

  sanitize_models_cache
  pass "models cache sanitized"

  run_doctor
}

run_enforce() {
  if run_doctor; then
    pass "home codex guard: pass"
    return 0
  fi

  warn "home codex guard: fail -> applying repair"
  run_repair
}

run_snapshot() {
  mkdir -p "$SYNC_DIR"
  cp "$HOME_CODEX/config.toml" "$TEMPLATE_CONFIG"
  cp "$HOME_CODEX/rules/default.rules" "$TEMPLATE_RULES"
  pass "baseline snapshot refreshed from $HOME_CODEX"
}

cmd="${1:-}"
case "$cmd" in
  doctor) run_doctor ;;
  repair) run_repair ;;
  enforce) run_enforce ;;
  snapshot) run_snapshot ;;
  -h|--help|help|"") usage ;;
  *) usage; exit 1 ;;
esac
