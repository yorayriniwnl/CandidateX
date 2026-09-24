"""Unit tests for Centralized System Limits and Hard Security Ceilings (Fix 34)."""

from fastapi.testclient import TestClient

from cci.limits import (
    DEFAULT_ACQUISITION_SECONDS,
    DEFAULT_LINK_TIMEOUT_SECONDS,
    DEFAULT_MAX_FILES_PER_REPO,
    DEFAULT_MAX_PAGE_BYTES,
    DEFAULT_MAX_PDF_PAGES,
    DEFAULT_MAX_REPOSITORIES,
    DEFAULT_MAX_RESUME_PAGES,
    DEFAULT_MAX_TEXT_CHARS,
    DEFAULT_MAX_UPLOAD_BYTES,
    DEFAULT_MAX_URLS,
    HARD_CEILING_ACQUISITION_SECONDS,
    HARD_CEILING_LINK_TIMEOUT_SECONDS,
    HARD_CEILING_MAX_FILES_PER_REPO,
    HARD_CEILING_MAX_PAGE_BYTES,
    HARD_CEILING_MAX_PDF_PAGES,
    HARD_CEILING_MAX_REPOSITORIES,
    HARD_CEILING_MAX_RESUME_PAGES,
    HARD_CEILING_MAX_TEXT_CHARS,
    HARD_CEILING_MAX_UPLOAD_BYTES,
    HARD_CEILING_MAX_URLS,
    LimitSpec,
    SystemLimits,
    get_system_limits,
)
from cci.live_app import app as live_app
from cci.main import app as main_app
import cci.live.contracts as live_contracts
import cci.live.public_links as live_public_links
import cci.live.web_discovery as live_web_discovery


def test_system_limits_operational_defaults():
    """Verifies that all 10 centralized limit dimensions possess correct operational defaults."""
    limits = get_system_limits()
    assert limits.max_urls.default == 24
    assert limits.max_urls.budget == 24
    assert limits.max_repositories.default == 6
    assert limits.max_repositories.budget == 6
    assert limits.max_files_per_repo.default == 100
    assert limits.max_files_per_repo.budget == 100
    assert limits.link_timeout_seconds.default == 20
    assert limits.link_timeout_seconds.budget == 20
    assert limits.acquisition_budget_seconds.default == 45
    assert limits.acquisition_budget_seconds.budget == 45
    assert limits.max_page_bytes.default == 512 * 1024
    assert limits.max_page_bytes.budget == 512 * 1024
    assert limits.max_text_chars.default == 12000
    assert limits.max_text_chars.budget == 12000
    assert limits.max_pdf_pages.default == 5
    assert limits.max_pdf_pages.budget == 5
    assert limits.max_resume_pages.default == 30
    assert limits.max_resume_pages.budget == 30
    assert limits.max_upload_bytes.default == 3 * 1024 * 1024
    assert limits.max_upload_bytes.budget == 3 * 1024 * 1024


def test_hard_security_ceilings_enforcement():
    """Verifies that user input can NEVER exceed the hard security ceilings."""
    limits = get_system_limits()

    # User input requesting excessive values must be clamped to hard_maximum
    assert limits.max_urls.clamp_requested(10_000) == HARD_CEILING_MAX_URLS
    assert limits.max_urls.clamp_requested(HARD_CEILING_MAX_URLS + 1) == HARD_CEILING_MAX_URLS
    assert limits.max_repositories.clamp_requested(999) == HARD_CEILING_MAX_REPOSITORIES
    assert limits.max_files_per_repo.clamp_requested(5000) == HARD_CEILING_MAX_FILES_PER_REPO
    assert limits.link_timeout_seconds.clamp_requested(3600) == HARD_CEILING_LINK_TIMEOUT_SECONDS
    assert limits.acquisition_budget_seconds.clamp_requested(3600) == HARD_CEILING_ACQUISITION_SECONDS
    assert limits.max_page_bytes.clamp_requested(100 * 1024 * 1024) == HARD_CEILING_MAX_PAGE_BYTES
    assert limits.max_text_chars.clamp_requested(1_000_000) == HARD_CEILING_MAX_TEXT_CHARS
    assert limits.max_pdf_pages.clamp_requested(100) == HARD_CEILING_MAX_PDF_PAGES
    assert limits.max_resume_pages.clamp_requested(500) == HARD_CEILING_MAX_RESUME_PAGES
    assert limits.max_upload_bytes.clamp_requested(500 * 1024 * 1024) == HARD_CEILING_MAX_UPLOAD_BYTES

    # Default / None request returns the active budget
    assert limits.max_urls.clamp_requested(None) == limits.max_urls.budget

    # Non-positive input is clamped to hard_minimum
    assert limits.max_urls.clamp_requested(0) == limits.max_urls.hard_minimum
    assert limits.max_urls.clamp_requested(-50) == limits.max_urls.hard_minimum


def test_environment_configuration_ceiling_protection():
    """Verifies that environment configuration can adjust budgets, but cannot exceed security ceilings."""
    class MockExcessiveSettings:
        LIMIT_MAX_URLS = 99999
        LIMIT_MAX_REPOSITORIES = 100
        LIMIT_MAX_FILES_PER_REPO = 1000
        LIMIT_LINK_TIMEOUT_SECONDS = 300
        LIMIT_ACQUISITION_SECONDS = 600
        LIMIT_MAX_PAGE_BYTES = 50 * 1024 * 1024
        LIMIT_MAX_TEXT_CHARS = 100_000
        LIMIT_MAX_PDF_PAGES = 50
        LIMIT_MAX_RESUME_PAGES = 500
        LIMIT_MAX_UPLOAD_BYTES = 100 * 1024 * 1024
        LIMIT_MAX_REQUEST_BYTES = 50 * 1024 * 1024

    clamped_limits = get_system_limits(MockExcessiveSettings())
    assert clamped_limits.max_urls.budget == HARD_CEILING_MAX_URLS
    assert clamped_limits.max_repositories.budget == HARD_CEILING_MAX_REPOSITORIES
    assert clamped_limits.max_files_per_repo.budget == HARD_CEILING_MAX_FILES_PER_REPO
    assert clamped_limits.link_timeout_seconds.budget == HARD_CEILING_LINK_TIMEOUT_SECONDS
    assert clamped_limits.acquisition_budget_seconds.budget == HARD_CEILING_ACQUISITION_SECONDS
    assert clamped_limits.max_page_bytes.budget == HARD_CEILING_MAX_PAGE_BYTES
    assert clamped_limits.max_text_chars.budget == HARD_CEILING_MAX_TEXT_CHARS
    assert clamped_limits.max_pdf_pages.budget == HARD_CEILING_MAX_PDF_PAGES
    assert clamped_limits.max_resume_pages.budget == HARD_CEILING_MAX_RESUME_PAGES
    assert clamped_limits.max_upload_bytes.budget == HARD_CEILING_MAX_UPLOAD_BYTES


def test_user_visible_explanations():
    """Verifies that human-readable explanations are generated without drift."""
    limits = get_system_limits()
    explanations = limits.get_user_visible_explanations()
    assert len(explanations) >= 3
    assert any("Public links: up to 24" in exp for exp in explanations)
    assert any("Bounded scan: 6 repositories, 100" in exp for exp in explanations)
    assert any("Document preview bounded to 12,000" in exp for exp in explanations)

    # Every individual limit must have an explanation
    d = limits.to_dict()
    for name, spec in d.items():
        assert len(spec["user_visible_explanation"]) > 20
        assert spec["unit"] != ""


def test_module_constants_derived_from_limits():
    """Verifies that live modules derive their boundary constants from centralized limits."""
    limits = get_system_limits()

    # contracts.py
    assert live_contracts.MAX_UPLOAD == limits.max_upload_bytes.budget
    assert live_contracts.MAX_REPOSITORIES == limits.max_repositories.budget
    assert live_contracts.MAX_FILES == limits.max_files_per_repo.budget
    assert live_contracts.MAX_SECONDS == limits.acquisition_budget_seconds.budget
    assert live_contracts.MAX_ANALYSIS_REQUEST_BYTES == limits.max_analysis_request_bytes.budget

    # public_links.py
    assert live_public_links.MAX_LINKS == limits.max_urls.budget
    assert live_public_links.MAX_BYTES == limits.max_page_bytes.budget
    assert live_public_links.LINK_SECONDS == limits.link_timeout_seconds.budget

    # web_discovery.py
    assert live_web_discovery.MAX_DISCOVERY_FETCHED == limits.max_urls.budget
    assert live_web_discovery.MAX_PAGE_BYTES == limits.max_page_bytes.budget


def test_system_limits_api_endpoints():
    """Verifies that system limits are accessible via HTTP REST endpoints."""
    # main app
    client_main = TestClient(main_app)
    resp_main = client_main.get("/api/v1/system/limits")
    assert resp_main.status_code == 200
    data_main = resp_main.json()
    assert "limits" in data_main
    assert "explanations" in data_main
    assert data_main["limits"]["max_urls"]["budget"] == 24
    assert data_main["limits"]["max_urls"]["hard_maximum"] == HARD_CEILING_MAX_URLS

    # live app
    client_live = TestClient(live_app)
    resp_live = client_live.get("/api/v1/system/limits")
    assert resp_live.status_code == 200
    data_live = resp_live.json()
    assert data_live["limits"]["max_repositories"]["budget"] == 6
    assert data_live["limits"]["max_repositories"]["hard_maximum"] == HARD_CEILING_MAX_REPOSITORIES
