#!/usr/bin/env bash
set -euo pipefail

REMOTE="origin"
BRANCH=""
MODE="ff"
WARNING_ACK="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --remote) REMOTE="${2:-}"; shift 2 ;;
    --branch) BRANCH="${2:-}"; shift 2 ;;
    --mode) MODE="${2:-}"; shift 2 ;;
    --yes-warning) WARNING_ACK="true"; shift ;;
    *) echo "unknown arg: $1"; exit 2 ;;
  esac
done

if [[ -z "$BRANCH" ]]; then
  BRANCH="$(git rev-parse --abbrev-ref HEAD)"
fi

if [[ "$MODE" != "ff" && "$MODE" != "force" ]]; then
  echo "[github-skill] mode must be ff or force"
  exit 2
fi

if [[ "$WARNING_ACK" != "true" ]]; then
  echo "[github-skill] warning acknowledgement required"
  echo "!! repo kamu akan sama persis dengan struktur proyek dan perubahan saat ini !!"
  echo "rerun with --yes-warning"
  exit 2
fi

git fetch "$REMOTE"

if git show-ref --quiet "refs/remotes/$REMOTE/$BRANCH"; then
  counts="$(git rev-list --left-right --count "$BRANCH...$REMOTE/$BRANCH")"
  ahead="$(awk '{print $1}' <<<"$counts")"
  behind="$(awk '{print $2}' <<<"$counts")"
else
  ahead="0"
  behind="0"
fi

echo "!! repo kamu akan sama persis dengan struktur proyek dan perubahan saat ini !!"
echo "[github-skill] branch=$BRANCH remote=$REMOTE mode=$MODE ahead=$ahead behind=$behind"

if [[ "$MODE" == "ff" ]]; then
  if [[ "$behind" -gt 0 ]]; then
    echo "[github-skill] remote has commits not in local. no-merge policy blocks ff push."
    echo "choose: reset local to remote, or rerun with --mode force after user approval"
    exit 1
  fi
  git push "$REMOTE" "$BRANCH"
else
  git push --force-with-lease "$REMOTE" "$BRANCH"
fi
