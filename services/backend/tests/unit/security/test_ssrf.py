import pytest
import ipaddress
import socket
import httpx
from unittest.mock import patch, MagicMock
from cci.security.ssrf import (
    SSRFSecurityError,
    is_ip_restricted,
    resolve_and_validate_hostname,
    validate_safe_url,
    safe_http_get,
)

def test_is_ip_restricted():
    assert is_ip_restricted(ipaddress.ip_address("127.0.0.1"))
    assert not is_ip_restricted(ipaddress.ip_address("8.8.8.8"))

def test_resolve_and_validate_hostname_direct_ip():
    with pytest.raises(SSRFSecurityError, match="Restricted direct IP address"):
        resolve_and_validate_hostname("127.0.0.1")
    ips = resolve_and_validate_hostname("8.8.8.8")
    assert ips == [ipaddress.ip_address("8.8.8.8")]

@patch("socket.getaddrinfo")
def test_resolve_and_validate_hostname_valid(mock_getaddrinfo):
    mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 0)), (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("not-an-ip", 0))]
    ips = resolve_and_validate_hostname("example.com")
    assert len(ips) == 1

@patch("socket.getaddrinfo")
def test_resolve_and_validate_hostname_empty(mock_getaddrinfo):
    mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("not-an-ip", 0))]
    with pytest.raises(SSRFSecurityError, match="Could not resolve any valid IP"):
        resolve_and_validate_hostname("example.com")

@patch("socket.getaddrinfo")
def test_resolve_and_validate_hostname_invalid(mock_getaddrinfo):
    mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0))]
    with pytest.raises(SSRFSecurityError, match="restricted IP"):
        resolve_and_validate_hostname("example.com")

def test_resolve_and_validate_hostname_prohibited():
    with pytest.raises(SSRFSecurityError, match="Prohibited hostname"):
        resolve_and_validate_hostname("localhost")

@patch("socket.getaddrinfo")
def test_resolve_and_validate_hostname_socket_error(mock_getaddrinfo):
    mock_getaddrinfo.side_effect = socket.gaierror("Name or service not known")
    with pytest.raises(SSRFSecurityError, match="DNS resolution failed"):
        resolve_and_validate_hostname("invalid.domain.xyz")

@patch("socket.getaddrinfo")
def test_validate_safe_url(mock_getaddrinfo):
    mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 0))]
    assert validate_safe_url("https://example.com/path?q=1") == "https://example.com/path?q=1"
    
    with pytest.raises(SSRFSecurityError, match="Prohibited URL scheme"):
        validate_safe_url("ftp://example.com")
    with pytest.raises(SSRFSecurityError, match="Missing host authority"):
        validate_safe_url("https://")
    with pytest.raises(SSRFSecurityError, match="Invalid or missing hostname"):
        validate_safe_url("https://@/path")
    with pytest.raises(SSRFSecurityError, match="Prohibited destination port"):
        validate_safe_url("https://example.com:22")

@patch("cci.security.ssrf.httpx.Client")
@patch("cci.security.ssrf.validate_safe_url")
def test_safe_http_get(mock_validate, mock_client_cls):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_stream = MagicMock()
    mock_response = MagicMock()
    mock_response.is_redirect = False
    mock_response.status_code = 200
    mock_response.headers = httpx.Headers({})
    mock_response.iter_bytes.return_value = [b"chunk"]
    mock_stream.__enter__.return_value = mock_response
    mock_client.stream.return_value = mock_stream
    
    resp = safe_http_get("https://example.com")
    assert resp.content == b"chunk"

@patch("cci.security.ssrf.httpx.Client")
@patch("cci.security.ssrf.validate_safe_url")
def test_safe_http_get_size_limit(mock_validate, mock_client_cls):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_stream = MagicMock()
    mock_response = MagicMock()
    mock_response.is_redirect = False
    mock_response.iter_bytes.return_value = [b"A" * 6000000]
    mock_stream.__enter__.return_value = mock_response
    mock_client.stream.return_value = mock_stream
    
    with pytest.raises(SSRFSecurityError, match="Response size exceeded safety cap"):
        safe_http_get("https://example.com")

@patch("cci.security.ssrf.httpx.Client")
@patch("cci.security.ssrf.validate_safe_url")
def test_safe_http_get_redirects(mock_validate, mock_client_cls):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    
    # First response: redirect
    mock_resp1 = MagicMock()
    mock_resp1.is_redirect = True
    mock_resp1.headers = httpx.Headers({"location": "https://example.com/2"})
    
    # Second response: ok
    mock_resp2 = MagicMock()
    mock_resp2.is_redirect = False
    mock_resp2.status_code = 200
    mock_resp2.headers = httpx.Headers({})
    mock_resp2.iter_bytes.return_value = [b"ok"]
    
    stream_mock1 = MagicMock()
    stream_mock1.__enter__.return_value = mock_resp1
    stream_mock2 = MagicMock()
    stream_mock2.__enter__.return_value = mock_resp2
    
    mock_client.stream.side_effect = [stream_mock1, stream_mock2]
    
    resp = safe_http_get("https://example.com")
    assert resp.content == b"ok"
    
@patch("cci.security.ssrf.httpx.Client")
@patch("cci.security.ssrf.validate_safe_url")
def test_safe_http_get_redirect_missing_location(mock_validate, mock_client_cls):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_resp1 = MagicMock()
    mock_resp1.is_redirect = True
    mock_resp1.headers = httpx.Headers({})
    stream_mock1 = MagicMock()
    stream_mock1.__enter__.return_value = mock_resp1
    mock_client.stream.return_value = stream_mock1
    
    with pytest.raises(SSRFSecurityError, match="Redirect missing Location header"):
        safe_http_get("https://example.com")

@patch("cci.security.ssrf.httpx.Client")
@patch("cci.security.ssrf.validate_safe_url")
def test_safe_http_get_too_many_redirects(mock_validate, mock_client_cls):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_resp1 = MagicMock()
    mock_resp1.is_redirect = True
    mock_resp1.headers = httpx.Headers({"location": "https://example.com/loop"})
    stream_mock1 = MagicMock()
    stream_mock1.__enter__.return_value = mock_resp1
    
    # Mock stream to always return the redirect response
    mock_client.stream.return_value = stream_mock1
    
    with pytest.raises(SSRFSecurityError, match="Exceeded maximum allowed redirects"):
        safe_http_get("https://example.com")
