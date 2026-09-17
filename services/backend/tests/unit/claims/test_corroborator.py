"""Unit tests for candidate claims corroborator."""

from uuid import uuid4
import pytest
from cci.claims.corroborator import (
    ClaimCorroborationResult,
    ExtractedClaimInput,
    corroborate_candidate_claims,
)
from cci.domain.contracts import EvidenceConfidenceFactors, EvidenceRecord
from cci.domain.enums import CapabilityKey, ClaimStatus, SourceFamily


def _create_mock_evidence(
    target_cap: CapabilityKey,
    support_score: float = 80.0,
    confidence: float = 0.85,
    is_pos: bool = True,
    text: str = "Evidence text",
) -> EvidenceRecord:
    factors = EvidenceConfidenceFactors(
        artifact_integrity=1.0,
        ownership_score=1.0,
        recency_factor=1.0,
        verification_level=1.0,
        depth_specificity=1.0,
        source_reliability=1.0,
    )
    return EvidenceRecord(
        evidence_id=uuid4(),
        fingerprint="sha256-mock-fingerprint",
        source_family=SourceFamily.GITHUB,
        source_locator="https://github.com/alice/project",
        immutable_revision="sha1234",
        target_capability=target_cap,
        support_score=support_score,
        is_positive_support=is_pos,
        confidence_factors=factors,
        confidence=confidence,
        provenance={"raw_support_text": text},
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
    claim = ExtractedClaimInput(
        claim_text="Architected distributed backend systems with high test coverage",
        target_capability=CapabilityKey.TESTING_QUALITY,
        technology_keywords=["testing"],
    )

    neg_ev = _create_mock_evidence(CapabilityKey.TESTING_QUALITY, confidence=0.9, is_pos=False, text="Broken test suite with failing assertions")

    results = corroborate_candidate_claims([claim], [neg_ev])
    assert len(results) == 1
    assert results[0].status == ClaimStatus.CONTRADICTED
    assert any("contradict" in results[0].explanation.lower() for _ in [1])
