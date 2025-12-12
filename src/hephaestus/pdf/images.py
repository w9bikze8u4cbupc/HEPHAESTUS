from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Sequence, Optional

import fitz  # type: ignore[import]

from .ingestion import PdfDocument
from ..text.spatial import BBox
from ..logging import get_logger

logger = get_logger(__name__)

ImageSourceType = Literal["embedded"]


@dataclass
class ExtractedImage:
    id: str
    page_index: int
    source_type: ImageSourceType
    width: int
    height: int
    pixmap: fitz.Pixmap
    bbox: Optional[BBox] = None  # Image placement on page


def extract_embedded_images(
    pdf: PdfDocument,
    min_width: int = 50,
    min_height: int = 50,
) -> list[ExtractedImage]:
    """Extract embedded raster images from PDF pages with dimensional filtering."""
    images: list[ExtractedImage] = []
    total_found = 0
    
    logger.info(f"Processing {pdf.page_count} pages for embedded images")
    
    for page in pdf.pages():
        raw_page = page.as_pymupdf_page()
        img_refs = raw_page.get_images(full=True)
        page_found = len(img_refs)
        total_found += page_found
        
        logger.debug(f"Page {page.index}: found {page_found} embedded images")
        
        for local_idx, img in enumerate(img_refs):
            xref = img[0]
            try:
                pix = fitz.Pixmap(pdf._doc, xref)  # type: ignore[attr-defined]
                width, height = pix.width, pix.height
                
                if width < min_width or height < min_height:
                    logger.debug(
                        f"Page {page.index}, image {local_idx}: "
                        f"filtered out ({width}x{height} < {min_width}x{min_height})"
                    )
                    pix = None  # Release memory
                    continue
                
                # Try to get image placement bounding box
                img_bbox = _get_image_bbox(raw_page, xref)
                
                img_id = f"p{page.index}_img{local_idx}"
                images.append(
                    ExtractedImage(
                        id=img_id,
                        page_index=page.index,
                        source_type="embedded",
                        width=width,
                        height=height,
                        pixmap=pix,
                        bbox=img_bbox,
                    )
                )
                
                bbox_info = f"bbox={img_bbox}" if img_bbox else "bbox=unknown"
                logger.debug(
                    f"Page {page.index}, image {local_idx}: "
                    f"extracted as {img_id} ({width}x{height}, {bbox_info})"
                )
                
            except Exception as exc:
                logger.warning(
                    f"Page {page.index}, image {local_idx}: "
                    f"failed to extract - {exc}"
                )
                continue
    
    logger.info(f"Found {total_found} total images, retained {len(images)} after filtering")
    return images


def _get_image_bbox(page: fitz.Page, xref: int) -> Optional[BBox]:
    """
    Try to determine the bounding box of an image on the page.
    
    Args:
        page: PyMuPDF page object
        xref: Image cross-reference number
        
    Returns:
        BBox if placement can be determined, None otherwise
    """
    try:
        # Get all image instances on the page
        image_list = page.get_images(full=True)
        
        # Find matching image by xref and try to get placement
        for img_info in image_list:
            if img_info[0] == xref:  # xref matches
                # Try to get image placement using get_image_rects
                try:
                    rects = page.get_image_rects(img_info)
                    if rects:
                        # Use first rectangle if multiple found
                        rect = rects[0]
                        return BBox(
                            x0=rect.x0,
                            y0=rect.y0,
                            x1=rect.x1,
                            y1=rect.y1
                        )
                except:
                    # get_image_rects might not be available in all PyMuPDF versions
                    pass
                
                # Fallback: try to find image in page content stream
                try:
                    # This is a more complex approach that would require
                    # parsing the page content stream - for now, return None
                    pass
                except:
                    pass
                
                break
        
        # If we can't determine placement, return None
        logger.debug(f"Could not determine bbox for image xref {xref}")
        return None
        
    except Exception as exc:
        logger.debug(f"Error getting image bbox for xref {xref}: {exc}")
        return None


def save_images_flat(
    images: Sequence[ExtractedImage],
    output_dir: Path,
    fmt: str = "png",
) -> list[Path]:
    """Save extracted images to a flat directory structure."""
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_paths: list[Path] = []
    
    logger.info(f"Saving {len(images)} images to {output_dir}")
    
    for image in images:
        filename = f"component_{image.id}.{fmt.lower()}"
        path = output_dir / filename
        
        try:
            image.pixmap.save(path.as_posix())
            saved_paths.append(path)
            logger.debug(f"Saved {image.id} as {path}")
        except Exception as exc:
            logger.error(f"Failed to save {image.id}: {exc}")
            continue
    
    logger.info(f"Successfully saved {len(saved_paths)} images")
    return saved_paths