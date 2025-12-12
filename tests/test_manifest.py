"""Tests for manifest generation."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from hephaestus.pdf.images import ExtractedImage
from hephaestus.classifier.model import ClassificationResult
from hephaestus.metadata.model import ComponentMetadata
from hephaestus.text.spatial import BBox
from hephaestus.output.manifest import (
    build_manifest, write_manifest_json, load_manifest_json,
    Manifest, ManifestItem
)


def create_test_image(image_id: str, width: int = 100, height: int = 100) -> ExtractedImage:
    """Create a test ExtractedImage."""
    mock_pixmap = MagicMock()
    return ExtractedImage(
        id=image_id,
        page_index=0,
        source_type="embedded",
        width=width,
        height=height,
        pixmap=mock_pixmap,
        bbox=BBox(50, 50, 50 + width, 50 + height)
    )


def create_test_classification(label: str, confidence: float) -> ClassificationResult:
    """Create a test ClassificationResult."""
    return ClassificationResult(
        label=label,
        confidence=confidence,
        source="heuristic",
        signals={"image_id": "test_img"}
    )


def create_test_metadata(image_id: str, label: str = None, quantity: int = None) -> ComponentMetadata:
    """Create test ComponentMetadata."""
    evidence = {}
    if label:
        evidence["label_confidence"] = 0.8
    if quantity:
        evidence["quantity_confidence"] = 0.7
    
    return ComponentMetadata(
        image_id=image_id,
        page_index=0,
        label=label,
        quantity=quantity,
        evidence=evidence
    )


class TestManifestItem:
    def test_manifest_item_creation(self):
        """Test ManifestItem creation and properties."""
        item = ManifestItem(
            image_id="test_img",
            file_name="component_test_img.png",
            page_index=0,
            classification="card",
            classification_confidence=0.8,
            label="Action Card",
            quantity=2,
            metadata_confidence=0.75,
            dimensions={"width": 100, "height": 150},
            bbox={"x0": 50, "y0": 50, "x1": 150, "y1": 200},
            dedup_group_id=None,
            is_duplicate=False,
            canonical_image_id="test_img"
        )
        
        assert item.image_id == "test_img"
        assert item.file_name == "component_test_img.png"
        assert item.label == "Action Card"
        assert item.quantity == 2
        
        # Test dictionary conversion
        item_dict = item.to_dict()
        assert item_dict["image_id"] == "test_img"
        assert item_dict["label"] == "Action Card"
        assert item_dict["quantity"] == 2

    def test_manifest_item_with_none_values(self):
        """Test ManifestItem with None values."""
        item = ManifestItem(
            image_id="test_img",
            file_name="component_test_img.png",
            page_index=0,
            classification="unknown",
            classification_confidence=0.3,
            label=None,
            quantity=None,
            metadata_confidence=0.0,
            dimensions={"width": 50, "height": 50},
            bbox=None,
            dedup_group_id=None,
            is_duplicate=False,
            canonical_image_id="test_img"
        )
        
        assert item.label is None
        assert item.quantity is None
        assert item.bbox is None
        
        item_dict = item.to_dict()
        assert item_dict["label"] is None
        assert item_dict["quantity"] is None
        assert item_dict["bbox"] is None


class TestManifest:
    def test_manifest_creation(self):
        """Test Manifest creation and properties."""
        items = [
            ManifestItem(
                image_id="img1",
                file_name="component_img1.png",
                page_index=0,
                classification="card",
                classification_confidence=0.8,
                label="Action Card",
                quantity=2,
                metadata_confidence=0.75,
                dimensions={"width": 100, "height": 150},
                bbox={"x0": 50, "y0": 50, "x1": 150, "y1": 200},
                dedup_group_id=None,
                is_duplicate=False,
                canonical_image_id="img1"
            )
        ]
        
        summary = {
            "total_items": 1,
            "components": 1,
            "non_components": 0
        }
        
        manifest = Manifest(
            version="1.0.0",
            source_pdf="test.pdf",
            extraction_timestamp="2023-01-01T00:00:00",
            total_items=1,
            summary=summary,
            items=items
        )
        
        assert manifest.version == "1.0.0"
        assert manifest.source_pdf == "test.pdf"
        assert manifest.total_items == 1
        assert len(manifest.items) == 1
        
        # Test dictionary conversion
        manifest_dict = manifest.to_dict()
        assert manifest_dict["version"] == "1.0.0"
        assert manifest_dict["total_items"] == 1
        assert len(manifest_dict["items"]) == 1


class TestManifestBuilding:
    def test_build_manifest_complete(self):
        """Test building manifest with complete data."""
        # Create test data
        images = [
            create_test_image("img1", 100, 150),
            create_test_image("img2", 80, 80),
        ]
        
        classifications = {
            "img1": create_test_classification("card", 0.8),
            "img2": create_test_classification("token", 0.7),
        }
        
        metadata = [
            create_test_metadata("img1", "Action Card", 2),
            create_test_metadata("img2", "Gold Token", 5),
        ]
        
        saved_paths = [
            Path("output/component_img1.png"),
            Path("output/component_img2.png"),
        ]
        
        # Build manifest
        manifest = build_manifest(
            Path("test.pdf"),
            images,
            classifications,
            metadata,
            saved_paths
        )
        
        assert manifest.version == "1.0.0"
        assert manifest.source_pdf == "test.pdf"
        assert manifest.total_items == 2
        assert len(manifest.items) == 2
        
        # Check first item
        item1 = manifest.items[0]
        assert item1.image_id == "img1"
        assert item1.classification == "card"
        assert item1.label == "Action Card"
        assert item1.quantity == 2
        assert item1.dimensions["width"] == 100
        assert item1.dimensions["height"] == 150
        
        # Check summary
        assert manifest.summary["total_items"] == 2
        assert manifest.summary["components"] == 2

    def test_build_manifest_partial_data(self):
        """Test building manifest with missing data."""
        images = [create_test_image("img1")]
        
        # No classifications or metadata
        classifications = {}
        metadata = []
        saved_paths = [Path("output/component_img1.png")]
        
        manifest = build_manifest(
            Path("test.pdf"),
            images,
            classifications,
            metadata,
            saved_paths
        )
        
        assert manifest.total_items == 1
        item = manifest.items[0]
        
        assert item.classification == "unknown"
        assert item.classification_confidence == 0.0
        assert item.label is None
        assert item.quantity is None
        assert item.metadata_confidence == 0.0

    def test_build_manifest_mismatched_paths(self):
        """Test building manifest when saved paths don't match images."""
        images = [
            create_test_image("img1"),
            create_test_image("img2"),
        ]
        
        # Only one saved path
        saved_paths = [Path("output/component_img1.png")]
        
        manifest = build_manifest(
            Path("test.pdf"),
            images,
            {},
            [],
            saved_paths
        )
        
        # Should only include images with saved paths
        assert manifest.total_items == 1
        assert manifest.items[0].image_id == "img1"


class TestManifestSerialization:
    def test_write_and_load_manifest(self):
        """Test writing and loading manifest JSON."""
        # Create test manifest
        items = [
            ManifestItem(
                image_id="img1",
                file_name="component_img1.png",
                page_index=0,
                classification="card",
                classification_confidence=0.8,
                label="Action Card",
                quantity=2,
                metadata_confidence=0.75,
                dimensions={"width": 100, "height": 150},
                bbox={"x0": 50, "y0": 50, "x1": 150, "y1": 200},
                dedup_group_id=None,
                is_duplicate=False,
                canonical_image_id="img1"
            )
        ]
        
        summary = {"total_items": 1, "components": 1}
        
        original_manifest = Manifest(
            version="1.0.0",
            source_pdf="test.pdf",
            extraction_timestamp="2023-01-01T00:00:00",
            total_items=1,
            summary=summary,
            items=items
        )
        
        # Write and load
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Write manifest
            manifest_path = write_manifest_json(original_manifest, output_dir)
            assert manifest_path.exists()
            assert manifest_path.name == "manifest.json"
            
            # Load manifest
            loaded_manifest = load_manifest_json(manifest_path)
            
            # Compare
            assert loaded_manifest.version == original_manifest.version
            assert loaded_manifest.source_pdf == original_manifest.source_pdf
            assert loaded_manifest.total_items == original_manifest.total_items
            assert len(loaded_manifest.items) == len(original_manifest.items)
            
            # Compare first item
            orig_item = original_manifest.items[0]
            loaded_item = loaded_manifest.items[0]
            
            assert loaded_item.image_id == orig_item.image_id
            assert loaded_item.label == orig_item.label
            assert loaded_item.quantity == orig_item.quantity
            assert loaded_item.bbox == orig_item.bbox

    def test_manifest_json_structure(self):
        """Test that manifest JSON has expected structure."""
        items = [
            ManifestItem(
                image_id="img1",
                file_name="component_img1.png",
                page_index=0,
                classification="card",
                classification_confidence=0.8,
                label="Action Card",
                quantity=2,
                metadata_confidence=0.75,
                dimensions={"width": 100, "height": 150},
                bbox={"x0": 50, "y0": 50, "x1": 150, "y1": 200},
                dedup_group_id=None,
                is_duplicate=False,
                canonical_image_id="img1"
            )
        ]
        
        summary = {"total_items": 1}
        
        manifest = Manifest(
            version="1.0.0",
            source_pdf="test.pdf",
            extraction_timestamp="2023-01-01T00:00:00",
            total_items=1,
            summary=summary,
            items=items
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            manifest_path = write_manifest_json(manifest, output_dir)
            
            # Load raw JSON and check structure
            with open(manifest_path, 'r') as f:
                json_data = json.load(f)
            
            # Check top-level structure
            required_keys = ["version", "source_pdf", "extraction_timestamp", "total_items", "summary", "items"]
            for key in required_keys:
                assert key in json_data
            
            # Check item structure
            assert len(json_data["items"]) == 1
            item = json_data["items"][0]
            
            item_keys = ["image_id", "file_name", "page_index", "classification", 
                        "classification_confidence", "label", "quantity", 
                        "metadata_confidence", "dimensions", "bbox"]
            for key in item_keys:
                assert key in item

    def test_manifest_roundtrip_with_none_values(self):
        """Test roundtrip serialization with None values."""
        items = [
            ManifestItem(
                image_id="img1",
                file_name="component_img1.png",
                page_index=0,
                classification="unknown",
                classification_confidence=0.3,
                label=None,
                quantity=None,
                metadata_confidence=0.0,
                dimensions={"width": 50, "height": 50},
                bbox=None,
                dedup_group_id=None,
                is_duplicate=False,
                canonical_image_id="img1"
            )
        ]
        
        summary = {"total_items": 1}
        
        original_manifest = Manifest(
            version="1.0.0",
            source_pdf="test.pdf",
            extraction_timestamp="2023-01-01T00:00:00",
            total_items=1,
            summary=summary,
            items=items
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            manifest_path = write_manifest_json(original_manifest, output_dir)
            loaded_manifest = load_manifest_json(manifest_path)
            
            loaded_item = loaded_manifest.items[0]
            assert loaded_item.label is None
            assert loaded_item.quantity is None
            assert loaded_item.bbox is None