# Hephaestus Inspector

**Phase 6.1: Inspection-First UI**

Read-only forensic inspection interface for Hephaestus extraction artifacts.

## Architecture

- **Static, local-first web UI** - No backend services
- **React + TypeScript + Vite** - Modern, type-safe development
- **Direct artifact reading** - Consumes manifest.json and extraction_log.jsonl directly
- **Zero mutation capabilities** - Pure observation interface
- **Immutable artifact contract** - UI reads, never writes

## Current Implementation Status

### ✅ View 1: Extraction Health Panel (COMPLETE)

The primary view that displays system health before component browsing.

### ✅ View 2: Failure Viewer (COMPLETE)

Raw rendering of extraction_log.jsonl with filtering capabilities - failures are primary evidence.

**Core Features**:
- Raw log table with all extraction attempts (stable file order)
- Filtering by: rulebook_id, page_index, image_id, reason_code, status
- Click-through to detailed entry view with:
  - Full raw JSON log entry
  - File existence check (invariant verification)
  - Manifest entry link (or absence explanation)
  - Error and warning details

**Compliance**:
- No aggregation-only views - raw rows always accessible
- Failures appear even with no filters applied
- No grouping that hides individual failures
- No "clean" formatting that obscures raw fields
- No suppression of repeated failures

### ✅ View 3: Component Inventory (COMPLETE)

Canonical/duplicate grouping with thumbnails, classification, confidence, and source page reference.

**Core Features**:
- Deterministic canonical grouping rule: `canonical_image_id` defines groups
- Multiple display modes: Canonical→Duplicates, All Items, Canonicals Only, Duplicates Only
- Sorting options: Page Order, Classification, Confidence, Group Size
- Classification filtering with confidence display
- Thumbnail placeholders with role badges (CANONICAL/DUPLICATE)
- Complete manifest metadata display: label, quantity, dimensions, file reference
- Click-through to View 4 (Component Drilldown) entry point

**Data Model**:
- Groups defined by `manifest.items[].canonical_image_id`
- Canonical item: `image_id === canonical_image_id`
- Duplicate items: `is_duplicate === true` in same group
- All data sourced directly from `manifest.json` items array

### 🚧 Pending Views (Strict Implementation Order)

1. **View 4: Component Drilldown** - PDF preview with overlays and metadata

## Development

```bash
cd ui
npm install
npm run dev
```

## Usage

1. Build the UI: `npm run build`
2. Copy `dist/` folder alongside Hephaestus export
3. Open `index.html` in browser
4. Select Hephaestus export directory

## Expected Directory Structure

```
export_directory/
├── manifest.json           # Required - contains extraction_health
├── extraction_log.jsonl    # Required - contains per-image attempts
├── images/
│   ├── all/               # All extracted images
│   ├── canonicals/        # Canonical images only
│   └── duplicates/        # Duplicate images only
└── package/               # Structured exports by category
```

## Phase 6.1 Constraints

- **No editing capabilities** - Read-only interface
- **No derived metrics** - All values from manifest/log
- **Failures visible by default** - No hiding or suppressing
- **Manifest is truth** - Single source of truth
- **Logs are first-class data** - Not secondary information

## Exit Criteria

Phase 6.1 complete when:
- Reviewer can explain any component/failure end-to-end using only the UI
- Every invariant-protected property is visible somewhere
- No mutation pathways exist in codebase