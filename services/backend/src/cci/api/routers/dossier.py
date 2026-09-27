"""Dossier and Candidate Evidence Graph API router."""

from typing import Any
from uuid import UUID

from cci.api.contracts.dossier import DossierResponse, InterviewProbesResponse
from cci.api.contracts.graph import CEGGraphResponse
from cci.domain.contracts import Dossier
from cci.domain.enums import CapabilityKey
from cci.graph.ceg import CandidateEvidenceGraph
from cci.reports.exporter import (
    generate_audit_csv,
    generate_audit_html,
    generate_audit_json,
    generate_audit_markdown,
    generate_combined_report_and_audit_html,
    generate_combined_report_and_audit_json,
    generate_combined_report_and_audit_markdown,
    generate_html_brief,
    generate_markdown_brief,
)
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


def _fetch_candidate_audit_events(candidate_id: UUID) -> list[Any]:
    """Fetches candidate audit events from the overrides audit trail."""
    try:
        from cci.api.routers.overrides import get_candidate_audit_trail
        return get_candidate_audit_trail(candidate_id)
    except Exception:
        return []


def _resolve_candidate_dossier_and_name(candidate_id: UUID) -> tuple[Dossier, str]:
    """Retrieves dossier and candidate display name from memory or DB."""
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
    return dossier, cand_name


@router.get(
    "/{candidate_id}/export",
    summary="Export candidate report, full audit, or combined package (HTML, Markdown, JSON, CSV)",
    status_code=status.HTTP_200_OK,
)
def export_candidate_dossier(
    candidate_id: UUID,
    format: str = Query(
        "html",
        pattern="^(html|markdown|json|csv)$",
        description="Export format: html, markdown, json, or csv",
    ),
    scope: str = Query(
        "report",
        pattern="^(report|audit|full|both)$",
        description="Scope: report (Technical Brief), audit (Full Audit & Governance), or full (Combined Report & Audit)",
    ),
) -> Response:
    """Exports candidate technical intelligence report, full audit trail, or combined bundle."""
    dossier, cand_name = _resolve_candidate_dossier_and_name(candidate_id)

    if scope == "report":
        if format == "html":
            content = generate_html_brief(dossier, candidate_name=cand_name)
            return Response(content=content, media_type="text/html")
        elif format == "markdown":
            content = generate_markdown_brief(dossier, candidate_name=cand_name)
            return Response(content=content, media_type="text/markdown")
        elif format == "csv":
            content = generate_audit_csv([], dossier=dossier)
            return Response(content=content, media_type="text/csv")
        else:
            return Response(
                content=dossier.model_dump_json(indent=2),
                media_type="application/json",
            )
    elif scope == "audit":
        audit_events = _fetch_candidate_audit_events(candidate_id)
        if format == "html":
            content = generate_audit_html(dossier, audit_events=audit_events, candidate_name=cand_name)
            return Response(content=content, media_type="text/html")
        elif format == "markdown":
            content = generate_audit_markdown(dossier, audit_events=audit_events, candidate_name=cand_name)
            return Response(content=content, media_type="text/markdown")
        elif format == "csv":
            content = generate_audit_csv(audit_events=audit_events, dossier=dossier)
            return Response(content=content, media_type="text/csv")
        else:
            content = generate_audit_json(dossier, audit_events=audit_events, candidate_name=cand_name)
            return Response(content=content, media_type="application/json")
    else:
        # full / both
        audit_events = _fetch_candidate_audit_events(candidate_id)
        if format == "html":
            content = generate_combined_report_and_audit_html(dossier, audit_events=audit_events, candidate_name=cand_name)
            return Response(content=content, media_type="text/html")
        elif format == "markdown":
            content = generate_combined_report_and_audit_markdown(dossier, audit_events=audit_events, candidate_name=cand_name)
            return Response(content=content, media_type="text/markdown")
        elif format == "csv":
            content = generate_audit_csv(audit_events=audit_events, dossier=dossier)
            return Response(content=content, media_type="text/csv")
        else:
            content = generate_combined_report_and_audit_json(dossier, audit_events=audit_events, candidate_name=cand_name)
            return Response(content=content, media_type="application/json")


@router.get(
    "/{candidate_id}/export-audit",
    summary="Export candidate full audit & governance log (HTML, Markdown, JSON, CSV)",
    status_code=status.HTTP_200_OK,
)
def export_candidate_audit(
    candidate_id: UUID,
    format: str = Query(
        "html",
        pattern="^(html|markdown|json|csv)$",
        description="Export format: html, markdown, json, or csv",
    ),
) -> Response:
    """Exports candidate full audit trail, runtime provenance, and evidence ledger."""
    return export_candidate_dossier(candidate_id, format=format, scope="audit")



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
