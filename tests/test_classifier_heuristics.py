"""Tests for heuristic-based classification."""

import tempfile
from pathlib import Path
import pytest
from hypothesis import given, strategies as st, settings
from PIL import Image
import io

import fitz  # type: ignore[import]

from hephaestus.pdf.ingestion import PdfDocument
from hephaestus.pdf.images import extract_embedded_images, ExtractedImage
from hephaestus.classifier.heuristics import classify_heuristic, calculate_confidence_score


def create_test_image_pixmap(width: int, height: int, color: str = 'red') -> fitz.Pixmap:
    """Create a test pixmap with specified dimensions."""
    # Handle zero dimensions by clamping to minimum of 1
    width = max(1, width)
    height = max(1, height)
    
    # Create PIL image
    pil_img = Image.new('RGB', (width, height), color=color)
    img_bytes = io.BytesIO()
    pil_img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    # Convert to fitz pixmap
    doc = fitz.open()
    page = doc.new_page(width=width+100, height=height+100)
    img_rect = fitz.Rect(10, 10, 10 + width, 10 + height)
    page.insert_image(img_rect, stream=img_bytes.getvalue())
    
    # Extract the pixmap
    img_list = page.get_images(full=True)
    if img_list:
        xref = img_list[0][0]
        pixmap = fitz.Pixmap(doc, xref)
        doc.close()
        return pixmap
    
    doc.close()
    raise ValueError("Failed to create test pixmap")


def create_test_extracted_image(width: int, height: int, page_index: int = 0, img_index: int = 0) -> ExtractedImage:
    """Create a test ExtractedImage with specified dimensions."""
    pixmap = create_test_image_pixmap(width, height)
    
    return ExtractedImage(
        id=f"p{page_index}_img{img_index}",
        page_index=page_index,
        source_type="embedded",
        width=width,
        height=height,
        pixmap=pixmap
    )


class TestHeuristicClassification:
    def test_small_image_classified_as_icon(self):
        """Test that very small images are classified as icons."""
        image = create_test_extracted_image(20, 20)
        signals = classify_heuristic(image)
        
        assert signals["likely_icon"] is True
        assert signals["confidence"] > 0.5

    def test_large_image_classified_as_board(self):
        """Test that large images are classified as boards."""
        image = create_test_extracted_image(500, 400)
        signals = classify_heuristic(image)
        
        assert signals["likely_board"] is True
        assert signals["confidence"] > 0.5

    def test_square_image_classified_as_token(self):
        """Test that square-ish images are classified as tokens."""
        image = create_test_extracted_image(100, 120)  # Aspect ratio ~0.83
        signals = classify_heuristic(image)
        
        # Should trigger token classification
        assert signals["likely_token"] is True or signals["likely_card"] is True

    def test_extreme_aspect_ratio_classified_as_noise(self):
        """Test that images with extreme aspect ratios are classified as noise."""
        # Very wide image
        image = create_test_extracted_image(400, 50)  # Aspect ratio = 8.0
        signals = classify_heuristic(image)
        
        assert signals["noise"] is True
        assert signals["confidence"] > 0.5

    def test_confidence_calculation(self):
        """Test confidence score calculation."""
        # Test with noise signal
        signals_noise = {"noise": True, "confidence": 0.5}
        confidence = calculate_confidence_score(signals_noise)
        assert confidence >= 0.7  # Should boost confidence for noise

        # Test with multiple positive signals
        signals_positive = {
            "likely_token": True,
            "likely_card": False,
            "rich_colors": True,
            "confidence": 0.4
        }
        confidence = calculate_confidence_score(signals_positive)
        assert confidence >= 0.5  # Should boost for multiple signals


class TestHeuristicProperties:
    """Property-based tests for heuristic classification."""

    @given(
        width=st.integers(min_value=10, max_value=1000),
        height=st.integers(min_value=10, max_value=1000)
    )
    def test_classification_is_deterministic(self, width, height):
        """For any image dimensions, classification should be deterministic."""
        image = create_test_extracted_image(width, height)
        
        # Run classification multiple times
        signals1 = classify_heuristic(image)
        signals2 = classify_heuristic(image)
        
        # Results should be identical
        assert signals1 == signals2

    @given(
        width=st.integers(min_value=1, max_value=50),
        height=st.integers(min_value=1, max_value=50)
    )
    def test_small_images_have_high_confidence(self, width, height):
        """For any small image, confidence should be reasonably high."""
        image = create_test_extracted_image(width, height)
        signals = classify_heuristic(image)
        
        # Small images should have confident classification
        assert signals["confidence"] > 0.3

    @given(
        width=st.integers(min_value=1, max_value=1000),
        height=st.integers(min_value=1, max_value=1000)
    )
    def test_signals_structure_is_consistent(self, width, height):
        """For any image, signals should have consistent structure."""
        image = create_test_extracted_image(width, height)
        signals = classify_heuristic(image)
        
        # Required keys should always be present
        required_keys = {
            "likely_token", "likely_card", "likely_board", 
            "likely_icon", "noise", "confidence"
        }
        
        for key in required_keys:
            assert key in signals
            
        # Confidence should be valid range
        assert 0.0 <= signals["confidence"] <= 1.0
        
        # Boolean signals should be boolean
        for key in ["likely_token", "likely_card", "likely_board", "likely_icon", "noise"]:
            assert isinstance(signals[key], bool)

    @given(st.integers(min_value=1, max_value=100))
    @settings(deadline=500)  # Increase deadline for image processing
    def test_extreme_aspect_ratios_detected(self, dimension):
        """For any extreme aspect ratio, noise should be detected."""
        # Test very wide image
        wide_image = create_test_extracted_image(dimension * 10, dimension)
        wide_signals = classify_heuristic(wide_image)
        
        # Test very tall image  
        tall_image = create_test_extracted_image(dimension, dimension * 10)
        tall_signals = classify_heuristic(tall_image)
        
        # At least one should be flagged as noise for extreme ratios
        if dimension * 10 / dimension > 3.0:  # Extreme ratio
            assert wide_signals["noise"] is True or tall_signals["noise"] is True


class TestHeuristicEdgeCases:
    def test_zero_dimension_handling(self):
        """Test handling of very small dimensions."""
        # Test with minimum dimensions (1x1) since 0 dimensions are invalid
        image = create_test_extracted_image(1, 1)
        signals = classify_heuristic(image)
        # Should handle gracefully, likely classify as noise with low confidence
        assert "confidence" in signals
        assert isinstance(signals["confidence"], (int, float))

    def test_classification_with_corrupted_pixmap(self):
        """Test classification behavior with problematic pixmap data."""
        # Create a minimal ExtractedImage with potentially problematic pixmap
        image = ExtractedImage(
            id="test_corrupted",
            page_index=0,
            source_type="embedded",
            width=100,
            height=100,
            pixmap=None  # This will cause issues
        )
        
        # Should handle gracefully and not crash
        signals = classify_heuristic(image)
        
        # Should classify as noise due to processing failure
        assert signals["noise"] is True
        assert signals["confidence"] > 0.5