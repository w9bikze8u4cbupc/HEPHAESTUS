"""Tests for perceptual hash computation."""

import tempfile
from pathlib import Path
import pytest
from PIL import Image
import imagehash

from hephaestus.dedup.hash import compute_hashes, ImageHashes, HashComputationError


class TestHashComputation:
    def test_compute_hashes_basic(self, tmp_path):
        """Test basic hash computation for a simple image."""
        # Create a simple test image
        img = Image.new('RGB', (100, 100), color='red')
        img_path = tmp_path / "test.png"
        img.save(img_path)
        
        # Compute hashes
        hashes = compute_hashes(img_path)
        
        # Verify structure
        assert isinstance(hashes, ImageHashes)
        assert isinstance(hashes.phash, imagehash.ImageHash)
        assert isinstance(hashes.dhash, imagehash.ImageHash)
    
    def test_compute_hashes_no_dhash(self, tmp_path):
        """Test hash computation with dhash disabled."""
        # Create a simple test image
        img = Image.new('RGB', (100, 100), color='blue')
        img_path = tmp_path / "test.png"
        img.save(img_path)
        
        # Compute hashes without dhash
        hashes = compute_hashes(img_path, compute_dhash=False)
        
        # Verify structure
        assert isinstance(hashes, ImageHashes)
        assert isinstance(hashes.phash, imagehash.ImageHash)
        assert hashes.dhash is None
    
    def test_compute_hashes_different_modes(self, tmp_path):
        """Test hash computation with different image modes."""
        # Test RGBA image
        img_rgba = Image.new('RGBA', (50, 50), color=(255, 0, 0, 128))
        rgba_path = tmp_path / "rgba.png"
        img_rgba.save(rgba_path)
        
        # Test grayscale image
        img_gray = Image.new('L', (50, 50), color=128)
        gray_path = tmp_path / "gray.png"
        img_gray.save(gray_path)
        
        # Both should work and produce valid hashes
        rgba_hashes = compute_hashes(rgba_path)
        gray_hashes = compute_hashes(gray_path)
        
        assert isinstance(rgba_hashes.phash, imagehash.ImageHash)
        assert isinstance(gray_hashes.phash, imagehash.ImageHash)
    
    def test_compute_hashes_deterministic(self, tmp_path):
        """Test that hash computation is deterministic."""
        # Create identical images
        img = Image.new('RGB', (64, 64), color='green')
        path1 = tmp_path / "img1.png"
        path2 = tmp_path / "img2.png"
        img.save(path1)
        img.save(path2)
        
        # Compute hashes multiple times
        hashes1a = compute_hashes(path1)
        hashes1b = compute_hashes(path1)
        hashes2 = compute_hashes(path2)
        
        # Should be identical
        assert hashes1a.phash == hashes1b.phash
        assert hashes1a.dhash == hashes1b.dhash
        assert hashes1a.phash == hashes2.phash
        assert hashes1a.dhash == hashes2.dhash
    
    def test_compute_hashes_nonexistent_file(self, tmp_path):
        """Test error handling for nonexistent files."""
        nonexistent = tmp_path / "nonexistent.png"
        
        with pytest.raises(HashComputationError):
            compute_hashes(nonexistent)
    
    def test_compute_hashes_corrupted_file(self, tmp_path):
        """Test error handling for corrupted image files."""
        corrupted = tmp_path / "corrupted.png"
        corrupted.write_bytes(b"not an image")
        
        with pytest.raises(HashComputationError):
            compute_hashes(corrupted)


class TestImageHashes:
    def test_image_hashes_immutable(self):
        """Test that ImageHashes is immutable."""
        # Create dummy hashes
        phash = imagehash.phash(Image.new('RGB', (10, 10), 'red'))
        dhash = imagehash.dhash(Image.new('RGB', (10, 10), 'red'))
        
        hashes = ImageHashes(phash=phash, dhash=dhash)
        
        # Should not be able to modify
        with pytest.raises(AttributeError):
            hashes.phash = imagehash.phash(Image.new('RGB', (10, 10), 'blue'))  # type: ignore
    
    def test_image_hashes_equality(self):
        """Test ImageHashes equality comparison."""
        img = Image.new('RGB', (10, 10), 'red')
        phash = imagehash.phash(img)
        dhash = imagehash.dhash(img)
        
        hashes1 = ImageHashes(phash=phash, dhash=dhash)
        hashes2 = ImageHashes(phash=phash, dhash=dhash)
        
        assert hashes1 == hashes2
        
        # Different hashes should not be equal
        # Create a more visually different image
        different_img = Image.new('RGB', (10, 10), 'white')
        # Add some pattern to make it more different
        for x in range(5):
            for y in range(5):
                different_img.putpixel((x, y), (0, 0, 0))
        
        different_phash = imagehash.phash(different_img)
        hashes3 = ImageHashes(phash=different_phash, dhash=dhash)
        
        # Only assert inequality if the hashes are actually different
        if different_phash != phash:
            assert hashes1 != hashes3