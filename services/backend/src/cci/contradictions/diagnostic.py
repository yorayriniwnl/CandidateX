"""Contradiction diagnostic D_k between positive and negative evidence."""

from collections.abc import Mapping
from uuid import UUID

from cci.contradictions.qualification import is_qualified_negative
from cci.domain.contracts import CapabilityConflict, EvidenceRecord, ScoringConfig
from cci.domain.enums import CapabilityKey
from cci.scoring.evidence_families import compute_record_family_weights


def compute_contradiction_diagnostic(
    evidence_records: list[EvidenceRecord],
    capability: CapabilityKey,
    config: ScoringConfig | None = None,
    family_weights: Mapping[UUID, float] | None = None,
) -> CapabilityConflict:
    """Computes contradiction diagnostic:

        D_k = (P_k - N_k) / (P_k + N_k + epsilon)

    where P_k is confidence sum of positive evidence and N_k is confidence sum of negative evidence.
    D_k is strictly bounded within [-1.0, 1.0].
    """
    cfg = config or ScoringConfig()
    eps = cfg.epsilon

    relevant = [
        e
        for e in evidence_records
        if e.target_capability == capability
        and e.confidence > 0.0
        and (e.is_positive_support or is_qualified_negative(e))
    ]

    if family_weights is None:
        family_weights = compute_record_family_weights(
            relevant, decay=cfg.evidence_family_decay
        )

    pos_records = [e for e in relevant if e.is_positive_support]
    neg_records = [e for e in relevant if not e.is_positive_support]

    P_k = sum(
        e.confidence * family_weights[e.evidence_id] for e in pos_records
    )
    N_k = sum(
        e.confidence * family_weights[e.evidence_id] for e in neg_records
    )

    denominator = P_k + N_k + eps
    D_k = float((P_k - N_k) / denominator)

    # Strict clamping
    D_k = max(-1.0, min(1.0, D_k))

    # Meaningful conflict threshold: both positive and negative evidence exist
    total_support = P_k + N_k
    has_conflict = False
    triggering_ids = []

    if total_support > 0.2 and P_k > 0.1 * total_support and N_k > 0.1 * total_support:
        has_conflict = True
        triggering_ids = [e.evidence_id for e in relevant]

    return CapabilityConflict(
        capability_key=capability,
        positive_support_sum=float(P_k),
        negative_support_sum=float(N_k),
        contradiction_diagnostic=D_k,
        has_meaningful_conflict=has_conflict,
        triggering_evidence_ids=triggering_ids,
    )
