"""Tests for PDF ingestion module."""

import pytest
from pathlib import Path

from hephaestus.pdf.ingestion import PdfDocument, PdfOpenError, EncryptedPdfError


def test_pdf_open_error_on_nonexistent_file():
    """Test that opening a non-existent PDF raises PdfOpenError."""
    nonexistent_path = Path("nonexistent.pdf")
    with pytest.raises(PdfOpenError, match="PDF file does not exist"):
        PdfDocument(nonexistent_path)


def test_pdf_document_imports():
    """Test that PDF ingestion classes can be imported."""
    assert PdfDocument is not None
    assert PdfOpenError is not None
    assert EncryptedPdfError is not None