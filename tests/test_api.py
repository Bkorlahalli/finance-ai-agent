"""
Integration tests for the FastAPI API endpoints.

Tests upload, transactions listing, summary, alerts, and health check.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import Base, engine


@pytest.fixture(autouse=True)
def setup_db():
    """Create and tear down test database tables."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


SAMPLE_CSV = (
    "date,description,amount,mode,reference_id\n"
    "2025-01-15,UPI-GooglePay-swiggy@paytm-SBIN,450.00,UPI,TXN_TEST_001\n"
    "2025-01-16,POS-Amazon-Electronics,12500.00,Card,TXN_TEST_002\n"
    "2025-01-17,UPI-PhonePe-uber@axisbank-Ride,350.00,UPI,TXN_TEST_003\n"
)


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestUploadEndpoint:
    """Tests for /upload endpoint."""

    def test_upload_csv(self, client):
        response = client.post(
            "/upload",
            files={"file": ("test.csv", SAMPLE_CSV, "text/csv")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["success", "partial"]
        assert data["total_processed"] == 3

    def test_upload_non_csv(self, client):
        response = client.post(
            "/upload",
            files={"file": ("test.txt", "not csv content", "text/plain")},
        )
        assert response.status_code == 400

    def test_upload_empty_file(self, client):
        response = client.post(
            "/upload",
            files={"file": ("empty.csv", "", "text/csv")},
        )
        assert response.status_code == 400


class TestTransactionsEndpoint:
    """Tests for /transactions endpoint."""

    def test_list_empty(self, client):
        response = client.get("/transactions")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_after_upload(self, client):
        # Upload first
        client.post(
            "/upload",
            files={"file": ("test.csv", SAMPLE_CSV, "text/csv")},
        )
        response = client.get("/transactions")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3


class TestSummaryEndpoint:
    """Tests for /summary endpoint."""

    def test_summary_empty(self, client):
        response = client.get("/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["total_transactions"] == 0

    def test_summary_with_data(self, client):
        client.post(
            "/upload",
            files={"file": ("test.csv", SAMPLE_CSV, "text/csv")},
        )
        response = client.get("/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["total_transactions"] == 3
        assert data["total_spending"] > 0


class TestAlertsEndpoint:
    """Tests for /alerts endpoint."""

    def test_alerts_empty(self, client):
        response = client.get("/alerts")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
