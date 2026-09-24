"""Authentication API router for HR SaaS session and token management (Fix 29)."""

from uuid import UUID

from cci.security.auth import (
    TenantContext,
    create_access_token,
    get_current_tenant,
)
from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication & Multi-Tenancy"])


class TokenRequest(BaseModel):
    organization_id: UUID = Field(..., description="Organization UUID for tenant boundary")
    user_id: UUID | None = Field(None, description="Optional user/actor UUID")
    role: str = Field(default="interviewer", description="Role: admin, recruiter, interviewer")
    expires_in_seconds: int = Field(default=86400, ge=60, le=2592000, description="Token validity in seconds")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    organization_id: UUID
    user_id: UUID | None = None
    role: str


class CurrentTenantResponse(BaseModel):
    organization_id: UUID
    user_id: UUID | None = None
    role: str
    is_authenticated: bool
    subject: str


@router.post(
    "/token",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Issue an authenticated tenant session access token",
)
def issue_tenant_token(request: TokenRequest, response: Response) -> TokenResponse:
    """Issues a cryptographically signed HMAC-SHA256 JWT access token for an organization."""
    response.headers["Cache-Control"] = "no-store"
    token = create_access_token(
        organization_id=request.organization_id,
        user_id=request.user_id,
        role=request.role,
        expires_in_seconds=request.expires_in_seconds,
    )
    return TokenResponse(
        access_token=token,
        token_type="Bearer",
        expires_in=request.expires_in_seconds,
        organization_id=request.organization_id,
        user_id=request.user_id,
        role=request.role,
    )


@router.get(
    "/me",
    response_model=CurrentTenantResponse,
    status_code=status.HTTP_200_OK,
    summary="Inspect authenticated tenant and actor security context",
)
def get_authenticated_tenant(
    tenant: TenantContext = Depends(get_current_tenant),
) -> CurrentTenantResponse:
    """Returns the current server-derived organization and caller identity."""
    return CurrentTenantResponse(
        organization_id=tenant.organization_id,
        user_id=tenant.user_id,
        role=tenant.role,
        is_authenticated=tenant.is_authenticated,
        subject=tenant.subject,
    )
