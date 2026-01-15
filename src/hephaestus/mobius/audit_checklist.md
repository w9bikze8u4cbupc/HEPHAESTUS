# MOBIUS Extraction Visual Audit Checklist

## Purpose
This checklist helps verify that MOBIUS-mode extraction produces component-centric output suitable for MOBIUS consumption.

## Extraction Metadata
- **PDF**: {pdf_name}
- **Pages Processed**: {pages_processed}
- **Components Extracted**: {components_extracted}
- **Regions Detected**: {regions_detected}
- **Extraction Mode**: mobius
- **Schema Version**: 9.0-mobius

## Visual Audit Criteria

### ✅ PASS Criteria
1. **No Full-Page Images**: All extracted images are component crops, not full pages
2. **Individual Components**: Each image contains one distinct game component (or grouped components if overlapping)
3. **Clean Boundaries**: Component edges are clearly defined, minimal background
4. **Usable Quality**: Images are clear enough for visual identification
5. **Deterministic Naming**: Filenames follow pattern: `<game>__p<page>__c<crop>__<component>__s<score>.png`

### ❌ FAIL Criteria
1. **Full-Page Captures**: Any image that is essentially a full page render
2. **Excessive Background**: Components with large amounts of surrounding page content
3. **Partial Components**: Cropped components that are cut off or incomplete
4. **Text Blocks**: Extracted regions that are primarily text paragraphs
5. **Headers/Footers**: Page margins or navigation elements extracted as components

## Audit Process

### Step 1: Quick Count Verification
- [ ] Number of extracted images matches `components_extracted` in manifest
- [ ] All images are in `images/` directory
- [ ] manifest.json exists and is valid JSON

### Step 2: Sample Visual Inspection
Open 5-10 random images and verify:
- [ ] Each image contains a recognizable game component
- [ ] No full-page screenshots
- [ ] Minimal extraneous background
- [ ] Component is centered and complete

### Step 3: Manifest Validation
Check manifest.json for:
- [ ] All items have `bbox` coordinates
- [ ] All items have `content_hash`
- [ ] All items have `is_group` flag
- [ ] `component_match` is null (expected until vocabulary provided)
- [ ] `match_score` is 0.0 (expected until vocabulary provided)

### Step 4: Edge Case Review
Look for potential issues:
- [ ] Very small components (< 50x50 pixels) - may be noise
- [ ] Very large components (> 35% of page) - may be layout blocks
- [ ] Extreme aspect ratios (> 8:1) - may be separators/banners
- [ ] Merged regions (`is_group: true`) - verify they are actually overlapping components

## Decision Matrix

| Audit Result | Action |
|--------------|--------|
| All PASS criteria met | ✅ Approve for MOBIUS consumption |
| 1-2 FAIL criteria, minor issues | ⚠️ Acceptable with notes, consider filter tuning |
| 3+ FAIL criteria or major issues | ❌ Reject, adjust detection config and re-extract |

## Notes Section
Use this space to document specific findings:

```
[Add observations here]
```

## Approval
- [ ] Visual audit complete
- [ ] Output suitable for MOBIUS consumption
- [ ] Auditor: _______________
- [ ] Date: _______________
