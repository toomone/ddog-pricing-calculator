"""
Tests for the quotes module.
"""
import pytest
import os
from app.quotes import (
    create_quote,
    get_quote,
    update_quote,
    get_price_for_product,
    QUOTES_DIR
)


class TestQuotesDirectory:
    """Tests for quotes directory setup."""

    def test_quotes_dir_exists(self):
        """Test that the quotes directory exists."""
        assert os.path.exists(QUOTES_DIR)


class TestCreateQuote:
    """Tests for quote creation."""

    def test_create_quote_returns_quote_object(self):
        """Test that create_quote returns a valid quote."""
        quote = create_quote(
            name="Test Quote",
            region="us",
            billing_type="annual",
            items=[{"product": "Test Product", "quantity": 5}]
        )
        assert quote is not None
        assert quote.id is not None
        assert quote.name == "Test Quote"
        assert quote.region == "us"
        assert quote.billing_type == "annual"

    def test_create_quote_generates_uuid(self):
        """Test that quotes get unique UUIDs."""
        quote1 = create_quote(
            name="Quote 1",
            region="us",
            billing_type="annual",
            items=[]
        )
        quote2 = create_quote(
            name="Quote 2",
            region="us",
            billing_type="annual",
            items=[]
        )
        assert quote1.id != quote2.id

    def test_create_quote_with_items(self):
        """Test creating a quote with line items."""
        items = [
            {"product": "Product A", "quantity": 10},
            {"product": "Product B", "quantity": 5}
        ]
        quote = create_quote(
            name="Quote with items",
            region="us",
            billing_type="monthly",
            items=items
        )
        assert len(quote.items) == 2


class TestGetQuote:
    """Tests for retrieving quotes."""

    def test_get_existing_quote(self):
        """Test fetching an existing quote."""
        # Create a quote first
        created = create_quote(
            name="Fetchable Quote",
            region="us",
            billing_type="annual",
            items=[]
        )
        
        # Fetch it
        fetched = get_quote(created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.name == created.name

    def test_get_nonexistent_quote(self):
        """Test fetching a quote that doesn't exist."""
        quote = get_quote("nonexistent-uuid-12345")
        assert quote is None


class TestUpdateQuote:
    """Tests for updating quotes."""

    def test_update_quote_name(self):
        """Test updating a quote's name."""
        # Create a quote
        created = create_quote(
            name="Original Name",
            region="us",
            billing_type="annual",
            items=[]
        )
        
        # Update it
        updated = update_quote(
            quote_id=created.id,
            name="Updated Name",
            region="us",
            billing_type="annual",
            items=[]
        )
        
        assert updated is not None
        assert updated.name == "Updated Name"

    def test_update_nonexistent_quote(self):
        """Test updating a quote that doesn't exist."""
        updated = update_quote(
            quote_id="nonexistent-uuid",
            name="Test",
            region="us",
            billing_type="annual",
            items=[]
        )
        assert updated is None


class TestPriceCalculation:
    """Tests for price calculation functions."""

    def test_get_price_for_product_returns_number(self):
        """Test that get_price_for_product returns a number."""
        # This tests with a product that may or may not exist
        price = get_price_for_product("Infrastructure Monitoring", "annual", "us")
        assert isinstance(price, (int, float))
        assert price >= 0

