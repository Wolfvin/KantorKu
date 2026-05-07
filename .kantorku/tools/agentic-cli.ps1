Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$CliArgs = @($args)

$scriptDir = $PSScriptRoot
$codexDir = Split-Path -Path $scriptDir -Parent
$projectRoot = Split-Path -Path $codexDir -Parent
$tmpRoot = Join-Path $projectRoot ".tmp/repo-intake"
$reportDir = Join-Path $tmpRoot "reports"

function Show-Usage {
  Write-Host "Usage:"
  Write-Host "  .\.codex\tools\agentic-cli.ps1 intake <repo-url|local-path> [repo-url|local-path ...]"
  Write-Host "  .\.codex\tools\agentic-cli.ps1 sync <source-dir>"
}

if ($CliArgs.Count -lt 1) {
  Show-Usage
  exit 1
}

$cmd = $CliArgs[0]
$rest = if ($CliArgs.Count -gt 1) { @($CliArgs[1..($CliArgs.Count - 1)]) } else { @() }

switch ($cmd) {
  "intake" {
    if (@($rest).Count -lt 1) {
      Show-Usage
      exit 1
    }

    $ts = Get-Date -Format "yyyyMMdd-HHmmss"
    $reportRoot = $reportDir
    New-Item -ItemType Directory -Path $reportRoot -Force | Out-Null

    $summary = Join-Path $reportRoot "summary_$ts.md"
    $synth = Join-Path $reportRoot "synthesis_$ts.md"
    $repoIntakeScript = Join-Path $scriptDir "repo-intake-cli.ps1"

    $summaryLines = @(
      "# Multi Repo Intake Summary",
      "",
      "- Generated: $ts",
      "- Workspace: $projectRoot",
      "",
      "## Sources"
    )

    foreach ($source in $rest) {
      Write-Host "[agentic-cli] intake $source"
      $output = & $repoIntakeScript $source 2>&1
      foreach ($line in $output) { Write-Host $line }
      $reportPath = $null
      foreach ($line in $output) {
        if ($line -match "^\[repo-intake\] report:\s+(.+)$") {
          $reportPath = $matches[1]
          break
        }
      }
      $summaryLines += "- $source"
      if ($reportPath) {
        $summaryLines += "  - Report: $reportPath"
      } else {
        $summaryLines += "  - Report: (unknown)"
      }
    }

    Set-Content -LiteralPath $summary -Value (($summaryLines -join "`n") + "`n") -Encoding UTF8

    $synthContent = @"
# Intake Synthesis

## Guidance
- Keep only high-signal patterns that improve agentic coding quality.
- Prefer official/curated sources when available.
- Do not import leaked or questionable IP.

## Next Steps
- Curate reports listed in summary into:
  - .codex/skills/*
  - .codex/README.md
  - .codex/memory/memory.md + .codex/memory/<topic>.md
"@
    Set-Content -LiteralPath $synth -Value ($synthContent.Trim() + "`n") -Encoding UTF8

    Write-Host "[agentic-cli] summary: $summary"
    Write-Host "[agentic-cli] synthesis: $synth"
    Write-Host "[agentic-cli] reports saved in $reportRoot"
    break
  }
  "sync" {
    if (@($rest).Count -lt 1) {
      Show-Usage
      exit 1
    }
    $src = $rest[0]
    if (-not (Test-Path -LiteralPath $src -PathType Container)) {
      throw "[agentic-cli] source dir not found: $src"
    }
    New-Item -ItemType Directory -Path $reportDir -Force | Out-Null
    Get-ChildItem -LiteralPath $src -Filter *.md -File -ErrorAction SilentlyContinue | ForEach-Object {
      Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $reportDir $_.Name) -Force
    }
    Write-Host "[agentic-cli] synced reports into $reportDir"
    break
  }
  default {
    Show-Usage
    exit 1
  }
}
