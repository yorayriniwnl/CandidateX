"""Claims verification and corroboration package."""

from cci.claims.corroborator import (
    ClaimCorroborationResult,
    ExtractedClaimInput,
    corroborate_candidate_claims,
)
from cci.claims.identity import (
    detect_duplicate_claims,
    generate_deterministic_claim_id,
    generate_deterministic_claim_uuid,
    normalize_claim_text,
    normalize_claim_type,
    normalize_structured_semantics,
)

__all__ = [
    "ClaimCorroborationResult",
    "ExtractedClaimInput",
    "corroborate_candidate_claims",
    "detect_duplicate_claims",
    "generate_deterministic_claim_id",
    "generate_deterministic_claim_uuid",
    "normalize_claim_text",
    "normalize_claim_type",
    "normalize_structured_semantics",
]
