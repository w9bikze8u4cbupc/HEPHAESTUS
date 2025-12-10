# HEPHAESTUS

HEPHAESTUS is a modular PDF board-game component extraction system that processes rulebook PDFs to extract, filter, and organize component images.

## Features

**Phase 1 (Current):**
- PDF ingestion and parsing with PyMuPDF
- Embedded image extraction with dimensional filtering
- PNG export with structured naming
- Command-line interface with configurable parameters
- Comprehensive error handling and logging

**Future Phases:**
- AI-powered component classification
- Spatial text extraction and association
- Perceptual deduplication
- JSON manifest generation
- Web UI for visual review

## Installation

```bash
# Clone the repository
git clone https://github.com/w9bikze8u4cbupc/HEPHAESTUS.git
cd HEPHAESTUS

# Install with development dependencies
pip install -e ".[dev]"
```

## Usage

```bash
# Extract components from a PDF
hephaestus extract rulebook.pdf

# Specify output directory and filtering thresholds
hephaestus extract rulebook.pdf --out components/ --min-width 100 --min-height 100

# Show help
hephaestus extract --help
```

## Development

```bash
# Run tests
pytest

# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type check
mypy src/
```

## Architecture

HEPHAESTUS follows a modular pipeline architecture:

- **PDF Ingestion**: Robust document parsing with error handling
- **Image Extraction**: Embedded image detection and filtering
- **File Output**: Standardized PNG export with naming conventions
- **CLI Interface**: User-friendly command-line tool

## Requirements

- Python 3.11+
- PyMuPDF for PDF processing
- Pillow for image handling
- Typer for CLI interface