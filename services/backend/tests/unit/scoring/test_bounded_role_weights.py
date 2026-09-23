"""Adversarial job descriptions must not collapse the capability ontology."""

import pytest

from cci.domain.contracts import NormalizedRequirement
from cci.domain.enums import CanonicalRole, CapabilityKey, RequirementPriority
from cci.jobs.parser import extract_requirements_from_jd
from cci.scoring.weights import (
    ROLE_BASELINE_PRIORS,
    _bound_role_weights,
    build_role_profile,
    compute_role_importances,
)


def _profile(jd_text: str, role: CanonicalRole = CanonicalRole.BACKEND):
    requirements = extract_requirements_from_jd(jd_text)
    return requirements, build_role_profile(requirements, role)


def test_single_mandatory_python_requirement_cannot_dominate_backend_role():
    _, profile = _profile("Must have Python experience")

    assert profile.softmax_weights[CapabilityKey.BACKEND_ENGINEERING] <= 0.40
    assert min(profile.softmax_weights.values()) >= 0.01
    assert sum(profile.softmax_weights.values()) == pytest.approx(1.0)


def test_repeating_one_keyword_twenty_times_does_not_change_role_weights():
    _, one_mention = _profile("Must have Python experience")
    repeated_jd = "\n".join(["Must have Python experience"] * 20)
    _, twenty_mentions = _profile(repeated_jd)

    assert twenty_mentions.softmax_weights == pytest.approx(
        one_mention.softmax_weights
    )


def test_distinct_requirements_mapped_to_backend_have_diminishing_bounded_returns():
    base = compute_role_importances([], CanonicalRole.BACKEND)[
        CapabilityKey.BACKEND_ENGINEERING
    ]
    one_text = "Must have Python experience"
    two_text = f"{one_text}\nFastAPI service development"
    many_text = "\n".join(
        [
            one_text,
            "FastAPI service development",
            "Django application development",
            "Flask API development",
            "Java application development",
            "Rust backend development",
            "Go microservices development",
            "Distributed systems experience",
            "REST API design",
            "GraphQL API development",
            "gRPC service development",
            "Concurrency and asynchronous programming",
        ]
    )
    one = compute_role_importances(
        extract_requirements_from_jd(one_text), CanonicalRole.BACKEND
    )[CapabilityKey.BACKEND_ENGINEERING]
    two = compute_role_importances(
        extract_requirements_from_jd(two_text), CanonicalRole.BACKEND
    )[CapabilityKey.BACKEND_ENGINEERING]
    many = compute_role_importances(
        extract_requirements_from_jd(many_text), CanonicalRole.BACKEND
    )[CapabilityKey.BACKEND_ENGINEERING]

    first_return = one - base
    second_return = two - one
    later_returns = many - two
    assert 0 < first_return <= 1.5
    assert 0 < second_return < first_return
    assert 0 < later_returns < second_return
    assert many - base <= 1.5


def test_distinct_python_requirements_are_not_collapsed_by_shared_keyword():
    one_text = "Must have Python for latency-sensitive services"
    second_text = "Must have Python for secure service development"
    one = compute_role_importances(
        extract_requirements_from_jd(one_text), CanonicalRole.BACKEND
    )[CapabilityKey.BACKEND_ENGINEERING]
    two = compute_role_importances(
        extract_requirements_from_jd(f"{one_text}\n{second_text}"),
        CanonicalRole.BACKEND,
    )[CapabilityKey.BACKEND_ENGINEERING]

    assert two > one
    assert two - one < one - ROLE_BASELINE_PRIORS[CanonicalRole.BACKEND][
        CapabilityKey.BACKEND_ENGINEERING
    ]


def test_requirement_priority_strength_respects_all_priority_levels():
    baseline = compute_role_importances([], CanonicalRole.BACKEND)[
        CapabilityKey.BACKEND_ENGINEERING
    ]
    importances = {}
    for priority in RequirementPriority:
        requirement = NormalizedRequirement(
            source_text=f"{priority.value} Python service development",
            normalized_name="Python service development",
            priority=priority,
            capability_mappings=[CapabilityKey.BACKEND_ENGINEERING],
        )
        importances[priority] = compute_role_importances(
            [requirement], CanonicalRole.BACKEND
        )[CapabilityKey.BACKEND_ENGINEERING]

    assert importances[RequirementPriority.MANDATORY] > importances[
        RequirementPriority.PREFERRED
    ]
    assert importances[RequirementPriority.PREFERRED] > importances[
        RequirementPriority.NICE_TO_HAVE
    ]
    assert importances[RequirementPriority.NICE_TO_HAVE] > baseline
    assert importances[RequirementPriority.OPTIONAL] == baseline


@pytest.mark.parametrize(
    ("name", "jd_text", "role"),
    [
        (
            "balanced_backend",
            """Requirements:
- Python API development
- PostgreSQL schema design
- Unit testing with pytest
- Docker deployment
- OAuth authentication
- Distributed systems
- System design
- Code review
- Technical documentation""",
            CanonicalRole.BACKEND,
        ),
        (
            "security_heavy_backend",
            """Requirements:
- Python backend services
- OAuth authentication and authorization
- OWASP secure coding
- Encryption and cryptography
- JWT access control
- Security threat modeling
- PostgreSQL data protection""",
            CanonicalRole.BACKEND,
        ),
        (
            "fullstack",
            """Requirements:
- React and TypeScript frontend
- Next.js accessible user interface
- Python API backend
- PostgreSQL data models
- Automated testing with Playwright
- Docker and CI/CD deployment
- System design
- Cross-functional collaboration""",
            CanonicalRole.FULLSTACK,
        ),
        (
            "generic",
            "Build useful products with a thoughtful, collaborative team.",
            CanonicalRole.BACKEND,
        ),
        ("empty", "", CanonicalRole.BACKEND),
        (
            "marketing_heavy",
            """Growth marketing and brand storytelling
SEO and social media campaigns
Customer acquisition copywriting
Content strategy and audience research""",
            CanonicalRole.BACKEND,
        ),
    ],
)
def test_adversarial_job_descriptions_preserve_all_role_dimensions(
    name, jd_text, role
):
    _, profile = _profile(jd_text, role)

    assert len(profile.softmax_weights) == len(CapabilityKey), name
    assert sum(profile.softmax_weights.values()) == pytest.approx(1.0), name
    assert max(profile.softmax_weights.values()) <= 0.40, name
    assert min(profile.softmax_weights.values()) >= 0.01, name


def test_security_heavy_jd_specializes_while_backend_remains_materially_weighted():
    _, prior = _profile("", CanonicalRole.BACKEND)
    _, security_heavy = _profile(
        """Requirements:
- OAuth authentication and authorization
- OWASP secure coding
- Encryption and cryptography
- JWT access control
- Security threat modeling
- PostgreSQL data protection""",
        CanonicalRole.BACKEND,
    )

    assert (
        security_heavy.softmax_weights[CapabilityKey.SECURITY]
        > prior.softmax_weights[CapabilityKey.SECURITY]
    )
    assert security_heavy.softmax_weights[CapabilityKey.SECURITY] >= 0.10
    assert security_heavy.softmax_weights[CapabilityKey.BACKEND_ENGINEERING] >= 0.10


def test_fullstack_jd_keeps_frontend_and_backend_materially_weighted():
    _, profile = _profile(
        """Requirements:
- React and TypeScript frontend
- Next.js accessible user interface
- Python API backend
- PostgreSQL data models
- Automated testing with Playwright
- Docker and CI/CD deployment
- System design""",
        CanonicalRole.FULLSTACK,
    )

    assert profile.softmax_weights[CapabilityKey.FRONTEND_ENGINEERING] >= 0.10
    assert profile.softmax_weights[CapabilityKey.BACKEND_ENGINEERING] >= 0.10


def test_unmapped_marketing_jd_leaves_canonical_role_prior_unchanged():
    _, prior = _profile("", CanonicalRole.BACKEND)
    _, marketing = _profile(
        "SEO brand marketing, growth campaigns, social media, and copywriting.",
        CanonicalRole.BACKEND,
    )

    assert marketing.softmax_weights == pytest.approx(prior.softmax_weights)
    assert marketing.raw_importances == pytest.approx(prior.raw_importances)


def test_low_temperature_cannot_bypass_maximum_role_weight():
    from cci.domain.contracts import ScoringConfig

    requirements = extract_requirements_from_jd(
        "Must have Python, FastAPI, Django, Flask, and distributed systems experience"
    )
    profile = build_role_profile(
        requirements,
        CanonicalRole.BACKEND,
        ScoringConfig(temperature=0.5),
    )

    assert max(profile.softmax_weights.values()) <= 0.40
    assert min(profile.softmax_weights.values()) >= 0.01


def test_role_profile_weight_keys_keep_canonical_capability_order():
    _, profile = _profile("Must have Python experience")

    assert list(profile.softmax_weights) == list(CapabilityKey)


def test_bounded_simplex_projection_preserves_feasible_custom_bounds():
    capabilities = list(CapabilityKey)
    # Five upper-bound candidates leave too little mass for seven floor values
    # unless the correction is distributed across the capped weights.
    weights = {
        capability: (0.15 if index < 5 else 0.25 / 7)
        for index, capability in enumerate(capabilities)
    }

    bounded = _bound_role_weights(weights, min_weight=0.08, max_weight=0.10)

    assert sum(bounded.values()) == pytest.approx(1.0)
    assert min(bounded.values()) >= 0.08
    assert max(bounded.values()) <= 0.10
