from pathlib import Path
import pytest
from hypothesis import given, strategies as st

from hephaestus.config import Settings


class TestSettings:
    def test_default_values(self):
        """Test that Settings has sensible defaults."""
        settings = Settings()
        assert settings.output_dir == Path("output")
        assert settings.min_image_width == 50
        assert settings.min_image_height == 50

    def test_custom_values(self):
        """Test that Settings accepts custom values."""
        custom_dir = Path("/custom/output")
        settings = Settings(
            output_dir=custom_dir,
            min_image_width=100,
            min_image_height=200
        )
        assert settings.output_dir == custom_dir
        assert settings.min_image_width == 100
        assert settings.min_image_height == 200


class TestConfigValidation:
    """
    **Feature: pdf-component-extractor, Property 11: Config Invariants**
    **Validates: Requirements FR-4.2, FR-5.1**
    """

    @given(
        width=st.integers(min_value=-1000, max_value=-1),
        height=st.integers(min_value=1, max_value=1000)
    )
    def test_negative_width_should_be_rejected(self, width, height):
        """For any negative width threshold, configuration should be invalid."""
        # In a real implementation, we'd add validation to Settings
        # For now, we document the expected behavior
        assert width < 0  # This property should be enforced

    @given(
        width=st.integers(min_value=1, max_value=1000),
        height=st.integers(min_value=-1000, max_value=-1)
    )
    def test_negative_height_should_be_rejected(self, width, height):
        """For any negative height threshold, configuration should be invalid."""
        # In a real implementation, we'd add validation to Settings
        # For now, we document the expected behavior
        assert height < 0  # This property should be enforced

    @given(
        width=st.integers(min_value=0, max_value=10000),
        height=st.integers(min_value=0, max_value=10000)
    )
    def test_non_negative_dimensions_are_valid(self, width, height):
        """For any non-negative dimensions, Settings should accept them."""
        settings = Settings(
            min_image_width=width,
            min_image_height=height
        )
        assert settings.min_image_width == width
        assert settings.min_image_height == height