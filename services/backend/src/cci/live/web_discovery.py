"""Evidence-prioritized web discovery frontier (Fix 25).

Replaces blind recursive crawling with a structured, priority-scored discovery frontier.
Invariants:
- Never executes candidate or untrusted code.
- Strict SSRF safety: public HTTP(S) only, validated non-private IPs, no proxy bypass.
- Strictly bounded: maximum depth, per-domain limits, total fetch cap, and time budget.
- Every discovered URL reaches a deterministic terminal state:
  * fetched
  * deferred
  * blocked
  * irrelevant
  * inaccessible
  * failed
  * not_scanned
- Filters irrelevant navigation (privacy, terms, social share, login, tracking, marketing, footer).
- Prioritizes credential issuers, project pages, repositories, deployments, technical docs, publications, and coding profiles.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import re
import time
from typing import Any, Mapping, Sequence
from urllib.parse import urljoin, urlparse, urlsplit

import httpx
import pymupdf

from cci.intake.canonicalizer import normalize_url
from cci.limits import get_system_limits
from cci.security.ssrf import resolve_and_validate_hostname, SSRFSecurityError

_sys_limits = get_system_limits()
MAX_DISCOVERY_FETCHED = _sys_limits.max_urls.budget
MAX_DISCOVERY_DEPTH = 2
MAX_PER_DOMAIN = 3
MAX_PAGE_BYTES = _sys_limits.max_page_bytes.budget
DEFAULT_TIME_BUDGET_SECONDS = float(_sys_limits.link_timeout_seconds.budget)
MAX_PDF_PAGES = _sys_limits.max_pdf_pages.budget
MAX_TEXT_CHARS = _sys_limits.max_text_chars.budget

TERMINAL_STATES = {
    "fetched",
    "deferred",
    "blocked",
    "irrelevant",
    "inaccessible",
    "failed",
    "not_scanned",
    "timeout",
    "rate_limited",
    "parser_error",
}

SOURCE_CATEGORIES = {
    "credential_issuer",
    "project_page",
    "repository",
    "deployment",
    "technical_docs",
    "publication",
    "coding_profile",
    "general_web",
    "irrelevant_nav",
}

# Irrelevant navigation patterns
IRRELEVANT_PATH_PATTERNS = {
    "privacy": re.compile(
        r"/(?:privacy(?:-policy)?|cookie(?:-policy)?|gdpr|data-protection)(?:[/?#]|$)",
        re.IGNORECASE,
    ),
    "terms": re.compile(
        r"/(?:terms(?:-of-service|-and-conditions)?|tos|legal|disclaimer|user-agreement)(?:[/?#]|$)",
        re.IGNORECASE,
    ),
    "login": re.compile(
        r"/(?:login|sign-?in|sign-?up|register|auth(?:entication)?|oauth|account/(?:login|register)|wp-login\.php|user/login)(?:[/?#]|$)",
        re.IGNORECASE,
    ),
    "tracking": re.compile(
        r"/(?:pixel|tracking|collect|telemetry|analytics)(?:[/?#]|$)",
        re.IGNORECASE,
    ),
    "marketing_nav": re.compile(
        r"/(?:pricing|plans|sales|features|enterprise|contact(?:-us)?|about-us|press|careers|jobs|advertise)(?:[/?#]|$)",
        re.IGNORECASE,
    ),
    "unrelated_footer": re.compile(
        r"/(?:sitemap(?:\.xml)?|accessibility|bug-bounty|status|help|faq)(?:[/?#]|$)",
        re.IGNORECASE,
    ),
}

IRRELEVANT_DOMAINS = {
    "doubleclick.net",
    "google-analytics.com",
    "googletagmanager.com",
    "hotjar.com",
    "stats.wp.com",
    "facebook.com",
    "api.whatsapp.com",
    "t.me",
}

SOCIAL_SHARE_PATTERNS = re.compile(
    r"(?:twitter\.com/(?:intent/tweet|share)|x\.com/intent|facebook\.com/sharer|linkedin\.com/(?:shareArticle|sharing)|reddit\.com/submit|api\.whatsapp\.com/send|t\.me/share)",
    re.IGNORECASE,
)

# Prioritized platform & evidence patterns
CREDENTIAL_ISSUER_DOMAINS = {
    "credly.com",
    "coursera.org",
    "udacity.com",
    "badges.parchment.com",
    "hackerrank.com",
    "freecodecamp.org",
    "trailhead.salesforce.com",
    "verify.skilljar.com",
    "acclaim.com",
    "certmetrics.com",
}

DEPLOYMENT_DOMAINS_SUFFIX = (
    ".vercel.app",
    ".netlify.app",
    ".herokuapp.com",
    ".fly.dev",
    ".railway.app",
    ".render.com",
    ".pages.dev",
    ".surge.sh",
)

REPOSITORY_DOMAINS = {
    "github.com",
    "gitlab.com",
    "bitbucket.org",
    "codeberg.org",
}

CODING_PROFILE_DOMAINS = {
    "leetcode.com",
    "kaggle.com",
    "codeforces.com",
    "topcoder.com",
    "codechef.com",
    "stackoverflow.com",
}

PUBLICATION_DOMAINS = {
    "arxiv.org",
    "doi.org",
    "dev.to",
    "medium.com",
    "substack.com",
    "researchgate.net",
    "scholar.google.com",
    "acm.org",
    "ieee.org",
}


def is_irrelevant_navigation(url: str) -> tuple[bool, str]:
    """Determines whether a URL represents deprioritized or irrelevant navigation."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    path = parsed.path

    if SOCIAL_SHARE_PATTERNS.search(url):
        return True, "social_share"

    if any(domain == d or domain.endswith("." + d) for d in IRRELEVANT_DOMAINS):
        return True, "tracking"

    for cat, pattern in IRRELEVANT_PATH_PATTERNS.items():
        if pattern.search(path):
            return True, cat

    return False, ""


def classify_source_category(url: str) -> tuple[str, float, str]:
    """Classifies a URL into an evidence category with base relevance score and priority."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    path = parsed.path.lower()

    # 1. Credential issuer
    if (
        any(domain == d or domain.endswith("." + d) for d in CREDENTIAL_ISSUER_DOMAINS)
        or re.search(r"/(?:certificates?|certifications?|credentials?|verify|badges)(?:[/. -]|$)", path)
    ):
        return "credential_issuer", 95.0, "high"

    # 2. Technical documentation (check before generic project domains)
    if (
        domain.startswith("docs.")
        or domain.endswith(".readthedocs.io")
        or domain.endswith(".gitbook.io")
        or re.search(r"/(?:docs|documentation|api-docs|swagger|redoc|reference)(?:[/. -]|$)", path)
    ):
        return "technical_docs", 80.0, "high"

    # 3. Project page / demo
    if (
        re.search(r"/(?:projects?|portfolio|work|demo|showcase|apps?)(?:[/. -]|$)", path)
        or any(domain.startswith(k + ".") for k in ("portfolio", "demo", "project"))
        or any(domain.endswith("." + k) for k in ("portfolio", "demo", "project"))
    ):
        return "project_page", 88.0, "high"

    # 4. Repository link
    if any(domain == d or domain.endswith("." + d) for d in REPOSITORY_DOMAINS):
        parts = [p for p in path.strip("/").split("/") if p]
        if len(parts) >= 2:
            return "repository", 82.0, "high"

    # 5. Deployment link
    if any(domain.endswith(suffix) for suffix in DEPLOYMENT_DOMAINS_SUFFIX):
        return "deployment", 82.0, "high"

    # 6. Publication links
    if (
        any(domain == d or domain.endswith("." + d) for d in PUBLICATION_DOMAINS)
        or re.search(r"/(?:papers?|publications?|articles?)(?:[/. -]|$)", path)
    ):
        return "publication", 72.0, "medium"

    # 7. Coding profiles
    if any(domain == d or domain.endswith("." + d) for d in CODING_PROFILE_DOMAINS):
        return "coding_profile", 68.0, "medium"

    # 8. General web
    return "general_web", 40.0, "low"


def is_ip_private_or_blocked(hostname: str) -> bool:
    """Checks if hostname is localhost or a non-global IP literal."""
    import ipaddress
    clean_host = (hostname or "").strip().lower()
    if not clean_host or clean_host in {"localhost", "::1"}:
        return True
    try:
        ip = ipaddress.ip_address(clean_host)
        return not ip.is_global
    except ValueError:
        return False


@dataclass
class FrontierItem:
    """A tracked URL within the evidence discovery frontier.

    Maintains all 11 required frontier attributes:
    1. original_url
    2. canonical_url
    3. parent_source
    4. discovery_method
    5. depth
    6. domain
    7. source_category
    8. relevance_score
    9. fetch_status
    10. priority
    11. discovered_at
    """

    original_url: str
    canonical_url: str
    parent_source: str | None
    discovery_method: str
    depth: int
    domain: str
    source_category: str
    relevance_score: float
    fetch_status: str  # Terminal state
    priority: str
    discovered_at: str
    detail: str = ""
    receipt: dict[str, Any] = field(default_factory=dict)

    def to_source_dict(self) -> dict[str, Any]:
        """Converts frontier item into a standard live source receipt dict."""
        out = {
            "url": self.canonical_url,
            "original_url": self.original_url,
            "canonical_url": self.canonical_url,
            "parent_source": self.parent_source,
            "discovery_method": self.discovery_method,
            "depth": self.depth,
            "domain": self.domain,
            "source_category": self.source_category,
            "kind": self.source_category,
            "relevance_score": round(self.relevance_score, 2),
            "fetch_status": self.fetch_status,
            "priority": self.priority,
            "discovered_at": self.discovered_at,
            "status": "observed" if self.fetch_status == "fetched" else "not_scanned" if self.fetch_status in ("deferred", "not_scanned") else self.fetch_status,
            "detail": self.detail or self.receipt.get("detail", ""),
        }
        if self.receipt:
            for k in ("title", "description", "excerpt", "content_sha256", "discovered_links", "http_status", "final_url", "redirects"):
                if k in self.receipt:
                    out[k] = self.receipt[k]
        return out


class PublicPageParser(HTMLParser):
    """Safe HTML parser extracting visible text, metadata, and candidate anchor links."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = 0
        self.in_title = False
        self.title: list[str] = []
        self.description = ""
        self.text: list[str] = []
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        if tag in {"script", "style", "noscript", "template", "svg"}:
            self.hidden += 1
        if tag == "title":
            self.in_title = True
        values = dict(attrs)
        if tag == "a" and values.get("href") and len(self.hrefs) < 300:
            self.hrefs.append(str(values["href"]))
        if tag == "meta" and str(values.get("name", "")).lower() == "description":
            self.description = str(values.get("content", ""))[:1000]

    def handle_endtag(self, tag: str):
        if tag in {"script", "style", "noscript", "template", "svg"}:
            self.hidden = max(0, self.hidden - 1)
        if tag == "title":
            self.in_title = False

    def handle_data(self, data: str):
        if self.hidden:
            return
        if self.in_title:
            self.title.append(data)
        elif data.strip():
            self.text.append(data.strip())


class EvidenceDiscoveryFrontier:
    """Frontier queue for evidence-prioritized web discovery (Fix 25)."""

    def __init__(
        self,
        *,
        max_fetched: int = MAX_DISCOVERY_FETCHED,
        max_depth: int = MAX_DISCOVERY_DEPTH,
        max_per_domain: int = MAX_PER_DOMAIN,
        time_budget: float = DEFAULT_TIME_BUDGET_SECONDS,
        transport: httpx.BaseTransport | None = None,
    ):
        limits = get_system_limits()
        self.max_fetched = limits.max_urls.clamp_requested(max_fetched) if max_fetched is not None else MAX_DISCOVERY_FETCHED
        self.max_depth = max_depth
        self.max_per_domain = max_per_domain
        self.time_budget = float(limits.link_timeout_seconds.clamp_requested(int(time_budget))) if time_budget is not None else DEFAULT_TIME_BUDGET_SECONDS
        self.transport = transport

        self.frontier: dict[str, FrontierItem] = {}
        self.queued_keys: list[str] = []
        self.fetched_count = 0
        self.domain_counts: dict[str, int] = {}

    def add_url(
        self,
        url: str,
        *,
        parent_source: str | None = None,
        discovery_method: str = "seed",
        depth: int = 0,
    ) -> FrontierItem | None:
        """Evaluates and admits a discovered URL into the frontier."""
        canonical = normalize_url(url)
        now_iso = datetime.now(timezone.utc).isoformat()

        if not canonical:
            failed_item = FrontierItem(
                original_url=url,
                canonical_url=url,
                parent_source=parent_source,
                discovery_method=discovery_method,
                depth=depth,
                domain="",
                source_category="general_web",
                relevance_score=0.0,
                fetch_status="failed",
                priority="low",
                discovered_at=now_iso,
                detail="Invalid or unparseable URL scheme/structure.",
            )
            self.frontier[url] = failed_item
            return failed_item

        # Deduplication: if canonical URL already admitted, preserve existing item
        if canonical in self.frontier:
            return self.frontier[canonical]

        parsed = urlparse(canonical)
        domain = parsed.netloc.lower()

        # 1. Filter irrelevant navigation immediately
        is_irrel, irrel_reason = is_irrelevant_navigation(canonical)
        if is_irrel:
            item = FrontierItem(
                original_url=url,
                canonical_url=canonical,
                parent_source=parent_source,
                discovery_method=discovery_method,
                depth=depth,
                domain=domain,
                source_category="irrelevant_nav",
                relevance_score=0.0,
                fetch_status="irrelevant",
                priority="irrelevant",
                discovered_at=now_iso,
                detail=f"Filtered irrelevant navigation ({irrel_reason}).",
            )
            self.frontier[canonical] = item
            return item

        # 2. SSRF Pre-validation: check for private/loopback IP literal or localhost
        if is_ip_private_or_blocked(parsed.hostname or ""):
            item = FrontierItem(
                original_url=url,
                canonical_url=canonical,
                parent_source=parent_source,
                discovery_method=discovery_method,
                depth=depth,
                domain=domain,
                source_category="general_web",
                relevance_score=0.0,
                fetch_status="blocked",
                priority="low",
                discovered_at=now_iso,
                detail="Blocked: destination failed public-network SSRF safety validation (private IP or localhost).",
            )
            self.frontier[canonical] = item
            return item

        # 3. Categorize and compute priority & relevance score with depth decay
        category, base_score, priority = classify_source_category(canonical)
        relevance_score = base_score * (0.85 ** depth)

        # 4. Check if max depth exceeded
        if depth > self.max_depth:
            item = FrontierItem(
                original_url=url,
                canonical_url=canonical,
                parent_source=parent_source,
                discovery_method=discovery_method,
                depth=depth,
                domain=domain,
                source_category=category,
                relevance_score=relevance_score,
                fetch_status="deferred",
                priority=priority,
                discovered_at=now_iso,
                detail=f"Exceeded maximum crawl depth ({self.max_depth}).",
            )
            self.frontier[canonical] = item
            return item

        item = FrontierItem(
            original_url=url,
            canonical_url=canonical,
            parent_source=parent_source,
            discovery_method=discovery_method,
            depth=depth,
            domain=domain,
            source_category=category,
            relevance_score=relevance_score,
            fetch_status="queued",  # Internal state prior to execution
            priority=priority,
            discovered_at=now_iso,
        )
        self.frontier[canonical] = item
        self.queued_keys.append(canonical)
        return item

    def _fetch_url(self, item: FrontierItem, deadline: float) -> tuple[str, str, dict[str, Any], list[str]]:
        """Safely fetches a single URL via SSRF-pinned HTTP client.

        Returns (terminal_status, detail, receipt, discovered_raw_links).
        """
        from cci.live.public_links import PublicTransport

        transport = self.transport or PublicTransport()
        discovered_links: list[str] = []
        receipt: dict[str, Any] = {
            "url": item.canonical_url,
            "kind": item.source_category,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

        if time.monotonic() >= deadline:
            return "not_scanned", "Time budget reached before fetch started.", receipt, []

        max_retries = 2
        for attempt in range(max_retries + 1):
            if time.monotonic() >= deadline:
                return "timeout", "Time budget reached before fetch completed.", receipt, []

            try:
                with httpx.Client(
                    transport=transport,
                    follow_redirects=False,
                    trust_env=False,
                    headers={
                        "User-Agent": "CandidateX-PublicEvidence/1.0",
                        "Accept": "text/html,text/plain,application/pdf",
                        "Accept-Encoding": "identity",
                    },
                ) as client:
                    current = item.canonical_url
                    redirects: list[str] = []
                    retry_needed = False

                    for hop in range(4):
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            return "timeout", "Time budget expired during redirection.", receipt, []

                        client.cookies.clear()
                        with client.stream("GET", current, timeout=min(4.0, remaining)) as response:
                            receipt.update(http_status=response.status_code, final_url=current, redirects=redirects)

                            if response.is_redirect:
                                if hop == 3 or not response.headers.get("location"):
                                    return "failed", "Redirect limit exceeded or missing destination.", receipt, []
                                current = urljoin(current, response.headers["location"])
                                redirects.append(current)
                                continue

                            # 429: Rate limited -> backoff and retry
                            if response.status_code == 429:
                                if attempt < max_retries:
                                    retry_after = response.headers.get("retry-after")
                                    backoff = min(2.0, float(retry_after)) if retry_after and retry_after.isdigit() else (0.2 * (2 ** attempt))
                                    if (deadline - time.monotonic()) > backoff:
                                        time.sleep(backoff)
                                        retry_needed = True
                                        break
                                return (
                                    "rate_limited",
                                    "Public page rate limit reached (HTTP 429).",
                                    receipt,
                                    [],
                                )

                            # 401, 403, 999: Terminal access-restricted (no retry)
                            if response.status_code in (401, 403, 999):
                                return (
                                    "inaccessible",
                                    f"Access restricted: HTTP {response.status_code} (login, authentication, or provider gate).",
                                    receipt,
                                    [],
                                )

                            # Terminal 4xx / 5xx (except 429/401/403)
                            if response.status_code >= 400:
                                return (
                                    "failed",
                                    f"Public page returned HTTP {response.status_code}.",
                                    receipt,
                                    [],
                                )

                            content_type = response.headers.get("content-type", "").lower()
                            if not any(t in content_type for t in ("text/html", "text/plain", "application/xhtml+xml", "application/pdf")):
                                return (
                                    "failed",
                                    "Unsupported content type: only HTML, plain text, and digital PDFs are inspected.",
                                    receipt,
                                    [],
                                )

                            content = bytearray()
                            for chunk in response.iter_bytes():
                                content.extend(chunk)
                                if len(content) > MAX_PAGE_BYTES:
                                    return (
                                        "failed",
                                        f"Page size exceeds maximum inspection limit ({MAX_PAGE_BYTES} bytes).",
                                        receipt,
                                        [],
                                    )
                                if time.monotonic() >= deadline:
                                    return "timeout", "Time budget expired during streaming.", receipt, []

                            raw_bytes = bytes(content)
                            text = raw_bytes.decode("utf-8", errors="replace")
                            parser = PublicPageParser()

                            try:
                                if "application/pdf" in content_type:
                                    with pymupdf.open(stream=raw_bytes, filetype="pdf") as document:
                                        if document.is_encrypted or len(document) > MAX_PDF_PAGES:
                                            return (
                                                "failed",
                                                f"PDF is encrypted or exceeds {MAX_PDF_PAGES}-page inspection limit.",
                                                receipt,
                                                [],
                                            )
                                        title = document.metadata.get("title", "")
                                        description = ""
                                        visible = "\n".join(page.get_text() for page in document)
                                elif "text/plain" in content_type:
                                    title, description, visible = "", "", text
                                else:
                                    parser.feed(text)
                                    title, description, visible = " ".join(parser.title), parser.description, " ".join(parser.text)
                                    discovered_links = parser.hrefs[:100]
                            except Exception as parse_exc:
                                receipt.update(content_sha256=hashlib.sha256(raw_bytes).hexdigest())
                                return (
                                    "parser_error",
                                    f"Public content could not be parsed: {parse_exc}",
                                    receipt,
                                    [],
                                )

                            excerpt = re.sub(r"\s+", " ", visible).strip()[:MAX_TEXT_CHARS]
                            gate = re.search(
                                r"(sign in to continue|log in to continue|verify you are human|just a moment|access denied|enable javascript and cookies)",
                                f"{title} {excerpt[:1200]}",
                                re.I,
                            )
                            receipt.update(
                                title=title[:300],
                                description=description,
                                excerpt=excerpt,
                                content_sha256=hashlib.sha256(raw_bytes).hexdigest(),
                            )

                            if gate:
                                return (
                                    "inaccessible",
                                    "Response is a login or anti-bot verification gate.",
                                    receipt,
                                    [],
                                )

                            if len(excerpt) < 40:
                                return (
                                    "failed",
                                    "Page has insufficient readable text without browser scripts.",
                                    receipt,
                                    [],
                                )

                            # Terminal state: fetched
                            return "fetched", "Successfully inspected public page.", receipt, discovered_links

                    if retry_needed:
                        continue

            except SSRFSecurityError as exc:
                return "blocked", f"SSRF security violation: {exc}", receipt, []
            except (httpx.TimeoutException, TimeoutError):
                if attempt < max_retries and (deadline - time.monotonic()) > 1.0:
                    time.sleep(0.2)
                    continue
                return "timeout", "Request timed out.", receipt, []
            except Exception as exc:
                if attempt < max_retries and (deadline - time.monotonic()) > 1.0:
                    time.sleep(0.2)
                    continue
                return "failed", f"Inspection failed: {exc}", receipt, []

        return "failed", "No inspectable response.", receipt, []

    def run(self) -> list[FrontierItem]:
        """Executes evidence discovery across the prioritized frontier until termination."""
        deadline = time.monotonic() + self.time_budget
        attempted_count = 0

        while self.queued_keys and attempted_count < self.max_fetched:
            if time.monotonic() >= deadline:
                break

            # Sort remaining queued items by relevance_score descending
            self.queued_keys.sort(key=lambda k: self.frontier[k].relevance_score, reverse=True)
            canonical = self.queued_keys.pop(0)
            item = self.frontier[canonical]

            # Domain budget check
            domain = item.domain
            if self.domain_counts.get(domain, 0) >= self.max_per_domain:
                item.fetch_status = "deferred"
                item.detail = f"Deferred: domain fetch cap ({self.max_per_domain}) reached for {domain}."
                continue

            status, detail, receipt, discovered_links = self._fetch_url(item, deadline)
            item.fetch_status = status
            item.detail = detail
            item.receipt = receipt
            attempted_count += 1

            if status == "fetched":
                self.fetched_count += 1
                self.domain_counts[domain] = self.domain_counts.get(domain, 0) + 1

                # Dynamic frontier expansion: admit newly discovered links if within depth limit
                if item.depth < self.max_depth:
                    for raw_href in discovered_links:
                        candidate_url = urljoin(item.canonical_url, raw_href)
                        self.add_url(
                            candidate_url,
                            parent_source=item.canonical_url,
                            discovery_method="public_page_link",
                            depth=item.depth + 1,
                        )

        # Terminalization of all remaining queued items
        time_expired = time.monotonic() >= deadline
        for k in self.queued_keys:
            rem_item = self.frontier[k]
            if rem_item.fetch_status == "queued":
                if time_expired:
                    rem_item.fetch_status = "not_scanned"
                    rem_item.detail = "Not scanned: time budget expired before processing."
                else:
                    rem_item.fetch_status = "deferred"
                    rem_item.detail = f"Deferred: frontier fetch cap ({self.max_fetched}) reached."

        # Safety verification: ensure every single item reached a valid terminal state
        for item in self.frontier.values():
            if item.fetch_status not in TERMINAL_STATES:
                item.fetch_status = "deferred"
                item.detail = "Deferred by frontier completion safeguard."

        return list(self.frontier.values())

    def get_receipts(self) -> list[dict[str, Any]]:
        """Returns standard live receipts for all frontier items."""
        return [item.to_source_dict() for item in self.frontier.values()]
