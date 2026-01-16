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
    
    # SOURCE A (PRIMARY): Rendered page figures with text masking
    logger.info("Source A: Extracting rendered page figures...")
    
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
        
        # Convert accepted figures to components
        for figure in figures:
            if figure.rejection_reason is not None:
                # Track rejected figures in role distribution
                role_distribution[figure.image_role] = role_distribution.get(figure.image_role, 0) + 1
                continue
            
            component = MobiusComponent(
                component_id=f"rendered_p{page_index}_f{figure.figure_index}",
                source_type="rendered_page",
                source_image_id=f"p{page_index}_f{figure.figure_index}",
                image_role=figure.image_role,
                source_bbox=figure.bbox_pdf,
                image_data=figure.image_data,
                width=figure.bbox_pixels[2],
                height=figure.bbox_pixels[3],
                page_index=page_index,
                width_ratio=figure.width_ratio,
                height_ratio=figure.height_ratio,
                text_overlap_ratio=figure.text_overlap_ratio,
                component_likeness_score=figure.component_likeness_score,
                stddev_luma=figure.stddev_luma,
                edge_density=figure.edge_density,
                rank_within_page=figure.rank_within_page
            )
            component.compute_content_hash()
            components.append(component)
            source_distribution["rendered_page"] += 1
            role_distribution["component_atomic"] = role_distribution.get("component_atomic", 0) + 1
    
    logger.info(f"Source A: extracted {source_distribution['rendered_page']} rendered figures ({len(all_figures)} total candidates)")
    
    # Log rejection summary
    rejection_counts = {}
    for fig in all_figures:
        if fig.rejection_reason:
            reason_key = fig.rejection_reason.split('_')[0] if '_' in fig.rejection_reason else fig.rejection_reason[:20]
            rejection_counts[reason_key] = rejection_counts.get(reason_key, 0) + 1
    if rejection_counts:
        logger.info(f"Source A rejection summary: {rejection_counts}")
    
    # SOURCE B (SECONDARY): Embedded images with corrected role classification
    logger.info("Source B: Extracting embedded images...")
    embedded_images = extract_embedded_images(doc, min_width=min_width, min_height=min_height)
    
    logger.info(f"Source B: found {len(embedded_images)} embedded images")
    
    for img in embedded_images:
        # Get page dimensions for ratio-based classification
        page = doc._doc[img.page_index]
        page_width = page.rect.width
        page_height = page.rect.height
        
        # Convert pixmap to numpy array
        import fitz
        if img.pixmap.n < 4:  # RGB or grayscale
            image_data = np.frombuffer(img.pixmap.samples, dtype=np.uint8).reshape(img.pixmap.height, img.pixmap.width, img.pixmap.n)
        else:  # RGBA - convert to RGB
            rgba = np.frombuffer(img.pixmap.samples, dtype=np.uint8).reshape(img.pixmap.height, img.pixmap.width, img.pixmap.n)
            image_data = rgba[:, :, :3]  # Drop alpha channel
        
        # Classify image role with page dimensions
        classification = classify_image_role(
            img.pixmap,
            img.width,
            img.height,
            img.page_index,
            0,  # image_index not available in ExtractedImage
            page_width=page_width,
            page_height=page_height,
            bbox=img.bbox
        )
        
        role = classification.role
        role_str = role.value
        
        # Track role distribution
        role_distribution[role_str] = role_distribution.get(role_str, 0) + 1
        images_by_role[role_str] = images_by_role.get(role_str, 0) + 1
        
        logger.debug(f"Image {img.id}: role={role_str}, rationale={classification.rationale}")
        
        # Process based on role
        if role == ImageRole.COMPONENT_ATOMIC:
            # Export whole, never crop
            component = MobiusComponent(
                component_id=f"embedded_{img.id}",
                source_type="embedded",
                source_image_id=img.id,
                image_role=role_str,
                source_bbox=img.bbox,
                image_data=image_data,
                width=img.width,
                height=img.height,
                page_index=img.page_index
            )
            component.compute_content_hash()
            components.append(component)
            source_distribution["embedded"] += 1
            
        elif role == ImageRole.COMPONENT_SHEET:
            # Segment into multiple atomic components
            logger.info(f"Segmenting component sheet: {img.id}")
            segments = segment_component_sheet(image_data, img.id)
            
            for segment in segments:
                component = MobiusComponent(
                    component_id=f"sheet_{img.id}_seg{segment.segment_index}",
                    source_type="embedded",
                    source_image_id=img.id,
                    sheet_id=img.id,
                    component_bbox_in_sheet=segment.bbox,
                    image_role="component_atomic",  # Segments become atomic
                    source_bbox=img.bbox,
                    image_data=segment.image_data,
                    width=segment.bbox[2],
                    height=segment.bbox[3],
                    page_index=img.page_index
                )
                component.compute_content_hash()
                components.append(component)
                source_distribution["embedded"] += 1
        
        elif role == ImageRole.ILLUSTRATION:
            # Ignore by default
            logger.debug(f"Ignoring illustration: {img.id}")
            
        elif role == ImageRole.DIAGRAM:
            # Ignore
            logger.debug(f"Ignoring diagram: {img.id}")
            
        elif role == ImageRole.ART:
            # Ignore (full-page art/backgrounds)
            logger.debug(f"Ignoring art: {img.id}")
    
    logger.info(f"Source B: extracted {source_distribution['embedded']} embedded components")
    logger.info(f"MOBIUS extraction complete: {len(components)} total components")
    logger.info(f"Source distribution: {source_distribution}")
    logger.info(f"Role distribution: {role_distribution}")
    
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
