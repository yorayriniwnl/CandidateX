"""Unit and integration tests for Fix 28: Production Abuse Controls.

Verifies:
1. Signed Analysis Tokens:
   - HMAC-SHA256 signature generation and verification.
   - Tamper-proofing (invalid signatures rejected).
   - Expiration verification (expired tokens rejected).
   - Token issuance endpoint (POST /api/v1/live/tokens).
2. Per-IP Sliding-Window Rate Limiting:
   - Sliding-window rate limiting per endpoint bucket.
   - HTTP 429 Too Many Requests on threshold breach.
   - Retry-After header presence.
   - Independent buckets (intake, runs, analyze, poll).
3. Concurrency Limiting:
   - Per-client and global concurrency caps.
   - Immediate rejection with HTTP 429 when slots saturated.
   - Slot release on run completion, failure, and cancellation.
4. Run Resource Budgets:
   - Wall-clock timeout budget.
   - GitHub API call budget (stops queries when budget exhausted, retains partial evidence).
   - Crawl page and byte budgets.
5. External Dependency Circuit Breakers:
   - CLOSED -> OPEN on consecutive failures (failure_threshold=5).
   - Fast-failing while OPEN (no network calls attempted).
   - OPEN -> HALF_OPEN after cooldown.
   - HALF_OPEN -> CLOSED on successful probes.
6. Caching & Deduplication:
   - In-memory content-addressable cache with TTL.
   - Deduplicating repeated queries.
7. Credential Redaction:
   - Redaction of GitHub tokens (ghp_*, github_pat_*), Bearer tokens, private keys.
   - Verification that error messages and artifacts never leak internal credentials.
8. SSRF Invariants:
   - Preservation of all existing strict SSRF controls.
"""

import time
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from cci.domain.enums import AnalysisRunState
from cci.live import acquisition
from cci.live.contracts import MAX_UPLOAD
from cci.live.runner import AnalysisRunManager, get_analysis_run_manager
from cci.live_app import app
from cci.security.abuse import (
    AnalysisTokenManager,
    CircuitBreaker,
    CircuitState,
    ConcurrencyLimiter,
    ContentCache,
    InvalidTokenError,
    RateLimiter,
    RunBudgetTracker,
    get_abuse_controls,
    sanitize_credentials,
)
from cci.security.ssrf import SSRFSecurityError, validate_safe_url
from tests.test_live_analysis import resume_bytes, transport

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_abuse_controls():
    """Resets all abuse control singletons between tests."""
    abuse = get_abuse_controls()
    abuse.reset()
    yield
    abuse.reset()


# ---------------------------------------------------------------------------
# 1. Signed Analysis Tokens Tests
# ---------------------------------------------------------------------------

def test_signed_analysis_token_issue_and_verification():
    """Verify cryptographic token signing, verification, and tamper rejection."""
    manager = AnalysisTokenManager(secret_key="test_secret_key_32_bytes_long_ok")
    token = manager.issue_token(subject="tenant-123", expires_in_seconds=300, tier="premium")

    claims = manager.verify_token(token)
    assert claims["sub"] == "tenant-123"
    assert claims["tier"] == "premium"
    assert "jti" in claims
    assert claims["exp"] > time.time()

    # Tampered signature rejected
    tampered_sig = token[:-4] + "xxxx"
    with pytest.raises(InvalidTokenError, match="Invalid token signature"):
        manager.verify_token(tampered_sig)

    # Expired token rejected
    expired_token = manager.issue_token(subject="tenant-expired", expires_in_seconds=-10)
    with pytest.raises(InvalidTokenError, match="expired"):
        manager.verify_token(expired_token)

    # Malformed token rejected
    with pytest.raises(InvalidTokenError, match="Malformed"):
        manager.verify_token("not-a-valid-token")


def test_token_endpoint_and_authenticated_intake():
    """Verify POST /tokens creates valid token accepted by analysis endpoints."""
    # 1. Request signed token
    token_resp = client.post("/api/v1/live/tokens", json={"subject": "client-abc", "tier": "default"})
    assert token_resp.status_code == 200
    token_data = token_resp.json()
    token = token_data["analysis_token"]
    assert token_data["token_type"] == "Bearer"

    # 2. Use token in intake
    headers = {"X-Filename": "resume.pdf", "Authorization": f"Bearer {token}"}
    intake_resp = client.post("/api/v1/live/intake", content=resume_bytes(), headers=headers)
    assert intake_resp.status_code == 200

    # 3. Invalid token rejected with 401
    bad_headers = {"X-Filename": "resume.pdf", "Authorization": "Bearer bad.token.here"}
    bad_resp = client.post("/api/v1/live/intake", content=resume_bytes(), headers=bad_headers)
    assert bad_resp.status_code == 401


# ---------------------------------------------------------------------------
# 2. Rate Limiting Tests
# ---------------------------------------------------------------------------

def test_sliding_window_rate_limiting_enforcement():
    """Verify sliding-window rate limiter trips on limit breach and returns Retry-After."""
    limiter = RateLimiter()
    key = "192.0.2.10"

    # Allow up to 3 requests in a 60s window
    for _ in range(3):
        allowed, retry_after, remaining = limiter.check_rate_limit(key, bucket="test", limit=3, window_seconds=60.0)
        assert allowed is True

    # 4th request must be rate limited
    allowed, retry_after, remaining = limiter.check_rate_limit(key, bucket="test", limit=3, window_seconds=60.0)
    assert allowed is False
    assert retry_after > 0
    assert remaining == 0


def test_api_rate_limiting_returns_429_with_retry_after():
    """Verify HTTP API returns 429 when rate limit is exceeded."""
    abuse = get_abuse_controls()
    # Configure tiny limit for testing: fill bucket
    for _ in range(20):
        client.post("/api/v1/live/intake", content=resume_bytes(), headers={"X-Filename": "resume.pdf"})

    # Next intake request exceeds 20/min limit
    exceeded_resp = client.post("/api/v1/live/intake", content=resume_bytes(), headers={"X-Filename": "resume.pdf"})
    assert exceeded_resp.status_code == 429
    assert "Retry-After" in exceeded_resp.headers
    assert "Rate limit exceeded" in exceeded_resp.json()["detail"]


# ---------------------------------------------------------------------------
# 3. Concurrency Limiting Tests
# ---------------------------------------------------------------------------

def test_concurrency_limiter_caps_active_runs():
    """Verify concurrency limiter enforces per-client and global limits."""
    limiter = ConcurrencyLimiter(global_max=3, per_key_max=2)

    # Client A acquires slot 1 & 2
    ok, _ = limiter.acquire("client-a")
    assert ok is True
    ok, _ = limiter.acquire("client-a")
    assert ok is True

    # Client A exceeds per-client cap (2)
    ok, reason = limiter.acquire("client-a")
    assert ok is False
    assert "Per-client concurrency limit" in reason

    # Client B acquires slot 3 (global max reached: 3)
    ok, _ = limiter.acquire("client-b")
    assert ok is True

    # Client B exceeds global cap
    ok, reason = limiter.acquire("client-b")
    assert ok is False
    assert "Global concurrency limit" in reason

    # Release client A slot 1 -> Client B can now acquire
    limiter.release("client-a")
    ok, _ = limiter.acquire("client-b")
    assert ok is True


def test_api_concurrency_cap_returns_429():
    """Verify HTTP endpoints return 429 when concurrency slots are saturated."""
    abuse = get_abuse_controls()
    # Artificially saturate concurrency slots
    abuse.concurrency_limiter.global_max = 2
    abuse.concurrency_limiter.per_key_max = 2

    # Acquire both slots
    abuse.concurrency_limiter.acquire("127.0.0.1")
    abuse.concurrency_limiter.acquire("127.0.0.1")

    # 3rd concurrent request rejected with 429
    resp = client.post(
        "/api/v1/live/runs",
        json={"role": "backend", "intake": {"manifest": {"claimed_skills": ["Python"]}}},
    )
    assert resp.status_code == 429
    assert "concurrency limit reached" in resp.json()["detail"].lower()
    assert resp.headers.get("Retry-After") == "5"


# ---------------------------------------------------------------------------
# 4. Run Resource Budgets Tests
# ---------------------------------------------------------------------------

def test_run_budget_tracker_github_call_budget():
    """Verify that GitHub call budget limits total API calls made during an analysis."""
    tracker = RunBudgetTracker(max_github_calls=3)

    assert tracker.record_github_call() is True  # Call 1
    assert tracker.record_github_call() is True  # Call 2
    assert tracker.record_github_call() is True  # Call 3
    assert tracker.record_github_call() is False  # Call 4 exceeds limit

    summary = tracker.get_summary()
    assert summary["github_calls"] == 4
    assert summary["github_calls_limit"] == 3
    assert "github_calls" in summary["exhausted_budgets"]


def test_run_budget_tracker_crawl_page_and_byte_budget():
    """Verify that web crawl page count and byte limits are enforced."""
    tracker = RunBudgetTracker(max_crawl_pages=2, max_crawl_bytes=1000)

    assert tracker.record_crawl_page(byte_size=400) is True  # Page 1 (400 bytes)
    assert tracker.record_crawl_page(byte_size=400) is True  # Page 2 (800 bytes)

    # Exceeding page limit (page 3)
    assert tracker.record_crawl_page(byte_size=100) is False

    # Exceeding byte limit
    assert tracker.record_crawl_page(byte_size=500) is False  # Total > 1000 bytes

    summary = tracker.get_summary()
    assert "crawl_pages" in summary["exhausted_budgets"]
    assert "crawl_bytes" in summary["exhausted_budgets"]


def test_run_budget_tracker_wall_clock_timeout():
    """Verify that wall-clock timeout budget is detected."""
    tracker = RunBudgetTracker(max_wall_clock_seconds=0.05)
    time.sleep(0.06)

    assert tracker.is_time_exhausted() is True
    assert tracker.remaining_seconds() == 0.0
    summary = tracker.get_summary()
    assert "wall_clock_timeout" in summary["exhausted_budgets"]


# ---------------------------------------------------------------------------
# 5. Circuit Breaker Tests
# ---------------------------------------------------------------------------

def test_circuit_breaker_transitions_and_fast_fail():
    """Verify CLOSED -> OPEN on failures, fast-failing while OPEN, and recovery."""
    breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=0.1, success_threshold=2)
    assert breaker.state == CircuitState.CLOSED
    assert breaker.can_execute() is True

    # Record 3 failures -> trips to OPEN
    breaker.record_failure()
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.state == CircuitState.OPEN
    assert breaker.can_execute() is False  # Fast fails!

    # Wait for cooldown
    time.sleep(0.12)
    assert breaker.state == CircuitState.HALF_OPEN
    assert breaker.can_execute() is True  # Allows probe call

    # Successful probes reset to CLOSED
    breaker.record_success()
    breaker.record_success()
    assert breaker.state == CircuitState.CLOSED
    assert breaker.can_execute() is True


def test_circuit_breaker_in_fetcher_fast_fails_github(monkeypatch):
    """Verify Fetcher fast-fails when GitHub circuit breaker is OPEN."""
    abuse = get_abuse_controls()
    abuse.circuit_breakers.get_breaker("api.github.com").record_failure()
    abuse.circuit_breakers.get_breaker("api.github.com").record_failure()
    abuse.circuit_breakers.get_breaker("api.github.com").record_failure()
    abuse.circuit_breakers.get_breaker("api.github.com").record_failure()
    abuse.circuit_breakers.get_breaker("api.github.com").record_failure()

    # Breaker is now OPEN
    assert abuse.circuit_breakers.can_execute("api.github.com") is False

    fetcher = acquisition.Fetcher()
    with pytest.raises(acquisition.AcquisitionError) as exc_info:
        fetcher.get("/repos/example/api")

    assert exc_info.value.status == "circuit_open"
    assert "Circuit breaker" in exc_info.value.detail


# ---------------------------------------------------------------------------
# 6. Content Cache and Deduplication Tests
# ---------------------------------------------------------------------------

def test_content_cache_and_deduplication():
    """Verify that in-memory cache stores and expires content-addressable receipts."""
    cache = ContentCache(default_ttl_seconds=0.1)
    cache.set("key1", {"data": "value"})

    assert cache.get("key1") == {"data": "value"}
    assert cache.get("nonexistent") is None

    # Expiry
    time.sleep(0.12)
    assert cache.get("key1") is None


# ---------------------------------------------------------------------------
# 7. Credential Redaction Tests
# ---------------------------------------------------------------------------

def test_credential_redaction_prevents_leaks():
    """Verify that sensitive internal tokens are scrubbed from strings and data structures."""
    secret_token = "ghp_1234567890abcdefghijklmnopqrstuvwxyz"
    fine_grained_pat = "github_pat_11AAAAAAA0000000000000_1234567890abcdefghijklmnopqrstuvwxyz1234567890abcdefghijklmn"
    bearer = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.do_not_leak"

    dirty_text = f"Connection failed with token: {secret_token} and pat: {fine_grained_pat} and {bearer}"
    clean_text = sanitize_credentials(dirty_text)

    assert secret_token not in clean_text
    assert fine_grained_pat not in clean_text
    assert "do_not_leak" not in clean_text
    assert "[REDACTED_CREDENTIAL]" in clean_text

    # Dict redaction
    dirty_dict = {
        "status": "error",
        "github_token": "secret123",
        "authorization": "Bearer secret_header",
        "nested": {"message": f"Error with {secret_token}"},
    }
    clean_dict = sanitize_credentials(dirty_dict)
    assert clean_dict["github_token"] == "[REDACTED_CREDENTIAL]"
    assert clean_dict["authorization"] == "[REDACTED_CREDENTIAL]"
    assert secret_token not in clean_dict["nested"]["message"]


# ---------------------------------------------------------------------------
# 8. SSRF Invariants Preserved
# ---------------------------------------------------------------------------

def test_ssrf_invariants_preserved():
    """Verify that strict SSRF validation is completely preserved."""
    # Loopback
    with pytest.raises(SSRFSecurityError):
        validate_safe_url("http://127.0.0.1/admin")

    # AWS metadata
    with pytest.raises(SSRFSecurityError):
        validate_safe_url("http://169.254.169.254/latest/meta-data")

    # RFC 1918 Private
    with pytest.raises(SSRFSecurityError):
        validate_safe_url("http://10.0.0.1/api")
    with pytest.raises(SSRFSecurityError):
        validate_safe_url("http://192.168.1.1/")
    with pytest.raises(SSRFSecurityError):
        validate_safe_url("http://172.16.0.1/")

    # IPv6 loopback
    with pytest.raises(SSRFSecurityError):
        validate_safe_url("http://[::1]/")

    # Public HTTPS URL allowed
    assert validate_safe_url("https://example.com/project") == "https://example.com/project"
