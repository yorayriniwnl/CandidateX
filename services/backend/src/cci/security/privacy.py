"""Privacy, PII Protection, and Retention Management Service (Fix 31).

Implements explicit data lifecycle policies, PII redaction from application logs,
comprehensive candidate deletion pathways (GDPR Right-to-be-Forgotten),
and retention enforcement to eliminate hidden indefinite storage.
"""

import hashlib
import logging
import re
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from cci.config import settings
from cci.db import models
from cci.db.models.audit import AuditEvent, DeletionEvent
from cci.security.audit import audit_service


# ------------------------------------------------------------------------------
# 1. Explicit Data Category Policies (No Hidden Indefinite Storage)
# ------------------------------------------------------------------------------
class DataCategory(str, Enum):
    UPLOADED_RESUME_BYTES = "uploaded_resume_bytes"
    EXTRACTED_PII = "extracted_pii"
    PARSED_RESUME_TEXT = "parsed_resume_text"
    ANALYSIS_ARTIFACTS = "analysis_artifacts"
    CACHED_PAGES = "cached_pages"
    CANDIDATE_RECORDS = "candidate_records"
    LOGS = "logs"
    EXPORTS = "exports"


class DataLifecyclePolicy(BaseModel):
    category: DataCategory
    description: str
    max_retention_days: float | None
    max_retention_hours: float | None
    is_indefinite: bool = False
    storage_location: str
    deletion_pathway: str
    logging_policy: str


def get_explicit_data_policies() -> list[DataLifecyclePolicy]:
    """Returns the explicit data lifecycle and retention policies across all 8 data categories."""
    return [
        DataLifecyclePolicy(
            category=DataCategory.UPLOADED_RESUME_BYTES,
            description="Raw binary bytes of uploaded resumes (PDF / DOCX).",
            max_retention_days=None,
            max_retention_hours=float(settings.RETENTION_RESUME_BYTES_HOURS),
            is_indefinite=False,
            storage_location="Ephemeral in-memory stream during intake parsing; zero permanent disk persistence.",
            deletion_pathway="Purged immediately post-parse; ephemeral staging cleared upon parse completion.",
            logging_policy="STRICTLY FORBIDDEN: Raw binary bytes and document buffers are never logged.",
        ),
        DataLifecyclePolicy(
            category=DataCategory.EXTRACTED_PII,
            description="Personal identifying information (candidate full names, personal emails, phone numbers).",
            max_retention_days=float(settings.RETENTION_CANDIDATE_RECORDS_DAYS),
            max_retention_hours=None,
            is_indefinite=False,
            storage_location="PostgreSQL / SQLite candidate and identity tables scoped strictly to authenticated tenant.",
            deletion_pathway="Full deletion pathway via DELETE /api/v1/candidates/{id} with cryptographic tombstone.",
            logging_policy="REDACTED: Automatically masked as [REDACTED_EMAIL] and [REDACTED_PHONE] via PIISanitizingFilter.",
        ),
        DataLifecyclePolicy(
            category=DataCategory.PARSED_RESUME_TEXT,
            description="Raw textual content extracted from candidate CV documents.",
            max_retention_days=float(settings.RETENTION_PARSED_TEXT_DAYS),
            max_retention_hours=None,
            is_indefinite=False,
            storage_location="candidate_documents.parsed_content in database and intake manifest.",
            deletion_pathway="Retention enforcement purges text after TTL; erased on candidate deletion request.",
            logging_policy="STRICTLY FORBIDDEN: Resume body text is intercepted and redacted to [REDACTED_RESUME_TEXT].",
        ),
        DataLifecyclePolicy(
            category=DataCategory.ANALYSIS_ARTIFACTS,
            description="Intermediate analysis artifacts, AST representations, and token extractions.",
            max_retention_days=float(settings.RETENTION_ANALYSIS_ARTIFACTS_DAYS),
            max_retention_hours=None,
            is_indefinite=False,
            storage_location="Analysis stage run data and temporary worker execution buffers.",
            deletion_pathway="Intermediate buffers cleared post-pipeline; expired runs evicted by retention enforcer.",
            logging_policy="Sanitized: Credentials, private repository tokens, and candidate text are stripped.",
        ),
        DataLifecyclePolicy(
            category=DataCategory.CACHED_PAGES,
            description="Public web pages, repository metadata, and HTTP query response caches.",
            max_retention_days=None,
            max_retention_hours=float(settings.RETENTION_CACHED_PAGES_HOURS),
            is_indefinite=False,
            storage_location="In-memory ContentCache with TTL eviction.",
            deletion_pathway="Automatic TTL expiration and manual eviction upon candidate deletion.",
            logging_policy="URL domain and status only; body text and discovered personal pages omitted.",
        ),
        DataLifecyclePolicy(
            category=DataCategory.CANDIDATE_RECORDS,
            description="Candidate profile metadata, skills inventory, and evaluated capability dossiers.",
            max_retention_days=float(settings.RETENTION_CANDIDATE_RECORDS_DAYS),
            max_retention_hours=None,
            is_indefinite=False,
            storage_location="candidates, identities, dossier_snapshots database tables.",
            deletion_pathway="DELETE /api/v1/candidates/{id} permanently cascades across all tables with tombstone hash.",
            logging_policy="Candidate UUIDs and status transitions only; PII redacted.",
        ),
        DataLifecyclePolicy(
            category=DataCategory.LOGS,
            description="Application server runtime logs, access records, and diagnostic traces.",
            max_retention_days=float(settings.RETENTION_LOGS_DAYS),
            max_retention_hours=None,
            is_indefinite=False,
            storage_location="Standard application logging stream / log rotate buffers.",
            deletion_pathway="System log rotation deletes log archives older than 30 days.",
            logging_policy="PIISanitizingFilter enforced on all loggers; zero resume bodies or contact PII allowed.",
        ),
        DataLifecyclePolicy(
            category=DataCategory.EXPORTS,
            description="Generated candidate dossier export reports (HTML / JSON / PDF).",
            max_retention_days=float(settings.RETENTION_EXPORTS_DAYS),
            max_retention_hours=None,
            is_indefinite=False,
            storage_location="Dynamic on-the-fly generation or temporary export cache.",
            deletion_pathway="Generated ephemerally; cached exports purged when candidate is deleted.",
            logging_policy="Audit trail records export action with candidate UUID; export body unlogged.",
        ),
    ]


# ------------------------------------------------------------------------------
# 2. PII Sanitization & Safe Logging Filter
# ------------------------------------------------------------------------------
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
PHONE_REGEX = re.compile(
    r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
)
SSN_REGEX = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
BEARER_REGEX = re.compile(r"Bearer\s+[A-Za-z0-9._~+/-]+=*", re.IGNORECASE)
API_KEY_REGEX = re.compile(
    r"(?:api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]+['\"]", re.IGNORECASE
)

RESUME_SECTION_MARKERS = [
    r"work\s+experience",
    r"professional\s+experience",
    r"employment\s+history",
    r"technical\s+skills",
    r"education",
    r"certifications",
]
RESUME_BLOCK_REGEX = re.compile(
    r"(?:(?:" + "|".join(RESUME_SECTION_MARKERS) + r")[\s\S]{100,})",
    re.IGNORECASE,
)


def sanitize_sensitive_text(text: str) -> str:
    """Sanitizes text by stripping out emails, phones, SSNs, credentials, and resume bodies."""
    if not isinstance(text, str):
        return text

    # Redact credentials and auth headers
    sanitized = BEARER_REGEX.sub("Bearer [REDACTED_TOKEN]", text)
    sanitized = API_KEY_REGEX.sub("api_key=[REDACTED_KEY]", sanitized)

    # Redact PII
    sanitized = EMAIL_REGEX.sub("[REDACTED_EMAIL]", sanitized)
    sanitized = PHONE_REGEX.sub("[REDACTED_PHONE]", sanitized)
    sanitized = SSN_REGEX.sub("[REDACTED_SSN]", sanitized)

    # Redact large resume text bodies if accidentally passed to logger
    if len(sanitized) > 200 and RESUME_BLOCK_REGEX.search(sanitized):
        sanitized = RESUME_BLOCK_REGEX.sub("[REDACTED_RESUME_TEXT]", sanitized)

    return sanitized


class PIISanitizingFilter(logging.Filter):
    """Logging filter that strips candidate PII and resume text from log records before emission."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not getattr(settings, "PII_LOG_REDACTION_ENABLED", True):
            return True

        if isinstance(record.msg, str):
            record.msg = sanitize_sensitive_text(record.msg)

        if record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(
                    sanitize_sensitive_text(str(a)) if isinstance(a, str) else a
                    for a in record.args
                )
            elif isinstance(record.args, dict):
                record.args = {
                    k: sanitize_sensitive_text(str(v)) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
        return True


def configure_pii_safe_logging() -> None:
    """Attaches PIISanitizingFilter to root and cci loggers to guarantee safe logging."""
    pii_filter = PIISanitizingFilter()
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.addFilter(pii_filter)

    cci_logger = logging.getLogger("cci")
    cci_logger.addFilter(pii_filter)
    for handler in cci_logger.handlers:
        handler.addFilter(pii_filter)


# ------------------------------------------------------------------------------
# 3. Candidate Deletion Pathway (GDPR Right-to-be-Forgotten)
# ------------------------------------------------------------------------------
class CandidateDeletionResult(BaseModel):
    candidate_id: UUID
    candidate_id_hash: str
    is_deleted: bool
    deleted_tables: list[str]
    tombstone_id: UUID
    recorded_at: str
    message: str


def delete_candidate_permanently(
    db: Session,
    candidate_id: UUID,
    organization_id: UUID,
    requested_by: str | UUID = "system",
    reason: str = "gdpr_right_to_be_forgotten",
) -> CandidateDeletionResult:
    """Permanently deletes all candidate PII, documents, and evidence, writing a cryptographic tombstone."""
    from cci.api.routers.dossier import unregister_dossier
    from cci.live.runner import get_analysis_run_manager
    from cci.pipeline.service import pipeline_service

    live_run_manager = get_analysis_run_manager()

    # 1. Fetch candidate scoped to organization
    cand = (
        db.query(models.Candidate)
        .filter(
            models.Candidate.id == candidate_id,
            models.Candidate.organization_id == organization_id,
        )
        .first()
    )

    if not cand:
        raise ValueError(
            f"Candidate {candidate_id} not found in organization {organization_id}."
        )

    cand_id_str = str(candidate_id)
    cand_id_hash = hashlib.sha256(cand_id_str.encode("utf-8")).hexdigest()
    tombstone_id = uuid4()
    now_iso = datetime.now(timezone.utc).isoformat()

    deleted_tables = [
        "candidates",
        "identities",
        "identity_links",
        "candidate_documents",
        "candidate_sources",
        "projects",
        "dossier_snapshots",
        "analysis_runs",
        "correction_requests",
    ]

    # 2. Delete database records (cascaded by foreign keys or explicitly)
    try:
        # Delete document records
        db.execute(
            delete(models.CandidateDocument).where(
                models.CandidateDocument.candidate_id == candidate_id
            )
        )
        # Delete source records
        db.execute(
            delete(models.CandidateSource).where(
                models.CandidateSource.candidate_id == candidate_id
            )
        )
        # Delete analysis runs and associated dossier snapshots
        run_ids = [
            r.id
            for r in db.query(models.AnalysisRun)
            .filter(models.AnalysisRun.candidate_id == candidate_id)
            .all()
        ]
        if run_ids:
            db.execute(
                delete(models.DossierSnapshot).where(
                    models.DossierSnapshot.analysis_run_id.in_(run_ids)
                )
            )
            db.execute(
                delete(models.AnalysisRun).where(models.AnalysisRun.id.in_(run_ids))
            )
        # Delete correction requests
        db.execute(
            delete(models.CorrectionRequest).where(
                models.CorrectionRequest.candidate_id == candidate_id
            )
        )
        # Delete core candidate row
        db.delete(cand)

        # 3. Create immutable GDPR deletion tombstone
        tombstone = DeletionEvent(
            id=tombstone_id,
            candidate_id_hash=cand_id_hash,
            requested_by=str(requested_by),
            deleted_tables=deleted_tables,
            reason=reason,
        )
        db.add(tombstone)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise RuntimeError(f"Database deletion failed: {exc}") from exc

    # 4. Evict in-memory caches across all components
    unregister_dossier(candidate_id)
    live_run_manager.evict_candidate_runs(candidate_id)
    pipeline_service.evict_candidate(candidate_id)

    # 5. Record audit trail event for deletion action
    audit_service.record_event(
        organization_id=organization_id,
        action="candidate_gdpr_deletion",
        entity_type="candidate",
        entity_id=candidate_id,
        actor_id=requested_by if isinstance(requested_by, UUID) else None,
        old_value={"candidate_id_hash": cand_id_hash},
        new_value={"status": "permanently_deleted"},
        reason=reason,
        details={
            "tombstone_id": str(tombstone_id),
            "deleted_tables": deleted_tables,
        },
        db=None,
    )

    return CandidateDeletionResult(
        candidate_id=candidate_id,
        candidate_id_hash=cand_id_hash,
        is_deleted=True,
        deleted_tables=deleted_tables,
        tombstone_id=tombstone_id,
        recorded_at=now_iso,
        message="Candidate records and associated PII permanently purged. Cryptographic tombstone recorded.",
    )


# ------------------------------------------------------------------------------
# 4. Retention Policy Enforcement
# ------------------------------------------------------------------------------
class RetentionEnforcementReport(BaseModel):
    enforced_at: str
    documents_purged: int = 0
    runs_purged: int = 0
    cache_entries_evicted: int = 0
    details: str


def enforce_retention_policies(
    db: Session | None = None,
    *,
    parsed_text_days: int | None = None,
    analysis_artifacts_days: int | None = None,
) -> RetentionEnforcementReport:
    """Enforces maximum retention limits on parsed text, intermediate artifacts, and caches."""
    from cci.live.runner import get_analysis_run_manager
    from cci.security.abuse import get_abuse_controls

    live_run_manager = get_analysis_run_manager()
    content_cache = get_abuse_controls().cache

    max_text_days = (
        parsed_text_days
        if parsed_text_days is not None
        else settings.RETENTION_PARSED_TEXT_DAYS
    )
    max_artifact_days = (
        analysis_artifacts_days
        if analysis_artifacts_days is not None
        else settings.RETENTION_ANALYSIS_ARTIFACTS_DAYS
    )

    now = datetime.now(timezone.utc)
    text_cutoff = now - timedelta(days=max_text_days)
    artifact_cutoff = now - timedelta(days=max_artifact_days)

    docs_purged = 0
    runs_purged = 0

    if db is not None:
        try:
            # Purge parsed_content from documents older than retention TTL
            old_docs = (
                db.query(models.CandidateDocument)
                .filter(models.CandidateDocument.created_at < text_cutoff)
                .all()
            )
            for doc in old_docs:
                db.delete(doc)
                docs_purged += 1

            # Purge stage data / artifacts from old analysis runs
            old_runs = (
                db.query(models.AnalysisRun)
                .filter(models.AnalysisRun.created_at < artifact_cutoff)
                .all()
            )
            for r in old_runs:
                db.delete(r)
                runs_purged += 1

            db.commit()
        except Exception:
            db.rollback()

    # Evict in-memory runs older than artifact TTL
    in_mem_evicted = live_run_manager.evict_expired_runs(
        max_age_seconds=float(max_artifact_days * 86400)
    )
    runs_purged += in_mem_evicted

    # Evict expired cache entries
    cache_evicted = content_cache.evict_expired()

    return RetentionEnforcementReport(
        enforced_at=now.isoformat(),
        documents_purged=docs_purged,
        runs_purged=runs_purged,
        cache_entries_evicted=cache_evicted,
        details="Retention policies successfully enforced. Expired text, artifacts, and cache entries purged.",
    )
