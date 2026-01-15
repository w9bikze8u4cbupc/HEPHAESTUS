"""
MOBIUS-mode component extraction.

Extracts individual component regions from PDF pages using region detection.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Tuple
import hashlib

from ..pdf.ingestion import PdfDocument
from ..regions.detection import detect_regions, RegionDetectionConfig, DetectedRegion
from ..regions.rendering import render_page_to_image
from ..text.spatial import extract_spatial_text
from ..text.index import SpatialTextIndex
from ..logging import get_logger

logger = get_logger(__name__)


@dataclass
class MobiusComponent:
    """A component extracted in MOBIUS mode."""
    
    # Unique identifier
    component_id: str
    
    # Source page
    page_index: int
    
    # Crop index on this page
    crop_index: int
    
    # Bounding box in PDF coordinates (x0, y0, x1, y1)
    bbox: Tuple[float, float, float, float]
    
    # Image data (RGB numpy array)
    image_data: "np.ndarray"
    
    # Dimensions
    width: int
    height: int
    
    # Confidence score from region detection
    confidence: float
    
    # Whether this is a grouped/composite component
    is_group: bool = False
    
    # Group metadata (if is_group=True)
    group_reason: Optional[str] = None
    group_members: Optional[List[str]] = None
    
    # Component match (from MOBIUS vocabulary, if provided)
    component_match: Optional[str] = None
    match_score: float = 0.0
    
    # Deterministic hash of image content
    content_hash: Optional[str] = None
    
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
    
    # Total regions detected (before filtering)
    regions_detected: int
    
    # Regions filtered out
    regions_filtered: int
    
    # Filtered regions with details (for manifest)
    filtered_regions_detail: List[Tuple[int, Tuple[float, float, float, float], str]]  # (page_idx, bbox, reason)
    
    # Configuration used
    config: RegionDetectionConfig


def extract_mobius_components(
    doc: PdfDocument,
    config: Optional[RegionDetectionConfig] = None,
    component_vocabulary: Optional["ComponentVocabulary"] = None,
    dpi: int = 150
) -> MobiusExtractionResult:
    """
    Extract components using MOBIUS-mode region detection.
    
    Args:
        doc: PDF document to process
        config: Region detection configuration (uses defaults if None)
        component_vocabulary: Optional component vocabulary for matching
        dpi: DPI for page rendering (default 150)
    
    Returns:
        MobiusExtractionResult with all extracted components and filtered regions
    """
    if config is None:
        config = RegionDetectionConfig()
    
    logger.info(f"Starting MOBIUS extraction: {doc.page_count} pages at {dpi} DPI")
    
    # Extract spatial text for component matching
    text_index = None
    if component_vocabulary:
        logger.info("Extracting spatial text for component matching...")
        text_spans = extract_spatial_text(doc)
        text_index = SpatialTextIndex(text_spans)
    
    components = []
    total_regions = 0
    total_filtered = 0
    filtered_regions_detail = []
    
    for page_idx in range(doc.page_count):
        logger.debug(f"Processing page {page_idx + 1}/{doc.page_count}")
        
        # Get page object via pages() iterator or direct access
        page = doc._doc.load_page(page_idx)
        
        # Render page to image
        page_image = render_page_to_image(page, dpi=dpi)
        
        # Detect regions (returns RegionDetectionResult with accepted + filtered)
        result = detect_regions(page_image, config)
        regions = result.accepted_regions
        filtered = result.filtered_regions
        
        total_regions += len(regions) + len(filtered)
        total_filtered += len(filtered)
        
        logger.debug(f"Page {page_idx}: detected {len(regions)} regions, filtered {len(filtered)}")
        
        # Record filtered regions for manifest
        page_width = page.rect.width
        page_height = page.rect.height
        img_height, img_width = page_image.shape[:2]
        
        for filtered_region in filtered:
            pdf_bbox = filtered_region.to_pdf_coords(page_width, page_height, img_width, img_height)
            filtered_regions_detail.append((page_idx, pdf_bbox, filtered_region.rejection_reason))
        
        # Extract each accepted region as a component
        for crop_idx, region in enumerate(regions):
            # Extract crop from page image
            x, y, w, h = region.bbox
            crop_image = page_image[y:y+h, x:x+w].copy()
            
            # Get PDF coordinates
            pdf_bbox = region.to_pdf_coords(page_width, page_height, img_width, img_height)
            
            # Generate component ID
            component_id = f"p{page_idx}_c{crop_idx}"
            
            # Create component
            component = MobiusComponent(
                component_id=component_id,
                page_index=page_idx,
                crop_index=crop_idx,
                bbox=pdf_bbox,
                image_data=crop_image,
                width=w,
                height=h,
                confidence=region.confidence,
                is_group=region.is_merged,  # Merged regions are groups
                group_reason="overlap" if region.is_merged else None,
                group_members=None  # TODO: track merged region IDs
            )
            
            # Compute content hash
            component.compute_content_hash()
            
            # Match against component vocabulary if provided
            if component_vocabulary and text_index:
                from .matching import match_component_to_vocabulary
                matched_name, match_score = match_component_to_vocabulary(
                    pdf_bbox, page_idx, text_index, component_vocabulary
                )
                component.component_match = matched_name
                component.match_score = match_score
                
                if matched_name:
                    logger.debug(f"Component {component_id} matched to '{matched_name}' (score: {match_score:.2f})")
            
            components.append(component)
    
    logger.info(f"MOBIUS extraction complete: {len(components)} components from {total_regions} regions ({total_filtered} filtered)")
    
    return MobiusExtractionResult(
        components=components,
        pages_processed=doc.page_count,
        regions_detected=total_regions,
        regions_filtered=total_filtered,
        filtered_regions_detail=filtered_regions_detail,
        config=config
    )


def save_mobius_components(
    components: List[MobiusComponent],
    output_dir: Path,
    rulebook_id: str
) -> Dict[str, Path]:
    """
    Save MOBIUS components to disk with deterministic naming.
    
    Naming convention: <rulebook>__p<page>__c<crop>__<component>__s<score>.png
    
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
        component_name = component.component_match or "unknown"
        score_str = f"{int(component.match_score * 100):03d}"
        
        filename = f"{rulebook_id}__p{component.page_index}__c{component.crop_index}__{component_name}__s{score_str}.png"
        filepath = images_dir / filename
        
        # Convert RGB to BGR for OpenCV
        bgr_image = cv2.cvtColor(component.image_data, cv2.COLOR_RGB2BGR)
        
        # Save with deterministic PNG settings
        cv2.imwrite(str(filepath), bgr_image, [cv2.IMWRITE_PNG_COMPRESSION, 6])
        
        path_mapping[component.component_id] = filepath
        logger.debug(f"Saved component {component.component_id} to {filepath}")
    
    logger.info(f"Saved {len(components)} MOBIUS components to {images_dir}")
    
    return path_mapping
