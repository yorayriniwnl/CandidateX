"""Unit tests for live candidate deployment inspection."""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

import httpx
import pytest
from cci.analyzers.deployment.inspector import (
    analyze_html_structure,
    analyze_security_headers,
    inspect_live_deployment,
)
from cci.domain.enums import CapabilityKey, SourceFamily


def test_analyze_security_headers():
    headers = httpx.Headers({
        "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
        "Content-Security-Policy": "default-src 'self'",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
    })
    res = analyze_security_headers(headers)
    assert res["header_count"] >= 4
    assert res["hsts"] is True
    assert res["csp"] is True
    assert res["nosniff"] is True
    assert res["xframe"] is True
    assert res["score"] >= 88.0


def test_analyze_html_structure():
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta property="og:title" content="Candidate Portfolio">
    <title>Portfolio</title>
</head>
<body>
    <header><nav>Nav</nav></header>
    <main><article>Content</article></main>
    <footer>Footer</footer>
</body>
</html>
"""
    res = analyze_html_structure(html)
    assert res["has_viewport"] is True
    assert res["has_semantic_tags"] is True
    assert res["has_og_tags"] is True
    assert res["score"] >= 85.0
    assert len(res["features"]) >= 3


def test_inspect_live_deployment_with_mock():
    mock_resp = httpx.Response(
        status_code=200,
        headers={
            "content-type": "text/html; charset=utf-8",
            "server": "Vercel",
            "x-vercel-id": "iad1::iad1-12345",
            "strict-transport-security": "max-age=31536000",
            "content-security-policy": "default-src 'self'",
            "x-content-type-options": "nosniff",
        },
        text="""<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body><main><h1>Hello World</h1></main></body></html>""",
    )

    evidence = inspect_live_deployment(
        deployment_url="https://candidate-project.vercel.app",
        commit_sha="live-2026",
        mock_response=mock_resp,
        skip_tls_socket=True,
    )

    assert len(evidence) >= 3

    target_caps = {e.target_capability for e in evidence}
    assert CapabilityKey.DEVOPS_CLOUD in target_caps
    assert CapabilityKey.SECURITY in target_caps
    assert CapabilityKey.FRONTEND_ENGINEERING in target_caps

    for ev in evidence:
        assert ev.source_family == SourceFamily.DEPLOYMENT
        assert ev.source_locator == "https://candidate-project.vercel.app"
        assert ev.immutable_revision == "live-2026"
        assert 0.0 <= ev.observed_score <= 100.0


def test_inspect_live_deployment_failed_status():
    mock_resp = httpx.Response(
        status_code=500,
        headers={"content-type": "text/plain"},
        text="Internal Server Error",
    )

    evidence = inspect_live_deployment(
        deployment_url="https://broken-service.com",
        mock_response=mock_resp,
        skip_tls_socket=True,
    )

    # Failed status should not yield positive capability evidence
    assert len(evidence) == 0
