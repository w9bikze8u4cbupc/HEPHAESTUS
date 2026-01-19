# Phase 10 Order G20 Evidence

**Date**: 2026-01-19  
**Order**: G20 - Deterministic Self-Test Mode + Single-Command Evidence  
**Status**: COMPLETE

## Objective

Eliminate repo-file mutation in failure testing and ensure evidence is reproducible under the "one command per step" rule.

## Constraints

- Evaluator/extraction untouched
- Only wrapper + docs modified
- Canonical SHA file never modified during testing
- Single-command invocations only

## Deliverables

### 1. Wrapper Enhancement

**File**: `scripts/validate_and_import_tm.ps1`

**New Switches**:
- `-SelfTestShaFailure`: Simulates SHA mismatch without modifying canonical SHA file
- `-NoImport`: Runs verification only, skips MOBIUS import

**Self-Test Implementation**:
1. Creates unique temp directory per run
2. Copies ZIP to temp
3. Creates corrupted SHA file in temp (all zeros)
4. Calls `verify_bundle.ps1` with temp paths
5. Verifies non-zero exit code
6. Cleans up temp files
7. Exits with code 1 (expected for failure test)

**Key Feature**: Canonical `bench_bundle/tm_g6_g7_g10.zip.sha256` is NEVER modified.

### 2. README Update

**Section**: Consumer Contract

**Added**:
- `-NoImport` option documentation
- `-SelfTestShaFailure` option documentation
- Self-test command example

### 3. Evidence Documentation

This document provides single-command evidence for both success and failure cases.

## Single-Command Evidence

### Success Case

**Command**:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\validate_and_import_tm.ps1
```

**Output**:
```
=== Terraforming Mars Bench: Validate + Import ===
Run ID: f326b2b1

[STEP] Running bundle verifier (SHA + smoke test)...
[PASS] Bundle verification complete
  - SHA-256 integrity: VERIFIED
  - Smoke test: PASS (recall 90.3%, FP 0)

[STEP] Importing bundle into MOBIUS...
[PASS] MOBIUS import complete
  - Components: 28 PNG files
  - Manifest: MOBIUS_READY/manifest.json
  - Cleanup: Temp files removed

=== Validation + Import Complete ===

Benchmark Invariants:
  Recall: 90.3% (28/31)
  False Positives: 0
  Theoretical Ceiling: 28 components vs 31 references

MOBIUS Ingestion Ready:
  Images: MOBIUS_READY/images/*.png (28 files)
  Metadata: MOBIUS_READY/manifest.json
```

**Exit Code**: `0`

### Failure Self-Test Case

**Command**:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\validate_and_import_tm.ps1 -SelfTestShaFailure
```

**Output**:
```
=== Self-Test Mode: SHA Mismatch ===
Run ID: c7072e10

Testing failure path with corrupted SHA (canonical file untouched)...

[STEP] Creating temp SHA file with corrupted hash...
  Temp SHA: bench_bundle\tmp_validate_import_c7072e10\tm_g6_g7_g10.zip.sha256
  Expected: 0000...0000 (corrupted)

[STEP] Running verifier with corrupted SHA...
[PASS] Expected SHA mismatch detected (self-test passed)

=== Self-Test Complete ===
Canonical SHA file was NOT modified
Verifier correctly rejected corrupted hash

Exit code 1 is EXPECTED for this test
```

**Exit Code**: `1` (expected for failure test)

## Acceptance Criteria

| Criterion | Status | Evidence |
|-----------|--------|----------|
| `-SelfTestShaFailure` exits non-zero | ✓ PASS | Exit code 1 |
| Canonical SHA never modified | ✓ PASS | Uses temp SHA file only |
| Success case single command | ✓ PASS | One command, exit 0 |
| Failure case single command | ✓ PASS | One command, exit 1 |
| Exact commands documented | ✓ PASS | Both commands shown above |
| Exact outputs documented | ✓ PASS | Full output captured |

## Verification of Canonical File Integrity

**Before self-test**:
```powershell
Get-Content bench_bundle\tm_g6_g7_g10.zip.sha256
```
Output: `e31012e1afd120096479d779afb14bad5a9868da8105d1d4dc52fd9147f4e7e0  tm_g6_g7_g10.zip`

**After self-test**:
```powershell
Get-Content bench_bundle\tm_g6_g7_g10.zip.sha256
```
Output: `e31012e1afd120096479d779afb14bad5a9868da8105d1d4dc52fd9147f4e7e0  tm_g6_g7_g10.zip`

**Result**: ✓ IDENTICAL - Canonical SHA file was not modified

## Repository Hygiene

**Generated Files**: All temp directories use unique run IDs and are cleaned up automatically.

**Temp Directory Pattern**: `bench_bundle/tmp_validate_import_<GUID>`

**Examples from test runs**:
- `bench_bundle/tmp_validate_import_f326b2b1` (success case)
- `bench_bundle/tmp_validate_import_c7072e10` (self-test case)

**Cleanup**: All temp directories removed after execution (unless `-KeepExtracted`)

**No Drift**: No generated files committed. All artifacts are ephemeral.

## Additional Options

### Verification Only (No Import)

**Command**:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\validate_and_import_tm.ps1 -NoImport
```

**Use Case**: CI stages that only need verification, not full import.

**Behavior**:
- Runs SHA verification
- Runs smoke test
- Skips MOBIUS import
- Exits with code 0 on success

## Files Modified

- `scripts/validate_and_import_tm.ps1` (enhanced with self-test mode)
- `README.md` (added self-test documentation)
- `docs/phase_10_order_G20_evidence.md` (this file)

## Conclusion

G20 deterministic self-test mode is complete:
- ✓ `-SelfTestShaFailure` simulates failure without repo mutation
- ✓ Canonical SHA file never modified during testing
- ✓ Single-command evidence for both success and failure
- ✓ Exit codes explicitly captured (0 for success, 1 for failure)
- ✓ Unique temp directories per run (CI-safe)
- ✓ No repository drift

The wrapper now provides deterministic, reproducible testing without any manual file manipulation.
