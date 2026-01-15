# Phase 9: MOBIUS-Ready Extraction – CLI Contract

## Status
- **Phase**: 9 (MOBIUS Alignment & Component-Centric Extraction)
- **Document Type**: Authoritative CLI Specification
- **Implementation Status**: Design only - not yet implemented
- **Authority**: Director-approved

## Core Objective

Produce MOBIUS-ready component images from rulebook PDFs with explicit component awareness and region-based extraction.

## Command-Line Interface

### Basic Usage

```bash
# MOBIUS mode (default) - component-aware region extraction
python -m hephaestus extract <pdf_path> --mode mobius --components <components.json> --out <output_dir>

# Legacy mode - embedded image extraction (Phase 8 behavior)
python -m hephaestus extract <pdf_path> --mode legacy --out <output_dir>
```

### Required Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `pdf_path` | Path | Path to rulebook PDF file |

### Mode Selection

| Flag | Values | Default | Description |
|------|--------|---------|-------------|
| `--mode` | `mobius` \| `legacy` | `mobius` | Extraction pipeline mode |

**Mode Behaviors**:

- **`mobius`**: Page rendering → region detection → component crops → MOBIUS-ready output
- **`legacy`**: Embedded image extraction (Phase 8 D2 behavior, preserved for stability)

### MOBIUS Mode Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--components` | Path | None | Path to component list JSON (optional but recommended) |
| `--components-json` | String | None | Component list as JSON string (alternative to file) |
| `--out` | Path | `output` | Output directory for MOBIUS-ready assets |
| `--dpi` | Integer | `150` | DPI for page rendering (higher = better quality, slower) |
| `--min-region-area` | Integer | `2500` | Minimum region area in pixels (50x50 default) |
| `--max-region-ratio` | Float | `0.8` | Maximum region size as ratio of page (0.8 = 80% of page) |
| `--merge-threshold` | Float | `0.3` | IoU threshold for merging overlapping regions |
| `--dedup-threshold` | Integer | `8` | Perceptual hash distance for deduplication |
| `--whitelist-full-page` | String | None | Comma-separated page numbers to allow full-page extraction |

### Legacy Mode Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--out` | Path | `output` | Output directory |
| `--min-width` | Integer | `50` | Minimum image width in pixels |
| `--min-height` | Integer | `50` | Minimum image height in pixels |
| `--dedup` | Boolean | `True` | Enable deduplication |
| `--dedup-threshold` | Integer | `8` | Perceptual hash distance threshold |

### Common Flags (Both Modes)

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--verbose` | Boolean | `False` | Enable verbose logging |
| `--write-manifest` | Boolean | `True` | Write manifest.json |
| `--deterministic` | Boolean | `True` | Enforce deterministic output |

## Component List Schema

### Input Format

```json
{
  "game": "Terraforming Mars",
  "components": [
    {
      "name": "player_boards",
      "aliases": ["player board", "corporation board"],
      "category": "board",
      "expected_count": 5,
      "notes": "One per player color"
    },
    {
      "name": "resource_cubes",
      "aliases": ["cubes", "resources"],
      "category": "token",
      "expected_count": null,
      "notes": "Multiple colors and types"
    },
    {
      "name": "project_cards",
      "aliases": ["cards", "project deck"],
      "category": "card",
      "expected_count": 208,
      "notes": "Main deck"
    }
  ]
}
```

### Schema Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `game` | String | No | Game name for context |
| `components` | Array | Yes | List of expected components |
| `components[].name` | String | Yes | Primary component identifier (slug-safe) |
| `components[].aliases` | Array[String] | No | Alternative names for matching |
| `components[].category` | String | No | Component type: `board`, `card`, `token`, `tile`, `other` |
| `components[].expected_count` | Integer\|null | No | Expected quantity (null = unknown) |
| `components[].notes` | String | No | Human-readable context |

## Output Structure (MOBIUS Mode)

### Directory Layout

```
<output_dir>/
├── images/                          # MOBIUS-ready component images
│   ├── <game>__p01__c001__player_boards__s95.png
│   ├── <game>__p01__c002__resource_cubes__group__s87.png
│   ├── <game>__p03__c001__project_cards__s92.png
│   └── ...
├── manifest.json                    # Integration contract
├── duplicates.json                  # Deduplication mapping
└── extraction_log.jsonl             # Detailed extraction log
```

### File Naming Convention

**Format**: `<game>__p<page>__c<crop>__<component>__[group__]s<score>.png`

**Components**:
- `<game>`: Slugified game name (lowercase, underscores)
- `p<page>`: Zero-padded page number (p01, p02, ...)
- `c<crop>`: Zero-padded crop index within page (c001, c002, ...)
- `<component>`: Matched component name or `unknown`
- `[group__]`: Optional marker for grouped components
- `s<score>`: Match confidence score (0-100)

**Examples**:
```
terraforming_mars__p05__c002__coins__s87.png
terraforming_mars__p07__c001__cards__group__s92.png
terraforming_mars__p12__c003__unknown__s00.png
```

**Rules**:
- All lowercase
- Underscores for spaces
- Zero-padded numbers for sorting
- `unknown` only when no component match found
- `group` marker for merged/overlapping components

### Manifest Schema (manifest.json)

```json
{
  "hephaestus_version": "9.0.0",
  "extraction_mode": "mobius",
  "source_pdf": "path/to/rulebook.pdf",
  "source_pdf_hash": "sha256:...",
  "components_input": "path/to/components.json",
  "components_input_hash": "sha256:...",
  "extraction_timestamp": "2026-01-15T12:00:00Z",
  "run_parameters": {
    "dpi": 150,
    "min_region_area": 2500,
    "max_region_ratio": 0.8,
    "merge_threshold": 0.3,
    "dedup_threshold": 8
  },
  "summary": {
    "total_pages": 16,
    "total_regions": 45,
    "total_images": 30,
    "grouped_images": 5,
    "matched_components": 25,
    "unknown_components": 5,
    "duplicate_groups": 12
  },
  "images": [
    {
      "file": "terraforming_mars__p05__c002__coins__s87.png",
      "page": 5,
      "crop_index": 2,
      "bbox": [120, 340, 180, 180],
      "grouped": false,
      "component_match": [
        {
          "name": "coins",
          "score": 0.87,
          "basis": "text_proximity+layout",
          "matched_alias": "currency"
        }
      ],
      "dedup": {
        "canonical_id": "img_015",
        "is_duplicate": false,
        "duplicate_of": null,
        "duplicate_count": 3
      }
    },
    {
      "file": "terraforming_mars__p07__c001__cards__group__s92.png",
      "page": 7,
      "crop_index": 1,
      "bbox": [80, 200, 400, 600],
      "grouped": true,
      "group_reason": "overlapping_assets",
      "component_match": [
        {
          "name": "project_cards",
          "score": 0.92,
          "basis": "layout+category",
          "matched_alias": "cards"
        }
      ],
      "dedup": {
        "canonical_id": "img_023",
        "is_duplicate": false,
        "duplicate_of": null,
        "duplicate_count": 0
      }
    }
  ]
}
```

### Duplicates Schema (duplicates.json)

```json
{
  "duplicate_groups": [
    {
      "canonical_id": "img_015",
      "canonical_file": "terraforming_mars__p05__c002__coins__s87.png",
      "duplicates": [
        {
          "file": "terraforming_mars__p08__c003__coins__s87.png",
          "page": 8,
          "hash_distance": 2
        },
        {
          "file": "terraforming_mars__p11__c001__coins__s87.png",
          "page": 11,
          "hash_distance": 3
        }
      ]
    }
  ]
}
```

## Determinism Guarantees

### MOBIUS Mode

1. **Page Rendering**: Same PDF + same DPI → identical rendered pages
2. **Region Detection**: Deterministic contour detection and filtering
3. **Bounding Box Ordering**: Sorted by (page, y, x) for consistent crop indices
4. **Component Matching**: Deterministic scoring (no randomness)
5. **Deduplication**: Deterministic perceptual hashing and canonical selection
6. **File Naming**: Deterministic based on page order and crop index
7. **Manifest Output**: Sorted keys, stable float precision (6 decimals)

### Legacy Mode

Preserves all Phase 8 D2 determinism guarantees (unchanged).

## Failure Modes

### Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success | Output ready for MOBIUS |
| 1 | PDF open error | Check file path and permissions |
| 2 | Component list parse error | Validate JSON schema |
| 3 | Region detection failure | Check DPI and page rendering |
| 4 | No regions found | Adjust min_region_area or check PDF content |
| 5 | Manifest write error | Check output directory permissions |

### Error Messages

All errors must include:
- Clear description of what failed
- Actionable remediation steps
- No stack traces in normal mode (use --verbose for debugging)

### Graceful Degradation

- **No component list provided**: Run in best-effort mode, mark all as `unknown`
- **Component matching fails**: Mark as `unknown`, include in output
- **Region detection finds nothing**: Fail with clear error (no silent fallback to full pages)
- **Deduplication fails**: Continue without dedup, log warning

## Acceptance Statement

**If this command runs successfully:**

```bash
python -m hephaestus extract rulebook.pdf \
  --mode mobius \
  --components components.json \
  --out MOBIUS_READY
```

**Then MOBIUS can:**

1. ✅ Load `MOBIUS_READY/manifest.json` to discover all component images
2. ✅ Use images from `MOBIUS_READY/images/` directly in video timeline
3. ✅ Match images to component list using manifest metadata
4. ✅ Identify grouped components via `grouped: true` flag
5. ✅ Handle duplicates using `duplicates.json` mapping
6. ✅ Trust that output is deterministic and reproducible
7. ✅ Consume output **without human intervention or workarounds**

## What This Does NOT Include

- ❌ No dashboard or web UI
- ❌ No export to external services
- ❌ No consumer-facing abstractions
- ❌ No SaaS or cloud integration
- ❌ No scope beyond: PDF → component images → MOBIUS
- ❌ No automatic component list generation (MOBIUS provides this)
- ❌ No ML-based region detection (heuristics only for Phase 9)

## Implementation Status

**Current**: Design specification only  
**Next**: Phase 9 Step 2 - Region detection module implementation  
**Timeline**: Immediate start authorized by director

## Version History

- **v9.0.0-draft**: Initial CLI contract (2026-01-15)
