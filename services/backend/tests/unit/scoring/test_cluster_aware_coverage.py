"""Coverage must reward independent sources and diverse artifacts, not analyzer volume."""

from hashlib import sha256

import pytest

from cci.domain.contracts import EvidenceConfidenceFactors, EvidenceRecord, ScoringConfig
from cci.domain.enums import CapabilityKey, SourceFamily
from cci.scoring.capability import compute_capability_score
from cci.uncertainty.bootstrap import cluster_bootstrap_ci


CAPABILITY = CapabilityKey.BACKEND_ENGINEERING


def _record(
    observation: str,
    cluster: str,
    *,
    family: SourceFamily = SourceFamily.GITHUB,
    artifact_path: str = "src/service.py",
    artifact_hash: str | None = None,
    confidence: float = 1.0,
) -> EvidenceRecord:
    artifact_hash = artifact_hash or sha256(
        f"{family.value}/{cluster}/{artifact_path}".encode()
    ).hexdigest()
    factors = EvidenceConfidenceFactors(
        artifact_integrity=1.0,
        ownership_score=confidence,
        recency_factor=1.0,
        verification_level=1.0,
        depth_specificity=1.0,
        source_reliability=1.0,
    )
    return EvidenceRecord(
        fingerprint=sha256(f"{cluster}/{artifact_path}/{observation}".encode()).hexdigest(),
        source_family=family,
        source_locator=f"https://{family.value}.example/{cluster}",
        immutable_revision=f"revision-{cluster}",
        target_capability=CAPABILITY,
        support_score=90.0,
        confidence_factors=factors,
        confidence=confidence,
        cluster_id=cluster,
        provenance={"artifact_path": artifact_path, "artifact_sha256": artifact_hash},
    )


def _coverage(records: list[EvidenceRecord], config: ScoringConfig | None = None):
    return compute_capability_score(records, CAPABILITY, config=config)


def test_twenty_observations_from_one_file_in_one_repository_count_once():
    records = [_record(str(i), "repo-a") for i in range(20)]

    estimate = _coverage(records)

    assert estimate.coverage_k == pytest.approx(0.2)
    assert estimate.cluster_count == 1
    assert estimate.raw_evidence_count == 20
    assert estimate.is_observed is False
    assert estimate.estimate is None


def test_distinct_artifacts_in_one_repository_have_diminishing_returns():
    records = [
        _record(str(i), "repo-a", artifact_path=f"src/module_{i}.py")
        for i in range(20)
    ]

    estimate = _coverage(records)

    # 1 + 1/2 + ... + 1/2^19, normalized by tau=5.
    expected = (2.0 - 0.5**19) / 5.0
    assert estimate.coverage_k == pytest.approx(expected)
    assert estimate.coverage_k < 0.41
    assert estimate.cluster_count == 1


def test_two_repositories_with_ten_artifacts_each_outweigh_one_repository():
    one_repository = [
        _record(str(i), "repo-a", artifact_path=f"src/module_{i}.py")
        for i in range(20)
    ]
    two_repositories = [
        _record(f"{repo}-{i}", repo, artifact_path=f"src/module_{i}.py")
        for repo in ("repo-a", "repo-b")
        for i in range(10)
    ]

    one = _coverage(one_repository)
    two = _coverage(two_repositories)

    expected_two = 2.0 * (2.0 - 0.5**9) / 5.0
    assert one.coverage_k < two.coverage_k
    assert two.coverage_k == pytest.approx(expected_two)
    assert two.cluster_count == 2


@pytest.mark.parametrize("independent_family", [SourceFamily.DEPLOYMENT, SourceFamily.CERTIFICATE])
def test_independent_deployment_or_certificate_adds_a_source_cluster(independent_family):
    records = [
        _record("repo", "project-1"),
        _record("independent", "project-1", family=independent_family),
    ]

    estimate = _coverage(records)

    assert estimate.coverage_k == pytest.approx(0.4)
    assert estimate.cluster_count == 2


def test_three_independent_projects_provide_three_units_of_coverage():
    records = [_record(str(i), f"project-{i}") for i in range(3)]

    estimate = _coverage(records)

    assert estimate.coverage_k == pytest.approx(0.6)
    assert estimate.cluster_count == 3


def test_duplicate_observation_does_not_increase_coverage():
    record = _record("same-fact", "repo-a")

    one = _coverage([record])
    duplicated = _coverage([record, record])

    assert duplicated.coverage_k == one.coverage_k == pytest.approx(0.2)
    assert duplicated.cluster_count == one.cluster_count == 1


def test_identical_artifact_copied_between_repositories_is_credited_once():
    shared_hash = sha256(b"identical artifact contents").hexdigest()
    records = [
        _record("copy-a", "repo-a", artifact_hash=shared_hash),
        _record("copy-b", "repo-b", artifact_hash=shared_hash),
    ]

    estimate = _coverage(records)

    assert estimate.coverage_k == pytest.approx(0.2)
    assert estimate.cluster_count == 1
    assert cluster_bootstrap_ci(records, CAPABILITY) == (None, None)


def test_configured_within_cluster_decay_changes_only_distinct_artifact_credit():
    records = [
        _record("a", "repo-a", artifact_path="src/a.py"),
        _record("b", "repo-a", artifact_path="src/b.py"),
    ]

    estimate = _coverage(records, ScoringConfig(cluster_artifact_decay=0.25))

    assert estimate.coverage_k == pytest.approx(0.25)
