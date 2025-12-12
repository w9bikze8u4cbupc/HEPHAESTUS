"""Tests for spatial text extraction."""

import tempfile
from pathlib import Path
import pytest
from hypothesis import given, strategies as st

import fitz  # type: ignore[import]

from hephaestus.pdf.ingestion import PdfDocument
from hephaestus.text.spatial import (
    extract_spatial_text, TextSpan, BBox, bbox_distance, 
    bbox_intersects, bbox_expand
)


def create_pdf_with_text(text_content: str) -> bytes:
    """Create a PDF with specified text content."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 50), text_content)
    
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


class TestBBox:
    def test_bbox_properties(self):
        """Test BBox property calculations."""
        bbox = BBox(10, 20, 110, 120)
        
        assert bbox.width() == 100
        assert bbox.height() == 100
        assert bbox.area() == 10000
        assert bbox.center() == (60, 70)

    def test_bbox_distance(self):
        """Test distance calculation between bounding boxes."""
        bbox1 = BBox(0, 0, 10, 10)
        bbox2 = BBox(30, 40, 40, 50)
        
        # Distance between centers: (5,5) to (35,45) = sqrt(30^2 + 40^2) = 50
        distance = bbox_distance(bbox1, bbox2)
        assert abs(distance - 50.0) < 0.1

    def test_bbox_intersects(self):
        """Test bounding box intersection detection."""
        bbox1 = BBox(0, 0, 10, 10)
        bbox2 = BBox(5, 5, 15, 15)  # Overlapping
        bbox3 = BBox(20, 20, 30, 30)  # Non-overlapping
        
        assert bbox_intersects(bbox1, bbox2) is True
        assert bbox_intersects(bbox1, bbox3) is False

    def test_bbox_expand(self):
        """Test bounding box expansion."""
        bbox = BBox(10, 10, 20, 20)
        expanded = bbox_expand(bbox, 5)
        
        assert expanded.x0 == 5
        assert expanded.y0 == 5
        assert expanded.x1 == 25
        assert expanded.y1 == 25


class TestSpatialTextExtraction:
    def test_extract_text_from_simple_pdf(self):
        """Test text extraction from a simple PDF."""
        test_text = "Hello World Test"
        pdf_bytes = create_pdf_with_text(test_text)
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp.flush()
            
            doc = PdfDocument(Path(tmp.name))
            spans = extract_spatial_text(doc)
            
            # Should extract at least one span
            assert len(spans) > 0
            
            # Should find our test text in at least one span
            found_text = any(test_text in span.text for span in spans)
            assert found_text is True
            
            # All spans should have valid properties
            for span in spans:
                assert span.page_index == 0
                assert len(span.text.strip()) > 0
                assert span.bbox.width() > 0
                assert span.bbox.height() > 0
                assert span.source in ["block", "line", "span"]
        
        Path(tmp.name).unlink()

    def test_extract_text_from_multi_page_pdf(self):
        """Test text extraction from multi-page PDF."""
        doc = fitz.open()
        
        # Create multiple pages with different text
        page_texts = ["Page 1 content", "Page 2 content", "Page 3 content"]
        for i, text in enumerate(page_texts):
            page = doc.new_page()
            page.insert_text((50, 50), text)
        
        pdf_bytes = doc.tobytes()
        doc.close()
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp.flush()
            
            pdf_doc = PdfDocument(Path(tmp.name))
            spans = extract_spatial_text(pdf_doc)
            
            # Should have spans from all pages
            page_indices = {span.page_index for span in spans}
            assert len(page_indices) == 3
            assert page_indices == {0, 1, 2}
            
            # Should find text from each page
            for i, expected_text in enumerate(page_texts):
                page_spans = [s for s in spans if s.page_index == i]
                found = any(expected_text in span.text for span in page_spans)
                assert found is True
        
        Path(tmp.name).unlink()

    def test_empty_pdf_handling(self):
        """Test handling of PDF with no text."""
        doc = fitz.open()
        page = doc.new_page()  # Empty page
        
        pdf_bytes = doc.tobytes()
        doc.close()
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp.flush()
            
            pdf_doc = PdfDocument(Path(tmp.name))
            spans = extract_spatial_text(pdf_doc)
            
            # Should handle gracefully (may return empty list or fallback)
            assert isinstance(spans, list)
        
        Path(tmp.name).unlink()


class TestSpatialTextProperties:
    """Property-based tests for spatial text extraction."""

    @given(st.text(min_size=1, max_size=100))
    def test_extraction_determinism(self, text_content):
        """For any text content, extraction should be deterministic."""
        # Filter out problematic characters that might cause PDF issues
        clean_text = ''.join(c for c in text_content if c.isprintable() and ord(c) < 128)
        if not clean_text.strip():
            clean_text = "test"
        
        pdf_bytes = create_pdf_with_text(clean_text)
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp.flush()
            
            doc = PdfDocument(Path(tmp.name))
            
            # Extract twice
            spans1 = extract_spatial_text(doc)
            spans2 = extract_spatial_text(doc)
            
            # Results should be identical
            assert len(spans1) == len(spans2)
            
            for s1, s2 in zip(spans1, spans2):
                assert s1.text == s2.text
                assert s1.page_index == s2.page_index
                assert s1.bbox.x0 == s2.bbox.x0
                assert s1.bbox.y0 == s2.bbox.y0
                assert s1.source == s2.source
        
        Path(tmp.name).unlink()

    @given(
        x0=st.floats(min_value=0, max_value=500),
        y0=st.floats(min_value=0, max_value=500),
        width=st.floats(min_value=10, max_value=100),
        height=st.floats(min_value=10, max_value=100)
    )
    def test_bbox_properties_consistency(self, x0, y0, width, height):
        """For any valid bounding box, properties should be consistent."""
        x1 = x0 + width
        y1 = y0 + height
        
        bbox = BBox(x0, y0, x1, y1)
        
        assert abs(bbox.width() - width) < 0.001
        assert abs(bbox.height() - height) < 0.001
        assert abs(bbox.area() - (width * height)) < 0.001
        
        center_x, center_y = bbox.center()
        assert abs(center_x - (x0 + width/2)) < 0.001
        assert abs(center_y - (y0 + height/2)) < 0.001

    @given(
        padding=st.floats(min_value=0, max_value=50)
    )
    def test_bbox_expansion_properties(self, padding):
        """For any padding value, bbox expansion should be correct."""
        original = BBox(10, 10, 20, 20)
        expanded = bbox_expand(original, padding)
        
        # Expanded bbox should be larger by 2*padding in each dimension
        assert abs(expanded.width() - (original.width() + 2*padding)) < 0.001
        assert abs(expanded.height() - (original.height() + 2*padding)) < 0.001
        
        # Center should remain the same
        orig_center = original.center()
        exp_center = expanded.center()
        assert abs(orig_center[0] - exp_center[0]) < 0.001
        assert abs(orig_center[1] - exp_center[1]) < 0.001


class TestTextSpanStructure:
    def test_text_span_immutability(self):
        """Test that TextSpan is properly immutable."""
        bbox = BBox(0, 0, 10, 10)
        span = TextSpan(
            page_index=0,
            text="test",
            bbox=bbox,
            source="span"
        )
        
        # Should not be able to modify fields
        with pytest.raises(AttributeError):
            span.text = "modified"  # type: ignore
        
        with pytest.raises(AttributeError):
            span.page_index = 1  # type: ignore

    def test_text_span_properties(self):
        """Test TextSpan property access."""
        bbox = BBox(10, 20, 30, 40)
        span = TextSpan(
            page_index=2,
            text="Sample text",
            bbox=bbox,
            source="line"
        )
        
        assert span.page_index == 2
        assert span.text == "Sample text"
        assert span.bbox == bbox
        assert span.source == "line"