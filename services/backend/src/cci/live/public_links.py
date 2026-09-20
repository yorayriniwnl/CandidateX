"""Bounded public page inspection. Remote content is data, never instructions or code."""
import hashlib
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import httpx
import pymupdf

from cci.intake.canonicalizer import classify_url
from cci.security.ssrf import resolve_and_validate_hostname, SSRFSecurityError

MAX_LINKS = 24
MAX_BYTES = 512 * 1024
LINK_SECONDS = 20


class PublicTransport(httpx.BaseTransport):
    """Pin the connection to a validated address while preserving TLS SNI and Host.

    No connection reuse across hosts sharing an IP. The underlying transport never
    receives the user hostname as its connection destination and ignores proxy env.
    """
    def __init__(self):
        self.transport = httpx.HTTPTransport(trust_env=False, retries=0,
            limits=httpx.Limits(max_keepalive_connections=0))

    def handle_request(self, request):
        parsed = urlsplit(str(request.url))
        if (parsed.scheme not in {'https', 'http'} or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or parsed.port not in {None, 80, 443}):
            raise SSRFSecurityError('Only public HTTP(S) links on standard ports without credentials are allowed.')
        addresses = resolve_and_validate_hostname(parsed.hostname)
        if any(not ip.is_global for ip in addresses):
            raise SSRFSecurityError('Non-public network addresses are not allowed.')
        headers = dict(request.headers)
        headers['host'] = request.url.netloc.decode('ascii')
        pinned = httpx.Request(request.method, request.url.copy_with(host=str(addresses[0])),
            headers=headers, extensions={**request.extensions, 'sni_hostname': request.url.host})
        return self.transport.handle_request(pinned)

    def close(self):
        self.transport.close()


class PageText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = 0
        self.in_title = False
        self.title, self.description, self.text = [], '', []

    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style', 'noscript', 'template', 'svg'}:
            self.hidden += 1
        if tag == 'title':
            self.in_title = True
        values = dict(attrs)
        if tag == 'meta' and values.get('name', '').lower() == 'description':
            self.description = values.get('content', '')[:1000]

    def handle_endtag(self, tag):
        if tag in {'script', 'style', 'noscript', 'template', 'svg'}:
            self.hidden = max(0, self.hidden - 1)
        if tag == 'title':
            self.in_title = False

    def handle_data(self, data):
        if self.hidden:
            return
        if self.in_title:
            self.title.append(data)
        elif data.strip():
            self.text.append(data.strip())


def inspect_link(url, deadline, transport=None):
    receipt = {'url': url, 'kind': classify_url(url), 'status': 'unavailable',
               'fetched_at': datetime.now(timezone.utc).isoformat(), 'verification': 'not_verified'}
    if time.monotonic() >= deadline:
        return {**receipt, 'status': 'not_scanned', 'detail': 'Public-link time budget reached.'}
    try:
        # One client per supplied link; never share credentials/cookies across links or redirects.
        with httpx.Client(transport=transport or PublicTransport(), follow_redirects=False,
                          trust_env=False, headers={'User-Agent': 'CandidateX-PublicEvidence/1.0',
                          'Accept': 'text/html,text/plain,application/pdf', 'Accept-Encoding': 'identity'}) as client:
            current, redirects = url, []
            for hop in range(4):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise httpx.ReadTimeout('Time budget reached')
                client.cookies.clear()
                with client.stream('GET', current, timeout=min(4, remaining)) as response:
                    receipt.update(http_status=response.status_code, final_url=current, redirects=redirects)
                    if response.is_redirect:
                        if hop == 3 or not response.headers.get('location'):
                            return {**receipt, 'status': 'unavailable', 'detail': 'Redirect limit or missing destination.'}
                        current = urljoin(current, response.headers['location'])
                        redirects.append(current)
                        continue
                    if response.status_code in (401, 403, 429, 999):
                        return {**receipt, 'status': 'access_restricted', 'detail': 'Login, provider restriction, or rate limit prevents public inspection.'}
                    if response.status_code != 200:
                        return {**receipt, 'detail': f'Public page returned HTTP {response.status_code}.'}
                    content_type = response.headers.get('content-type', '').lower()
                    if not any(t in content_type for t in ('text/html', 'text/plain', 'application/xhtml+xml', 'application/pdf')):
                        return {**receipt, 'status': 'unsupported_content', 'detail': 'Only public HTML, text, and digital PDFs are inspected. Images require separate verification.'}
                    content = bytearray()
                    for chunk in response.iter_bytes():
                        content.extend(chunk)
                        if len(content) > MAX_BYTES:
                            return {**receipt, 'status': 'too_large', 'detail': 'Public page exceeds the 512 KB inspection limit.'}
                        if time.monotonic() >= deadline:
                            raise httpx.ReadTimeout('Time budget reached')
                    text = bytes(content).decode('utf-8', errors='replace')
                    parser = PageText()
                    if 'application/pdf' in content_type:
                        with pymupdf.open(stream=bytes(content), filetype='pdf') as document:
                            if document.is_encrypted or len(document) > 5:
                                return {**receipt, 'status': 'unsupported_content', 'detail': 'Public PDF is encrypted or exceeds the five-page certificate/document limit.'}
                            title = document.metadata.get('title', '')
                            description = ''
                            visible = '\n'.join(page.get_text() for page in document)
                    elif 'text/plain' in content_type:
                        title, description, visible = '', '', text
                    else:
                        parser.feed(text)
                        title, description, visible = ' '.join(parser.title), parser.description, ' '.join(parser.text)
                    excerpt = re.sub(r'\s+', ' ', visible).strip()[:12000]
                    gate = re.search(r'(sign in to continue|log in to continue|verify you are human|just a moment|access denied|enable javascript and cookies)', f'{title} {excerpt[:1200]}', re.I)
                    receipt.update(title=title[:300], description=description, excerpt=excerpt,
                                   content_sha256=hashlib.sha256(content).hexdigest())
                    if gate:
                        return {**receipt, 'status': 'access_restricted', 'detail': 'The public response is a login or anti-bot gate; its content is not verification evidence.'}
                    if len(excerpt) < 40:
                        return {**receipt, 'status': 'limited_content', 'detail': 'Page is reachable but has insufficient readable text without browser scripts.'}
                    return {**receipt, 'status': 'observed', 'verification': 'public_page_observed',
                            'detail': 'Retrieved public page text. Page claims are self-published unless independently confirmed by an issuer; no ownership or skill credit is inferred.'}
    except SSRFSecurityError:
        return {**receipt, 'status': 'security_blocked', 'detail': 'Destination failed public-network safety validation.'}
    except httpx.TimeoutException:
        return {**receipt, 'status': 'timeout', 'detail': 'Public page exceeded its time budget.'}
    except Exception:
        return {**receipt, 'detail': 'Public page could not be safely retrieved or parsed.'}
    return {**receipt, 'detail': 'No inspectable public response.'}


def acquire_public_links(urls):
    unique = list(dict.fromkeys(urls))
    deadline = time.monotonic() + LINK_SECONDS
    with ThreadPoolExecutor(max_workers=6) as pool:
        receipts = list(pool.map(lambda url: inspect_link(url, deadline), unique[:MAX_LINKS]))
    receipts.extend({'url': url, 'kind': classify_url(url), 'status': 'not_scanned',
                     'detail': f'All links are retained; the first {MAX_LINKS} are fetched per run. Select this URL for a follow-up run.'}
                    for url in unique[MAX_LINKS:])
    return receipts
