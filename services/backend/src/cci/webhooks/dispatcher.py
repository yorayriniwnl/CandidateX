"""SaaS Webhook Event Dispatcher with SSRF-safe delivery and HMAC-SHA256 signature verification."""

import hashlib
import hmac
import json
import time
from typing import Any, Dict, List
from uuid import UUID, uuid4

import httpx

from cci.db.models.organizations import Organization
from cci.db.session import SessionLocal
from cci.logging_config import get_logger
from cci.security.ssrf import validate_safe_url

logger = get_logger(__name__)


def generate_event_signature(payload_bytes: bytes, secret: str) -> str:
    """Computes HMAC-SHA256 signature for outgoing webhook payload."""
    return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()


class WebhookDispatcher:
    """Dispatches asynchronous or threadpool webhook events to customer endpoints."""

    def register_webhook(
        self,
        org_id: UUID,
        target_url: str,
        secret: str,
        events: List[str],
        description: str = "",
    ) -> Dict[str, Any]:
        """Registers a new webhook subscription in the organization's settings."""
        # Pre-validate target URL against SSRF
        validate_safe_url(target_url)

        webhook_id = str(uuid4())
        webhook_entry = {
            "id": webhook_id,
            "target_url": target_url,
            "secret": secret,
            "events": events,
            "description": description,
            "is_active": True,
            "created_at": time.time(),
        }

        with SessionLocal() as db:
            org = db.get(Organization, org_id)
            if not org:
                raise ValueError("Organization not found")

            settings_dict = dict(org.settings or {})
            webhooks = settings_dict.setdefault("webhooks", [])
            webhooks.append(webhook_entry)
            org.settings = dict(settings_dict)
            db.commit()

        return {
            "id": webhook_id,
            "target_url": target_url,
            "events": events,
            "is_active": True,
        }

    def list_webhooks(self, org_id: UUID) -> List[Dict[str, Any]]:
        """Lists active webhook subscriptions for the organization."""
        with SessionLocal() as db:
            org = db.get(Organization, org_id)
            if not org or not org.settings:
                return []
            webhooks = org.settings.get("webhooks", [])
            return [
                {
                    "id": w["id"],
                    "target_url": w["target_url"],
                    "events": w.get("events", ["*"]),
                    "description": w.get("description", ""),
                    "is_active": w.get("is_active", True),
                }
                for w in webhooks
            ]

    def delete_webhook(self, org_id: UUID, webhook_id: str) -> bool:
        """Deletes a webhook subscription."""
        with SessionLocal() as db:
            org = db.get(Organization, org_id)
            if not org or not org.settings:
                return False

            settings_dict = dict(org.settings or {})
            webhooks = settings_dict.get("webhooks", [])
            initial_len = len(webhooks)
            filtered = [w for w in webhooks if w["id"] != str(webhook_id)]

            if len(filtered) < initial_len:
                settings_dict["webhooks"] = filtered
                org.settings = dict(settings_dict)
                db.commit()
                return True
            return False

    def dispatch_event(self, org_id: UUID, event_type: str, payload: Dict[str, Any]) -> int:
        """Dispatches an event to all matching registered webhook endpoints for the organization."""
        webhooks_to_call = []
        with SessionLocal() as db:
            org = db.get(Organization, org_id)
            if not org or not org.settings:
                return 0
            webhooks = org.settings.get("webhooks", [])
            for w in webhooks:
                if not w.get("is_active", True):
                    continue
                subscribed = w.get("events", ["*"])
                if "*" in subscribed or event_type in subscribed:
                    webhooks_to_call.append(w)

        if not webhooks_to_call:
            return 0

        event_envelope = {
            "id": str(uuid4()),
            "event": event_type,
            "timestamp": int(time.time()),
            "organization_id": str(org_id),
            "data": payload,
        }
        body_bytes = json.dumps(event_envelope, default=str).encode("utf-8")

        sent_count = 0
        for hook in webhooks_to_call:
            target_url = hook["target_url"]
            secret = hook.get("secret", "")
            sig = generate_event_signature(body_bytes, secret)

            headers = {
                "Content-Type": "application/json",
                "User-Agent": "CandidateX-Webhook/1.0",
                "X-CandidateX-Event": event_type,
                "X-CandidateX-Signature": sig,
            }

            try:
                # SSRF safeguard on every dispatch
                validate_safe_url(target_url)
                with httpx.Client(timeout=5.0) as client:
                    resp = client.post(target_url, content=body_bytes, headers=headers)
                    if resp.is_success:
                        sent_count += 1
                    else:
                        logger.warning(
                            "Webhook delivery failed",
                            extra={"url": target_url, "status_code": resp.status_code, "event": event_type},
                        )
            except Exception as e:
                logger.warning(
                    "Webhook delivery error",
                    extra={"url": target_url, "error": str(e), "event": event_type},
                )

        return sent_count


webhook_dispatcher = WebhookDispatcher()
