"""Failure classification, selective retries, failure isolation, and partial run tracking (Fix 36).

Provides deterministic failure classification and resilience rules:
- One failed source must NEVER destroy the entire analysis.
- Each source maintains independent state and diagnostics.
- Retries are applied strictly to appropriate transient failure classes:
    * timeout -> retry (transient)
    * 429 rate limit -> backoff/retry (transient)
    * 403 / login gate -> terminal access_restricted (never retried)
    * invalid URL -> terminal invalid_url (never retried)
    * DNS private-IP resolution -> terminal security_blocked (never retried)
    * parser failure -> retain fetched receipt and terminal parser_error (never retried)
- When any source fails, runs terminate in PARTIAL state with precise missing pieces.
"""

from enum import Enum
import time
from typing import Any, Mapping, Sequence


class FailureClass(str, Enum):
    """Canonical taxonomy of source failure classes."""

    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    ACCESS_RESTRICTED = "access_restricted"
    INVALID_URL = "invalid_url"
    SECURITY_BLOCKED = "security_blocked"
    PARSER_ERROR = "parser_error"
    TOO_LARGE = "too_large"
    UNAVAILABLE = "unavailable"
    DEFERRED = "deferred"
    NOT_SELECTED = "not_selected"


RETRYABLE_STATUSES: set[str] = {
    FailureClass.TIMEOUT.value,
    FailureClass.RATE_LIMITED.value,
    "transient_network_error",
}

TERMINAL_STATUSES: set[str] = {
    FailureClass.ACCESS_RESTRICTED.value,
    FailureClass.INVALID_URL.value,
    FailureClass.SECURITY_BLOCKED.value,
    FailureClass.PARSER_ERROR.value,
    FailureClass.TOO_LARGE.value,
    FailureClass.DEFERRED.value,
    FailureClass.NOT_SELECTED.value,
}


def is_retryable_status(status: str) -> bool:
    """Returns True if the failure status belongs to an appropriate retryable class."""
    return status.lower() in RETRYABLE_STATUSES


def classify_http_failure(
    status_code: int,
    headers: Mapping[str, str] | None = None,
) -> tuple[str, str, bool, float]:
    """Classifies an HTTP response code into canonical failure status, detail, retryability, and backoff delay.

    Returns:
        (status_str, detail_str, is_retryable, backoff_seconds)
    """
    headers = headers or {}
    if status_code == 429:
        retry_after = headers.get("retry-after")
        backoff = 0.5
        if retry_after and retry_after.isdigit():
            backoff = min(5.0, max(0.2, float(retry_after)))
        return (
            FailureClass.RATE_LIMITED.value,
            "Public source rate limit reached (HTTP 429).",
            True,
            backoff,
        )
    if status_code in (401, 403, 999):
        return (
            FailureClass.ACCESS_RESTRICTED.value,
            f"Login, authentication, or provider gate prevents public inspection (HTTP {status_code}).",
            False,
            0.0,
        )
    if status_code == 404:
        return (
            FailureClass.UNAVAILABLE.value,
            "Public source not found (HTTP 404).",
            False,
            0.0,
        )
    if 500 <= status_code < 600:
        return (
            FailureClass.UNAVAILABLE.value,
            f"Upstream provider returned server error (HTTP {status_code}).",
            True,
            0.5,
        )
    return (
        FailureClass.UNAVAILABLE.value,
        f"Public source returned HTTP {status_code}.",
        False,
        0.0,
    )


def extract_missing_pieces(
    sources: Sequence[Mapping[str, Any]],
    *,
    time_exhausted: bool = False,
    has_evidence: bool = True,
) -> list[dict[str, Any]]:
    """Constructs a deterministic list of missing sources and failure reasons for PARTIAL runs."""
    missing: list[dict[str, Any]] = []

    for s in sources:
        st = str(s.get("status", "unknown")).lower()
        if st not in ("observed", "completed"):
            missing.append({
                "source": s.get("url", s.get("name", "unknown_source")),
                "kind": s.get("kind", "source"),
                "status": st,
                "detail": s.get("detail", "Source was not observed or incomplete."),
                "is_retryable": is_retryable_status(st),
            })

    if time_exhausted:
        missing.append({
            "source": "analysis_pipeline",
            "kind": "system",
            "status": FailureClass.TIMEOUT.value,
            "detail": "Wall-clock time budget reached before all stages completed.",
            "is_retryable": True,
        })

    if not has_evidence:
        missing.append({
            "source": "evidence_collection",
            "kind": "evidence",
            "status": "zero_evidence",
            "detail": "No empirical technical evidence was observed across the supplied sources.",
            "is_retryable": False,
        })

    return missing
