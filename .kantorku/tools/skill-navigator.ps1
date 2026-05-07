Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$CliArgs = @($args)

$mapFile = Join-Path $PSScriptRoot "skill-map.tsv"
$skillsRoot = Join-Path $PSScriptRoot "../skills"

function Show-Usage {
  Write-Host "Usage:"
  Write-Host "  .\.codex\tools\skill-navigator.ps1 suggest <prompt text>"
  Write-Host "  .\.codex\tools\skill-navigator.ps1 list [category]"
}

if ($CliArgs.Count -lt 1) {
  Show-Usage
  exit 1
}

$cmd = $CliArgs[0]
$rest = if ($CliArgs.Count -gt 1) { @($CliArgs[1..($CliArgs.Count - 1)]) } else { @() }

$rows = @()
if (Test-Path -LiteralPath $mapFile) {
  $rows = @(Get-Content -LiteralPath $mapFile | Select-Object -Skip 1 | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | ForEach-Object {
    $parts = $_ -split "`t", 3
    if ($parts.Count -lt 3) { return }
    [pscustomobject]@{
      Skill = $parts[0]
      Category = $parts[1]
      Keywords = $parts[2]
    }
  })
} else {
  $rows = @(Get-ChildItem -LiteralPath $skillsRoot -Directory -ErrorAction SilentlyContinue | ForEach-Object {
    $skillFile = Join-Path $_.FullName "SKILL.md"
    $desc = ""
    if (Test-Path -LiteralPath $skillFile) {
      $descLine = Get-Content -LiteralPath $skillFile | Where-Object { $_ -match '^description:\s*' } | Select-Object -First 1
      if ($descLine) {
        $desc = ($descLine -replace '^description:\s*', '')
      }
    }
    [pscustomobject]@{
      Skill = $_.Name
      Category = "general"
      Keywords = (($_.Name -replace "-", " ") + " " + $desc)
    }
  })
}

switch ($cmd) {
  "suggest" {
    if (@($rest).Count -lt 1) {
      Show-Usage
      exit 1
    }
    $prompt = ($rest -join " ").ToLowerInvariant()
    $scored = foreach ($row in $rows) {
      $score = 0
      $tokens = $row.Keywords -split "\s+" | Where-Object { $_ -ne "" }
      foreach ($token in $tokens) {
        if ($prompt.Contains($token.ToLowerInvariant())) {
          $score++
        }
      }
      if ($score -gt 0) {
        [pscustomobject]@{
          Score = $score
          Skill = $row.Skill
          Category = $row.Category
        }
      }
    }

    $scored |
      Sort-Object -Property @{ Expression = "Score"; Descending = $true }, Skill, Category |
      Select-Object -First 8 |
      ForEach-Object {
        Write-Host "- $($_.Skill) ($($_.Category)) score=$($_.Score)"
      }
    break
  }
  "list" {
    $category = if (@($rest).Count -gt 0) { @($rest)[0] } else { "" }
    if ([string]::IsNullOrWhiteSpace($category)) {
      $rows | ForEach-Object { Write-Host "- $($_.Skill) ($($_.Category))" }
    } else {
      $rows | Where-Object { $_.Category -eq $category } | ForEach-Object { Write-Host "- $($_.Skill) ($($_.Category))" }
    }
    break
  }
  default {
    Show-Usage
    exit 1
  }
}
