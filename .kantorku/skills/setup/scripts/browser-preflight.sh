#!/usr/bin/env bash
set -euo pipefail

ok() { echo "[ok] $*"; }
warn() { echo "[warn] $*"; }
fail() { echo "[fail] $*"; }

has_agent_browser=false
has_lightpanda=false
cdp_ready=false

if command -v agent-browser >/dev/null 2>&1; then
  has_agent_browser=true
  ok "agent-browser found: $(command -v agent-browser)"
else
  warn "agent-browser not found in PATH"
fi

if command -v lightpanda >/dev/null 2>&1; then
  has_lightpanda=true
  ok "lightpanda found: $(command -v lightpanda)"
else
  warn "lightpanda not found in PATH"
fi

if command -v curl >/dev/null 2>&1; then
  if curl -fsS --max-time 2 http://127.0.0.1:9222/json/version >/dev/null 2>&1; then
    cdp_ready=true
    ok "CDP endpoint ready at 127.0.0.1:9222"
  else
    warn "CDP endpoint not ready at 127.0.0.1:9222"
  fi
else
  warn "curl not found, skipping CDP check"
fi

mcp_file=".vscode/mcp.json"
if [[ -f "$mcp_file" ]]; then
  if rg -n '"lightpanda"|agent-browser|browser' "$mcp_file" >/dev/null 2>&1; then
    ok "browser-related MCP entry found in $mcp_file"
  else
    warn "no browser-related MCP entry found in $mcp_file"
  fi
else
  warn "$mcp_file not found"
fi

echo "---- summary ----"
echo "agent_browser: $has_agent_browser"
echo "lightpanda: $has_lightpanda"
echo "cdp_ready: $cdp_ready"

if [[ "$has_agent_browser" == "false" && "$has_lightpanda" == "false" ]]; then
  fail "no browser automation runtime detected"
  exit 1
fi

ok "browser preflight complete"
