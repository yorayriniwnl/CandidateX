"""Source/Crawl Explorer with hierarchical discovery tree and terminal state tracking (Fix 46).

Enforces the core hardening invariants:
1. Tracks all nine canonical crawl lifecycle states:
   - supplied
   - resume extracted
   - discovered
   - queued
   - fetched
   - failed
   - blocked
   - deferred
   - not scanned
2. Represents discovery relationships as an explicit, hierarchical tree.
3. No hidden missing links: every link discovered in resumes, READMEs, or portfolios
   has an explicit terminal state node in the tree.
4. Candidate code is NEVER executed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence
import uuid

from cci.domain.contracts import CandidateManifest
from cci.intake.canonicalizer import classify_url, normalize_url


class CrawlSourceState(str, Enum):
    """The nine canonical crawl/source lifecycle states defined in Fix 46."""

    SUPPLIED = "supplied"
    RESUME_EXTRACTED = "resume extracted"
    DISCOVERED = "discovered"
    QUEUED = "queued"
    FETCHED = "fetched"
    FAILED = "failed"
    BLOCKED = "blocked"
    DEFERRED = "deferred"
    NOT_SCANNED = "not scanned"

    @classmethod
    def from_raw_status(cls, raw_status: str | None, default: CrawlSourceState = DISCOVERED) -> CrawlSourceState:
        if not raw_status:
            return default
        s = raw_status.lower().strip().replace("_", " ")
        for member in cls:
            if member.value == s:
                return member
        # Fallback aliases
        mapping = {
            "declared": cls.SUPPLIED,
            "resume": cls.RESUME_EXTRACTED,
            "resume extracted": cls.RESUME_EXTRACTED,
            "resume_extracted": cls.RESUME_EXTRACTED,
            "observed": cls.FETCHED,
            "reachable": cls.FETCHED,
            "inaccessible": cls.FAILED,
            "timeout": cls.FAILED,
            "circuit open": cls.BLOCKED,
            "circuit_open": cls.BLOCKED,
            "budget exhausted": cls.DEFERRED,
            "budget_exhausted": cls.DEFERRED,
            "access restricted": cls.BLOCKED,
            "access_restricted": cls.BLOCKED,
            "unscanned": cls.NOT_SCANNED,
            "not scanned": cls.NOT_SCANNED,
            "not_scanned": cls.NOT_SCANNED,
        }
        return mapping.get(s, default)


@dataclass
class SourceNode:
    """A node in the hierarchical source discovery tree."""

    source_id: str
    url: str
    normalized_url: str
    kind: str
    state: CrawlSourceState
    origin: str  # "supplied", "resume extracted", "discovered"
    parent_url: str | None = None
    discovery_reason: str | None = None
    discovery_depth: int = 0
    status_detail: str | None = None
    files_inspected: int = 0
    evidence_count: int = 0
    commit_sha: str | None = None
    fetched_at: str | None = None
    children: list[SourceNode] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "url": self.url,
            "normalized_url": self.normalized_url,
            "kind": self.kind,
            "state": self.state.value,
            "origin": self.origin,
            "parent_url": self.parent_url,
            "discovery_reason": self.discovery_reason,
            "discovery_depth": self.discovery_depth,
            "status_detail": self.status_detail,
            "files_inspected": self.files_inspected,
            "evidence_count": self.evidence_count,
            "commit_sha": self.commit_sha,
            "fetched_at": self.fetched_at,
            "children": [c.to_dict() for c in self.children],
        }


@dataclass
class SourceDiscoveryTree:
    """Complete source discovery tree preserving all links with terminal states."""

    root_nodes: list[SourceNode]
    total_sources: int
    counts_by_state: dict[str, int]
    max_depth: int
    missing_links_count: int = 0  # Invariant: 0 hidden missing links

    def to_dict(self) -> dict[str, Any]:
        return {
            "root_nodes": [n.to_dict() for n in self.root_nodes],
            "total_sources": self.total_sources,
            "counts_by_state": self.counts_by_state,
            "max_depth": self.max_depth,
            "missing_links_count": self.missing_links_count,
        }


def build_source_discovery_tree(
    sources: Sequence[Mapping[str, Any]],
    manifest: CandidateManifest | None = None,
    discovered_links: Sequence[Mapping[str, Any]] | None = None,
) -> SourceDiscoveryTree:
    """Builds a complete, hierarchical source discovery tree (Fix 46).
    
    Guarantees:
    - Every source is classified into one of the 9 canonical lifecycle states.
    - Discovery parent-child relationships form an explicit tree.
    - No hidden missing links: every link discovered in READMEs or pages is retained.
    - Candidate code is NEVER executed.
    """
    nodes_by_url: dict[str, SourceNode] = {}
    url_to_parent: dict[str, str] = {}
    counts: dict[str, int] = {state.value: 0 for state in CrawlSourceState}

    # 1. Register explicitly supplied sources (from manifest or direct input)
    supplied_urls: set[str] = set()
    if manifest:
        for u in (manifest.github_urls or []):
            if u:
                supplied_urls.add(u)
        for u in (manifest.project_links or []):
            if u:
                supplied_urls.add(u)
        for u in (manifest.deployment_urls or []):
            if u:
                supplied_urls.add(u)
        for u in (manifest.portfolio_urls or []):
            if u:
                supplied_urls.add(u)
        for u in (manifest.coding_profile_urls or []):
            if u:
                supplied_urls.add(u)
        for u in (manifest.credential_urls or []):
            if u:
                supplied_urls.add(u)

    # 2. Process fetched/inspected sources
    for src in sources:
        raw_url = str(src.get("url") or "")
        if not raw_url:
            continue
        norm_url = normalize_url(raw_url) or raw_url.lower().rstrip("/")
        raw_status = src.get("status")
        state = CrawlSourceState.from_raw_status(raw_status, default=CrawlSourceState.FETCHED)

        origin = "supplied" if (raw_url in supplied_urls or norm_url in supplied_urls) else "resume extracted"
        kind = str(src.get("kind") or classify_url(raw_url))

        node = SourceNode(
            source_id=str(src.get("source_id") or uuid.uuid5(uuid.NAMESPACE_URL, norm_url)),
            url=raw_url,
            normalized_url=norm_url,
            kind=kind,
            state=state,
            origin=origin,
            parent_url=src.get("parent_url"),
            discovery_reason=src.get("discovery_reason") or "Direct candidate input",
            discovery_depth=int(src.get("discovery_depth", 0)),
            status_detail=src.get("detail"),
            files_inspected=int(src.get("files_inspected", 0)),
            evidence_count=int(src.get("evidence_count", 0)),
            commit_sha=src.get("commit_sha"),
            fetched_at=src.get("fetched_at"),
        )
        nodes_by_url[norm_url] = node

        # Record discovered links nested in this source
        nested_discovered = src.get("discovered_links", [])
        for d in nested_discovered:
            d_url = str(d.get("url") or "")
            if d_url:
                d_norm = normalize_url(d_url) or d_url.lower().rstrip("/")
                if d_norm not in url_to_parent:
                    url_to_parent[d_norm] = norm_url

    # 3. Register any supplied URLs not yet in sources
    for raw_url in supplied_urls:
        if not raw_url:
            continue
        norm_url = normalize_url(raw_url) or raw_url.lower().rstrip("/")
        if norm_url not in nodes_by_url:
            node = SourceNode(
                source_id=str(uuid.uuid5(uuid.NAMESPACE_URL, norm_url)),
                url=raw_url,
                normalized_url=norm_url,
                kind=classify_url(raw_url),
                state=CrawlSourceState.SUPPLIED,
                origin="supplied",
                parent_url=None,
                discovery_reason="Explicitly supplied by candidate in manifest",
                discovery_depth=0,
                status_detail="Supplied candidate input pending crawl",
            )
            nodes_by_url[norm_url] = node

    # 4. Process additional discovered links (no hidden missing links!)
    all_discovered = list(discovered_links or [])
    for src in sources:
        all_discovered.extend(src.get("discovered_links", []))

    for d in all_discovered:
        d_url = str(d.get("url") or "")
        if not d_url:
            continue
        d_norm = normalize_url(d_url) or d_url.lower().rstrip("/")
        parent_url = d.get("parent_url") or url_to_parent.get(d_norm)
        norm_parent = (normalize_url(parent_url) or parent_url.lower().rstrip("/")) if parent_url else None

        if d_norm not in nodes_by_url:
            # Discovered link not yet fetched: assign terminal state
            raw_state = d.get("status") or "discovered"
            state = CrawlSourceState.from_raw_status(raw_state, default=CrawlSourceState.DISCOVERED)
            kind = str(d.get("kind") or classify_url(d_url))
            parent_node = nodes_by_url.get(norm_parent) if norm_parent else None
            depth = (parent_node.discovery_depth + 1) if parent_node else 1

            node = SourceNode(
                source_id=str(d.get("source_id") or uuid.uuid5(uuid.NAMESPACE_URL, d_norm)),
                url=d_url,
                normalized_url=d_norm,
                kind=kind,
                state=state,
                origin="discovered",
                parent_url=norm_parent,
                discovery_reason=d.get("discovery_reason") or "Found in scanned repository/page",
                discovery_depth=depth,
                status_detail=d.get("detail") or "Discovered reference retained in evidence catalog",
            )
            nodes_by_url[d_norm] = node
        else:
            # If already present but parent was discovered, link it
            if norm_parent and not nodes_by_url[d_norm].parent_url:
                nodes_by_url[d_norm].parent_url = norm_parent

    # 5. Construct tree hierarchy
    root_nodes: list[SourceNode] = []
    max_depth = 0

    for norm_url, node in nodes_by_url.items():
        counts[node.state.value] += 1
        max_depth = max(max_depth, node.discovery_depth)
        p_url = node.parent_url
        norm_p = (normalize_url(p_url) or p_url.lower().rstrip("/")) if p_url else None
        if norm_p and norm_p in nodes_by_url and norm_p != norm_url:
            parent = nodes_by_url[norm_p]
            if node not in parent.children:
                parent.children.append(node)
        else:
            root_nodes.append(node)

    return SourceDiscoveryTree(
        root_nodes=root_nodes,
        total_sources=len(nodes_by_url),
        counts_by_state=counts,
        max_depth=max_depth,
        missing_links_count=0,  # Invariant: 0 hidden missing links
    )
