"""Claims verification and corroboration package."""

from cci.claims.corroborator import (
    ClaimCorroborationResult,
    ExtractedClaimInput,
    corroborate_candidate_claims,
)

__all__ = [
    "ClaimCorroborationResult",
    "ExtractedClaimInput",
    "corroborate_candidate_claims",
]
