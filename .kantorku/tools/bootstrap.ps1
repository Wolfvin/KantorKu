#!/usr/bin/env pwsh
# =====================================================
# KantorKu Bootstrap Script (Windows PowerShell)
# Initializes the .kantorku/ workspace for development
# =====================================================

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WorkspaceRoot = Resolve-Path (Join-Path $ScriptDir "..\..")
$KantorkuDir = Join-Path $WorkspaceRoot ".kantorku"
$FrameworkDir = Join-Path $WorkspaceRoot "framework"
$HomeKantorku = Join-Path $env:USERPROFILE ".kantorku"

function Write-Info($msg)  { Write-Host "[INFO]  $msg" -ForegroundColor Blue }
function Write-Ok($msg)    { Write-Host "[OK]    $msg" -ForegroundColor Green }
function Write-Warn($msg)  { Write-Host "[WARN]  $msg" -ForegroundColor Yellow }
function Write-Err($msg)   { Write-Host "[ERROR] $msg" -ForegroundColor Red }

# ─────────────────────────────────────
# Step 1: Install Python dependencies
# ─────────────────────────────────────
function Step-InstallDeps {
    Write-Info "Step 1/5: Installing Python dependencies..."

    if (-not (Test-Path $FrameworkDir)) {
        Write-Err "Framework directory not found: $FrameworkDir"
        exit 1
    }

    Set-Location $FrameworkDir

    $pipCmd = $null
    if (Get-Command pip -ErrorAction SilentlyContinue) {
        $pipCmd = "pip"
    } elseif (Get-Command pip3 -ErrorAction SilentlyContinue) {
        $pipCmd = "pip3"
    } else {
        Write-Err "pip/pip3 not found. Install Python 3.11+ first."
        exit 1
    }

    & $pipCmd install -e ".[all]" 2>&1 | Select-Object -Last 5
    Write-Ok "Python dependencies installed via $pipCmd"
}

# ─────────────────────────────────────
# Step 2: Verify Python 3.11+
# ─────────────────────────────────────
function Step-VerifyPython {
    Write-Info "Step 2/5: Verifying Python version..."

    $pyCmd = $null
    if (Get-Command python3 -ErrorAction SilentlyContinue) {
        $pyCmd = "python3"
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        $pyCmd = "python"
    } else {
        Write-Err "python/python3 not found in PATH"
        exit 1
    }

    $version = & $pyCmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    $parts = $version -split '\.'
    $major = [int]$parts[0]
    $minor = [int]$parts[1]

    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 11)) {
        Write-Err "Python 3.11+ required, found $version"
        exit 1
    }

    Write-Ok "Python $version detected (>= 3.11)"
}

# ─────────────────────────────────────
# Step 3: Link skills to ~/.kantorku/skills/
# ─────────────────────────────────────
function Step-LinkSkills {
    Write-Info "Step 3/5: Linking skills to $HomeKantorku\skills\..."

    New-Item -ItemType Directory -Path $HomeKantorku -Force | Out-Null

    $skillsPath = Join-Path $HomeKantorku "skills"

    if (Test-Path $skillsPath) {
        $item = Get-Item $skillsPath
        if ($item.LinkType -eq "SymbolicLink") {
            Remove-Item $skillsPath -Force
            Write-Info "Removed existing skills symlink"
        } else {
            $backupName = "skills.bak.$(Get-Date -Format 'yyyyMMddHHmmss')"
            Rename-Item $skillsPath $backupName
            Write-Warn "Existing skills directory backed up to $backupName"
        }
    }

    # Create junction (Windows equivalent of symlink)
    New-Item -ItemType Junction -Path $skillsPath -Target (Join-Path $KantorkuDir "skills") | Out-Null
    Write-Ok "Skills linked: $skillsPath -> $(Join-Path $KantorkuDir 'skills')"

    # Copy config.toml if not already present
    $homeConfig = Join-Path $HomeKantorku "config.toml"
    if (-not (Test-Path $homeConfig)) {
        Copy-Item (Join-Path $KantorkuDir "config.toml") $homeConfig
        Write-Ok "Default config copied to $homeConfig"
    } else {
        Write-Info "Existing config.toml found at $HomeKantorku\ -- keeping"
    }
}

# ─────────────────────────────────────
# Step 4: Initialize MEMORY.md
# ─────────────────────────────────────
function Step-InitMemory {
    Write-Info "Step 4/5: Initializing MEMORY.md..."

    $memoryFile = Join-Path $KantorkuDir "memory\MEMORY.md"
    $content = Get-Content $memoryFile -Raw -ErrorAction SilentlyContinue

    if ($content -match "KantorKu" -and $content -match "AI worker") {
        Write-Ok "MEMORY.md already contains project context"
        return
    }

    # Auto-detect project info
    $projectVersion = "0.5.0"
    $pyVersion = "unknown"

    if (Get-Command python3 -ErrorAction SilentlyContinue) {
        $pyVersion = & python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($LASTEXITCODE -ne 0) { $pyVersion = "unknown" }
    }

    $pyprojectPath = Join-Path $FrameworkDir "pyproject.toml"
    if (Test-Path $pyprojectPath) {
        $tomlContent = Get-Content $pyprojectPath -Raw
        $match = [regex]::Match($tomlContent, 'version\s*=\s*"([^"]+)"')
        if ($match.Success) { $projectVersion = $match.Groups[1].Value }
    }

    $timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"

    $memoryContent = @"
# Project Memory

## Context
KantorKu — AI worker orchestration framework modeling a real digital office.
14 specialized workers coordinated by a Conductor (CEO) with contract-based workflows.

**Auto-detected info:**
- Project: KantorKu v$projectVersion
- Python: $pyVersion
- Framework dir: $FrameworkDir
- Bootstrapped: $timestamp

## Key Decisions
- [$((Get-Date).ToString('yyyy-MM-dd'))] Workspace bootstrapped via bootstrap.ps1

## Active Tasks
- [ ] Verify all workers respond to health check

## Completed Tasks
- [x] Workspace bootstrap ($((Get-Date).ToString('yyyy-MM-dd')))

## Learnings
"@

    Set-Content -Path $memoryFile -Value $memoryContent -Encoding UTF8
    Write-Ok "MEMORY.md initialized with project info"
}

# ─────────────────────────────────────
# Step 5: Configure MCP servers
# ─────────────────────────────────────
function Step-ConfigureMCP {
    Write-Info "Step 5/5: Configuring MCP servers..."

    $configFile = Join-Path $FrameworkDir "kantorku.toml"

    if (Test-Path $configFile) {
        Write-Ok "kantorku.toml found at $configFile"

        # Verify the config is valid TOML
        try {
            & python3 -c "import toml; toml.load('$configFile')" 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-Ok "kantorku.toml is valid TOML"
            } else {
                Write-Warn "kantorku.toml may have syntax errors -- verify manually"
            }
        } catch {
            Write-Warn "Could not validate kantorku.toml syntax"
        }
    } else {
        Write-Warn "kantorku.toml not found -- copying from example"
        $exampleFile = Join-Path $FrameworkDir "kantorku.toml.example"
        if (Test-Path $exampleFile) {
            Copy-Item $exampleFile $configFile
            Write-Ok "Copied kantorku.toml.example -> kantorku.toml"
            Write-Info "Edit $configFile to add your API keys"
        } else {
            Write-Warn "kantorku.toml.example not found either -- skip MCP config"
        }
    }

    # Check for kantorku CLI
    if (Get-Command kantorku -ErrorAction SilentlyContinue) {
        Write-Ok "kantorku CLI available"
    } else {
        Write-Info "kantorku CLI not in PATH -- ensure framework is installed: pip install -e '.[all]'"
    }
}

# ─────────────────────────────────────
# Main
# ─────────────────────────────────────
Write-Host ""
Write-Host "=================================================="
Write-Host "   KantorKu Workspace Bootstrap (Windows)"
Write-Host "=================================================="
Write-Host ""

Step-InstallDeps
Step-VerifyPython
Step-LinkSkills
Step-InitMemory
Step-ConfigureMCP

Write-Host ""
Write-Ok "Bootstrap complete! Your workspace is ready."
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Edit framework\kantorku.toml with your API keys"
Write-Host "  2. Run: kantorku setup          (interactive key wizard)"
Write-Host "  3. Run: kantorku serve           (start backend)"
Write-Host "  4. Run: .\.kantorku\tools\guard.sh doctor  (verify health)"
Write-Host ""
