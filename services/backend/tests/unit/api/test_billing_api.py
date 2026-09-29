"""Unit tests for SaaS Billing and Usage Metering API."""

from fastapi.testclient import TestClient
from cci.main import app

client = TestClient(app)


def test_billing_plans_list():
    """Verify that GET /api/v1/billing/plans returns all pricing tiers."""
    res = client.get("/api/v1/billing/plans")
    assert res.status_code == 200
    data = res.json()
    assert "plans" in data
    assert "free" in data["plans"]
    assert "starter" in data["plans"]
    assert "pro" in data["plans"]
    assert "enterprise" in data["plans"]
    assert data["plans"]["pro"]["monthly_analyses_limit"] == 500


def test_billing_usage_and_upgrade():
    """Verify organization usage retrieval and tier upgrades."""
    # Obtain token
    token_res = client.post(
        "/api/v1/auth/token",
        json={
            "email": "cfo@fintechgroup.io",
            "password": "cfopassword123",
            "organization_slug": "fintechgroup",
        },
    )
    assert token_res.status_code == 200
    token = token_res.json()["access_token"]

    # Check initial usage
    usage_res = client.get(
        "/api/v1/billing/usage",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert usage_res.status_code == 200
    usage_data = usage_res.json()
    assert "analyses_used" in usage_data
    assert "analyses_limit" in usage_data
    assert "billing_cycle" in usage_data

    # Upgrade to Enterprise tier
    upgrade_res = client.post(
        "/api/v1/billing/upgrade",
        headers={"Authorization": f"Bearer {token}"},
        json={"plan_key": "enterprise"},
    )
    assert upgrade_res.status_code == 200
    assert upgrade_res.json()["new_plan"] == "enterprise"

    # Verify updated usage reflects Enterprise quota
    updated_usage_res = client.get(
        "/api/v1/billing/usage",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert updated_usage_res.status_code == 200
    assert updated_usage_res.json()["analyses_limit"] == 10000
