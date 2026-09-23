"""Formal paper ablation study engine.

ABLATION CONFIGURATIONS:
1. FULL_CCI: Attribution-gated evidence quality; scores require configured minimum coverage.
2. NO_RECENCY_DECAY: lambda_k = 0 -> t_e,k = 1.0 (ignores staleness of 5-year-old code).
3. NO_OWNERSHIP_DISCOUNT: o_e = 1.0 (ignores forks and multi-contributor sharing).
4. UNIFORM_WEIGHTS: w_k = 1/12 (ignores role-specific technical requirements).
5. UNCALIBRATED_SOURCES: r_s = 1.0 (treats self-reported resume identically to verified git commit).
"""

from enum import Enum

import numpy as np
from scipy import stats

from cci.domain.contracts import ScoringConfig
from cci.domain.enums import CanonicalRole, CapabilityKey
from cci.research.simulation import SimulatedCandidate, SimulatedObservation
from cci.scoring.capability import (
    build_evidence_coverage_item,
    compute_cluster_aware_coverage,
    has_sufficient_candidate_evidence,
)
from cci.scoring.recency import compute_recency_factor
from cci.scoring.reliability import DEFAULT_PRIORS, calculate_beta_mean
from cci.scoring.confidence import compute_evidence_confidence
from cci.scoring.weights import compute_softmax_weights


class AblationMode(str, Enum):
    FULL_CCI = "FULL_CCI"
    NO_RECENCY_DECAY = "NO_RECENCY_DECAY"
    NO_OWNERSHIP_DISCOUNT = "NO_OWNERSHIP_DISCOUNT"
    UNIFORM_WEIGHTS = "UNIFORM_WEIGHTS"
    UNCALIBRATED_SOURCES = "UNCALIBRATED_SOURCES"


def _compute_ablation_confidence(
    obs: SimulatedObservation,
    mode: AblationMode,
) -> float:
    """Computes evidence confidence c_e,k under specified ablation constraints."""
    # 1. Artifact integrity a_e
    a = obs.artifact_integrity

    # 2. Ownership attribution o_e
    if mode == AblationMode.NO_OWNERSHIP_DISCOUNT:
        o = 1.0
    else:
        o = obs.ownership_score

    # 3. Recency decay factor t_e,k
    if mode == AblationMode.NO_RECENCY_DECAY:
        t = 1.0
    else:
        t = compute_recency_factor(obs.elapsed_years, obs.capability_key)

    # 4. Verification level v_e
    v = obs.verification_level

    # 5. Depth specificity x_e
    x = obs.depth_specificity

    # 6. Source reliability r_s
    if mode == AblationMode.UNCALIBRATED_SOURCES:
        r = 1.0
    else:
        alpha, beta = DEFAULT_PRIORS.get(obs.source_family, (5.0, 5.0))
        r = calculate_beta_mean(0, 0, alpha, beta)

    return compute_evidence_confidence(a, o, t, v, x, r)


def evaluate_candidate_ablation(
    candidate: SimulatedCandidate,
    mode: AblationMode,
    role_weights: dict[CapabilityKey, float],
    true_weights: dict[CapabilityKey, float] | None = None,
    config: ScoringConfig | None = None,
) -> tuple[float | None, float, dict[CapabilityKey, float]]:
    """Evaluates a simulated candidate's capability scores and RCI under ablation."""
    cfg = config or ScoringConfig()
    # Group observations by capability
    obs_by_cap: dict[CapabilityKey, list[SimulatedObservation]] = {}
    for obs in candidate.observations:
        obs_by_cap.setdefault(obs.capability_key, []).append(obs)

    estimated_q: dict[CapabilityKey, float] = {}

    for cap_key in CapabilityKey:
        cap_obs = obs_by_cap.get(cap_key, [])
        if not cap_obs:
            continue

        z_scores = [o.observed_score for o in cap_obs]
        c_factors = [_compute_ablation_confidence(o, mode) for o in cap_obs]

        sum_c = sum(c_factors)
        tau_k = cfg.tau_saturation.get(cap_key, 5.0)
        coverage_k, _ = compute_cluster_aware_coverage(
            (
                build_evidence_coverage_item(
                    source_family=observation.source_family,
                    source_locator=observation.source_locator
                    or f"synthetic://{observation.source_family.value}",
                    confidence=confidence,
                    cluster_id=observation.cluster_id,
                    artifact_id=observation.artifact_id,
                    artifact_hash=observation.artifact_hash,
                )
                for observation, confidence in zip(cap_obs, c_factors)
            ),
            tau_k,
            cfg.cluster_artifact_decay,
        )
        if sum_c > 0.0 and has_sufficient_candidate_evidence(coverage_k, cfg):
            q_hat = sum(c * z for c, z in zip(c_factors, z_scores)) / sum_c
            estimated_q[cap_key] = float(np.clip(q_hat, 0.0, 100.0))

    # Compute estimated RCI over observed capabilities
    if not estimated_q:
        return None, 0.0, estimated_q

    w_sum = sum(role_weights[k] for k in estimated_q)
    if w_sum <= 0.0:
        return None, 0.0, estimated_q

    weighted_q = sum(role_weights[k] * estimated_q[k] for k in estimated_q)
    rci_est = weighted_q / w_sum

    # Compute ground truth RCI over the same observed capabilities for fair comparison
    target_w = true_weights if true_weights is not None else role_weights
    target_w_sum = sum(target_w[k] for k in estimated_q)
    if target_w_sum <= 0.0:
        return None, 0.0, estimated_q
    weighted_true = sum(
        target_w[k] * candidate.ground_truth_capabilities[k] for k in estimated_q
    )
    rci_true = weighted_true / target_w_sum

    return rci_est, rci_true, estimated_q


def run_ablation_evaluation(
    cohort: list[SimulatedCandidate],
    mode: AblationMode,
    role: CanonicalRole,
    config: ScoringConfig | None = None,
) -> dict[str, float]:
    """Runs ablation evaluation across a candidate cohort and computes paper metrics."""
    cfg = config or ScoringConfig()
    # Default role importance
    raw_importances = {k: 1.0 for k in CapabilityKey}
    from cci.research.simulation import ROLE_CAPABILITY_PROFILES

    prof = ROLE_CAPABILITY_PROFILES.get(role, {})
    for k, (mean_val, _) in prof.items():
        raw_importances[k] = mean_val / 50.0
    true_role_weights = compute_softmax_weights(raw_importances, temperature=1.0)

    # Build weights based on mode
    if mode == AblationMode.UNIFORM_WEIGHTS:
        eval_weights = {k: 1.0 / 12.0 for k in CapabilityKey}
    else:
        eval_weights = true_role_weights

    est_rcis: list[float] = []
    true_rcis: list[float] = []
    cap_errors: list[float] = []

    for cand in cohort:
        rci_est, rci_true, q_hats = evaluate_candidate_ablation(
            cand, mode, eval_weights, true_weights=true_role_weights, config=cfg
        )
        if rci_est is not None:
            est_rcis.append(rci_est)
            true_rcis.append(rci_true)

            for cap_key, q_val in q_hats.items():
                true_q = cand.ground_truth_capabilities[cap_key]
                cap_errors.append(abs(q_val - true_q))

    if len(est_rcis) < 2:
        return {"mae": 0.0, "rmse": 0.0, "spearman": 0.0, "kendall": 0.0}

    rci_errors = [abs(e - t) for e, t in zip(est_rcis, true_rcis)]
    mae = float(np.mean(rci_errors))
    rmse = float(np.sqrt(np.mean([(e - t) ** 2 for e, t in zip(est_rcis, true_rcis)])))
    spearman_corr, _ = stats.spearmanr(est_rcis, true_rcis)
    kendall_corr, _ = stats.kendalltau(est_rcis, true_rcis)
    cap_mae = float(np.mean(cap_errors)) if cap_errors else 0.0

    return {
        "rci_mae": round(mae, 4),
        "rci_rmse": round(rmse, 4),
        "spearman_rho": round(float(spearman_corr), 4),
        "kendall_tau": round(float(kendall_corr), 4),
        "capability_mae": round(cap_mae, 4),
        "sample_count": len(est_rcis),
    }
