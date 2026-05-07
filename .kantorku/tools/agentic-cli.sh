#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODEX_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$CODEX_DIR/.." && pwd)"
TMP_ROOT="$PROJECT_ROOT/.tmp/repo-intake"
REPORT_DIR="$TMP_ROOT/reports"

usage() {
  cat <<USAGE
Usage:
  bash .codex/tools/agentic-cli.sh intake [--keep] <repo-url|local-path> [repo-url|local-path ...]
  bash .codex/tools/agentic-cli.sh sync <source-dir>

Examples:
  bash .codex/tools/agentic-cli.sh intake https://github.com/openai/skills
  bash .codex/tools/agentic-cli.sh intake --keep https://github.com/openai/skills
  bash .codex/tools/agentic-cli.sh intake https://github.com/openai/skills https://github.com/Enderfga/openclaw-claude-code
  bash .codex/tools/agentic-cli.sh sync .tmp/repo-intake/reports
USAGE
}

cmd="${1:-}"
shift || true

if [ -z "$cmd" ]; then
  usage
  exit 1
fi

case "$cmd" in
  intake)
    if [ $# -lt 1 ]; then
      usage
      exit 1
    fi
    keep_flag=false
    inputs=()
    while [ $# -gt 0 ]; do
      case "$1" in
        --keep)
          keep_flag=true
          shift
          ;;
        *)
          inputs+=("$1")
          shift
          ;;
      esac
    done
    if [ ${#inputs[@]} -lt 1 ]; then
      usage
      exit 1
    fi

    ts="$(date +%Y%m%d-%H%M%S)"
    report_root="$REPORT_DIR"
    mkdir -p "$report_root"
    summary="$report_root/summary_$ts.md"
    synth="$report_root/synthesis_$ts.md"

    echo "# Multi Repo Intake Summary" > "$summary"
    echo "" >> "$summary"
    echo "- Generated: $ts" >> "$summary"
    echo "- Workspace: $PROJECT_ROOT" >> "$summary"
    echo "" >> "$summary"
    echo "## Sources" >> "$summary"

    for url in "${inputs[@]}"; do
      echo "[agentic-cli] intake $url"
      intake_output="$(
        if [ "$keep_flag" = true ]; then
          bash "$SCRIPT_DIR/repo-intake-cli.sh" "$url" --keep
        else
          bash "$SCRIPT_DIR/repo-intake-cli.sh" "$url"
        fi
      )"
      report_path="$(printf '%s\n' "$intake_output" | awk -F': ' '/report:/{print $2}' | tail -n 1)"
      workdir_path="$(printf '%s\n' "$intake_output" | awk -F': ' '/workdir:/{print $2}' | tail -n 1)"
      clone_path="$(printf '%s\n' "$intake_output" | awk -F': ' '/clone_path:/{print $2}' | tail -n 1)"
      if [ -n "$report_path" ]; then
        echo "- $url" >> "$summary"
        echo "  - Report: $report_path" >> "$summary"
        [ -n "$workdir_path" ] && echo "  - Workdir: $workdir_path" >> "$summary"
        [ -n "$clone_path" ] && echo "  - ClonePath: $clone_path" >> "$summary"
      else
        echo "- $url" >> "$summary"
        echo "  - Report: (unknown)" >> "$summary"
      fi
    done

    cat > "$synth" <<SYNTH
# Intake Synthesis

## Guidance
- Keep only high-signal patterns that improve agentic coding quality.
- Prefer official/curated sources when available.
- Do not import leaked or questionable IP.

## Next Steps
- Curate reports listed in summary into:
  - .codex/skills/*
  - .codex/README.md
  - .codex/memory/memory.md + .codex/memory/<topic>.md
SYNTH

    echo "[agentic-cli] summary: $summary"
    echo "[agentic-cli] synthesis: $synth"
    echo "[agentic-cli] reports saved in $report_root"
    ;;
  sync)
    src="${1:-}"
    if [ -z "$src" ]; then
      usage
      exit 1
    fi
    mkdir -p "$REPORT_DIR"
    cp -f "$src"/*.md "$REPORT_DIR/" 2>/dev/null || true
    echo "[agentic-cli] synced reports into $REPORT_DIR"
    ;;
  *)
    usage
    exit 1
    ;;
esac
