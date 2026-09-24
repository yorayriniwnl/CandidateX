"""Production telemetry, execution metrics, and candidate-safe structured observability (Fix 35).

Records runtime performance and pipeline telemetry across all execution dimensions:
- analysis_run_duration
- stage_duration
- source_fetch_counts
- source_failure_reasons
- github_api_utilization
- crawl_budget_usage
- artifacts_scanned
- evidence_generated
- evidence_discarded (deduplication)
- coverage
- attribution_quality
- queue_delay
- retry_count
- failure_stage

Enforces:
- Absolute candidate privacy: never records or logs candidate-sensitive text or PII.
- Structured errors with deterministic error IDs, request IDs, and analysis run IDs.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import re
from typing import Any, Mapping, Sequence
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from cci.security.privacy import sanitize_sensitive_text

logger = logging.getLogger(__name__)


def _sanitize_telemetry_string(text: str | None) -> str | None:
    """Removes sensitive candidate information, tokens, and PII from telemetry messages."""
    if not text:
        return text
    # Strip auth tokens / secrets
    s = re.sub(r"(?:bearer\s+|token=)[a-zA-Z0-9_\-\.]{10,}", "[REDACTED_CREDENTIAL]", text, flags=re.I)
    # Strip candidate PII via central sanitizer
    s = sanitize_sensitive_text(s)
    # Truncate to safe length
    return s[:500]


class StructuredAnalysisError(BaseModel):
    """Structured, machine-readable error record tagged with run and request identifiers."""

    model_config = ConfigDict(frozen=True)

    error_id: str = Field(default_factory=lambda: f"err_{uuid4().hex[:12]}")
    analysis_run_id: str
    request_id: str | None = None
    stage: str | None = None
    error_code: str = "PIPELINE_ERROR"
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def create(
        cls,
        analysis_run_id: str | UUID,
        exc: Exception | str,
        *,
        request_id: str | None = None,
        stage: str | None = None,
        error_code: str = "EXECUTION_FAILURE",
        details: dict[str, Any] | None = None,
    ) -> "StructuredAnalysisError":
        raw_msg = str(exc)
        safe_msg = _sanitize_telemetry_string(raw_msg) or "An error occurred during pipeline execution."
        safe_details: dict[str, Any] = {}
        if details:
            for k, v in details.items():
                if isinstance(v, str):
                    safe_details[k] = _sanitize_telemetry_string(v)
                elif isinstance(v, (int, float, bool)):
                    safe_details[k] = v
                else:
                    safe_details[k] = _sanitize_telemetry_string(str(v))

        return cls(
            analysis_run_id=str(analysis_run_id),
            request_id=request_id,
            stage=stage,
            error_code=error_code,
            message=safe_msg,
            details=safe_details,
        )


class StageTelemetry(BaseModel):
    """Execution telemetry for a single discrete pipeline stage."""

    stage_name: str
    started_at: str
    completed_at: str | None = None
    duration_seconds: float = 0.0
    status: str = "pending"  # running, completed, failed, skipped
    artifacts_count: int = 0
    error: str | None = None


class RunTelemetry(BaseModel):
    """Comprehensive observability snapshot for a complete analysis execution."""

    analysis_run_id: str
    request_id: str | None = None
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    queue_delay_seconds: float = 0.0
    analysis_run_duration_seconds: float = 0.0
    stage_durations: dict[str, float] = Field(default_factory=dict)
    stages: dict[str, StageTelemetry] = Field(default_factory=dict)

    # Source acquisition metrics
    source_fetch_counts: dict[str, int] = Field(
        default_factory=lambda: {
            "total_attempted": 0,
            "fetched": 0,
            "failed": 0,
            "deferred": 0,
            "blocked": 0,
            "not_selected": 0,
        }
    )
    source_failure_reasons: dict[str, int] = Field(default_factory=dict)

    # Budget & API utilization
    github_api_utilization: dict[str, Any] = Field(
        default_factory=lambda: {
            "calls_made": 0,
            "call_budget": 50,
            "utilization_pct": 0.0,
            "rate_limited": False,
        }
    )
    crawl_budget_usage: dict[str, Any] = Field(
        default_factory=lambda: {
            "pages_fetched": 0,
            "pages_budget": 24,
            "bytes_downloaded": 0,
            "bytes_budget": 5242880,
            "utilization_pct": 0.0,
        }
    )

    # Processing & Evidence Metrics
    artifacts_scanned: int = 0
    evidence_generated: int = 0
    evidence_discarded: int = 0
    coverage: float | None = None
    attribution_quality: dict[str, Any] = Field(
        default_factory=lambda: {
            "mean_confidence": 0.0,
            "attributed_count": 0,
            "ambiguous_count": 0,
        }
    )

    # Execution Outcome
    retry_count: int = 0
    failure_stage: str | None = None
    structured_error: dict[str, Any] | None = None

    def start_run(self, request_id: str | None = None) -> None:
        """Marks run start and records queue latency."""
        now = datetime.now(timezone.utc)
        self.started_at = now.isoformat()
        if request_id:
            self.request_id = request_id
        try:
            created = datetime.fromisoformat(self.created_at)
            self.queue_delay_seconds = max(0.0, round((now - created).total_seconds(), 4))
        except Exception:
            self.queue_delay_seconds = 0.0

    def start_stage(self, stage_name: str) -> None:
        """Starts timing an individual pipeline stage."""
        now = datetime.now(timezone.utc).isoformat()
        self.stages[stage_name] = StageTelemetry(
            stage_name=stage_name,
            started_at=now,
            status="running",
        )

    def complete_stage(self, stage_name: str, artifacts_count: int = 0) -> None:
        """Records stage completion and calculates elapsed duration."""
        now = datetime.now(timezone.utc)
        stage_rec = self.stages.get(stage_name)
        if stage_rec:
            stage_rec.completed_at = now.isoformat()
            stage_rec.status = "completed"
            stage_rec.artifacts_count = artifacts_count
            try:
                start_dt = datetime.fromisoformat(stage_rec.started_at)
                dur = max(0.0, round((now - start_dt).total_seconds(), 4))
            except Exception:
                dur = 0.0
            stage_rec.duration_seconds = dur
            self.stage_durations[stage_name] = dur

    def fail_stage(
        self,
        stage_name: str,
        exc: Exception | str,
        *,
        error_code: str = "STAGE_ERROR",
        details: dict[str, Any] | None = None,
    ) -> StructuredAnalysisError:
        """Records stage failure, generates a candidate-safe structured error, and finalizes stage telemetry."""
        now = datetime.now(timezone.utc)
        self.failure_stage = stage_name
        err = StructuredAnalysisError.create(
            analysis_run_id=self.analysis_run_id,
            exc=exc,
            request_id=self.request_id,
            stage=stage_name,
            error_code=error_code,
            details=details,
        )
        self.structured_error = err.model_dump()

        stage_rec = self.stages.get(stage_name)
        if stage_rec:
            stage_rec.completed_at = now.isoformat()
            stage_rec.status = "failed"
            stage_rec.error = err.message
            try:
                start_dt = datetime.fromisoformat(stage_rec.started_at)
                dur = max(0.0, round((now - start_dt).total_seconds(), 4))
            except Exception:
                dur = 0.0
            stage_rec.duration_seconds = dur
            self.stage_durations[stage_name] = dur

        return err

    def record_sources(self, sources: Sequence[Mapping[str, Any]]) -> None:
        """Analyzes source acquisition outcomes, updating fetch counts and categorized failure reasons."""
        counts = {
            "total_attempted": len(sources),
            "fetched": 0,
            "failed": 0,
            "deferred": 0,
            "blocked": 0,
            "not_selected": 0,
        }
        reasons: dict[str, int] = {}
        total_bytes = 0

        for s in sources:
            st = s.get("status", "unknown")
            if st in ("observed", "fetched", "completed"):
                counts["fetched"] += 1
            elif st in ("deferred", "not_scanned"):
                counts["deferred"] += 1
            elif st in ("blocked", "security_blocked", "access_restricted"):
                counts["blocked"] += 1
            elif st in ("not_selected",):
                counts["not_selected"] += 1
            else:
                counts["failed"] += 1

            # Categorize failure reasons safely without leaking URLs or candidate details
            detail = s.get("detail", "")
            if detail and st not in ("observed", "fetched", "completed"):
                clean_reason = self._categorize_reason(detail)
                reasons[clean_reason] = reasons.get(clean_reason, 0) + 1

            # Accumulate bytes if recorded
            rcpt = s.get("receipt", {}) if isinstance(s.get("receipt"), dict) else s
            if "bytes_downloaded" in rcpt:
                total_bytes += int(rcpt.get("bytes_downloaded", 0))

        self.source_fetch_counts = counts
        self.source_failure_reasons = reasons
        pages_fetched = counts["fetched"]
        pages_budget = self.crawl_budget_usage.get("pages_budget", 24)
        bytes_budget = self.crawl_budget_usage.get("bytes_budget", 5242880)

        self.crawl_budget_usage.update({
            "pages_fetched": pages_fetched,
            "bytes_downloaded": total_bytes,
            "utilization_pct": round((pages_fetched / max(1, pages_budget)) * 100.0, 2),
        })

    def _categorize_reason(self, detail: str) -> str:
        """Maps detailed failure text into high-level privacy-safe categorization categories."""
        d_lower = detail.lower()
        if "timeout" in d_lower or "budget" in d_lower:
            return "timeout_expired"
        if "404" in d_lower or "not found" in d_lower:
            return "http_not_found"
        if "401" in d_lower or "403" in d_lower or "login" in d_lower or "access restricted" in d_lower:
            return "access_restricted"
        if "429" in d_lower or "rate limit" in d_lower:
            return "rate_limit_exceeded"
        if "ssrf" in d_lower or "safety validation" in d_lower or "private" in d_lower:
            return "security_validation_blocked"
        if "too_large" in d_lower or "exceeds" in d_lower or "size" in d_lower:
            return "payload_size_limit_exceeded"
        if "encrypted" in d_lower:
            return "encrypted_document"
        if "unsupported" in d_lower:
            return "unsupported_content_type"
        return "unspecified_acquisition_failure"

    def record_github_usage(self, calls: int, budget: int = 50, rate_limited: bool = False) -> None:
        """Records GitHub API call consumption and budget utilization."""
        pct = round((calls / max(1, budget)) * 100.0, 2)
        self.github_api_utilization = {
            "calls_made": calls,
            "call_budget": budget,
            "utilization_pct": pct,
            "rate_limited": rate_limited,
        }

    def record_pipeline_metrics(
        self,
        dossier: Any,
        raw_evidence_count: int | None = None,
        artifacts_scanned: int = 0,
    ) -> None:
        """Extracts and computes final coverage, deduplication, and attribution metrics from dossier snapshot."""
        if artifacts_scanned > 0:
            self.artifacts_scanned = artifacts_scanned

        ev_records = getattr(dossier, "evidence_records", []) or []
        final_ev_count = len(ev_records)
        raw_count = raw_evidence_count if raw_evidence_count is not None else final_ev_count

        self.evidence_generated = raw_count
        self.evidence_discarded = max(0, raw_count - final_ev_count)
        self.coverage = getattr(dossier, "coverage", None)

        # Attribution quality assessment
        assocs = getattr(dossier, "repository_associations", []) or []
        ownerships = getattr(dossier, "ownership_assessments", []) or []
        all_attributions = [*assocs, *ownerships]

        confidences = []
        high_count = 0
        ambig_count = 0

        for att in all_attributions:
            conf = getattr(att, "ownership_score", getattr(att, "confidence", None))
            if conf is not None:
                confidences.append(float(conf))
                if float(conf) >= 0.70:
                    high_count += 1
                else:
                    ambig_count += 1

        mean_conf = round(sum(confidences) / len(confidences), 4) if confidences else 0.0
        self.attribution_quality = {
            "mean_confidence": mean_conf,
            "attributed_count": high_count,
            "ambiguous_count": ambig_count,
        }

    def increment_retry(self) -> None:
        """Increments the recorded retry counter."""
        self.retry_count += 1

    def finalize(self) -> None:
        """Calculates total run duration and closes the telemetry record."""
        now = datetime.now(timezone.utc)
        self.completed_at = now.isoformat()
        if self.started_at:
            try:
                start_dt = datetime.fromisoformat(self.started_at)
                self.analysis_run_duration_seconds = max(0.0, round((now - start_dt).total_seconds(), 4))
            except Exception:
                self.analysis_run_duration_seconds = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Returns the serialized telemetry record."""
        return self.model_dump()


def create_run_telemetry(analysis_run_id: str | UUID, request_id: str | None = None) -> RunTelemetry:
    """Factory creating an initialized RunTelemetry record."""
    now_iso = datetime.now(timezone.utc).isoformat()
    return RunTelemetry(
        analysis_run_id=str(analysis_run_id),
        request_id=request_id,
        created_at=now_iso,
    )
