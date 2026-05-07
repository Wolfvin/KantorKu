param(
  [Parameter(Mandatory = $true)]
  [string]$ScriptPath,
  [string[]]$ForwardArgs = @()
)

$resolvedScript = Resolve-Path -LiteralPath $ScriptPath -ErrorAction Stop

$bash = Get-Command bash -ErrorAction SilentlyContinue
if ($bash) {
  & $bash.Source $resolvedScript.Path @ForwardArgs
  exit $LASTEXITCODE
}

$wsl = Get-Command wsl -ErrorAction SilentlyContinue
if ($wsl) {
  $wslScript = & $wsl.Source wslpath -a $resolvedScript.Path
  if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($wslScript)) {
    Write-Error "Gagal mengonversi path script untuk WSL: $($resolvedScript.Path)"
    exit 1
  }
  & $wsl.Source bash $wslScript.Trim() @ForwardArgs
  exit $LASTEXITCODE
}

Write-Error "Tidak menemukan 'bash' atau 'wsl'. Install Git Bash atau WSL untuk menjalankan script .sh."
exit 1
