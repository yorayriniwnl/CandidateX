from typing import Any

"""Interview probe priorities and evidence-grounded interview questions."""

import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cci.db.base import GUID, Base, JSONType, TimestampMixin, UUIDPrimaryKeyMixin


class InterviewProbePriority(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Prioritized target capability for interview inquiry I_k."""

    __tablename__ = "interview_probe_priorities"

    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    capability_key: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # CapabilityKey enum
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    priority_score: Mapped[float] = mapped_column(Float, nullable=False)  # I_k
    role_weight: Mapped[float] = mapped_column(Float, nullable=False)  # w_k
    coverage_gap_term: Mapped[float] = mapped_column(Float, nullable=False)  # 1 - Cov_k
    uncertainty_term: Mapped[float] = mapped_column(Float, nullable=False)  # CI width
    contradiction_term: Mapped[float] = mapped_column(
        Float, nullable=False
    )  # D_k based term

    questions: Mapped[list["InterviewQuestionEntity"]] = relationship(
        "InterviewQuestionEntity",
        back_populates="probe_priority",
        cascade="all, delete-orphan",
    )


class InterviewQuestionEntity(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Deterministic, evidence-grounded probe question for interviewer decision support."""

    __tablename__ = "interview_questions"

    probe_priority_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("interview_probe_priorities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_capability: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    verification_guidance: Mapped[str] = mapped_column(Text, nullable=False)
    grounding_evidence_ids: Mapped[list[Any]] = mapped_column(
        JSONType, default=list, nullable=False
    )
    suggested_followups: Mapped[list[Any]] = mapped_column(
        JSONType, default=list, nullable=False
    )

    probe_priority: Mapped["InterviewProbePriority"] = relationship(
        "InterviewProbePriority", back_populates="questions"
    )
