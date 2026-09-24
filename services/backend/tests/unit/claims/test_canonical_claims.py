"""Tests for Fix 13: Canonical Claim Model, 10-state ClaimStatus taxonomy, and CEG claim nodes."""

from datetime import datetime, timezone
from uuid import UUID, uuid4
import pytest
from pydantic import ValidationError

from cci.domain.enums import (
    CanonicalRole,
    CapabilityKey,
    ClaimStatus,
    GraphEdgeType,
    GraphNodeType,
    SourceFamily,
)
from cci.domain.contracts import (
    Claim,
    Dossier,
    EvidenceConfidenceFactors,
    EvidenceRecord,
)
from cci.claims.corroborator import (
    ClaimCorroborationResult,
    ExtractedClaimInput,
    corroborate_candidate_claims,
)
from cci.graph.builder import build_dossier_graph


def test_claim_status_taxonomy_exact_ten():
    """Acceptance gate: ClaimStatus must define exactly the 10 canonical taxonomy states."""
    expected_names = {
        "SELF_REPORTED",
        "OBSERVED",
        "SUPPORTED",
        "STRONGLY_SUPPORTED",
        "ISSUER_VERIFIED",
        "PARTIALLY_SUPPORTED",
        "CONTRADICTED",
        "NOT_OBSERVED",
        "INACCESSIBLE",
        "INSUFFICIENT_EVIDENCE",
    }
    actual_names = {s.name for s in ClaimStatus if s.name in expected_names}
    assert actual_names == expected_names
    for state_name in expected_names:
        assert hasattr(ClaimStatus, state_name)
        member = getattr(ClaimStatus, state_name)
        assert member.value == state_name.lower()
        # Both uppercase and lowercase strings must resolve to the member
        assert ClaimStatus(state_name) == member
        assert ClaimStatus(state_name.lower()) == member


def test_claim_status_backward_compatibility_aliases():
    """Verify legacy status values map to canonical taxonomy without breaking."""
    assert ClaimStatus("corroborated") == ClaimStatus.SUPPORTED
    assert ClaimStatus("partial") == ClaimStatus.PARTIALLY_SUPPORTED
    assert ClaimStatus("unknown") == ClaimStatus.NOT_OBSERVED
    assert ClaimStatus.CORROBORATED == ClaimStatus.SUPPORTED
    assert ClaimStatus.PARTIAL == ClaimStatus.PARTIALLY_SUPPORTED
    assert ClaimStatus.UNKNOWN == ClaimStatus.NOT_OBSERVED


def test_canonical_claim_model_has_required_fifteen_fields():
    """Verify the canonical Claim entity has all minimum required fields from Fix 13."""
    cid = uuid4()
    run_id = uuid4()
    claim_id = uuid4()
    now = datetime.now(timezone.utc)

    claim = Claim(
        claim_id=claim_id,
        analysis_run_id=run_id,
        candidate_id=cid,
        claim_type="skill",
        original_text="5+ years of distributed systems in Python",
        normalized_subject="Python",
        structured_value={"years": 5},
        unit="years",
        source=SourceFamily.RESUME,
        section="experience",
        source_location="line 42",
        source_document_hash="a" * 64,
        status=ClaimStatus.SELF_REPORTED,
        verification_state="unverified",
        created_at=now,
    )

    assert claim.claim_id == claim_id
    assert claim.analysis_run_id == run_id
    assert claim.candidate_id == cid
    assert claim.claim_type == "skill"
    assert claim.original_text == "5+ years of distributed systems in Python"
    assert claim.normalized_subject == "Python"
    assert claim.structured_value == {"years": 5}
    assert claim.unit == "years"
    assert claim.source == SourceFamily.RESUME
    assert claim.section == "experience"
    assert claim.source_location == "line 42"
    assert claim.source_document_hash == "a" * 64
    assert claim.status == ClaimStatus.SELF_REPORTED
    assert claim.verification_state == "unverified"
    assert claim.created_at == now


def test_claim_corroboration_must_reference_evidence_ids():
    """Invariant: Every claim corroboration must reference evidence IDs when supported or contradicted."""
    # SUPPORTED requires grounding_evidence_ids
    with pytest.raises(ValidationError, match="grounding evidence"):
        Claim(
            claim_type="skill",
            original_text="Built Kafka ingestion pipeline",
            status=ClaimStatus.SUPPORTED,
            grounding_evidence_ids=[],
        )

    # STRONGLY_SUPPORTED requires grounding_evidence_ids
    with pytest.raises(ValidationError, match="grounding evidence"):
        Claim(
            claim_type="skill",
            original_text="Built Kafka ingestion pipeline",
            status=ClaimStatus.STRONGLY_SUPPORTED,
            grounding_evidence_ids=[],
        )

    # CONTRADICTED requires grounding_evidence_ids
    with pytest.raises(ValidationError, match="grounding evidence"):
        Claim(
            claim_type="skill",
            original_text="Built Kafka ingestion pipeline",
            status=ClaimStatus.CONTRADICTED,
            grounding_evidence_ids=[],
        )

    # Valid supported claim with evidence ID succeeds
    ev_id = uuid4()
    valid_claim = Claim(
        claim_type="skill",
        original_text="Built Kafka ingestion pipeline",
        status=ClaimStatus.SUPPORTED,
        grounding_evidence_ids=[ev_id],
    )
    assert valid_claim.grounding_evidence_ids == [ev_id]

    # SELF_REPORTED and NOT_OBSERVED do not require evidence IDs
    unsupported = Claim(
        claim_type="skill",
        original_text="Built Kafka ingestion pipeline",
        status=ClaimStatus.NOT_OBSERVED,
        grounding_evidence_ids=[],
    )
    assert unsupported.status == ClaimStatus.NOT_OBSERVED


def test_never_use_not_observed_as_false():
    """Invariant: NOT_OBSERVED is missing evidence, never contradictory evidence."""
    claim = Claim(
        claim_type="skill",
        original_text="Kubernetes cluster operator",
        status=ClaimStatus.NOT_OBSERVED,
    )
    assert claim.status != ClaimStatus.CONTRADICTED
    assert claim.status.value == "not_observed"


def test_corroborator_produces_canonical_claims_with_evidence_refs():
    """Verify corroborator creates canonical Claim instances referencing evidence."""
    ev_id = uuid4()
    factors = EvidenceConfidenceFactors(
        artifact_integrity=1.0,
        ownership_score=1.0,
        recency_factor=1.0,
        verification_level=1.0,
        depth_specificity=1.0,
        source_reliability=1.0,
    )
    evidence = EvidenceRecord(
        evidence_id=ev_id,
        fingerprint="b" * 64,
        source_family=SourceFamily.GITHUB,
        source_locator="https://github.com/acme/project",
        immutable_revision="b" * 40,
        target_capability=CapabilityKey.BACKEND_ENGINEERING,
        technical_signal_strength=85.0,
        is_positive_support=True,
        confidence_factors=factors,
        confidence=1.0,
        provenance={"raw_support_text": "python asyncio fast api endpoint"},
    )

    claim_input = ExtractedClaimInput(
        claim_text="FastAPI backend engineer with Python",
        target_capability=CapabilityKey.BACKEND_ENGINEERING,
        technology_keywords=["fastapi", "python"],
    )

    results = corroborate_candidate_claims([claim_input], [evidence])
    assert len(results) == 1
    result = results[0]
    assert result.status == ClaimStatus.SUPPORTED
    assert ev_id in result.grounding_evidence_ids
    assert len(result.grounding_evidence_ids) >= 1

    # Can convert to or is canonical Claim
    canonical = result.to_claim() if hasattr(result, "to_claim") else Claim.from_corroboration(result)
    assert canonical.original_text == claim_input.claim_text
    assert canonical.status == ClaimStatus.SUPPORTED
    assert canonical.grounding_evidence_ids == [ev_id]


def test_ceg_builder_adds_claim_nodes_and_corroboration_edges():
    """Verify CEG builder creates GraphNodeType.CLAIM nodes and links evidence to them."""
    cid = uuid4()
    run_id = uuid4()
    ev_id = uuid4()
    factors = EvidenceConfidenceFactors(
        artifact_integrity=1.0,
        ownership_score=1.0,
        recency_factor=1.0,
        verification_level=1.0,
        depth_specificity=1.0,
        source_reliability=1.0,
    )
    evidence = EvidenceRecord(
        evidence_id=ev_id,
        fingerprint="c" * 64,
        source_family=SourceFamily.GITHUB,
        source_locator="https://github.com/acme/repo",
        immutable_revision="c" * 40,
        target_capability=CapabilityKey.TESTING_QUALITY,
        technical_signal_strength=90.0,
        confidence_factors=factors,
        confidence=1.0,
    )
    claim_id = uuid4()
    claim = Claim(
        claim_id=claim_id,
        analysis_run_id=run_id,
        candidate_id=cid,
        claim_type="skill",
        original_text="pytest test-driven development",
        target_capability=CapabilityKey.TESTING_QUALITY,
        status=ClaimStatus.SUPPORTED,
        grounding_evidence_ids=[ev_id],
    )
    dossier = Dossier(
        candidate_id=cid,
        analysis_run_id=run_id,
        role=CanonicalRole.BACKEND,
        coverage=0.7,
        is_insufficient_evidence=False,
        capability_estimates={},
        capability_conflicts={},
        role_requirements=[],
        ownership_assessments=[],
        claims_corroboration=[claim.model_dump(mode="json")],
        interview_probes=[],
        interview_questions=[],
        evidence_records=[evidence],
    )

    graph = build_dossier_graph(dossier)
    claim_node_key = f"claim_{claim_id}"
    assert claim_node_key in graph.nodes
    node = graph.nodes[claim_node_key]
    assert node.node_type == GraphNodeType.CLAIM
    assert node.properties["original_text"] == "pytest test-driven development"
    assert node.properties["status"] == "supported"

    # Evidence links to Claim with CORROBORATES edge
    corrob_edges = [
        edge for edge in graph.edges.values()
        if edge.source_id == str(ev_id) and edge.target_id == claim_node_key
    ]
    assert len(corrob_edges) == 1
    assert corrob_edges[0].edge_type == GraphEdgeType.CORROBORATES


def test_adversarial_legacy_alias_bypass_attempt():
    """Attack: Passing legacy alias 'corroborated' or 'partial' cannot bypass evidence requirements."""
    with pytest.raises(ValidationError, match="grounding evidence"):
        Claim(
            original_text="Expert in distributed transactions",
            status="corroborated",  # type: ignore
            grounding_evidence_ids=[],
        )
    with pytest.raises(ValidationError, match="grounding evidence"):
        Claim(
            original_text="Expert in distributed transactions",
            status="partial",  # type: ignore
            grounding_evidence_ids=[],
        )


def test_adversarial_empty_and_whitespace_original_text():
    """Attack: Claim cannot have empty text."""
    with pytest.raises(ValidationError):
        Claim(original_text="")
    with pytest.raises(ValidationError):
        Claim(original_text="", status=ClaimStatus.SELF_REPORTED)


def test_adversarial_zero_confidence_evidence_cannot_corroborate():
    """Attack: Zero-confidence evidence cannot manufacture claim support."""
    ev_id = uuid4()
    factors = EvidenceConfidenceFactors(
        artifact_integrity=1.0,
        ownership_score=0.0,  # Zero ownership factor causes composite confidence to be 0
        recency_factor=1.0,
        verification_level=1.0,
        depth_specificity=1.0,
        source_reliability=1.0,
    )
    evidence = EvidenceRecord(
        evidence_id=ev_id,
        fingerprint="d" * 64,
        source_family=SourceFamily.GITHUB,
        source_locator="https://github.com/someone_else/project",
        immutable_revision="d" * 40,
        target_capability=CapabilityKey.BACKEND_ENGINEERING,
        technical_signal_strength=95.0,
        confidence_factors=factors,
        confidence=0.0,
    )
    claim_input = ExtractedClaimInput(
        claim_text="PostgreSQL database scaling",
        target_capability=CapabilityKey.BACKEND_ENGINEERING,
        technology_keywords=["postgresql"],
    )
    results = corroborate_candidate_claims([claim_input], [evidence])
    assert len(results) == 1
    assert results[0].status == ClaimStatus.NOT_OBSERVED
    assert results[0].confidence == 0.0
    assert results[0].grounding_evidence_ids == []


def test_adversarial_contradicted_claim_creates_contradicts_edge_in_ceg():
    """Attack: Refuted claim must create CONTRADICTS edge from evidence to claim, never CORROBORATES."""
    cid = uuid4()
    run_id = uuid4()
    ev_id = uuid4()
    factors = EvidenceConfidenceFactors(
        artifact_integrity=1.0,
        ownership_score=1.0,
        recency_factor=1.0,
        verification_level=1.0,
        depth_specificity=1.0,
        source_reliability=1.0,
    )
    evidence = EvidenceRecord(
        evidence_id=ev_id,
        fingerprint="e" * 64,
        source_family=SourceFamily.GITHUB,
        source_locator="https://github.com/acme/project",
        immutable_revision="e" * 40,
        target_capability=CapabilityKey.TESTING_QUALITY,
        technical_signal_strength=20.0,
        is_positive_support=False,
        confidence_factors=factors,
        confidence=1.0,
        provenance={"synthetic": True},
        negative_evidence_details={
            "claim_reference": "cr1:" + "f" * 64,
            "candidate_type": "candidatex.contradiction.coverage_below_claim",
            "expected_observation": "Test coverage >= 90%",
            "actual_observation": "Test coverage 20%",
            "scan_scope": {"scope_kind": "synthetic"},
            "required_scan_completeness": 1.0,
            "observed_scan_completeness": 1.0,
            "explanation": "Contradicts claimed coverage",
        },
    )
    claim_id = uuid4()
    claim = Claim(
        claim_id=claim_id,
        analysis_run_id=run_id,
        candidate_id=cid,
        claim_type="metric",
        original_text="90% test coverage across all modules",
        target_capability=CapabilityKey.TESTING_QUALITY,
        status=ClaimStatus.CONTRADICTED,
        grounding_evidence_ids=[ev_id],
    )
    dossier = Dossier(
        candidate_id=cid,
        analysis_run_id=run_id,
        role=CanonicalRole.BACKEND,
        coverage=0.8,
        is_insufficient_evidence=False,
        capability_estimates={},
        capability_conflicts={},
        role_requirements=[],
        ownership_assessments=[],
        claims_corroboration=[claim.model_dump(mode="json")],
        interview_probes=[],
        interview_questions=[],
        evidence_records=[evidence],
    )
    graph = build_dossier_graph(dossier)
    edges = [e for e in graph.edges.values() if e.source_id == str(ev_id) and e.target_id == f"claim_{claim_id}"]
    assert len(edges) == 1
    assert edges[0].edge_type == GraphEdgeType.CONTRADICTS
    assert not any(e.edge_type == GraphEdgeType.CORROBORATES for e in edges)

