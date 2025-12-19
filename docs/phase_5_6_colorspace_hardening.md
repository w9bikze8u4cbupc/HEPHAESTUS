# Phase 5.6 - PDF Image Colorspace Hardening

**Status:** MANDATORY (Phase 6 Blocker)  
**Priority:** P0 - Critical System Defect  
**Created:** December 19, 2025

## Executive Summary

Phase 5.5 revealed a critical systemic defect in PDF image colorspace handling that causes 33% catastrophic failure on mainstream rulebook PDFs. Phase 5.6 must implement robust colorspace normalization before Phase 6 can proceed.

## Problem Statement

### Current Failure Mode
The Hephaestus PDF ingestion pipeline fails catastrophically on PDFs containing non-RGB colorspaces:

**Failed Rulebooks:**
- **Jaipur:** 0 images persisted (total loss)
- **7 Wonders Duel:** 0 images persisted (total loss)  
- **Viticulture:** 6 images persisted (near-total loss)

**Error Pattern:**
```
ERROR | Failed to save p*_img*: unsupported colorspace for 'png'
ERROR | Failed to save p*_img*: pixmap must be grayscale or rgb to write as png
```

### Root Cause Analysis
1. **Colorspace Diversity:** PDFs contain CMYK, ICCBased, Indexed, DeviceN colorspaces
2. **No Normalization:** Pipeline attempts direct PNG encoding without conversion
3. **Silent Failures:** Images dropped without hard errors or operator visibility
4. **Misleading Manifests:** Downstream stages proceed with empty datasets

## Phase 5.6 Objectives

### Primary Goal
Implement robust colorspace normalization to ensure 100% image persistence across all mainstream PDF formats.

### Success Criteria
1. **Zero Silent Drops:** All colorspace conversion failures must be explicit
2. **Mainstream PDF Support:** Jaipur, 7WD, Viticulture achieve >80% component detection
3. **Health Metrics:** Per-PDF extraction statistics with conversion failure tracking
4. **Fail-Fast Behavior:** Hard errors when >X% images fail conversion

## Required Implementation

### 1. Colorspace Normalization Engine

**Mandatory Conversions:**
- CMYK → RGB (with ICC profile handling)
- ICCBased → RGB (profile-aware conversion)
- Indexed → RGB (palette expansion)
- DeviceN → RGB (separation handling)
- Grayscale → RGB (channel expansion)

**Implementation Requirements:**
- Use proper color management libraries (e.g., Pillow with ICC support)
- Preserve image quality during conversion
- Handle edge cases (missing profiles, corrupted data)
- Log all conversion operations for debugging

### 2. Extraction Health Metrics

**Per-PDF Statistics:**
```json
{
  "extraction_health": {
    "images_attempted": 254,
    "images_saved": 254,
    "conversion_failures": 0,
    "colorspace_distribution": {
      "RGB": 180,
      "CMYK": 74,
      "Indexed": 0,
      "ICCBased": 0
    },
    "conversion_operations": {
      "CMYK_to_RGB": 74,
      "no_conversion": 180
    }
  }
}
```

### 3. Fail-Fast Error Handling

**Hard Error Conditions:**
- `>20%` images fail colorspace conversion
- Missing critical ICC profiles for CMYK content
- Corrupted colorspace data preventing conversion

**Error Reporting:**
- Explicit failure messages with colorspace details
- Conversion attempt logs for debugging
- Clear operator guidance on resolution steps

## Implementation Strategy

### Phase 5.6.1 - Colorspace Detection & Logging
1. Audit all extracted images for colorspace types
2. Log colorspace distribution per PDF
3. Identify conversion requirements without modification

### Phase 5.6.2 - Normalization Implementation  
1. Implement RGB normalization for all colorspace types
2. Add conversion health metrics to manifests
3. Test on failed rulebooks (Jaipur, 7WD, Viticulture)

### Phase 5.6.3 - Validation & Hardening
1. Rerun failed rulebooks with normalization
2. Verify >80% component detection on all 3
3. Validate no silent drops across full corpus
4. Performance impact assessment

## Acceptance Criteria

### Mandatory Requirements
- [ ] **Jaipur rerun:** >0 images persisted, >80% component detection
- [ ] **7 Wonders Duel rerun:** >0 images persisted, >80% component detection  
- [ ] **Viticulture rerun:** >50 images persisted, >80% component detection
- [ ] **Zero silent drops** across all 9 rulebooks
- [ ] **Health metrics** in all manifest files
- [ ] **Hard error** implementation for >20% conversion failures

### Quality Gates
- [ ] No performance degradation >10% on successful PDFs
- [ ] Conversion quality assessment (visual spot checks)
- [ ] Error message clarity validation
- [ ] Documentation of supported colorspace matrix

## Risk Assessment

### Technical Risks
- **Performance Impact:** Colorspace conversion may slow processing
- **Quality Loss:** Conversion artifacts in specific colorspace combinations
- **Library Dependencies:** Additional color management library requirements

### Mitigation Strategies
- Benchmark conversion performance on test corpus
- Implement quality validation checks post-conversion
- Provide fallback conversion methods for edge cases

## Success Metrics

### Quantitative Targets
- **Image Persistence Rate:** 100% (zero silent drops)
- **Failed PDF Recovery:** 3/3 previously failed rulebooks functional
- **Component Detection:** >80% on recovered PDFs
- **Performance Impact:** <10% processing time increase

### Qualitative Validation
- Visual quality assessment of converted images
- Operator error message clarity
- System robustness under edge case conditions

## Phase 6 Unblocking Criteria

Phase 6 can only proceed when:
1. All Phase 5.6 acceptance criteria are met
2. Full corpus (9/9 rulebooks) processes without silent failures
3. Health metrics demonstrate system robustness
4. Performance impact is within acceptable bounds

**Phase 5.6 must be completed before any Phase 6 activities begin.**

## Next Steps

1. **Await Implementation Guidance:** Specific normalization strategy and library recommendations
2. **Colorspace Audit:** Analyze failed PDFs to understand exact colorspace requirements  
3. **Implementation Planning:** Break down work into discrete, testable components
4. **Validation Framework:** Establish testing methodology for conversion quality

---

**Phase 5.6 Status:** PENDING IMPLEMENTATION  
**Phase 6 Status:** BLOCKED (Dependent on Phase 5.6 completion)