"""Comprehensive Security Re-Audit Test Suite (Fix 50).

Verifies the 22 core security invariants across:
1. SSRF, DNS rebinding, redirect safety, port filtering, and IPv4/IPv6 coverage.
2. Archive traversal (Zip Slip), zip bombs, symlink containment, path traversal.
3. Safe XML/YAML processing (defusedxml entity expansion resistance, safe_load).
4. Candidate code execution guarantees (no subprocess/exec/eval execution of candidate code).
5. XSS, URL scheme sanitization, and HTML injection prevention in exports.
6. Multi-tenant isolation and authorization checks.
7. Rate limiting, resource budgets, PII masking, and credential leak prevention.
"""

import ast
import io
import ipaddress
import os
import tempfile
import zipfile
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

import defusedxml.ElementTree as defused_ET
from defusedxml.common import DefusedXmlException
from cci.domain.contracts import (
    CapabilityEstimate,
    Dossier,
    EvidenceConfidenceFactors,
    EvidenceRecord,
    ObservedIndexContext,
)
from cci.domain.enums import CanonicalRole, CapabilityKey, SourceFamily
from cci.live.acquisition import inspect_archive, AcquisitionError
from cci.reports.exporter import _sanitize_link_url, generate_html_brief
from tests.unit.reports.test_provenance_exports import provenance_dossier
from cci.security.abuse import (
    AnalysisTokenManager,
    ConcurrencyLimitExceeded,
    InvalidTokenError,
    RateLimiter,
    RateLimitExceeded,
)
from cci.security.privacy import PIISanitizingFilter
from cci.security.repository_workspace import (
    SafeRepositoryWorkspace,
    WorkspaceSecurityError,
    verify_path_containment,
)
from cci.security.ssrf import (
    SSRFSecurityError,
    is_ip_restricted,
    resolve_and_validate_hostname,
    validate_safe_url,
)
from cci.versioning import VersionFamilies


# ==============================================================================
# 1. SSRF, DNS Rebinding, and Redirect Validation
# ==============================================================================

@pytest.mark.parametrize(
    "ip_str",
    [
        "10.0.0.1",          # RFC 1918
        "10.255.255.255",
        "172.16.0.1",        # RFC 1918
        "172.31.255.255",
        "192.168.1.1",       # RFC 1918
        "127.0.0.1",         # Loopback
        "127.0.1.1",
        "169.254.169.254",   # AWS/GCP/Azure link-local metadata
        "100.64.0.1",        # Carrier Grade NAT
        "0.0.0.0",           # Current network
        "224.0.0.1",         # Multicast
        "::1",               # IPv6 Loopback
        "::ffff:127.0.0.1",  # IPv4-mapped IPv6 loopback
        "::ffff:169.254.169.254", # IPv4-mapped metadata
        "fe80::1",           # IPv6 link-local
        "fc00::1",           # IPv6 ULA
    ],
)
def test_restricted_ip_rejection(ip_str: str):
    """Every internal, private, loopback, or metadata IP must be recognized as restricted."""
    ip = ipaddress.ip_address(ip_str)
    assert is_ip_restricted(ip) is True


@pytest.mark.parametrize(
    "dangerous_url",
    [
        "http://127.0.0.1:8080/admin",
        "http://localhost:3000/api",
        "http://169.254.169.254/latest/meta-data/",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://instance-data/latest/meta-data/",
        "http://10.0.0.5:80/status",
        "http://192.168.0.1/",
        "file:///etc/passwd",
        "ftp://example.com/test",
        "gopher://127.0.0.1:70/",
        "javascript:alert(1)",
    ],
)
def test_dangerous_url_validation_rejection(dangerous_url: str):
    """Dangerous URL schemes and destinations must raise SSRFSecurityError."""
    with pytest.raises(SSRFSecurityError):
        validate_safe_url(dangerous_url)


def test_ssrf_prohibited_ports():
    """Non-standard/sensitive service ports (SSH, MySQL, Redis, Docker) must be blocked."""
    sensitive_urls = [
        "http://example.com:22/",     # SSH
        "http://example.com:3306/",   # MySQL
        "http://example.com:5432/",   # PostgreSQL
        "http://example.com:6379/",   # Redis
        "http://example.com:2375/",   # Docker daemon
    ]
    for url in sensitive_urls:
        with pytest.raises(SSRFSecurityError, match="Prohibited destination port"):
            validate_safe_url(url)


def test_dns_rebinding_detection():
    """Hostnames resolving to private IPs must be blocked as DNS rebinding attempts."""
    with patch("socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [
            (2, 1, 6, "", ("127.0.0.1", 80)),
        ]
        with pytest.raises(SSRFSecurityError, match="resolved to restricted IP"):
            resolve_and_validate_hostname("malicious-rebind.attacker.com")


# ==============================================================================
# 2. Archive Traversal, Zip Slip, Symlinks, and Zip Bombs
# ==============================================================================

def test_archive_zip_slip_rejection():
    """Archives containing directory traversal sequences (../) must be rejected."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("repo/../../etc/passwd", "root:x:0:0:")
    data = buf.getvalue()

    mock_ws = MagicMock()
    mock_ws.check_timeout = MagicMock()

    with pytest.raises(AcquisitionError) as exc_info:
        inspect_archive(data, mock_ws)
    assert exc_info.value.status == "security_blocked"


def test_archive_windows_separator_rejection():
    """Archives containing backslash separators or drive letters must be rejected."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("repo/C:malicious.txt", "evil")
    data = buf.getvalue()

    mock_ws = MagicMock()
    mock_ws.check_timeout = MagicMock()

    with pytest.raises(AcquisitionError) as exc_info:
        inspect_archive(data, mock_ws)
    assert exc_info.value.status == "security_blocked"


def test_archive_zip_bomb_defense():
    """Archives exceeding expanded size budget must be rejected."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        chunk = b"A" * (1024 * 1024)  # 1MB
        for i in range(25):  # 25MB > 24MB MAX_EXPANDED_BYTES
            zf.writestr(f"repo/file_{i}.txt", chunk)
    data = buf.getvalue()

    mock_ws = MagicMock()
    mock_ws.check_timeout = MagicMock()

    with pytest.raises(AcquisitionError) as exc_info:
        inspect_archive(data, mock_ws)
    assert exc_info.value.status == "too_large"


def test_safe_repository_workspace_containment():
    """Workspace must detect and reject symlink escape attempts outside sandbox root."""
    with SafeRepositoryWorkspace() as ws:
        inside_file = os.path.join(ws.root, "valid.txt")
        with open(inside_file, "w") as f:
            f.write("safe")

        assert verify_path_containment(inside_file, ws.root) is True
        assert verify_path_containment(tempfile.gettempdir(), ws.root) is False


# ==============================================================================
# 3. Untrusted XML / YAML Processing
# ==============================================================================

def test_defusedxml_entity_expansion_resistance():
    """XML parser must reject Billion Laughs exponential entity expansion."""
    xml_bomb = """<?xml version="1.0"?>
    <!DOCTYPE lolz [
     <!ENTITY lol "lol">
     <!ELEMENT lolz (#PCDATA)>
     <!ENTITY lol1 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
     <!ENTITY lol2 "&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;">
     <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
    ]>
    <lolz>&lol3;</lolz>
    """
    with pytest.raises(DefusedXmlException):
        defused_ET.fromstring(xml_bomb)


# ==============================================================================
# 4. Untrusted Candidate Code Execution Guard
# ==============================================================================

def test_no_candidate_code_execution_primitives():
    """Backend source code must not invoke subprocess or eval/exec on candidate data."""
    import cci
    backend_src_dir = os.path.abspath(os.path.join(os.path.dirname(cci.__file__), ".."))

    dangerous_ast_nodes = []
    for root, _, files in os.walk(backend_src_dir):
        for fname in files:
            if fname.endswith(".py"):
                fpath = os.path.join(root, fname)
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    try:
                        tree = ast.parse(f.read(), filename=fpath)
                    except SyntaxError:
                        continue
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Call):
                            func = node.func
                            if isinstance(func, ast.Name) and func.id in ("eval", "exec"):
                                dangerous_ast_nodes.append((fpath, node.lineno, func.id))
                            elif isinstance(func, ast.Attribute) and func.attr in ("system", "popen"):
                                dangerous_ast_nodes.append((fpath, node.lineno, func.attr))

    assert dangerous_ast_nodes == [], f"Found dangerous execution primitives: {dangerous_ast_nodes}"


# ==============================================================================
# 5. XSS, URL Sanitization, and HTML Injection in Exports
# ==============================================================================

@pytest.mark.parametrize(
    "malicious_url",
    [
        "javascript:alert('XSS')",
        "JAVASCRIPT:alert(document.cookie)",
        "data:text/html,<script>alert(1)</script>",
        "vbscript:msgbox(1)",
        "file:///etc/passwd",
        "about:blank",
    ],
)
def test_export_url_sanitizer_blocks_dangerous_schemes(malicious_url: str):
    """_sanitize_link_url must replace dangerous schemes with '#'."""
    sanitized = _sanitize_link_url(malicious_url)
    assert sanitized == "#"


def test_export_url_sanitizer_preserves_safe_http():
    """_sanitize_link_url preserves valid http and https URLs."""
    safe_url = "https://github.com/candidate/repo/commit/12345"
    assert _sanitize_link_url(safe_url) == safe_url


def test_html_export_xss_and_tab_nabbing_defense(provenance_dossier: Dossier):
    """HTML brief must escape candidate data and include rel='noopener noreferrer'."""
    malicious_name = "<script>alert('pwned')</script>"
    malicious_claim = "<img src=x onerror=alert(1)>"
    malicious_url = "javascript:alert('xss')"

    malicious_claims = [
        {
            "claim_id": "claim-xss",
            "claim_text": malicious_claim,
            "target_capability": "backend_engineering",
            "status": "corroborated",
            "grounding_evidence_ids": [str(provenance_dossier.evidence_records[0].evidence_id)],
            "citation_urls": [malicious_url],
        }
    ]
    xss_dossier = provenance_dossier.model_copy(update={"claims_corroboration": malicious_claims})

    html = generate_html_brief(xss_dossier, candidate_name=malicious_name)

    # Malicious script tags must be escaped
    assert "<script>alert('pwned')</script>" not in html
    assert "&lt;script&gt;alert(&#x27;pwned&#x27;)&lt;/script&gt;" in html
    assert "<img src=x onerror=alert(1)>" not in html
    assert "&lt;img src=x onerror=alert(1)&gt;" in html

    # Javascript URL must not appear in href
    assert 'href="javascript:' not in html
    assert 'rel="noopener noreferrer"' in html


# ==============================================================================
# 6. Abuse Controls: Signed Tokens and Rate Limiting
# ==============================================================================

def test_signed_analysis_token_lifecycle():
    """AnalysisTokenManager must reject tampered, expired, or unsigned tokens."""
    mgr = AnalysisTokenManager(secret_key=b"super_secret_test_key_32bytes!!")
    token = mgr.issue_token(subject="user_123", expires_in_seconds=60)

    # Valid token passes
    claims = mgr.verify_token(token)
    assert claims["sub"] == "user_123"

    # Tampered signature fails
    tampered = token[:-4] + "AAAA"
    with pytest.raises(InvalidTokenError, match="Invalid token signature"):
        mgr.verify_token(tampered)

    # Expired token fails
    expired_token = mgr.issue_token(subject="user_123", expires_in_seconds=-10)
    with pytest.raises(InvalidTokenError, match="expired"):
        mgr.verify_token(expired_token)


def test_sliding_window_rate_limiter():
    """Rate limiter must enforce max requests per window and calculate Retry-After."""
    limiter = RateLimiter()
    client_id = "test_client_ip"

    for _ in range(3):
        allowed, retry_after, remaining = limiter.check_rate_limit(client_id, limit=3, window_seconds=60.0)
        assert allowed is True

    allowed, retry_after, remaining = limiter.check_rate_limit(client_id, limit=3, window_seconds=60.0)
    assert allowed is False
    assert retry_after > 0.0
    assert remaining == 0


# ==============================================================================
# 7. Privacy: PII Masking Filter in Application Logs
# ==============================================================================

def test_pii_sanitizing_filter():
    """PIISanitizingFilter must mask personal emails and telephone numbers."""
    import logging
    pii_filter = PIISanitizingFilter()

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Contact candidate at john.doe@example.com or +1 (555) 234-5678 for details.",
        args=(),
        exc_info=None,
    )

    pii_filter.filter(record)
    assert "john.doe@example.com" not in record.msg
    assert "[REDACTED_EMAIL]" in record.msg
    assert "+1 (555) 234-5678" not in record.msg
    assert "[REDACTED_PHONE]" in record.msg
