"""Diminishing weights for correlated observations within evidence families."""

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable
from uuid import UUID

from cci.domain.contracts import EvidenceRecord
from cci.domain.evidence_families import build_fallback_evidence_family_identity


@dataclass(frozen=True)
class EvidenceFamilyWeightInput:
    """The persisted facts needed to assign a deterministic family contribution."""

    evidence_id: UUID
    evidence_family_id: str
    observation_type: str
    is_positive_support: bool
    confidence: float
    fingerprint: str


def family_weight_input_from_record(
    record: EvidenceRecord,
) -> EvidenceFamilyWeightInput:
    """Builds a weight input, deriving a conservative ID for legacy records."""
    family_id = record.evidence_family_id
    if family_id is None:
        family_id = build_fallback_evidence_family_identity(
            source_family=record.source_family,
            cluster_id=record.cluster_id or record.source_locator,
            artifact_path=record.provenance.get("artifact_path"),
            capability=record.target_capability,
            observation_type=record.observation_type,
            fingerprint=record.fingerprint,
        ).evidence_family_id

    return EvidenceFamilyWeightInput(
        evidence_id=record.evidence_id,
        evidence_family_id=family_id,
        observation_type=record.observation_type,
        is_positive_support=record.is_positive_support,
        confidence=record.confidence,
        fingerprint=record.fingerprint,
    )


def compute_evidence_family_weights(
    items: Iterable[EvidenceFamilyWeightInput],
    *,
    decay: float,
) -> dict[UUID, float]:
    """Returns one geometric contribution per observation, retaining every row.

    Each family keeps the strongest observation for each analyzer modality and
    support polarity. Those representatives receive geometric weights ordered
    by confidence; repeated observations of the same modality and polarity stay
    in the returned map with zero contribution.
    """
    if not 0.0 <= decay < 1.0:
        raise ValueError("decay must be in the range [0, 1)")

    grouped: dict[str, list[EvidenceFamilyWeightInput]] = defaultdict(list)
    weights: dict[UUID, float] = {}
    for item in items:
        weights[item.evidence_id] = 0.0
        grouped[item.evidence_family_id].append(item)

    for family_items in grouped.values():
        strongest_by_observation: dict[
            tuple[str, bool], EvidenceFamilyWeightInput
        ] = {}
        for item in family_items:
            key = (item.observation_type, item.is_positive_support)
            current = strongest_by_observation.get(key)
            if current is None or (
                item.confidence,
                item.fingerprint,
                str(item.evidence_id),
            ) > (
                current.confidence,
                current.fingerprint,
                str(current.evidence_id),
            ):
                strongest_by_observation[key] = item

        representatives = sorted(
            strongest_by_observation.values(),
            key=lambda item: (
                -item.confidence,
                item.observation_type,
                item.is_positive_support,
                item.fingerprint,
                str(item.evidence_id),
            ),
        )
        for rank, item in enumerate(representatives):
            weights[item.evidence_id] = decay**rank

    return weights
