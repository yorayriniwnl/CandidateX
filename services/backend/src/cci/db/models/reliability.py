"""Beta-posterior source family reliability persistence."""

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from cci.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SourceReliabilityPosterior(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Source family Beta(alpha, beta) reliability tracking and belief snapshot."""

    __tablename__ = "source_reliability_posteriors"

    source_family: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    alpha_prior: Mapped[float] = mapped_column(Float, nullable=False)
    beta_prior: Mapped[float] = mapped_column(Float, nullable=False)
    true_positive_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    false_positive_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    posterior_mean: Mapped[float] = mapped_column(
        Float, nullable=False
    )  # r_s = (TP + alpha)/(TP + FP + alpha + beta)
    state: Mapped[str] = mapped_column(
        String(50), default="expert_prior", nullable=False
    )  # expert_prior, posterior_simulated, or empirically_calibrated
    version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_empirically_updated: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    empirical_sample_size: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    calibration_provenance: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
