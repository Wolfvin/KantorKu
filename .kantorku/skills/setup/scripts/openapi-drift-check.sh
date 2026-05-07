#!/usr/bin/env bash
set -euo pipefail

url=""
state_file=""
timeout="20"

usage() {
  cat <<'EOF'
Usage:
  openapi-drift-check.sh --url <openapi-url> --state-file <path> [--timeout <seconds>]

Output:
  status=pass      (no change)
  status=changed   (fingerprint changed)
  status=fail      (request/hash failure)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --url) url="${2:-}"; shift 2 ;;
    --state-file) state_file="${2:-}"; shift 2 ;;
    --timeout) timeout="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -z "$url" || -z "$state_file" ]]; then
  echo "Missing required args" >&2
  usage >&2
  exit 2
fi

tmp_payload="$(mktemp)"
trap 'rm -f "$tmp_payload"' EXIT

if ! curl -fsSL --max-time "$timeout" "$url" -o "$tmp_payload"; then
  echo "status=fail"
  echo "reason=request_failed"
  exit 1
fi

hash_payload() {
  local file="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$file" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$file" | awk '{print $1}'
  elif command -v openssl >/dev/null 2>&1; then
    openssl dgst -sha256 "$file" | awk '{print $NF}'
  else
    return 1
  fi
}

if ! new_hash="$(hash_payload "$tmp_payload")"; then
  echo "status=fail"
  echo "reason=hash_tool_missing"
  exit 1
fi

mkdir -p "$(dirname "$state_file")"
if [[ ! -f "$state_file" ]]; then
  printf "%s\n" "$new_hash" > "$state_file"
  echo "status=changed"
  echo "reason=initialized_state"
  echo "fingerprint=$new_hash"
  echo "state_file=$state_file"
  exit 0
fi

old_hash="$(tr -d '[:space:]' < "$state_file")"

if [[ "$old_hash" == "$new_hash" ]]; then
  echo "status=pass"
  echo "fingerprint=$new_hash"
  echo "state_file=$state_file"
  exit 0
fi

printf "%s\n" "$new_hash" > "$state_file"
echo "status=changed"
echo "old_fingerprint=$old_hash"
echo "new_fingerprint=$new_hash"
echo "state_file=$state_file"
