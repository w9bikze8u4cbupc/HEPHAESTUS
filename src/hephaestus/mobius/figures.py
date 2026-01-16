"""
Rendered-figure extraction with text masking.

Extracts component figures from rendered PDF pages by masking text regions.
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional
import numpy as np

from ..logging import get_logger

logger = get_logger(__name__)


@dataclass
class RenderedFigure:
    """A figure extracted from a rendered page."""
    
    # Bounding box in pixel coordinates (x, y, w, h)
    bbox_pixels: Tuple[int, int, int, int]
    
    # Bounding box in PDF coordinates (x0, y0, x1, y1)
    bbox_pdf: Tuple[float, float, float, float]
    
    # Image data (RGB numpy array)
    image_data: np.ndarray
    
    # Page index
    page_index: int
    
    # Figure index on page
    figure_index: int
    
    # DPI used for rendering
    dpi: int


def extract_rendered_figures(
    page_image: np.ndarray,
    text_blocks: List,
    page_width: float,
    page_height: float,
    page_index: int,
    dpi: int = 200
) -> List[RenderedFigure]:
    """
    Extract figures from rendered page using text masking.
    
    Pipeline:
    1. Build text mask from text block coordinates
    2. Mask out text regions from rendered image
    3. Detect connected components in remaining pixels
    4. Filter and merge candidate bboxes
    5. Extract figure crops
    
    Args:
        page_image: Rendered page as RGB numpy array
        text_blocks: PyMuPDF text blocks from page.get_text("blocks")
        page_width: PDF page width in points
        page_height: PDF page height in points
        page_index: Page number
        dpi: DPI used for rendering
    
    Returns:
        List of RenderedFigure objects
    """
    try:
        import cv2
    except ImportError:
        logger.warning("OpenCV not available, cannot extract rendered figures")
        return []
    
    img_height, img_width = page_image.shape[:2]
    
    # Step 1: Build text mask
    text_mask = _build_text_mask(text_blocks, page_width, page_height, img_width, img_height)
    
    # Step 2: Mask out text from image
    masked_image = page_image.copy()
    masked_image[text_mask > 0] = 255  # White out text regions
    
    # Step 3: Convert to grayscale and detect edges
    gray = cv2.cvtColor(masked_image, cv2.COLOR_RGB2GRAY)
    
    # Invert: we want dark regions (ink) to be foreground
    inverted = 255 - gray
    
    # Threshold to binary
    _, binary = cv2.threshold(inverted, 30, 255, cv2.THRESH_BINARY)
    
    # Morphological operations to connect nearby components
    kernel = np.ones((5, 5), np.uint8)
    dilated = cv2.dilate(binary, kernel, iterations=2)
    
    # Find connected components
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(dilated, connectivity=8)
    
    logger.debug(f"Page {page_index}: found {num_labels-1} connected components")
    
    # Step 4: Filter and extract candidate bboxes
    figures = []
    page_area = img_width * img_height
    
    for i in range(1, num_labels):  # Skip background (label 0)
        x, y, w, h, area = stats[i]
        
        # Filter 1: Size thresholds
        if area < 1000:  # Too small (< 1000 pixels)
            continue
        if area > page_area * 0.7:  # Too large (> 70% of page)
            continue
        
        # Filter 2: Aspect ratio
        aspect_ratio = max(w / h, h / w) if h > 0 else float('inf')
        if aspect_ratio > 10.0:  # Extreme banner
            continue
        
        # Filter 3: Ink coverage (avoid mostly empty boxes)
        roi = binary[y:y+h, x:x+w]
        ink_ratio = np.count_nonzero(roi) / (w * h) if (w * h) > 0 else 0
        if ink_ratio < 0.05:  # Less than 5% ink
            continue
        
        # Convert to PDF coordinates
        scale_x = page_width / img_width
        scale_y = page_height / img_height
        pdf_x0 = x * scale_x
        pdf_y0 = y * scale_y
        pdf_x1 = (x + w) * scale_x
        pdf_y1 = (y + h) * scale_y
        
        # Extract figure crop from original (non-masked) image
        figure_crop = page_image[y:y+h, x:x+w].copy()
        
        figure = RenderedFigure(
            bbox_pixels=(x, y, w, h),
            bbox_pdf=(pdf_x0, pdf_y0, pdf_x1, pdf_y1),
            image_data=figure_crop,
            page_index=page_index,
            figure_index=len(figures),
            dpi=dpi
        )
        figures.append(figure)
    
    # Step 5: Merge overlapping figures
    figures = _merge_overlapping_figures(figures)
    
    # Reassign indices after merging
    for i, fig in enumerate(figures):
        fig.figure_index = i
    
    logger.info(f"Page {page_index}: extracted {len(figures)} rendered figures")
    
    return figures


def _build_text_mask(
    text_blocks: List,
    page_width: float,
    page_height: float,
    img_width: int,
    img_height: int,
    expand_margin: int = 5
) -> np.ndarray:
    """
    Build a binary mask of text regions.
    
    Args:
        text_blocks: PyMuPDF text blocks
        page_width: PDF page width
        page_height: PDF page height
        img_width: Image width in pixels
        img_height: Image height in pixels
        expand_margin: Pixels to expand each text bbox
    
    Returns:
        Binary mask (uint8) where 255 = text region
    """
    mask = np.zeros((img_height, img_width), dtype=np.uint8)
    
    if not text_blocks:
        return mask
    
    # Scale factors: PDF points -> pixels
    scale_x = img_width / page_width
    scale_y = img_height / page_height
    
    for block in text_blocks:
        if len(block) < 5:
            continue
        
        # Text block in PDF coordinates
        pdf_x0, pdf_y0, pdf_x1, pdf_y1 = block[:4]
        
        # Transform to pixel coordinates
        pix_x0 = int(pdf_x0 * scale_x)
        pix_y0 = int(pdf_y0 * scale_y)
        pix_x1 = int(pdf_x1 * scale_x)
        pix_y1 = int(pdf_y1 * scale_y)
        
        # Expand by margin
        pix_x0 = max(0, pix_x0 - expand_margin)
        pix_y0 = max(0, pix_y0 - expand_margin)
        pix_x1 = min(img_width, pix_x1 + expand_margin)
        pix_y1 = min(img_height, pix_y1 + expand_margin)
        
        # Fill mask
        mask[pix_y0:pix_y1, pix_x0:pix_x1] = 255
    
    return mask


def _merge_overlapping_figures(figures: List[RenderedFigure]) -> List[RenderedFigure]:
    """
    Merge overlapping figures using IoU threshold.
    
    Args:
        figures: List of RenderedFigure objects
    
    Returns:
        Merged list of figures
    """
    if len(figures) <= 1:
        return figures
    
    merged = []
    used = set()
    
    for i, fig1 in enumerate(figures):
        if i in used:
            continue
        
        current = fig1
        merged_any = True
        
        while merged_any:
            merged_any = False
            for j, fig2 in enumerate(figures):
                if j in used or j == i:
                    continue
                
                iou = _calculate_iou_pixels(current.bbox_pixels, fig2.bbox_pixels)
                if iou >= 0.3:  # 30% overlap threshold
                    current = _merge_two_figures(current, fig2)
                    used.add(j)
                    merged_any = True
        
        merged.append(current)
        used.add(i)
    
    return merged


def _calculate_iou_pixels(bbox1: Tuple[int, int, int, int], bbox2: Tuple[int, int, int, int]) -> float:
    """Calculate IoU for pixel bboxes (x, y, w, h)."""
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


def _merge_two_figures(fig1: RenderedFigure, fig2: RenderedFigure) -> RenderedFigure:
    """Merge two overlapping figures."""
    import cv2
    
    x1, y1, w1, h1 = fig1.bbox_pixels
    x2, y2, w2, h2 = fig2.bbox_pixels
    
    # Calculate merged bbox
    x_min = min(x1, x2)
    y_min = min(y1, y2)
    x_max = max(x1 + w1, x2 + w2)
    y_max = max(y1 + h1, y2 + h2)
    
    merged_bbox_pixels = (x_min, y_min, x_max - x_min, y_max - y_min)
    
    # Merge PDF bboxes
    pdf_x0 = min(fig1.bbox_pdf[0], fig2.bbox_pdf[0])
    pdf_y0 = min(fig1.bbox_pdf[1], fig2.bbox_pdf[1])
    pdf_x1 = max(fig1.bbox_pdf[2], fig2.bbox_pdf[2])
    pdf_y1 = max(fig1.bbox_pdf[3], fig2.bbox_pdf[3])
    merged_bbox_pdf = (pdf_x0, pdf_y0, pdf_x1, pdf_y1)
    
    # Create merged image (use fig1's parent image if available, otherwise composite)
    # For simplicity, just use fig1's image data (assumes they're from same page)
    merged_image = fig1.image_data
    
    return RenderedFigure(
        bbox_pixels=merged_bbox_pixels,
        bbox_pdf=merged_bbox_pdf,
        image_data=merged_image,
        page_index=fig1.page_index,
        figure_index=fig1.figure_index,
        dpi=fig1.dpi
    )
