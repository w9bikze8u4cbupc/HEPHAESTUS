"""
Heuristic-based classification using deterministic rules.

This module analyzes image properties like dimensions, aspect ratio, and color
distribution to generate classification signals without AI inference.
"""

import math
from typing import Dict, Any
from PIL import Image
import io

from ..pdf.images import ExtractedImage
from ..logging import get_logger

logger = get_logger(__name__)


def classify_heuristic(image: ExtractedImage) -> Dict[str, Any]:
    """
    Returns heuristic signals for image classification.
    
    Args:
        image: ExtractedImage object with pixmap data
        
    Returns:
        Dictionary with classification signals:
        {
            "likely_token": bool,
            "likely_card": bool, 
            "likely_board": bool,
            "likely_icon": bool,
            "noise": bool,
            "confidence": float
        }
    """
    signals = {
        "likely_token": False,
        "likely_card": False,
        "likely_board": False,
        "likely_icon": False,
        "noise": False,
        "confidence": 0.0
    }
    
    try:
        # Convert pixmap to PIL Image for analysis
        pil_image = _pixmap_to_pil(image.pixmap)
        
        # Basic dimension analysis
        width, height = image.width, image.height
        aspect_ratio = width / height if height > 0 else 1.0
        area = width * height
        
        # Size-based heuristics
        if area < 1000:  # Very small images likely icons or noise
            signals["likely_icon"] = True
            signals["confidence"] = 0.7
        elif area > 100000:  # Large images likely boards or full pages
            signals["likely_board"] = True
            signals["confidence"] = 0.6
        elif 0.6 <= aspect_ratio <= 0.8:  # Square-ish, likely tokens
            signals["likely_token"] = True
            signals["confidence"] = 0.5
        elif 0.6 <= aspect_ratio <= 0.7:  # Card-like aspect ratio
            signals["likely_card"] = True
            signals["confidence"] = 0.5
            
        # Aspect ratio analysis
        if aspect_ratio < 0.3 or aspect_ratio > 3.0:  # Extreme ratios often decorative
            signals["noise"] = True
            signals["confidence"] = max(signals["confidence"], 0.6)
            
        # Color complexity analysis (optional enhancement)
        color_signals = _analyze_color_complexity(pil_image)
        signals.update(color_signals)
        
        # Transparency analysis
        transparency_signals = _analyze_transparency(pil_image)
        signals.update(transparency_signals)
        
        logger.debug(f"Heuristic classification for {image.id}: {signals}")
        
    except Exception as exc:
        logger.warning(f"Heuristic classification failed for {image.id}: {exc}")
        signals["noise"] = True
        signals["confidence"] = 0.8  # High confidence it's problematic
    
    return signals


def _pixmap_to_pil(pixmap) -> Image.Image:
    """Convert PyMuPDF Pixmap to PIL Image."""
    img_data = pixmap.tobytes("png")
    return Image.open(io.BytesIO(img_data))


def _analyze_color_complexity(pil_image: Image.Image) -> Dict[str, Any]:
    """Analyze color distribution for classification signals."""
    signals = {}
    
    try:
        # Convert to RGB if needed
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
            
        # Get color histogram
        histogram = pil_image.histogram()
        
        # Calculate color diversity (simplified)
        # More diverse colors might indicate game components vs simple icons
        non_zero_bins = sum(1 for count in histogram if count > 0)
        total_bins = len(histogram)
        color_diversity = non_zero_bins / total_bins if total_bins > 0 else 0
        
        if color_diversity > 0.3:  # Rich color palette
            signals["rich_colors"] = True
        else:  # Limited palette, might be icon or simple graphic
            signals["limited_palette"] = True
            
    except Exception as exc:
        logger.debug(f"Color analysis failed: {exc}")
        signals["color_analysis_failed"] = True
        
    return signals


def _analyze_transparency(pil_image: Image.Image) -> Dict[str, Any]:
    """Analyze transparency for classification signals."""
    signals = {}
    
    try:
        if pil_image.mode in ('RGBA', 'LA') or 'transparency' in pil_image.info:
            signals["has_transparency"] = True
            # Transparent images often tokens or UI elements
            if pil_image.mode == 'RGBA':
                alpha_channel = pil_image.split()[-1]
                alpha_histogram = alpha_channel.histogram()
                # Check if significant transparency exists
                transparent_pixels = alpha_histogram[0]  # Fully transparent
                total_pixels = sum(alpha_histogram)
                if transparent_pixels > total_pixels * 0.1:  # >10% transparent
                    signals["significant_transparency"] = True
        else:
            signals["has_transparency"] = False
            
    except Exception as exc:
        logger.debug(f"Transparency analysis failed: {exc}")
        signals["transparency_analysis_failed"] = True
        
    return signals


def calculate_confidence_score(signals: Dict[str, Any]) -> float:
    """Calculate overall confidence score from heuristic signals."""
    base_confidence = signals.get("confidence", 0.0)
    
    # Boost confidence for clear indicators
    if signals.get("noise", False):
        return min(base_confidence + 0.2, 1.0)
    
    # Multiple positive signals increase confidence
    positive_signals = sum([
        signals.get("likely_token", False),
        signals.get("likely_card", False),
        signals.get("likely_board", False),
        signals.get("rich_colors", False),
    ])
    
    if positive_signals >= 2:
        return min(base_confidence + 0.1, 1.0)
        
    return base_confidence