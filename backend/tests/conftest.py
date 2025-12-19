"""
Pytest configuration and fixtures for backend API tests.
"""
import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_quote_data():
    """Sample quote data for testing."""
    return {
        "name": "Test Quote",
        "region": "us",
        "billing_type": "annual",
        "items": [
            {
                "id": "test-product-id",
                "product": "Infrastructure Monitoring",
                "quantity": 10
            }
        ]
    }


@pytest.fixture
def sample_product():
    """Sample product data for testing."""
    return {
        "id": "test-id-123",
        "product": "Infrastructure Monitoring",
        "billing_unit": "per host",
        "billed_annually": "$15",
        "billed_month_to_month": "$18",
        "on_demand": "$20"
    }

