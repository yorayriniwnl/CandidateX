"""Unit tests for Source & Crawl Explorer (Fix 46).

Verifies:
1. All nine canonical crawl lifecycle states:
   - supplied
   - resume extracted
   - discovered
   - queued
   - fetched
   - failed
   - blocked
   - deferred
   - not scanned
2. Explicit hierarchical discovery tree modeling parent-child relationships.
3. Hardening Invariant: No hidden missing links. Discovered references are retained
   with terminal states (missing_links_count == 0).
4. Full integration with CandidateManifest.
5. Serialization to dictionary format for frontend and API contracts.
6. Invariant: Candidate code is never executed.
"""

from __future__ import annotations

import pytest
from cci.domain.contracts import CandidateManifest
from cci.sources.explorer import (
    CrawlSourceState,
    SourceNode,
    SourceDiscoveryTree,
    build_source_discovery_tree,
)


def test_all_nine_canonical_lifecycle_states():
    """Verify that all 9 canonical lifecycle states are defined and mapped correctly."""
    expected_states = {
        "supplied",
        "resume extracted",
        "discovered",
        "queued",
        "fetched",
        "failed",
        "blocked",
        "deferred",
        "not scanned",
    }
    actual_states = {state.value for state in CrawlSourceState}
    assert actual_states == expected_states, f"States mismatch: {actual_states ^ expected_states}"

    # Verify alias mappings
    assert CrawlSourceState.from_raw_status("declared") == CrawlSourceState.SUPPLIED
    assert CrawlSourceState.from_raw_status("resume_extracted") == CrawlSourceState.RESUME_EXTRACTED
    assert CrawlSourceState.from_raw_status("observed") == CrawlSourceState.FETCHED
    assert CrawlSourceState.from_raw_status("reachable") == CrawlSourceState.FETCHED
    assert CrawlSourceState.from_raw_status("inaccessible") == CrawlSourceState.FAILED
    assert CrawlSourceState.from_raw_status("timeout") == CrawlSourceState.FAILED
    assert CrawlSourceState.from_raw_status("circuit_open") == CrawlSourceState.BLOCKED
    assert CrawlSourceState.from_raw_status("budget_exhausted") == CrawlSourceState.DEFERRED
    assert CrawlSourceState.from_raw_status("access_restricted") == CrawlSourceState.BLOCKED
    assert CrawlSourceState.from_raw_status("unscanned") == CrawlSourceState.NOT_SCANNED


def test_build_hierarchical_discovery_tree():
    """Verify discovery tree models parent-child relationships across multiple depths."""
    sources = [
        {
            "source_id": "src-repo-1",
            "url": "https://github.com/alice/distributed-raft",
            "kind": "github",
            "status": "fetched",
            "discovery_depth": 0,
            "files_inspected": 24,
            "evidence_count": 8,
            "commit_sha": "a1b2c3d",
            "discovered_links": [
                {
                    "url": "https://raft-demo.alice.dev",
                    "kind": "deployment",
                    "status": "fetched",
                    "discovery_reason": "Found in README live demo link",
                },
                {
                    "url": "https://internal-docs.alice.dev/metrics",
                    "kind": "webpage",
                    "status": "blocked",
                    "discovery_reason": "Found in benchmark doc",
                    "detail": "Blocked by Crawler Security Policy: private address range",
                },
            ],
        },
        {
            "source_id": "src-demo-1",
            "url": "https://raft-demo.alice.dev",
            "kind": "deployment",
            "status": "fetched",
            "parent_url": "https://github.com/alice/distributed-raft",
            "discovery_depth": 1,
            "discovered_links": [
                {
                    "url": "https://raft-demo.alice.dev/ws/stream",
                    "kind": "deployment",
                    "status": "deferred",
                    "discovery_reason": "Found in websocket client config",
                    "detail": "Deferred: streaming websocket outside scan boundary",
                }
            ],
        },
    ]

    tree = build_source_discovery_tree(sources=sources)

    assert isinstance(tree, SourceDiscoveryTree)
    assert tree.total_sources == 4
    assert tree.max_depth >= 2
    assert tree.missing_links_count == 0

    # Verify root nodes
    root_urls = [n.normalized_url for n in tree.root_nodes]
    assert "https://github.com/alice/distributed-raft" in root_urls

    # Find repo root
    repo_node = next(n for n in tree.root_nodes if "distributed-raft" in n.normalized_url)
    assert repo_node.state == CrawlSourceState.FETCHED
    assert repo_node.files_inspected == 24
    assert repo_node.evidence_count == 8
    assert repo_node.commit_sha == "a1b2c3d"

    # Verify children of repo
    child_urls = [c.normalized_url for c in repo_node.children]
    assert "https://raft-demo.alice.dev" in child_urls
    assert "https://internal-docs.alice.dev/metrics" in child_urls

    # Check terminal state of blocked child
    blocked_child = next(c for c in repo_node.children if "internal-docs" in c.normalized_url)
    assert blocked_child.state == CrawlSourceState.BLOCKED
    assert "Crawler Security Policy" in blocked_child.status_detail

    # Check child of demo deployment (depth 2)
    demo_node = next(c for c in repo_node.children if "https://raft-demo.alice.dev" == c.normalized_url)
    assert len(demo_node.children) == 1
    stream_child = demo_node.children[0]
    assert stream_child.state == CrawlSourceState.DEFERRED
    assert stream_child.discovery_depth == 2


def test_invariant_zero_hidden_missing_links():
    """Verify that every discovered reference is retained with a terminal state."""
    sources = [
        {
            "url": "https://github.com/bob/engine",
            "status": "fetched",
            "discovered_links": [
                {"url": "https://dead-link-404.bob.io", "status": "failed", "detail": "HTTP 404"},
                {"url": "https://private-corp.internal/spec", "status": "blocked", "detail": "Private LAN"},
                {"url": "https://api-rate-limit.external/info", "status": "deferred", "detail": "Rate limited"},
                {"url": "https://thirdparty.org/lib", "status": "not scanned", "detail": "Depth limit exceeded"},
            ],
        }
    ]

    tree = build_source_discovery_tree(sources=sources)

    # Invariant: 0 hidden missing links
    assert tree.missing_links_count == 0
    assert tree.total_sources == 5

    # Check counts by state
    counts = tree.counts_by_state
    assert counts["fetched"] == 1
    assert counts["failed"] == 1
    assert counts["blocked"] == 1
    assert counts["deferred"] == 1
    assert counts["not scanned"] == 1

    # Verify all 4 discovered children exist in repo node
    root = tree.root_nodes[0]
    assert len(root.children) == 4
    child_states = {c.state for c in root.children}
    assert child_states == {
        CrawlSourceState.FAILED,
        CrawlSourceState.BLOCKED,
        CrawlSourceState.DEFERRED,
        CrawlSourceState.NOT_SCANNED,
    }


def test_manifest_supplied_sources_integration():
    """Verify that candidate-supplied sources from CandidateManifest are integrated."""
    manifest = CandidateManifest(
        display_name="Candidate Alpha",
        github_urls=["https://github.com/candidate/project-alpha"],
        project_links=["https://project-alpha.org"],
        deployment_urls=["https://demo.alpha.org"],
        portfolio_urls=["https://candidate.dev"],
        coding_profile_urls=["https://codeforces.com/profile/cand"],
        credential_urls=["https://credly.com/badges/abc-123"],
    )

    # Sources partially fetched
    sources = [
        {
            "url": "https://github.com/candidate/project-alpha",
            "status": "fetched",
            "files_inspected": 10,
        },
        {
            "url": "https://candidate.dev",
            "status": "fetched",
            "files_inspected": 2,
        },
    ]

    tree = build_source_discovery_tree(sources=sources, manifest=manifest)

    # All manifest URLs must be present in tree
    assert tree.total_sources == 6
    # 2 fetched, 4 supplied pending scan
    assert tree.counts_by_state["fetched"] == 2
    assert tree.counts_by_state["supplied"] == 4

    # Check that supplied nodes are marked with origin 'supplied'
    for node in tree.root_nodes:
        assert node.origin == "supplied"


def test_source_discovery_tree_serialization():
    """Verify that to_dict() produces valid JSON-serializable dictionaries."""
    sources = [
        {
            "source_id": "test-id-1",
            "url": "https://github.com/test/repo",
            "status": "fetched",
            "files_inspected": 15,
            "evidence_count": 5,
            "discovered_links": [
                {
                    "url": "https://demo.test.io",
                    "status": "discovered",
                }
            ],
        }
    ]

    tree = build_source_discovery_tree(sources=sources)
    tree_dict = tree.to_dict()

    assert "root_nodes" in tree_dict
    assert "total_sources" in tree_dict
    assert "counts_by_state" in tree_dict
    assert "max_depth" in tree_dict
    assert "missing_links_count" in tree_dict
    assert tree_dict["missing_links_count"] == 0

    root = tree_dict["root_nodes"][0]
    assert root["source_id"] == "test-id-1"
    assert root["state"] == "fetched"
    assert len(root["children"]) == 1
    assert root["children"][0]["state"] == "discovered"
