"""Candidate Technical Dossier Builder.

INVARIANTS:
1. Dossier provides decision support to human technical interviewers, NEVER autonomous hire/reject.
2. Every interview probe is explicitly grounded in verified evidence citations or coverage gaps.
3. Strict multi-tenancy and audit tracking are preserved.
"""

from uuid import UUID, uuid4

from cci.claims.corroborator import ClaimCorroborationResult
from cci.domain.contracts import (
    CapabilityConflict,
    CapabilityEstimate,
    Dossier,
    EvidenceRecord,
    InterviewQuestion,
    NormalizedRequirement,
    OwnershipAssessment,
    ProbePriority,
)
from cci.domain.coverage_policy import (
    DEFAULT_COVERAGE_SUFFICIENCY_THRESHOLD,
    is_coverage_sufficient,
)
from cci.domain.enums import CanonicalRole, CapabilityKey


def generate_interview_questions(
    probes: list[ProbePriority],
    capability_conflicts: dict[CapabilityKey, CapabilityConflict],
    evidence_records: list[EvidenceRecord],
    claims_corroboration: list[ClaimCorroborationResult] | None = None,
    max_questions: int = 5,
) -> list[InterviewQuestion]:
    """Generates evidence-grounded probe questions based on ranked inquiry priorities."""
    questions: list[InterviewQuestion] = []
    evidence_by_cap: dict[CapabilityKey, list[EvidenceRecord]] = {}
    for ev in evidence_records:
        evidence_by_cap.setdefault(ev.target_capability, []).append(ev)

    # Sort probes by rank
    sorted_probes = sorted(probes, key=lambda p: p.rank)[:max_questions]

    for probe in sorted_probes:
        cap_key = probe.capability_key
        ev_list = evidence_by_cap.get(cap_key, [])
        conflict = capability_conflicts.get(cap_key)
        has_conflict = conflict.has_meaningful_conflict if conflict else False

        grounding_ids = [e.evidence_id for e in ev_list[:3]]
        sample_artifacts = [
            e.provenance.get("artifact_path", "")
            for e in ev_list
            if e.provenance.get("artifact_path")
        ][:2]
        art_mention = (
            f" (e.g. in {', '.join(sample_artifacts)})" if sample_artifacts else ""
        )

        if has_conflict:
            q_text = (
                f"We observed conflicting signals regarding {cap_key.value}{art_mention}. "
                f"Could you explain your specific design decisions and the engineering trade-offs you made?"
            )
            d_k_val = conflict.contradiction_diagnostic if conflict else 0.0
            rationale = (
                f"High contradiction diagnostic (D_k={d_k_val:.2f}) "
                f"with role importance weight w_k={probe.role_weight:.3f}."
            )
            guidance = (
                "Listen for candid discussion of system limitations, debugging approaches, "
                "and how the candidate reconciled conflicting engineering requirements."
            )
            followups = [
                "What would you do differently if rebuilding this component today?",
                "How did you verify system behavior under failure conditions?",
            ]
        elif probe.coverage_gap_term > 0.5:
            q_text = (
                f"There is limited direct repository evidence for {cap_key.value}. "
                f"Could you walk through a production system or project where you designed or implemented this capability?"
            )
            rationale = (
                f"Large evidence coverage gap (1 - Cov_k = {probe.coverage_gap_term:.2f}) "
                f"for a high-priority role capability (w_k={probe.role_weight:.3f})."
            )
            guidance = (
                "Listen for specific technical details (architecture, concurrency, error handling) "
                "indicating deep hands-on mastery rather than theoretical familiarity."
            )
            followups = [
                "What were the most challenging edge cases or bottlenecks encountered?",
                "How did your team monitor and maintain this service in production?",
            ]
        else:
            q_text = (
                f"In your work on {cap_key.value}{art_mention}, how did you approach "
                f"architectural scalability, testing, and operational reliability?"
            )
            rationale = (
                f"Ranked inquiry target (Rank {probe.rank}, priority score {probe.priority_score:.2f}) "
                f"to validate verified evidence depth."
            )
            guidance = (
                "Listen for architectural rigor, clear ownership boundaries, "
                "and familiarity with production trade-offs."
            )
            followups = [
                "How did you establish automated testing or continuous validation?",
            ]

        questions.append(
            InterviewQuestion(
                question_id=uuid4(),
                target_capability=cap_key,
                question_text=q_text,
                rationale=rationale,
                verification_guidance=guidance,
                grounding_evidence_ids=grounding_ids,
                suggested_followups=followups,
            )
        )

    return questions


def build_candidate_dossier(
    candidate_id: UUID,
    analysis_run_id: UUID,
    role: CanonicalRole,
    capability_estimates: dict[CapabilityKey, CapabilityEstimate],
    capability_conflicts: dict[CapabilityKey, CapabilityConflict],
    role_requirements: list[NormalizedRequirement],
    ownership_assessments: list[OwnershipAssessment],
    claims_corroboration: list[ClaimCorroborationResult],
    interview_probes: list[ProbePriority],
    interview_questions: list[InterviewQuestion] | None = None,
    evidence_records: list[EvidenceRecord] | None = None,
    rci: float | None = None,
    coverage: float = 0.0,
    is_insufficient_evidence: bool | None = None,
    coverage_sufficiency_threshold: float = DEFAULT_COVERAGE_SUFFICIENCY_THRESHOLD,
) -> Dossier:
    """Builds a complete, immutable Dossier snapshot."""
    computed_insufficient = not is_coverage_sufficient(
        coverage, threshold=coverage_sufficiency_threshold
    )
    if (
        is_insufficient_evidence is not None
        and is_insufficient_evidence != computed_insufficient
    ):
        raise ValueError(
            "Dossier insufficiency must match the configured coverage threshold"
        )

    # Generate questions if not explicitly provided
    if interview_questions is None:
        interview_questions = generate_interview_questions(
            probes=interview_probes,
            capability_conflicts=capability_conflicts,
            evidence_records=evidence_records or [],
            claims_corroboration=claims_corroboration,
        )

    # Convert claims corroboration to contract dict format
    claims_dicts = [c.to_dict() for c in claims_corroboration]

    return Dossier(
        dossier_id=uuid4(),
        candidate_id=candidate_id,
        analysis_run_id=analysis_run_id,
        role=role,
        rci=rci,
        coverage=coverage,
        coverage_sufficiency_threshold=coverage_sufficiency_threshold,
        is_insufficient_evidence=computed_insufficient,
        capability_estimates=capability_estimates,
        capability_conflicts=capability_conflicts,
        role_requirements=role_requirements,
        ownership_assessments=ownership_assessments,
        claims_corroboration=claims_dicts,
        interview_probes=interview_probes,
        interview_questions=interview_questions,
        evidence_records=evidence_records or [],
    )
