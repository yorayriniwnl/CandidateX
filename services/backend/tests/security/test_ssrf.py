"""Security tests verifying strict SSRF protection and DNS pinning invariants."""

import ipaddress
import pytest
from cci.security.ssrf import (
    SSRFSecurityError,
    is_ip_restricted,
    resolve_and_validate_hostname,
    validate_safe_url,
)


def test_private_and_loopback_ip_blocking():
    """Verify that RFC 1918 private and loopback IP addresses are strictly identified as restricted."""
    restricted_ips = [
        "127.0.0.1",
        "127.0.1.1",
        "10.0.0.1",
        "10.254.0.1",
        "172.16.0.1",
        "172.31.255.255",
        "192.168.0.1",
        "192.168.1.100",
        "0.0.0.0",
        "100.64.0.1",  # CGNAT
        "192.0.2.1",   # TEST-NET
        "::1",         # IPv6 Loopback
        "fc00::1",     # IPv6 ULA
        "fe80::1",     # IPv6 Link-local
    ]

    for ip_str in restricted_ips:
        ip_obj = ipaddress.ip_address(ip_str)
        assert is_ip_restricted(ip_obj), f"Expected {ip_str} to be restricted"


def test_cloud_metadata_ip_blocking():
    """CRITICAL SECURITY TEST: AWS / GCP / Azure IMDS endpoint 169.254.169.254 must be blocked."""
    metadata_ip = ipaddress.ip_address("169.254.169.254")
    assert is_ip_restricted(metadata_ip)

    # Validate direct URL
    with pytest.raises(SSRFSecurityError, match="Restricted direct IP|Prohibited"):
        validate_safe_url("http://169.254.169.254/latest/meta-data/")

    # Validate cloud metadata hostnames
    for host in ("metadata.google.internal", "localhost", "instance-data"):
        with pytest.raises(SSRFSecurityError, match="Prohibited hostname"):
            resolve_and_validate_hostname(host)


def test_prohibited_url_schemes():
    """Security test: Only http and https schemes are allowed. file://, gopher://, ftp:// must be rejected."""
    dangerous_urls = [
        "file:///etc/passwd",
        "file:///C:/Windows/win.ini",
        "gopher://127.0.0.1:70/",
        "ftp://example.com/file",
        "dict://127.0.0.1:11211/",
        "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
    ]

    for url in dangerous_urls:
        with pytest.raises(SSRFSecurityError, match="Prohibited URL scheme"):
            validate_safe_url(url)


def test_prohibited_sensitive_ports():
    """Security test: Internal database and management ports must be blocked."""
    sensitive_urls = [
        "http://example.com:22",    # SSH
        "http://example.com:3306",  # MySQL
        "http://example.com:5432",  # PostgreSQL
        "http://example.com:6379",  # Redis
        "http://example.com:2375",  # Docker daemon
    ]

    for url in sensitive_urls:
        with pytest.raises(SSRFSecurityError, match="Prohibited destination port"):
            validate_safe_url(url)


def test_dns_rebinding_simulation(monkeypatch):
    """Security test: Hostname resolving to a restricted IP address must raise SSRFSecurityError."""
    import socket

    def mock_getaddrinfo(host, port, *args, **kwargs):
        # Simulate a domain that resolves to internal 10.0.0.1
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", port))]

    monkeypatch.setattr(socket, "getaddrinfo", mock_getaddrinfo)

    with pytest.raises(SSRFSecurityError, match="DNS rebinding / SSRF attempt"):
        resolve_and_validate_hostname("evil-rebind.com")
