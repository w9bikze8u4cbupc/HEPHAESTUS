#!/usr/bin/env pwsh
# Smoke test for tm_g6_g7_g10 bundle
# Validates bundle integrity by running evaluator and checking acceptance criteria

$ErrorActionPreference = "Stop"

Write-Host "=== TM G6-G7-G10 Bundle Smoke Test ===" -ForegroundColor Cyan
Write-Host ""

# Paths
$bundleDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent (Split-Path -Parent $bundleDir)
$referenceDir = Join-Path $repoRoot "acceptance_test\terraforming_mars_reference"
$extractedDir = Join-Path $bundleDir "MOBIUS_READY\images"
$manifest = Join-Path $bundleDir "MOBIUS_READY\manifest.json"
$outputJson = Join-Path $bundleDir "evaluation_smoke.json"
$evaluatorScript = Join-Path $repoRoot "scripts\evaluate_mobius_recall.py"

# Validate paths exist
if (-not (Test-Path $referenceDir)) {
    Write-Host "[FAIL] Reference directory not found: $referenceDir" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $extractedDir)) {
    Write-Host "[FAIL] Extracted images directory not found: $extractedDir" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $manifest)) {
    Write-Host "[FAIL] Manifest not found: $manifest" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $evaluatorScript)) {
    Write-Host "[FAIL] Evaluator script not found: $evaluatorScript" -ForegroundColor Red
    exit 1
}

Write-Host "Running evaluator..." -ForegroundColor Yellow
Write-Host "  Reference: $referenceDir"
Write-Host "  Extracted: $extractedDir"
Write-Host "  Manifest: $manifest"
Write-Host "  Output: $outputJson"
Write-Host ""

# Run evaluator
try {
    python $evaluatorScript `
        --reference-dir $referenceDir `
        --extracted-dir $extractedDir `
        --manifest $manifest `
        --output $outputJson 2>&1 | Out-Null
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[FAIL] Evaluator exited with code $LASTEXITCODE" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "[FAIL] Evaluator execution failed: $_" -ForegroundColor Red
    exit 1
}

# Load results
if (-not (Test-Path $outputJson)) {
    Write-Host "[FAIL] Evaluator did not produce output JSON" -ForegroundColor Red
    exit 1
}

$results = Get-Content $outputJson | ConvertFrom-Json

# Check acceptance criteria
$recall = $results.recall
$falsePositives = $results.false_positives

Write-Host "Results:" -ForegroundColor Cyan
Write-Host "  Recall: $($recall * 100)% ($($results.matches)/$($results.total_references))"
Write-Host "  False Positives: $falsePositives"
Write-Host ""

# Validate acceptance criteria
$recallPass = $recall -ge 0.90
$fpPass = $falsePositives -le 2

if ($recallPass -and $fpPass) {
    Write-Host "[PASS] Bundle validation successful" -ForegroundColor Green
    Write-Host "  Recall >= 90%: PASS ($($recall * 100)%)" -ForegroundColor Green
    Write-Host "  False Positives <= 2: PASS ($falsePositives)" -ForegroundColor Green
    exit 0
} else {
    Write-Host "[FAIL] Bundle validation failed" -ForegroundColor Red
    if (-not $recallPass) {
        Write-Host "  Recall >= 90%: FAIL ($($recall * 100)%)" -ForegroundColor Red
    }
    if (-not $fpPass) {
        Write-Host "  False Positives <= 2: FAIL ($falsePositives)" -ForegroundColor Red
    }
    exit 1
}
