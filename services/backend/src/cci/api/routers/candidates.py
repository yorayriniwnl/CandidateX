"""Candidate directory and manifest API router."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import cci.db.repository as repo
from cci.db.session import SessionLocal
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/candidates", tags=["Candidate Directory"])


class CandidateSummaryResponse(BaseModel):
    id: UUID
    display_name: str
    primary_email: str | None = None
    has_completed_dossier: bool
    rci: float | None = None
    coverage: float | None = None
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


class SaveCandidateRequest(BaseModel):
    id: str | None = None
    display_name: str
    primary_email: str | None = None
    has_completed_dossier: bool = True
    rci: float | None = None
    coverage: float | None = None
    role: str | None = None
    has_meaningful_conflict: bool = False
    created_at: str | None = None
    manifest_data: dict[str, Any] | None = None


_MEMORY_CANDIDATES: dict[UUID, CandidateSummaryResponse] = {}


@router.post(
    "",
    response_model=CandidateSummaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save a candidate profile into the HR directory",
)
def save_candidate_profile(
    req: SaveCandidateRequest,
    organization_id: UUID | None = None,
) -> CandidateSummaryResponse:
    """Saves or updates a candidate profile in the HR directory."""
    try:
        cand_id = UUID(req.id) if req.id else uuid4()
    except (ValueError, TypeError):
        cand_id = uuid4()

    created_at_str = req.created_at or datetime.now(timezone.utc).isoformat()
    summary = CandidateSummaryResponse(
        id=cand_id,
        display_name=req.display_name,
        primary_email=req.primary_email,
        has_completed_dossier=req.has_completed_dossier,
        rci=req.rci,
        coverage=req.coverage,
        role=req.role,
        has_meaningful_conflict=req.has_meaningful_conflict,
        created_at=created_at_str,
    )
    _MEMORY_CANDIDATES[cand_id] = summary

    try:
        with SessionLocal() as db:
            org_id = organization_id or UUID("00000000-0000-0000-0000-000000000001")
            existing_org = db.get(repo.models.Organization, org_id)
            if not existing_org:
                repo.save_organization(db, name="Default Org", slug="default", org_id=org_id)
            from cci.domain.contracts import CandidateManifest as DomainManifest
            manifest_dict = req.manifest_data or {
                "candidate_id": str(cand_id),
                "full_name": req.display_name,
                "display_name": req.display_name,
                "email": req.primary_email,
                "github_urls": [],
                "portfolio_urls": [],
                "deployment_urls": [],
                "declared_skills": [],
                "extraction_metadata": {},
            }
            manifest_obj = DomainManifest.model_validate(manifest_dict)
            repo.save_candidate(db, organization_id=org_id, manifest=manifest_obj, candidate_id=cand_id)
            db.commit()
    except Exception:
        pass

    return summary


@router.get(
    "",
    response_model=list[CandidateSummaryResponse],
    status_code=status.HTTP_200_OK,
    summary="List all candidates with evaluation and dossier summary",
)
def list_candidates(
    organization_id: UUID | None = None,
) -> list[CandidateSummaryResponse]:
    """Lists candidates along with their latest evaluation score summary."""
    try:
        with SessionLocal() as db:
            cands = repo.list_candidates(db, organization_id=organization_id)
            summaries = []
            db_ids = set()
            for c in cands:
                db_ids.add(c.id)
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
                        coverage=coverage,
                        role=role_val,
                        has_meaningful_conflict=has_conflict,
                        created_at=c.created_at.isoformat()
                        if hasattr(c, "created_at") and c.created_at
                        else "",
                    )
                )
            for mem_cand in _MEMORY_CANDIDATES.values():
                if mem_cand.id not in db_ids:
                    summaries.append(mem_cand)
            return summaries
    except Exception:
        return list(_MEMORY_CANDIDATES.values())


@router.get(
    "/{candidate_id}",
    response_model=CandidateDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get detailed candidate manifest and intake records",
)
def get_candidate(candidate_id: UUID) -> CandidateDetailResponse:
    """Retrieves candidate manifest details."""
    try:
        with SessionLocal() as db:
            cand = repo.get_candidate_by_id(db, candidate_id)
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
