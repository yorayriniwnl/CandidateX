"""Billing, Quota, and Subscription API router."""

from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from cci.billing.service import PLANS, billing_service
from cci.security.auth import AuthenticatedUser, get_current_user, require_role

router = APIRouter(prefix="/api/v1/billing", tags=["Billing & Quota Management"])


class UpgradePlanRequest(BaseModel):
    plan_key: str = Field(..., description="Target plan: starter, pro, enterprise")


class PlanInfoResponse(BaseModel):
    plans: Dict[str, Any]


@router.get(
    "/usage",
    summary="Get current billing cycle usage, quotas, and tier limits",
    status_code=status.HTTP_200_OK,
)
def get_usage(user: AuthenticatedUser = Depends(get_current_user)) -> Dict[str, Any]:
    """Retrieves usage statistics, analyses consumed, and remaining quota for the caller's organization."""
    return billing_service.get_usage_summary(user.organization_id)


@router.get(
    "/plans",
    summary="List all available subscription plans and their quotas",
    status_code=status.HTTP_200_OK,
)
def list_plans() -> Dict[str, Any]:
    """Returns details of all SaaS plans, pricing, and capability allowances."""
    return {"plans": PLANS}


@router.post(
    "/upgrade",
    summary="Upgrade subscription plan for the organization",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_role("admin"))],
)
def upgrade_plan(
    request: UpgradePlanRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """Updates the organization plan to a higher tier and recalculates quota ceilings."""
    if request.plan_key not in PLANS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid plan '{request.plan_key}'. Choose from: {', '.join(PLANS.keys())}",
        )

    from cci.db.models.organizations import Organization
    from cci.db.session import SessionLocal

    with SessionLocal() as db:
        org = db.get(Organization, user.organization_id)
        if not org:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

        current_settings = dict(org.settings or {})
        current_settings["plan"] = request.plan_key
        org.settings = current_settings
        db.commit()

    return {
        "status": "upgraded",
        "new_plan": request.plan_key,
        "details": PLANS[request.plan_key],
        "message": f"Successfully activated {PLANS[request.plan_key]['name']} for organization.",
    }
