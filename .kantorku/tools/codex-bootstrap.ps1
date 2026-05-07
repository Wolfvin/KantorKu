Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$CliArgs = @($args)

function Require-Command {
  param([Parameter(Mandatory = $true)][string]$Name)
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Error: $Name tidak ditemukan di PATH."
  }
}

function Install-VSCodeExtensions {
  $codeCmd = Get-Command code -ErrorAction SilentlyContinue
  if (-not $codeCmd) {
    Write-Host "[skip] command 'code' tidak tersedia. Lewati install extension VS Code."
    return
  }

  Write-Host "[1/5] Install extension VS Code"
  $requiredExtensions = @(
    "openai.chatgpt",
    "eamodio.gitlens",
    "dbaeumer.vscode-eslint",
    "esbenp.prettier-vscode",
    "usernamehw.errorlens"
  )
  $optionalCandidates = @("GitHub.copilot", "github.copilot")

  $installed = @(& $codeCmd.Source --list-extensions 2>$null)
  $installedSet = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
  foreach ($ext in $installed) { [void]$installedSet.Add($ext) }

  foreach ($ext in $requiredExtensions) {
    if ($installedSet.Contains($ext)) {
      Write-Host "  - $ext (sudah terpasang)"
      continue
    }
    Write-Host "  - install $ext"
    try {
      & $codeCmd.Source --install-extension $ext | Out-Null
    } catch {
      Write-Warning "gagal install $ext, lanjut ke extension berikutnya"
    }
  }

  $copilotInstalled = $false
  foreach ($ext in $optionalCandidates) {
    if ($installedSet.Contains($ext)) {
      Write-Host "  - $ext (sudah terpasang)"
      $copilotInstalled = $true
      break
    }

    Write-Host "  - coba install $ext"
    try {
      & $codeCmd.Source --install-extension $ext | Out-Null
      $copilotInstalled = $true
      break
    } catch {
      continue
    }
  }

  if (-not $copilotInstalled) {
    Write-Host "  ! warning: GitHub Copilot tidak tersedia di marketplace editor ini. Lewati."
  }
}

function Install-CodeReviewGraph {
  param([Parameter(Mandatory = $true)][string]$ProjectRoot)
  Write-Host "[2/5] Install code-review-graph (venv lokal project)"
  $toolsDir = Join-Path $ProjectRoot ".tools"
  $venvDir = Join-Path $toolsDir "code-review-graph-venv"
  New-Item -ItemType Directory -Path $toolsDir -Force | Out-Null
  & python -m venv $venvDir

  $pipExe = Join-Path $venvDir "Scripts/pip.exe"
  if (-not (Test-Path -LiteralPath $pipExe)) {
    $pipExe = Join-Path $venvDir "bin/pip"
  }
  & $pipExe install --upgrade pip
  & $pipExe install code-review-graph
}

function Link-ProjectSkills {
  param(
    [Parameter(Mandatory = $true)][string]$CodexDir,
    [Parameter(Mandatory = $true)][string]$CodexUserDir
  )
  Write-Host "[3/5] Link project skills ke ~/.codex/skills (best effort)"
  $skillsUserDir = Join-Path $CodexUserDir "skills"
  New-Item -ItemType Directory -Path $skillsUserDir -Force | Out-Null

  $skillsRoot = Join-Path $CodexDir "skills"
  if (-not (Test-Path -LiteralPath $skillsRoot)) {
    Write-Host "  - skip: folder skills tidak ada di $skillsRoot"
    return
  }

  $linked = 0
  Get-ChildItem -LiteralPath $skillsRoot -Directory | ForEach-Object {
    $skillName = $_.Name
    $target = Join-Path $skillsUserDir $skillName
    if (Test-Path -LiteralPath $target) {
      Write-Host "  - skip: $skillName sudah ada di ~/.codex/skills"
      return
    }

    try {
      New-Item -ItemType Junction -Path $target -Target $_.FullName | Out-Null
      $linked++
      Write-Host "  - linked: $skillName"
    } catch {
      Write-Warning "gagal link $skillName ($($_.Exception.Message))"
    }
  }

  Write-Host "  - total linked: $linked"
}

function Initialize-Memory {
  param(
    [Parameter(Mandatory = $true)][string]$CodexDir,
    [Parameter(Mandatory = $true)][string]$ProjectRoot,
    [Parameter(Mandatory = $true)][string]$ProjectName
  )
  Write-Host "[4/5] Inisialisasi .codex/memory/memory.md"
  $memoryFile = Join-Path $CodexDir "memory/memory.md"
  if (-not (Test-Path -LiteralPath $memoryFile)) {
    Write-Host "  - skip: memory.md tidak ditemukan"
    return
  }

  $stack = @()
  if (Test-Path -LiteralPath (Join-Path $ProjectRoot "package.json")) { $stack += "Node.js" }
  if (Test-Path -LiteralPath (Join-Path $ProjectRoot "Cargo.toml")) { $stack += "Rust" }
  if (Test-Path -LiteralPath (Join-Path $ProjectRoot "tauri.conf.json")) { $stack += "Tauri" }
  if (Test-Path -LiteralPath (Join-Path $ProjectRoot "src-tauri/tauri.conf.json")) { $stack += "Tauri" }
  $stackValue = if ($stack.Count -gt 0) { ($stack | Select-Object -Unique) -join " " } else { "Unknown" }

  $today = Get-Date -Format "yyyy-MM-dd"
  $content = Get-Content -LiteralPath $memoryFile -Raw
  $content = $content -replace "Name: \(fill after bootstrap\)", "Name: $ProjectName"
  $content = $content -replace "Stack: \(fill after bootstrap\)", "Stack: $stackValue"
  $content = $content -replace "Last updated: \(fill after bootstrap\)", "Last updated: $today"
  Set-Content -LiteralPath $memoryFile -Value $content -Encoding UTF8
  Write-Host "  - updated project memory ($today)"
}

function Upsert-McpViaCodex {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string[]]$Command
  )
  $exists = $false
  try {
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & codex mcp get $Name *> $null
    if ($LASTEXITCODE -eq 0) { $exists = $true }
  } catch {
    $exists = $false
  } finally {
    $ErrorActionPreference = $prev
  }

  if ($exists) {
    Write-Host "  - update MCP '$Name'"
    & codex mcp remove $Name | Out-Null
  } else {
    Write-Host "  - add MCP '$Name'"
  }
  & codex mcp add $Name -- @Command | Out-Null
}

function Configure-McpServers {
  param(
    [Parameter(Mandatory = $true)][string]$ProjectRoot,
    [Parameter(Mandatory = $true)][bool]$HasCodexCli
  )
  $codeReviewGraphCmd = Join-Path $ProjectRoot ".tools/code-review-graph-venv/Scripts/code-review-graph.exe"
  if (-not (Test-Path -LiteralPath $codeReviewGraphCmd)) {
    $codeReviewGraphCmd = Join-Path $ProjectRoot ".tools/code-review-graph-venv/bin/code-review-graph"
  }

  if ($HasCodexCli) {
    Write-Host "[5/5] Konfigurasi MCP server via Codex CLI"
    Upsert-McpViaCodex -Name "context7" -Command @("npx", "-y", "@upstash/context7-mcp")
    Upsert-McpViaCodex -Name "filesystem" -Command @("npx", "-y", "@modelcontextprotocol/server-filesystem", $ProjectRoot)
    Upsert-McpViaCodex -Name "git" -Command @("npx", "-y", "@modelcontextprotocol/server-git", "--repository", $ProjectRoot)
    Upsert-McpViaCodex -Name "fetch" -Command @("npx", "-y", "@modelcontextprotocol/server-fetch")
    Upsert-McpViaCodex -Name "time" -Command @("npx", "-y", "@modelcontextprotocol/server-time", "--local-timezone=Asia/Pontianak")
    Upsert-McpViaCodex -Name "memory" -Command @("npx", "-y", "@modelcontextprotocol/server-memory")
    Upsert-McpViaCodex -Name "tauri" -Command @("npx", "-y", "@hypothesi/tauri-mcp-server")
    Upsert-McpViaCodex -Name "codeReviewGraph" -Command @($codeReviewGraphCmd, "serve")
    return
  }

  Write-Host "[5/5] Konfigurasi MCP server via .vscode/mcp.json (tanpa Codex CLI)"
  $vscodeDir = Join-Path $ProjectRoot ".vscode"
  New-Item -ItemType Directory -Path $vscodeDir -Force | Out-Null

  $mcpFile = Join-Path $vscodeDir "mcp.json"
  if (Test-Path -LiteralPath $mcpFile) {
    $backup = "$mcpFile.bak.$(Get-Date -Format 'yyyyMMddHHmmss')"
    Copy-Item -LiteralPath $mcpFile -Destination $backup -Force
    Write-Host "  - existing mcp.json dibackup ke: $backup"
  }

  $servers = @{
    context7 = @{
      type = "stdio"
      command = "npx"
      args = @("-y", "@upstash/context7-mcp")
    }
    openaiDeveloperDocs = @{
      type = "http"
      url = "https://developers.openai.com/mcp"
    }
    filesystem = @{
      type = "stdio"
      command = "npx"
      args = @("-y", "@modelcontextprotocol/server-filesystem", '${workspaceFolder}')
    }
    git = @{
      type = "stdio"
      command = "npx"
      args = @("-y", "@modelcontextprotocol/server-git", "--repository", '${workspaceFolder}')
    }
    fetch = @{
      type = "stdio"
      command = "npx"
      args = @("-y", "@modelcontextprotocol/server-fetch")
    }
    time = @{
      type = "stdio"
      command = "npx"
      args = @("-y", "@modelcontextprotocol/server-time", "--local-timezone=Asia/Pontianak")
    }
    memory = @{
      type = "stdio"
      command = "npx"
      args = @("-y", "@modelcontextprotocol/server-memory")
    }
    tauri = @{
      type = "stdio"
      command = "npx"
      args = @("-y", "@hypothesi/tauri-mcp-server")
    }
    codeReviewGraph = @{
      type = "stdio"
      command = $codeReviewGraphCmd
      args = @("serve")
    }
  }

  $obj = @{ servers = $servers }
  $json = $obj | ConvertTo-Json -Depth 10
  Set-Content -LiteralPath $mcpFile -Value ($json + "`n") -Encoding UTF8
  Write-Host "  - write: $mcpFile"
}

function Verify-Setup {
  param(
    [Parameter(Mandatory = $true)][string]$ProjectRoot,
    [Parameter(Mandatory = $true)][bool]$HasCodexCli
  )
  Write-Host "[done] Verifikasi"
  if ($HasCodexCli) {
    & codex mcp list
  } else {
    Write-Host "  - codex CLI tidak tersedia, cek file konfigurasi:"
    Write-Host "    $(Join-Path $ProjectRoot '.vscode/mcp.json')"
  }
}

$codexDir = $PSScriptRoot
$projectRoot = if ($CliArgs.Count -gt 0 -and -not [string]::IsNullOrWhiteSpace($CliArgs[0])) {
  $CliArgs[0]
} else {
  Split-Path -Path $codexDir -Parent
}
$projectRoot = (Resolve-Path -LiteralPath $projectRoot).Path
$projectName = Split-Path -Path $projectRoot -Leaf
$codexUserDir = Join-Path $env:USERPROFILE ".codex"
$hasCodexCli = [bool](Get-Command codex -ErrorAction SilentlyContinue)

Write-Host "Bootstrap start"
Write-Host "- Project root: $projectRoot"

if (-not (Test-Path -LiteralPath $projectRoot -PathType Container)) {
  throw "Error: project root '$projectRoot' tidak ditemukan."
}

Require-Command -Name "npx"
Require-Command -Name "python"
Install-VSCodeExtensions
Install-CodeReviewGraph -ProjectRoot $projectRoot
Link-ProjectSkills -CodexDir $codexDir -CodexUserDir $codexUserDir
Initialize-Memory -CodexDir $codexDir -ProjectRoot $projectRoot -ProjectName $projectName
Configure-McpServers -ProjectRoot $projectRoot -HasCodexCli $hasCodexCli
Verify-Setup -ProjectRoot $projectRoot -HasCodexCli $hasCodexCli

Write-Host "[done] Selesai"
Write-Host "Selesai. Reload VS Code window agar MCP server kebaca ulang."
Write-Host "Smart compact standard command (Windows): powershell -ExecutionPolicy Bypass -File .codex/tools/agentic-hub.ps1 compact"
Write-Host "Smart compact standard command (Linux/macOS): bash .codex/tools/agentic-hub.sh compact"
Write-Host "Warning: native /compact runtime tidak melewati smart compact pre-layer."
