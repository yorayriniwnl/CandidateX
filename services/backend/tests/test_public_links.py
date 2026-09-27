import ipaddress
import time

import httpx
import pytest

from cci.live import public_links as links
from cci.security.ssrf import SSRFSecurityError


def test_transport_pins_destination_and_preserves_tls_name(monkeypatch):
    monkeypatch.setattr(links, 'resolve_and_validate_hostname', lambda host: [ipaddress.ip_address('93.184.216.34')])
    transport = links.PublicTransport()
    transport.transport.close()
    def handle(req):
        assert req.url.host == '93.184.216.34'
        assert req.headers['host'] == 'example.com'
        assert req.extensions['sni_hostname'] == 'example.com'
        return httpx.Response(200, text='public')
    transport.transport = httpx.MockTransport(handle)
    with httpx.Client(transport=transport) as client:
        assert client.get('https://example.com/cert').status_code == 200


@pytest.mark.parametrize('url', ['http://localhost/', 'http://127.0.0.1/', 'http://169.254.169.254/',
    'http://[::1]/', 'https://user:pass@example.com/', 'http://example.com:3000/', 'file:///tmp/x'])
def test_private_or_credential_urls_blocked(url):
    result = links.inspect_link(url, time.monotonic() + 5)
    assert result['status'] in {'security_blocked', 'unavailable'}


def test_redirect_to_private_address_never_sent(monkeypatch):
    calls = []
    def resolve(host):
        if host != 'example.com':
            raise SSRFSecurityError('private')
        return [ipaddress.ip_address('93.184.216.34')]
    monkeypatch.setattr(links, 'resolve_and_validate_hostname', resolve)
    transport = links.PublicTransport()
    transport.transport.close()
    def handle(req):
        calls.append(req.url)
        return httpx.Response(302, headers={'location': 'http://169.254.169.254/latest/meta-data'})
    transport.transport = httpx.MockTransport(handle)
    assert links.inspect_link('https://example.com', time.monotonic() + 5, transport)['status'] == 'security_blocked'
    assert len(calls) == 1


def test_mixed_public_private_dns_never_connects(monkeypatch):
    monkeypatch.setattr(links, 'resolve_and_validate_hostname', lambda host: [
        ipaddress.ip_address('93.184.216.34'), ipaddress.ip_address('127.0.0.1')])
    transport = links.PublicTransport()
    transport.transport.close()
    def forbidden(req):
        pytest.fail('A mixed DNS answer reached the network')
    transport.transport = httpx.MockTransport(forbidden)
    assert links.inspect_link('https://example.com', time.monotonic() + 5, transport)['status'] == 'security_blocked'


def test_page_content_is_observation_not_credential_verification():
    transport = httpx.MockTransport(lambda req: httpx.Response(200, headers={'content-type': 'text/html'},
        text='<title>Python Certificate</title><script>SECRET</script><p>Awarded to Example Candidate for completing the Python course.</p>'))
    result = links.inspect_link('https://coursera.org/verify/abc', time.monotonic() + 5, transport)
    assert result['status'] == 'observed'
    assert result['verification'] == 'public_page_observed'
    assert 'SECRET' not in result['excerpt']
    assert result['kind'] == 'credential'


def test_large_pages_gates_and_unscanned_links_are_explicit(monkeypatch):
    transport = httpx.MockTransport(lambda req: httpx.Response(200, headers={'content-type': 'text/html'}, text='x' * (links.MAX_BYTES + 1)))
    assert links.inspect_link('https://example.com', time.monotonic() + 5, transport)['status'] == 'too_large'
    monkeypatch.setattr(links, 'MAX_LINKS', 0)
    assert links.acquire_public_links(['https://example.com'])[0]['status'] == 'not_scanned'


def test_public_digital_certificate_pdf_text_is_inspected():
    import pymupdf
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((50, 50), 'Example Candidate completed the Python Programming Course Certificate.')
        content = document.tobytes()
    transport = httpx.MockTransport(lambda req: httpx.Response(200, headers={'content-type': 'application/pdf'}, content=content))
    result = links.inspect_link('https://issuer.example/certificate.pdf', time.monotonic() + 5, transport)
    assert result['status'] == 'observed'
    assert 'Example Candidate' in result['excerpt']
    assert result['verification'] == 'public_page_observed'

def test_html_discovery_retains_canonical_outbound_links():
    transport = httpx.MockTransport(lambda req: httpx.Response(
        200,
        headers={'content-type': 'text/html'},
        text='''<html><head><title>Portfolio</title></head><body>
        <a href="/projects/candidatex?utm_source=cv#demo">CandidateX</a>
        <a href="https://github.com/example/project">Source</a>
        <a href="https://github.com/example/project#readme">Duplicate source</a>
        <a href="mailto:person@example.com">Email</a>
        <p>Public portfolio evidence.</p>
        </body></html>''',
    ))
    result = links.inspect_link('https://example.com/portfolio', time.monotonic() + 5, transport)
    assert result['status'] == 'observed'
    discovered = result['discovered_links']
    assert discovered == [
        {'url': 'https://example.com/projects/candidatex', 'kind': 'project', 'discovery_reason': 'public_page_link'},
        {'url': 'https://github.com/example/project', 'kind': 'github', 'discovery_reason': 'public_page_link'},
    ]
