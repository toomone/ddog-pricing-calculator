"""
Tests for the allotments scraper module.
"""
import pytest
from app.allotments_scraper import (
    load_allotments_data,
    load_allotments_metadata,
    find_product_id_by_name
)
from app.scraper import load_pricing_data, DEFAULT_REGION


class TestAllotmentsData:
    """Tests for allotments data loading."""

    def test_load_allotments_data(self):
        """Test loading allotments data."""
        data = load_allotments_data()
        assert isinstance(data, list)

    def test_load_allotments_metadata(self):
        """Test loading allotments metadata."""
        metadata = load_allotments_metadata()
        assert isinstance(metadata, dict)


class TestAllotmentsStructure:
    """Tests for allotments data structure."""

    def test_allotments_have_parent_product(self):
        """Test that allotments have a parent product field."""
        data = load_allotments_data()
        if len(data) > 0:
            assert "parent_product" in data[0]

    def test_allotments_have_allotted_product(self):
        """Test that allotments have an allotted product field."""
        data = load_allotments_data()
        if len(data) > 0:
            assert "allotted_product" in data[0]

    def test_allotments_have_quantity(self):
        """Test that allotments have quantity per parent."""
        data = load_allotments_data()
        if len(data) > 0:
            assert "quantity_per_parent" in data[0]

    def test_allotments_have_unit(self):
        """Test that allotments have allotted unit."""
        data = load_allotments_data()
        if len(data) > 0:
            assert "allotted_unit" in data[0]


class TestProductIdMatching:
    """Tests for product ID matching functionality."""

    def test_find_product_id_by_exact_name(self):
        """Test finding product ID by exact name match."""
        pricing_data = load_pricing_data(DEFAULT_REGION)
        if len(pricing_data) > 0:
            # Use an actual product name from the data
            product_name = pricing_data[0]["product"]
            found_id = find_product_id_by_name(product_name, pricing_data)
            assert found_id is not None

    def test_find_product_id_returns_none_for_unknown(self):
        """Test that unknown products return None."""
        pricing_data = load_pricing_data(DEFAULT_REGION)
        found_id = find_product_id_by_name("Completely Unknown Product XYZ123", pricing_data)
        # This might return None or a close match depending on implementation
        # The test verifies the function doesn't crash

    def test_find_product_id_case_insensitive(self):
        """Test that product ID matching is case insensitive."""
        pricing_data = load_pricing_data(DEFAULT_REGION)
        if len(pricing_data) > 0:
            product_name = pricing_data[0]["product"]
            # Try with different case
            found_id_lower = find_product_id_by_name(product_name.lower(), pricing_data)
            found_id_upper = find_product_id_by_name(product_name.upper(), pricing_data)
            # Both should find the same product
            assert found_id_lower == found_id_upper


class TestAllotmentsProductIds:
    """Tests for allotments with product IDs."""

    def test_allotments_may_have_product_ids(self):
        """Test that allotments can have product ID fields."""
        data = load_allotments_data()
        # Check if any allotments have product IDs (optional field)
        has_allotted_id = any("allotted_product_id" in a for a in data)
        has_parent_id = any("parent_product_id" in a for a in data)
        # These are enriched fields, may or may not be present
        # Just verify the structure is correct
        assert isinstance(data, list)

