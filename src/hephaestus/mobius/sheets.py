"""
Component sheet segmentation for MOBIUS extraction.

Segments component_sheet images into individual atomic components.
"""

from dataclasses import dataclass
from typing import List, Tuple
import numpy as np

from ..logging import get_logger

logger = get_logger(__name__)


@dataclass
class SheetSegment:
    """A segment (component) extracted from a component sheet."""
    
    # Bounding box in sheet coordinates (x, y, w, h)
    bbox: Tuple[int, int, int, int]
    
    # Segment index (deterministic ordering)
    segment_index: int
    
    # Image data (RGB numpy array)
    image_data: np.ndarray


def segment_component_sheet(
    sheet_image: np.ndarray,
    sheet_id: str
) -> List[SheetSegment]:
    """
    Segment a component sheet into individual components.
    
    Uses grid detection and contour finding to identify individual components.
    
    Args:
        sheet_image: RGB numpy array of the component sheet
        sheet_id: Identifier for the sheet (for logging)
    
    Returns:
        List of SheetSegment objects (deterministically ordered)
    """
    try:
        import cv2
    except ImportError:
        logger.warning(f"OpenCV not available, cannot segment sheet {sheet_id}")
        return []
    
    logger.info(f"Segmenting component sheet {sheet_id}")
    
    height, width = sheet_image.shape[:2]
    
    # Convert to grayscale
    if len(sheet_image.shape) == 3:
        gray = cv2.cvtColor(sheet_image, cv2.COLOR_RGB2GRAY)
    else:
        gray = sheet_image.copy()
    
    # Edge detection
    edges = cv2.Canny(gray, 50, 150)
    
    # Morphological operations to connect nearby edges
    kernel = np.ones((5, 5), np.uint8)
    dilated = cv2.dilate(edges, kernel, iterations=2)
    
    # Find contours
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    logger.debug(f"Found {len(contours)} contours in sheet {sheet_id}")
    
    # Filter contours to find component-sized regions
    segments = []
    min_area = (width * height) * 0.01  # At least 1% of sheet
    max_area = (width * height) * 0.4   # At most 40% of sheet
    
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        
        # Filter by area
        if area < min_area or area > max_area:
            continue
        
        # Filter by aspect ratio (reasonable component shapes)
        aspect_ratio = max(w / h, h / w) if h > 0 else float('inf')
        if aspect_ratio > 5.0:
            continue
        
        # Extract segment
        segment_image = sheet_image[y:y+h, x:x+w].copy()
        
        segments.append(SheetSegment(
            bbox=(x, y, w, h),
            segment_index=len(segments),
            image_data=segment_image
        ))
    
    # Sort segments deterministically (top-to-bottom, left-to-right)
    segments.sort(key=lambda s: (s.bbox[1], s.bbox[0]))
    
    # Reassign indices after sorting
    for i, segment in enumerate(segments):
        segment.segment_index = i
    
    logger.info(f"Segmented sheet {sheet_id} into {len(segments)} components")
    
    return segments
