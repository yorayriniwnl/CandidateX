"""Scoring outputs: capability estimates, uncertainty, conflicts, and overall RCI/Coverage."""

import uuid
from typing import Optional
from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from cci.db.base import Base, GUID, JSONType, TimestampMixin, UUIDPrimaryKeyMixin


class ScoringConfigEntity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Persisted version of scoring parameters and calibration constants."""
    __tablename__ = "scoring_configs"

    version: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    temperature: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    epsilon: Mapped[float] = mapped_column(Float, default=1e-5, nullable=False)
    low_coverage_threshold: Mapped[float] = mapped_column(Float, default=0.35, nullable=False)
    probe_alpha: Mapped[float] = mapped_column(Float, default=0.40, nullable=False)
    probe_beta: Mapped[float] = mapped_column(Float, default=0.35, nullable=False)
    probe_gamma: Mapped[float] = mapped_column(Float, default=0.25, nullable=False)
    eta_parameters: Mapped[dict] = mapped_column(JSONType, nullable=False)
    lambda_decay: Mapped[dict] = mapped_column(JSONType, nullable=False)
    tau_saturation: Mapped[dict] = mapped_column(JSONType, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class CapabilityEstimateEntity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Individual capability estimate q_k, effective evidence count, and CI bounds."""
    __tablename__ = "capability_estimates"

    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    capability_key: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # CapabilityKey enum
    estimate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # q_k in [0, 100], or None for UNKNOWN
    is_observed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    effective_evidence_count: Mapped[float] = mapped_column(Float, nullable=False)  # n_eff,k
    raw_evidence_count: Mapped[int] = mapped_column(Integer, nullable=False)
    cluster_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    standard_error: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    dispersion: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    ci_lower: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ci_upper: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    coverage_k: Mapped[float] = mapped_column(Float, nullable=False)  # min(1, sum(c)/tau_k)


class CapabilityUncertaintyEntity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Detailed uncertainty diagnostics for a capability."""
    __tablename__ = "capability_uncertainty"

    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    capability_key: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    epistemic_uncertainty: Mapped[float] = mapped_column(Float, nullable=False)
    ci_width: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_low_coverage: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class CapabilityConflictEntity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Contradiction diagnostic D_k between positive and negative evidence."""
    __tablename__ = "capability_conflicts"

    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    capability_key: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    positive_support_sum: Mapped[float] = mapped_column(Float, nullable=False)  # P_k
    negative_support_sum: Mapped[float] = mapped_column(Float, nullable=False)  # N_k
    contradiction_diagnostic: Mapped[float] = mapped_column(Float, nullable=False)  # D_k in [-1, 1]
    has_meaningful_conflict: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    triggering_evidence_ids: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)


class AnalysisScoreEntity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Overall Candidate Capability Intelligence evaluation score (RCI and Coverage)."""
    __tablename__ = "analysis_scores"

    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("analysis_runs.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    rci: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Overall RCI in [0, 100], or None
    coverage: Mapped[float] = mapped_column(Float, nullable=False)      # Evidence coverage in [0, 1]
    is_insufficient_evidence: Mapped[bool] = mapped_column(Boolean, nullable=False)
    observed_capabilities_count: Mapped[int] = mapped_column(Integer, nullable=False)
    scoring_config_version: Mapped[str] = mapped_column(String(50), nullable=False)
