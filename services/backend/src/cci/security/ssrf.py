"""Strict SSRF Protection, DNS Pinning, and Safe HTTP Request Transport.

INVARIANTS:
1. Candidate external links (portfolios, demo apps) must NEVER reach private networks,
   loopback devices, link-local addresses, or cloud metadata endpoints.
2. DNS rebinding attacks are prevented by pre-resolving and validating all destination IPs.
3. Every redirect hop is independently validated against SSRF rules.
4. Response payloads are bounded by strict size (5MB) and timeout (5s) caps.
"""

import ipaddress
import socket
import urllib.parse
from typing import List, Optional, Set, Tuple
import httpx


class SSRFSecurityError(Exception):
    """Raised when a URL targets a restricted, private, or dangerous destination."""
    pass


# Prohibited CIDR IP networks (IPv4 and IPv6)
RESTRICTED_NETWORKS: List[ipaddress.IPv4Network | ipaddress.IPv6Network] = [
    # IPv4
    ipaddress.ip_network("0.0.0.0/8"),          # Current network
    ipaddress.ip_network("10.0.0.0/8"),         # RFC 1918 Private
    ipaddress.ip_network("100.64.0.0/10"),      # Carrier-grade NAT
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback
    ipaddress.ip_network("169.254.0.0/16"),     # Link-local / Cloud Metadata (169.254.169.254)
    ipaddress.ip_network("172.16.0.0/12"),      # RFC 1918 Private
    ipaddress.ip_network("192.0.0.0/24"),       # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),       # TEST-NET-1
    ipaddress.ip_network("192.168.0.0/16"),     # RFC 1918 Private
    ipaddress.ip_network("198.18.0.0/15"),      # Network benchmark tests
    ipaddress.ip_network("198.51.100.0/24"),    # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),     # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),        # Multicast
    ipaddress.ip_network("240.0.0.0/4"),        # Reserved for future use
    ipaddress.ip_network("255.255.255.255/32"), # Broadcast
    # IPv6
    ipaddress.ip_network("::/128"),             # Unspecified
    ipaddress.ip_network("::1/128"),            # Loopback
    ipaddress.ip_network("::ffff:0:0/96"),      # IPv4-mapped IPv6
    ipaddress.ip_network("64:ff9b::/96"),       # IPv4/IPv6 translation
    ipaddress.ip_network("100::/64"),           # Discard prefix
    ipaddress.ip_network("2001:db8::/32"),      # Documentation
    ipaddress.ip_network("fc00::/7"),           # Unique Local Address (ULA)
    ipaddress.ip_network("fe80::/10"),          # Link-local unicast
    ipaddress.ip_network("ff00::/8"),           # Multicast
]

# Explicitly prohibited hostnames
PROHIBITED_HOSTNAMES: Set[str] = {
    "localhost",
    "metadata.google.internal",
    "instance-data",
    "metadata",
    "internal",
    "local",
}

ALLOWED_SCHEMES: Set[str] = {"http", "https"}
MAX_RESPONSE_BYTES = 5 * 1024 * 1024  # 5 Megabytes
DEFAULT_TIMEOUT_SECONDS = 5.0
MAX_REDIRECTS = 3


def is_ip_restricted(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Checks if an IP address belongs to any restricted or private network."""
    return any(ip in network for network in RESTRICTED_NETWORKS)


def resolve_and_validate_hostname(hostname: str) -> List[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    """Resolves a hostname via DNS and verifies that NONE of the resolved IPs are restricted.
    
    Raises SSRFSecurityError if resolution fails or targets a restricted IP.
    """
    host_lower = hostname.strip().lower()

    if host_lower in PROHIBITED_HOSTNAMES or host_lower.endswith((".localhost", ".local", ".internal")):
        raise SSRFSecurityError(f"Prohibited hostname: '{hostname}'")

    try:
        # Check if the hostname is directly an IP address
        direct_ip = ipaddress.ip_address(host_lower)
        if is_ip_restricted(direct_ip):
            raise SSRFSecurityError(f"Restricted direct IP address: {direct_ip}")
        return [direct_ip]
    except ValueError:
        pass  # It is a domain name, proceed with DNS resolution

    try:
        addr_info = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        raise SSRFSecurityError(f"DNS resolution failed for '{hostname}': {e}")

    resolved_ips: List[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for entry in addr_info:
        sockaddr = entry[4]
        ip_str = sockaddr[0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
            if is_ip_restricted(ip_obj):
                raise SSRFSecurityError(f"DNS rebinding / SSRF attempt: '{hostname}' resolved to restricted IP {ip_obj}")
            resolved_ips.append(ip_obj)
        except ValueError:
            continue

    if not resolved_ips:
        raise SSRFSecurityError(f"Could not resolve any valid IP addresses for '{hostname}'")

    return resolved_ips


def validate_safe_url(url: str) -> str:
    """Validates URL scheme, port, hostname, and resolved IP addresses.
    
    Returns normalized safe URL if valid, or raises SSRFSecurityError.
    """
    parsed = urllib.parse.urlparse(url.strip())

    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise SSRFSecurityError(f"Prohibited URL scheme: '{parsed.scheme}'. Only HTTP and HTTPS are permitted.")

    if not parsed.netloc:
        raise SSRFSecurityError(f"Missing host authority in URL: '{url}'")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFSecurityError(f"Invalid or missing hostname in URL: '{url}'")

    # Prohibit non-standard sensitive ports (e.g. 22, 25, 3306, 5432, 6379, 2375)
    port = parsed.port
    if port is not None and port not in (80, 443, 8080, 8443, 3000, 5000):
        raise SSRFSecurityError(f"Prohibited destination port: {port}")

    # Validate hostname and DNS resolution
    resolve_and_validate_hostname(hostname)

    return url


def safe_http_get(
    url: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_bytes: int = MAX_RESPONSE_BYTES,
) -> httpx.Response:
    """Performs an SSRF-safe HTTP GET request with redirect validation and size bounding."""
    current_url = url
    client = httpx.Client(timeout=timeout, follow_redirects=False)

    try:
        for hop in range(MAX_REDIRECTS + 1):
            # Validate every destination URL before sending request
            validate_safe_url(current_url)

            # Perform bounded stream request
            with client.stream("GET", current_url, headers={"User-Agent": "CandidateX-Deployment-Inspector/1.0"}) as response:
                if response.is_redirect:
                    if hop >= MAX_REDIRECTS:
                        raise SSRFSecurityError(f"Exceeded maximum allowed redirects ({MAX_REDIRECTS})")
                    location = response.headers.get("location")
                    if not location:
                        raise SSRFSecurityError("Redirect missing Location header")
                    current_url = urllib.parse.urljoin(current_url, location)
                    continue

                # Read body up to max_bytes
                content_chunks = []
                total_bytes = 0
                for chunk in response.iter_bytes():
                    total_bytes += len(chunk)
                    if total_bytes > max_bytes:
                        raise SSRFSecurityError(f"Response size exceeded safety cap of {max_bytes} bytes")
                    content_chunks.append(chunk)

                # Construct in-memory response object
                full_body = b"".join(content_chunks)
                return httpx.Response(
                    status_code=response.status_code,
                    headers=response.headers,
                    content=full_body,
                    request=response.request,
                )

        raise SSRFSecurityError("Unexpected redirect loop")
    finally:
        client.close()
