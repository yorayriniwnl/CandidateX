"""Monte Carlo candidate cohort simulation engine for paper reproducibility.

FORMAL PAPER MODEL REPLICATION:
Simulates synthetic candidate cohorts with known latent ground-truth capability profiles q_k^*
and realistic noisy evidence emission across the 6 canonical engineering roles.
Supports 16 deterministic pseudo-random seeds x 300 candidates (N=4,800 total).
"""

import hashlib
import json
from dataclasses import dataclass
from uuid import NAMESPACE_URL, UUID, uuid5

import numpy as np

from cci.domain.enums import CanonicalRole, CapabilityKey, SourceFamily
from cci.domain.evidence_families import build_evidence_family_identity

SIMULATION_VERSION = "cohort-simulation-1.0"
SIMULATED_OBSERVATION_TYPES = (
    "simulation:implementation_signal",
    "simulation:verification_signal",
    "simulation:operation_signal",
)

# Role capability emphasis profiles: mean latent capability (core vs. peripheral)
ROLE_CAPABILITY_PROFILES: dict[
    CanonicalRole, dict[CapabilityKey, tuple[float, float]]
] = {
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
    observed_score: float  # z_e,k with observation noise
    ownership_score: float  # o_e
    elapsed_years: float  # delta_t
    artifact_integrity: float  # a_e
    verification_level: float  # v_e
    depth_specificity: float  # x_e
    source_family: SourceFamily  # r_s
    evidence_id: UUID
    evidence_family_id: str
    observation_type: str
    fingerprint: str
    semantic_subject: str
    evidence_family_basis: dict[str, str]
    cluster_id: str | None = None
    source_locator: str | None = None
    artifact_id: str | None = None
    artifact_hash: str | None = None


@dataclass
class SimulatedCandidate:
    """A synthetic candidate with latent ground-truth capability vector and simulated observations."""

    candidate_id: UUID
    role: CanonicalRole
    ground_truth_capabilities: dict[CapabilityKey, float]
    observations: list[SimulatedObservation]
    seed: int


def generate_synthetic_cohort(
    role: CanonicalRole,
    count: int = 300,
    seed: int = 42,
) -> list[SimulatedCandidate]:
    """Generates a reproducible synthetic cohort of candidates for a canonical role."""
    rng = np.random.RandomState(seed)
    cohort: list[SimulatedCandidate] = []
    profile = ROLE_CAPABILITY_PROFILES.get(
        role, ROLE_CAPABILITY_PROFILES[CanonicalRole.BACKEND]
    )

    for i in range(count):
        cand_id = uuid5(
            NAMESPACE_URL,
            f"cci-simulation:candidate:{role.value}:{seed}:{i}",
        )
        ground_truth: dict[CapabilityKey, float] = {}

        # 1. Sample latent ground-truth capabilities q_k^* in [0, 100]
        # Candidate general ability factor
        general_ability_shift = rng.normal(0.0, 6.0)

        for cap_key in CapabilityKey:
            base_mean, base_std = profile.get(cap_key, (60.0, 12.0))
            sampled_val = rng.normal(base_mean + general_ability_shift, base_std)
            ground_truth[cap_key] = float(np.clip(sampled_val, 10.0, 99.0))

        # 2. Simulate evidence emissions across capabilities
        observations: list[SimulatedObservation] = []

        for cap_key, true_q in ground_truth.items():
            # Higher capability candidates emit more evidence on average
            expected_emissions = int(max(0, rng.poisson(lam=1.5 + (true_q / 35.0))))

            for _ in range(expected_emissions):
                # Ownership simulation: 15% chance of forked/shared repo with low ownership
                is_fork = rng.random() < 0.15
                if is_fork:
                    ownership = float(rng.uniform(0.05, 0.18))
                else:
                    ownership = float(np.clip(rng.beta(8.0, 2.0), 0.50, 1.0))

                # Elapsed years: exponential decay (majority recent, some older)
                elapsed = float(rng.exponential(scale=1.8))
                elapsed = min(elapsed, 8.0)

                # Source family sampling
                sf_rand = rng.random()
                if sf_rand < 0.55:
                    sf = SourceFamily.GITHUB
                elif sf_rand < 0.70:
                    sf = SourceFamily.DEPLOYMENT
                elif sf_rand < 0.82:
                    sf = SourceFamily.DATABASE
                else:
                    sf = SourceFamily.RESUME

                # Realistic observation score with empirical source phenomena:
                if is_fork:
                    # Forked/multi-author repo reflects external project codebase
                    ext_quality = float(rng.normal(55.0, 18.0))
                    obs_score = float(
                        np.clip(
                            (1.0 - ownership) * ext_quality
                            + ownership * true_q
                            + rng.normal(0.0, 3.0),
                            0.0,
                            100.0,
                        )
                    )
                elif sf == SourceFamily.RESUME:
                    # Self-reported resume claim: upward self-reporting bias & noise
                    resume_inflation = float(rng.normal(16.0, 5.0))
                    obs_score = float(np.clip(true_q + resume_inflation, 0.0, 100.0))
                else:
                    # Verified technical evidence: career progression and staleness drift
                    career_progression = -1.5 * max(0.0, elapsed - 0.5)
                    stale_noise = rng.normal(0.0, 2.0 + 1.5 * np.sqrt(elapsed))
                    obs_score = float(
                        np.clip(true_q + career_progression + stale_noise, 0.0, 100.0)
                    )

                source_cluster_index = int(rng.randint(0, 3))
                artifact_index = int(rng.randint(0, 4))
                cluster_id = (
                    f"{sf.value}:seed-{seed}:candidate-{i}:project-"
                    f"{source_cluster_index}"
                )
                source_locator = f"synthetic://{cluster_id}"
                artifact_id = f"{cluster_id}:artifact-{artifact_index}"
                semantic_subject = f"{cap_key.value}:artifact-{artifact_index}"
                observation_type = SIMULATED_OBSERVATION_TYPES[
                    int(rng.randint(0, len(SIMULATED_OBSERVATION_TYPES)))
                ]
                observation_ordinal = len(observations)
                evidence_id = uuid5(
                    NAMESPACE_URL,
                    f"cci-simulation:evidence:{role.value}:{seed}:{i}:"
                    f"{observation_ordinal}",
                )
                family = build_evidence_family_identity(
                    source_family=sf,
                    cluster_id=cluster_id,
                    capability=cap_key,
                    fact_domain="simulation",
                    subject=semantic_subject,
                )
                fingerprint_material = json.dumps(
                    {
                        "version": SIMULATION_VERSION,
                        "role": role.value,
                        "seed": seed,
                        "candidate_ordinal": i,
                        "observation_ordinal": observation_ordinal,
                        "source_family": sf.value,
                        "cluster_id": cluster_id,
                        "artifact_id": artifact_id,
                        "capability": cap_key.value,
                        "score": obs_score,
                        "observation_type": observation_type,
                        "semantic_subject": semantic_subject,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
                fingerprint = hashlib.sha256(
                    fingerprint_material.encode("utf-8")
                ).hexdigest()

                observations.append(
                    SimulatedObservation(
                        capability_key=cap_key,
                        observed_score=obs_score,
                        ownership_score=ownership,
                        elapsed_years=elapsed,
                        artifact_integrity=float(rng.uniform(0.90, 1.0)),
                        verification_level=1.0 if sf != SourceFamily.RESUME else 0.50,
                        depth_specificity=float(rng.uniform(0.70, 0.95)),
                        source_family=sf,
                        evidence_id=evidence_id,
                        evidence_family_id=family.evidence_family_id,
                        observation_type=observation_type,
                        fingerprint=fingerprint,
                        semantic_subject=semantic_subject,
                        evidence_family_basis=family.basis,
                        cluster_id=cluster_id,
                        source_locator=source_locator,
                        artifact_id=artifact_id,
                    )
                )

        cohort.append(
            SimulatedCandidate(
                candidate_id=cand_id,
                role=role,
                ground_truth_capabilities=ground_truth,
                observations=observations,
                seed=seed,
            )
        )

    return cohort
