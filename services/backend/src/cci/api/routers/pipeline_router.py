"""Pipeline orchestration and lifecycle management API router with multi-tenancy (Fix 29)."""

import math
from typing import Any
from uuid import UUID

import cci.db.repository as repo
from cci.db import models
from cci.db.session import SessionLocal
from cci.domain.contracts import Dossier
from cci.domain.enums import CanonicalRole, CapabilityKey, EvidenceState
from cci.pipeline.service import pipeline_service
from cci.security.auth import (
    TenantContext,
    get_current_tenant,
    verify_analysis_run_tenant,
)
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

router = APIRouter(prefix="/api/v1/pipeline", tags=["Pipeline Orchestration"])


class PipelineRunRequest(BaseModel):
    candidate_id: UUID
    role: CanonicalRole = CanonicalRole.BACKEND
    jd_text: str | None = None
    cv_text: str | None = None
    repo_urls: list[str] | None = Field(default_factory=list)
    declared_claims: list[str] | None = Field(default_factory=list)
    expert_weight_overrides: dict[CapabilityKey, float] | None = None


class StageProgressResponse(BaseModel):
    stage: str
    label: str
    status: str
    started_at: str | None = None
    completed_at: str | None = None
    details: str | None = None


class PipelineStatusResponse(BaseModel):
    analysis_run_id: UUID
    candidate_id: UUID
    role: CanonicalRole
    status: str
    current_stage: str | None = None
    stages: list[StageProgressResponse]
    dossier_id: UUID | None = None
    rci: float | None = None
    coverage: float | None = None
    coverage_sufficiency_threshold: float | None = None
    evidence_state: EvidenceState = EvidenceState.UNKNOWN
    error: str | None = None


class PipelineRescoreRequest(BaseModel):
    run_id: UUID
    weights: dict[CapabilityKey, float]
    justification: str = Field(
        default="Research demonstration weight override", min_length=3, max_length=2000
    )

    @field_validator("weights")
    @classmethod
    def validate_weights(cls, weights):
        if (
            not weights
            or any(not math.isfinite(v) or v < 0 for v in weights.values())
            or sum(weights.values()) <= 0
        ):
            raise ValueError("Supply finite non-negative weights with a positive total")
        return weights


@router.post(
    "/run",
    response_model=PipelineStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger end-to-end Candidate Capability Intelligence pipeline",
)
def run_pipeline(
    request: PipelineRunRequest,
    tenant: TenantContext = Depends(get_current_tenant),
) -> Any:
    """Executes the full 10-stage analysis pipeline scoped strictly to the authenticated tenant."""
    with SessionLocal() as db:
        cand = repo.get_candidate_by_id(db, request.candidate_id)
        if cand is not None:
            if cand.organization_id != tenant.organization_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Candidate {request.candidate_id} not found",
                )
        else:
            cand = models.Candidate(
                id=request.candidate_id,
                organization_id=tenant.organization_id,
                display_name="Candidate",
                manifest_data={"cv_text": request.cv_text},
                is_active=True,
            )
            db.add(cand)
            db.commit()

    state = pipeline_service.start_pipeline(
        candidate_id=request.candidate_id,
        role=request.role,
        jd_text=request.jd_text,
        cv_text=request.cv_text,
        repo_urls=request.repo_urls,
        declared_claims=request.declared_claims,
        expert_weight_overrides=request.expert_weight_overrides,
        organization_id=tenant.organization_id,
    )

    stage_responses = [
        StageProgressResponse(
            stage=s.stage.value,
            label=s.label,
            status=s.status,
            started_at=s.started_at,
            completed_at=s.completed_at,
            details=s.details,
        )
        for s in state.stages
    ]

    return PipelineStatusResponse(
        analysis_run_id=state.analysis_run_id,
        candidate_id=state.candidate_id,
        role=state.role,
        status=state.status.value,
        current_stage=state.current_stage.value if state.current_stage else None,
        stages=stage_responses,
        dossier_id=state.dossier.dossier_id if state.dossier else None,
        rci=state.dossier.rci if state.dossier else None,
        coverage=state.dossier.coverage if state.dossier else None,
        coverage_sufficiency_threshold=(
            state.dossier.coverage_sufficiency_threshold if state.dossier else None
        ),
        evidence_state=(
            state.dossier.evidence_state if state.dossier else EvidenceState.UNKNOWN
        ),
        error=state.error,
    )


@router.get(
    "/status/{run_id}",
    response_model=PipelineStatusResponse,
    summary="Get pipeline execution progress and result summary",
)
def get_pipeline_status(
    run_id: UUID,
    tenant: TenantContext = Depends(get_current_tenant),
) -> Any:
    """Retrieves current stage and progress for an active or completed analysis run scoped to tenant."""
    with SessionLocal() as db:
        verify_analysis_run_tenant(db, run_id, tenant.organization_id)

    state = pipeline_service.get_pipeline_state(run_id, organization_id=tenant.organization_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis run {run_id} not found",
        )

    stage_responses = [
        StageProgressResponse(
            stage=s.stage.value,
            label=s.label,
            status=s.status,
            started_at=s.started_at,
            completed_at=s.completed_at,
            details=s.details,
        )
        for s in state.stages
    ]

    return PipelineStatusResponse(
        analysis_run_id=state.analysis_run_id,
        candidate_id=state.candidate_id,
        role=state.role,
        status=state.status.value,
        current_stage=state.current_stage.value if state.current_stage else None,
        stages=stage_responses,
        dossier_id=state.dossier.dossier_id if state.dossier else None,
        rci=state.dossier.rci if state.dossier else None,
        coverage=state.dossier.coverage if state.dossier else None,
        coverage_sufficiency_threshold=(
            state.dossier.coverage_sufficiency_threshold if state.dossier else None
        ),
        evidence_state=(
            state.dossier.evidence_state if state.dossier else EvidenceState.UNKNOWN
        ),
        error=state.error,
    )


@router.post(
    "/rescore",
    response_model=Dossier,
    summary="Pure functional rescore of candidate dossier with expert weights",
)
def rescore_pipeline(
    request: PipelineRescoreRequest,
    tenant: TenantContext = Depends(get_current_tenant),
) -> Any:
    """Pure functional recalculation of RCI without re-running analyzers or re-crawling, scoped to tenant."""
    with SessionLocal() as db:
        verify_analysis_run_tenant(db, request.run_id, tenant.organization_id)

    rescored = pipeline_service.rescore_run(
        run_id=request.run_id,
        new_weights=request.weights,
        justification=request.justification,
        organization_id=tenant.organization_id,
    )
    if not rescored:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis run {request.run_id} or dossier not found",
        )
    return rescored
