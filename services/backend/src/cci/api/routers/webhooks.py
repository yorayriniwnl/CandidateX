"""Webhook Subscription and Management API router."""

from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from cci.security.auth import AuthenticatedUser, get_current_user, require_role
from cci.webhooks.dispatcher import webhook_dispatcher

router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks & Event Delivery"])


class CreateWebhookRequest(BaseModel):
    target_url: str = Field(..., description="HTTPS destination endpoint to receive JSON webhooks")
    secret: str = Field(..., min_length=8, description="Secret used to compute HMAC-SHA256 signature in X-CandidateX-Signature")
    events: List[str] = Field(
        default=["*"],
        description="Event types: candidate.analyzed, candidate.created, interview.feedback_added, or * for all",
    )
    description: str = Field(default="", max_length=200)


class WebhookResponse(BaseModel):
    id: str
    target_url: str
    events: List[str]
    description: str = ""
    is_active: bool = True


@router.post(
    "",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new webhook subscription",
    dependencies=[Depends(require_role("admin"))],
)
def create_webhook(
    request: CreateWebhookRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> WebhookResponse:
    """Registers an external webhook endpoint with SSRF verification."""
    try:
        res = webhook_dispatcher.register_webhook(
            org_id=user.organization_id,
            target_url=request.target_url,
            secret=request.secret,
            events=request.events,
            description=request.description,
        )
        return WebhookResponse(
            id=res["id"],
            target_url=res["target_url"],
            events=res["events"],
            description=request.description,
            is_active=True,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "",
    response_model=List[WebhookResponse],
    status_code=status.HTTP_200_OK,
    summary="List all registered webhooks for the tenant",
    dependencies=[Depends(require_role("admin", "recruiter"))],
)
def list_webhooks(user: AuthenticatedUser = Depends(get_current_user)) -> List[WebhookResponse]:
    """Lists active webhook subscriptions configured for the current tenant organization."""
    hooks = webhook_dispatcher.list_webhooks(user.organization_id)
    return [
        WebhookResponse(
            id=h["id"],
            target_url=h["target_url"],
            events=h.get("events", ["*"]),
            description=h.get("description", ""),
            is_active=h.get("is_active", True),
        )
        for h in hooks
    ]


@router.delete(
    "/{webhook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a webhook subscription",
    dependencies=[Depends(require_role("admin"))],
)
def delete_webhook(
    webhook_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> None:
    """Deletes a webhook subscription by ID."""
    deleted = webhook_dispatcher.delete_webhook(user.organization_id, webhook_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    return None


@router.post(
    "/test",
    summary="Send a test ping event to all registered webhooks",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role("admin"))],
)
def test_webhook(user: AuthenticatedUser = Depends(get_current_user)) -> Dict[str, Any]:
    """Dispatches a mock test event to verify end-to-end webhook delivery."""
    dispatched = webhook_dispatcher.dispatch_event(
        org_id=user.organization_id,
        event_type="test.ping",
        payload={"message": "CandidateX webhook delivery test", "version": "1.0.0"},
    )
    return {"dispatched_to_endpoints": dispatched, "status": "sent"}
