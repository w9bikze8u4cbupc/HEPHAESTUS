"""
Quick test for region detection module.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from hephaestus.pdf.ingestion import PdfDocument
from hephaestus.regions.rendering import render_page_to_image
from hephaestus.regions.detection import detect_regions, RegionDetectionConfig


def test_region_detection(pdf_path: str):
    """Test region detection on a PDF."""
    print(f"Testing region detection on: {pdf_path}")
    
    with PdfDocument(pdf_path) as doc:
        print(f"PDF has {doc.page_count} pages")
        
        # Test on first page
        pages = list(doc.pages())
        page = pages[0]
        print(f"\nProcessing page 1...")
        
        # Render page
        img = render_page_to_image(page.as_pymupdf_page(), dpi=150)
        print(f"Rendered to {img.shape}")
        
        # Detect regions
        config = RegionDetectionConfig(
            min_area=2500,
            max_area_ratio=0.8,
            merge_threshold=0.3
        )
        
        regions = detect_regions(img, config)
        print(f"Detected {len(regions)} regions")
        
        for i, region in enumerate(regions):
            x, y, w, h = region.bbox
            print(f"  Region {i+1}: bbox=({x}, {y}, {w}, {h}), area={region.area}, confidence={region.confidence:.2f}, merged={region.is_merged}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_detection.py <pdf_path>")
        sys.exit(1)
    
    test_region_detection(sys.argv[1])
