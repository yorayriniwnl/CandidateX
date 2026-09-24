"""Database persistence for empirical calibration cases (Fix 21)."""

from datetime import datetime
from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from cci.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CalibrationCaseModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Persistence model for consenting real or benchmark calibration cases."""

    __tablename__ = "calibration_cases"

    anonymized_subject_id: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    is_synthetic: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    consent_granted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_version: Mapped[str] = mapped_column(String(50), nullable=False)
    data_source: Mapped[str] = mapped_column(String(100), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
