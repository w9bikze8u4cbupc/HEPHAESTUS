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
    
    # G6.1: PDF-space (physical) measurements
    bbox_width_in: float = 0.0  # Width in inches
    bbox_height_in: float = 0.0  # Height in inches
    bbox_area_in2: float = 0.0  # Area in square inches
    
    # Page coverage ratios (for role classification)
    width_ratio: float = 0.0
    height_ratio: float = 0.0
    
    # Text overlap ratio (for text panel rejection)
    text_overlap_ratio: float = 0.0
    
    # Quality metrics
    component_likeness_score: float = 0.0
    stddev_luma: float = 0.0
    edge_density: float = 0.0
    uniformity_ratio: float = 0.0  # G6.3: Near-uniform metric
    
    # G6.2: Clip re-render metadata
    render_dpi_used: int = 0  # Actual DPI used for clip render
    
    # G7.2: Size tier classification
    size_tier: str = "MID"  # BOARD, MID, or ICON
    
    # G7.3: Raster upscale detection
    raster_upscale_suspect: bool = False
    render_info_gain: float = 0.0  # Information gain from low to high DPI
    
    # Classification
    image_role: str = "component_atomic"
    rejection_reason: Optional[str] = None
    rank_within_page: int = 0


def extract_rendered_figures(
    page_image: np.ndarray,
    text_blocks: List,
    page_width: float,
    page_height: float,
    page_index: int,
    dpi: int = 400
) -> List[RenderedFigure]:
    """
    Extract figures from rendered page using text masking.
    
    Pipeline (Order G4):
    1. Build text mask from text block coordinates
    2. Mask out text regions from rendered image
    3. Detect connected components in remaining pixels
    4. Filter and merge candidate bboxes
    5. Compute quality metrics and text overlap
    6. Apply rejection gates (page coverage, text overlap, low-information)
    7. Rank remaining candidates
    8. Extract figure crops
    
    Args:
        page_image: Rendered page as RGB numpy array
        text_blocks: PyMuPDF text blocks from page.get_text("blocks")
        page_width: PDF page width in points
        page_height: PDF page height in points
        page_index: Page number
        dpi: DPI used for rendering
    
    Returns:
        List of RenderedFigure objects (includes rejected figures with rejection_reason)
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
    
    # Step 4: Extract candidate bboxes with basic geometric filtering
    candidates = []
    page_area = img_width * img_height
    
    for i in range(1, num_labels):  # Skip background (label 0)
        x, y, w, h, area = stats[i]
        
        # Filter 1: Size thresholds (basic sanity)
        if area < 1000:  # Too small (< 1000 pixels)
            continue
        if area > page_area * 0.95:  # Too large (> 95% of page - likely full page)
            continue
        
        # Filter 2: Aspect ratio (basic sanity)
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
        
        # Extract figure crop from original (non-masked) image - NO RESIZING (G4.5)
        figure_crop = page_image[y:y+h, x:x+w].copy()
        
        figure = RenderedFigure(
            bbox_pixels=(x, y, w, h),
            bbox_pdf=(pdf_x0, pdf_y0, pdf_x1, pdf_y1),
            image_data=figure_crop,
            page_index=page_index,
            figure_index=len(candidates),
            dpi=dpi
        )
        candidates.append(figure)
    
    # Step 5: Merge overlapping figures
    candidates = _merge_overlapping_figures(candidates)
    
    # Step 6: Compute metrics and apply rejection gates
    figures = []
    for i, fig in enumerate(candidates):
        fig.figure_index = i
        
        # G6.1: Compute PDF-space (physical) measurements
        bbox_width_pt = fig.bbox_pdf[2] - fig.bbox_pdf[0]
        bbox_height_pt = fig.bbox_pdf[3] - fig.bbox_pdf[1]
        fig.bbox_width_in = bbox_width_pt / 72.0  # 72 points = 1 inch
        fig.bbox_height_in = bbox_height_pt / 72.0
        fig.bbox_area_in2 = fig.bbox_width_in * fig.bbox_height_in
        
        # Compute page coverage ratios
        bbox_w = fig.bbox_pixels[2]
        bbox_h = fig.bbox_pixels[3]
        fig.width_ratio = bbox_w / img_width
        fig.height_ratio = bbox_h / img_height
        
        # G7.2: Size-tiered role classification
        fig.size_tier = _classify_size_tier(fig.bbox_width_in, fig.bbox_height_in, fig.width_ratio, fig.height_ratio)
        
        # G7.2: Apply tier-specific size gates
        if fig.size_tier == "ICON":
            # ICON tier: relaxed gates for small tokens (recall priority)
            min_bbox_in = 0.22  # Minimum 0.22 inches (was 0.30)
            min_bbox_area_in2 = 0.048  # 0.22 × 0.22 (was 0.09)
        elif fig.size_tier == "MID":
            # MID tier: moderate gates for cards/tiles
            min_bbox_in = 0.23  # Minimum 0.23 inches (was 0.25)
            min_bbox_area_in2 = 0.053  # 0.23 × 0.23 (was 0.0625)
        else:  # BOARD
            # BOARD tier: relaxed gates for large structured components
            min_bbox_in = 0.20  # Minimum 0.20 inches
            min_bbox_area_in2 = 0.04  # 0.20 × 0.20
        
        if fig.bbox_width_in < min_bbox_in or fig.bbox_height_in < min_bbox_in:
            fig.rejection_reason = f"too_small_{fig.size_tier}_w{fig.bbox_width_in:.2f}in_h{fig.bbox_height_in:.2f}in_min{min_bbox_in}in"
            figures.append(fig)
            continue
        
        if fig.bbox_area_in2 < min_bbox_area_in2:
            fig.rejection_reason = f"too_small_{fig.size_tier}_area_{fig.bbox_area_in2:.3f}in2_min{min_bbox_area_in2}in2"
            figures.append(fig)
            continue
        
        # G4.1: Apply page-relative role classification
        if fig.width_ratio >= 0.80 and fig.height_ratio >= 0.80:
            fig.image_role = "art"
            fig.rejection_reason = f"full_page_coverage_w{fig.width_ratio:.2f}_h{fig.height_ratio:.2f}"
            figures.append(fig)
            continue
        elif fig.width_ratio >= 0.60 and fig.height_ratio >= 0.60:
            fig.image_role = "illustration"
            fig.rejection_reason = f"large_page_coverage_w{fig.width_ratio:.2f}_h{fig.height_ratio:.2f}"
            figures.append(fig)
            continue
        
        # G5.2: Page-relative "component band" gate (secondary to physical size)
        # Reject micro-fragments
        if fig.width_ratio < 0.03 and fig.height_ratio < 0.03:
            fig.rejection_reason = f"micro_fragment_w{fig.width_ratio:.3f}_h{fig.height_ratio:.3f}"
            figures.append(fig)
            continue
        
        # Reject near-full-page
        if fig.width_ratio > 0.85 and fig.height_ratio > 0.85:
            fig.rejection_reason = f"near_full_page_w{fig.width_ratio:.2f}_h{fig.height_ratio:.2f}"
            figures.append(fig)
            continue
        
        # G4.2: Compute text overlap ratio
        fig.text_overlap_ratio = _compute_text_overlap_ratio(
            fig.bbox_pdf, text_blocks, page_width, page_height
        )
        
        # G4.2: Hard reject text panels
        if fig.text_overlap_ratio >= 0.08:
            fig.rejection_reason = f"text_panel_overlap{fig.text_overlap_ratio:.3f}"
            figures.append(fig)
            continue
        
        # G6.3: Compute quality metrics (including uniformity)
        fig.stddev_luma, fig.edge_density, fig.uniformity_ratio = _compute_quality_metrics_g6(fig.image_data)
        
        # G6.3: Strong background/texture rejection
        if fig.edge_density < 0.015 and fig.stddev_luma < 10 and fig.uniformity_ratio > 0.80:
            fig.rejection_reason = f"background_texture_edge{fig.edge_density:.4f}_std{fig.stddev_luma:.2f}_unif{fig.uniformity_ratio:.2f}"
            figures.append(fig)
            continue
        
        # G4.3: Compute component likeness score
        fig.component_likeness_score = _compute_component_likeness_score(fig)
        
        # Passed all gates - mark as component_atomic
        fig.image_role = "component_atomic"
        figures.append(fig)
    
    # G4.3: Rank within page (stable sort)
    # Sort by: (-score, x0, y0, width, height) for determinism
    accepted = [f for f in figures if f.rejection_reason is None]
    accepted.sort(key=lambda f: (
        -f.component_likeness_score,
        f.bbox_pdf[0],
        f.bbox_pdf[1],
        f.bbox_pixels[2],
        f.bbox_pixels[3]
    ))
    
    for rank, fig in enumerate(accepted):
        fig.rank_within_page = rank
    
    logger.info(f"Page {page_index}: {len(accepted)} accepted, {len(figures) - len(accepted)} rejected")
    
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


def _compute_text_overlap_ratio(
    bbox_pdf: Tuple[float, float, float, float],
    text_blocks: List,
    page_width: float,
    page_height: float
) -> float:
    """
    Compute text overlap ratio for a candidate bbox (G4.2).
    
    Args:
        bbox_pdf: Candidate bbox in PDF coordinates (x0, y0, x1, y1)
        text_blocks: PyMuPDF text blocks
        page_width: PDF page width
        page_height: PDF page height
    
    Returns:
        Text overlap ratio (0.0-1.0)
    """
    if not text_blocks:
        return 0.0
    
    cand_x0, cand_y0, cand_x1, cand_y1 = bbox_pdf
    cand_area = (cand_x1 - cand_x0) * (cand_y1 - cand_y0)
    
    if cand_area <= 0:
        return 0.0
    
    total_overlap = 0.0
    
    for block in text_blocks:
        if len(block) < 5:
            continue
        
        text_x0, text_y0, text_x1, text_y1 = block[:4]
        
        # Compute intersection
        inter_x0 = max(cand_x0, text_x0)
        inter_y0 = max(cand_y0, text_y0)
        inter_x1 = min(cand_x1, text_x1)
        inter_y1 = min(cand_y1, text_y1)
        
        if inter_x1 > inter_x0 and inter_y1 > inter_y0:
            inter_area = (inter_x1 - inter_x0) * (inter_y1 - inter_y0)
            total_overlap += inter_area
    
    overlap_ratio = total_overlap / cand_area
    return overlap_ratio


def _compute_quality_metrics_g6(image_data: np.ndarray) -> Tuple[float, float, float]:
    """
    Compute quality metrics for G6.3 background rejection.
    
    Args:
        image_data: RGB numpy array
    
    Returns:
        (stddev_luma, edge_density, uniformity_ratio)
    """
    try:
        import cv2
    except ImportError:
        return (0.0, 0.0, 0.0)
    
    # Convert to grayscale
    if len(image_data.shape) == 3:
        gray = cv2.cvtColor(image_data, cv2.COLOR_RGB2GRAY)
    else:
        gray = image_data
    
    # Compute luma standard deviation
    stddev_luma = float(np.std(gray))
    
    # Compute edge density
    edges = cv2.Canny(gray, 50, 150)
    edge_pixels = np.count_nonzero(edges)
    total_pixels = gray.shape[0] * gray.shape[1]
    edge_density = edge_pixels / total_pixels if total_pixels > 0 else 0.0
    
    # G6.3: Compute uniformity ratio (percentage of pixels near median)
    median_luma = np.median(gray)
    # Count pixels within tight band around median (±15 luma values)
    near_median = np.abs(gray - median_luma) <= 15
    uniformity_ratio = np.count_nonzero(near_median) / total_pixels if total_pixels > 0 else 0.0
    
    return (stddev_luma, edge_density, uniformity_ratio)


def render_bbox_clip_high_fidelity(
    page: "fitz.Page",
    bbox_pdf: Tuple[float, float, float, float],
    target_dpi: int = 600
) -> Tuple[np.ndarray, int]:
    """
    G6.2: Render a specific bbox region at high DPI using clip rendering.
    
    Args:
        page: PyMuPDF page object
        bbox_pdf: Bounding box in PDF coordinates (x0, y0, x1, y1)
        target_dpi: Target DPI for rendering (default 600, optionally 800 for very small)
    
    Returns:
        (image_data as RGB numpy array, actual_dpi_used)
    """
    import fitz
    
    # Compute bbox physical size
    bbox_width_pt = bbox_pdf[2] - bbox_pdf[0]
    bbox_height_pt = bbox_pdf[3] - bbox_pdf[1]
    bbox_width_in = bbox_width_pt / 72.0
    bbox_height_in = bbox_height_pt / 72.0
    
    # For very small bboxes, use higher DPI
    if bbox_width_in < 0.5 or bbox_height_in < 0.5:
        target_dpi = 800
    
    # Compute zoom factor
    zoom = target_dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    
    # Create clip rectangle
    clip = fitz.Rect(bbox_pdf)
    
    # Render with clipping at target DPI
    pix = page.get_pixmap(matrix=mat, clip=clip, colorspace=fitz.csRGB)
    
    # Convert to numpy array
    img = np.frombuffer(pix.samples, dtype=np.uint8)
    img = img.reshape(pix.height, pix.width, 3)
    
    # Verify quality floor: min dimension >= 400px
    min_dim = min(pix.width, pix.height)
    if min_dim < 400:
        # Increase DPI to meet quality floor
        required_zoom = 400 / min(bbox_width_pt, bbox_height_pt) * 72.0
        target_dpi = int(required_zoom)
        zoom = target_dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, clip=clip, colorspace=fitz.csRGB)
        img = np.frombuffer(pix.samples, dtype=np.uint8)
        img = img.reshape(pix.height, pix.width, 3)
    
    return (img, target_dpi)


def _classify_size_tier(bbox_width_in: float, bbox_height_in: float, width_ratio: float, height_ratio: float) -> str:
    """
    G7.2: Classify component into size tier (BOARD/MID/ICON).
    
    Args:
        bbox_width_in: Width in inches
        bbox_height_in: Height in inches
        width_ratio: Width ratio relative to page
        height_ratio: Height ratio relative to page
    
    Returns:
        Size tier: "BOARD", "MID", or "ICON"
    """
    # BOARD: Near full-page, structured components (game boards, large reference sheets)
    # Criteria: Large page coverage OR large physical size
    if (width_ratio >= 0.50 and height_ratio >= 0.50) or (bbox_width_in >= 4.0 and bbox_height_in >= 4.0):
        return "BOARD"
    
    # ICON: Small tokens, markers, icons
    # Criteria: Small physical size AND small page coverage
    if bbox_width_in < 1.0 and bbox_height_in < 1.0 and width_ratio < 0.15 and height_ratio < 0.15:
        return "ICON"
    
    # MID: Cards, tiles, medium components (default)
    return "MID"


def compute_render_information_gain(
    page: "fitz.Page",
    bbox_pdf: Tuple[float, float, float, float],
    low_dpi: int = 150,
    high_dpi: int = 600
) -> Tuple[float, bool]:
    """
    G7.3: Compute render information gain to detect raster-upscale suspects.
    
    Renders the same bbox at low and high DPI, then compares edge density.
    If high DPI doesn't add meaningful edges, the source is likely raster-upscaled.
    
    Args:
        page: PyMuPDF page object
        bbox_pdf: Bounding box in PDF coordinates
        low_dpi: Low DPI for baseline render (default 150)
        high_dpi: High DPI for comparison render (default 600)
    
    Returns:
        (info_gain, is_suspect) where:
        - info_gain: Ratio of edge_density_high / edge_density_low
        - is_suspect: True if info_gain < 1.3 (insufficient gain)
    """
    import fitz
    
    try:
        import cv2
    except ImportError:
        return (1.0, False)
    
    # Render at low DPI
    zoom_low = low_dpi / 72.0
    mat_low = fitz.Matrix(zoom_low, zoom_low)
    clip = fitz.Rect(bbox_pdf)
    pix_low = page.get_pixmap(matrix=mat_low, clip=clip, colorspace=fitz.csRGB)
    img_low = np.frombuffer(pix_low.samples, dtype=np.uint8).reshape(pix_low.height, pix_low.width, 3)
    
    # Render at high DPI
    zoom_high = high_dpi / 72.0
    mat_high = fitz.Matrix(zoom_high, zoom_high)
    pix_high = page.get_pixmap(matrix=mat_high, clip=clip, colorspace=fitz.csRGB)
    img_high = np.frombuffer(pix_high.samples, dtype=np.uint8).reshape(pix_high.height, pix_high.width, 3)
    
    # Compute edge density for both
    gray_low = cv2.cvtColor(img_low, cv2.COLOR_RGB2GRAY)
    gray_high = cv2.cvtColor(img_high, cv2.COLOR_RGB2GRAY)
    
    edges_low = cv2.Canny(gray_low, 50, 150)
    edges_high = cv2.Canny(gray_high, 50, 150)
    
    edge_density_low = np.count_nonzero(edges_low) / (gray_low.shape[0] * gray_low.shape[1])
    edge_density_high = np.count_nonzero(edges_high) / (gray_high.shape[0] * gray_high.shape[1])
    
    # Compute information gain
    if edge_density_low > 0:
        info_gain = edge_density_high / edge_density_low
    else:
        info_gain = 1.0 if edge_density_high == 0 else 2.0
    
    # Suspect if gain is less than 1.3x (insufficient detail added by higher DPI)
    is_suspect = info_gain < 1.3
    
    return (info_gain, is_suspect)


def _compute_component_likeness_score(fig: RenderedFigure) -> float:
    """
    Compute component likeness score for ranking (G4.3).
    
    Simple heuristic based on:
    - Size (prefer medium-sized components)
    - Aspect ratio (prefer reasonable ratios)
    - Edge density (prefer structured content)
    - Texture (prefer textured content)
    
    Args:
        fig: RenderedFigure
    
    Returns:
        Score (0.0-1.0, higher is better)
    """
    score = 0.0
    
    # Size score: prefer medium-sized components (10k-500k pixels)
    area = fig.bbox_pixels[2] * fig.bbox_pixels[3]
    if 10_000 <= area <= 500_000:
        score += 0.3
    elif 1_000 <= area < 10_000:
        score += 0.15
    
    # Aspect ratio score: prefer reasonable ratios (1:1 to 3:1)
    w, h = fig.bbox_pixels[2], fig.bbox_pixels[3]
    aspect_ratio = max(w / h, h / w) if h > 0 else 10.0
    if aspect_ratio <= 3.0:
        score += 0.3
    elif aspect_ratio <= 5.0:
        score += 0.15
    
    # Edge density score: prefer structured content
    if fig.edge_density >= 0.05:
        score += 0.2
    elif fig.edge_density >= 0.02:
        score += 0.1
    
    # Texture score: prefer textured content
    if fig.stddev_luma >= 20.0:
        score += 0.2
    elif fig.stddev_luma >= 10.0:
        score += 0.1
    
    return min(score, 1.0)


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
    
    # Use fig1's image data (assumes they're from same page)
    merged_image = fig1.image_data
    
    return RenderedFigure(
        bbox_pixels=merged_bbox_pixels,
        bbox_pdf=merged_bbox_pdf,
        image_data=merged_image,
        page_index=fig1.page_index,
        figure_index=fig1.figure_index,
        dpi=fig1.dpi
    )
