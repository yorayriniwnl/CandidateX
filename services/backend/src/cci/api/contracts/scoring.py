"""Capability estimates, RCI, and Coverage API schemas."""

from typing import Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from cci.domain.contracts import (
    AnalysisScore,
    CapabilityConflict,
    CapabilityEstimate,
    CapabilityUncertainty,
    RoleProfile,
)
from cci.domain.enums import CapabilityKey


class ScoringOverviewResponse(BaseModel):
    """Interviewer score summary combining RCI, Coverage, and capability details."""
    analysis_run_id: UUID
    overall_score: AnalysisScore
    role_profile: RoleProfile
    capabilities: Dict[CapabilityKey, CapabilityEstimate]
    uncertainties: Dict[CapabilityKey, CapabilityUncertainty]
    conflicts: Dict[CapabilityKey, CapabilityConflict]
