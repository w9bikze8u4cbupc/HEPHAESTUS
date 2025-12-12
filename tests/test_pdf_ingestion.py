import io
from pathlib import Path
import tempfile
import pytest
from hypothesis import given, strategies as st

import fitz  # type: ignore[import]

from hephaestus.pdf.ingestion import PdfDocument, PdfPage, PdfOpenError, EncryptedPdfError
from tests.helpers.pdf_factory import make_multi_page_pdf, make_encrypted_pdf


def create_test_pdf(page_count: int = 1) -> bytes:
    """Create a simple test PDF with the specified number of pages."""
    doc = fitz.open()  # Create empty document
    for i in range(page_count):
        page = doc.new_page(width=595, height=842)  # A4 size
        page.insert_text((50, 50), f"Test page {i + 1}")
    
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_encrypted_pdf() -> bytes:
    """Create an encrypted test PDF."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Encrypted content")
    
    # Encrypt with password
    pdf_bytes = doc.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="test", owner_pw="test")
    doc.close()
    return pdf_bytes


class TestPdfPage:
    def test_page_properties(self, tmp_path):
        """Test that PdfPage exposes correct properties."""
        pdf_path = make_multi_page_pdf(tmp_path, 1, ["Test page 1"])
        
        with PdfDocument(pdf_path) as doc:
            pages = list(doc.pages())
            
            assert len(pages) == 1
            page = pages[0]
            
            assert page.index == 0
            assert page.width > 0
            assert page.height > 0
            assert isinstance(page.as_pymupdf_page(), fitz.Page)


class TestPdfDocument:
    def test_valid_pdf_opens_successfully(self, tmp_path):
        """Test that valid PDFs open and provide correct metadata."""
        pdf_path = make_multi_page_pdf(tmp_path, 3, ["Page 1", "Page 2", "Page 3"])
        
        with PdfDocument(pdf_path) as doc:
            assert doc.page_count == 3
            assert doc.path == pdf_path
            
            pages = list(doc.pages())
            assert len(pages) == 3
            
            for i, page in enumerate(pages):
                assert page.index == i

    def test_nonexistent_file_raises_error(self):
        """Test that non-existent files raise PdfOpenError."""
        nonexistent_path = Path("nonexistent_file.pdf")
        
        with pytest.raises(PdfOpenError, match="PDF file does not exist"):
            PdfDocument(nonexistent_path)

    def test_encrypted_pdf_raises_error(self, tmp_path):
        """Test that encrypted PDFs raise EncryptedPdfError."""
        pdf_path = make_encrypted_pdf(tmp_path)
        
        with pytest.raises(EncryptedPdfError, match="PDF is encrypted"):
            PdfDocument(pdf_path)

    def test_corrupted_pdf_raises_error(self, tmp_path):
        """Test that corrupted PDFs raise PdfOpenError."""
        corrupted_data = b"This is not a valid PDF file"
        corrupted_path = tmp_path / "corrupted.pdf"
        corrupted_path.write_bytes(corrupted_data)
        
        with pytest.raises(PdfOpenError, match="Failed to open PDF"):
            PdfDocument(corrupted_path)

    def test_file_handle_lifecycle_smoke_test(self, tmp_path):
        """Smoke test: Opening and closing a PDF 100 times should not leak file handles."""
        pdf_path = make_multi_page_pdf(tmp_path, 1, ["Test content"])
        
        # Open and close PDF 100 times - should not leak handles
        for i in range(100):
            with PdfDocument(pdf_path) as doc:
                pages = list(doc.pages())
                assert len(pages) == 1
        
        # If we get here without errors, file handles are properly managed


class TestPdfProcessingProperties:
    """
    **Feature: pdf-component-extractor, Property 1: Deterministic IDs**
    **Validates: Requirements FR-2.3**
    """

    @given(page_count=st.integers(min_value=1, max_value=10))
    def test_page_iteration_is_deterministic(self, page_count):
        """For any valid PDF, page iteration should be deterministic and complete."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = make_multi_page_pdf(Path(temp_dir), page_count)
            
            with PdfDocument(pdf_path) as doc:
                # Multiple iterations should yield identical results
                pages1 = list(doc.pages())
                pages2 = list(doc.pages())
                
                assert len(pages1) == page_count
                assert len(pages2) == page_count
                
                for p1, p2 in zip(pages1, pages2):
                    assert p1.index == p2.index
                    assert p1.width == p2.width
                    assert p1.height == p2.height

    @given(page_count=st.integers(min_value=1, max_value=10))
    def test_page_dimensions_are_consistent(self, page_count):
        """For any PDF, page dimensions should match PyMuPDF values within tolerance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = make_multi_page_pdf(Path(temp_dir), page_count)
            
            with PdfDocument(pdf_path) as doc:
                for page in doc.pages():
                    raw_page = page.as_pymupdf_page()
                    
                    # Dimensions should match within 1 pixel tolerance
                    assert abs(page.width - raw_page.rect.width) <= 1
                    assert abs(page.height - raw_page.rect.height) <= 1