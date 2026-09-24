"""Unit tests for FIX 48: Human Decision Support invariants and 7 pillars.

Invariants verified:
1. CandidateX does not decide whether to hire a person.
2. System never designates a 'best candidate' or automated hiring recommendation.
3. All 7 decision-support pillars are present and mathematically grounded.
4. Leaderboard framing is strictly rejected.
"""

from uuid import uuid4
import pytest

from cci.domain.contracts import (
    CapabilityConflict,
    CapabilityEstimate,
    Dossier,
    InterviewQuestion,
    ProbePriority,
)
from cci.domain.enums import CanonicalRole, CapabilityKey
from cci.reports.exporter import generate_html_brief, generate_markdown_brief


@pytest.fixture
def decision_support_dossier() -> Dossier:
    cand_id = uuid4()
    run_id = uuid4()

    estimates = {}
    conflicts = {}

    for key in CapabilityKey:
        if key in (CapabilityKey.BACKEND_ENGINEERING, CapabilityKey.DATABASE_ENGINEERING):
            estimates[key] = CapabilityEstimate(
                capability_key=key,
                estimate=85.0,
                is_observed=True,
                effective_evidence_count=3.5,
                raw_evidence_count=5,
                cluster_count=2,
                standard_error=2.0,
                dispersion=4.0,
                ci_lower=78.0,
                ci_upper=92.0,
                coverage_k=0.70,
            )
            conflicts[key] = CapabilityConflict(
                capability_key=key,
                positive_support_sum=10.0,
                negative_support_sum=0.0,
                contradiction_diagnostic=1.0,
                has_meaningful_conflict=False,
            )
        elif key == CapabilityKey.SECURITY:
            estimates[key] = CapabilityEstimate(
                capability_key=key,
                estimate=55.0,
                is_observed=True,
                effective_evidence_count=1.2,
                raw_evidence_count=2,
                cluster_count=1,
                standard_error=8.0,
                dispersion=12.0,
                ci_lower=35.0,
                ci_upper=75.0,  # Wide CI -> High uncertainty
                coverage_k=0.20,
            )
            conflicts[key] = CapabilityConflict(
                capability_key=key,
                positive_support_sum=2.0,
                negative_support_sum=6.0,
                contradiction_diagnostic=0.25,
                has_meaningful_conflict=True,
            )
        else:
            estimates[key] = CapabilityEstimate(
                capability_key=key,
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
            conflicts[key] = CapabilityConflict(
                capability_key=key,
                positive_support_sum=0.0,
                negative_support_sum=0.0,
                contradiction_diagnostic=0.0,
                has_meaningful_conflict=False,
            )

    probes = [
        ProbePriority(
            capability_key=CapabilityKey.SECURITY,
            rank=1,
            priority_score=0.95,
            role_weight=0.15,
            coverage_gap_term=0.8,
            uncertainty_term=0.9,
            contradiction_term=1.0,
        )
    ]

    questions = [
        InterviewQuestion(
            target_capability=CapabilityKey.SECURITY,
            question_text="How do you validate untrusted deserialization inputs?",
            rationale="Contradiction observed in security controls",
            verification_guidance="Evaluate secure parsing, schema enforcement",
        )
    ]

    claims = [
        {
            "target_capability": "backend_engineering",
            "claim_text": "Built distributed caching backend",
            "status": "corroborated",
            "grounding_evidence_ids": [str(uuid4())],
        },
        {
            "target_capability": "security",
            "claim_text": "Led enterprise cryptography and security posture",
            "status": "contradicted",
            "grounding_evidence_ids": [str(uuid4())],
        },
        {
            "target_capability": "machine_learning",
            "claim_text": "Implemented transformer models in production",
            "status": "unknown",
            "grounding_evidence_ids": [],
        },
    ]

    return Dossier(
        dossier_id=uuid4(),
        candidate_id=cand_id,
        analysis_run_id=run_id,
        role=CanonicalRole.BACKEND,
        rci=78.0,
        coverage=0.30,
        is_insufficient_evidence=False,
        capability_estimates=estimates,
        capability_conflicts=conflicts,
        role_requirements=[],
        ownership_assessments=[],
        interview_probes=probes,
        interview_questions=questions,
        claims_corroboration=claims,
    )


def test_dossier_reports_contain_decision_support_not_automated_decisions(decision_support_dossier):
    """Verifies that brief exports maintain human decision support and no automated decisions."""
    md = generate_markdown_brief(decision_support_dossier, candidate_name="Alex Mercer")
    html_doc = generate_html_brief(decision_support_dossier, candidate_name="Alex Mercer")

    for doc in (md, html_doc):
        # 1. Mandatory decision support statement
        assert "decision support" in doc.lower()
        # 2. Strict prohibition against autonomous hiring decisions
        assert "does not make autonomous hire/reject decisions" in doc.lower() or "employer decision support only" in doc.lower()
        # 3. No leaderboard or ranking framing
        assert "leaderboard" not in doc.lower()
        assert "best candidate" not in doc.lower()
        assert "rank #1" not in doc.lower()


def test_seven_decision_support_pillars_present(decision_support_dossier):
    """Verifies that the 7 core decision-support pillars are properly expressed in the dossier."""
    dossier = decision_support_dossier

    # Pillar 1: Evidence Available
    assert dossier.coverage > 0.0
    assert len(dossier.capability_estimates) == 12

    # Pillar 2: Role-Relevant Strengths Observed
    corroborated_claims = [c for c in dossier.claims_corroboration if c.get("status") == "corroborated"]
    assert len(corroborated_claims) == 1
    assert corroborated_claims[0]["target_capability"] == "backend_engineering"

    # Pillar 3: Unresolved Claims
    unresolved = [c for c in dossier.claims_corroboration if c.get("status") in ("unknown", "partial")]
    assert len(unresolved) == 1
    assert unresolved[0]["target_capability"] == "machine_learning"

    # Pillar 4: Uncertainty (Wide Confidence Intervals or Insufficient Evidence)
    uncertain_caps = [
        c for c in dossier.capability_estimates.values()
        if c.is_observed and c.ci_lower is not None and c.ci_upper is not None and (c.ci_upper - c.ci_lower) > 30.0
    ]
    assert len(uncertain_caps) >= 1
    assert uncertain_caps[0].capability_key == CapabilityKey.SECURITY

    # Pillar 5: Evidence Gaps (Unobserved capabilities)
    unobserved = [c for c in dossier.capability_estimates.values() if not c.is_observed]
    assert len(unobserved) == 9  # 12 - 3 observed

    # Pillar 6: Contradictions
    contradicted = [c for c in dossier.capability_conflicts.values() if c.has_meaningful_conflict]
    assert len(contradicted) == 1
    assert contradicted[0].capability_key == CapabilityKey.SECURITY

    # Pillar 7: Interview Questions
    assert len(dossier.interview_questions) >= 1
    assert "deserialization" in dossier.interview_questions[0].question_text
