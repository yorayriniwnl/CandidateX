"""Capability-specific recency decay calculations."""

import math
from datetime import datetime, timezone

from cci.domain.contracts import ScoringConfig
from cci.domain.enums import CapabilityKey


def compute_recency_factor(
    delta_t_years: float,
    capability: CapabilityKey,
    config: ScoringConfig | None = None,
) -> float:
    """Computes capability-specific recency decay factor:

        t_{e,k} = exp(-lambda_k * delta_t_e)

    Args:
        delta_t_years: Elapsed time between observation and evaluation (in years). Must be >= 0.
        capability: The specific technical capability key.
        config: Scoring hyperparameters containing capability lambda_decay values.

    Returns:
        Recency factor t_{e,k} in the open interval (0, 1].
    """
    if delta_t_years < 0:
        delta_t_years = 0.0

    cfg = config or ScoringConfig()
    lambda_k = cfg.lambda_decay.get(capability, 0.25)

    return math.exp(-lambda_k * delta_t_years)


def calculate_elapsed_years(
    observed_at: datetime,
    reference_time: datetime | None = None,
) -> float:
    """Calculates elapsed fractional years between observed_at and reference_time."""
    ref = reference_time or datetime.now(timezone.utc)

    # Ensure timezone awareness consistency
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)

    delta_seconds = max(0.0, (ref - observed_at).total_seconds())
    return delta_seconds / (365.25 * 24 * 3600)
