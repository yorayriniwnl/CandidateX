"""Tests for Fix 19: Complete Separation of Research/Synthetic Data from Live Data."""

from uuid import uuid4
import pytest

from cci.domain.contracts import (
    EvidenceConfidenceFactors,
    EvidenceRecord,
)
from cci.domain.enums import (
    CanonicalRole,
    CapabilityKey,
    EvidenceMode,
    SourceFamily,
)
from cci.pipeline.orchestrator import execute_analysis_pipeline
from cci.reports.exporter import generate_html_brief, generate_markdown_brief


def test_evidence_mode_canonical_enum():
    """Requirement: EvidenceMode defines LIVE, SYNTHETIC, TEST_FIXTURE, RESEARCH_SIMULATION."""
    expected = {
        "LIVE": "live",
        "SYNTHETIC": "synthetic",
        "TEST_FIXTURE": "test_fixture",
        "RESEARCH_SIMULATION": "research_simulation",
    }
    for member_name, val in expected.items():
        assert hasattr(EvidenceMode, member_name)
        member = getattr(EvidenceMode, member_name)
        assert member.value == val
        # Case-insensitive resolution
        assert EvidenceMode(val) == member
        assert EvidenceMode(member_name) == member

    # Backward compatibility with "provided"
    assert EvidenceMode("provided") == EvidenceMode.TEST_FIXTURE
    assert EvidenceMode.PROVIDED == EvidenceMode.TEST_FIXTURE

    # Helper properties
    assert EvidenceMode.LIVE.is_live is True
    assert EvidenceMode.LIVE.is_synthetic is False
    assert EvidenceMode.SYNTHETIC.is_synthetic is True
    assert EvidenceMode.RESEARCH_SIMULATION.is_synthetic is True


def test_live_pipeline_strictly_rejects_synthetic_records():
    """Invariant: Synthetic values must never appear inside live candidate results.

    Passing any evidence marked synthetic into a live analysis run must immediately raise ValueError.
    """
    factors = EvidenceConfidenceFactors(
        artifact_integrity=1.0,
        ownership_score=1.0,
        recency_factor=1.0,
        verification_level=1.0,
        depth_specificity=1.0,
        source_reliability=1.0,
    )
    synthetic_record = EvidenceRecord(
        evidence_id=uuid4(),
        fingerprint="s" * 64,
        source_family=SourceFamily.GITHUB,
        source_locator="https://github.com/alice/project",
        immutable_revision="a" * 40,
        target_capability=CapabilityKey.BACKEND_ENGINEERING,
        support_score=90.0,
        confidence_factors=factors,
        confidence=0.9,
        provenance={"artifact_path": "src/api.py", "synthetic": True},
    )

    with pytest.raises(ValueError, match="Synthetic evidence record.*must never appear in a live candidate analysis run"):
        execute_analysis_pipeline(
            candidate_id=uuid4(),
            role=CanonicalRole.BACKEND,
            custom_evidence=[synthetic_record],
            evidence_mode=EvidenceMode.LIVE,
        )


def test_live_pipeline_permits_authentic_records():
    """Live pipeline accepts authentic non-synthetic records and stamps evidence_mode='live'."""
    factors = EvidenceConfidenceFactors(
        artifact_integrity=1.0,
        ownership_score=1.0,
        recency_factor=1.0,
        verification_level=1.0,
        depth_specificity=1.0,
        source_reliability=1.0,
    )
    live_record = EvidenceRecord(
        evidence_id=uuid4(),
        fingerprint="l" * 64,
        source_family=SourceFamily.GITHUB,
        source_locator="https://github.com/alice/project",
        immutable_revision="a" * 40,
        target_capability=CapabilityKey.BACKEND_ENGINEERING,
        support_score=90.0,
        confidence_factors=factors,
        confidence=0.9,
        provenance={"artifact_path": "src/api.py"},
    )

    state = execute_analysis_pipeline(
        candidate_id=uuid4(),
        role=CanonicalRole.BACKEND,
        custom_evidence=[live_record],
        evidence_mode=EvidenceMode.LIVE,
    )
    assert state.status.value == "completed"
    assert state.dossier is not None
    assert state.dossier.evidence_mode == EvidenceMode.LIVE.value


def test_synthetic_demo_runs_preserve_synthetic_mode_and_labeling():
    """Synthetic demonstration runs preserve evidence_mode and visibly label research simulations."""
    factors = EvidenceConfidenceFactors(
        artifact_integrity=1.0,
        ownership_score=1.0,
        recency_factor=1.0,
        verification_level=1.0,
        depth_specificity=1.0,
        source_reliability=1.0,
    )
    demo_record = EvidenceRecord(
        evidence_id=uuid4(),
        fingerprint="d" * 64,
        source_family=SourceFamily.GITHUB,
        source_locator="https://github.com/alice/demo",
        immutable_revision="a" * 40,
        target_capability=CapabilityKey.BACKEND_ENGINEERING,
        support_score=85.0,
        confidence_factors=factors,
        confidence=0.85,
        provenance={"artifact_path": "src/main.py", "synthetic": True},
    )

    state = execute_analysis_pipeline(
        candidate_id=uuid4(),
        role=CanonicalRole.BACKEND,
        custom_evidence=[demo_record],
        evidence_mode=EvidenceMode.SYNTHETIC,
        scenario="consistent",
    )
    assert state.status.value == "completed"
    dossier = state.dossier
    assert dossier.evidence_mode == EvidenceMode.SYNTHETIC.value

    # Check Markdown report labels research simulation prominently
    md = generate_markdown_brief(dossier, "Synthetic Candidate")
    assert "RESEARCH SIMULATION / SYNTHETIC DEMONSTRATION" in md
    assert "NOT evaluate a real human candidate" in md

    # Check HTML report labels research simulation
    html_report = generate_html_brief(dossier, "Synthetic Candidate")
    assert "RESEARCH SIMULATION" in html_report
    assert "does not assess a real candidate" in html_report


def test_live_dossier_does_not_contain_simulation_warning_banner():
    """Live candidate dossiers do NOT carry the synthetic simulation warning banner."""
    state = execute_analysis_pipeline(
        candidate_id=uuid4(),
        role=CanonicalRole.BACKEND,
        custom_evidence=[],
        evidence_mode=EvidenceMode.LIVE,
    )
    dossier = state.dossier
    assert dossier.evidence_mode == EvidenceMode.LIVE.value

    md = generate_markdown_brief(dossier, "Real Candidate")
    assert "RESEARCH SIMULATION / SYNTHETIC DEMONSTRATION" not in md

    html_report = generate_html_brief(dossier, "Real Candidate")
    assert "RESEARCH SIMULATION:</strong> This profile was generated from synthetic" not in html_report


def test_no_fallback_from_live_failure_to_synthetic():
    """Invariant: When live acquisition fails or has no observations, pipeline does NOT fall back to synthetic data."""
    # When zero observations are found in a live run, it evaluates to zero evidence / unknown, NOT synthetic substitution
    state = execute_analysis_pipeline(
        candidate_id=uuid4(),
        role=CanonicalRole.BACKEND,
        custom_evidence=[],
        evidence_mode=EvidenceMode.LIVE,
    )
    assert state.dossier.evidence_mode == EvidenceMode.LIVE.value
    assert len(state.dossier.evidence_records) == 0
    assert state.dossier.is_insufficient_evidence is True
    assert state.dossier.rci is None
