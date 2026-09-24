"""Dossier and Candidate Evidence Graph API router with multi-tenancy (Fix 29)."""

from typing import Any
from uuid import UUID

from cci.api.contracts.dossier import DossierResponse, InterviewProbesResponse
from cci.api.contracts.graph import CEGGraphResponse
from cci.db.session import SessionLocal
from cci.domain.contracts import Dossier
from cci.domain.enums import CapabilityKey
from cci.graph.ceg import CandidateEvidenceGraph
from cci.reports.exporter import generate_html_brief, generate_markdown_brief
from cci.security.auth import TenantContext, get_current_tenant, verify_candidate_tenant
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

router = APIRouter(prefix="/api/v1/dossier", tags=["Dossier & Evidence Graph"])

# In-memory registry for completed dossiers, CEGs, and tenant associations
_DOSSIER_STORE: dict[UUID, Dossier] = {}
_GRAPH_STORE: dict[UUID, CandidateEvidenceGraph] = {}
_DOSSIER_ORG_MAP: dict[UUID, UUID] = {}


def register_dossier(
    dossier: Dossier,
    graph: CandidateEvidenceGraph | None = None,
    organization_id: UUID | None = None,
) -> None:
    """Registers a completed dossier and optional CEG graph in memory with tenant binding."""
    _DOSSIER_STORE[dossier.candidate_id] = dossier
    if graph:
        _GRAPH_STORE[dossier.candidate_id] = graph
    if organization_id:
        _DOSSIER_ORG_MAP[dossier.candidate_id] = organization_id


def unregister_dossier(candidate_id: UUID) -> None:
    """Evicts in-memory dossier, graph, and tenant association upon candidate deletion."""
    _DOSSIER_STORE.pop(candidate_id, None)
    _GRAPH_STORE.pop(candidate_id, None)
    _DOSSIER_ORG_MAP.pop(candidate_id, None)



def get_stored_dossier(candidate_id: UUID, organization_id: UUID | None = None) -> Dossier | None:
    """Retrieves an in-memory dossier by candidate ID, respecting organization scoping."""
    if organization_id is not None:
        mapped_org = _DOSSIER_ORG_MAP.get(candidate_id)
        if mapped_org is not None and mapped_org != organization_id:
            return None
    return _DOSSIER_STORE.get(candidate_id)


def get_stored_graph(candidate_id: UUID, organization_id: UUID | None = None) -> CandidateEvidenceGraph | None:
    """Retrieves an in-memory graph by candidate ID, respecting organization scoping."""
    if organization_id is not None:
        mapped_org = _DOSSIER_ORG_MAP.get(candidate_id)
        if mapped_org is not None and mapped_org != organization_id:
            return None
    return _GRAPH_STORE.get(candidate_id)


@router.get(
    "/{candidate_id}",
    response_model=DossierResponse,
    summary="Get candidate technical dossier",
    status_code=status.HTTP_200_OK,
)
def get_candidate_dossier(
    candidate_id: UUID,
    tenant: TenantContext = Depends(get_current_tenant),
) -> DossierResponse:
    """Returns the complete technical dossier snapshot for a candidate scoped to the authenticated tenant."""
    # Verify candidate tenant boundary
    with SessionLocal() as db:
        verify_candidate_tenant(db, candidate_id, tenant.organization_id)

    dossier = get_stored_dossier(candidate_id, tenant.organization_id)
    if not dossier:
        try:
            from cci.db.repository import get_dossier_by_candidate_id

            with SessionLocal() as db:
                dossier = get_dossier_by_candidate_id(db, candidate_id, organization_id=tenant.organization_id)
                if dossier:
                    register_dossier(dossier, organization_id=tenant.organization_id)
        except Exception:
            pass

    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dossier not found for candidate ID {candidate_id}",
        )
    return DossierResponse(dossier=dossier)


@router.get(
    "/{candidate_id}/export",
    summary="Export candidate technical intelligence brief (HTML, Markdown, JSON)",
    status_code=status.HTTP_200_OK,
)
def export_candidate_dossier(
    candidate_id: UUID,
    format: str = Query(
        "html",
        pattern="^(html|markdown|json)$",
        description="Export format: html, markdown, or json",
    ),
    tenant: TenantContext = Depends(get_current_tenant),
) -> Response:
    """Exports a formatted, printable technical brief scoped strictly to the authenticated tenant."""
    with SessionLocal() as db:
        verify_candidate_tenant(db, candidate_id, tenant.organization_id)

    dossier = get_stored_dossier(candidate_id, tenant.organization_id)
    cand_name = "Candidate"
    if not dossier:
        try:
            from cci.db.repository import (
                get_candidate_by_id,
                get_dossier_by_candidate_id,
            )

            with SessionLocal() as db:
                dossier = get_dossier_by_candidate_id(db, candidate_id, organization_id=tenant.organization_id)
                cand = get_candidate_by_id(db, candidate_id, organization_id=tenant.organization_id)
                if cand:
                    cand_name = cand.display_name
                if dossier:
                    register_dossier(dossier, organization_id=tenant.organization_id)
        except Exception:
            pass

    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dossier not found for candidate ID {candidate_id}",
        )

    if format == "html":
        content = generate_html_brief(dossier, candidate_name=cand_name)
        return Response(content=content, media_type="text/html")
    elif format == "markdown":
        content = generate_markdown_brief(dossier, candidate_name=cand_name)
        return Response(content=content, media_type="text/markdown")
    else:
        return Response(
            content=dossier.model_dump_json(indent=2),
            media_type="application/json",
        )


@router.get(
    "/{candidate_id}/graph",
    response_model=CEGGraphResponse,
    summary="Get candidate evidence graph projection",
    status_code=status.HTTP_200_OK,
)
def get_candidate_graph(
    candidate_id: UUID,
    tenant: TenantContext = Depends(get_current_tenant),
) -> Any:
    """Returns the complete Candidate Evidence Graph (CEG) projection scoped to the authenticated tenant."""
    with SessionLocal() as db:
        verify_candidate_tenant(db, candidate_id, tenant.organization_id)

    graph = get_stored_graph(candidate_id, tenant.organization_id)
    dossier = get_stored_dossier(candidate_id, tenant.organization_id)
    if not graph:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence graph not found for candidate ID {candidate_id}",
        )
    analysis_run_id = dossier.analysis_run_id if dossier else candidate_id
    return graph.to_api_response(
        candidate_id=candidate_id, analysis_run_id=analysis_run_id
    )


@router.get(
    "/{candidate_id}/probes",
    response_model=InterviewProbesResponse,
    summary="Get prioritized interview inquiry probes",
    status_code=status.HTTP_200_OK,
)
def get_candidate_probes(
    candidate_id: UUID,
    tenant: TenantContext = Depends(get_current_tenant),
) -> InterviewProbesResponse:
    """Returns ranked interview probe priorities and evidence-grounded questions scoped to tenant."""
    with SessionLocal() as db:
        verify_candidate_tenant(db, candidate_id, tenant.organization_id)

    dossier = get_stored_dossier(candidate_id, tenant.organization_id)
    if not dossier:
        try:
            from cci.db.repository import get_dossier_by_candidate_id

            with SessionLocal() as db:
                dossier = get_dossier_by_candidate_id(db, candidate_id, organization_id=tenant.organization_id)
                if dossier:
                    register_dossier(dossier, organization_id=tenant.organization_id)
        except Exception:
            pass

    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dossier not found for candidate ID {candidate_id}",
        )
    return InterviewProbesResponse(
        analysis_run_id=dossier.analysis_run_id,
        probes=dossier.interview_probes,
        questions=dossier.interview_questions,
    )


@router.get(
    "/{candidate_id}/provenance/{capability_key}",
    summary="Get backward provenance trace for capability score",
    status_code=status.HTTP_200_OK,
)
def get_capability_provenance(
    candidate_id: UUID,
    capability_key: CapabilityKey,
    tenant: TenantContext = Depends(get_current_tenant),
) -> list[dict[str, Any]]:
    """Traces backwards from a capability score to supporting evidence scoped strictly to tenant."""
    with SessionLocal() as db:
        verify_candidate_tenant(db, candidate_id, tenant.organization_id)

    graph = get_stored_graph(candidate_id, tenant.organization_id)
    if not graph:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence graph not found for candidate ID {candidate_id}",
        )
    return graph.trace_provenance(capability_key)
