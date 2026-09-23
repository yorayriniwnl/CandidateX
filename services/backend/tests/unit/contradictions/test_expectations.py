import hashlib

import pytest

from cci.contradictions.expectations import (
    build_observable_claim_expectations,
    make_claim_reference,
    parse_observable_claim,
)
from cci.domain.contracts import CandidateManifest
from cci.domain.enums import CapabilityKey
from cci.live.contracts import ResumeIntake
from cci.live.claims import build_observable_claim_expectations as build_from_live_claims


def intake(*, projects=(), skills=(), experience=(), deployments=(), links=()):
    return ResumeIntake(
        manifest=CandidateManifest(
            display_name="Example",
            project_claims=list(projects),
            claimed_skills=list(skills),
            experience_claims=[{"text": text} for text in experience],
            deployment_urls=list(deployments),
            github_urls=list(links),
        ),
        document_sha256="a" * 64,
        filename="resume.pdf",
    )


def test_reference_uses_versioned_normalized_payload_and_repository_scope():
    claim = "At least 95% line coverage"
    kind = "candidatex.contradiction.coverage_below_claim"
    expected = "cr1:" + hashlib.sha256(
        b"candidatex.claim-reference.v1\0at least 95% line coverage\0testing_quality\0"
        b"candidatex.contradiction.coverage_below_claim\0acme/api"
    ).hexdigest()
    assert make_claim_reference(claim, CapabilityKey.TESTING_QUALITY, kind, "ACME/API") == expected
    assert make_claim_reference("  AT LEAST 95%   LINE COVERAGE ", CapabilityKey.TESTING_QUALITY, kind, "https://github.com/acme/api/tree/main") == expected
    assert make_claim_reference(claim, CapabilityKey.TESTING_QUALITY, kind, "acme/web") != expected


def test_coverage_claim_has_normalized_comparison_fields():
    result = build_observable_claim_expectations(intake(projects=[{
        "title": "API repo=acme/api", "description": "At least 95% line coverage",
    }]))
    assert len(result) == 1
    assert result[0].candidate_type == "candidatex.contradiction.coverage_below_claim"
    assert result[0].target_capability is CapabilityKey.TESTING_QUALITY
    assert result[0].repository_scope == "acme/api"
    assert result[0].comparator == ">="
    assert result[0].threshold == 95
    assert result[0].unit == "%"
    assert result[0].metric_id == "line_coverage"


@pytest.mark.parametrize("phrase,comparator", [
    ("No less than 90% test coverage", ">="),
    (">90% branch coverage", ">"),
    (">= 90% coverage", ">="),
])
def test_coverage_lower_bound_forms(phrase, comparator):
    result = parse_observable_claim(phrase, repository_scope="acme/api")
    assert len(result) == 1
    assert result[0].comparator == comparator


@pytest.mark.parametrize("phrase", [
    "95% line coverage", "At least 95 tests coverage", "At least 95% coverage and >=90% line coverage",
    "At least 95% coverage and more than 90 tests",
])
def test_coverage_requires_one_percentage_lower_bound(phrase):
    assert parse_observable_claim(phrase, repository_scope="acme/api") == []


def test_framework_use_requires_registered_exact_token_and_scope():
    result = parse_observable_claim("Built with FastAPI", repository_scope="acme/api")
    assert len(result) == 1
    assert result[0].technology == "fastapi"
    assert result[0].target_capability is CapabilityKey.BACKEND_ENGINEERING
    assert result[0].candidate_type == "candidatex.contradiction.framework_usage_absent"
    assert parse_observable_claim("FastAPI expert", repository_scope="acme/api") == []
    assert parse_observable_claim("Built with MysteryFramework", repository_scope="acme/api") == []
    assert parse_observable_claim("Built with FastAPI") == []
    assert parse_observable_claim("Built with FastAPI and Django", repository_scope="acme/api") == []


def test_deployment_requires_expected_identity_and_selected_url():
    url = "https://api.example.com"
    result = build_observable_claim_expectations(intake(
        projects=[{"title": "API", "description": f"project=api-v2 {url}"}],
        deployments=[url],
    ))
    assert len(result) == 1
    assert result[0].candidate_type == "candidatex.contradiction.deployment_project_mismatch"
    assert result[0].target_capability is CapabilityKey.DEVOPS_CLOUD
    assert result[0].project_identity == "api-v2"
    assert result[0].deployment_url == url
    assert build_observable_claim_expectations(intake(projects=[{
        "title": "API", "description": f"Live at {url}",
    }], deployments=[url])) == []
    split = build_observable_claim_expectations(intake(
        projects=[{"title": "project=api-v2", "description": f"Live at {url}"}],
        deployments=[url],
    ))
    assert len(split) == 1
    assert split[0].project_identity == "api-v2"


def test_performance_grammar_normalizes_context_and_capability():
    text = "requests_per_sec at least 500 req/s technology=FastAPI statistic=P95 workload=Read environment=Prod"
    result = parse_observable_claim(text, repository_scope="acme/api")
    assert len(result) == 1
    expectation = result[0]
    assert expectation.candidate_type == "candidatex.contradiction.performance_claim_mismatch"
    assert expectation.target_capability is CapabilityKey.BACKEND_ENGINEERING
    assert (expectation.metric_id, expectation.comparator, expectation.threshold, expectation.unit) == (
        "requests_per_sec", ">=", 500, "req/s",
    )
    assert (expectation.technology, expectation.statistic, expectation.workload, expectation.environment) == (
        "fastapi", "p95", "read", "prod",
    )
    assert parse_observable_claim("latency < 50 ms technology=unknown", repository_scope="acme/api") == []
    assert parse_observable_claim("latency 50 ms technology=fastapi", repository_scope="acme/api") == []
    assert parse_observable_claim("Claimed latency < 50 ms technology=fastapi", repository_scope="acme/api") == []
    assert parse_observable_claim("latency < 50 ms technology=fastapi extra", repository_scope="acme/api") == []


def test_repository_scope_must_be_unique_and_in_same_project_claim():
    projects = [{"title": "API", "description": "Used FastAPI"}]
    assert build_observable_claim_expectations(intake(
        projects=projects, links=["https://github.com/acme/api"],
    )) == []
    assert build_observable_claim_expectations(intake(projects=[{
        "title": "API repo=acme/api repo=acme/web", "description": "Used FastAPI",
    }])) == []
    assert build_observable_claim_expectations(intake(
        projects=projects, skills=["Used FastAPI"], experience=["Used FastAPI"],
        links=["https://github.com/acme/api"],
    )) == []
    assert build_observable_claim_expectations(intake(projects=[{
        "title": "API", "description": "latency < 50 ms/op technology=fastapi",
    }])) == []


def test_sentence_punctuation_does_not_change_repository_identity():
    result = build_observable_claim_expectations(intake(projects=[{
        "title": "API", "description": "Used FastAPI in https://github.com/acme/api.",
    }]))
    assert len(result) == 1
    assert result[0].repository_scope == "acme/api"
    labeled = build_observable_claim_expectations(intake(projects=[{
        "title": "API", "description": "Used FastAPI in repo=acme/api.",
    }]))
    assert len(labeled) == 1
    assert labeled[0].repository_scope == "acme/api"


def test_generic_slash_phrase_cannot_supply_repository_scope():
    assert build_observable_claim_expectations(intake(projects=[{
        "title": "API", "description": "Used FastAPI with CI/CD",
    }])) == []
    assert build_observable_claim_expectations(intake(projects=[{
        "title": "API acme/api", "description": "Used FastAPI",
    }])) == []
    scoped = build_observable_claim_expectations(intake(projects=[{
        "title": "API repo=acme/api", "description": "Used FastAPI with CI/CD",
    }]))
    assert len(scoped) == 1
    assert scoped[0].repository_scope == "acme/api"


@pytest.mark.parametrize("claim", [
    "We did not use FastAPI",
    "Never used FastAPI",
    "Not at least 95% coverage",
])
def test_negated_claims_do_not_make_affirmative_expectations(claim):
    assert parse_observable_claim(claim, repository_scope="acme/api") == []


def test_unscoped_or_ambiguous_claim_produces_no_expectation():
    assert parse_observable_claim("I used FastAPI") == []
    assert parse_observable_claim("Used FastAPI and at least 95% coverage", repository_scope="acme/api") == []


def test_live_claims_exposes_the_same_transient_builder():
    sample = intake(projects=[{"title": "API repo=acme/api", "description": "Used FastAPI"}])
    assert build_from_live_claims(sample) == build_observable_claim_expectations(sample)
