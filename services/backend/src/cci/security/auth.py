"""Authentication and Multi-Tenancy Security Controls (Fix 29).

Enforces server-derived organization identity, cryptographic session tokens,
and strict multi-tenant boundary scoping across all HR SaaS endpoints:
- Candidate list & detail
- Dossier, Evidence, Graph & Provenance
- Audit logs & Recruiter overrides
- Interview feedback
- Intelligence exports
- Pipeline analysis runs
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from fastapi import Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from cci.config import settings
from cci.db import models
from cci.db import repository as repo


class AuthenticationError(Exception):
    """Base exception for authentication failures."""
    pass


class TokenExpiredError(AuthenticationError):
    """Raised when an authentication token has expired."""
    pass


class InvalidTokenError(AuthenticationError):
    """Raised when an authentication token is malformed or invalid."""
    pass


class TenantAccessDenied(Exception):
    """Raised when a caller attempts to access another organization's resource."""
    pass


@dataclass
class TenantContext:
    """Authenticated tenant and user security context."""

    organization_id: UUID
    user_id: UUID | None = None
    role: str = "interviewer"
    is_authenticated: bool = True
    subject: str = ""
    claims: dict[str, Any] = field(default_factory=dict)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    padded = s + "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(padded.encode("utf-8"))


def create_access_token(
    organization_id: UUID | str,
    user_id: UUID | str | None = None,
    role: str = "interviewer",
    expires_in_seconds: int | None = None,
    secret_key: str | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Issues a cryptographically signed HMAC-SHA256 JWT access token."""
    key = (secret_key or settings.JWT_SECRET_KEY).encode("utf-8")
    now = int(time.time())
    ttl = (
        expires_in_seconds
        if expires_in_seconds is not None
        else settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    exp = now + ttl

    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(user_id) if user_id else f"org_agent_{organization_id}",
        "org_id": str(organization_id),
        "role": role,
        "iat": now,
        "exp": exp,
        "jti": str(uuid4()),
    }
    if user_id:
        payload["uid"] = str(user_id)
    if extra_claims:
        payload.update(extra_claims)

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    message = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(key, message, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def verify_access_token(
    token: str,
    secret_key: str | None = None,
) -> dict[str, Any]:
    """Verifies HMAC-SHA256 signature, expiration, and claims of an access token."""
    key = (secret_key or settings.JWT_SECRET_KEY).encode("utf-8")
    parts = token.strip().split(".")
    if len(parts) != 3:
        raise InvalidTokenError("Malformed authentication token format.")

    header_b64, payload_b64, sig_b64 = parts

    try:
        header_raw = _b64url_decode(header_b64)
        header = json.loads(header_raw.decode("utf-8"))
    except Exception as exc:
        raise InvalidTokenError(f"Malformed token header: {exc}") from exc

    if header.get("alg") != "HS256":
        raise InvalidTokenError(f"Unsupported token algorithm '{header.get('alg')}'.")

    # Verify signature
    message = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_sig = hmac.new(key, message, hashlib.sha256).digest()
    try:
        actual_sig = _b64url_decode(sig_b64)
    except Exception as exc:
        raise InvalidTokenError(f"Malformed token signature: {exc}") from exc

    if not hmac.compare_digest(actual_sig, expected_sig):
        raise InvalidTokenError("Invalid token signature.")

    # Decode and check claims
    try:
        payload_raw = _b64url_decode(payload_b64)
        payload = json.loads(payload_raw.decode("utf-8"))
    except Exception as exc:
        raise InvalidTokenError(f"Malformed token payload: {exc}") from exc

    exp = payload.get("exp")
    if exp is None or not isinstance(exp, (int, float)):
        raise InvalidTokenError("Token missing expiration claim.")
    if time.time() >= exp:
        raise TokenExpiredError("Authentication token has expired.")

    org_id_str = payload.get("org_id")
    if not org_id_str:
        raise InvalidTokenError("Token missing required 'org_id' organization claim.")

    try:
        UUID(org_id_str)
    except (ValueError, TypeError) as exc:
        raise InvalidTokenError("Token contains malformed 'org_id' UUID claim.") from exc

    return payload


def extract_bearer_token(request: Request) -> str | None:
    """Extracts authentication token from Authorization header, X-Tenant-Token, or cookies."""
    auth_header = request.headers.get("Authorization", "").strip()
    if auth_header:
        if auth_header.lower().startswith("bearer "):
            return auth_header[7:].strip()
        return auth_header

    x_tenant = request.headers.get("X-Tenant-Token", "").strip()
    if x_tenant:
        return x_tenant

    x_org = request.headers.get("X-Organization-Token", "").strip()
    if x_org:
        return x_org

    cookie_token = request.cookies.get("cci_token")
    if cookie_token:
        return cookie_token.strip()

    return None


def get_current_tenant(
    request: Request,
    authorization: str | None = Header(None, alias="Authorization"),
    x_tenant_token: str | None = Header(None, alias="X-Tenant-Token"),
) -> TenantContext:
    """FastAPI dependency: resolves authoritative, server-derived tenant context.

    Never trusts caller-supplied query parameters or unauthenticated request bodies
    for organization identification.
    """
    token_str = extract_bearer_token(request)

    if token_str:
        try:
            claims = verify_access_token(token_str)
            org_id = UUID(claims["org_id"])
            user_id = UUID(claims["uid"]) if "uid" in claims else None
            role = claims.get("role", "interviewer")
            sub = claims.get("sub", str(org_id))
            return TenantContext(
                organization_id=org_id,
                user_id=user_id,
                role=role,
                is_authenticated=True,
                subject=sub,
                claims=claims,
            )
        except TokenExpiredError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
                headers={"WWW-Authenticate": "Bearer error=\"invalid_token\", error_description=\"Token has expired\""},
            ) from exc
        except InvalidTokenError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
                headers={"WWW-Authenticate": "Bearer error=\"invalid_token\", error_description=\"Malformed or invalid signature\""},
            ) from exc

    # No token provided
    if getattr(settings, "AUTH_REQUIRED", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # In local development / testing mode with AUTH_REQUIRED=False:
    dev_org_id = UUID(getattr(settings, "DEFAULT_DEV_ORG_ID", "00000000-0000-0000-0000-000000000001"))
    return TenantContext(
        organization_id=dev_org_id,
        user_id=None,
        role="admin",
        is_authenticated=False,
        subject=str(dev_org_id),
        claims={"org_id": str(dev_org_id), "role": "admin", "dev_fallback": True},
    )


def verify_candidate_tenant(
    db: Session | None,
    candidate_id: UUID,
    organization_id: UUID,
    allow_unregistered: bool = False,
) -> models.Candidate | None:
    """Verifies server-side that the candidate belongs to the authenticated tenant.

    Raises HTTP 404 if the candidate does not exist or belongs to another tenant,
    strictly preventing object ID enumeration and cross-tenant data leaks.
    """
    if db is not None:
        cand = repo.get_candidate_by_id(db, candidate_id, organization_id=organization_id)
        if cand is not None:
            return cand

        # Check if candidate exists under a different organization
        other_cand = repo.get_candidate_by_id(db, candidate_id)
        if other_cand is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate {candidate_id} not found",
            )

    # In-memory dossier/graph registry check
    try:
        from cci.api.routers.dossier import _DOSSIER_ORG_MAP, _DOSSIER_STORE

        if candidate_id in _DOSSIER_STORE:
            mapped_org = _DOSSIER_ORG_MAP.get(candidate_id)
            if mapped_org is not None and mapped_org != organization_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Candidate {candidate_id} not found",
                )
            return None
    except ImportError:
        pass

    if allow_unregistered:
        return None

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Candidate {candidate_id} not found",
    )


def verify_analysis_run_tenant(
    db: Session | None,
    run_id: UUID,
    organization_id: UUID,
) -> models.AnalysisRun | None:
    """Verifies that an analysis run belongs to the authenticated tenant."""
    if db is not None:
        run = repo.get_analysis_run_by_id(db, run_id, organization_id=organization_id)
        if run is not None:
            return run

        other_run = repo.get_analysis_run_by_id(db, run_id)
        if other_run is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analysis run {run_id} not found",
            )

    # In-memory pipeline service check
    try:
        from cci.pipeline.service import pipeline_service

        state = pipeline_service.get_pipeline_state(run_id)
        if state is not None:
            if getattr(state, "organization_id", None) is not None:
                if state.organization_id != organization_id:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Analysis run {run_id} not found",
                    )
            return None
    except ImportError:
        pass

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Analysis run {run_id} not found",
    )
