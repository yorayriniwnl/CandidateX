"""Unit tests for healthz endpoint."""

from fastapi.testclient import TestClient
from cci.main import app

client = TestClient(app)


def test_healthz_endpoint():
    """Verify /healthz returns 200 OK and healthy status."""
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "cci-backend"
    assert "version" in data
    assert "timestamp" in data
