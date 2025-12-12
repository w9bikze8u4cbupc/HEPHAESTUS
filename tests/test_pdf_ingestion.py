import io
from pathlib import Path
import tempfile
import pytest
from hypothesis import given, strategies as st

import fitz  # type: ignore[import]

from hephaestus.pdf.ingestion import PdfDocument, PdfPage, PdfOpenError, EncryptedPdfError


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
    def test_page_properties(self):
        """Test that PdfPage exposes correct properties."""
        pdf_bytes = create_test_pdf(1)
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp.flush()
            
            doc = PdfDocument(Path(tmp.name))
            pages = list(doc.pages())
            
            assert len(pages) == 1
            page = pages[0]
            
            assert page.index == 0
            assert page.width > 0
            assert page.height > 0
            assert isinstance(page.as_pymupdf_page(), fitz.Page)
        
        Path(tmp.name).unlink()


class TestPdfDocument:
    def test_valid_pdf_opens_successfully(self):
        """Test that valid PDFs open and provide correct metadata."""
        pdf_bytes = create_test_pdf(3)
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp.flush()
            
            doc = PdfDocument(Path(tmp.name))
            
            assert doc.page_count == 3
            assert doc.path == Path(tmp.name)
            
            pages = list(doc.pages())
            assert len(pages) == 3
            
            for i, page in enumerate(pages):
                assert page.index == i
        
        Path(tmp.name).unlink()

    def test_nonexistent_file_raises_error(self):
        """Test that non-existent files raise PdfOpenError."""
        nonexistent_path = Path("nonexistent_file.pdf")
        
        with pytest.raises(PdfOpenError, match="PDF file does not exist"):
            PdfDocument(nonexistent_path)

    def test_encrypted_pdf_raises_error(self):
        """Test that encrypted PDFs raise EncryptedPdfError."""
        pdf_bytes = create_encrypted_pdf()
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp.flush()
            
            with pytest.raises(EncryptedPdfError, match="PDF is encrypted"):
                PdfDocument(Path(tmp.name))
        
        Path(tmp.name).unlink()

    def test_corrupted_pdf_raises_error(self):
        """Test that corrupted PDFs raise PdfOpenError."""
        corrupted_data = b"This is not a valid PDF file"
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(corrupted_data)
            tmp.flush()
            
            with pytest.raises(PdfOpenError, match="Failed to open PDF"):
                PdfDocument(Path(tmp.name))
        
        Path(tmp.name).unlink()


class TestPdfProcessingProperties:
    """
    **Feature: pdf-component-extractor, Property 1: Deterministic IDs**
    **Validates: Requirements FR-2.3**
    """

    @given(page_count=st.integers(min_value=1, max_value=10))
    def test_page_iteration_is_deterministic(self, page_count):
        """For any valid PDF, page iteration should be deterministic and complete."""
        pdf_bytes = create_test_pdf(page_count)
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp.flush()
            
            doc = PdfDocument(Path(tmp.name))
            
            # Multiple iterations should yield identical results
            pages1 = list(doc.pages())
            pages2 = list(doc.pages())
            
            assert len(pages1) == page_count
            assert len(pages2) == page_count
            
            for p1, p2 in zip(pages1, pages2):
                assert p1.index == p2.index
                assert p1.width == p2.width
                assert p1.height == p2.height
        
        Path(tmp.name).unlink()

    @given(page_count=st.integers(min_value=1, max_value=10))
    def test_page_dimensions_are_consistent(self, page_count):
        """For any PDF, page dimensions should match PyMuPDF values within tolerance."""
        pdf_bytes = create_test_pdf(page_count)
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp.flush()
            
            doc = PdfDocument(Path(tmp.name))
            
            for page in doc.pages():
                raw_page = page.as_pymupdf_page()
                
                # Dimensions should match within 1 pixel tolerance
                assert abs(page.width - raw_page.rect.width) <= 1
                assert abs(page.height - raw_page.rect.height) <= 1
        
        Path(tmp.name).unlink()