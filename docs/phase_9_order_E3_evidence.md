# Phase 9 Order E3: Text Density Coordinate Mapping - Evidence

**Date:** 2026-01-15  
**Commit:** cce3f36  
**Status:** COMPLETE

---

## Objective

Fix text-density filtering by ensuring region bboxes and text bboxes are in the same coordinate space (pixel space) prior to intersection.

---

## Coordinate Transform Used

**Transform:** PDF page space → Pixel space

**Method:**
1. PyMuPDF text blocks are extracted in PDF page coordinates (points)
2. Region bboxes are detected in pixel coordinates (from rendered image)
3. Transform text block bboxes to pixel space using scale factors:
   - `scale_x = img_width / page_width`
   - `scale_y = img_height / page_height`
4. Compute intersection in pixel space
5. Calculate text density as: `(total_chars / region_area_pixels) * 1000`

**Key Code:**
```python
# Transform text block to pixel coordinates
pix_bx0 = int(pdf_bx0 * scale_x)
pix_by0 = int(pdf_by0 * scale_y)
pix_bx1 = int(pdf_bx1 * scale_x)
pix_by1 = int(pdf_by1 * scale_y)

# Check intersection (both in pixel space)
if not (pix_bx1 < x or pix_bx0 > x + w or pix_by1 < y or pix_by0 > y + h):
    total_chars += len(text.strip())
```

---

## CLI Command Used

```powershell
python -m hephaestus.cli extract acceptance_test/fb-terraforming-mars-rule.pdf `
  --output "$env:USERPROFILE\Desktop\HEPHAESTUS_TEST_RUN1" `
  --mode mobius
```

---

## Extraction Results

```
✅ MOBIUS extraction complete!
📄 Processed: acceptance_test\fb-terraforming-mars-rule.pdf
📄 Pages: 16
🖼️  Components extracted: 13
🔍 Regions detected: 2138
🚫 Regions filtered: 2125
📁 Output directory: ...\MOBIUS_READY
📋 Manifest: manifest.json
```

---

## Manifest Evidence

### Filtered Summary

```json
{
  "text_panel": 1,
  "border_bottom": 4,
  "border_left": 8,
  "border_right": 2,
  "border_top": 10,
  "oversize_region": 32,
  "too_small": 2068
}
```

**✅ filtered_summary.text_panel = 1** (was 0 in Order E2)

---

## Debug Text Density Values

### Rejected Text Panel (p15_c1 candidate)

```json
{
  "bbox": [26.39, 352.30, 216.41, 637.40],
  "debug_text_density": 1.7175118185219196,
  "page_index": 15,
  "rejection_reason": "text_panel"
}
```

**Text density:** 1.72 chars/1000px² (above threshold of 1.5)

### Exported Components (Sample)

**p0_c0:**
- `debug_text_density`: 0.0

**p0_c1:**
- `debug_text_density`: 0.0

**p15_c0:**
- `debug_text_density`: 0.0

All exported components have text_density below threshold (< 1.5).

---

## Acceptance Criteria

### ✅ PASS

1. **Terraforming Mars run shows filtered_summary.text_panel > 0**
   - text_panel: 1 ✅

2. **Previous text panel crop (p15_c1) is not exported**
   - p15_c1 filtered with rejection_reason="text_panel" ✅
   - Only p15_c0 exported from page 15 ✅

3. **debug_text_density field added to manifest**
   - All exported items have debug_text_density ✅
   - Filtered text panel has debug_text_density=1.72 ✅

4. **Determinism preserved**
   - Run 1: 13 files
   - Run 2: 13 files
   - Run 3: 13 files
   - File lists identical across all runs ✅

---

## Determinism Proof

**Test:** 3 consecutive runs with identical command

**Results:**
```
Run 1: 13 files
Run 2: 13 files
Run 3: 13 files
✓ All 3 runs have identical file lists
```

**File list (all runs):**
- fb-terraforming-mars-rule__p0__c0__unknown__s000.png
- fb-terraforming-mars-rule__p0__c1__unknown__s000.png
- fb-terraforming-mars-rule__p0__c2__unknown__s000.png
- fb-terraforming-mars-rule__p0__c3__unknown__s000.png
- fb-terraforming-mars-rule__p0__c4__unknown__s000.png
- fb-terraforming-mars-rule__p0__c5__unknown__s000.png
- fb-terraforming-mars-rule__p0__c6__unknown__s000.png
- fb-terraforming-mars-rule__p0__c7__unknown__s000.png
- fb-terraforming-mars-rule__p0__c8__unknown__s000.png
- fb-terraforming-mars-rule__p0__c9__unknown__s000.png
- fb-terraforming-mars-rule__p0__c10__unknown__s000.png
- fb-terraforming-mars-rule__p0__c11__unknown__s000.png
- fb-terraforming-mars-rule__p15__c0__unknown__s000.png

**Note:** p15_c1 (text panel) consistently filtered across all runs.

---

## Technical Implementation

### Files Changed

1. **src/hephaestus/regions/detection.py**
   - Updated `_is_text_dense_region()` to transform text blocks to pixel space
   - Added `text_density` field to `DetectedRegion` and `FilteredRegion`
   - Updated `text_density_threshold` to 1.5 chars/1000px²

2. **src/hephaestus/mobius/extraction.py**
   - Added `debug_text_density` field to `MobiusComponent`
   - Updated `filtered_regions_detail` to include text_density
   - Pass text_density from regions to components

3. **src/hephaestus/mobius/manifest.py**
   - Added `debug_text_density` to `MobiusManifestItem`
   - Added `debug_text_density` to `FilteredRegionRecord`
   - Updated manifest building to populate text_density fields

### Constraints Met

- ✅ No new CLI flags
- ✅ No new dependencies
- ✅ No OCR/Vision/ML
- ✅ No recall tuning beyond coordinate fix

---

## Stop Condition Met

Evidence produced:
- ✅ Coordinate transform explained (PDF→pixel via scale factors)
- ✅ Manifest excerpt with filtered_summary.text_panel = 1
- ✅ debug_text_density values for 2 exported crops (p0_c0, p0_c1)
- ✅ debug_text_density for rejected p15_c1 panel (1.72)
- ✅ Determinism proof (3 runs, identical file lists)

**Order E3 execution complete. Awaiting director review.**
