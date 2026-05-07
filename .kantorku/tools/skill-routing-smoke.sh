#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

pass() { printf "[PASS] %s\n" "$1"; }
fail() { printf "[FAIL] %s\n" "$1"; exit 1; }

check_file() {
  local f="$1"
  [[ -f "$f" ]] || fail "missing file: $f"
}

check_contains() {
  local f="$1"
  local p="$2"
  rg -q "$p" "$f" || fail "$f missing pattern: $p"
}

check_file ".codex/AGENTS.md"
check_file ".codex/skills/skill-router/SKILL.md"
check_file ".codex/skills/think/SKILL.md"
check_file ".codex/skills/inject/SKILL.md"

if [[ -f "AGENTS.md" ]]; then
  check_contains "AGENTS.md" "think"
  check_contains "AGENTS.md" "skill-router"
  pass "AGENTS gate skill-router + think"
else
  pass "AGENTS.md optional (not present in this repo root)"
fi

check_contains ".codex/AGENTS.md" "think"
check_contains ".codex/AGENTS.md" "skill-router"
pass ".codex/AGENTS gate skill-router + think"

check_contains ".codex/skills/skill-router/SKILL.md" "Canonical Owner Map"
check_contains ".codex/skills/skill-router/SKILL.md" "inject"
pass "skill-router canonical owner map"

check_contains ".codex/skills/inject/SKILL.md" "name: inject"
pass "hyphen-case skill names"

echo "Routing smoke test OK."
