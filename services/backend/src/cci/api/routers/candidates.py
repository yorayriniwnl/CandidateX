"""Candidate directory and manifest API router with strict multi-tenancy (Fix 29)."""

from typing import Any
from uuid import UUID, uuid4

import cci.db.repository as repo
from cci.db import models
from cci.db.session import SessionLocal
from cci.domain.contracts import ObservedIndexContext
from cci.domain.enums import EvidenceState
from cci.security.auth import TenantContext, get_current_tenant
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/candidates", tags=["Candidate Directory"])


class CandidateCreateRequest(BaseModel):
    display_name: str
    primary_email: str | None = None
    manifest_data: dict[str, Any] = Field(default_factory=dict)
    candidate_id: UUID | None = None


class CandidateSummaryResponse(BaseModel):
    id: UUID
    display_name: str
    primary_email: str | None = None
    has_completed_dossier: bool
    rci: float | None = Field(
        default=None,
        description="Deprecated compatibility field; use observed_capability_index and its context",
        json_schema_extra={"deprecated": True},
    )
    observed_capability_index: float | None = None
    observed_index_context: ObservedIndexContext | None = None
    coverage: float | None = None
    coverage_sufficiency_threshold: float | None = None
    evidence_state: EvidenceState = EvidenceState.UNKNOWN
    role: str | None = None
    has_meaningful_conflict: bool = False
    created_at: str


class CandidateDetailResponse(BaseModel):
    id: UUID
    display_name: str
    primary_email: str | None = None
    manifest_data: dict[str, Any]
    is_active: bool
    created_at: str


@router.post(
    "",
    response_model=CandidateDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a candidate record scoped to the authenticated tenant",
)
def create_candidate(
    request: CandidateCreateRequest,
    tenant: TenantContext = Depends(get_current_tenant),
) -> CandidateDetailResponse:
    """Creates a candidate entity strictly bound to the authenticated organization."""
    with SessionLocal() as db:
        cid = request.candidate_id or uuid4()
        existing = repo.get_candidate_by_id(db, cid)
        if existing:
            if existing.organization_id != tenant.organization_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Candidate ID conflict.",
                )
            cand = existing
        else:
            cand = models.Candidate(
                id=cid,
                organization_id=tenant.organization_id,
                display_name=request.display_name,
                primary_email=request.primary_email,
                manifest_data=request.manifest_data,
                is_active=True,
            )
            db.add(cand)
            db.commit()
            db.refresh(cand)

        return CandidateDetailResponse(
            id=cand.id,
            display_name=cand.display_name,
            primary_email=cand.primary_email,
            manifest_data=cand.manifest_data,
            is_active=cand.is_active,
            created_at=cand.created_at.isoformat() if hasattr(cand, "created_at") and cand.created_at else "",
        )


@router.get(
    "",
    response_model=list[CandidateSummaryResponse],
    status_code=status.HTTP_200_OK,
    summary="List all candidates with evaluation and dossier summary",
)
def list_candidates(
    organization_id: UUID | None = Query(None, description="Deprecated; organization identity is derived from session/token"),
    tenant: TenantContext = Depends(get_current_tenant),
) -> list[CandidateSummaryResponse]:
    """Lists candidates along with their latest evaluation score summary scoped server-side to the authenticated tenant."""
    # Organization identity must come from authenticated session/token, not a caller-supplied query parameter.
    effective_org_id = tenant.organization_id
    try:
        with SessionLocal() as db:
            cands = repo.list_candidates(db, organization_id=effective_org_id)
            summaries = []
            for c in cands:
                try:
                    dossier = repo.get_dossier_by_candidate_id(db, c.id, organization_id=effective_org_id)
                except TypeError:
                    dossier = repo.get_dossier_by_candidate_id(db, c.id)
                has_dossier = dossier is not None
                rci = dossier.rci if dossier else None
                coverage = dossier.coverage if dossier else None
                role_val = dossier.role.value if dossier else None
                has_conflict = False
                if dossier:
                    has_conflict = any(
                        conf.has_meaningful_conflict
                        for conf in dossier.capability_conflicts.values()
                    )

                summaries.append(
                    CandidateSummaryResponse(
                        id=c.id,
                        display_name=c.display_name,
                        primary_email=c.primary_email,
                        has_completed_dossier=has_dossier,
                        rci=rci,
                        observed_capability_index=(
                            dossier.observed_capability_index if dossier else None
                        ),
                        observed_index_context=(
                            dossier.observed_index_context if dossier else None
                        ),
                        coverage=coverage,
                        coverage_sufficiency_threshold=(
                            dossier.coverage_sufficiency_threshold if dossier else None
                        ),
                        evidence_state=(
                            dossier.evidence_state if dossier else EvidenceState.UNKNOWN
                        ),
                        role=role_val,
                        has_meaningful_conflict=has_conflict,
                        created_at=c.created_at.isoformat()
                        if hasattr(c, "created_at") and c.created_at
                        else "",
                    )
                )
            return summaries
    except Exception:
        return []


@router.get(
    "/{candidate_id}",
    response_model=CandidateDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get detailed candidate manifest and intake records",
)
def get_candidate(
    candidate_id: UUID,
    tenant: TenantContext = Depends(get_current_tenant),
) -> CandidateDetailResponse:
    """Retrieves candidate manifest details strictly scoped to the authenticated organization."""
    try:
        with SessionLocal() as db:
            cand = repo.get_candidate_by_id(db, candidate_id, organization_id=tenant.organization_id)
            if not cand:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Candidate {candidate_id} not found",
                )
            return CandidateDetailResponse(
                id=cand.id,
                display_name=cand.display_name,
                primary_email=cand.primary_email,
                manifest_data=cand.manifest_data,
                is_active=cand.is_active,
                created_at=cand.created_at.isoformat()
                if hasattr(cand, "created_at") and cand.created_at
                else "",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


class CandidateDeletionResponse(BaseModel):
    candidate_id: UUID
    candidate_id_hash: str
    is_deleted: bool
    deleted_tables: list[str]
    tombstone_id: UUID
    recorded_at: str
    message: str


@router.delete(
    "/{candidate_id}",
    response_model=CandidateDeletionResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete candidate and all associated PII, documents, and evidence (GDPR Right-to-be-Forgotten)",
)
def delete_candidate_endpoint(
    candidate_id: UUID,
    reason: str = Query("candidate_request", description="Reason for candidate deletion"),
    tenant: TenantContext = Depends(get_current_tenant),
) -> CandidateDeletionResponse:
    """Executes the candidate deletion pathway, permanently removing all PII and recording a cryptographic tombstone."""
    from cci.security.privacy import delete_candidate_permanently

    try:
        with SessionLocal() as db:
            result = delete_candidate_permanently(
                db=db,
                candidate_id=candidate_id,
                organization_id=tenant.organization_id,
                requested_by=tenant.user_id or "authenticated_user",
                reason=reason,
            )
            return CandidateDeletionResponse(**result.model_dump())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Candidate deletion failed: {exc}",
        ) from exc

