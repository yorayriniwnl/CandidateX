"""Unit tests for SaaS Authentication and API Key management router."""

from fastapi.testclient import TestClient
from cci.main import app

client = TestClient(app)


def test_auth_token_issuance():
    """Verify that POST /api/v1/auth/token generates a valid JWT token."""
    res = client.post(
        "/api/v1/auth/token",
        json={
            "email": "sarah.connor@cyberdyne.ai",
            "password": "supersecurepassword123",
            "organization_slug": "cyberdyne",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["email"] == "sarah.connor@cyberdyne.ai"
    assert data["role"] == "admin"
    assert data["expires_in"] > 0


def test_auth_me_profile():
    """Verify that GET /api/v1/auth/me returns authenticated user identity."""
    # Obtain token first
    token_res = client.post(
        "/api/v1/auth/token",
        json={
            "email": "recruiter@techcorp.io",
            "password": "securepassword456",
            "organization_slug": "techcorp",
        },
    )
    assert token_res.status_code == 200
    token = token_res.json()["access_token"]

    # Call /me with Bearer token
    me_res = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    profile = me_res.json()
    assert profile["email"] == "recruiter@techcorp.io"
    assert profile["role"] == "admin"
    assert "organization_id" in profile


def test_api_key_lifecycle():
    """Verify end-to-end API Key creation, listing, and validation."""
    # Obtain user token
    token_res = client.post(
        "/api/v1/auth/token",
        json={
            "email": "devops@cloudscale.net",
            "password": "devopspassword789",
            "organization_slug": "cloudscale",
        },
    )
    assert token_res.status_code == 200
    token = token_res.json()["access_token"]

    # 1. Create API key
    create_res = client.post(
        "/api/v1/auth/api-keys",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "GitHub Actions ATS Sync", "role": "admin"},
    )
    assert create_res.status_code == 201
    key_data = create_res.json()
    raw_api_key = key_data["api_key"]
    key_id = key_data["id"]
    assert raw_api_key.startswith("cx_live_")
    assert key_data["name"] == "GitHub Actions ATS Sync"

    # 2. Authenticate using the new API key in X-API-Key header
    api_auth_res = client.get(
        "/api/v1/auth/me",
        headers={"X-API-Key": raw_api_key},
    )
    assert api_auth_res.status_code == 200

    # 3. List API keys
    list_res = client.get(
        "/api/v1/auth/api-keys",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_res.status_code == 200
    keys = list_res.json()
    assert any(k["id"] == key_id for k in keys)

    # 4. Revoke API key
    del_res = client.delete(
        f"/api/v1/auth/api-keys/{key_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_res.status_code == 204

    # 5. Verify revoked API key is rejected
    revoked_res = client.get(
        "/api/v1/auth/me",
        headers={"X-API-Key": raw_api_key},
    )
    assert revoked_res.status_code == 401
