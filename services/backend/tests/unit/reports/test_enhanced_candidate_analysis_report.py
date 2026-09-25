"""Unit tests verifying high-impact, executive-grade candidate analysis reports.

Tests:
1. Forensic Contradiction Detail breakdown when contradictions exist.
2. Executive 45-Minute Timed Technical Interview Blueprint in Markdown and HTML.
3. Symbol and claim-grounded interview questions with positive/negative evaluation rubrics.
"""

from uuid import uuid4
import pytest

from cci.domain.contracts import (
    CapabilityConflict,
    CapabilityEstimate,
    Dossier,
    EvidenceConfidenceFactors,
    EvidenceRecord,
    NormalizedRequirement,
    ProbePriority,
    InterviewQuestion,
)
from cci.claims.corroborator import ClaimCorroborationResult
from cci.domain.enums import CanonicalRole, CapabilityKey, ClaimStatus, SourceFamily
from cci.dossier.builder import generate_interview_questions
from cci.reports.exporter import (
    _build_interview_blueprint,
    generate_html_brief,
    generate_markdown_brief,
)


@pytest.fixture
def adversarial_dossier():
    """Dossier fixture with verified strengths, a contradictory dimension, and unobserved gaps."""
    cand_id = uuid4()
    run_id = uuid4()

    estimates = {}
    conflicts = {}

    factors_high = EvidenceConfidenceFactors(
        artifact_integrity=1.0,
        ownership_score=0.92,
        recency_factor=0.95,
        verification_level=1.0,
        depth_specificity=0.90,
        source_reliability=0.90,
    )
    factors_contradicted = EvidenceConfidenceFactors(
        artifact_integrity=1.0,
        ownership_score=0.85,
        recency_factor=0.90,
        verification_level=0.90,
        depth_specificity=0.85,
        source_reliability=0.85,
    )

    ev_backend = EvidenceRecord(
        evidence_id=uuid4(),
        fingerprint="sha256:backend_verified",
        source_family=SourceFamily.GITHUB,
        source_locator="https://github.com/candidate/distributed-cache",
        immutable_revision="a1b2c3d4e5f6",
        target_capability=CapabilityKey.BACKEND_ENGINEERING,
        support_score=94.0,
        is_positive_support=True,
        confidence_factors=factors_high,
        confidence=factors_high.composite_confidence,
        cluster_id="cluster-cache",
        provenance={"artifact_path": "src/engine/lru_partition.py"},
    )
    ev_test_pos = EvidenceRecord(
        evidence_id=uuid4(),
        fingerprint="sha256:test_pos",
        source_family=SourceFamily.GITHUB,
        source_locator="https://github.com/candidate/distributed-cache",
        immutable_revision="a1b2c3d4e5f6",
        target_capability=CapabilityKey.TESTING_QUALITY,
        support_score=90.0,
        is_positive_support=True,
        confidence_factors=factors_contradicted,
        confidence=0.40,
        cluster_id="cluster-cache",
        provenance={"artifact_path": "tests/test_unit.py"},
    )
    ev_test_neg = EvidenceRecord(
        evidence_id=uuid4(),
        fingerprint="sha256:test_neg",
        source_family=SourceFamily.GITHUB,
        source_locator="https://github.com/candidate/distributed-cache",
        immutable_revision="a1b2c3d4e5f6",
        target_capability=CapabilityKey.TESTING_QUALITY,
        support_score=20.0,
        is_positive_support=False,
        confidence_factors=factors_contradicted,
        confidence=0.85,
        cluster_id="cluster-cache",
        provenance={"artifact_path": "tests/test_skipped.py"},
    )

    for cap in CapabilityKey:
        if cap == CapabilityKey.BACKEND_ENGINEERING:
            estimates[cap] = CapabilityEstimate(
                capability_key=cap,
                estimate=94.0,
                is_observed=True,
                effective_evidence_count=3.8,
                raw_evidence_count=5,
                cluster_count=2,
                standard_error=1.2,
                dispersion=2.5,
                ci_lower=91.0,
                ci_upper=97.0,
                coverage_k=0.85,
            )
            conflicts[cap] = CapabilityConflict(
                capability_key=cap,
                positive_support_sum=15.0,
                negative_support_sum=0.2,
                contradiction_diagnostic=0.97,
                has_meaningful_conflict=False,
            )
        elif cap == CapabilityKey.TESTING_QUALITY:
            estimates[cap] = CapabilityEstimate(
                capability_key=cap,
                estimate=45.0,
                is_observed=True,
                effective_evidence_count=2.1,
                raw_evidence_count=3,
                cluster_count=1,
                standard_error=4.5,
                dispersion=8.0,
                ci_lower=32.0,
                ci_upper=58.0,
                coverage_k=0.50,
            )
            conflicts[cap] = CapabilityConflict(
                capability_key=cap,
                positive_support_sum=1.2,
                negative_support_sum=4.8,
                contradiction_diagnostic=-0.60,
                has_meaningful_conflict=True,
                triggering_evidence_ids=[ev_test_pos.evidence_id, ev_test_neg.evidence_id],
            )
        else:
            estimates[cap] = CapabilityEstimate(
                capability_key=cap,
                estimate=None,
                is_observed=False,
                effective_evidence_count=0.0,
                raw_evidence_count=0,
                cluster_count=0,
                standard_error=0.0,
                dispersion=0.0,
                ci_lower=None,
                ci_upper=None,
                coverage_k=0.0,
            )
            conflicts[cap] = CapabilityConflict(
                capability_key=cap,
                positive_support_sum=0.0,
                negative_support_sum=0.0,
                contradiction_diagnostic=0.0,
                has_meaningful_conflict=False,
            )

    probes = [
        ProbePriority(
            capability_key=CapabilityKey.TESTING_QUALITY,
            rank=1,
            priority_score=0.88,
            role_weight=0.20,
            coverage_gap_term=0.50,
            uncertainty_term=0.26,
            contradiction_term=0.80,
        ),
        ProbePriority(
            capability_key=CapabilityKey.SOFTWARE_ARCHITECTURE,
            rank=2,
            priority_score=0.75,
            role_weight=0.25,
            coverage_gap_term=1.0,
            uncertainty_term=0.50,
            contradiction_term=0.0,
        ),
        ProbePriority(
            capability_key=CapabilityKey.BACKEND_ENGINEERING,
            rank=3,
            priority_score=0.45,
            role_weight=0.25,
            coverage_gap_term=0.15,
            uncertainty_term=0.06,
            contradiction_term=0.03,
        ),
    ]

    claims = [
        {
            "claim_id": str(uuid4()),
            "claim_text": "Built 99.9% fault-tolerant microservices with 100% automated test coverage",
            "target_capability": CapabilityKey.TESTING_QUALITY.value,
            "status": "contradicted",
            "grounding_evidence_ids": [str(ev_test_neg.evidence_id)],
            "citation_urls": ["https://github.com/candidate/distributed-cache"],
        },
        {
            "claim_id": str(uuid4()),
            "claim_text": "Architected low-latency distributed LRU caching engine",
            "target_capability": CapabilityKey.BACKEND_ENGINEERING.value,
            "status": "corroborated",
            "grounding_evidence_ids": [str(ev_backend.evidence_id)],
            "citation_urls": ["https://github.com/candidate/distributed-cache"],
        },
    ]

    reqs = [
        NormalizedRequirement(
            requirement_id=uuid4(),
            source_text="Requires deep backend engineering",
            normalized_name="Backend Engineering",
            capability_mappings=[CapabilityKey.BACKEND_ENGINEERING],
        ),
        NormalizedRequirement(
            requirement_id=uuid4(),
            source_text="Comprehensive automated test suites required",
            normalized_name="Automated Testing",
            capability_mappings=[CapabilityKey.TESTING_QUALITY],
        ),
    ]

    return Dossier(
        dossier_id=uuid4(),
        candidate_id=cand_id,
        analysis_run_id=run_id,
        role=CanonicalRole.BACKEND,
        rci=75.0,
        coverage=0.42,
        is_insufficient_evidence=False,
        capability_estimates=estimates,
        capability_conflicts=conflicts,
        role_requirements=reqs,
        ownership_assessments=[],
        claims_corroboration=claims,
        interview_probes=probes,
        interview_questions=[
            InterviewQuestion(
                target_capability=CapabilityKey.TESTING_QUALITY,
                question_text="How do you verify automated test quality under load?",
                rationale="High contradiction",
                verification_guidance="Listen for test isolation and flaky test handling",
            )
        ],
        evidence_records=[ev_backend, ev_test_pos, ev_test_neg],
    )


def test_build_interview_blueprint_structure(adversarial_dossier):
    """Verifies that 3-phase interview blueprint is properly synthesized from evidence."""
    bp = _build_interview_blueprint(adversarial_dossier)

    assert "phase_1" in bp
    assert "phase_2" in bp
    assert "phase_3" in bp

    # Phase 1: Verified technical strength (Backend Engineering)
    assert "Backend Engineering" in bp["phase_1"]["capability"]
    assert "94.0/100" in bp["phase_1"]["metric"]

    # Phase 2: Contradiction defense (Testing Quality has D_k = -0.60)
    assert "Testing Quality" in bp["phase_2"]["capability"]
    assert "-0.60" in bp["phase_2"]["metric"]

    # Phase 3: Unobserved gap
    assert bp["phase_3"]["capability"] != ""
    assert "unobserved" in bp["phase_3"]["metric"].lower() or "exploratory" in bp["phase_3"]["metric"].lower()


def test_markdown_brief_contains_blueprint_and_forensic_contradictions(adversarial_dossier):
    """Verifies that Markdown brief renders the 45-minute blueprint and forensic contradiction detail."""
    md = generate_markdown_brief(adversarial_dossier, candidate_name="Jordan Executive")

    # 1. Forensic contradiction section
    assert "## 3. Contradiction Diagnostics" in md
    assert "### 3.1 Forensic Contradiction Detail & Defense Rubrics" in md
    assert "Testing Quality" in md
    assert "-0.60" in md
    assert "Interviewer Action:" in md

    # 2. Executive 45-minute blueprint table
    assert "## 4.1 Executive 45-Minute Timed Technical Interview Blueprint" in md
    assert "00:00 – 15:00" in md
    assert "15:00 – 30:00" in md
    assert "30:00 – 45:00" in md
    assert "Verified Mastery Deep-Dive" in md
    assert "Contradiction Defense" in md
    assert "Unobserved Gap Scenario" in md
    assert "Interviewer Time Management:" in md


def test_html_brief_contains_interactive_blueprint(adversarial_dossier):
    """Verifies that HTML brief contains visual timeline cards and rubrics."""
    html_doc = generate_html_brief(adversarial_dossier, candidate_name="Jordan Executive")

    assert "3.1 Executive 45-Minute Timed Technical Interview Blueprint" in html_doc
    assert "blueprint-container" in html_doc
    assert "Phase 1: Verified Depth" in html_doc
    assert "Phase 2: Contradiction" in html_doc
    assert "Phase 3: Gap Architecture" in html_doc
    assert "rubric-pos" in html_doc
    assert "rubric-neg" in html_doc


def test_generate_interview_questions_injects_claims_and_rubrics(adversarial_dossier):
    """Verifies that dynamic interview questions reference claims and evaluation rubrics."""
    claims = [
        ClaimCorroborationResult(
            claim_id=uuid4(),
            claim_text="100% automated test coverage in production",
            target_capability=CapabilityKey.TESTING_QUALITY,
            status=ClaimStatus.CONTRADICTED,
            confidence=0.85,
            grounding_evidence_ids=[adversarial_dossier.evidence_records[2].evidence_id],
            citation_urls=["https://github.com/candidate/distributed-cache"],
            explanation="Contradicted by missing and skipped tests",
        )
    ]

    questions = generate_interview_questions(
        probes=adversarial_dossier.interview_probes,
        capability_conflicts=adversarial_dossier.capability_conflicts,
        evidence_records=adversarial_dossier.evidence_records,
        claims_corroboration=claims,
    )

    test_q = next(q for q in questions if q.target_capability == CapabilityKey.TESTING_QUALITY)
    assert "100% automated test coverage in production" in test_q.question_text
    assert "D_k=-0.60" in test_q.question_text
    assert "Rubric — Positive:" in test_q.verification_guidance
    assert "Negative:" in test_q.verification_guidance
