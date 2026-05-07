#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-server_lokal/src}"

violations=$(rg -n "Connection::open\(" "$ROOT" -S \
  | rg -v "src/storage/sqlite.rs" \
  || true)

if [[ -n "$violations" ]]; then
  echo "[FAIL] direct Connection::open found outside storage/sqlite.rs"
  echo "$violations"
  exit 1
fi

echo "[PASS] sqlite boundary open-check"
