# Phase 5.6+ Structural Invariants

## Overview

This directory contains the **structural invariant verification system** that enforces the Phase 5.6 guarantees as permanent architectural constraints. These are not implementation details or optional checks - they are **hard requirements** that must hold across all future development.

## Critical Invariants

### 1. Manifest-Disk Consistency
**Requirement**: `manifest_paths == disk_paths`
- Every file referenced in manifest must exist on disk
- Every file on disk must be referenced in manifest
- No orphaned files or missing references allowed

### 2. Health Metrics Identity  
**Requirement**: `attempted = saved + failures`
- Health metrics must be mathematically consistent
- Log entries must match health metrics
- Manifest entries must match saved count

### 3. Persistence Boundary
**Requirement**: Status must match file existence
- `FAILED` status ⟹ No file exists on disk
- `PERSISTED` status ⟹ File exists with size > 0 bytes
- No partial writes or empty files allowed

### 4. Extraction Log Integrity
**Requirement**: Complete log with proper context
- One JSONL entry per image attempt
- No placeholder context (`image_id=unknown`, `page_index=-1`)
- All required fields present and valid

### 5. Zero Silent Drops
**Requirement**: All failures explicitly logged
- No images can disappear without trace
- All conversion failures must be recorded
- Fail-fast behavior on >20% failure rate

## Special Assertions

### SETI p23_img27
This specific image must be logged as failed on `page_index=23`. This assertion verifies that extraction log context propagation is working correctly and prevents regression to placeholder metadata.

## Usage

### Command Line
```bash
# Verify all invariants
python tests/invariants/phase_5_6_invariants.py

# Run test suite
python -m pytest tests/invariants/test_phase_5_6_invariants.py -v
```

### CI Integration
The `hephaestus-invariants` GitHub Actions workflow automatically verifies these invariants on every push and pull request. **Any violation is a Phase-blocking defect.**

### Development Integration
Before merging any Phase 6+ changes:
1. Run the full Phase 5.6 test suite: `python phase_5_6_test_runner.py`
2. Verify invariants: `python tests/invariants/phase_5_6_invariants.py`
3. Ensure CI passes

## Mini-Corpus

The invariant system uses a pinned mini-corpus of three critical PDFs:
- **Jaipur**: CMYK conversion validation
- **SETI**: ICCBased conversion + failure handling
- **Dune Imperium**: Regression prevention baseline

These represent the core colorspace scenarios that Phase 5.6 resolved.

## Failure Response

If invariants fail:
1. **STOP** - Do not proceed with Phase 6 work
2. **DIAGNOSE** - Identify which invariant is violated
3. **FIX** - Restore the invariant before continuing
4. **VERIFY** - Confirm all invariants pass before resuming

## Architecture Notes

### Why These Invariants Matter
Phase 5.6 resolved the most dangerous class of failure in extraction systems: **false success**. These invariants prevent regression to that failure mode by enforcing:
- Truth in reporting (no silent drops)
- Consistency between components (manifest ↔ disk ↔ logs)
- Proper error handling (explicit failures, not hidden ones)

### Design Principles
1. **Manifest is the API** - All truth flows through manifest
2. **Disk state never drifts** - Physical files match logical records
3. **Failures are data** - Not errors to suppress or hide
4. **No heuristics without visibility** - All decisions must be auditable
5. **Atomic operations** - No partial states or race conditions

## Files

- `phase_5_6_invariants.py` - Core invariant verification logic
- `test_phase_5_6_invariants.py` - Pytest test suite
- `mini_corpus.json` - Pinned test corpus configuration
- `README.md` - This documentation
- `__init__.py` - Module initialization

## Version History

- **v1.0.0** (2025-12-19): Initial Phase 5.6+ invariant system
  - Established 5 core structural invariants
  - Added SETI p23_img27 special assertion
  - Integrated with CI/CD pipeline
  - Created mini-corpus for regression prevention

---

**Remember**: These invariants are architectural constraints, not implementation details. They represent the foundation of system reliability established in Phase 5.6 and must be preserved throughout all future development.