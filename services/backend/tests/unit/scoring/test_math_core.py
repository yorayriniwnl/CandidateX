"""Unit tests validating every individual formal mathematical equation."""

import math
import pytest
from uuid import uuid4
from datetime import datetime, timezone

from cci.domain.contracts import (
    CapabilityEstimate,
    EvidenceConfidenceFactors,
    EvidenceRecord,
    NormalizedRequirement,
    RoleProfile,
    ScoringConfig,
)
from cci.domain.enums import (
    CanonicalRole,
    CapabilityKey,
    RequirementPriority,
    SourceFamily,
)
from cci.scoring.recency import compute_recency_factor, calculate_elapsed_years
from cci.scoring.confidence import compute_evidence_confidence, compute_confidence_from_factors
from cci.scoring.capability import (
    compute_capability_score,
    compute_effective_evidence_count,
)
from cci.scoring.weights import (
    apply_expert_overrides,
    build_role_profile,
    compute_role_importances,
    compute_softmax_weights,
)
from cci.scoring.rci import (
    compute_evidence_coverage,
    compute_rci,
    evaluate_analysis_score,
)
from cci.uncertainty.bootstrap import cluster_bootstrap_ci
from cci.uncertainty.diagnostics import compute_uncertainty_diagnostics
from cci.contradictions.diagnostic import compute_contradiction_diagnostic
from cci.probes.priority import compute_probe_priorities


# ---------------------------------------------------------------------------
# Equation 1: Recency Decay t_{e,k} = exp(-lambda_k * delta_t_e)
# ---------------------------------------------------------------------------

def test_recency_decay_exact_values():
    config = ScoringConfig()
    lambda_be = config.lambda_decay[CapabilityKey.BACKEND_ENGINEERING]

    # At delta_t = 0, recency factor is exactly 1.0
    assert pytest.approx(compute_recency_factor(0.0, CapabilityKey.BACKEND_ENGINEERING, config), rel=1e-6) == 1.0

    # At delta_t = 2.0 years
    expected = math.exp(-lambda_be * 2.0)
    assert pytest.approx(compute_recency_factor(2.0, CapabilityKey.BACKEND_ENGINEERING, config), rel=1e-6) == expected


def test_recency_monotonicity():
    """Recency factor must strictly decrease as elapsed time increases."""
    times = [0.0, 0.5, 1.0, 2.0, 5.0, 10.0]
    factors = [compute_recency_factor(t, CapabilityKey.BACKEND_ENGINEERING) for t in times]

    for i in range(len(factors) - 1):
        assert factors[i] > factors[i + 1]


# ---------------------------------------------------------------------------
# Equation 2: Attribution-gated confidence c = o * (a * t * v * x * r)^(1/5)
# ---------------------------------------------------------------------------

def test_confidence_exact_exponent():
    """Verify evidence quality uses a fifth root and attribution remains a direct gate."""
    # With all six inputs at 0.5, quality is 0.5 and attribution halves its weight.
    conf = compute_evidence_confidence(0.5, 0.5, 0.5, 0.5, 0.5, 0.5)
    assert pytest.approx(conf, rel=1e-6) == 0.25

    # At full evidence quality, confidence weight equals the attribution gate.
    conf_one_half = compute_evidence_confidence(1.0, 0.5, 1.0, 1.0, 1.0, 1.0)
    assert pytest.approx(conf_one_half, rel=1e-6) == 0.5


@pytest.mark.parametrize('attribution', [0.0, 0.01, 0.03, 0.10, 0.25, 0.50, 0.80, 1.0])
def test_attribution_is_a_direct_gate_on_evidence_quality(attribution):
    quality = 0.75
    actual = compute_evidence_confidence(
        artifact_integrity=quality,
        ownership_score=attribution,
        recency_factor=quality,
        verification_level=quality,
        depth_specificity=quality,
        source_reliability=quality,
    )
    factors = EvidenceConfidenceFactors(
        artifact_integrity=quality,
        ownership_score=attribution,
        recency_factor=quality,
        verification_level=quality,
        depth_specificity=quality,
        source_reliability=quality,
    )

    assert pytest.approx(actual, rel=1e-9) == attribution * quality
    assert pytest.approx(factors.composite_confidence, rel=1e-9) == attribution * quality
    assert actual <= attribution


def test_confidence_factor_monotonicity():
    """Increasing any single factor must monotonically increase confidence."""
    base = [0.8, 0.7, 0.6, 0.5, 0.9, 0.75]
    base_conf = compute_evidence_confidence(*base)

    for idx in range(6):
        increased = list(base)
        increased[idx] = min(1.0, base[idx] + 0.1)
        inc_conf = compute_evidence_confidence(*increased)
        assert inc_conf > base_conf


# ---------------------------------------------------------------------------
# Equation 3 & 4: Capability Estimate q_k and Effective Count n_eff
# ---------------------------------------------------------------------------

def _make_dummy_evidence(
    cap: CapabilityKey,
    score: float,
    conf: float,
    cluster: str = "cluster-1",
    is_pos: bool = True,
    ownership: float = 1.0,
) -> EvidenceRecord:
    factors = EvidenceConfidenceFactors(
        artifact_integrity=conf,
        ownership_score=ownership,
        recency_factor=conf,
        verification_level=conf,
        depth_specificity=conf,
        source_reliability=conf,
    )
    return EvidenceRecord(
        fingerprint=str(uuid4()),
        source_family=SourceFamily.GITHUB,
        source_locator="https://github.com/test/repo",
        immutable_revision="main@12345",
        target_capability=cap,
        support_score=score,
        is_positive_support=is_pos,
        confidence_factors=factors,
        confidence=conf * ownership,
        cluster_id=cluster,
        analyzer_version="1.0.0",
    )


def test_effective_evidence_count_inequality():
    """Kish's formula: n_eff <= n_raw for any positive weights, and n_eff == n_raw if equal."""
    # When weights are equal: [0.8, 0.8, 0.8, 0.8] -> n_eff == 4.0
    equal_confs = [0.8, 0.8, 0.8, 0.8]
    assert pytest.approx(compute_effective_evidence_count(equal_confs), rel=1e-6) == 4.0

    # When weights are unequal: n_eff strictly less than 4.0
    unequal_confs = [0.9, 0.7, 0.3, 0.1]
    n_eff = compute_effective_evidence_count(unequal_confs)
    assert n_eff < 4.0
    assert n_eff > 1.0


def test_missing_capability_is_unknown_not_zero():
    """Missing evidence must result in q_k = None (UNKNOWN), never zero."""
    records = [
        _make_dummy_evidence(CapabilityKey.BACKEND_ENGINEERING, 85.0, 0.8),
    ]
    # Evaluate FRONTEND_ENGINEERING which has 0 evidence
    frontend_est = compute_capability_score(records, CapabilityKey.FRONTEND_ENGINEERING)
    assert frontend_est.estimate is None
    assert not frontend_est.is_observed
    assert frontend_est.effective_evidence_count == 0.0
    assert frontend_est.coverage_k == 0.0


def test_weak_attribution_does_not_emit_candidate_capability_estimate():
    capability = CapabilityKey.BACKEND_ENGINEERING
    strongly_attributed = [
        _make_dummy_evidence(capability, 90.0, 1.0, cluster=f"project-{i}")
        for i in range(2)
    ]
    weakly_attributed = [
        _make_dummy_evidence(
            capability, 90.0, 1.0, cluster=f"project-{i}", ownership=0.03
        )
        for i in range(2)
    ]

    strong_estimate = compute_capability_score(
        strongly_attributed, capability
    )
    weak_estimate = compute_capability_score(weakly_attributed, capability)

    assert strong_estimate.is_observed
    assert strong_estimate.estimate == 90.0
    assert weak_estimate.estimate is None
    assert not weak_estimate.is_observed
    assert weak_estimate.raw_evidence_count == 2
    assert 0.0 < weak_estimate.coverage_k < strong_estimate.coverage_k


@pytest.mark.parametrize(
    ("ownership", "expected_observed"), [(0.8749, False), (0.875, True)]
)
def test_capability_estimate_uses_configured_coverage_boundary(
    ownership: float, expected_observed: bool
):
    capability = CapabilityKey.BACKEND_ENGINEERING
    records = [
        _make_dummy_evidence(
            capability, 80.0, 1.0, cluster=f"project-{i}", ownership=ownership
        )
        for i in range(2)
    ]

    estimate = compute_capability_score(records, capability)

    assert estimate.coverage_k == pytest.approx(2.0 * ownership / 5.0)
    assert estimate.is_observed is expected_observed
    assert estimate.estimate == (80.0 if expected_observed else None)


def test_capability_estimate_weighted_average():
    """Verify exact weighted average q_k = sum(c * z) / sum(c)."""
    # Item 1: score=80, conf=0.4 (weight=0.4)
    # Item 2: score=90, conf=0.8 (weight=0.8)
    # q_k = (80*0.4 + 90*0.8) / (0.4 + 0.8) = (32 + 72) / 1.2 = 104 / 1.2 = 86.6667
    records = [
        _make_dummy_evidence(CapabilityKey.DATABASE_ENGINEERING, 80.0, 0.4),
        _make_dummy_evidence(CapabilityKey.DATABASE_ENGINEERING, 90.0, 0.8),
    ]
    config = ScoringConfig(
        tau_saturation={CapabilityKey.DATABASE_ENGINEERING: 1.0}
    )
    est = compute_capability_score(
        records, CapabilityKey.DATABASE_ENGINEERING, config=config
    )
    assert est.is_observed
    assert pytest.approx(est.estimate, rel=1e-4) == (104.0 / 1.2)


# ---------------------------------------------------------------------------
# Equation 7: Contradiction Diagnostic D_k = (P - N) / (P + N + eps)
# ---------------------------------------------------------------------------

def test_contradiction_diagnostic_sign_and_bounds():
    cap = CapabilityKey.SECURITY
    config = ScoringConfig(epsilon=1e-5)

    # 1. Pure positive evidence -> D_k near +1.0
    pure_pos = [_make_dummy_evidence(cap, 85.0, 0.9, is_pos=True)]
    conflict_pos = compute_contradiction_diagnostic(pure_pos, cap, config)
    assert conflict_pos.contradiction_diagnostic > 0.99
    assert not conflict_pos.has_meaningful_conflict

    # 2. Pure negative evidence -> D_k near -1.0
    pure_neg = [_make_dummy_evidence(cap, 20.0, 0.9, is_pos=False)]
    conflict_neg = compute_contradiction_diagnostic(pure_neg, cap, config)
    assert conflict_neg.contradiction_diagnostic < -0.99
    assert not conflict_neg.has_meaningful_conflict

    # 3. Equal positive and negative evidence -> D_k near 0.0 and meaningful conflict flagged
    balanced = [
        _make_dummy_evidence(cap, 90.0, 0.8, is_pos=True),
        _make_dummy_evidence(cap, 15.0, 0.8, is_pos=False),
    ]
    conflict_balanced = compute_contradiction_diagnostic(balanced, cap, config)
    assert pytest.approx(conflict_balanced.contradiction_diagnostic, abs=1e-4) == 0.0
    assert conflict_balanced.has_meaningful_conflict
    assert len(conflict_balanced.triggering_evidence_ids) == 2


# ---------------------------------------------------------------------------
# Equation 8 & 9: Role Importances & Softmax Weights
# ---------------------------------------------------------------------------

def test_softmax_weights_sum_to_one():
    """Softmax weights w_k must sum strictly to 1.0."""
    requirements = [
        NormalizedRequirement(
            source_text="Must have strong Python and distributed systems",
            normalized_name="Python / Distributed Systems",
            priority=RequirementPriority.MANDATORY,
            capability_mappings=[CapabilityKey.BACKEND_ENGINEERING, CapabilityKey.SOFTWARE_ARCHITECTURE],
            mention_frequency=3,
            semantic_specificity=0.8,
        )
    ]
    profile = build_role_profile(requirements, CanonicalRole.BACKEND)
    assert pytest.approx(sum(profile.softmax_weights.values()), rel=1e-5) == 1.0
    assert profile.softmax_weights[CapabilityKey.BACKEND_ENGINEERING] > profile.softmax_weights[CapabilityKey.FRONTEND_ENGINEERING]


def test_expert_override_application():
    """Overrides must normalize, maintain 1.0 sum, and record audit trail."""
    profile = build_role_profile([], CanonicalRole.BACKEND)
    overrides = {cap: 1.0 for cap in CapabilityKey}
    overrides[CapabilityKey.SECURITY] = 10.0  # Massive boost to security

    overridden_profile = apply_expert_overrides(
        original_profile=profile,
        overridden_weights=overrides,
        justification="Senior security-sensitive platform role",
        user_id="lead_reviewer_42",
    )

    assert overridden_profile.is_overridden
    assert pytest.approx(sum(overridden_profile.softmax_weights.values()), rel=1e-5) == 1.0
    assert overridden_profile.softmax_weights[CapabilityKey.SECURITY] > 0.4
    assert overridden_profile.override_audit is not None
    assert overridden_profile.override_audit["user_id"] == "lead_reviewer_42"


# ---------------------------------------------------------------------------
# Equation 10 & 11: Coverage & RCI
# ---------------------------------------------------------------------------

def test_rci_excludes_unobserved_from_denominator():
    """Critical invariant: unobserved capabilities do NOT enter RCI denominator."""
    # Suppose role has equal weights 1/12 across all 12 capabilities.
    weights = {cap: 1.0 / 12.0 for cap in CapabilityKey}

    # Candidate only has evidence for BACKEND_ENGINEERING with score 80.0
    cap_estimates = {
        CapabilityKey.BACKEND_ENGINEERING: CapabilityEstimate(
            capability_key=CapabilityKey.BACKEND_ENGINEERING,
            estimate=80.0,
            is_observed=True,
            effective_evidence_count=3.0,
            raw_evidence_count=3,
            coverage_k=0.6,
        )
    }
    # All other capabilities unobserved
    for cap in CapabilityKey:
        if cap != CapabilityKey.BACKEND_ENGINEERING:
            cap_estimates[cap] = CapabilityEstimate(
                capability_key=cap,
                estimate=None,
                is_observed=False,
                effective_evidence_count=0.0,
                raw_evidence_count=0,
                coverage_k=0.0,
            )

    # RCI must be 80.0 (not 80/12 = 6.67!)
    rci = compute_rci(cap_estimates, weights)
    assert pytest.approx(rci, rel=1e-4) == 80.0

    # Evidence Coverage is penalized by missing capabilities: 0.6 * (1/12) = 0.05
    coverage = compute_evidence_coverage(cap_estimates, weights)
    assert pytest.approx(coverage, rel=1e-4) == (0.6 / 12.0)


def test_rci_excludes_estimates_below_attributed_coverage_threshold():
    capability = CapabilityKey.BACKEND_ENGINEERING
    estimate = CapabilityEstimate(
        capability_key=capability,
        estimate=90.0,
        is_observed=True,
        effective_evidence_count=2.0,
        raw_evidence_count=2,
        coverage_k=0.012,
    )

    assert compute_rci({capability: estimate}, {capability: 1.0}) is None


# ---------------------------------------------------------------------------
# Equation 12: Probe Priority I_k
# ---------------------------------------------------------------------------

def test_probe_priorities_ordering():
    """Capabilities with higher coverage gap and conflict must be prioritized higher."""
    profile = build_role_profile([], CanonicalRole.BACKEND)
    
    # Create estimates where BACKEND has high conflict, FRONTEND has high coverage gap
    capabilities = {}
    uncertainties = {}
    conflicts = {}

    for cap in CapabilityKey:
        capabilities[cap] = CapabilityEstimate(
            capability_key=cap,
            estimate=75.0,
            is_observed=True,
            effective_evidence_count=2.0,
            raw_evidence_count=2,
            coverage_k=0.8 if cap == CapabilityKey.BACKEND_ENGINEERING else 0.1,
        )
        uncertainties[cap] = compute_uncertainty_diagnostics(capabilities[cap])
        conflicts[cap] = compute_contradiction_diagnostic([], cap)

    probes = compute_probe_priorities(profile, capabilities, uncertainties, conflicts)
    assert len(probes) == 12
    # Ranks must be 1 to 12
    assert [p.rank for p in probes] == list(range(1, 13))
    # Priority scores must be monotonically descending
    for i in range(len(probes) - 1):
        assert probes[i].priority_score >= probes[i + 1].priority_score
