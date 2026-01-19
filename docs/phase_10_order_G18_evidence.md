# Phase 10 Order G18 Evidence

**Date**: 2026-01-19  
**Order**: G18 - MOBIUS Integration Harness  
**Status**: COMPLETE

## Objective

Add minimal, production-safe integration pathway in MOBIUS that:
- Accepts `tm_g6_g7_g10.zip` (or extracted folder)
- Verifies SHA-256 integrity
- Consumes canonical payload: `MOBIUS_READY/images/*.png` + `manifest.json`
- Exposes single "import + validate" command for CI

## Constraints

✓ No changes to G6/G7 evaluator logic  
✓ No new heuristics  
✓ Deterministic, Windows-safe, Unicode-safe  
✓ No manual steps required

## Deliverables

### 1. Bench Importer Module

**File**: `src/hephaestus/mobius/bench_importer.py`

**Features**:
- SHA-256 verification against `.sha256` file
- ZIP extraction to temp directory
- Bundle structure validation (MOBIUS_READY/images/*.png + manifest.json)
- Manifest schema validation
- Automatic cleanup (optional `--keep-extracted`)
- Reports ingestion paths for MOBIUS consumption

### 2. CLI Command

**Command**: `python -m hephaestus.cli bench import-tm --zip <path>`

**Integration**: Added as subcommand to main HEPHAESTUS CLI via Typer

**Help Output**:
```
Usage: python -m hephaestus.cli bench [OPTIONS] COMMAND [ARGS]...

Bench bundle import commands

Commands:
  import-tm   Import Terraforming Mars bench bundle (tm_g6_g7_g10.zip).
```

### 3. CI Smoke Test

**File**: `scripts/ci_bench_smoke.ps1`

**Behavior**:
- Runs `bench_bundle\RUN_VERIFY.ps1`
- Asserts recall >= 0.90
- Asserts FP <= 2
- Exits non-zero on failure

## Command Output Evidence

### CLI Import Command

```bash
python -m hephaestus.cli bench import-tm --zip bench_bundle\tm_g6_g7_g10.zip
```

**Output**:
```
=== MOBIUS Bench Import: Terraforming Mars ===
ZIP: bench_bundle\tm_g6_g7_g10.zip
SHA: bench_bundle\tm_g6_g7_g10.zip.sha256
Expected: e31012e1afd120096479d779afb14bad5a9868da8105d1d4dc52fd9147f4e7e0
Actual:   e31012e1afd120096479d779afb14bad5a9868da8105d1d4dc52fd9147f4e7e0
[PASS] SHA-256 integrity verified
Extract: bench_bundle\tmp_import_tm_g6_g7_g10
[PASS] Bundle extracted
[PASS] Bundle structure validated
[INFO] Components extracted: 28
[INFO] Manifest items: 28
[PASS] Manifest loaded

=== MOBIUS Ingestion Paths ===
Images:   bench_bundle\tmp_import_tm_g6_g7_g10\MOBIUS_READY\images
Manifest: bench_bundle\tmp_import_tm_g6_g7_g10\MOBIUS_READY\manifest.json
Count:    28 PNG files

[INFO] Cleaning up extracted files...

[PASS] Import complete

Expected baseline:
  Recall: 90.3% (28/31)
  False positives: 0
  Theoretical ceiling: 28 components vs 31 references
```

**Exit Code**: 0

### CI Smoke Test

```bash
powershell -ExecutionPolicy Bypass -File scripts\ci_bench_smoke.ps1
```

**Output**:
```
=== CI Bench Smoke Test ===

Running bundle verifier...
=== TM G6-G7-G10 Bundle Verify ===
Expected: e31012e1afd120096479d779afb14bad5a9868da8105d1d4dc52fd9147f4e7e0
Actual:   e31012e1afd120096479d779afb14bad5a9868da8105d1d4dc52fd9147f4e7e0
[PASS] ZIP SHA256 integrity verified.
Extracting ZIP to: C:\HEPHAESTUS\bench_bundle\tmp_verify_tm_g6_g7_g10
Running extracted smoke test...
=== TM G6-G7-G10 Bundle Smoke Test ===

Running evaluator...
  Reference: C:\HEPHAESTUS\acceptance_test\terraforming_mars_reference
  Extracted: C:\HEPHAESTUS\bench_bundle\tmp_verify_tm_g6_g7_g10\MOBIUS_READY\images
  Manifest: C:\HEPHAESTUS\bench_bundle\tmp_verify_tm_g6_g7_g10\MOBIUS_READY\manifest.json
  Output: C:\HEPHAESTUS\bench_bundle\tmp_verify_tm_g6_g7_g10\evaluation_smoke.json

Results:
  Recall: 90.3225806451612900% (28/31)
  False Positives: 0

[PASS] Bundle validation successful
  Recall >= 90%: PASS (90.3225806451612900%)
  False Positives <= 2: PASS (0)
[PASS] Bundle verify complete.

[PASS] CI Bench Smoke Test Complete
  - SHA-256 integrity: VERIFIED
  - Bundle extraction: SUCCESS
  - Recall >= 90%: PASS (90.3%)
  - False positives <= 2: PASS (0)
```

**Exit Code**: 0

## Validation Results

| Check | Status | Value |
|-------|--------|-------|
| SHA-256 Integrity | ✓ PASS | Verified |
| Bundle Extraction | ✓ PASS | Success |
| Structure Validation | ✓ PASS | MOBIUS_READY present |
| Manifest Schema | ✓ PASS | Valid JSON |
| Components Count | ✓ PASS | 28 components |
| Recall >= 90% | ✓ PASS | 90.3% (28/31) |
| False Positives <= 2 | ✓ PASS | 0 |

## Integration Pathway

### For MOBIUS Consumption

1. **Fetch bundle**: Download `tm_g6_g7_g10.zip` + `.sha256`
2. **Import**: `python -m hephaestus.cli bench import-tm --zip <path> --keep-extracted`
3. **Ingest files**:
   - Images: `<extract-dir>/MOBIUS_READY/images/*.png`
   - Metadata: `<extract-dir>/MOBIUS_READY/manifest.json`

### For CI Pipeline

```yaml
- name: Validate Bench Bundle
  run: powershell -ExecutionPolicy Bypass -File scripts\ci_bench_smoke.ps1
```

## Files Modified

- `src/hephaestus/mobius/bench_importer.py` (new)
- `src/hephaestus/cli.py` (added bench subcommand)
- `scripts/ci_bench_smoke.ps1` (new)
- `docs/phase_10_order_G18_evidence.md` (this file)

## Conclusion

G18 integration harness is complete and validated:
- ✓ Non-invasive (no changes to G6/G7 logic)
- ✓ Deterministic and Windows-safe
- ✓ Single-command import with SHA verification
- ✓ CI-ready smoke test
- ✓ Benchmark invariants confirmed (90.3% recall, 0 FP)

The bundle is ready for MOBIUS production integration.
