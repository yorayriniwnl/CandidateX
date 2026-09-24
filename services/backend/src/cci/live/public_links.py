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

from cci.intake.canonicalizer import classify_url, normalize_url
from cci.limits import get_system_limits
from cci.security.ssrf import resolve_and_validate_hostname, SSRFSecurityError

_sys_limits = get_system_limits()
MAX_LINKS = _sys_limits.max_urls.budget
MAX_BYTES = _sys_limits.max_page_bytes.budget
LINK_SECONDS = _sys_limits.link_timeout_seconds.budget
MAX_PDF_PAGES = _sys_limits.max_pdf_pages.budget
MAX_TEXT_CHARS = _sys_limits.max_text_chars.budget


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
        self.title, self.description, self.text, self.hrefs = [], '', [], []

    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style', 'noscript', 'template', 'svg'}:
            self.hidden += 1
        if tag == 'title':
            self.in_title = True
        values = dict(attrs)
        if tag == 'a' and values.get('href') and len(self.hrefs) < 300:
            self.hrefs.append(values['href'])
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

    parsed = urlsplit(url)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        return {**receipt, 'status': 'invalid_url', 'detail': 'Invalid URL scheme or format; only HTTP and HTTPS are permitted.'}

    from cci.cache import get_content_cache
    content_cache = get_content_cache()
    cached = content_cache.get_public_page(url)
    if cached is not None:
        return {**cached.receipt, 'cached': True}

    max_retries = 2
    for attempt in range(max_retries + 1):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return {**receipt, 'status': 'timeout', 'detail': 'Public page exceeded its time budget.'}
        try:
            # One client per supplied link; never share credentials/cookies across links or redirects.
            with httpx.Client(transport=transport or PublicTransport(), follow_redirects=False,
                              trust_env=False, headers={'User-Agent': 'CandidateX-PublicEvidence/1.0',
                              'Accept': 'text/html,text/plain,application/pdf', 'Accept-Encoding': 'identity'}) as client:
                current, redirects = url, []
                retry_needed = False
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

                        # 429: Rate limited -> backoff and retry
                        if response.status_code == 429:
                            if attempt < max_retries:
                                retry_after = response.headers.get('retry-after')
                                backoff = min(1.0, float(retry_after)) if retry_after and retry_after.isdigit() else (0.2 * (2 ** attempt))
                                if (deadline - time.monotonic()) > backoff:
                                    time.sleep(backoff)
                                    retry_needed = True
                                    break
                            return {**receipt, 'status': 'rate_limited', 'detail': 'Public page rate limit reached (HTTP 429).'}

                        # 401, 403, 999: Terminal access-restricted
                        if response.status_code in (401, 403, 999):
                            return {**receipt, 'status': 'access_restricted', 'detail': f'Login or access gate prevents public inspection (HTTP {response.status_code}).'}

                        if response.status_code != 200:
                            return {**receipt, 'detail': f'Public page returned HTTP {response.status_code}.'}

                        content_type = response.headers.get('content-type', '').lower()
                        if not any(t in content_type for t in ('text/html', 'text/plain', 'application/xhtml+xml', 'application/pdf')):
                            return {**receipt, 'status': 'unsupported_content', 'detail': 'Only public HTML, text, and digital PDFs are inspected. Images require separate verification.'}

                        content = bytearray()
                        for chunk in response.iter_bytes():
                            content.extend(chunk)
                            if len(content) > MAX_BYTES:
                                return {**receipt, 'status': 'too_large', 'detail': f'Public page exceeds the {MAX_BYTES // 1024} KB inspection limit.'}
                            if time.monotonic() >= deadline:
                                raise httpx.ReadTimeout('Time budget reached')

                        text = bytes(content).decode('utf-8', errors='replace')
                        parser = PageText()
                        try:
                            if 'application/pdf' in content_type:
                                with pymupdf.open(stream=bytes(content), filetype='pdf') as document:
                                    if document.is_encrypted or len(document) > MAX_PDF_PAGES:
                                        return {**receipt, 'status': 'unsupported_content', 'detail': f'Public PDF is encrypted or exceeds the {MAX_PDF_PAGES}-page certificate/document limit.'}
                                    title = document.metadata.get('title', '')
                                    description = ''
                                    visible = '\n'.join(page.get_text() for page in document)
                            elif 'text/plain' in content_type:
                                title, description, visible = '', '', text
                            else:
                                parser.feed(text)
                                title, description, visible = ' '.join(parser.title), parser.description, ' '.join(parser.text)
                        except Exception as parse_exc:
                            return {
                                **receipt,
                                'status': 'parser_error',
                                'detail': f'Public content could not be parsed: {parse_exc}',
                                'content_sha256': hashlib.sha256(content).hexdigest(),
                            }

                        discovered_links = []
                        if 'text/html' in content_type or 'application/xhtml+xml' in content_type:
                            current_normalized = normalize_url(current)
                            seen_links = set()
                            for href in parser.hrefs:
                                candidate = normalize_url(urljoin(current, href))
                                if not candidate or candidate == current_normalized or candidate in seen_links:
                                    continue
                                seen_links.add(candidate)
                                discovered_links.append({
                                    'url': candidate,
                                    'kind': classify_url(candidate),
                                    'discovery_reason': 'public_page_link',
                                })
                                if len(discovered_links) >= 100:
                                    break

                        excerpt = re.sub(r'\s+', ' ', visible).strip()[:MAX_TEXT_CHARS]
                        gate = re.search(r'(sign in to continue|log in to continue|verify you are human|just a moment|access denied|enable javascript and cookies)', f'{title} {excerpt[:1200]}', re.I)
                        receipt.update(title=title[:300], description=description, excerpt=excerpt,
                                        discovered_links=discovered_links,
                                        content_sha256=hashlib.sha256(content).hexdigest())
                        if gate:
                            return {**receipt, 'status': 'access_restricted', 'detail': 'The public response is a login or anti-bot gate; its content is not verification evidence.'}
                        if len(excerpt) < 40:
                            return {**receipt, 'status': 'limited_content', 'detail': 'Page is reachable but has insufficient readable text without browser scripts.'}
                        final_receipt = {**receipt, 'status': 'observed', 'verification': 'public_page_observed',
                                'detail': 'Retrieved public page text. Page claims are self-published unless independently confirmed by an issuer; no ownership or skill credit is inferred.'}
                        content_cache.put_public_page(
                            canonical_url=url,
                            content_bytes=bytes(content),
                            receipt=final_receipt,
                            etag=response.headers.get('etag'),
                            last_modified=response.headers.get('last-modified'),
                            content_type=content_type,
                            discovered_links=[d['url'] for d in discovered_links if isinstance(d, dict) and 'url' in d],
                            fetched_at=receipt.get('fetched_at'),
                        )
                        return final_receipt

                if retry_needed:
                    continue

        except SSRFSecurityError:
            return {**receipt, 'status': 'security_blocked', 'detail': 'Destination failed public-network safety validation.'}
        except httpx.TimeoutException:
            if attempt < max_retries and (deadline - time.monotonic()) > 1.0:
                time.sleep(0.2)
                continue
            return {**receipt, 'status': 'timeout', 'detail': 'Public page exceeded its time budget.'}
        except Exception:
            if attempt < max_retries and (deadline - time.monotonic()) > 1.0:
                time.sleep(0.2)
                continue
            return {**receipt, 'detail': 'Public page could not be safely retrieved or parsed.'}

    return {**receipt, 'detail': 'No inspectable public response.'}


def acquire_public_links(urls, transport=None, max_links=None, time_budget=None):
    """Acquires public web evidence using the evidence-prioritized discovery frontier (Fix 25)."""
    from cci.live.web_discovery import EvidenceDiscoveryFrontier
    limits = get_system_limits()
    raw_limit = max_links if max_links is not None else MAX_LINKS
    limit = limits.max_urls.clamp_requested(raw_limit)
    raw_budget = time_budget if time_budget is not None else LINK_SECONDS
    budget = limits.link_timeout_seconds.clamp_requested(raw_budget)
    frontier = EvidenceDiscoveryFrontier(
        max_fetched=limit,
        time_budget=budget,
        transport=transport,
    )
    for url in urls:
        frontier.add_url(url, discovery_method="seed", depth=0)
    frontier.run()
    return frontier.get_receipts()
