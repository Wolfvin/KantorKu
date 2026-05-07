param(
  [Parameter(Position = 0)]
  [ValidateSet("doctor", "repair", "enforce", "snapshot", "help", "-h", "--help", "")]
  [string]$Command = ""
)

$ErrorActionPreference = "Stop"

function Show-Usage {
  @"
Usage:
  powershell -ExecutionPolicy Bypass -File .codex/tools/home-codex-guard.ps1 doctor
  powershell -ExecutionPolicy Bypass -File .codex/tools/home-codex-guard.ps1 repair
  powershell -ExecutionPolicy Bypass -File .codex/tools/home-codex-guard.ps1 enforce
  powershell -ExecutionPolicy Bypass -File .codex/tools/home-codex-guard.ps1 snapshot
"@
}

function Write-Pass([string]$Message) { Write-Host "[PASS] $Message" }
function Write-Warn([string]$Message) { Write-Host "[WARN] $Message" }
function Write-Fail([string]$Message) { Write-Host "[FAIL] $Message" }

$toolDir = Split-Path -Parent $PSCommandPath
$root = [System.IO.Path]::GetFullPath((Join-Path $toolDir "..\.."))
$homeCodex = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME ".codex" }
$syncDir = Join-Path $root ".codex\home-sync"
$templateConfig = Join-Path $syncDir "home-config.toml"
$templateRules = Join-Path $syncDir "home-default.rules"
$policyFile = Join-Path $syncDir "home-model-policy.json"
$setupScript = Join-Path $root ".codex\skills\setup\scripts\codex-arg0-ensure.sh"
$runShScript = Join-Path $root ".codex\tools\_run-sh.ps1"

function Ensure-Parent([string]$Path) {
  $parent = Split-Path -Parent $Path
  if ($parent -and -not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
  }
}

function Get-Sha256([string]$Path) {
  (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Check-FileEqual([string]$Current, [string]$Template, [string]$Label) {
  if (-not (Test-Path -LiteralPath $Template)) {
    Write-Fail "$Label template missing: $Template"
    return $false
  }
  if (-not (Test-Path -LiteralPath $Current)) {
    Write-Fail "$Label missing: $Current"
    return $false
  }

  $a = Get-Sha256 -Path $Current
  $b = Get-Sha256 -Path $Template
  if ($a -eq $b) {
    Write-Pass "$Label matches baseline"
    return $true
  }

  Write-Fail "$Label drift detected"
  return $false
}

function Check-ModelsCachePolicy {
  $cache = Join-Path $homeCodex "models_cache.json"
  if (-not (Test-Path -LiteralPath $cache)) {
    Write-Warn "models cache missing: $cache"
    return $false
  }
  if (-not (Test-Path -LiteralPath $policyFile)) {
    Write-Fail "models policy template missing: $policyFile"
    return $false
  }

  $policy = Get-Content -LiteralPath $policyFile -Raw | ConvertFrom-Json
  $cacheObj = Get-Content -LiteralPath $cache -Raw | ConvertFrom-Json
  $models = @($cacheObj.models)
  $slug = [string]$policy.required_slug
  $defaultEffort = [string]$policy.required_default_reasoning_level
  $requiredSupported = @($policy.required_supported_efforts)

  $target = $models | Where-Object { $_.slug -eq $slug } | Select-Object -First 1
  if (-not $target) {
    Write-Fail "models_cache policy check failed (fail:missing_slug)"
    return $false
  }

  if ($defaultEffort -and $target.default_reasoning_level -ne $defaultEffort) {
    Write-Fail "models_cache policy check failed (fail:default_reasoning_mismatch)"
    return $false
  }

  $supported = @($target.supported_reasoning_levels | Where-Object { $_.effort } | ForEach-Object { [string]$_.effort })
  $required = @($requiredSupported | ForEach-Object { [string]$_ })
  $joinedSupported = ($supported | Sort-Object) -join ","
  $joinedRequired = ($required | Sort-Object) -join ","
  if ($required.Count -gt 0 -and $joinedSupported -ne $joinedRequired) {
    Write-Fail "models_cache policy check failed (fail:supported_reasoning_mismatch)"
    return $false
  }

  Write-Pass "models_cache policy matches baseline"
  return $true
}

function Run-Doctor {
  $ok = $true

  if (Test-Path -LiteralPath $homeCodex) {
    Write-Pass "home codex dir exists: $homeCodex"
  } else {
    Write-Fail "home codex dir missing: $homeCodex"
    $ok = $false
  }

  if (-not (Check-FileEqual -Current (Join-Path $homeCodex "config.toml") -Template $templateConfig -Label "home config.toml")) { $ok = $false }
  if (-not (Check-FileEqual -Current (Join-Path $homeCodex "rules\default.rules") -Template $templateRules -Label "home default.rules")) { $ok = $false }
  if (-not (Check-ModelsCachePolicy)) { $ok = $false }

  $arg0Dir = Join-Path $homeCodex "tmp\arg0\codex-arg0GInYml"
  $wrapperCandidates = @(
    (Join-Path $arg0Dir "codex-wrapper"),
    (Join-Path $arg0Dir "codex-wrapper.cmd"),
    (Join-Path $arg0Dir "codex-wrapper.ps1")
  )
  $wrapperFound = $wrapperCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
  if ($wrapperFound) {
    Write-Pass "arg0 wrapper exists"
  } else {
    Write-Warn "arg0 wrapper missing (non-blocking on Windows): $($wrapperCandidates -join ', ')"
  }

  return $ok
}

function Sanitize-ModelsCache {
  $cache = Join-Path $homeCodex "models_cache.json"
  if (-not (Test-Path -LiteralPath $cache)) { return }
  if (-not (Test-Path -LiteralPath $policyFile)) { return }

  $policy = Get-Content -LiteralPath $policyFile -Raw | ConvertFrom-Json
  $obj = Get-Content -LiteralPath $cache -Raw | ConvertFrom-Json
  if (-not $obj.models) {
    $obj | Add-Member -NotePropertyName models -NotePropertyValue @() -Force
  }

  $requiredSlug = [string]$policy.required_slug
  $requiredEffort = [string]$policy.required_default_reasoning_level
  $requiredSupported = @($policy.required_supported_efforts)
  $clearPayload = [bool]$policy.clear_instruction_payload

  foreach ($m in @($obj.models)) {
    if ($clearPayload) {
      if ($null -ne $m.base_instructions) { $m.base_instructions = "" }
      if (-not $m.model_messages) {
        $m | Add-Member -NotePropertyName model_messages -NotePropertyValue ([pscustomobject]@{}) -Force
      }
      if ($null -ne $m.model_messages.instructions_template) { $m.model_messages.instructions_template = "" }
      if ($m.model_messages.instructions_variables) {
        $m.model_messages.instructions_variables = [pscustomobject]@{}
      }
    }

    if ($m.slug -eq $requiredSlug) {
      $m.default_reasoning_level = $requiredEffort
      $m.supported_reasoning_levels = @(
        foreach ($effort in $requiredSupported) {
          [pscustomobject]@{
            effort = [string]$effort
            description = "Balances speed and reasoning depth for everyday tasks"
          }
        }
      )
    }
  }

  $json = $obj | ConvertTo-Json -Depth 100 -Compress
  Set-Content -LiteralPath $cache -Value $json -Encoding utf8
}

function Refresh-Arg0Wrapper {
  if (-not (Test-Path -LiteralPath $setupScript)) {
    Write-Warn "setup script missing: $setupScript"
    return
  }
  if (-not (Test-Path -LiteralPath $runShScript)) {
    Write-Warn "shell runner missing: $runShScript"
    return
  }

  try {
    & powershell -ExecutionPolicy Bypass -File $runShScript -ScriptPath $setupScript
    if ($LASTEXITCODE -eq 0) {
      Write-Pass "arg0 wrapper refreshed"
    } else {
      Write-Warn "arg0 wrapper refresh failed (exit=$LASTEXITCODE)"
    }
  } catch {
    Write-Warn "arg0 wrapper refresh skipped: $($_.Exception.Message)"
  }
}

function Run-Repair {
  New-Item -ItemType Directory -Path $homeCodex -Force | Out-Null
  New-Item -ItemType Directory -Path (Join-Path $homeCodex "rules") -Force | Out-Null

  Ensure-Parent -Path (Join-Path $homeCodex "config.toml")
  Copy-Item -LiteralPath $templateConfig -Destination (Join-Path $homeCodex "config.toml") -Force
  Write-Pass "restored home config.toml"

  Ensure-Parent -Path (Join-Path $homeCodex "rules\default.rules")
  Copy-Item -LiteralPath $templateRules -Destination (Join-Path $homeCodex "rules\default.rules") -Force
  Write-Pass "restored home default.rules"

  Refresh-Arg0Wrapper

  Sanitize-ModelsCache
  Write-Pass "models cache sanitized"

  return (Run-Doctor)
}

function Run-Enforce {
  if (Run-Doctor) {
    Write-Pass "home codex guard: pass"
    return $true
  }

  Write-Warn "home codex guard: fail -> applying repair"
  return (Run-Repair)
}

function Run-Snapshot {
  New-Item -ItemType Directory -Path $syncDir -Force | Out-Null
  Copy-Item -LiteralPath (Join-Path $homeCodex "config.toml") -Destination $templateConfig -Force
  Copy-Item -LiteralPath (Join-Path $homeCodex "rules\default.rules") -Destination $templateRules -Force
  Write-Pass "baseline snapshot refreshed from $homeCodex"
  return $true
}

switch ($Command) {
  "doctor" {
    if (-not (Run-Doctor)) { exit 1 }
  }
  "repair" {
    if (-not (Run-Repair)) { exit 1 }
  }
  "enforce" {
    if (-not (Run-Enforce)) { exit 1 }
  }
  "snapshot" {
    if (-not (Run-Snapshot)) { exit 1 }
  }
  "help" { Show-Usage }
  "-h" { Show-Usage }
  "--help" { Show-Usage }
  "" { Show-Usage }
}
