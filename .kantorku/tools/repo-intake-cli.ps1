Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$CliArgs = @($args)

$scriptDir = $PSScriptRoot
$codexDir = Split-Path -Path $scriptDir -Parent
$projectRoot = Split-Path -Path $codexDir -Parent
$tmpRoot = Join-Path $projectRoot ".tmp/repo-intake"
$reportRoot = Join-Path $tmpRoot "reports"

function Show-Usage {
  Write-Host "Usage:"
  Write-Host "  .\.codex\tools\repo-intake-cli.ps1 <repo-url|local-path> [--name <slug>] [--keep]"
  Write-Host ""
  Write-Host "Examples:"
  Write-Host "  .\.codex\tools\repo-intake-cli.ps1 https://github.com/openai/skills"
  Write-Host "  .\.codex\tools\repo-intake-cli.ps1 .tmp/repo-intake/collection-claude-20260414-112445"
  Write-Host "  .\.codex\tools\repo-intake-cli.ps1 git@github.com:org/repo.git --name repo-scan"
}

function Slugify {
  param([Parameter(Mandatory = $true)][string]$Text)
  $value = $Text.ToLowerInvariant()
  $value = [System.Text.RegularExpressions.Regex]::Replace($value, "[^a-z0-9]+", "-")
  $value = $value.Trim("-")
  if ([string]::IsNullOrWhiteSpace($value)) { return "repo" }
  return $value
}

function To-RelativePath {
  param(
    [Parameter(Mandatory = $true)][string]$BasePath,
    [Parameter(Mandatory = $true)][string]$FullPath
  )
  $base = [IO.Path]::GetFullPath($BasePath)
  $full = [IO.Path]::GetFullPath($FullPath)
  if (-not $base.EndsWith([IO.Path]::DirectorySeparatorChar)) {
    $base += [IO.Path]::DirectorySeparatorChar
  }
  $baseUri = [Uri]$base
  $fullUri = [Uri]$full
  $rel = $baseUri.MakeRelativeUri($fullUri).ToString()
  return [Uri]::UnescapeDataString($rel).Replace("/", [IO.Path]::DirectorySeparatorChar)
}

if ($CliArgs.Count -lt 1) {
  Show-Usage
  exit 1
}

$sourceInput = $CliArgs[0]
$nameOverride = ""
$keepClone = $false

$idx = 1
while ($idx -lt $CliArgs.Count) {
  switch ($CliArgs[$idx]) {
    "--name" {
      if ($idx + 1 -ge $CliArgs.Count) { throw "Unknown argument: --name requires value" }
      $nameOverride = $CliArgs[$idx + 1]
      $idx += 2
      continue
    }
    "--keep" {
      $keepClone = $true
      $idx += 1
      continue
    }
    "-h" { Show-Usage; exit 0 }
    "--help" { Show-Usage; exit 0 }
    default {
      throw "Unknown argument: $($CliArgs[$idx])"
    }
  }
}

$sourceMode = "remote"
$scanDir = ""
$sourceLabel = $sourceInput

if (Test-Path -LiteralPath $sourceInput -PathType Container) {
  $sourceMode = "local"
  $scanDir = (Resolve-Path -LiteralPath $sourceInput).Path
}

$repoBasename = [IO.Path]::GetFileName($sourceInput)
if ($repoBasename.EndsWith(".git")) {
  $repoBasename = $repoBasename.Substring(0, $repoBasename.Length - 4)
}
$repoSlug = if ([string]::IsNullOrWhiteSpace($nameOverride)) { Slugify $repoBasename } else { Slugify $nameOverride }
$ts = Get-Date -Format "yyyyMMdd-HHmmss"
$cloneDir = Join-Path $tmpRoot "$repoSlug-$ts"

New-Item -ItemType Directory -Path $tmpRoot -Force | Out-Null
New-Item -ItemType Directory -Path $reportRoot -Force | Out-Null

$reportFile = Join-Path $reportRoot "repo_intake_report_${repoSlug}_${ts}.md"

if ($sourceMode -eq "remote") {
  Write-Host "[repo-intake] cloning: $sourceInput"
  & git clone --depth 1 $sourceInput $cloneDir | Out-Null
  if ($LASTEXITCODE -ne 0) {
    throw "[repo-intake] gagal clone: $sourceInput"
  }
  $scanDir = $cloneDir
  $sourceLabel = $sourceInput
} else {
  Write-Host "[repo-intake] scanning local path: $scanDir"
}

Write-Host "[repo-intake] scanning repository"

$allFiles = @()
if (Test-Path -LiteralPath $scanDir) {
  $allFiles = @(Get-ChildItem -LiteralPath $scanDir -Recurse -File -Force -ErrorAction SilentlyContinue)
}

$readmeFiles = @($allFiles |
  Where-Object { $_.Name -match "^(?i)readme(\..*)?$" } |
  Where-Object { (To-RelativePath -BasePath $scanDir -FullPath $_.FullName).Split([IO.Path]::DirectorySeparatorChar).Count -le 2 } |
  ForEach-Object { To-RelativePath -BasePath $scanDir -FullPath $_.FullName } |
  Sort-Object -Unique)

$ciFiles = @($allFiles |
  Where-Object { $_.FullName -like "*\.github\workflows\*.yml" } |
  ForEach-Object { To-RelativePath -BasePath $scanDir -FullPath $_.FullName } |
  Sort-Object -Unique)

$manifestNames = @(
  "package.json", "pnpm-workspace.yaml", "pyproject.toml", "requirements.txt",
  "Cargo.toml", "go.mod", "Dockerfile", "docker-compose.yml", ".mcp.json", "mcp.json"
)
$manifestFiles = @($allFiles |
  Where-Object { $manifestNames -contains $_.Name } |
  Where-Object { (To-RelativePath -BasePath $scanDir -FullPath $_.FullName).Split([IO.Path]::DirectorySeparatorChar).Count -le 3 } |
  ForEach-Object { To-RelativePath -BasePath $scanDir -FullPath $_.FullName } |
  Sort-Object -Unique)

$agentFiles = @($allFiles |
  Where-Object {
    $_.Name -in @("AGENTS.md", "CLAUDE.md") -or
    $_.FullName -like "*\.codex\*" -or
    $_.FullName -like "*\.cursor\*"
  } |
  Where-Object { (To-RelativePath -BasePath $scanDir -FullPath $_.FullName).Split([IO.Path]::DirectorySeparatorChar).Count -le 4 } |
  ForEach-Object { To-RelativePath -BasePath $scanDir -FullPath $_.FullName } |
  Sort-Object -Unique)

$skillFiles = @($allFiles |
  Where-Object { $_.Name -eq "SKILL.md" } |
  Where-Object { (To-RelativePath -BasePath $scanDir -FullPath $_.FullName).Split([IO.Path]::DirectorySeparatorChar).Count -le 5 } |
  ForEach-Object { To-RelativePath -BasePath $scanDir -FullPath $_.FullName } |
  Sort-Object -Unique)

$skillCount = $skillFiles.Count

function Format-BulletList {
  param([object[]]$Items)
  if (-not $Items -or $Items.Count -eq 0) { return "- (none found)" }
  return ($Items | ForEach-Object { "- $_" }) -join "`n"
}

$skillSample = if ($skillFiles.Count -gt 40) { $skillFiles[0..39] } else { $skillFiles }

$report = @"
---
name: repo-intake-$repoSlug-$ts
description: Raw intake report generated by repo-intake CLI for $sourceLabel
type: reference
---

## Source
- Input: $sourceLabel
- Mode: $sourceMode
- Cloned at: $ts
- Working path: $scanDir

## Quick Signals
- SKILL.md count: $skillCount

## README Files
$(Format-BulletList -Items $readmeFiles)

## CI Workflows
$(Format-BulletList -Items $ciFiles)

## Build/Runtime Manifests
$(Format-BulletList -Items $manifestFiles)

## Agent/Instruction Files
$(Format-BulletList -Items $agentFiles)

## Skill Files (sample)
$(Format-BulletList -Items $skillSample)

## Next Step for Agent
Use this report as intake evidence, then curate only high-signal patterns into:
- .codex/skills/*
- .codex/README.md
- .codex/memory/memory.md + .codex/memory/<topic>.md
"@

Set-Content -LiteralPath $reportFile -Value ($report.Trim() + "`n") -Encoding UTF8

if (-not $keepClone) {
  if ($sourceMode -eq "remote") {
    Remove-Item -LiteralPath $cloneDir -Recurse -Force -ErrorAction SilentlyContinue
    $cloneState = "deleted"
  } else {
    $cloneState = "kept (local source path)"
  }
} else {
  if ($sourceMode -eq "remote") {
    $cloneState = "kept"
  } else {
    $cloneState = "kept (local source path)"
  }
}

Write-Host "[repo-intake] report: $reportFile"
Write-Host "[repo-intake] clone: $cloneState"
Write-Host "[repo-intake] reports dir: $reportRoot"
