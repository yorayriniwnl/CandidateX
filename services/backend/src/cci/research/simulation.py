"""Synthetic generator for the repository supplementary implementation ablation.

This generator produces role-specific synthetic cohorts used by
``research/run_paper_experiments.py``. It is intentionally kept separate from the
submitted paper's broader 28,800 candidate-role controlled benchmark.

The repository harness is supplementary implementation evidence, not an exact
regeneration of the submitted paper benchmark. Paper-reported benchmark provenance
is recorded in ``research/paper_benchmark_manifest.json``.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple
from uuid import UUID, uuid4

import numpy as np

from cci.domain.enums import CanonicalRole, CapabilityKey, SourceFamily


# Role capability emphasis profiles: mean latent capability (core vs. peripheral)
ROLE_CAPABILITY_PROFILES: Dict[CanonicalRole, Dict[CapabilityKey, Tuple[float, float]]] = {
    CanonicalRole.BACKEND: {
        CapabilityKey.BACKEND_ENGINEERING: (82.0, 8.0),
        CapabilityKey.DATABASE_ENGINEERING: (78.0, 9.0),
        CapabilityKey.SOFTWARE_ARCHITECTURE: (76.0, 10.0),
        CapabilityKey.TESTING_QUALITY: (75.0, 9.0),
        CapabilityKey.DEVOPS_CLOUD: (68.0, 11.0),
        CapabilityKey.ALGORITHMS_PROBLEM_SOLVING: (72.0, 10.0),
        CapabilityKey.DOCUMENTATION_COMMUNICATION: (70.0, 10.0),
        CapabilityKey.COLLABORATION: (72.0, 9.0),
        CapabilityKey.SECURITY: (65.0, 12.0),
        CapabilityKey.DATA_ENGINEERING: (62.0, 12.0),
        CapabilityKey.FRONTEND_ENGINEERING: (48.0, 15.0),
        CapabilityKey.MACHINE_LEARNING: (45.0, 14.0),
    },
    CanonicalRole.FRONTEND: {
        CapabilityKey.FRONTEND_ENGINEERING: (85.0, 7.0),
        CapabilityKey.TESTING_QUALITY: (74.0, 9.0),
        CapabilityKey.SOFTWARE_ARCHITECTURE: (72.0, 10.0),
        CapabilityKey.DOCUMENTATION_COMMUNICATION: (72.0, 9.0),
        CapabilityKey.COLLABORATION: (74.0, 9.0),
        CapabilityKey.ALGORITHMS_PROBLEM_SOLVING: (68.0, 11.0),
        CapabilityKey.BACKEND_ENGINEERING: (55.0, 14.0),
        CapabilityKey.DEVOPS_CLOUD: (58.0, 13.0),
        CapabilityKey.SECURITY: (60.0, 12.0),
        CapabilityKey.DATABASE_ENGINEERING: (48.0, 15.0),
        CapabilityKey.DATA_ENGINEERING: (42.0, 14.0),
        CapabilityKey.MACHINE_LEARNING: (40.0, 13.0),
    },
    CanonicalRole.FULLSTACK: {
        CapabilityKey.BACKEND_ENGINEERING: (78.0, 9.0),
        CapabilityKey.FRONTEND_ENGINEERING: (78.0, 9.0),
        CapabilityKey.DATABASE_ENGINEERING: (74.0, 10.0),
        CapabilityKey.SOFTWARE_ARCHITECTURE: (74.0, 10.0),
        CapabilityKey.TESTING_QUALITY: (74.0, 9.0),
        CapabilityKey.DEVOPS_CLOUD: (70.0, 11.0),
        CapabilityKey.DOCUMENTATION_COMMUNICATION: (72.0, 9.0),
        CapabilityKey.COLLABORATION: (74.0, 9.0),
        CapabilityKey.ALGORITHMS_PROBLEM_SOLVING: (70.0, 10.0),
        CapabilityKey.SECURITY: (65.0, 11.0),
        CapabilityKey.DATA_ENGINEERING: (58.0, 13.0),
        CapabilityKey.MACHINE_LEARNING: (48.0, 14.0),
    },
    CanonicalRole.ML_ENGINEER: {
        CapabilityKey.MACHINE_LEARNING: (86.0, 7.0),
        CapabilityKey.ALGORITHMS_PROBLEM_SOLVING: (80.0, 8.0),
        CapabilityKey.DATA_ENGINEERING: (78.0, 9.0),
        CapabilityKey.BACKEND_ENGINEERING: (70.0, 11.0),
        CapabilityKey.SOFTWARE_ARCHITECTURE: (68.0, 11.0),
        CapabilityKey.TESTING_QUALITY: (68.0, 11.0),
        CapabilityKey.DEVOPS_CLOUD: (65.0, 12.0),
        CapabilityKey.DOCUMENTATION_COMMUNICATION: (72.0, 9.0),
        CapabilityKey.COLLABORATION: (70.0, 10.0),
        CapabilityKey.DATABASE_ENGINEERING: (62.0, 12.0),
        CapabilityKey.SECURITY: (58.0, 13.0),
        CapabilityKey.FRONTEND_ENGINEERING: (42.0, 14.0),
    },
    CanonicalRole.DEVOPS_CLOUD: {
        CapabilityKey.DEVOPS_CLOUD: (86.0, 7.0),
        CapabilityKey.SECURITY: (80.0, 8.0),
        CapabilityKey.BACKEND_ENGINEERING: (72.0, 10.0),
        CapabilityKey.DATABASE_ENGINEERING: (70.0, 11.0),
        CapabilityKey.SOFTWARE_ARCHITECTURE: (70.0, 11.0),
        CapabilityKey.TESTING_QUALITY: (74.0, 9.0),
        CapabilityKey.DOCUMENTATION_COMMUNICATION: (70.0, 10.0),
        CapabilityKey.COLLABORATION: (72.0, 9.0),
        CapabilityKey.ALGORITHMS_PROBLEM_SOLVING: (65.0, 12.0),
        CapabilityKey.DATA_ENGINEERING: (62.0, 12.0),
        CapabilityKey.FRONTEND_ENGINEERING: (45.0, 15.0),
        CapabilityKey.MACHINE_LEARNING: (45.0, 14.0),
    },
    CanonicalRole.DATA_ENGINEER: {
        CapabilityKey.DATA_ENGINEERING: (86.0, 7.0),
        CapabilityKey.DATABASE_ENGINEERING: (84.0, 7.0),
        CapabilityKey.BACKEND_ENGINEERING: (74.0, 9.0),
        CapabilityKey.ALGORITHMS_PROBLEM_SOLVING: (74.0, 9.0),
        CapabilityKey.SOFTWARE_ARCHITECTURE: (70.0, 10.0),
        CapabilityKey.TESTING_QUALITY: (70.0, 10.0),
        CapabilityKey.DEVOPS_CLOUD: (68.0, 11.0),
        CapabilityKey.DOCUMENTATION_COMMUNICATION: (70.0, 10.0),
        CapabilityKey.COLLABORATION: (72.0, 9.0),
        CapabilityKey.MACHINE_LEARNING: (65.0, 12.0),
        CapabilityKey.SECURITY: (62.0, 12.0),
        CapabilityKey.FRONTEND_ENGINEERING: (42.0, 14.0),
    },
}


@dataclass
class SimulatedObservation:
    """An emitted evidence observation with simulated real-world factors."""

    capability_key: CapabilityKey
    observed_score: float
    ownership_score: float
    elapsed_years: float
    artifact_integrity: float
    verification_level: float
    depth_specificity: float
    source_family: SourceFamily


@dataclass
class SimulatedCandidate:
    """Synthetic role-specific candidate used by the supplementary harness."""

    candidate_id: UUID
    role: CanonicalRole
    ground_truth_capabilities: Dict[CapabilityKey, float]
    observations: List[SimulatedObservation]
    seed: int


def generate_synthetic_cohort(
    role: CanonicalRole,
    count: int = 300,
    seed: int = 42,
) -> List[SimulatedCandidate]:
    """Generate a reproducible role-specific synthetic cohort."""
    rng = np.random.RandomState(seed)
    cohort: List[SimulatedCandidate] = []
    profile = ROLE_CAPABILITY_PROFILES.get(
        role,
        ROLE_CAPABILITY_PROFILES[CanonicalRole.BACKEND],
    )

    for _ in range(count):
        candidate_id = uuid4()
        ground_truth: Dict[CapabilityKey, float] = {}
        general_ability_shift = rng.normal(0.0, 6.0)

        for capability in CapabilityKey:
            base_mean, base_std = profile.get(capability, (60.0, 12.0))
            sampled_value = rng.normal(base_mean + general_ability_shift, base_std)
            ground_truth[capability] = float(np.clip(sampled_value, 10.0, 99.0))

        observations: List[SimulatedObservation] = []
        for capability, true_q in ground_truth.items():
            expected_emissions = int(
                max(0, rng.poisson(lam=1.5 + (true_q / 35.0)))
            )

            for _ in range(expected_emissions):
                is_fork = rng.random() < 0.15
                if is_fork:
                    ownership = float(rng.uniform(0.05, 0.18))
                else:
                    ownership = float(np.clip(rng.beta(8.0, 2.0), 0.50, 1.0))

                elapsed = min(float(rng.exponential(scale=1.8)), 8.0)

                source_roll = rng.random()
                if source_roll < 0.55:
                    source_family = SourceFamily.GITHUB
                elif source_roll < 0.70:
                    source_family = SourceFamily.DEPLOYMENT
                elif source_roll < 0.82:
                    source_family = SourceFamily.DATABASE
                else:
                    source_family = SourceFamily.RESUME

                if is_fork:
                    external_quality = float(rng.normal(55.0, 18.0))
                    observed_score = float(
                        np.clip(
                            (1.0 - ownership) * external_quality
                            + ownership * true_q
                            + rng.normal(0.0, 3.0),
                            0.0,
                            100.0,
                        )
                    )
                elif source_family == SourceFamily.RESUME:
                    resume_inflation = float(rng.normal(16.0, 5.0))
                    observed_score = float(
                        np.clip(true_q + resume_inflation, 0.0, 100.0)
                    )
                else:
                    career_progression = -1.5 * max(0.0, elapsed - 0.5)
                    stale_noise = rng.normal(0.0, 2.0 + 1.5 * np.sqrt(elapsed))
                    observed_score = float(
                        np.clip(
                            true_q + career_progression + stale_noise,
                            0.0,
                            100.0,
                        )
                    )

                observations.append(
                    SimulatedObservation(
                        capability_key=capability,
                        observed_score=observed_score,
                        ownership_score=ownership,
                        elapsed_years=elapsed,
                        artifact_integrity=float(rng.uniform(0.90, 1.0)),
                        verification_level=(
                            1.0 if source_family != SourceFamily.RESUME else 0.50
                        ),
                        depth_specificity=float(rng.uniform(0.70, 0.95)),
                        source_family=source_family,
                    )
                )

        cohort.append(
            SimulatedCandidate(
                candidate_id=candidate_id,
                role=role,
                ground_truth_capabilities=ground_truth,
                observations=observations,
                seed=seed,
            )
        )

    return cohort
