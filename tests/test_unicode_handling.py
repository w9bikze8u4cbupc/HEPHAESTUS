"""
Tests for Unicode and encoding handling in HEPHAESTUS.

Regression tests for P0 Unicode encoding issues.
"""

import tempfile
from pathlib import Path
import json

import pytest

from src.hephaestus.cli import safe_echo
from src.hephaestus.output.manifest import ManifestItem, write_manifest_json, Manifest


class TestUnicodeHandling:
    """Test Unicode and encoding handling."""
    
    def test_safe_echo_with_unicode(self, capsys):
        """Test that safe_echo handles Unicode characters without crashing."""
        # Test with Unicode emoji (the characters that caused the original crash)
        unicode_message = "✅ Test complete! 🖼️ Images: 5 🎯 Components: 3"
        
        # This should not raise UnicodeEncodeError
        safe_echo(unicode_message)
        
        captured = capsys.readouterr()
        # Should either show Unicode or ASCII fallback, but not crash
        assert len(captured.out) > 0
    
    def test_safe_echo_fallback_conversion(self, capsys, monkeypatch):
        """Test that safe_echo converts to ASCII fallback when Unicode fails."""
        
        # Mock typer.echo to raise UnicodeEncodeError only for Unicode characters
        original_echo = __import__('typer').echo
        def mock_echo_selective(message):
            if any(ord(char) > 127 for char in message):
                raise UnicodeEncodeError('charmap', message, 0, 1, 'character maps to <undefined>')
            else:
                original_echo(message)
        
        import typer
        monkeypatch.setattr(typer, "echo", mock_echo_selective)
        
        # Test the fallback behavior
        safe_echo("✅ Extraction complete!")
        
        captured = capsys.readouterr()
        assert "[OK] Extraction complete!" in captured.out
    
    def test_manifest_unicode_content(self):
        """Test that manifest can handle Unicode content in labels and filenames."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Create manifest with Unicode content
            manifest_item = ManifestItem(
                image_id="test_unicode",
                file_name="component_test_unicode.png",
                page_index=0,
                classification="card",
                classification_confidence=0.8,
                label="Château de Versailles (château)",  # Unicode characters
                quantity=1,
                metadata_confidence=0.9,
                dimensions={"width": 100, "height": 150},
                bbox=None,
                dedup_group_id=None,
                is_duplicate=False,
                canonical_image_id="test_unicode"
            )
            
            manifest = Manifest(
                version="1.0.0",
                source_pdf="test_unicode_文档.pdf",  # Unicode filename
                extraction_timestamp="2025-01-01T00:00:00",
                total_items=1,
                summary={"total": 1},
                items=[manifest_item]
            )
            
            # Write manifest (should handle Unicode correctly)
            manifest_path = write_manifest_json(manifest, output_dir)
            
            # Verify file was created and contains correct Unicode content
            assert manifest_path.exists()
            
            # Read back and verify Unicode content is preserved
            with open(manifest_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            assert data["source_pdf"] == "test_unicode_文档.pdf"
            assert data["items"][0]["label"] == "Château de Versailles (château)"
    
    def test_unicode_in_file_paths(self):
        """Test handling of Unicode characters in file paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Create a path with Unicode characters
            unicode_subdir = output_dir / "测试目录"  # Chinese characters
            unicode_subdir.mkdir()
            
            # Test that we can create files in Unicode directories
            test_file = unicode_subdir / "test_file.json"
            test_content = {"message": "Hello 世界"}
            
            with open(test_file, 'w', encoding='utf-8') as f:
                json.dump(test_content, f, ensure_ascii=False)
            
            # Verify file exists and content is correct
            assert test_file.exists()
            
            with open(test_file, 'r', encoding='utf-8') as f:
                loaded_content = json.load(f)
            
            assert loaded_content["message"] == "Hello 世界"


if __name__ == "__main__":
    pytest.main([__file__])