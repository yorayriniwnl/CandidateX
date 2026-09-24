"""Source family reliability representation via Bayesian Beta-Binomial posteriors.

FORMAL PAPER MODEL:
r_s = (TP_s + alpha_s) / (TP_s + FP_s + alpha_s + beta_s)

HARDENING INVARIANTS (FIX 20):
1. Source reliability priors are expert-selected priors, NOT empirically calibrated.
   They must NEVER be described as "empirically calibrated" unless actually updated
   from external measured real-world ground truth.
2. Every snapshot documents:
   - Prior parameters (alpha_prior, beta_prior)
   - Rationale explaining the domain basis for the baseline prior
   - Version identifier
   - Whether empirically updated (is_empirically_updated = False by default)
   - Real-world sample size (empirical_sample_size = 0 by default)
3. Belief states:
   - EXPERT_PRIOR: Pure expert-selected prior without observation updates.
   - POSTERIOR_SIMULATED: Updated with synthetic/simulation observations (not real outcome truth).
   - EMPIRICALLY_CALIBRATED: Updated from real, consenting measured outcome truth with provenance.
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

# Explicit documented domain rationale for each expert-selected prior
DEFAULT_PRIOR_RATIONALES: dict[SourceFamily, str] = {
    SourceFamily.GITHUB: (
        "Expert-selected prior Beta(10, 2) (mean ≈ 0.833). Reflects deterministic static inspection "
        "of version-controlled code artifacts, tempered by unverified authorship until attributed."
    ),
    SourceFamily.DEPLOYMENT: (
        "Expert-selected prior Beta(8, 2) (mean = 0.800). Reflects runtime observation of reachable "
        "public deployments, discounting transient network failures."
    ),
    SourceFamily.DATABASE: (
        "Expert-selected prior Beta(9, 2) (mean ≈ 0.818). Reflects structural schema definitions and "
        "declarative migrations observed in repository sources."
    ),
    SourceFamily.CODING: (
        "Expert-selected prior Beta(8, 3) (mean ≈ 0.727). Reflects third-party contest/profile records "
        "subject to platform variance and rate-limit boundaries."
    ),
    SourceFamily.CERTIFICATE: (
        "Expert-selected prior Beta(7, 3) (mean = 0.700). Reflects declared credential identifiers "
        "requiring third-party issuer attestation."
    ),
    SourceFamily.RESUME: (
        "Expert-selected prior Beta(5, 5) (mean = 0.500). Uninformative/neutral baseline reflecting "
        "self-report bias; declarations require external corroborating artifacts."
    ),
    SourceFamily.LINKEDIN: (
        "Expert-selected prior Beta(6, 4) (mean = 0.600). Reflects public professional profile claims "
        "with self-report discount."
    ),
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
    rationale: str | None = None,
    is_empirically_updated: bool = False,
    empirical_sample_size: int = 0,
    calibration_provenance: str | None = None,
) -> SourceReliabilitySnapshot:
    """Computes an immutable SourceReliabilitySnapshot given observation counts and priors.

    Invariants:
    1. Unless `is_empirically_updated=True` with explicit external ground truth provenance,
       snapshots are classified as `EXPERT_PRIOR` (when counts are 0) or `POSTERIOR_SIMULATED`
       (when counts are generated from simulations or tests).
    2. Snapshots are NEVER marked `EMPIRICALLY_CALIBRATED` without real outcome data.
    """
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
    has_observations = (true_positives > 0 or false_positives > 0)

    if is_empirically_updated and has_observations:
        state = ReliabilityState.EMPIRICALLY_CALIBRATED
        effective_sample_size = (
            empirical_sample_size
            if empirical_sample_size > 0
            else (true_positives + false_positives)
        )
    elif has_observations:
        state = ReliabilityState.POSTERIOR_SIMULATED
        effective_sample_size = 0
    else:
        state = ReliabilityState.EXPERT_PRIOR
        effective_sample_size = 0

    actual_rationale = rationale or DEFAULT_PRIOR_RATIONALES.get(
        source_family,
        f"Expert-selected prior Beta({alpha}, {beta}) for {source_family.value}."
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
        rationale=actual_rationale,
        is_empirically_updated=is_empirically_updated and has_observations,
        empirical_sample_size=effective_sample_size,
        calibration_provenance=calibration_provenance,
        updated_at=datetime.now(timezone.utc),
    )


def calibrate_from_observations(
    existing_snapshot: SourceReliabilitySnapshot,
    new_true_positives: int,
    new_false_positives: int,
    is_empirically_updated: bool | None = None,
    empirical_sample_size: int | None = None,
    calibration_provenance: str | None = None,
) -> SourceReliabilitySnapshot:
    """Incrementally updates a SourceReliabilitySnapshot with newly observed counts."""
    total_tp = existing_snapshot.true_positive_count + new_true_positives
    total_fp = existing_snapshot.false_positive_count + new_false_positives

    empirical_flag = (
        is_empirically_updated
        if is_empirically_updated is not None
        else existing_snapshot.is_empirically_updated
    )
    sample_sz = (
        empirical_sample_size
        if empirical_sample_size is not None
        else existing_snapshot.empirical_sample_size
    )

    return compute_source_reliability(
        source_family=existing_snapshot.source_family,
        true_positives=total_tp,
        false_positives=total_fp,
        alpha_prior=existing_snapshot.alpha_prior,
        beta_prior=existing_snapshot.beta_prior,
        version=existing_snapshot.version,
        rationale=existing_snapshot.rationale,
        is_empirically_updated=empirical_flag,
        empirical_sample_size=sample_sz,
        calibration_provenance=calibration_provenance or existing_snapshot.calibration_provenance,
    )


def calibrate_from_empirical_outcomes(
    source_family: SourceFamily,
    true_positives: int,
    false_positives: int,
    sample_size: int,
    calibration_provenance: str,
    alpha_prior: float | None = None,
    beta_prior: float | None = None,
    version: str = "1.0.0",
) -> SourceReliabilitySnapshot:
    """Calibrate source reliability from external, verified real-world outcome truth.

    Requires non-empty `calibration_provenance` and `sample_size > 0`.
    """
    if not calibration_provenance or not calibration_provenance.strip():
        raise ValueError(
            "Empirical calibration requires explicit calibration provenance reference"
        )
    if sample_size <= 0:
        raise ValueError("Empirical calibration requires positive sample_size")

    return compute_source_reliability(
        source_family=source_family,
        true_positives=true_positives,
        false_positives=false_positives,
        alpha_prior=alpha_prior,
        beta_prior=beta_prior,
        version=version,
        rationale=(
            f"Empirically calibrated against external measured truth: "
            f"{calibration_provenance.strip()} (N={sample_size})."
        ),
        is_empirically_updated=True,
        empirical_sample_size=sample_size,
        calibration_provenance=calibration_provenance.strip(),
    )


def get_default_reliability_snapshots() -> dict[
    SourceFamily, SourceReliabilitySnapshot
]:
    """Generates default prior reliability snapshots for all 7 canonical source families."""
    return {sf: compute_source_reliability(source_family=sf) for sf in SourceFamily}
