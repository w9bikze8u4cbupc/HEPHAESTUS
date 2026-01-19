param(
  [string]$ZipPath = (Join-Path $PSScriptRoot "..\tm_g6_g7_g10.zip"),
  [string]$ShaPath = (Join-Path $PSScriptRoot "..\tm_g6_g7_g10.zip.sha256")
)

$ErrorActionPreference = "Stop"

Write-Host "=== TM G6-G7-G10 Bundle Verify ==="

if (-not (Test-Path $ZipPath)) { throw "Missing ZIP: $ZipPath" }
if (-not (Test-Path $ShaPath)) { throw "Missing SHA file: $ShaPath" }

$expectedLine = (Get-Content $ShaPath -Raw).Trim()
if ([string]::IsNullOrWhiteSpace($expectedLine)) { throw "SHA file is empty: $ShaPath" }

# Format: "<hash>  <filename>"
$expectedHash = $expectedLine.Split(" ", [System.StringSplitOptions]::RemoveEmptyEntries)[0].ToLower()
if ($expectedHash.Length -ne 64) { throw "Expected SHA256 hash length 64, got $($expectedHash.Length)" }

$actualHash = (Get-FileHash -Algorithm SHA256 $ZipPath).Hash.ToLower()

Write-Host "Expected: $expectedHash"
Write-Host "Actual:   $actualHash"

if ($actualHash -ne $expectedHash) {
  throw "SHA256 mismatch. ZIP integrity check failed."
}

Write-Host "[PASS] ZIP SHA256 integrity verified."

# Extract to deterministic temp folder
$tmpRoot = Join-Path (Split-Path $ZipPath -Parent) "tmp_verify_tm_g6_g7_g10"
if (Test-Path $tmpRoot) { Remove-Item -Recurse -Force $tmpRoot }
New-Item -ItemType Directory -Force -Path $tmpRoot | Out-Null

Write-Host "Extracting ZIP to: $tmpRoot"
Expand-Archive -Path $ZipPath -DestinationPath $tmpRoot -Force

# Run smoke test against extracted bundle
$bundleDir = $tmpRoot
$smokeScript = Join-Path $bundleDir "smoke_eval.ps1"
if (-not (Test-Path $smokeScript)) { throw "Missing smoke script inside extracted bundle: $smokeScript" }

Write-Host "Running extracted smoke test..."
powershell -ExecutionPolicy Bypass -File $smokeScript

Write-Host "[PASS] Bundle verify complete."
exit 0
