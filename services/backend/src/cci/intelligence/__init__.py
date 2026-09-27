"""Deterministic intelligence helpers for evidence quality and repository interpretation.

These modules deliberately avoid external model APIs. They enrich static observations
without executing candidate code or replacing CandidateX's mathematical scoring core.
"""

from cci.intelligence.evidence_quality import (
    EvidenceQualityAssessment,
    assess_evidence_quality,
)

__all__ = ["EvidenceQualityAssessment", "assess_evidence_quality"]
