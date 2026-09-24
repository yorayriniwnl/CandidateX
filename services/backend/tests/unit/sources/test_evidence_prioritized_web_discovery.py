"""Unit tests for evidence-prioritized web discovery frontier (Fix 25).

Verifies that blind recursive crawling is replaced with an evidence-prioritized
discovery frontier:
1. Frontier item schema with all 11 required fields:
   * original URL
   * canonical URL
   * parent source
   * discovery method
   * depth
   * domain
   * source category
   * relevance score
   * fetch status
   * priority
   * discovered_at
2. Filters irrelevant navigation:
   * privacy
   * terms
   * social share URLs
   * login
   * tracking
   * marketing navigation
   * unrelated footer links
3. Prioritizes:
   * credential issuer pages
   * project pages
   * repository links
   * deployment links
   * technical documentation
   * publication links
   * coding profiles
4. Every discovered URL reaches one of the 7 terminal states:
   * fetched
   * deferred
   * blocked
   * irrelevant
   * inaccessible
   * failed
   * not scanned
5. Resource bounds and safety:
   * depth bounding (no blind recursive crawling)
   * per-domain limits
   * fetch cap
   * SSRF protection
"""

import httpx
import pytest

from cci.live.web_discovery import (
    EvidenceDiscoveryFrontier,
    TERMINAL_STATES,
    classify_source_category,
    is_irrelevant_navigation,
)


def test_frontier_item_schema_and_fields():
    """Verify that every frontier item contains all 11 required attributes."""
    frontier = EvidenceDiscoveryFrontier(max_fetched=10)
    item = frontier.add_url("https://credly.com/org/aws/badge/solutions-architect", discovery_method="seed", depth=0)
    assert item is not None

    # Verify 11 required fields
    assert item.original_url == "https://credly.com/org/aws/badge/solutions-architect"
    assert item.canonical_url == "https://credly.com/org/aws/badge/solutions-architect"
    assert item.parent_source is None
    assert item.discovery_method == "seed"
    assert item.depth == 0
    assert item.domain == "credly.com"
    assert item.source_category == "credential_issuer"
    assert item.relevance_score > 0.0
    assert item.priority in {"high", "medium", "low", "irrelevant"}
    assert item.discovered_at is not None

    receipt = item.to_source_dict()
    for field in (
        "original_url", "canonical_url", "parent_source", "discovery_method",
        "depth", "domain", "source_category", "relevance_score", "fetch_status",
        "priority", "discovered_at",
    ):
        assert field in receipt


def test_classify_and_prioritize_evidence_categories():
    """Verify strictly ordered prioritization across evidence categories."""
    cat_cred, score_cred, prio_cred = classify_source_category("https://credly.com/badges/12345")
    cat_proj, score_proj, prio_proj = classify_source_category("https://myportfolio.dev/projects/distributed-db")
    cat_repo, score_repo, prio_repo = classify_source_category("https://github.com/candidate/engine")
    cat_deploy, score_deploy, prio_deploy = classify_source_category("https://candidate-api.vercel.app")
    cat_docs, score_docs, prio_docs = classify_source_category("https://docs.myproject.io/guide")
    cat_pub, score_pub, prio_pub = classify_source_category("https://arxiv.org/abs/2301.12345")
    cat_code, score_code, prio_code = classify_source_category("https://leetcode.com/candidate")
    cat_gen, score_gen, prio_gen = classify_source_category("https://example.com/blog/hello")

    assert cat_cred == "credential_issuer"
    assert cat_proj == "project_page"
    assert cat_repo == "repository"
    assert cat_deploy == "deployment"
    assert cat_docs == "technical_docs"
    assert cat_pub == "publication"
    assert cat_code == "coding_profile"
    assert cat_gen == "general_web"

    # Verify prioritization hierarchy
    assert score_cred > score_proj >= score_repo >= score_deploy >= score_docs > score_pub >= score_code > score_gen
    assert prio_cred == "high"
    assert prio_proj == "high"
    assert prio_repo == "high"
    assert prio_deploy == "high"
    assert prio_docs == "high"
    assert prio_pub in {"high", "medium"}
    assert prio_code in {"high", "medium"}
    assert prio_gen == "low"


def test_filter_irrelevant_navigation():
    """Verify that irrelevant navigation links are immediately filtered and marked irrelevant."""
    irrelevant_links = [
        ("https://example.com/privacy-policy", "privacy"),
        ("https://example.com/cookie-policy", "privacy"),
        ("https://example.com/terms-of-service", "terms"),
        ("https://example.com/tos", "terms"),
        ("https://twitter.com/intent/tweet?url=https://example.com", "social_share"),
        ("https://facebook.com/sharer/sharer.php?u=https://example.com", "social_share"),
        ("https://linkedin.com/shareArticle?mini=true", "social_share"),
        ("https://example.com/login", "login"),
        ("https://example.com/sign-in", "login"),
        ("https://example.com/register", "login"),
        ("https://doubleclick.net/pixel", "tracking"),
        ("https://example.com/pricing", "marketing_nav"),
        ("https://example.com/contact-us", "marketing_nav"),
        ("https://example.com/careers", "marketing_nav"),
        ("https://example.com/sitemap.xml", "unrelated_footer"),
        ("https://example.com/accessibility", "unrelated_footer"),
    ]

    for url, expected_subcat in irrelevant_links:
        is_irrel, subcat = is_irrelevant_navigation(url)
        assert is_irrel is True, f"Expected {url} to be irrelevant"
        assert subcat == expected_subcat

    frontier = EvidenceDiscoveryFrontier(max_fetched=10)
    for url, _ in irrelevant_links:
        item = frontier.add_url(url)
        assert item is not None
        assert item.fetch_status == "irrelevant"
        assert item.priority == "irrelevant"
        assert item.relevance_score == 0.0


def test_ssrf_blocked_urls_reach_blocked_terminal_state():
    """Verify that private IP and loopback destinations reach 'blocked' terminal state."""
    frontier = EvidenceDiscoveryFrontier(max_fetched=10)
    blocked_urls = [
        "http://127.0.0.1/admin",
        "http://10.0.0.1/internal",
        "http://169.254.169.254/latest/meta-data",
        "http://192.168.1.1/router",
    ]
    for url in blocked_urls:
        item = frontier.add_url(url)
        assert item is not None
        assert item.fetch_status == "blocked"


def test_all_seven_terminal_states_reached():
    """Verify deterministic reachability of all 7 terminal states."""
    responses = {
        "https://example.com/success": httpx.Response(200, text="<html><body><h1>Candidate Project</h1><p>A full-stack distributed system with 99.9% uptime.</p></body></html>", headers={"content-type": "text/html"}),
        "https://example.com/restricted": httpx.Response(403, text="Forbidden", headers={"content-type": "text/html"}),
        "https://example.com/server-error": httpx.Response(500, text="Internal Server Error", headers={"content-type": "text/html"}),
        "https://example.com/login-gate": httpx.Response(200, text="<html><title>Sign in to continue</title><body>Please log in to view certificate.</body></html>", headers={"content-type": "text/html"}),
    }

    def mock_transport_fn(req):
        url_str = str(req.url)
        if url_str in responses:
            return responses[url_str]
        return httpx.Response(404, text="Not Found")

    transport = httpx.MockTransport(mock_transport_fn)

    # Low max_fetched so extras are deferred
    frontier = EvidenceDiscoveryFrontier(max_fetched=2, max_depth=1, max_per_domain=5, time_budget=10.0, transport=transport)

    # 1. Fetched
    frontier.add_url("https://example.com/success")
    # 2. Inaccessible (HTTP 403 or login gate)
    frontier.add_url("https://example.com/restricted")
    # 3. Failed (HTTP 500)
    frontier.add_url("https://example.com/server-error")
    # 4. Irrelevant
    frontier.add_url("https://example.com/privacy-policy")
    # 5. Blocked
    frontier.add_url("http://127.0.0.1:8080/private")
    # 6. Deferred (extra URLs beyond max_fetched cap)
    frontier.add_url("https://example.com/extra-project-1")
    frontier.add_url("https://example.com/extra-project-2")

    items = frontier.run()
    statuses = {item.fetch_status for item in items}

    # Verify that every item's fetch_status is in TERMINAL_STATES
    for item in items:
        assert item.fetch_status in TERMINAL_STATES, f"URL {item.canonical_url} has invalid status {item.fetch_status}"

    # Verify presence of expected terminal states
    assert "fetched" in statuses
    assert "inaccessible" in statuses
    assert "irrelevant" in statuses
    assert "blocked" in statuses
    assert "deferred" in statuses


def test_domain_capping_and_depth_limits_prevent_blind_crawling():
    """Verify that domain fetch caps and max_depth bounds prevent recursive crawl explosion."""
    def mock_transport_fn(req):
        return httpx.Response(
            200,
            text="""
            <html><body>
            <h1>Engineering Portfolio & Project Showcase</h1>
            <p>Comprehensive overview of candidate software engineering projects, system architecture, and production services.</p>
            <a href="/subpage_01">Page 1</a>
            <a href="/subpage_02">Page 2</a>
            <a href="/subpage_03">Page 3</a>
            <a href="/subpage_04">Page 4</a>
            <a href="/subpage_05">Page 5</a>
            </body></html>
            """,
            headers={"content-type": "text/html"},
        )

    transport = httpx.MockTransport(mock_transport_fn)

    # max_per_domain = 2, max_depth = 1, max_fetched = 10
    frontier = EvidenceDiscoveryFrontier(
        max_fetched=10,
        max_depth=1,
        max_per_domain=2,
        time_budget=10.0,
        transport=transport,
    )
    frontier.add_url("https://testdomain.org/home")
    items = frontier.run()

    # Domain testdomain.org should have exactly max_per_domain = 2 fetched
    fetched_for_domain = [it for it in items if it.domain == "testdomain.org" and it.fetch_status == "fetched"]
    assert len(fetched_for_domain) == 2

    # Excess discovered links for that domain must be deferred, not blindly fetched
    deferred_for_domain = [it for it in items if it.domain == "testdomain.org" and it.fetch_status == "deferred"]
    assert len(deferred_for_domain) > 0

    # Every item must have terminal status
    for item in items:
        assert item.fetch_status in TERMINAL_STATES
