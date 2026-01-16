# Phase 9 Order G: Image-Role–Driven MOBIUS Extraction - Evidence

**Date:** 2026-01-15  
**Commit:** bf76c8f  
**Status:** COMPLETE - ARCHITECTURAL LOCK

---

## CLI Command Used

```powershell
python -m hephaestus.cli extract acceptance_test/fb-terraforming-mars-rule.pdf `
  --output "$env:USERPROFILE\Desktop\HEPHAESTUS_ORDER_G_RUN1" `
  --mode mobius
```

---

## Extraction Results

```
✅ MOBIUS extraction complete!
📄 Processed: acceptance_test\fb-terraforming-mars-rule.pdf
📄 Pages: 16
🖼️  Embedded images: 30
🎯 Components extracted: 30
📊 Role distribution: {'component_atomic': 30}
📁 Output directory: ...\MOBIUS_READY
```

---

## Manifest Evidence

### Role Distribution

```json
{
  "component_atomic": 30,
  "component_sheet": 0,
  "illustration": 0,
  "diagram": 0,
  "art": 0
}
```

**All 30 embedded images classified as component_atomic and exported whole.**

### Image Counts Per Role

- **component_atomic:** 30 (exported)
- **component_sheet:** 0 (would be segmented if present)
- **illustration:** 0 (ignored)
- **diagram:** 0 (never exported)
- **art:** 0 (ignored)

### Sample Manifest Item

```json
{
  "component_id": "atomic_p0_img0",
  "source_type": "embedded",
  "image_role": "component_atomic",
  "width": 776,
  "height": 964,
  "sheet_id": null,
  "component_bbox_in_sheet": null
}
```

---

## Determinism Proof

**Test:** 2 consecutive runs with identical command

**Results:**
```
Run 1: 30 files
Run 2: 30 files
✓ Deterministic: file lists identical
```

---

## Architecture Implementation

### Core Invariant (LOCKED)

**Cropping is FORBIDDEN unless image_role == component_sheet.**

✅ Verified: No cropping performed. All 30 components exported whole (component_atomic).

### Image-Role Taxonomy

1. **component_atomic** - Single indivisible component (exported whole, never cropped)
2. **component_sheet** - Multiple similar components (only role allowed to be subdivided)
3. **illustration** - Context/explanation (ignored by default)
4. **diagram** - Annotated/editorial (never exported)
5. **art** - Cover art (ignored)

### Pipeline Order

1. ✅ Extract embedded images (primary source)
2. ✅ Classify each image by role
3. ✅ Segment component_sheet images only (none found in Terraforming Mars)
4. ✅ Export atomic components

---

## Legacy Mode Integration

**How legacy extraction feeds MOBIUS mode:**

Legacy mode (`extract_embedded_images`) extracts embedded raster images from PDF. MOBIUS mode uses the SAME extraction function but adds:
1. Image-role classification
2. Sheet segmentation (for component_sheet only)
3. Role-based filtering

**No page rendering** is used as primary source. Embedded images are the authoritative source.

---

## Cross-Game Validation

### Terraforming Mars ✅

- **Embedded images:** 30
- **Components extracted:** 30 (all atomic)
- **No page fragments:** ✅
- **No text panels:** ✅
- **No invented components:** ✅

### Expected Behavior for Other Games

**Scythe:** Would extract structure bonus tiles as atomic components. If component sheets present, would segment.

**Hanamikoji:** Would extract only atomic cards. No sheets invented. No cropping performed.

---

## Constraints Met

- ✅ No new CLI flags
- ✅ No new dependencies (uses existing OpenCV from regions extra)
- ✅ No Vision API / OCR / ML
- ✅ No heuristic page mining as primary logic
- ✅ Legacy mode unaffected

---

## Files Changed

1. **src/hephaestus/mobius/roles.py** (NEW) - Image-role classification
2. **src/hephaestus/mobius/sheets.py** (NEW) - Component sheet segmentation
3. **src/hephaestus/mobius/extraction.py** - Rewritten for image-role architecture
4. **src/hephaestus/mobius/manifest.py** - Updated for role-driven manifest
5. **src/hephaestus/cli.py** - Updated MOBIUS mode integration

---

## Stop Condition Met

Evidence produced:
- ✅ CLI command documented
- ✅ Manifest excerpts showing role distribution (30 atomic, 0 sheets)
- ✅ Image counts per role
- ✅ Determinism proof (2 runs, identical file lists)
- ✅ Legacy integration explanation

**Order G execution complete. Phase 9 architecture locked.**
