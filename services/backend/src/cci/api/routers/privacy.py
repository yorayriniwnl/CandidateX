"""Privacy, PII protection, and data retention router (Fix 31)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from cci.db.session import SessionLocal
from cci.security.auth import TenantContext, get_current_tenant
from cci.security.privacy import (
    CandidateDeletionResult,
    DataLifecyclePolicy,
    RetentionEnforcementReport,
    delete_candidate_permanently,
    enforce_retention_policies,
    get_explicit_data_policies,
)

router = APIRouter(prefix="/api/v1/privacy", tags=["Privacy & Data Retention"])


class PrivacyPoliciesResponse(BaseModel):
    policies: list[DataLifecyclePolicy]
    guarantee_no_hidden_indefinite_storage: bool = True
    total_categories: int = 8


@router.get(
    "/policies",
    response_model=PrivacyPoliciesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get explicit data retention and PII protection policies across all 8 data categories",
)
def get_privacy_policies_endpoint() -> PrivacyPoliciesResponse:
    """Returns explicit retention and deletion policies across all 8 CandidateX data categories, guaranteeing no hidden indefinite storage."""
    policies = get_explicit_data_policies()
    return PrivacyPoliciesResponse(
        policies=policies,
        guarantee_no_hidden_indefinite_storage=True,
        total_categories=len(policies),
    )


@router.post(
    "/retention/enforce",
    response_model=RetentionEnforcementReport,
    status_code=status.HTTP_200_OK,
    summary="Trigger data retention enforcement to purge expired parsed text, artifacts, and cache entries",
)
def enforce_retention_endpoint(
    parsed_text_days: int | None = Query(None, description="Override parsed text retention cutoff days"),
    analysis_artifacts_days: int | None = Query(None, description="Override artifact retention cutoff days"),
    tenant: TenantContext = Depends(get_current_tenant),
) -> RetentionEnforcementReport:
    """Purges expired resume text, intermediate analysis artifacts, and cached web data according to configured retention limits."""
    try:
        with SessionLocal() as db:
            report = enforce_retention_policies(
                db=db,
                parsed_text_days=parsed_text_days,
                analysis_artifacts_days=analysis_artifacts_days,
            )
            return report
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retention enforcement failed: {exc}",
        ) from exc


@router.delete(
    "/candidates/{candidate_id}",
    response_model=CandidateDeletionResult,
    status_code=status.HTTP_200_OK,
    summary="GDPR Right-to-be-Forgotten candidate deletion pathway",
)
def gdpr_delete_candidate_endpoint(
    candidate_id: UUID,
    reason: str = Query("gdpr_right_to_be_forgotten", description="Reason for deletion"),
    tenant: TenantContext = Depends(get_current_tenant),
) -> CandidateDeletionResult:
    """Permanently purges all candidate PII, documents, and evidence, recording a cryptographic tombstone."""
    try:
        with SessionLocal() as db:
            return delete_candidate_permanently(
                db=db,
                candidate_id=candidate_id,
                organization_id=tenant.organization_id,
                requested_by=tenant.user_id or "authenticated_user",
                reason=reason,
            )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Candidate deletion failed: {exc}",
        ) from exc
