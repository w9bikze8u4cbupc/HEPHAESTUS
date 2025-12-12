"""Tests for metadata annotation."""

import pytest
from typing import Optional
from unittest.mock import MagicMock

from hephaestus.pdf.images import ExtractedImage
from hephaestus.classifier.model import ClassificationResult
from hephaestus.text.spatial import TextSpan, BBox
from hephaestus.text.index import SpatialTextIndex
from hephaestus.metadata.annotator import annotate_components
from hephaestus.metadata.labels import infer_label
from hephaestus.metadata.quantity import infer_quantity
from hephaestus.metadata.model import ComponentMetadata


def create_test_image(image_id: str, bbox: Optional[BBox] = BBox(50, 50, 150, 150)) -> ExtractedImage:
    """Create a test ExtractedImage."""
    mock_pixmap = MagicMock()
    return ExtractedImage(
        id=image_id,
        page_index=0,
        source_type="embedded",
        width=100,
        height=100,
        pixmap=mock_pixmap,
        bbox=bbox
    )


def create_test_classification(label: str, confidence: float) -> ClassificationResult:
    """Create a test ClassificationResult."""
    return ClassificationResult(
        label=label,
        confidence=confidence,
        source="heuristic",
        signals={}
    )


class TestLabelInference:
    def test_infer_label_from_simple_text(self):
        """Test label inference from simple text spans."""
        spans = [
            TextSpan(0, "Game Card", BBox(10, 10, 50, 30), "span"),
            TextSpan(0, "Token Piece", BBox(60, 10, 100, 30), "span"),
        ]
        
        label, evidence = infer_label(spans)
        
        assert label is not None
        assert len(evidence["candidates"]) == 2
        assert evidence["label_confidence"] > 0.0

    def test_infer_label_filters_stop_words(self):
        """Test that stop words are filtered out."""
        spans = [
            TextSpan(0, "the example", BBox(10, 10, 50, 30), "span"),
            TextSpan(0, "Card Token", BBox(60, 10, 100, 30), "span"),
        ]
        
        label, evidence = infer_label(spans)
        
        # Should prefer "Card Token" over "the example" and clean it to "Card"
        assert label == "Card"

    def test_infer_label_no_suitable_candidates(self):
        """Test behavior when no suitable candidates exist."""
        spans = [
            TextSpan(0, "123456", BBox(10, 10, 50, 30), "span"),  # Purely numeric
            TextSpan(0, "see above", BBox(60, 10, 100, 30), "span"),  # Stop phrase
        ]
        
        label, evidence = infer_label(spans)
        
        assert label is None
        assert evidence["reason"] == "no_suitable_candidate"

    def test_infer_label_empty_input(self):
        """Test behavior with empty input."""
        label, evidence = infer_label([])
        
        assert label is None
        assert evidence["reason"] == "no_nearby_text"


class TestQuantityInference:
    def test_infer_quantity_x_patterns(self):
        """Test quantity inference from x patterns."""
        spans = [
            TextSpan(0, "x3 tokens", BBox(10, 10, 50, 30), "span"),
            TextSpan(0, "5x cards", BBox(60, 10, 100, 30), "span"),
        ]
        
        quantity, evidence = infer_quantity(spans)
        
        assert quantity is not None
        assert quantity in [3, 5]
        assert evidence["quantity_confidence"] > 0.0

    def test_infer_quantity_word_patterns(self):
        """Test quantity inference from word patterns."""
        spans = [
            TextSpan(0, "3 cards", BBox(10, 10, 50, 30), "span"),
            TextSpan(0, "tokens 4", BBox(60, 10, 100, 30), "span"),
        ]
        
        quantity, evidence = infer_quantity(spans)
        
        assert quantity is not None
        assert quantity in [3, 4]

    def test_infer_quantity_parenthetical(self):
        """Test quantity inference from parenthetical numbers."""
        spans = [
            TextSpan(0, "Resource (5)", BBox(10, 10, 50, 30), "span"),
        ]
        
        quantity, evidence = infer_quantity(spans)
        
        assert quantity == 5

    def test_infer_quantity_no_patterns(self):
        """Test behavior when no quantity patterns are found."""
        spans = [
            TextSpan(0, "Game Card", BBox(10, 10, 50, 30), "span"),
            TextSpan(0, "Token Piece", BBox(60, 10, 100, 30), "span"),
        ]
        
        quantity, evidence = infer_quantity(spans)
        
        assert quantity is None
        assert evidence["reason"] == "no_quantity_patterns_found"


class TestMetadataAnnotation:
    def test_annotate_component_with_bbox(self):
        """Test annotation of component with bounding box."""
        # Create test data
        image = create_test_image("test_img", BBox(50, 50, 150, 150))
        classification = create_test_classification("card", 0.8)
        
        # Create text spans near the image
        spans = [
            TextSpan(0, "Action Card", BBox(40, 40, 80, 60), "span"),
            TextSpan(0, "x2 pieces", BBox(160, 160, 200, 180), "span"),
        ]
        
        text_index = SpatialTextIndex(spans)
        
        # Annotate
        metadata_list = annotate_components(
            [image],
            {"test_img": classification},
            text_index,
            expand=50.0
        )
        
        assert len(metadata_list) == 1
        metadata = metadata_list[0]
        
        assert metadata.image_id == "test_img"
        assert metadata.page_index == 0
        # Should find some nearby text
        assert metadata.evidence["nearby_spans_found"] > 0

    def test_annotate_component_without_bbox(self):
        """Test annotation of component without bounding box."""
        # Create image without bbox
        image = create_test_image("test_img", None)
        classification = create_test_classification("card", 0.8)
        
        spans = [
            TextSpan(0, "Action Card", BBox(40, 40, 80, 60), "span"),
        ]
        
        text_index = SpatialTextIndex(spans)
        
        # Annotate
        metadata_list = annotate_components(
            [image],
            {"test_img": classification},
            text_index
        )
        
        assert len(metadata_list) == 1
        metadata = metadata_list[0]
        
        assert metadata.label is None
        assert metadata.quantity is None
        assert metadata.evidence["missing_bbox"] is True

    def test_annotate_non_component(self):
        """Test that non-components are skipped."""
        image = create_test_image("test_img", BBox(50, 50, 150, 150))
        classification = create_test_classification("icon", 0.9)
        
        spans = [
            TextSpan(0, "Action Card", BBox(40, 40, 80, 60), "span"),
        ]
        
        text_index = SpatialTextIndex(spans)
        
        # Annotate
        metadata_list = annotate_components(
            [image],
            {"test_img": classification},
            text_index
        )
        
        assert len(metadata_list) == 1
        metadata = metadata_list[0]
        
        # Should be skipped due to classification
        assert metadata.evidence["should_annotate"] is False

    def test_annotate_batch_with_mixed_types(self):
        """Test batch annotation with mixed component types."""
        images = [
            create_test_image("card_1", BBox(50, 50, 150, 150)),
            create_test_image("icon_1", BBox(200, 200, 250, 250)),
            create_test_image("token_1", BBox(300, 300, 400, 400)),
        ]
        
        classifications = {
            "card_1": create_test_classification("card", 0.8),
            "icon_1": create_test_classification("icon", 0.9),
            "token_1": create_test_classification("token", 0.7),
        }
        
        spans = [
            TextSpan(0, "Action Card x2", BBox(40, 40, 160, 160), "span"),
            TextSpan(0, "Gold Token (3)", BBox(290, 290, 410, 410), "span"),
        ]
        
        text_index = SpatialTextIndex(spans)
        
        # Annotate
        metadata_list = annotate_components(images, classifications, text_index, expand=30.0)
        
        assert len(metadata_list) == 3
        
        # Check that appropriate items were annotated
        card_metadata = next(m for m in metadata_list if m.image_id == "card_1")
        icon_metadata = next(m for m in metadata_list if m.image_id == "icon_1")
        token_metadata = next(m for m in metadata_list if m.image_id == "token_1")
        
        # Card should be annotated
        assert card_metadata.evidence["should_annotate"] is True
        
        # Icon should be skipped
        assert icon_metadata.evidence["should_annotate"] is False
        
        # Token should be annotated
        assert token_metadata.evidence["should_annotate"] is True


class TestComponentMetadata:
    def test_metadata_properties(self):
        """Test ComponentMetadata property methods."""
        # Complete metadata
        complete_metadata = ComponentMetadata(
            image_id="test",
            page_index=0,
            label="Action Card",
            quantity=3,
            evidence={"label_confidence": 0.8, "quantity_confidence": 0.7}
        )
        
        assert complete_metadata.has_label() is True
        assert complete_metadata.has_quantity() is True
        assert complete_metadata.is_complete() is True
        assert complete_metadata.get_confidence_score() == 0.75  # Average of 0.8 and 0.7
        
        # Partial metadata
        partial_metadata = ComponentMetadata(
            image_id="test",
            page_index=0,
            label="Card",
            quantity=None,
            evidence={"label_confidence": 0.6}
        )
        
        assert partial_metadata.has_label() is True
        assert partial_metadata.has_quantity() is False
        assert partial_metadata.is_complete() is False
        assert partial_metadata.get_confidence_score() == 0.6

    def test_metadata_summary(self):
        """Test metadata summary generation."""
        metadata = ComponentMetadata(
            image_id="test",
            page_index=0,
            label="Action Card",
            quantity=2,
            evidence={"label_confidence": 0.8, "quantity_confidence": 0.7}
        )
        
        summary = metadata.get_summary()
        
        assert "2x" in summary
        assert "Action Card" in summary
        assert "confidence: 0.75" in summary