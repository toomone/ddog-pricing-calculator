"""
Tests for the pricing scraper module.
"""
import pytest
from app.scraper import (
    load_pricing_data,
    load_metadata,
    save_pricing_data,
    save_metadata,
    get_all_regions,
    REGIONS,
    DEFAULT_REGION
)


class TestRegions:
    """Tests for region configuration."""

    def test_regions_dict_not_empty(self):
        """Test that REGIONS dictionary is not empty."""
        assert len(REGIONS) > 0

    def test_default_region_exists(self):
        """Test that the default region exists in REGIONS."""
        assert DEFAULT_REGION in REGIONS

    def test_all_regions_have_required_fields(self):
        """Test that all regions have required configuration."""
        required_fields = ["name", "url", "site"]
        for region_id, region_config in REGIONS.items():
            for field in required_fields:
                assert field in region_config, f"Region {region_id} missing field: {field}"

    def test_get_all_regions(self):
        """Test getting all regions."""
        regions = get_all_regions()
        assert isinstance(regions, dict)
        assert len(regions) > 0
        assert "us" in regions


class TestPricingDataIO:
    """Tests for pricing data loading and saving."""

    def test_load_pricing_data_default_region(self):
        """Test loading pricing data for default region."""
        data = load_pricing_data(DEFAULT_REGION)
        assert isinstance(data, list)

    def test_load_pricing_data_eu_region(self):
        """Test loading pricing data for EU region."""
        data = load_pricing_data("eu1")
        assert isinstance(data, list)

    def test_load_metadata_default_region(self):
        """Test loading metadata for default region."""
        metadata = load_metadata(DEFAULT_REGION)
        assert isinstance(metadata, dict)

    def test_metadata_has_required_fields(self):
        """Test that metadata has required fields."""
        metadata = load_metadata(DEFAULT_REGION)
        assert "last_sync" in metadata or metadata == {}
        assert "product_count" in metadata or metadata == {}


class TestPricingDataStructure:
    """Tests for pricing data structure."""

    def test_pricing_items_have_id(self):
        """Test that pricing items have an ID field."""
        data = load_pricing_data(DEFAULT_REGION)
        if len(data) > 0:
            assert "id" in data[0], "Pricing items should have an 'id' field"

    def test_pricing_items_have_product_name(self):
        """Test that pricing items have a product name."""
        data = load_pricing_data(DEFAULT_REGION)
        if len(data) > 0:
            assert "product" in data[0], "Pricing items should have a 'product' field"

    def test_pricing_items_have_prices(self):
        """Test that pricing items have price fields."""
        data = load_pricing_data(DEFAULT_REGION)
        if len(data) > 0:
            item = data[0]
            price_fields = ["billed_annually", "billed_month_to_month", "on_demand"]
            for field in price_fields:
                assert field in item, f"Pricing items should have '{field}' field"

