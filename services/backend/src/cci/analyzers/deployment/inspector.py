"""Safe candidate live deployment inspector.

INVARIANTS:
1. Candidate deployment code is NEVER executed (no headless browser running untrusted JS).
2. All outbound connections are strictly validated by SSRF protection.
3. Every observation generates an immutable EvidenceInput linked to the deployment URL.
"""

import re
import socket
import ssl
import urllib.parse
from datetime import datetime, timezone
from typing import Any

import httpx
from cci.domain.contracts import EvidenceInput
from cci.domain.enums import CapabilityKey, SourceFamily
from cci.domain.signal_rules import signal_rule_fields
from cci.security.ssrf import SSRFSecurityError, safe_http_get

EXTRACTOR_VERSION = "1.0.0"


def inspect_tls_certificate(hostname: str, port: int = 443) -> dict[str, Any]:
    """Inspects TLS certificate validity and issuer in an SSRF-safe manner."""
    try:
        # Validate hostname before making TLS handshake
        from cci.security.ssrf import resolve_and_validate_hostname

        resolve_and_validate_hostname(hostname)

        context = ssl.create_default_context()
        with socket.create_connection((hostname, port), timeout=4.0) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert: Any = ssock.getpeercert()
                version = ssock.version()
                return {
                    "is_valid": True,
                    "tls_version": version,
                    "subject": cert.get("subject") if cert else None,
                    "issuer": cert.get("subject") if cert else None,
                    "notAfter": cert.get("notAfter"),
                }
    except Exception as e:
        return {"is_valid": False, "error": str(e)}


def analyze_security_headers(headers: httpx.Headers) -> dict[str, Any]:
    """Inspects HTTP response headers for defensive security practices."""
    h_lower = {k.lower(): v for k, v in headers.items()}

    hsts = "strict-transport-security" in h_lower
    csp = "content-security-policy" in h_lower
    nosniff = h_lower.get("x-content-type-options", "").lower() == "nosniff"
    xframe = h_lower.get("x-frame-options", "").lower() in ("deny", "sameorigin")
    referrer = "referrer-policy" in h_lower
    permissions = "permissions-policy" in h_lower

    header_count = sum([hsts, csp, nosniff, xframe, referrer, permissions])

    score = 65.0
    if hsts:
        score += 8.0
    if csp:
        score += 10.0
    if nosniff:
        score += 5.0
    if xframe:
        score += 4.0
    if referrer or permissions:
        score += 3.0

    return {
        "header_count": header_count,
        "hsts": hsts,
        "csp": csp,
        "nosniff": nosniff,
        "xframe": xframe,
        "score": min(score, 95.0),
    }


def analyze_html_structure(html: str) -> dict[str, Any]:
    """Statically inspects HTML response for semantic structure and responsive metadata."""
    html_lower = html.lower()

    has_viewport = bool(re.search(r'<meta[^>]+name=["\']viewport["\']', html_lower))
    has_title = bool(re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE))
    has_semantic_tags = any(
        tag in html_lower for tag in ("<main", "<nav", "<header", "<footer", "<article")
    )
    has_og_tags = bool(re.search(r'<meta[^>]+property=["\']og:', html_lower))

    score = 70.0
    features = []
    if has_viewport:
        score += 8.0
        features.append("Responsive mobile viewport meta tag")
    if has_semantic_tags:
        score += 7.0
        features.append("HTML5 semantic elements (<main>, <nav>, etc.)")
    if has_og_tags:
        score += 5.0
        features.append("OpenGraph social sharing metadata")

    return {
        "has_viewport": has_viewport,
        "has_title": has_title,
        "has_semantic_tags": has_semantic_tags,
        "has_og_tags": has_og_tags,
        "score": min(score, 90.0),
        "features": features,
    }


def inspect_live_deployment(
    deployment_url: str,
    commit_sha: str | None = None,
    mock_response: httpx.Response | None = None,
    skip_tls_socket: bool = False,
) -> list[EvidenceInput]:
    """Inspects a candidate live deployment URL and produces structured EvidenceInput objects."""
    evidence: list[EvidenceInput] = []
    parsed = urllib.parse.urlparse(deployment_url)
    hostname = parsed.hostname or deployment_url
    revision = (
        commit_sha
        or f"deployment-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    )

    # 1. Fetch HTTP response safely via SSRF guard (or mock response in unit tests)
    if mock_response is not None:
        response = mock_response
    else:
        try:
            response = safe_http_get(deployment_url)
        except SSRFSecurityError:
            # Prohibited or unreachable destination - no positive evidence generated
            return []
        except Exception:
            return []

    is_success = 200 <= response.status_code < 300
    if not is_success:
        return []

    # 2. DevOps & Cloud Delivery Evidence (Live deployed application)
    headers_dict = {k.lower(): v for k, v in response.headers.items()}
    cdn_hints = [
        h
        for h in headers_dict
        if any(c in h for c in ("cf-", "vercel", "netlify", "fastly", "x-amz-", "fly-"))
    ]
    cdn_desc = (
        f"CDN/Edge platform detected ({', '.join(cdn_hints[:2])})"
        if cdn_hints
        else "Production web server"
    )

    evidence.append(
        EvidenceInput(
            **signal_rule_fields("candidatex.deployment.live_service"),
            source_family=SourceFamily.DEPLOYMENT,
            source_locator=deployment_url,
            immutable_revision=revision,
            artifact_path="live_deployment",
            symbol_or_line=f"HTTP {response.status_code}",
            target_capability=CapabilityKey.DEVOPS_CLOUD,
            technical_signal_strength=82.0 if cdn_hints else 76.0,
            is_positive_support=True,
            raw_support_text=f"Live operational web service verified at {deployment_url} (Status: {response.status_code}, {cdn_desc})",
            extractor_version=EXTRACTOR_VERSION,
        )
    )

    # 3. Defensive Security Headers Evidence
    sec_analysis = analyze_security_headers(response.headers)
    if sec_analysis["header_count"] >= 2:
        sec_features = []
        if sec_analysis["hsts"]:
            sec_features.append("HSTS")
        if sec_analysis["csp"]:
            sec_features.append("Content-Security-Policy")
        if sec_analysis["nosniff"]:
            sec_features.append("X-Content-Type-Options (nosniff)")
        if sec_analysis["xframe"]:
            sec_features.append("X-Frame-Options")

        evidence.append(
            EvidenceInput(
                **signal_rule_fields("candidatex.deployment.security_headers"),
                source_family=SourceFamily.DEPLOYMENT,
                source_locator=deployment_url,
                immutable_revision=revision,
                artifact_path="security_headers",
                symbol_or_line=f"{sec_analysis['header_count']} Security Headers",
                target_capability=CapabilityKey.SECURITY,
                technical_signal_strength=sec_analysis["score"],
                is_positive_support=True,
                raw_support_text=f"Defensive HTTP security headers verified at {deployment_url}: {', '.join(sec_features)}",
                extractor_version=EXTRACTOR_VERSION,
            )
        )

    # 4. Frontend Engineering DOM & Responsive Evidence
    content_type = response.headers.get("content-type", "").lower()
    if "text/html" in content_type:
        html_text = response.text
        html_analysis = analyze_html_structure(html_text)
        if html_analysis["features"]:
            evidence.append(
                EvidenceInput(
                    **signal_rule_fields("candidatex.deployment.responsive_dom"),
                    source_family=SourceFamily.DEPLOYMENT,
                    source_locator=deployment_url,
                    immutable_revision=revision,
                    artifact_path="html_dom",
                    symbol_or_line="Responsive DOM Layout",
                    target_capability=CapabilityKey.FRONTEND_ENGINEERING,
                    technical_signal_strength=html_analysis["score"],
                    is_positive_support=True,
                    raw_support_text=f"Modern responsive web architecture verified at {deployment_url}: {'; '.join(html_analysis['features'])}",
                    extractor_version=EXTRACTOR_VERSION,
                )
            )

    # 5. TLS Certificate Inspection
    if parsed.scheme.lower() == "https" and not skip_tls_socket:
        tls_info = inspect_tls_certificate(hostname)
        if tls_info.get("is_valid"):
            evidence.append(
                EvidenceInput(
                    **signal_rule_fields("candidatex.deployment.tls_certificate"),
                    source_family=SourceFamily.DEPLOYMENT,
                    source_locator=deployment_url,
                    immutable_revision=revision,
                    artifact_path="tls_certificate",
                    symbol_or_line=f"TLS {tls_info.get('tls_version', 'v1.3')}",
                    target_capability=CapabilityKey.SECURITY,
                    technical_signal_strength=84.0,
                    is_positive_support=True,
                    raw_support_text=f"Valid production TLS certificate verified for {hostname} (Expires: {tls_info.get('notAfter')})",
                    extractor_version=EXTRACTOR_VERSION,
                )
            )

    return evidence
