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
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field

from cci.domain.contracts import EvidenceInput
from cci.domain.enums import CapabilityKey, SourceFamily
from cci.domain.signal_rules import signal_rule_fields
from cci.security.ssrf import SSRFSecurityError, resolve_and_validate_hostname, safe_http_get

EXTRACTOR_VERSION = "1.0.0"


class DeploymentInspectionReport(BaseModel):
    """Structured report from live candidate deployment inspection (Fix 22)."""

    model_config = ConfigDict(frozen=True)

    deployment_url: str
    status_code: int = 0
    content_type: str = ""
    status: str = "unavailable"
    detail: str = ""
    application_identity: dict[str, Any] = Field(default_factory=dict)
    linked_repository: str | None = None
    documented_routes: list[str] = Field(default_factory=list)
    security_headers: dict[str, Any] = Field(default_factory=dict)
    tls_info: dict[str, Any] = Field(default_factory=dict)
    frontend_structure: dict[str, Any] = Field(default_factory=dict)
    app_metadata: dict[str, Any] = Field(default_factory=dict)
    evidence_inputs: list[EvidenceInput] = Field(default_factory=list)
    supported_signals: list[str] = Field(
        default_factory=lambda: [
            "deployment_existence",
            "project_linkage",
            "runtime_public_artifact_observation",
        ]
    )


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


def extract_application_identity(html: str, headers: httpx.Headers) -> dict[str, Any]:
    """Statically extracts application identity and platform hints from HTML and headers."""
    title_match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
    title = title_match.group(1).strip() if title_match else ""

    app_name_match = re.search(
        r'<meta[^>]+name=["\'](?:application-name|apple-mobile-web-app-title)["\'][^>]+content=["\']([^"\']+)["\']',
        html,
        re.IGNORECASE,
    )
    if not app_name_match:
        app_name_match = re.search(
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\'](?:application-name|apple-mobile-web-app-title)["\']',
            html,
            re.IGNORECASE,
        )
    app_name = app_name_match.group(1).strip() if app_name_match else ""

    gen_match = re.search(
        r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']([^"\']+)["\']',
        html,
        re.IGNORECASE,
    )
    if not gen_match:
        gen_match = re.search(
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']generator["\']',
            html,
            re.IGNORECASE,
        )
    generator = gen_match.group(1).strip() if gen_match else ""

    og_site_match = re.search(
        r'<meta[^>]+property=["\']og:site_name["\'][^>]+content=["\']([^"\']+)["\']',
        html,
        re.IGNORECASE,
    )
    if not og_site_match:
        og_site_match = re.search(
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:site_name["\']',
            html,
            re.IGNORECASE,
        )
    og_site = og_site_match.group(1).strip() if og_site_match else ""

    h_lower = {k.lower(): v for k, v in headers.items()}
    server = h_lower.get("server", "")
    powered_by = h_lower.get("x-powered-by", "")

    return {
        "title": title[:300],
        "application_name": app_name[:100],
        "generator": generator[:100],
        "og_site_name": og_site[:100],
        "server": server[:100],
        "powered_by": powered_by[:100],
    }


def extract_linked_repository(html: str, known_repos: Sequence[str] = ()) -> str | None:
    """Discovers repository links in page HTML, prioritizing known candidate repositories."""
    matches = re.findall(
        r'https?://github\.com/([a-zA-Z0-9_\-\.]+)/([a-zA-Z0-9_\-\.]+)',
        html,
        re.IGNORECASE,
    )
    discovered_repos: list[str] = []
    ignored_names = {
        "features", "pricing", "about", "contact", "security", "site",
        "topics", "collections", "trending", "events", "readme", "sponsors",
    }
    for owner, repo_name in matches:
        clean_repo = re.sub(r'[\'\"\,>#\?].*$', '', repo_name).rstrip('.git').rstrip('/')
        if owner.lower() in ignored_names or clean_repo.lower() in ignored_names:
            continue
        full_url = f"https://github.com/{owner}/{clean_repo}"
        discovered_repos.append(full_url)

    if not discovered_repos:
        return None

    # If candidate repositories are known, prioritize match
    if known_repos:
        norm_known = {r.lower().rstrip('/'): r for r in known_repos}
        for disc in discovered_repos:
            if disc.lower().rstrip('/') in norm_known:
                return norm_known[disc.lower().rstrip('/')]

    return discovered_repos[0]


def extract_documented_routes(html: str) -> list[str]:
    """Statically identifies safe documented route links without active crawling or mutations."""
    hrefs = re.findall(r'href=["\'](/[^"\'\s#\?]+)', html, re.IGNORECASE)
    safe_prefixes = (
        "/api", "/docs", "/swagger", "/openapi", "/graphql", "/health",
        "/about", "/projects", "/blog", "/pricing", "/features", "/v1", "/v2",
    )
    discovered: list[str] = []
    seen: set[str] = set()
    for path in hrefs:
        if any(path.endswith(ext) for ext in (".js", ".css", ".png", ".jpg", ".svg", ".ico", ".woff", ".woff2")):
            continue
        if any(path.lower().startswith(p) for p in safe_prefixes):
            clean = path[:100]
            if clean not in seen:
                seen.add(clean)
                discovered.append(clean)
        if len(discovered) >= 25:
            break

    return discovered


def extract_app_metadata(html: str, headers: httpx.Headers) -> dict[str, Any]:
    """Extracts frontend framework markers, meta descriptions, and asset counts."""
    desc_match = re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
        html,
        re.IGNORECASE,
    )
    if not desc_match:
        desc_match = re.search(
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description["\']',
            html,
            re.IGNORECASE,
        )
    description = desc_match.group(1).strip() if desc_match else ""

    gen_match = re.search(
        r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']([^"\']+)["\']',
        html,
        re.IGNORECASE,
    )
    if not gen_match:
        gen_match = re.search(
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']generator["\']',
            html,
            re.IGNORECASE,
        )
    generator_val = gen_match.group(1).lower() if gen_match else ""
    powered_by = headers.get("x-powered-by", "").lower() if headers else ""

    html_lower = html.lower()
    frameworks: list[str] = []
    if (
        "__next_data__" in html_lower
        or "/_next/" in html_lower
        or "next" in generator_val
        or "next" in powered_by
    ):
        frameworks.append("Next.js")
    if "data-reactroot" in html_lower or "react" in html_lower:
        frameworks.append("React")
    if "data-v-" in html_lower or "vue" in html_lower:
        frameworks.append("Vue.js")
    if "ng-version" in html_lower or "ng-" in html_lower:
        frameworks.append("Angular")
    if "svelte" in html_lower:
        frameworks.append("Svelte")
    if "/@vite/client" in html_lower:
        frameworks.append("Vite")

    script_count = len(re.findall(r'<script\b', html, re.IGNORECASE))
    style_count = len(re.findall(r'<link[^>]+rel=["\']stylesheet["\']|<style\b', html, re.IGNORECASE))

    return {
        "description": description[:500],
        "frameworks": frameworks,
        "script_count": script_count,
        "style_count": style_count,
    }


def inspect_candidate_deployment(
    deployment_url: str,
    known_repos: Sequence[str] = (),
    commit_sha: str | None = None,
    mock_response: httpx.Response | None = None,
    skip_tls_socket: bool = False,
) -> DeploymentInspectionReport:
    """Safely inspects a candidate live deployment URL and produces a comprehensive report (Fix 22).

    Invariants:
    1. Public URL is validated safely before network contact.
    2. Read-only HTTP GET (never destructive, never using candidate credentials).
    3. TLS presence confirms reachability and transport security; does NOT grant candidate mastery.
    4. Supports deployment existence, project linkage, and runtime observation.
    """
    parsed = urllib.parse.urlsplit(deployment_url)
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 80, 443)
    ):
        return DeploymentInspectionReport(
            deployment_url=deployment_url,
            status="security_blocked",
            detail="Destination failed safety validation (scheme must be http/https on standard port without credentials).",
        )

    # SSRF protection and safe retrieval
    if mock_response is not None:
        response = mock_response
    else:
        try:
            response = safe_http_get(deployment_url)
        except SSRFSecurityError:
            return DeploymentInspectionReport(
                deployment_url=deployment_url,
                status="security_blocked",
                detail="Destination failed public-network safety validation.",
            )
        except Exception as e:
            return DeploymentInspectionReport(
                deployment_url=deployment_url,
                status="inaccessible",
                detail=f"Public deployment could not be reached: {e}",
            )

    status_code = response.status_code
    content_type = response.headers.get("content-type", "")
    html_text = response.text if "text/" in content_type or "xml" in content_type else ""

    if 200 <= status_code < 300:
        obs_status = "observed"
        detail = f"Verified live operational web service (HTTP {status_code})."
    elif status_code in (401, 403, 429):
        obs_status = "access_restricted"
        detail = f"Deployment reachable but access restricted (HTTP {status_code})."
    else:
        obs_status = "failed"
        detail = f"Deployment returned HTTP {status_code}."

    app_id = extract_application_identity(html_text, response.headers)
    linked_repo = extract_linked_repository(html_text, known_repos=known_repos)
    doc_routes = extract_documented_routes(html_text)
    sec_headers = analyze_security_headers(response.headers)
    frontend = analyze_html_structure(html_text) if html_text else {}
    app_meta = extract_app_metadata(html_text, response.headers)

    tls_info: dict[str, Any] = {}
    if parsed.scheme.lower() == "https":
        if skip_tls_socket or mock_response is not None:
            tls_info = {"is_valid": True, "tls_version": "TLSv1.3", "notAfter": "unknown"}
        else:
            tls_info = inspect_tls_certificate(parsed.hostname)

    evidence_inputs = inspect_live_deployment(
        deployment_url=deployment_url,
        commit_sha=commit_sha,
        mock_response=response,
        skip_tls_socket=skip_tls_socket or (mock_response is not None),
    )

    return DeploymentInspectionReport(
        deployment_url=deployment_url,
        status_code=status_code,
        content_type=content_type,
        status=obs_status,
        detail=detail,
        application_identity=app_id,
        linked_repository=linked_repo,
        documented_routes=doc_routes,
        security_headers=sec_headers,
        tls_info=tls_info,
        frontend_structure=frontend,
        app_metadata=app_meta,
        evidence_inputs=evidence_inputs,
        supported_signals=[
            "deployment_existence",
            "project_linkage",
            "runtime_public_artifact_observation",
        ],
    )
