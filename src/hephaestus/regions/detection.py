"""
Region detection for component extraction.

Uses computer vision techniques to identify component regions in rendered pages.
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional
import numpy as np
import cv2

from ..logging import get_logger

logger = get_logger(__name__)


@dataclass
class RegionDetectionConfig:
    """Configuration for region detection."""
    
    # Minimum region area in pixels (default 50x50 = 2500)
    min_area: int = 2500
    
    # Maximum region size as ratio of page area (0.35 = 35%)
    max_area_ratio: float = 0.35
    
    # IoU threshold for merging overlapping regions
    merge_threshold: float = 0.3
    
    # Border exclusion margins (as ratio of page dimensions)
    top_margin_ratio: float = 0.06      # 6% from top
    bottom_margin_ratio: float = 0.06   # 6% from bottom
    left_margin_ratio: float = 0.02     # 2% from left
    right_margin_ratio: float = 0.02    # 2% from right
    
    # Minimum area as ratio of page (0.0015 = 0.15%)
    min_area_ratio: float = 0.0015
    
    # Aspect ratio constraints (reject extreme banners)
    max_aspect_ratio: float = 8.0       # w/h or h/w must be <= 8
    
    # Edge detection parameters
    canny_low: int = 50
    canny_high: int = 150
    
    # Morphological operations
    dilate_kernel_size: int = 5
    dilate_iterations: int = 2
    
    # Contour approximation epsilon (as ratio of perimeter)
    approx_epsilon: float = 0.02
    
    # Text-likeness threshold (edge density for text detection)
    text_edge_density_threshold: float = 0.15
    
    # Text panel detection: connected components threshold
    # Text blocks have many small connected components (letters)
    text_cc_density_threshold: float = 0.02  # CCs per 100 pixels
    
    # Text panel detection: horizontal line alignment
    # Text panels have strong horizontal structure
    text_horizontal_ratio_threshold: float = 1.5  # horizontal edges / vertical edges


@dataclass
class DetectedRegion:
    """A detected component region."""
    
    # Bounding box in image coordinates (x, y, w, h)
    bbox: Tuple[int, int, int, int]
    
    # Area in pixels
    area: int
    
    # Confidence score (0.0 - 1.0)
    confidence: float
    
    # Whether this region was merged from multiple detections
    is_merged: bool = False
    
    def to_pdf_coords(self, page_width: float, page_height: float, img_width: int, img_height: int) -> Tuple[float, float, float, float]:
        """Convert image coordinates to PDF coordinates."""
        x, y, w, h = self.bbox
        
        # Scale factors
        scale_x = page_width / img_width
        scale_y = page_height / img_height
        
        # Convert to PDF coordinates (x0, y0, x1, y1)
        x0 = x * scale_x
        y0 = y * scale_y
        x1 = (x + w) * scale_x
        y1 = (y + h) * scale_y
        
        return (x0, y0, x1, y1)


@dataclass
class FilteredRegion:
    """A region that was filtered out (not exported)."""
    
    # Bounding box in image coordinates (x, y, w, h)
    bbox: Tuple[int, int, int, int]
    
    # Area in pixels
    area: int
    
    # Rejection reason (canonical enum string)
    rejection_reason: str
    
    def to_pdf_coords(self, page_width: float, page_height: float, img_width: int, img_height: int) -> Tuple[float, float, float, float]:
        """Convert image coordinates to PDF coordinates."""
        x, y, w, h = self.bbox
        
        # Scale factors
        scale_x = page_width / img_width
        scale_y = page_height / img_height
        
        # Convert to PDF coordinates (x0, y0, x1, y1)
        x0 = x * scale_x
        y0 = y * scale_y
        x1 = (x + w) * scale_x
        y1 = (y + h) * scale_y
        
        return (x0, y0, x1, y1)


@dataclass
class RegionDetectionResult:
    """Result of region detection including filtered regions."""
    
    # Regions that passed all filters (will be exported)
    accepted_regions: List[DetectedRegion]
    
    # Regions that were filtered out (will not be exported)
    filtered_regions: List[FilteredRegion]


def detect_regions(
    image: np.ndarray,
    config: Optional[RegionDetectionConfig] = None
) -> RegionDetectionResult:
    """
    Detect component regions in a rendered page image.
    
    Uses multi-pass edge detection and contour finding to identify rectangular regions
    that likely contain game components. Two passes optimize for different component sizes.
    
    Args:
        image: RGB or grayscale numpy array
        config: Detection configuration (uses defaults if None)
    
    Returns:
        RegionDetectionResult with accepted and filtered regions
    """
    if config is None:
        config = RegionDetectionConfig()
    
    logger.debug(f"Detecting regions in {image.shape} image")
    
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    else:
        gray = image.copy()
    
    # Calculate page area for filtering
    page_height, page_width = gray.shape
    page_area = page_height * page_width
    max_area = int(page_area * config.max_area_ratio)
    min_area_absolute = max(config.min_area, int(page_area * config.min_area_ratio))
    
    # Calculate border exclusion zones
    top_margin = int(page_height * config.top_margin_ratio)
    bottom_margin = int(page_height * config.bottom_margin_ratio)
    left_margin = int(page_width * config.left_margin_ratio)
    right_margin = int(page_width * config.right_margin_ratio)
    
    # Pass 1: Standard detection (larger components)
    edges_pass1 = cv2.Canny(gray, config.canny_low, config.canny_high)
    kernel_pass1 = np.ones((config.dilate_kernel_size, config.dilate_kernel_size), np.uint8)
    dilated_pass1 = cv2.dilate(edges_pass1, kernel_pass1, iterations=config.dilate_iterations)
    contours_pass1, _ = cv2.findContours(dilated_pass1, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Pass 2: Fine-grained detection (smaller components like tokens/icons)
    # Use lower Canny thresholds and less dilation
    edges_pass2 = cv2.Canny(gray, config.canny_low // 2, config.canny_high // 2)
    kernel_pass2 = np.ones((3, 3), np.uint8)
    dilated_pass2 = cv2.dilate(edges_pass2, kernel_pass2, iterations=1)
    contours_pass2, _ = cv2.findContours(dilated_pass2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Combine contours from both passes
    all_contours = list(contours_pass1) + list(contours_pass2)
    
    logger.debug(f"Found {len(contours_pass1)} contours (pass 1) + {len(contours_pass2)} contours (pass 2) = {len(all_contours)} total")
    
    # Extract bounding boxes and filter
    regions = []
    filtered_regions = []
    
    for contour in all_contours:
        # Get bounding rectangle
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        bbox = (x, y, w, h)
        
        # Filter 1: Area thresholds
        if area < min_area_absolute:
            filtered_regions.append(FilteredRegion(bbox=bbox, area=area, rejection_reason="too_small"))
            continue
        if area > max_area:
            filtered_regions.append(FilteredRegion(bbox=bbox, area=area, rejection_reason="oversize_region"))
            continue
        
        # Filter 2: Border exclusion (headers/footers/margins)
        if y < top_margin:  # Touches top margin
            filtered_regions.append(FilteredRegion(bbox=bbox, area=area, rejection_reason="border_top"))
            continue
        if y + h > page_height - bottom_margin:  # Touches bottom margin
            filtered_regions.append(FilteredRegion(bbox=bbox, area=area, rejection_reason="border_bottom"))
            continue
        if x < left_margin:  # Touches left margin
            filtered_regions.append(FilteredRegion(bbox=bbox, area=area, rejection_reason="border_left"))
            continue
        if x + w > page_width - right_margin:  # Touches right margin
            filtered_regions.append(FilteredRegion(bbox=bbox, area=area, rejection_reason="border_right"))
            continue
        
        # Filter 3: Aspect ratio constraint (reject extreme banners)
        aspect_ratio = max(w / h, h / w) if h > 0 else float('inf')
        if aspect_ratio > config.max_aspect_ratio:
            filtered_regions.append(FilteredRegion(bbox=bbox, area=area, rejection_reason="aspect_ratio"))
            continue
        
        # Filter 4: Text-likeness heuristic (BLOCKING - hard rejection)
        if _is_text_panel(gray[y:y+h, x:x+w], edges_pass1[y:y+h, x:x+w], config):
            filtered_regions.append(FilteredRegion(bbox=bbox, area=area, rejection_reason="text_panel"))
            continue
        
        # Calculate confidence based on contour properties
        # Higher confidence for more rectangular shapes
        perimeter = cv2.arcLength(contour, True)
        if perimeter > 0:
            circularity = 4 * np.pi * area / (perimeter * perimeter)
            # Rectangles have circularity around 0.785 (π/4)
            # Adjust confidence based on how rectangular the shape is
            confidence = min(1.0, circularity * 1.3)
        else:
            confidence = 0.5
        
        regions.append(DetectedRegion(
            bbox=(x, y, w, h),
            area=area,
            confidence=confidence,
            is_merged=False
        ))
    
    logger.debug(f"Filtered to {len(regions)} candidate regions, rejected {len(filtered_regions)}")
    
    # Merge overlapping regions (handles duplicates from multi-pass)
    regions = _merge_overlapping_regions(regions, config.merge_threshold)
    
    logger.debug(f"After merging: {len(regions)} final regions")
    
    # Sort by position (top-to-bottom, left-to-right)
    regions = _sort_regions_by_position(regions)
    
    return RegionDetectionResult(
        accepted_regions=regions,
        filtered_regions=filtered_regions
    )


def _is_text_like_region(gray_region: np.ndarray, edges_region: np.ndarray, threshold: float) -> bool:
    """
    Detect if a region is likely text-heavy (and should be excluded).
    
    Uses edge density as a proxy: text regions have high edge density
    with low fill ratio (lots of thin strokes).
    """
    if gray_region.size == 0 or edges_region.size == 0:
        return False
    
    # Calculate edge density (ratio of edge pixels to total pixels)
    edge_pixels = np.count_nonzero(edges_region)
    total_pixels = edges_region.size
    edge_density = edge_pixels / total_pixels if total_pixels > 0 else 0.0
    
    # Text regions typically have edge density > threshold
    return edge_density > threshold


def _is_text_panel(gray_region: np.ndarray, edges_region: np.ndarray, config: RegionDetectionConfig) -> bool:
    """
    Enhanced text panel detection using multiple heuristics.
    
    Text panels (like "Components list") have distinctive characteristics:
    1. High edge density (many thin strokes)
    2. Many small connected components (individual letters)
    3. Strong horizontal structure (lines of text)
    
    Args:
        gray_region: Grayscale crop of the region
        edges_region: Edge-detected crop of the region
        config: Detection configuration with thresholds
    
    Returns:
        True if region is likely a text panel
    """
    if gray_region.size == 0 or edges_region.size == 0:
        return False
    
    h, w = gray_region.shape
    area = h * w
    
    # Gate 1: Edge density (original heuristic)
    edge_pixels = np.count_nonzero(edges_region)
    edge_density = edge_pixels / area if area > 0 else 0.0
    
    if edge_density > config.text_edge_density_threshold:
        # Likely text-heavy, apply additional gates
        
        # Gate 2: Connected components density
        # Text has many small disconnected components (letters)
        num_labels, labels = cv2.connectedComponents(edges_region)
        cc_density = (num_labels - 1) / (area / 100.0) if area > 0 else 0.0  # CCs per 100 pixels
        
        if cc_density > config.text_cc_density_threshold:
            # Gate 3: Horizontal structure (lines of text)
            # Compute horizontal vs vertical edge strength
            sobel_x = cv2.Sobel(gray_region, cv2.CV_64F, 1, 0, ksize=3)
            sobel_y = cv2.Sobel(gray_region, cv2.CV_64F, 0, 1, ksize=3)
            
            horizontal_strength = np.sum(np.abs(sobel_y))  # Horizontal edges (text lines)
            vertical_strength = np.sum(np.abs(sobel_x))    # Vertical edges
            
            if vertical_strength > 0:
                horizontal_ratio = horizontal_strength / vertical_strength
                if horizontal_ratio > config.text_horizontal_ratio_threshold:
                    # All three gates passed: this is a text panel
                    return True
    
    return False


def _calculate_iou(bbox1: Tuple[int, int, int, int], bbox2: Tuple[int, int, int, int]) -> float:
    """Calculate Intersection over Union for two bounding boxes."""
    x1, y1, w1, h1 = bbox1
    x2, y2, w2, h2 = bbox2
    
    # Calculate intersection
    x_left = max(x1, x2)
    y_top = max(y1, y2)
    x_right = min(x1 + w1, x2 + w2)
    y_bottom = min(y1 + h1, y2 + h2)
    
    if x_right < x_left or y_bottom < y_top:
        return 0.0
    
    intersection = (x_right - x_left) * (y_bottom - y_top)
    
    # Calculate union
    area1 = w1 * h1
    area2 = w2 * h2
    union = area1 + area2 - intersection
    
    if union == 0:
        return 0.0
    
    return intersection / union


def _merge_two_regions(r1: DetectedRegion, r2: DetectedRegion) -> DetectedRegion:
    """Merge two overlapping regions into one."""
    x1, y1, w1, h1 = r1.bbox
    x2, y2, w2, h2 = r2.bbox
    
    # Calculate merged bounding box
    x_min = min(x1, x2)
    y_min = min(y1, y2)
    x_max = max(x1 + w1, x2 + w2)
    y_max = max(y1 + h1, y2 + h2)
    
    merged_bbox = (x_min, y_min, x_max - x_min, y_max - y_min)
    merged_area = (x_max - x_min) * (y_max - y_min)
    
    # Average confidence
    merged_confidence = (r1.confidence + r2.confidence) / 2.0
    
    return DetectedRegion(
        bbox=merged_bbox,
        area=merged_area,
        confidence=merged_confidence,
        is_merged=True
    )


def _merge_overlapping_regions(
    regions: List[DetectedRegion],
    threshold: float
) -> List[DetectedRegion]:
    """Merge regions that overlap significantly."""
    if len(regions) <= 1:
        return regions
    
    merged = []
    used = set()
    
    for i, r1 in enumerate(regions):
        if i in used:
            continue
        
        current = r1
        merged_any = True
        
        while merged_any:
            merged_any = False
            for j, r2 in enumerate(regions):
                if j in used or j == i:
                    continue
                
                iou = _calculate_iou(current.bbox, r2.bbox)
                if iou >= threshold:
                    current = _merge_two_regions(current, r2)
                    used.add(j)
                    merged_any = True
        
        merged.append(current)
        used.add(i)
    
    return merged


def _sort_regions_by_position(regions: List[DetectedRegion]) -> List[DetectedRegion]:
    """
    Sort regions by position: top-to-bottom, left-to-right, then by area descending.
    
    This ensures deterministic ordering across runs.
    """
    # Sort by: y-coordinate (top to bottom), x-coordinate (left to right), area (largest first)
    return sorted(regions, key=lambda r: (r.bbox[1], r.bbox[0], -r.area))
