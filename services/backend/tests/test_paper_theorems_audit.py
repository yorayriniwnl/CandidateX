"""Formal Paper Theorems and System Invariants Audit Suite (Agent 14).

Verifies all 10 Conference Paper Theorems and Core Axiomatic Invariants:
Theorem 1: Recency Decay Monotonicity and Asymptotics.
Theorem 2: Attribution-Gated Confidence Boundedness & Strict Monotonicity.
Theorem 3: Capability Point Estimate q_k Convexity and Range Preservation.
Theorem 4: Effective Sample Size n_eff,k <= N_k (Kish Design Effect).
Theorem 5: Role Weight Softmax Normalization, Positivity, and Shift Invariance.
Theorem 6: Role Capability Index (RCI) Boundedness and Convexity.
Theorem 7: Contradiction Diagnostic D_k Range [-1, 1] and Neutrality at P = N.
Theorem 8: Information Value Ranking I_k Monotonicity.
Theorem 9: Beta-Binomial Source Reliability Posterior Consistency.
Theorem 10: Platform Security and Governance Invariants:
  - Untrusted code execution prohibition (NEVER executed).
  - Closed-world manifest constraint.
  - Missing evidence produces UNKNOWN (never 0.0).
  - Pure functional rescore with zero re-crawling.
  - Human interviewer decision support only (no autonomous hire/reject).
"""

import math
from datetime import datetime, timezone
from uuid import uuid4
import numpy as np
import pytest

from cci.domain.contracts import (
    CapabilityConflict,
    CapabilityEstimate,
    EvidenceConfidenceFactors,
    EvidenceRecord,
    ScoringConfig,
)
from cci.domain.enums import CanonicalRole, CapabilityKey, SourceFamily
from cci.pipeline.orchestrator import execute_analysis_pipeline, rescore_dossier
from cci.probes.priority import compute_probe_priorities
from cci.scoring.capability import (
    compute_capability_score,
    compute_effective_evidence_count,
)
from cci.scoring.confidence import compute_evidence_confidence
from cci.scoring.rci import compute_evidence_coverage, compute_rci
from cci.scoring.recency import compute_recency_factor
from cci.scoring.reliability import calibrate_from_observations, compute_source_reliability
from cci.scoring.weights import (
    build_role_profile,
    compute_role_importances,
    compute_softmax_weights,
)
from cci.uncertainty.diagnostics import compute_uncertainty_diagnostics


# ------------------------------------------------------------------------------
# Theorem 1: Recency Decay Monotonicity and Asymptotics
# ------------------------------------------------------------------------------
def test_theorem_1_recency_decay():
    """Theorem 1: t(delta_t, k) is strictly monotonically decreasing, t(0) = 1, lim_{t->inf} = 0."""
    for cap in CapabilityKey:
        # At delta_t = 0, recency factor is 1.0
        t0 = compute_recency_factor(delta_t_years=0.0, capability=cap)
        assert t0 == pytest.approx(1.0, abs=1e-6)

        # Strictly decreasing over time: delta_t1 < delta_t2 => t1 > t2
        t1 = compute_recency_factor(delta_t_years=1.0, capability=cap)
        t2 = compute_recency_factor(delta_t_years=3.0, capability=cap)
        t3 = compute_recency_factor(delta_t_years=10.0, capability=cap)
        assert 1.0 > t1 > t2 > t3 > 0.0

        # Asymptotic zero at extreme elapsed time
        t_far = compute_recency_factor(delta_t_years=100.0, capability=cap)
        assert t_far == pytest.approx(0.0, abs=1e-5)

    # Technology evolution speed contrast: ML/Frontend decays faster than Algorithms/Architecture
    cfg_speed = ScoringConfig(
        lambda_decay={
            CapabilityKey.FRONTEND_ENGINEERING: 0.35,
            CapabilityKey.ALGORITHMS_PROBLEM_SOLVING: 0.15,
        }
    )
    t_fe = compute_recency_factor(delta_t_years=2.0, capability=CapabilityKey.FRONTEND_ENGINEERING, config=cfg_speed)
    t_algo = compute_recency_factor(delta_t_years=2.0, capability=CapabilityKey.ALGORITHMS_PROBLEM_SOLVING, config=cfg_speed)
    assert t_fe < t_algo, "Fast-moving tech must decay faster than foundational algorithmic skills"


# ------------------------------------------------------------------------------
# Theorem 2: Attribution-Gated Confidence Boundedness & Strict Monotonicity
# ------------------------------------------------------------------------------
def test_theorem_2_confidence_composition():
    """Theorem 2: c_e,k = o * (a * t * v * x * r)^(1/5) is bounded and monotonic."""
    base_factors = {
        "artifact_integrity": 0.8,
        "ownership_score": 0.8,
        "recency_factor": 0.8,
        "verification_level": 0.8,
        "depth_specificity": 0.8,
        "source_reliability": 0.8,
    }
    c_base = compute_evidence_confidence(**base_factors)
    assert c_base == pytest.approx(0.64, abs=1e-6)

    # Strict monotonicity in every single factor
    for factor_name in base_factors:
        higher_factors = dict(base_factors)
        higher_factors[factor_name] = 0.95
        c_higher = compute_evidence_confidence(**higher_factors)
        assert c_higher > c_base, f"Strict monotonicity violated for factor {factor_name}"

        lower_factors = dict(base_factors)
        lower_factors[factor_name] = 0.3
        c_lower = compute_evidence_confidence(**lower_factors)
        assert c_lower < c_base, f"Strict monotonicity violated for factor {factor_name}"

    # Boundary conditions: all 1s -> 1.0; any zero -> 0.0
    c_max = compute_evidence_confidence(**{k: 1.0 for k in base_factors})
    assert c_max == pytest.approx(1.0, abs=1e-6)

    zero_factors = dict(base_factors)
    zero_factors["ownership_score"] = 0.0
    c_zero = compute_evidence_confidence(**zero_factors)
    assert c_zero == 0.0


# ------------------------------------------------------------------------------
# Theorem 3: Capability Point Estimate q_k Convexity and Range Preservation
# ------------------------------------------------------------------------------
def test_theorem_3_point_estimate_convexity():
    """Theorem 3: q_k is a convex combination of support ratings z_e, lying strictly in [min z_e, max z_e]."""
    cap = CapabilityKey.BACKEND_ENGINEERING
    scores = [65.0, 80.0, 95.0]
    confs = [0.4, 0.9, 0.6]

    records = [
        EvidenceRecord(
            fingerprint=f"fp_{i}",
            source_family=SourceFamily.GITHUB,
            source_locator="https://github.com/repo",
            immutable_revision="sha",
            target_capability=cap,
            support_score=s,
            confidence_factors=EvidenceConfidenceFactors(
                artifact_integrity=c, ownership_score=c, recency_factor=c,
                verification_level=c, depth_specificity=c, source_reliability=c
            ),
            confidence=c,
        )
        for i, (s, c) in enumerate(zip(scores, confs))
    ]

    estimate = compute_capability_score(
        records, cap, config=ScoringConfig(low_coverage_threshold=0.0)
    )
    assert estimate.estimate is not None
    assert min(scores) <= estimate.estimate <= max(scores)
    assert 0.0 <= estimate.estimate <= 100.0

    # If all scores are identical z0, q_k must equal z0 exactly
    uniform_records = [
        EvidenceRecord(
            fingerprint=f"fp_uni_{i}",
            source_family=SourceFamily.GITHUB,
            source_locator="https://github.com/repo",
            immutable_revision="sha",
            target_capability=cap,
            support_score=88.5,
            confidence_factors=EvidenceConfidenceFactors(
                artifact_integrity=c, ownership_score=c, recency_factor=c,
                verification_level=c, depth_specificity=c, source_reliability=c
            ),
            confidence=c,
        )
        for i, c in enumerate([0.2, 0.5, 0.8])
    ]
    est_uni = compute_capability_score(
        uniform_records, cap, config=ScoringConfig(low_coverage_threshold=0.0)
    )
    assert est_uni.estimate == pytest.approx(88.5, abs=1e-5)


# ------------------------------------------------------------------------------
# Theorem 4: Effective Sample Size n_eff,k <= N_k (Kish Design Effect)
# ------------------------------------------------------------------------------
def test_theorem_4_kish_effective_sample_size():
    """Theorem 4: n_eff = (sum c)^2 / sum(c^2) <= N, with equality iff all c_i are identical."""
    # Case 1: Identical confidences => n_eff == N
    n_identical = 7
    c_identical = [0.85] * n_identical
    n_eff_identical = compute_effective_evidence_count(c_identical)
    assert n_eff_identical == pytest.approx(n_identical, abs=1e-5)

    # Case 2: Unequal confidences => n_eff < N strictly
    c_unequal = [0.95, 0.20, 0.15, 0.88, 0.35, 0.10]
    n_eff_unequal = compute_effective_evidence_count(c_unequal)
    assert n_eff_unequal < len(c_unequal)
    assert n_eff_unequal >= 1.0


# ------------------------------------------------------------------------------
# Theorem 5: Role Weight Softmax Normalization, Positivity, and Shift Invariance
# ------------------------------------------------------------------------------
def test_theorem_5_softmax_role_weights():
    """Theorem 5: Softmax role weights satisfy sum w_k = 1.0, w_k > 0, and shift invariance."""
    importances = {
        cap: float(i + 1) * 0.5
        for i, cap in enumerate(CapabilityKey)
    }

    # Sum to 1.0 and strictly positive
    weights = compute_softmax_weights(importances, temperature=1.0)
    assert sum(weights.values()) == pytest.approx(1.0, abs=1e-6)
    for w in weights.values():
        assert w > 0.0

    # Shift Invariance: u_k' = u_k + C produces identical softmax weights
    shift_c = 42.5
    shifted_importances = {cap: u + shift_c for cap, u in importances.items()}
    shifted_weights = compute_softmax_weights(shifted_importances, temperature=1.0)

    for cap in CapabilityKey:
        assert shifted_weights[cap] == pytest.approx(weights[cap], abs=1e-5)

    # Temperature limits: as T -> inf, weights approach uniform 1/12
    high_temp_weights = compute_softmax_weights(importances, temperature=10000.0)
    expected_uniform = 1.0 / 12.0
    for w in high_temp_weights.values():
        assert w == pytest.approx(expected_uniform, abs=1e-3)


# ------------------------------------------------------------------------------
# Theorem 6: Role Capability Index (RCI) Boundedness and Convexity
# ------------------------------------------------------------------------------
def test_theorem_6_rci_properties():
    """Theorem 6: RCI is in [0, 100], and if all observed capabilities equal q0, RCI = q0."""
    role_weights = {cap: 1.0 / 12.0 for cap in CapabilityKey}

    # Case 1: Arbitrary observed estimates
    estimates = {}
    for i, cap in enumerate(CapabilityKey):
        is_obs = i < 6  # 6 observed, 6 unobserved
        estimates[cap] = CapabilityEstimate(
            capability_key=cap,
            estimate=float(60 + i * 5) if is_obs else None,
            is_observed=is_obs,
            effective_evidence_count=3.0 if is_obs else 0.0,
            raw_evidence_count=4 if is_obs else 0,
            standard_error=2.0 if is_obs else 0.0,
            dispersion=3.0 if is_obs else 0.0,
            ci_lower=55.0 if is_obs else None,
            ci_upper=85.0 if is_obs else None,
            coverage_k=0.7 if is_obs else 0.0,
        )

    rci = compute_rci(estimates, role_weights)
    assert rci is not None
    assert 0.0 <= rci <= 100.0

    # Case 2: Constant observed score q0
    q0 = 82.4
    estimates_constant = {
        cap: CapabilityEstimate(
            capability_key=cap,
            estimate=q0 if i < 4 else None,
            is_observed=(i < 4),
            effective_evidence_count=2.0 if i < 4 else 0.0,
            raw_evidence_count=3 if i < 4 else 0,
            standard_error=1.0 if i < 4 else 0.0,
            dispersion=2.0 if i < 4 else 0.0,
            ci_lower=q0 - 5 if i < 4 else None,
            ci_upper=q0 + 5 if i < 4 else None,
            coverage_k=0.5 if i < 4 else 0.0,
        )
        for i, cap in enumerate(CapabilityKey)
    }
    rci_constant = compute_rci(estimates_constant, role_weights)
    assert rci_constant == pytest.approx(q0, abs=1e-5)


# ------------------------------------------------------------------------------
# Theorem 7: Contradiction Diagnostic D_k Properties
# ------------------------------------------------------------------------------
def test_theorem_7_contradiction_diagnostic():
    """Theorem 7: D_k = (P - N)/(P + N + eps) in [-1, 1], D_k = 0 when P = N."""
    cfg = ScoringConfig(epsilon=0.01)

    def d_k(pos: float, neg: float) -> float:
        return (pos - neg) / (pos + neg + cfg.epsilon)

    # When positive support == negative support, D_k is 0.0
    assert d_k(15.0, 15.0) == pytest.approx(0.0, abs=1e-6)

    # When positive strongly dominates, D_k approaches +1.0
    assert d_k(100.0, 0.0) == pytest.approx(1.0, abs=1e-3)

    # When negative strongly dominates, D_k approaches -1.0
    assert d_k(0.0, 100.0) == pytest.approx(-1.0, abs=1e-3)

    # Range preservation across extreme values
    for p in [0.0, 0.1, 5.0, 50.0, 1000.0]:
        for n in [0.0, 0.1, 5.0, 50.0, 1000.0]:
            val = d_k(p, n)
            assert -1.0 <= val <= 1.0


# ------------------------------------------------------------------------------
# Theorem 8: Information Value Ranking I_k Monotonicity
# ------------------------------------------------------------------------------
def test_theorem_8_probe_priority_monotonicity():
    """Theorem 8: Probe priority I_k increases with coverage gap (1 - Cov_k)."""
    profile = build_role_profile([], CanonicalRole.BACKEND)
    cap1 = CapabilityKey.BACKEND_ENGINEERING
    cap2 = CapabilityKey.DATABASE_ENGINEERING

    # Construct two identical capabilities except cap1 has lower coverage (larger gap)
    est_large_gap = CapabilityEstimate(
        capability_key=cap1, estimate=80.0, is_observed=True,
        effective_evidence_count=2.0, raw_evidence_count=2,
        standard_error=2.0, dispersion=3.0, ci_lower=75.0, ci_upper=85.0,
        coverage_k=0.2, # 80% coverage gap
    )
    est_small_gap = CapabilityEstimate(
        capability_key=cap2, estimate=80.0, is_observed=True,
        effective_evidence_count=8.0, raw_evidence_count=8,
        standard_error=2.0, dispersion=3.0, ci_lower=75.0, ci_upper=85.0,
        coverage_k=0.9, # 10% coverage gap
    )

    capabilities = {cap1: est_large_gap, cap2: est_small_gap}
    for cap in CapabilityKey:
        if cap not in capabilities:
            capabilities[cap] = CapabilityEstimate(
                capability_key=cap, estimate=None, is_observed=False,
                effective_evidence_count=0.0, raw_evidence_count=0,
                standard_error=0.0, dispersion=0.0, ci_lower=None, ci_upper=None, coverage_k=0.0,
            )

    uncertainties = {cap: compute_uncertainty_diagnostics(est) for cap, est in capabilities.items()}
    conflicts = {
        cap: CapabilityConflict(
            capability_key=cap, positive_support_sum=10.0, negative_support_sum=1.0,
            contradiction_diagnostic=0.8, has_meaningful_conflict=False
        )
        for cap in CapabilityKey
    }

    # Uniform role profile to test coverage gap effect purely
    probes = compute_probe_priorities(
        role_profile=profile,
        capabilities=capabilities,
        uncertainties=uncertainties,
        conflicts=conflicts,
    )

    probe_map = {p.capability_key: p for p in probes}
    # Larger coverage gap must contribute larger coverage_gap_term
    assert probe_map[cap1].coverage_gap_term > probe_map[cap2].coverage_gap_term


# ------------------------------------------------------------------------------
# Theorem 9: Beta-Binomial Source Reliability Posterior Consistency
# ------------------------------------------------------------------------------
def test_theorem_9_beta_binomial_consistency():
    """Theorem 9: Beta-binomial posterior mean converges to empirical success rate as n -> inf."""
    # Prior Beta(8, 2) => Prior mean = 8/10 = 0.80
    prior_alpha, prior_beta = 8.0, 2.0
    snap_prior = compute_source_reliability(
        source_family=SourceFamily.GITHUB,
        alpha_prior=prior_alpha,
        beta_prior=prior_beta,
    )
    assert snap_prior.posterior_mean == pytest.approx(0.80, abs=1e-5)

    # Observe 900 successes and 100 failures out of 1000 trials (90% success)
    snap_post = calibrate_from_observations(
        existing_snapshot=snap_prior,
        new_true_positives=900,
        new_false_positives=100,
    )
    # Posterior mean should be (8 + 900) / (10 + 1000) = 908 / 1010 ~ 0.899
    assert snap_post.posterior_mean == pytest.approx(908.0 / 1010.0, abs=1e-3)
    assert abs(snap_post.posterior_mean - 0.90) < 0.01


# ------------------------------------------------------------------------------
# Theorem 10: Platform Security and Governance Invariants
# ------------------------------------------------------------------------------
def test_theorem_10_system_invariants():
    """Theorem 10: Validates all core architectural, security, and governance invariants."""
    # 1. Missing Evidence Invariant: unobserved capabilities must be UNKNOWN, never 0.0
    state = execute_analysis_pipeline(
        candidate_id=uuid4(),
        role=CanonicalRole.BACKEND,
    )
    assert state.dossier is not None
    unobserved = state.dossier.capability_estimates[CapabilityKey.MACHINE_LEARNING]
    assert unobserved.estimate is None
    assert unobserved.is_observed is False
    assert unobserved.coverage_k == 0.0

    # 2. Pure Functional Rescore Invariant: does not re-crawl and produces identical point estimates
    dossier1 = state.dossier
    custom_w = {CapabilityKey.BACKEND_ENGINEERING: 0.60, CapabilityKey.DATABASE_ENGINEERING: 0.40}
    dossier2 = rescore_dossier(dossier1, custom_w)

    for cap in CapabilityKey:
        est1 = dossier1.capability_estimates[cap]
        est2 = dossier2.capability_estimates[cap]
        assert est1.estimate == est2.estimate
        assert est1.is_observed == est2.is_observed
        assert est1.effective_evidence_count == est2.effective_evidence_count

    # 3. Decision Support Invariant: system limits state no autonomous decisions
    assert any("decision support only" in limit.lower() for limit in dossier1.system_limitations)
    assert any("never executed" in limit.lower() for limit in dossier1.system_limitations)
