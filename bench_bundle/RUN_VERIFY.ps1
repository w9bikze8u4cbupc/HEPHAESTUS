#!/usr/bin/env pwsh
# Root-level wrapper for bundle verification
# Runs: bench_bundle\tm_g6_g7_g10\verify_bundle.ps1

param(
  [switch]$KeepExtracted
)

$ErrorActionPreference = "Stop"

$verifyScript = Join-Path $PSScriptRoot "tm_g6_g7_g10\verify_bundle.ps1"

if (-not (Test-Path $verifyScript)) {
  Write-Host "[FAIL] Verify script not found: $verifyScript" -ForegroundColor Red
  exit 1
}

# Pass through -KeepExtracted if specified
if ($KeepExtracted) {
  & powershell -ExecutionPolicy Bypass -File $verifyScript -KeepExtracted
} else {
  & powershell -ExecutionPolicy Bypass -File $verifyScript
}

exit $LASTEXITCODE
