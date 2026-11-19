"""Regression checks for the revised, source-aware synthetic generator.

These are implementation tests, not evidence of real-world candidate validity.
The historical 2026-09-17 results remain unchanged and must not be reused after
changing the generator.
"""

from cci.domain.enums import CanonicalRole, SourceFamily
from cci.research.simulation import generate_synthetic_cohort


def _signature(candidate):
    """Stable benchmark features; UUIDs are not seeded and are omitted."""
    return [
        (
            o.capability_key,
            o.source_family,
            o.observed_score,
            o.ownership_score,
            o.elapsed_years,
            o.artifact_integrity,
            o.verification_level,
            o.depth_specificity,
        )
        for o in candidate.observations
    ]


def test_only_github_can_emit_fork_style_low_ownership():
    saw_fork = False
    saw_non_github = False
    for role in CanonicalRole:
        for candidate in generate_synthetic_cohort(role=role, count=30, seed=73):
            for o in candidate.observations:
                if o.ownership_score < 0.5:
                    saw_fork = True
                    assert o.source_family is SourceFamily.GITHUB
                if o.source_family is not SourceFamily.GITHUB:
                    saw_non_github = True
                    assert o.ownership_score >= 0.5
    assert saw_fork and saw_non_github


def test_generated_observations_replay_with_same_seed_and_role():
    for role in CanonicalRole:
        a = generate_synthetic_cohort(role=role, count=3, seed=101)
        b = generate_synthetic_cohort(role=role, count=3, seed=101)
        assert [c.ground_truth_capabilities for c in a] == [
            c.ground_truth_capabilities for c in b
        ]
        assert [_signature(c) for c in a] == [_signature(c) for c in b]


def test_roles_use_different_random_stream_initializations(monkeypatch):
    import cci.research.simulation as simulation

    original_random_state = simulation.np.random.RandomState
    chosen_seeds = []

    def record_random_state(seed_value):
        chosen_seeds.append(seed_value)
        return original_random_state(seed_value)

    monkeypatch.setattr(simulation.np.random, "RandomState", record_random_state)
    generate_synthetic_cohort(role=CanonicalRole.BACKEND, count=1, seed=43)
    generate_synthetic_cohort(role=CanonicalRole.FRONTEND, count=1, seed=43)
    assert len(chosen_seeds) == 2
    assert chosen_seeds[0] != chosen_seeds[1]
