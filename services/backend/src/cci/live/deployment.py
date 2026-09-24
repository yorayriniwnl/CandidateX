"""Live deployment acquisition and evidence construction (Fix 22).

Wires deployment inspection into live analysis pipeline with:
- Safe SSRF-protected public URL validation
- Read-only HTTP GET (never destructive, never using credentials)
- Structured EvidenceRecord generation supporting deployment existence,
  project linkage, and runtime artifact observation without inflating candidate mastery.
"""

from datetime import datetime, timezone
import hashlib
from typing import Any, Sequence
from urllib.parse import urlparse
from uuid import UUID, uuid4

from cci.analyzers.deployment.inspector import (
    DeploymentInspectionReport,
    inspect_candidate_deployment,
)
from cci.domain.contracts import (
    EvidenceConfidenceFactors,
    EvidenceRecord,
)
from cci.domain.enums import CapabilityKey, SourceFamily
from cci.domain.evidence_families import build_fallback_evidence_family_identity
from cci.scoring.confidence import compute_confidence_from_factors
from cci.scoring.reliability import compute_source_reliability


def acquire_deployment_sources(
    deployment_urls: Sequence[str],
    candidate_repositories: Sequence[str] = (),
    analysis_run_id: UUID | None = None,
    mock_responses: dict[str, Any] | None = None,
    skip_tls_socket: bool = False,
) -> tuple[list[EvidenceRecord], list[dict[str, Any]]]:
    """Inspects candidate-declared deployments and generates immutable evidence records and receipts.

    Invariants:
    1. Never executes candidate code.
    2. Never authenticates with candidate credentials.
    3. Never performs destructive HTTP requests (GET/HEAD only).
    4. Does not give capability credit merely because HTTPS exists:
       Deployment evidence supports deployment existence, project linkage, and runtime observation.
    """
    unique_urls = list(dict.fromkeys(deployment_urls))
    evidence_records: list[EvidenceRecord] = []
    source_receipts: list[dict[str, Any]] = []
    run_id = analysis_run_id or uuid4()

    for url in unique_urls:
        mock_resp = mock_responses.get(url) if mock_responses else None
        report: DeploymentInspectionReport = inspect_candidate_deployment(
            deployment_url=url,
            known_repos=candidate_repositories,
            mock_response=mock_resp,
            skip_tls_socket=skip_tls_socket or (mock_resp is not None),
        )

        receipt: dict[str, Any] = {
            "url": url,
            "kind": "deployment",
            "status": report.status,
            "detail": report.detail,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "verification": (
                "runtime_deployment_inspected"
                if report.status == "observed"
                else "not_verified"
            ),
            "http_status": report.status_code,
            "content_type": report.content_type,
            "application_identity": report.application_identity,
            "linked_repository": report.linked_repository,
            "documented_routes": report.documented_routes,
            "security_headers": report.security_headers,
            "tls": report.tls_info,
            "frontend_structure": report.frontend_structure,
            "app_metadata": report.app_metadata,
            "supported_signals": report.supported_signals,
        }
        source_receipts.append(receipt)

        if report.status != "observed" or not report.evidence_inputs:
            continue

        parsed = urlparse(url)
        hostname = parsed.hostname or url
        cluster_id = f"cluster:deployment:{hostname}"
        revision = f"deployment-{hashlib.sha256(url.encode()).hexdigest()[:12]}"

        # Ownership attribution: higher if linked repository matches candidate repo,
        # otherwise conservative baseline for unauthenticated public URL declaration
        is_linked_to_candidate_repo = bool(
            report.linked_repository
            and any(
                report.linked_repository.lower().rstrip("/") == cr.lower().rstrip("/")
                for cr in candidate_repositories
            )
        )
        ownership_score = 0.85 if is_linked_to_candidate_repo else 0.40
        attribution_basis = (
            "deployment_linked_to_candidate_repository"
            if is_linked_to_candidate_repo
            else "candidate_declared_deployment_url"
        )

        for ev_in in report.evidence_inputs:
            content_hash = hashlib.sha256(
                f"{url}:{ev_in.artifact_path}:{ev_in.symbol_or_line}".encode()
            ).hexdigest()
            fingerprint = hashlib.sha256(
                f"{url}:{ev_in.artifact_path}:{ev_in.symbol_or_line}:{ev_in.target_capability.value}".encode()
            ).hexdigest()

            family_id = ev_in.evidence_family_id
            family_basis = ev_in.evidence_family_basis
            if family_id is None:
                identity = build_fallback_evidence_family_identity(
                    source_family=SourceFamily.DEPLOYMENT,
                    cluster_id=cluster_id,
                    artifact_path=ev_in.artifact_path,
                    capability=ev_in.target_capability,
                    observation_type=ev_in.observation_type,
                    fingerprint=fingerprint,
                )
                family_id = identity.evidence_family_id
                family_basis = identity.basis

            factors = EvidenceConfidenceFactors(
                artifact_integrity=1.0,
                ownership_score=ownership_score,
                recency_factor=1.0,  # Live runtime operational check
                verification_level=0.60,
                depth_specificity=0.35,  # Surface runtime observation; not deep code mastery
                source_reliability=compute_source_reliability(
                    SourceFamily.DEPLOYMENT
                ).posterior_mean,
            )

            record = EvidenceRecord(
                evidence_id=uuid4(),
                analysis_run_id=run_id,
                fingerprint=fingerprint,
                evidence_family_id=family_id,
                evidence_family_basis=family_basis,
                observation_type=ev_in.observation_type,
                source_family=SourceFamily.DEPLOYMENT,
                source_locator=url,
                immutable_revision=revision,
                target_capability=ev_in.target_capability,
                support_score=ev_in.observed_score,
                is_positive_support=ev_in.is_positive_support,
                technical_signal_strength=ev_in.technical_signal_strength,
                cluster_id=cluster_id,
                confidence_factors=factors,
                confidence=compute_confidence_from_factors(factors),
                provenance={
                    "artifact_path": ev_in.artifact_path,
                    "artifact_sha256": content_hash,
                    "symbol_or_line": ev_in.symbol_or_line,
                    "raw_support_text": ev_in.raw_support_text[:2000],
                    "extractor_version": ev_in.extractor_version,
                    "signal_rule_id": ev_in.signal_rule_id,
                    "signal_rule_version": ev_in.signal_rule_version,
                    "linked_repository": report.linked_repository,
                    "application_identity": report.application_identity,
                    "documented_routes": report.documented_routes,
                    "supported_signals": report.supported_signals,
                    "candidate_mastery_inferred": False,
                    "observed_at": datetime.now(timezone.utc).isoformat(),
                },
                artifact_attribution=None,
            )
            evidence_records.append(record)

    return evidence_records, source_receipts
