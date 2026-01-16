"""
MOBIUS-mode component extraction.

Extracts components using image-role classification and sheet segmentation.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Tuple
import hashlib
import numpy as np

from ..pdf.ingestion import PdfDocument
from ..pdf.images import extract_embedded_images
from ..logging import get_logger

logger = get_logger(__name__)


@dataclass
class MobiusComponent:
    """A component extracted in MOBIUS mode."""
    
    # Unique identifier
    component_id: str
    
    # Source information
    source_type: str  # "embedded" or "rendered_page"
    source_image_id: str  # Original image ID from PDF
    
    # Sheet information (if derived from sheet)
    sheet_id: Optional[str] = None
    component_bbox_in_sheet: Optional[Tuple[int, int, int, int]] = None
    
    # Image role
    image_role: str = "component_atomic"
    
    # Bounding box in PDF coordinates (x0, y0, x1, y1) - for source image
    source_bbox: Optional[Tuple[float, float, float, float]] = None
    
    # Image data (RGB numpy array)
    image_data: "np.ndarray" = None
    
    # Dimensions
    width: int = 0
    height: int = 0
    
    # Page index
    page_index: int = 0
    
    # Component match (from MOBIUS vocabulary, if provided)
    component_match: Optional[str] = None
    match_score: float = 0.0
    
    # Deterministic hash of image content
    content_hash: Optional[str] = None
    
    # G4 metrics (for rendered figures)
    width_ratio: float = 0.0
    height_ratio: float = 0.0
    text_overlap_ratio: float = 0.0
    component_likeness_score: float = 0.0
    stddev_luma: float = 0.0
    edge_density: float = 0.0
    rank_within_page: int = 0
    rejection_reason: Optional[str] = None
    
    # G6 metrics
    bbox_width_in: float = 0.0  # Physical width in inches
    bbox_height_in: float = 0.0  # Physical height in inches
    uniformity_ratio: float = 0.0  # Near-uniform metric
    render_dpi_used: int = 0  # Actual DPI used for clip render
    
    # Rejection reason (G3.2, if rejected)
    rejection_reason: Optional[str] = None
    
    def compute_content_hash(self) -> str:
        """Compute deterministic hash of image content."""
        import numpy as np
        # Use tobytes() for deterministic byte representation
        content_bytes = self.image_data.tobytes()
        hash_obj = hashlib.sha256(content_bytes)
        self.content_hash = hash_obj.hexdigest()[:16]  # First 16 chars
        return self.content_hash


@dataclass
class MobiusExtractionResult:
    """Result of MOBIUS-mode extraction."""
    
    # All extracted components
    components: List[MobiusComponent]
    
    # Total pages processed
    pages_processed: int
    
    # Image role distribution
    role_distribution: Dict[str, int]
    
    # Total embedded images found
    total_embedded_images: int
    
    # Images by role
    images_by_role: Dict[str, int]


def extract_mobius_components(
    doc: PdfDocument,
    component_vocabulary: Optional["ComponentVocabulary"] = None,
    min_width: int = 50,
    min_height: int = 50,
    render_dpi: int = 400
) -> MobiusExtractionResult:
    """
    Extract components using two-source MOBIUS extraction.
    
    Pipeline:
    Source A (Primary): Rendered page figures with text masking
    Source B (Secondary): Embedded images with role classification
    
    Args:
        doc: PDF document to process
        component_vocabulary: Optional component vocabulary for matching
        min_width: Minimum image width for extraction
        min_height: Minimum image height for extraction
        render_dpi: DPI for page rendering (Source A)
    
    Returns:
        MobiusExtractionResult with all extracted components
    """
    from .roles import classify_image_role, ImageRole
    from .sheets import segment_component_sheet
    from .figures import extract_rendered_figures
    from ..regions.rendering import render_page_to_image
    
    logger.info(f"Starting MOBIUS extraction (two-source): {doc.page_count} pages")
    
    components = []
    role_distribution = {}
    images_by_role = {}
    source_distribution = {"rendered_page": 0, "embedded": 0}
    
    # G5.3: Track candidates and rejections separately
    candidates_total = 0
    rejected_total = 0
    rejection_reasons = {}
    
    # SOURCE A (PRIMARY): Rendered page figures with text masking
    logger.info("Source A: Extracting rendered page figures...")
    
    # First, extract all embedded images for G5.4 comparison
    logger.info("Pre-extracting embedded images for fidelity comparison...")
    embedded_images = extract_embedded_images(doc, min_width=min_width, min_height=min_height)
    logger.info(f"Found {len(embedded_images)} embedded images")
    
    # Build embedded image lookup by page
    embedded_by_page = {}
    for img in embedded_images:
        if img.page_index not in embedded_by_page:
            embedded_by_page[img.page_index] = []
        embedded_by_page[img.page_index].append(img)
    
    all_figures = []  # Track all figures (accepted + rejected)
    
    for page_index in range(doc.page_count):
        page = doc._doc[page_index]
        
        # Render page at 400 DPI (G4.5)
        page_image = render_page_to_image(page, dpi=render_dpi)
        
        # Extract text blocks for masking and overlap computation
        text_blocks = page.get_text("blocks")
        
        # Extract figures (includes rejected with rejection_reason)
        figures = extract_rendered_figures(
            page_image,
            text_blocks,
            page.rect.width,
            page.rect.height,
            page_index,
            dpi=render_dpi
        )
        
        all_figures.extend(figures)
        candidates_total += len(figures)
        
        # Convert accepted figures to components
        for figure in figures:
            if figure.rejection_reason is not None:
                # G5.3: Track rejections
                rejected_total += 1
                reason_key = figure.rejection_reason.split('_')[0] if '_' in figure.rejection_reason else figure.rejection_reason[:20]
                rejection_reasons[reason_key] = rejection_reasons.get(reason_key, 0) + 1
                # Track rejected role
                role_distribution[figure.image_role] = role_distribution.get(figure.image_role, 0) + 1
                continue
            
            # G6.2: Mandatory clip re-render for every accepted component
            from .figures import render_bbox_clip_high_fidelity
            
            clip_image, clip_dpi = render_bbox_clip_high_fidelity(page, figure.bbox_pdf, target_dpi=600)
            figure.render_dpi_used = clip_dpi
            
            # G6.5: Prefer embedded images when they are truly higher fidelity
            best_image_data = clip_image
            best_source_type = "rendered_page"
            best_source_id = f"p{page_index}_f{figure.figure_index}"
            
            page_embedded = embedded_by_page.get(page_index, [])
            for emb_img in page_embedded:
                # Compute IoU between rendered figure and embedded image (PDF space)
                iou = _compute_bbox_iou_pdf(figure.bbox_pdf, emb_img.bbox)
                
                if iou >= 0.6:
                    # G6.5: Compute effective DPI for embedded vs clip-render
                    # Embedded effective DPI = embedded_px / bbox_in
                    emb_bbox_width_pt = emb_img.bbox.x1 - emb_img.bbox.x0
                    emb_bbox_height_pt = emb_img.bbox.y1 - emb_img.bbox.y0
                    emb_bbox_width_in = emb_bbox_width_pt / 72.0
                    emb_bbox_height_in = emb_bbox_height_pt / 72.0
                    
                    embedded_dpi_w = emb_img.width / emb_bbox_width_in if emb_bbox_width_in > 0 else 0
                    embedded_dpi_h = emb_img.height / emb_bbox_height_in if emb_bbox_height_in > 0 else 0
                    embedded_effective_dpi = min(embedded_dpi_w, embedded_dpi_h)
                    
                    # Prefer embedded only if meaningfully higher fidelity
                    if embedded_effective_dpi >= clip_dpi * 1.15:
                        # Use embedded image instead
                        import fitz
                        if emb_img.pixmap.n < 4:  # RGB or grayscale
                            best_image_data = np.frombuffer(emb_img.pixmap.samples, dtype=np.uint8).reshape(
                                emb_img.pixmap.height, emb_img.pixmap.width, emb_img.pixmap.n
                            )
                        else:  # RGBA - convert to RGB
                            rgba = np.frombuffer(emb_img.pixmap.samples, dtype=np.uint8).reshape(
                                emb_img.pixmap.height, emb_img.pixmap.width, emb_img.pixmap.n
                            )
                            best_image_data = rgba[:, :, :3]  # Drop alpha channel
                        
                        best_source_type = "embedded_preferred"
                        best_source_id = emb_img.id
                        logger.debug(f"Using embedded image {emb_img.id} instead of clip-render (IoU={iou:.2f}, embedded_dpi={embedded_effective_dpi:.0f} > clip_dpi={clip_dpi}*1.15)")
                        break
            
            component = MobiusComponent(
                component_id=f"rendered_p{page_index}_f{figure.figure_index}",
                source_type=best_source_type,
                source_image_id=best_source_id,
                image_role=figure.image_role,
                source_bbox=figure.bbox_pdf,
                image_data=best_image_data,
                width=best_image_data.shape[1] if len(best_image_data.shape) >= 2 else figure.bbox_pixels[2],
                height=best_image_data.shape[0] if len(best_image_data.shape) >= 1 else figure.bbox_pixels[3],
                page_index=page_index,
                bbox_width_in=figure.bbox_width_in,
                bbox_height_in=figure.bbox_height_in,
                width_ratio=figure.width_ratio,
                height_ratio=figure.height_ratio,
                text_overlap_ratio=figure.text_overlap_ratio,
                component_likeness_score=figure.component_likeness_score,
                stddev_luma=figure.stddev_luma,
                edge_density=figure.edge_density,
                uniformity_ratio=figure.uniformity_ratio,
                render_dpi_used=figure.render_dpi_used,
                rank_within_page=figure.rank_within_page
            )
            component.compute_content_hash()
            components.append(component)
            source_distribution[best_source_type] = source_distribution.get(best_source_type, 0) + 1
            role_distribution["component_atomic"] = role_distribution.get("component_atomic", 0) + 1
    
    # G5.3: Log accurate accounting
    logger.info(f"Source A: {len(components)} accepted, {rejected_total} rejected ({candidates_total} total candidates)")
    logger.info(f"Source A rejection summary: {rejection_reasons}")
    
    # SOURCE B: Already processed in G5.4 (embedded images used for fidelity comparison)
    # Track embedded images in role distribution for reporting
    for img in embedded_images:
        page = doc._doc[img.page_index]
        page_width = page.rect.width
        page_height = page.rect.height
        
        # Classify for reporting only
        classification = classify_image_role(
            img.pixmap,
            img.width,
            img.height,
            img.page_index,
            0,
            page_width=page_width,
            page_height=page_height,
            bbox=img.bbox
        )
        
        images_by_role[classification.role.value] = images_by_role.get(classification.role.value, 0) + 1
    
    # G5.3: Final accounting
    logger.info(f"MOBIUS extraction complete: {len(components)} components exported")
    logger.info(f"Source distribution: {source_distribution}")
    logger.info(f"Candidates: {candidates_total} total, {len(components)} accepted, {rejected_total} rejected")
    logger.info(f"Role distribution (all candidates): {role_distribution}")
    
    return MobiusExtractionResult(
        components=components,
        pages_processed=doc.page_count,
        role_distribution=role_distribution,
        total_embedded_images=len(embedded_images),
        images_by_role=images_by_role
    )


def save_mobius_components(
    components: List[MobiusComponent],
    output_dir: Path,
    rulebook_id: str
) -> Dict[str, Path]:
    """
    Save MOBIUS components to disk with deterministic naming.
    
    Naming convention: <rulebook>__<component_id>.png
    
    Args:
        components: List of components to save
        output_dir: Output directory
        rulebook_id: Rulebook identifier
    
    Returns:
        Mapping of component_id to saved file path
    """
    import cv2
    
    output_dir = Path(output_dir)
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    
    path_mapping = {}
    
    for component in components:
        # Build filename
        filename = f"{rulebook_id}__{component.component_id}.png"
        filepath = images_dir / filename
        
        # Convert RGB to BGR for OpenCV
        bgr_image = cv2.cvtColor(component.image_data, cv2.COLOR_RGB2BGR)
        
        # Save with deterministic PNG settings
        cv2.imwrite(str(filepath), bgr_image, [cv2.IMWRITE_PNG_COMPRESSION, 6])
        
        path_mapping[component.component_id] = filepath
        logger.debug(f"Saved component {component.component_id} to {filepath}")
    
    logger.info(f"Saved {len(components)} MOBIUS components to {images_dir}")
    
    return path_mapping


def _compute_bbox_iou_pdf(bbox1: Tuple[float, float, float, float], bbox2) -> float:
    """
    Compute IoU between two bboxes in PDF coordinate space.
    
    Args:
        bbox1: Tuple (x0, y0, x1, y1) in PDF coordinates
        bbox2: BBox object or tuple (x0, y0, x1, y1) in PDF coordinates
    
    Returns:
        IoU ratio (0.0-1.0)
    """
    # Handle BBox object
    if hasattr(bbox2, 'x0'):
        x2_0, y2_0, x2_1, y2_1 = bbox2.x0, bbox2.y0, bbox2.x1, bbox2.y1
    else:
        x2_0, y2_0, x2_1, y2_1 = bbox2
    
    x1_0, y1_0, x1_1, y1_1 = bbox1
    
    # Compute intersection
    inter_x0 = max(x1_0, x2_0)
    inter_y0 = max(y1_0, y2_0)
    inter_x1 = min(x1_1, x2_1)
    inter_y1 = min(y1_1, y2_1)
    
    if inter_x1 <= inter_x0 or inter_y1 <= inter_y0:
        return 0.0
    
    inter_area = (inter_x1 - inter_x0) * (inter_y1 - inter_y0)
    
    # Compute union
    area1 = (x1_1 - x1_0) * (y1_1 - y1_0)
    area2 = (x2_1 - x2_0) * (y2_1 - y2_0)
    union = area1 + area2 - inter_area
    
    if union <= 0:
        return 0.0
    
    return inter_area / union
