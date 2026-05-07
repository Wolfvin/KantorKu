#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

SKILLS_DIR=".codex/skills"
MEMORY_DIR=".codex/memory"
MEMORY_FILE="$MEMORY_DIR/memory.md"
MAP_FILE=".codex/tools/skill-map.tsv"

usage() {
  cat <<'USAGE'
Usage:
  bash .codex/tools/body-doctor.sh doctor
  bash .codex/tools/body-doctor.sh repair
USAGE
}

pass() { printf "[PASS] %s\n" "$1"; }
warn() { printf "[WARN] %s\n" "$1"; }
fail() { printf "[FAIL] %s\n" "$1"; }

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

list_skills() {
  find "$SKILLS_DIR" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort
}

rebuild_skill_map() {
  mkdir -p "$(dirname "$MAP_FILE")"
  declare -A old_cat=()
  declare -A old_kw=()
  if [ -f "$MAP_FILE" ]; then
    while IFS=$'\t' read -r skill category keywords; do
      [ -n "${skill:-}" ] || continue
      [ "$skill" = "skill" ] && continue
      old_cat["$skill"]="${category:-general}"
      old_kw["$skill"]="${keywords:-}"
    done < "$MAP_FILE"
  fi

  {
    echo -e "skill\tcategory\tkeywords"
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
  [ -f "$MEMORY_FILE" ] || printf "# Memory Index (Smart Compact v1)\n\n" > "$MEMORY_FILE"
  [ -f "$MEMORY_DIR/backend.md" ] || printf "# Topic: backend\n\n" > "$MEMORY_DIR/backend.md"
  pass "memory staging layout ready (memory.md + backend.md)"
}

run_doctor() {
  local rc=0

  if [ ! -f "$MEMORY_FILE" ]; then
    fail "missing $MEMORY_FILE"
    rc=1
  else
    pass "memory file exists"
  fi

  local missing=0
  while IFS= read -r skill; do
    [ -n "$skill" ] || continue
    local sdir="$SKILLS_DIR/$skill"
    if [ ! -f "$sdir/SKILL.md" ]; then
      fail "missing $sdir/SKILL.md"
      missing=$((missing + 1))
    fi
    if [ ! -f "$sdir/agents/openai.yaml" ]; then
      fail "missing $sdir/agents/openai.yaml"
      missing=$((missing + 1))
    fi
  done < <(list_skills)
  if [ "$missing" -eq 0 ]; then
    pass "all skills have SKILL.md and agents/openai.yaml"
  else
    rc=1
  fi

  if [ -f "$MAP_FILE" ]; then
    pass "skill map exists ($MAP_FILE)"
  else
    fail "missing $MAP_FILE"
    rc=1
  fi

  local topics
  topics="$(find "$MEMORY_DIR" -maxdepth 1 -type f -name '*.md' ! -name 'memory.md' | wc -l | tr -d ' ')"
  if [ "$topics" -ge 1 ]; then
    pass "multi-file memory staging clean (topics=$topics)"
  else
    warn "no topic memory files detected"
    rc=1
  fi

  if bash .codex/tools/skill-routing-smoke.sh >/dev/null 2>&1; then
    pass "skill-routing-smoke passed"
  else
    fail "skill-routing-smoke failed"
    rc=1
  fi

  if bash .codex/tools/agentic-hub.sh doctor >/dev/null 2>&1; then
    pass "agentic-hub doctor passed"
  else
    fail "agentic-hub doctor failed"
    rc=1
  fi

  return "$rc"
}

run_repair() {
  mkdir -p "$SKILLS_DIR" "$MEMORY_DIR"

  while IFS= read -r skill; do
    [ -n "$skill" ] || continue
    local sdir="$SKILLS_DIR/$skill"
    if [ ! -f "$sdir/SKILL.md" ]; then
      warn "skip $skill (missing SKILL.md)"
      continue
    fi
    if [ ! -f "$sdir/agents/openai.yaml" ]; then
      mkdir -p "$sdir/agents"
      create_default_openai_yaml "$sdir"
      pass "created $sdir/agents/openai.yaml"
    fi
  done < <(list_skills)

  rebuild_skill_map
  pass "rebuilt $MAP_FILE"

  ensure_memory_staging_layout

  run_doctor
}

cmd="${1:-}"
case "$cmd" in
  doctor) run_doctor ;;
  repair) run_repair ;;
  -h|--help|help|"") usage ;;
  *)
    usage
    exit 1
    ;;
esac
