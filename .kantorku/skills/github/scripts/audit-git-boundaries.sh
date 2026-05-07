#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "${ROOT}" ]]; then
  echo "[github-skill] not inside a git repository"
  exit 2
fi

cd "$ROOT"

mapfile -t nested_git_markers < <(find "$ROOT" -mindepth 2 \( -type d -name .git -o -type f -name .git \) 2>/dev/null | sort)

if [[ ${#nested_git_markers[@]} -eq 0 ]]; then
  echo "[github-skill] no nested git repositories detected"
  exit 0
fi

echo "[github-skill] nested git repositories detected:"
for marker in "${nested_git_markers[@]}"; do
  dir="$(dirname "$marker")"
  rel="${dir#"$ROOT"/}"

  mode="nested-git-init"
  stage_line="$(git ls-files --stage -- "$rel" | head -n1 || true)"
  if [[ -n "${stage_line}" ]]; then
    stage_mode="$(awk '{print $1}' <<<"$stage_line")"
    if [[ "$stage_mode" == "160000" ]]; then
      mode="git-submodule"
    fi
  fi

  echo "- $rel ($mode)"
  echo "  folder $rel tidak masuk, apakah mau masukkan?"

done

exit 1
