"""
Property-based and unit tests for output packaging functionality.

**Feature: pdf-component-extractor, Property 12: Directory Structure Consistency**
**Feature: pdf-component-extractor, Property 13: Category Mapping Determinism**
"""

import tempfile
from pathlib import Path
from typing import List

import pytest
from hypothesis import given, strategies as st

from src.hephaestus.output.package import (
    normalize_category,
    create_directory_structure,
    package_exports,
    PackageResult
)
from src.hephaestus.output.manifest import ManifestItem


class TestCategoryMapping:
    """Test category mapping functionality."""
    
    def test_normalize_category_known_labels(self):
        """Test that known classification labels map to expected categories."""
        assert normalize_category("card") == "cards"
        assert normalize_category("token") == "tokens"
        assert normalize_category("board") == "boards"
        assert normalize_category("tile") == "tiles"
        assert normalize_category("dice") == "dice"
        assert normalize_category("non-component") == "non_components"
        assert normalize_category("non_component") == "non_components"
    
    def test_normalize_category_unknown_labels(self):
        """Test that unknown labels map to 'unknown' category."""
        assert normalize_category("unknown_label") == "unknown"
        assert normalize_category("") == "unknown"
        assert normalize_category("random") == "unknown"
    
    @given(st.text())
    def test_category_mapping_determinism(self, classification_label: str):
        """
        **Feature: pdf-component-extractor, Property 13: Category Mapping Determinism**
        For any classification label, the category mapping should be consistent and deterministic.
        """
        # The function should always return the same result for the same input
        result1 = normalize_category(classification_label)
        result2 = normalize_category(classification_label)
        assert result1 == result2
        
        # Result should always be a valid category name
        valid_categories = {"cards", "tokens", "boards", "tiles", "dice", "non_components", "unknown"}
        assert result1 in valid_categories


class TestDirectoryStructure:
    """Test directory structure creation."""
    
    @given(
        categories=st.sets(st.sampled_from(["cards", "tokens", "boards", "tiles", "dice", "unknown", "non_components"]), min_size=1),
        export_mode=st.sampled_from(["all", "canonicals-only"]),
        include_non_components=st.booleans()
    )
    def test_directory_structure_consistency(self, categories, export_mode, include_non_components):
        """
        **Feature: pdf-component-extractor, Property 12: Directory Structure Consistency**
        For any packaging operation, the created directory structure should match the expected taxonomy.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Create directory structure
            all_dir, canonicals_dir, duplicates_dir = create_directory_structure(
                output_dir, categories, export_mode, include_non_components
            )
            
            # Verify base directory structure
            assert all_dir.exists()
            assert all_dir == output_dir / "images" / "all"
            assert canonicals_dir.exists()
            assert canonicals_dir == output_dir / "images" / "canonicals"
            
            # Verify duplicates directory based on export mode
            if export_mode == "all":
                assert duplicates_dir.exists()
                assert duplicates_dir == output_dir / "images" / "duplicates"
            else:
                # duplicates_dir is returned but may not exist for canonicals-only
                assert duplicates_dir == output_dir / "images" / "duplicates"
            
            # Verify category subdirectories
            expected_categories = categories.copy()
            if not include_non_components:
                expected_categories.discard("non_components")
            
            for category in expected_categories:
                canonical_category_dir = canonicals_dir / category
                assert canonical_category_dir.exists(), f"Canonical category dir {category} should exist"
                
                if export_mode == "all":
                    duplicate_category_dir = duplicates_dir / category
                    assert duplicate_category_dir.exists(), f"Duplicate category dir {category} should exist"
            
            # Verify non_components handling
            if "non_components" in categories:
                non_comp_canonical = canonicals_dir / "non_components"
                if include_non_components:
                    assert non_comp_canonical.exists()
                else:
                    assert not non_comp_canonical.exists()


class TestPackageExports:
    """Test the main package_exports function."""
    
    def create_test_manifest_item(self, image_id: str, classification: str, is_duplicate: bool = False) -> ManifestItem:
        """Helper to create test manifest items."""
        return ManifestItem(
            image_id=image_id,
            file_name=f"component_{image_id}.png",
            page_index=0,
            classification=classification,
            classification_confidence=0.8,
            label=None,
            quantity=None,
            metadata_confidence=0.0,
            dimensions={"width": 100, "height": 100},
            bbox=None,
            dedup_group_id=None,
            is_duplicate=is_duplicate,
            canonical_image_id=image_id if not is_duplicate else "canonical_id",
            file_path=None
        )
    
    def test_package_exports_basic_functionality(self):
        """Test basic packaging functionality with simple inputs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Create images/all/ directory and test files
            all_dir = output_dir / "images" / "all"
            all_dir.mkdir(parents=True)
            
            # Create test manifest items
            manifest_items = [
                self.create_test_manifest_item("img1", "card", is_duplicate=False),
                self.create_test_manifest_item("img2", "token", is_duplicate=True),
            ]
            
            # Create test image files
            for item in manifest_items:
                test_file = all_dir / f"component_{item.image_id}.png"
                test_file.write_text("fake image data")
            
            # Run packaging
            updated_items, result = package_exports(
                output_dir, manifest_items, "all", False
            )
            
            # Verify results
            assert len(updated_items) == 2
            assert result.exported_primary == 1  # One canonical
            assert result.exported_duplicates == 1  # One duplicate
            
            # Verify path fields are set correctly
            canonical_item = next(item for item in updated_items if not item.is_duplicate)
            duplicate_item = next(item for item in updated_items if item.is_duplicate)
            
            assert canonical_item.path_all is not None
            assert canonical_item.path_primary is not None
            assert canonical_item.path_duplicate is None
            
            assert duplicate_item.path_all is not None
            assert duplicate_item.path_primary is None
            assert duplicate_item.path_duplicate is not None
    
    def test_canonicals_only_mode(self):
        """Test canonicals-only export mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            all_dir = output_dir / "images" / "all"
            all_dir.mkdir(parents=True)
            
            manifest_items = [
                self.create_test_manifest_item("img1", "card", is_duplicate=False),
                self.create_test_manifest_item("img2", "card", is_duplicate=True),
            ]
            
            # Create test files
            for item in manifest_items:
                test_file = all_dir / f"component_{item.image_id}.png"
                test_file.write_text("fake image data")
            
            # Run packaging in canonicals-only mode
            updated_items, result = package_exports(
                output_dir, manifest_items, "canonicals-only", False
            )
            
            # Verify only canonicals are exported to structured folders
            assert result.exported_primary == 1
            assert result.exported_duplicates == 0
            
            # Verify duplicate has no structured path
            duplicate_item = next(item for item in updated_items if item.is_duplicate)
            assert duplicate_item.path_duplicate is None
    
    def test_include_non_components_false(self):
        """Test that non_components are excluded when include_non_components=False."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            all_dir = output_dir / "images" / "all"
            all_dir.mkdir(parents=True)
            
            manifest_items = [
                self.create_test_manifest_item("img1", "card", is_duplicate=False),
                self.create_test_manifest_item("img2", "non-component", is_duplicate=False),
            ]
            
            # Create test files
            for item in manifest_items:
                test_file = all_dir / f"component_{item.image_id}.png"
                test_file.write_text("fake image data")
            
            # Run packaging
            updated_items, result = package_exports(
                output_dir, manifest_items, "all", False
            )
            
            # Verify non-component is not exported to structured folders
            assert result.exported_primary == 1  # Only the card
            
            # Verify non-component item has no structured paths
            non_comp_item = next(item for item in updated_items if normalize_category(item.classification) == "non_components")
            assert non_comp_item.path_primary is None
            assert non_comp_item.path_duplicate is None
            assert non_comp_item.path_all is not None  # Should still have path_all

    def test_packaging_path_consistency_regression(self):
        """
        Regression test for P0 packaging path bug.
        Ensures extraction → packaging → file existence works correctly.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Simulate the extraction flow: save_images_flat creates images/all/
            from src.hephaestus.pdf.images import ExtractedImage
            import fitz
            
            # Create a minimal test image
            test_pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 10, 10))
            test_pixmap.set_rect(test_pixmap.irect, (255, 255, 255))  # White background
            
            test_image = ExtractedImage(
                id="test_img",
                page_index=0,
                source_type="embedded",
                width=10,
                height=10,
                pixmap=test_pixmap
            )
            
            # Step 1: Save images using save_images_flat (should create images/all/)
            from src.hephaestus.pdf.images import save_images_flat
            path_mapping, health_metrics = save_images_flat([test_image], output_dir, rulebook_id="test")
            saved_paths = list(path_mapping.values())
            
            # Verify images are saved in the correct location
            expected_path = output_dir / "images" / "all" / "component_test_img.png"
            assert expected_path.exists(), f"Image should be saved at {expected_path}"
            assert len(saved_paths) == 1
            assert saved_paths[0] == expected_path
            
            # Step 2: Create manifest item and run packaging
            manifest_item = self.create_test_manifest_item("test_img", "token", is_duplicate=False)
            
            # Step 3: Run packaging (should find the file and copy it)
            updated_items, result = package_exports(
                output_dir, [manifest_item], "all", True
            )
            
            # Step 4: Verify packaging succeeded
            assert result.exported_primary == 1, "Should export 1 canonical"
            assert result.exported_duplicates == 0, "Should export 0 duplicates"
            
            # Step 5: Verify files exist at expected locations
            canonical_path = output_dir / "images" / "canonicals" / "tokens" / "component_test_img.png"
            assert canonical_path.exists(), f"Canonical should exist at {canonical_path}"
            
            # Step 6: Verify manifest paths are correct
            updated_item = updated_items[0]
            assert updated_item.path_all == "images/all/component_test_img.png"
            assert updated_item.path_primary == "images/canonicals/tokens/component_test_img.png"
            assert updated_item.path_duplicate is None


if __name__ == "__main__":
    pytest.main([__file__])