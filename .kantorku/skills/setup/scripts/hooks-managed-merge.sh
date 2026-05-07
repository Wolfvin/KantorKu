#!/usr/bin/env bash
set -euo pipefail

hooks_file=""
managed_key=""
managed_cmd=""

usage() {
  cat <<'EOF'
Usage:
  hooks-managed-merge.sh \
    --hooks-file <path> \
    --managed-key <key> \
    --managed-cmd <command>

Behavior:
- Preserves all non-managed entries.
- Upserts one managed wrapper entry identified by `managed_key`.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --hooks-file) hooks_file="${2:-}"; shift 2 ;;
    --managed-key) managed_key="${2:-}"; shift 2 ;;
    --managed-cmd) managed_cmd="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -z "$hooks_file" || -z "$managed_key" || -z "$managed_cmd" ]]; then
  echo "Missing required args" >&2
  usage >&2
  exit 2
fi

mkdir -p "$(dirname "$hooks_file")"

python3 - "$hooks_file" "$managed_key" "$managed_cmd" <<'PY'
import json
import os
import sys
from typing import Any

path, key, cmd = sys.argv[1], sys.argv[2], sys.argv[3]

def default_doc() -> dict[str, Any]:
    return {"hooks": []}

if os.path.exists(path):
    raw = open(path, "r", encoding="utf-8").read().strip()
    if raw:
        try:
            doc = json.loads(raw)
        except Exception as e:
            print(f"status=fail\nreason=invalid_json:{e}")
            sys.exit(1)
    else:
        doc = default_doc()
else:
    doc = default_doc()

if isinstance(doc, list):
    doc = {"hooks": doc}
elif isinstance(doc, dict):
    if "hooks" not in doc or not isinstance(doc["hooks"], list):
        doc["hooks"] = []
else:
    print("status=fail\nreason=invalid_root_type")
    sys.exit(1)

hooks = doc["hooks"]
kept = []
for h in hooks:
    if not isinstance(h, dict):
        continue
    if h.get("managed_key") == key:
        continue
    kept.append(h)

managed = {
    "managed_key": key,
    "event": "*",
    "command": cmd,
    "enabled": True,
}
kept.append(managed)
doc["hooks"] = kept

tmp = f"{path}.tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=2)
    f.write("\n")
os.replace(tmp, path)

print("status=pass")
print(f"hooks_file={path}")
print(f"managed_key={key}")
print(f"managed_count={sum(1 for h in doc['hooks'] if isinstance(h, dict) and h.get('managed_key') == key)}")
PY
