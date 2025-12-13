# Implementation Plan

## Project Setup and Foundation

- [x] 1. Set up project structure and build system


  - Create `pyproject.toml` with hatchling build system, Python 3.11+ requirement
  - Configure dependencies: pymupdf, Pillow, typer[all], rich
  - Configure dev dependencies: pytest, black, ruff, mypy, hypothesis
  - Set up package structure under `src/hephaestus/`
  - Configure tool settings for black, ruff, mypy in pyproject.toml
  - Create basic `README.md` with installation and usage instructions
  - _Requirements: FR-6.1, NFR-2, NFR-3_



- [ ] 2. Implement core configuration and logging modules
  - Create `src/hephaestus/__init__.py` package initialization
  - Implement `config.py` with Settings dataclass for output_dir, min dimensions
  - Implement `logging.py` with get_logger function and structured formatting


  - _Requirements: FR-6.1, FR-5.1_

- [x] 2.1 Write property test for configuration validation


  - **Property 11: Config Invariants**
  - **Validates: Requirements FR-4.2, FR-5.1**

## PDF Processing Core

- [ ] 3. Implement PDF ingestion module
  - Create `src/hephaestus/pdf/__init__.py` package


  - Implement custom exceptions: PdfOpenError, EncryptedPdfError in `pdf/ingestion.py`
  - Implement PdfPage class with index, width, height properties and raw() method

  - Implement PdfDocument class with path, page_count properties and pages() method
  - Add file existence validation and PyMuPDF error handling
  - _Requirements: FR-1.1, FR-1.2, FR-5.2_

- [ ] 3.1 Write property test for PDF document processing
  - **Property 1: Deterministic IDs**


  - **Validates: Requirements FR-2.3**

- [ ] 3.2 Write unit tests for PDF ingestion
  - Test opening valid PDFs with correct page count and dimensions
  - Test error handling for non-existent files, corrupted PDFs, encrypted PDFs
  - Test page iteration and metadata extraction
  - _Requirements: FR-1.1, FR-1.2, FR-7.1_



## Image Extraction Engine


- [ ] 4. Implement image extraction and filtering
  - Define ImageSourceType literal and ExtractedImage dataclass in `pdf/images.py`

  - Implement extract_embedded_images function with PyMuPDF image extraction
  - Add dimensional filtering logic with configurable thresholds
  - Implement stable ID generation using "p{page_idx}_img{local_idx}" format
  - Add INFO and DEBUG level logging for extraction progress and filtering decisions
  - _Requirements: FR-2.1, FR-2.2, FR-2.3, FR-5.1_


- [ ] 4.1 Write property test for size threshold filtering
  - **Property 2: Size Threshold Monotonicity**
  - **Validates: Requirements FR-2.2**

- [ ] 4.2 Write property test for ID generation stability
  - **Property 1: Deterministic IDs**
  - **Validates: Requirements FR-2.3**


- [ ] 4.3 Write unit tests for image extraction
  - Test extraction from PDFs with known embedded image counts
  - Test filtering behavior with various threshold combinations

  - Test ID generation format and uniqueness
  - _Requirements: FR-2.1, FR-2.2, FR-2.3, FR-7.1_


## File Output Management

- [ ] 5. Implement image saving and export
  - Implement save_images_flat function in `pdf/images.py`
  - Add automatic output directory creation
  - Implement PNG format conversion using PyMuPDF or Pillow
  - Use "component_{image_id}.png" naming convention

  - Return list of saved file paths
  - _Requirements: FR-3.1, FR-3.2_

- [-] 5.1 Write property test for file output quality

  - **Property 8: Format Validity**
  - **Validates: Requirements FR-3.1**

- [x] 5.2 Write property test for filename uniqueness


  - **Property 5: No Orphan Files**
  - **Validates: Requirements FR-3.1, FR-3.2**


- [ ] 5.3 Write unit tests for image saving
  - Test automatic directory creation

  - Test PNG format validity using Pillow verification
  - Test filename convention compliance
  - Test file count matches extracted image count
  - _Requirements: FR-3.1, FR-3.2, FR-7.1_

## CLI Interface Implementation


- [ ] 6. Implement command-line interface
  - Create `cli.py` with Typer application setup
  - Implement extract command with pdf_path argument and options for output_dir, min_width, min_height
  - Add comprehensive error handling for PDF opening failures with appropriate exit codes
  - Integrate logging throughout the extraction pipeline
  - Add progress reporting and summary statistics
  - Configure CLI entry point in pyproject.toml

  - _Requirements: FR-4.1, FR-4.2, FR-5.1, FR-5.2_

- [x] 6.1 Write property test for CLI parameter application

  - **Property 5: CLI Parameter Application**
  - **Validates: Requirements FR-4.2**

- [x] 6.2 Write property test for exit code semantics

  - **Property 4: Exit Code Semantics**
  - **Validates: Requirements FR-5.2**

- [ ] 6.3 Write unit tests for CLI interface
  - Test successful extraction workflow with valid PDFs
  - Test error handling for invalid inputs and processing failures
  - Test help text display and option parsing
  - Test exit codes for various failure scenarios

  - _Requirements: FR-4.1, FR-4.2, FR-5.2, FR-7.1_

## Error Handling and Robustness


- [x] 7. Implement comprehensive error handling

  - Add graceful degradation for individual page/image processing failures
  - Implement proper exception logging with stack traces in debug mode
  - Ensure processing continues when recoverable errors occur
  - Add validation for configuration parameters and user inputs
  - _Requirements: FR-5.1, FR-5.2_

- [ ] 7.1 Write property test for graceful failure handling
  - **Property 3: Non-crashing on Single-page Failure**



  - **Validates: Requirements FR-5.2**

- [ ] 7.2 Write property test for logging consistency
  - **Property 8: Logging Consistency**
  - **Validates: Requirements FR-5.1**

## Testing Infrastructure and Validation

- [ ] 8. Create comprehensive test suite
  - Set up pytest configuration and test discovery
  - Create programmatic PDF generation utilities for consistent test data
  - Implement test fixtures for various PDF scenarios (valid, corrupted, encrypted, multi-page)
  - Add property-based test generators for images, dimensions, and file paths
  - Configure Hypothesis settings for minimum 100 iterations per property test
  - _Requirements: FR-7.1, FR-7.2_

- [ ] 8.1 Write property test for page ordering preservation
  - **Property 9: Page Ordering**
  - **Validates: Requirements FR-1.2, FR-2.1**

- [ ] 8.2 Write property test for thread-safety of utilities
  - **Property 10: Thread-safety of Pure Utilities**
  - **Validates: Requirements FR-6.1**

- [ ] 9. Integration testing and validation
  - Create end-to-end integration tests using real PDF samples
  - Test complete extraction pipeline from CLI invocation to file output
  - Validate performance requirements with typical rulebook PDFs
  - Test cross-platform compatibility (Windows, macOS, Linux)
  - _Requirements: FR-7.1, NFR-1, NFR-2_

## Phase 5: Structured Output Packaging

- [x] 10. Create output packaging module



  - Create `src/hephaestus/output/__init__.py` package
  - Implement PackageResult and ManifestItem dataclasses in `output/package.py`
  - Implement category mapping logic for classification labels to folder names
  - Create directory structure creation utilities
  - _Requirements: FR-7.1, FR-7.3_



- [ ] 10.1 Write property test for directory structure consistency
  - **Property 12: Directory Structure Consistency**

  - **Validates: Requirements FR-7.1**

- [ ] 10.2 Write property test for category mapping determinism
  - **Property 13: Category Mapping Determinism**
  - **Validates: Requirements FR-7.1**

- [ ] 11. Implement packaging logic and file operations
  - Implement package_exports function with copy-based file operations
  - Add support for export modes (all vs canonicals-only)
  - Implement include_non_components filtering logic
  - Add manifest path field updates (path_all, path_primary, path_duplicate)
  - Ensure idempotent operations with safe file overwriting
  - _Requirements: FR-7.2, FR-7.3, FR-7.5_

- [ ] 11.1 Write property test for export mode compliance
  - **Property 14: Export Mode Compliance**
  - **Validates: Requirements FR-7.2**

- [ ] 11.2 Write property test for manifest path accuracy
  - **Property 15: Manifest Path Accuracy**
  - **Validates: Requirements FR-7.3**

- [ ] 11.3 Write property test for packaging idempotence
  - **Property 16: Packaging Idempotence**
  - **Validates: Requirements FR-7.5**

- [ ] 12. Add packaging CLI options and integration
  - Add --package/--no-package, --export-mode, --include-non-components options to CLI
  - Integrate packaging step into extraction pipeline
  - Update CLI help text and option descriptions
  - Add packaging statistics to output logging
  - _Requirements: FR-7.4_

- [ ] 12.1 Write unit tests for packaging CLI options
  - Test CLI option parsing and validation
  - Test integration of packaging with extraction pipeline
  - Test packaging statistics reporting
  - _Requirements: FR-7.4, FR-8.1_

- [ ] 13. Create comprehensive packaging tests
  - Implement unit tests for package_exports function
  - Test directory creation, file copying, and manifest updates
  - Test Windows-safe file operations (no WinError 32)
  - Test all export modes and configuration combinations
  - _Requirements: FR-8.1_

- [ ] 13.1 Write property test for file copy preservation
  - **Property 17: File Copy Preservation**
  - **Validates: Requirements FR-7.5**

- [ ] 14. Phase 5 checkpoint - structured output validation
  - Ensure all tests pass, ask the user if questions arise
  - Validate complete directory layout creation
  - Test canonicals-only mode exports only canonical images
  - Verify manifest includes correct paths
  - Test idempotent re-runs produce identical results
  - _Requirements: FR-7.1, FR-7.2, FR-7.3, FR-7.5_

## Final Checkpoint and Documentation

- [ ] 15. Final validation and documentation
  - Ensure all tests pass, ask the user if questions arise
  - Validate code quality with black, ruff, and mypy
  - Update README.md with complete installation, usage, and feature documentation including Phase 5 options
  - Add docstrings and type hints throughout codebase
  - Verify CLI help text and error messages are clear and actionable
  - Update design.md and requirements.md with Phase 5 structured output documentation
  - _Requirements: FR-4.1, FR-5.1, FR-7.4, NFR-3_