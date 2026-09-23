"""Semantic evidence identities must follow facts and source boundaries, not text."""

from cci.domain.contracts import EvidenceInput
from cci.domain.enums import CapabilityKey, SourceFamily
from cci.domain.evidence_families import (
    build_evidence_family_identity,
    build_fallback_evidence_family_identity,
    normalize_family_subject,
    normalize_source_cluster,
)


def _identity(
    subject: str,
    *,
    source_family: SourceFamily = SourceFamily.GITHUB,
    cluster_id: str = "https://github.com/acme/api",
    capability: CapabilityKey = CapabilityKey.BACKEND_ENGINEERING,
    fact_domain: str = "dependency",
):
    return build_evidence_family_identity(
        source_family=source_family,
        cluster_id=cluster_id,
        capability=capability,
        fact_domain=fact_domain,
        subject=subject,
    )


def _evidence_input(family_id: str, basis: dict[str, str], text: str) -> EvidenceInput:
    return EvidenceInput(
        source_family=SourceFamily.GITHUB,
        source_locator="https://github.com/acme/api",
        immutable_revision="a" * 40,
        artifact_path="requirements.txt",
        target_capability=CapabilityKey.BACKEND_ENGINEERING,
        observed_score=55.0,
        raw_support_text=text,
        extractor_version="test-v1",
        evidence_family_id=family_id,
        evidence_family_basis=basis,
    )


def test_family_id_is_stable_and_semantic_not_text_based():
    first = _identity("FastAPI")
    same_fact = _identity("fastapi", cluster_id="https://github.com/acme/api/")
    other_fact = _identity("starlette")

    assert first.evidence_family_id == same_fact.evidence_family_id
    assert first.evidence_family_id == (
        "ef1:dfb97bcbc576adab76cc095b2f5b1874f37d96b09cc3bb602a60270c55d2c656"
    )
    assert first.evidence_family_id != other_fact.evidence_family_id
    assert first.evidence_family_id.startswith("ef1:")
    assert first.basis["schema"] == "ef1"
    assert first.basis["domain"] == "dependency"
    assert first.basis["subject"] == "fastapi"


def test_identical_support_text_does_not_merge_distinct_semantic_subjects():
    support_text = "dependency found in source"
    first = _identity("fastapi")
    second = _identity("starlette")

    observations = [
        _evidence_input(first.evidence_family_id, first.basis, support_text),
        _evidence_input(second.evidence_family_id, second.basis, support_text),
    ]

    assert observations[0].raw_support_text == observations[1].raw_support_text
    assert observations[0].evidence_family_id != observations[1].evidence_family_id


def test_family_identity_separates_source_clusters_and_capabilities():
    baseline = _identity("fastapi")
    other_cluster = _identity("fastapi", cluster_id="https://github.com/acme/worker")
    other_source = _identity("fastapi", source_family=SourceFamily.DEPLOYMENT)
    other_capability = _identity("fastapi", capability=CapabilityKey.SOFTWARE_ARCHITECTURE)

    assert baseline.evidence_family_id != other_cluster.evidence_family_id
    assert baseline.evidence_family_id != other_source.evidence_family_id
    assert baseline.evidence_family_id != other_capability.evidence_family_id


def test_source_cluster_normalization_matches_coverage_boundaries():
    assert normalize_source_cluster(
        SourceFamily.GITHUB,
        "https://www.github.com/Acme/API.git/",
    ) == "github:github.com/acme/api"
    assert normalize_source_cluster(
        SourceFamily.GITHUB,
        "https://github.com/acme/api",
    ) == "github:github.com/acme/api"


def test_subject_normalization_preserves_route_path_case():
    assert normalize_family_subject("dependency", " FastAPI ") == "fastapi"
    assert normalize_family_subject("route", "get|/Users/Me|read_user") == (
        "GET|/Users/Me|read_user"
    )
    assert normalize_family_subject("route", "GET|/Users/me|read_user") != (
        "GET|/Users/Me|read_user"
    )


def test_fallback_identity_is_stable_and_scoped_to_one_observation():
    arguments = {
        "source_family": SourceFamily.GITHUB,
        "cluster_id": "https://github.com/acme/api",
        "artifact_path": "src/health.py",
        "capability": CapabilityKey.BACKEND_ENGINEERING,
        "observation_type": "parser:route_detection",
        "fingerprint": "a" * 64,
    }
    first = build_fallback_evidence_family_identity(**arguments)
    repeated = build_fallback_evidence_family_identity(**arguments)
    other_path = build_fallback_evidence_family_identity(
        **{**arguments, "artifact_path": "src/admin.py"}
    )
    other_fingerprint = build_fallback_evidence_family_identity(
        **{**arguments, "fingerprint": "b" * 64}
    )
    other_type = build_fallback_evidence_family_identity(
        **{**arguments, "observation_type": "parser:auth_detection"}
    )

    assert first.evidence_family_id == repeated.evidence_family_id
    assert first.evidence_family_id != other_path.evidence_family_id
    assert first.evidence_family_id != other_fingerprint.evidence_family_id
    assert first.evidence_family_id != other_type.evidence_family_id
