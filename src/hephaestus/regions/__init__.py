"""
Phase 9: Region detection for component-centric extraction.

This module provides page rendering and region detection capabilities
for extracting individual component images from rulebook PDFs.
"""

from .detection import detect_regions, RegionDetectionConfig, DetectedRegion
from .rendering import render_page_to_image

__all__ = [
    'detect_regions',
    'RegionDetectionConfig',
    'DetectedRegion',
    'render_page_to_image',
]
