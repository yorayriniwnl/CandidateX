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


def test_security_header_policy_bonus_is_once_and_score_caps_at_95():
    policy_only = analyze_security_headers(httpx.Headers({
        "Referrer-Policy": "no-referrer",
        "Permissions-Policy": "camera=()",
    }))
    all_headers = analyze_security_headers(httpx.Headers({
        "Strict-Transport-Security": "max-age=31536000",
        "Content-Security-Policy": "default-src 'self'",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
        "Permissions-Policy": "camera=()",
    }))
    assert (policy_only["header_count"], policy_only["score"]) == (2, 68.0)
    assert (all_headers["header_count"], all_headers["score"]) == (6, 95.0)


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


def test_html_title_does_not_add_strength_and_all_scored_markers_cap_at_90():
    title_only = analyze_html_structure("<html><title>Portfolio</title></html>")
    all_markers = analyze_html_structure(
        '<meta name="viewport"><main>Content</main><meta property="og:title">'
    )
    assert (title_only["has_title"], title_only["score"], title_only["features"]) == (
        True, 70.0, []
    )
    assert (all_markers["has_viewport"], all_markers["has_semantic_tags"],
            all_markers["has_og_tags"], all_markers["score"]) == (
        True, True, True, 90.0
    )


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

    assert {
        ev.artifact_path: (ev.signal_rule_id, ev.signal_rule_version, ev.technical_signal_strength)
        for ev in evidence
    } == {
        "live_deployment": ("candidatex.deployment.live_service", "1.0.0", 82.0),
        "security_headers": ("candidatex.deployment.security_headers", "1.0.0", 88.0),
        "html_dom": ("candidatex.deployment.responsive_dom", "1.0.0", 85.0),
    }


def test_live_service_without_cdn_and_valid_tls(monkeypatch):
    monkeypatch.setattr(
        "cci.analyzers.deployment.inspector.inspect_tls_certificate",
        lambda hostname: {"is_valid": True, "tls_version": "TLSv1.3", "notAfter": "later"},
    )
    evidence = inspect_live_deployment(
        "https://example.com", commit_sha="sha1",
        mock_response=httpx.Response(200, headers={"content-type": "text/plain"}, text="OK"),
    )
    assert {
        ev.artifact_path: (ev.signal_rule_id, ev.signal_rule_version, ev.technical_signal_strength)
        for ev in evidence
    } == {
        "live_deployment": ("candidatex.deployment.live_service", "1.0.0", 76.0),
        "tls_certificate": ("candidatex.deployment.tls_certificate", "1.0.0", 84.0),
    }


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
