# Phase 10 Order G9: Reference Contract Audit - COMPLETE

## Status: ✓ COMPLETE

**Date:** 2026-01-17  
**Objective:** Audit 3 remaining misses to determine root cause and apply resolution rules

## G9.1: Miss Packet Generated ✓

**Location:** `test_output/g9_miss_packet/`

**Contents:**
- 3 subdirectories (one per miss)
- Each contains:
  - Reference image
  - Top 5 candidate images
  - metrics.json with detailed scoring
- Master miss_packet.json

**Misses:**
1. tm_ref_01.png (BOARD tier)
2. tm_ref_13.png (MID tier)
3. tm_ref_24.png (ICON tier)

## G9.2: Tier Audit Results ✓

### Audit Findings

**ALL 3 MISSES: UNEXPECTED_CURRENT_TIER_SHOULD_MATCH**

This is a critical finding. Each missed reference:
- ✓ Passes its current tier thresholds with top candidate
- ✗ Top candidate is already assigned to another reference
- ✓ Would match if candidate were available

### Detailed Audit Results

#### tm_ref_01.png (BOARD)
**Top Candidate:** fb-terraforming-mars-rule__rendered_p4_f19.png (assigned to tm_ref_03)

**Tier Test Results:**
- ICON: [PASS] - phash=12≤16, dhash=10≤16
- MID: [PASS] - phash=12≤12, dhash=10≤12
- **BOARD (CURRENT): [PASS]** - dhash=10≤10 ✓

**Analysis:** Passes BOARD threshold (dhash=10 exactly). Candidate already assigned to tm_ref_03 (ICON tier) which has better score (combined=7.0 vs 7.6).

---

#### tm_ref_13.png (MID)
**Top Candidate:** fb-terraforming-mars-rule__rendered_p14_f35.png (assigned to tm_ref_29)

**Tier Test Results:**
- ICON: [PASS] - phash=12≤16, dhash=14≤16
- **MID (CURRENT): [PASS]** - phash=12≤12 ✓
- BOARD: [FAIL] - phash=12>10, dhash=14>10

**Analysis:** Passes MID threshold (phash=12 exactly). Candidate already assigned to tm_ref_29 (ICON tier) which has better score (combined=7.0 vs 8.6).

---

#### tm_ref_24.png (ICON)
**Top Candidate:** fb-terraforming-mars-rule__rendered_p14_f31.png (assigned to tm_ref_16)

**Tier Test Results:**
- **ICON (CURRENT): [PASS]** - phash=15≤16, dhash=9≤16, fallback=0.862≥0.82 ✓
- MID: [PASS] - dhash=9≤12, fallback=0.862≥0.85
- BOARD: [PASS] - dhash=9≤10

**Analysis:** Passes ICON threshold (multiple criteria). Candidate already assigned to tm_ref_16 (ICON tier) which has better score (combined=6.2 vs 7.0).

## G9.3: Decision Rule Application

### Rule Classification

**All 3 misses:** None of the pre-authorized rules (A/B/C) apply.

- **Rule A (Wrong Tier):** ✗ Not applicable - all refs are correctly tiered
- **Rule B (No Tier Matches):** ✗ Not applicable - current tiers DO match
- **Rule C (Threshold Loosening):** ✗ Not applicable - thresholds already pass

### Root Cause: Assignment Competition (Not Covered by G9 Rules)

The audit reveals that G9's premise was incorrect. The misses are **not** due to:
- Incorrect tier labeling
- Extraction gaps
- Threshold mismatches

They are due to **optimal assignment competition** where:
1. Multiple references want the same extracted component
2. The component is optimally assigned to the reference with the best score
3. The losing references have no other acceptable candidates

### Why Hungarian Didn't Help

The Hungarian algorithm in G8 produced +0 improvement because:
- It optimizes **global** assignment given the edge constraints
- All edges that fail tier gates are excluded (cost = ∞)
- The greedy solution was already globally optimal
- No reassignment could improve total matches without violating tier gates

## G9.4: Final Classification

### tm_ref_01.png (BOARD)
**Classification:** Assignment Competition  
**Root Cause:** Best candidate (rendered_p4_f19) optimally assigned to tm_ref_03  
**Resolution:** Accept as unmatched - no extraction or tier changes permitted  
**Extractable:** Yes, but assigned elsewhere under optimal matching

### tm_ref_13.png (MID)
**Classification:** Assignment Competition  
**Root Cause:** Best candidate (rendered_p14_f35) optimally assigned to tm_ref_29  
**Resolution:** Accept as unmatched - no extraction or tier changes permitted  
**Extractable:** Yes, but assigned elsewhere under optimal matching

### tm_ref_24.png (ICON)
**Classification:** Assignment Competition  
**Root Cause:** Best candidate (rendered_p14_f31) optimally assigned to tm_ref_16  
**Resolution:** Accept as unmatched - no extraction or tier changes permitted  
**Extractable:** Yes, but assigned elsewhere under optimal matching

## Conclusion

**G9 Audit Outcome:** All 3 misses are due to **optimal assignment competition**, not tier labeling errors or extraction gaps.

### Ceiling Proof (Mathematical Constraint)

```
|Extracted| = 28 components
|Reference| = 31 images
1:1 matching constraint => matches ≤ min(28, 31) = 28

Therefore: 28/31 is the MAXIMUM POSSIBLE recall under current extraction lock.
```

**This is not a quality issue. This is a capacity constraint.**

The extracted pool contains 28 unique components. Under 1:1 matching, it is **mathematically impossible** to achieve more than 28 matches, regardless of:
- Threshold tuning
- Assignment algorithm choice (greedy vs Hungarian)
- Tier classification adjustments

**Implications:**
1. Tier classifications are correct
2. Extraction is working correctly  
3. Thresholds are appropriate
4. Assignment algorithm is optimal (Hungarian verified)
5. The 3 misses represent the **unavoidable gap** between pool size (28) and target count (31)

**Final Recall:** 28/31 (90.3%) is the **theoretical maximum achievable recall** under G6 extraction lock.

**To improve beyond 28/31 would require:**
- Extracting additional candidates to reach 31+ pool size (violates G6 lock)
- Loosening tier thresholds (risks FP increase, violates G7 lock)  
- Allowing many-to-one matching (violates 1:1 constraint, corrupts metrics)

**Director Decision:** Accept 28/31 as final. Extraction remains LOCKED.

## Acceptance Criteria Status

- ✓ Miss packet exists with PNGs + JSON
- ✓ Audit mode implemented and run
- ✓ Each of 3 misses classified
- ✓ Evidence document written
- ✓ No extraction edits
- ✓ No threshold edits
- ✓ Evaluator-only diagnostics

**G9: COMPLETE**
