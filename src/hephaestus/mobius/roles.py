"""
Image-role classification for MOBIUS extraction.

Classifies embedded images into roles to determine extraction strategy.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple
import numpy as np

from ..logging import get_logger

logger = get_logger(__name__)


class ImageRole(Enum):
    """Image role taxonomy for MOBIUS extraction."""
    
    COMPONENT_ATOMIC = "component_atomic"      # Single indivisible component
    COMPONENT_SHEET = "component_sheet"        # Multiple similar components (grid/inventory)
    ILLUSTRATION = "illustration"              # Context/explanation (boards, setup)
    DIAGRAM = "diagram"                        # Annotated/editorial (arrows, callouts)
    ART = "art"                               # Cover art/atmosphere


@dataclass
class ImageRoleClassification:
    """Result of image-role classification."""
    
    role: ImageRole
    confidence: float
    rationale: str


def classify_image_role(
    pixmap: "fitz.Pixmap",
    width: int,
    height: int,
    page_index: int,
    image_index: int
) -> ImageRoleClassification:
    """
    Classify an embedded image into its role.
    
    Uses deterministic heuristics based on image properties.
    
    Args:
        pixmap: PyMuPDF Pixmap object
        width: Image width in pixels
        height: Image height in pixels
        page_index: Source page index
        image_index: Image index on page
    
    Returns:
        ImageRoleClassification with role, confidence, and rationale
    """
    # Convert pixmap to numpy array for analysis
    import fitz
    
    # Get image data as numpy array
    if pixmap.n < 4:  # RGB or grayscale
        image_data = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.height, pixmap.width, pixmap.n)
    else:  # RGBA
        image_data = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(pixmap.height, pixmap.width, pixmap.n)
    
    area = width * height
    aspect_ratio = max(width / height, height / width) if height > 0 else 1.0
    
    # Rule 1: Very large images (> 40% of typical page) are likely illustrations/boards
    # Typical page at 150 DPI: ~1240x1754 pixels = 2.17M pixels
    # 40% threshold = ~870k pixels
    if area > 870_000:
        return ImageRoleClassification(
            role=ImageRole.ILLUSTRATION,
            confidence=0.9,
            rationale=f"large_area_{area}_pixels"
        )
    
    # Rule 2: Very small images (< 10k pixels) are likely icons/diagrams
    if area < 10_000:
        return ImageRoleClassification(
            role=ImageRole.DIAGRAM,
            confidence=0.8,
            rationale=f"small_area_{area}_pixels"
        )
    
    # Rule 3: Extreme aspect ratios (> 5:1) are likely diagrams/banners
    if aspect_ratio > 5.0:
        return ImageRoleClassification(
            role=ImageRole.DIAGRAM,
            confidence=0.85,
            rationale=f"extreme_aspect_{aspect_ratio:.2f}"
        )
    
    # Rule 4: Check for grid structure (component sheets)
    # Component sheets have repetitive structure
    # DISABLED: Grid detection too aggressive, classifying full pages as sheets
    # if _has_grid_structure(image_data, width, height):
    #     return ImageRoleClassification(
    #         role=ImageRole.COMPONENT_SHEET,
    #         confidence=0.85,
    #         rationale="grid_structure_detected"
    #     )
    
    # Rule 5: Medium-sized, reasonable aspect ratio = likely atomic component
    # This is the default for card-sized images
    if 10_000 <= area <= 500_000 and aspect_ratio <= 3.0:
        return ImageRoleClassification(
            role=ImageRole.COMPONENT_ATOMIC,
            confidence=0.7,
            rationale=f"card_sized_area_{area}_aspect_{aspect_ratio:.2f}"
        )
    
    # Default: Treat as atomic component (conservative)
    return ImageRoleClassification(
        role=ImageRole.COMPONENT_ATOMIC,
        confidence=0.5,
        rationale="default_atomic"
    )


def _has_grid_structure(image_data: np.ndarray, width: int, height: int) -> bool:
    """
    Detect if image has grid structure (component sheet indicator).
    
    Uses edge detection to find regular spacing patterns.
    
    Args:
        image_data: RGB numpy array
        width: Image width
        height: Image height
    
    Returns:
        True if grid structure detected
    """
    try:
        import cv2
    except ImportError:
        # If OpenCV not available, return False (no grid detection)
        return False
    
    # Convert to grayscale
    if len(image_data.shape) == 3:
        gray = cv2.cvtColor(image_data, cv2.COLOR_RGB2GRAY)
    else:
        gray = image_data
    
    # Edge detection
    edges = cv2.Canny(gray, 50, 150)
    
    # Look for horizontal and vertical lines (grid indicators)
    # Use Hough line transform to detect straight lines
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=min(width, height)//4, maxLineGap=10)
    
    if lines is None or len(lines) < 4:
        return False
    
    # Count horizontal and vertical lines
    horizontal_lines = 0
    vertical_lines = 0
    
    for line in lines:
        x1, y1, x2, y2 = line[0]
        
        # Check if line is horizontal (small y difference)
        if abs(y2 - y1) < 10:
            horizontal_lines += 1
        
        # Check if line is vertical (small x difference)
        if abs(x2 - x1) < 10:
            vertical_lines += 1
    
    # Grid structure: at least 2 horizontal and 2 vertical lines
    return horizontal_lines >= 2 and vertical_lines >= 2
