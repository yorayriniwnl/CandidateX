"""Unit tests for candidate claims corroborator."""

from uuid import uuid4
import pytest
from cci.claims.corroborator import (
    ClaimCorroborationResult,
    ExtractedClaimInput,
    corroborate_candidate_claims,
)
from cci.domain.contracts import (
    EvidenceConfidenceFactors,
    EvidenceRecord,
    NegativeEvidenceDetails,
    NegativeEvidenceScanScope,
)
from cci.domain.enums import CapabilityKey, ClaimStatus, SourceFamily


def _synthetic_negative_details(
    claim_reference: str = "cr1:" + "a" * 64,
    candidate_type: str = "candidatex.contradiction.coverage_below_claim",
) -> NegativeEvidenceDetails:
    return NegativeEvidenceDetails(
        claim_reference=claim_reference,
        candidate_type=candidate_type,
        expected_observation="line_coverage >= 95%",
        actual_observation="line_coverage = 70%",
        scan_scope=NegativeEvidenceScanScope(
            scope_kind="synthetic",
            repository_scope=None,
            pinned_revision=None,
            artifact_paths=[],
            category=None,
        ),
        required_scan_completeness=1.0,
        observed_scan_completeness=1.0,
        explanation="Synthetic negative observation for testing",
    )


def _create_mock_evidence(
    target_cap: CapabilityKey,
    support_score: float = 80.0,
    confidence: float = 0.85,
    is_pos: bool = True,
    text: str = "Evidence text",
    evidence_family_id: str | None = None,
    observation_type: str = "legacy_unknown",
    fingerprint: str | None = None,
    negative_details: NegativeEvidenceDetails | None = None,
    provenance: dict | None = None,
) -> EvidenceRecord:
    factors = EvidenceConfidenceFactors(
        artifact_integrity=1.0,
        ownership_score=1.0,
        recency_factor=1.0,
        verification_level=1.0,
        depth_specificity=1.0,
        source_reliability=1.0,
    )
    evidence_id = uuid4()
    prov = {"raw_support_text": text}
    if provenance:
        prov.update(provenance)
    return EvidenceRecord(
        evidence_id=evidence_id,
        fingerprint=fingerprint or f"sha256-mock-{evidence_id.hex}",
        source_family=SourceFamily.GITHUB,
        source_locator="https://github.com/alice/project",
        immutable_revision="sha1234",
        target_capability=target_cap,
        support_score=support_score,
        is_positive_support=is_pos,
        negative_evidence_details=negative_details,
        confidence_factors=factors,
        confidence=confidence,
        evidence_family_id=evidence_family_id,
        observation_type=observation_type,
        provenance=prov,
    )


def test_corroborated_claim():
    """Verify claim receives CORROBORATED when cumulative positive evidence >= 1.0."""
    claim = ExtractedClaimInput(
        claim_text="Designed and implemented PostgreSQL relational schemas and migrations",
        target_capability=CapabilityKey.DATABASE_ENGINEERING,
        technology_keywords=["PostgreSQL", "schemas", "migrations"],
    )

    ev1 = _create_mock_evidence(CapabilityKey.DATABASE_ENGINEERING, confidence=0.7, text="PostgreSQL CREATE TABLE and indexes")
    ev2 = _create_mock_evidence(CapabilityKey.DATABASE_ENGINEERING, confidence=0.6, text="Alembic reversible migrations")

    results = corroborate_candidate_claims([claim], [ev1, ev2])
    assert len(results) == 1
    res = results[0]
    assert res.status == ClaimStatus.CORROBORATED
    assert res.confidence > 0.5
    assert len(res.grounding_evidence_ids) == 2


def test_partially_corroborated_claim():
    """Verify claim receives PARTIAL when evidence exists but cumulative confidence < 1.0."""
    claim = ExtractedClaimInput(
        claim_text="Built machine learning models using PyTorch",
        target_capability=CapabilityKey.MACHINE_LEARNING,
        technology_keywords=["PyTorch"],
    )

    ev1 = _create_mock_evidence(CapabilityKey.MACHINE_LEARNING, confidence=0.55, text="requirements.txt declared torch")

    results = corroborate_candidate_claims([claim], [ev1])
    assert len(results) == 1
    assert results[0].status == ClaimStatus.PARTIAL
    assert results[0].confidence == 0.55


def test_unknown_claim_missing_evidence():
    """CRITICAL INVARIANT: Missing evidence yields UNKNOWN status, never zero score or contradiction."""
    claim = ExtractedClaimInput(
        claim_text="Kubernetes cluster administration and Helm charts",
        target_capability=CapabilityKey.DEVOPS_CLOUD,
        technology_keywords=["Kubernetes", "Helm"],
    )

    # No DevOps evidence provided
    results = corroborate_candidate_claims([claim], [])
    assert len(results) == 1
    assert results[0].status == ClaimStatus.UNKNOWN
    assert results[0].confidence == 0.0
    assert len(results[0].grounding_evidence_ids) == 0


def test_contradicted_claim():
    """Verify claim receives CONTRADICTED when negative evidence outweighs positive."""
    claim_ref = "cr1:" + "f" * 64
    claim = ExtractedClaimInput(
        claim_text="Architected distributed backend systems with high test coverage",
        target_capability=CapabilityKey.TESTING_QUALITY,
        technology_keywords=["testing"],
        claim_reference=claim_ref,
    )

    neg_ev = _create_mock_evidence(
        CapabilityKey.TESTING_QUALITY,
        confidence=0.9,
        is_pos=False,
        text="Broken test suite with failing assertions",
        negative_details=_synthetic_negative_details(claim_reference=claim_ref),
        provenance={"synthetic": True},
    )

    results = corroborate_candidate_claims([claim], [neg_ev])
    assert len(results) == 1
    assert results[0].status == ClaimStatus.CONTRADICTED
    assert any("contradict" in results[0].explanation.lower() for _ in [1])


def test_claim_negative_requires_exact_claim_reference():
    claim_ref = "cr1:" + "1" * 64
    other_ref = "cr1:" + "2" * 64
    claim = ExtractedClaimInput(
        claim_text="Architected systems with at least 95% line coverage",
        target_capability=CapabilityKey.TESTING_QUALITY,
        technology_keywords=["coverage"],
        claim_reference=claim_ref,
    )
    wrong_claim_negative = _create_mock_evidence(
        CapabilityKey.TESTING_QUALITY,
        is_pos=False,
        negative_details=_synthetic_negative_details(claim_reference=other_ref),
        provenance={"synthetic": True},
    )
    legacy_negative = _create_mock_evidence(
        CapabilityKey.TESTING_QUALITY,
        is_pos=False,
        text="coverage failure",
    )
    unreferenced_claim = ExtractedClaimInput(
        claim_text="Architected systems with at least 95% line coverage",
        target_capability=CapabilityKey.TESTING_QUALITY,
        technology_keywords=["coverage"],
    )

    # Wrong claim reference yields UNKNOWN
    assert corroborate_candidate_claims([claim], [wrong_claim_negative])[0].status == ClaimStatus.UNKNOWN

    # Legacy negative yields UNKNOWN even with keyword hit
    assert corroborate_candidate_claims([claim], [legacy_negative])[0].status == ClaimStatus.UNKNOWN
    assert corroborate_candidate_claims([unreferenced_claim], [legacy_negative])[0].status == ClaimStatus.UNKNOWN


def test_repeated_family_observation_does_not_corroborate_claim_twice():
    family_id = "ef1:" + "a" * 64
    claim = ExtractedClaimInput(
        claim_text="Built PostgreSQL data services",
        target_capability=CapabilityKey.DATABASE_ENGINEERING,
    )
    manifest = _create_mock_evidence(
        CapabilityKey.DATABASE_ENGINEERING,
        confidence=0.7,
        text="PostgreSQL manifest support",
        evidence_family_id=family_id,
        observation_type="dependency:manifest",
        fingerprint="a" * 64,
    )
    repeated = _create_mock_evidence(
        CapabilityKey.DATABASE_ENGINEERING,
        confidence=0.6,
        text="PostgreSQL manifest support repeated",
        evidence_family_id=family_id,
        observation_type="dependency:manifest",
        fingerprint="b" * 64,
    )

    base = corroborate_candidate_claims([claim], [manifest])[0]
    with_repeat = corroborate_candidate_claims([claim], [manifest, repeated])[0]

    assert base.status == with_repeat.status == ClaimStatus.PARTIAL
    assert base.confidence == with_repeat.confidence == 0.7
    assert with_repeat.grounding_evidence_ids == [
        manifest.evidence_id,
        repeated.evidence_id,
    ]


def test_distinct_family_observation_type_contributes_decayed_claim_confidence():
    family_id = "ef1:" + "b" * 64
    claim = ExtractedClaimInput(
        claim_text="Built PostgreSQL data services",
        target_capability=CapabilityKey.DATABASE_ENGINEERING,
    )
    manifest = _create_mock_evidence(
        CapabilityKey.DATABASE_ENGINEERING,
        confidence=0.7,
        text="PostgreSQL manifest support",
        evidence_family_id=family_id,
        observation_type="dependency:manifest",
        fingerprint="a" * 64,
    )
    import_use = _create_mock_evidence(
        CapabilityKey.DATABASE_ENGINEERING,
        confidence=0.7,
        text="PostgreSQL import support",
        evidence_family_id=family_id,
        observation_type="dependency:python_import",
        fingerprint="b" * 64,
    )

    result = corroborate_candidate_claims([claim], [manifest, import_use])[0]

    # python_import sorts first for the tied representative rank; manifest gets 0.5.
    assert result.status == ClaimStatus.CORROBORATED
    assert result.confidence == 0.525
    assert set(result.grounding_evidence_ids) == {
        manifest.evidence_id,
        import_use.evidence_id,
    }
