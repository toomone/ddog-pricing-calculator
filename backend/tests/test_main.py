"""
Tests for the main FastAPI application endpoints.
"""
import pytest


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_check(self, client):
        """Test that the health endpoint returns OK."""
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestProductsEndpoint:
    """Tests for the products endpoint."""

    def test_get_products_default_region(self, client):
        """Test fetching products for the default region."""
        response = client.get("/api/products")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_products_with_region(self, client):
        """Test fetching products for a specific region."""
        response = client.get("/api/products?region=eu1")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_products_have_required_fields(self, client):
        """Test that products have all required fields."""
        response = client.get("/api/products")
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            product = data[0]
            required_fields = ["id", "product", "billing_unit", "billed_annually", "billed_month_to_month", "on_demand"]
            for field in required_fields:
                assert field in product, f"Missing field: {field}"


class TestMetadataEndpoint:
    """Tests for the metadata endpoint."""

    def test_get_metadata_default_region(self, client):
        """Test fetching metadata for the default region."""
        response = client.get("/api/metadata")
        assert response.status_code == 200
        data = response.json()
        assert "last_sync" in data
        assert "product_count" in data

    def test_get_metadata_with_region(self, client):
        """Test fetching metadata for a specific region."""
        response = client.get("/api/metadata?region=eu1")
        assert response.status_code == 200
        data = response.json()
        assert "last_sync" in data


class TestRegionsEndpoint:
    """Tests for the regions endpoint."""

    def test_get_regions(self, client):
        """Test fetching available regions."""
        response = client.get("/api/regions")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "us" in data
        assert "eu1" in data


class TestQuotesEndpoint:
    """Tests for the quotes endpoints."""

    def test_create_quote(self, client, sample_quote_data):
        """Test creating a new quote."""
        response = client.post("/api/quotes", json=sample_quote_data)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == sample_quote_data["name"]
        assert data["region"] == sample_quote_data["region"]

    def test_get_quote(self, client, sample_quote_data):
        """Test fetching a quote by ID."""
        # First create a quote
        create_response = client.post("/api/quotes", json=sample_quote_data)
        assert create_response.status_code == 200
        quote_id = create_response.json()["id"]
        
        # Then fetch it
        response = client.get(f"/api/quotes/{quote_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == quote_id

    def test_get_nonexistent_quote(self, client):
        """Test fetching a quote that doesn't exist."""
        response = client.get("/api/quotes/nonexistent-id")
        assert response.status_code == 404


class TestAllotmentsEndpoint:
    """Tests for the allotments endpoint."""

    def test_get_allotments(self, client):
        """Test fetching allotments."""
        response = client.get("/api/allotments")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_allotments_have_required_fields(self, client):
        """Test that allotments have required fields."""
        response = client.get("/api/allotments")
        assert response.status_code == 200
        data = response.json()
        
        if len(data) > 0:
            allotment = data[0]
            required_fields = ["parent_product", "allotted_product", "quantity_per_parent", "allotted_unit"]
            for field in required_fields:
                assert field in allotment, f"Missing field: {field}"

