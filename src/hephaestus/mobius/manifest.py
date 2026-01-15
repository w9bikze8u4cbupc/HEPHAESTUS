"""
MOBIUS manifest generation.

Creates manifest.json for MOBIUS-mode extractions with component metadata.
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
    page_index: int
    crop_index: int
    
    # Bounding box in PDF coordinates (x0, y0, x1, y1)
    bbox: Tuple[float, float, float, float]
    
    # Dimensions
    width: int
    height: int
    
    # Detection confidence
    confidence: float
    
    # Grouping metadata
    is_group: bool
    group_reason: Optional[str]
    group_members: Optional[List[str]]
    
    # Component matching (from MOBIUS vocabulary)
    component_match: Optional[str]
    match_score: float
    
    # Content hash for deduplication
    content_hash: str


@dataclass
class MobiusManifest:
    """Complete MOBIUS manifest."""
    
    # Metadata
    schema_version: str = "9.0-mobius"
    extraction_mode: str = "mobius"
    generated_at: str = ""
    
    # Source
    pdf_path: str = ""
    pdf_name: str = ""
    
    # Extraction summary
    pages_processed: int = 0
    components_extracted: int = 0
    regions_detected: int = 0
    regions_filtered: int = 0
    
    # Configuration
    detection_config: Dict = None
    
    # Components
    items: List[MobiusManifestItem] = None
    
    def __post_init__(self):
        if self.items is None:
            self.items = []
        if self.detection_config is None:
            self.detection_config = {}


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
            page_index=component.page_index,
            crop_index=component.crop_index,
            bbox=component.bbox,
            width=component.width,
            height=component.height,
            confidence=component.confidence,
            is_group=component.is_group,
            group_reason=component.group_reason,
            group_members=component.group_members,
            component_match=component.component_match,
            match_score=component.match_score,
            content_hash=component.content_hash or ""
        )
        items.append(item)
    
    # Build config dict
    config_dict = {
        "min_area": result.config.min_area,
        "max_area_ratio": result.config.max_area_ratio,
        "min_area_ratio": result.config.min_area_ratio,
        "max_aspect_ratio": result.config.max_aspect_ratio,
        "border_margins": {
            "top": result.config.top_margin_ratio,
            "bottom": result.config.bottom_margin_ratio,
            "left": result.config.left_margin_ratio,
            "right": result.config.right_margin_ratio
        },
        "text_edge_density_threshold": result.config.text_edge_density_threshold
    }
    
    # Create manifest
    manifest = MobiusManifest(
        generated_at=datetime.utcnow().isoformat() + "Z",
        pdf_path=str(pdf_path),
        pdf_name=pdf_path.name,
        pages_processed=result.pages_processed,
        components_extracted=len(result.components),
        regions_detected=result.regions_detected,
        regions_filtered=result.regions_filtered,
        detection_config=config_dict,
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
