"""Role importance, temperature softmax weighting, and expert weight overrides."""

import math
import re
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

_JD_PRIORITY_WEIGHT: dict[RequirementPriority, float] = {
    RequirementPriority.MANDATORY: 1.0,
    RequirementPriority.PREFERRED: 0.5,
    RequirementPriority.NICE_TO_HAVE: 0.25,
    RequirementPriority.OPTIONAL: 0.0,
}


def compute_role_importances(
    requirements: list[NormalizedRequirement],
    role: CanonicalRole,
    config: ScoringConfig | None = None,
) -> dict[CapabilityKey, float]:
    """Adds a bounded, diminishing JD adjustment to canonical role-prior logits.

    Repeated mentions in one normalized requirement group are counted once. Distinct
    groups mapped to the same capability receive geometric marginal returns, and
    the total adjustment for each capability is capped by the active config.
    """
    cfg = config or ScoringConfig()
    baselines = ROLE_BASELINE_PRIORS.get(role, {cap: 1.0 for cap in CapabilityKey})
    groups_by_capability: dict[
        CapabilityKey, dict[tuple[str, ...], float]
    ] = {cap: {} for cap in CapabilityKey}

    for req in requirements:
        group_key = _normalized_requirement_group(req)
        group_strength = (
            _JD_PRIORITY_WEIGHT[req.priority]
            * req.mapping_confidence
            * req.semantic_specificity
        )
        for cap in req.capability_mappings:
            existing = groups_by_capability[cap].get(group_key, 0.0)
            groups_by_capability[cap][group_key] = max(existing, group_strength)

    importances: dict[CapabilityKey, float] = {}
    for cap in CapabilityKey:
        groups = sorted(
            groups_by_capability[cap].items(),
            key=lambda item: (-item[1], item[0]),
        )
        marginal_support = sum(
            strength * cfg.jd_requirement_group_decay**index
            for index, (_, strength) in enumerate(groups)
        )
        adjustment = cfg.jd_max_logit_adjustment * (
            1.0 - math.exp(-marginal_support / cfg.jd_adjustment_saturation)
        )
        importances[cap] = max(
            0.0, float(baselines.get(cap, 1.0) + adjustment)
        )

    return importances


def _normalized_requirement_group(req: NormalizedRequirement) -> tuple[str, ...]:
    """Returns a case- and punctuation-normalized identity for one requirement."""
    normalized_text = re.sub(r"[^a-z0-9+#]+", " ", req.source_text.casefold())
    normalized_text = " ".join(normalized_text.split())
    if normalized_text:
        return (normalized_text,)
    return (" ".join(req.normalized_name.casefold().split()),)


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


def _bound_role_weights(
    weights: dict[CapabilityKey, float],
    min_weight: float,
    max_weight: float,
) -> dict[CapabilityKey, float]:
    """Proportionally project weights onto a bounded probability simplex."""
    count = len(weights)
    if count == 0:
        return {}
    if min_weight > max_weight:
        raise ValueError("Minimum role weight cannot exceed maximum role weight")
    if min_weight * count > 1.0 or max_weight * count < 1.0:
        raise ValueError("Role weight bounds cannot form a normalized distribution")
    if min_weight * count >= 1.0 - 1e-12:
        return {cap: 1.0 / count for cap in weights}

    capabilities = list(weights)
    values = {cap: max(0.0, float(weights[cap])) for cap in capabilities}
    total_input = sum(values.values())
    if total_input <= 0.0:
        values = {cap: 1.0 / count for cap in capabilities}
    else:
        values = {cap: value / total_input for cap, value in values.items()}
        # Keep underflowed softmax dimensions eligible when a valid config uses
        # a zero lower bound; otherwise multiplicative projection cannot add
        # probability mass to them.
        smallest_positive_support = max(values.values()) * 1e-15
        values = {
            cap: max(value, smallest_positive_support)
            for cap, value in values.items()
        }
        total_input = sum(values.values())
        values = {cap: value / total_input for cap, value in values.items()}

    def scaled_total(scale: float) -> float:
        return sum(
            min(max_weight, max(min_weight, scale * values[cap]))
            for cap in capabilities
        )

    # The sum of clamp(scale * p_k, min, max) is monotone in scale. Bisection
    # finds a normalized point, including cases where several values hit a
    # bound at once.
    lower = 0.0
    upper = 1.0
    while scaled_total(upper) < 1.0:
        upper *= 2.0
    for _ in range(96):
        scale = (lower + upper) / 2.0
        if scaled_total(scale) < 1.0:
            lower = scale
        else:
            upper = scale
    bounded = {
        cap: min(max_weight, max(min_weight, upper * values[cap]))
        for cap in capabilities
    }

    # Distribute the final floating-point residue over available headroom.
    correction = 1.0 - sum(bounded.values())
    for cap in capabilities:
        if abs(correction) <= 1e-15:
            break
        room = (
            max_weight - bounded[cap]
            if correction > 0.0
            else bounded[cap] - min_weight
        )
        adjustment = math.copysign(min(abs(correction), max(0.0, room)), correction)
        bounded[cap] += adjustment
        correction -= adjustment
    return {cap: bounded[cap] for cap in weights}


def build_role_profile(
    requirements: list[NormalizedRequirement],
    role: CanonicalRole,
    config: ScoringConfig | None = None,
) -> RoleProfile:
    """Builds a verified RoleProfile model."""
    cfg = config or ScoringConfig()
    importances = compute_role_importances(requirements, role, cfg)
    weights = _bound_role_weights(
        compute_softmax_weights(importances, cfg.temperature),
        cfg.min_role_weight,
        cfg.max_role_weight,
    )

    return RoleProfile(
        canonical_role=role,
        raw_importances=importances,
        softmax_weights=weights,
        temperature_used=cfg.temperature,
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
    if any(not math.isfinite(v) or v < 0 for v in overridden_weights.values()):
        raise ValueError("Weights must be finite and non-negative")
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
        temperature_used=original_profile.temperature_used,
        is_overridden=True,
        override_audit=audit,
    )
