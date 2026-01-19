$ErrorActionPreference = "Stop"

$bundleDir = $PSScriptRoot
$zipPath = Join-Path $bundleDir "..\tm_g6_g7_g10.zip"
$shaPath = Join-Path $bundleDir "..\tm_g6_g7_g10.zip.sha256"

Write-Host "=== Build TM G6-G7-G10 Bundle ==="
Write-Host "Bundle dir: $bundleDir"
Write-Host "ZIP:        $zipPath"
Write-Host "SHA:        $shaPath"

if (Test-Path $zipPath) { Remove-Item -Force $zipPath }
if (Test-Path $shaPath) { Remove-Item -Force $shaPath }

Compress-Archive -Path (Join-Path $bundleDir "*") -DestinationPath $zipPath -Force

$h = (Get-FileHash -Algorithm SHA256 $zipPath).Hash.ToLower()
"$h  tm_g6_g7_g10.zip" | Set-Content -Encoding ascii $shaPath

$zipItem = Get-Item $zipPath
Write-Host "Built: $($zipItem.Name) ($($zipItem.Length) bytes)"
Write-Host "SHA256: $h"

exit 0
