#!/usr/bin/env bash
set -euo pipefail

build=""
snapshot=""
classification=""
severity=""
summary=""
evidence=""
fallback="none"

usage() {
  cat <<'EOF'
Usage:
  visual-triage-report.sh \
    --build <build-id> \
    --snapshot <snapshot-id> \
    --classification <irregular|valid> \
    --severity <high|medium|low> \
    --summary <text> \
    --evidence <url-or-path> \
    [--fallback <none|standard_diff|manual_review>]
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --build) build="${2:-}"; shift 2 ;;
    --snapshot) snapshot="${2:-}"; shift 2 ;;
    --classification) classification="${2:-}"; shift 2 ;;
    --severity) severity="${2:-}"; shift 2 ;;
    --summary) summary="${2:-}"; shift 2 ;;
    --evidence) evidence="${2:-}"; shift 2 ;;
    --fallback) fallback="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -z "$build" || -z "$snapshot" || -z "$classification" || -z "$severity" || -z "$summary" || -z "$evidence" ]]; then
  echo "Missing required args" >&2
  usage >&2
  exit 2
fi

case "$classification" in
  irregular|valid) ;;
  *) echo "Invalid --classification: $classification" >&2; exit 2 ;;
esac

case "$severity" in
  high|medium|low) ;;
  *) echo "Invalid --severity: $severity" >&2; exit 2 ;;
esac

case "$fallback" in
  none|standard_diff|manual_review) ;;
  *) echo "Invalid --fallback: $fallback" >&2; exit 2 ;;
esac

cat <<EOF
mode=visual_triage
build=$build
snapshot=$snapshot
classification=$classification
severity=$severity
summary=$summary
evidence=$evidence
fallback=$fallback
status=ready
EOF
