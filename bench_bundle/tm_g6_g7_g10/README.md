# Terraforming Mars G6-G7-G10 Production Bundle

**Date**: 2026-01-17  
**Phase**: HEPHAESTUS Phase 10 Complete  
**Status**: PASS (90.3% recall, 0 false positives)

## Overview

This bundle contains the complete MOBIUS extraction output and evaluation results for Terraforming Mars rulebook, validated against 31 reference images with tier-aware thresholds and 1:1 matching enforcement.

## Contents

### 1. Extraction Output (`MOBIUS_READY/`)
- `images/` - 28 extracted component images (PNG format)
- `manifest.json` - Complete extraction metadata with bbox coordinates, DPI, size tiers

### 2. Evaluation Results
- `evaluation.json` - Full evaluation metrics and match details
- `evaluation.log` - Human-readable evaluation output with ceiling warning

### 3. Evidence Documentation
- `G7_evidence.md` - Tier-aware threshold acceptance evidence
- `G9_evidence.md` - Miss packet audit and theoretical ceiling analysis
- `G10_evidence.md` - Final validation with ceiling warning banner

### 4. Miss Packet (`miss_packet/`)
- Reference images for 3 unmatched components
- Top 5 candidate images per miss
- Detailed metrics JSON per miss
- Audit results showing all 3 misses are assignment competition (not extraction gaps)

## Acceptance Criteria (G7.5)

✓ **Recall ≥90%**: PASS (90.3%, 28/31 matches)  
✓ **False Positives ≤2**: PASS (0 false positives)  
✓ **1:1 Matching**: Enforced via greedy + Hungarian algorithm  
✓ **Unicode-Safe**: Windows path handling fixed  
✓ **Tier-Aware**: ICON/MID/BOARD thresholds applied

## Tier Breakdown

| Tier | References | Matches | Recall | Thresholds |
|------|-----------|---------|--------|------------|
| ICON | 26 | 25 | 96.2% | phash≤16, dhash≤16, ORB≥0.08, fallback≥0.82 |
| MID | 4 | 3 | 75.0% | phash≤12, dhash≤12, ORB≥0.12, fallback≥0.85 |
| BOARD | 1 | 0 | 0.0% | phash≤10, dhash≤10, ORB≥0.15, fallback≥0.88 |

## Theoretical Ceiling

**Extracted Pool**: 28 components  
**Reference Set**: 31 images  
**Max Possible Recall (1:1)**: 90.3% (28/31)

The 3 unmatched references are due to **assignment competition** under 1:1 constraint:
- All 3 top candidates pass their tier thresholds
- All 3 top candidates are already optimally assigned to other references
- This is the theoretical maximum given current extraction output

## Unmatched References

1. **tm_ref_01.png** (BOARD) - Main game board
   - Top candidate: `rendered_p4_f19.png` (assigned to tm_ref_03.png)
   - Passes ICON/MID/BOARD thresholds but optimally assigned elsewhere

2. **tm_ref_13.png** (MID) - Mid-size component
   - Top candidate: `rendered_p14_f35.png` (assigned to tm_ref_29.png)
   - Passes ICON/MID thresholds but optimally assigned elsewhere

3. **tm_ref_24.png** (ICON) - Small icon
   - Top candidate: `rendered_p14_f31.png` (assigned to tm_ref_16.png)
   - Passes ICON/MID/BOARD thresholds but optimally assigned elsewhere

## G9 Audit Conclusion

**Classification**: All 3 misses show `UNEXPECTED_CURRENT_TIER_SHOULD_MATCH`

This means:
- ✗ Not Rule A (wrong tier) - all pass their current tier
- ✗ Not Rule B (no tier matches) - all pass multiple tiers
- ✗ Not Rule C (threshold mismatch) - all pass thresholds

**Root Cause**: Pure assignment competition under 1:1 constraint. The extracted pool (28) is smaller than the reference set (31), creating a hard ceiling at 90.3%.

## Usage

### Run Evaluation
```bash
python scripts/evaluate_mobius_recall.py \
  --reference-dir acceptance_test/terraforming_mars_reference \
  --extracted-dir bench_bundle/tm_g6_g7_g10/MOBIUS_READY/images \
  --manifest bench_bundle/tm_g6_g7_g10/MOBIUS_READY/manifest.json \
  --output results.json
```

### Generate Miss Packet
```bash
python scripts/evaluate_mobius_recall.py \
  --reference-dir acceptance_test/terraforming_mars_reference \
  --extracted-dir bench_bundle/tm_g6_g7_g10/MOBIUS_READY/images \
  --manifest bench_bundle/tm_g6_g7_g10/MOBIUS_READY/manifest.json \
  --output results.json \
  --generate-miss-packet miss_packet_output/
```

### Run Tier Audit
```bash
python scripts/evaluate_mobius_recall.py \
  --reference-dir acceptance_test/terraforming_mars_reference \
  --extracted-dir bench_bundle/tm_g6_g7_g10/MOBIUS_READY/images \
  --manifest bench_bundle/tm_g6_g7_g10/MOBIUS_READY/manifest.json \
  --output results.json \
  --audit-misses
```

## System Requirements

- Python 3.8+
- opencv-python
- pillow
- imagehash
- scipy (for Hungarian algorithm)

## Phase History

- **G6**: Extraction optimization (locked)
- **G7**: Evaluation harness with tier-aware thresholds (locked)
- **G8**: Hungarian algorithm optimization (no improvement, greedy was optimal)
- **G9**: Miss packet audit (confirmed theoretical ceiling)
- **G10**: Ceiling warning banner + CLI validation

## Next Steps

This bundle is ready for:
1. MOBIUS consumption (28 high-quality components)
2. Cross-game generalization testing
3. Reference pack expansion (if higher recall needed)
4. Production deployment

## Contact

For questions about this bundle or the evaluation methodology, refer to:
- `docs/phase_9_order_G7_evidence.md` - G7 acceptance evidence
- `docs/phase_10_order_G9_evidence.md` - G9 audit analysis
- `scripts/evaluate_mobius_recall.py` - Evaluation harness source
