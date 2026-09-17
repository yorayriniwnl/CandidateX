"""Beta-posterior source family reliability persistence."""

import uuid
from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from cci.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SourceReliabilityPosterior(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Source family Beta(alpha, beta) reliability tracking and calibration snapshot."""
    __tablename__ = "source_reliability_posteriors"

    source_family: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    alpha_prior: Mapped[float] = mapped_column(Float, nullable=False)
    beta_prior: Mapped[float] = mapped_column(Float, nullable=False)
    true_positive_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    false_positive_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    posterior_mean: Mapped[float] = mapped_column(Float, nullable=False)  # r_s = (TP + alpha)/(TP + FP + alpha + beta)
    state: Mapped[str] = mapped_column(String(50), default="prior", nullable=False)  # prior or calibrated
    version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
