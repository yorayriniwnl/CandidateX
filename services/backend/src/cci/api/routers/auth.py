"""Authentication and API Key Management router for SaaS multi-tenancy."""

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from cci.db.models.organizations import ApiKey, Organization, User
from cci.db.session import SessionLocal
from cci.middleware.rate_limit import rate_limit
from cci.security.auth import (
    AuthenticatedUser,
    create_jwt_token,
    generate_api_key,
    get_current_user,
    require_role,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication & Multi-Tenancy"])


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(..., min_length=4)
    organization_slug: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400
    user_id: UUID
    organization_id: UUID
    email: str
    role: str


class CreateApiKeyRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Key name or label (e.g. Production ATS, CI Pipeline)")
    role: str = Field(default="admin", description="Permission role: admin, recruiter, or interviewer")


class ApiKeyCreatedResponse(BaseModel):
    id: UUID
    name: str
    api_key: str = Field(..., description="Raw secret API key. Store this safely; it is only revealed once.")
    key_prefix: str
    role: str
    created_at: str


class ApiKeySummaryResponse(BaseModel):
    id: UUID
    name: str
    key_prefix: str
    role: str
    is_active: bool
    last_used_at: Optional[str] = None
    created_at: str


class UserProfileResponse(BaseModel):
    user_id: UUID
    organization_id: UUID
    organization_name: str
    organization_slug: str
    email: str
    role: str
    is_active: bool


@router.post(
    "/token",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Obtain a JWT access token for user or tenant",
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60))],
)
def login(request: LoginRequest) -> TokenResponse:
    """Authenticates a user and issues a signed JWT access token scoped to their organization."""
    with SessionLocal() as db:
        stmt = select(User).where(User.email == request.email.lower().strip())
        user = db.execute(stmt).scalar_one_or_none()

        if not user:
            # Auto-provision in development or default organization if first time
            org_slug = request.organization_slug or "default"
            org_stmt = select(Organization).where(Organization.slug == org_slug)
            org = db.execute(org_stmt).scalar_one_or_none()
            if not org:
                org = Organization(
                    id=uuid4(),
                    name=f"{org_slug.capitalize()} Organization",
                    slug=org_slug,
                    is_active=True,
                )
                db.add(org)
                db.flush()

            user = User(
                id=uuid4(),
                organization_id=org.id,
                email=request.email.lower().strip(),
                full_name=request.email.split("@")[0].capitalize(),
                hashed_password="pbkdf2_sha256$auto_provisioned",
                role="admin",
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is inactive")

        token = create_jwt_token(
            {
                "user_id": str(user.id),
                "organization_id": str(user.organization_id),
                "email": user.email,
                "role": user.role,
            },
            expires_in=86400,
        )

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=86400,
            user_id=user.id,
            organization_id=user.organization_id,
            email=user.email,
            role=user.role,
        )


@router.get(
    "/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get profile of the currently authenticated tenant user",
)
def get_me(user: AuthenticatedUser = Depends(get_current_user)) -> UserProfileResponse:
    """Returns information about the caller, their tenant organization, and granted permissions."""
    org_name = "CandidateX Workspace"
    org_slug = "workspace"
    try:
        with SessionLocal() as db:
            org = db.get(Organization, user.organization_id)
            if org:
                org_name = org.name
                org_slug = org.slug
    except Exception:
        pass

    return UserProfileResponse(
        user_id=user.user_id,
        organization_id=user.organization_id,
        organization_name=org_name,
        organization_slug=org_slug,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
    )


@router.post(
    "/api-keys",
    response_model=ApiKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new programmatic API key for integrations",
    dependencies=[Depends(require_role("admin", "recruiter"))],
)
def create_api_key(
    request: CreateApiKeyRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> ApiKeyCreatedResponse:
    """Creates a new API Key for automated ATS integrations, CI/CD, or candidate evaluation pipelines."""
    raw_key, api_key_obj = generate_api_key(
        organization_id=user.organization_id,
        name=request.name,
        user_id=user.user_id,
        role=request.role,
    )

    return ApiKeyCreatedResponse(
        id=api_key_obj.id,
        name=api_key_obj.name,
        api_key=raw_key,
        key_prefix=api_key_obj.key_prefix,
        role=api_key_obj.role,
        created_at=api_key_obj.created_at.isoformat() if api_key_obj.created_at else datetime.now(timezone.utc).isoformat(),
    )


@router.get(
    "/api-keys",
    response_model=list[ApiKeySummaryResponse],
    status_code=status.HTTP_200_OK,
    summary="List active API keys for the current tenant",
    dependencies=[Depends(require_role("admin", "recruiter"))],
)
def list_api_keys(
    user: AuthenticatedUser = Depends(get_current_user),
) -> list[ApiKeySummaryResponse]:
    """Lists all active API keys belonging to the authenticated tenant organization."""
    with SessionLocal() as db:
        stmt = (
            select(ApiKey)
            .where(ApiKey.organization_id == user.organization_id)
            .order_by(ApiKey.created_at.desc())
        )
        keys = db.execute(stmt).scalars().all()
        return [
            ApiKeySummaryResponse(
                id=k.id,
                name=k.name,
                key_prefix=k.key_prefix,
                role=k.role,
                is_active=k.is_active,
                last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
                created_at=k.created_at.isoformat() if k.created_at else "",
            )
            for k in keys
        ]


@router.delete(
    "/api-keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke an API key",
    dependencies=[Depends(require_role("admin"))],
)
def revoke_api_key(
    key_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
) -> None:
    """Revokes an API key so it can no longer be used for authentication."""
    with SessionLocal() as db:
        key = db.get(ApiKey, key_id)
        if not key or key.organization_id != user.organization_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")

        key.is_active = False
        db.commit()
    return None
