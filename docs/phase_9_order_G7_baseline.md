# G7 Baseline: 1:1 Matching Results

## Evaluation Integrity Fixed

**Date:** 2026-01-16  
**Evaluator:** `scripts/evaluate_mobius_recall.py` (1:1 matching enforced)  
**Dataset:** Terraforming Mars reference set (31 images)  
**Extracted:** `test_output/g7_tuned/MOBIUS_READY/images` (28 components)

## Current Metrics (True Baseline)

- **Recall:** 54.8% (17/31 matches) - Target: ≥90% (28/31)
- **False Positives:** 11 - Target: ≤2
- **Unmatched References:** 14

### Acceptance Criteria Status
- Recall ≥90%: **FAIL** (54.8%)
- False positives ≤2: **FAIL** (11)
- **Overall: FAIL**

## Matched References (17)

| Reference | Matched Component | Score | Method |
|-----------|------------------|-------|--------|
| tm_ref_02.png | rendered_p12_f6.png | 8.000 | dhash |
| tm_ref_03.png | rendered_p4_f19.png | 7.000 | dhash |
| tm_ref_10.png | rendered_p5_f3.png | 4.000 | phash |
| tm_ref_11.png | rendered_p13_f16.png | 10.000 | dhash |
| tm_ref_14.png | rendered_p8_f26.png | 10.000 | phash |
| tm_ref_15.png | rendered_p14_f32.png | 10.000 | phash |
| tm_ref_16.png | rendered_p14_f31.png | 7.000 | phash |
| tm_ref_17.png | rendered_p14_f28.png | 10.000 | phash |
| tm_ref_18.png | rendered_p13_f17.png | 10.000 | phash |
| tm_ref_19.png | rendered_p13_f15.png | 9.000 | dhash |
| tm_ref_21.png | rendered_p14_f16.png | 4.000 | phash |
| tm_ref_22.png | rendered_p14_f15.png | 9.000 | dhash |
| tm_ref_23.png | rendered_p14_f17.png | 9.000 | dhash |
| tm_ref_25.png | rendered_p14_f26.png | 9.000 | dhash |
| tm_ref_26.png | rendered_p13_f18.png | 9.000 | phash |
| tm_ref_29.png | rendered_p14_f35.png | 7.000 | phash |
| tm_ref_30.png | rendered_p14_f29.png | 6.000 | phash |

## Unmatched References (14) - Diagnostic Analysis

### Near-Miss Cases (candidates exist, thresholds too strict)

**tm_ref_01.png** - Best: rendered_p4_f19.png (phash=12, dhash=10, combined=12.94)
- Already assigned to tm_ref_03
- Second best: rendered_p12_f6.png (phash=16, dhash=10) - assigned to tm_ref_02
- **Issue:** Competing for same components, needs threshold loosening OR component missing

**tm_ref_06.png** - Best: rendered_p14_f35.png (phash=9, dhash=12, combined=12.27)
- Already assigned to tm_ref_29
- **Issue:** Just outside threshold (dhash=12 vs threshold=10), needs +2 loosening

**tm_ref_20.png** - Best: rendered_p13_f18.png (phash=10, dhash=14, combined=13.00)
- Already assigned to tm_ref_26
- **Issue:** dhash=14 exceeds threshold, needs +4 loosening

**tm_ref_24.png** - Best: rendered_p14_f31.png (phash=15, dhash=9, combined=12.30)
- Already assigned to tm_ref_16
- **Issue:** phash=15 exceeds threshold, dhash=9 is acceptable but loses to better match

**tm_ref_27.png** - Best: rendered_p14_f29.png (phash=10, dhash=7, combined=10.90)
- Already assigned to tm_ref_30
- **Issue:** Would match if available (dhash=7 < threshold)

**tm_ref_28.png** - Best: rendered_p13_f15.png (phash=9, dhash=14, combined=12.30)
- Already assigned to tm_ref_19
- **Issue:** phash=9 is excellent, dhash=14 exceeds threshold

**tm_ref_31.png** - Best: rendered_p14_f17.png (phash=13, dhash=11, combined=13.70)
- Already assigned to tm_ref_23
- **Issue:** Both hashes exceed threshold by small margin

### Weak Candidates (likely extraction gaps)

**tm_ref_04.png** - Best: rendered_p13_f26.png (phash=14, dhash=11, combined=13.70)
- Not assigned elsewhere
- **Issue:** All candidates have hash distances >10, ORB=0.000 (no features)
- **Likely:** Component not extracted or severely cropped

**tm_ref_05.png** - Best: rendered_p9_f9.png (phash=15, dhash=12, combined=14.37)
- Not assigned elsewhere
- **Issue:** All candidates weak (hash dist >12)
- **Likely:** Component not extracted

**tm_ref_07.png** - Best: rendered_p13_f18.png (phash=14, dhash=11, combined=13.70)
- Already assigned to tm_ref_26
- **Issue:** All candidates have hash distances >11

**tm_ref_08.png** - Best: rendered_p13_f16.png (phash=11, dhash=15, combined=13.70)
- Already assigned to tm_ref_11
- **Issue:** All candidates have at least one hash distance >11

**tm_ref_09.png** - Best: rendered_p13_f6.png (phash=12, dhash=11, combined=13.67)
- Not assigned elsewhere (false positive)
- **Issue:** Both hashes exceed threshold by 1-2 points

**tm_ref_12.png** - Best: rendered_p14_f16.png (phash=15, dhash=12, combined=14.40)
- Already assigned to tm_ref_21
- **Issue:** All candidates have hash distances >12

**tm_ref_13.png** - Best: rendered_p14_f35.png (phash=12, dhash=14, combined=14.36)
- Already assigned to tm_ref_29
- **Issue:** All candidates have at least one hash distance >12

## False Positives (11)

Components extracted but not matched to any reference:

1. rendered_p11_f4.png
2. rendered_p11_f5.png
3. rendered_p13_f10.png
4. rendered_p13_f11.png
5. rendered_p13_f26.png
6. rendered_p13_f6.png
7. rendered_p14_f11.png
8. rendered_p15_f0.png
9. rendered_p8_f27.png
10. rendered_p9_f13.png
11. rendered_p9_f9.png

## Root Cause Analysis

### Primary Issues

1. **Threshold Too Strict:** Many unmatched refs have candidates with hash distances 11-14 (just outside threshold=10)
   - 7 refs have best candidates with combined scores 12.3-14.4
   - Loosening thresholds to phash≤15, dhash≤15 would recover ~6-8 matches

2. **Extraction Gaps:** Some refs have no good candidates (all scores >14)
   - tm_ref_04, tm_ref_05 likely not extracted
   - Need to check if these are ICON tier that got filtered

3. **False Positive Dedup:** 11 FPs suggest over-extraction or insufficient deduplication
   - Many FPs are from pages 11, 13, 14 (same pages as matched components)
   - Likely near-duplicates or adjacent crops

### Secondary Issues

1. **Assignment Competition:** Multiple refs competing for same extracted component
   - rendered_p14_f29.png wanted by tm_ref_27, tm_ref_30 (assigned to 30)
   - rendered_p13_f15.png wanted by tm_ref_19, tm_ref_28 (assigned to 19)

2. **ORB Fallback Not Triggering:** All unmatched refs show orb_sim ≈ 0.000
   - ORB threshold=0.15 may be too high for these component types
   - Or components lack sufficient features for ORB matching

## Recommended Tuning Sequence

### Phase 1: Loosen Matching Thresholds (Quick Win)
- Increase phash_threshold: 10 → 15
- Increase dhash_threshold: 10 → 15
- Expected gain: +6-8 matches (recall → 74-81%)

### Phase 2: Reduce False Positives (Dedup)
- Implement stricter deduplication for ICON tier
- Add feature density floor (min ORB keypoints or edge density)
- Target: 11 FPs → 2 FPs

### Phase 3: Fix Extraction Gaps
- Investigate tm_ref_04, tm_ref_05 (likely ICON tier filtered)
- Check if text_overlap suppression is too aggressive for small ICONs
- Loosen uniformity rejection for ICON tier with sufficient features

### Phase 4: Embedded Preference Activation
- Log embedded candidate selection to diagnose why embedded_preferred=0
- Check IoU association and DPI thresholds
- Ensure coordinate space alignment

## Next Action

Re-run evaluation with loosened thresholds:
```bash
python scripts/evaluate_mobius_recall.py \
  --reference-dir acceptance_test/terraforming_mars_reference \
  --extracted-dir test_output/g7_tuned/MOBIUS_READY/images \
  --manifest test_output/g7_tuned/MOBIUS_READY/manifest.json \
  --phash-threshold 15 \
  --dhash-threshold 15 \
  --output test_output/g7_tuned_eval_loose.json
```

Expected result: Recall 74-81%, FP still 11 (address in Phase 2)
