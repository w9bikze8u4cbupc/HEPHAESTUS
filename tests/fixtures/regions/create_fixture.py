"""
Create synthetic test fixture for region detection.
"""

import numpy as np
from PIL import Image, ImageDraw

def create_test_page():
    """Create a synthetic page with known component regions."""
    # Create white page (1200x1500 pixels)
    width, height = 1200, 1500
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw header (should be filtered out - top margin)
    draw.rectangle([0, 0, width, 80], fill='lightgray', outline='black', width=2)
    
    # Draw footer (should be filtered out - bottom margin)
    draw.rectangle([0, height-80, width, height], fill='lightgray', outline='black', width=2)
    
    # Draw left margin text (should be filtered out)
    draw.rectangle([10, 200, 30, 1300], fill='lightgray', outline='black', width=1)
    
    # Draw component 1: Large board (should be detected)
    draw.rectangle([200, 200, 600, 600], fill='lightblue', outline='black', width=3)
    
    # Draw component 2: Card (should be detected)
    draw.rectangle([700, 200, 900, 500], fill='lightgreen', outline='black', width=3)
    
    # Draw component 3: Token (should be detected)
    draw.ellipse([200, 700, 350, 850], fill='yellow', outline='black', width=3)
    
    # Draw component 4: Another token (should be detected)
    draw.ellipse([400, 700, 550, 850], fill='orange', outline='black', width=3)
    
    # Draw component 5: Small icon (should be detected)
    draw.rectangle([700, 600, 800, 700], fill='pink', outline='black', width=2)
    
    # Draw text-like region (should be filtered out - high edge density)
    for i in range(10):
        y = 1000 + i * 15
        draw.line([200, y, 900, y], fill='black', width=1)
    
    # Draw extreme banner (should be filtered out - aspect ratio)
    draw.rectangle([100, 1300, 1100, 1320], fill='red', outline='black', width=2)
    
    return img

if __name__ == "__main__":
    img = create_test_page()
    img.save("tests/fixtures/regions/test_page.png")
    print("Created test_page.png with known regions:")
    print("  - Expected detections: 5 components (board, 2 cards/tokens, 2 small)")
    print("  - Expected filtered: header, footer, margins, text block, banner")
