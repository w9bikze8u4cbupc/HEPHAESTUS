# HEPHAESTUS – System Design

## 1. Overview

HEPHAESTUS is a modular pipeline for extracting board-game components from rulebook PDFs. It is designed to be:

- **Robust** – handles malformed PDFs and noisy layouts gracefully
- **Extensible** – supports future modules for AI classification, spatial text, and deduplication
- **Testable** – each module has a clear API and is unit-testable in isolation

The initial implementation focuses on **Phase 1**: PDF ingestion + embedded image extraction + flat image export via a CLI.

## 2. Architecture

### 2.1 High-Level Pipeline

```text
PDF file(s)
   │
   ▼
[PDF Ingestion]
   │
   ▼
[Image Extraction (embedded)]
   │
   ▼
[Filtering + ID Assignment]
   │
   ▼
[Image Export]
   │
   ▼
[Future: Classification → Metadata → Dedup → Manifest]
```

### 2.2 Modules

We organize the code under `src/hephaestus/`:

- `config.py` – global settings abstraction
- `logging.py` – centralized logger factory
- `pdf/ingestion.py` – PDF opening & page abstraction
- `pdf/images.py` – embedded image extraction & representation
- `cli.py` – Typer-based CLI front-end

**(Future)**
- `pdf/text.py` – spatial text extraction
- `classifier/` – heuristics + vision API
- `metadata/` – label/quantity annotator
- `dedup/` – perceptual dedup engine
- `output/manifest.py` – JSON manifest

## 3. Core Components (Phase 1)

### 3.1 Configuration

**File:** `config.py`

Use a simple dataclass for now:

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass
class Settings:
    output_dir: Path = Path("output")
    min_image_width: int = 50
    min_image_height: int = 50
```

Later we can extend this to read from env vars or a config file.

### 3.2 Logging

**File:** `logging.py`

Provide a helper:

```python
import logging

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
```

All modules use `get_logger(__name__)`.

### 3.3 PDF Ingestion

**File:** `pdf/ingestion.py`

**Responsibilities**
- Validate file existence
- Open with PyMuPDF
- Expose:
  - `PdfDocument` – wraps `fitz.Document`
  - `PdfPage` – wraps `fitz.Page` with convenience properties

**API sketch**

```python
from pathlib import Path
import fitz

class PdfOpenError(Exception): ...
class EncryptedPdfError(PdfOpenError): ...

class PdfPage:
    def __init__(self, doc: "PdfDocument", index: int, page: fitz.Page):
        self._doc = doc
        self._index = index
        self._page = page
    
    @property
    def index(self) -> int: ...
    @property
    def width(self) -> float: ...
    @property
    def height(self) -> float: ...
    def raw(self) -> fitz.Page: ...

class PdfDocument:
    def __init__(self, path: Path):
        # validate + open, raising PdfOpenError / EncryptedPdfError
        ...
    
    @property
    def path(self) -> Path: ...
    @property
    def page_count(self) -> int: ...
    def pages(self) -> list[PdfPage]: ...
```

**Error handling**
- `PdfOpenError` for generic open failures
- `EncryptedPdfError` if `doc.needs_pass` is true
- Caller (CLI) handles these and exits with appropriate messages

### 3.4 Image Extraction

**File:** `pdf/images.py`

**Data model**

```python
from dataclasses import dataclass
from typing import Literal
import fitz

ImageSourceType = Literal["embedded"]

@dataclass
class ExtractedImage:
    id: str
    page_index: int
    source_type: ImageSourceType
    width: int
    height: int
    pixmap: fitz.Pixmap
```

**Extraction function**

```python
from collections.abc import Sequence
from .ingestion import PdfDocument

def extract_embedded_images(
    pdf: PdfDocument,
    min_width: int,
    min_height: int,
) -> list[ExtractedImage]:
    ...
```

**Behavior**
- Iterate each `PdfPage`
- Call `page.raw().get_images(full=True)`
- For each image reference:
  - Load `fitz.Pixmap`
  - Filter on width/height thresholds
  - Create `ExtractedImage` with ID: `f"p{page_index}_img{local_idx}"`

**Logging at INFO:**
- Total images found
- Total retained

**Logging at DEBUG:**
- Per-image decisions (dimensions vs thresholds)

### 3.5 Image Export

**File:** `pdf/images.py` (or `output/images.py` later)

```python
from pathlib import Path
from typing import Sequence
from .images import ExtractedImage

def save_images_flat(
    images: Sequence[ExtractedImage],
    output_dir: Path,
    fmt: str = "png",
) -> list[Path]:
    ...
```

**Behavior**
- Ensure `output_dir` exists
- Convert each pixmap to the target format (PNG) using PyMuPDF or Pillow
- File name: `component_<id>.<fmt>`
- Return list of paths

### 3.6 CLI

**File:** `cli.py`

Use Typer:

```python
import typer
from pathlib import Path
from .config import Settings
from .logging import get_logger
from .pdf.ingestion import PdfDocument, PdfOpenError, EncryptedPdfError
from .pdf.images import extract_embedded_images, save_images_flat

app = typer.Typer(help="HEPHAESTUS – board-game component extractor")

@app.command()
def extract(
    pdf_path: Path = typer.Argument(..., exists=True, readable=True),
    out: Path = typer.Option(Path("output"), "--out", "-o"),
    min_width: int = typer.Option(50, help="Minimum image width in pixels"),
    min_height: int = typer.Option(50, help="Minimum image height in pixels"),
):
    logger = get_logger(__name__)
    try:
        logger.info(f"Opening PDF: {pdf_path}")
        doc = PdfDocument(pdf_path)
    except EncryptedPdfError as e:
        logger.error(f"Encrypted PDF: {e}")
        raise typer.Exit(code=2)
    except PdfOpenError as e:
        logger.error(f"Failed to open PDF: {e}")
        raise typer.Exit(code=1)
    
    logger.info("Extracting embedded images...")
    images = extract_embedded_images(doc, min_width=min_width, min_height=min_height)
    logger.info(f"Retained {len(images)} images after filtering")
    
    logger.info(f"Saving images to {out}")
    paths = save_images_flat(images, out)
    logger.info(f"Saved {len(paths)} images")

def main():
    app()

if __name__ == "__main__":
    main()
```

**Entry point in pyproject.toml:**

```toml
[project.scripts]
hephaestus = "hephaestus.cli:main"
```

## 4. Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

We derive testable properties from the requirements:

**Property 1: Deterministic IDs**
*For any* PDF and configuration, repeated runs should yield identical IDs and filenames
**Validates: Requirements FR-2.3**

**Property 2: Size Threshold Monotonicity**
*For any* set of images, increasing thresholds should never increase the number of retained images
**Validates: Requirements FR-2.2**

**Property 3: Non-crashing on Single-page Failure**
*For any* PDF where one page fails to load or parse images, the rest should still process
**Validates: Requirements FR-5.2**

**Property 4: Exit Code Semantics**
*For any* processing run, opening failure should result in non-zero exit; successful extraction should result in zero
**Validates: Requirements FR-5.2**

**Property 5: No Orphan Files**
*For any* extraction run, every exported file should correspond to exactly one ExtractedImage
**Validates: Requirements FR-3.1, FR-3.2**

**Property 6: Reversibility of Path Mapping**
*For any* filename, we should be able to recover image ID and infer page index
**Validates: Requirements FR-3.2**

**Property 7: No Silent Data Loss**
*For any* filtered or failed image, it should be either logged at INFO/DEBUG or represented as an error, not silently discarded
**Validates: Requirements FR-5.1**

**Property 8: Format Validity**
*For any* exported image, it should be a valid PNG that Pillow can open
**Validates: Requirements FR-3.1**

**Property 9: Page Ordering**
*For any* PDF, images extracted from pages should respect page order in iteration
**Validates: Requirements FR-1.2, FR-2.1**

**Property 10: Thread-safety of Pure Utilities**
*For any* pure helpers (ID generation, naming), they should be free of shared mutable state
**Validates: Requirements FR-6.1**

**Property 11: Config Invariants**
*For any* negative thresholds or non-existent output directories, they should be rejected with clear errors
**Validates: Requirements FR-4.2, FR-5.1**

## 5. Error Handling

### Exception Hierarchy

```python
class HephaestusError(Exception):
    """Base exception for all HEPHAESTUS errors"""

class PdfOpenError(HephaestusError):
    """PDF cannot be opened or is corrupted"""

class EncryptedPdfError(PdfOpenError):
    """PDF requires password authentication"""

class ImageExtractionError(HephaestusError):
    """Image extraction operation failed"""

class FileOutputError(HephaestusError):
    """File saving operation failed"""
```

### Error Handling Strategy

1. **PDF Level Errors**: Catch and wrap PyMuPDF exceptions with context
2. **Image Processing Errors**: Handle Pillow exceptions during format conversion
3. **File System Errors**: Manage directory creation and file writing failures
4. **Graceful Degradation**: Continue processing remaining images when individual extractions fail
5. **User Feedback**: Provide actionable error messages with suggested resolutions

## 6. Testing Strategy

### Unit tests (pytest):
- `test_pdf_ingestion.py` – opening, error handling, page metadata
- `test_image_extraction.py` – small vs large images, IDs, counts
- `test_cli.py` – happy path, bad path, encrypted PDFs

### Property-based tests (Hypothesis):
- ID and filename generation (no collisions, valid characters)
- Filtering function (monotonic w.r.t. thresholds)

### Fixtures:
- Programmatically generated PDFs with known embedded images
- Corrupted/edge-case PDFs (empty, single page, huge pages)

### Testing Requirements

- **Framework**: Hypothesis (Python property-based testing library)
- **Configuration**: Minimum 100 iterations per property test
- **Tagging**: Each property-based test tagged with format: `**Feature: pdf-component-extractor, Property {number}: {property_text}**`
- Each correctness property implemented by a single property-based test
- Property tests run minimum 100 iterations for statistical confidence
- Unit tests cover specific scenarios and integration points
- All tests use programmatically generated data for consistency
- Test suite validates both success and failure paths

## 7. Future Extensions (Non-implemented but planned)

- **Spatial Text Extractor** – PyMuPDF text blocks + bounding boxes, spatial indexing
- **Hybrid Component Classifier** – Heuristics + Vision API (OpenAI) with cost-aware batching
- **Metadata Annotator** – Associate labels/quantities from text to images
- **Perceptual Dedup Engine** – Image hashing (imagehash), configurable similarity thresholds
- **Structured Output Manager** – JSON manifest with full component descriptions
- **Web UI / API** – FastAPI service + simple React UI for visual review