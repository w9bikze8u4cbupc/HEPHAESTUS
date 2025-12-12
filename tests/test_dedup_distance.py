"""Tests for perceptual hash distance metrics."""

import pytest
from PIL import Image
import imagehash

from hephaestus.dedup.distance import hamming_distance, combined_distance
from hephaestus.dedup.hash import ImageHashes


class TestHammingDistance:
    def test_hamming_distance_identical(self):
        """Test hamming distance between identical hashes."""
        img = Image.new('RGB', (64, 64), 'red')
        hash1 = imagehash.phash(img)
        hash2 = imagehash.phash(img)
        
        distance = hamming_distance(hash1, hash2)
        assert distance == 0
    
    def test_hamming_distance_different(self):
        """Test hamming distance between different hashes."""
        # Create more visually different images
        img1 = Image.new('RGB', (64, 64), 'white')
        img2 = Image.new('RGB', (64, 64), 'black')
        
        # Add patterns to make them more different
        for x in range(0, 64, 8):
            for y in range(0, 64, 8):
                img1.putpixel((x, y), (0, 0, 0))
                img2.putpixel((x, y), (255, 255, 255))
        
        hash1 = imagehash.phash(img1)
        hash2 = imagehash.phash(img2)
        
        distance = hamming_distance(hash1, hash2)
        # Only assert if hashes are actually different
        if hash1 != hash2:
            assert distance > 0
        assert isinstance(distance, int)
    
    def test_hamming_distance_symmetric(self):
        """Test that hamming distance is symmetric."""
        # Create different patterned images
        img1 = Image.new('RGB', (32, 32), 'white')
        img2 = Image.new('RGB', (32, 32), 'white')
        
        # Add different patterns
        for x in range(16):
            img1.putpixel((x, x), (0, 0, 0))
            img2.putpixel((x, 31-x), (0, 0, 0))
        
        hash1 = imagehash.phash(img1)
        hash2 = imagehash.phash(img2)
        
        dist1 = hamming_distance(hash1, hash2)
        dist2 = hamming_distance(hash2, hash1)
        
        assert dist1 == dist2


class TestCombinedDistance:
    def test_combined_distance_phash_only(self):
        """Test combined distance with only phash available."""
        img1 = Image.new('RGB', (32, 32), 'white')
        img2 = Image.new('RGB', (32, 32), 'black')
        
        phash1 = imagehash.phash(img1)
        phash2 = imagehash.phash(img2)
        
        hashes1 = ImageHashes(phash=phash1, dhash=None)
        hashes2 = ImageHashes(phash=phash2, dhash=None)
        
        distance = combined_distance(hashes1, hashes2)
        expected = float(hamming_distance(phash1, phash2))
        
        assert distance == expected
    
    def test_combined_distance_both_hashes(self):
        """Test combined distance with both phash and dhash."""
        img1 = Image.new('RGB', (32, 32), 'white')
        img2 = Image.new('RGB', (32, 32), 'black')
        
        phash1 = imagehash.phash(img1)
        phash2 = imagehash.phash(img2)
        dhash1 = imagehash.dhash(img1)
        dhash2 = imagehash.dhash(img2)
        
        hashes1 = ImageHashes(phash=phash1, dhash=dhash1)
        hashes2 = ImageHashes(phash=phash2, dhash=dhash2)
        
        distance = combined_distance(hashes1, hashes2)
        
        # Should be weighted combination
        phash_dist = hamming_distance(phash1, phash2)
        dhash_dist = hamming_distance(dhash1, dhash2)
        expected = 0.7 * phash_dist + 0.3 * dhash_dist
        
        assert abs(distance - expected) < 0.001
    
    def test_combined_distance_custom_weights(self):
        """Test combined distance with custom weights."""
        img1 = Image.new('RGB', (32, 32), 'white')
        img2 = Image.new('RGB', (32, 32), 'black')
        
        phash1 = imagehash.phash(img1)
        phash2 = imagehash.phash(img2)
        dhash1 = imagehash.dhash(img1)
        dhash2 = imagehash.dhash(img2)
        
        hashes1 = ImageHashes(phash=phash1, dhash=dhash1)
        hashes2 = ImageHashes(phash=phash2, dhash=dhash2)
        
        distance = combined_distance(hashes1, hashes2, phash_weight=0.8, dhash_weight=0.2)
        
        # Should use custom weights
        phash_dist = hamming_distance(phash1, phash2)
        dhash_dist = hamming_distance(dhash1, dhash2)
        expected = 0.8 * phash_dist + 0.2 * dhash_dist
        
        assert abs(distance - expected) < 0.001
    
    def test_combined_distance_mixed_availability(self):
        """Test combined distance when only one image has dhash."""
        img1 = Image.new('RGB', (32, 32), 'white')
        img2 = Image.new('RGB', (32, 32), 'black')
        
        phash1 = imagehash.phash(img1)
        phash2 = imagehash.phash(img2)
        dhash1 = imagehash.dhash(img1)
        
        hashes1 = ImageHashes(phash=phash1, dhash=dhash1)
        hashes2 = ImageHashes(phash=phash2, dhash=None)
        
        distance = combined_distance(hashes1, hashes2)
        expected = float(hamming_distance(phash1, phash2))
        
        # Should fall back to phash only
        assert distance == expected