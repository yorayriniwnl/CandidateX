"""Centralized system limits, operational budgets, and immutable security ceilings (Fix 34).

Centralizes all previously scattered boundary constants across the platform:
- 24 URLs (public link inspection and web discovery)
- 6 repositories (bounded scan per candidate)
- 100 files (source code selection per repository)
- 20 seconds (per-link fetch timeout)
- 45 seconds (acquisition phase wall-clock budget)
- 512 KB (per-page download and JSON request body limit)
- 12,000 characters (document excerpt and preview truncation)
- 5 PDF pages (public certificate and document page limit)
- 30 PDF pages (resume upload page limit)
- 3 MB (resume file upload payload limit)

Enforces:
1. Operational defaults.
2. Hard security maximums (ceilings) that can NEVER be bypassed by user input or request payload.
3. Configurable per-run budgets (clamped within [minimum, hard_maximum]).
4. User-visible explanations explaining the rationale and scope of each limit.
"""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Immutable Security Ceilings (Hard Maximums)
# ---------------------------------------------------------------------------
HARD_CEILING_MAX_URLS: int = 48
HARD_CEILING_MAX_REPOSITORIES: int = 12
HARD_CEILING_MAX_FILES_PER_REPO: int = 250
HARD_CEILING_LINK_TIMEOUT_SECONDS: int = 30
HARD_CEILING_ACQUISITION_SECONDS: int = 60
HARD_CEILING_MAX_PAGE_BYTES: int = 1024 * 1024  # 1 MB
HARD_CEILING_MAX_TEXT_CHARS: int = 24000
HARD_CEILING_MAX_PDF_PAGES: int = 10
HARD_CEILING_MAX_RESUME_PAGES: int = 50
HARD_CEILING_MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024  # 10 MB
HARD_CEILING_MAX_REQUEST_BYTES: int = 1024 * 1024  # 1 MB

# ---------------------------------------------------------------------------
# Operational Defaults
# ---------------------------------------------------------------------------
DEFAULT_MAX_URLS: int = 24
DEFAULT_MAX_REPOSITORIES: int = 6
DEFAULT_MAX_FILES_PER_REPO: int = 100
DEFAULT_LINK_TIMEOUT_SECONDS: int = 20
DEFAULT_ACQUISITION_SECONDS: int = 45
DEFAULT_MAX_PAGE_BYTES: int = 512 * 1024  # 512 KB
DEFAULT_MAX_TEXT_CHARS: int = 12000
DEFAULT_MAX_PDF_PAGES: int = 5
DEFAULT_MAX_RESUME_PAGES: int = 30
DEFAULT_MAX_UPLOAD_BYTES: int = 3 * 1024 * 1024  # 3 MB
DEFAULT_MAX_REQUEST_BYTES: int = 512 * 1024  # 512 KB


class LimitSpec(BaseModel):
    """Specification of an individual system limit dimension."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(description="Canonical machine identifier for the limit")
    default: int = Field(description="Standard operational default value")
    hard_maximum: int = Field(description="Absolute immutable security ceiling")
    hard_minimum: int = Field(default=0, description="Absolute lower bound")
    budget: int = Field(description="Active per-run operational budget")
    unit: str = Field(description="Unit of measurement: pages, repositories, files, seconds, bytes, chars")
    user_visible_explanation: str = Field(description="User-facing rationale and scope explanation")

    def clamp_requested(self, requested: int | None) -> int:
        """Clamps any user-requested limit to ensure it never exceeds the hard security ceiling."""
        if requested is None:
            return self.budget
        try:
            val = int(requested)
        except (ValueError, TypeError):
            return self.budget
        return min(self.hard_maximum, max(self.hard_minimum, val))


class SystemLimits(BaseModel):
    """Aggregate model representing all centralized platform limits and active budgets."""

    model_config = ConfigDict(frozen=True)

    max_urls: LimitSpec
    max_repositories: LimitSpec
    max_files_per_repo: LimitSpec
    link_timeout_seconds: LimitSpec
    acquisition_budget_seconds: LimitSpec
    max_page_bytes: LimitSpec
    max_text_chars: LimitSpec
    max_pdf_pages: LimitSpec
    max_resume_pages: LimitSpec
    max_upload_bytes: LimitSpec
    max_analysis_request_bytes: LimitSpec

    def get_user_visible_explanations(self) -> list[str]:
        """Generates candidate- and interviewer-facing limitations text."""
        return [
            (
                f"Public links: up to {self.max_urls.budget} HTML/text/digital PDF pages, "
                f"{self.max_page_bytes.budget // 1024} KB each, 3 redirects; PDFs up to "
                f"{self.max_pdf_pages.budget} pages. Login gates, image-only and script-only pages remain unresolved."
            ),
            (
                f"Bounded scan: {self.max_repositories.budget} repositories, "
                f"{self.max_files_per_repo.budget} selected text files each, "
                f"{self.acquisition_budget_seconds.budget}s acquisition budget."
            ),
            (
                f"Document preview bounded to {self.max_text_chars.budget:,} characters; "
                f"resume uploads bounded to {self.max_resume_pages.budget} pages "
                f"({self.max_upload_bytes.budget // (1024 * 1024)} MB)."
            ),
            "Public page text, profile metadata and certificate mentions do not increase capability scores. Issuer authentication and employment verification are not automated.",
            "Candidate repository code is never executed; insights are static and operational.",
        ]

    def to_dict(self) -> dict[str, dict[str, Any]]:
        """Serializes all limit specifications into a structured dictionary."""
        return {
            "max_urls": self.max_urls.model_dump(),
            "max_repositories": self.max_repositories.model_dump(),
            "max_files_per_repo": self.max_files_per_repo.model_dump(),
            "link_timeout_seconds": self.link_timeout_seconds.model_dump(),
            "acquisition_budget_seconds": self.acquisition_budget_seconds.model_dump(),
            "max_page_bytes": self.max_page_bytes.model_dump(),
            "max_text_chars": self.max_text_chars.model_dump(),
            "max_pdf_pages": self.max_pdf_pages.model_dump(),
            "max_resume_pages": self.max_resume_pages.model_dump(),
            "max_upload_bytes": self.max_upload_bytes.model_dump(),
            "max_analysis_request_bytes": self.max_analysis_request_bytes.model_dump(),
        }


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return min(maximum, max(minimum, value))


def get_system_limits(cfg: Any | None = None) -> SystemLimits:
    """Constructs SystemLimits resolving active budgets from settings while enforcing immutable hard ceilings."""
    if cfg is None:
        try:
            from cci.config import settings
            cfg = settings
        except Exception:
            cfg = None

    def _get_budget(attr: str, default: int, hard_max: int, hard_min: int = 0) -> int:
        val = getattr(cfg, attr, default) if cfg is not None else default
        try:
            val_int = int(val)
        except (ValueError, TypeError):
            val_int = default
        # Enforce security ceiling: environment may adjust budget, but NEVER exceed hard ceiling
        return _clamp(val_int, hard_min, hard_max)

    urls_budget = _get_budget("LIMIT_MAX_URLS", DEFAULT_MAX_URLS, HARD_CEILING_MAX_URLS)
    repos_budget = _get_budget("LIMIT_MAX_REPOSITORIES", DEFAULT_MAX_REPOSITORIES, HARD_CEILING_MAX_REPOSITORIES)
    files_budget = _get_budget("LIMIT_MAX_FILES_PER_REPO", DEFAULT_MAX_FILES_PER_REPO, HARD_CEILING_MAX_FILES_PER_REPO)
    timeout_budget = _get_budget("LIMIT_LINK_TIMEOUT_SECONDS", DEFAULT_LINK_TIMEOUT_SECONDS, HARD_CEILING_LINK_TIMEOUT_SECONDS)
    acq_budget = _get_budget("LIMIT_ACQUISITION_SECONDS", DEFAULT_ACQUISITION_SECONDS, HARD_CEILING_ACQUISITION_SECONDS)
    bytes_budget = _get_budget("LIMIT_MAX_PAGE_BYTES", DEFAULT_MAX_PAGE_BYTES, HARD_CEILING_MAX_PAGE_BYTES)
    chars_budget = _get_budget("LIMIT_MAX_TEXT_CHARS", DEFAULT_MAX_TEXT_CHARS, HARD_CEILING_MAX_TEXT_CHARS)
    pdf_budget = _get_budget("LIMIT_MAX_PDF_PAGES", DEFAULT_MAX_PDF_PAGES, HARD_CEILING_MAX_PDF_PAGES)
    resume_budget = _get_budget("LIMIT_MAX_RESUME_PAGES", DEFAULT_MAX_RESUME_PAGES, HARD_CEILING_MAX_RESUME_PAGES)
    upload_budget = _get_budget("LIMIT_MAX_UPLOAD_BYTES", DEFAULT_MAX_UPLOAD_BYTES, HARD_CEILING_MAX_UPLOAD_BYTES)
    req_budget = _get_budget("LIMIT_MAX_REQUEST_BYTES", DEFAULT_MAX_REQUEST_BYTES, HARD_CEILING_MAX_REQUEST_BYTES)

    return SystemLimits(
        max_urls=LimitSpec(
            name="max_urls",
            default=DEFAULT_MAX_URLS,
            hard_maximum=HARD_CEILING_MAX_URLS,
            budget=urls_budget,
            unit="pages",
            user_visible_explanation="Public link inspection is limited to a bounded number of public pages per candidate analysis to prevent unbounded crawl abuse and denial of service.",
        ),
        max_repositories=LimitSpec(
            name="max_repositories",
            default=DEFAULT_MAX_REPOSITORIES,
            hard_maximum=HARD_CEILING_MAX_REPOSITORIES,
            budget=repos_budget,
            unit="repositories",
            user_visible_explanation="Repository analysis is bounded to a finite set of public repositories per candidate to guarantee predictable run latency and stay within API rate limits.",
        ),
        max_files_per_repo=LimitSpec(
            name="max_files_per_repo",
            default=DEFAULT_MAX_FILES_PER_REPO,
            hard_maximum=HARD_CEILING_MAX_FILES_PER_REPO,
            budget=files_budget,
            unit="files",
            user_visible_explanation="Static inspection selects relevant source files per repository to focus on core candidate implementations.",
        ),
        link_timeout_seconds=LimitSpec(
            name="link_timeout_seconds",
            default=DEFAULT_LINK_TIMEOUT_SECONDS,
            hard_maximum=HARD_CEILING_LINK_TIMEOUT_SECONDS,
            budget=timeout_budget,
            unit="seconds",
            user_visible_explanation="Public page HTTP retrieval is bounded by a per-link timeout to prevent hung network connections.",
        ),
        acquisition_budget_seconds=LimitSpec(
            name="acquisition_budget_seconds",
            default=DEFAULT_ACQUISITION_SECONDS,
            hard_maximum=HARD_CEILING_ACQUISITION_SECONDS,
            budget=acq_budget,
            unit="seconds",
            user_visible_explanation="Acquisition phase has an operational wall-clock budget to ensure responsive execution.",
        ),
        max_page_bytes=LimitSpec(
            name="max_page_bytes",
            default=DEFAULT_MAX_PAGE_BYTES,
            hard_maximum=HARD_CEILING_MAX_PAGE_BYTES,
            budget=bytes_budget,
            unit="bytes",
            user_visible_explanation="Individual public page and document downloads are capped to prevent memory exhaustion.",
        ),
        max_text_chars=LimitSpec(
            name="max_text_chars",
            default=DEFAULT_MAX_TEXT_CHARS,
            hard_maximum=HARD_CEILING_MAX_TEXT_CHARS,
            budget=chars_budget,
            unit="characters",
            user_visible_explanation="Document and public link text previews are truncated to prevent unbounded memory and database bloat.",
        ),
        max_pdf_pages=LimitSpec(
            name="max_pdf_pages",
            default=DEFAULT_MAX_PDF_PAGES,
            hard_maximum=HARD_CEILING_MAX_PDF_PAGES,
            budget=pdf_budget,
            unit="pages",
            user_visible_explanation="Public PDF documents (certificates, credentials) are restricted to the first pages to isolate relevant content from large publications.",
        ),
        max_resume_pages=LimitSpec(
            name="max_resume_pages",
            default=DEFAULT_MAX_RESUME_PAGES,
            hard_maximum=HARD_CEILING_MAX_RESUME_PAGES,
            budget=resume_budget,
            unit="pages",
            user_visible_explanation="Resume PDF uploads are capped to prevent denial-of-service via massive document payloads.",
        ),
        max_upload_bytes=LimitSpec(
            name="max_upload_bytes",
            default=DEFAULT_MAX_UPLOAD_BYTES,
            hard_maximum=HARD_CEILING_MAX_UPLOAD_BYTES,
            budget=upload_budget,
            unit="bytes",
            user_visible_explanation="Resume file upload payload is capped to ensure predictable transmission and processing.",
        ),
        max_analysis_request_bytes=LimitSpec(
            name="max_analysis_request_bytes",
            default=DEFAULT_MAX_REQUEST_BYTES,
            hard_maximum=HARD_CEILING_MAX_REQUEST_BYTES,
            budget=req_budget,
            unit="bytes",
            user_visible_explanation="Analysis JSON request bodies are bounded to prevent memory exhaustion and excessive payload transmission.",
        ),
    )
