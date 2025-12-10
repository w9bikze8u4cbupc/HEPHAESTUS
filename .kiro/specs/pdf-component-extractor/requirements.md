# HEPHAESTUS – PDF Component Extraction System

## Requirements (EARS + INCOSE style)

## 1. Introduction

HEPHAESTUS is a modular system that ingests board-game rulebook PDFs, extracts visual components, classifies them, associates them with textual labels and quantities, de-duplicates similar assets, and exports images plus a structured manifest for downstream tools.

This document specifies the **functional and non-functional requirements** for the system, following EARS patterns and INCOSE quality guidelines.

## 2. Glossary

- **Rulebook PDF** – A PDF file containing the rules and components of a board game
- **Component image** – An image representing a physical game piece (card, token, board, tile, etc.)
- **Non-component image** – Decorative art, logos, icons, or layout elements not intended as physical pieces
- **Manifest** – A structured machine-readable file (JSON) describing all extracted components, their labels, quantities, and metadata
- **MVP** – Minimum Viable Product (Phase 1: PDF ingestion + embedded image extraction + flat file output)
- **Perceptual hash** – A hash of an image that preserves visual similarity (for de-duplication)
- **HEPHAESTUS** – The PDF board-game component extraction system
- **PyMuPDF** – Python library (fitz) for PDF document manipulation and parsing
- **CLI** – Command-line interface for system interaction

## 3. System Context

When provided with one or more rulebook PDFs, the system will:

1. Load each document safely
2. Extract images (initially embedded raster images; later vector and page-rendered images)
3. Filter and classify candidate component images
4. Associate names, descriptions, and quantities from nearby text
5. De-duplicate similar images
6. Export images to disk and a JSON manifest describing them

## 4. Functional Requirements

### 4.1 PDF Ingestion & Parsing

**FR-1.1 – Open PDF documents**

_When_ the user provides a path to a PDF file, _the HEPHAESTUS shall_ attempt to open the file using PyMuPDF and expose pages via a stable interface.

**Acceptance criteria**
- WHEN a valid PDF is provided, THE HEPHAESTUS SHALL return a document object with the correct page count
- WHEN a non-existent path is provided, THE HEPHAESTUS SHALL emit a clear "file not found" error and non-zero exit code
- WHEN an encrypted PDF is provided, THE HEPHAESTUS SHALL emit a specific "encrypted document" error and not crash

**FR-1.2 – Page metadata**

_When_ a PDF is successfully opened, _the HEPHAESTUS shall_ provide page-level metadata including index, width, and height for each page.

**Acceptance criteria**
- WHEN querying page dimensions from a known test PDF, THE HEPHAESTUS SHALL match PyMuPDF values within 1 pixel
- WHEN iterating over pages, THE HEPHAESTUS SHALL yield indices `[0..N-1]` with no gaps

### 4.2 Image Extraction & Filtering (Phase 1 MVP)

**FR-2.1 – Embedded image extraction**

_When_ a PDF is processed, _the HEPHAESTUS shall_ extract all embedded raster images from every page.

**Acceptance criteria**
- WHEN processing a PDF with a known number of embedded images, THE HEPHAESTUS SHALL return that number before filtering
- WHEN extracting images, THE HEPHAESTUS SHALL associate each extracted image with its source page index

**FR-2.2 – Size-based filtering**

_When_ images are extracted, _the HEPHAESTUS shall_ filter out images whose width or height is below configurable thresholds.

**Acceptance criteria**
- WHEN processing a test PDF with small (e.g. 16×16) and large (e.g. 300×300) images, THE HEPHAESTUS SHALL retain only the large images after filtering when thresholds are set above 16
- WHEN filtering images, THE HEPHAESTUS SHALL log filter decisions at debug level, including original dimensions and threshold values

**FR-2.3 – Stable image identifiers**

_When_ images are extracted, _the HEPHAESTUS shall_ assign deterministic, human-readable IDs based on page index and image index.

**Acceptance criteria**
- WHEN running the extractor multiple times on the same PDF with the same configuration, THE HEPHAESTUS SHALL yield identical IDs for each image
- WHEN changing logging verbosity, THE HEPHAESTUS SHALL maintain stable IDs across runs

### 4.3 File Output Management

**FR-3.1 – Image export**

_When_ extraction succeeds, _the HEPHAESTUS shall_ save all retained images into an output directory in a standard format (PNG by default).

**Acceptance criteria**
- WHEN the output directory does not exist, THE HEPHAESTUS SHALL create it automatically
- WHEN saving images, THE HEPHAESTUS SHALL create valid PNGs that can be opened by Pillow
- WHEN extraction completes, THE HEPHAESTUS SHALL ensure the number of PNG files equals the number of retained images

**FR-3.2 – Naming convention**

_When_ images are saved, _the HEPHAESTUS shall_ use a consistent and descriptive naming convention that embeds the image ID.

**Acceptance criteria**
- WHEN saving images during Phase 1, THE HEPHAESTUS SHALL use filenames following the pattern `component_<image_id>.png`
- WHEN processing multiple images in a single run, THE HEPHAESTUS SHALL ensure no two images produce the same file path

### 4.4 CLI Interface

**FR-4.1 – Basic CLI command**

_When_ the user runs `hephaestus extract <pdf_path>`, _the HEPHAESTUS shall_ process the specified PDF and export images to an output directory.

**Acceptance criteria**
- WHEN running the command with a valid PDF, THE HEPHAESTUS SHALL produce an output directory containing images
- WHEN running with `--help`, THE HEPHAESTUS SHALL show usage information, options, and defaults

**FR-4.2 – Configurable thresholds**

_When_ the user runs the CLI, _the HEPHAESTUS shall_ allow overriding minimum width, minimum height, and output directory via options.

**Acceptance criteria**
- WHEN running with `--min-width` and `--min-height`, THE HEPHAESTUS SHALL change which images are retained
- WHEN running with `--out`, THE HEPHAESTUS SHALL write files to the specified directory

### 4.5 Logging & Error Handling

**FR-5.1 – Informative logging**

_When_ the HEPHAESTUS processes a PDF, _the HEPHAESTUS shall_ log high-level progress (open, extract, save) at INFO level and detailed extraction decisions at DEBUG level.

**Acceptance criteria**
- WHEN processing PDFs, THE HEPHAESTUS SHALL log PDF path, page count, number of images found, number retained, and number saved
- WHEN errors occur, THE HEPHAESTUS SHALL include a clear message and stack trace (in debug mode) without exposing secrets or environment details

**FR-5.2 – Graceful failure**

_When_ a recoverable error occurs on a page or image, _the HEPHAESTUS shall_ log the error and continue processing the remaining pages/images.

**Acceptance criteria**
- WHEN a single corrupted image is encountered, THE HEPHAESTUS SHALL not abort the whole extraction
- WHEN at least one image is successfully processed, THE HEPHAESTUS SHALL maintain CLI exit code zero; non-zero for complete failure (e.g., unable to open document)

### 4.6 Modular Architecture & Extensibility

**FR-6.1 – Pipeline modularity**

_When_ implementing the system, _the design shall_ separate concerns into modules: config, logging, PDF ingestion, image extraction, classification (future), metadata (future), deduplication (future), and output management.

**Acceptance criteria**
- WHEN running unit tests, THE HEPHAESTUS SHALL allow exercising PDF ingestion without invoking image extraction and vice versa
- WHEN adding future modules (e.g., classifier), THE HEPHAESTUS SHALL allow integration without changing the public API of existing modules

### 4.7 Testing Strategy

**FR-7.1 – Unit tests**

_When_ the codebase is built, _the HEPHAESTUS shall_ include unit tests for all critical functions.

**Acceptance criteria**
- WHEN running `pytest`, THE HEPHAESTUS SHALL execute successfully in CI and locally
- WHEN testing the system, THE HEPHAESTUS SHALL include tests for PDF opening, image extraction, filtering, and CLI behavior

**FR-7.2 – Property-based tests (core logic)**

_When_ feasible, _the HEPHAESTUS shall_ employ property-based testing for pure functions (e.g., ID generation, naming, filtering).

**Acceptance criteria**
- WHEN testing key modules, THE HEPHAESTUS SHALL include at least one module (e.g., filtering or naming) covered by Hypothesis tests that explore a wide range of randomized inputs

## 5. Non-Functional Requirements

**NFR-1 – Performance**

_When_ processing a typical rulebook (≤ 100 pages), _the HEPHAESTUS should_ complete Phase 1 extraction on a modern laptop in under 60 seconds.

**NFR-2 – Portability**

_When_ installed, _the HEPHAESTUS shall_ run on Windows, macOS, and Linux with Python 3.11+.

**NFR-3 – Maintainability**

_When_ the system evolves, _the codebase shall_ follow PEP-8, include type hints, and pass linting (Black, Ruff, MyPy) to remain maintainable.

## 6. Open Issues

- Vision-based classifier design is deferred to a later phase
- Ground-truth dataset for component recall/precision is not yet defined
- Threshold defaults (size, aspect ratio, hash similarity) will be tuned empirically in future phases