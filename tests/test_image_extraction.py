"""Tests for image extraction module."""

from hephaestus.pdf.images import ExtractedImage, extract_embedded_images, save_images_flat


def test_image_extraction_imports():
    """Test that image extraction functions can be imported."""
    assert ExtractedImage is not None
    assert extract_embedded_images is not None
    assert save_images_flat is not None