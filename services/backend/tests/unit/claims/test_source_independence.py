"""Unit tests for Fix 43: Source Independence and Provenance Families."""

from uuid import uuid4
import pytest

from cci.claims.corroborator import (
    ClaimCorroborationResult,
    ExtractedClaimInput,
    corroborate_candidate_claims,
)
from cci.claims.independence import (
    classify_provenance_family,
    compute_source_independence,
    evaluate_corroboration_with_source_independence,
    is_candidate_self_declaration,
)
from cci.domain.contracts import EvidenceConfidenceFactors, EvidenceRecord
from cci.domain.enums import CapabilityKey, ClaimStatus, ProvenanceFamily, SourceFamily


def _create_test_record(
    source_family: SourceFamily,
    source_locator: str,
    target_capability: CapabilityKey = CapabilityKey.BACKEND_ENGINEERING,
    confidence: float = 0.8,
    observation_type: str = "observation",
    artifact_path: str = "",
    raw_text: str = "test evidence",
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
        fingerprint=f"fp-{uuid4().hex[:12]}",
        source_family=source_family,
        source_locator=source_locator,
        immutable_revision="main-commit-1",
        target_capability=target_capability,
        confidence_factors=factors,
        technical_signal_strength=0.8,
        confidence=confidence,
        observation_type=observation_type,
        provenance={"artifact_path": artifact_path, "raw_support_text": raw_text},
    )


def test_provenance_families_modeled():
    """Verify all 8 canonical provenance families from Fix 43 design spec exist."""
    expected_families = {
        "CANDIDATE_DECLARATION",
        "CANDIDATE_CONTROLLED_ARTIFACT",
        "PLATFORM_METADATA",
        "INDEPENDENT_PLATFORM",
        "ISSUER_CONTROLLED",
        "ORGANIZATION_CONTROLLED",
        "PUBLICATION_INDEX",
        "UNKNOWN",
    }
    actual_families = {f.value for f in ProvenanceFamily}
    assert expected_families == actual_families


def test_provenance_family_classification():
    """Verify evidence items are classified into correct provenance families."""
    # Resume
    ev_resume = _create_test_record(SourceFamily.RESUME, "local/resume.pdf")
    assert classify_provenance_family(ev_resume) == ProvenanceFamily.CANDIDATE_DECLARATION

    # Publication Index
    ev_paper = _create_test_record(SourceFamily.RESUME, "https://arxiv.org/abs/2301.00001")
    assert classify_provenance_family(ev_paper) == ProvenanceFamily.PUBLICATION_INDEX

    # Issuer Controlled
    ev_cert = _create_test_record(SourceFamily.CERTIFICATE, "https://www.credly.com/badges/abc")
    assert classify_provenance_family(ev_cert) == ProvenanceFamily.ISSUER_CONTROLLED

    # Independent Platform (coding)
    ev_coding = _create_test_record(SourceFamily.CODING, "https://leetcode.com/candidate")
    assert classify_provenance_family(ev_coding) == ProvenanceFamily.INDEPENDENT_PLATFORM

    # Platform Metadata
    ev_meta = _create_test_record(
        SourceFamily.GITHUB, "https://github.com/alice/repo", observation_type="commit_history_stats"
    )
    assert classify_provenance_family(ev_meta) == ProvenanceFamily.PLATFORM_METADATA

    # Organization Controlled
    ev_org = _create_test_record(SourceFamily.GITHUB, "https://github.com/apache/kafka")
    assert classify_provenance_family(ev_org, candidate_identifier="alice") == ProvenanceFamily.ORGANIZATION_CONTROLLED

    # Candidate Controlled
    ev_cand = _create_test_record(SourceFamily.GITHUB, "https://github.com/alice/my-project")
    assert classify_provenance_family(ev_cand, candidate_identifier="alice") == ProvenanceFamily.CANDIDATE_CONTROLLED_ARTIFACT


def test_resume_portfolio_readme_profile_do_not_count_as_four_independent_confirmations():
    """CRITICAL FIX 43 INVARIANT:
    Evidence from:
      - resume
      - candidate portfolio
      - candidate README
      - candidate GitHub profile
    may all originate from the candidate. Do not count them as four independent confirmations.
    """
    claim = ExtractedClaimInput(
        claim_text="Designed and implemented distributed stream processing using Apache Kafka",
        target_capability=CapabilityKey.BACKEND_ENGINEERING,
        technology_keywords=["Kafka"],
    )

    ev_resume = _create_test_record(
        SourceFamily.RESUME, "resume.pdf", confidence=0.8, raw_text="Kafka distributed streaming"
    )
    ev_portfolio = _create_test_record(
        SourceFamily.GITHUB, "https://alice.github.io/portfolio", confidence=0.8, raw_text="Kafka streaming architecture"
    )
    ev_readme = _create_test_record(
        SourceFamily.GITHUB, "https://github.com/alice/repo", confidence=0.8, artifact_path="README.md", raw_text="Uses Kafka"
    )
    ev_profile = _create_test_record(
        SourceFamily.GITHUB, "https://github.com/alice", confidence=0.8, artifact_path="profile/bio.md", raw_text="Kafka engineer"
    )

    # All 4 originate from candidate self-declarations
    assert is_candidate_self_declaration(ev_resume) is True
    assert is_candidate_self_declaration(ev_portfolio) is True
    assert is_candidate_self_declaration(ev_readme) is True
    assert is_candidate_self_declaration(ev_profile) is True

    independence = compute_source_independence([ev_resume, ev_portfolio, ev_readme, ev_profile])
    assert independence["has_independent_confirmation"] is False
    assert independence["all_candidate_self_declarations"] is True

    results = corroborate_candidate_claims(
        [claim],
        [ev_resume, ev_portfolio, ev_readme, ev_profile],
        candidate_identifier="alice",
    )
    assert len(results) == 1
    result = results[0]

    # Must NOT achieve full SUPPORTED status; capped at PARTIALLY_SUPPORTED
    assert result.status == ClaimStatus.PARTIALLY_SUPPORTED
    assert result.has_independent_confirmation is False
    assert result.confidence <= 0.50
    assert "originate" in result.explanation.lower() or "candidate" in result.explanation.lower()


def test_independent_confirmation_allows_supported_status():
    """Independent platform / issuer confirmation allows claim to achieve SUPPORTED status."""
    claim = ExtractedClaimInput(
        claim_text="Designed and implemented distributed stream processing using Apache Kafka",
        target_capability=CapabilityKey.BACKEND_ENGINEERING,
        technology_keywords=["Kafka"],
    )

    ev_readme = _create_test_record(
        SourceFamily.GITHUB, "https://github.com/alice/repo", confidence=0.8, artifact_path="README.md", raw_text="Uses Kafka"
    )
    ev_credly = _create_test_record(
        SourceFamily.CERTIFICATE, "https://www.credly.com/badges/confluent-kafka-pro", confidence=0.85, raw_text="Kafka Certified"
    )

    independence = compute_source_independence([ev_readme, ev_credly])
    assert independence["has_independent_confirmation"] is True
    assert independence["all_candidate_self_declarations"] is False

    results = corroborate_candidate_claims(
        [claim],
        [ev_readme, ev_credly],
        candidate_identifier="alice",
    )
    assert len(results) == 1
    result = results[0]

    assert result.status == ClaimStatus.SUPPORTED
    assert result.has_independent_confirmation is True
    assert result.confidence > 0.50
    assert "ISSUER_CONTROLLED" in result.provenance_families


def test_provenance_family_diminishing_returns():
    """Observations within the same provenance family undergo diminishing returns."""
    ev1 = _create_test_record(
        SourceFamily.CERTIFICATE, "https://www.credly.com/badges/cert1", confidence=0.8, raw_text="cert1"
    )
    ev2 = _create_test_record(
        SourceFamily.CERTIFICATE, "https://www.credly.com/badges/cert2", confidence=0.8, raw_text="cert2"
    )

    # Base with 1 evidence
    status1, conf1, _, _ = evaluate_corroboration_with_source_independence([ev1], [])
    # Combined with 2 evidence from same provenance family
    status2, conf2, _, _ = evaluate_corroboration_with_source_independence([ev1, ev2], [])

    # Second item receives 1 / (1 + 0.5 * 1) = 0.667 decay, so total sum is 0.8 + 0.8*0.667 = 1.333
    # conf2 is min(1.0, 1.333 / 2.0) = 0.667, strictly less than linear doubling (0.8 + 0.8 = 1.6 -> 0.8)
    assert status1 == ClaimStatus.PARTIALLY_SUPPORTED
    assert status2 == ClaimStatus.SUPPORTED
    assert conf2 < 0.80
