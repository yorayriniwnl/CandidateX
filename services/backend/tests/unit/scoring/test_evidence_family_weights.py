"""Family weights bound repeated analyzer emissions without dropping provenance."""

from hashlib import sha256
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import pytest

from cci.domain.contracts import EvidenceConfidenceFactors, EvidenceRecord
from cci.domain.enums import CapabilityKey, SourceFamily
from cci.scoring.evidence_families import (
    EvidenceFamilyWeightInput,
    compute_evidence_family_weights,
    family_weight_input_from_record,
)


FAMILY_ID = "ef1:" + "f" * 64
REPO_URL = "https://github.com/acme/api"


def _weight_input(
    name: str,
    observation_type: str,
    polarity: bool,
    confidence: float,
    *,
    family_id: str = FAMILY_ID,
    fingerprint: str | None = None,
    evidence_id: UUID | None = None,
) -> EvidenceFamilyWeightInput:
    return EvidenceFamilyWeightInput(
        evidence_id=evidence_id or uuid5(NAMESPACE_URL, f"weight-test:{name}"),
        evidence_family_id=family_id,
        observation_type=observation_type,
        is_positive_support=polarity,
        confidence=confidence,
        fingerprint=fingerprint or sha256(name.encode()).hexdigest(),
    )


def _record(
    *,
    evidence_id: UUID,
    fingerprint: str,
    artifact_path: str,
    evidence_family_id: str | None = None,
    observation_type: str = "dependency:manifest",
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
        evidence_id=evidence_id,
        fingerprint=fingerprint,
        source_family=SourceFamily.GITHUB,
        source_locator=REPO_URL,
        immutable_revision="a" * 40,
        target_capability=CapabilityKey.BACKEND_ENGINEERING,
        support_score=75.0,
        confidence_factors=factors,
        confidence=0.8,
        cluster_id=REPO_URL,
        evidence_family_id=evidence_family_id,
        observation_type=observation_type,
        provenance={"artifact_path": artifact_path},
    )


def test_one_representative_per_type_and_polarity_gets_diminishing_weights():
    manifest = _weight_input("manifest", "dependency:manifest", True, 0.9)
    duplicate_manifest = _weight_input(
        "duplicate-manifest",
        "dependency:manifest",
        True,
        0.8,
    )
    import_use = _weight_input("import", "dependency:python_import", True, 0.7)

    weights = compute_evidence_family_weights(
        [manifest, duplicate_manifest, import_use],
        decay=0.5,
    )

    assert weights[manifest.evidence_id] == 1.0
    assert weights[duplicate_manifest.evidence_id] == 0.0
    assert weights[import_use.evidence_id] == 0.5
    assert set(weights) == {
        manifest.evidence_id,
        duplicate_manifest.evidence_id,
        import_use.evidence_id,
    }


def test_representative_ties_are_stable_under_input_reordering():
    lower = _weight_input(
        "lower",
        "dependency:manifest",
        True,
        0.8,
        fingerprint="a" * 64,
    )
    higher = _weight_input(
        "higher",
        "dependency:manifest",
        True,
        0.8,
        fingerprint="z" * 64,
    )

    forward = compute_evidence_family_weights([lower, higher], decay=0.5)
    reverse = compute_evidence_family_weights([higher, lower], decay=0.5)

    assert forward == reverse
    assert forward[higher.evidence_id] == 1.0
    assert forward[lower.evidence_id] == 0.0


def test_positive_and_negative_observations_remain_separate_representatives():
    positive = _weight_input("positive", "route:python_decorator", True, 0.7)
    negative = _weight_input("negative", "route:python_decorator", False, 0.9)

    weights = compute_evidence_family_weights([positive, negative], decay=0.5)

    assert weights[negative.evidence_id] == 1.0
    assert weights[positive.evidence_id] == 0.5


def test_zero_decay_keeps_nonrepresentative_rows_with_zero_weight():
    manifest = _weight_input("manifest", "dependency:manifest", True, 0.9)
    duplicate = _weight_input("duplicate", "dependency:manifest", True, 0.8)
    import_use = _weight_input("import", "dependency:python_import", True, 0.7)

    weights = compute_evidence_family_weights(
        [manifest, duplicate, import_use],
        decay=0.0,
    )

    assert weights[manifest.evidence_id] == 1.0
    assert weights[duplicate.evidence_id] == 0.0
    assert weights[import_use.evidence_id] == 0.0


def test_identical_fingerprints_in_separate_explicit_families_are_not_merged():
    first = _weight_input(
        "first-family",
        "dependency:manifest",
        True,
        0.8,
        family_id="ef1:" + "a" * 64,
        fingerprint="c" * 64,
    )
    second = _weight_input(
        "second-family",
        "dependency:manifest",
        True,
        0.8,
        family_id="ef1:" + "b" * 64,
        fingerprint="c" * 64,
    )

    weights = compute_evidence_family_weights([first, second], decay=0.5)

    assert weights[first.evidence_id] == 1.0
    assert weights[second.evidence_id] == 1.0


def test_missing_family_uses_source_artifact_type_and_fingerprint_fallback():
    fingerprint = "c" * 64
    first = _record(
        evidence_id=UUID(int=2),
        fingerprint=fingerprint,
        artifact_path="requirements.txt",
    )
    repeated = _record(
        evidence_id=UUID(int=1),
        fingerprint=fingerprint,
        artifact_path="requirements.txt",
    )
    other_artifact = _record(
        evidence_id=UUID(int=3),
        fingerprint=fingerprint,
        artifact_path="pyproject.toml",
    )
    items = [
        family_weight_input_from_record(record)
        for record in (first, repeated, other_artifact)
    ]

    weights = compute_evidence_family_weights(items, decay=0.5)

    assert items[0].evidence_family_id == items[1].evidence_family_id
    assert items[0].evidence_family_id != items[2].evidence_family_id
    assert weights[first.evidence_id] == 1.0
    assert weights[repeated.evidence_id] == 0.0
    assert weights[other_artifact.evidence_id] == 1.0


@pytest.mark.parametrize("decay", [-0.01, 1.0])
def test_weight_helper_rejects_decay_outside_configured_range(decay: float):
    item = _weight_input("only", "dependency:manifest", True, 0.8)

    with pytest.raises(ValueError):
        compute_evidence_family_weights([item], decay=decay)
