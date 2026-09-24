"""Unit tests for wiring deployment inspection into live analysis (Fix 22).

Invariants:
1. Public URLs are validated safely (SSRF protection, public scheme and standard port, no credentials).
2. Never perform destructive actions (strictly read-only GET/HEAD).
3. Never authenticate using candidate credentials.
4. Do not give capability credit merely because HTTPS exists.
5. Deployment evidence supports deployment existence, project linkage, and runtime observation.
"""

from uuid import uuid4
import httpx
import pytest

from cci.analyzers.deployment.inspector import (
    DeploymentInspectionReport,
    extract_app_metadata,
    extract_application_identity,
    extract_documented_routes,
    extract_linked_repository,
    inspect_candidate_deployment,
)
from cci.domain.contracts import (
    Dossier,
    EvidenceRecord,
)
from cci.domain.enums import CanonicalRole, CapabilityKey, GraphEdgeType, GraphNodeType, SourceFamily
from cci.graph.builder import build_dossier_graph
from cci.live.deployment import acquire_deployment_sources


SAMPLE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="application-name" content="PayFlow Engine">
    <meta name="generator" content="Next.js 14">
    <meta property="og:site_name" content="PayFlow Portal">
    <meta name="description" content="Production microservices billing engine">
    <title>PayFlow - Realtime Billing Service</title>
</head>
<body>
    <header>
        <nav>
            <a href="/about">About</a>
            <a href="/api/v1/health">API Health</a>
            <a href="/docs">API Documentation</a>
            <a href="/swagger">Swagger</a>
            <a href="https://github.com/acme/payflow-backend">Source Repository</a>
        </nav>
    </header>
    <main>
        <h1>Welcome to PayFlow</h1>
        <div data-reactroot="">Interactive React App</div>
    </main>
    <footer>
        <a href="https://github.com/features">Ignored Link</a>
    </footer>
</body>
</html>
"""


def _sample_headers():
    return httpx.Headers({
        "content-type": "text/html; charset=utf-8",
        "server": "Vercel",
        "x-powered-by": "Next.js",
        "strict-transport-security": "max-age=63072000; includeSubDomains; preload",
        "content-security-policy": "default-src 'self'",
        "x-content-type-options": "nosniff",
        "x-frame-options": "DENY",
    })


def test_extract_application_identity():
    """Verify static extraction of application name, title, generator, and server hints."""
    id_info = extract_application_identity(SAMPLE_HTML, _sample_headers())
    assert id_info["title"] == "PayFlow - Realtime Billing Service"
    assert id_info["application_name"] == "PayFlow Engine"
    assert id_info["generator"] == "Next.js 14"
    assert id_info["og_site_name"] == "PayFlow Portal"
    assert id_info["server"] == "Vercel"
    assert id_info["powered_by"] == "Next.js"


def test_extract_linked_repository_prioritizes_candidate_repo():
    """Verify detection of GitHub repository links and matching candidate repo."""
    # Matches the link in HTML
    linked = extract_linked_repository(
        SAMPLE_HTML, known_repos=["https://github.com/acme/payflow-backend"]
    )
    assert linked == "https://github.com/acme/payflow-backend"

    # Filters out generic GitHub links like github.com/features
    assert "features" not in (linked or "")


def test_extract_documented_routes():
    """Verify static identification of safe documentation and API routes."""
    routes = extract_documented_routes(SAMPLE_HTML)
    assert "/about" in routes
    assert "/api/v1/health" in routes
    assert "/docs" in routes
    assert "/swagger" in routes


def test_extract_app_metadata():
    """Verify extraction of meta descriptions, frameworks, and asset markers."""
    meta = extract_app_metadata(SAMPLE_HTML, _sample_headers())
    assert meta["description"] == "Production microservices billing engine"
    assert "Next.js" in meta["frameworks"]
    assert "React" in meta["frameworks"]


def test_inspect_candidate_deployment_safe_validation():
    """Verify rejection of unsafe public URL schemes, credentials, and ports."""
    # Rejects file:// scheme
    rep_file = inspect_candidate_deployment("file:///etc/passwd")
    assert rep_file.status == "security_blocked"

    # Rejects credentials in URL
    rep_creds = inspect_candidate_deployment("https://user:pass@example.com")
    assert rep_creds.status == "security_blocked"

    # Rejects non-standard ports
    rep_port = inspect_candidate_deployment("http://example.com:8080")
    assert rep_port.status == "security_blocked"


def test_inspect_candidate_deployment_success():
    """Verify comprehensive deployment inspection with mock response."""
    mock_resp = httpx.Response(status_code=200, headers=_sample_headers(), text=SAMPLE_HTML)

    rep = inspect_candidate_deployment(
        deployment_url="https://payflow.example.com",
        known_repos=["https://github.com/acme/payflow-backend"],
        mock_response=mock_resp,
        skip_tls_socket=True,
    )

    assert rep.status == "observed"
    assert rep.status_code == 200
    assert rep.application_identity["application_name"] == "PayFlow Engine"
    assert rep.linked_repository == "https://github.com/acme/payflow-backend"
    assert len(rep.documented_routes) >= 3
    assert rep.security_headers["header_count"] >= 4
    assert rep.frontend_structure["has_viewport"] is True
    assert rep.app_metadata["frameworks"] == ["Next.js", "React"]
    assert len(rep.evidence_inputs) >= 2
    assert "deployment_existence" in rep.supported_signals
    assert "project_linkage" in rep.supported_signals
    assert "runtime_public_artifact_observation" in rep.supported_signals


def test_https_presence_does_not_grant_mastery():
    """Invariant: TLS presence verifies transport security, not candidate engineering mastery."""
    mock_resp = httpx.Response(status_code=200, headers={"content-type": "text/plain"}, text="OK")
    records, receipts = acquire_deployment_sources(
        deployment_urls=["https://simple-service.example.com"],
        mock_responses={"https://simple-service.example.com": mock_resp},
        skip_tls_socket=True,
    )
    assert len(receipts) == 1
    assert receipts[0]["status"] == "observed"

    # Verify that evidence provenance explicitly disclaims automated mastery
    for rec in records:
        assert rec.provenance.get("candidate_mastery_inferred") is False
        assert "supported_signals" in rec.provenance
        # Depth specificity must be conservative (< 0.50) for surface runtime observations
        assert rec.confidence_factors.depth_specificity <= 0.40


def test_acquire_deployment_sources_with_project_linkage():
    """Verify that linked repository elevates ownership score compared to unlinked deployment."""
    mock_resp = httpx.Response(status_code=200, headers=_sample_headers(), text=SAMPLE_HTML)

    # 1. Linked to candidate repository
    linked_records, _ = acquire_deployment_sources(
        deployment_urls=["https://payflow.example.com"],
        candidate_repositories=["https://github.com/acme/payflow-backend"],
        mock_responses={"https://payflow.example.com": mock_resp},
        skip_tls_socket=True,
    )
    assert len(linked_records) >= 1
    assert linked_records[0].confidence_factors.ownership_score == pytest.approx(0.85)

    # 2. Unlinked deployment
    unlinked_records, _ = acquire_deployment_sources(
        deployment_urls=["https://payflow.example.com"],
        candidate_repositories=["https://github.com/different/repo"],
        mock_responses={"https://payflow.example.com": mock_resp},
        skip_tls_socket=True,
    )
    assert len(unlinked_records) >= 1
    assert unlinked_records[0].confidence_factors.ownership_score == pytest.approx(0.40)


def test_graph_builder_includes_deployment_nodes_and_deployed_as_edges():
    """Verify that CEG graph builder creates Deployment node and DEPLOYED_AS edge."""
    mock_resp = httpx.Response(status_code=200, headers=_sample_headers(), text=SAMPLE_HTML)
    records, _ = acquire_deployment_sources(
        deployment_urls=["https://payflow.example.com"],
        candidate_repositories=["https://github.com/acme/payflow-backend"],
        mock_responses={"https://payflow.example.com": mock_resp},
        skip_tls_socket=True,
    )

    dossier = Dossier(
        dossier_id=uuid4(),
        candidate_id=uuid4(),
        analysis_run_id=uuid4(),
        role=CanonicalRole.BACKEND,
        rci=75.0,
        coverage=0.5,
        is_insufficient_evidence=False,
        capability_estimates={},
        capability_conflicts={},
        role_requirements=[],
        ownership_assessments=[],
        interview_probes=[],
        interview_questions=[],
        claims_corroboration=[],
        evidence_records=records,
    )

    graph = build_dossier_graph(dossier)

    # Check Deployment node
    deploy_nodes = graph.get_nodes_by_type(GraphNodeType.DEPLOYMENT)
    assert len(deploy_nodes) >= 1
    assert "payflow.example.com" in deploy_nodes[0].properties.get("url", "")

    # Check DEPLOYED_AS edge linking repo to deployment
    deployed_as_edges = [
        e for e in graph.edges.values() if e.edge_type == GraphEdgeType.DEPLOYED_AS
    ]
    assert len(deployed_as_edges) >= 1
    assert deployed_as_edges[0].properties.get("basis") == "verified_runtime_linkage"

    # Verify authorship invariants remain strictly valid
    assert len(graph.validate_authorship_invariants()) == 0
