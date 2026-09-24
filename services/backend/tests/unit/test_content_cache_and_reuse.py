"""Unit tests for Fix 37: Content-Addressable Caching, Conditional Reuse, and Cross-Tenant Authorization Isolation."""

import time
from uuid import uuid4
import httpx
import pytest

from cci.cache import (
    ContentCache,
    get_content_cache,
)
from cci.live.public_links import inspect_link
from cci.live.web_discovery import EvidenceDiscoveryFrontier


class MockTransport(httpx.BaseTransport):
    def __init__(self, responses: list[httpx.Response]):
        self.responses = list(responses)
        self.call_count = 0

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.call_count += 1
        if not self.responses:
            return httpx.Response(200, text="Default test body text with sufficient length.", request=request)
        return self.responses.pop(0)


class TestContentCacheCore:
    def test_github_cache_by_repo_and_commit_sha(self):
        cache = ContentCache()
        repo = "octocat/Hello-World"
        sha = "7fd1a60b01f91b314f59955a4e4d4e80d8edf11d"
        data = b"ZIP_ARCHIVE_DATA_SAMPLE"

        entry = cache.put_github(repo, sha, data)
        assert entry.repo == repo.lower()
        assert entry.commit_sha == sha.lower()
        assert entry.content_bytes == data
        assert entry.content_sha256 is not None
        assert entry.fetched_at is not None

        # Fetch hit
        cached = cache.get_github(repo, sha)
        assert cached is not None
        assert cached.content_bytes == data
        assert cached.fetched_at == entry.fetched_at

        # Miss on different SHA
        assert cache.get_github(repo, "0000000000000000000000000000000000000000") is None

    def test_cross_tenant_github_authorization_isolation(self):
        cache = ContentCache()
        repo = "internal/secret-repo"
        sha = "1234567890abcdef1234567890abcdef12345678"
        data = b"CONFIDENTIAL_TENANT_A_SOURCE_CODE"

        tenant_a = uuid4()
        tenant_b = uuid4()

        # Tenant A caches a private repo/commit
        cache.put_github(repo, sha, data, tenant_id=tenant_a, is_private=True)

        # Tenant A can access its cached asset
        cached_a = cache.get_github(repo, sha, tenant_id=tenant_a)
        assert cached_a is not None
        assert cached_a.content_bytes == data

        # Tenant B CANNOT access Tenant A's cached asset (no authorization leak)
        cached_b = cache.get_github(repo, sha, tenant_id=tenant_b)
        assert cached_b is None

        # Anonymous/public request CANNOT access Tenant A's cached asset
        cached_anon = cache.get_github(repo, sha, tenant_id=None)
        assert cached_anon is None

    def test_public_page_cache_by_canonical_url(self):
        cache = ContentCache()
        url = "https://example.com/docs/api"
        content = b"<html><head><title>API Docs</title></head><body>Welcome to the documentation.</body></html>"
        receipt = {"url": url, "status": "observed", "title": "API Docs"}

        entry = cache.put_public_page(
            canonical_url=url,
            content_bytes=content,
            receipt=receipt,
            etag='"xyz-123"',
            last_modified="Wed, 21 Oct 2025 07:28:00 GMT",
            discovered_links=["https://example.com/docs/api/v2"],
        )

        assert entry.canonical_url == url
        assert entry.etag == '"xyz-123"'
        assert entry.last_modified == "Wed, 21 Oct 2025 07:28:00 GMT"

        # Check retrieval
        cached = cache.get_public_page(url)
        assert cached is not None
        assert cached.content_bytes == content
        assert cached.etag == '"xyz-123"'
        assert cached.receipt["status"] == "observed"
        assert cached.discovered_links == ["https://example.com/docs/api/v2"]

        # Conditional headers helper
        cond_headers = cache.get_conditional_headers(url)
        assert cond_headers.get("If-None-Match") == '"xyz-123"'
        assert cond_headers.get("If-Modified-Since") == "Wed, 21 Oct 2025 07:28:00 GMT"

    def test_cross_tenant_artifact_isolation(self):
        cache = ContentCache()
        sha256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        tenant_a = uuid4()
        tenant_b = uuid4()

        cache.put_artifact(sha256, {"parsed": "private"}, tenant_id=tenant_a, is_private=True)

        assert cache.get_artifact(sha256, tenant_id=tenant_a) is not None
        assert cache.get_artifact(sha256, tenant_id=tenant_b) is None
        assert cache.get_artifact(sha256, tenant_id=None) is None

    def test_retention_ttl_and_eviction(self):
        cache = ContentCache(default_ttl_seconds=0.01)
        cache.set("temp_key", "temp_value")
        assert cache.get("temp_key") == "temp_value"

        time.sleep(0.02)
        # Expired get returns None
        assert cache.get("temp_key") is None

        # Evict expired
        cache.set("key2", "val2", ttl_seconds=0.01)
        time.sleep(0.02)
        evicted = cache.evict_expired()
        assert evicted >= 1


class TestIntegrationPublicLinksAndWebDiscoveryCache:
    def setup_method(self):
        get_content_cache().clear()

    def teardown_method(self):
        get_content_cache().clear()

    def test_inspect_link_uses_cache_on_second_call(self):
        url = "http://example.com/cached-page"
        html = "<html><head><title>Cached Page</title></head><body>This is cached page text that meets length limits.</body></html>"
        transport = MockTransport([
            httpx.Response(200, headers={"content-type": "text/html"}, text=html, request=httpx.Request("GET", url)),
        ])

        deadline = time.monotonic() + 10.0
        # First call: hits network transport
        res1 = inspect_link(url, deadline, transport=transport)
        assert res1["status"] == "observed"
        assert transport.call_count == 1
        original_fetched_at = res1["fetched_at"]

        # Second call: served from ContentCache without hitting transport
        res2 = inspect_link(url, deadline, transport=transport)
        assert res2["status"] == "observed"
        assert res2.get("cached") is True
        assert res2["fetched_at"] == original_fetched_at  # Preserves fetched-at timestamp!
        assert transport.call_count == 1  # Network transport was NOT invoked again!

    def test_web_discovery_frontier_uses_cache(self):
        url = "https://example.com/portfolio"
        html = "<html><head><title>Portfolio</title></head><body>Full portfolio content with sufficient readable text.</body></html>"
        transport = MockTransport([
            httpx.Response(200, headers={"content-type": "text/html"}, text=html, request=httpx.Request("GET", url)),
        ])

        frontier = EvidenceDiscoveryFrontier(transport=transport, time_budget=5.0)
        frontier.add_url(url)
        items = frontier.run()
        assert len(items) == 1
        assert items[0].fetch_status == "fetched"
        assert transport.call_count == 1

        # Second frontier run on identical URL
        frontier2 = EvidenceDiscoveryFrontier(transport=transport, time_budget=5.0)
        frontier2.add_url(url)
        items2 = frontier2.run()
        assert len(items2) == 1
        assert items2[0].fetch_status == "fetched"
        # Transport call count remains 1 because item was served directly from ContentCache!
        assert transport.call_count == 1
