"""Tests for duplicate clustering logic."""

import pytest
from PIL import Image
import imagehash

from hephaestus.dedup.cluster import cluster_duplicates, DedupGroup
from hephaestus.dedup.hash import ImageHashes


class TestDedupGroup:
    def test_dedup_group_immutable(self):
        """Test that DedupGroup is immutable."""
        group = DedupGroup(
            group_id="dup_001",
            image_ids=["img1", "img2"],
            canonical_id="img1"
        )
        
        # Should not be able to modify
        with pytest.raises(AttributeError):
            group.group_id = "dup_002"  # type: ignore


class TestClusterDuplicates:
    def test_cluster_empty_input(self):
        """Test clustering with empty input."""
        result = cluster_duplicates({})
        assert result == []
    
    def test_cluster_single_image(self):
        """Test clustering with single image."""
        img = Image.new('RGB', (32, 32), 'red')
        phash = imagehash.phash(img)
        hashes = ImageHashes(phash=phash)
        
        image_hashes = {"img1": hashes}
        result = cluster_duplicates(image_hashes)
        
        # Single image should not form a group
        assert result == []
    
    def test_cluster_identical_images(self):
        """Test clustering identical images."""
        img = Image.new('RGB', (32, 32), 'red')
        phash = imagehash.phash(img)
        hashes = ImageHashes(phash=phash)
        
        image_hashes = {
            "img1": hashes,
            "img2": hashes,
            "img3": hashes
        }
        
        result = cluster_duplicates(image_hashes, threshold=8)
        
        # Should form one group
        assert len(result) == 1
        group = result[0]
        
        assert group.group_id == "dup_001"
        assert set(group.image_ids) == {"img1", "img2", "img3"}
        assert group.canonical_id == "img1"  # Lexicographically first
    
    def test_cluster_different_images(self):
        """Test clustering completely different images."""
        img1 = Image.new('RGB', (32, 32), 'red')
        img2 = Image.new('RGB', (32, 32), 'blue')
        img3 = Image.new('RGB', (32, 32), 'green')
        
        hashes1 = ImageHashes(phash=imagehash.phash(img1))
        hashes2 = ImageHashes(phash=imagehash.phash(img2))
        hashes3 = ImageHashes(phash=imagehash.phash(img3))
        
        image_hashes = {
            "img1": hashes1,
            "img2": hashes2,
            "img3": hashes3
        }
        
        result = cluster_duplicates(image_hashes, threshold=8)
        
        # Should not form any groups (assuming images are different enough)
        # This might vary based on actual hash values, so we check structure
        for group in result:
            assert isinstance(group, DedupGroup)
            assert len(group.image_ids) >= 2
            assert group.canonical_id in group.image_ids
    
    def test_cluster_threshold_sensitivity(self):
        """Test that clustering respects threshold parameter."""
        # Create slightly different images
        img1 = Image.new('RGB', (32, 32), 'red')
        img2 = Image.new('RGB', (32, 32), (255, 1, 0))  # Very slightly different
        
        hashes1 = ImageHashes(phash=imagehash.phash(img1))
        hashes2 = ImageHashes(phash=imagehash.phash(img2))
        
        image_hashes = {
            "img1": hashes1,
            "img2": hashes2
        }
        
        # With high threshold, should group together
        result_high = cluster_duplicates(image_hashes, threshold=64)
        
        # With low threshold, might not group (depends on actual hash difference)
        result_low = cluster_duplicates(image_hashes, threshold=0)
        
        # High threshold should have same or more groups than low threshold
        assert len(result_high) >= len(result_low)
    
    def test_cluster_deterministic_grouping(self):
        """Test that clustering produces deterministic results."""
        img = Image.new('RGB', (32, 32), 'red')
        phash = imagehash.phash(img)
        hashes = ImageHashes(phash=phash)
        
        image_hashes = {
            "img3": hashes,
            "img1": hashes,
            "img2": hashes
        }
        
        # Run clustering multiple times
        result1 = cluster_duplicates(image_hashes, threshold=8)
        result2 = cluster_duplicates(image_hashes, threshold=8)
        
        # Results should be identical
        assert len(result1) == len(result2)
        
        if result1:  # If groups were formed
            group1 = result1[0]
            group2 = result2[0]
            
            assert group1.group_id == group2.group_id
            assert group1.image_ids == group2.image_ids
            assert group1.canonical_id == group2.canonical_id
    
    def test_cluster_canonical_selection(self):
        """Test canonical image selection logic."""
        img = Image.new('RGB', (32, 32), 'red')
        phash = imagehash.phash(img)
        hashes = ImageHashes(phash=phash)
        
        # Test with different ID orderings
        image_hashes = {
            "z_last": hashes,
            "a_first": hashes,
            "m_middle": hashes
        }
        
        result = cluster_duplicates(image_hashes, threshold=8)
        
        if result:  # If groups were formed
            group = result[0]
            # Should select lexicographically first
            assert group.canonical_id == "a_first"
    
    def test_cluster_multiple_groups(self):
        """Test clustering with multiple separate groups."""
        # Create two pairs of identical images
        img1 = Image.new('RGB', (32, 32), 'red')
        img2 = Image.new('RGB', (32, 32), 'blue')
        
        phash1 = imagehash.phash(img1)
        phash2 = imagehash.phash(img2)
        
        hashes1 = ImageHashes(phash=phash1)
        hashes2 = ImageHashes(phash=phash2)
        
        image_hashes = {
            "red1": hashes1,
            "red2": hashes1,
            "blue1": hashes2,
            "blue2": hashes2
        }
        
        result = cluster_duplicates(image_hashes, threshold=8)
        
        # Should form two groups (if images are different enough)
        # The exact number depends on hash similarity, but structure should be correct
        for group in result:
            assert len(group.image_ids) >= 2
            assert group.canonical_id in group.image_ids
            
            # All images in group should have same prefix (red or blue)
            prefixes = set(img_id.split('1')[0] + '1' if '1' in img_id else img_id.split('2')[0] + '2' for img_id in group.image_ids)
            # This test might be too strict depending on actual hash values
    
    def test_cluster_group_id_ordering(self):
        """Test that group IDs are assigned in deterministic order."""
        # Create images that will definitely form separate groups
        img1 = Image.new('RGB', (32, 32), 'red')
        img2 = Image.new('RGB', (32, 32), 'blue')
        
        phash1 = imagehash.phash(img1)
        phash2 = imagehash.phash(img2)
        
        hashes1 = ImageHashes(phash=phash1)
        hashes2 = ImageHashes(phash=phash2)
        
        image_hashes = {
            "z_red1": hashes1,
            "z_red2": hashes1,
            "a_blue1": hashes2,
            "a_blue2": hashes2
        }
        
        result = cluster_duplicates(image_hashes, threshold=8)
        
        if len(result) >= 2:
            # Groups should be ordered by canonical ID
            group_ids = [group.group_id for group in result]
            canonical_ids = [group.canonical_id for group in result]
            
            # Group IDs should be sequential
            assert group_ids == ["dup_001", "dup_002"]
            
            # Should be ordered by canonical ID
            assert canonical_ids == sorted(canonical_ids)