#!/usr/bin/env python3
"""
Auto-crop all component images to remove whitespace/borders.
Takes the legacy extraction output and crops each image to its content bounds.
"""
import cv2
import numpy as np
from pathlib import Path
from typing import Tuple, Optional
import shutil

def imread_unicode(path: str) -> Optional[np.ndarray]:
    """Unicode-safe image loading for Windows."""
    try:
        data = np.fromfile(str(path), dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        print(f"Warning: Failed to load {path}: {e}")
        return None


def find_content_bounds(img: np.ndarray, threshold: int = 240) -> Tuple[int, int, int, int]:
    """
    Find the bounding box of non-white content in an image.
    
    Args:
        img: Input image (BGR)
        threshold: Pixel value threshold (pixels above this are considered "white")
    
    Returns:
        (x, y, w, h) bounding box of content
    """
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # More aggressive thresholding - consider near-white as white too
    # Pixels below threshold are content (black=0, white=255)
    _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY_INV)
    
    # Apply morphological operations to clean up noise
    kernel = np.ones((3, 3), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    
    # Find contours
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        # No content found, return full image
        return 0, 0, img.shape[1], img.shape[0]
    
    # Filter out very small contours (noise)
    min_area = 100
    contours = [c for c in contours if cv2.contourArea(c) > min_area]
    
    if not contours:
        return 0, 0, img.shape[1], img.shape[0]
    
    # Get bounding box of all contours combined
    x_min, y_min = img.shape[1], img.shape[0]
    x_max, y_max = 0, 0
    
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        x_min = min(x_min, x)
        y_min = min(y_min, y)
        x_max = max(x_max, x + w)
        y_max = max(y_max, y + h)
    
    # Add small padding (2 pixels)
    padding = 2
    x_min = max(0, x_min - padding)
    y_min = max(0, y_min - padding)
    x_max = min(img.shape[1], x_max + padding)
    y_max = min(img.shape[0], y_max + padding)
    
    return x_min, y_min, x_max - x_min, y_max - y_min


def crop_image(input_path: Path, output_path: Path) -> bool:
    """
    Crop an image to its content bounds and save.
    
    Args:
        input_path: Path to input image
        output_path: Path to save cropped image
    
    Returns:
        True if successful, False otherwise
    """
    img = imread_unicode(str(input_path))
    if img is None:
        return False
    
    # Find content bounds
    x, y, w, h = find_content_bounds(img)
    
    # Check if crop is meaningful (not just full image)
    original_area = img.shape[0] * img.shape[1]
    crop_area = w * h
    crop_ratio = crop_area / original_area
    
    # Crop the image
    cropped = img[y:y+h, x:x+w]
    
    # Save using unicode-safe method
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _, encoded = cv2.imencode('.png', cropped)
    encoded.tofile(str(output_path))
    
    # Report
    reduction = (1 - crop_ratio) * 100
    print(f"  {input_path.name}")
    print(f"    Original: {img.shape[1]}x{img.shape[0]} -> Cropped: {w}x{h} ({reduction:.1f}% reduction)")
    
    return True


def main():
    # Source and destination directories
    source_dir = Path("test_output/tm_legacy_check/images/canonicals/boards")
    output_dir = Path("test_output/tm_cropped_components")
    
    if not source_dir.exists():
        print(f"Error: Source directory not found: {source_dir}")
        return
    
    # Get all PNG files
    image_files = sorted(source_dir.glob("*.png"))
    
    if not image_files:
        print(f"No PNG files found in {source_dir}")
        return
    
    print(f"Found {len(image_files)} images to crop")
    print(f"Output directory: {output_dir}")
    print("="*60)
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process each image
    success_count = 0
    for img_path in image_files:
        output_path = output_dir / img_path.name
        if crop_image(img_path, output_path):
            success_count += 1
    
    print("="*60)
    print(f"✓ Successfully cropped {success_count}/{len(image_files)} images")
    print(f"✓ Output saved to: {output_dir.absolute()}")
    
    # Open the output folder
    import subprocess
    subprocess.run(["explorer", str(output_dir.absolute())], check=False)


if __name__ == "__main__":
    main()
