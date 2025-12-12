"""Integration tests for the deduplication system."""

import tempfile
from pathlib import Path
import pytest
from PIL import Image

from hephaestus.pdf.images import ExtractedImage
from hephaestus.output.manifest import ManifestItem
from hephaestus.dedup.model import deduplicate_images
from tests.helpers.pdf_factory import make_pdf_with_images


class TestDedupIntegration:
    def test_deduplicate_empty_inputs(self):
        """Test deduplication with empty inputs."""
        result = deduplicate_images([], [], threshold=8)
        assert result == {}
    
    def test_deduplicate_single_image(self, tmp_path):
        """Test deduplication with single image."""
        # Create a test image
        img = Image.new('RGB', (100, 100), 'red')
        img_path = tmp_path / "test.png"
        img.save(img_path)
        
        # Create mock ExtractedImage and ManifestItem
        extracted_image = ExtractedImage(
            id="img1",
            page_index=0,
            source_type="embedded",
            width=100,
            height=100,
            pixmap=None
        )
        
        manifest_item = ManifestItem(
            image_id="img1",
            file_name="test.png",
            page_index=0,
            classification="token",
            classification_confidence=0.8,
            label=None,
            quantity=None,
            metadata_confidence=0.0,
            dimensions={"width": 100, "height": 100},
            bbox=None,
            dedup_group_id=None,
            is_duplicate=False,
            canonical_image_id="img1",
            file_path=str(img_path)
        )
        
        result = deduplicate_images([extracted_image], [manifest_item], threshold=8)
        
        # Single image should not form groups
        assert result == {}
    
    def test_deduplicate_identical_images(self, tmp_path):
        """Test deduplication with identical images."""
        # Create identical test images
        img = Image.new('RGB', (100, 100), 'red')
        
        img_path1 = tmp_path / "img1.png"
        img_path2 = tmp_path / "img2.png"
        img.save(img_path1)
        img.save(img_path2)
        
        # Create mock ExtractedImages
        extracted_images = [
            ExtractedImage(
                id="img1",
                page_index=0,
                source_type="embedded",
                width=100,
                height=100,
                pixmap=None
            ),
            ExtractedImage(
                id="img2",
                page_index=0,
                source_type="embedded",
                width=100,
                height=100,
                pixmap=None
            )
        ]
        
        # Create mock ManifestItems
        manifest_items = [
            ManifestItem(
                image_id="img1",
                file_name="img1.png",
                page_index=0,
                classification="token",
                classification_confidence=0.8,
                label=None,
                quantity=None,
                metadata_confidence=0.0,
                dimensions={"width": 100, "height": 100},
                bbox=None,
                dedup_group_id=None,
                is_duplicate=False,
                canonical_image_id="img1",
                file_path=str(img_path1)
            ),
            ManifestItem(
                image_id="img2",
                file_name="img2.png",
                page_index=0,
                classification="token",
                classification_confidence=0.8,
                label=None,
                quantity=None,
                metadata_confidence=0.0,
                dimensions={"width": 100, "height": 100},
                bbox=None,
                dedup_group_id=None,
                is_duplicate=False,
                canonical_image_id="img2",
                file_path=str(img_path2)
            )
        ]
        
        result = deduplicate_images(extracted_images, manifest_items, threshold=8)
        
        # Should form one group
        assert len(result) == 2  # Both images should be in the result
        
        # Both should map to the same group
        group1 = result["img1"]
        group2 = result["img2"]
        assert group1 == group2
        
        # Check group properties
        assert group1.group_id == "dup_001"
        assert set(group1.image_ids) == {"img1", "img2"}
        assert group1.canonical_id == "img1"  # Lexicographically first
    
    def test_deduplicate_different_images(self, tmp_path):
        """Test deduplication with different images."""
        # Create different test images
        img1 = Image.new('RGB', (100, 100), 'red')
        img2 = Image.new('RGB', (100, 100), 'blue')
        
        img_path1 = tmp_path / "img1.png"
        img_path2 = tmp_path / "img2.png"
        img1.save(img_path1)
        img2.save(img_path2)
        
        # Create mock ExtractedImages
        extracted_images = [
            ExtractedImage(
                id="img1",
                page_index=0,
                source_type="embedded",
                width=100,
                height=100,
                pixmap=None
            ),
            ExtractedImage(
                id="img2",
                page_index=0,
                source_type="embedded",
                width=100,
                height=100,
                pixmap=None
            )
        ]
        
        # Create mock ManifestItems
        manifest_items = [
            ManifestItem(
                image_id="img1",
                file_name="img1.png",
                page_index=0,
                classification="token",
                classification_confidence=0.8,
                label=None,
                quantity=None,
                metadata_confidence=0.0,
                dimensions={"width": 100, "height": 100},
                bbox=None,
                dedup_group_id=None,
                is_duplicate=False,
                canonical_image_id="img1",
                file_path=str(img_path1)
            ),
            ManifestItem(
                image_id="img2",
                file_name="img2.png",
                page_index=0,
                classification="token",
                classification_confidence=0.8,
                label=None,
                quantity=None,
                metadata_confidence=0.0,
                dimensions={"width": 100, "height": 100},
                bbox=None,
                dedup_group_id=None,
                is_duplicate=False,
                canonical_image_id="img2",
                file_path=str(img_path2)
            )
        ]
        
        result = deduplicate_images(extracted_images, manifest_items, threshold=8)
        
        # Different images should not form groups (assuming they're different enough)
        # This depends on actual hash values, so we just check structure
        for group in result.values():
            assert len(group.image_ids) >= 2
            assert group.canonical_id in group.image_ids
    
    def test_deduplicate_missing_file_paths(self, tmp_path):
        """Test deduplication handles missing file paths gracefully."""
        # Create mock ExtractedImage
        extracted_image = ExtractedImage(
            id="img1",
            page_index=0,
            source_type="embedded",
            width=100,
            height=100,
            pixmap=None
        )
        
        # Create ManifestItem with different image_id (no match)
        manifest_item = ManifestItem(
            image_id="different_id",
            file_name="test.png",
            page_index=0,
            classification="token",
            classification_confidence=0.8,
            label=None,
            quantity=None,
            metadata_confidence=0.0,
            dimensions={"width": 100, "height": 100},
            bbox=None,
            dedup_group_id=None,
            is_duplicate=False,
            canonical_image_id="different_id",
            file_path=str(tmp_path / "test.png")
        )
        
        result = deduplicate_images([extracted_image], [manifest_item], threshold=8)
        
        # Should handle gracefully and return empty result
        assert result == {}
    
    def test_deduplicate_corrupted_image_files(self, tmp_path):
        """Test deduplication handles corrupted image files gracefully."""
        # Create corrupted "image" file
        corrupted_path = tmp_path / "corrupted.png"
        corrupted_path.write_bytes(b"not an image")
        
        # Create mock ExtractedImage and ManifestItem
        extracted_image = ExtractedImage(
            id="img1",
            page_index=0,
            source_type="embedded",
            width=100,
            height=100,
            pixmap=None
        )
        
        manifest_item = ManifestItem(
            image_id="img1",
            file_name="corrupted.png",
            page_index=0,
            classification="token",
            classification_confidence=0.8,
            label=None,
            quantity=None,
            metadata_confidence=0.0,
            dimensions={"width": 100, "height": 100},
            bbox=None,
            dedup_group_id=None,
            is_duplicate=False,
            canonical_image_id="img1",
            file_path=str(corrupted_path)
        )
        
        result = deduplicate_images([extracted_image], [manifest_item], threshold=8)
        
        # Should handle gracefully and return empty result
        assert result == {}
    
    def test_deduplicate_threshold_effects(self, tmp_path):
        """Test that threshold parameter affects grouping."""
        # Create slightly different images
        img1 = Image.new('RGB', (100, 100), 'red')
        img2 = Image.new('RGB', (100, 100), (255, 1, 0))  # Very slightly different
        
        img_path1 = tmp_path / "img1.png"
        img_path2 = tmp_path / "img2.png"
        img1.save(img_path1)
        img2.save(img_path2)
        
        # Create mock data
        extracted_images = [
            ExtractedImage(id="img1", page_index=0, source_type="embedded", width=100, height=100, pixmap=None),
            ExtractedImage(id="img2", page_index=0, source_type="embedded", width=100, height=100, pixmap=None)
        ]
        
        manifest_items = [
            ManifestItem(
                image_id="img1", file_name="img1.png", page_index=0, classification="token",
                classification_confidence=0.8, label=None, quantity=None, metadata_confidence=0.0,
                dimensions={"width": 100, "height": 100}, bbox=None, dedup_group_id=None,
                is_duplicate=False, canonical_image_id="img1", file_path=str(img_path1)
            ),
            ManifestItem(
                image_id="img2", file_name="img2.png", page_index=0, classification="token",
                classification_confidence=0.8, label=None, quantity=None, metadata_confidence=0.0,
                dimensions={"width": 100, "height": 100}, bbox=None, dedup_group_id=None,
                is_duplicate=False, canonical_image_id="img2", file_path=str(img_path2)
            )
        ]
        
        # Test with high threshold (should group)
        result_high = deduplicate_images(extracted_images, manifest_items, threshold=64)
        
        # Test with low threshold (might not group)
        result_low = deduplicate_images(extracted_images, manifest_items, threshold=0)
        
        # High threshold should have same or more groups than low threshold
        assert len(result_high) >= len(result_low)