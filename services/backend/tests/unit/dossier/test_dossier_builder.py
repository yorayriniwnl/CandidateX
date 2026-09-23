"""Unit tests for Dossier Builder, interview question generator, and API endpoints."""

from datetime import datetime, timezone
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from cci.api.routers.dossier import register_dossier
from cci.claims.corroborator import ClaimCorroborationResult
from cci.domain.contracts import (
    ArtifactAttribution,
    CapabilityConflict,
    CapabilityEstimate,
    Dossier,
    EvidenceConfidenceFactors,
    EvidenceRecord,
    NormalizedRequirement,
    OwnershipAssessment,
    ProbePriority,
)
from cci.domain.enums import ArtifactAttributionState, CanonicalRole, CapabilityKey, ClaimStatus, GraphEdgeType, GraphNodeType, SourceFamily
from cci.dossier.builder import build_candidate_dossier, generate_interview_questions
from cci.graph.ceg import CandidateEvidenceGraph, CEGEdge, CEGNode
from cci.main import app

client = TestClient(app)


def _mock_dossier_fixtures():
    cand_id = uuid4()
    run_id = uuid4()

    probe_conflict = ProbePriority(
        capability_key=CapabilityKey.BACKEND_ENGINEERING,
        rank=1,
        priority_score=0.85,
        role_weight=0.30,
        coverage_gap_term=0.10,
        uncertainty_term=0.20,
        contradiction_term=0.60,
    )
    probe_gap = ProbePriority(
        capability_key=CapabilityKey.MACHINE_LEARNING,
        rank=2,
        priority_score=0.75,
        role_weight=0.25,
        coverage_gap_term=0.90,
        uncertainty_term=0.10,
        contradiction_term=0.0,
    )

    conflict_backend = CapabilityConflict(
        capability_key=CapabilityKey.BACKEND_ENGINEERING,
        positive_support_sum=5.0,
        negative_support_sum=3.0,
        contradiction_diagnostic=-0.35,
        has_meaningful_conflict=True,
    )

    cap_est = CapabilityEstimate(
        capability_key=CapabilityKey.BACKEND_ENGINEERING,
        estimate=78.5,
        effective_evidence_count=4.2,
        raw_evidence_count=5,
        dispersion=5.1,
        standard_error=2.5,
        coverage_k=0.90,
        is_observed=True,
    )

    req = NormalizedRequirement(
        source_text="Must have 5+ years in Python backend",
        normalized_name="Python Backend",
        capability_mappings=[CapabilityKey.BACKEND_ENGINEERING],
    )

    own = OwnershipAssessment(
        repository_url="https://github.com/alice/app",
        candidate_identifier="alice",
        ownership_score=0.95,
    )

    claim_res = ClaimCorroborationResult(
        claim_id=uuid4(),
        claim_text="FastAPI microservices",
        target_capability=CapabilityKey.BACKEND_ENGINEERING,
        status=ClaimStatus.CORROBORATED,
        confidence=0.85,
        grounding_evidence_ids=[uuid4()],
        citation_urls=["https://github.com/alice/app"],
        explanation="Corroborated by route handlers",
    )

    factors = EvidenceConfidenceFactors(
        artifact_integrity=1.0,
        ownership_score=1.0,
        recency_factor=1.0,
        verification_level=1.0,
        depth_specificity=1.0,
        source_reliability=1.0,
    )
    ev_record = EvidenceRecord(
        evidence_id=uuid4(),
        fingerprint="fp123",
        source_family=SourceFamily.GITHUB,
        source_locator="https://github.com/alice/app",
        immutable_revision="sha1",
        target_capability=CapabilityKey.BACKEND_ENGINEERING,
        support_score=85.0,
        confidence_factors=factors,
        confidence=0.88,
        provenance={"artifact_path": "src/api/routes.py", "raw_support_text": "FastAPI routes"},
    )

    return {
        "cand_id": cand_id,
        "run_id": run_id,
        "probes": [probe_conflict, probe_gap],
        "conflicts": {CapabilityKey.BACKEND_ENGINEERING: conflict_backend},
        "estimates": {CapabilityKey.BACKEND_ENGINEERING: cap_est},
        "requirements": [req],
        "ownership": [own],
        "claims": [claim_res],
        "evidence": [ev_record],
    }


def test_generate_interview_questions():
    fixtures = _mock_dossier_fixtures()
    questions = generate_interview_questions(
        probes=fixtures["probes"],
        capability_conflicts=fixtures["conflicts"],
        evidence_records=fixtures["evidence"],
    )

    assert len(questions) == 2
    # Question 1: Conflict probe
    q1 = questions[0]
    assert q1.target_capability == CapabilityKey.BACKEND_ENGINEERING
    assert "conflicting" in q1.question_text.lower()
    assert "contradiction diagnostic" in q1.rationale.lower()

    # Question 2: Coverage gap probe
    q2 = questions[1]
    assert q2.target_capability == CapabilityKey.MACHINE_LEARNING
    assert "coverage gap" in q2.rationale.lower()


def test_dossier_builder_retains_family_metadata_with_evidence_records():
    fixtures = _mock_dossier_fixtures()
    record = fixtures["evidence"][0].model_copy(
        update={
            "evidence_family_id": "ef1:" + "d" * 64,
            "observation_type": "route:python_decorator",
            "cluster_id": "https://github.com/alice/app",
            "artifact_id": uuid4(),
        }
    )

    dossier = build_candidate_dossier(
        candidate_id=fixtures["cand_id"],
        analysis_run_id=fixtures["run_id"],
        role=CanonicalRole.BACKEND,
        capability_estimates=fixtures["estimates"],
        capability_conflicts=fixtures["conflicts"],
        role_requirements=fixtures["requirements"],
        ownership_assessments=fixtures["ownership"],
        claims_corroboration=fixtures["claims"],
        interview_probes=fixtures["probes"],
        evidence_records=[record],
    )

    assert dossier.evidence_records == [record]
    assert dossier.evidence_records[0].evidence_family_id == "ef1:" + "d" * 64
    assert dossier.is_insufficient_evidence is True
    assert dossier.evidence_state.value == "INSUFFICIENT"


def test_build_candidate_dossier():
    fixtures = _mock_dossier_fixtures()
    dossier = build_candidate_dossier(
        candidate_id=fixtures["cand_id"],
        analysis_run_id=fixtures["run_id"],
        role=CanonicalRole.BACKEND,
        capability_estimates=fixtures["estimates"],
        capability_conflicts=fixtures["conflicts"],
        role_requirements=fixtures["requirements"],
        ownership_assessments=fixtures["ownership"],
        claims_corroboration=fixtures["claims"],
        interview_probes=fixtures["probes"],
        evidence_records=fixtures["evidence"],
        rci=82.4,
        coverage=0.88,
        is_insufficient_evidence=False,
    )

    assert dossier.candidate_id == fixtures["cand_id"]
    assert dossier.role == CanonicalRole.BACKEND
    assert dossier.rci == 82.4
    assert dossier.coverage == 0.88
    assert len(dossier.interview_questions) == 2
    assert len(dossier.claims_corroboration) == 1
    assert len(dossier.system_limitations) >= 3


def test_dossier_exposes_observed_index_context_without_hiding_partial_score():
    fixtures = _mock_dossier_fixtures()
    estimates = dict(fixtures["estimates"])
    estimates[CapabilityKey.BACKEND_ENGINEERING] = estimates[
        CapabilityKey.BACKEND_ENGINEERING
    ].model_copy(update={"cluster_count": 3})

    def attributed_record(path, confidence, cluster_id, day, revision):
        return fixtures["evidence"][0].model_copy(
            update={
                "cluster_id": cluster_id,
                "created_at": datetime(2026, 1, day, tzinfo=timezone.utc),
                "artifact_attribution": ArtifactAttribution(
                    artifact_path=path,
                    revision_sha=revision * 40,
                    state=ArtifactAttributionState.STRONG_ATTRIBUTION,
                    ownership_score=0.8,
                    attribution_confidence=confidence,
                    candidate_commit_count=2,
                    sampled_path_commit_count=3,
                ),
            }
        )

    records = [
        attributed_record("src/api/routes.py", 0.9, "repo-a", 1, "a"),
        attributed_record("src/api/routes.py", 0.6, "repo-b", 2, "b"),
        attributed_record("src/worker.py", 0.4, "repo-c", 3, "c"),
    ]
    dossier = build_candidate_dossier(
        candidate_id=fixtures["cand_id"],
        analysis_run_id=fixtures["run_id"],
        role=CanonicalRole.BACKEND,
        capability_estimates=estimates,
        capability_conflicts=fixtures["conflicts"],
        role_requirements=fixtures["requirements"],
        ownership_assessments=fixtures["ownership"],
        claims_corroboration=fixtures["claims"],
        interview_probes=fixtures["probes"],
        evidence_records=records,
        rci=82.4,
        coverage=0.2,
        is_insufficient_evidence=True,
        coverage_sufficiency_threshold=0.5,
    )

    context = dossier.observed_index_context
    assert dossier.observed_capability_index == 82.4
    assert context.metric_label == "Observed Capability Index"
    assert context.basis == "Based only on observed evidence."
    assert context.role_weighted_evidence_coverage == 0.2
    assert context.observed_role_dimensions == 1
    assert context.total_role_dimensions == len(CapabilityKey)
    assert context.coverage_sufficiency_threshold == 0.5
    assert context.is_insufficient_evidence is True
    assert context.standalone_presentation_allowed is False
    assert context.unique_independent_source_cluster_count == 3
    assert context.independent_source_cluster_counts_by_capability[
        CapabilityKey.BACKEND_ENGINEERING
    ] == 3
    assert context.mean_path_attribution_confidence == pytest.approx(0.5)
    assert context.path_attribution_sample_count == 2
    serialized = dossier.model_dump(mode="json")
    assert serialized["observed_capability_index"] == 82.4
    assert (
        serialized["observed_index_context"]["metric_label"]
        == "Observed Capability Index"
    )


def test_dossier_api_endpoints():
    fixtures = _mock_dossier_fixtures()
    cand_id = fixtures["cand_id"]
    run_id = fixtures["run_id"]

    dossier = build_candidate_dossier(
        candidate_id=cand_id,
        analysis_run_id=run_id,
        role=CanonicalRole.BACKEND,
        capability_estimates=fixtures["estimates"],
        capability_conflicts=fixtures["conflicts"],
        role_requirements=fixtures["requirements"],
        ownership_assessments=fixtures["ownership"],
        claims_corroboration=fixtures["claims"],
        interview_probes=fixtures["probes"],
        evidence_records=fixtures["evidence"],
        rci=85.0,
        coverage=0.90,
    )

    # Build CEG graph
    graph = CandidateEvidenceGraph()
    graph.add_node(CEGNode("cand_node", GraphNodeType.CANDIDATE, {"label": "Alice"}))
    graph.add_node(CEGNode(f"cap_{CapabilityKey.BACKEND_ENGINEERING.value}", GraphNodeType.CAPABILITY, {"label": "Backend"}))
    graph.add_node(CEGNode("ev_node", GraphNodeType.EVIDENCE, {"label": "Routes", "score": 85.0}))
    graph.add_edge(CEGEdge("e1", "ev_node", f"cap_{CapabilityKey.BACKEND_ENGINEERING.value}", GraphEdgeType.SUPPORTS_CAPABILITY))

    register_dossier(dossier, graph)

    # 1. GET /api/v1/dossier/{candidate_id}
    res = client.get(f"/api/v1/dossier/{cand_id}")
    assert res.status_code == 200
    data = res.json()
    assert "dossier" in data
    assert data["dossier"]["role"] == "backend"
    assert data["dossier"]["rci"] == 85.0
    assert data["dossier"]["observed_capability_index"] == 85.0
    assert (
        data["dossier"]["observed_index_context"]["metric_label"]
        == "Observed Capability Index"
    )
    assert data["dossier"]["observed_index_context"][
        "standalone_presentation_allowed"
    ] is True

    # 2. GET /api/v1/dossier/{candidate_id}/graph
    res_graph = client.get(f"/api/v1/dossier/{cand_id}/graph")
    assert res_graph.status_code == 200
    graph_data = res_graph.json()
    assert len(graph_data["nodes"]) == 3
    assert len(graph_data["edges"]) == 1

    # 3. GET /api/v1/dossier/{candidate_id}/probes
    res_probes = client.get(f"/api/v1/dossier/{cand_id}/probes")
    assert res_probes.status_code == 200
    probes_data = res_probes.json()
    assert len(probes_data["probes"]) == 2
    assert len(probes_data["questions"]) == 2

    # 4. GET /api/v1/dossier/{candidate_id}/provenance/{capability_key}
    res_prov = client.get(f"/api/v1/dossier/{cand_id}/provenance/backend_engineering")
    assert res_prov.status_code == 200
    prov_data = res_prov.json()
    assert len(prov_data) == 1
    assert prov_data[0]["evidence_id"] == "ev_node"

    # 5. 404 for unknown candidate
    unknown_id = uuid4()
    res_404 = client.get(f"/api/v1/dossier/{unknown_id}")
    assert res_404.status_code == 404
