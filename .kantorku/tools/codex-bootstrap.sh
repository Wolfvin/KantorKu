#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${1:-$(cd "$SCRIPT_DIR/.." && pwd)}"
PROJECT_NAME="$(basename "$PROJECT_ROOT")"
CODE_REVIEW_GRAPH_CMD="$PROJECT_ROOT/.tools/code-review-graph-venv/bin/code-review-graph"
CODEX_USER_DIR="$HOME/.codex"
HAS_CODEX_CLI=false
if command -v codex >/dev/null 2>&1; then
  HAS_CODEX_CLI=true
fi

if ! command -v npx >/dev/null 2>&1; then
  echo "Error: npx tidak ditemukan di PATH." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 tidak ditemukan di PATH." >&2
  exit 1
fi

install_vscode_extensions() {
  if ! command -v code >/dev/null 2>&1; then
    echo "[skip] command 'code' tidak tersedia. Lewati install extension VS Code."
    return
  fi

  echo "[1/5] Install extension VS Code"
  local required_extensions=(
    "openai.chatgpt"
    "eamodio.gitlens"
    "dbaeumer.vscode-eslint"
    "esbenp.prettier-vscode"
    "usernamehw.errorlens"
  )

  local optional_extension_candidates=(
    "GitHub.copilot"
    "github.copilot"
  )

  for ext in "${required_extensions[@]}"; do
    if code --list-extensions | grep -Fxiq "$ext"; then
      echo "  - $ext (sudah terpasang)"
    else
      echo "  - install $ext"
      if ! code --install-extension "$ext"; then
        echo "  ! warning: gagal install $ext, lanjut ke extension berikutnya"
      fi
    fi
  done

  local copilot_installed=false
  for ext in "${optional_extension_candidates[@]}"; do
    if code --list-extensions | grep -Fxiq "$ext"; then
      echo "  - $ext (sudah terpasang)"
      copilot_installed=true
      break
    fi

    echo "  - coba install $ext"
    if code --install-extension "$ext"; then
      copilot_installed=true
      break
    fi
  done

  if [ "$copilot_installed" = false ]; then
    echo "  ! warning: GitHub Copilot tidak tersedia di marketplace editor ini. Lewati."
  fi
}

upsert_mcp() {
  local name="$1"
  shift

  if codex mcp get "$name" >/dev/null 2>&1; then
    echo "  - update MCP '$name'"
    codex mcp remove "$name"
  else
    echo "  - add MCP '$name'"
  fi

  codex mcp add "$name" -- "$@"
}

install_code_review_graph() {
  echo "[2/5] Install code-review-graph (venv lokal project)"
  mkdir -p "$PROJECT_ROOT/.tools"
  python3 -m venv "$PROJECT_ROOT/.tools/code-review-graph-venv"
  "$PROJECT_ROOT/.tools/code-review-graph-venv/bin/pip" install --upgrade pip
  "$PROJECT_ROOT/.tools/code-review-graph-venv/bin/pip" install code-review-graph
}

link_project_skills() {
  echo "[3/5] Link project skills ke ~/.codex/skills (best effort)"
  mkdir -p "$CODEX_USER_DIR/skills"

  local skills_root="$SCRIPT_DIR/skills"
  if [ ! -d "$skills_root" ]; then
    echo "  - skip: folder skills tidak ada di $skills_root"
    return
  fi

  local linked=0
  for skill_dir in "$skills_root"/*; do
    if [ ! -d "$skill_dir" ]; then
      continue
    fi

    local skill_name
    skill_name="$(basename "$skill_dir")"
    local target="$CODEX_USER_DIR/skills/$skill_name"

    if [ -L "$target" ] || [ -d "$target" ]; then
      echo "  - skip: $skill_name sudah ada di ~/.codex/skills"
      continue
    fi

    ln -s "$skill_dir" "$target"
    linked=$((linked + 1))
    echo "  - linked: $skill_name"
  done

  echo "  - total linked: $linked"
}

initialize_memory() {
  echo "[4/5] Inisialisasi .codex/memory/memory.md"
  local memory_file="$SCRIPT_DIR/memory/memory.md"
  if [ ! -f "$memory_file" ]; then
    echo "  - skip: memory.md tidak ditemukan"
    return
  fi

  local stack=""
  if [ -f "$PROJECT_ROOT/package.json" ]; then
    stack="$stack Node.js"
  fi
  if [ -f "$PROJECT_ROOT/Cargo.toml" ]; then
    stack="$stack Rust"
  fi
  if [ -f "$PROJECT_ROOT/tauri.conf.json" ] || [ -f "$PROJECT_ROOT/src-tauri/tauri.conf.json" ]; then
    stack="$stack Tauri"
  fi
  stack="$(echo "$stack" | xargs)"
  if [ -z "$stack" ]; then
    stack="Unknown"
  fi

  local today
  today="$(date '+%Y-%m-%d')"

  sed -i "s/Name: (fill after bootstrap)/Name: $PROJECT_NAME/" "$memory_file" || true
  sed -i "s/Stack: (fill after bootstrap)/Stack: $stack/" "$memory_file" || true
  sed -i "s/Last updated: (fill after bootstrap)/Last updated: $today/" "$memory_file" || true

  echo "  - updated project memory ($today)"
}

configure_mcp_servers() {
  if [ "$HAS_CODEX_CLI" = true ]; then
    echo "[5/5] Konfigurasi MCP server via Codex CLI"
    upsert_mcp context7 npx -y @upstash/context7-mcp
    upsert_mcp filesystem npx -y @modelcontextprotocol/server-filesystem "$PROJECT_ROOT"
    upsert_mcp git npx -y @modelcontextprotocol/server-git --repository "$PROJECT_ROOT"
    upsert_mcp fetch npx -y @modelcontextprotocol/server-fetch
    upsert_mcp time npx -y @modelcontextprotocol/server-time --local-timezone=Asia/Pontianak
    upsert_mcp memory npx -y @modelcontextprotocol/server-memory
    upsert_mcp tauri npx -y @hypothesi/tauri-mcp-server
    upsert_mcp codeReviewGraph "$CODE_REVIEW_GRAPH_CMD" serve
    return
  fi

  echo "[5/5] Konfigurasi MCP server via .vscode/mcp.json (tanpa Codex CLI)"
  mkdir -p "$PROJECT_ROOT/.vscode"

  local mcp_file="$PROJECT_ROOT/.vscode/mcp.json"
  if [ -f "$mcp_file" ]; then
    local backup_file="$mcp_file.bak.$(date +%Y%m%d%H%M%S)"
    cp "$mcp_file" "$backup_file"
    echo "  - existing mcp.json dibackup ke: $backup_file"
  fi

  cat > "$mcp_file" <<EOM
{
  "servers": {
    "context7": {
      "type": "stdio",
      "command": "npx",
      "args": [
        "-y",
        "@upstash/context7-mcp"
      ]
    },
    "openaiDeveloperDocs": {
      "type": "http",
      "url": "https://developers.openai.com/mcp"
    },
    "filesystem": {
      "type": "stdio",
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "\${workspaceFolder}"
      ]
    },
    "git": {
      "type": "stdio",
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-git",
        "--repository",
        "\${workspaceFolder}"
      ]
    },
    "fetch": {
      "type": "stdio",
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-fetch"
      ]
    },
    "time": {
      "type": "stdio",
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-time",
        "--local-timezone=Asia/Pontianak"
      ]
    },
    "memory": {
      "type": "stdio",
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-memory"
      ]
    },
    "tauri": {
      "type": "stdio",
      "command": "npx",
      "args": [
        "-y",
        "@hypothesi/tauri-mcp-server"
      ]
    },
    "codeReviewGraph": {
      "type": "stdio",
      "command": "$CODE_REVIEW_GRAPH_CMD",
      "args": [
        "serve"
      ]
    }
  }
}
EOM
  echo "  - write: $mcp_file"
}

verify_setup() {
  echo "[done] Verifikasi"
  if [ "$HAS_CODEX_CLI" = true ]; then
    codex mcp list
  else
    echo "  - codex CLI tidak tersedia, cek file konfigurasi:"
    echo "    $PROJECT_ROOT/.vscode/mcp.json"
  fi
}

echo "Bootstrap start"
echo "- Project root: $PROJECT_ROOT"

if [ ! -d "$PROJECT_ROOT" ]; then
  echo "Error: project root '$PROJECT_ROOT' tidak ditemukan." >&2
  exit 1
fi

install_vscode_extensions
install_code_review_graph
link_project_skills
initialize_memory
configure_mcp_servers
verify_setup

echo "[done] Selesai"
echo "Selesai. Reload VS Code window agar MCP server kebaca ulang."
echo "Smart compact standard command: bash .codex/tools/agentic-hub.sh compact"
echo "Warning: native /compact runtime tidak melewati smart compact pre-layer."
