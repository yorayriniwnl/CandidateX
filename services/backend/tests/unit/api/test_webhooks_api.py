"""Unit tests for SaaS Webhook Subscription API."""

from fastapi.testclient import TestClient
from cci.main import app

client = TestClient(app)


def test_webhook_crud():
    """Verify webhook registration, listing, and deletion."""
    # Obtain token
    token_res = client.post(
        "/api/v1/auth/token",
        json={
            "email": "integrations@hiringhub.com",
            "password": "hubpassword123",
            "organization_slug": "hiringhub",
        },
    )
    assert token_res.status_code == 200
    token = token_res.json()["access_token"]

    # 1. Register webhook
    hook_res = client.post(
        "/api/v1/webhooks",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "target_url": "https://api.github.com/webhook-sink-test",
            "secret": "supersecretkey999",
            "events": ["candidate.analyzed", "dossier.rescored"],
            "description": "Production ATS Event Sync",
        },
    )
    assert hook_res.status_code == 201
    hook_data = hook_res.json()
    hook_id = hook_data["id"]
    assert hook_data["target_url"] == "https://api.github.com/webhook-sink-test"
    assert "candidate.analyzed" in hook_data["events"]

    # 2. List webhooks
    list_res = client.get(
        "/api/v1/webhooks",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_res.status_code == 200
    hooks = list_res.json()
    assert any(h["id"] == hook_id for h in hooks)

    # 3. Test webhook ping endpoint
    test_res = client.post(
        "/api/v1/webhooks/test",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert test_res.status_code == 200

    # 4. Delete webhook
    del_res = client.delete(
        f"/api/v1/webhooks/{hook_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_res.status_code == 204
