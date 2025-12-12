"""Tests for spatial text index."""

import pytest
from hypothesis import given, strategies as st

from hephaestus.text.spatial import TextSpan, BBox
from hephaestus.text.index import SpatialTextIndex, SpatialQuery


def create_test_spans() -> list[TextSpan]:
    """Create a set of test text spans for testing."""
    return [
        TextSpan(0, "Top left", BBox(10, 10, 50, 30), "span"),
        TextSpan(0, "Top right", BBox(100, 10, 140, 30), "span"),
        TextSpan(0, "Bottom left", BBox(10, 100, 50, 120), "span"),
        TextSpan(0, "Bottom right", BBox(100, 100, 140, 120), "span"),
        TextSpan(0, "Center", BBox(60, 60, 90, 80), "span"),
        TextSpan(1, "Page 2 text", BBox(20, 20, 60, 40), "span"),
    ]


class TestSpatialTextIndex:
    def test_index_creation(self):
        """Test spatial index creation and basic properties."""
        spans = create_test_spans()
        index = SpatialTextIndex(spans)
        
        assert index.get_total_span_count() == 6
        assert index.get_page_count() == 2
        
        page_0_spans = index.get_page_spans(0)
        page_1_spans = index.get_page_spans(1)
        
        assert len(page_0_spans) == 5
        assert len(page_1_spans) == 1

    def test_spatial_query_intersection(self):
        """Test spatial queries with bounding box intersection."""
        spans = create_test_spans()
        index = SpatialTextIndex(spans)
        
        # Query near top-left area
        query = SpatialQuery(
            page_index=0,
            bbox=BBox(0, 0, 20, 20),
            expand=15.0
        )
        
        results = index.query(query)
        
        # Should find "Top left" span
        assert len(results) >= 1
        assert any("Top left" in span.text for span in results)

    def test_spatial_query_no_intersection(self):
        """Test spatial queries with no intersections."""
        spans = create_test_spans()
        index = SpatialTextIndex(spans)
        
        # Query in empty area with no expansion
        query = SpatialQuery(
            page_index=0,
            bbox=BBox(200, 200, 220, 220),
            expand=0.0
        )
        
        results = index.query(query)
        
        # Should find no spans
        assert len(results) == 0

    def test_spatial_query_with_expansion(self):
        """Test that expansion parameter affects results."""
        spans = create_test_spans()
        index = SpatialTextIndex(spans)
        
        # Query near center but not intersecting
        query_no_expand = SpatialQuery(
            page_index=0,
            bbox=BBox(45, 45, 55, 55),
            expand=0.0
        )
        
        query_with_expand = SpatialQuery(
            page_index=0,
            bbox=BBox(45, 45, 55, 55),
            expand=20.0
        )
        
        results_no_expand = index.query(query_no_expand)
        results_with_expand = index.query(query_with_expand)
        
        # Expansion should find more spans
        assert len(results_with_expand) >= len(results_no_expand)

    def test_query_nearest(self):
        """Test nearest neighbor queries."""
        spans = create_test_spans()
        index = SpatialTextIndex(spans)
        
        # Query from center position
        query = SpatialQuery(
            page_index=0,
            bbox=BBox(75, 65, 85, 75),  # Near center
            expand=0.0
        )
        
        nearest = index.query_nearest(query, max_results=3)
        
        assert len(nearest) <= 3
        assert len(nearest) > 0
        
        # Results should be sorted by distance (closest first)
        # Center span should be first
        assert "Center" in nearest[0].text

    def test_page_isolation(self):
        """Test that queries are isolated to specific pages."""
        spans = create_test_spans()
        index = SpatialTextIndex(spans)
        
        # Query page 1
        query = SpatialQuery(
            page_index=1,
            bbox=BBox(0, 0, 200, 200),
            expand=50.0
        )
        
        results = index.query(query)
        
        # Should only find spans from page 1
        assert all(span.page_index == 1 for span in results)
        assert len(results) == 1
        assert "Page 2 text" in results[0].text

    def test_empty_index(self):
        """Test behavior with empty index."""
        index = SpatialTextIndex([])
        
        assert index.get_total_span_count() == 0
        assert index.get_page_count() == 0
        
        query = SpatialQuery(
            page_index=0,
            bbox=BBox(0, 0, 10, 10),
            expand=10.0
        )
        
        results = index.query(query)
        assert len(results) == 0

    def test_statistics(self):
        """Test index statistics generation."""
        spans = create_test_spans()
        index = SpatialTextIndex(spans)
        
        stats = index.get_statistics()
        
        assert stats["total_spans"] == 6
        assert stats["page_count"] == 2
        assert 0 in stats["spans_per_page"]
        assert 1 in stats["spans_per_page"]
        assert stats["spans_per_page"][0] == 5
        assert stats["spans_per_page"][1] == 1
        
        # All test spans are "span" source type
        assert stats["source_distribution"]["span"] == 6


class TestSpatialQueryProperties:
    """Property-based tests for spatial queries."""

    @given(
        page_index=st.integers(min_value=0, max_value=5),
        x0=st.floats(min_value=0, max_value=100),
        y0=st.floats(min_value=0, max_value=100),
        width=st.floats(min_value=1, max_value=50),
        height=st.floats(min_value=1, max_value=50),
        expand=st.floats(min_value=0, max_value=20)
    )
    def test_query_determinism(self, page_index, x0, y0, width, height, expand):
        """For any query parameters, results should be deterministic."""
        spans = create_test_spans()
        index = SpatialTextIndex(spans)
        
        query = SpatialQuery(
            page_index=page_index,
            bbox=BBox(x0, y0, x0 + width, y0 + height),
            expand=expand
        )
        
        # Run query multiple times
        results1 = index.query(query)
        results2 = index.query(query)
        
        # Results should be identical
        assert len(results1) == len(results2)
        
        for r1, r2 in zip(results1, results2):
            assert r1.text == r2.text
            assert r1.page_index == r2.page_index
            assert r1.bbox == r2.bbox

    @given(
        expand1=st.floats(min_value=0, max_value=10),
        expand2=st.floats(min_value=0, max_value=10)
    )
    def test_expansion_monotonicity(self, expand1, expand2):
        """Larger expansion should never return fewer results."""
        spans = create_test_spans()
        index = SpatialTextIndex(spans)
        
        # Ensure expand2 >= expand1
        if expand2 < expand1:
            expand1, expand2 = expand2, expand1
        
        query1 = SpatialQuery(
            page_index=0,
            bbox=BBox(50, 50, 60, 60),
            expand=expand1
        )
        
        query2 = SpatialQuery(
            page_index=0,
            bbox=BBox(50, 50, 60, 60),
            expand=expand2
        )
        
        results1 = index.query(query1)
        results2 = index.query(query2)
        
        # Larger expansion should find at least as many results
        assert len(results2) >= len(results1)

    @given(
        max_results=st.integers(min_value=1, max_value=10)
    )
    def test_nearest_query_limits(self, max_results):
        """Nearest queries should respect max_results parameter."""
        spans = create_test_spans()
        index = SpatialTextIndex(spans)
        
        query = SpatialQuery(
            page_index=0,
            bbox=BBox(75, 65, 85, 75),
            expand=0.0
        )
        
        results = index.query_nearest(query, max_results=max_results)
        
        # Should not exceed max_results
        assert len(results) <= max_results
        
        # Should not exceed total spans on page
        page_span_count = len(index.get_page_spans(0))
        assert len(results) <= page_span_count


class TestSpatialQuery:
    def test_spatial_query_immutability(self):
        """Test that SpatialQuery is properly immutable."""
        bbox = BBox(0, 0, 10, 10)
        query = SpatialQuery(
            page_index=0,
            bbox=bbox,
            expand=5.0
        )
        
        # Should not be able to modify fields
        with pytest.raises(AttributeError):
            query.page_index = 1  # type: ignore
        
        with pytest.raises(AttributeError):
            query.expand = 10.0  # type: ignore

    def test_spatial_query_properties(self):
        """Test SpatialQuery property access."""
        bbox = BBox(10, 20, 30, 40)
        query = SpatialQuery(
            page_index=2,
            bbox=bbox,
            expand=15.0
        )
        
        assert query.page_index == 2
        assert query.bbox == bbox
        assert query.expand == 15.0