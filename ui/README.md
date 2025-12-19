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

The primary view that displays system health before component browsing:

**Core Metrics** (from `manifest.extraction_health`):
- Images attempted/saved/failed counts
- Success/failure rates
- Fail-fast threshold status (20% threshold explicitly labeled)

**Health ↔ Log Consistency**:
- Invariant verification between manifest metrics and extraction log
- Displays both sources for comparison

**Colorspace Distribution**:
- Direct display of `colorspace_distribution` from manifest
- Shows count and percentage for each colorspace type

**Conversion Operations**:
- Direct display of `conversion_operations` from manifest  
- Shows successful conversion counts by operation type

**Failure Reasons**:
- Enumerated display of `failure_reasons` from manifest
- Shows count and percentage of each failure type

**Source Traceability**:
- Every displayed value includes source field reference
- No derived metrics - all values traceable to manifest/log

### 🚧 Pending Views (Strict Implementation Order)

1. **View 2: Failure Viewer** - Direct extraction_log.jsonl rendering with filtering
2. **View 3: Component Inventory** - Canonical/duplicate grouping with thumbnails
3. **View 4: Component Drilldown** - PDF preview with overlays and metadata

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