"""Helper functions for creating test PDFs with proper file handle management."""

import tempfile
from pathlib import Path
from typing import List, Tuple
import io

import fitz  # type: ignore[import]
from PIL import Image


def make_pdf_with_images_and_text(tmp_path: Path, 
                                  image_sizes: List[Tuple[int, int]] = None,
                                  text_content: str = None) -> Path:
    """
    Create a PDF with embedded images and text, ensuring all handles are closed.
    
    Args:
        tmp_path: Directory to create the PDF in
        image_sizes: List of (width, height) tuples for images to embed
        text_content: Text to add to the PDF
        
    Returns:
        Path to the created PDF file
    """
    if image_sizes is None:
        image_sizes = [(100, 100)]
    
    pdf_path = tmp_path / "test.pdf"
    
    doc = fitz.open()
    try:
        page = doc.new_page(width=595, height=842)
        
        # Add text if provided
        if text_content:
            page.insert_text((50, 50), text_content)
        
        # Add images
        y_offset = 100
        for width, height in image_sizes:
            if width > 0 and height > 0:  # Skip zero-dimension images
                # Create a simple colored image
                img = Image.new('RGB', (width, height), color='red')
                img_bytes = io.BytesIO()
                img.save(img_bytes, format='PNG')
                img_bytes.seek(0)
                
                # Insert image into PDF
                img_rect = fitz.Rect(50, y_offset, 50 + width, y_offset + height)
                page.insert_image(img_rect, stream=img_bytes.getvalue())
                y_offset += height + 10
        
        # Write PDF to file
        pdf_bytes = doc.tobytes()
        pdf_path.write_bytes(pdf_bytes)
        
    finally:
        doc.close()
    
    return pdf_path


def make_encrypted_pdf(tmp_path: Path) -> Path:
    """Create an encrypted PDF with proper file handle management."""
    pdf_path = tmp_path / "encrypted.pdf"
    
    doc = fitz.open()
    try:
        page = doc.new_page()
        page.insert_text((50, 50), "Encrypted content")
        
        # Encrypt with password
        pdf_bytes = doc.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="test", owner_pw="test")
        pdf_path.write_bytes(pdf_bytes)
        
    finally:
        doc.close()
    
    return pdf_path


def make_empty_pdf(tmp_path: Path) -> Path:
    """Create an empty PDF with proper file handle management."""
    pdf_path = tmp_path / "empty.pdf"
    
    doc = fitz.open()
    try:
        doc.new_page()  # Empty page
        pdf_bytes = doc.tobytes()
        pdf_path.write_bytes(pdf_bytes)
        
    finally:
        doc.close()
    
    return pdf_path