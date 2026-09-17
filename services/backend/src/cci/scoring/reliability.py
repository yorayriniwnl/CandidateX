"""Source family reliability calibration via Bayesian Beta-Binomial posteriors.

FORMAL PAPER MODEL:
r_s = (TP_s + alpha_s) / (TP_s + FP_s + alpha_s + beta_s)

INVARIANTS:
1. Reliability calibration is purely functional and deterministic.
2. Priors reflect empirical precision per source family:
   - Git/Code artifacts: high baseline reliability (Beta(10, 2) -> 0.833).
   - Operational Deployments: high baseline reliability (Beta(8, 2) -> 0.800).
   - Database Schemas: high baseline reliability (Beta(9, 2) -> 0.818).
   - Resumes / Self-claims: moderate baseline reliability (Beta(5, 5) -> 0.500).
"""

from datetime import datetime, timezone

from cci.domain.contracts import SourceReliabilitySnapshot
from cci.domain.enums import ReliabilityState, SourceFamily

# Canonical default Beta priors: (alpha, beta)
DEFAULT_PRIORS: dict[SourceFamily, tuple[float, float]] = {
    SourceFamily.GITHUB: (10.0, 2.0),  # Mean: 10/12 ≈ 0.8333
    SourceFamily.DEPLOYMENT: (8.0, 2.0),  # Mean: 8/10 = 0.8000
    SourceFamily.DATABASE: (9.0, 2.0),  # Mean: 9/11 ≈ 0.8182
    SourceFamily.CODING: (8.0, 3.0),  # Mean: 8/11 ≈ 0.7273
    SourceFamily.CERTIFICATE: (7.0, 3.0),  # Mean: 7/10 = 0.7000
    SourceFamily.RESUME: (5.0, 5.0),  # Mean: 5/10 = 0.5000 (self-report bias discount)
    SourceFamily.LINKEDIN: (6.0, 4.0),  # Mean: 6/10 = 0.6000
}


def calculate_beta_mean(tp: int, fp: int, alpha: float, beta: float) -> float:
    """Calculates posterior mean r_s = (TP + alpha) / (TP + FP + alpha + beta)."""
    numerator = float(tp) + alpha
    denominator = float(tp + fp) + alpha + beta
    if denominator <= 0.0:
        return 0.5
    return max(0.0, min(1.0, numerator / denominator))


def calculate_beta_variance(tp: int, fp: int, alpha: float, beta: float) -> float:
    """Calculates posterior variance Var(r_s) = (a * b) / ((a + b)^2 * (a + b + 1))."""
    a = float(tp) + alpha
    b = float(fp) + beta
    total = a + b
    if total <= 0.0:
        return 0.0
    return (a * b) / ((total**2) * (total + 1.0))


def compute_source_reliability(
    source_family: SourceFamily,
    true_positives: int = 0,
    false_positives: int = 0,
    alpha_prior: float | None = None,
    beta_prior: float | None = None,
    version: str = "1.0.0",
) -> SourceReliabilitySnapshot:
    """Computes an immutable SourceReliabilitySnapshot given TP/FP counts and priors."""
    if true_positives < 0 or false_positives < 0:
        raise ValueError(
            "True positive and false positive counts must be non-negative integers"
        )

    default_alpha, default_beta = DEFAULT_PRIORS.get(source_family, (5.0, 5.0))
    alpha = alpha_prior if alpha_prior is not None else default_alpha
    beta = beta_prior if beta_prior is not None else default_beta

    if alpha <= 0.0 or beta <= 0.0:
        raise ValueError(
            "Beta prior parameters alpha and beta must be strictly positive"
        )

    mean = calculate_beta_mean(true_positives, false_positives, alpha, beta)
    state = (
        ReliabilityState.CALIBRATED
        if (true_positives > 0 or false_positives > 0)
        else ReliabilityState.PRIOR
    )

    return SourceReliabilitySnapshot(
        source_family=source_family,
        alpha_prior=alpha,
        beta_prior=beta,
        true_positive_count=true_positives,
        false_positive_count=false_positives,
        posterior_mean=mean,
        state=state,
        version=version,
        updated_at=datetime.now(timezone.utc),
    )


def calibrate_from_observations(
    existing_snapshot: SourceReliabilitySnapshot,
    new_true_positives: int,
    new_false_positives: int,
) -> SourceReliabilitySnapshot:
    """Incrementally updates a SourceReliabilitySnapshot with newly verified observation counts."""
    total_tp = existing_snapshot.true_positive_count + new_true_positives
    total_fp = existing_snapshot.false_positive_count + new_false_positives

    return compute_source_reliability(
        source_family=existing_snapshot.source_family,
        true_positives=total_tp,
        false_positives=total_fp,
        alpha_prior=existing_snapshot.alpha_prior,
        beta_prior=existing_snapshot.beta_prior,
        version=existing_snapshot.version,
    )


def get_default_reliability_snapshots() -> dict[
    SourceFamily, SourceReliabilitySnapshot
]:
    """Generates default prior reliability snapshots for all 7 canonical source families."""
    return {sf: compute_source_reliability(source_family=sf) for sf in SourceFamily}
