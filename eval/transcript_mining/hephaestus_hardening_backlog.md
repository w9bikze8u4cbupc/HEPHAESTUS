# HEPHAESTUS Hardening Backlog (Derived from Transcript Patterns)

## Methodology

All items derived from recurring patterns across multiple independent transcript sources.
Each item includes: pattern reference, risk assessment, proposed test, determinism impact.

## High-Priority Items

### H1: Alpha Channel Normalization Validation

**Pattern Reference**: Pattern 1 (alpha: 11839 mentions across multiple sources)

**Risk**: Alpha/transparency handling may cause extraction inconsistencies or classification errors.

**Proposed Test**: 
- Create test corpus with PDFs containing alpha channel images
- Verify extraction produces consistent RGBA vs RGB output
- Test deduplication with alpha variations

**Determinism Impact**: HIGH - Alpha handling must be deterministic to preserve Phase 5.6 guarantees.

**Status**: Needs investigation

---

### H2: Mask Operation Edge Cases

**Pattern Reference**: Pattern 4 (mask: 4299, soft mask: 2)

**Risk**: Complex masking may cause incomplete or incorrect image extraction.

**Proposed Test**:
- Test PDFs with soft masks, hard masks, and nested masks
- Verify extracted images match visual appearance
- Check for missing or corrupted image data

**Determinism Impact**: MEDIUM - Mask handling should be deterministic but may reveal new edge cases.

**Status**: Needs investigation

---

### H3: Coordinate System Validation

**Pattern Reference**: Pattern 2 (layout: 10867, coordinates: 3197)

**Risk**: Bbox coordinates may be incorrect for certain PDF producers or transformations.

**Proposed Test**:
- Validate bbox accuracy across different PDF producers
- Test rotated/transformed images
- Verify spatial text association accuracy

**Determinism Impact**: LOW - Coordinate extraction is already deterministic, but accuracy may vary.

**Status**: Needs validation

---

## Medium-Priority Items

### M1: DPI Normalization Investigation

**Pattern Reference**: Pattern 6 (DPI: 181, downsample: 67)

**Risk**: Variable DPI may affect classification or deduplication.

**Proposed Test**:
- Analyze DPI distribution in current corpus
- Test if DPI variations affect perceptual hashing
- Consider DPI normalization for classification

**Determinism Impact**: MEDIUM - DPI normalization must be deterministic if implemented.

**Status**: Needs analysis

---

### M2: Compression Format Edge Cases

**Pattern Reference**: Pattern 5 (Flate: 376, JPEG2000: 1)

**Risk**: Rare compression formats may not be handled correctly.

**Proposed Test**:
- Test PDFs with JPEG2000, JBIG2, and other rare formats
- Verify extraction success rate
- Check for format-specific artifacts

**Determinism Impact**: LOW - PyMuPDF handles most formats deterministically.

**Status**: Needs testing

---

### M3: Inline Image Detection

**Pattern Reference**: Boundary Condition 1 (inline image: 1)

**Risk**: Inline images may be missed by current extraction.

**Proposed Test**:
- Identify PDFs with inline images
- Determine if inline images are relevant for component extraction
- Assess impact on extraction completeness

**Determinism Impact**: LOW - Inline images are rare in board game rulebooks.

**Status**: Needs assessment

---

## Low-Priority Items

### L1: ICC Profile Validation

**Pattern Reference**: Pattern 7 (ICC: 423)

**Risk**: ICC profile handling already addressed in Phase 5.6, but edge cases may exist.

**Proposed Test**:
- Verify Phase 5.6 colorspace tests cover ICC profiles
- Test with unusual or malformed ICC profiles

**Determinism Impact**: NONE - Already covered by Phase 5.6 invariants.

**Status**: Covered by existing tests

---

### L2: Scanned PDF Handling

**Pattern Reference**: Misinterpretation 2 (scanned PDF: 22)

**Risk**: Scanned PDFs may have different component characteristics.

**Proposed Test**:
- Analyze scanned vs native PDF extraction differences
- Verify classification accuracy on scanned PDFs

**Determinism Impact**: NONE - Extraction is deterministic regardless of PDF type.

**Status**: Observational only

---

## Items NOT Included (Explicitly Rejected)

1. **Tool switching**: No recommendation to switch from PyMuPDF despite mentions of other libraries.

2. **Page rendering**: ~~HEPHAESTUS extracts embedded images, not page renders. No change needed.~~ **SUPERSEDED BY PHASE 9**: Phase 9 MOBIUS-mode requires page-region cropping for component-aware extraction. This rejection was valid for Phase 8 legacy mode only.

3. **Vector graphics**: Out of scope for raster image extraction.

4. **OCR improvements**: Already implemented via spatial text extraction.

5. **Speculative features**: Only patterns with clear multi-source evidence included.

