"""Unit tests for Fix 36: Retries, Failure Classification, Failure Isolation, and Partial Run Tracking."""

import time
import httpx
import pytest

from cci.live.resilience import (
    FailureClass,
    classify_http_failure,
    extract_missing_pieces,
    is_retryable_status,
)
from cci.live.public_links import inspect_link
from cci.live.web_discovery import EvidenceDiscoveryFrontier


class MockTransport(httpx.BaseTransport):
    """Custom mock transport to simulate arbitrary HTTP sequences."""

    def __init__(self, responses: list[httpx.Response | Exception]):
        self.responses = list(responses)
        self.call_count = 0

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.call_count += 1
        if not self.responses:
            return httpx.Response(200, text="Fallback content with sufficient length for testing purposes.", request=request)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class TestFailureClassification:
    def test_classify_http_failure_429(self):
        status, detail, is_ret, backoff = classify_http_failure(429, {"retry-after": "2"})
        assert status == FailureClass.RATE_LIMITED.value
        assert is_ret is True
        assert backoff == 2.0

    def test_classify_http_failure_403(self):
        status, detail, is_ret, backoff = classify_http_failure(403)
        assert status == FailureClass.ACCESS_RESTRICTED.value
        assert is_ret is False
        assert backoff == 0.0

    def test_classify_http_failure_401(self):
        status, detail, is_ret, backoff = classify_http_failure(401)
        assert status == FailureClass.ACCESS_RESTRICTED.value
        assert is_ret is False

    def test_classify_http_failure_500(self):
        status, detail, is_ret, backoff = classify_http_failure(500)
        assert status == FailureClass.UNAVAILABLE.value
        assert is_ret is True

    def test_is_retryable_status(self):
        assert is_retryable_status("timeout") is True
        assert is_retryable_status("rate_limited") is True
        assert is_retryable_status("access_restricted") is False
        assert is_retryable_status("security_blocked") is False
        assert is_retryable_status("invalid_url") is False
        assert is_retryable_status("parser_error") is False
        assert is_retryable_status("too_large") is False

    def test_extract_missing_pieces(self):
        sources = [
            {"url": "https://example.com/ok", "status": "observed", "kind": "public_page"},
            {"url": "https://example.com/gate", "status": "access_restricted", "detail": "Login gate", "kind": "public_page"},
            {"url": "https://example.com/timeout", "status": "timeout", "detail": "Timed out", "kind": "public_page"},
        ]
        missing = extract_missing_pieces(sources, time_exhausted=True, has_evidence=False)
        assert len(missing) == 4
        # Source 1: gate
        assert missing[0]["source"] == "https://example.com/gate"
        assert missing[0]["status"] == "access_restricted"
        assert missing[0]["is_retryable"] is False

        # Source 2: timeout
        assert missing[1]["source"] == "https://example.com/timeout"
        assert missing[1]["status"] == "timeout"
        assert missing[1]["is_retryable"] is True

        # System timeout
        assert missing[2]["source"] == "analysis_pipeline"
        assert missing[2]["status"] == "timeout"
        assert missing[2]["is_retryable"] is True

        # Zero evidence
        assert missing[3]["source"] == "evidence_collection"
        assert missing[3]["status"] == "zero_evidence"
        assert missing[3]["is_retryable"] is False


class TestPublicLinksResilience:
    def test_rate_limited_429_retries_and_recovers(self):
        transport = MockTransport([
            httpx.Response(429, headers={"retry-after": "0"}, request=httpx.Request("GET", "http://example.com")),
            httpx.Response(200, headers={"content-type": "text/html"}, text="<html><head><title>Success</title></head><body>This is valid and long enough public text content.</body></html>", request=httpx.Request("GET", "http://example.com")),
        ])

        deadline = time.monotonic() + 10.0
        res = inspect_link("http://example.com", deadline, transport=transport)
        assert res["status"] == "observed"
        assert transport.call_count == 2

    def test_rate_limited_429_exhausted_becomes_terminal(self):
        transport = MockTransport([
            httpx.Response(429, headers={"retry-after": "0"}, request=httpx.Request("GET", "http://example.com")),
            httpx.Response(429, headers={"retry-after": "0"}, request=httpx.Request("GET", "http://example.com")),
            httpx.Response(429, headers={"retry-after": "0"}, request=httpx.Request("GET", "http://example.com")),
        ])

        deadline = time.monotonic() + 10.0
        res = inspect_link("http://example.com", deadline, transport=transport)
        assert res["status"] == "rate_limited"
        assert "429" in res["detail"]

    def test_access_restricted_403_never_retried(self):
        transport = MockTransport([
            httpx.Response(403, request=httpx.Request("GET", "http://example.com")),
            httpx.Response(200, text="Should never be called", request=httpx.Request("GET", "http://example.com")),
        ])

        deadline = time.monotonic() + 10.0
        res = inspect_link("http://example.com", deadline, transport=transport)
        assert res["status"] == "access_restricted"
        assert transport.call_count == 1

    def test_login_gate_detected_terminal_access_restricted(self):
        html = "<html><head><title>Sign in to continue</title></head><body>Please log in to continue accessing our secure candidate platform.</body></html>"
        transport = MockTransport([
            httpx.Response(200, headers={"content-type": "text/html"}, text=html, request=httpx.Request("GET", "http://example.com")),
        ])

        deadline = time.monotonic() + 10.0
        res = inspect_link("http://example.com", deadline, transport=transport)
        assert res["status"] == "access_restricted"
        assert "gate" in res["detail"]
        assert transport.call_count == 1

    def test_invalid_url_terminal(self):
        deadline = time.monotonic() + 10.0
        res = inspect_link("ftp://invalid-scheme.com", deadline)
        assert res["status"] == "invalid_url"
        assert "HTTP" in res["detail"]

    def test_ssrf_private_ip_terminal_security_blocked(self):
        deadline = time.monotonic() + 10.0
        res = inspect_link("http://127.0.0.1:8080/admin", deadline)
        assert res["status"] == "security_blocked"
        assert "public-network safety" in res["detail"]

    def test_parser_failure_retains_receipt(self):
        # Corrupt PDF that throws in pymupdf
        transport = MockTransport([
            httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"%PDF-1.4 corrupt junk", request=httpx.Request("GET", "http://example.com/doc.pdf")),
        ])

        deadline = time.monotonic() + 10.0
        res = inspect_link("http://example.com/doc.pdf", deadline, transport=transport)
        assert res["status"] == "parser_error"
        assert "content_sha256" in res
        assert transport.call_count == 1


class TestWebDiscoveryResilience:
    def test_web_discovery_429_retry_and_terminal(self):
        transport = MockTransport([
            httpx.Response(429, headers={"retry-after": "0"}, request=httpx.Request("GET", "https://example.com/page")),
            httpx.Response(429, headers={"retry-after": "0"}, request=httpx.Request("GET", "https://example.com/page")),
            httpx.Response(429, headers={"retry-after": "0"}, request=httpx.Request("GET", "https://example.com/page")),
        ])
        frontier = EvidenceDiscoveryFrontier(transport=transport, time_budget=5.0)
        frontier.add_url("https://example.com/page")
        items = frontier.run()

        item = items[0]
        assert item.fetch_status == "rate_limited"

    def test_web_discovery_403_access_restricted_terminal(self):
        transport = MockTransport([
            httpx.Response(403, request=httpx.Request("GET", "https://example.com/page")),
            httpx.Response(200, text="Never reached", request=httpx.Request("GET", "https://example.com/page")),
        ])
        frontier = EvidenceDiscoveryFrontier(transport=transport, time_budget=5.0)
        frontier.add_url("https://example.com/page")
        items = frontier.run()

        item = items[0]
        assert item.fetch_status == "inaccessible"
        assert transport.call_count == 1

    def test_web_discovery_parser_error_terminal(self):
        transport = MockTransport([
            httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"%PDF-bad data", request=httpx.Request("GET", "https://example.com/doc.pdf")),
        ])
        frontier = EvidenceDiscoveryFrontier(transport=transport, time_budget=5.0)
        frontier.add_url("https://example.com/doc.pdf")
        items = frontier.run()

        item = items[0]
        assert item.fetch_status == "parser_error"
        receipt = item.to_source_dict()
        assert receipt.get("content_sha256") is not None


class TestRunPartialFailureIsolation:
    def test_missing_pieces_attached_on_partial_run(self):
        from cci.live.runner import DurableAnalysisRun, AnalysisRunState
        from uuid import uuid4

        run = DurableAnalysisRun(
            analysis_run_id=uuid4(),
            target_role="backend",
        )
        sources = [
            {"url": "https://github.com/test/repo", "status": "observed", "kind": "repository"},
            {"url": "https://example.com/bad", "status": "access_restricted", "detail": "HTTP 403 Forbidden", "kind": "public_page"},
        ]
        missing = extract_missing_pieces(sources, time_exhausted=False, has_evidence=True)
        run.result = {"sources": sources, "missing_pieces": missing}
        run.state = AnalysisRunState.PARTIAL

        status = run.to_status_dict()
        assert status["state"] == "PARTIAL"
        assert len(status["missing_pieces"]) == 1
        assert status["missing_pieces"][0]["source"] == "https://example.com/bad"
        assert status["missing_pieces"][0]["is_retryable"] is False
