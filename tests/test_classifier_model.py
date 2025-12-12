"""Tests for hybrid classification model."""

import pytest
from hypothesis import given, strategies as st
from unittest.mock import patch, MagicMock

from hephaestus.classifier.model import (
    HybridClassifier, ClassificationResult, ComponentType
)
from hephaestus.pdf.images import ExtractedImage
from tests.test_classifier_heuristics import create_test_extracted_image


class TestClassificationResult:
    def test_component_detection(self):
        """Test component vs non-component detection."""
        # Component result
        component_result = ClassificationResult(
            label="token",
            confidence=0.8,
            source="heuristic",
            signals={}
        )
        assert component_result.is_component() is True
        assert component_result.get_primary_category() == "component"
        
        # Non-component result
        non_component_result = ClassificationResult(
            label="icon",
            confidence=0.7,
            source="heuristic", 
            signals={}
        )
        assert non_component_result.is_component() is False
        assert non_component_result.get_primary_category() == "non-component"

    def test_component_type_mapping(self):
        """Test ComponentType enum mapping."""
        result = ClassificationResult(
            label="card",
            confidence=0.8,
            source="heuristic",
            signals={},
            component_type=ComponentType.CARD
        )
        assert result.component_type == ComponentType.CARD


class TestHybridClassifier:
    def test_classifier_initialization(self):
        """Test classifier initialization with different parameters."""
        classifier = HybridClassifier(
            heuristic_threshold=0.8,
            vision_weight=0.7,
            enable_vision=False
        )
        
        assert classifier.heuristic_threshold == 0.8
        assert classifier.vision_weight == 0.7
        assert classifier.enable_vision is False

    def test_heuristic_only_classification(self):
        """Test classification using only heuristics."""
        classifier = HybridClassifier(enable_vision=False)
        
        # Small image should be classified as icon
        small_image = create_test_extracted_image(20, 20)
        result = classifier.classify(small_image)
        
        assert result.source == "heuristic"
        assert result.label in ["icon", "non-component"]
        assert 0.0 <= result.confidence <= 1.0

    def test_high_confidence_heuristic_dominates(self):
        """Test that high-confidence heuristics dominate even with vision enabled."""
        # Mock vision to always return low confidence
        with patch('hephaestus.classifier.model.is_vision_available', return_value=True):
            with patch('hephaestus.classifier.model.classify_with_vision') as mock_vision:
                mock_vision.return_value = {
                    "vision_label": "card",
                    "confidence": 0.3,
                    "categories": {"component": 0.3}
                }
                
                classifier = HybridClassifier(
                    heuristic_threshold=0.6,
                    enable_vision=True
                )
                
                # Large image should trigger high-confidence heuristic (board)
                large_image = create_test_extracted_image(500, 400)
                result = classifier.classify(large_image)
                
                # Should use heuristic despite vision being available
                assert result.source == "heuristic"
                assert result.label == "board"

    @patch('hephaestus.classifier.model.is_vision_available', return_value=True)
    def test_vision_dominates_low_confidence_heuristic(self, mock_vision_available):
        """Test that vision dominates when heuristics have low confidence."""
        with patch('hephaestus.classifier.model.classify_with_vision') as mock_vision:
            mock_vision.return_value = {
                "vision_label": "token",
                "confidence": 0.8,
                "categories": {"component": 0.8}
            }
            
            classifier = HybridClassifier(
                heuristic_threshold=0.7,
                enable_vision=True
            )
            
            # Medium-sized image with ambiguous heuristics
            medium_image = create_test_extracted_image(80, 90)
            result = classifier.classify(medium_image)
            
            # Vision should dominate due to higher confidence
            assert result.source in ["vision", "hybrid"]
            assert result.confidence > 0.5

    def test_batch_classification(self):
        """Test batch classification functionality."""
        classifier = HybridClassifier(enable_vision=False)
        
        images = [
            create_test_extracted_image(20, 20),   # Small - icon
            create_test_extracted_image(100, 120), # Medium - token/card
            create_test_extracted_image(500, 400)  # Large - board
        ]
        
        results = classifier.classify_batch(images)
        
        assert len(results) == 3
        for result in results:
            assert isinstance(result, ClassificationResult)
            assert 0.0 <= result.confidence <= 1.0
            assert result.source == "heuristic"

    def test_classification_summary(self):
        """Test classification summary generation."""
        classifier = HybridClassifier(enable_vision=False)
        
        # Create mock results
        results = [
            ClassificationResult("token", 0.8, "heuristic", {}),
            ClassificationResult("card", 0.7, "heuristic", {}),
            ClassificationResult("icon", 0.9, "heuristic", {}),
            ClassificationResult("board", 0.6, "vision", {})
        ]
        
        summary = classifier.get_classification_summary(results)
        
        assert summary["total"] == 4
        assert summary["components"] == 3  # token, card, board
        assert summary["non_components"] == 1  # icon
        assert summary["component_ratio"] == 0.75
        assert "average_confidence" in summary
        assert "sources" in summary
        assert "labels" in summary

    def test_error_handling_in_classification(self):
        """Test error handling during classification."""
        classifier = HybridClassifier(enable_vision=False)
        
        # Create problematic image that might cause errors
        problematic_image = ExtractedImage(
            id="problematic",
            page_index=0,
            source_type="embedded",
            width=100,
            height=100,
            pixmap=None  # This will cause issues
        )
        
        # Should handle gracefully
        result = classifier.classify(problematic_image)
        
        assert isinstance(result, ClassificationResult)
        assert result.confidence >= 0.0


class TestHybridClassificationProperties:
    """Property-based tests for hybrid classification."""

    @given(
        width=st.integers(min_value=10, max_value=1000),
        height=st.integers(min_value=10, max_value=1000)
    )
    def test_classification_stability(self, width, height):
        """For any image dimensions, classification should be stable across runs."""
        classifier = HybridClassifier(enable_vision=False)
        image = create_test_extracted_image(width, height)
        
        # Run classification multiple times
        result1 = classifier.classify(image)
        result2 = classifier.classify(image)
        
        # Results should be identical for deterministic classification
        assert result1.label == result2.label
        assert result1.confidence == result2.confidence
        assert result1.source == result2.source

    @given(
        threshold=st.floats(min_value=0.1, max_value=0.9),
        vision_weight=st.floats(min_value=0.1, max_value=0.9)
    )
    def test_parameter_bounds(self, threshold, vision_weight):
        """For any valid parameters, classifier should initialize and work."""
        classifier = HybridClassifier(
            heuristic_threshold=threshold,
            vision_weight=vision_weight,
            enable_vision=False
        )
        
        image = create_test_extracted_image(100, 100)
        result = classifier.classify(image)
        
        assert isinstance(result, ClassificationResult)
        assert 0.0 <= result.confidence <= 1.0

    @given(st.integers(min_value=1, max_value=20))
    def test_batch_consistency(self, batch_size):
        """For any batch size, batch classification should match individual results."""
        classifier = HybridClassifier(enable_vision=False)
        
        # Create batch of identical images
        images = [create_test_extracted_image(100, 100) for _ in range(batch_size)]
        
        # Classify individually
        individual_results = [classifier.classify(img) for img in images]
        
        # Classify as batch
        batch_results = classifier.classify_batch(images)
        
        assert len(batch_results) == batch_size
        
        # Results should be consistent (all identical images)
        for i in range(batch_size):
            assert individual_results[i].label == batch_results[i].label
            assert individual_results[i].confidence == batch_results[i].confidence

    @given(st.integers(min_value=0, max_value=100))
    def test_summary_statistics_validity(self, num_results):
        """For any number of results, summary statistics should be valid."""
        if num_results == 0:
            summary = HybridClassifier().get_classification_summary([])
            assert summary["total"] == 0
            return
        
        # Create mock results
        results = []
        for i in range(num_results):
            label = ["token", "card", "icon"][i % 3]
            result = ClassificationResult(label, 0.5, "heuristic", {})
            results.append(result)
        
        classifier = HybridClassifier()
        summary = classifier.get_classification_summary(results)
        
        assert summary["total"] == num_results
        assert summary["components"] + summary["non_components"] == num_results
        assert 0.0 <= summary["component_ratio"] <= 1.0
        assert 0.0 <= summary["average_confidence"] <= 1.0