"""
Page rendering for region detection.

Converts PDF pages to images for computer vision processing.
"""

from pathlib import Path
from typing import Optional
import numpy as np
import fitz  # PyMuPDF

from ..logging import get_logger

logger = get_logger(__name__)


def render_page_to_image(
    page: fitz.Page,
    dpi: int = 150,
    colorspace: str = "rgb"
) -> np.ndarray:
    """
    Render a PDF page to a numpy array image.
    
    Args:
        page: PyMuPDF page object
        dpi: Resolution for rendering (default 150)
        colorspace: Color space for output ("rgb" or "gray")
    
    Returns:
        numpy array of shape (height, width, channels)
        
    Note:
        Higher DPI = better quality but slower processing.
        150 DPI is a good balance for component detection.
    """
    # Calculate zoom factor from DPI
    # PyMuPDF default is 72 DPI
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    
    # Render page to pixmap
    if colorspace == "gray":
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
    else:
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
    
    # Convert to numpy array
    # PyMuPDF pixmap is in RGB/GRAY format
    img = np.frombuffer(pix.samples, dtype=np.uint8)
    
    if colorspace == "gray":
        img = img.reshape(pix.height, pix.width)
    else:
        img = img.reshape(pix.height, pix.width, 3)
    
    logger.debug(f"Rendered page to {img.shape} at {dpi} DPI")
    
    return img


def render_page_region(
    page: fitz.Page,
    bbox: tuple[float, float, float, float],
    dpi: int = 150
) -> np.ndarray:
    """
    Render a specific region of a PDF page.
    
    Args:
        page: PyMuPDF page object
        bbox: Bounding box (x0, y0, x1, y1) in PDF coordinates
        dpi: Resolution for rendering
    
    Returns:
        numpy array of the cropped region
    """
    # Calculate zoom factor
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    
    # Create clip rectangle
    clip = fitz.Rect(bbox)
    
    # Render with clipping
    pix = page.get_pixmap(matrix=mat, clip=clip, colorspace=fitz.csRGB)
    
    # Convert to numpy array
    img = np.frombuffer(pix.samples, dtype=np.uint8)
    img = img.reshape(pix.height, pix.width, 3)
    
    return img
