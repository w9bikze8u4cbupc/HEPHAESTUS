"""
MOBIUS manifest generation.

Creates manifest.json for MOBIUS-mode extractions with image-role metadata.
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json
from datetime import datetime

from .extraction import MobiusComponent, MobiusExtractionResult
from ..logging import get_logger

logger = get_logger(__name__)


@dataclass
class MobiusManifestItem:
    """Manifest entry for a MOBIUS component."""
    
    # Component identification
    component_id: str
    file_name: str
    
    # Source information
    source_type: str
    source_image_id: str
    
    # Sheet information (if derived from sheet)
    sheet_id: Optional[str]
    component_bbox_in_sheet: Optional[Tuple[int, int, int, int]]
    
    # Image role
    image_role: str
    
    # Source bbox in PDF coordinates
    source_bbox: Optional[Tuple[float, float, float, float]]
    
    # Dimensions
    width: int
    height: int
    
    # Page index
    page_index: int
    
    # Component matching (from MOBIUS vocabulary)
    component_match: Optional[str]
    match_score: float
    
    # Content hash for deduplication
    content_hash: str
    
    # G4 metrics (for rendered figures)
    width_ratio: float = 0.0
    height_ratio: float = 0.0
    text_overlap_ratio: float = 0.0
    component_likeness_score: float = 0.0
    stddev_luma: float = 0.0
    edge_density: float = 0.0
    rank_within_page: int = 0
    
    # G6 metrics
    bbox_width_in: float = 0.0
    bbox_height_in: float = 0.0
    uniformity_ratio: float = 0.0
    render_dpi_used: int = 0
    
    # Content hash for deduplication
    content_hash: str
    
    # G3.5: Component-likeness score
    component_likeness_score: float = 0.0
    
    # G3.5: Rejection reason (if rejected)
    rejection_reason: Optional[str] = None


@dataclass
class MobiusManifest:
    """Complete MOBIUS manifest."""
    
    # Metadata
    schema_version: str = "9.1-mobius-role-driven"
    extraction_mode: str = "mobius"
    generated_at: str = ""
    
    # Source
    pdf_path: str = ""
    pdf_name: str = ""
    
    # Extraction summary
    pages_processed: int = 0
    components_extracted: int = 0
    total_embedded_images: int = 0
    
    # Image role distribution
    role_distribution: Dict[str, int] = None
    images_by_role: Dict[str, int] = None
    
    # Components
    items: List[MobiusManifestItem] = None
    
    def __post_init__(self):
        if self.items is None:
            self.items = []
        if self.role_distribution is None:
            self.role_distribution = {}
        if self.images_by_role is None:
            self.images_by_role = {}


def build_mobius_manifest(
    pdf_path: Path,
    result: MobiusExtractionResult,
    path_mapping: Dict[str, Path]
) -> MobiusManifest:
    """
    Build MOBIUS manifest from extraction result.
    
    Args:
        pdf_path: Source PDF path
        result: MOBIUS extraction result
        path_mapping: Component ID to file path mapping
    
    Returns:
        Complete MOBIUS manifest
    """
    logger.info("Building MOBIUS manifest...")
    
    # Create manifest items
    items = []
    for component in result.components:
        filepath = path_mapping.get(component.component_id)
        if not filepath:
            logger.warning(f"No file path for component {component.component_id}")
            continue
        
        item = MobiusManifestItem(
            component_id=component.component_id,
            file_name=filepath.name,
            source_type=component.source_type,
            source_image_id=component.source_image_id,
            sheet_id=component.sheet_id,
            component_bbox_in_sheet=component.component_bbox_in_sheet,
            image_role=component.image_role,
            source_bbox=component.source_bbox,
            width=int(component.width),  # Convert numpy int to Python int
            height=int(component.height),  # Convert numpy int to Python int
            page_index=component.page_index,
            component_match=component.component_match,
            match_score=component.match_score,
            content_hash=component.content_hash or "",
            width_ratio=component.width_ratio,
            height_ratio=component.height_ratio,
            text_overlap_ratio=component.text_overlap_ratio,
            component_likeness_score=component.component_likeness_score,
            stddev_luma=component.stddev_luma,
            edge_density=component.edge_density,
            rank_within_page=component.rank_within_page,
            bbox_width_in=component.bbox_width_in,
            bbox_height_in=component.bbox_height_in,
            uniformity_ratio=component.uniformity_ratio,
            render_dpi_used=component.render_dpi_used
        )
        items.append(item)
    
    # Create manifest
    manifest = MobiusManifest(
        generated_at=datetime.utcnow().isoformat() + "Z",
        pdf_path=str(pdf_path),
        pdf_name=pdf_path.name,
        pages_processed=result.pages_processed,
        components_extracted=len(result.components),
        total_embedded_images=result.total_embedded_images,
        role_distribution=result.role_distribution,
        images_by_role=result.images_by_role,
        items=items
    )
    
    logger.info(f"Built manifest with {len(items)} components")
    
    return manifest


def write_mobius_manifest(manifest: MobiusManifest, output_dir: Path) -> Path:
    """
    Write MOBIUS manifest to JSON file.
    
    Args:
        manifest: MOBIUS manifest to write
        output_dir: Output directory
    
    Returns:
        Path to written manifest file
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    manifest_path = output_dir / "manifest.json"
    
    # Convert to dict
    manifest_dict = asdict(manifest)
    
    # Write with deterministic formatting
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_dict, f, indent=2, sort_keys=True, ensure_ascii=False)
    
    logger.info(f"Wrote MOBIUS manifest to {manifest_path}")
    
    return manifest_path
