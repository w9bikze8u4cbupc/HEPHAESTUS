import tempfile
from pathlib import Path
import pytest
from hypothesis import given, strategies as st, assume
from PIL import Image
import io

import fitz  # type: ignore[import]

from hephaestus.pdf.ingestion import PdfDocument
from hephaestus.pdf.images import extract_embedded_images, save_images_flat, ExtractedImage
from tests.helpers.pdf_factory import make_pdf_with_images_and_text, make_pdf_with_images


def create_pdf_with_images(image_sizes: list[tuple[int, int]]) -> bytes:
    """Create a PDF with embedded images of specified sizes."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    
    y_offset = 50
    for width, height in image_sizes:
        # Create a simple colored image
        img = Image.new('RGB', (width, height), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        # Insert image into PDF
        img_rect = fitz.Rect(50, y_offset, 50 + width, y_offset + height)
        page.insert_image(img_rect, stream=img_bytes.getvalue())
        y_offset += height + 10
    
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


class TestImageExtraction:
    def test_extract_images_from_pdf(self):
        """Test basic image extraction functionality."""
        # Create PDF with known images
        image_sizes = [(100, 100), (200, 150), (50, 50)]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = make_pdf_with_images_and_text(Path(temp_dir), image_sizes)
            
            with PdfDocument(pdf_path) as doc:
                images = extract_embedded_images(doc, min_width=40, min_height=40)
                
                # Should extract all images since they're all >= 40x40
                assert len(images) == 3
                
                # Check image properties
                for i, image in enumerate(images):
                    assert image.page_index == 0
                    assert image.source_type == "embedded"
                    assert image.id == f"p0_img{i}"
                    assert image.width > 0
                    assert image.height > 0

    def test_size_filtering(self):
        """Test that size filtering works correctly."""
        # Create PDF with mixed size images
        image_sizes = [(100, 100), (30, 30), (200, 150), (25, 40)]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = make_pdf_with_images_and_text(Path(temp_dir), image_sizes)
            
            with PdfDocument(pdf_path) as doc:
                # Filter with 50x50 minimum
                images = extract_embedded_images(doc, min_width=50, min_height=50)
                
                # Should only get the 100x100 and 200x150 images
                assert len(images) == 2
                
                for image in images:
                    assert image.width >= 50
                    assert image.height >= 50


class TestImageSaving:
    def test_save_images_creates_files(self, tmp_path):
        """Test that save_images_flat creates the expected files."""
        # Create a simple test image using centralized helper
        images_spec = [(100, 100, 'red')]
        pdf_path = make_pdf_with_images(tmp_path, images_spec)
        
        with PdfDocument(pdf_path) as doc:
            images = extract_embedded_images(doc, min_width=50, min_height=50)
            
            output_path = tmp_path / "output"
            output_path.mkdir()
            saved_paths = save_images_flat(images, output_path)
            
            assert len(saved_paths) == len(images)
            
            for path in saved_paths:
                assert path.exists()
                assert path.suffix == ".png"
                assert path.name.startswith("component_")
                
                # Verify the image can be opened
                with Image.open(path) as img:
                    assert img.width > 0
                    assert img.height > 0


class TestSizeThresholdFiltering:
    """
    **Feature: pdf-component-extractor, Property 2: Size Threshold Monotonicity**
    **Validates: Requirements FR-2.2**
    """

    @given(
        base_threshold=st.integers(min_value=10, max_value=100),
        threshold_increase=st.integers(min_value=1, max_value=50)
    )
    def test_increasing_thresholds_never_increases_retained_images(self, base_threshold, threshold_increase):
        """For any set of images, increasing thresholds should never increase retained count."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create PDF with various sized images using centralized helper
            images_spec = [(50, 50, 'red'), (100, 100, 'blue'), (150, 150, 'green'), (200, 200, 'yellow')]
            pdf_path = make_pdf_with_images(Path(temp_dir), images_spec)
            
            with PdfDocument(pdf_path) as doc:
                # Extract with base threshold
                images_base = extract_embedded_images(doc, min_width=base_threshold, min_height=base_threshold)
                
                # Extract with higher threshold
                higher_threshold = base_threshold + threshold_increase
                images_higher = extract_embedded_images(doc, min_width=higher_threshold, min_height=higher_threshold)
                
                # Higher threshold should never result in more images
                assert len(images_higher) <= len(images_base)

    @given(
        width_threshold=st.integers(min_value=1, max_value=300),
        height_threshold=st.integers(min_value=1, max_value=300)
    )
    def test_threshold_filtering_is_accurate(self, width_threshold, height_threshold):
        """For any thresholds, all retained images should meet the criteria."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create images with known sizes using centralized helper
            images_spec = [(50, 50, 'red'), (100, 200, 'blue'), (300, 100, 'green'), (400, 400, 'yellow')]
            pdf_path = make_pdf_with_images(Path(temp_dir), images_spec)
            
            with PdfDocument(pdf_path) as doc:
                images = extract_embedded_images(doc, min_width=width_threshold, min_height=height_threshold)
                
                # All retained images should meet the threshold criteria
                for image in images:
                    assert image.width >= width_threshold
                    assert image.height >= height_threshold


class TestIDGenerationStability:
    """
    **Feature: pdf-component-extractor, Property 1: Deterministic IDs**
    **Validates: Requirements FR-2.3**
    """

    @given(
        page_count=st.integers(min_value=1, max_value=5),
        images_per_page=st.integers(min_value=1, max_value=3)
    )
    def test_id_generation_is_deterministic(self, page_count, images_per_page):
        """For any PDF, repeated extractions should yield identical IDs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create multi-page PDF with images using centralized helper
            pdf_path = Path(temp_dir) / "multipage.pdf"
            
            doc = fitz.open()
            try:
                for page_idx in range(page_count):
                    page = doc.new_page(width=595, height=842)
                    
                    for img_idx in range(images_per_page):
                        # Create and insert image
                        img = Image.new('RGB', (100, 100), color='blue')
                        img_bytes = io.BytesIO()
                        img.save(img_bytes, format='PNG')
                        img_bytes.seek(0)
                        
                        y_pos = 50 + (img_idx * 110)
                        img_rect = fitz.Rect(50, y_pos, 150, y_pos + 100)
                        page.insert_image(img_rect, stream=img_bytes.getvalue())
                
                pdf_bytes = doc.tobytes()
                pdf_path.write_bytes(pdf_bytes)
            finally:
                doc.close()
            
            with PdfDocument(pdf_path) as pdf_doc:
                # Extract images multiple times
                images1 = extract_embedded_images(pdf_doc, min_width=50, min_height=50)
                images2 = extract_embedded_images(pdf_doc, min_width=50, min_height=50)
                
                # Should get same number of images
                assert len(images1) == len(images2)
                
                # IDs should be identical
                ids1 = [img.id for img in images1]
                ids2 = [img.id for img in images2]
                assert ids1 == ids2
                
                # IDs should follow expected format
                for page_idx in range(page_count):
                    for img_idx in range(images_per_page):
                        expected_id = f"p{page_idx}_img{img_idx}"
                        assert expected_id in ids1

    @given(st.integers(min_value=0, max_value=10))
    def test_id_format_consistency(self, page_index):
        """For any page index, ID format should be consistent."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create simple PDF using centralized helper
            images_spec = [(100, 100, 'red'), (150, 150, 'blue')]
            pdf_path = make_pdf_with_images(Path(temp_dir), images_spec)
            
            with PdfDocument(pdf_path) as doc:
                images = extract_embedded_images(doc, min_width=50, min_height=50)
                
                for local_idx, image in enumerate(images):
                    # ID should follow p{page}_img{local_idx} format
                    expected_id = f"p{image.page_index}_img{local_idx}"
                    assert image.id == expected_id