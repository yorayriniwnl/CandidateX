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
from cci.domain.enums import CanonicalRole, CapabilityKey



def _contextual_probe(evidence_records: list[EvidenceRecord]) -> tuple[str | None, list[str]]:
    """Build an artifact-specific interview prompt from deterministic evidence cues."""
    if not evidence_records:
        return None, []

    ranked = sorted(evidence_records, key=lambda item: item.confidence, reverse=True)
    primary = ranked[0]
    provenance = primary.provenance or {}
    artifact = provenance.get("artifact_path") or "the observed artifact"
    support = " ".join(
        str((item.provenance or {}).get("raw_support_text", ""))
        for item in ranked[:4]
    ).lower()
    paths = " ".join(
        str((item.provenance or {}).get("artifact_path", ""))
        for item in ranked[:4]
    ).lower()
    context = f"{paths} {support}"

    if any(term in context for term in ("jwt", "oauth", "authorization", "authentication", "permission", "security")):
        return (
            f"In {artifact}, walk through the trust boundary end to end: what is authenticated, "
            "what is authorized, where validation occurs, and what failure mode you were defending against?",
            [
                "Which attack or misuse case influenced this design most?",
                "How would you test that an authorization bypass cannot occur?",
            ],
        )
    if any(term in context for term in ("transaction", "migration", "foreign key", "rollback", "sqlalchemy", "database")):
        return (
            f"Using {artifact}, explain the data-integrity decisions: schema boundaries, transaction scope, "
            "failure behavior, and the query or indexing trade-off that mattered most.",
            [
                "What breaks if two requests update the same data concurrently?",
                "Which invariant belongs in the database rather than application code?",
            ],
        )
    if any(term in context for term in ("async", "await", "goroutine", "channel", "queue", "semaphore", "worker")):
        return (
            f"In {artifact}, trace one concurrent or asynchronous path from entry to completion. "
            "Where can work pile up, how is cancellation or failure handled, and what bounds resource use?",
            [
                "What is the back-pressure strategy under a sudden traffic spike?",
                "Which race condition or ordering bug would you test first?",
            ],
        )
    if any(term in context for term in ("pytest", "jest", "vitest", "playwright", "cypress", "mock", "fixture", "assert")):
        return (
            f"Using {artifact}, explain what the test is actually protecting. Which regression would it catch, "
            "what important behavior is still untested, and why was this test boundary chosen?",
            [
                "Which assertion would you keep if the test had to be reduced to one?",
                "What would require an integration test instead of a unit test?",
            ],
        )
    if any(term in context for term in ("docker", "kubernetes", "terraform", "workflow", "ci/cd", "deployment")):
        return (
            f"Using {artifact}, walk through the delivery path from source change to a running service. "
            "Where can deployment fail safely, what is immutable, and how would you roll back?",
            [
                "Which configuration should never be baked into the image?",
                "What health signal decides whether a rollout continues?",
            ],
        )
    if any(term in context for term in ("route", "endpoint", "handler", "@app.", "requestmapping", "getmapping", "postmapping")):
        return (
            f"Pick the request path represented in {artifact} and trace it end to end: validation, business logic, "
            "persistence or downstream calls, error mapping, and the response contract.",
            [
                "Which part of this request path is hardest to make idempotent?",
                "What would you instrument to diagnose a slow request in production?",
            ],
        )
    if any(term in context for term in ("architecture", "domain", "adapter", "repository", "service", "controller", "interface")):
        return (
            f"In {artifact}, explain the boundary between components and why it exists. "
            "Which dependency direction is intentional, and what change would force you to redraw that boundary?",
            [
                "Where is coupling still higher than you would like?",
                "Which interface is protecting a real variation point versus adding ceremony?",
            ],
        )

    return (
        f"Using {artifact}, explain the implementation decision represented by this evidence, "
        "the trade-off you accepted, and the failure case that would make you redesign it.",
        [
            "What evidence would convince you that this design is no longer adequate?",
        ],
    )

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
        contextual_question, contextual_followups = _contextual_probe(ev_list)

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
                *contextual_followups[:1],
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
            q_text = contextual_question or (
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
            followups = contextual_followups or [
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
    is_insufficient_evidence: bool = False,
) -> Dossier:
    """Builds a complete, immutable Dossier snapshot."""
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
        is_insufficient_evidence=is_insufficient_evidence,
        capability_estimates=capability_estimates,
        capability_conflicts=capability_conflicts,
        role_requirements=role_requirements,
        ownership_assessments=ownership_assessments,
        claims_corroboration=claims_dicts,
        interview_probes=interview_probes,
        interview_questions=interview_questions,
    )
