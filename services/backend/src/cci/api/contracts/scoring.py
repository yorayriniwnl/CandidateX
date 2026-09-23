"""Capability estimates, observed index, and coverage API schemas."""

from uuid import UUID

from cci.domain.contracts import (
    AnalysisScore,
    CapabilityConflict,
    CapabilityEstimate,
    CapabilityUncertainty,
    RoleProfile,
)
from cci.domain.enums import CapabilityKey
from pydantic import BaseModel


class ScoringOverviewResponse(BaseModel):
    """Interviewer score summary combining the legacy RCI field, coverage, and capability details."""

    analysis_run_id: UUID
    overall_score: AnalysisScore
    role_profile: RoleProfile
    capabilities: dict[CapabilityKey, CapabilityEstimate]
    uncertainties: dict[CapabilityKey, CapabilityUncertainty]
    conflicts: dict[CapabilityKey, CapabilityConflict]
