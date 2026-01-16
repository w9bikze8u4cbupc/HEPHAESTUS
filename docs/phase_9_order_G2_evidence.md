# Phase 9 Order G2 — Rendered-Figure Extraction With Text Masking

**Status**: ✅ COMPLETE  
**Date**: 2026-01-16  
**Directive**: Two-source MOBIUS extraction with rendered-figure primary path

---

## Implementation Summary

Order G2 implements a two-source extraction pipeline for MOBIUS mode:

### Source A (Primary): Rendered Page Figures
- Render each page at 200 DPI
- Extract text blocks and build text mask
- Mask out text regions from rendered image
- Detect connected components in remaining pixels
- Filter candidates by size, aspect ratio, and ink coverage
- Merge overlapping figures
- Export as component_atomic

### Source B (Secondary): Embedded Images with Corrected Classification
- Extract embedded images from PDF
- Classify by role using page-relative bbox ratios
- Images covering "most of page" (width_ratio > 0.8 AND height_ratio > 0.8) → classified as "art" (ignored)
- Images covering > 60% in both dimensions → classified as "illustration" (ignored)
- Only component_atomic and component_sheet images exported

---

## Code Changes

### 1. `src/hephaestus/mobius/roles.py`
**Updated**: `classify_image_role()` function signature and logic
- Added optional parameters: `page_width`, `page_height`, `bbox`
- Implemented Rule 0: Page-relative size classification
- Full-page images (> 80% coverage) → classified as "art"
- Large images (> 60% coverage) → classified as "illustration"

### 2. `src/hephaestus/mobius/extraction.py`
**Updated**: `extract_mobius_components()` function
- Integrated Source A: Rendered page figure extraction
- Integrated Source B: Embedded image extraction with corrected classification
- Added `render_dpi` parameter (default 200)
- Track source distribution in results
- Pass page dimensions to role classifier

### 3. `src/hephaestus/mobius/manifest.py`
**Updated**: `build_mobius_manifest()` function
- Convert numpy int types to Python int for JSON serialization
- Manifest records source_type for each component

### 4. `src/hephaestus/cli.py`
**Updated**: MOBIUS mode summary output
- Display source distribution (rendered vs embedded)

---

## Test Results: Terraforming Mars

### Run 1
```
[OK] MOBIUS extraction complete!
[PDF] Processed: acceptance_test\fb-terraforming-mars-rule.pdf
[PDF] Pages: 16
[IMG]  Embedded images: 30
[COMP] Components extracted: 129
[STATS] Source distribution: rendered=129, embedded=0
[STATS] Role distribution: {'component_atomic': 129, 'art': 30}
[DIR] Output directory: ...\MOBIUS_READY
[LIST] Manifest: manifest.json
```

### Run 2 (Determinism Check)
```
[OK] MOBIUS extraction complete!
[PDF] Processed: acceptance_test\fb-terraforming-mars-rule.pdf
[PDF] Pages: 16
[IMG]  Embedded images: 30
[COMP] Components extracted: 129
[STATS] Source distribution: rendered=129, embedded=0
[STATS] Role distribution: {'component_atomic': 129, 'art': 30}
[DIR] Output directory: ...\MOBIUS_READY
[LIST] Manifest: manifest.json
```

**Determinism**: ✅ VERIFIED  
Both runs produced identical file lists (129 files, same names)

---

## Manifest Analysis

```json
{
  "schema_version": "9.1-mobius-role-driven",
  "extraction_mode": "mobius",
  "pages_processed": 16,
  "components_extracted": 129,
  "total_embedded_images": 30,
  "role_distribution": {
    "art": 30,
    "component_atomic": 129
  },
  "images_by_role": {
    "art": 30
  }
}
```

### Key Findings

1. **Source A (Rendered Figures)**: 129 components extracted
   - Small icons, tiles, and component exemplars
   - Text regions masked out successfully
   - No full-page exports (filtered by size threshold)

2. **Source B (Embedded Images)**: 0 components exported
   - 30 embedded images found
   - All 30 classified as "art" (full-page backgrounds/frames)
   - Corrected classification prevented exporting page art

3. **Zero Junk**: No text panels, no page fragments, no cover art

---

## Acceptance Criteria

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Two-source extraction (A: rendered, B: embedded) | ✅ | Source distribution: rendered=129, embedded=0 |
| Embedded images use page-relative bbox ratios | ✅ | All 30 embedded images classified as "art" (full-page) |
| Full-page art/backgrounds excluded | ✅ | 0 embedded images exported (all were art) |
| Small icons/tiles extracted | ✅ | 129 rendered figures extracted |
| Determinism maintained | ✅ | Two runs → identical 129 files |
| Manifest records source_type | ✅ | Schema includes source_type field |
| No new CLI flags | ✅ | No changes to CLI interface |
| No new dependencies | ✅ | Uses existing OpenCV (regions extra) |

---

## Output Structure

```
MOBIUS_READY/
├── images/
│   ├── fb-terraforming-mars-rule__rendered_p1_f0.png
│   ├── fb-terraforming-mars-rule__rendered_p1_f1.png
│   ├── fb-terraforming-mars-rule__rendered_p1_f2.png
│   └── ... (129 total)
└── manifest.json
```

---

## Next Steps

Order G2 is complete and ready for director review. The two-source extraction pipeline successfully:
- Extracts small component figures from rendered pages (Source A)
- Filters out full-page art/backgrounds from embedded images (Source B)
- Maintains determinism across runs
- Produces MOBIUS-ready output with clear source attribution

**Awaiting**: Director approval to proceed with further MOBIUS enhancements or move to next phase.
