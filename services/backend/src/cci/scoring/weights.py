"""Role importance, temperature softmax weighting, and expert weight overrides."""

import math
from datetime import datetime, timezone

from cci.domain.contracts import NormalizedRequirement, RoleProfile, ScoringConfig
from cci.domain.enums import CanonicalRole, CapabilityKey, RequirementPriority

# Baseline role priors giving canonical role archetypes non-zero baseline importances
ROLE_BASELINE_PRIORS: dict[CanonicalRole, dict[CapabilityKey, float]] = {
    CanonicalRole.BACKEND: {
        CapabilityKey.BACKEND_ENGINEERING: 3.0,
        CapabilityKey.DATABASE_ENGINEERING: 2.5,
        CapabilityKey.SOFTWARE_ARCHITECTURE: 2.0,
        CapabilityKey.TESTING_QUALITY: 2.0,
        CapabilityKey.ALGORITHMS_PROBLEM_SOLVING: 2.0,
        CapabilityKey.DEVOPS_CLOUD: 1.5,
        CapabilityKey.SECURITY: 1.5,
        CapabilityKey.COLLABORATION: 1.0,
        CapabilityKey.DOCUMENTATION_COMMUNICATION: 1.0,
        CapabilityKey.DATA_ENGINEERING: 1.0,
        CapabilityKey.FRONTEND_ENGINEERING: 0.5,
        CapabilityKey.MACHINE_LEARNING: 0.5,
    },
    CanonicalRole.FRONTEND: {
        CapabilityKey.FRONTEND_ENGINEERING: 3.0,
        CapabilityKey.SOFTWARE_ARCHITECTURE: 2.0,
        CapabilityKey.TESTING_QUALITY: 2.0,
        CapabilityKey.COLLABORATION: 1.5,
        CapabilityKey.DOCUMENTATION_COMMUNICATION: 1.5,
        CapabilityKey.ALGORITHMS_PROBLEM_SOLVING: 1.5,
        CapabilityKey.BACKEND_ENGINEERING: 1.0,
        CapabilityKey.SECURITY: 1.0,
        CapabilityKey.DEVOPS_CLOUD: 0.5,
        CapabilityKey.DATABASE_ENGINEERING: 0.5,
        CapabilityKey.DATA_ENGINEERING: 0.5,
        CapabilityKey.MACHINE_LEARNING: 0.5,
    },
    CanonicalRole.FULLSTACK: {
        CapabilityKey.BACKEND_ENGINEERING: 2.5,
        CapabilityKey.FRONTEND_ENGINEERING: 2.5,
        CapabilityKey.DATABASE_ENGINEERING: 2.0,
        CapabilityKey.SOFTWARE_ARCHITECTURE: 2.0,
        CapabilityKey.TESTING_QUALITY: 2.0,
        CapabilityKey.DEVOPS_CLOUD: 1.5,
        CapabilityKey.SECURITY: 1.5,
        CapabilityKey.ALGORITHMS_PROBLEM_SOLVING: 1.5,
        CapabilityKey.COLLABORATION: 1.0,
        CapabilityKey.DOCUMENTATION_COMMUNICATION: 1.0,
        CapabilityKey.DATA_ENGINEERING: 1.0,
        CapabilityKey.MACHINE_LEARNING: 0.5,
    },
    CanonicalRole.ML_ENGINEER: {
        CapabilityKey.MACHINE_LEARNING: 3.0,
        CapabilityKey.DATA_ENGINEERING: 2.5,
        CapabilityKey.ALGORITHMS_PROBLEM_SOLVING: 2.5,
        CapabilityKey.BACKEND_ENGINEERING: 2.0,
        CapabilityKey.SOFTWARE_ARCHITECTURE: 1.5,
        CapabilityKey.TESTING_QUALITY: 1.5,
        CapabilityKey.DEVOPS_CLOUD: 1.5,
        CapabilityKey.DATABASE_ENGINEERING: 1.5,
        CapabilityKey.DOCUMENTATION_COMMUNICATION: 1.0,
        CapabilityKey.COLLABORATION: 1.0,
        CapabilityKey.SECURITY: 1.0,
        CapabilityKey.FRONTEND_ENGINEERING: 0.5,
    },
    CanonicalRole.DEVOPS_CLOUD: {
        CapabilityKey.DEVOPS_CLOUD: 3.0,
        CapabilityKey.SECURITY: 2.5,
        CapabilityKey.SOFTWARE_ARCHITECTURE: 2.0,
        CapabilityKey.BACKEND_ENGINEERING: 2.0,
        CapabilityKey.DATABASE_ENGINEERING: 1.5,
        CapabilityKey.TESTING_QUALITY: 1.5,
        CapabilityKey.COLLABORATION: 1.5,
        CapabilityKey.DOCUMENTATION_COMMUNICATION: 1.5,
        CapabilityKey.DATA_ENGINEERING: 1.0,
        CapabilityKey.ALGORITHMS_PROBLEM_SOLVING: 1.0,
        CapabilityKey.FRONTEND_ENGINEERING: 0.5,
        CapabilityKey.MACHINE_LEARNING: 0.5,
    },
    CanonicalRole.DATA_ENGINEER: {
        CapabilityKey.DATA_ENGINEERING: 3.0,
        CapabilityKey.DATABASE_ENGINEERING: 2.5,
        CapabilityKey.BACKEND_ENGINEERING: 2.0,
        CapabilityKey.SOFTWARE_ARCHITECTURE: 2.0,
        CapabilityKey.DEVOPS_CLOUD: 1.5,
        CapabilityKey.ALGORITHMS_PROBLEM_SOLVING: 1.5,
        CapabilityKey.TESTING_QUALITY: 1.5,
        CapabilityKey.MACHINE_LEARNING: 1.5,
        CapabilityKey.SECURITY: 1.0,
        CapabilityKey.COLLABORATION: 1.0,
        CapabilityKey.DOCUMENTATION_COMMUNICATION: 1.0,
        CapabilityKey.FRONTEND_ENGINEERING: 0.5,
    },
}


def compute_role_importances(
    requirements: list[NormalizedRequirement],
    role: CanonicalRole,
    config: ScoringConfig | None = None,
) -> dict[CapabilityKey, float]:
    """Computes unnormalized importance u_k for each of the 12 capabilities:

    u_k = u_baseline,k + eta1*m_k + eta2*p_k + eta3*ln(1 + f_k) + eta4*s_k
    """
    cfg = config or ScoringConfig()
    baselines = ROLE_BASELINE_PRIORS.get(role, {cap: 1.0 for cap in CapabilityKey})

    m_counts: dict[CapabilityKey, int] = {cap: 0 for cap in CapabilityKey}
    p_counts: dict[CapabilityKey, int] = {cap: 0 for cap in CapabilityKey}
    freq_sums: dict[CapabilityKey, int] = {cap: 0 for cap in CapabilityKey}
    spec_sums: dict[CapabilityKey, float] = {cap: 0.0 for cap in CapabilityKey}
    req_counts: dict[CapabilityKey, int] = {cap: 0 for cap in CapabilityKey}

    for req in requirements:
        for cap in req.capability_mappings:
            if req.priority == RequirementPriority.MANDATORY:
                m_counts[cap] += 1
            elif req.priority == RequirementPriority.PREFERRED:
                p_counts[cap] += 1
            freq_sums[cap] += req.mention_frequency
            spec_sums[cap] += req.semantic_specificity
            req_counts[cap] += 1

    importances: dict[CapabilityKey, float] = {}
    for cap in CapabilityKey:
        base = baselines.get(cap, 1.0)
        m_k = m_counts[cap]
        p_k = p_counts[cap]
        f_k = freq_sums[cap]
        avg_s_k = (spec_sums[cap] / req_counts[cap]) if req_counts[cap] > 0 else 0.0

        u_k = (
            base
            + cfg.eta1_mandatory * m_k
            + cfg.eta2_preferred * p_k
            + cfg.eta3_frequency * math.log(1.0 + f_k)
            + cfg.eta4_specificity * avg_s_k
        )
        importances[cap] = max(0.0, float(u_k))

    return importances


def compute_softmax_weights(
    importances: dict[CapabilityKey, float],
    temperature: float = 1.0,
) -> dict[CapabilityKey, float]:
    """Computes temperature-scaled softmax role weights w_k:

        w_k = exp(u_k / T) / sum_j exp(u_j / T)

    Guaranteed: w_k in (0, 1) and sum(w_k) == 1.0.
    """
    T = max(1e-6, float(temperature))
    max_u = max(importances.values()) if importances else 0.0

    exp_values: dict[CapabilityKey, float] = {}
    for cap, u in importances.items():
        # Numerically stable softmax: shift by max_u
        exp_values[cap] = math.exp((u - max_u) / T)

    total_exp = sum(exp_values.values())
    if total_exp <= 0.0:
        equal = 1.0 / len(CapabilityKey)
        return {cap: equal for cap in CapabilityKey}

    weights = {cap: exp_val / total_exp for cap, exp_val in exp_values.items()}

    # Exact normalization to avoid floating point summation drift
    correction = 1.0 - sum(weights.values())
    first_key = next(iter(weights))
    weights[first_key] += correction

    return weights


def build_role_profile(
    requirements: list[NormalizedRequirement],
    role: CanonicalRole,
    config: ScoringConfig | None = None,
) -> RoleProfile:
    """Builds a verified RoleProfile model."""
    cfg = config or ScoringConfig()
    importances = compute_role_importances(requirements, role, cfg)
    weights = compute_softmax_weights(importances, cfg.temperature)

    return RoleProfile(
        canonical_role=role,
        raw_importances=importances,
        softmax_weights=weights,
        is_overridden=False,
        override_audit=None,
    )


def apply_expert_overrides(
    original_profile: RoleProfile,
    overridden_weights: dict[CapabilityKey, float],
    justification: str,
    user_id: str | None = None,
) -> RoleProfile:
    """Applies expert manual weight adjustments, normalizes, and records audit trail."""
    # Ensure all capabilities are present
    total = sum(overridden_weights.values())
    if total <= 0.0:
        raise ValueError("Overridden weights sum must be strictly greater than 0.")

    normalized_weights = {
        cap: max(0.0, overridden_weights.get(cap, 0.0)) / total for cap in CapabilityKey
    }
    # Float drift correction
    diff = 1.0 - sum(normalized_weights.values())
    first_key = next(iter(normalized_weights))
    normalized_weights[first_key] += diff

    audit = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "justification": justification,
        "original_weights": {
            k.value: v for k, v in original_profile.softmax_weights.items()
        },
        "overridden_weights": {k.value: v for k, v in normalized_weights.items()},
    }

    return RoleProfile(
        canonical_role=original_profile.canonical_role,
        raw_importances=original_profile.raw_importances,
        softmax_weights=normalized_weights,
        is_overridden=True,
        override_audit=audit,
    )
