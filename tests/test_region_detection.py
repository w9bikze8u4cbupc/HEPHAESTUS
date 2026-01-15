"""
Unit tests for region detection module.

Tests use synthetic fixtures (no PDF dependency).
"""

import pytest
import numpy as np
from PIL import Image
from pathlib import Path

# Only import if regions extra is installed
try:
    from hephaestus.regions.detection import (
        detect_regions,
        RegionDetectionConfig,
        DetectedRegion
    )
    REGIONS_AVAILABLE = True
except ImportError:
    REGIONS_AVAILABLE = False


@pytest.mark.skipif(not REGIONS_AVAILABLE, reason="regions extra not installed")
class TestRegionDetection:
    """Test suite for region detection."""
    
    @pytest.fixture
    def test_image(self):
        """Load test fixture image."""
        fixture_path = Path(__file__).parent / "fixtures" / "regions" / "test_page.png"
        img = Image.open(fixture_path)
        return np.array(img)
    
    @pytest.fixture
    def default_config(self):
        """Default detection configuration."""
        return RegionDetectionConfig(
            min_area=2500,
            max_area_ratio=0.35,
            merge_threshold=0.3,
            top_margin_ratio=0.06,
            bottom_margin_ratio=0.06,
            left_margin_ratio=0.02,
            right_margin_ratio=0.02,
            min_area_ratio=0.0015,
            max_aspect_ratio=8.0
        )
    
    def test_detects_expected_regions_count_range(self, test_image, default_config):
        """Test that detection finds expected number of component regions."""
        regions = detect_regions(test_image, default_config)
        
        # Expected: 5 components (board, card, 2 tokens, small icon)
        # Filtered: header, footer, margins, text block, banner
        # Allow some tolerance for edge detection variations
        assert 4 <= len(regions) <= 6, f"Expected 4-6 regions, got {len(regions)}"
    
    def test_filters_headers_and_footers(self, test_image, default_config):
        """Test that header and footer regions are filtered out."""
        regions = detect_regions(test_image, default_config)
        
        page_height = test_image.shape[0]
        top_margin = int(page_height * default_config.top_margin_ratio)
        bottom_margin = int(page_height * default_config.bottom_margin_ratio)
        
        for region in regions:
            x, y, w, h = region.bbox
            # No region should touch top or bottom margins
            assert y >= top_margin, f"Region at y={y} touches top margin"
            assert y + h <= page_height - bottom_margin, f"Region at y={y}+{h} touches bottom margin"
    
    def test_deterministic_sorting(self, test_image, default_config):
        """Test that region detection produces deterministic ordering."""
        # Run detection twice
        regions1 = detect_regions(test_image, default_config)
        regions2 = detect_regions(test_image, default_config)
        
        # Should produce identical results
        assert len(regions1) == len(regions2), "Region count differs between runs"
        
        for r1, r2 in zip(regions1, regions2):
            assert r1.bbox == r2.bbox, f"Bounding boxes differ: {r1.bbox} vs {r2.bbox}"
            assert r1.area == r2.area, f"Areas differ: {r1.area} vs {r2.area}"
            assert abs(r1.confidence - r2.confidence) < 1e-6, f"Confidence differs: {r1.confidence} vs {r2.confidence}"
    
    def test_merge_overlaps_is_deterministic(self, test_image, default_config):
        """Test that overlap merging is deterministic."""
        # Run detection multiple times
        results = [detect_regions(test_image, default_config) for _ in range(3)]
        
        # All runs should produce identical merged regions
        for i in range(1, len(results)):
            assert len(results[0]) == len(results[i]), "Merged region count varies"
            for r1, r2 in zip(results[0], results[i]):
                assert r1.bbox == r2.bbox, "Merged bounding boxes differ"
                assert r1.is_merged == r2.is_merged, "Merge flags differ"
    
    def test_filters_extreme_aspect_ratios(self, test_image, default_config):
        """Test that extreme banner-like regions are filtered."""
        regions = detect_regions(test_image, default_config)
        
        for region in regions:
            x, y, w, h = region.bbox
            aspect_ratio = max(w / h, h / w) if h > 0 else float('inf')
            assert aspect_ratio <= default_config.max_aspect_ratio, \
                f"Region with extreme aspect ratio {aspect_ratio:.2f} not filtered"
    
    def test_respects_min_area_threshold(self, test_image, default_config):
        """Test that regions below minimum area are filtered."""
        regions = detect_regions(test_image, default_config)
        
        page_area = test_image.shape[0] * test_image.shape[1]
        min_area_absolute = max(default_config.min_area, int(page_area * default_config.min_area_ratio))
        
        for region in regions:
            assert region.area >= min_area_absolute, \
                f"Region with area {region.area} below threshold {min_area_absolute}"
    
    def test_respects_max_area_threshold(self, test_image, default_config):
        """Test that regions above maximum area are filtered."""
        regions = detect_regions(test_image, default_config)
        
        page_area = test_image.shape[0] * test_image.shape[1]
        max_area = int(page_area * default_config.max_area_ratio)
        
        for region in regions:
            assert region.area <= max_area, \
                f"Region with area {region.area} exceeds threshold {max_area}"
    
    def test_confidence_scores_in_valid_range(self, test_image, default_config):
        """Test that confidence scores are in [0, 1] range."""
        regions = detect_regions(test_image, default_config)
        
        for region in regions:
            assert 0.0 <= region.confidence <= 1.0, \
                f"Confidence {region.confidence} out of range [0, 1]"
    
    def test_regions_sorted_top_to_bottom_left_to_right(self, test_image, default_config):
        """Test that regions are sorted by position."""
        regions = detect_regions(test_image, default_config)
        
        if len(regions) < 2:
            pytest.skip("Need at least 2 regions to test sorting")
        
        # Check that regions are sorted by (y, x, -area)
        for i in range(len(regions) - 1):
            r1, r2 = regions[i], regions[i + 1]
            y1, x1 = r1.bbox[1], r1.bbox[0]
            y2, x2 = r2.bbox[1], r2.bbox[0]
            
            # Either y1 < y2, or y1 == y2 and x1 <= x2
            assert y1 <= y2, f"Regions not sorted by y: {y1} > {y2}"
            if y1 == y2:
                assert x1 <= x2, f"Regions with same y not sorted by x: {x1} > {x2}"
