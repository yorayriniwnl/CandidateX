"""Dossier and Candidate Evidence Graph API router."""

from typing import Any
from uuid import UUID

from cci.api.contracts.dossier import DossierResponse, InterviewProbesResponse
from cci.api.contracts.graph import CEGGraphResponse
from cci.domain.contracts import Dossier
from cci.domain.enums import CapabilityKey
from cci.graph.ceg import CandidateEvidenceGraph
from cci.reports.exporter import generate_html_brief, generate_markdown_brief
from fastapi import APIRouter, HTTPException, Query, Response, status

router = APIRouter(prefix="/api/v1/dossier", tags=["Dossier & Evidence Graph"])

# In-memory registry for completed dossiers and CEGs (can be backed by DB/Redis)
_DOSSIER_STORE: dict[UUID, Dossier] = {}
_GRAPH_STORE: dict[UUID, CandidateEvidenceGraph] = {}


def register_dossier(
    dossier: Dossier, graph: CandidateEvidenceGraph | None = None
) -> None:
    """Registers a completed dossier and optional CEG graph in memory."""
    _DOSSIER_STORE[dossier.candidate_id] = dossier
    if graph:
        _GRAPH_STORE[dossier.candidate_id] = graph


def get_stored_dossier(candidate_id: UUID) -> Dossier | None:
    """Retrieves an in-memory dossier by candidate ID."""
    return _DOSSIER_STORE.get(candidate_id)


def get_stored_graph(candidate_id: UUID) -> CandidateEvidenceGraph | None:
    """Retrieves an in-memory graph by candidate ID."""
    return _GRAPH_STORE.get(candidate_id)


@router.get(
    "/{candidate_id}",
    response_model=DossierResponse,
    summary="Get candidate technical dossier",
    status_code=status.HTTP_200_OK,
)
def get_candidate_dossier(candidate_id: UUID) -> DossierResponse:
    """Returns the complete technical dossier snapshot for a candidate."""
    dossier = _DOSSIER_STORE.get(candidate_id)
    if not dossier:
        try:
            from cci.db.repository import get_dossier_by_candidate_id
            from cci.db.session import SessionLocal

            with SessionLocal() as db:
                dossier = get_dossier_by_candidate_id(db, candidate_id)
                if dossier:
                    _DOSSIER_STORE[candidate_id] = dossier
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
) -> Response:
    """Exports a formatted, printable technical brief for hiring managers and interviewers."""
    dossier = _DOSSIER_STORE.get(candidate_id)
    cand_name = "Candidate"
    if not dossier:
        try:
            from cci.db.repository import (
                get_candidate_by_id,
                get_dossier_by_candidate_id,
            )
            from cci.db.session import SessionLocal

            with SessionLocal() as db:
                dossier = get_dossier_by_candidate_id(db, candidate_id)
                cand = get_candidate_by_id(db, candidate_id)
                if cand:
                    cand_name = cand.display_name
                if dossier:
                    _DOSSIER_STORE[candidate_id] = dossier
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
        # json
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
def get_candidate_graph(candidate_id: UUID) -> Any:
    """Returns the complete Candidate Evidence Graph (CEG) nodes and edges projection."""
    graph = _GRAPH_STORE.get(candidate_id)
    dossier = _DOSSIER_STORE.get(candidate_id)
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
def get_candidate_probes(candidate_id: UUID) -> InterviewProbesResponse:
    """Returns ranked interview probe priorities and evidence-grounded questions."""
    dossier = _DOSSIER_STORE.get(candidate_id)
    if not dossier:
        try:
            from cci.db.repository import get_dossier_by_candidate_id
            from cci.db.session import SessionLocal

            with SessionLocal() as db:
                dossier = get_dossier_by_candidate_id(db, candidate_id)
                if dossier:
                    _DOSSIER_STORE[candidate_id] = dossier
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
    candidate_id: UUID, capability_key: CapabilityKey
) -> list[dict[str, Any]]:
    """Traces backwards from a capability score to exact supporting artifacts, sources, and evidence."""
    graph = _GRAPH_STORE.get(candidate_id)
    if not graph:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence graph not found for candidate ID {candidate_id}",
        )
    return graph.trace_provenance(capability_key)
