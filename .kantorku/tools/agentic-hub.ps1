Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$CliArgs = @($args)
if ($CliArgs.Count -eq 1 -and $CliArgs[0] -is [string] -and $CliArgs[0].Contains(" ")) {
  $CliArgs = @($CliArgs[0] -split "\s+" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
}

$scriptDir = $PSScriptRoot
$codexDir = Split-Path -Path $scriptDir -Parent
$projectRoot = Split-Path -Path $codexDir -Parent
$mcpFileDefault = Join-Path $projectRoot ".vscode/mcp.json"
$memoryFile = Join-Path $codexDir "memory/memory.md"

function ConvertTo-Hashtable {
  param([Parameter(Mandatory = $true)][object]$InputObject)
  if ($null -eq $InputObject) { return $null }
  if ($InputObject -is [hashtable]) { return $InputObject }
  if ($InputObject -is [System.Collections.IDictionary]) {
    $map = @{}
    foreach ($k in $InputObject.Keys) {
      $map[$k] = ConvertTo-Hashtable -InputObject $InputObject[$k]
    }
    return $map
  }
  if ($InputObject -is [System.Collections.IEnumerable] -and -not ($InputObject -is [string])) {
    $list = @()
    foreach ($item in $InputObject) {
      $list += ,(ConvertTo-Hashtable -InputObject $item)
    }
    return $list
  }
  if ($InputObject -is [pscustomobject]) {
    $map = @{}
    foreach ($prop in $InputObject.PSObject.Properties) {
      $map[$prop.Name] = ConvertTo-Hashtable -InputObject $prop.Value
    }
    return $map
  }
  return $InputObject
}

function Show-Usage {
  Write-Host "Agentic Hub CLI"
  Write-Host ""
  Write-Host "Usage:"
  Write-Host "  .\.codex\tools\agentic-hub.ps1 doctor"
  Write-Host "  .\.codex\tools\agentic-hub.ps1 bootstrap [project-root]"
  Write-Host "  .\.codex\tools\agentic-hub.ps1 intake <repo-url|local-path> [repo-url|local-path ...]"
  Write-Host "  .\.codex\tools\agentic-hub.ps1 sync [reports-dir]"
  Write-Host "  .\.codex\tools\agentic-hub.ps1 compact"
  Write-Host "  .\.codex\tools\agentic-hub.ps1 checkpoint --goal <text> --done <text> --next <text> [--blockers <text>]"
  Write-Host "  .\.codex\tools\agentic-hub.ps1 skill suggest <prompt text>"
  Write-Host "  .\.codex\tools\agentic-hub.ps1 skill list [category]"
  Write-Host "  .\.codex\tools\agentic-hub.ps1 body doctor|repair"
  Write-Host ""
  Write-Host "  .\.codex\tools\agentic-hub.ps1 mcp list [mcp-file]"
  Write-Host "  .\.codex\tools\agentic-hub.ps1 mcp add-http <name> <url> [mcp-file]"
  Write-Host "  .\.codex\tools\agentic-hub.ps1 mcp add-stdio <name> <command> [arg ...] [--file <mcp-file>]"
  Write-Host ""
  Write-Host "  .\.codex\tools\agentic-hub.ps1 connector list [mcp-file]"
  Write-Host "  .\.codex\tools\agentic-hub.ps1 connector add-http <name> <url> [mcp-file]"
  Write-Host "  .\.codex\tools\agentic-hub.ps1 connector add-stdio <name> <command> [arg ...] [--file <mcp-file>]"
  Write-Host "  .\.codex\tools\agentic-hub.ps1 connector preset claude-core [mcp-file]"
  Write-Host ""
  Write-Host "  .\.codex\tools\agentic-hub.ps1 plugin note <name> <source>"
  Write-Host "  .\.codex\tools\agentic-hub.ps1 plugin import-openclaw <openclaw.plugin.json>"
  Write-Host "  .\.codex\tools\agentic-hub.ps1 plugin recommend buildwithclaude"
  Write-Host "  .\.codex\tools\agentic-hub.ps1 plugin recommend ariff"
}

function Ensure-FileParent {
  param([Parameter(Mandatory = $true)][string]$File)
  $parent = Split-Path -Path $File -Parent
  if (-not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
  }
}

function Add-MemoryLineOnce {
  param([Parameter(Mandatory = $true)][string]$Line)
  Ensure-FileParent -File $memoryFile
  if (-not (Test-Path -LiteralPath $memoryFile)) {
    Set-Content -LiteralPath $memoryFile -Value "# Project Memory`n" -Encoding UTF8
  }
  $content = Get-Content -LiteralPath $memoryFile -Raw
  if (-not $content.Contains($Line)) {
    Add-Content -LiteralPath $memoryFile -Value "$Line"
  }
}

function Ensure-McpFile {
  param([Parameter(Mandatory = $true)][string]$McpFile)
  Ensure-FileParent -File $McpFile
  if (-not (Test-Path -LiteralPath $McpFile)) {
    Set-Content -LiteralPath $McpFile -Value "{`n  `"servers`": {}`n}`n" -Encoding UTF8
  }
}

function Backup-File {
  param([Parameter(Mandatory = $true)][string]$File)
  if (Test-Path -LiteralPath $File) {
    Copy-Item -LiteralPath $File -Destination "$File.bak.$(Get-Date -Format 'yyyyMMddHHmmss')" -Force
  }
}

function Read-McpConfig {
  param([Parameter(Mandatory = $true)][string]$McpFile)
  Ensure-McpFile -McpFile $McpFile
  $raw = Get-Content -LiteralPath $McpFile -Raw
  if ([string]::IsNullOrWhiteSpace($raw)) {
    return @{ servers = @{} }
  }
  $obj = ConvertTo-Hashtable -InputObject ($raw | ConvertFrom-Json)
  if (-not $obj.ContainsKey("servers") -or -not $obj.servers) {
    $obj.servers = @{}
  }
  return $obj
}

function Write-McpConfig {
  param(
    [Parameter(Mandatory = $true)][string]$McpFile,
    [Parameter(Mandatory = $true)][hashtable]$Config
  )
  $json = $Config | ConvertTo-Json -Depth 20
  Set-Content -LiteralPath $McpFile -Value ($json + "`n") -Encoding UTF8
}

function Mcp-List {
  param([string]$McpFile = $mcpFileDefault)
  if (-not (Test-Path -LiteralPath $McpFile)) {
    Write-Host "[agentic-hub] mcp file not found: $McpFile"
    return 1
  }

  $cfg = Read-McpConfig -McpFile $McpFile
  $servers = $cfg.servers
  if (-not $servers.Keys -or $servers.Keys.Count -eq 0) {
    Write-Host "(no servers)"
    return 0
  }

  foreach ($name in ($servers.Keys | Sort-Object)) {
    $item = $servers[$name]
    $typ = $item.type
    if ($typ -eq "http") {
      $detail = $item.url
    } else {
      $cmd = $item.command
      $args = @($item.args) -join " "
      $detail = "$cmd $args".Trim()
    }
    Write-Host "- $name [$typ] $detail"
  }
  return 0
}

function Mcp-AddHttp {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$Url,
    [string]$McpFile = $mcpFileDefault
  )
  Ensure-McpFile -McpFile $McpFile
  Backup-File -File $McpFile

  $cfg = Read-McpConfig -McpFile $McpFile
  $cfg.servers[$Name] = @{
    type = "http"
    url = $Url
  }
  Write-McpConfig -McpFile $McpFile -Config $cfg
  Write-Host "[agentic-hub] upserted http MCP '$Name' -> $Url"
}

function Mcp-AddStdio {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$Command,
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$Rest = @()
  )
  $mcpFile = $mcpFileDefault
  $argsList = [System.Collections.Generic.List[string]]::new()

  $i = 0
  while ($i -lt $Rest.Count) {
    if ($Rest[$i] -eq "--file") {
      if ($i + 1 -ge $Rest.Count) {
        throw "[agentic-hub] --file membutuhkan path"
      }
      $mcpFile = $Rest[$i + 1]
      $i += 2
      continue
    }
    $argsList.Add($Rest[$i])
    $i++
  }

  Ensure-McpFile -McpFile $mcpFile
  Backup-File -File $mcpFile

  $cfg = Read-McpConfig -McpFile $mcpFile
  $cfg.servers[$Name] = @{
    type = "stdio"
    command = $Command
    args = @($argsList)
  }
  Write-McpConfig -McpFile $mcpFile -Config $cfg
  Write-Host "[agentic-hub] upserted stdio MCP '$Name' -> $Command $($argsList -join ' ')"
}

function Plugin-Note {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$Source
  )
  $today = Get-Date -Format "yyyy-MM-dd"
  $line = "- $Name | $Source | $today"
  Add-MemoryLineOnce -Line $line
  Write-Host "[agentic-hub] noted plugin reference: $Name"
}

function Checkpoint-Note {
  param([string[]]$Args)
  $goal = ""
  $done = ""
  $next = ""
  $blockers = "-"

  $i = 0
  while ($i -lt $Args.Count) {
    switch ($Args[$i]) {
      "--goal" { $goal = $Args[$i + 1]; $i += 2; continue }
      "--done" { $done = $Args[$i + 1]; $i += 2; continue }
      "--next" { $next = $Args[$i + 1]; $i += 2; continue }
      "--blockers" { $blockers = $Args[$i + 1]; $i += 2; continue }
      default { throw "[agentic-hub] unknown checkpoint arg: $($Args[$i])" }
    }
  }

  if ([string]::IsNullOrWhiteSpace($goal) -or [string]::IsNullOrWhiteSpace($done) -or [string]::IsNullOrWhiteSpace($next)) {
    throw "[agentic-hub] checkpoint requires --goal --done --next"
  }

  $now = Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"
  Add-MemoryLineOnce -Line "## Session Checkpoints"
  Add-MemoryLineOnce -Line "- $now | goal: $goal | done: $done | next: $next | blockers: $blockers"
  Write-Host "[agentic-hub] checkpoint saved into: $memoryFile"
}

function Connector-PresetClaudeCore {
  param([string]$McpFile = $mcpFileDefault)
  Write-Host "[agentic-hub] applying connector preset: claude-core"
  Mcp-AddHttp -Name "openaiDeveloperDocs" -Url "https://developers.openai.com/mcp" -McpFile $McpFile
  Mcp-AddStdio -Name "context7" -Command "npx" -Rest @("-y", "@upstash/context7-mcp", "--file", $McpFile)
  Mcp-AddStdio -Name "filesystem" -Command "npx" -Rest @("-y", "@modelcontextprotocol/server-filesystem", '${workspaceFolder}', "--file", $McpFile)
  Mcp-AddStdio -Name "git" -Command "npx" -Rest @("-y", "@modelcontextprotocol/server-git", "--repository", '${workspaceFolder}', "--file", $McpFile)
  Mcp-AddStdio -Name "fetch" -Command "npx" -Rest @("-y", "@modelcontextprotocol/server-fetch", "--file", $McpFile)
  Mcp-AddStdio -Name "time" -Command "npx" -Rest @("-y", "@modelcontextprotocol/server-time", "--local-timezone=Asia/Pontianak", "--file", $McpFile)
  Mcp-AddStdio -Name "memory" -Command "npx" -Rest @("-y", "@modelcontextprotocol/server-memory", "--file", $McpFile)
  Plugin-Note -Name "claude-core-connectors" -Source "preset://claude-core"
  Write-Host "[agentic-hub] preset applied into: $McpFile"
}

function Plugin-ImportOpenClaw {
  param([Parameter(Mandatory = $true)][string]$PluginJson)
  if (-not (Test-Path -LiteralPath $PluginJson)) {
    throw "[agentic-hub] openclaw plugin file not found: $PluginJson"
  }

  $obj = ConvertTo-Hashtable -InputObject (Get-Content -LiteralPath $PluginJson -Raw | ConvertFrom-Json)
  $pluginId = if ($obj.ContainsKey("id")) { $obj.id } else { "unknown" }
  $name = if ($obj.ContainsKey("name")) { $obj.name } else { "unknown" }
  $enabled = if ($obj.ContainsKey("enabledByDefault")) { $obj.enabledByDefault } else { $false }
  $tools = @()
  if ($obj.ContainsKey("contracts") -and $obj.contracts -and $obj.contracts.ContainsKey("tools")) {
    $tools = @($obj.contracts.tools)
  }
  $skills = if ($obj.ContainsKey("skills")) { @($obj.skills) } else { @() }
  Plugin-Note -Name "openclaw-claude-code" -Source $PluginJson
  Add-MemoryLineOnce -Line "- openclaw-claude-code | id=$pluginId | name=$name | enabled=$enabled | tools=$($tools.Count) | skills=$($skills.Count) | source=$PluginJson"
  Write-Host "[agentic-hub] imported openclaw plugin profile into memory"
}

function Plugin-Recommend {
  param([Parameter(Mandatory = $true)][string]$Source)
  switch ($Source) {
    "buildwithclaude" {
      Write-Host "[agentic-hub] recommended plugins (buildwithclaude)"
      Write-Host "1. codex-hud"
      Write-Host "   /plugin install codex-hud@buildwithclaude"
      Write-Host "2. cc-best"
      Write-Host "   /plugin install cc-best@buildwithclaude"
      Write-Host "3. shipwright"
      Write-Host "   /plugin install shipwright@buildwithclaude"
      Write-Host ""
      Write-Host "Add marketplace first:"
      Write-Host "  /plugin marketplace add davepoon/buildwithclaude"
      Plugin-Note -Name "buildwithclaude-curated" -Source "marketplace://davepoon/buildwithclaude"
      return
    }
    "ariff" {
      Write-Host "[agentic-hub] recommended plugins (ariff-claude-plugins)"
      Write-Host "1. anti-hallucination suite (targeted)"
      Write-Host "   - hallucination-guard (hook)"
      Write-Host "   - answer-validator (hook)"
      Write-Host "   - truth-finder (agent)"
      Write-Host "   - answer-analyzer (agent)"
      Write-Host "   - anti-hallucination, cross-checker, source-verifier,"
      Write-Host "     confidence-scorer, citation-enforcer, uncertainty-detector,"
      Write-Host "     output-auditor, context-grounding (skills)"
      Write-Host ""
      Write-Host "Marketplace (Claude REPL):"
      Write-Host "  /plugin marketplace add a-ariff/ariff-claude-plugins"
      Plugin-Note -Name "ariff-anti-hallucination-suite" -Source "marketplace://a-ariff/ariff-claude-plugins"
      return
    }
    default {
      throw "[agentic-hub] unknown recommendation source: $Source"
    }
  }
}

function Smart-Compact {
  $script = Join-Path $scriptDir "smart-compact.sh"
  if (-not (Test-Path -LiteralPath $script)) {
    throw "[agentic-hub] smart compact script not found: $script"
  }

  Write-Host "[agentic-hub] smart compact: pre-layer before native compact"
  Write-Host "[agentic-hub] warning: native /compact does not run this pre-layer; use this command as standard path"

  if (Get-Command bash -ErrorAction SilentlyContinue) {
    & bash $script
    return
  }
  if (Get-Command wsl -ErrorAction SilentlyContinue) {
    & wsl bash $script
    return
  }

  throw "[agentic-hub] bash not found. Install Git Bash or WSL to run smart compact."
}

if ($CliArgs.Count -lt 1) {
  Show-Usage
  exit 1
}

$cmd = $CliArgs[0]
$rest = if ($CliArgs.Count -gt 1) { @($CliArgs[1..($CliArgs.Count - 1)]) } else { @() }

switch ($cmd) {
  "doctor" {
    Write-Host "[agentic-hub] doctor"
    Write-Host "- project: $projectRoot"
    foreach ($bin in @("powershell", "python", "python3", "git", "npx", "code", "codex", "bash")) {
      if (Get-Command $bin -ErrorAction SilentlyContinue) {
        Write-Host "- ${bin}: OK"
      } else {
        Write-Host "- ${bin}: missing"
      }
    }
    if (Test-Path -LiteralPath $mcpFileDefault) {
      Write-Host "- mcp: $mcpFileDefault"
      [void](Mcp-List -McpFile $mcpFileDefault)
    } else {
      Write-Host "- mcp: missing ($mcpFileDefault)"
    }
    break
  }
  "bootstrap" {
    $target = if (@($rest).Count -gt 0) { @($rest)[0] } else { $projectRoot }
    $bootstrapScript = Join-Path $codexDir "bootstrap.ps1"
    & $bootstrapScript $target
    break
  }
  "intake" {
    if (@($rest).Count -lt 1) { Show-Usage; exit 1 }
    $cli = Join-Path $scriptDir "agentic-cli.ps1"
    & $cli intake @rest
    break
  }
  "sync" {
    $src = if (@($rest).Count -gt 0) { @($rest)[0] } else { ".tmp/repo-intake/reports" }
    $cli = Join-Path $scriptDir "agentic-cli.ps1"
    & $cli sync $src
    break
  }
  "compact" {
    Smart-Compact
    break
  }
  "checkpoint" {
    Checkpoint-Note -Args $rest
    break
  }
  "skill" {
    if (@($rest).Count -lt 1) { Show-Usage; exit 1 }
    $sub = @($rest)[0]
    $skillRest = if (@($rest).Count -gt 1) { @($rest[1..(@($rest).Count - 1)]) } else { @() }
    $navigator = Join-Path $scriptDir "skill-navigator.ps1"
    switch ($sub) {
      "suggest" {
        if (@($skillRest).Count -lt 1) { Show-Usage; exit 1 }
        & $navigator suggest @skillRest
        break
      }
      "list" {
        if (@($skillRest).Count -gt 0) {
          & $navigator list @($skillRest)[0]
        } else {
          & $navigator list
        }
        break
      }
      default {
        Show-Usage
        exit 1
      }
    }
    break
  }
  "body" {
    $sub = if (@($rest).Count -gt 0) { @($rest)[0] } else { "doctor" }
    if ($sub -notin @("doctor", "repair")) { Show-Usage; exit 1 }
    $bodyDoctor = Join-Path $scriptDir "body-doctor.sh"
    & bash $bodyDoctor $sub
    break
  }
  "mcp" {
    if (@($rest).Count -lt 1) { Show-Usage; exit 1 }
    $sub = @($rest)[0]
    $mrest = if (@($rest).Count -gt 1) { @($rest[1..(@($rest).Count - 1)]) } else { @() }
    switch ($sub) {
      "list" {
        $target = if (@($mrest).Count -gt 0) { @($mrest)[0] } else { $mcpFileDefault }
        [void](Mcp-List -McpFile $target)
        break
      }
      "add-http" {
        if (@($mrest).Count -lt 2) { Show-Usage; exit 1 }
        $target = if (@($mrest).Count -gt 2) { @($mrest)[2] } else { $mcpFileDefault }
        Mcp-AddHttp -Name @($mrest)[0] -Url @($mrest)[1] -McpFile $target
        break
      }
      "add-stdio" {
        if (@($mrest).Count -lt 2) { Show-Usage; exit 1 }
        $tail = @()
        if (@($mrest).Count -gt 2) { $tail = @($mrest[2..(@($mrest).Count - 1)]) }
        Mcp-AddStdio -Name @($mrest)[0] -Command @($mrest)[1] -Rest $tail
        break
      }
      "preset" {
        $presetName = if (@($mrest).Count -gt 0) { @($mrest)[0] } else { "" }
        $target = if (@($mrest).Count -gt 1) { @($mrest)[1] } else { $mcpFileDefault }
        if ($presetName -ne "claude-core") { throw "[agentic-hub] unknown preset: $presetName" }
        Connector-PresetClaudeCore -McpFile $target
        break
      }
      default {
        Show-Usage
        exit 1
      }
    }
    break
  }
  "connector" {
    if (@($rest).Count -lt 1) { Show-Usage; exit 1 }
    $connectorArgs = @("mcp") + $rest
    & $MyInvocation.MyCommand.Path @connectorArgs
    break
  }
  "plugin" {
    if (@($rest).Count -lt 1) { Show-Usage; exit 1 }
    $sub = @($rest)[0]
    $prest = if (@($rest).Count -gt 1) { @($rest[1..(@($rest).Count - 1)]) } else { @() }
    switch ($sub) {
      "note" {
        if (@($prest).Count -lt 2) { Show-Usage; exit 1 }
        Plugin-Note -Name @($prest)[0] -Source @($prest)[1]
        break
      }
      "import-openclaw" {
        if (@($prest).Count -lt 1) { Show-Usage; exit 1 }
        Plugin-ImportOpenClaw -PluginJson @($prest)[0]
        break
      }
      "recommend" {
        if (@($prest).Count -lt 1) { Show-Usage; exit 1 }
        Plugin-Recommend -Source @($prest)[0]
        break
      }
      default {
        Show-Usage
        exit 1
      }
    }
    break
  }
  "-h" { Show-Usage; break }
  "--help" { Show-Usage; break }
  "help" { Show-Usage; break }
  default {
    Show-Usage
    exit 1
  }
}
