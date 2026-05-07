#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODEX_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$CODEX_DIR/.." && pwd)"
MCP_FILE_DEFAULT="$PROJECT_ROOT/.vscode/mcp.json"
MEMORY_FILE="$CODEX_DIR/memory/memory.md"

usage() {
  cat <<USAGE
Agentic Hub CLI

Usage:
  bash .codex/tools/agentic-hub.sh doctor
  bash .codex/tools/agentic-hub.sh bootstrap [project-root]
  bash .codex/tools/agentic-hub.sh setup preflight
  bash .codex/tools/agentic-hub.sh evolve run <growth_objective> [mode] [risk_budget]
  bash .codex/tools/agentic-hub.sh evolve auto
  bash .codex/tools/agentic-hub.sh evolve auto-once
  bash .codex/tools/agentic-hub.sh evolve think-gate <plan_first|execute_first> [reason] [risk_level]
  bash .codex/tools/agentic-hub.sh evolve mode-show
  bash .codex/tools/agentic-hub.sh evolve mode-clear
  bash .codex/tools/agentic-hub.sh evolve conflict-flag set|clear|show
  bash .codex/tools/agentic-hub.sh intake <repo-url|local-path> [repo-url|local-path ...]
  bash .codex/tools/agentic-hub.sh sync [reports-dir]
  bash .codex/tools/agentic-hub.sh compact
  bash .codex/tools/agentic-hub.sh checkpoint --goal <text> --done <text> --next <text> [--blockers <text>]
  bash .codex/tools/agentic-hub.sh skill suggest <prompt text>
  bash .codex/tools/agentic-hub.sh skill list [category]
  bash .codex/tools/agentic-hub.sh body doctor|repair
  bash .codex/tools/agentic-hub.sh home guard doctor|repair|enforce|snapshot

  bash .codex/tools/agentic-hub.sh mcp list [mcp-file]
  bash .codex/tools/agentic-hub.sh mcp add-http <name> <url> [mcp-file]
  bash .codex/tools/agentic-hub.sh mcp add-stdio <name> <command> [arg ...] [--file <mcp-file>]

  bash .codex/tools/agentic-hub.sh connector list [mcp-file]
  bash .codex/tools/agentic-hub.sh connector add-http <name> <url> [mcp-file]
  bash .codex/tools/agentic-hub.sh connector add-stdio <name> <command> [arg ...] [--file <mcp-file>]
  bash .codex/tools/agentic-hub.sh connector preset claude-core [mcp-file]

  bash .codex/tools/agentic-hub.sh plugin note <name> <source>
  bash .codex/tools/agentic-hub.sh plugin import-openclaw <openclaw.plugin.json>
  bash .codex/tools/agentic-hub.sh plugin recommend buildwithclaude
  bash .codex/tools/agentic-hub.sh plugin recommend ariff

Examples:
  bash .codex/tools/agentic-hub.sh intake https://github.com/openai/skills https://github.com/Enderfga/openclaw-claude-code
  bash .codex/tools/agentic-hub.sh mcp add-http openaiDeveloperDocs https://developers.openai.com/mcp
  bash .codex/tools/agentic-hub.sh connector add-stdio codeReviewGraph .tools/code-review-graph-venv/bin/code-review-graph serve
  bash .codex/tools/agentic-hub.sh connector preset claude-core
  bash .codex/tools/agentic-hub.sh plugin import-openclaw .tmp/repo-intake/openclaw-claude-code-20260414-112001/openclaw.plugin.json
  bash .codex/tools/agentic-hub.sh plugin recommend buildwithclaude
  bash .codex/tools/agentic-hub.sh plugin recommend ariff
  bash .codex/tools/agentic-hub.sh skill suggest "fix regression auth and verify claim with citations"
  bash .codex/tools/agentic-hub.sh compact
  bash .codex/tools/agentic-hub.sh checkpoint --goal "Intake clawspring" --done "Parsed architecture" --next "Update skill" --blockers "-"
  bash .codex/tools/agentic-hub.sh body doctor
  bash .codex/tools/agentic-hub.sh setup preflight
  bash .codex/tools/agentic-hub.sh evolve run "upgrade routing precision" adaptive low
  bash .codex/tools/agentic-hub.sh evolve auto
  bash .codex/tools/agentic-hub.sh evolve think-gate plan_first "high_ambiguity" high
  bash .codex/tools/agentic-hub.sh evolve conflict-flag set
  bash .codex/tools/agentic-hub.sh home guard enforce
USAGE
}

ensure_file_parent() {
  local file="$1"
  mkdir -p "$(dirname "$file")"
}

append_memory_line_once() {
  local line="$1"
  ensure_file_parent "$MEMORY_FILE"
  if [ ! -f "$MEMORY_FILE" ]; then
    cat > "$MEMORY_FILE" <<'MD'
# Project Memory
MD
  fi
  if ! grep -Fq -- "$line" "$MEMORY_FILE"; then
    printf '%s\n' "$line" >> "$MEMORY_FILE"
  fi
}

ensure_mcp_file() {
  local mcp_file="$1"
  ensure_file_parent "$mcp_file"
  if [ ! -f "$mcp_file" ]; then
    cat > "$mcp_file" <<'JSON'
{
  "servers": {}
}
JSON
  fi
}

backup_file() {
  local file="$1"
  if [ -f "$file" ]; then
    cp "$file" "$file.bak.$(date +%Y%m%d%H%M%S)"
  fi
}

mcp_list() {
  local mcp_file="${1:-$MCP_FILE_DEFAULT}"
  if [ ! -f "$mcp_file" ]; then
    echo "[agentic-hub] mcp file not found: $mcp_file"
    return 1
  fi

  python3 - "$mcp_file" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
obj = json.loads(path.read_text())
servers = obj.get("servers", {})
if not servers:
    print("(no servers)")
    raise SystemExit(0)

for name in sorted(servers.keys()):
    cfg = servers[name]
    typ = cfg.get("type", "?")
    if typ == "http":
        detail = cfg.get("url", "")
    else:
        cmd = cfg.get("command", "")
        args = " ".join(cfg.get("args", []))
        detail = f"{cmd} {args}".strip()
    print(f"- {name} [{typ}] {detail}")
PY
}

mcp_add_http() {
  local name="$1"
  local url="$2"
  local mcp_file="${3:-$MCP_FILE_DEFAULT}"

  ensure_mcp_file "$mcp_file"
  backup_file "$mcp_file"

  python3 - "$mcp_file" "$name" "$url" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
name = sys.argv[2]
url = sys.argv[3]
obj = json.loads(path.read_text())
obj.setdefault("servers", {})
obj["servers"][name] = {
    "type": "http",
    "url": url,
}
path.write_text(json.dumps(obj, indent=2) + "\n")
print(f"[agentic-hub] upserted http MCP '{name}' -> {url}")
PY
}

mcp_add_stdio() {
  local name="$1"
  local command="$2"
  shift 2

  local mcp_file="$MCP_FILE_DEFAULT"
  local args=()
  while [ $# -gt 0 ]; do
    if [ "$1" = "--file" ]; then
      mcp_file="${2:-$MCP_FILE_DEFAULT}"
      shift 2
      continue
    fi
    args+=("$1")
    shift
  done

  ensure_mcp_file "$mcp_file"
  backup_file "$mcp_file"

  python3 - "$mcp_file" "$name" "$command" "${args[@]}" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
name = sys.argv[2]
command = sys.argv[3]
args = sys.argv[4:]
obj = json.loads(path.read_text())
obj.setdefault("servers", {})
obj["servers"][name] = {
    "type": "stdio",
    "command": command,
    "args": args,
}
path.write_text(json.dumps(obj, indent=2) + "\n")
print(f"[agentic-hub] upserted stdio MCP '{name}' -> {command} {' '.join(args)}")
PY
}

plugin_note() {
  local name="$1"
  local source="$2"
  local today
  today="$(date +%Y-%m-%d)"
  append_memory_line_once "- $name | $source | $today"
  echo "[agentic-hub] noted plugin reference: $name"
}

checkpoint_note() {
  local goal=""
  local done=""
  local next=""
  local blockers="-"

  while [ $# -gt 0 ]; do
    case "$1" in
      --goal)
        goal="${2:-}"
        shift 2
        ;;
      --done)
        done="${2:-}"
        shift 2
        ;;
      --next)
        next="${2:-}"
        shift 2
        ;;
      --blockers)
        blockers="${2:-}"
        shift 2
        ;;
      *)
        echo "[agentic-hub] unknown checkpoint arg: $1" >&2
        return 1
        ;;
    esac
  done

  if [ -z "$goal" ] || [ -z "$done" ] || [ -z "$next" ]; then
    echo "[agentic-hub] checkpoint requires --goal --done --next" >&2
    return 1
  fi

  local now
  now="$(date '+%Y-%m-%d %H:%M:%S %z')"
  append_memory_line_once "## Session Checkpoints"
  append_memory_line_once "- $now | goal: $goal | done: $done | next: $next | blockers: $blockers"
  echo "[agentic-hub] checkpoint saved into: $MEMORY_FILE"
}

smart_compact() {
  local script="$CODEX_DIR/tools/smart-compact.sh"
  if [ ! -x "$script" ]; then
    chmod +x "$script"
  fi
  echo "[agentic-hub] smart compact: pre-layer before native compact"
  echo "[agentic-hub] warning: native /compact does not run this pre-layer; use this command as standard path"
  "$script"
}

setup_preflight() {
  local script="$CODEX_DIR/skills/setup/scripts/codex-arg0-ensure.sh"
  if [ ! -x "$script" ]; then
    chmod +x "$script"
  fi
  echo "[agentic-hub] setup preflight: ensure codex arg0 wrapper + compact models cache"
  bash "$script"
}

evolve_run() {
  local script="$CODEX_DIR/tools/evolve-run.sh"
  if [ ! -x "$script" ]; then
    chmod +x "$script"
  fi
  if [ $# -lt 1 ]; then
    echo "[agentic-hub] evolve run requires: <growth_objective> [mode] [risk_budget]" >&2
    return 1
  fi
  bash "$script" "$@"
}

evolve_auto() {
  local script="$CODEX_DIR/tools/evolve-auto.sh"
  if [ ! -x "$script" ]; then
    chmod +x "$script"
  fi
  echo "[agentic-hub] evolve auto (conservative): one batch step per run"
  bash "$script"
}

evolve_auto_once() {
  local auto_script="$CODEX_DIR/tools/evolve-auto.sh"
  local mode_script="$CODEX_DIR/tools/think-mode-switch.sh"
  local state_file="$CODEX_DIR/reports/evolve-auto-state.json"

  if [ ! -x "$auto_script" ]; then
    chmod +x "$auto_script"
  fi
  if [ ! -x "$mode_script" ]; then
    chmod +x "$mode_script"
  fi

  # Non-interactive one-shot preset: execute first, long enough TTL for full A/B/C cycle.
  bash "$mode_script" oneshot "one_run_no_confirmation" "medium" "99" >/dev/null
  echo "[agentic-hub] evolve auto-once: oneshot mode applied (execute_first)"

  while true; do
    if ! bash "$auto_script"; then
      echo "[agentic-hub] evolve auto-once: stop on first error"
      echo "EVOLVE_AUTO_ONCE_STATUS=error"
      return 1
    fi

    if [ ! -f "$state_file" ]; then
      echo "[agentic-hub] evolve auto-once: missing state file $state_file"
      echo "EVOLVE_AUTO_ONCE_STATUS=error"
      return 1
    fi

    read -r halted next_idx <<<"$(python3 - <<'PY' "$state_file"
import json, sys
s=json.load(open(sys.argv[1], encoding="utf-8"))
print("true" if s.get("halted") else "false", int(s.get("next_batch_index", 0)))
PY
)"

    if [ "$halted" = "true" ]; then
      echo "[agentic-hub] evolve auto-once: halted by guard"
      echo "EVOLVE_AUTO_ONCE_STATUS=halted"
      return 0
    fi

    if [ "$next_idx" -gt 2 ]; then
      # Success policy: clear one-shot mode to avoid affecting next run.
      bash "$mode_script" clear >/dev/null
      echo "[agentic-hub] evolve auto-once: completed all batches and cleared mode switch"
      echo "EVOLVE_AUTO_ONCE_STATUS=completed"
      return 0
    fi
  done
}

evolve_think_gate() {
  local script="$CODEX_DIR/tools/think-mode-switch.sh"
  if [ ! -x "$script" ]; then
    chmod +x "$script"
  fi
  local desired="${1:-}"
  local reason="${2:-think_gate_decision}"
  local risk="${3:-medium}"
  if [ -z "$desired" ]; then
    echo "[agentic-hub] evolve think-gate requires: <plan_first|execute_first> [reason] [risk_level]" >&2
    return 1
  fi
  bash "$script" set "$desired" "$reason" "$risk"
}

evolve_mode_show() {
  local script="$CODEX_DIR/tools/think-mode-switch.sh"
  if [ ! -x "$script" ]; then
    chmod +x "$script"
  fi
  bash "$script" show
}

evolve_mode_clear() {
  local script="$CODEX_DIR/tools/think-mode-switch.sh"
  if [ ! -x "$script" ]; then
    chmod +x "$script"
  fi
  bash "$script" clear
}

evolve_conflict_flag() {
  local action="${1:-show}"
  local flag="$CODEX_DIR/reports/source-conflict-unresolved.flag"
  mkdir -p "$(dirname "$flag")"
  case "$action" in
    set)
      printf '%s\n' "unresolved_source_conflict $(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$flag"
      echo "$flag"
      ;;
    clear)
      rm -f "$flag"
      echo "cleared"
      ;;
    show)
      if [ -f "$flag" ]; then
        cat "$flag"
      else
        echo "not_set"
      fi
      ;;
    *)
      echo "[agentic-hub] evolve conflict-flag requires: set|clear|show" >&2
      return 1
      ;;
  esac
}

home_guard() {
  local script="$CODEX_DIR/tools/home-codex-guard.sh"
  local action="${1:-enforce}"
  if [ ! -x "$script" ]; then
    chmod +x "$script"
  fi
  bash "$script" "$action"
}

home_guard_auto_enforce() {
  local cmd="${1:-}"
  if [ "${AGENTIC_HUB_SKIP_HOME_GUARD:-0}" = "1" ]; then
    return 0
  fi
  if [ "$cmd" = "home" ]; then
    return 0
  fi
  local script="$CODEX_DIR/tools/home-codex-guard.sh"
  if [ -x "$script" ]; then
    bash "$script" enforce >/dev/null
  fi
}

connector_preset_claude_core() {
  local mcp_file="${1:-$MCP_FILE_DEFAULT}"
  echo "[agentic-hub] applying connector preset: claude-core"

  mcp_add_http "openaiDeveloperDocs" "https://developers.openai.com/mcp" "$mcp_file"
  mcp_add_stdio "context7" "npx" "-y" "@upstash/context7-mcp" "--file" "$mcp_file"
  mcp_add_stdio "filesystem" "npx" "-y" "@modelcontextprotocol/server-filesystem" "\${workspaceFolder}" "--file" "$mcp_file"
  mcp_add_stdio "git" "npx" "-y" "@modelcontextprotocol/server-git" "--repository" "\${workspaceFolder}" "--file" "$mcp_file"
  mcp_add_stdio "fetch" "npx" "-y" "@modelcontextprotocol/server-fetch" "--file" "$mcp_file"
  mcp_add_stdio "time" "npx" "-y" "@modelcontextprotocol/server-time" "--local-timezone=Asia/Pontianak" "--file" "$mcp_file"
  mcp_add_stdio "memory" "npx" "-y" "@modelcontextprotocol/server-memory" "--file" "$mcp_file"

  plugin_note "claude-core-connectors" "preset://claude-core"
  echo "[agentic-hub] preset applied into: $mcp_file"
}

plugin_import_openclaw() {
  local plugin_json="$1"
  if [ ! -f "$plugin_json" ]; then
    echo "[agentic-hub] openclaw plugin file not found: $plugin_json" >&2
    return 1
  fi

  local summary
  summary="$(python3 - "$plugin_json" <<'PY'
import json
import sys
from pathlib import Path

plugin_path = Path(sys.argv[1])
obj = json.loads(plugin_path.read_text())

plugin_id = obj.get("id", "unknown")
name = obj.get("name", "unknown")
tools = obj.get("contracts", {}).get("tools", [])
skills = obj.get("skills", [])
enabled = obj.get("enabledByDefault", False)
print(f"- openclaw-claude-code | id={plugin_id} | name={name} | enabled={enabled} | tools={len(tools)} | skills={len(skills)} | source={plugin_path}")
PY
)"

  plugin_note "openclaw-claude-code" "$plugin_json"
  append_memory_line_once "$summary"
  echo "[agentic-hub] imported openclaw plugin profile into memory"
}

plugin_recommend() {
  local source="${1:-}"
  case "$source" in
    buildwithclaude)
      cat <<'TXT'
[agentic-hub] recommended plugins (buildwithclaude)
1. codex-hud
   /plugin install codex-hud@buildwithclaude
2. cc-best
   /plugin install cc-best@buildwithclaude
3. shipwright
   /plugin install shipwright@buildwithclaude

Add marketplace first:
  /plugin marketplace add davepoon/buildwithclaude
TXT
      plugin_note "buildwithclaude-curated" "marketplace://davepoon/buildwithclaude"
      ;;
    ariff)
      cat <<'TXT'
[agentic-hub] recommended plugins (ariff-claude-plugins)
1. anti-hallucination suite (targeted)
   - hallucination-guard (hook)
   - answer-validator (hook)
   - truth-finder (agent)
   - answer-analyzer (agent)
   - anti-hallucination, cross-checker, source-verifier,
     confidence-scorer, citation-enforcer, uncertainty-detector,
     output-auditor, context-grounding (skills)

Marketplace (Claude REPL):
  /plugin marketplace add a-ariff/ariff-claude-plugins
TXT
      plugin_note "ariff-anti-hallucination-suite" "marketplace://a-ariff/ariff-claude-plugins"
      ;;
    *)
      echo "[agentic-hub] unknown recommendation source: $source" >&2
      return 1
      ;;
  esac
}

cmd="${1:-}"
if [ -z "$cmd" ]; then
  usage
  exit 1
fi
shift || true

home_guard_auto_enforce "$cmd"

case "$cmd" in
  doctor)
    echo "[agentic-hub] doctor"
    echo "- project: $PROJECT_ROOT"
    for bin in bash python3 git npx code codex; do
      if command -v "$bin" >/dev/null 2>&1; then
        echo "- $bin: OK"
      else
        echo "- $bin: missing"
      fi
    done
    if [ -f "$MCP_FILE_DEFAULT" ]; then
      echo "- mcp: $MCP_FILE_DEFAULT"
      mcp_list "$MCP_FILE_DEFAULT" || true
    else
      echo "- mcp: missing ($MCP_FILE_DEFAULT)"
    fi
    ;;
  bootstrap)
    target="${1:-$PROJECT_ROOT}"
    bash "$CODEX_DIR/bootstrap.sh" "$target"
    ;;
  setup)
    sub="${1:-preflight}"
    case "$sub" in
      preflight)
        setup_preflight
        ;;
      *)
        usage
        exit 1
        ;;
    esac
    ;;
  evolve)
    sub="${1:-run}"
    shift || true
    case "$sub" in
      run)
        evolve_run "$@"
        ;;
      auto)
        evolve_auto
        ;;
      auto-once)
        evolve_auto_once
        ;;
      think-gate)
        evolve_think_gate "$@"
        ;;
      mode-show)
        evolve_mode_show
        ;;
      mode-clear)
        evolve_mode_clear
        ;;
      conflict-flag)
        evolve_conflict_flag "${1:-show}"
        ;;
      *)
        usage
        exit 1
        ;;
    esac
    ;;
  intake)
    if [ $# -lt 1 ]; then
      usage
      exit 1
    fi
    bash "$SCRIPT_DIR/agentic-cli.sh" intake "$@"
    ;;
  sync)
    src="${1:-.tmp/repo-intake/reports}"
    bash "$SCRIPT_DIR/agentic-cli.sh" sync "$src"
    ;;
  compact)
    smart_compact
    ;;
  checkpoint)
    checkpoint_note "$@"
    ;;
  skill)
    sub="${1:-}"
    shift || true
    case "$sub" in
      suggest)
        if [ $# -lt 1 ]; then
          usage
          exit 1
        fi
        bash "$SCRIPT_DIR/skill-navigator.sh" suggest "$@"
        ;;
      list)
        bash "$SCRIPT_DIR/skill-navigator.sh" list "${1:-}"
        ;;
      *)
        usage
        exit 1
        ;;
    esac
    ;;
  body)
    sub="${1:-doctor}"
    case "$sub" in
      doctor|repair)
        bash "$SCRIPT_DIR/body-doctor.sh" "$sub"
        ;;
      *)
        usage
        exit 1
        ;;
    esac
    ;;
  home)
    sub="${1:-guard}"
    shift || true
    case "$sub" in
      guard)
        home_guard "${1:-enforce}"
        ;;
      *)
        usage
        exit 1
        ;;
    esac
    ;;
  mcp)
    sub="${1:-}"
    shift || true
    case "$sub" in
      list)
        mcp_list "${1:-$MCP_FILE_DEFAULT}"
        ;;
      add-http)
        if [ $# -lt 2 ]; then
          usage
          exit 1
        fi
        mcp_add_http "$1" "$2" "${3:-$MCP_FILE_DEFAULT}"
        ;;
      add-stdio)
        if [ $# -lt 2 ]; then
          usage
          exit 1
        fi
        mcp_add_stdio "$@"
        ;;
      preset)
        preset_name="${1:-}"
        case "$preset_name" in
          claude-core)
            connector_preset_claude_core "${2:-$MCP_FILE_DEFAULT}"
            ;;
          *)
            echo "[agentic-hub] unknown preset: $preset_name" >&2
            exit 1
            ;;
        esac
        ;;
      *)
        usage
        exit 1
        ;;
    esac
    ;;
  connector)
    # connector is an alias for MCP operations
    sub="${1:-}"
    shift || true
    case "$sub" in
      list)
        mcp_list "${1:-$MCP_FILE_DEFAULT}"
        ;;
      add-http)
        if [ $# -lt 2 ]; then
          usage
          exit 1
        fi
        mcp_add_http "$1" "$2" "${3:-$MCP_FILE_DEFAULT}"
        ;;
      add-stdio)
        if [ $# -lt 2 ]; then
          usage
          exit 1
        fi
        mcp_add_stdio "$@"
        ;;
      preset)
        preset_name="${1:-}"
        case "$preset_name" in
          claude-core)
            connector_preset_claude_core "${2:-$MCP_FILE_DEFAULT}"
            ;;
          *)
            echo "[agentic-hub] unknown preset: $preset_name" >&2
            exit 1
            ;;
        esac
        ;;
      *)
        usage
        exit 1
        ;;
    esac
    ;;
  plugin)
    sub="${1:-}"
    shift || true
    case "$sub" in
      note)
        if [ $# -lt 2 ]; then
          usage
          exit 1
        fi
        plugin_note "$1" "$2"
        ;;
      import-openclaw)
        if [ $# -lt 1 ]; then
          usage
          exit 1
        fi
        plugin_import_openclaw "$1"
        ;;
      recommend)
        if [ $# -lt 1 ]; then
          usage
          exit 1
        fi
        plugin_recommend "$1"
        ;;
      *)
        usage
        exit 1
        ;;
    esac
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    usage
    exit 1
    ;;
esac
