#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODEX_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
STATE_FILE="$CODEX_DIR/reports/think-mode-switch.json"

usage() {
  cat <<USAGE
Usage:
  bash .codex/tools/think-mode-switch.sh set <plan_first|execute_first> [reason] [risk_level]
  bash .codex/tools/think-mode-switch.sh oneshot [reason] [risk_level] [expires_after_step]
  bash .codex/tools/think-mode-switch.sh show
  bash .codex/tools/think-mode-switch.sh clear
USAGE
}

cmd="${1:-}"
shift || true

mkdir -p "$(dirname "$STATE_FILE")"

case "$cmd" in
  set)
    mode="${1:-}"
    reason="${2:-think_gate_decision}"
    risk="${3:-medium}"
    if [[ "$mode" != "plan_first" && "$mode" != "execute_first" ]]; then
      echo "mode must be plan_first or execute_first" >&2
      exit 1
    fi
    python3 - <<'PY' "$STATE_FILE" "$mode" "$reason" "$risk"
import json, sys, datetime
path, mode, reason, risk = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
doc = {
  "desired_mode": mode,
  "reason": reason,
  "risk_level": risk,
  "source": "think",
  "expires_after_step": 1,
  "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
}
with open(path, "w", encoding="utf-8") as f:
  json.dump(doc, f)
print(path)
PY
    ;;
  oneshot)
    reason="${1:-one_run_no_confirmation}"
    risk="${2:-medium}"
    expires="${3:-99}"
    if ! [[ "$expires" =~ ^[0-9]+$ ]] || [ "$expires" -lt 1 ]; then
      echo "expires_after_step must be integer >= 1" >&2
      exit 1
    fi
    python3 - <<'PY' "$STATE_FILE" "$reason" "$risk" "$expires"
import json, sys, datetime
path, reason, risk, expires = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
doc = {
  "desired_mode": "execute_first",
  "reason": reason,
  "risk_level": risk,
  "source": "think_oneshot",
  "expires_after_step": expires,
  "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
}
with open(path, "w", encoding="utf-8") as f:
  json.dump(doc, f)
print(path)
PY
    ;;
  show)
    if [ -f "$STATE_FILE" ]; then
      cat "$STATE_FILE"
    else
      echo "{}"
    fi
    ;;
  clear)
    rm -f "$STATE_FILE"
    echo "cleared"
    ;;
  *)
    usage
    exit 1
    ;;
esac
